#!/usr/bin/env python3
"""Inspect one allowed Codex transcript; export visible text only with --out."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from core.codex_session_reader_v0_1 import CodexSessionError, read_codex_session


def _guard_output(source: Path, output: Path) -> None:
    if source.resolve() == output.resolve() or (output.exists() and os.path.samefile(source, output)):
        raise CodexSessionError("output_is_source", "Output must not be the source file or an alias of it.")


def _export(output: Path, report: dict) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=output.parent, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
        os.replace(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-file", required=True, type=Path)
    parser.add_argument("--thread-id", required=True, help="Expected task ID; a single-task allowlist")
    parser.add_argument("--out", type=Path, help="Explicit full report path; omit for counts only")
    parser.add_argument("--max-bytes", type=int, help="Read a frozen prefix instead of the current entire file")
    parser.add_argument("--expected-sha256", help="Require this snapshot digest before exporting")
    args = parser.parse_args()
    try:
        if args.out:
            _guard_output(args.session_file, args.out)
        report = read_codex_session(args.session_file, expected_thread_id=args.thread_id,
                                    max_bytes=args.max_bytes, expected_sha256=args.expected_sha256)
        if args.out:
            _export(args.out, report)
        summary = {k: report[k] for k in ("schema_version", "ok", "source", "summary", "issues")}
        print(json.dumps(summary, ensure_ascii=False, allow_nan=False))
        return 0 if report["ok"] else 2
    except (CodexSessionError, OSError) as error:
        code = error.code if isinstance(error, CodexSessionError) else "io_error"
        # Do not print transcript contents, even on failure.
        print(json.dumps({"ok": False, "error": {"code": code, "message": str(error)}}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
