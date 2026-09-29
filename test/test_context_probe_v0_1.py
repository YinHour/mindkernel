"""Synthetic boundary tests; literals are expectations, not human feedback."""
import copy
import unittest

from tools.experiments.probe_context_v0_1 import assemble


def record(identifier="budget", **changes):
    result = {
        "id": identifier, "kind": "constraint", "key": "weekly_budget",
        "value": "每周 3–5 小时", "scope": {"project": "MindKernel", "task": None},
        "source": {"ref": "synthetic://conversation/1", "event_id": identifier,
                   "authority": "user_explicit", "created_at": "2026-09-17T12:00:00+08:00",
                   "available_at": "2026-09-17T12:00:00+08:00"},
        "recorded_at": "2026-09-28T17:45:00+08:00",
        "valid_from": "2026-09-17T12:00:00+08:00", "valid_until": None,
        "recheck_after": None, "supersedes": [],
    }
    result.update(changes)
    return result


def run(records, at="2026-09-28T10:00:00+08:00", **kwargs):
    return assemble(records, as_of=at, project="MindKernel", **kwargs)


def ids(result, bucket):
    return [r["id"] for r in result[bucket]]


class ContextBoundaryTests(unittest.TestCase):
    def test_budget_survives_without_a_lexical_query(self):
        self.assertEqual(ids(run([record()]), "current"), ["budget"])

    def test_expiry_is_exclusive_even_in_another_timezone(self):
        r = record(kind="availability", valid_until="2026-09-22T00:00:00+08:00")
        self.assertEqual(ids(run([r], "2026-09-21T15:59:59Z"), "current"), ["budget"])
        self.assertEqual(run([r], "2026-09-21T16:00:00Z")["excluded"], [{"id": "budget", "reason": "expired"}])

    def test_new_explicit_revision_wins_in_either_input_order(self):
        old, new = record(), record("new", value="每周 2 小时")
        new["source"]["created_at"] = new["source"]["available_at"] = "2026-09-18T12:00:00+08:00"
        self.assertEqual(ids(run([old, new]), "current"), ["new"])
        self.assertEqual(run([new, old]), run([old, new]))

    def test_later_inference_cannot_replace_explicit_budget(self):
        inferred = record("guess", value="每天 5 小时")
        inferred["source"]["authority"] = "assistant_inference"
        inferred["source"]["created_at"] = inferred["source"]["available_at"] = "2026-09-27T12:00:00+08:00"
        result = run([record(), inferred])
        self.assertEqual(ids(result, "current"), ["budget"])
        self.assertEqual(ids(result, "needs_recheck"), ["guess"])

    def test_latest_explicit_update_due_for_review_does_not_revive_old_budget(self):
        newer = record("new", value="每周 2 小时", recheck_after="2026-09-20T00:00:00+08:00")
        newer["source"]["created_at"] = newer["source"]["available_at"] = "2026-09-18T12:00:00+08:00"
        self.assertEqual(ids(run([record(), newer], "2026-09-19T12:00:00+08:00"), "current"), ["new"])
        result = run([record(), newer])
        self.assertEqual(result["current"], [])
        self.assertEqual(ids(result, "needs_recheck"), ["new"])
        self.assertIn({"id": "budget", "reason": "older_or_lower_authority"}, result["excluded"])
        # A bounded temporary exception can still expire without permanently
        # replacing the underlying constraint.
        newer["valid_until"] = "2026-09-21T00:00:00+08:00"
        self.assertEqual(ids(run([record(), newer]), "current"), ["budget"])

    def test_old_task_state_is_pending_recheck(self):
        state = record("state", kind="task_state", key="active_item", value="W1-02 ready",
                       recheck_after="2026-09-18T00:00:00+08:00")
        state["source"]["authority"] = "artifact_observation"
        self.assertEqual(ids(run([state]), "needs_recheck"), ["state"])
        self.assertEqual(run([state])["current"], [])

    def test_summary_is_pending_even_before_its_recheck_time(self):
        state = record("summary", kind="task_state", recheck_after="2026-10-01T00:00:00+08:00")
        state["source"]["authority"] = "history_summary"
        self.assertEqual(ids(run([state]), "needs_recheck"), ["summary"])

    def test_future_availability_is_upcoming_not_current(self):
        r = record("monday", kind="availability", key="availability",
                   valid_from="2026-09-21T00:00:00+08:00", valid_until="2026-09-22T00:00:00+08:00")
        result = run([r], "2026-09-17T14:00:00+08:00", horizon="2026-09-22T00:00:00+08:00")
        self.assertEqual(ids(result, "upcoming"), ["monday"])
        self.assertEqual(result["current"], [])

    def test_future_source_is_not_opened_by_a_long_horizon(self):
        r = record()
        r["source"]["available_at"] = "2026-09-30T00:00:00+08:00"
        r["recorded_at"] = "2026-10-01T00:00:00+08:00"
        self.assertEqual(run([r], horizon="2026-10-10T00:00:00+08:00")["excluded"],
                         [{"id": "budget", "reason": "future_source"}])

    def test_other_project_and_task_do_not_leak(self):
        other = record("other", scope={"project": "Other", "task": None})
        task = record("task", scope={"project": "MindKernel", "task": "different"})
        result = run([other, task], task="this")
        self.assertEqual(result["excluded"], [{"id": "other", "reason": "outside_scope"}, {"id": "task", "reason": "outside_scope"}])

    def test_permanently_superseded_record_does_not_revive(self):
        new = record("new", value="每周 2 小时", supersedes=["budget"],
                     valid_from="2026-09-18T00:00:00+08:00", valid_until="2026-09-20T00:00:00+08:00")
        new["source"]["created_at"] = new["source"]["available_at"] = "2026-09-18T00:00:00+08:00"
        result = run([record(), new])
        self.assertEqual(result["current"], [])
        self.assertIn({"id": "budget", "reason": "superseded"}, result["excluded"])

    def test_future_revision_does_not_cancel_present_constraint(self):
        future = record("future", supersedes=["budget"], value="每周 1 小时")
        future["source"]["created_at"] = future["source"]["available_at"] = "2026-09-30T00:00:00+08:00"
        future["recorded_at"] = "2026-10-01T00:00:00+08:00"
        self.assertEqual(ids(run([record(), future]), "current"), ["budget"])

    def test_same_time_disagreement_requires_resolution(self):
        result = run([record(), record("conflict", value="每周 2 小时")])
        self.assertEqual(result["current"], [])
        self.assertEqual(ids(result, "conflicts"), ["budget", "conflict"])

    def test_missing_provenance_is_rejected(self):
        r = record()
        del r["source"]["ref"]
        self.assertEqual(run([r])["excluded"], [{"id": "budget", "reason": "invalid_record"}])

    def test_naive_time_is_rejected(self):
        r = record(valid_from="2026-09-17T12:00:00")
        self.assertEqual(run([r])["excluded"], [{"id": "budget", "reason": "invalid_record"}])

    def test_artifact_keeps_provenance_without_reading_the_file(self):
        r = record("file", kind="artifact", key="active_doc", value="/nonexistent/example.md",
                   recheck_after="2026-10-01T00:00:00+08:00")
        r["source"]["authority"] = "artifact_observation"
        before = copy.deepcopy(r)
        result = run([r])
        self.assertEqual(result["current"], [r])
        self.assertEqual(r, before)

    def test_duplicate_record_ids_are_not_silently_counted_twice(self):
        with self.assertRaises(ValueError):
            run([record(), record()])

    def test_malformed_record_cannot_hide_a_duplicate_id(self):
        invalid = record()
        del invalid["source"]["ref"]
        for case, records in enumerate(([invalid, record()], [record(), invalid], [invalid, invalid])):
            with self.subTest(case=case), self.assertRaisesRegex(ValueError, "duplicate record id"):
                run(records)

    def test_future_arrangement_can_need_reconfirmation_before_it_starts(self):
        future = record(
            "future", kind="availability", key="availability",
            valid_from="2026-09-21T00:00:00+08:00",
            valid_until="2026-09-22T00:00:00+08:00",
            recheck_after="2026-09-20T00:00:00+08:00",
        )
        before = run([future], "2026-09-19T12:00:00+08:00", horizon="2026-09-22T00:00:00+08:00")
        self.assertEqual(ids(before, "upcoming"), ["future"])
        due = run([future], "2026-09-20T00:00:00+08:00", horizon="2026-09-22T00:00:00+08:00")
        self.assertEqual(ids(due, "needs_recheck"), ["future"])
        self.assertEqual(due["current"], [])
        self.assertEqual(due["upcoming"], [])
        self.assertEqual(due["excluded"], [])
        self.assertEqual(due["needs_recheck"][0]["valid_from"], future["valid_from"])


if __name__ == "__main__":
    unittest.main()
