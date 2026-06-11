# Structure Outline — Implement meta-agent diagnosis + revision loop

**Design basis:** design.md @ 2026-06-09T00:00:00Z
**Generated:** 2026-06-09T00:00:00Z
**Status:** draft

## New Types

- `MetaResponse = str` — raw text returned by `meta_agent.complete(system, user)`; callers parse it as JSON (Decision 2, Option A).
- `DiagnosisResult { category: str (member of CATEGORIES), rationale: str }` — parsed shape returned by `categorize_failure`, quoting failure evidence. Must remain compatible with `produce_diagnosis`' downstream `recommendations`/`non_prompt_issues` assembly (AC1, ref: Q4).
- `EditProposal { old_text: str, new_text: str, description: str }` — one concrete, anchorable edit returned by the revise meta-agent; slots into `apply_revisions`' first-occurrence substring replace (AC2, Decision 2, ref: Q7).
- `AnchorCheck { ok: bool, reason: "missing" | "ambiguous" | "ok" }` — result of pre-apply anchor verification (Decision 3); used to skip/log unsafe edits without writing the skill (ref: Q10).

## Modified Types

- `categorize_failure` return — was a heuristic `{...}`; now grounded `{category, rationale, ...}` preserving existing keys consumed by `produce_diagnosis` (ref: design.md §Delta, Q1/Q4).
- `propose_revisions` revision entries — replace hard-coded `old_text=None`/`new_text=None`/`type="pending_meta_agent"` with concrete `old_text`/`new_text` pairs from `EditProposal` (ref: design.md §Delta, Q2/Q7).
- `report.py` ledger/report — add a version-level `test_score`-drop alert to `report["alerts"]` and `ledger.json` (ref: design.md §Delta, Q15).

## Contracts

- `meta_agent.complete(system: str, user: str) -> str` — single shared LLM-invocation seam over the `using-claude-cli` path; defensive JSON-friendly text return; on subprocess/parse failure raises or returns a sentinel that callers treat as "no result" rather than crashing the `set -euo pipefail` loop (Decision 1, ref: Q6, Q3). **Mockable boundary for diagnose_test.py and revise_test.py.**
- `categorize_failure(failure, skill_text) -> DiagnosisResult` — invokes `meta_agent.complete` with full skill text + failing case evidence; parses category (∈ `CATEGORIES`) + rationale; keeps `ALL_PASSING`/empty-failures short-circuit (AC1, ref: Q1, Q11).
- `propose_revisions(skill_text, diagnosis) -> list[EditProposal]` — invokes `meta_agent.complete` with diagnosis + skill text; returns concrete anchored edits (AC2, ref: Q2).
- `verify_anchor(skill_text, old_text) -> AnchorCheck` — confirms `old_text` is present and unique in `skill_text` before applying; logs skip/ambiguous otherwise (Decision 3, ref: Q10). Lives in the revise layer so `apply_revisions`' contract stays unchanged.
- `apply_revisions(skill_text, revisions) -> str` — **unchanged contract** (first-occurrence substring replace); now fed verified concrete edits (ref: Q7).
- `build_ledger_entry(...)` — extended to compute and surface a `> 0.05` version-level `test_score`-drop alert (AC4, ref: Q15).

## Slice 1: Shared meta-agent invocation seam

**Goal:** A standalone, mockable `meta_agent.complete(system, user) -> str` wrapper over the `using-claude-cli` path that both downstream scripts will call, with defensive handling so a subprocess/parse failure yields a logged no-result instead of crashing the loop. Testable in isolation: call it with a mocked subprocess and assert returned text + failure behavior.
**Files touched:**

- ✨ `scripts/meta_agent.py` — the `complete(system, user)` wrapper + defensive failure handling (Decision 1, ref: Q6, Q3)
- ✨ `scripts/meta_agent_test.py` — stdlib-only unit test mocking the subprocess seam; asserts normal return and parse/subprocess-failure path
**Verification:**
- [ ] `python3 scripts/meta_agent_test.py` passes (normal call returns text; failure path returns sentinel / no crash)
**Context cost:** S
**Depends on:** none

## Slice 2: Grounded diagnosis via meta-agent

**Goal:** `categorize_failure` returns a transcript-evidence-grounded `{category, rationale}` from a real `meta_agent.complete` call (mocked in tests), replacing the string-matching heuristic while preserving downstream keys and the `ALL_PASSING`/empty-failures short-circuit; `diagnose.py` gains a `--dry-run` that emits the diagnosis without side effects beyond the diagnosis file. End-to-end testable: mocked meta-agent in → parsed diagnosis out.
**Files touched:**

- ⚠️ `scripts/diagnose.py` — replace heuristic body of `categorize_failure` with `meta_agent.complete` call + JSON parse to category+rationale; add `--dry-run` flag (AC1, ref: Q1, Q9, Q11)
- ✨ `scripts/diagnose_test.py` — stdlib-only test mocking `meta_agent.complete`; asserts grounded category/rationale, short-circuit, and dry-run side-effect-free behavior
**Verification:**
- [ ] `python3 scripts/diagnose_test.py` passes (grounded categorization parsed; `ALL_PASSING` short-circuit intact; `--dry-run` writes nothing beyond diagnosis file)
**Context cost:** M
**Depends on:** Slice 1

## Slice 3: Concrete revisions with anchor-safe apply

