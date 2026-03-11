#!/usr/bin/env python3
"""MindKernel v0.2 daemon prototype.

D1 (done):
- poll/tail skeleton, pid lock, graceful shutdown, checkpoint/recover

D2 (minimal):
- event normalization + dedupe + session-level throttle

D3 (minimal):
- realtime candidate extraction + scheduler enqueue (optional)

D4 (prototype-grade):
- batch metrics persisted for observability
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import sqlite3
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS_SCHED = ROOT / "tools" / "scheduler"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(TOOLS_SCHED) not in sys.path:
    sys.path.insert(0, str(TOOLS_SCHED))

import scheduler_v0_1 as sch  # noqa: E402
from core.event_normalizer_v0_2 import event_fingerprint, minute_bucket, normalize_event  # noqa: E402
from core.realtime_memory_candidate_v0_2 import (  # noqa: E402
    extract_candidates,
    is_system_noise_text,
    is_workflow_ack_text,
    temporal_signature_text,
)
from core.strategies import get_strategy, CandidateScore  # noqa: E402

DEFAULT_EVENTS_FILE = ROOT / "data" / "fixtures" / "daemon_events_v0_2.jsonl"
DEFAULT_STATE_DB = ROOT / "data" / "daemon" / "memory_observer_v0_2.sqlite"
DEFAULT_PID_FILE = ROOT / "data" / "daemon" / "memory_observer_v0_2.pid"

RISK_RANK = {"low": 1, "medium": 2, "high": 3}


@dataclass
class BatchResult:
    processed: int
    errors: int
    offset: int
    last_event_id: str | None
    normalized: int
    deduped_events: int
    candidates: int
    enqueued: int
    dedup_enqueues: int
    throttled: int
    skipped_hwm: int
    system_repeat_alerts: int
    ack_compressed: int
    ack_rollup_candidates: int


_STOP = False

# 阈值策略实例（延迟初始化）
_threshold_strategy = None


def _get_threshold_strategy():
    """获取阈值策略实例"""
    global _threshold_strategy
    if _threshold_strategy is None:
        _threshold_strategy = get_strategy("rule_based")
    return _threshold_strategy


def _apply_threshold_strategy(cand: dict) -> tuple[str, str]:
    """
    应用阈值策略决定候选状态
    
    Returns:
        (status, note): 状态和备注
    """
    strategy = _get_threshold_strategy()
    
    # 构造评分
    score = CandidateScore(
        risk_score=int(cand.get("risk_score", 25)),
        risk_level=str(cand.get("risk_level", "low")),
        value_score=int(cand.get("value_score", 20)),
        reason_codes=cand.get("reason_codes", []),
    )
    
    # 获取决策
    decision = strategy.decide(score)
    
    # 映射到状态
    status_map = {
        "auto_pool": "observed_only",  # 入观察池，等待后续处理
        "review_queue": "review_pending",  # 待审核
        "discard": "strategy_discarded",  # 策略决定丢弃
    }
    
    status = status_map.get(decision.action, "observed_only")
    return status, decision.note


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_iso(ts: str | None) -> datetime:
    v = str(ts or "").strip()
    if not v:
        return datetime.now(timezone.utc)
    try:
        if v.endswith("Z"):
            dt = datetime.fromisoformat(v[:-1] + "+00:00")
        else:
            dt = datetime.fromisoformat(v)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:  # noqa: BLE001
        return datetime.now(timezone.utc)


def _iso_minus_minutes(base_ts: str | None, minutes: int) -> str:
    dt = _parse_iso(base_ts) - timedelta(minutes=max(1, int(minutes)))
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _hash12(s: str) -> str:
    import hashlib

    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:12]


def _on_stop_signal(_signum: int, _frame):
    global _STOP
    _STOP = True


def install_signal_handlers():
    signal.signal(signal.SIGINT, _on_stop_signal)
    signal.signal(signal.SIGTERM, _on_stop_signal)


def ensure_parent(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)


def is_pid_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def acquire_pid_file(pid_file: Path):
    ensure_parent(pid_file)
    if pid_file.exists():
        raw = pid_file.read_text(encoding="utf-8", errors="ignore").strip()
        try:
            existing_pid = int(raw)
        except ValueError:
            existing_pid = -1

        if is_pid_running(existing_pid):
            raise RuntimeError(f"pid file locked by running process: pid={existing_pid}, pid_file={pid_file}")
        pid_file.unlink(missing_ok=True)

    pid_file.write_text(str(os.getpid()), encoding="utf-8")


def release_pid_file(pid_file: Path):
    try:
        if pid_file.exists():
            pid_file.unlink()
    except OSError:
        pass


def db_conn(db_path: Path) -> sqlite3.Connection:
    ensure_parent(db_path)
    c = sqlite3.connect(str(db_path))
    c.row_factory = sqlite3.Row
    return c


def init_db(c: sqlite3.Connection):
    c.executescript(
        """
        PRAGMA journal_mode=WAL;

        CREATE TABLE IF NOT EXISTS daemon_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            mode TEXT NOT NULL,
            events_file TEXT NOT NULL,
            offset INTEGER NOT NULL DEFAULT 0,
            processed_total INTEGER NOT NULL DEFAULT 0,
            last_event_id TEXT,
            started_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS daemon_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT,
            offset_start INTEGER NOT NULL,
            offset_end INTEGER NOT NULL,
            status TEXT NOT NULL,
            error TEXT,
            processed_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_daemon_audit_processed_at
        ON daemon_audit(processed_at DESC);

        CREATE TABLE IF NOT EXISTS daemon_seen (
            event_fingerprint TEXT PRIMARY KEY,
            event_id TEXT,
            session_id TEXT,
            turn_id TEXT,
            seen_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS daemon_candidates (
            idempotency_key TEXT PRIMARY KEY,
            candidate_id TEXT NOT NULL,
            event_id TEXT,
            session_id TEXT,
            turn_id TEXT,
            risk_level TEXT,
            risk_score INTEGER,
            value_score INTEGER,
            status TEXT NOT NULL,
            job_id TEXT,
            note TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_daemon_candidates_session
        ON daemon_candidates(session_id, created_at DESC);

        CREATE TABLE IF NOT EXISTS daemon_throttle (
            session_id TEXT NOT NULL,
            minute_bucket TEXT NOT NULL,
            count INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL,
            PRIMARY KEY(session_id, minute_bucket)
        );

        CREATE TABLE IF NOT EXISTS daemon_temporal_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_kind TEXT NOT NULL,
            signature TEXT NOT NULL,
            event_id TEXT,
            session_id TEXT,
            turn_id TEXT,
            observed_at TEXT NOT NULL,
            content_preview TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_daemon_temporal_signals_sig
        ON daemon_temporal_signals(signal_kind, signature, observed_at DESC);

        CREATE TABLE IF NOT EXISTS daemon_batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mode TEXT NOT NULL,
            started_at TEXT NOT NULL,
            ended_at TEXT NOT NULL,
            processed INTEGER NOT NULL,
            normalized INTEGER NOT NULL,
            deduped_events INTEGER NOT NULL,
            candidates INTEGER NOT NULL,
            enqueued INTEGER NOT NULL,
            dedup_enqueues INTEGER NOT NULL,
            throttled INTEGER NOT NULL,
            skipped_hwm INTEGER NOT NULL,
            errors INTEGER NOT NULL,
            offset INTEGER NOT NULL,
            system_repeat_alerts INTEGER NOT NULL DEFAULT 0,
            ack_compressed INTEGER NOT NULL DEFAULT 0,
            ack_rollup_candidates INTEGER NOT NULL DEFAULT 0
        );
        """
    )

    row = c.execute("SELECT id FROM daemon_state WHERE id=1").fetchone()
    if not row:
        ts = now_iso()
        c.execute(
            """
            INSERT INTO daemon_state(id, mode, events_file, offset, processed_total, last_event_id, started_at, updated_at)
            VALUES (1, 'poll', '', 0, 0, NULL, ?, ?)
            """,
            (ts, ts),
        )

    # lightweight migration for older daemon_batches schema
    batch_cols = {r["name"] for r in c.execute("PRAGMA table_info(daemon_batches)").fetchall()}
    if "system_repeat_alerts" not in batch_cols:
        c.execute("ALTER TABLE daemon_batches ADD COLUMN system_repeat_alerts INTEGER NOT NULL DEFAULT 0")
    if "ack_compressed" not in batch_cols:
        c.execute("ALTER TABLE daemon_batches ADD COLUMN ack_compressed INTEGER NOT NULL DEFAULT 0")
    if "ack_rollup_candidates" not in batch_cols:
        c.execute("ALTER TABLE daemon_batches ADD COLUMN ack_rollup_candidates INTEGER NOT NULL DEFAULT 0")

    c.commit()


def load_state(c: sqlite3.Connection) -> dict:
    row = c.execute(
        "SELECT mode, events_file, offset, processed_total, last_event_id, started_at, updated_at FROM daemon_state WHERE id=1"
    ).fetchone()
    if not row:
        raise RuntimeError("daemon_state missing")
    return {
        "mode": row["mode"],
        "events_file": row["events_file"],
        "offset": int(row["offset"]),
        "processed_total": int(row["processed_total"]),
        "last_event_id": row["last_event_id"],
        "started_at": row["started_at"],
        "updated_at": row["updated_at"],
    }


def save_state(
    c: sqlite3.Connection,
    *,
    mode: str,
    events_file: str,
    offset: int,
    processed_total: int,
    last_event_id: str | None,
):
    c.execute(
        """
        UPDATE daemon_state
        SET mode=?, events_file=?, offset=?, processed_total=?, last_event_id=?, updated_at=?
        WHERE id=1
        """,
        (mode, events_file, int(max(0, offset)), int(max(0, processed_total)), last_event_id, now_iso()),
    )
    c.commit()


def _event_id(payload: dict, fallback_offset: int) -> str:
    for k in ("event_id", "id", "turn_id"):
        v = payload.get(k)
        if v:
            return str(v)
    return f"evt_offset_{fallback_offset}"


def _seen_event(c: sqlite3.Connection, event_fp: str) -> bool:
    row = c.execute("SELECT event_fingerprint FROM daemon_seen WHERE event_fingerprint=?", (event_fp,)).fetchone()
    return bool(row)


def _mark_seen(c: sqlite3.Connection, event_fp: str, ev: dict):
    c.execute(
        """
        INSERT OR IGNORE INTO daemon_seen(event_fingerprint, event_id, session_id, turn_id, seen_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (event_fp, ev.get("event_id"), ev.get("session_id"), ev.get("turn_id"), now_iso()),
    )


def _throttle_count(c: sqlite3.Connection, session_id: str, bucket: str) -> int:
    row = c.execute(
        "SELECT count FROM daemon_throttle WHERE session_id=? AND minute_bucket=?",
        (session_id, bucket),
    ).fetchone()
    return int(row["count"]) if row else 0


def _throttle_inc(c: sqlite3.Connection, session_id: str, bucket: str):
    c.execute(
        """
        INSERT INTO daemon_throttle(session_id, minute_bucket, count, updated_at)
        VALUES (?, ?, 1, ?)
        ON CONFLICT(session_id, minute_bucket)
        DO UPDATE SET count=count+1, updated_at=excluded.updated_at
        """,
        (session_id, bucket, now_iso()),
    )


def _record_temporal_signal(c: sqlite3.Connection, *, signal_kind: str, signature: str, ev: dict):
    c.execute(
        """
        INSERT INTO daemon_temporal_signals(signal_kind, signature, event_id, session_id, turn_id, observed_at, content_preview)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            signal_kind,
            signature,
            str(ev.get("event_id") or ""),
            str(ev.get("session_id") or "session_unknown"),
            str(ev.get("turn_id") or ""),
            str(ev.get("timestamp") or now_iso()),
            str(ev.get("content") or "")[:200],
        ),
    )


def _count_recent_signals(
    c: sqlite3.Connection,
    *,
    signal_kind: str,
    signature: str,
    since_ts_iso: str,
) -> int:
    row = c.execute(
        """
        SELECT COUNT(1) AS n
        FROM daemon_temporal_signals
        WHERE signal_kind=? AND signature=? AND observed_at>=?
        """,
        (signal_kind, signature, since_ts_iso),
    ).fetchone()
    return int(row["n"]) if row else 0


def _candidate_upsert(c: sqlite3.Connection, cand: dict, *, status: str, job_id: str | None = None, note: str | None = None):
    t = now_iso()
    c.execute(
        """
        INSERT INTO daemon_candidates(
            idempotency_key, candidate_id, event_id, session_id, turn_id,
            risk_level, risk_score, value_score, status, job_id, note, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(idempotency_key) DO UPDATE SET
            status=excluded.status,
            job_id=excluded.job_id,
            note=excluded.note,
            updated_at=excluded.updated_at
        """,
        (
            cand.get("idempotency_key"),
            cand.get("candidate_id"),
            cand.get("event_id"),
            cand.get("session_id"),
            cand.get("turn_id"),
            cand.get("risk_level"),
            int(cand.get("risk_score") or 0),
            int(cand.get("value_score") or 0),
            status,
            job_id,
            note,
            t,
            t,
        ),
    )


def _risk_meets_min(cand: dict, min_level: str) -> bool:
    return RISK_RANK.get(str(cand.get("risk_level") or "low"), 1) >= RISK_RANK.get(min_level, 1)


def _load_allowlist(path: Path | None) -> set[str]:
    if path is None:
        return set()
    if not path.exists():
        return set()
    out: set[str] = set()
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        v = line.strip()
        if not v or v.startswith("#"):
            continue
        out.add(v)
    return out


def process_batch(
    c: sqlite3.Connection,
    *,
    mode: str,
    events_file: Path,
    offset: int,
    processed_total: int,
    max_batch: int,
    last_event_id: str | None,
    verbose: bool,
    scheduler_conn: sqlite3.Connection | None,
    enqueue_enabled: bool,
    feature_flag: str,
    partial_session_allowlist: set[str],
    session_rate_limit_per_min: int,
    scheduler_queue_high_watermark: int,
    enqueue_min_risk_level: str,
    max_candidates_per_event: int,
    system_repeat_window_min: int,
    system_repeat_threshold: int,
    ack_window_min: int,
    ack_rollup_every: int,
) -> BatchResult:
    if mode not in {"poll", "tail"}:
        raise ValueError(f"unsupported mode: {mode}")

    ensure_parent(events_file)
    if not events_file.exists():
        events_file.write_text("", encoding="utf-8")

    processed = 0
    errors = 0
    normalized = 0
    deduped_events = 0
    candidates = 0
    enqueued = 0
    dedup_enqueues = 0
    throttled = 0
    skipped_hwm = 0
    system_repeat_alerts = 0
    ack_compressed = 0
    ack_rollup_candidates = 0

    scheduler_queued_cache: int | None = None

    with events_file.open("rb") as f:
        file_size = events_file.stat().st_size
        if offset > file_size:
            offset = 0

        f.seek(offset)

        while processed < max_batch and not _STOP:
            start = f.tell()
            line = f.readline()
            if not line:
                break
            end = f.tell()
            stripped = line.strip()
            if not stripped:
                offset = end
                continue

            status = "ok"
            err = None
            event_id = None

            try:
                payload = json.loads(stripped.decode("utf-8", errors="replace"))
                event_id = _event_id(payload, end)

                ev = normalize_event(payload)
                normalized += 1
                processed += 1
                processed_total += 1
                last_event_id = ev.get("event_id") or event_id

                fp = event_fingerprint(ev)
                if _seen_event(c, fp):
                    deduped_events += 1
                    status = "deduped_event"
                    if verbose:
                        print(f"[daemon] dedup event_id={event_id} offset={start}->{end}", file=sys.stderr)
                else:
                    _mark_seen(c, fp, ev)

                    ev_text = str(ev.get("content") or "")
                    ev_ts = str(ev.get("timestamp") or now_iso())
                    ev_candidates: list[dict] = []

                    # time-dimension channel A:
                    # repeated system/control envelopes => high-risk system anomaly signal
                    if str(ev.get("role") or "") == "user" and is_system_noise_text(ev_text):
                        sig = temporal_signature_text(ev_text)
                        _record_temporal_signal(c, signal_kind="system_signal", signature=sig, ev=ev)
                        repeat_in_window = _count_recent_signals(
                            c,
                            signal_kind="system_signal",
                            signature=sig,
                            since_ts_iso=_iso_minus_minutes(ev_ts, system_repeat_window_min),
                        )
                        repeat_24h = _count_recent_signals(
                            c,
                            signal_kind="system_signal",
                            signature=sig,
                            since_ts_iso=_iso_minus_minutes(ev_ts, 24 * 60),
                        )
                        status = "system_signal_observed"

                        if repeat_in_window >= max(1, int(system_repeat_threshold)):
                            sig_hash = _hash12(sig)
                            hour_bucket = _parse_iso(ev_ts).strftime("%Y%m%d%H")
                            idem = f"rtmem:system-repeat:{sig_hash}:{hour_bucket}"
                            # 系统重复信号 = 系统稳定性指标，不是"高风险"
                            # 按新策略：系统性问题不代表高风险
                            level = "low"
                            score = 15  # 系统信号低风险
                            cand = {
                                "candidate_id": f"cand_sysrep_{_hash12(idem)}",
                                "event_id": ev.get("event_id"),
                                "session_id": ev.get("session_id"),
                                "turn_id": ev.get("turn_id"),
                                "role": ev.get("role"),
                                "risk_score": score,
                                "risk_level": level,
                                "value_score": 10,  # 系统信号低价值
                                "reason_codes": ["SYSTEM_REPEAT_ALERT"],
                                "summary": f"系统提示重复(稳定性指标): sig={sig_hash}, window={system_repeat_window_min}m repeat={repeat_in_window}, repeat_24h={repeat_24h}",
                                "created_at": now_iso(),
                                "idempotency_key": idem,
                                "scheduler_job": {
                                    "object_type": "reflect_job",
                                    "object_id": f"rt_system_repeat_{sig_hash}_{hour_bucket}",
                                    "action": "reflect",
                                    "run_at": now_iso(),
                                    "priority": "low",  # 降低优先级
                                    "max_attempts": 3,
                                    "idempotency_key": idem,
                                    "correlation_id": f"daemon_v0_2:system_repeat:{sig_hash}",
                                },
                            }
                            ev_candidates.append(cand)
                            system_repeat_alerts += 1

                    # time-dimension channel B:
                    # workflow ACK tokens are compressed; emit periodic rollup summary only
                    elif str(ev.get("role") or "") == "user" and is_workflow_ack_text(ev_text):
                        sig = f"{ev.get('session_id') or 'session_unknown'}::{temporal_signature_text(ev_text)}"
                        _record_temporal_signal(c, signal_kind="workflow_ack", signature=sig, ev=ev)
                        ack_count = _count_recent_signals(
                            c,
                            signal_kind="workflow_ack",
                            signature=sig,
                            since_ts_iso=_iso_minus_minutes(ev_ts, ack_window_min),
                        )
                        status = "ack_compressed"
                        if ack_count % max(1, int(ack_rollup_every)) == 0:
                            sig_hash = _hash12(sig)
                            tag = _parse_iso(ev_ts).strftime("%Y%m%d%H")
                            idem = f"rtmem:ack-rollup:{sig_hash}:{tag}:{ack_count}"
                            cand = {
                                "candidate_id": f"cand_ack_{_hash12(idem)}",
                                "event_id": ev.get("event_id"),
                                "session_id": ev.get("session_id"),
                                "turn_id": ev.get("turn_id"),
                                "role": ev.get("role"),
                                "risk_score": 22,
                                "risk_level": "low",
                                "value_score": 30,
                                "reason_codes": ["ACK_ROLLUP"],
                                "summary": f"工作流确认信号压缩: {ack_window_min}m 内 ack={ack_count}",
                                "created_at": now_iso(),
                                "idempotency_key": idem,
                                "scheduler_job": {
                                    "object_type": "reflect_job",
                                    "object_id": f"rt_ack_rollup_{sig_hash}_{tag}",
                                    "action": "reflect",
                                    "run_at": now_iso(),
                                    "priority": "low",
                                    "max_attempts": 2,
                                    "idempotency_key": idem,
                                    "correlation_id": f"daemon_v0_2:ack_rollup:{sig_hash}",
                                },
                            }
                            ev_candidates.append(cand)
                            ack_rollup_candidates += 1
                        else:
                            ack_compressed += 1

                    else:
                        ev_candidates = extract_candidates(ev, min_content_len=6, max_candidates=max_candidates_per_event)

                    candidates += len(ev_candidates)

                    for cand in ev_candidates:
                        sess = str(cand.get("session_id") or "session_unknown")
                        bucket = minute_bucket(str(ev.get("timestamp") or now_iso()))
                        cnt = _throttle_count(c, sess, bucket)
                        if cnt >= max(1, int(session_rate_limit_per_min)):
                            throttled += 1
                            _candidate_upsert(c, cand, status="throttled", note=f"session_rate_limit:{session_rate_limit_per_min}")
                            continue

                        # candidate accepted into throttle budget
                        _throttle_inc(c, sess, bucket)

                        # D5 runtime flag gate
                        # off: observe only, no enqueue
                        # shadow: extract + metrics only, no enqueue
                        # partial: enqueue only for allowlisted sessions
                        # on: enqueue for all sessions
                        sess_id = str(cand.get("session_id") or "session_unknown")
                        
                        # 应用阈值策略
                        strategy_status, strategy_note = _apply_threshold_strategy(cand)
                        if strategy_status == "strategy_discarded":
                            # 策略决定丢弃
                            _candidate_upsert(c, cand, status="strategy_discarded", note=strategy_note)
                            continue
                        
                        if feature_flag == "off":
                            _candidate_upsert(c, cand, status="feature_flag_off")
                            continue
                        if feature_flag == "shadow":
                            _candidate_upsert(c, cand, status="shadow_only")
                            continue
                        if feature_flag == "partial" and sess_id not in partial_session_allowlist:
                            _candidate_upsert(c, cand, status="partial_skip")
                            continue

                        if not enqueue_enabled or scheduler_conn is None:
                            _candidate_upsert(c, cand, status="observed_only")
                            continue
                        if not _risk_meets_min(cand, enqueue_min_risk_level):
                            _candidate_upsert(c, cand, status="risk_filtered", note=f"min_risk={enqueue_min_risk_level}")
                            continue

                        if scheduler_queued_cache is None:
                            st = sch.stats(scheduler_conn)
                            scheduler_queued_cache = int(st.get("queued", 0))

                        risk_level = str(cand.get("risk_level") or "low")
                        if scheduler_queued_cache >= int(scheduler_queue_high_watermark) and RISK_RANK.get(risk_level, 1) < RISK_RANK["high"]:
                            skipped_hwm += 1
                            _candidate_upsert(
                                c,
                                cand,
                                status="skipped_high_watermark",
                                note=f"queued={scheduler_queued_cache} hwm={scheduler_queue_high_watermark}",
                            )
                            continue

                        job = cand.get("scheduler_job") or {}
                        r = sch.enqueue(
                            scheduler_conn,
                            object_type=str(job.get("object_type") or "reflect_job"),
                            object_id=str(job.get("object_id") or f"rt_reflect_{cand.get('candidate_id')}") ,
                            action=str(job.get("action") or "reflect"),
                            run_at=str(job.get("run_at") or now_iso()),
                            priority=str(job.get("priority") or "medium"),
                            max_attempts=int(job.get("max_attempts") or 3),
                            idempotency_key=str(job.get("idempotency_key") or cand.get("idempotency_key")),
                            correlation_id=str(job.get("correlation_id") or f"daemon_v0_2:{cand.get('candidate_id')}"),
                        )
                        deduped = bool(r.get("deduplicated"))
                        job_id = str(r.get("job_id") or "")
                        if deduped:
                            dedup_enqueues += 1
                            _candidate_upsert(c, cand, status="deduplicated_enqueue", job_id=job_id)
                        else:
                            enqueued += 1
                            scheduler_queued_cache = (scheduler_queued_cache or 0) + 1
                            _candidate_upsert(c, cand, status="enqueued", job_id=job_id)

                if verbose:
                    print(f"[daemon] processed event_id={event_id} offset={start}->{end}", file=sys.stderr)
            except Exception as e:  # noqa: BLE001
                status = "error"
                err = f"{type(e).__name__}: {e}"
                errors += 1
                if verbose:
                    print(f"[daemon] parse-error offset={start}->{end} err={err}", file=sys.stderr)

            c.execute(
                """
                INSERT INTO daemon_audit(event_id, offset_start, offset_end, status, error, processed_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (event_id, int(start), int(end), status, err, now_iso()),
            )
            offset = end

        c.commit()

    save_state(
        c,
        mode="poll" if mode == "tail" else mode,
        events_file=str(events_file),
        offset=offset,
        processed_total=processed_total,
        last_event_id=last_event_id,
    )

    return BatchResult(
        processed=processed,
        errors=errors,
        offset=offset,
        last_event_id=last_event_id,
        normalized=normalized,
        deduped_events=deduped_events,
        candidates=candidates,
        enqueued=enqueued,
        dedup_enqueues=dedup_enqueues,
        throttled=throttled,
        skipped_hwm=skipped_hwm,
        system_repeat_alerts=system_repeat_alerts,
        ack_compressed=ack_compressed,
        ack_rollup_candidates=ack_rollup_candidates,
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="MindKernel v0.2 memory observer daemon")
    p.add_argument("--mode", choices=["poll", "tail"], default="poll")
    p.add_argument("--events-file", default=str(DEFAULT_EVENTS_FILE))
    p.add_argument("--state-db", default=str(DEFAULT_STATE_DB))
    p.add_argument("--pid-file", default=str(DEFAULT_PID_FILE))

    p.add_argument("--scheduler-db", default="", help="optional scheduler db path for enqueue")
    p.add_argument("--enable-enqueue", action="store_true", help="legacy switch; use --feature-flag on/partial for enqueue")
    p.add_argument("--feature-flag", choices=["off", "shadow", "partial", "on"], default="off", help="runtime rollout strategy (default off)")
    p.add_argument("--partial-session-allowlist", default="", help="line-based session_id allowlist file for partial mode")
    p.add_argument("--enqueue-min-risk-level", choices=["low", "medium", "high"], default="low")
    p.add_argument("--session-rate-limit-per-min", type=int, default=20)
    p.add_argument("--scheduler-queue-high-watermark", type=int, default=500)
    p.add_argument("--max-candidates-per-event", type=int, default=1)

    # time-dimension strategy
    p.add_argument("--system-repeat-window-min", type=int, default=60)
    p.add_argument("--system-repeat-threshold", type=int, default=3)
    p.add_argument("--ack-window-min", type=int, default=120)
    p.add_argument("--ack-rollup-every", type=int, default=10)

    p.add_argument("--poll-interval-sec", type=float, default=1.0)
    p.add_argument("--max-batch", type=int, default=200)
    p.add_argument("--max-loops", type=int, default=0, help="0 means unlimited")
    p.add_argument("--run-once", action="store_true")
    p.add_argument("--reset-checkpoint", action="store_true")
    p.add_argument("--verbose", action="store_true")
    return p.parse_args()


def main():
    args = parse_args()

    events_file = Path(args.events_file).expanduser().resolve()
    state_db = Path(args.state_db).expanduser().resolve()
    pid_file = Path(args.pid_file).expanduser().resolve()

    scheduler_db = Path(args.scheduler_db).expanduser().resolve() if args.scheduler_db else None

    feature_flag = str(args.feature_flag or "off")
    # backward compatibility: old switch implies on
    if args.enable_enqueue and feature_flag == "off":
        feature_flag = "on"

    allowlist_path = Path(args.partial_session_allowlist).expanduser().resolve() if args.partial_session_allowlist else None
    partial_session_allowlist = _load_allowlist(allowlist_path)

    enqueue_enabled = bool(scheduler_db is not None and feature_flag in {"on", "partial"})

    install_signal_handlers()

    c: sqlite3.Connection | None = None
    sc: sqlite3.Connection | None = None

    processed_this_run = 0
    errors_this_run = 0
    normalized_this_run = 0
    deduped_events_this_run = 0
    candidates_this_run = 0
    enqueued_this_run = 0
    dedup_enqueues_this_run = 0
    throttled_this_run = 0
    skipped_hwm_this_run = 0
    system_repeat_alerts_this_run = 0
    ack_compressed_this_run = 0
    ack_rollup_candidates_this_run = 0

    loops = 0
    stopped_by_signal = False

    batch_started = now_iso()

    try:
        acquire_pid_file(pid_file)

        c = db_conn(state_db)
        init_db(c)

        if scheduler_db is not None:
            sc = sch.conn(scheduler_db)
            sch.init_db(sc)

        state = load_state(c)
        offset = int(state["offset"])
        processed_total = int(state["processed_total"])
        last_event_id = state.get("last_event_id")

        if args.reset_checkpoint:
            offset = 0
            save_state(
                c,
                mode=args.mode,
                events_file=str(events_file),
                offset=offset,
                processed_total=processed_total,
                last_event_id=last_event_id,
            )

        if state.get("events_file") and state.get("events_file") != str(events_file):
            offset = 0
            save_state(
                c,
                mode=args.mode,
                events_file=str(events_file),
                offset=offset,
                processed_total=processed_total,
                last_event_id=last_event_id,
            )

        while True:
            loops += 1

            br = process_batch(
                c,
                mode=args.mode,
                events_file=events_file,
                offset=offset,
                processed_total=processed_total,
                max_batch=max(1, int(args.max_batch)),
                last_event_id=last_event_id,
                verbose=bool(args.verbose),
                scheduler_conn=sc,
                enqueue_enabled=enqueue_enabled,
                feature_flag=feature_flag,
                partial_session_allowlist=partial_session_allowlist,
                session_rate_limit_per_min=max(1, int(args.session_rate_limit_per_min)),
                scheduler_queue_high_watermark=max(1, int(args.scheduler_queue_high_watermark)),
                enqueue_min_risk_level=args.enqueue_min_risk_level,
                max_candidates_per_event=max(1, int(args.max_candidates_per_event)),
                system_repeat_window_min=max(1, int(args.system_repeat_window_min)),
                system_repeat_threshold=max(1, int(args.system_repeat_threshold)),
                ack_window_min=max(1, int(args.ack_window_min)),
                ack_rollup_every=max(1, int(args.ack_rollup_every)),
            )

            processed_this_run += br.processed
            errors_this_run += br.errors
            normalized_this_run += br.normalized
            deduped_events_this_run += br.deduped_events
            candidates_this_run += br.candidates
            enqueued_this_run += br.enqueued
            dedup_enqueues_this_run += br.dedup_enqueues
            throttled_this_run += br.throttled
            skipped_hwm_this_run += br.skipped_hwm
            system_repeat_alerts_this_run += br.system_repeat_alerts
            ack_compressed_this_run += br.ack_compressed
            ack_rollup_candidates_this_run += br.ack_rollup_candidates

            offset = br.offset
            last_event_id = br.last_event_id
            state = load_state(c)
            processed_total = int(state["processed_total"])

            if _STOP:
                stopped_by_signal = True
                break
            if args.run_once:
                break
            if int(args.max_loops) > 0 and loops >= int(args.max_loops):
                break

            if br.processed == 0:
                time.sleep(max(0.05, float(args.poll_interval_sec)))

        c.execute(
            """
            INSERT INTO daemon_batches(
                mode, started_at, ended_at, processed, normalized, deduped_events,
                candidates, enqueued, dedup_enqueues, throttled, skipped_hwm,
                errors, offset, system_repeat_alerts, ack_compressed, ack_rollup_candidates
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "poll" if args.mode == "tail" else args.mode,
                batch_started,
                now_iso(),
                processed_this_run,
                normalized_this_run,
                deduped_events_this_run,
                candidates_this_run,
                enqueued_this_run,
                dedup_enqueues_this_run,
                throttled_this_run,
                skipped_hwm_this_run,
                errors_this_run,
                offset,
                system_repeat_alerts_this_run,
                ack_compressed_this_run,
                ack_rollup_candidates_this_run,
            ),
        )
        c.commit()

        scheduler_stats = sch.stats(sc) if sc is not None else None

        out = {
            "ok": True,
            "mode": args.mode,
            "events_file": str(events_file),
            "state_db": str(state_db),
            "scheduler_db": str(scheduler_db) if scheduler_db else None,
            "feature_flag": feature_flag,
            "partial_session_allowlist_size": len(partial_session_allowlist),
            "enqueue_enabled": enqueue_enabled,
            "pid_file": str(pid_file),
            "processed_this_run": processed_this_run,
            "errors_this_run": errors_this_run,
            "normalized_this_run": normalized_this_run,
            "deduped_events_this_run": deduped_events_this_run,
            "candidates_this_run": candidates_this_run,
            "enqueued_this_run": enqueued_this_run,
            "dedup_enqueues_this_run": dedup_enqueues_this_run,
            "throttled_this_run": throttled_this_run,
            "skipped_hwm_this_run": skipped_hwm_this_run,
            "system_repeat_alerts_this_run": system_repeat_alerts_this_run,
            "ack_compressed_this_run": ack_compressed_this_run,
            "ack_rollup_candidates_this_run": ack_rollup_candidates_this_run,
            "processed_total": processed_total,
            "offset": offset,
            "last_event_id": last_event_id,
            "loops": loops,
            "stopped_by_signal": stopped_by_signal,
            "scheduler_stats": scheduler_stats,
            "updated_at": now_iso(),
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
    except Exception as e:  # noqa: BLE001
        out = {
            "ok": False,
            "error": f"{type(e).__name__}: {e}",
            "updated_at": now_iso(),
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
        raise SystemExit(1)
    finally:
        if c is not None:
            c.close()
        if sc is not None:
            sc.close()
        release_pid_file(pid_file)


if __name__ == "__main__":
    main()
