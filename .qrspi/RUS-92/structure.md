# Structure Outline — Resolve project-analysis tech debt: pivot residue, eval docs, doc bloat, untested CI-revise counter

**Design basis:** design.md @ 2026-06-19T00:00:00Z
**Generated:** 2026-06-19T00:00:00Z
**Status:** draft

## New Types

None. No new runtime structs/classes. The only new *named contract* is a decision-dict field (see Modified Types / Contracts).

## Modified Types

- `decision()` factory dict (`scripts/qrspi_resolve_state.py`) — add field `ciCounterAction: str ∈ {"bump", "reset", "none"}`, defaulted on the factory so all actions carry it (ref: design.md §Delta Slice 2, Decision 1 Option A, OQ1). This is a fixed-key dict; the field must be added at the single factory construction point so every one of the resolver's action branches emits it.

## Contracts

- `decision(...) -> dict` (`scripts/qrspi_resolve_state.py`) — factory now sets `ciCounterAction` defaulted to `"none"`; callers/tests treat the key as always-present (ref: Q3).
- `resolve(state, ci_revise_cap=...) -> dict` (`scripts/qrspi_resolve_state.py`) — sets `ciCounterAction = "bump"` on the red-frontier-under-cap revise, `"reset"` on a non-CI revise, `"none"` otherwise. No new params; the verdict is derived from existing inputs (`ci_state`, `ci_attempt`, `cap`, `changeRequested`) (ref: design.md §Pattern Decision 1, OQ1).
- `qrspi_resolve.py` envelope — echoes `ciCounterAction` through to JS only if the resolver dict is not already passed verbatim (verify at implementation; ref: Q3, design.md §Delta Slice 2).
- `doRevise(...)` (`.claude/workflows/qrspi-batch.js`) — bump-vs-reset branch dispatches on `decision.ciCounterAction` instead of re-deriving from `ciFailing`/`changeRequested`. The JS-only `answered.some(a => a.applied)` no-amend gate is **preserved**: when the resolver says `reset` but no content amend occurred (pure ANSWER/DECLINE), JS still no-ops the trailer write (ref: design.md §Pattern Decision 2 Option A, Q2, Q5).
- AC1 acceptance grep (test/verification contract): `grep -rn "runCriticPanelLoop" .claude/agents/` returns zero hits. Scope is **`.claude/agents/` only** — `.claude/workflows/qrspi-review.js` and `qrspi-teeth-eval.js` mentions are legitimate live-code contract documentation and are out of scope (ref: design.md §Desired End State AC1, Q4).

## Slice 1: Pivot-residue sweep (agent frontmatter + dead-path comments)

**Goal:** `grep -rn "runCriticPanelLoop" .claude/agents/` returns zero hits; the five design-critic agents name `/review-design` as their spawn path; the impl-critic panel-noun reads "review panel"; genuine dead-path comments in `qrspi-batch.js` are removed — all without touching live code or the legitimate workflow-file mentions.
**Files touched:**

- ⚠️ `.claude/agents/qrspi-design-critic-completeness.md` — replace `runCriticPanelLoop` spawn line (`:3`) with the `/review-design` form mirroring the impl-review peer (ref: Q4)
- ⚠️ `.claude/agents/qrspi-design-critic-edge-alignment.md` — same spawn-line replacement (`:3`)
- ⚠️ `.claude/agents/qrspi-design-critic-internal-consistency.md` — same spawn-line replacement (`:3`)
- ⚠️ `.claude/agents/qrspi-design-critic-simplicity.md` — same spawn-line replacement (`:3`)
- ⚠️ `.claude/agents/qrspi-design-critic-design-review.md` — replace spawn line (`:3`, with its `(opt-in, default-OFF)` qualifier) with the `/review-design` form (ref: Q4)
- ⚠️ `.claude/agents/qrspi-impl-critic-impl-review.md` — replace "implementation-phase **critic panel** (IMPL-REVIEW)" → "implementation-phase **review panel** (IMPL-REVIEW)" at `:3` (spawn line already correct) (ref: design.md §Delta Slice 1)
- ⚠️ `.claude/workflows/qrspi-batch.js` — remove genuine dead-path comments, located by re-grepping `removed|no longer|deleted worker|the old` against the LIVE file (NOT the stale `~525–561 / ~810–833` citations); keep edits to comment lines only (48/168/1033/1169/1212 region per research, re-verify) (ref: Q9, Risk Register row 1)

