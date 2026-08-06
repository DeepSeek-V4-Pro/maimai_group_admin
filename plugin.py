"""群管理助手 v2.4.0 — 给 QQ 群装一个自动小管理员

18 个管理 Tool + 14 条快捷命令 + 5 个 HookHandler，支持禁言/解禁/踢人/警告/设精华/撤回/改名片/
改头衔/改群名/公告发布与删除/入群审批，含 8 步安全护栏 + 按群独立配置。

v2.4 更新：修复 LLM "口头宣称执行但未真实调用工具" 的问题 —— 18 个管理工具
默认以 visible 直接暴露给 LLM（不再依赖 tool_search 延迟发现）、提示词强制真实调用
group_* 工具、守门新增拦截"编造已执行结果"的回复；同步优化插件简介与说明文档。

模块结构：
  config_model.py   配置模型（10 个配置分区，2 个默认提示词）
  plugin_core.py    核心生命周期、后台任务、辅助方法
  tools.py          18 个管理 Tool
  commands.py       14 个管理员命令
  handlers.py       1 个 EventHandler + 5 个 HookHandler
  plugin.py         入口：组合所有模块，导出 create_plugin
"""

from __future__ import annotations

from maibot_sdk import MaiBotPlugin

from .commands import CommandMixin
from .config_model import GroupAdminConfig
from .handlers import HandlerMixin
from .plugin_core import PluginCore
from .tools import ToolMixin


class GroupAdminPlugin(PluginCore, ToolMixin, CommandMixin, HandlerMixin):
    """群管理助手插件 — 组合核心、工具、命令、事件处理器。"""
    config_model = GroupAdminConfig


def create_plugin() -> GroupAdminPlugin:
    """创建群管理助手插件实例。"""
    return GroupAdminPlugin()
