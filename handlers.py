"""群管理助手 — EventHandler 与 HookHandler 组件"""

from __future__ import annotations

import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from maibot_sdk import EventHandler, HookHandler
from maibot_sdk.types import ErrorPolicy, EventType, HookMode, HookOrder


# 守门：Bot 回复中"宣称已完成管理操作"的句式 → 对应工具动作。
# 顺序敏感：先匹配更具体的动作（如"解除禁言"优先于"禁言"），命中即停止。
_ACTION_CLAIM_PATTERNS: list[tuple[str, "re.Pattern"]] = [
    ("unmute", re.compile(r"已解禁|已解除\S{0,12}?禁言|解除\S{0,12}?禁言了")),
    ("mute", re.compile(r"已将@?\s*\S{0,12}?\s*禁言|已把\S{0,12}?禁言|已对\S{0,12}?禁言|已经?禁言了|已禁言了")),
    ("kick", re.compile(r"已将@?\s*\S{0,12}?\s*踢出|已把\S{0,12}?踢出|已踢出\S{0,8}?了")),
    ("recall", re.compile(r"已撤回|已经?撤回")),
    ("essence", re.compile(r"已设\S{0,8}?精华|设为精华|已将\S{0,12}?设为精华")),
    ("unessence", re.compile(r"已取消\S{0,8}?精华|取消\S{0,8}?精华了")),
    ("warn", re.compile(r"已警告|已提醒|已向\S{0,12}?发出\S{0,8}?(警告|提醒)")),
    ("notice", re.compile(r"已发布公告|公告已发布")),
    ("delete_notice", re.compile(r"已删除公告|公告已删除")),
    ("approve", re.compile(r"已通过\S{0,8}?申请|已同意\S{0,12}?(入群|申请)")),
    ("reject", re.compile(r"已拒绝\S{0,8}?申请")),
    ("card", re.compile(r"已将\S{0,12}?名片改|已修改\S{0,8}?名片|已改\S{0,8}?名片")),
    ("title", re.compile(r"已\S{0,8}?头衔")),
    ("set_name", re.compile(r"已\S{0,8}?群名改|群名已改")),
]


