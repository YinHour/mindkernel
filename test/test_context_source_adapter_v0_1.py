"""Source-boundary tests using the public synthetic reader fixture only."""
import copy
import hashlib
import importlib
from pathlib import Path
import unittest

from core.codex_session_reader_v0_1 import read_codex_session


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "data/fixtures/codex-session-v0_1/visible-session.jsonl"


class ContextSourceAdapterTests(unittest.TestCase):
    def setUp(self):
        self.report = read_codex_session(FIXTURE, expected_thread_id="synthetic-mindkernel")
        self.record = {
            "id": "phase", "kind": "intent", "key": "phase", "value": "仍在方案讨论",
            "scope": {"project": "MindKernel", "task": None},
            "source": {"event_id": "user-1", "authority": "user_explicit",
                       "ref": str(FIXTURE.resolve()) + "#L3", "quote": "现在只讨论方案。",
                       "created_at": "2026-09-17T03:00:00Z", "available_at": "2026-09-17T03:00:01Z"},
            "recorded_at": "2026-09-30T01:00:00Z", "valid_from": "2026-09-17T03:00:00Z",
            "valid_until": None, "recheck_after": "2026-10-01T00:00:00Z", "supersedes": [],
        }

    def run_adapter(self, records=None, **kwargs):
        module = "tools.experiments.assemble_context_v0_1"
        self.assertIsNotNone(importlib.util.find_spec(module), "source adapter is not implemented")
        options = dict(expected_thread_id="synthetic-mindkernel", project="MindKernel",
                       as_of="2026-09-28T00:00:00Z")
        options.update(kwargs)
        return importlib.import_module(module).assemble_from_sources(
            self.report, [self.record] if records is None else records, **options)

    def excluded(self, reason, **kwargs):
        result = self.run_adapter(**kwargs)
        self.assertEqual(result["context"]["current"], [])
        self.assertEqual(result["source_excluded"], [{"id": "phase", "reason": reason}])
        self.assertIn({"id": "phase", "reason": reason}, result["context"]["excluded"])

    def observation(self, authority="artifact_observation"):
        content = "W1-03 in_progress\n"
        digest = hashlib.sha256(content.encode()).hexdigest()
        self.record.update(kind="task_state", key="active_item", value="W1-03 in_progress")
        self.record["source"] = {
            "event_id": "state-observed", "ref": "synthetic://state", "authority": authority,
            "created_at": "2026-09-17T03:00:00Z", "available_at": "2026-09-17T03:00:01Z",
            "sha256": digest,
        }
        return dict(self.record["source"], content=content)

    def test_real_reader_output_binds_source_and_preserves_annotation_time(self):
        result = self.run_adapter()
        self.assertEqual(result["context"]["current"], [self.record])
        binding = result["bindings"][0]
        self.assertEqual(binding["event_id"], "user-1")
        self.assertEqual(binding["source_written_at"], "2026-09-17T03:00:01Z")
        self.assertEqual(binding["annotated_at"], "2026-09-30T01:00:00Z")
        self.assertEqual(result["source_excluded"], [])

    def test_missing_message_is_excluded(self):
        self.report["messages"] = self.report["messages"][1:]
        self.excluded("source_missing")

    def test_assistant_cannot_be_promoted_to_user(self):
        self.report["messages"][0]["role"] = "assistant"
        self.excluded("speaker_mismatch")

    def test_message_from_another_thread_is_excluded(self):
        self.report["messages"][0]["thread_id"] = "another-task"
        self.excluded("source_thread_mismatch")

    def test_missing_or_naive_source_times_are_not_filled_in(self):
        for field in ("created_at", "recorded_at"):
            for value in (None, "2026-09-17T03:00:00"):
                with self.subTest(field=field, value=value):
                    report = copy.deepcopy(self.report)
                    self.report["messages"][0][field] = value
                    self.excluded("source_time_unknown")
                    self.report = report

    def test_quote_or_reference_mismatch_is_not_silently_repaired(self):
        for field, value, reason in [("quote", "并非原文", "quote_mismatch"),
                                      ("ref", "synthetic://another-source", "source_ref_mismatch")]:
            with self.subTest(field=field):
                original = self.record["source"][field]
                self.record["source"][field] = value
                self.excluded(reason)
                self.record["source"][field] = original

    def test_annotation_cannot_backdate_message_availability(self):
        self.record["source"]["available_at"] = "2026-09-17T03:00:00Z"
        self.excluded("source_time_mismatch")

    def test_creation_precision_can_be_later_than_truncated_write_time(self):
        self.report["messages"][0]["created_at"] = "2026-09-17T03:00:01.000123Z"
        self.record["source"]["created_at"] = "2026-09-17T03:00:01.000123Z"
        self.record["source"]["available_at"] = "2026-09-17T03:00:01.000123Z"
        self.assertEqual(len(self.run_adapter()["context"]["current"]), 1)

    def test_future_evidence_is_excluded_even_with_long_horizon(self):
        result = self.run_adapter(as_of="2026-09-17T03:00:00Z", horizon="2026-10-02T00:00:00Z")
        self.assertEqual(result["context"]["current"], [])
        self.assertEqual(result["context"]["excluded"], [{"id": "phase", "reason": "future_source"}])

    def test_structured_reply_uses_original_carrier_for_quote_check(self):
        message = self.report["messages"][2]
        self.record["source"].update(event_id=message["id"], ref=message["source_ref"],
                                      created_at=message["created_at"], available_at=message["recorded_at"],
                                      quote=message["raw_text"].strip())
        self.assertEqual(len(self.run_adapter()["context"]["current"]), 1)

    def test_non_user_sources_require_explicit_observation_payload(self):
        self.observation()
        self.excluded("observation_missing")

    def test_observation_hash_binds_the_actual_content(self):
        observation = self.observation()
        observation["content"] = "changed content"
        self.excluded("observation_hash_mismatch", observations=[observation])

    def test_unencodable_user_source_is_excluded_without_aborting_assembly(self):
        self.report["messages"][0]["text"] = "broken\ud800"
        self.record["source"]["quote"] = "broken\ud800"
        self.excluded("source_invalid_utf8")

    def test_unencodable_observation_is_excluded_without_aborting_assembly(self):
        observation = self.observation()
        observation["content"] = "broken\ud800"
        self.excluded("source_invalid_utf8", observations=[observation])

    def test_saved_annotation_hash_cannot_be_replaced_by_a_new_hash(self):
        observation = self.observation()
        observation["content"] = "changed content"
        observation["sha256"] = hashlib.sha256(observation["content"].encode()).hexdigest()
        self.excluded("observation_hash_mismatch", observations=[observation])

    def test_observation_authority_or_time_must_match_attestation(self):
        for field, value in [("authority", "user_explicit"), ("available_at", "2026-09-18T00:00:00Z")]:
            with self.subTest(field=field):
                observation = self.observation()
                observation[field] = value
                self.excluded("observation_metadata_mismatch", observations=[observation])

    def test_verified_history_summary_still_needs_recheck(self):
        observation = self.observation("history_summary")
        self.record["source"]["container_sha256"] = self.record["source"].pop("sha256")
        result = self.run_adapter(observations=[observation])
        self.assertEqual(result["context"]["current"], [])
        self.assertEqual(result["context"]["needs_recheck"], [self.record])

    def test_invalid_report_or_wrong_allowlist_fails_closed(self):
        for field, value in [("ok", False), ("schema_version", "unknown")]:
            with self.subTest(field=field):
                previous = self.report[field]
                self.report[field] = value
                with self.assertRaises(ValueError):
                    self.run_adapter()
                self.report[field] = previous
        with self.assertRaises(ValueError):
            self.run_adapter(expected_thread_id="other")

    def test_duplicate_message_or_observation_ids_are_ambiguous(self):
        self.report["messages"].append(copy.deepcopy(self.report["messages"][0]))
        with self.assertRaises(ValueError):
            self.run_adapter()
        self.report["messages"].pop()
        observation = self.observation()
        with self.assertRaises(ValueError):
            self.run_adapter(observations=[observation, observation])

    def test_bad_record_cannot_hide_duplicate_annotation_id(self):
        bad = copy.deepcopy(self.record)
        bad["source"]["event_id"] = "missing"
        with self.assertRaises(ValueError):
            self.run_adapter(records=[bad, self.record])

    def test_rerun_and_order_are_stable_and_inputs_are_unchanged(self):
        other = copy.deepcopy(self.record)
        other.update(id="later-review", key="other")
        before = copy.deepcopy((self.report, self.record, other))
        first = self.run_adapter(records=[self.record, other])
        self.assertEqual(first, self.run_adapter(records=[other, self.record]))
        self.assertEqual(first, self.run_adapter(records=[self.record, other]))
        self.assertEqual((self.report, self.record, other), before)

    def test_verified_record_still_obeys_scope_expiry_and_conflict_rules(self):
        result = self.run_adapter(project="other")
        self.assertEqual(result["context"]["excluded"], [{"id": "phase", "reason": "outside_scope"}])
        self.record["valid_until"] = "2026-09-28T00:00:00Z"
        self.assertEqual(self.run_adapter()["context"]["excluded"], [{"id": "phase", "reason": "expired"}])
        self.record["valid_until"] = None
        other = copy.deepcopy(self.record)
        other.update(id="conflict", value="进入实施")
        result = self.run_adapter(records=[self.record, other])
        self.assertEqual(result["context"]["current"], [])
        self.assertEqual([r["id"] for r in result["context"]["conflicts"]], ["conflict", "phase"])
