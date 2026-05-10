#!/usr/bin/env python3
"""
Dreaming Scheduler — 做梦调度器

启动条件检查 + 触发 dreaming_worker。
可通过两种方式触发：
1. launchd 每日凌晨 01:30 定时触发
2. 手动运行：`python dreaming_scheduler.py`
"""

from __future__ import annotations

import logging
import subprocess
import sys
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKER_SCRIPT = ROOT / "core" / "dreaming_worker.py"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(ROOT / "logs" / "dreaming_scheduler.log"),
    ],
)
logger = logging.getLogger("dreaming.scheduler")

# 延迟导入
from core.dreaming_state import should_run, mark_run


def trigger_worker(session_id: str) -> None:
    """通过 subprocess 触发 worker"""
    logger.info(f"[Scheduler] 触发 worker: {session_id}")

    env = {
        "PATH": "/usr/local/bin:/usr/bin:/bin:/usr/local/bin",
    }

    result = subprocess.run(
        [
            sys.executable,
            str(WORKER_SCRIPT),
            "--session-id", session_id,
        ],
        capture_output=True,
        text=True,
        timeout=360,
        cwd=str(ROOT),
        env=dict(subprocess.os.environ.copy(), **env),
    )

    if result.returncode == 0:
        logger.info(f"[Scheduler] Worker 成功: {result.stdout[-500:]}")
        mark_run(session_id, success=True)
    else:
        logger.error(f"[Scheduler] Worker 失败: {result.stderr[-500:]}")
        mark_run(session_id, success=False)


def run() -> bool:
    """
    主入口：检查条件，满足则触发 worker。
    返回 True 表示触发了 worker。
    """
    should, reason = should_run()
    if not should:
        logger.info(f"[Scheduler] 未触发: {reason}")
        return False

    session_id = f"dream_{datetime.now(timezone(timedelta(hours=8))).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}"
    logger.info(f"[Scheduler] 触发做梦: {reason}, session_id={session_id}")

    try:
        trigger_worker(session_id)
        return True
    except Exception as e:
        logger.exception(f"[Scheduler] 触发失败: {e}")
        mark_run(session_id, success=False)
        return False


if __name__ == "__main__":
    ran = run()
    sys.exit(0 if ran else 1)