class HandlerMixin:
    """EventHandler + 5 个 HookHandler + 注入辅助。"""

    PROMPT_MARKER = "[群管理助手 管理上下文]"

    _ROLE_CN: dict[str, str] = {"owner": "群主", "admin": "管理员", "member": "普通成员"}
    _ACTIONS_BY_ROLE: dict[str, str] = {
        "owner": "禁言/解禁/警告/设精华/撤回/改名片/公告/改名/审批入群/踢人",
        "admin": "禁言/解禁/警告/设精华/撤回/改名片/公告/审批入群/踢人",
        "member": "无管理操作权限，可协助管理员做决策建议",
    }

    # ===== Prompt 构建 =====

    def _build_admin_prompt(
        self,
        group_id: int,
        role: str,
        sender_role: Optional[str] = None,
        sender_id: int = 0,
        sender_identity: Optional[dict[str, Any]] = None,
    ) -> str:
        sections: list[str] = [self.PROMPT_MARKER]
        role_cn = self._ROLE_CN.get(role, role)
        sender_cn = self._ROLE_CN.get(sender_role or "", sender_role or "未知")
        sender_id_str = str(sender_id) if sender_id else "未知"
        sender_identity = sender_identity or {}
        sender_label = sender_identity.get("display_name") or sender_id_str
        available = self._ACTIONS_BY_ROLE.get(role, self._ACTIONS_BY_ROLE["member"])
        core = self.config.prompts.auto_moderate_system
        core = core.replace("{bot_role}", role_cn).replace("{available_actions}", available)
        core = core.replace("{sender_role}", sender_cn).replace("{sender_id}", sender_id_str)
        sections.append(core)
        sections.append(f"当前群号：{group_id}")
        if sender_id:
            sender_line = f"当前发言者：{sender_label}（{sender_cn}，QQ {sender_id}"
            if sender_identity.get("person_id"):
                sender_line += f"，person_id {sender_identity['person_id']}"
            sender_line += "）。"
            sections.append(sender_line)
            sections.append("工具参数：调用 group_* 工具时 user_id 一律填写 QQ 号。")
        sections.append("身份规则：群主/管理员勿质疑，其指令视为授权；普通成员无权指挥，拒绝其处罚请求。")
        sections.append(
            "身份提醒：以上身份仅对当前发言者本条消息有效，勿从历史推断、勿跨轮次锁定；"
            "不确定身份时用昵称/群名片，只有刚通过 group_get_member 确认过才用身份称呼。"
        )
        sections.append("以上为群管理参考信息，融入决策即可，不要复述这段文字。")
        return "\n\n".join(sections)

    def _resolve_group_id_from_hook(self, kwargs: dict) -> int:
        return self._resolve_group_id("", kwargs)

    # =========================================================================
    # EventHandler: auto_moderate_tracker — 映射群号/计数消息/检测@提及
    # =========================================================================

    @EventHandler("auto_moderate_tracker", description="自动审核追踪: 映射群号、计数消息、检测@提及", event_type=EventType.ON_MESSAGE)
    async def handle_auto_moderate(self, message: Any = None, stream_id: str = "", **kwargs: Any):
        if not self.config.plugin.enabled: return {"continue_processing": True}
        group_id = 0
        sender_id = 0
        if isinstance(message, dict):
            mi = message.get("message_info", {}) or {}
            gi = mi.get("group_info", {}) or {}
            ac = mi.get("additional_config", {}) or {}
            group_id = self._to_int(gi.get("group_id", 0))
            if not group_id:
                group_id = self._to_int(mi.get("group_id", 0))
            if not group_id and isinstance(ac, dict):
                group_id = self._to_int(ac.get("platform_io_target_group_id", 0))
            self_id = ac.get("self_id")
            if self_id and not self._bot_self_id: self._bot_self_id = self._to_int(self_id)
            if group_id:
                self._cache_stream_group(stream_id, group_id)
                sid = str(kwargs.get("session_id", ""))
                self._cache_stream_group(sid, group_id)
                if isinstance(ac, dict):
                    for k in ("session_id", "stream_id", "chat_id"):
                        v = ac.get(k)
                        self._cache_stream_group(str(v or ""), group_id)
                sender_identity = self._extract_sender_identity(kwargs, message)
                sender_id = sender_identity.get("qq", 0)
                if sender_id:
                    self._cache_stream_sender(stream_id, sender_id)
                    self._cache_stream_sender(sid, sender_id)
                    self._cache_stream_sender_identity(stream_id, sender_identity)
                    self._cache_stream_sender_identity(sid, sender_identity)
                    if isinstance(ac, dict):
                        for k in ("session_id", "stream_id", "chat_id"):
                            v = ac.get(k)
                            self._cache_stream_sender(str(v or ""), sender_id)
                            self._cache_stream_sender_identity(str(v or ""), sender_identity)
        if self.config.logging.verbose_logging and group_id:
            self.ctx.logger.info("[群管理] EventHandler 追踪: group=%s stream_id=%s session_id in kwargs=%s", group_id, stream_id, bool(kwargs.get("session_id")))
        if not self.config.auto_moderate.enabled:
            return {"continue_processing": True}
        if not group_id or not self._is_group_enabled(group_id): return {"continue_processing": True}
        await self._ensure_bot_role(group_id)
        if sender_id:
            await self._refresh_sender_role(group_id, sender_id)
        if time.time() - self._last_cleanup_time > 3600:
            self._cleanup_memory()
        return {"continue_processing": True}

    # =========================================================================
    # HookHandler: chat.receive.after_process — 缓存 session_id → group_id
    # =========================================================================

    @HookHandler(
        "chat.receive.after_process",
        name="group_admin_session_bind",
        description="在消息处理完成后缓存消息ID/会话ID → group_id 映射，供后续注入使用",
        mode=HookMode.BLOCKING,
        order=HookOrder.EARLY,
        error_policy=ErrorPolicy.SKIP,
    )
    async def cache_session_group(self, message: Any = None, **kwargs: Any):
        if not isinstance(message, dict):
            return {"action": "continue"}
        mi = message.get("message_info", {}) or {}
        gi = mi.get("group_info", {}) or {}
        group_id = self._to_int(gi.get("group_id", 0))
        if not group_id:
            group_id = self._to_int(mi.get("group_id", 0))
        if not group_id:
            ac = mi.get("additional_config", {}) or {}
            if isinstance(ac, dict):
                group_id = self._to_int(ac.get("platform_io_target_group_id", 0))
        if group_id <= 0:
            return {"action": "continue"}
        msg_id = str(message.get("message_id", ""))
        self._cache_stream_group(msg_id, group_id)
        sid = str(message.get("session_id", ""))
        self._cache_stream_group(sid, group_id)
        for key in ("session_id", "stream_id", "chat_id"):
            sid2 = str(kwargs.get(key, ""))
            self._cache_stream_group(sid2, group_id)
        ac = mi.get("additional_config", {}) or {}
        if isinstance(ac, dict):
            for k in ("session_id", "stream_id", "chat_id"):
                v = ac.get(k)
                self._cache_stream_group(str(v or ""), group_id)
        sender_identity = self._extract_sender_identity(kwargs, message)
        sender_id = sender_identity.get("qq", 0)
        if sender_id:
            self._cache_stream_sender(msg_id, sender_id)
            self._cache_stream_sender(sid, sender_id)
            self._cache_stream_sender_identity(msg_id, sender_identity)
            self._cache_stream_sender_identity(sid, sender_identity)
            for key in ("session_id", "stream_id", "chat_id"):
                sid2 = str(kwargs.get(key, ""))
                self._cache_stream_sender(sid2, sender_id)
                self._cache_stream_sender_identity(sid2, sender_identity)
            if isinstance(ac, dict):
                for k in ("session_id", "stream_id", "chat_id"):
                    v = ac.get(k)
                    self._cache_stream_sender(str(v or ""), sender_id)
                    self._cache_stream_sender_identity(str(v or ""), sender_identity)
        self.ctx.logger.debug("[群管理] 缓存映射: group=%s msg=%s session=%s", group_id, msg_id, sid or "none")
        return {"action": "continue"}

    # =========================================================================
    # 注入辅助
    # =========================================================================

    def _resolve_injection_group_id(self, **kwargs: Any) -> int:
        if not self.config.plugin.enabled or not self.config.auto_moderate.enabled:
            return 0
        gid = self._resolve_group_id("", kwargs)
        if gid and self._is_group_enabled(gid):
            return gid
        return 0

    async def _prepare_injection(self, **kwargs: Any) -> tuple[int, str, str, int, Optional[str]] | None:
        if not self.config.plugin.enabled or not self.config.auto_moderate.enabled:
            return None
        group_id = self._resolve_injection_group_id(**kwargs)
        if self.config.logging.verbose_logging:
            self.ctx.logger.info("[群管理] 注入检测: group_id=%s", group_id)
        if group_id <= 0:
            return None
        role = await self._ensure_bot_role(group_id) or "member"
        sender_identity = self._resolve_sender_identity_for_injection(kwargs)
        sender_id = sender_identity.get("qq", 0)
        sender_role = await self._refresh_sender_role(group_id, sender_id) if sender_id else None
        prompt = self._build_admin_prompt(group_id, role, sender_role, sender_id, sender_identity)
        return group_id, role, prompt, sender_id, sender_role

    def _resolve_sender_for_injection(self, kwargs: dict) -> int:
        sender_id = self._extract_sender_id(kwargs)
        if sender_id:
            return sender_id
        for key in ("session_id", "stream_id", "chat_id"):
            sid = str(kwargs.get(key, "") or "")
            sender_id = self._lookup_stream_sender(sid)
            if sender_id:
                return sender_id
        return 0

    def _resolve_sender_identity_for_injection(self, kwargs: dict) -> dict[str, Any]:
        identity = self._extract_sender_identity(kwargs)
        if identity.get("qq", 0):
            return identity
        for key in ("session_id", "stream_id", "chat_id"):
            sid = str(kwargs.get(key, "") or "")
            cached = self._lookup_stream_sender_identity(sid)
            if cached.get("qq", 0):
                return cached
        return identity

    # =========================================================================
    # Hook 载荷注入辅助 — 新版 items（Context Item）/ 旧版 messages 双兼容
    # =========================================================================

    @staticmethod
    def _build_system_item(prompt: str) -> dict[str, Any]:
        """构造新版 Context Item 格式的系统消息，供 items 协议注入。"""

        return {
            "item_type": "SystemMessageItem",
            "meta": {
                "item_id": uuid.uuid4().hex,
                "logical_turn_id": None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            "parts": [{"type": "text", "text": prompt}],
        }

    @staticmethod
    def _inject_prompt_into_items(items: list, prompt: str) -> list:
        """向新版 Context Items 列表注入管理提示词。"""

        updated: list[dict[str, Any]] = []
        inserted = False
        for item in items:
            if not isinstance(item, dict):
                updated.append(item)
                continue
            message = dict(item)
            if str(message.get("item_type") or "") == "SystemMessageItem" and not inserted:
                parts = message.get("parts")
                if not isinstance(parts, list):
                    parts = []
                existing_text = "".join(
                    str(part.get("text") or "")
                    for part in parts
                    if isinstance(part, dict) and str(part.get("type") or "").lower() == "text"
                )
                if HandlerMixin.PROMPT_MARKER not in existing_text:
                    message["parts"] = list(parts) + [{"type": "text", "text": f"\n\n{prompt}"}]
                inserted = True
            updated.append(message)
        if not inserted:
            updated.insert(0, HandlerMixin._build_system_item(prompt))
        return updated

    @staticmethod
    def _inject_prompt_into_messages(messages: list, prompt: str) -> list:
        """向旧版 messages 列表注入管理提示词（兼容未升级的旧 MaiBot）。"""

        updated: list[dict[str, Any]] = []
        inserted = False
        for item in messages:
            if not isinstance(item, dict):
                updated.append(item)
                continue
            message = dict(item)
            role_name = str(message.get("role") or "").lower()
            content = str(message.get("content") or message.get("content_text") or "")
            if role_name == "system" and not inserted:
                if HandlerMixin.PROMPT_MARKER not in content:
                    content = f"{content.rstrip()}\n\n{prompt}" if content.strip() else prompt
                    message["content"] = content
                    if "content_text" in message:
                        message["content_text"] = content
                inserted = True
            updated.append(message)
        if not inserted:
            updated.insert(0, {"role": "system", "content": prompt})
        return updated

    def _inject_prompt_into_hook_payload(self, kwargs: dict, prompt: str) -> dict | None:
        """按新版 items / 旧版 messages 协议注入提示词，返回完整修改后 kwargs。"""

        items = kwargs.get("items")
        if isinstance(items, list):
            modified = dict(kwargs)
            modified["items"] = self._inject_prompt_into_items(items, prompt)
            if "item_schema_version" in kwargs:
                modified["item_schema_version"] = kwargs["item_schema_version"]
            return modified
        messages = kwargs.get("messages")
        if isinstance(messages, list):
            modified = dict(kwargs)
            modified["messages"] = self._inject_prompt_into_messages(messages, prompt)
            return modified
        return None

    # =========================================================================
    # HookHandler: before_request — 注入 extra_prompt（v1.4）
    # =========================================================================

    @HookHandler(
        "maisaka.replyer.before_request",
        name="group_admin_replyer_prompt",
        description="[v1.4] 向当前启用群的 Replyer extra_prompt 注入管理提示词，让 LLM 回复时具备管理意识。",
        mode=HookMode.BLOCKING,
        order=HookOrder.EARLY,
        error_policy=ErrorPolicy.SKIP,
    )
    async def inject_admin_prompt(self, **kwargs: Any):
        prep = await self._prepare_injection(**kwargs)
        if not prep: return {"action": "continue"}
        group_id, role, prompt, sender_id, sender_role = prep
        extra = str(kwargs.get("extra_prompt") or "")
        extra = f"{extra}\n\n{prompt}" if extra else prompt
        self.ctx.logger.debug("[群管理] before_request 注入 extra_prompt: group=%s role=%s sender=%s sender_role=%s", group_id, role, sender_id, sender_role)
        modified = dict(kwargs)
        modified["extra_prompt"] = extra
        return {"action": "continue", "modified_kwargs": modified}

    # =========================================================================
    # HookHandler: before_model_request — 注入 items / messages（v1.4，v2.7 适配 items）
    # =========================================================================

    @HookHandler(
        "maisaka.replyer.before_model_request",
        name="group_admin_model_prompt",
        description="[v2.7] 向 Planner/Timing Gate/Replyer 的 Context Items（兼容旧版 messages）直注管理提示词，按群精确注入。",
        mode=HookMode.BLOCKING,
        order=HookOrder.EARLY,
        error_policy=ErrorPolicy.SKIP,
    )
    async def inject_admin_model_prompt(self, **kwargs: Any):
        prep = await self._prepare_injection(**kwargs)
        if not prep: return {"action": "continue"}
        group_id, role, prompt, sender_id, sender_role = prep
        modified = self._inject_prompt_into_hook_payload(kwargs, prompt)
        if modified is None:
            return {"action": "continue"}
        self.ctx.logger.debug(
            "[群管理] before_model_request 注入: group=%s role=%s sender=%s sender_role=%s protocol=%s",
            group_id, role, sender_id, sender_role,
            "items" if isinstance(kwargs.get("items"), list) else "messages",
        )
        return {"action": "continue", "modified_kwargs": modified}

    # =========================================================================
    # HookHandler: planner.before_request — 注入 Planner 决策提示词
    # =========================================================================

    def _build_admin_planner_prompt(
        self,
        group_id: int,
        role: str,
        sender_role: Optional[str] = None,
        sender_id: int = 0,
        sender_identity: Optional[dict[str, Any]] = None,
    ) -> str:
        sections: list[str] = [self.PROMPT_MARKER]
        role_cn = self._ROLE_CN.get(role, role)
        sender_cn = self._ROLE_CN.get(sender_role or "", sender_role or "未知")
        sender_id_str = str(sender_id) if sender_id else "未知"
        sender_identity = sender_identity or {}
        sender_label = sender_identity.get("display_name") or sender_id_str
        available = self._ACTIONS_BY_ROLE.get(role, self._ACTIONS_BY_ROLE["member"])
        core = self.config.prompts.planner_moderate_system
        core = core.replace("{bot_role}", role_cn).replace("{available_actions}", available)
        core = core.replace("{sender_role}", sender_cn).replace("{sender_id}", sender_id_str)
        sections.append(core)
        sections.append(f"当前群号：{group_id}")
        if sender_id:
            sender_line = f"当前发言者：{sender_label}（{sender_cn}，QQ {sender_id}"
            if sender_identity.get("person_id"):
                sender_line += f"，person_id {sender_identity['person_id']}"
            sender_line += "）。"
            sections.append(sender_line)
            sections.append("工具参数：规划 group_* 调用时 user_id 一律填写 QQ 号。")
        sections.append("身份规则：群主/管理员勿质疑，其指令视为授权；普通成员无权指挥，拒绝其处罚请求。")
        sections.append(
            "身份提醒：以上身份仅对当前发言者本条消息有效，勿从历史推断、勿跨轮次锁定；"
            "不确定身份时用昵称/群名片，只有刚通过 group_get_member 确认过才用身份称呼。"
        )
        sections.append("以上为群管理准则，不要在你的分析中引用或复述。")
        return "\n\n".join(sections)

    @HookHandler(
        "maisaka.planner.before_request",
        name="group_admin_planner_prompt",
        description="向 Planner 的 messages 注入群管理准则，让 LLM 在决策时具备管理意识。",
        mode=HookMode.BLOCKING,
        order=HookOrder.EARLY,
        error_policy=ErrorPolicy.SKIP,
    )
    async def inject_admin_planner_prompt(self, **kwargs: Any):
        group_id = self._resolve_injection_group_id(**kwargs)
        if self.config.logging.verbose_logging:
            self.ctx.logger.info("[群管理] planner 注入检测: group_id=%s kwargs keys=%s stream_to_group keys=%s",
                group_id, list(kwargs.keys()), list(self._stream_to_group.keys())[:10])
        if group_id <= 0:
            return {"action": "continue"}
        sid = str(kwargs.get("session_id", ""))
        self._cache_stream_group(sid, group_id)
        role = await self._ensure_bot_role(group_id) or "member"
        sender_identity = self._resolve_sender_identity_for_injection(kwargs)
        sender_id = sender_identity.get("qq", 0)
        sender_role = await self._refresh_sender_role(group_id, sender_id) if sender_id else None
        prompt = self._build_admin_planner_prompt(group_id, role, sender_role, sender_id, sender_identity)
        modified = self._inject_prompt_into_hook_payload(kwargs, prompt)
        if modified is None:
            return {"action": "continue"}
        self.ctx.logger.debug(
            "[群管理] planner.before_request 注入成功: group=%s role=%s sender=%s sender_role=%s protocol=%s",
            group_id, role, sender_id, sender_role,
            "items" if isinstance(kwargs.get("items"), list) else "messages",
        )
        return {"action": "continue", "modified_kwargs": modified}

    # =========================================================================
    # HookHandler: after_response — 守门: 拦截不当管理回复
    # =========================================================================

    @HookHandler(
        "maisaka.replyer.after_response",
        name="group_admin_reply_guard",
        description="守门: 检查 LLM 回复中的不当管理行为（宣称无权限但实际有、编造操作结果等）",
        mode=HookMode.BLOCKING,
        order=HookOrder.LATE,
        error_policy=ErrorPolicy.SKIP,
    )
    async def guard_admin_response(self, **kwargs: Any):
        if not self.config.plugin.enabled or not self.config.auto_moderate.enabled:
            return {"action": "continue"}
        group_id = self._resolve_group_id_from_hook(kwargs)
        if not group_id or not self._is_group_enabled(group_id):
            return {"action": "continue"}
        response_text = ""
        for key in ("response", "reply", "content", "text", "message"):
            val = kwargs.get(key)
            if isinstance(val, str) and val.strip():
                response_text = val
                break
        if not response_text:
            return {"action": "continue"}
        role = self._get_group_role(group_id) or "member"
        if role not in ("owner", "admin"):
            return {"action": "continue"}
        deny_flags = ("我没有权限", "我不能执行", "我无法进行", "我做不到", "权限不足", "无法禁言", "无法踢人", "我没有这个权限")
        legit_reason_flags = ("保护名单", "豁免名单", "冷却中", "已达每日上限", "处罚阶梯", "未找到成员")
        if any(flag in response_text for flag in deny_flags) and not any(flag in response_text for flag in legit_reason_flags):
            role_cn = self._ROLE_CN.get(role, role)
            correction = f"我是{role_cn}，我来处理。"
            if self.config.logging.verbose_logging:
                self.ctx.logger.info(f"[群管理] 守门拦截: Bot(role={role})错误宣称无权限, group={group_id}\n--- 原始回复 ---\n{response_text}\n--- 替换为 ---\n{correction}")
            else:
                self.ctx.logger.warning(f"[群管理] 守门拦截: Bot(role={role})错误宣称无权限, group={group_id}, text={response_text[:80]}")
            modified = dict(kwargs)
            modified["response"] = correction
            return {"action": "continue", "modified_kwargs": modified}
        for action, claim_pattern in _ACTION_CLAIM_PATTERNS:
            if not claim_pattern.search(response_text):
                continue
            if self._was_tool_executed_recently(group_id, action):
                break
            correction = "刚才提到的操作我并没有真正执行，先不打扰大家了。"
            if self.config.logging.verbose_logging:
                self.ctx.logger.info(f"[群管理] 守门拦截: Bot 口头宣称已执行但无真实工具调用, group={group_id}, action={action}\n--- 原始回复 ---\n{response_text}\n--- 替换为 ---\n{correction}")
            else:
                self.ctx.logger.warning(f"[群管理] 守门拦截: Bot 口头宣称已执行但无真实工具调用, group={group_id}, action={action}, text={response_text[:80]}")
            modified = dict(kwargs)
            modified["response"] = correction
            return {"action": "continue", "modified_kwargs": modified}
        return {"action": "continue"}
