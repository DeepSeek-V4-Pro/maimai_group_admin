# 更新日志

### v2.5.0 (2026-08-08)

**对话身份识别 + 高频缓存刷新 + 权限决策链可视化 + 提示词优化**

**功能优化（1 项）**
- 对话中主动识别当前发言者身份：不再依赖"调用管理工具时才查询身份"。每条群消息到达时由 EventHandler 提取发言者 QQ 号并缓存，再按节流间隔（默认 120 秒）刷新身份；注入 Replyer/Planner 的提示词携带"当前发言者：群主/管理员/普通成员"，LLM 在回复前就知道对方身份，避免"先质疑群主是冒充的、调用工具后才认出来"的错位。

**缓存刷新（3 项）**
- 群成员身份缓存有效期由固定 1 小时改为可配置 `identity.role_cache_ttl_seconds`（默认 600 秒，10 分钟），目标身份（禁言/踢人对象）权限信息不再长期滞后。
- Bot 自身角色刷新间隔由固定 30 分钟改为可配置 `identity.bot_role_refresh_seconds`（默认 300 秒，5 分钟）；检测失败时 60 秒后自动重试，不再长时间停留在错误的"普通成员"状态。
- 新增 `identity.sender_role_refresh_seconds`（默认 120 秒）控制发言者身份主动刷新频率；`group_get_member` 工具仍强制走 API 获取最新身份。

**权限决策链可视化（2 项）**
- 新增 `/admin perm [@qq|昵称]` 命令：完整展示"身份查询 → 全局管理员名单 → 群主授权/命令白名单 → 保护/豁免名单 → Bot 自身角色"的判断链（`✓/✗` + 原因），方便排查权限问题。
- 命令权限校验（`_check_admin_permission`）与 `/admin perm` 均输出结构化决策链日志；`verbose_logging=true` 时输出每一步详情，普通模式输出摘要。

**提示词优化（1 项）**
- `auto_moderate_system` / `planner_moderate_system` 默认模板新增 `{sender_role}`、`{sender_id}` 变量与"发言者身份规则"：群主/管理员不得质疑，其管理指令视为授权；普通成员无权指挥管理操作；身份以最近一次查询结果为准。同时大幅压缩模板体积（改用紧凑要点式，保留全部行为约束），降低 token 开销。

**Bug 修复与其他优化（9 项）**
- 修复发言者身份提取失败问题：MaiBot 序列化消息中发送者 QQ 位于 `message_info.user_info.user_id`（此前错误使用 `sender_info`，导致提示词一直显示"发言者：未知"）；现兼容 `user_info` / `sender_info` 两种结构。
- 对照 napcat-adapter v1.3.2 全量核对 16 个适配器接口（30 处调用）：API 名称、参数名、direct/action 两种调用方式、失败语义（适配器在 NapCat 返回非 ok 时抛错，工具正确上报失败）全部匹配。
- `group_post_notice` 修复公告 ID 提取：适配器返回的是 OneBot 原始信封（`data` 内嵌），此前未解包导致 `notice_id` 经常取不到；现在先取 `data` 再读 `notice_id`。
- `/shutlist` 剩余时长字段兜底：NapCat 可能返回 `time` 而非 `remaining_time`，现在两者兼容。
- `_check_target_role` 不再缓存空身份结果：API 返回空 role 时下次直接重查，避免权限判断被空缓存卡住。
- 工具层群号兜底新增 message 结构直读：`_resolve_tool_group_id` 在缓存缺失时从当前消息提取群号并回写缓存，群号信息更实时。
- 群号映射缓存不再依赖自动审核开关：`auto_moderate.enabled=false` 时仍缓存 group_id → 会话映射，`/admin` 命令在纯命令模式下也能解析群号。
- 守门 `guard_admin_response` 修正误伤：回复包含"保护名单/豁免名单/冷却中/已达每日上限/处罚阶梯/未找到成员"等正当拒绝原因时，不再强制改写为"我是群主，我来处理"。
- `group_get_member` 返回中文身份（群主/管理员/普通成员）+ 英文 role 值，方便 LLM 理解。

