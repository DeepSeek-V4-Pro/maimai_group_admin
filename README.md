# maimai_group_admin 本分支差异说明

本分支相对原版2.1版本新增或修正的内容：

## 1. 入站自动审核

- 新增入站文本 LLM 审核，可通过 `audit_model`、`audit_max_tokens` 和置信度门槛控制。
- `audit_model` 在配置页面使用下拉选项，当前支持 `planner` / `utils` / `replyer`。
- 自动审核只自动执行 `warn` / `mute`；是否自动撤回由 `auto_recall` 控制，默认关闭。
- 设置页面将基础与文本审核、图片与表情审核、处置与评论拆成独立分组；旧版 `auto_moderate` 内的同名配置会自动迁移。

## 2. 图片、表情包与合并转发审核

- 新增图片/表情包描述进入审核流程，可分别由 `audit_regular_images`、`audit_emojis` 控制开关。
- 支持对合并转发进行展开审核，并可在刷屏计数中设置为每组合并转发按单条消息计数。
- 支持主程序侧未通过审核的图片/表情包再次读取原图并推送识图复查，由 `retry_violation_media_with_image_audit` 控制。
- 可通过 `violation_media_text_judge_enabled` 控制是否让大模型判断 VLM 返回文本是否表示模型明确拒绝识图。
- 违规图片/表情处理策略由 `violation_media_policy` 控制，支持 `none` / `warn` / `notify`。
-  `violation_media_policy = "notify"` 时，如 VLM 返回文本经大模型判定为“模型明确拒绝识图”，会主动通知人工复核；
- 在 `notify_on_media_description_failure = true` 时，出现识图失败、超时、空返回、无法判断内容等失败类情况都会主动通知人工复核。此时不额外做 VLM + LLM 复核确认。
- `violation_media_notify_target` 支持 `admin`、`owner`、`admin_or_owner` 或指定 QQ 号；指定 QQ 号时优先固定通知该对象。
- 开启媒体复核相关能力大约会多用 1-3 成 token；图片很多或视觉模型单次消耗较高时，极端情况下可能接近 3-4 成。

## 3. 刷屏检测与处罚阶梯

- 沿用原版警告计数机制，新增入站消息触发刷屏判定的路径。

## 4. 人设化管理评论

- 新增 `persona_managed_comments_enabled`，默认关闭。
- 开启后，管理处置评论、警告提醒、图片人工复核通知会尽量读取主程序人设与表达风格后生成。
- `persona_managed_comments_model` 统一控制人设化管理评论使用的模型。

## 5. 管理工具与命令增强

- `group_warn_user` 和 `/warn` 支持 `sexual` / `illegal` 类型。

## 6. 原版问题修复

- 修复原版处罚阶梯只会返回第一个命中档位的问题；多个档位同时满足时，改为选择 `count` 最大的档位。
- 修复 `/admin undo` 不检查解禁 API 结果就提示成功的问题。
- 修复 `/mute`、`/kick`、`/warn` 的昵称解析不兼容 Napcat `{"data": [...]}` 成员列表的问题。
- 修复 `group_recall_msg` / `/recall` 未对消息 ID 做整数转换导致部分平台 API 不兼容的问题。
- 修复 `admin.owner_allowed_commands` 非空时，群主命令因未传入命令文本而被误拒绝的问题。
- 修复群管理 Tool 可在未启用群中被直接调用的问题；所有群级 Tool 现在会先检查目标群是否启用。
- 修复 `/mute`、`/unmute`、`/kick`、`/warn` 在权限检查前先解析目标成员的问题，避免未授权用户触发成员列表查询。
- 修复会话映射缓存混用 `stream_id` / `session_id` / `message_id` 的问题，避免回复消息 ID 被误当作群会话 stream 使用。

## 7. 额外运行能力声明

为支持上述功能，本分支相对原版 manifest 额外声明以下 capability：

- `chat.get_stream_by_group_id`
- `chat.open_session`
- `config.get`
- `llm.generate`
- `maisaka.proactive.trigger`
