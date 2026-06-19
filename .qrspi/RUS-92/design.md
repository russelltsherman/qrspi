# Design — Resolve project-analysis tech debt: pivot residue, eval docs, doc bloat, untested CI-revise counter

**Ticket:** RUS-92
**Research basis:** research.md @ 2026-06-19T00:00:00Z
**Generated:** 2026-06-19T00:00:00Z
**Status:** draft

## Current State

This ticket touches four largely independent debt surfaces; the codebase facts establish that three are pure documentation/string sweeps and one (the CI-revise counter) is *already* mostly where the ticket wants it.

**Pivot residue (AC1).** Exactly five design-critic agent front-matter files declare the literal string `Spawned by runCriticPanelLoop in qrspi-batch.js` — `qrspi-design-critic-completeness.md:3`, `-edge-alignment.md:3`, `-internal-consistency.md:3`, `-simplicity.md:3` (plain form), and `-design-review.md:3` (with an `(opt-in, default-OFF)` qualifier) (ref: Q4). `runCriticPanelLoop` no longer exists as a definition or call in `qrspi-batch.js` — a grep returns only these five agent-file mentions, and `runPhase:509-511` states the autonomous batch runs no critics (ref: Q4). The plan-critic and impl-critic peers already point at the `/review-*` commands as their *spawn path* (`qrspi-impl-critic-impl-review.md:3` says "Spawned by the /review-implementation command (advisory, propose-only)") (ref: Q4), so the design five are out of sync on the spawn line. **One additional sub-requirement of AC1 (ticket Slice 1):** `qrspi-impl-critic-impl-review.md:3` still calls itself part of the "implementation-phase **critic panel** (IMPL-REVIEW)"; the ticket requires aligning that "critic panel" → "review panel" (the impl-critic's spawn path is already correct, but its panel-noun is stale). The ticket also cites dead-path comments at `~525–561` and `~810–833` in `qrspi-batch.js`; research re-read both ranges and found them to be **live code, not dead-path comments** — the real residue comments are at lines 48, 168, 509–511, 1033, 1169, 1212 and others (ref: Q9). **Note — `runCriticPanelLoop` also legitimately appears as descriptive contract-shape comments in two workflow files that are NOT pivot residue:** `.claude/workflows/qrspi-review.js:151` and `.claude/workflows/qrspi-teeth-eval.js` (lines 48, 59, 83, 137, 161). Those comments accurately describe the live lens-prompt contract shape the on-demand review engine and the teeth-eval harness still thread; they must be **left intact** (deleting them would strip accurate documentation from live code), so the AC1 acceptance grep is scoped to **agent frontmatter**, per the ticket's own AC1 wording ("returns zero hits in agent frontmatter").

**Eval docs (AC2).** Six locations describe the eval harness as a "non-functional placeholder": `.claude/CLAUDE.md:187`, `docs/qrspi-orientation.md:76`, `docs/eval-system.md` (7, 97, 101), `docs/qrspi_quick_reference.md:208`, `docs/qrspi_practical_application.md:185`, and `scripts/eval_all.py:11` (ref: Q11). `docs/eval-system.md` additionally carries version-pinned line citations (`run_eval.py:117-137`, `revise.py:26-44`) whose accuracy against the live `evals/` tree was **not** re-verified by research (ref: Q11). Project MEMORY records "Eval harness is a placeholder"; any wording change must not contradict that record (ref: Q11).

**Doc bloat (AC3).** The `docs/qrspi_*` guide-pack is five files (`qrspi_claude_code_guide.md`, `qrspi_complete_guide.md`, `qrspi_practical_application.md`, `qrspi_quick_reference.md`, `qrspi_working_example.md`); the meta-index is `docs/qrspi-orientation.md`; the canonical narrative is `docs/qrspi-pr-gated-lifecycle-design.md` (ref: Q12). The PR-gated lifecycle narrative is independently restated in at least four live places: `.claude/CLAUDE.md` "Lifecycle — PR-gated", `qrspi-work/SKILL.md` (9, 28–29, 197–198, 432), the `qrspi-batch.js` comments, and the canonical design doc (ref: Q12). The `/review-*` skills are four near-clones (ref: ticket Slice 3; the lifecycle dedup is the verified part of this AC, ref: Q12).

**CI-revise counter (AC4).** The cap *decision* already lives entirely in the pure, unit-tested resolver: `qrspi_resolve_state.resolve` step 2c returns `revise`/`ciFailing` when a red frontier has `attempt < cap` and `wait`/`ciFailing`/`ciGaveUp` at/above cap (ref: Q6). The cap value is read by `qrspi_resolve.load_ci_revise_cap` → `qrspi_config.read_config` (flat key `ciReviseCap`, fail-closed to 3) and passed to `resolve(state, ci_revise_cap=...)`; the resolver does no disk I/O (ref: Q6). The read-side reset (effective count → 0 when not red) is in the gather `parse_pr_nodes` (ref: Q1, Q5). What remains in JS `doRevise` is **orchestration only**: choosing `bumpCiReviseTrailers` (CI path) vs `resetCiReviseTrailer` (non-CI path), keyed on `ciFailing`/`changeRequested`/`answered.some(a=>a.applied)` (ref: Q2, Q5). The actual trailer write delegates to `qrspi_ci_revise_bump.py` (bump, with its own `_test.py`) or a bare `gt modify -m` (reset) (ref: Q1, Q5). The decision dict already carries `ciFailing`/`ciGaveUp` and embeds `attempt N/cap` in `reason`; `ciRedBranches`/`ciFailingChecks` are re-emitted at the envelope top level by `qrspi_resolve.py`, not on the fixed-key decision dict (ref: Q3, Q13). Existing tests in `qrspi_resolve_state_test.py:343-474` already cover red/pending/green × frontier × cap boundaries, `ciFailing`, `ciGaveUp`, and per-slice `max` aggregation (ref: Q10).

## Desired End State

- **AC1:** `grep -rn "runCriticPanelLoop" .claude/agents/` returns zero hits (the ticket's "zero hits in agent **frontmatter**" bar — the legitimate descriptive comments in `.claude/workflows/qrspi-review.js` and `.claude/workflows/qrspi-teeth-eval.js` are accurate contract-shape documentation in live code and are intentionally **out of scope**, so a whole-`.claude/` grep is the wrong bar). The five design-critic files instead name `/review-design` as their spawn path, matching the plan/impl peers' wording (ref: Q4). `qrspi-impl-critic-impl-review.md`'s panel-noun is corrected from "critic panel" → "review panel" (ticket Slice 1). No agent description references `runCriticPanelLoop`, a function absent from `qrspi-batch.js`. The genuine dead-path comments (re-derived against the live file, not the stale `~525–561 / ~810–833` citations) are removed (ref: Q9).
- **AC2:** No source/doc file calls the eval harness a "non-functional placeholder." All six locations describe its true state — **functional but unwired/orphaned** (ref: Q11). The `docs/eval-system.md` embedded line citations are re-verified against the live `evals/` tree and corrected to match (ref: Q11). The wording remains consistent across all six and does not contradict the project MEMORY entry (ref: Q11).
- **AC3:** The five `qrspi_*` guide-pack docs are consolidated into one maintained guide (redundant files deleted); the lifecycle narrative has a single canonical home (`docs/qrspi-pr-gated-lifecycle-design.md`) that the others reference rather than restate, preserving the entry-gate and projection-status invariants the resolver keys on (`Selected` / `Design Review` / `Plan Review` / `Code Review` / `Done`) (ref: Q12); the four `/review-*` skills share one loop reference (ref: ticket Slice 3).
- **AC4:** The CI-Revise counter cap/bump/reset *transition decisions* are expressed and unit-tested in `qrspi_resolve_state.py`, and `qrspi-batch.js` applies the resolver's verdict rather than deriving counter state. Because the cap decision is *already* in the resolver (ref: Q6), the deliverable is: (a) make the resolver explicitly own the bump-vs-reset *verdict* (a new decision field telling JS which write to perform) and (b) add unit tests covering the bump/reset/cap transitions on that field, while preserving the shared-serialization and two-reset invariants (ref: Q1, Q5, Q7).

## Delta

**Slice 1 — pivot-residue sweep (string edits only):**
- Modify the five design-critic `.claude/agents/*.md` files: replace the `runCriticPanelLoop` spawn line with the `/review-design` form (mirroring the impl-review peer wording) (ref: Q4).
- Modify `.claude/agents/qrspi-impl-critic-impl-review.md:3`: replace "implementation-phase **critic panel** (IMPL-REVIEW)" with "implementation-phase **review panel** (IMPL-REVIEW)" — the ticket's "critic panel" → "review panel" sub-requirement of AC1 (its spawn line is already correct; only the panel-noun is stale).
- Remove the true dead-path comments in `qrspi-batch.js`, located by re-grepping `removed|no longer|deleted worker|the old` against the live file (NOT by the stale line numbers) (ref: Q9).
- **Do NOT touch** `.claude/workflows/qrspi-review.js` or `.claude/workflows/qrspi-teeth-eval.js`: their `runCriticPanelLoop` mentions are accurate descriptive comments about the live lens-contract shape, not pivot residue, and the AC1 acceptance grep is scoped to `.claude/agents/` accordingly (ref: Q4).

**Slice 2 — CI-revise verdict → resolver + tests:**
- Modify `scripts/qrspi_resolve_state.py`: add an explicit verdict field to the `decision()` factory (e.g. `ciCounterAction` ∈ {`bump`,`reset`,`none`}) so every action returns it, keeping the fixed-key contract (ref: Q3). The resolver sets `bump` on the red-under-cap revise, `reset` on a non-CI revise, `none` otherwise.
- Modify `scripts/qrspi_resolve_state_test.py`: add `case(...)` entries asserting the new field across bump (red < cap), reset (green change-request), and cap (red ≥ cap → `none`/`ciGaveUp`) transitions, using existing `_phase`/`_slice` builders with `ci_state=`/`ci_attempt=` and `cap=` overrides (ref: Q10).
- Modify `qrspi_resolve.py` if needed to echo the field through the envelope (only if not already passed) (ref: Q3).
- Modify `doRevise` in `qrspi-batch.js`: thin the bump-vs-reset branch to dispatch on the resolver's `ciCounterAction` instead of re-deriving from `ciFailing`/`changeRequested`/`answered` — preserving the `answered.some(a=>a.applied)` JS-only gate where a pure ANSWER/DECLINE touches no commit (ref: Q2, Q5).

**Slice 3 — docs consolidation + eval-wording correction:**
- Merge the five `docs/qrspi_*` guide-pack files into one maintained guide; delete the redundant files and the meta-index `docs/qrspi-orientation.md` content that only describes siblings (ref: Q12).
- Replace duplicated lifecycle narrative in `.claude/CLAUDE.md`, `qrspi-work/SKILL.md`, and `qrspi-batch.js` comments with references to `docs/qrspi-pr-gated-lifecycle-design.md` (ref: Q12).
- Collapse the four `/review-*` skills onto a shared loop reference (ref: ticket Slice 3).
- Correct the six "non-functional placeholder" strings to "functional but unwired" and re-verify/fix the `docs/eval-system.md` line citations (ref: Q11).

## Pattern Decisions

### Decision 1: How the resolver communicates the bump-vs-reset choice to JS

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Add an explicit `ciCounterAction` enum field to the `decision()` factory; JS dispatches on it | Single source of truth in the tested resolver; directly satisfies AC4 "JS no longer derives that state"; testable as a `case(...)` assertion | One added field on the fixed-key dict (must touch the factory once, ref: Q3) |
| B | Leave JS deriving bump/reset from `ciFailing`+`changeRequested`+`answered`; only add resolver tests for the cap | Smallest diff | Fails AC4's "no longer derives that state itself" — the derivation stays in non-unit-testable JS (ref: Q2) |

**Recommendation:** Option A
**Rationale:** The codebase's dominant pattern is "pure functional core / imperative shell" — all decision logic in tested Python, JS as a thin shell (ref: Discovered Patterns). The `decision()` factory is the single fixed-key construction point and already carries sibling verdict fields (`ciFailing`, `ciGaveUp`) (ref: Q3). Option A extends that exact pattern; Option B leaves the very derivation AC4 names in the untestable layer.
**NEW PATTERN?** No — extends the existing fixed-key decision-dict pattern (ref: Q3).

### Decision 2: Where the `answered.applied` JS-only gate lives

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Keep the `answered.some(a=>a.applied)` gate in JS; resolver emits `reset` and JS no-ops if nothing was applied | Honest about the boundary — `applied` is the one signal that exists only post-worker in JS (ref: Q2); preserves the comment-only-no-amend invariant (ref: Q5) | The reset decision is split: resolver says "reset eligible," JS confirms "amend happened" |
| B | Push `applied` into the resolver | Fully centralizes | Impossible — `applied` is computed only after the JS content worker returns; the resolver is pure and pre-worker (ref: Q2) |

**Recommendation:** Option A
**Rationale:** Research is explicit that `applied` is the only counter-relevant input that lives purely in JS and cannot be known at resolve time (ref: Q2). Centralizing the *policy* (which write is eligible) while leaving the *post-hoc amend confirmation* in JS respects the real data-flow boundary.
**NEW PATTERN?** No — preserves the existing two-reset / one-writer-per-path design (ref: Q5).

### Decision 3: Eval-doc replacement wording

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | "functional but unwired/orphaned" across all six | Matches ticket AC2 phrasing; accurate per research framing; consistent | Must re-verify `eval-system.md` line citations separately (ref: Q11) |
| B | Delete the eval references entirely | Less to maintain | Loses the (true) status signal; contradicts owner's "leave as worked-example corpus" stance and project MEMORY (ref: Q11, ticket Out of Scope) |

**Recommendation:** Option A
**Rationale:** AC2 wants the docs to "describe its true state (functional but unwired)" — deletion would drop the signal, and the owner explicitly keeps the eval corpus (ref: ticket, Q11).
**NEW PATTERN?** No.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Editing `qrspi-batch.js` dead-path comments using the ticket's stale `~525–561 / ~810–833` line numbers deletes live code | med | high | Re-grep `removed\|no longer\|deleted worker\|the old` against the live 1682-line file; never trust the cited ranges (ref: Q9) |
| Slice 1 and slice 2 both edit `qrspi-batch.js` and collide | med | med | Order slices: 1 (comment removals) before 2 (`doRevise` refactor); slice 1 touches comment lines (48/168/1033/1169/1212…), slice 2 touches `doRevise` (918–1045) — keep edits to disjoint regions (ref: Q9, Slice ordering constraint) |
| Adding `ciCounterAction` to the decision dict breaks callers expecting the exact key set | low | med | Add it via the `decision()` factory so all 8 actions get it defaulted; assert presence in existing `case(...)` runs (ref: Q3, Q10) |
| Thinning `doRevise` drops the `answered.applied` no-amend gate, writing a stale reset on a comment-only PR | low | med | Preserve the JS `applied` confirmation explicitly (Decision 2); regression-check via manual e2e since `qrspi-batch.js` is not unit-testable (ref: Q2, Q5) |
| `docs/eval-system.md` line citations "corrected" to numbers that are themselves wrong | med | low | Re-read the live `evals/run_eval.py` / `revise.py` to confirm true line numbers before editing (ref: Q11) |
| Lifecycle-narrative dedup drops an invariant the resolver/workers key on | low | high | Preserve `Selected/Design Review/Plan Review/Code Review/Done` and the entry-gate wording verbatim in the canonical doc; only remove restatements (ref: Q12) |
| Overlap with live RUS-86/RUS-87/RUS-90 editing the same resolver/batch | med | med | No `blockedBy` edge exists; coordinate at the structure phase per the ticket's coordination note (ref: ticket Coordination note) |

## Open Questions

- OQ1 — **RESOLVED (maintainer, 2026-06-19):** single `ciCounterAction` enum (`bump`/`reset`/`none`), per Decision 1 Option A. The enum is a mutually-exclusive verdict (one action), so a single string field matches its semantics better than two booleans (which would admit an illegal `bump && reset` state) and is consistent with the dict's other string-valued fields (`action`, `reason`). Slice 2 stands as written.
- OQ2 — **RESOLVED (maintainer, 2026-06-19):** moving the bump-vs-reset *verdict* into the resolver is sufficient to satisfy AC4. AC4's intent is "JS no longer *derives* counter state"; once the decision is in the tested resolver and JS only *applies* it, that is met. The trailer *write* (and the `answered.some(a=>a.applied)` confirmation) stays in JS / `qrspi_ci_revise_bump.py` by data-flow necessity — `applied` is only known post-worker, so it cannot move into the pure pre-worker resolver (ref: Q2). No additional write-machinery relocation is expected.
- OQ3 — **DEFERRED to the structure phase (maintainer, 2026-06-19):** which of the five `qrspi_*` files becomes the surviving canonical guide (or a fresh `docs/qrspi-guide.md`) and where `qrspi-orientation.md`'s non-redundant parts land is an editorial choice for `/qrspi-structure` to settle when it scopes Slice 3. (Designer's lean, non-binding: author one fresh consolidated guide rather than promoting an existing file, so no single doc's frame is inherited; lifecycle narrative stays a pointer to `docs/qrspi-pr-gated-lifecycle-design.md`.)
- OQ4 — **DEFERRED to the structure phase (maintainer, 2026-06-19):** whether the `/review-*` shared-loop-reference collapse stays in Slice 3 or becomes its own slice is a slicing decision for `/qrspi-structure`. (Designer's lean, non-binding: split it out — distinct blast radius from the doc merge, four skill files.)
