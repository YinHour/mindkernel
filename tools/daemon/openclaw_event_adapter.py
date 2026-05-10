#!/usr/bin/env python3
"""
OpenClaw Session → MindKernel Daemon 事件适配器

读取 OpenClaw transcript JSONL，将每条 user/assistant 消息
转换为 daemon 期望的 event 格式，写入 daemon events JSONL。

Usage:
  python3 openclaw_event_adapter.py [--once | --poll]

配合 cron 使用（--once，每5分钟跑一次），
或作为独立 daemon 运行（--poll，每30秒轮询）。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

DEFAULT_TRANSCRIPT_DIR = Path.home() / ".openclaw" / "agents" / "main" / "sessions"
DEFAULT_OUTPUT_EVENTS = ROOT / "data" / "fixtures" / "daemon_events_openclaw.jsonl"
CHECKPOINT_FILE = ROOT / "data" / "daemon" / "openclaw_adapter_checkpoint.json"
PYTHON = "/opt/homebrew/bin/python3"

# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_checkpoint() -> dict:
    if CHECKPOINT_FILE.exists():
        return json.loads(CHECKPOINT_FILE.read_text())
    return {"last_event_id": "", "last_ts": ""}


def save_checkpoint(cp: dict):
    CHECKPOINT_FILE.write_text(json.dumps(cp, ensure_ascii=False, indent=2))


# ── AI Internal Content Filter ─────────────────────────────────────────────────
# 过滤规则：以下内容不应作为独立记忆条目保留

# 完全跳过：无意义系统噪音
SKIP_PATTERNS = [
    "HEARTBEAT_OK",
    "NO_REPLY",
    "heartbeat poll",
    "[OpenClaw heartbeat",
    "``` Sender",
    "conversation_id",
    "reply_to_current",
    "tool_result", "tool result",
]

# 跳过以这些开头的行（格式标记）
SKIP_PREFIXES = (
    "MEDIA:",
    "[[reply_to",
    "[[audio",
    "[embed ",
    "<!-- OPENCLAW",
)

# AI 内部推理关键词
AI_INTERNAL_KEYWORDS = [
    "tool_call", "tool_result", "tool_use",
    "function_call", "invoke", "parameters:",
    "FCP:", "FSM:", "STATE:", "ACT:",
    "Commit:", "commit ", "git commit", "git add",
    "Traceback", "Error:", "Exception:",
    "正在执行", "执行结果", "调用成功",
    "→ ", "✓ ", "✗ ", "❌ ",
]


def is_ai_internal_content(text: str) -> bool:
    """判断文本是否为 AI 内部推理内容（不应作为独立记忆）。"""
    if not text or len(text.strip()) < 3:
        return True
    t = text.strip()

    # 完全跳过模式
    t_lower = t.lower()
    for pat in SKIP_PATTERNS:
        if pat.lower() in t_lower:
            return True

    # 前缀跳过
    if t_lower.startswith(SKIP_PREFIXES):
        return True

    # 心跳系统消息
    if t.startswith("[") and ("GMT+" in t_lower or "GMT-" in t_lower or "UTC" in t_lower) and ("heartbeat" in t.lower() or "HEARTBEAT" in t.upper()):
        return True

    # JSON-like 系统元数据行
    if t.startswith("{") and t.endswith("}") and len(t) < 500:
        try:
            import json
            json.loads(t)
            return True
        except Exception:
            pass

    # 纯英文单行系统信息
    if len(t) < 100 and any(t_lower.startswith(kw) for kw in ["NO_REPLY", "HEARTBEAT", "heartbeat"]):
        return True

    # AI 内部推理标记
    lower_t = t.lower()
    for kw in AI_INTERNAL_KEYWORDS:
        if kw.lower() in lower_t:
            # 有中文句子的长消息放行
            if len(t) > 60 and any(c in t for c in "，。！？…"):
                continue
            return True

    # 重复确认词（极短消息）
    if t in ("好", "好的", "可以", "行", "嗯", "ok", "OK", "收到", "👍", "✅"):
        return True

    return False

def extract_text(content) -> str:
    """从 OpenClaw message content 提取纯文本（仅 user-facing 可见内容）。"""
    if isinstance(content, list):
        parts = []
        for c in content:
            if isinstance(c, dict) and c.get("type") == "text":
                parts.append(c.get("text", ""))
        raw = " ".join(parts)
    elif isinstance(content, str):
        raw = content
    else:
        return ""

    # 清理 Telegram metadata 包装
    parts = raw.split("```")
    if len(parts) >= 2:
        candidate = parts[-1].strip()
        if candidate.startswith("Sender"):
            candidate = candidate.split("Sender", 1)[-1].strip()
        try:
            json.loads(candidate)
            candidate = ""
        except (json.JSONDecodeError, ValueError):
            pass
        if candidate:
            return candidate.strip()

    for line in raw.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            json.loads(stripped)
            continue
        except (json.JSONDecodeError, ValueError):
            pass
        if any(kw in stripped for kw in ["Conversation info", "Sender", "message_id", "timestamp"]):
            continue
        return stripped
    return ""


def transcript_to_events(transcript_path: str, session_id: str) -> list[dict]:
    """从 transcript JSONL 读取所有消息，转换为 daemon 事件。"""
    events = []
    try:
        with open(transcript_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if obj.get("type") != "message":
                    continue
                msg = obj.get("message", {})
                role = msg.get("role", "")
                if role not in ("user", "assistant", "system"):
                    continue
                ts = obj.get("timestamp", "")
                content = extract_text(msg.get("content", []))
                if not content:
                    continue
                # 过滤 AI 内部推理内容
                if role == "assistant" and is_ai_internal_content(content):
                    continue
                event_id = f"oc_{obj.get('id', '')}" or None
                if not event_id or event_id == "oc_":
                    seed = f"{session_id}|{role}|{content[:80]}|{ts}"
                    import hashlib
                    event_id = f"oc_{hashlib.sha1(seed.encode()).hexdigest()[:12]}"
                events.append({
                    "event_id": event_id,
                    "session_id": session_id,
                    "turn_id": obj.get("id", ""),
                    "role": role,
                    "channel": "telegram",
                    "content": content,
                    "timestamp": ts,
                })
    except FileNotFoundError:
        pass
    return events


def get_latest_transcript() -> tuple[str | None, str | None]:
    """通过 /tools/invoke 获取最新 transcript 路径。"""
    import urllib.request
    cfg = json.loads((Path.home() / ".openclaw" / "openclaw.json").read_text())
    token = cfg["gateway"]["auth"]["token"]
    port = cfg["gateway"]["port"]
    payload = json.dumps({"tool": "sessions_list", "args": {"limit": 5}}).encode()
    req = urllib.request.Request(
        "http://localhost:" + str(port) + "/tools/invoke",
        data=payload,
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
            sessions = data.get("result", {}).get("content", [])
            if not sessions:
                return None, None
            sessions_text = sessions[0].get("text", "{}")
            sessions_data = json.loads(sessions_text)
            session_list = sessions_data.get("sessions", [])
            if not session_list:
                return None, None
            s = session_list[0]
            return s.get("transcriptPath"), s.get("key", "openclaw-session")
    except Exception:
        pass
    return None, None


def write_events(events: list[dict], output_path: Path):
    """追加写入 events JSONL。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "a") as f:
        for ev in events:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")


