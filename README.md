### Fork 版改动 (2026-07-01)

> 以下为本 fork 在原作者版本基础上的改动。

**入站自动审核增强**
- 新增入站 LLM 审核链路：从 `chat.receive` / `chat.receive.after_process` 提取发送者、文本、图片和消息 ID，并按群白名单异步排队审核
- 新增审核 JSON 约束，自动解析 `action` / `violation_type` / `confidence` / `duration` / `recall` / `reason`
- 新增置信度门槛：`warn` / `mute` 低于 `audit_confidence_threshold` 时不会自动执行，降低误判处置风险
- 新增同一用户近期消息缓存，刷屏判断会参考短期历史，避免把单条链接、文件或普通分享误判为 spam
- 新增审核任务去重和清理：同一消息不会重复审核，完成任务和过期消息记录会随 `_cleanup_memory` 回收

**图片与合并转发审核**
- 新增图片/表情审核：支持从 hash、base64 或 URL 获取图片描述，并将描述交给入站 LLM 判断
- 新增图片描述超时/为空处理策略：`none`、`warn`、`notify_admin`
- `notify_admin` 会 @ 最后发言的群主或管理员人工复核；若近期没有群主/管理员发言记录，则直接通知群主
- 新增 QQ 合并转发识别与展开，尽量读取内部文本和图片后整体审核
- 合并转发默认按单条消息计入近期历史，避免把转发内部多条记录误当作发送者刷屏

**自动处置与对话联动**
- 入站审核结论可自动调用现有 `group_warn_user` / `group_mute_user` / `group_recall_msg`
- 新增 `auto_recall` 开关，审核要求撤回时可选择是否自动撤回原消息
- 新增 `trigger_moderation_reply` 开关，处置成功后可触发麦麦主动回复
- `group_warn_user` 扩展违规类型：新增 `sexual` / `illegal`
- 警告文本改为优先由 LLM 生成自然提示，并通过 `chat.get_stream_by_group_id` / `chat.open_session` 尝试定位群会话发送

**配置与 capability**
- `[auto_moderate]` 新增 `audit_model`、`audit_max_tokens`、`audit_confidence_gate`、`audit_confidence_threshold`
- `[auto_moderate]` 新增 `audit_images`、`image_audit_max_images`、`forwarded_image_audit_max_images`、`image_description_timeout`、`image_unknown_policy`、`image_unknown_notice_use_llm`、`image_unknown_notice_model`
- `[auto_moderate]` 新增 `expand_forwarded_records`、`treat_forwarded_records_as_single_message`、`auto_recall`、`trigger_moderation_reply`
- `[prompts]` 新增 `image_unknown_notice_prompt`，用于编辑图片/表情包描述为空/超时时 LLM 呼叫群主或管理员的提示词；支持 `{bot_style_context}`、`{bot_nickname}`、`{unreadable_count}`、`{unreadable_kind}`、`{unreadable_kind_detail}` 占位符
- 呼叫群主或管理员的 LLM 文案会读取 MaiBot 主程序的 `bot.nickname`、`bot.alias_names`、`personality.personality`、`personality.reply_style`，并按表达风格做最终重写
- `_manifest.json` 新增 `chat.get_stream_by_group_id`、`chat.open_session`、`config.get`、`llm.generate`、`maisaka.proactive.trigger` capability
