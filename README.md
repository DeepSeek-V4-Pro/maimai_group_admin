# 群管理助手 v2.5 — 给 QQ 群装一个“自动小管理员”

**这个插件是干什么的？**

一句话：让你的 QQ 群机器人（Bot）当群里的“小管理员”，有人违规时它能自己处理。

装好并启用后，Bot 可以帮你：

- **自动管违规**：广告、刷屏、骂人 → 自动警告、禁言，严重的直接踢出
- **替你干活**：发群公告、撤回消息、设精华、通过/拒绝入群申请
- **听你指挥**：群主/管理员发 `/mute 某人`、`/kick 某人`、`/warn 某人` 等命令即可手动操作

**上手简单**，装进 MaiBot、填好群号就能用，下面有保姆级教程。

> ⚠️ 这是自动管理插件，Bot 会真实执行禁言/踢人操作，请先看完【免责声明】和【安全护栏】再启用。

---

## 🐛 遇到问题 / Bug 反馈

用着出问题（Bot 不执行、报错、行为异常、操作没生效等），**请直接到 GitHub 提 Issue**：

👉 [点这里去反馈](https://github.com/DeepSeek-V4-Pro/maimai_group_admin/issues/new/choose)

反馈时请尽量带上：

1. MaiBot 版本 + 插件版本（WebUI 插件管理页可查看）
2. 发生了什么、你期望什么（复现步骤）
3. 相关日志或截图（日志见 `MaiBot/logs/`）

你的反馈很重要，很多问题就是这样被发现的，先谢过 🙏

---

## 📖 目录

- [急速上手指南](#急速上手指南猫娘都能看懂)
- [免责声明](#免责声明)
- [版本兼容性](#版本兼容性)
- [定位说明](#定位说明)
- [快速开始](#快速开始)
- [配置文件详解](#配置文件详解)
- [功能详解](#功能详解)
- [推荐配置](#推荐配置)
- [常见问题](#常见问题)
- [日志参考](#日志参考)
- [技术细节](#技术细节)
- [功能总览](#功能总览)
- [更新日志](#更新日志)

---

## 🚀 急速上手指南（猫娘都能看懂）

```
1. 把整个 maimai_group_admin 文件夹丢进 MaiBot 的 plugins/ 目录（或者插件市场点击安装）
2. WebUI → 插件管理 → 找到 deepseek-v4-pro.maimai-group-admin → 点启用
3. 配置文件，改两个地方：
   [admin] admins = ["你的QQ号"]
   [auto_moderate] enabled_groups = ["要管的群号"]
4. 在群里发 /admin status 看是否生效
```

> ⚠️ **强烈建议：看完下方完整的说明文档再使用，否则后果自负（比如群友被bot制裁）。**  
> 默认配置是娱乐向，直接用于大群管理可能出问题。请务必阅读"安全护栏""推荐配置""免责声明"等章节。

---

## ⚠️ 免责声明

1. **本插件为娱乐性质的自动化工具**，不保证管理决策的准确性和适当性。LLM 的判断可能存在误判（将正常对话误认为违规）或漏判（未识别真正的违规内容）。
2. **使用者需自行承担风险**。因本插件自动执行的管理操作（禁言、踢人等）引发的任何纠纷、损失或账号风险，插件开发者不承担任何责任。
3. **不建议在严肃的管理场景中完全依赖本插件**。建议保持人类管理员对关键决策的监督和干预能力。
4. **请遵守 QQ 平台的使用规范**，合理设置禁言时长和操作频率，避免因频繁操作导致 Bot 账号被限制。
5. **Bot 必须是群管理员或群主**才能执行管理操作。如果 Bot 是普通成员，所有管理 Tool 将无法使用。
6. 本插件基于 MaiBot Plugin SDK v2 和 NapCat 适配器开发，不保证与其他适配器或 SDK 版本的兼容性。

---

## 📌 版本兼容性

- **兼容版本**：MaiBot **1.0.0 ~ 1.99.99**（MaiBot Plugin SDK v2）
- **已知问题**：MaiBot 核心 `hook_dispatcher` 的 `kwargs` 替换逻辑（`= dict(...)` 完全替换而非合并 `update`）可能导致多插件共用同一 Hook 点时后注册的插件拿不到 `session_id` 等关键参数。本插件已通过 `cache_session_group` 从 `message.session_id` 直接提取会话 ID 绕过此限制。

---

## 定位说明

本插件设计为**轻量娱乐向**的群管理辅助工具，核心理念是：

- **LLM 自主判断**：Bot 根据上下文自行决定何时操作，无需人工逐一指令
- **人类兜底**：通过 `/admin` 命令和 `exempt_users` 等机制，管理员可随时纠正或阻止 Bot 的操作
- **安全优先**：默认配置保守（`daily_mute_limit=10`、`max_mute_duration=3600s`、`auto_exempt_admins=true`），建议先在测试群试用

**如需用于正式群管理**，建议：

1. 将 `auto_moderate.enabled` 设为 `false`，仅通过管理员命令手动操作
2. 关闭自动审批（`auto_approve.enabled = false`）
3. 将 `protected_users` 配置所有不应被操作的用户
4. 定期通过 `/admin log` 审查操作记录
5. 保持至少一名人类管理员在线监督

---

## 快速开始

### 安装

将 `plugins/maimai_group_admin/` 目录放入 MaiBot 的 `plugins/` 下，确保包含以下文件：

```
plugins/maimai_group_admin/
  _manifest.json    # 插件声明
  plugin.py         # 插件入口，组合所有模块
  plugin_core.py    # 核心生命周期、后台任务、辅助方法
  config_model.py   # 配置模型（10 个配置分区 + 2 个默认提示词）
  tools.py          # 18 个管理 Tool
  commands.py       # 15 个管理员命令
  handlers.py       # 1 个 EventHandler + 5 个 HookHandler
  config.toml       # 配置文件
  __init__.py       # 包初始化
  README.md         # 本说明
```

### 最小配置

编辑 `config.toml`：

```toml
[plugin]
enabled = true

[identity]
bot_qq = "你的Bot的QQ号"    # 推荐填写，留空则自动从消息中获取

[auto_moderate]
enabled_groups = ["123456789"]  # 需要管理的群号，留空=全部群生效

[admin]
admins = ["你的QQ号"]           # 能使用/admin命令的管理员

[auto_approve]
enabled = false                 # 建议初次使用关闭自动审批
default_action = "ignore"
```

### 启用

WebUI → 插件管理 → 找到 `deepseek-v4-pro.maimai-group-admin` → 点击启用

### 验证

在管理的群内发送 `/admin status`，应看到：

```
群 123456789 管理面板
身份：owner
状态：运行中
今日已禁言 0 人（上限 10），已踢出 0 人（上限 3）
```

---

## 配置文件详解

以下是 `config.toml` 每个字段的完整说明，按配置分组列出。

---

### [plugin] — 插件开关

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enabled` | bool | `false` | 插件总开关，设为 `true` 后插件才开始工作 |
| `config_version` | string | `"2.5.0"` | 配置版本号，升级插件时用于迁移判断，**请勿手动修改** |

---

### [admin] — 管理员权限

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `admins` | list[string] | `[]` | 人类管理员 QQ 号列表，**必须填写你的 QQ 号**才能使用 `/admin` 等命令。跨群有效 |
| `allow_group_owner` | bool | `true` | 是否允许目标群的群主执行管理员命令（即使不在 admins 列表中） |
| `owner_allowed_commands` | list[string] | `[]` | 群主可用的命令白名单（如 `["status","log","mute","kick"]`），留空 = 全部可用。已在权限校验中实际执行 |
| `deny_response` | string | `"silent"` | 无权限用户的处理方式：`"silent"`=静默忽略，`"reply"`=回复"你没有权限执行此操作" |

> **重要**：`admins` 必须至少填一个 QQ 号，否则仅群主能用管理命令。

---

### [identity] — 身份标识

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `bot_nickname` | string | `"麦麦"` | Bot 昵称，会出现在管理 prompt 和通知中。建议与 Bot 的人设名称一致 |
| `auto_detect` | bool | `true` | 是否自动检测 Bot 在各群的权限角色（群主/管理员/普通成员） |
| `bot_qq` | string | `""` | Bot 的 QQ 号。**强烈推荐填写**，留空则从首次群消息事件中自动获取 |
| `override_roles` | dict[str,str] | `{}` | 手动覆盖指定群的 Bot 角色。格式：`"群号" = "owner"`（可选值：`owner`/`admin`/`member`）。优先级高于自动检测 |
| `role_cache_ttl_seconds` | int | `600` | 群成员身份缓存有效期（秒）。目标身份（如禁言/踢人对象）在此时间内复用缓存，到期后重新查询 |
| `bot_role_refresh_seconds` | int | `300` | Bot 自身在各群的角色刷新间隔（秒）。权限变化后最多延迟该时长生效 |
| `sender_role_refresh_seconds` | int | `120` | 当前发言者身份的主动刷新间隔（秒）。对话中自动识别群主/管理员/普通成员，并按此频率刷新 |

> `override_roles` 示例：
> ```toml
> [identity.override_roles]
> "123456789" = "owner"
> "987654321" = "admin"
> ```

---

### [auto_moderate] — 自动审核

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enabled` | bool | `true` | 是否启用 LLM 自动审核（双路注入 + 按群精确注入 + Planner 决策注入） |
| `enabled_groups` | list[string] | `[]` | 需要管理的群号白名单，如 `["123456789"]`。留空 = 全部群生效 |

> ⚠️ **注意**：`enabled_groups` 留空时插件会在**所有群**启用自动审核。如不确定，请先填写具体群号限制范围。

---

### [safeguard] — 安全管理

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `max_mute_duration` | int | `3600` | 单次禁言最大秒数（1 小时）。LLM 请求的超长禁言会被截断到该值 |
| `kick_require_confirm` | bool | `true` | 踢人前是否要求 LLM 先调用 `group_get_member` 确认目标身份 |
| `mute_cooldown` | int | `300` | 同一用户两次禁言的最小间隔（秒）。已实际执行，tool_mute_user 和 /mute 命令均会检查 |
| `daily_mute_limit` | int | `10` | 每个群每天最大禁言次数（防止误操作风暴） |
| `daily_kick_limit` | int | `3` | 每个群每天最大踢人次数 |
| `protected_users` | list[string] | `[]` | **全局保护名单**，这些 QQ 号在任何群里都不会被操作。建议填群主和重要成员 |
| `exempt_users` | dict[str,list] | `{}` | **按群豁免名单**，格式见下方示例。通过 `/admin ban`/`unban` 命令也可添加 |
| `auto_exempt_admins` | bool | `true` | 是否自动豁免群主和管理员（系统硬拦截，LLM 无法操作他们） |

> `exempt_users` 示例：
> ```toml
> [safeguard.exempt_users]
> "123456789" = ["111222333", "444555666"]
> ```

---

### [warning] — 警告系统

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enabled` | bool | `true` | 是否启用警告计数器 |
| `spam_warn_threshold` | int | `3` | 刷屏类警告次数达到该值后系统提示升级处罚 |
| `spam_warn_window` | int | `600` | 刷屏警告计数窗口（秒），超出窗口的旧警告自动过期 |
| `abuse_warn_threshold` | int | `1` | 辱骂类警告阈值（建议设低，辱骂零容忍） |
| `abuse_warn_window` | int | `3600` | 辱骂警告计数窗口（秒） |
| `ad_warn_threshold` | int | `1` | 广告类警告阈值 |
| `ad_warn_window` | int | `1800` | 广告警告计数窗口（秒） |

> 当某类警告达到阈值时，Tool 返回值会附带 `"该用户 xxx 类警告已达 n/m，建议升级处罚"` 提示。

---

### [escalation] — 处罚阶梯

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enabled` | bool | `true` | 是否启用处罚阶梯 |
| `escalation_steps` | list[table] | `[]` | 阶梯规则列表，**默认空=不生效**，需自行配置 TOML 数组 |

每条阶梯规则的字段：

| 子字段 | 类型 | 说明 |
|--------|------|------|
| `within_hours` | int | 回溯多少小时内 |
| `count` | int | 操作次数达到该值后触发 |
| `action` | string | 触发动作：`"mute"` 或 `"kick"` |
| `max_duration` | int | 若 action=mute，禁言最大秒数（覆盖 LLM 请求的时长） |

> 配置示例（TOML 数组格式，每项用 `[[escalation.escalation_steps]]` 开头）：
> ```toml
> [[escalation.escalation_steps]]
> within_hours = 24
> count = 1
> action = "mute"
> max_duration = 600
> 
> [[escalation.escalation_steps]]
> within_hours = 24
> count = 2
> action = "mute"
> max_duration = 1800
> 
> [[escalation.escalation_steps]]
> within_hours = 72
> count = 3
> action = "kick"
> ```

---

### [auto_approve] — 自动审批入群

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enabled` | bool | `false` | 是否启用自动审批入群。**建议初次使用保持关闭** |
| `default_action` | string | `"ignore"` | 默认动作：`"ignore"`=不处理，`"approve"`=自动通过，`"reject"`=自动拒绝 |
| `require_message_keywords` | list[string] | `[]` | 入群申请必须包含的关键词（全部满足才按 default_action 处理） |
| `reject_keywords` | list[string] | `[]` | 拒绝关键词，申请中包含任一即自动拒绝 |
| `max_pending_seconds` | int | `300` | 超过此秒数的申请自动跳过（避免处理积压旧申请） |
| `daily_approve_limit` | int | `5` | 每日自动通过上限 |
| `daily_reject_limit` | int | `10` | 每日自动拒绝上限 |
| `check_interval_seconds` | int | `120` | 后台扫描间隔（秒），设为 `0` 禁用后台任务 |
| `groups` | table[] | `[]` | 按群覆盖设置，TOML 数组表格式。每项字段见下方 |

**groups 子字段：**

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `group_id` | string | `""` | 群号 |
| `default_action` | string | `"ignore"` | 默认动作: ignore/approve/reject |
| `require_keywords` | string | `""` | 必须包含的关键词，逗号分隔 |
| `reject_keywords` | string | `""` | 拒绝关键词，逗号分隔 |
| `daily_approve_limit` | int | `0` | 每日通过上限（0=使用全局） |
| `daily_reject_limit` | int | `0` | 每日拒绝上限（0=使用全局） |

> 配置示例：
> ```toml
> [[auto_approve.groups]]
> group_id = "123456789"
> default_action = "approve"
> reject_keywords = "广告, 推广"
> daily_approve_limit = 5
> daily_reject_limit = 10
> 
> [[auto_approve.groups]]
> group_id = "987654321"
> default_action = "ignore"
> ```

---

### [logging] — 日志与记录

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `max_log_entries` | int | `2000` | 内存中保留的操作日志最大条数（超过后自动丢弃旧记录） |
| `default_log_lines` | int | `10` | `/admin log` 不加行数参数时的默认显示行数 |
| `verbose_logging` | bool | `false` | 开启后输出完整注入 prompt 和守门详情到 INFO 日志，用于排查提示词效果 |

---

### [prompts] — 提示词

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `auto_moderate_system` | string | (长文本) | 自动审核系统提示词（Replyer 用），支持 `{bot_role}`/`{available_actions}`/`{sender_role}`/`{sender_id}` 模板变量。可自定义 |
| `planner_moderate_system` | string | (长文本) | 规划器系统提示词（Planner 决策用），支持 `{bot_role}`/`{available_actions}`/`{sender_role}`/`{sender_id}` 模板变量 |
| `command_denied_message` | string | `"你没有权限执行此操作。"` | 非授权用户尝试使用管理命令时的回复内容（仅 deny_response="reply" 时生效） |

> `auto_moderate_system` 和 `planner_moderate_system` 均支持模板变量：`{bot_role}`（群主/管理员/普通成员）、`{available_actions}`（动态可用工具列表）、`{sender_role}`（当前发言者身份）、`{sender_id}`（当前发言者 QQ 号）

---

## 功能详解

### 一、LLM 自动管理层（18 个 Tool + 5 个 HookHandler）

Bot 通过 chat.receive.after_process HookHandler 缓存 msg_id → group_id 和当前发言者，为双路注入（`before_request → extra_prompt` + `before_model_request → messages`）提供精确的群号映射。每次 LLM 思考时按群注入管理上下文，并携带**当前发言者的身份**（群主/管理员/普通成员），Planner/Timing Gate/Replyer 全部具备管理意识。回复后 `after_response` HookHandler 守门检查不当行为。

> `chat.receive.after_process` 缓存钩子实现按群精确注入（每个群获取真实 bot 角色与发言者身份），未启用群和私聊自动跳过。发言者身份按 `sender_role_refresh_seconds`（默认 120 秒）主动刷新，Bot 角色按 `bot_role_refresh_seconds`（默认 300 秒）刷新。

#### 写操作（14 个）

| Tool | 参数 | 最低权限 | 说明 |
|------|------|----------|------|
| `group_warn_user` | group_id, user_id, violation_type(spam/abuse/ad), reason | 管理员 | 发送警告消息 + 写入警告计数器，阈值达标后提示升级 |
| `group_mute_user` | group_id, user_id, duration(秒), reason | 管理员 | 禁言指定用户，受 max_mute_duration 限制 |
| `group_unmute_user` | group_id, user_id | 管理员 | 解除禁言（duration=0） |
| `group_kick_user` | group_id, user_id, reason | 管理员/群主 | 踢出用户。管理员需在严重违规请示群主或群主要求时使用 |
| `group_recall_msg` | group_id, message_id, reason | 管理员 | 撤回消息（群主/管理员无2分钟限制，需先回复目标消息获取 message_id） |
| `group_set_essence` | group_id, message_id | 管理员 | 设为精华消息（需先让用户回复目标消息获取 message_id） |
| `group_unset_essence` | group_id, message_id | 管理员 | 取消精华 |
| `group_set_user_card` | group_id, user_id, card | 管理员 | 修改群名片（只能改普通成员） |
| `group_approve_join` | group_id, request_id, reason(可选) | 管理员 | 通过入群申请 |
| `group_reject_join` | group_id, request_id, reason | 管理员 | 拒绝入群申请 |
| `group_set_name` | group_id, name | **仅群主** | 修改群名称 |
| `group_set_title` | group_id, user_id, title | **仅群主** | 设置专属头衔（最长6字符） |
| `group_post_notice` | group_id, content | 管理员/群主 | 发布群公告，返回 notice_id 供后续删除 |
| `group_delete_notice` | group_id, notice_id | 管理员/群主 | 删除群公告（先用 group_get_notice 获取 notice_id） |

#### 查询（4 个）

| Tool | 参数 | 最低权限 | 说明 |
|------|------|----------|------|
| `group_get_member` | group_id, user_id | 无 | 查询群成员身份（owner/admin/member）、昵称和群名片。踢人/禁言前必须先调用 |
| `group_get_shut_list` | group_id | 管理员 | 查看当前群的禁言列表 |
| `group_get_system_msg` | group_id | 管理员/群主 | 获取群系统消息（入群申请、邀请入群） |
| `group_get_notice` | group_id | 无 | 获取群公告列表（含 notice_id），删除公告前调用 |

#### 动态注册

Tool 全部 18 个静态注册，始终可用。Bot 角色的影响在 prompt 注入环节体现：

- **群主**：注入完整管理权限描述（"全部管理: 禁言/解禁/警告/设精华/撤回/改名片/公告/改名/审批入群/踢人"）
- **管理员**：注入受限描述（"禁言/解禁/警告/设精华/撤回/改名片/公告/审批入群/踢人"）
- **普通成员**：注入提示"你在此群无管理操作权限，可协助管理员做决策建议。"

> 注意：Tool 本身不按角色禁用。若 Bot 为普通成员调用禁言等操作，QQ API 会在执行时返回权限不足的错误。

---

### 二、人类管理员命令（15 个）

所有命令需满足权限校验（`config.admin.admins` 或群主身份）。

#### /admin 控制台（8 个）

| 命令 | 用法 | 说明 |
|------|------|------|
| `/admin status [群号]` | 查看运行状态 | 显示 bot 角色、日计数、启用状态 |
| `/admin off [群号]` | 关闭自动管理 | 从 `enabled_groups` 移除并持久化到 `config.toml`，重启后保留 |
| `/admin on [群号]` | 开启自动管理 | 自动加入 `enabled_groups` 并持久化到 `config.toml`，重启后保留 |
| `/admin undo [群号] @qq` | 强制解禁 | 同时从 exempt_users 移除 |
| `/admin log [群号] [n]` | 操作记录 | 查看最近 n 条操作（默认 10 条） |
| `/admin perm [@qq|昵称]` | 权限决策链 | 可视化展示被查用户从身份查询 → 管理员/群主授权 → 保护名单 → Bot 角色 的完整判断链，用于排查权限问题 |
| `/admin ban [群号] @qq` | 添加豁免 | 写入 `exempt_users[群号]` |
| `/admin unban [群号] @qq` | 移除豁免 | 从 `exempt_users` 删除 |
#### 快捷操作（7 个）

| 命令 | 用法 | 权限 | 安全护栏 |
|------|------|------|----------|
| `/mute @qq 5分钟 刷屏` | 禁言，支持 QQ 号或昵称 | admins/群主 | 受保护用户/豁免名单检查 |
| `/unmute @qq` | 解禁 | admins/群主 | — |
| `/kick @qq 广告` | 踢出 | admins/群主 | 受保护用户/豁免名单检查 |
| `/warn @qq spam 原因` | 正式警告 | admins/群主 | — |
| `/essence` | 设精华（需先回复目标消息） | admins/群主 | — |
| `/recall` | 撤回（需先回复目标消息） | admins/群主 | — |
| `/shutlist` | 查看禁言列表 | admins/群主 | — |

> **注意**：`/essence` 和 `/recall` 需要先在 QQ 中**回复（引用）目标消息**，然后再发送命令。命令会自动从回复中提取目标消息的 ID。

---

### 三、安全护栏（8 步校验链）

所有 LLM Tool 和 `/mute` `/kick` 快捷命令在执行前均按以下顺序校验：

```
① protected_users（全局保护名单）
    ↓ 命中 → 拒绝
② exempt_users[群号]（按群豁免）
    ↓ 命中 → 拒绝
③ admins（bot管理员，与群主同级保护）
    ↓ 命中 → 拒绝
④ auto_exempt_admins（自动查身份）
    ↓ 目标为群主/管理员 → 拒绝
⑤ mute_cooldown（同用户禁言最小间隔）
    ↓ 未达标 → 拒绝
⑥ 每日限额（每群独立计数）
    ↓ 超额 → 拒绝
⑦ kick_require_confirm（踢人确认）
    ↓ 未调用 group_get_member → 拒绝
⑧ 处罚阶梯（warn/mute/kick 联合计数）
    ↓ 命中 → 自动覆盖 LLM 请求参数
    ↓ 通过 → 执行操作
```

阶梯匹配后系统**自动覆盖** LLM 请求的禁言时长，Tool 返回值中附带提示。

---

### 四、自动审批入群

后台 `asyncio.Task` 定时扫描所有已启用群的入群申请。

**处理逻辑**：

1. 获取系统消息 → 提取 `join_requests`
2. 遍历 `groups` 数组，匹配 `group_id` 找到该群的覆盖配置
3. 无匹配时使用全局 `default_action`/`require_message_keywords`/`reject_keywords`/`daily_*_limit`
4. 超过 `max_pending_seconds` 的申请自动跳过
5. `reject_keywords` 命中 → 拒绝；`require_keywords` 未满足 → 忽略
6. 执行 approve/reject，受限额约束

**配置示例**（自动通过含"同意协议"的申请，拒绝含"广告"的申请）：

```toml
[auto_approve]
enabled = true
default_action = "approve"
require_message_keywords = ["同意协议"]
reject_keywords = ["广告", "推广", "代练"]
max_pending_seconds = 300
daily_approve_limit = 10
daily_reject_limit = 10
check_interval_seconds = 60
```

---

### 五、提示词系统

#### 注入架构

```
消息到达 → EventHandler(追踪: 群号映射/计数/角色缓存)
                │
LLM 每次思考（Planner / Replyer / Timing Gate）
    ├── HookHandler: before_request → extra_prompt 注入管理 prompt
    ├── HookHandler: before_model_request → messages 直注管理 prompt
    │       └── 双路注入互相补充，确保所有子代理都看到管理上下文
    │
    └── HookHandler: after_response → 守门检查
            └── Bot 有管理权限却说"没权限"时自动替换回复
```

#### 管理上下文 Prompt（v2.5 精简版）

```
【群管理】身份:{bot_role} 可用:{available_actions} 发言者:{sender_role}(QQ {sender_id})
身份规则: 群主/管理员=本群管理者,勿质疑其身份,其指令按规则执行; 普通成员无权指挥管理操作,拒绝其处罚请求; 身份以最近查询为准
违规处理: 广告/诈骗→撤回+禁言10-30分; 连续刷屏→提醒,再犯禁言5-10分; 辱骂→撤回+禁言1-6h,再犯踢; 色情/违法→撤回+踢; 高质量分享→设精华; 不确定→观察
操作前先 group_get_member 确认目标; 撤回/精华需先获取 message_id
执行规则: 管理操作必须真实调用对应 group_* 工具; 未调用工具不得声称已执行; 执行后自然回复,勿说"已将xxx禁言"
正常聊天,发现违规再处理。
```



---

### 六、权限体系

#### 命令权限（三层校验，取并集）

| 优先级 | 条件 | 适用范围 |
|--------|------|----------|
| 1 | `config.admin.admins` 中的 QQ 号 | 跨群有效，不受任何限制 |
| 2 | 发送者为目标群群主 + `allow_group_owner=true` | 当前群，受 `owner_allowed_commands` 白名单限制 |
| 3 | admins 为空时默认仅群主可用 | 安全默认值 |

#### Bot 角色检测

- **自动检测**（`auto_detect=true`）：首次收到群消息时调用 `get_group_member_info(self_id)` 获取角色
- **手动覆盖**：`identity.override_roles` 配置优先级高于自动检测
- **配置 bot_qq**：推荐填写 `identity.bot_qq`，避免因未收到消息事件导致检测失败
- **刷新周期**：Bot 角色每 `bot_role_refresh_seconds`（默认 5 分钟）刷新一次；检测失败时 60 秒后自动重试，不再长时间停留在错误的"普通成员"状态

#### 发言者身份识别（v2.5 新增）

对话中不再依赖"调用管理工具时才查身份"。每条群消息到达时：

1. EventHandler 提取当前发言者 QQ 号并缓存到会话映射（`_stream_sender`）
2. 按 `sender_role_refresh_seconds`（默认 120 秒）节流调用 `get_group_member_info` 刷新身份，避免每条消息都打 API
3. 提示词注入时携带"当前发言者：群主/管理员/普通成员"，LLM 在回复前就知道对方身份，不会再出现"先质疑群主是冒充的、调用工具后才认出来"的错位
4. `/admin perm @qq` 可强制实时查询并展示完整权限决策链

目标成员（如禁言/踢人对象）的身份缓存有效期由 `role_cache_ttl_seconds`（默认 10 分钟）控制；`group_get_member` 工具始终强制走 API 拉取最新身份。

---

## 推荐配置

### 娱乐向（默认适合）

```toml
[plugin]
enabled = true

[auto_moderate]
enabled_groups = ["你的群号"]

[safeguard]
max_mute_duration = 3600
daily_mute_limit = 10
daily_kick_limit = 3
auto_exempt_admins = true

[auto_approve]
enabled = false
```

### 正式管理向（保守）

```toml
[auto_moderate]
enabled = false    # 关闭自动审核，仅用管理员命令

[safeguard]
max_mute_duration = 600     # 最大10分钟
daily_mute_limit = 5        # 保守上限
daily_kick_limit = 1
protected_users = ["群主QQ", "其他管理QQ"]

[admin]
admins = ["你的QQ"]
deny_response = "reply"     # 无权限时回复提示
```

### 严格过滤向

```toml
[plugin]
enabled = true

[auto_moderate]
enabled_groups = ["你的群号"]

[warning]
spam_warn_threshold = 1     # 首次刷屏就警告
abuse_warn_threshold = 0    # 辱骂直接处罚不警告

[[escalation.escalation_steps]]
within_hours = 24
count = 1
action = "mute"
max_duration = 1800          # 首次就禁言30分钟
```

---

## 常见问题

### Q: `/admin status` 显示 bot 角色为"未知"

**原因**：Bot 未收到过群消息事件，或 `bot_qq` 未配置。

**解决**：
1. 在 `config.toml` 中设置 `[identity] bot_qq = "你的Bot的QQ号"`
2. 或在群内发送一条消息触发角色检测
3. 或手动设置 `[identity.override_roles] "群号" = "owner"`

### Q: LLM 不响应管理请求（只会说"我不会"）

**原因**：Bot 的人设优先级高于管理 prompt，v1.0 的规章制度式 prompt 尤其容易被忽略。

**解决**：
1. 确保 Bot 在群内是管理员/群主
2. 检查 `auto_moderate.enabled = true`
3. **v2.5 已优化**：管理上下文改为紧凑参考块注入，明确要求"融入决策、不要复述"，不替换人设，与人设冲突大幅降低
4. 开启 `logging.verbose_logging = true` 可在日志中看到每次注入的完整 prompt，确认是否到位
5. 如仍不行，在 `auto_moderate_system` 中进一步定制与人设协调的措辞

### Q: Bot 分不清谁是群主/管理员（先质疑后认错）

**原因**：v2.4 及更早版本只在调用管理工具时才查询目标身份，对话中 LLM 不知道当前说话人是谁，可能说出"群主是冒充的"之类的话，调用工具后才反应过来。

**解决**：升级到 **v2.5**。v2.5 在每条群消息到达时主动识别发言者身份并注入提示词，LLM 回复前就知道对方是群主/管理员/普通成员；提示词明确要求"不得质疑群主/管理员身份"。身份默认每 2 分钟刷新一次，可在 `[identity] sender_role_refresh_seconds` 调整。

### Q: 权限判断异常，如何排查

**解决**：在群内发送 `/admin perm @qq` 查看该用户的完整权限决策链（身份 → 管理员名单 → 群主授权 → 保护/豁免 → Bot 角色）。如需更详细的过程，开启 `logging.verbose_logging = true` 后重载插件，日志会输出每一步的 `✓/✗` 和原因。

### Q: Bot 嘴上说要禁言/撤回，但实际没执行

**原因**：旧版本中管理工具默认对 LLM 隐藏，模型必须先"搜索工具"、下一轮才能调用；漏搜时就只会口头宣布，导致操作没生效。

**解决**：升级到 **v2.4**。v2.4 已把 18 个管理工具直接暴露给 LLM，提示词强制"必须真实调用工具、禁止口头宣称"，守门还会拦截"编造已执行"的回复。升级后请重载插件。

### Q: `/mute @昵称` 提示"未找到成员"

**原因**：昵称匹配需要先调用 `get_group_member_list` 获取成员列表。

**解决**：使用 QQ 号代替昵称：`/mute @123456789 5分钟`

### Q: 快捷命令（`/mute` `/kick` 等）无法识别

**原因**：新增的 Command 需要 WebUI 完整重载才能注册。

**解决**：WebUI → 插件管理 → 禁用 → 启用

### Q: `send.hybrid` 权限被拒绝

**原因**：manifest 中的 `capabilities` 未包含 `send.hybrid`。

**解决**：确认 `_manifest.json` 中 `capabilities` 包含 `"send.hybrid"`，然后 WebUI 完整重载

### Q: 自动审批不工作

**原因**：`default_action = "ignore"` 或全局 `enabled = false` 且无 per-group 覆盖。

**解决**：设置全局 `enabled = true` 并 `default_action = "approve"/"reject"`，或在 `groups` 中为指定群添加覆盖配置

### Q: 自动审批处理了其他群的申请

**原因**：`get_group_system_msg` 可能返回全部群的系统消息。

**解决**：插件已内置 `req.group_id` 过滤，会跳过不匹配的群

### Q: 处罚阶梯不生效

**原因**：`escalation_steps` 配置为空列表。

**解决**：在 `config.toml` 中配置 `[[escalation.escalation_steps]]` 条目（使用 TOML 数组格式，不是内联表）

### Q: 提示词注入没生效

**原因**：新增的 HookHandler 需要 WebUI 完整重载才能注册。

**解决**：WebUI → 插件管理 → 禁用 → 启用。

### Q: 排查提示词是否注入到位

**解决**：设置 `logging.verbose_logging = true` 并重载插件，日志中将输出每次注入的完整 prompt 和守门动作。

### Q: 操作日志/计数器重启后丢失

**原因**：所有运行时状态（日志、计数器、豁免名单）存储在内存中。

**解决**：这是设计决定，`/admin ban/unban` 的修改如需持久化请直接编辑 `config.toml`

---

## 日志参考

所有功能输出 `[群管理]` 前缀日志，方便排查问题：

| 日志前缀 | 含义 |
|----------|------|
| `Tool-mute / Tool-kick / Tool-warn / ...` | LLM 调用管理 Tool |
| `Cmd-status / Cmd-mute / Cmd-off / ...` | 管理员命令执行 |
| `角色检测结果: group=... role=...` | Bot 身份识别 |
| `发言者身份刷新: group=... user=... role=...` | 当前发言者身份主动刷新（verbose_logging） |
| `权限决策链[命令权限] user=... group=...` | 命令权限判断全过程（verbose_logging 输出完整步骤） |
| `注入管理 prompt: group=... role=...` | HookHandler 按群精确注入 |
| `注入检测: group_id=...` | verbose_logging 注入诊断 |
| `守门拦截: Bot(role=...)错误宣称无权限` | after_response 守门触发 |
| `守门拦截: Bot 口头宣称已执行但无真实工具调用` | 守门拦截"编造已执行"回复 |
| `守门改写回复: group=...` | 守门已替换回复内容 |
| `自动检查入群申请: groups={...}` | 自动审批扫描开始 |
| `入群申请详情 / 入群申请决策` | 审批决策过程 |
| `自动通过入群 / 自动拒绝入群` | 审批执行结果 |
| `操作被拦截: ...` | 安全护栏拦截 |
| `跨日清零: group=...` | 每日计数器重置 |

---

## 技术细节

- **平台**：QQ（NapCat / MaiBot1.0-1.99）
- **SDK**：MaiBot Plugin SDK v2
- **适配器**：MaiBot-Napcat-Adapter
- **提示词注入**：三阶段注入 — `chat.receive.after_process` 缓存映射 → `maisaka.planner.before_request`（Planner 决策准则） → `maisaka.replyer.before_request` + `before_model_request`（Replyer 自然语言提示）
- **守门**：`after_response` HookHandler 两层拦截 — ① 拦截 Bot 错误宣称无权限的回复，替换为"我是{群主/管理员}，我来处理。"；② 拦截"已将 xxx 禁言 / 已撤回 / 已踢出"等无真实工具执行的"编造已执行"回复，改写为诚实表述。
- **并发安全**：`asyncio.Lock` 保护所有共享状态
- **API 调用**：群管理核心操作使用 `_call_api`（直接 kwarg），系统消息/审批使用 `_call_action_api`（params 包装）
- **依赖**：tomlkit（配置持久化读写）
- **许可证**：GPL-v3.0-or-later

---

## v2.5 功能总览

| 模块 | 数量 | 详情 |
|------|:---:|------|
| 管理 Tool | 18 | warn / mute / unmute / kick / recall / set_essence / unset_essence / card / title / name / approve_join / reject_join / post_notice / delete_notice / get_member / get_shut_list / get_system_msg / get_notice |
| 快捷命令 | 15 | /admin(status\|off\|on\|undo\|log\|perm\|ban\|unban) + /mute / /unmute / /kick / /warn / /essence / /recall / /shutlist |
| HookHandler | 5 | chat.receive(缓存) / planner.before_request(Planner注入) / replyer.before_request(extra_prompt) / replyer.before_model_request(messages) / replyer.after_response(守门) |
| EventHandler | 1 | 追踪（群号映射/计数/角色缓存） |
| 安全护栏 | 8 步 | protected_users → exempt_users → admins → auto_exempt → mute_cooldown → 每日限额 → kick_confirm → 处罚阶梯 |
| 配置分区 | 10 | plugin / admin / identity / auto_moderate / safeguard / warning / escalation / auto_approve / logging / prompts |
| 自动审批 | 支持 | 全局 + 按群独立覆盖（TOML 数组表），关键词过滤 + 每日限额 |
| 警告系统 | 支持 | spam / abuse / ad 三类，可配阈值和计数窗口 |
| 处罚阶梯 | 支持 | 按回溯小时数和操作次数自动升级 mute→kick |
| 角色感知 | 支持 | 自动检测 Bot 角色 + 主动识别当前发言者身份（群主/管理员/普通成员），双身份注入提示词 |
| 权限决策链 | 支持 | `/admin perm` 可视化 + verbose 日志输出完整判断链，方便排查权限问题 |
| 身份缓存刷新 | 高频 | Bot 角色 5 分钟、发言者 2 分钟、目标身份 10 分钟，均可在 `[identity]` 配置 |
| 并发安全 | asyncio.Lock | 所有 Tool 和后台任务共享一把锁 |

---

## 更新日志

完整更新历史请参见 [CHANGELOG.md](CHANGELOG.md)。
