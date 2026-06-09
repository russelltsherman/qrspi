# Implementation Plan — Implement meta-agent diagnosis + revision loop

**Structure basis:** structure.md @ 2026-06-09T00:00:00Z
**Generated:** 2026-06-09T00:00:00Z
**Status:** draft
**Total steps:** 26

## Slice 1: Shared meta-agent invocation seam

### Setup

1. ✨ Create `scripts/meta_agent.py` — module exposing the single shared LLM-invocation seam. Add module docstring referencing Decision 1 (Option A: wrapper over the `using-claude-cli` subprocess path; ref Q6, Q3).

### Core Logic

2. ✨ In `scripts/meta_agent.py`, implement `complete(system: str, user: str) -> str` (Contract: single shared LLM-invocation seam). Shell out to the `using-claude-cli` path, returning the raw model text as a string (`MetaResponse = str`, parsed as JSON by callers per Decision 2 Option A).
3. ✨ In `scripts/meta_agent.py`, add defensive failure handling so a subprocess error or non-zero exit yields a logged no-result sentinel (callers treat as "no result") rather than crashing the `set -euo pipefail` loop (Decision 1, ref Q3, Q6).

### Tests

4. ✨ Create `scripts/meta_agent_test.py` — stdlib-only unit test that mocks the subprocess seam; asserts (a) a normal call returns the model text, and (b) a subprocess/parse failure returns the sentinel / does not raise out of `complete`.
5. Run: `python3 scripts/meta_agent_test.py`
   - **Expected:** all asserts pass.

### Verify Slice 1

6. **Checkpoint:** `python3 scripts/meta_agent_test.py`
   - [ ] Normal call returns model text.
   - [ ] Subprocess/parse-failure path returns sentinel / no crash.

---

## Slice 2: Grounded diagnosis via meta-agent

### Core Logic

7. ⚠️ Modify `scripts/diagnose.py` — replace the heuristic body of `categorize_failure`.
   - **Current:** `categorize_failure(failure, skill_text)` classifies via string-matching heuristics and returns `{case_id, score, categories, failed_assertions, regression_risk}`.
   - **After:** `categorize_failure(failure, skill_text) -> DiagnosisResult` invokes `meta_agent.complete(system, user)` with the full skill text + failing-case evidence, parses JSON into `{category, rationale}` where `category ∈ CATEGORIES` and `rationale` quotes failure evidence; preserves the existing keys consumed by `produce_diagnosis`' `recommendations`/`non_prompt_issues` assembly (AC1, ref Q1, Q4).
8. ⚠️ Modify `scripts/diagnose.py` — keep the `ALL_PASSING` / empty-failures short-circuit ahead of any `meta_agent.complete` call so passing cases make no model invocation (AC1, ref Q11).
9. ⚠️ Modify `scripts/diagnose.py` — handle a `meta_agent.complete` no-result/unparseable return defensively (no-edit/no-category fallback + logged error), not a crash (Risk: unparseable JSON, ref Q3).
10. ⚠️ Modify `scripts/diagnose.py` — add a `--dry-run` flag.
    - **Current:** `diagnose.py` has no dry-run concept and always writes `diagnosis.json`.
    - **After:** `--dry-run` emits the diagnosis with no side effects beyond the diagnosis file (ref Q9).

### Tests

11. ✨ Create `scripts/diagnose_test.py` — stdlib-only test that mocks `meta_agent.complete`; asserts (a) grounded `{category, rationale}` parsed from the mocked response, (b) `ALL_PASSING`/empty-failures short-circuits without calling the mock, (c) `--dry-run` writes nothing beyond the diagnosis file.
12. Run: `python3 scripts/diagnose_test.py`
    - **Expected:** all asserts pass.

### Verify Slice 2

13. **Checkpoint:** `python3 scripts/diagnose_test.py`
    - [ ] Grounded categorization parsed from mocked meta-agent.
    - [ ] `ALL_PASSING` short-circuit intact (no model call).
    - [ ] `--dry-run` writes nothing beyond the diagnosis file.

---

## Slice 3: Concrete revisions with anchor-safe apply

### Core Logic

14. ⚠️ Modify `scripts/revise.py` — replace placeholder edit construction in `propose_revisions`.
    - **Current:** `propose_revisions(skill_text, diagnosis)` emits one revision per recommendation with hard-coded `old_text=None`/`new_text=None`/`type="pending_meta_agent"`.
    - **After:** `propose_revisions(skill_text, diagnosis) -> list[EditProposal]` invokes `meta_agent.complete(system, user)` with diagnosis + skill text and parses concrete `{old_text, new_text, description}` edits anchored in the actual skill content (AC2, Decision 2, ref Q2, Q7).