**Verification:**
- [ ] `grep -rn "runCriticPanelLoop" .claude/agents/` returns zero hits
- [ ] `grep -rn "runCriticPanelLoop" .claude/workflows/qrspi-review.js .claude/workflows/qrspi-teeth-eval.js` still returns the original hits (legitimate docs untouched)
- [ ] `grep -n "review panel" .claude/agents/qrspi-impl-critic-impl-review.md` shows the corrected noun; `grep -n "critic panel"` returns zero
- [ ] `git diff .claude/workflows/qrspi-batch.js` shows only comment-line deletions; `python3 scripts/run_tests.py` still passes (no behavioral change)

**Context cost:** M
**Depends on:** none

## Slice 2: CI-revise verdict moved into the resolver + tests

**Goal:** The bump-vs-reset *decision* lives in the pure, unit-tested resolver as `ciCounterAction`, with tests covering bump/reset/cap transitions; `doRevise` in JS applies the verdict instead of deriving it, preserving the `answered.applied` no-amend gate.
**Files touched:**

- ⚠️ `scripts/qrspi_resolve_state.py` — add `ciCounterAction` to the `decision()` factory (defaulted `"none"`); set `"bump"` on red-under-cap revise, `"reset"` on non-CI revise (ref: design.md §Delta Slice 2, Decision 1)
- ⚠️ `scripts/qrspi_resolve_state_test.py` — add `case(...)` entries asserting `ciCounterAction` across bump (red < cap), reset (green change-request), and cap (red ≥ cap → `"none"`/`ciGaveUp`) transitions, reusing existing `_phase`/`_slice` builders with `ci_state=`/`ci_attempt=`/`cap=` overrides (ref: Q10)
- ⚠️ `scripts/qrspi_resolve.py` — echo `ciCounterAction` through the envelope only if the decision dict is not already passed verbatim (verify first; may be a no-op) (ref: Q3)
- ⚠️ `.claude/workflows/qrspi-batch.js` — thin `doRevise` (918–1045) to dispatch the bump-vs-reset write on `decision.ciCounterAction`; preserve the JS-only `answered.some(a => a.applied)` confirmation gate (ref: design.md §Decision 2, Q2, Q5)

**Verification:**
- [ ] `python3 scripts/run_tests.py resolve` passes, including the new `ciCounterAction` cases
- [ ] New cases assert: red<cap → `"bump"`; green + change-request → `"reset"`; red≥cap → `"none"` with `ciGaveUp`
- [ ] Existing `qrspi_resolve_state_test.py:343-474` CI cases still pass (field added via factory → all actions defaulted)
- [ ] Manual e2e read-through of `doRevise`: confirms `applied` gate still short-circuits the trailer write on a comment-only PR (`qrspi-batch.js` is not unit-testable; ref: Risk Register row 4)

**Context cost:** M
**Depends on:** Slice 1 (both edit `qrspi-batch.js`; Slice 1 touches comment lines, Slice 2 touches `doRevise` (918–1045) — disjoint regions, ordered to avoid collision per Risk Register row 2)

## Slice 3: Eval-doc wording correction + lifecycle-narrative dedup + guide-pack consolidation

**Goal:** The eval harness is described as "functional but unwired/orphaned" everywhere (not "non-functional placeholder"), with `docs/eval-system.md` line citations re-verified; the five `qrspi_*` guide-pack docs are consolidated into one fresh maintained guide; the lifecycle narrative has a single canonical home that the others reference rather than restate, preserving the resolver-keyed invariants.
**Files touched:**

