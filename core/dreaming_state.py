#!/usr/bin/env python3
"""
Dreaming State — 做梦调度器状态管理

管理做梦触发器的状态：
- last_run_date / last_run_at：上次运行时间
- last_session_id：上次 session ID（用于幂等）
- consecutive_failures：连续失败计数
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_FILE = ROOT / "data" / "dreaming_state.json"

logger = logging.getLogger("dreaming.state")

# ── 触发条件配置 ──────────────────────────────────────────────────────────

TRIGGER_CONFIG = {
    "time_window_start": 1,   # 凌晨 1:00
    "time_window_end": 5,     # 凌晨 5:00
    "min_interval_hours": 20,
    "max_daily_attempts": 1,
    "max_session_duration_seconds": 300,
}


def _tz_now():
    return datetime.now(timezone(timedelta(hours=8)))


def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {
        "last_run_date": None,
        "last_run_at": None,
        "last_session_id": None,
        "consecutive_failures": 0,
    }


def _save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def should_run() -> tuple[bool, str]:
    """
    判断是否应该触发做梦。
    返回 (是否应该运行, 原因字符串)
    """
    state = _load_state()
    now = _tz_now()
    current_hour = now.hour

    # 1. 时间窗口检查
    in_window = TRIGGER_CONFIG["time_window_start"] <= current_hour < TRIGGER_CONFIG["time_window_end"]
    if not in_window:
        return False, f"不在触发窗口（当前 {current_hour}:00，窗口 {TRIGGER_CONFIG['time_window_start']}:00-{TRIGGER_CONFIG['time_window_end']}:00）"

    # 2. 每日限制
    today = now.date().isoformat()
    if state.get("last_run_date") == today:
        return False, f"今日（{today}）已运行过，跳过"

    # 3. 间隔检查
    last_run = state.get("last_run_at")
    if last_run:
        try:
            last_dt = datetime.fromisoformat(last_run)
            gap_hours = (now - last_dt).total_seconds() / 3600
            if gap_hours < TRIGGER_CONFIG["min_interval_hours"]:
                return False, f"距上次运行仅 {gap_hours:.1f}h，需 ≥{TRIGGER_CONFIG['min_interval_hours']}h"
        except Exception:
            pass

    return True, "触发条件满足"


def mark_run(session_id: str, success: bool = True) -> None:
    """标记本次运行"""
    state = _load_state()
    now = _tz_now()

    state["last_run_date"] = now.date().isoformat()
    state["last_run_at"] = now.isoformat()
    state["last_session_id"] = session_id

    if success:
        state["consecutive_failures"] = 0
    else:
        state["consecutive_failures"] = state.get("consecutive_failures", 0) + 1

    _save_state(state)
    logger.info(f"[DreamingState] 标记运行: session={session_id}, success={success}")


def get_state() -> dict:
    return _load_state()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    should, reason = should_run()
    print(f"should_run={should}, reason={reason}")
    print(f"state={json.dumps(_load_state(), indent=2)}")
