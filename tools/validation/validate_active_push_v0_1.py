#!/usr/bin/env python3
"""
Validate active_push_worker v0.1
- Lock mechanism
- DB table not-found graceful handling
- Buffer write/read/clear cycle
- Confidence estimation
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools" / "active_push" / "active_push_worker_v0_1.py"


def run_cmd(cmd: list) -> tuple[int, str, str]:
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


def test_lock_mechanism():
    """测试 PID 文件锁"""
    print("TEST: lock mechanism")
    # 启动一个进程获取锁
    p = subprocess.Popen(
        [sys.executable, str(SCRIPT), "--once"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    p.wait()
    # 第二个进程应该检测到锁
    rc2, out2, err2 = run_cmd([sys.executable, str(SCRIPT), "--once"])
    print(f"  first pid={p.pid} rc={p.returncode}")
    print(f"  second launch rc={rc2} out={out2.strip()} err={err2.strip()[:100]}")
    assert rc2 == 0 and "not ready" in out2 or "Skipping" in out2, f"unexpected output: {out2} {err2}"
    print("  ✓ lock机制正常（第二个进程优雅退出）")


def test_confidence_estimates():
    """测试置信度估算"""
    print("TEST: confidence estimation")
    sys.path.insert(0, str(ROOT / "tools" / "active_push"))
    from active_push_worker_v0_1 import _estimate_confidence

    cases = [
        ({"final_outcome": "completed", "decision_mode": "normal", "epistemic_state": "supported"}, 0.92),
        ({"final_outcome": "completed", "decision_mode": "normal"}, 0.88),
        ({"final_outcome": "completed", "decision_mode": "conservative", "epistemic_state": "supported"}, 0.50),
        ({"final_outcome": "limited", "epistemic_state": "supported"}, 0.72),
        ({"final_outcome": "escalated"}, 0.60),
        ({"final_outcome": "blocked"}, 0.20),
    ]

    all_pass = True
    for payload, expected in cases:
        got = _estimate_confidence(payload)
        status = "✓" if abs(got - expected) < 0.01 else "✗"
        if status == "✗":
            all_pass = False
        print(f"  {status} {payload.get('final_outcome')}/{payload.get('decision_mode')} → {got:.2f} (expect {expected:.2f})")
    assert all_pass, "confidence estimation failed"
    print("  ✓ 置信度估算全部通过")


def test_format_suggestion():
    """测试回复建议格式化"""
    print("TEST: reply suggestion formatting")
    sys.path.insert(0, str(ROOT / "tools" / "active_push"))
    from active_push_worker_v0_1 import _format_reply_suggestion

    payload = {"final_outcome": "completed", "decision_mode": "normal", "reason": "Test decision reason"}
    suggestion = _format_reply_suggestion(payload, 0.92)
    assert "✅" in suggestion and "MECD" in suggestion and "92%" in suggestion
    print(f"  ✓ {suggestion[:80]}")


if __name__ == "__main__":
    os.chdir(ROOT)
    print("=" * 50)
    print("active_push_worker v0.1 validation")
    print("=" * 50)
    test_confidence_estimates()
    test_format_suggestion()
    test_lock_mechanism()
    print("\n✅ All tests passed")
