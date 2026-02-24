#!/usr/bin/env python3
"""MindKernel memory index prototype v0.1 (retain/recall/reflect)."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORKSPACE = ROOT
DEFAULT_DB = ROOT / ".memory" / "index.sqlite"

RETAIN_HEADER_RE = re.compile(r"^##\s+Retain\b", re.IGNORECASE)
HEADER_RE = re.compile(r"^##\s+")
# - O(c=0.95) @Peter @warelay: content
RETAIN_LINE_RE = re.compile(
    r"^\s*[-*]\s*(?P<kind>[WBOS])(?:\(c=(?P<conf>0(?:\.\d+)?|1(?:\.0+)?)\))?\s*(?P<entities>(?:@[^:\s]+\s*)*):\s*(?P<content>.+)$"
)
DATE_IN_PATH_RE = re.compile(r"memory/(\d{4}-\d{2}-\d{2})\.md$")
TOKEN_RE = re.compile(r"[a-z0-9']+|[\u4e00-\u9fff]+")
SLUG_RE = re.compile(r"[^a-z0-9]+")

AUTO_START = "<!-- AUTO-GENERATED:REFLECT:START -->"
AUTO_END = "<!-- AUTO-GENERATED:REFLECT:END -->"

NEG_WORDS = {
    "not",
    "no",
    "never",
    "dont",
    "don't",
    "doesnt",
    "doesn't",
    "cannot",
    "can't",
    "won't",
    "无",
    "不",
    "没",
    "不是",
    "不要",
}

STOP_WORDS = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "to",
    "of",
    "with",
    "for",
    "in",
    "on",
    "is",
    "are",
    "was",
    "were",
    "be",
    "do",
    "does",
    "did",
}

POSITIVE_WORDS = {
    "prefer",
    "prefers",
    "like",
    "likes",
    "support",
    "supports",
    "stable",
    "useful",
    "good",
    "喜欢",
    "偏好",
    "支持",
    "稳定",
    "有用",
    "推荐",
    "赞成",
    "靠谱",
}

NEGATIVE_POLARITY_WORDS = {
    "dislike",
    "dislikes",
    "reject",
    "rejects",
    "avoid",
    "avoids",
    "bad",
    "unstable",
    "oppose",
    "opposes",
    "反对",
    "拒绝",
    "讨厌",
    "不喜欢",
    "不偏好",
    "不支持",
    "不稳定",
    "不要",
    "不推荐",
}

POLARITY_STOP = POSITIVE_WORDS | NEGATIVE_POLARITY_WORDS | NEG_WORDS

SUPPORT_DELTA = 0.05
CONTRADICT_DELTA = 0.08


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(db_path))
    c.row_factory = sqlite3.Row
    return c


def init_db(c: sqlite3.Connection):
    c.executescript(
        """
        PRAGMA journal_mode=WAL;

        CREATE TABLE IF NOT EXISTS documents (
            path TEXT PRIMARY KEY,
            sha1 TEXT NOT NULL,
            mtime REAL NOT NULL,
            indexed_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS facts (
            id TEXT PRIMARY KEY,
            kind TEXT NOT NULL,
            content TEXT NOT NULL,
            entities TEXT NOT NULL,
            confidence REAL NOT NULL,
            source_path TEXT NOT NULL,
            line_no INTEGER NOT NULL,
            source_ref TEXT NOT NULL,
            observed_date TEXT,
            indexed_at TEXT NOT NULL
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts USING fts5(
            fact_id UNINDEXED,
            content,
            entities,
            kind
        );

        CREATE TABLE IF NOT EXISTS opinions_state (
            opinion_key TEXT PRIMARY KEY,
            statement TEXT NOT NULL,
            entities TEXT NOT NULL,
            signature TEXT NOT NULL,
            negation INTEGER NOT NULL,
            confidence REAL NOT NULL,
            support_count INTEGER NOT NULL DEFAULT 0,
            contradict_count INTEGER NOT NULL DEFAULT 0,
            evidence_refs_json TEXT NOT NULL,
            last_event TEXT NOT NULL,
            last_updated TEXT NOT NULL,
            UNIQUE(signature, entities)
        );

        CREATE TABLE IF NOT EXISTS reindex_failures (
            path TEXT PRIMARY KEY,
            last_error TEXT NOT NULL,
            retry_count INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'pending',
            last_failed_at TEXT NOT NULL,
            last_retry_at TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_facts_kind ON facts(kind);
        CREATE INDEX IF NOT EXISTS idx_facts_observed_date ON facts(observed_date);
        CREATE INDEX IF NOT EXISTS idx_opinions_sig_entities ON opinions_state(signature, entities);
        CREATE INDEX IF NOT EXISTS idx_reindex_failures_status ON reindex_failures(status);
        """
    )
    c.commit()


def sha1_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def slugify(text: str) -> str:
    s = SLUG_RE.sub("-", text.strip().lower()).strip("-")
    return s or "entity"


def tokenize_text(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def has_negation(tokens: list[str]) -> bool:
    for t in tokens:
        if t in NEG_WORDS:
            return True
        if any(ch in t for ch in ["不", "没", "无"]) and len(t) >= 1:
            return True
    return False


def _normalize_signature_token(t: str) -> str:
    # tiny heuristic: normalize simple English plural/3rd-person suffix
    if re.fullmatch(r"[a-z']+", t) and len(t) > 3 and t.endswith("s"):
        t = t[:-1]
    return t


def opinion_signature(text: str) -> str:
    tokens = tokenize_text(text)
    cleaned = []
    for t in tokens:
        if t in NEG_WORDS or t in STOP_WORDS:
            continue
        t = t.replace("不", "").replace("没", "").replace("无", "")
        t = _normalize_signature_token(t)
        if t:
            cleaned.append(t)
    return " ".join(cleaned)


def detect_polarity(text: str) -> dict:
    tokens = tokenize_text(text)
    pos = 0
    neg = 0
    negate_next = False

    for tok in tokens:
        t = _normalize_signature_token(tok)
        if not t:
            continue

        if t in NEG_WORDS:
            negate_next = True
            continue

        if t in NEGATIVE_POLARITY_WORDS:
            if negate_next:
                pos += 1
                negate_next = False
            else:
                neg += 1
            continue

        if t in POSITIVE_WORDS:
            if negate_next:
                neg += 1
                negate_next = False
            else:
                pos += 1
            continue

        if any(t.startswith(prefix) for prefix in ["不", "没", "无"]) and len(t) >= 2:
            tail = t[1:]
            tail = _normalize_signature_token(tail)
            if tail in POSITIVE_WORDS:
                neg += 1
                continue
            if tail in NEGATIVE_POLARITY_WORDS:
                pos += 1
                continue

        negate_next = False

    score = pos - neg
    if score >= 1:
        label = "positive"
    elif score <= -1:
        label = "negative"
    else:
        label = "neutral"

    confidence = abs(score) / max(1, pos + neg)
    return {
        "label": label,
        "score": score,
        "confidence": round(min(1.0, max(0.0, confidence)), 4),
        "pos_hits": pos,
        "neg_hits": neg,
    }


def opinion_topic_signature(text: str) -> str:
    tokens = tokenize_text(text)
    cleaned = []
    for t in tokens:
        if t in STOP_WORDS or t in POLARITY_STOP:
            continue
        t = t.replace("不", "").replace("没", "").replace("无", "")
        t = _normalize_signature_token(t)
        if t and t not in POLARITY_STOP:
            cleaned.append(t)

    if not cleaned:
        return opinion_signature(text)
    return " ".join(cleaned)


def iter_md_files(workspace: Path):
    candidates = []
    for p in [workspace / "memory.md"]:
        if p.exists() and p.is_file():
            candidates.append(p)

    for base in [workspace / "memory", workspace / "bank"]:
        if base.exists():
            candidates.extend(sorted(base.rglob("*.md")))

    seen = set()
    for p in candidates:
        rp = p.resolve()
        if rp in seen:
            continue
        seen.add(rp)
        yield p


def extract_observed_date(rel_path: str) -> str | None:
    m = DATE_IN_PATH_RE.search(rel_path.replace("\\", "/"))
    return m.group(1) if m else None


def parse_retain_facts(md_text: str, rel_path: str):
    lines = md_text.splitlines()
    in_retain = False
    out = []

    for i, line in enumerate(lines, start=1):
        if RETAIN_HEADER_RE.match(line.strip()):
            in_retain = True
            continue

        if in_retain and HEADER_RE.match(line.strip()):
            in_retain = False
            continue

        if not in_retain:
            continue

        m = RETAIN_LINE_RE.match(line)
        if not m:
            continue

        kind = m.group("kind")
        conf = float(m.group("conf") or 0.7)
        content = m.group("content").strip()
        entities_raw = m.group("entities") or ""
        entities = [e.strip()[1:] for e in entities_raw.split() if e.strip().startswith("@")]

        out.append(
            {
                "kind": kind,
                "confidence": conf,
                "content": content,
                "entities": entities,
                "line_no": i,
                "source_ref": f"{rel_path}#L{i}",
                "observed_date": extract_observed_date(rel_path),
            }
        )

    return out


def clear_document_facts(c: sqlite3.Connection, rel_path: str):
    fact_rows = c.execute("SELECT id FROM facts WHERE source_path=?", (rel_path,)).fetchall()
    for r in fact_rows:
        c.execute("DELETE FROM facts_fts WHERE fact_id=?", (r["id"],))
    c.execute("DELETE FROM facts WHERE source_path=?", (rel_path,))


def remove_document(c: sqlite3.Connection, rel_path: str):
    clear_document_facts(c, rel_path)
    c.execute("DELETE FROM documents WHERE path=?", (rel_path,))


def mark_reindex_failure(c: sqlite3.Connection, rel_path: str, err: str, max_retries: int):
    row = c.execute("SELECT retry_count FROM reindex_failures WHERE path=?", (rel_path,)).fetchone()
    retry_count = int(row["retry_count"]) + 1 if row else 1
    status = "failed" if retry_count >= max_retries else "pending"
    now = now_iso()
    c.execute(
        """
        INSERT INTO reindex_failures(path, last_error, retry_count, status, last_failed_at, last_retry_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(path) DO UPDATE SET
            last_error=excluded.last_error,
            retry_count=excluded.retry_count,
            status=excluded.status,
            last_failed_at=excluded.last_failed_at,
            last_retry_at=excluded.last_retry_at
        """,
        (rel_path, err, retry_count, status, now, now),
    )


def clear_reindex_failure(c: sqlite3.Connection, rel_path: str):
    c.execute("DELETE FROM reindex_failures WHERE path=?", (rel_path,))


def upsert_document_and_facts(c: sqlite3.Connection, workspace: Path, path: Path):
    text = path.read_text(errors="ignore")
    rel_path = str(path.relative_to(workspace))
    st = path.stat()
    sha = sha1_text(text)

    indexed_at = now_iso()
    c.execute(
        "INSERT INTO documents(path, sha1, mtime, indexed_at) VALUES (?, ?, ?, ?) ON CONFLICT(path) DO UPDATE SET sha1=excluded.sha1, mtime=excluded.mtime, indexed_at=excluded.indexed_at",
        (rel_path, sha, st.st_mtime, indexed_at),
    )

    # replace facts for this doc
    clear_document_facts(c, rel_path)

    facts = parse_retain_facts(text, rel_path)
    for f in facts:
        fid = f"fact_{sha1_text(f['source_ref'] + '|' + f['content'])[:16]}"
        entities_str = " ".join(sorted(set(f["entities"])))
        c.execute(
            "INSERT OR REPLACE INTO facts(id, kind, content, entities, confidence, source_path, line_no, source_ref, observed_date, indexed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                fid,
                f["kind"],
                f["content"],
                entities_str,
                f["confidence"],
                rel_path,
                f["line_no"],
                f["source_ref"],
                f["observed_date"],
                indexed_at,
            ),
        )
        c.execute(
            "INSERT INTO facts_fts(fact_id, content, entities, kind) VALUES (?, ?, ?, ?)",
            (fid, f["content"], entities_str, f["kind"]),
        )

    clear_reindex_failure(c, rel_path)
    return {"path": rel_path, "facts_indexed": len(facts), "mode": "updated"}


def cmd_reindex(
    c: sqlite3.Connection,
    workspace: Path,
    incremental: bool = True,
    retry_failures: bool = True,
    max_retries: int = 3,
):
    init_db(c)
    stats = {
        "docs": 0,
        "facts": 0,
        "items": [],
        "skipped": 0,
        "deleted": 0,
        "failed": 0,
        "retried": 0,
        "incremental": incremental,
    }

    files = list(iter_md_files(workspace))
    rel_map = {str(p.relative_to(workspace)): p for p in files}

    # clean removed docs
    existing = c.execute("SELECT path FROM documents").fetchall()
    for r in existing:
        rel_path = r["path"]
        if rel_path not in rel_map:
            remove_document(c, rel_path)
            clear_reindex_failure(c, rel_path)
            stats["deleted"] += 1

    pending_failures = {}
    if retry_failures:
        for r in c.execute("SELECT path, retry_count FROM reindex_failures WHERE status='pending'").fetchall():
            pending_failures[r["path"]] = int(r["retry_count"])

    for rel_path, p in rel_map.items():
        try:
            st = p.stat()
            doc_row = c.execute("SELECT mtime FROM documents WHERE path=?", (rel_path,)).fetchone()
            should_retry = rel_path in pending_failures

            if should_retry:
                stats["retried"] += 1

            if incremental and doc_row and (not should_retry):
                old_mtime = float(doc_row["mtime"])
                if abs(old_mtime - float(st.st_mtime)) < 1e-6:
                    stats["skipped"] += 1
                    continue

            r = upsert_document_and_facts(c, workspace, p)
            stats["docs"] += 1
            stats["facts"] += r["facts_indexed"]
            stats["items"].append(r)
        except Exception as e:
            err = f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=1)}"
            mark_reindex_failure(c, rel_path, err, max_retries=max_retries)
            stats["failed"] += 1
            stats["items"].append({"path": rel_path, "error": str(e), "mode": "failed"})

    c.commit()
    return stats


def cmd_recall(c: sqlite3.Connection, query: str | None, kind: str | None, entity: str | None, since_days: int | None, limit: int):
    if query:
        where = []
        params: list = []

        if since_days is not None:
            day = (datetime.now(timezone.utc) - timedelta(days=since_days)).date().isoformat()
            where.append("(f.observed_date IS NULL OR f.observed_date >= ?)")
            params.append(day)

        if kind:
            where.append("f.kind = ?")
            params.append(kind)

        if entity:
            where.append("f.entities LIKE ?")
            params.append(f"%{entity}%")

        where.append("facts_fts MATCH ?")
        params.append(query)

        sql = """
        SELECT f.* FROM facts_fts
        JOIN facts f ON f.id = facts_fts.fact_id
        WHERE """ + " AND ".join(where) + " ORDER BY f.observed_date DESC, f.indexed_at DESC LIMIT ?"
        params.append(limit)
        rows = c.execute(sql, params).fetchall()
    else:
        params = []
        where = []

        if since_days is not None:
            day = (datetime.now(timezone.utc) - timedelta(days=since_days)).date().isoformat()
            where.append("(observed_date IS NULL OR observed_date >= ?)")
            params.append(day)

        if kind:
            where.append("kind = ?")
            params.append(kind)

        if entity:
            where.append("entities LIKE ?")
            params.append(f"%{entity}%")

        sql = "SELECT * FROM facts"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY observed_date DESC, indexed_at DESC LIMIT ?"
        params.append(limit)
        rows = c.execute(sql, params).fetchall()

    facts = []
    for r in rows:
        facts.append(
            {
                "id": r["id"],
                "kind": r["kind"],
                "content": r["content"],
                "entities": [x for x in (r["entities"] or "").split() if x],
                "confidence": r["confidence"],
                "source_ref": r["source_ref"],
                "observed_date": r["observed_date"],
            }
        )
    return {"facts": facts, "count": len(facts)}


def _upsert_autogen_block(path: Path, title: str, block_lines: list[str]):
    if path.exists():
        content = path.read_text(errors="ignore")
    else:
        content = f"# {title}\n\n"

    block = "\n".join([AUTO_START, *block_lines, AUTO_END])

    if AUTO_START in content and AUTO_END in content:
        start = content.index(AUTO_START)
        end = content.index(AUTO_END) + len(AUTO_END)
        new_content = content[:start] + block + content[end:]
    else:
        if not content.endswith("\n"):
            content += "\n"
        new_content = content + "\n" + block + "\n"

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new_content)


def cluster_opinion_conflicts(opinion_candidates: list[dict], limit_groups: int = 20):
    groups: dict[str, dict] = {}

    for op in opinion_candidates:
        entities = sorted(op.get("entities", []))
        entities_str = " ".join(entities)
        statement = (op.get("content") or "").strip()
        if not statement:
            continue

        topic_sig = opinion_topic_signature(statement)
        if not topic_sig:
            continue

        pol = detect_polarity(statement)
        key = f"{entities_str}|{topic_sig}"

        if key not in groups:
            gid = f"ocg_{sha1_text(key)[:12]}"
            groups[key] = {
                "group_id": gid,
                "entities": entities,
                "topic_signature": topic_sig,
                "polarity_counts": {"positive": 0, "negative": 0, "neutral": 0},
                "items": [],
            }

        g = groups[key]
        label = pol["label"]
        g["polarity_counts"][label] += 1
        g["items"].append(
            {
                "label": label,
                "score": pol["score"],
                "confidence": float(op.get("confidence", 0.7)),
                "source_ref": op.get("source_ref"),
                "observed_date": op.get("observed_date"),
                "content": statement,
            }
        )

    out = []
    for g in groups.values():
        pos = int(g["polarity_counts"].get("positive", 0))
        neg = int(g["polarity_counts"].get("negative", 0))
        total = len(g["items"])
        has_conflict = pos > 0 and neg > 0
        conflict_score = round((min(pos, neg) / max(1, total)), 4) if has_conflict else 0.0

        g["total"] = total
        g["has_conflict"] = has_conflict
        g["conflict_score"] = conflict_score
        g["recommended_action"] = "mandatory_review" if has_conflict else "auto_merge"
        g["items"] = sorted(
            g["items"],
            key=lambda x: (x.get("observed_date") or "", x.get("source_ref") or ""),
            reverse=True,
        )[:8]
        out.append(g)

    out.sort(key=lambda x: (x["has_conflict"], x["conflict_score"], x["total"]), reverse=True)
    return out[:limit_groups]


def evolve_opinions(c: sqlite3.Connection, opinion_candidates: list[dict]):
    # deterministic order: observed_date then source_ref
    def _key(x):
        return (x.get("observed_date") or "", x.get("source_ref") or "")

    for op in sorted(opinion_candidates, key=_key):
        entities = sorted(op.get("entities", []))
        entities_str = " ".join(entities)
        statement = op.get("content", "").strip()
        if not statement:
            continue

        sig = opinion_signature(statement)
        pol = detect_polarity(statement)
        if pol["label"] == "negative":
            neg = 1
        elif pol["label"] == "positive":
            neg = 0
        else:
            neg = 1 if has_negation(tokenize_text(statement)) else 0

        row = c.execute(
            "SELECT * FROM opinions_state WHERE signature=? AND entities=?",
            (sig, entities_str),
        ).fetchone()

        src = op.get("source_ref") or ""
        base_conf = float(op.get("confidence", 0.7))

        if not row:
            opinion_key = f"op_{sha1_text(sig + '|' + entities_str)[:16]}"
            c.execute(
                """
                INSERT INTO opinions_state(
                    opinion_key, statement, entities, signature, negation,
                    confidence, support_count, contradict_count,
                    evidence_refs_json, last_event, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, 0, 0, ?, 'new', ?)
                """,
                (
                    opinion_key,
                    statement,
                    entities_str,
                    sig,
                    neg,
                    max(0.05, min(0.99, base_conf)),
                    json.dumps([src], ensure_ascii=False),
                    now_iso(),
                ),
            )
            continue

        conf = float(row["confidence"])
        support = int(row["support_count"])
        contradict = int(row["contradict_count"])
        evidence = json.loads(row["evidence_refs_json"] or "[]")

        if src and src not in evidence:
            evidence.append(src)

        if int(row["negation"]) == neg:
            conf = min(0.99, conf + SUPPORT_DELTA)
            support += 1
            last_event = "support"
        else:
            conf = max(0.05, conf - CONTRADICT_DELTA)
            contradict += 1
            last_event = "contradict"

        c.execute(
            """
            UPDATE opinions_state
            SET confidence=?, support_count=?, contradict_count=?,
                evidence_refs_json=?, last_event=?, last_updated=?
            WHERE opinion_key=?
            """,
            (
                conf,
                support,
                contradict,
                json.dumps(evidence, ensure_ascii=False),
                last_event,
                now_iso(),
                row["opinion_key"],
            ),
        )

    c.commit()


def list_opinion_states(c: sqlite3.Connection, limit: int = 200):
    rows = c.execute(
        "SELECT * FROM opinions_state ORDER BY last_updated DESC LIMIT ?",
        (limit,),
    ).fetchall()

    out = []
    for r in rows:
        out.append(
            {
                "opinion_key": r["opinion_key"],
                "statement": r["statement"],
                "entities": [x for x in (r["entities"] or "").split() if x],
                "confidence": r["confidence"],
                "support_count": r["support_count"],
                "contradict_count": r["contradict_count"],
                "last_event": r["last_event"],
                "evidence_refs": json.loads(r["evidence_refs_json"] or "[]"),
                "last_updated": r["last_updated"],
            }
        )
    return out


def apply_reflect_writeback(workspace: Path, reflection: dict, max_per_entity: int, max_opinions: int):
    written = []

    entities_dir = workspace / "bank" / "entities"
    entities_dir.mkdir(parents=True, exist_ok=True)

    for summary in reflection.get("entity_summaries", []):
        entity = summary["entity"]
        facts = summary.get("top_facts", [])[:max_per_entity]

        lines = [
            f"# {entity}",
            "",
            "> Auto-generated by `memory_index_v0_1.py reflect --writeback`.",
            "",
            "## Facts",
        ]
        for f in facts:
            lines.append(
                f"- [{f['kind']} c={f['confidence']:.2f}] {f['content']} _(source: {f['source_ref']})_"
            )
        lines.append("")

        out_path = entities_dir / f"{slugify(entity)}.md"
        out_path.write_text("\n".join(lines))
        written.append(str(out_path.relative_to(workspace)))

    opinions_path = workspace / "bank" / "opinions.md"
    states = reflection.get("opinion_states", [])[:max_opinions]
    op_lines = [
        "## Auto Opinions",
        "",
    ]

    if states:
        for st in states:
            entities = " ".join(f"@{e}" for e in st.get("entities", []))
            s = int(st.get("support_count", 0))
            c = int(st.get("contradict_count", 0))
            trend = "↑" if s > c else ("↓" if c > s else "→")
            op_lines.append(
                f"- (c={float(st['confidence']):.2f}, trend={trend}, +{s}/-{c}) {entities} {st['statement']}"
            )
            ev = st.get("evidence_refs", [])[:3]
            if ev:
                op_lines.append(f"  - evidence: {', '.join(ev)}")
    else:
        # fallback for no evolved state
        for op in reflection.get("opinion_candidates", [])[:max_opinions]:
            entities = " ".join(f"@{e}" for e in op.get("entities", []))
            op_lines.append(
                f"- (c={op['confidence']:.2f}) {entities} {op['content']} _(source: {op['source_ref']})_".strip()
            )

    conflict_groups = [g for g in reflection.get("opinion_conflict_groups", []) if g.get("has_conflict")]
    if conflict_groups:
        op_lines.append("")
        op_lines.append("## Conflict Clusters")
        for g in conflict_groups[:8]:
            entities = " ".join(f"@{e}" for e in g.get("entities", []))
            pc = g.get("polarity_counts", {})
            op_lines.append(
                f"- [{g.get('group_id')}] {entities} topic=`{g.get('topic_signature')}` +{pc.get('positive',0)}/-{pc.get('negative',0)}"
            )
            top = g.get("items", [])[:2]
            for item in top:
                op_lines.append(
                    f"  - [{item.get('label')}] {item.get('content')} _(source: {item.get('source_ref')})_"
                )

    _upsert_autogen_block(opinions_path, "Opinions", op_lines)
    written.append(str(opinions_path.relative_to(workspace)))

    return written


def cmd_reflect(
    c: sqlite3.Connection,
    since_days: int | None,
    workspace: Path,
    writeback: bool,
    max_per_entity: int,
    max_opinions: int,
):
    params = []
    where = []
    if since_days is not None:
        day = (datetime.now(timezone.utc) - timedelta(days=since_days)).date().isoformat()
        where.append("(observed_date IS NULL OR observed_date >= ?)")
        params.append(day)

    sql = "SELECT kind, entities, confidence, content, source_ref, observed_date FROM facts"
    if where:
        sql += " WHERE " + " AND ".join(where)
    rows = c.execute(sql, params).fetchall()

    entity_map: dict[str, list[dict]] = {}
    opinion_candidates = []

    for r in rows:
        entities = [e for e in (r["entities"] or "").split() if e]
        for e in entities:
            entity_map.setdefault(e, []).append(
                {
                    "kind": r["kind"],
                    "content": r["content"],
                    "source_ref": r["source_ref"],
                    "confidence": r["confidence"],
                }
            )
        if r["kind"] == "O":
            pol = detect_polarity(r["content"])
            opinion_candidates.append(
                {
                    "entities": entities,
                    "content": r["content"],
                    "confidence": r["confidence"],
                    "source_ref": r["source_ref"],
                    "observed_date": r["observed_date"],
                    "topic_signature": opinion_topic_signature(r["content"]),
                    "polarity": pol["label"],
                    "polarity_score": pol["score"],
                }
            )

    entity_summaries = []
    for e, items in sorted(entity_map.items()):
        entity_summaries.append(
            {
                "entity": e,
                "fact_count": len(items),
                "top_facts": items[:5],
            }
        )

    conflict_groups = cluster_opinion_conflicts(opinion_candidates, limit_groups=max(10, max_opinions))

    out = {
        "entity_summaries": entity_summaries,
        "opinion_candidates": opinion_candidates[:50],
        "opinion_conflict_groups": conflict_groups,
        "generated_at": now_iso(),
    }

    if writeback:
        evolve_opinions(c, opinion_candidates)
        out["opinion_states"] = list_opinion_states(c, limit=max_opinions)
        written = apply_reflect_writeback(workspace, out, max_per_entity=max_per_entity, max_opinions=max_opinions)
        out["writeback"] = {"enabled": True, "paths": written}

    return out


def main():
    p = argparse.ArgumentParser(description="MindKernel memory index v0.1")
    p.add_argument("--workspace", default=str(DEFAULT_WORKSPACE), help="workspace root path")
    p.add_argument("--db", default=str(DEFAULT_DB), help="sqlite db path")

    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init-db")
    rx = sub.add_parser("reindex")
    rx.add_argument("--full", action="store_true", help="force full reindex (disable incremental skip)")
    rx.add_argument("--no-retry-failures", action="store_true", help="do not retry pending failed documents")
    rx.add_argument("--max-retries", type=int, default=3, help="max retries before marking a document as failed")

    rc = sub.add_parser("recall")
    rc.add_argument("--query")
    rc.add_argument("--kind", choices=["W", "B", "O", "S"])
    rc.add_argument("--entity")
    rc.add_argument("--since-days", type=int)
    rc.add_argument("--limit", type=int, default=20)

    rf = sub.add_parser("reflect")
    rf.add_argument("--since-days", type=int)
    rf.add_argument("--writeback", action="store_true", help="write reflection result into bank/entities + bank/opinions")
    rf.add_argument("--max-per-entity", type=int, default=8)
    rf.add_argument("--max-opinions", type=int, default=50)

    lo = sub.add_parser("list-opinions-state")
    lo.add_argument("--limit", type=int, default=50)

    args = p.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    db_path = Path(args.db).expanduser().resolve()

    c = connect(db_path)
    init_db(c)

    if args.cmd == "init-db":
        print(json.dumps({"ok": True, "db": str(db_path)}, ensure_ascii=False))
        return

    if args.cmd == "reindex":
        print(
            json.dumps(
                cmd_reindex(
                    c,
                    workspace,
                    incremental=not args.full,
                    retry_failures=not args.no_retry_failures,
                    max_retries=max(1, int(args.max_retries)),
                ),
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if args.cmd == "recall":
        print(
            json.dumps(
                cmd_recall(c, args.query, args.kind, args.entity, args.since_days, args.limit),
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if args.cmd == "reflect":
        print(
            json.dumps(
                cmd_reflect(
                    c,
                    args.since_days,
                    workspace=workspace,
                    writeback=args.writeback,
                    max_per_entity=args.max_per_entity,
                    max_opinions=args.max_opinions,
                ),
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if args.cmd == "list-opinions-state":
        print(json.dumps(list_opinion_states(c, args.limit), ensure_ascii=False, indent=2))
        return


if __name__ == "__main__":
    main()