15. ✨ Add `verify_anchor(skill_text, old_text) -> AnchorCheck` to `scripts/revise.py` — returns `{ok, reason}` where `reason ∈ {"missing","ambiguous","ok"}`: `missing` if `old_text` absent, `ambiguous` if it occurs more than once, else `ok` (Decision 3, ref Q10). Lives in the revise layer so `apply_revisions`' contract is untouched.
16. ⚠️ Modify `scripts/revise.py` — run `verify_anchor` per proposed edit before applying; skip + log any edit whose check is `missing`/`ambiguous` so the skill is never mis-written; pass only `ok` edits to `apply_revisions` (Decision 3, ref Q10).
17. ⚠️ Modify `scripts/revise.py` — leave `apply_revisions(skill_text, revisions) -> str` mechanically unchanged (first-occurrence substring replace); it now receives verified concrete edits only (unchanged contract, ref Q7).
18. ⚠️ Modify `scripts/revise.py` — make `revise_skill` return `revised` (not `pending_meta_agent`) when one or more verified edits land (AC2, ref Q12).
19. ⚠️ Modify `scripts/revise.py` — make `revision-log.json` read-only under `--dry-run`.
    - **Current:** `--dry-run` skips apply + skips writing the skill but still appends to `revision-log.json`.
    - **After:** `--dry-run` does not mutate `revision-log.json` (ref Q9).

### Tests

20. ✨ Create `scripts/revise_test.py` — stdlib-only test that mocks `meta_agent.complete`; asserts (a) a concrete mocked edit applies and `revise_skill` returns `revised`, (b) a `missing` anchor is skipped + logged and the skill text is unchanged, (c) an `ambiguous` anchor is skipped + logged and the skill text is unchanged, (d) `--dry-run` leaves `revision-log.json` untouched.
21. Run: `python3 scripts/revise_test.py`
    - **Expected:** all asserts pass.

### Verify Slice 3

22. **Checkpoint:** `python3 scripts/revise_test.py`
    - [ ] Concrete edit applies → `revised` status.
    - [ ] Missing/ambiguous anchor skipped, skill text unchanged.
    - [ ] `--dry-run` does not mutate `revision-log.json`.

---

## Slice 4: Version-level regression guard in report.py

### Core Logic

23. ⚠️ Modify `scripts/report.py` — extend `build_ledger_entry(...)` with a version-level `test_score`-drop guard.
    - **Current:** `report.py` flags per-case drops `> 0.2` (`detect_regressions`); no version-level `test_score`-drop alert exists.
    - **After:** `build_ledger_entry` computes the `test_score` delta from the prior version and, when the drop exceeds `0.05`, surfaces an alert in both `report["alerts"]` and the durable `ledger.json` entry, complementing the existing per-case 0.2 guard (AC4, ref Q15).

### Tests

24. ✨ Create `scripts/report_test.py` — stdlib-only test over synthetic version sequences: asserts (a) a `> 0.05` drop produces an alert in both `report["alerts"]` and the ledger entry, (b) a `≤ 0.05` change produces no such alert.
25. Run: `python3 scripts/report_test.py`
    - **Expected:** all asserts pass.

### Verify Slice 4

26. **Checkpoint:** `python3 scripts/report_test.py`
    - [ ] `> 0.05` drop alerts in both report and ledger.
    - [ ] `≤ 0.05` change does not alert.

---

## Slice 5: Under-specified convergence fixture + empirical loop run

> **NOTE — gated by an unresolved external dependency.** Structure §Unverified Assumptions and design.md AC3 / Risk Register state that `run_eval.py`/`grade.py` are stubs producing zeros, so the AC3 empirical-convergence verification cannot pass until the real runtime/judge lands. This slice's *fixture authoring* (steps below) is in scope; its end-to-end checkpoint is BLOCKED and validated only via the mocked unit tests from Slices 2–3 until that dependency is resolved (also OQ5: fixture definition + convergence target unresolved). Surface to the reviewer before implementing.

### Setup

27. ✨ Create `evals/fixtures/<under-specified-skill>` — a deliberately under-specified skill prompt for convergence validation (ref Q14). Exact fixture content and the convergence target (per-case 0.9 bar vs loop 0.85 `TARGET_SCORE`) are unresolved (OQ5) — confirm with reviewer before authoring.
28. ✨ Create `evals/golden/<convergence-golden>` — golden output if the run path requires it (ref Q14). Author only if the loop run path consumes a golden file.

### Verify Slice 5

29. **Checkpoint:** `bash run_loop.sh` against the new fixture
    - [ ] (BLOCKED on the stated runtime/judge dependency) `test_score` is monotonically non-decreasing across iterations.
    - [ ] Until unblocked: loop wiring validated via the mocked Slice 2–3 unit tests (`python3 scripts/diagnose_test.py && python3 scripts/revise_test.py`).

---

## Rollback Notes

- **Step 7 (`categorize_failure` rewrite):** the original heuristic body is the rollback target — preserve it in the commit diff so reverting the commit restores heuristic categorization without re-deriving it.
- **Steps 14–18 (`revise.py` revision path):** these change `revise_skill`'s output from `pending_meta_agent` to `revised`, which makes `run_loop.sh` actually overwrite `SKILL_PATH` in place (design.md Q8: in-place overwrite, no snapshot/backup). Before running the live loop against any real skill, snapshot `SKILL_PATH` (e.g. copy aside or commit) since a bad edit is otherwise unrecoverable; OQ2 (whether this ticket wires the commented `git checkout HEAD~1` rollback) is unresolved — confirm with reviewer.
- **Steps 27–28 (fixtures):** new files under `evals/` — rollback is deletion of the added fixture/golden files; no shared state mutated.
- **No DB migrations or destructive config changes in this plan.** Note step numbers continue past Slice 4's "Total steps: 26" because the gated Slice 5 setup/verify steps (27–29) are listed for completeness but excluded from the executable total.
