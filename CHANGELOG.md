# 更新日志

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