**Goal:** `propose_revisions` returns concrete `old_text`/`new_text` edits from a real `meta_agent.complete` call (mocked in tests); a new `verify_anchor` rejects missing/ambiguous anchors before applying so the skill is never mis-written; `apply_revisions` stays mechanically unchanged; `revise_skill` returns `revised` (not `pending_meta_agent`) when edits land; and `--dry-run` is fixed so `revision-log.json` is not mutated. End-to-end testable: mocked meta-agent edit in → verified apply → `revised` status; ambiguous anchor → skipped + logged + skill untouched.
**Files touched:**

- ⚠️ `scripts/revise.py` — replace placeholder edit construction in `propose_revisions` with `meta_agent.complete` call returning concrete edits; add `verify_anchor` pre-apply pass; keep `apply_revisions` unchanged; make `revision-log.json` read-only under `--dry-run` (AC2, Decision 3, ref: Q2, Q7, Q9, Q10)
- ✨ `scripts/revise_test.py` — stdlib-only test mocking `meta_agent.complete`; asserts concrete edits apply, `revised` status, anchor missing/ambiguous skip-and-no-write, dry-run leaves `revision-log.json` untouched
**Verification:**
- [ ] `python3 scripts/revise_test.py` passes (concrete edit applies → `revised`; missing/ambiguous anchor skipped, skill text unchanged; dry-run does not mutate `revision-log.json`)
**Context cost:** M
**Depends on:** Slice 1

## Slice 4: Version-level regression guard in report.py

**Goal:** `report.py` flags any version whose `test_score` drops more than 0.05 from the prior version, surfaced in `report["alerts"]` and the durable `ledger.json`, complementing the existing per-case 0.2 guard. Independently testable against synthetic version sequences.
**Files touched:**

- ⚠️ `scripts/report.py` — add `> 0.05` version-level `test_score`-drop guard in `build_ledger_entry`; surface in `alerts` + `ledger.json` (AC4, ref: Q15)
- ✨ `scripts/report_test.py` — stdlib-only test: a >0.05 drop raises an alert in both `report["alerts"]` and the ledger entry; a ≤0.05 change does not
**Verification:**
- [ ] `python3 scripts/report_test.py` passes (>0.05 drop alerts in report + ledger; ≤0.05 does not)
**Context cost:** S
**Depends on:** none

## Slice 5: Under-specified convergence fixture + empirical loop run

**Goal:** A deliberately under-specified skill fixture (plus any required golden output) added under `evals/`, then `run_loop.sh` run against it to observe a monotonically non-decreasing `test_score` across iterations. This is the AC3 acceptance path and is the last slice because it depends on the real diagnose/revise behavior from Slices 2–3 landing.
**Files touched:**

- ✨ `evals/fixtures/<under-specified-skill>` — deliberately under-specified skill prompt for convergence validation (ref: Q14)
- ✨ `evals/golden/<convergence-golden>` — golden output if the run path requires it (ref: Q14)
**Verification:**
- [ ] `run_loop.sh` against the new fixture yields a monotonically non-decreasing `test_score` across iterations (BLOCKED on the ticket's stated runtime/judge dependency — see Unverified Assumptions; until then, validate the loop wiring with the mocked unit tests from Slices 2–3)
**Context cost:** M
**Depends on:** Slice 2, Slice 3

---

## Unverified Assumptions

- **AC3 empirical convergence is not currently observable in code** (Slice 5 verification). The design states `run_eval.py`/`grade.py` are stubs producing zeros and that AC3 depends on "the runtime/judge being real" — the ticket's stated external dependency. No concrete code in this Delta makes the runtime/judge real, so the Slice 5 end-to-end verification cannot pass until that dependency lands. Needs human decision before planning whether Slice 5 is in scope now or gated (ref: design.md AC3, Risk Register, Q6/Q14).
- **OQ1 — concrete model id / invocation for `meta_agent.py`.** The design does not fix whether `complete` shells out to the `using-claude-cli` skill vs. a direct `claude -p` call, nor whether an API key / CLI auth exists in the loop's execution environment. The Slice 1 wrapper cannot be fully specified without this (ref: design.md OQ1, Q6).
- **OQ2 — skill snapshot/rollback scope.** Whether this ticket wires the commented `git checkout HEAD~1` rollback / snapshots `SKILL_PATH` before each write, or defers it to a hardening ticket, is unresolved. It materially affects the in-place-overwrite risk but maps to no committed slice here (ref: design.md OQ2, Q8).
- **OQ3 — score scale for the 0.05 guard.** Score scale is ambiguous (`report.py` 0.2 reads as 1 point on a 5-point scale; diagnose 0.9 / loop 0.85 imply 0–1). Whether the new 0.05 guard is a 0–1 absolute and whether normalization is needed before comparing versions is unresolved — affects Slice 4's exact comparison (ref: design.md OQ3, Q15).
- **OQ4 — `regression_risk` inversion in `diagnose.py:102`.** Whether the `"low" if difficulty == "hard"` inversion is intentional and should be corrected while touching the file is unresolved — would change Slice 2's scope (ref: design.md OQ4, Q4).
- **OQ5 — fixture definition + convergence target.** What exactly defines the "deliberately under-specified prompt" and what delta counts as convergence (per-case 0.9 bar vs loop 0.85 `TARGET_SCORE`) is unresolved — Slice 5's fixture content and pass criterion depend on it (ref: design.md OQ5, Q11/Q14).
