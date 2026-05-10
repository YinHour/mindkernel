# M2 行动分发落地 — Implementation Plan

**Goal:** 让 MindKernel 从被动响应变成主动出击，三类行动（ask_human / propose_task / drive_conversation）真实触发外部行为。

**Architecture:**
- Generator（每30分钟）：扫描近期记忆/Experience，生成 `dreaming_entries` 带 `triggered_actions`
- Dispatcher（每日02:00）：将 `dreaming_entries` 分发到 `active_push_buffer`
- Executor（每15分钟）：三类 action 真实执行（Telegram / Things 3 / OpenClaw session）
- 全链路幂等，ledger 防重

**Tech Stack:** Python 3.13 (venv), launchd, openclaw message CLI, Things 3 CLI (things.py)

---

## Task M2-1: 修复 Telegram Sender Python 环境

**Problem:** `dreaming_telegram_sender.py` 使用 `/opt/homebrew/bin/python3`（系统 Python 3.14），缺少项目依赖。

**Step 1: 验证问题**
```bash
/opt/homebrew/bin/python3 -c "from core.dreaming_store import conn" 2>&1
# Expected: ModuleNotFoundError
```

**Step 2: 修复 plist — 改用 venv python**
```bash
# 将 ProgramArguments 从:
# /opt/homebrew/bin/python3 tools/dreaming/dreaming_telegram_sender.py
# 改为:
# /Users/zhengwang/projects/mindkernel/.venv/bin/python tools/dreaming/dreaming_telegram_sender.py
```

**Step 3: 重新加载 plist**
```bash
launchctl bootout gui/$(id -u)/com.zhengwang.mindkernel.dreaming-telegram
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.zhengwang.mindkernel.dreaming-telegram.plist
echo "Telegram sender restarted with venv python"
```

**Step 4: 手动触发验证**
```bash
cd /Users/zhengwang/projects/mindkernel
.venv/bin/python tools/dreaming/dreaming_telegram_sender.py
# Expected: "[TG] No new messages to send" (buffer is clean)
```

**Step 5: Commit**
```bash
git add ~/Library/LaunchAgents/com.zhengwang.mindkernel.dreaming-telegram.plist
git commit -m "fix(M2): use venv python in dreaming-telegram plist"
```

---

## Task M2-2: 实现持续做梦 Generator（根因修复）

**Problem:** 只有 3 条 dreaming_entries，无持续生成机制，M2 整个链条处于休眠。

**Files:**
- Create: `core/dreaming_generator.py`

**Step 1: 写测试**
```bash
cd /Users/zhengwang/projects/mindkernel
.venv/bin/python -c "
from core.dreaming_generator import generate_dreaming_entries
from core.dreaming_store import conn
with conn() as c:
    before = c.execute('SELECT COUNT(*) FROM dreaming_entries').fetchone()[0]
entries = generate_dreaming_entries(max_entries=5)
print(f'Generated {len(entries)} entries (before: {before})')
for e in entries[:2]:
    print(' ', e['id'], e.get('triggered_actions', '[]')[:80])
"
# Expected: 生成若干新条目，写入 dreaming_entries 表
```

**Step 2: 实现 `core/dreaming_generator.py`**
核心逻辑：
- 扫描近 7 天未处理的 memory_items / experience_records
- LLM 驱动洞察生成（使用 GLM-4.7 / MiniMax-M2.7）
- 生成 `triggered_actions` 候选（ask_human / propose_task / drive_conversation）
- 幂等：检查 `dreaming_entries` 中相同 memory_ref 跳过
- 支持 batch：每次生成 3~5 条

关键函数：
```python
def generate_dreaming_entries(max_entries: int = 5) -> list[dict]:
    """扫描近期记忆，生成带 triggered_actions 的 dreaming_entries。"""
    # 1. 读取近7天 active memory/experience
    # 2. 构造 prompt 调用 LLM 生成洞察 + actions
    # 3. 过滤已有 memory_ref（幂等）
    # 4. 写入 dreaming_entries 表 (status='candidate')
    # 5. 返回生成条目
```

**Step 3: 创建 launchd 生成器（每30分钟）**
```bash
# 创建 plist: com.zhengwang.mindkernel.dreaming-generator.plist
# Program: /Users/zhengwang/projects/mindkernel/.venv/bin/python -m core.dreaming_generator
# Interval: 1800 (30 min)
```