**其他**
- 版本号迭代至 2.5.0（manifest / config_version / README / CHANGELOG 同步更新），README 更新配置说明、命令数量（15 个）、FAQ 与功能总览。

### v2.4.0 (2026-08-06)

**修复 Bot "口头宣称执行但实际未执行" + 插件简介/文档全面优化**

**功能修复（1 项）**
- 修复 LLM 有概率"嘴上说执行、实际未调用工具"的问题：18 个管理 Tool 统一声明 `visibility="visible"`。此前插件工具在 MaiBot 中默认是 `deferred`（延迟工具），LLM 必须先调用 `tool_search` 搜索、等到下一轮才真正可用；模型未搜索时只会用文字宣布"我来禁言/我来处理"，导致禁言/撤回/踢出等操作间歇性不生效。改为直接暴露后，工具始终在 Planner 可用工具列表中，决策即可立即调用。

**提示词与守门（2 项）**
- 强化 Replyer / Planner 注入提示词：所有管理操作必须真实调用对应的 `group_*` 工具完成，禁止只用文字宣称"已禁言/已撤回/已踢出"等结果，禁止只宣布"我要禁言"却不调用工具。
- 守门 `group_admin_reply_guard` 新增"编造已执行"检测：Bot 回复中出现"已将 xxx 禁言 / 已撤回 / 已踢出"等完成式表述，但 30 秒内没有对应的真实工具执行记录时，自动改写为诚实回复并记录日志（被动语态如"该用户已被禁言"不会误伤）。

**简介与文档（3 项）**
- 重写插件简介（manifest 描述）与 README 开头：用大白话说明"这个插件是干什么的"，去掉大量专业术语，降低插件市场用户的阅读门槛。
- README 开头新增"遇到问题 / Bug 反馈"专区，提供 GitHub Issues 入口和反馈模板说明，方便用户直接反馈问题。
- 优化 README 排版：新增目录、统一章节层级、更新技术细节与功能总览。

**其他**
- 版本号迭代至 2.4.0（manifest / config_version / README / CHANGELOG 同步更新）。

### v2.3.0 (2026-08-05)

**群号自动获取稳定性修复 + 潜在问题修复 + 版本迭代**

- 提示词注入现在会携带 `当前群号：{group_id}`（Replyer 与 Planner 两处），LLM 调用管理工具时不再需要猜测群号。
- 18 个 Tool 增加群号兜底：LLM 填 0 或填错群号时，自动改用当前会话群号；目标群不在 `enabled_groups` 白名单时直接拦截。
- 统一群号解析逻辑：`_resolve_group_id` 作为唯一解析入口（缓存 → kwargs → message 结构 → `additional_config.platform_io_target_group_id`），注入、守门、命令三条路径共用；修复 `chat_id` 被当作群号的问题。
- `_stream_to_group` 缓存改为 LRU（最近使用刷新顺序），上限提高至 5000，避免活跃会话映射被批量淘汰导致注入间歇性失效。
- `cache_session_group` / `handle_auto_moderate` 增加 `message_info.group_id` 与 `platform_io_target_group_id` 提取兜底，兼容不同适配器消息结构。
- 修复 `_check_warning_threshold` 阈值 ≤ 0 时误报“提醒已达阈值”的问题（警告功能关闭/阈值禁用时不再输出误导性提示）。
- 快捷命令（`/mute` `/unmute` `/kick` `/warn`）权限校验提前到昵称解析之前，未授权用户不再触发成员列表查询。
- `/admin status` 无法确定群号时提示用法，不再显示“群 0 管理面板”。
- `/admin on` / `/admin off` 的配置持久化加锁，与豁免名单保存保持一致，避免并发修改 `config.toml` 的竞态。
- 版本号迭代至 2.3.0（manifest / config_version / README / CHANGELOG 同步更新）。

