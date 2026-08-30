"""群管理助手 — 配置模型"""

from __future__ import annotations

from typing import Any

from maibot_sdk import Field, PluginConfigBase


class PluginSectionConfig(PluginConfigBase):
    __ui_label__ = "插件开关"; __ui_icon__ = "power"; __ui_order__ = 0
    enabled: bool = Field(default=False, description="是否启用插件")
    config_version: str = Field(default="2.7.0", description="配置版本")

class AdminSectionConfig(PluginConfigBase):
    __ui_label__ = "管理员权限"; __ui_icon__ = "shield"; __ui_order__ = 1
    admins: list[str] = Field(default_factory=list, description="人类管理员QQ号列表")
    allow_group_owner: bool = Field(default=True, description="是否允许群主执行/admin命令")
    owner_allowed_commands: list[str] = Field(default_factory=list, description="群主可用命令白名单")
    deny_response: str = Field(default="silent", description="非授权用户行为: silent/reply")
    allow_member_self_modify: bool = Field(default=False, description="允许普通成员通过命令修改自己的专属头衔和群名片")

class IdentitySectionConfig(PluginConfigBase):
    __ui_label__ = "身份标识"; __ui_icon__ = "user"; __ui_order__ = 2
    bot_nickname: str = Field(default="麦麦", description="Bot昵称")
    auto_detect: bool = Field(default=True, description="留空自动获取bot角色")
    bot_qq: str = Field(default="", description="Bot的QQ号,留空则从消息事件自动获取")
    override_roles: dict[str, str] = Field(default_factory=dict, description="手动覆盖指定群的bot角色")
    role_cache_ttl_seconds: int = Field(default=600, description="群成员身份缓存有效期(秒)")
    bot_role_refresh_seconds: int = Field(default=300, description="Bot自身角色刷新间隔(秒)")
    sender_role_refresh_seconds: int = Field(default=120, description="发言者身份主动刷新间隔(秒)")

class AutoModerateSectionConfig(PluginConfigBase):
    __ui_label__ = "自动审核"; __ui_icon__ = "zap"; __ui_order__ = 3
    enabled: bool = Field(default=True, description="是否启用自动审核")
    enabled_groups: list[str] = Field(default_factory=list, description="启用插件的群号白名单")

class SafeguardSectionConfig(PluginConfigBase):
    __ui_label__ = "安全管理"; __ui_icon__ = "shield-off"; __ui_order__ = 4
    max_mute_duration: int = Field(default=3600, description="最大禁言秒数")
    kick_require_confirm: bool = Field(default=True, description="踢人前LLM必须先调用group_get_member")
    mute_cooldown: int = Field(default=300, description="同用户禁言最小间隔秒")
    daily_mute_limit: int = Field(default=10, description="每群每日禁言上限")
    daily_kick_limit: int = Field(default=3, description="每群每日踢人上限")
    protected_users: list[str] = Field(default_factory=list, description="全局保护名单")
    exempt_users: dict[str, list[str]] = Field(default_factory=dict, description="按群豁免列表")
    auto_exempt_admins: bool = Field(default=True, description="自动豁免群主/管理员")

class WarningSectionConfig(PluginConfigBase):
    __ui_label__ = "警告系统"; __ui_icon__ = "alert-triangle"; __ui_order__ = 5
    enabled: bool = Field(default=True, description="是否启用警告系统")
    spam_warn_threshold: int = Field(default=3, description="刷屏警告阈值")
    spam_warn_window: int = Field(default=600, description="刷屏计数窗口(秒)")
    abuse_warn_threshold: int = Field(default=1, description="辱骂警告阈值")
    abuse_warn_window: int = Field(default=3600, description="辱骂计数窗口(秒)")
    ad_warn_threshold: int = Field(default=1, description="广告警告阈值")
    ad_warn_window: int = Field(default=1800, description="广告计数窗口(秒)")

class EscalationStepConfig(PluginConfigBase):
    within_hours: int = Field(default=24, description="回溯小时数")
    count: int = Field(default=1, description="触发次数")
    action: str = Field(default="mute", description="动作: mute/kick")
    max_duration: int = Field(default=600, description="最大禁言秒数(仅mute时有效)")

class EscalationSectionConfig(PluginConfigBase):
    __ui_label__ = "处罚阶梯"; __ui_icon__ = "trending-up"; __ui_order__ = 6
    enabled: bool = Field(default=True, description="是否启用处罚阶梯")
    escalation_steps: list[EscalationStepConfig] = Field(default_factory=list, description="处罚阶梯列表")

