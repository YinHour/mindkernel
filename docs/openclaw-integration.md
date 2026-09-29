# MindKernel × OpenClaw 集成方案

> 本文档描述如何通过 MCP（Model Context Protocol）将 MindKernel 的记忆能力接入 OpenClaw Agent。

> 状态说明（2026-09-17）：下方接入表为历史部署记录，不代表当前机器已安装或运行。2026-05-10 的 `TODO.md` 另记录经验卡片已接入 active push buffer；实际展示与送达仍需端到端验证。做梦机制的 `drive_conversation` 当前通过 Telegram Sender 触达，不等同于向 OpenClaw session 发起对话。

## 架构概览

```
┌──────────────────────────────────────────────────────┐
│                   OpenClaw Agent                       │
│   (Memory Adapter: 对话历史 → MindKernel retain 格式)  │
└──────────────────────┬───────────────────────────────┘
                       │ mcporter call
                       ▼
┌──────────────────────────────────────────────────────┐
│               mcporter (MCP Client)                    │
│   ~/.mcporter/mcporter.json                           │
└──────────────────────┬───────────────────────────────┘
                       │ stdio (JSON-RPC 2.0)
                       ▼
┌──────────────────────────────────────────────────────┐
│         MindKernel MCP Server (Python)                │
│   plugins/mcp_server/server.py                        │
│   ├── mindkernel_retain   (写记忆)                    │
│   ├── mindkernel_recall   (读记忆)                    │
│   └── mindkernel_reflect  (反思生成经验)               │
└──────────────────────┬───────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────┐
│              MindKernel Core (Python)                 │
│   core/memory_experience_core_v0_1.py                 │
│   core/reflect_gate_v0_1.py                          │
└──────────────────────┬───────────────────────────────┘
                       │
                       ▼
              data/mindkernel_v0_1.sqlite
```

## 历史接入进度（结合后续开发记录）

| 组件 | 状态 | 说明 |
|------|------|------|
| MCP Server (`server.py`) | ✅ 完成 | JSON-RPC 2.0 stdio，已验证 |
| 三个核心工具 | ✅ 完成 | retain / recall / reflect |
| mcporter 配置 | ✅ 完成 | `~/.mcporter/mcporter.json` |
| OpenClaw mcporter skill | ✅ 完成 | 全局已安装 |
| **记忆适配层** | ✅ 完成 | `skills/mindkernel-retain/retain.py` + cron |
| **Daemon 对接** | ✅ 完成 | `openclaw_event_adapter.py` + daemon `--feature-flag on` |
| **launchd 自启** | ✅ 完成 | 3个 plist 已加载 |
| **Reflect Worker** | ✅ 完成 | scheduler queue → experience 生成 |
| 经验卡片推送 | 已有后续实现记录 | 2026-05-10：`scan_experience_cards` 接入 active_push_worker；对话展示与送达需实测 |

## 快速验证

```bash
# 1. 列出工具
mcporter list mindkernel

# 2. 查询已有记忆
mcporter call mindkernel.mindkernel_recall table="memory_items" limit=5

# 3. 写入一条测试记忆
mcporter call mindkernel.mindkernel_retain \
  text="通过MCP接入了OpenClaw" \
  source="openclaw" \
  tags='["integration","test"]'

# 4. 查看刚写入的记录
mcporter call mindkernel.mindkernel_recall table="memory_items" limit=1
```

## 记忆适配层设计（设计背景；接入状态见上表）

### 触发时机

OpenClaw 每次响应用户消息后，评估是否值得 retain：

- **高价值触发**（直接 retain）：
  - 用户提供了新事实、数据、决定
  - 用户更正了之前的错误
  - 明确的偏好或习惯表达

- **批量触发**（Daemon 定时）：
  - 每日对话摘要
  - 高频模式识别后写入

### retain 格式映射

| OpenClaw 对话事件 | MindKernel payload |
|-------------------|---------------------|
| 用户消息原文 | `text` |
| 消息来源（telegram/feishu）| `source` |
| 时间戳 | `created_at` |
| 消息ID | 存入 `evidence_refs` |
| 提取的实体/标签 | `tags` |

### 示例流程

```
用户: "我下周要去北京出差"
         ↓
OpenClaw 拦截消息
         ↓
记忆候选评估 → 触发 retain
         ↓
mcporter call mindkernel.mindkernel_retain
  text="用户计划下周（2026-03-24起）去北京出差"
  source="telegram"
  tags='["travel","plan"]'
         ↓
MindKernel SQLite 写入
```

## 后续验证

1. **记忆适配层**：验证真实对话的候选评估、retain 写入与来源引用。
2. **Daemon 协同**：验证对话事件进入队列后，worker 实际消费并产生预期对象。
3. **经验卡片**：验证 reflect 生成、推送入队、用户实际收到及反馈关联，分别记录各步结果。

---

> 原始集成记录：2026-03-18；文档口径校正：2026-09-17（未重新验收部署）。