### v2.2.0 (2026-07-22)

**全面代码审查与 Bug 修复（共 15 项）**

**移除废弃功能（1 项）**
- 移除 `/admin reload` 命令及 `_clear_runtime_cache()` 方法（MaiBot 自带热重载，此功能多余）。

**配置持久化修复（1 项）**
- `_save_exempt_users()` 和 `_save_enabled_groups()` 改为原地修改 TOML 文档对象，不再创建新 table/array 替换，避免丢失配置文件中的注释和格式。

**Bug 修复（7 项）**
- 修复 `cmd_admin_undo` 未检查解禁 API 返回值、豁免移除提示始终显示的问题。
- 修复 `cmd_admin_ban` / `cmd_admin_unban` / `cmd_admin_undo` 修改 `exempt_users` 时未加锁的竞态条件。
- 修复 `owner_allowed_commands` 白名单因 `command_text` 从未传入而完全失效的问题。
- 修复 `cmd_admin_ban` / `cmd_admin_unban` / `cmd_admin_undo` 回退正则优先匹配群号而非 QQ 号的问题。
- 修复 `tool_mute_user` 超长禁言直接拒绝而非截断（与管理员命令行为不一致）。
- 修复守门 `deny_flags` 包含"不能操作"导致保护名单场景误判的问题。
- 修复 `cmd_admin_shutlist` 直接输出原始 JSON 的问题，改为格式化显示。

**代码优化（4 项）**
- 清除 17 处 API 调用中冗余的 `self._to_int()` 转换。
- `_check_admin_permission` 消除冗余 `is_owner` 变量。
- `cmd_admin_mute` 冷却提示措辞修正（"秒前"→"等待 N 秒"）。
- 所有命令的 `_check_admin_permission` 调用传入 `command_text`，使 `owner_allowed_commands` 白名单生效。

**文档修正与优化（2 项）**
- 修正 README.md 和 plugin.py 中 `/admin reload` 移除后残留的命令数量错误与过时引用。
- 清理 README.md 中过时的版本标记（"v1.1 新增"、"v2.0 新增" 等），补全配置示例缺失节，优化多处文案表述。

### v2.1.0 (2026-07-05)

**命令系统修复与配置持久化 + 安全修复与提示词优化（共 14 项）**

**命令签名修复（2 项）**
- 所有 15 个命令 handler 添加 `user_id` / `matched_groups` 显式参数，匹配 SDK 通过函数签名反射传参的机制，解决命令因提取不到 sender 和参数被静默拒绝的问题。
- `_check_admin_permission` 签名改为直接接收 `user_id`，不再从 `**kwargs` 中猜测，权限校验准确率 100%。

**配置持久化（2 项）**
- `/admin ban` / `/admin unban` / `/admin undo` 修改豁免名单后自动写入 `config.toml`，重启后保留。
- 新增 `_save_exempt_users()` 方法，使用 `tomlkit` 直接读写配置文件。

**Bug 修复（6 项）**
- 修复 `enabled_groups` 为空（全部群启用）时 HookHandler 注入静默跳过的问题：`_prepare_injection` 和 `inject_admin_planner_prompt` 改为使用 `_is_group_enabled` 统一判断。
- 修复 `tool_recall_msg` 使用 `_to_int(message_id)` 导致字符串类型消息ID被转成 0 的撤回失败 bug，改为直接传递原始 message_id。
- 修复 `inject_admin_model_prompt` 无差别写入 `content_text` 字段可能破坏部分模型的消息格式，改为仅在原始消息包含该字段时写入。
- 修复 README 插件 ID 错误（`maimai.group-admin` → `deepseek-v4-pro.maimai-group-admin`）、`config_version` 默认值错误（`"2.0.0"` → `"2.1.0"`）。
- 修复 `_manifest.json` 的 `dependencies` 格式：缺少 discriminator `type` 字段、字段名 `version` 应为 `version_spec`、`reason` 不被 SDK schema 接受。
- 修复权限描述不一致：`_ACTIONS_BY_ROLE` 补全管理员可用的"公告"和"踢人"；`tool_kick_user` 取消对管理员的拦截改为 `bot_role not in ("owner", "admin")`，描述改为"管理员需在严重违规请示群主或群主要求时使用"；`group_post_notice`/`group_delete_notice` 从"仅群主"改为"管理员/群主可用"；其余 8 个 Tool 补全权限标注；README 查询表补全最低权限列。

