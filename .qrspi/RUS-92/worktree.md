# Work Tree — Resolve project-analysis tech debt: pivot residue, eval docs, doc bloat, untested CI-revise counter

**Plan basis:** plan.md @ 2026-06-19T00:00:00Z
**Generated:** 2026-06-19T00:00:00Z
**Status:** draft
**Total sessions:** 4
**Critical path:** T11 → T12 → T13 → T14 → T15 → T16 → T17 → T18 → T19 → T20 → T21

The critical path runs through Slice 2 (the only behavioral slice): the resolver factory field (T11) gates both verdict branches (T12, T13), which gate the resolver tests (T14–T16), the test run (T17), the envelope passthrough (T18), the `doRevise` dispatch rewrite (T19), and the two verifies (T20, T21). Slices 1, 3, and 4 are doc/comment-only sweeps with shallow internal chains and no cross-slice code dependency, so they are not on the critical path despite Slice 3 carrying the most tasks.

## Session 1 — Slice 1: Pivot-residue sweep (agent frontmatter + dead-path comments)

**Load:** plan.md §Slice 1, structure.md §Slice 1 (contract: agent spawn-line wording + comment-only edits to qrspi-batch.js)
**Estimated context:** ~12% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Replace `runCriticPanelLoop` spawn line at `:3` with `/review-design` form in `qrspi-design-critic-completeness.md` | — | §1.1 | S | pending |
| T2 | Same spawn-line replacement in `qrspi-design-critic-edge-alignment.md` | — | §1.2 | S | pending |
| T3 | Same spawn-line replacement in `qrspi-design-critic-internal-consistency.md` | — | §1.3 | S | pending |
| T4 | Same spawn-line replacement in `qrspi-design-critic-simplicity.md` | — | §1.4 | S | pending |
| T5 | Replace spawn line at `:3` in `qrspi-design-critic-design-review.md`, dropping dead `runCriticPanelLoop` ref, preserving live qualifier | — | §1.5 | S | pending |
| T6 | Replace `critic panel` → `review panel` noun at `:3` in `qrspi-impl-critic-impl-review.md` | — | §1.6 | S | pending |
| T7 | Remove genuine dead-path comments in `qrspi-batch.js` (live grep first; comment lines only, no executable change) | — | §1.7 | M | pending |
| T8 | **Verify Slice 1**: `grep runCriticPanelLoop .claude/agents/` zero hits; review.js/teeth-eval.js hits intact | T1, T2, T3, T4, T5 | §1.8 | S | pending |
| T9 | **Verify Slice 1**: `review panel` present and `critic panel` absent in impl-review agent | T6 | §1.9 | S | pending |
| T10 | **Verify Slice 1**: `git diff qrspi-batch.js` shows only comment deletions; `run_tests.py` passes | T7 | §1.10 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete. Slice 2 is the only behavioral slice (resolver + doRevise) and demands a fresh context focused on the resolver/test surface, not the agent-doc surface just edited.

## Session 2 — Slice 2: CI-revise verdict moved into the resolver + tests (CRITICAL PATH)

**Load:** plan.md §Slice 2, structure.md §Contracts (`ciCounterAction` ∈ {bump,reset,none}; `decision()` factory; `doRevise` dispatch), impl-log.md §Slice 1 (notes only)
**Estimated context:** ~22% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T11 | Add `ciCounterAction` field (default `"none"`) to `decision()` factory in `qrspi_resolve_state.py` | T10 | §2.11 | S | pending |
| T12 | Set `ciCounterAction = "bump"` on the red-under-cap revise branch in `resolve(...)` | T11 | §2.12 | S | pending |
| T13 | Set `ciCounterAction = "reset"` on the non-CI revise branch; leave cap-exceeded/non-revise at `"none"` | T11 | §2.13 | S | pending |
| T14 | Add test case asserting `ciCounterAction == "bump"` (red frontier under cap) in `qrspi_resolve_state_test.py` | T12 | §2.14 | S | pending |
| T15 | Add test case asserting `ciCounterAction == "reset"` (green frontier + change request) | T13 | §2.15 | S | pending |
| T16 | Add test case asserting `ciCounterAction == "none"` with `ciGaveUp` (red frontier at/above cap) | T12, T13 | §2.16 | S | pending |
| T17 | Run `python3 scripts/run_tests.py resolve`; new cases + existing `:343-474` CI cases pass | T14, T15, T16 | §2.17 | S | pending |
| T18 | Echo `ciCounterAction` through the `qrspi_resolve.py` envelope (verify verbatim-forward → no-op, else add key) | T11 | §2.18 | S | pending |
| T19 | Rewrite `doRevise` (≈918–1045) to dispatch on `decision.ciCounterAction`; preserve `answered.some(a => a.applied)` gate | T17, T18 | §2.19 | M | pending |
| T20 | **Verify Slice 2**: `run_tests.py resolve` passes incl. three new cases + existing CI cases | T17 | §2.20 | S | pending |
| T21 | **Verify Slice 2**: read-through of `doRevise` — applied gate short-circuits comment-only; no bump/reset re-derivation remains | T19 | §2.21 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 2 behavioral work complete and verified. Slice 3 is a large doc-only sweep (eval-string corrections, guide-pack consolidation, lifecycle dedup) spanning many files; a fresh context avoids carrying resolver/JS detail into a documentation-editing pass and keeps the consolidation read budget under 40%.

