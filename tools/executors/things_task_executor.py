#!/usr/bin/env python3
"""
Things Task Executor — M2 propose_task 行动分发到 Things 3

功能：
- 读取 active_push_buffer 中 type=propose_task 的条目
- 通过 things CLI 创建 Things 3 任务
- 幂等 ledger 防重复创建

Usage:
  python tools/executors/things_task_executor.py [--once]
  python tools/executors/things_task_executor.py --daemon
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BUFFER = ROOT / "data" / "governance" / "active_push_buffer.jsonl"
LEDGER = ROOT / "data" / "governance" / "things_executed_ledger.jsonl"
THINGS_BIN = "/opt/homebrew/bin/things"


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_ledger() -> set:
    if not LEDGER.exists():
        return set()
    try:
        return set(json.loads(LEDGER.read_text()))
    except Exception:
        return set()


def save_ledger(ids: set):
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(sorted(ids)))


def things_add(title: str, notes: str = "", tags: str = "MindKernel", urgency: str = "medium") -> bool:
    """通过 things CLI 添加任务（Things 3 未安装时 fallback 到 JSONL 队列）。"""
    cmd = [THINGS_BIN, "add"]
    cmd += ["--notes", notes[:500]] if notes else []
    cmd += ["--tags", tags]
    if urgency == "high":
        cmd += ["--when", "today"]
    elif urgency == "medium":
        cmd += ["--when", "tomorrow"]
    cmd += ["--", title[:200]]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(f"[Things] Added: {title[:60]}")
            return True
        print(f"[Things] CLI failed (RC={result.returncode}), falling back to JSONL queue")
    except Exception as e:
        print(f"[Things] CLI exception: {e}, falling back to JSONL queue")

    # Fallback: write to JSONL task queue
    return write_task_to_queue(title, notes=notes, tags=tags, urgency=urgency)


def write_task_to_queue(title: str, notes: str = "", tags: str = "MindKernel", urgency: str = "medium") -> bool:
    """Fallback: write task to JSONL queue when Things 3 not available."""
    import uuid
    queue_path = ROOT / "data" / "governance" / "propose_task_queue.jsonl"
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "id": f"task_{uuid.uuid4().hex[:8]}",
        "title": title[:200],
        "notes": notes[:500],
        "tags": tags,
        "urgency": urgency,
        "source": "dreaming",
        "created_at": now_iso(),
        "status": "pending",
    }
    with open(queue_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"[TaskQueue] Queued: {title[:60]}")
    return True


def execute_propose_task(entry: dict) -> bool:
    """执行单个 propose_task action。"""
    task_text = entry.get("task_text", entry.get("text", "MindKernel 建议任务"))
    notes = entry.get("notes", "")
    urgency = entry.get("urgency", "medium")
    return things_add(task_text, notes=notes, urgency=urgency)


def main():
    parser = argparse.ArgumentParser(description="MindKernel Things Task Executor")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    parser.add_argument("--interval", type=int, default=300, help="Loop interval in seconds")
    args = parser.parse_args()

    print(f"[Things] Executor starting... mode={'daemon' if args.daemon else 'once'}")

    executed_ids = load_ledger()
    new_executed = set()

    def process_buffer():
        if not BUFFER.exists():
            return
        remaining = []
        new_sent = 0
        for line in BUFFER.read_text().splitlines():
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except Exception:
                remaining.append(line)
                continue

            if entry.get("source") != "dreaming":
                remaining.append(line)
                continue

            if entry.get("type") != "propose_task" and entry.get("action_type") != "propose_task":
                remaining.append(line)
                continue

            entry_id = entry.get("id", "")
            if entry_id in executed_ids:
                remaining.append(line)
                continue

            if execute_propose_task(entry):
                new_sent += 1
                executed_ids.add(entry_id)
                new_executed.add(entry_id)
            else:
                remaining.append(line)

        BUFFER.write_text("\n".join(remaining) + "\n")
        if new_sent:
            save_ledger(executed_ids)
            print(f"[Things] Done. Created {new_sent} tasks. Total ledger: {len(executed_ids)}")

    if args.daemon:
        import time
        while True:
            process_buffer()
            time.sleep(args.interval)
    else:
        process_buffer()


if __name__ == "__main__":
    main()
