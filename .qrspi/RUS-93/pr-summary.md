# PR: RUS-93 Upgrade /review-* advisory family: visible findings, honest signal, one engine

**Ticket:** RUS-93
**Design:** design.md @ 2026-06-19T00:00:00Z
**Structure:** structure.md @ 2026-06-19T00:00:00Z

## Summary

The on-demand `/review-{design,plan,implementation}` advisory family was three hand-executed
`SKILL.md` loops (~270–300 lines each) that ran an LLM-driven revise loop over a scratch copy,
dropped the actual finding text at the render boundary, reported a verdict that reflected the
*revised* scratch rather than the artifact as written, and never wired the documented `lensModel`
override. This stack replaces that with a single deterministic engine
(`.claude/workflows/qrspi-review.js`) invoked by three thin SKILL wrappers, makes
`render_synopsis` emit the verbatim blocking finding strings, drops the revise loop so the panel
reports the artifact as written (round 0 only), and wires a new `critics.review.lensModel`
override onto the `*-review` lens spawn. **Reviewer focus:** (1) the propose-only invariant in the
new engine — head SHA is captured in RESOLVE and re-asserted in SYNOPSIS, and the engine emits no
`gt`/`gh` branch-mutating command (only `gh pr` reads + one comment write + a local ledger append);
(2) the non-coupling of `resolve_review_lens_model` from the batch `resolve_design`/`critics.design.*`
path; (3) the render correction that emits finding sub-sections *after* the axis table rather than
between table rows (would break Markdown).

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC #1 — Failing-review synopsis shows the actual blocking finding **text**, not just a per-lens count | `scripts/qrspi_review_synopsis.py:render_synopsis` (+ `_dedupe` helper; per-FAIL `#### Blocking findings — <lens>` sub-sections after the axis table) | `scripts/qrspi_review_synopsis_test.py:test_blocking_finding_strings_surface_verbatim`, `:test_blocking_findings_deduped`, `:test_non_blocking_notes_unchanged_alongside_blocking_findings` |
| AC #2 — Panel reports the artifact **as written** (no scratch-laundered verdict) | `.claude/workflows/qrspi-review.js` runs `synthesize` ONCE (round 0, no revise loop); terminal action = `converged` (round-0 pass) else `exhausted` | `scripts/qrspi_review_synopsis_test.py:test_no_blocking_findings_section_for_passing_lens`, `:test_no_blocking_findings_section_when_fail_has_no_findings` (render of round-0 verdicts); engine path verified by manual e2e (orchestrator-deferred) |
| AC #3 — Deterministic orchestration replaces the hand-driven markdown loop; propose-only preserved | `.claude/workflows/qrspi-review.js` (RESOLVE→`parallel()` fan-out→SYNOPSIS; head-SHA capture + re-assert; no branch write) | `python3 scripts/run_tests.py` (40 passed) guards the Python helpers the engine drives; `node --check` on the engine; grep gate for branch-mutating commands |
| AC #4 — Single source of truth: three SKILLs become thin phase-parameterized wrappers | `.claude/skills/review-{design,plan,implementation}/SKILL.md` collapsed to `Workflow({name:"qrspi-review",args:{ticket,phase}})` | Verified by diff (293/274/267 lines removed); behavior covered transitively by the engine's helper tests |
| AC #5 — Adversarial `*-review` lens runs under the strongest configured model via a wired seam | `scripts/qrspi_critics_config.py:resolve_review_lens_model` reads `critics.review.lensModel`; engine passes it as the `model` override on the `*-review` spawn only | `scripts/qrspi_critics_config_test.py:test_configured_id_returned`, `:test_configured_id_stripped`, `:test_separate_from_design_lens_model_non_coupling` (+ 6 fail-closed cases) |

> AC #6 was dropped per the ticket's 2026-06-19 scope change; the ledger row's `agreement`
> positional is passed an empty block `{}` and `qrspi_review_agreement.compute` is not invoked.