class GroupApproveOverrideConfig(PluginConfigBase):
    group_id: str = Field(default="", description="群号")
    default_action: str = Field(default="ignore", description="默认动作: ignore/approve/reject")
    require_keywords: str = Field(default="", description="必须包含的关键词(逗号分隔, 留空=不过滤)")
    reject_keywords: str = Field(default="", description="拒绝关键词(逗号分隔)")
    daily_approve_limit: int = Field(default=0, description="每日自动通过上限(0=使用全局)")
    daily_reject_limit: int = Field(default=0, description="每日自动拒绝上限(0=使用全局)")

class AutoApproveSectionConfig(PluginConfigBase):
    __ui_label__ = "自动审批入群"; __ui_icon__ = "user-plus"; __ui_order__ = 7
    enabled: bool = Field(default=False, description="是否启用自动审批")
    default_action: str = Field(default="ignore", description="默认动作: ignore/approve/reject")
    require_message_keywords: list[str] = Field(default_factory=list, description="必须包含的关键词")
    reject_keywords: list[str] = Field(default_factory=list, description="拒绝关键词")
    max_pending_seconds: int = Field(default=300, description="审批超时秒数")
    daily_approve_limit: int = Field(default=5, description="每日自动通过上限")
    daily_reject_limit: int = Field(default=10, description="每日自动拒绝上限")
    check_interval_seconds: int = Field(default=120, description="自动检查间隔(秒), 0=禁用")
    groups: list[GroupApproveOverrideConfig] = Field(default_factory=list, description="按群覆盖设置(数组)")

class LoggingSectionConfig(PluginConfigBase):
    __ui_label__ = "日志与记录"; __ui_icon__ = "file-text"; __ui_order__ = 8
    max_log_entries: int = Field(default=2000, description="操作日志最大条数")
    default_log_lines: int = Field(default=10, description="/admin log 默认行数")
    verbose_logging: bool = Field(default=False, description="详细日志: 输出完整注入prompt和守门详情，用于排查问题")

class PromptsSectionConfig(PluginConfigBase):
    __ui_label__ = "提示词"; __ui_icon__ = "message-square"; __ui_order__ = 9
    auto_moderate_system: str = Field(default=(
        "【群管理】你是本群 Bot，身份：{bot_role}；可用操作：{available_actions}。\n"
        "处理规则：广告/诈骗→撤回+禁言10-30分；连续刷屏→先提醒，再犯禁言5-10分；辱骂→撤回+禁言1-6小时，再犯踢；"
        "色情/违法→撤回+踢；优质分享→设精华；不确定→先观察。\n"
        "执行要求：操作前先调用 group_get_member 确认目标；撤回/精华需先获取 message_id；"
        "必须真实调用对应 group_* 工具，未调用不得声称已执行；执行后自然回复，不要复述“已将xx禁言”。\n"
        "正常聊天优先，发现违规再处理。"
    ), description="自动审核系统提示词（Replyer 用）。默认模板只使用 {bot_role}/{available_actions}，发言者/群号由插件动态追加；自定义时也可使用 {sender_role}/{sender_id}")
    planner_moderate_system: str = Field(default=(
        "# 群管理准则\n"
        "Bot 身份：{bot_role}；可用操作：{available_actions}。\n"
        "处理规则：广告/诈骗→撤回+禁言10-30分；刷屏→先警告，再犯禁言5-10分；辱骂→撤回+禁言1-6小时，再犯踢；"
        "色情/违法→撤回+踢（管理员先请示群主）；优质分享→设精华；不确定→先观察。\n"
        "执行要求：操作前先调用 group_get_member；禁言最长1小时，踢出前确认；"
        "需执行时本轮直接调用 group_* 工具，未调用不得声称已执行。"
    ), description="规划器系统提示词（Planner 决策用）。默认模板只使用 {bot_role}/{available_actions}，发言者/群号由插件动态追加；自定义时也可使用 {sender_role}/{sender_id}")
    command_denied_message: str = Field(default="你没有权限执行此操作。", description="权限拒绝回复")

class GroupAdminConfig(PluginConfigBase):
    plugin: PluginSectionConfig = Field(default_factory=PluginSectionConfig)
    admin: AdminSectionConfig = Field(default_factory=AdminSectionConfig)
    identity: IdentitySectionConfig = Field(default_factory=IdentitySectionConfig)
    auto_moderate: AutoModerateSectionConfig = Field(default_factory=AutoModerateSectionConfig)
    safeguard: SafeguardSectionConfig = Field(default_factory=SafeguardSectionConfig)
    warning: WarningSectionConfig = Field(default_factory=WarningSectionConfig)
    escalation: EscalationSectionConfig = Field(default_factory=EscalationSectionConfig)
    auto_approve: AutoApproveSectionConfig = Field(default_factory=AutoApproveSectionConfig)
    logging: LoggingSectionConfig = Field(default_factory=LoggingSectionConfig)
    prompts: PromptsSectionConfig = Field(default_factory=PromptsSectionConfig)
