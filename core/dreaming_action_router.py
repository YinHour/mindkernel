#!/usr/bin/env python3
"""
Dreaming Action Router — 做梦行动分发路由

三类行动的分发逻辑（幂等）：
- ask_human  → 写入 active_push_buffer + message 工具
- propose_task → 写入任务队列（TODO: 接入 Things / 飞书任务）
- drive_conversation → 写入 active_push_buffer
"""

from __future__ import annotations

import json
import logging
import re
import sys
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUSH_BUFFER = ROOT / "data" / "governance" / "active_push_buffer.jsonl"

logger = logging.getLogger("dreaming.router")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def push_to_active_buffer(
    action: dict,
    insight_id: str,
    entry: dict,
) -> bool:
    """
    写入 active_push_buffer，触发 HEARTBEAT 展示。
    """
    PUSH_BUFFER.parent.mkdir(parents=True, exist_ok=True)

    push_type = entry.get("dreaming_task", "dreaming")
    opening_line = action.get("opening_line", "")
    task_text = action.get("task_text", "")
    topic = action.get("topic", "")
    urgency = action.get("urgency", "medium")

    # 构建展示文本
    actual_action = action.get("action", "")
    if opening_line:
        display_text = opening_line
    elif task_text:
        display_text = f"💡 建议：{task_text}"
    elif topic:
        display_text = f"💬 {topic}"
    elif actual_action == "ask_human" and action.get("question"):
        display_text = f"🤔 {action.get('question')}"
    else:
        display_text = f"🌙 做梦洞察（ID: {insight_id}）"

    push_entry = {
        "id": f"push_{uuid.uuid4().hex[:8]}",
        "source": "dreaming",
        "insight_id": insight_id,
        "type": push_type,
        "action_type": actual_action,
        "text": display_text,
        "urgency": urgency,
        "triggered_at": now_iso(),
        "status": "pending",
    }

    with open(PUSH_BUFFER, "a", encoding="utf-8") as f:
        f.write(json.dumps(push_entry, ensure_ascii=False) + "\n")

    logger.info(f"[Router] 写入 push buffer: {push_entry['id']}, text={display_text[:60]}")
    return True


def dispatch_entry_actions(entry_id: str, entry: dict) -> list[dict]:
    """
    分发单条 dreaming_entry 的所有 triggered_actions。
    幂等：重复调用不会重复分发。
    """
    from core.dreaming_store import is_action_dispatched, mark_action_dispatched

    results = []
    for action in entry.get("triggered_actions", []):
        action_type = action.get("action", "")
        if action_type == "none":
            continue

        action_id = f"{entry_id}_{action_type}"
        if is_action_dispatched(action_id):
            logger.info(f"[Router] 幂等跳过: {action_id}")
            continue

        try:
            if action_type == "ask_human":
                result = _dispatch_ask_human(action, entry)
            elif action_type == "propose_task":
                result = _dispatch_propose_task(action, entry)
            elif action_type == "drive_conversation":
                result = _dispatch_drive_conversation(action, entry)
            else:
                result = {"status": "unknown_action", "action": action_type}
                logger.warning(f"[Router] 未知 action 类型: {action_type}")

            mark_action_dispatched(action_id, result)
            results.append(result)

        except Exception as e:
            logger.exception(f"[Router] 分发失败: action_id={action_id}, e={e}")
            results.append({"status": "error", "action_id": action_id, "error": str(e)})

    return results


def _dispatch_ask_human(action: dict, entry: dict) -> dict:
    """分发 ask_human：写入 push buffer"""
    push_to_active_buffer(action, entry["id"], entry)
    return {
        "status": "dispatched",
        "action": "ask_human",
        "entry_id": entry["id"],
        "question": action.get("question", ""),
        "urgency": action.get("urgency", "medium"),
    }


def _dispatch_propose_task(action: dict, entry: dict) -> dict:
    """分发 propose_task：写入 push buffer + 执行 Things 3"""
    push_to_active_buffer(action, entry["id"], entry)
    # Execute via Things CLI
    task_text = action.get("task_text", "")
    notes = action.get("notes", "")
    urgency = action.get("urgency", "medium")
    things_ok = False
    try:
        import subprocess
        things_bin = "/opt/homebrew/bin/things"
        cmd = [things_bin, "add"]
        if notes:
            cmd += ["--notes", notes[:500]]
        cmd += ["--tags", "MindKernel"]
        if urgency == "high":
            cmd += ["--when", "today"]
        elif urgency == "medium":
            cmd += ["--when", "tomorrow"]
        cmd += ["--", task_text[:200]]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        things_ok = result.returncode == 0
        if things_ok:
            logger.info(f"[Router→Things] Added: {task_text[:60]}")
        else:
            logger.warning(f"[Router→Things] Failed: {result.stderr[:100]}")
            _write_task_to_queue_fallback(task_text, notes, urgency, entry["id"])
    except Exception as e:
        logger.warning(f"[Router→Things] Exception: {e}")
        _write_task_to_queue_fallback(task_text, notes, urgency, entry["id"])
    return {
        "status": "dispatched",
        "action": "propose_task",
        "entry_id": entry["id"],
        "task_text": task_text,
        "urgency": urgency,
        "things_executed": things_ok,
    }


def _write_task_to_queue_fallback(title: str, notes: str = "", urgency: str = "medium", entry_id: str = ""):
    """Fallback: write propose_task to JSONL when Things 3 not available."""
    import uuid
    queue_path = ROOT / "data" / "governance" / "propose_task_queue.jsonl"
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    entry_obj = {
        "id": f"task_{uuid.uuid4().hex[:8]}",
        "title": title[:200],
        "notes": notes[:500],
        "tags": "MindKernel",
        "urgency": urgency,
        "source": "dreaming",
        "dreaming_entry_id": entry_id,
        "created_at": now_iso(),
        "status": "pending",
    }
    with open(queue_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry_obj, ensure_ascii=False) + "\n")
    logger.info(f"[Router→TaskQueue] Queued: {title[:60]}")


def _dispatch_drive_conversation(action: dict, entry: dict) -> dict:
    """分发 drive_conversation：写入 push buffer"""
    push_to_active_buffer(action, entry["id"], entry)
    return {
        "status": "dispatched",
        "action": "drive_conversation",
        "entry_id": entry["id"],
        "opening_line": action.get("opening_line", ""),
        "urgency": action.get("urgency", "medium"),
    }


def dispatch_all_pending() -> list[dict]:
    """
    扫描所有 pending 的 triggered_actions，一次性分发。
    """
    from core.dreaming_store import conn

    results = []
    with conn() as c:
        rows = c.execute(
            """SELECT id, triggered_actions, dreaming_task, cognition_text
               FROM dreaming_entries
               WHERE status = 'candidate'
                 AND triggered_actions != '[]'
               ORDER BY created_at DESC
               LIMIT 50"""
        ).fetchall()

    for row in rows:
        entry = dict(row)
        entry["triggered_actions"] = json.loads(entry["triggered_actions"])
        try:
            results.extend(dispatch_entry_actions(entry["id"], entry))
        except Exception as e:
            logger.warning(f"[Router] entry {entry['id']} 分发失败: {e}")

    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    print("=== 手动触发 Action 分发 ===")
    results = dispatch_all_pending()
    print(f"共分发 {len(results)} 个 action")
    for r in results:
        print(json.dumps(r, indent=2, ensure_ascii=False))