def run_once(poll_interval: int = 0):
    """单次运行：读取 transcript，写入 events。"""
    checkpoint = load_checkpoint()
    last_event_id = checkpoint.get("last_event_id", "")

    transcript_path, session_id = get_latest_transcript()
    if not transcript_path:
        print("[adapter] could not get transcript path")
        return

    events = transcript_to_events(transcript_path, session_id or "openclaw-session")
    if not events:
        print("[adapter] no new events")
        return

    # 去重：跳过 last_event_id 之前的
    if last_event_id:
        seen_last = False
        new_events = []
        for ev in events:
            if ev["event_id"] == last_event_id:
                seen_last = True
                continue
            if seen_last:
                new_events.append(ev)
        events = new_events

    if not events:
        print("[adapter] no new events after dedup")
        return

    write_events(events, DEFAULT_OUTPUT_EVENTS)

    # 更新 checkpoint
    save_checkpoint({
        "last_event_id": events[-1]["event_id"],
        "last_ts": events[-1]["timestamp"],
        "transcript_path": transcript_path,
    })
    print(f"[adapter] wrote {len(events)} events to {DEFAULT_OUTPUT_EVENTS}")


def run_poll(interval: int = 30):
    """持续轮询模式（daemon 风格）。"""
    print(f"[adapter] polling mode, interval={interval}s")
    while True:
        run_once()
        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description="OpenClaw → MindKernel Daemon 事件适配器")
    parser.add_argument("--once", action="store_true", help="单次运行后退出")
    parser.add_argument("--poll", action="store_true", help="持续轮询模式")
    parser.add_argument("--interval", type=int, default=30, help="轮询间隔秒数（默认30）")
    args = parser.parse_args()

    if args.poll:
        run_poll(args.interval)
    else:
        run_once()


if __name__ == "__main__":
    main()
