#!/usr/bin/env python3
"""
MindKernel Active Push Worker v0.1

监控 MECD pipeline 产出的高置信度 Decision Trace（≥0.85），
主动向用户展示，并写入 MEMORY.md / memory/ 日志。

触发条件（满足任一）：
  1. final_outcome == "completed" AND decision_mode == "normal"
     AND epistemic_state == "supported"                   → confidence ≈ 0.92
  2. final_outcome == "completed" AND decision_mode == "normal"  → confidence ≈ 0.88

幂等：基于 decision_trace_id 写入 ledger，重复触发不重复展示。
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

DEFAULT_DB = ROOT / "data" / "mindkernel_v0_1.sqlite"
LEDGER_FILE = ROOT / "data" / "governance" / "active_push_ledger.jsonl"
LEDGER_LOCK = ROOT / "data" / "governance" / "active_push_ledger.lock"
PUSH_BUFFER = ROOT / "data" / "governance" / "active_push_buffer.jsonl"
MEMORY_MD = ROOT.parent / "workspace" / "MEMORY.md"

CONFIDENCE_THRESHOLD = 0.85


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _mk_now_local():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")


def _acquire_lock(path: Path):
    """PID 文件锁（fcntl.flock 在某些环境不可用）"""
    path.parent.mkdir(parents=True, exist_ok=True)
    my_pid = os.getpid()
    if path.exists():
        old_pid = int(path.read_text().strip())
        # 检查旧 PID 是否还活着
        try:
            os.kill(old_pid, 0)
            # 旧进程还活着，锁被占用
            raise OSError(f"Lock held by PID {old_pid}")
        except (ProcessLookupError, PermissionError):
            # 旧进程已死，可覆盖
            pass
    path.write_text(str(my_pid))
    return path


def _read_ledger() -> set:
    ledger = set()
    if not LEDGER_FILE.exists():
        return ledger
    for line in LEDGER_FILE.read_text().splitlines():
        try:
            ledger.add(json.loads(line)["decision_id"])
        except Exception:
            pass
    return ledger


def _append_ledger(decision_id: str, pushed_at: str):
    LEDGER_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LEDGER_FILE, "a") as f:
        f.write(json.dumps({"decision_id": decision_id, "pushed_at": pushed_at}, ensure_ascii=False) + "\n")


def _append_push_buffer(entry: dict):
    PUSH_BUFFER.parent.mkdir(parents=True, exist_ok=True)
    with open(PUSH_BUFFER, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _estimate_confidence(payload: dict) -> float:
    """从 decision trace payload 估算置信度（0.0~1.0）"""
    outcome = payload.get("final_outcome", "")
    mode = payload.get("decision_mode", "")
    epistemic = payload.get("epistemic_state", "")

    if outcome == "completed" and mode == "normal" and epistemic == "supported":
        return 0.92
    elif outcome == "completed" and mode == "normal":
        return 0.88
    elif outcome == "limited" and epistemic == "supported":
        return 0.72
    elif outcome == "escalated":
        return 0.60
    elif outcome == "abstained":
        return 0.40
    elif outcome == "blocked":
        return 0.20
    return 0.50


def _format_reply_suggestion(payload: dict, confidence: float) -> str:
    """生成用户可见的回复建议"""
    outcome = payload.get("final_outcome", "")
    reason = payload.get("reason", "") or ""
    reason_short = reason[:120].strip()

    if outcome == "completed":
        return f"✅ MECD 决策完成（置信度 {confidence:.0%}）：{reason_short}"
    elif outcome == "limited":
        return f"⚠️ MECD 有限决策（置信度 {confidence:.0%}）：{reason_short}"
    elif outcome == "escalated":
        return f"⬆️ MECD 待升决策（置信度 {confidence:.0%}）：{reason_short}"
    else:
        return f"📋 MECD 决策记录（置信度 {confidence:.0%}）：{reason_short}"


def _write_to_memory_md(entry: dict):
    """写入 MEMORY.md 结论区"""
    if not MEMORY_MD.exists():
        return

    content = MEMORY_MD.read_text(encoding="utf-8")
    decision_id = entry["decision_id"]
    suggestion = entry["reply_suggestion"]
    decision_time = entry["decision_time"]
    confidence = entry["confidence"]

    marker = f"[MECD-PUSH:{decision_id}]"
    if marker in content:
        return

    new_block = f"\n<!-- {marker} -->\n- **{decision_time}** [{confidence:.0%}] {suggestion}\n"

    if "## 最新决策区" in content:
        content = content.replace("## 最新决策区", f"## 最新决策区{new_block}")
    else:
        content += f"\n\n## 最新决策区\n{new_block}"

    MEMORY_MD.write_text(content, encoding="utf-8")


def _write_experience_log(entry: dict):
    """写入 memory/YYYY-MM-DD.md 带 [MECD-PUSH] 标记"""
    today_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_path = ROOT.parent / "workspace" / "memory" / f"{today_utc}.md"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    decision_id = entry["decision_id"]
    suggestion = entry["reply_suggestion"]
    confidence = entry["confidence"]
    payload = entry["payload"]
    pushed_at = entry["pushed_at"]

    block = (
        f"\n## [MECD-PUSH] 主动推送记录\n"
        f"- decision_id: `{decision_id}`\n"
        f"- confidence: {confidence:.0%}\n"
        f"- outcome: {payload.get('final_outcome')}\n"
        f"- mode: {payload.get('decision_mode')}\n"
        f"- epistemic: {payload.get('epistemic_state')}\n"
        f"- reason: {payload.get('reason', '')[:200]}\n"
        f"- reply_suggestion: {suggestion}\n"
        f"- pushed_at: {pushed_at}\n"
    )

    marker = f"[MECD-PUSH:{decision_id}]"
    if log_path.exists():
        existing = log_path.read_text(encoding="utf-8")
        if marker in existing:
            return
        log_path.write_text(existing + block + "\n", encoding="utf-8")
    else:
        header = f"# {today_utc}\n\n<!-- {marker} -->\n"
        log_path.write_text(header + block + "\n", encoding="utf-8")


def scan_decision_traces(db_path: Path, dry_run: bool = True) -> list[dict]:
    """扫描近 24 小时新 decision traces，触发主动推送"""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    ledger = _read_ledger()
    pushed = []

    rows = conn.execute(
        """
        SELECT id, final_outcome, payload_json, created_at
        FROM decision_traces
        WHERE created_at >= datetime('now', '-24 hours')
        ORDER BY created_at DESC
        LIMIT 50
        """
    ).fetchall()

    conn.close()

    for row in rows:
        dt_id = row["id"]
        if dt_id in ledger:
            continue

        payload = json.loads(row["payload_json"])
        confidence = _estimate_confidence(payload)

        if confidence < CONFIDENCE_THRESHOLD:
            continue

        suggestion = _format_reply_suggestion(payload, confidence)
        entry = {
            "decision_id": dt_id,
            "confidence": confidence,
            "decision_time": row["created_at"],
            "reply_suggestion": suggestion,
            "payload": payload,
            "pushed_at": now_iso(),
        }

        if not dry_run:
            _append_push_buffer(entry)
            _append_ledger(dt_id, now_iso())
            _write_to_memory_md(entry)
            _write_experience_log(entry)

        pushed.append(entry)

    return pushed


def read_buffer() -> list[dict]:
    """读取当前 push buffer（供 heartbeat 读取展示）"""
    entries = []
    if not PUSH_BUFFER.exists():
        return entries
    for line in PUSH_BUFFER.read_text().splitlines():
        try:
            entries.append(json.loads(line))
        except Exception:
            pass
    return entries


def clear_buffer():
    """清空 push buffer（展示后调用）"""
    if PUSH_BUFFER.exists():
        PUSH_BUFFER.unlink()


def main():
    p = argparse.ArgumentParser(description="MindKernel Active Push Worker v0.1")
    p.add_argument("--db", default=str(DEFAULT_DB))
    p.add_argument("--dry-run", action="store_true", default=False)
    p.add_argument("--daemon", action="store_true")
    p.add_argument("--interval", type=int, default=300)
    p.add_argument("--once", action="store_true")
    args = p.parse_args()

    lock_path = Path(str(LEDGER_LOCK).replace(".lock", f"_{os.getpid()}.lock"))
    if args.daemon or args.once:
        try:
            _acquire_lock(lock_path)
        except OSError as e:
            print(f"ERROR: another push worker is running — {e}")
            sys.exit(1)

    print(f"[active_push] Starting... dry={args.dry_run} threshold={CONFIDENCE_THRESHOLD}")

    if args.daemon:
        print(f"[active_push] Daemon mode, interval={args.interval}s")
        while True:
            try:
                results = scan_decision_traces(Path(args.db), dry_run=args.dry_run)
                for r in results:
                    print(f"[PUSH] decision_id={r['decision_id']} conf={r['confidence']:.0%} → {r['reply_suggestion']}")
            except sqlite3.OperationalError as e:
                if "no such table" in str(e):
                    print(f"[active_push] DB table not ready, skipping this cycle.")
                else:
                    print(f"[ERROR] DB error: {e}")
            except Exception as e:
                print(f"[ERROR] scan_decision_traces failed: {e}")
            time.sleep(args.interval)
    else:
        try:
            results = scan_decision_traces(Path(args.db), dry_run=args.dry_run)
            print(f"[active_push] Scanned. new pushes={len(results)}")
            for r in results:
                print(f"  → {r['reply_suggestion']}")
        except sqlite3.OperationalError as e:
            if "no such table" in str(e):
                print(f"[active_push] DB table 'decision_traces' not ready yet (MECD pipeline pending). Skipping.")
            else:
                raise


if __name__ == "__main__":
    main()
