#!/usr/bin/env python3
"""
MindKernel 治理引擎 — MECD 参数定标核心

功能：
1. 读取 Decision traces，分析 outcome 分布
2. 调用 param_config.update_feedback() 自动更新参数
3. 生成治理报告
4. 异常时告警

Usage:
  python3 governance_engine.py [--once] [--poll --interval 3600]
  推荐 cron 每日一次，或 daemon 内每小时一次

自动在以下情况触发参数更新：
- 有新的 decision trace 未被处理时
- Experience active_ratio 异常时（过度/不足晋升）
- Opinion 置信度偏离目标时
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

API_BASE = "http://localhost:18793"
API_KEY = "mk_IsQ2BrHQCmKx6vqDU0wv5JceElh4hjE7zjQks2YdxTM"
CHECKPOINT_FILE = ROOT / "data" / "governance" / "governance_checkpoint.json"
REPORTS_DIR = ROOT / "reports" / "governance"

PYTHON = "/opt/homebrew/bin/python3"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


# ---------------------------------------------------------------------------
# Checkpoint
# ---------------------------------------------------------------------------

def load_checkpoint() -> dict:
    cp = {"last_decision_id": None, "last_run": None}
    if CHECKPOINT_FILE.exists():
        cp = json.loads(CHECKPOINT_FILE.read_text())
    # Validate last_decision_id exists in either database; reset if missing
    last_id = cp.get("last_decision_id")
    if last_id:
        import sqlite3
        valid = False
        for db_file in ["data/scheduler.sqlite", "data/mindkernel_v0_1.sqlite"]:
            db_path = ROOT / db_file
            if db_path.exists():
                conn = sqlite3.connect(str(db_path))
                cur = conn.cursor()
                cur.execute("SELECT 1 FROM decision_traces WHERE id = ? LIMIT 1", (last_id,))
                if cur.fetchone():
                    valid = True
                conn.close()
            if valid:
                break
        if not valid:
            print(f"[WARN] checkpoint last_decision_id '{last_id}' not found in any database; resetting to None")
            cp["last_decision_id"] = None
            save_checkpoint(cp)
    return cp


def save_checkpoint(cp: dict):
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_FILE.write_text(json.dumps(cp, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
# 数据库直接读取（不依赖 REST API）
# ---------------------------------------------------------------------------

def read_decision_traces(db_path: Path, since_id: str | None = None, limit: int = 50) -> list[dict]:
    """从指定数据库读取 decision traces。"""
    import sqlite3

    if not db_path.exists():
        return []

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    if since_id:
        cur.execute(
            "SELECT id, final_outcome, payload_json, created_at FROM decision_traces WHERE id > ? ORDER BY created_at ASC LIMIT ?",
            (since_id, limit),
        )
    else:
        cur.execute("SELECT id, final_outcome, payload_json, created_at FROM decision_traces ORDER BY created_at DESC LIMIT ?", (limit,))

    rows = cur.fetchall()
    conn.close()

    traces = []
    for row in rows:
        trace_id, outcome, payload_json, created_at = row
        try:
            payload = json.loads(payload_json) if payload_json else {}
        except Exception:
            payload = {}
        traces.append({
            "id": trace_id,
            "outcome": outcome if outcome else payload.get("outcome", "neutral"),
            "confidence": float(payload.get("confidence", 0.5)),
            "episode_summary": payload.get("episode_summary", ""),
            "source": payload.get("source", "daemon"),
            "created_at": created_at,
        })
    return traces


def read_all_new_decision_traces(since_id: str | None, limit: int = 100) -> list[dict]:
    """从两个库合并读取新的 decision traces，按时间排序去重。"""
    scheduler_traces = read_decision_traces(ROOT / "data" / "scheduler.sqlite", since_id=None, limit=limit)
    main_traces = read_decision_traces(ROOT / "data" / "mindkernel_v0_1.sqlite", since_id=None, limit=limit)

    # 合并
    all_traces = {t["id"]: t for t in scheduler_traces + main_traces}

    # 按时间排序
    sorted_traces = sorted(all_traces.values(), key=lambda t: t.get("created_at", ""))

    # 过滤掉已处理的
    if since_id:
        seen = False
        filtered = []
        for t in sorted_traces:
            if t["id"] == since_id:
                seen = True
                continue
            if seen:
                filtered.append(t)
        sorted_traces = filtered

    return sorted_traces[:limit]


def read_experience_stats(db_path: Path) -> dict:
    """读取 Experience 统计。"""
    import sqlite3

    if not db_path.exists():
        return {}

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("SELECT status, COUNT(*) FROM experience_records GROUP BY status")
    stats = dict(cur.fetchall())
    conn.close()
    return stats


def read_memory_stats(db_path: Path) -> dict:
    """读取 Memory 统计。"""
    import sqlite3

    if not db_path.exists():
        return {}

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("SELECT status, COUNT(*) FROM memory_items GROUP BY status")
    stats = dict(cur.fetchall())
    conn.close()
    return stats


# ---------------------------------------------------------------------------
# 核心：运行治理循环
# ---------------------------------------------------------------------------

def run_governance_cycle() -> dict:
    """
    一次治理循环：
    1. 读取新的 Decision traces
    2. 对每条 trace 调用 update_feedback
    3. 检查 Experience 晋升率
    4. 生成报告
    """
    from core.param_config import generate_status_report, get, get_all, update_feedback

    checkpoint = load_checkpoint()
    last_id = checkpoint.get("last_decision_id")

    scheduler_db = ROOT / "data" / "scheduler.sqlite"
    main_db = ROOT / "data" / "mindkernel_v0_1.sqlite"

    # Decision traces 可能在两个库：scheduler.sqlite（worker 历史）和 mindkernel_v0_1.sqlite（M→E 自动写入）
    # checkpoint 按 id 去重，两库合并查

    # 读取新 traces（合并两个库）
    traces = read_all_new_decision_traces(since_id=last_id, limit=100)
    if not traces:
        print(f"[{now_iso()}] No new decision traces")
        checkpoint["last_run"] = now_iso()
        save_checkpoint(checkpoint)
        return {"ok": True, "new_traces": 0, "param_updates": {}}

    # 对每条 trace 更新参数
    all_changes: dict = {}
    for trace in traces:
        try:
            changes = update_feedback(trace)
            if changes:
                all_changes[trace["id"]] = changes
        except Exception as e:
            print(f"[WARN] update_feedback failed for {trace['id']}: {e}")

    # 更新 checkpoint
    checkpoint["last_decision_id"] = traces[-1]["id"]
    checkpoint["last_run"] = now_iso()
    save_checkpoint(checkpoint)

    # Experience 统计
    exp_stats = read_experience_stats(main_db)
    mem_stats = read_memory_stats(main_db)

    # 生成参数报告
    status = generate_status_report()

    # 写入报告
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_DIR / f"governance_{ts}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    exp_active = exp_stats.get("active", 0)
    exp_candidate = exp_stats.get("candidate", 0)
    exp_total = exp_active + exp_candidate or 1
    active_ratio = exp_active / exp_total

    mem_candidate = mem_stats.get("candidate", 0)
    mem_active = mem_stats.get("active", 0)

    # 晋升率异常检测
    alerts = []
    if active_ratio > 0.3:
        alerts.append(f"⚠️ active_ratio={active_ratio:.1%} 偏高，可能晋升过于激进（建议<20%）")
    if active_ratio < 0.02 and exp_total > 10:
        alerts.append(f"⚠️ active_ratio={active_ratio:.1%} 偏低，可能晋升过于保守")

    report_lines = [
        f"# MindKernel 治理报告",
        f"- generated_at: {now_iso()}",
        f"- 新处理 decision traces: {len(traces)}",
        f"- 累计参数更新: {len(all_changes)}",
        "",
        "## MECD 状态快照",
        "",
        f"- Memory: active={mem_active} / candidate={mem_candidate}",
        f"- Experience: active={exp_active} / candidate={exp_candidate}",
        f"- active_ratio: {active_ratio:.1%}",
        f"- Experience 总量: {exp_total}",
        "",
        "## Decision traces 处理结果",
        f"- 本次处理: {len(traces)} 条",
        f"- 参数更新数: {len(all_changes)}",
    ]

    if alerts:
        report_lines.extend(["", "## 告警", ""])
        for a in alerts:
            report_lines.append(f"- {a}")

    report_lines.extend(["", status["report"]])

    report_path.write_text("\n".join(report_lines), encoding="utf-8")

    # 也写一个最新的符号链接
    latest = REPORTS_DIR / "governance_latest.md"
    latest.write_text("\n".join(report_lines), encoding="utf-8")

    result = {
        "ok": True,
        "new_traces": len(traces),
        "param_updates": len(all_changes),
        "experience": exp_stats,
        "memory": mem_stats,
        "active_ratio": active_ratio,
        "report_path": str(report_path),
        "alerts": alerts,
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="MindKernel 治理引擎")
    parser.add_argument("--once", action="store_true", help="单次运行（适合 cron）")
    parser.add_argument("--poll", action="store_true", help="持续轮询模式")
    parser.add_argument("--interval", type=int, default=3600, help="轮询间隔秒数（默认3600=1小时）")
    args = parser.parse_args()

    if args.poll:
        import time
        print(f"[governance] polling mode, interval={args.interval}s")
        while True:
            run_governance_cycle()
            time.sleep(args.interval)
    else:
        run_governance_cycle()


if __name__ == "__main__":
    main()