## Changes by Slice

### Slice 1: Surface blocking finding text in the synopsis render

| File | Change | Lines |
|------|--------|-------|
| `scripts/qrspi_review_synopsis.py` | ⚠️ modified | +36, -1 |
| `scripts/qrspi_review_synopsis_test.py` | ⚠️ modified | +41 |

### Slice 2: Add the on-demand `critics.review.lensModel` reader

| File | Change | Lines |
|------|--------|-------|
| `scripts/qrspi_critics_config.py` | ⚠️ modified | +26 |
| `scripts/qrspi_critics_config_test.py` | ⚠️ modified | +63 |

### Slice 3: Deterministic review engine + thin SKILL wrappers + wired lens model

| File | Change | Lines |
|------|--------|-------|
| `.claude/workflows/qrspi-review.js` | ✨ new | +503 |
| `.claude/skills/review-design/SKILL.md` | ⚠️ modified (collapsed to wrapper) | net ≈ -293 |
| `.claude/skills/review-implementation/SKILL.md` | ⚠️ modified (collapsed to wrapper) | net ≈ -274 |
| `.claude/skills/review-plan/SKILL.md` | ⚠️ modified (collapsed to wrapper) | net ≈ -267 |
| `.claude/agents/qrspi-design-critic-design-review.md` | ⚠️ modified (model note → now-wired) | +2, -2 |
| `.claude/agents/qrspi-plan-critic-plan-review.md` | ⚠️ modified (model note → now-wired) | +2, -2 |
| `.claude/agents/qrspi-impl-critic-impl-review.md` | ⚠️ modified (model note → now-wired) | +2, -2 |
| `.claude/agents/qrspi-critic-reviser.md` | ⚠️ modified (marked dormant) | +9 |

> Each implementation commit also appends its session entry to `.qrspi/RUS-93/impl-log.md`
> (+81 across the three slices) — a workflow artifact, not product code.

## Testing Summary