- ⚠️ `.claude/CLAUDE.md` — correct the `:187` "non-functional placeholder" eval string → "functional but unwired"; replace the duplicated "Lifecycle — PR-gated" narrative with a reference to `docs/qrspi-pr-gated-lifecycle-design.md`, preserving the `Selected/Design Review/Plan Review/Code Review/Done` invariants verbatim (ref: Q11, Q12, Risk Register row 6)
- ⚠️ `docs/qrspi-orientation.md` — correct the `:76` eval string; strip the meta-index content that only describes the deleted sibling guides; point lifecycle narrative at the canonical doc (ref: Q11, Q12, OQ3)
- ⚠️ `docs/eval-system.md` — correct the `7/97/101` eval strings; re-read live `evals/run_eval.py` / `revise.py` and fix the `run_eval.py:117-137` / `revise.py:26-44` line citations to the true numbers (ref: Q11, Risk Register row 5)
- ⚠️ `docs/qrspi_practical_application.md` — correct the `:185` eval string (file is consolidated/deleted below; if deleted, the correction is moot — fold its kept content into the new guide)
- ⚠️ `docs/qrspi_quick_reference.md` — correct the `:208` eval string (same consolidation note)
- ⚠️ `scripts/eval_all.py` — correct the `:11` "non-functional placeholder" comment → "functional but unwired" (ref: Q11)
- ✨ `docs/qrspi-guide.md` — fresh consolidated guide absorbing the kept content of the five `qrspi_*` guide-pack files; lifecycle stays a pointer to `docs/qrspi-pr-gated-lifecycle-design.md` (Designer's non-binding lean, OQ3: author fresh rather than promote an existing file)
- ⚠️ `docs/qrspi_claude_code_guide.md` — **DELETE** (content merged into `docs/qrspi-guide.md`) (ref: Q12)
- ⚠️ `docs/qrspi_complete_guide.md` — **DELETE** (merged) (ref: Q12)
- ⚠️ `docs/qrspi_working_example.md` — **DELETE** (merged) (ref: Q12)
- ⚠️ `.claude/skills/qrspi-work/SKILL.md` — replace the restated lifecycle narrative (lines 9, 28–29, 197–198, 432) with a reference to the canonical doc, preserving the resolver-keyed status invariants (ref: Q12)

**Note on file count:** This slice lists >10 file touches, but per Structure rule 8 it is one cohesive editorial unit — every change is a single project-wide doc consolidation pass with one verification surface (the placeholder-string grep + the lifecycle-invariant check), and the guide files cannot be deleted independently of authoring the merged guide. There is no internal testability boundary to split on. (Slice 2's `qrspi-batch.js` and `qrspi_*` guide files that also carry eval strings are reconciled here: if a file is deleted, its eval-string correction is satisfied by deletion.) If at plan time the consolidation proves separable from the eval-wording fix at a real verification boundary, the planner may split; structurally they share one grep gate.

**Verification:**
- [ ] `grep -rn "non-functional placeholder" .claude/ docs/ scripts/` returns zero hits
- [ ] The replacement wording is consistent ("functional but unwired/orphaned") across all six original locations and does not contradict the project MEMORY "Eval harness is a placeholder" record (reconcile wording, ref: Q11)
- [ ] `docs/eval-system.md` line citations match the live `evals/run_eval.py` / `revise.py` (open both, confirm)
- [ ] The three deleted guide files are gone; `docs/qrspi-guide.md` exists and no dangling links remain (`grep -rn "qrspi_claude_code_guide\|qrspi_complete_guide\|qrspi_working_example"` returns zero, or only the new guide's own provenance note)
- [ ] `Selected/Design Review/Plan Review/Code Review/Done` and the entry-gate wording survive verbatim in `docs/qrspi-pr-gated-lifecycle-design.md`; restatements elsewhere are now pointers (ref: Risk Register row 6)

**Context cost:** L
**Depends on:** none (independent of Slices 1–2; touches docs + `scripts/eval_all.py` + `qrspi-work/SKILL.md`, disjoint from the resolver/`doRevise`/agent-frontmatter edits). May run in parallel; ordered last only to keep the high-blast-radius doc churn off the code-review path.

## Slice 4: Collapse the four `/review-*` skills onto a shared loop reference

**Goal:** The four near-clone `/review-*` skill files (`review-design`, `review-plan`, `review-implementation`, and the shared engine reference) share one loop reference instead of restating the deterministic-round-0 review loop four times, with each skill's distinct lens/phase wiring preserved.
**Files touched:**

- ⚠️ `.claude/skills/review-design/SKILL.md` — replace the restated loop body with a reference to the shared loop doc; keep the design-lens/phase wiring (ref: ticket Slice 3, OQ4)
- ⚠️ `.claude/skills/review-plan/SKILL.md` — same collapse, plan-lens wiring preserved
- ⚠️ `.claude/skills/review-implementation/SKILL.md` — same collapse, impl-lens wiring preserved
- ✨ `.claude/skills/review-design/references/shared-loop.md` (or a shared location to be confirmed at plan time) — the single canonical loop reference the three skills point at (ref: OQ4 Designer's lean)

**Verification:**
- [ ] Each of the three `/review-*` SKILL.md files references the shared loop doc and no longer restates the round-0 loop verbatim
- [ ] Each skill's distinct lens name and phase (`design-review` / `plan-review` / `impl-review`) is preserved and correct
- [ ] No `/review-*` skill's triggering description regressed (manual read; the descriptions are load-bearing for auto-invocation)

**Context cost:** M
**Depends on:** none (distinct blast radius from Slice 3's doc merge — four skill files, no overlap with the `qrspi_*` guide-pack). Split out from Slice 3 per OQ4 Designer's lean (distinct testability boundary: the skill collapse is verifiable independently of the guide consolidation).

---

## Unverified Assumptions

- **OQ3 / OQ4 editorial choices are non-binding designer leans, settled here provisionally.** This structure adopts: (a) a fresh `docs/qrspi-guide.md` rather than promoting an existing guide (OQ3); (b) splitting the `/review-*` collapse into its own Slice 4 rather than folding it into Slice 3 (OQ4). Both are the designer's stated non-binding leans; a reviewer may override either without invalidating the rest of the structure.
- **`docs/eval-system.md` line citations (`run_eval.py:117-137`, `revise.py:26-44`) were NOT re-verified by research** (ref: Q11). The exact correct line numbers are unknown until the implementer opens the live `evals/` files; the slice carries this as an explicit in-slice verification step, but the *target* numbers cannot be stated in advance.
- **The genuine dead-path comment locations in `qrspi-batch.js` are not pinned to exact lines.** Research gives a candidate set (48, 168, 509–511, 1033, 1169, 1212) but the design mandates re-grepping `removed|no longer|deleted worker|the old` against the live file rather than trusting any cited range. The exact line set is resolved at implementation, not here.
- **Whether `qrspi_resolve.py` needs to change at all is unverified** (ref: Q3 / design.md §Delta Slice 2: "Modify `qrspi_resolve.py` if needed to echo the field through the envelope (only if not already passed)"). If the resolver decision dict is passed verbatim into the envelope, this edit is a no-op; the implementer must check.
- **Which non-redundant parts of `docs/qrspi-orientation.md` survive consolidation is an editorial judgment** not fully specified by the design — the meta-index "content that only describes siblings" is to be stripped, but the boundary of "only describes siblings" vs "carries unique signal" is decided during the Slice 3 merge.
- **Project MEMORY wording reconciliation:** AC2 requires the new "functional but unwired" wording not contradict the MEMORY record "Eval harness is a placeholder." Whether MEMORY itself must be updated (vs. just the six doc/source locations) is not resolved by the design; flagged for human attention before planning.
