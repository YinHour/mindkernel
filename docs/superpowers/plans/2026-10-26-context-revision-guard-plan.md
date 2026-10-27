# Context Revision Guard Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans for this single engineering unit. The user requested continuation of the approved September design, not a new design discussion.

**Goal:** Ensure selected historical expressions carry their applicable revisions and field status, or report why a complete input cannot be built.

**Architecture:** A pure offline function over explicitly provided, source-checked events and manual field relations. It resolves field status and selects complete evidence groups before optional retrieval fill. It does not discover semantic relations, read files, invoke a model, or change the existing source adapter.

**Tech Stack:** Python 3.11+ standard library; unittest. Current runtime Python 3.12.14.

**Spec:** [Field revision contract](../../04-prototypes/context-revision-selection-v0.1.md).

## Global Constraints

- Engineering budget <=90 minutes including review/updates; experiment inference calls 0. Code review is development work, not a new model comparison.
- Reuse the existing independent checkout on `codex/w1-context-adapter`; preserve earlier uncommitted work. No commit, push or merge in this unit.
- Default history caps: 4 events, 10,000 UTF-8 bytes including field metadata; no silent truncation of required evidence.
- No new collection, training, runtime database or background integration. Real data stays ignored.
- Synthetic September acceptance data and all frozen experiments stay unchanged.

## Review Focus

1. A future/out-of-scope relation with a missing older target must not poison earlier replay; an applicable missing target must prevent model-ready output.
2. Reopening one field cannot withdraw unrelated fields, nor resurrect an old time after the reopening becomes stale.
3. Same-time incompatible values and non-user suggestions must not silently become confirmed user facts.
4. Mandatory budget plus related evidence must respect both record and serialized-byte caps; optional fill cannot reintroduce a stale unqualified packet.
5. Malformed IDs, relation scope/field mismatch, invalid timestamps, and caller-owned mutable objects must not create order-dependent or false-ready outputs.

### Task 1: Implement and verify the pure revision selection layer

**Files:**
- Create `tools/experiments/select_revision_context_v0_1.py`.
- Create `test/test_context_revision_selection_v0_1.py`.
- Update prototype docs, test inventory and execution records after verification.

**Interfaces:**
- Input events use the synthetic fixture shape: `id`, `scope`, `authority`, `created_at`, `available_at`, `text`, `claims`; optional `valid_from`, `valid_until`. `claims` are manual field-value annotations, not automatically verified semantics.
- Relations use `id`, `type`, `older`, `newer`, `field`, `scope`; source and timing come from `newer`. Future or irrelevant relations are ignored before target validation.
- API: `select_revision_context(events, relations, *, as_of, project, task=None, seed_ids, required_ids=(), max_history_records=4, max_history_bytes=10000) -> dict`.
- Output: `status`, `model_input` (null unless ready), `selected_ids`, `excluded`, `omissions`, `errors`. Ready input holds ordered `history` packets with per-field `status`/value/evidence/reason plus a request-only interpretation rule. It never produces `needs_user_reply_now`.
- `current` means the latest supported explicit expression, not a confirmed configuration or long-term preference. Unaffected workflow expressions remain supported with their original provenance; no cancellation or execution is inferred.
- Selection starts with required events. Related seed groups precede isolated optional fill; dependency expansion includes both ends of applicable relations and competing explicit claims on the same field/scope. If a related group cannot fit, return `budget_incomplete` with no model input; isolated optional overflow can be omitted explicitly.
- Missing required evidence returns `required_unavailable`; applicable invalid relations return `invalid_relation`; selected incompatible latest claims return `conflict`; malformed caller data raises `ValueError`.

- [x] Step 1: Turn S01–S11 into executable semantic assertions in the test file. Add the five review-focus boundaries, byte overflow, deterministic ordering, and no input mutation. Use literal fixture expectations; missing implementation must fail assertions, not be skipped.
- [x] Step 2: Run `python3 -m unittest discover -s test -p 'test_context_revision_selection_v0_1.py' -v`; save RED evidence. Expected: tests fail because the module/entrypoint is absent.
- [x] Step 3: Implement the documented API; source validation, relation eligibility/validation, field resolution, complete group selection and capacity checks are separate small helpers.
- [x] Step 4: Run the same targeted command. Expected: all cases pass, including no ready payload on invalid/incomplete input.
- [x] Step 5: Rebuild the saved real revision expectation with new manual field relations in a new ignored directory. Check source hashes and old comparison invariants; expected selected history is budget + the three revision events, with old schedule needing review and daily report fields retained. No inference calls.
- [x] Step 6: Run `python3 -m unittest discover -s test -p 'test_*.py' -v` with bundled Python on PATH. Expected: complete suite green. Obtain one fresh read-only code review; handle findings with regression evidence.
- [x] Step 7: Update contract/runtime examples, current progress and bottlenecks, and original-directory entrypoints. Check document links and Git diff; keep uncommitted artifacts and record remaining model/independent-feedback limits.

执行结果：27 项针对性、117 项完整测试通过；真实保存案例重建及旧文件校验通过。一次独立 review 的三项问题均先复现再修正。工作区保留未提交状态；详细证据见推进记录和本地工程目录。