**配置补充（1 项）**
- `config.toml` 新增 `planner_moderate_system` 字段，与 `config_model.py` 默认值对齐。

**提示词优化（3 项）**
- `auto_moderate_system` 标题精简为"保持人设，自然融入"，删除冗余的"不要切换管理员口吻"（已在正文中体现），合并节奏控制表述。
- `planner_moderate_system` 从工具名导向改为行为导向（`group_recall_msg 撤回` → `撤回`），扁平化结构，尾部强调词更简洁。
- 两个提示词同步更新 `config_model.py` 默认值和 `config.toml` 实际配置。

### v2.0.0 (2026-07-03)

**重大架构重构与提示词体系升级（15 项）**

**多文件模块化（6 项）**
- 将单文件 1736 行 `plugin.py` 拆分为 6 个模块文件：`config_model.py`、`plugin_core.py`、`tools.py`、`commands.py`、`handlers.py`、`plugin.py`
- 采用 Python Mixin 多继承模式，每个模块职责单一、便于维护
- 清理 `plugin_core.py` 中未使用的 import（减少 9 个冗余导入）
- `HandlerMixin` 类注释修正为 5 个 HookHandler

**Planner 阶段注入（3 项）**
- 新增 `maisaka.planner.before_request` HookHandler，向 Planner 的 system messages 注入群管理决策准则
- Planner 提示词独立于 Replyer 提示词，`planner_moderate_system` 使用 `# 群管理准则` 标题风格匹配系统 prompt
- Planner 注入使用独立的 `_build_admin_planner_prompt` 构建方法

**缓存修复（2 项）**
- `cache_session_group` 钩子改为从 `message.session_id` 字段直接提取会话 ID 缓存映射
- 修复 `chat.receive.after_process` 不传 `session_id` 进 kwargs 导致 Planner 注入找不到群号的问题
- Planner hook 找到群号后立即回写 `_stream_to_group[session_id]` 供后续轮次使用

**提示词优化（4 项）**
- 角色名中文化：`{bot_role}` 输出 `群主`/`管理员`/`普通成员` 而非英文 owner/admin/member
- 权限列表统一：`_ACTIONS_BY_ROLE` 共享字典，owner/admin/member 各自对应正确的可用操作（admin 含踢人但需征求群主同意）
- 守门回复动态化：替换文本从硬编码 `"收到，我来处理。"` 改为 `"我是{群主/管理员}，我来处理。"`
- 18 个 Tool 描述规范化：统一 `"做什么（谁可用）"` 格式，移除操作流程混入

### v1.5.0 (2026-06-30)

**全面质量修复**

**缓存生命周期（6 项）**
- `_known_roles` 值改为 `(role, timestamp)` 元组，读写均带 3600s TTL，清理按时间戳排序淘汰
- `_last_mute_time` / `_get_member_called` 在 `_cleanup_memory` 中按时清理过期条目
- `_daily_*_count` 在 `_check_daily_reset` 中清理旧日 key
- 删除死代码 `_msg_counter`
- 新增独立 `_cleanup_task`（每 600s 运行），不再依赖 `auto_approve` 或事件驱动
- `_bot_self_id` 改为全局单值 `Optional[int]`，从任意群首次消息即可赋值

**跨群统计隔离（5 项）**
- `_warnings` 结构改为 `{group_id: {user_id: {vtype: [(ts,c)]}}}`，所有读写按群隔离
- `_check_escalation` / `_count_ops_in_window` 加入 `group_id` 过滤
- `_check_warning_threshold` 新增 `group_id` 参数
- `_check_join_requests` 合并 `auto_moderate.enabled_groups` + `auto_approve.groups[]`
- 修复 `auto_approve.groups` 中单独配置的群被 `_is_group_enabled` 跳过的 bug

