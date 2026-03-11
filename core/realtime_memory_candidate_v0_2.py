"""MindKernel v0.2 realtime memory candidate extractor (D3)."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta, timezone

HIGH_RISK_PATTERNS = [
    r"\b(delete|wipe|erase)\s+(all|everything|all data|the file|files?)\b",
    r"\boverwrite\s+(all|everything|the file|files?)\b",
    r"\breset all\b",
    r"(删除|清空)(全部|所有)?(文件|目录|数据)",
    r"覆盖(文件|全部|所有内容)",
    r"重置全部|抹掉(全部|所有)?(数据|记录)?",
]
MEDIUM_RISK_PATTERNS = [
    r"\b(todo|deadline|remind|follow[- ]?up|plan)\b",
    r"待办|截止|提醒|计划|下周|记住|记一下|跟进",
]

MEMORY_SIGNAL_PATTERNS = [
    r"\b(remember|preference|always|never)\b",
    r"记住|偏好|习惯|长期",
]

# system/control envelopes that should not be treated as normal memory facts
SYSTEM_NOISE_PATTERNS = [
    r"^\s*pre-compaction memory flush",
    r"\[system message\]",
    r'a cron job ".*" just completed successfully',
    r"^\s*system:\s*\[",
]

# explicit negations that should down-rank overwrite/delete keywords
HIGH_RISK_NEGATIONS = [
    r"\b(do not|don't|never)\s+(delete|overwrite|wipe|erase)\b",
    r"不要(删除|覆盖|清空|重置)",
    r"禁止(删除|覆盖|清空|重置)",
]

ACK_ONLY_PATTERNS = [
    r"^(好的|好|收到|明白|了解|ok|okay|yes|继续|继续推进|可以|行)$",
]

TIME_PREFIX_RE = re.compile(r"^\[[A-Za-z]{3}\s+\d{4}-\d{2}-\d{2}[^\]]*\]\s*")
SESSION_ID_RE = re.compile(r"\[sessionid:\s*[0-9a-f\-]{8,}\]", re.IGNORECASE)
UUID_RE = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE)
WHITESPACE_RE = re.compile(r"\s+")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def in_seconds_iso(sec: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=max(0, int(sec)))).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _has_any(patterns: list[str], text: str) -> bool:
    if not text:
        return False
    return any(re.search(p, text, flags=re.IGNORECASE) for p in patterns)


def _strip_chat_time_prefix(text: str) -> str:
    if not text:
        return ""
    return TIME_PREFIX_RE.sub("", text.strip())


def is_system_noise_text(text: str) -> bool:
    if not text:
        return False
    return _has_any(SYSTEM_NOISE_PATTERNS, text)


def is_workflow_ack_text(text: str) -> bool:
    t = _strip_chat_time_prefix(text).strip().lower()
    if not t:
        return False
    return _has_any(ACK_ONLY_PATTERNS, t)


def temporal_signature_text(text: str) -> str:
    """Normalize text into a stable signature for time-window repeat counting."""
    t = (text or "").lower().strip()
    t = TIME_PREFIX_RE.sub("", t)
    t = SESSION_ID_RE.sub("[session]", t)
    t = UUID_RE.sub("[uuid]", t)
    t = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", "[date]", t)
    t = re.sub(r"\b\d{1,2}:\d{2}(?::\d{2})?\b", "[time]", t)
    t = re.sub(r"\b\d+\b", "[num]", t)
    t = WHITESPACE_RE.sub(" ", t).strip()
    if len(t) > 240:
        t = t[:240]
    return t or "[empty]"


def infer_risk(text: str) -> tuple[int, str, list[str]]:
    reasons: list[str] = []

    # 系统噪音直接返回低风险
    if is_system_noise_text(text):
        reasons.append("SYSTEM_NOISE")
        return 12, "low", reasons

    # 系统消息（非噪音）也返回低风险 - 系统性问题不代表高风险
    if is_system_message_text(text):
        reasons.append("SYSTEM_MESSAGE")
        return 12, "low", reasons

    high_hit = _has_any(HIGH_RISK_PATTERNS, text)
    high_negated = _has_any(HIGH_RISK_NEGATIONS, text)
    if high_hit and not high_negated:
        reasons.append("HIGH_RISK_PATTERN")
        return 82, "high", reasons
    if high_hit and high_negated:
        reasons.append("HIGH_RISK_NEGATED")
        return 28, "low", reasons

    if _has_any(MEDIUM_RISK_PATTERNS, text):
        reasons.append("MEDIUM_RISK_PATTERN")
        return 56, "medium", reasons

    reasons.append("DEFAULT_LOW")
    return 25, "low", reasons


# 识别系统消息的模式（用于降风险）
SYSTEM_MESSAGE_PATTERNS = [
    r"^System:",
    r"^\[system\]",
    r"^系统:",
    r"Gateway restart",
    r"config-patch",
    r"Pre-compaction",
    r"memory flush",
]


def is_system_message_text(text: str) -> bool:
    """识别系统消息（非用户主观内容）"""
    if not text:
        return False
    return _has_any(SYSTEM_MESSAGE_PATTERNS, text)


# 识别记忆价值信号：主题/结果/产出物
MEMORY_ASSET_PATTERNS = [
    r"完成|完成",
    r"创建|新建|生成",
    r"修改|更新|编辑",
    r"提交|commit|push",
    r"测试|验证|验证",
    r"报告|总结|摘要",
    r"解决|修复|fix",
    r"部署|deploy",
    r"配置|配置|setting",
    r"学习|记住|记住",
    r"决定|决策|选择",
]


def infer_value_score(text: str, role: str) -> int:
    # 基础分：用户消息更高
    base = 30 if role == "user" else 5
    
    # 系统消息直接降为最低价值
    if is_system_message_text(text):
        return 5
    
    # 用户消息中的记忆价值信号
    if _has_any(MEMORY_SIGNAL_PATTERNS, text):
        base += 25
    
    # 主题/结果/asset 信号
    if _has_any(MEMORY_ASSET_PATTERNS, text):
        base += 30
    
    return min(100, base)


def _priority_from_risk_level(level: str) -> str:
    if level == "high":
        return "high"
    if level == "medium":
        return "medium"
    return "low"


def _stable_hash(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def extract_candidates(
    ev: dict,
    *,
    min_content_len: int = 6,
    max_candidates: int = 1,
    include_system: bool = True,
) -> list[dict]:
    """Extract realtime candidates from normalized event.

    D3 policy (minimal):
    - focus on user events
    - support system events for error/alert monitoring
    - require non-empty content and min length
    - one candidate per event by default
    - system/control envelopes are handled separately by daemon temporal logic
    """

    role = str(ev.get("role") or "")
    text = str(ev.get("content") or "").strip()
    # Support user events + system events (for error monitoring)
    if role == "user":
        pass  # user events always OK
    elif role == "system" and include_system:
        pass  # system events OK if enabled
    else:
        return []
    if len(text) < max(1, int(min_content_len)):
        return []
    if is_system_noise_text(text):
        return []

    risk_score, risk_level, reasons = infer_risk(text)
    # Boost value_score for system error events
    value_score = infer_value_score(text, role)
    if role == "system" and any(kw in text.lower() for kw in ["错误", "error", "失败", "fail", "invalid", "不支持"]):
        value_score = min(100, value_score + 30)

    seed = f"{ev.get('session_id')}|{ev.get('turn_id')}|{ev.get('event_id')}|{text}"
    h = _stable_hash(seed)
    candidate_id = f"cand_{h[:12]}"
    object_id = f"rt_reflect_{ev.get('session_id','s')}_{ev.get('turn_id','t')}_{h[:8]}"
    idem = f"rtmem:{ev.get('session_id','s')}:{ev.get('turn_id','t')}:{h[:16]}"

    candidate = {
        "candidate_id": candidate_id,
        "event_id": ev.get("event_id"),
        "session_id": ev.get("session_id"),
        "turn_id": ev.get("turn_id"),
        "role": role,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "value_score": value_score,
        "reason_codes": reasons,
        "summary": text[:200],
        "created_at": now_iso(),
        "idempotency_key": idem,
        "scheduler_job": {
            "object_type": "reflect_job",
            "object_id": object_id,
            "action": "reflect",
            "run_at": in_seconds_iso(1),
            "priority": _priority_from_risk_level(risk_level),
            "max_attempts": 3,
            "idempotency_key": idem,
            "correlation_id": f"daemon_v0_2:{ev.get('session_id')}:{ev.get('turn_id')}",
        },
    }

    return [candidate][: max(1, int(max_candidates))]
