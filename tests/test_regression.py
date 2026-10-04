"""Run with the deployed MaiBot Python: python -m unittest discover -s tests -v."""
import ast
import importlib.util
import logging
import os
from pathlib import Path
import sys
import time
import types
import unittest
from unittest.mock import AsyncMock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("group_admin_test_package", ROOT / "__init__.py", submodule_search_locations=[str(ROOT)])
package = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = package
spec.loader.exec_module(package)
from group_admin_test_package.plugin import GroupAdminPlugin


class RegressionTests(unittest.IsolatedAsyncioTestCase):
    def make_plugin(self, role="owner"):
        plugin = GroupAdminPlugin()
        plugin.set_plugin_config({"plugin": {"config_version": "2.7.1", "enabled": True}, "identity": {"auto_detect": False, "override_roles": {"100": role}}, "auto_moderate": {"enabled_groups": ["100"]}})
        plugin._cache_stream_group("session", 100)
        plugin._bot_self_id = 999
        plugin._ctx = types.SimpleNamespace(logger=logging.getLogger("regression"), send=types.SimpleNamespace(text=AsyncMock(), hybrid=AsyncMock()), api=types.SimpleNamespace(call=AsyncMock(side_effect=self.api)))
        plugin._save_exempt_users = AsyncMock()
        return plugin

    async def api(self, api_name, version="1", **kwargs):
        if api_name.endswith("get_group_member_info"):
            return {"role": "admin", "nickname": "测试", "card": "测试名片", "title": "测试头衔"}
        if api_name.endswith("get_group_member_list"):
            return [{"user_id": 200, "nickname": "测试", "title": "测试头衔"}]
        if api_name.endswith("get_login_info"):
            return {"user_id": 999}
        if api_name.endswith("get_group_shut_list"):
            return {"status": "ok", "data": []}
        if api_name.endswith("get_group_system_msg"):
            return {"status": "ok", "data": {"join_requests": [{"flag": "request", "user_id": 200, "group_id": 100, "time": time.time()}]}}
        return {"status": "ok", "retcode": 0, "data": {"notice_id": "notice"}}

    async def test_all_18_tools(self):
        cases = {
            "warn_user": {"user_id": 200, "violation_type": "spam", "reason": "测试"},
            "mute_user": {"user_id": 200, "duration": 21600}, "unmute_user": {"user_id": 200},
            "kick_user": {"user_id": 200}, "set_user_card": {"user_id": 200, "card": "名片"},
            "set_title": {"user_id": 200, "title": "头衔"}, "set_name": {"name": "测试群"},
            "approve_join": {"request_id": "request"}, "reject_join": {"request_id": "request"},
            "post_notice": {"content": "公告"}, "delete_notice": {"notice_id": "notice"},
            "set_essence": {"message_id": "123"}, "unset_essence": {"message_id": "123"},
            "recall_msg": {"message_id": "123"}, "get_member": {"user_id": 200},
            "get_shut_list": {}, "get_notice": {}, "get_system_msg": {},
        }
        for method, params in cases.items():
            with self.subTest(tool=method):
                plugin = self.make_plugin()
                result = await getattr(plugin, "tool_" + method)(group_id=100, stream_id="session", **params)
                self.assertIn("content", result)
                self.assertNotRegex(result["content"], "未能生效|无法|未找到|权限不足")

    async def test_owner_bypasses_all_safeguards(self):
        p = self.make_plugin()
        p.config.safeguard.protected_users = ["200"]
        p.config.safeguard.exempt_users = {"100": ["200"]}
        p.config.admin.admins = ["200"]
        today = p._today_key()
        for counter in (p._daily_mute_count, p._daily_kick_count, p._daily_approve_count, p._daily_reject_count):
            counter[100] = {today: 999}
        p._last_mute_time[(100, 200)] = time.time()
        self.assertFalse((await p._is_protected(100, 200))[0])
        self.assertIsNone(p._check_escalation(100, 200))
        self.assertIn("已将", (await p.tool_mute_user(100, 200, 21600))["content"])
        self.assertEqual(p.ctx.api.call.call_args.kwargs["duration"], 21600)
        self.assertIn("已将", (await p.tool_kick_user(100, 200))["content"])
        self.assertIn("已通过", (await p.tool_approve_join(100, "request"))["content"])
        self.assertIn("已拒绝", (await p.tool_reject_join(100, "request"))["content"])

    async def test_admin_safeguards_remain(self):
        p = self.make_plugin("admin")
        p.config.safeguard.protected_users = ["200"]
        self.assertTrue((await p._is_protected(100, 200))[0])
        self.assertIn("无法禁言", (await p.tool_mute_user(100, 200, 21600))["content"])
        p.config.safeguard.protected_users = []
        p.config.safeguard.auto_exempt_admins = False
        self.assertIn("已将", (await p.tool_mute_user(100, 200, 21600))["content"])
        self.assertEqual(p.ctx.api.call.call_args.kwargs["duration"], 3600)
        self.assertIn("冷却中", (await p.tool_mute_user(100, 200, 600))["content"])
        self.assertIn("先调用", (await p.tool_kick_user(100, 200))["content"])

    async def test_lookup_failure_does_not_confirm_target(self):
        p = self.make_plugin("admin")
        p.ctx.api.call = AsyncMock(return_value=None)
        await p.tool_get_member(100, 200)
        self.assertNotIn(200, p._get_member_called.get(100, {}))

    async def test_failed_api_and_invalid_duration(self):
        p = self.make_plugin()
        p.ctx.api.call = AsyncMock(return_value={"status": "failed", "retcode": 1})
        self.assertIn("未能生效", (await p.tool_set_name(100, "测试"))["content"])
        self.assertFalse(p._was_tool_executed_recently(100, "set_name"))
        for duration in (-1, 0, 2592001):
            self.assertIn("必须", (await p.tool_mute_user(100, 200, duration))["content"])

    async def test_login_lookup_resolves_bot_id(self):
        p = self.make_plugin()
        p.config.identity.auto_detect = True
        p._bot_self_id = None
        self.assertEqual(await p._ensure_bot_role(100), "admin")
        self.assertEqual(p._bot_self_id, 999)

    async def test_prompt_hooks_preserve_payload(self):
        p = self.make_plugin()
        for hook in (p.inject_admin_planner_prompt, p.inject_admin_model_prompt):
            payload = {"session_id": "session", "items": [], "item_schema_version": 1, "tool_definitions": ["keep"], "task_name": "keep"}
            result = await hook(**payload)
            modified = result["modified_kwargs"]
            self.assertEqual(modified["task_name"], "keep")
            self.assertEqual(modified["tool_definitions"], ["keep"])
            self.assertIn("无需", modified["items"][0]["parts"][0]["text"])
            again = await hook(**modified)
            self.assertEqual(again["modified_kwargs"]["items"], modified["items"])

    async def test_member_cannot_command_owner_bot(self):
        p = self.make_plugin()
        p._check_target_role = AsyncMock(return_value="member")
        self.assertFalse(await p._check_command_permission("session", 100, 200, minimum_role="admin"))

    async def test_all_29_commands(self):
        matched = {"target": "200", "qq": "200", "duration": "360", "unit": "分钟", "reason": "测试", "type": "spam", "title": "头衔", "card": "名片", "name": "群名", "content": "公告", "notice_id": "notice", "request_id": "request"}
        methods = [name for name in dir(GroupAdminPlugin) if name.startswith("cmd_")]
        self.assertEqual(len(methods), 29)
        for method in methods:
            with self.subTest(command=method):
                p = self.make_plugin()
                p.config.admin.admins = ["300"]
                p._send_at_text = AsyncMock()
                p._extract_reply_message_id = lambda kwargs: "123"
                result = await getattr(p, method)(stream_id="session", user_id="300", matched_groups=matched, reply_message_id="123", text="/测试")
                self.assertEqual(result, (True, "", True))

    async def test_owner_command_mute_and_kick_ignore_limits(self):
        p = self.make_plugin()
        p.config.admin.admins = ["300"]
        p.config.safeguard.protected_users = ["200"]
        p._daily_mute_count[100] = {p._today_key(): 999}
        p._daily_kick_count[100] = {p._today_key(): 999}
        p._last_mute_time[(100, 200)] = time.time()
        p._send_at_text = AsyncMock()
        await p.cmd_admin_mute(stream_id="session", user_id="300", matched_groups={"target": "200", "duration": "6", "unit": "小时"})
        self.assertEqual(p.ctx.api.call.call_args.kwargs["duration"], 21600)
        await p.cmd_admin_kick(stream_id="session", user_id="300", matched_groups={"target": "200"})
        self.assertTrue(p.ctx.api.call.call_args.kwargs["api_name"].endswith("set_group_kick"))

    async def test_auto_approval_handles_join_and_invite_without_owner_quota(self):
        p = self.make_plugin()
        p.config.auto_approve.enabled = True
        p.config.auto_approve.default_action = "approve"
        p._daily_approve_count[100] = {p._today_key(): 999}
        async def api(api_name, **kwargs):
            if api_name.endswith("get_group_system_msg"):
                return {"data": {"join_requests": [{"flag": "join", "group_id": 100, "user_id": 200}], "invited_requests": [{"flag": "invite", "group_id": 100, "user_id": 201}]}}
            return await self.api(api_name, **kwargs)
        p.ctx.api.call = AsyncMock(side_effect=api)
        await p._check_join_requests()
        approvals = [call.kwargs["params"] for call in p.ctx.api.call.call_args_list if call.kwargs["api_name"].endswith("set_group_add_request")]
        self.assertEqual({item["sub_type"] for item in approvals}, {"add", "invite"})
        self.assertEqual(p._daily_approve_count[100][p._today_key()], 1001)

    async def test_message_identity_precedes_latest_session_sender(self):
        p = self.make_plugin()
        p._cache_stream_sender_identity("session", {"qq": 201})
        p._cache_stream_sender_identity("reply", {"qq": 200})
        self.assertEqual(p._resolve_sender_identity_for_injection({"session_id": "session", "reply_message_id": "reply"})["qq"], 200)

    async def test_guard_preserves_platform_failure(self):
        p = self.make_plugin()
        await p._ensure_bot_role(100)
        result = await p.guard_admin_response(session_id="session", response="权限不足，接口执行失败")
        self.assertNotIn("modified_kwargs", result)

    async def test_adapter_signatures_when_bot_root_provided(self):
        bot_root = os.environ.get("MAIBOT_AUDIT_ROOT")
        if not bot_root:
            self.skipTest("Set MAIBOT_AUDIT_ROOT for deployed adapter contract validation")
        endpoints = {}
        for path in (Path(bot_root) / "plugins" / "snowluma-adapter" / "apis").glob("*.py"):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8-sig"))):
                if not isinstance(node, ast.AsyncFunctionDef): continue
                for dec in node.decorator_list:
                    if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name) and dec.func.id == "API":
                        endpoints[ast.literal_eval(dec.args[0])] = {arg.arg for arg in node.args.args if arg.arg != "self"}
        for path in (ROOT / "tools.py", ROOT / "commands.py", ROOT / "plugin_core.py"):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute): continue
                if node.func.attr not in ("_call_api", "_call_action_api"): continue
                keywords = {kw.arg: kw.value for kw in node.keywords}
                if "api_name" not in keywords: continue
                api_name = ast.literal_eval(keywords.pop("api_name"))
                with self.subTest(api=api_name, file=path.name, line=node.lineno):
                    self.assertIn(api_name, endpoints)
                    supplied = {"params"} if node.func.attr == "_call_action_api" else set(keywords)
                    self.assertTrue(supplied <= endpoints[api_name], (supplied, endpoints[api_name]))


if __name__ == "__main__":
    unittest.main()