## Session 3 — Slice 3: Eval-doc wording + lifecycle dedup + guide-pack consolidation

**Load:** plan.md §Slice 3, structure.md §Slice 3 (eval-string target wording; canonical lifecycle doc pointer; guide-pack merge contract), impl-log.md §Slice 2 (notes only)
**Estimated context:** ~30% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T22 | Correct eval string at `.claude/CLAUDE.md:187` → `functional but unwired/orphaned` | T21 | §3.22 | S | pending |
| T23 | Correct comment at `scripts/eval_all.py:11` → `functional but unwired` | — | §3.23 | S | pending |
| T24 | Correct eval strings at `docs/eval-system.md` lines 7/97/101 | — | §3.24 | S | pending |
| T25 | Re-verify and fix `docs/eval-system.md` line citations against live `evals/run_eval.py` / `evals/revise.py` | T24 | §3.25 | M | pending |
| T26 | Create `docs/qrspi-guide.md` consolidating kept content of the five `docs/qrspi_*` guides; lifecycle stays a pointer; corrected eval wording | — | §3.26 | L | pending |
| T27 | Fold `qrspi_practical_application.md` kept content into `docs/qrspi-guide.md` | T26 | §3.27 | M | pending |
| T28 | Fold `qrspi_quick_reference.md` kept content into `docs/qrspi-guide.md` | T26 | §3.28 | M | pending |
| T29 | **DELETE** `docs/qrspi_claude_code_guide.md` (merged in T26) | T26 | §3.29 | S | pending |
| T30 | **DELETE** `docs/qrspi_complete_guide.md` (merged in T26) | T26 | §3.30 | S | pending |
| T31 | **DELETE** `docs/qrspi_working_example.md` (merged in T26) | T26 | §3.31 | S | pending |
| T32 | **DELETE** `docs/qrspi_practical_application.md` (merged; supersedes T27 in-place edit) | T27 | §3.32 | S | pending |
| T33 | **DELETE** `docs/qrspi_quick_reference.md` (merged; supersedes T28 in-place edit) | T28 | §3.33 | S | pending |
| T34 | Edit `docs/qrspi-orientation.md`: fix `:76` eval string; strip deleted-sibling index; lifecycle → pointer | T29, T30, T31, T32, T33 | §3.34 | M | pending |
| T35 | Replace duplicated `Lifecycle — PR-gated` narrative in `.claude/CLAUDE.md` with canonical-doc pointer; retain status invariants + entry-gate verbatim | T22 | §3.35 | M | pending |
| T36 | Replace restated lifecycle narrative in `qrspi-work/SKILL.md` (lines 9, 28–29, 197–198, 432) with pointer; status invariants verbatim | — | §3.36 | M | pending |
| T37 | Confirm/ensure `Selected/.../Done` sequence + entry-gate survive verbatim in `qrspi-pr-gated-lifecycle-design.md` (no-op unless invariant missing) | T35, T36 | §3.37 | S | pending |
| T38 | **Verify Slice 3**: `grep "non-functional placeholder"` zero hits; replacement consistent across all six locations | T22, T23, T24, T26, T34 | §3.38 | S | pending |
| T39 | **Verify Slice 3**: `docs/eval-system.md` citations match live `evals/run_eval.py` / `revise.py` | T25 | §3.39 | S | pending |
| T40 | **Verify Slice 3**: five `qrspi_*` guides gone, `docs/qrspi-guide.md` exists, no dangling links | T29, T30, T31, T32, T33, T34 | §3.40 | S | pending |
| T41 | **Verify Slice 3**: status sequence + entry-gate verbatim in canonical doc; restatements are pointers | T37 | §3.41 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 3 doc consolidation complete. Slice 4 collapses the three `/review-*` SKILL.md files onto a shared loop reference — a distinct authoring task needing a clean read of the current SKILL.md loop bodies, unburdened by the guide-pack/lifecycle edits just made.

## Session 4 — Slice 4: Collapse the `/review-*` skills onto a shared loop reference

**Load:** plan.md §Slice 4, structure.md §Slice 4 (shared-loop reference contract; per-skill lens/phase wiring: design-review / plan-review / impl-review), impl-log.md §Slice 3 (notes only)
**Estimated context:** ~16% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T42 | Create `.claude/skills/review-design/references/shared-loop.md` — canonical deterministic-round-0 loop, parameterized over per-skill lens/phase | T41 | §4.42 | M | pending |
| T43 | Replace restated loop body in `review-design/SKILL.md` with shared-loop reference; keep `design-review` lens/phase; don't alter description | T42 | §4.43 | S | pending |
| T44 | Replace restated loop body in `review-plan/SKILL.md` with shared-loop reference; keep `plan-review` lens/phase; don't alter description | T42 | §4.44 | S | pending |
| T45 | Replace restated loop body in `review-implementation/SKILL.md` with shared-loop reference; keep `impl-review` lens/phase; don't alter description | T42 | §4.45 | S | pending |
| T46 | **Verify Slice 4**: `grep shared-loop` hits all three SKILL.md; loop no longer restated; each lens/phase preserved | T43, T44, T45 | §4.46 | S | pending |
| T47 | **Verify Slice 4**: manual read of three `description:` fields — no triggering-description regression | T43, T44, T45 | §4.47 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** All four slices complete and verified. Final boundary closes the work — no further session is loaded.