- [x] Slice 1: unit — `python3 scripts/qrspi_review_synopsis_test.py` — 21 passed (16 prior + 5 new)
- [x] Slice 2: unit — `python3 scripts/qrspi_critics_config_test.py` — 59 passed (49 prior + 10 new)
- [x] Slice 2: scoped suite — `python3 scripts/run_tests.py critics` — 1 file passed
- [x] Full suite (every slice) — `python3 scripts/run_tests.py` — 40 passed, 0 failed
- [x] Slice 3: engine syntax — `node --check .claude/workflows/qrspi-review.js` — OK
- [x] Slice 3: static pipeline simulation — synthesize → terminal pick (`converged`/`exhausted`) → `build_record(agreement={})` → `render_synopsis` exercised against the real Slice-1/Slice-2 helpers
- [x] Slice 3: grep gate — no `gt`/`gh` branch-mutating command emitted by the engine
- [ ] Manual e2e against a live ticket PR (post synopsis comment + ledger append, assert unchanged head SHA) — **orchestrator-deferred** (requires live git/gt/gh/Linear, unavailable in the worktree; see Open Items)

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| `render_synopsis` finding placement | Structure: "beneath each FAIL **row** a 'Blocking findings' sub-section" | Sub-sections rendered as a block **after** the per-lens axis table (one `#### Blocking findings — <lens>` per FAIL lens with findings) | Emitting prose between table rows breaks the Markdown table. Finding strings still surface verbatim; the `PASS|FAIL|count` row is unchanged; `render_synopsis(...) -> str` signature unchanged — presentation choice, not a contract change. |
| `scripts/fixtures/contract_seam/review/` (Slice 3, planned ✨ new) | New JS↔Python parser seam fixtures | **Not created** | T14 decision: the engine adds no new JS function that parses Python stdout — every Python call is a command string handed to a worker whose STRUCTURED envelope is JSON-schema-validated at the `agent()` boundary (same as `qrspi-batch.js`). No new parser seam ⇒ no fixtures needed. Recorded in the engine header. |
| Engine → Python stdin feeding | SKILL pattern piped JSON via `printf ... \| python3 - <<'PY'` | Engine WRITES the verdict array / decision-readiness verdict to files; heredocs read them via `sys.argv` paths | The pipe+heredoc construct is broken (both redirect stdin; the heredoc wins, so `python3 -` reads the script, not the JSON). File-arg form is a faithfulness-preserving correction — same helpers, same contract. |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| Batch panels regress when `qrspi_critics_config.py` is touched to expose `lensModel` for plan/impl | **Mitigated.** `DEFAULT_DESIGN_LENSES`/`resolve_design`/the `critics.design.*` envelope + "do NOT couple" comments left untouched; non-coupling asserted by `test_separate_from_design_lens_model_non_coupling`; full suite + critics contract fixture green | Revert slice-2 commit `3f7ee3a`; `resolve_review_lens_model` is additive and has no other caller until slice-3 |
| Propose-only invariant lost in the JS port (stray branch write / dropped SHA assert) | **Mitigated.** Head SHA captured in RESOLVE, re-asserted in SYNOPSIS; engine emits only `gh pr` reads + one `qrspi_comment_reply.py` write + a local ledger append; grep gate confirms no `gt`/`gh` branch-mutating command; both worker prompts carry an explicit prohibition | Revert slice-3 commit `4d1a965`; the three SKILLs were collapsed in the same commit so the hand-driven loop is restored atomically |
| Dropping the revise loop orphans `qrspi-critic-reviser` / the `next_action` call site | **Mitigated.** `qrspi_critic_loop` MODULE retained (still imported by `qrspi_critic_synthesize.py`); only the `qrspi-critic-reviser` AGENT marked dormant; engine never passes `revise` (rejected by `build_record`) | No rollback needed; reviser agent re-activates if the loop is restored |
| JS engine not unit-testable in isolation → orchestration ships under-tested | **Accepted (known strategy).** Substantive logic stays in tested helpers (`synthesize`, `render_synopsis`, `partition_decision_readiness`, `build_record`, new `resolve_review_lens_model`); engine residual is the inlined binary terminal pick, verified by `node --check` + static simulation; live e2e deferred (Open Items) | n/a — matches the documented pure-core/harness-shell split |
| Render change leaks finding text in a way that breaks ledger/summary readers | **Mitigated.** Render is output-only; `ledger_row_fields`/`partition_decision_readiness` signatures unchanged; changes confined to `render_synopsis` body | Revert slice-1 commit `26f79eb` |

No new risks discovered during implementation.

## Open Items

- **Manual end-to-end verification is orchestrator-deferred (T27).** Running each of the three
  `/review-*` commands against a live ticket PR — confirming the synopsis comment posts, the ledger
  row appends with terminal `converged`/`exhausted`, and `gh pr view` shows an unchanged head SHA —
  requires live git/gt/gh/Linear, which are unavailable in this worktree. Must be exercised once
  before/after merge.
- **Worktree admin-dir orphan (infra, recurring).** The worktree admin dir
  (`.git/worktrees/RUS-93`) was repeatedly orphaned/pruned during implementation (the known
  "worktree metadata pruned → orphans" issue). Slice work was file-edits + `python3` verification
  only and completed cleanly, but the finalize/submit worker must health-check
  (`git rev-parse --is-inside-work-tree`) and rebuild the admin dir before each git/gt command, or
  `gt submit` will hard-stop with "not a git repository". Not introduced by this ticket; flagged so
  finalize doesn't mistake it for a code fault.
- **`critics.review.lensModel` is unset by default.** The new seam reads from a key absent from the
  committed `.qrspi/config.example.json`; with no value the `*-review` lens inherits the session
  model (fail-closed `None`). A follow-up could document/seed the key in the example config so the
  Opus-tier intent is realized out of the box.
