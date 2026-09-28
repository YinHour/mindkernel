"""Public CLI contract tests using synthetic transcripts only."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools/memory/read_codex_session_v0_1.py"
FIXTURE = ROOT / "data/fixtures/codex-session-v0_1/visible-session.jsonl"


class CodexSessionReaderTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / "session.jsonl"
        self.source.write_bytes(FIXTURE.read_bytes())
        self.output = Path(self.temp.name) / "result.json"

    def run_reader(self, *extra, thread_id="synthetic-mindkernel", output=True):
        args = [sys.executable, str(CLI), "--session-file", str(self.source),
                "--thread-id", thread_id]
        if output:
            args += ["--out", str(self.output)]
        process = subprocess.run(args + list(extra), capture_output=True, text=True)
        self.assertTrue(process.stdout.strip(), process.stderr)
        summary = json.loads(process.stdout)
        report = json.loads(self.output.read_text()) if output and self.output.exists() else None
        return process, summary, report

    def write_rows(self, rows):
        self.source.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))

    def rows(self):
        return [json.loads(line) for line in FIXTURE.read_text().splitlines()]

    def issue_codes(self, report):
        return {issue["code"] for issue in report["issues"]}

    def test_visible_messages_keep_source_order_and_human_provenance(self):
        before = self.source.read_bytes()
        process, summary, report = self.run_reader()
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertTrue(summary["ok"])
        self.assertEqual([m["id"] for m in report["messages"]],
                         ["user-1", "assistant-1", "user-2", "assistant-2"])
        first = report["messages"][0]
        self.assertEqual(first["text"], "现在只讨论方案。")
        self.assertEqual(first["source_line"], 3)
        self.assertEqual(first["turn_id"], "turn-1")
        self.assertEqual(first["created_at"], "2026-09-17T03:00:00Z")
        self.assertEqual(first["recorded_at"], "2026-09-17T03:00:01Z")
        self.assertEqual(report["source"]["cwd"], "/synthetic/project-mirror")
        self.assertNotIn("PRIVATE_REASONING", self.output.read_text())
        self.assertNotIn("RAW_TOOL_PAYLOAD", self.output.read_text())
        self.assertNotIn("ENVIRONMENT_NOT_A_USER_FACT", self.output.read_text())
        self.assertNotIn("messages", summary)
        self.assertEqual(self.source.read_bytes(), before)

    def test_structured_answer_keeps_question_answer_and_original_carrier(self):
        _, _, report = self.run_reader()
        message = report["messages"][2]
        self.assertEqual(message["interaction_type"], "structured_reply")
        self.assertEqual(message["text"], "问题：每周投入多少时间？\n回答：每周 3–5 小时")
        self.assertIn("<send_user_message_question_reply>", message["raw_text"])

    def test_repeated_snapshot_and_duplicate_message_do_not_accumulate(self):
        rows = self.rows()
        rows.append(rows[2])
        self.write_rows(rows)
        _, _, first = self.run_reader()
        output_bytes = self.output.read_bytes()
        _, _, second = self.run_reader()
        self.assertEqual(len(first["messages"]), 4)
        self.assertEqual(first["summary"]["duplicate_messages"], 1)
        self.assertEqual(first, second)
        self.assertEqual(self.output.read_bytes(), output_bytes)

    def test_revised_id_is_reported_without_rewriting_earlier_history(self):
        rows = self.rows()
        revision = json.loads(json.dumps(rows[2]))
        revision["payload"]["content"][0]["text"] = "现在可以实现读取器。"
        rows.append(revision)
        self.write_rows(rows)
        process, _, report = self.run_reader()
        self.assertEqual(process.returncode, 2)
        self.assertFalse(report["ok"])
        self.assertEqual(len(report["messages"]), 4)
        self.assertEqual(report["messages"][0]["text"], "现在只讨论方案。")
        self.assertEqual(report["revisions"][0]["message"]["text"], "现在可以实现读取器。")
        self.assertIn("message_revision", self.issue_codes(report))

    def test_wrong_thread_is_rejected_without_exporting(self):
        process, summary, report = self.run_reader(thread_id="some-other-task")
        self.assertEqual(process.returncode, 2)
        self.assertEqual(summary["error"]["code"], "thread_mismatch")
        self.assertIsNone(report)

    def test_prefix_limit_and_digest_replay_a_frozen_snapshot(self):
        original = self.source.read_bytes()
        self.source.write_bytes(original + b'{"unfinished":')
        process, _, report = self.run_reader("--max-bytes", str(len(original)),
                                             "--expected-sha256", hashlib.sha256(original).hexdigest())
        self.assertEqual(process.returncode, 0)
        self.assertEqual(report["source"]["snapshot_bytes"], len(original))
        self.assertEqual(len(report["messages"]), 4)

    def test_hash_mismatch_does_not_replace_existing_output(self):
        self.output.write_text('{"previous":"keep"}')
        process, summary, _ = self.run_reader("--expected-sha256", "0" * 64)
        self.assertEqual(process.returncode, 2)
        self.assertEqual(summary["error"]["code"], "snapshot_mismatch")
        self.assertEqual(self.output.read_text(), '{"previous":"keep"}')

    def test_unfinished_tail_is_deferred_until_a_complete_record_exists(self):
        with self.source.open("ab") as f:
            f.write(b'{"unfinished":')
        process, _, report = self.run_reader()
        self.assertEqual(process.returncode, 2)
        self.assertEqual(len(report["messages"]), 4)
        self.assertIn("incomplete_tail", self.issue_codes(report))

    def test_corrupt_complete_line_is_not_silently_ignored(self):
        with self.source.open("ab") as f:
            f.write(b'{not-json}\n')
        process, _, report = self.run_reader()
        self.assertEqual(process.returncode, 2)
        self.assertIn("invalid_json", self.issue_codes(report))

    def test_unknown_user_origin_and_assistant_phase_are_not_learned(self):
        rows = self.rows()
        del rows[2]["payload"]["internal_chat_message_metadata_passthrough"]["content_item_kinds"]
        rows[-1]["payload"]["phase"] = "internal-new-phase"
        self.write_rows(rows)
        process, _, report = self.run_reader()
        self.assertEqual(process.returncode, 2)
        self.assertEqual([m["id"] for m in report["messages"]], ["assistant-1", "user-2"])
        self.assertTrue({"unknown_user_origin", "unknown_assistant_phase"} <= self.issue_codes(report))

    def test_missing_created_time_is_explicit_and_not_filled_with_now(self):
        rows = self.rows()
        del rows[2]["payload"]["internal_chat_message_metadata_passthrough"]["create_time"]
        self.write_rows(rows)
        process, _, report = self.run_reader()
        self.assertEqual(process.returncode, 2)
        self.assertIsNone(report["messages"][0]["created_at"])
        self.assertEqual(report["messages"][0]["recorded_at"], "2026-09-17T03:00:01Z")
        self.assertIn("missing_created_at", self.issue_codes(report))

    def test_unknown_format_cannot_succeed_with_zero_messages(self):
        self.write_rows([{"type": "session", "id": "synthetic-mindkernel"}])
        process, summary, report = self.run_reader()
        self.assertEqual(process.returncode, 2)
        self.assertEqual(summary["error"]["code"], "unsupported_header")
        self.assertIsNone(report)

    def test_source_cannot_be_used_as_output_even_through_a_hardlink(self):
        original = self.source.read_bytes()
        self.output.hardlink_to(self.source)
        process, summary, _ = self.run_reader(output=False)
        self.assertEqual(process.returncode, 0)
        # Check the refusal separately: output is JSONL, not a report object.
        process = subprocess.run([sys.executable, str(CLI), "--session-file", str(self.source),
            "--thread-id", "synthetic-mindkernel", "--out", str(self.output)], capture_output=True, text=True)
        self.assertEqual(process.returncode, 2)
        self.assertEqual(json.loads(process.stdout)["error"]["code"], "output_is_source")
        self.assertEqual(self.source.read_bytes(), original)

    def test_mixed_context_and_user_content_is_not_promoted_to_user_evidence(self):
        rows = self.rows()
        rows[2]["payload"]["internal_chat_message_metadata_passthrough"]["content_item_kinds"].append("agents_md.instructions")
        self.write_rows(rows)
        process, _, report = self.run_reader()
        self.assertEqual(process.returncode, 2)
        self.assertNotIn("user-1", [m["id"] for m in report["messages"]])
        self.assertIn("mixed_user_origin", self.issue_codes(report))

    def test_unsupported_content_and_record_shapes_are_reported(self):
        rows = self.rows()
        rows[2]["payload"]["content"].append({"type": "input_image", "image_url": "synthetic"})
        rows.extend([[], {"type": "future_record", "payload": {}}])
        self.write_rows(rows)
        process, _, report = self.run_reader()
        self.assertEqual(process.returncode, 2)
        self.assertNotIn("user-1", [m["id"] for m in report["messages"]])
        self.assertTrue({"unsupported_content", "invalid_record", "unknown_record_type"} <= self.issue_codes(report))

    def test_empty_supported_session_is_not_a_success(self):
        self.write_rows(self.rows()[:1])
        process, _, report = self.run_reader()
        self.assertEqual(process.returncode, 2)
        self.assertIn("no_visible_messages", self.issue_codes(report))

    def test_incomplete_utf8_tail_preserves_complete_messages(self):
        with self.source.open("ab") as f:
            f.write(b'{"text":"' + "中".encode()[:2])
        process, _, report = self.run_reader()
        self.assertEqual(process.returncode, 2)
        self.assertEqual(len(report["messages"]), 4)
        self.assertIn("incomplete_tail", self.issue_codes(report))

    def test_snapshot_boundary_beyond_source_is_rejected(self):
        process, summary, report = self.run_reader("--max-bytes", str(self.source.stat().st_size + 1))
        self.assertEqual(process.returncode, 2)
        self.assertEqual(summary["error"]["code"], "invalid_snapshot_size")
        self.assertIsNone(report)

    def test_observed_assistant_without_creation_time_keeps_null_and_warns(self):
        rows = self.rows()
        del rows[3]["payload"]["internal_chat_message_metadata_passthrough"]["create_time"]
        self.write_rows(rows)
        process, _, report = self.run_reader()
        self.assertEqual(process.returncode, 0)
        self.assertIsNone(report["messages"][1]["created_at"])
        self.assertIsNone(report["messages"][1]["created_at_epoch"])
        self.assertEqual(report["messages"][1]["recorded_at"], "2026-09-17T03:00:02Z")
        self.assertEqual(report["issues"][0]["severity"], "warning")
        self.assertEqual(report["summary"]["warning_count"], 1)
        self.assertEqual(report["summary"]["error_count"], 0)

    def test_assistant_with_neither_timestamp_is_an_error(self):
        rows = self.rows()
        del rows[3]["payload"]["internal_chat_message_metadata_passthrough"]["create_time"]
        del rows[3]["timestamp"]
        self.write_rows(rows)
        process, _, report = self.run_reader()
        self.assertEqual(process.returncode, 2)
        self.assertGreater(report["summary"]["error_count"], 0)

    def test_new_origin_label_needs_review_even_when_no_user_prefix_exists(self):
        rows = self.rows()
        rows[2]["payload"]["internal_chat_message_metadata_passthrough"]["content_item_kinds"] = ["future.origin"]
        self.write_rows(rows)
        process, _, report = self.run_reader()
        self.assertEqual(process.returncode, 2)
        self.assertIn("unknown_user_origin", self.issue_codes(report))

    def test_oversized_creation_time_is_reported_instead_of_crashing(self):
        rows = self.rows()
        rows[2]["payload"]["internal_chat_message_metadata_passthrough"]["create_time"] = 10 ** 400
        self.write_rows(rows)
        process, _, report = self.run_reader()
        self.assertEqual(process.returncode, 2)
        self.assertIsNone(report["messages"][0]["created_at"])
        self.assertIn("missing_created_at", self.issue_codes(report))


if __name__ == "__main__":
    unittest.main()