**竞态条件（2 项）**
- `_check_join_requests` 中 approve/reject 分支的计数修改加 `async with self._lock`
- `cmd_admin_warn` 写入 `_warnings` 加 `async with self._lock`

**管理员体验（4 项）**
- `/admin reload` 新增 `_clear_runtime_cache()` 清空角色/群组/流映射等缓存
- `on_config_update` 自动重启 `_auto_check_task`
- 自动审批前加入 `_is_protected` 检查
- `tool_warn_user` 优先使用 `stream_id` 发送消息

**异常处理统一（27 处）**
- 全 17 个 Tool + 2 个后台循环 + 1 个 Command：`logger.error("...", exc_info=True)`（含完整 traceback）
- 5 个 API 层 helper：`logger.warning(f"...: {e}")`（简洁消息）
- 2 个数据质量兜底：静默
- `_call_api` / `_call_action_api` 新增日志
- `_resolve_target` 裸 `except: pass` → 加日志
- `_ensure_bot_role` 异常→加日志
- 所有 `[群管理]` 前缀 100% 覆盖
- 6 个 Command 中未使用变量 `data` → `_`

### v1.4.0 (2026-06-28)

**重大安全修复**

- 新增 `chat.receive.after_process` HookHandler 缓存 `msg_id → group_id` 映射，解决 `before_request` / `before_model_request` 双路注入无法获取群号的根本问题。
- 按群精确注入：每个启用群获取真实 bot 角色（owner/admin/member），未启用群和私聊自动跳过。
- 修复 `_ensure_bot_role` 跨群 self_id fallback（`next(iter(...))`）导致权限污染。
- 修复 `_check_admin_permission` group_id=0 时误判 sender 为 owner。
- 修复 `_resolve_group_id_from_hook` 正则猜测和 stream 缓存反向污染。
- 修复 `_get_member_called` 无 TTL，改为时间戳存储（300s 过期）。
- 修复 `_check_join_requests` known_groups 跨群污染和 data 标准化紊乱。
- 所有 18 个 Tool 添加 `group_id <= 0` 前置校验。
- 精简 `_prepare_injection` 从 7 级检测简化为缓存查找，移除 ~110 行死代码。
- 移除未使用的 `_last_inject_time` 字段。

### v1.3.0 (2026-06-26)

**重大重构**

- 双路注入架构：`before_request → extra_prompt` + `before_model_request → messages` 同时注入，彻底解决 Planner/Timing Gate/Replyer 管理上下文缺失导致自动审核形同虚设的问题。
- 精简默认 prompt 约 40%（380→220 中文字符），去除冗余修辞，信息密度更高。
- 移除废弃字段 `re_inject_interval_messages` / `re_inject_interval_seconds`。
- 提取 `_prepare_injection()` 消除重复代码。
- 修复 EventHandler 重复代码块。
- 版本号迭代至 1.3.0，config_version 同步更新。

### v1.2.0 (2026-06-26)

若干小 bug 修复（未逐条记录，仅更新版本号提醒有更新）。

### v1.1.0 (2026-06-24)

**优化部分**

- 全面优化了插件提示词和提示词注入方式

**Bug 修复**

- 修复 `_check_daily_reset` 在跨日时将整个日计数字典覆写为单日条目，导致历史计数丢失的问题

**清理**

- 移除 `_manifest.json` 中已废弃的 `maisaka.context.append` capability（v1.1 已迁移到 HookHandler + extra_prompt）

**文案优化**

- `/admin status` 输出改为面板卡片风格，禁言/踢人计数不再显示为 `0/10` 进度条格式
- `/admin log` 输出从管道分隔格式改为更紧凑的 `[时间] 状态 动作 @用户 -- 原因` 格式