**Step 4: 验证**
```bash
cd /Users/zhengwang/projects/mindkernel
.venv/bin/python -m core.dreaming_generator
# Check: SELECT COUNT(*) FROM dreaming_entries — should increase
```

**Step 5: Commit**
```bash
git add core/dreaming_generator.py
git add ~/Library/LaunchAgents/com.zhengwang.mindkernel.dreaming-generator.plist
git commit -m "feat(M2): add dreaming_generator — 持续生成带triggered_actions的dreaming_entries"
```

---

## Task M2-3: 实现 propose_task → Things 3

**Problem:** `propose_task` 分发只有存根，需要真实接入 Things 3。

**Step 1: 验证 things CLI 可用**
```bash
~/go/bin/things.py list --tasks 2>&1 | head -10
# 或: which things（如果装了 things CLI）
```

**Step 2: 创建 `tools/executors/things_task_executor.py`**
```python
def execute_propose_task(action: dict) -> bool:
    """通过 things CLI 或 things-py 创建 Things 3 任务。"""
    task_title = action.get("task_text", "MindKernel 建议任务")
    notes = action.get("notes", "")
    # 调用: things add "title" --notes "notes"
    # 或 things_py API
```

**Step 3: 修改 `dreaming_action_router.py` 的 `_dispatch_propose_task`**
当前只写入 buffer，改为真实执行 Things：
```python
def _dispatch_propose_task(action: dict, entry: dict) -> dict:
    from tools.executors.things_task_executor import execute_propose_task
    success = execute_propose_task(action)
    return {
        "action": "propose_task",
        "status": "executed" if success else "failed",
        ...
    }
```

**Step 4: Commit**
```bash
git add tools/executors/things_task_executor.py
git commit -m "feat(M2): implement propose_task → Things 3 executor"
```

---

## Task M2-4: 实现 drive_conversation → OpenClaw Session

**Problem:** `drive_conversation` 无实现，AI 不会主动发起对话。

**Step 1: 研究 OpenClaw sessions_send**
```bash
openclaw help sessions 2>&1 | head -20
# 确认 sessions_send 工具可用
```

**Step 2: 创建 `tools/executors/conversation_driver.py`**
```python
def execute_drive_conversation(action: dict, session_key: str = "main") -> bool:
    """通过 sessions_send 向 OpenClaw main session 发送消息，触发主动对话。"""
    opening_line = action.get("opening_line", "")
    topic = action.get("topic", "")
    text = opening_line or f"💬 {topic}"
    # 调用 sessions_send(session_key, text)
```

**Step 3: 修改 `dreaming_action_router.py` 的 `_dispatch_drive_conversation`**
改为真实发送：
```python
def _dispatch_drive_conversation(action: dict, entry: dict) -> dict:
    from tools.executors.conversation_driver import execute_drive_conversation
    success = execute_drive_conversation(action)
    return {
        "action": "drive_conversation",
        "status": "executed" if success else "failed",
        ...
    }
```

**Step 4: Commit**
```bash
git add tools/executors/conversation_driver.py
git commit -m "feat(M2): implement drive_conversation → OpenClaw session主动触达"
```

---

## Task M2-5: M2 端到端验证

**Step 1: 触发一次 generator**
```bash
cd /Users/zhengwang/projects/mindkernel
.venv/bin/python -m core.dreaming_generator
```

**Step 2: 检查 dreaming_entries**
```bash
.venv/bin/python -c "
from core.dreaming_store import conn
with conn() as c:
    rows = c.execute('SELECT id, triggered_actions FROM dreaming_entries ORDER BY created_at DESC LIMIT 5').fetchall()
    for r in rows: print(r[0], r[1][:100])
"
```

**Step 3: 手动触发 dispatcher**
```bash
.venv/bin/python -m core.dreaming_action_router
# 检查 active_push_buffer 有新条目
```

**Step 4: 手动触发 telegram sender**
```bash
.venv/bin/python tools/dreaming/dreaming_telegram_sender.py
# 检查 Telegram 收到消息
```

---

## Task M2-6: 全链路提交 & 推送

```bash
git add .
git commit -m "feat(M2): 行动分发落地 — generator/ask_human-TG/propose_task-Things/drive_conversation"
git push origin main
```

---

## 预期效果

- Generator 每30分钟扫描新记忆，生成 `dreaming_entries`
- 每日02:00 dispatcher 分发 entries 到 buffer
- Telegram sender 每15分钟发送 pending ask_human 到王大爷
- Things 3 收到 propose_task 任务提案
- OpenClaw main session 收到 drive_conversation 主动触达
