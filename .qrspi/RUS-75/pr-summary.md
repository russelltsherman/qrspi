# PR: RUS-75 Wire the per-slice edge critic into doImplementation

**Ticket:** RUS-75
**Design:** design.md @ 2026-06-14T00:00:00Z
**Structure:** structure.md @ 2026-06-14T00:00:00Z

## Summary

This wires the already-built-but-dead RUS-58 per-slice edge critic (`runSliceCritic`)
and the pure `qrspi_slice_critic.py decide` reducer into the `doImplementation` slice
loop in `.claude/workflows/qrspi-batch.js`. With `implCriticCfg.enabled: true`, each
slice is now critiqued in-loop right after its commit (decide → `runSliceCritic` →
skip-on-failure → accumulate residual findings), and both per-slice and the previously
unsurfaced in-memory `coherenceFindings` are spliced into the correct slice commit
messages in the finalize worker — lowest-N-first — before the single `gt submit --stack`.
The change is a single file, all five edits gated by `implCriticCfg.enabled`, so the
disabled path stays byte-for-byte unchanged (AC5). **Reviewer focus:** (1) the disabled-path
invariant — that no extra worker spawns or finalize-prompt bytes appear when the gate is
off; (2) the no-silent-ship invariant — every `ok:false` / null-decide maps to `skip(...)`;
(3) the caller-side skip-on-empty findings gate that avoids needless `gt modify`/restack.

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: After each commit, when enabled, invoke `decide(setup, s.n)` via a worker; `run:false` is a critic-skip, not a ticket skip | `qrspi-batch.js:sliceCriticDecide` + in-loop block (`if (!dec.run) log(...)`) | Manual e2e (T8, deferred); pure reducer covered by `scripts/qrspi_slice_critic_test.py` (8 passed) |
| AC2: When `dec.run`, call `runSliceCritic(t, r, wd, s.n, dec, s.planSlice, s.structureSlice, implCriticCfg.maxRounds)` | `qrspi-batch.js` in-loop `else` branch | Manual e2e (T8, deferred); `node --check` parse |
| AC3: `runSliceCritic` `ok:false` → `return skip(...)`; no silent ship | `qrspi-batch.js` `if (!sc.ok) return skip(...)` | Manual e2e (T8, deferred) |
| AC4: Per-slice residual findings spliced into slice-N commit via `qrspi_critic_body.py --phase slice`, lowest-N-first, before submit; empty buckets skipped caller-side | `qrspi-batch.js` `spliceTargets` + `findingsSpliceStep` + `nonEmpty()` | `scripts/qrspi_critic_body_test.py` (41 passed); manual e2e (T8) |
| AC4b: In-memory `coherenceFindings` also spliced into slice-1 (coherence → slice-1 per-slice → pr-summary), skip-on-empty | `qrspi-batch.js` `spliceTargets.push({slice:1, kind:'coherence'...})` | `scripts/qrspi_critic_body_test.py` (41 passed); manual e2e (T8) |
| AC5: Disabled path (`enabled:false`) byte-for-byte unchanged | Entire critic block inside `if (implCriticCfg.enabled)`; `findingsSpliceStep` is `''` when buckets empty | Verified by inspection (impl-log); manual disabled-run transcript (T8, deferred) |
| AC6: Critic runs in-loop, before next slice builds, so restack ordering holds | In-loop placement after commit, before next iteration | Manual e2e (T8, deferred) |
| AC7: Verified by a manual multi-slice e2e batch run with enabled true/false | n/a (operator verification) | Manual e2e (T8, deferred — operator-run) |

## Changes by Slice

### Slice 1: Wire the per-slice edge critic into doImplementation (in-loop call + finalize splice)

| File | Change | Lines |
|------|--------|-------|
| `.claude/workflows/qrspi-batch.js` | modified | +95, -1 |

Five mutually dependent edits, all gated by `implCriticCfg.enabled`:

1. `SLICE_DECIDE_SCHEMA` constant (after `LOOP_DECISION_SCHEMA`) — validates the `decide` envelope `{run, skipReason, diffBase, diffHead}`.
2. `sliceCriticDecide(t, setup, n)` worker helper (after `criticDecision`) — injects `t.id` into the `{id, slices}` stdin blob, validates, returns the envelope or `null`.
3. `const perSliceFindings = {}` cross-iteration accumulator (beside `let coherenceFindings`).
4. In-loop gated critic block after the per-slice commit: decide → null⇒`skip()` → `!dec.run`⇒critic-skip log (slice ships) → else `runSliceCritic` → `ok:false`⇒`skip()` → store `residualFindings`.
5. Finalize worker: `findingsSpliceStep` injected as step 1b (coherence→slice-1, then per-slice lowest-N-first), BEFORE the existing pr-summary slice-1 splice and the single `gt submit --stack`; caller-side mandatory skip-on-empty via `nonEmpty()`.

(The other 7 changed files in the diff are RUS-75 phase artifacts under `.qrspi/RUS-75/` — questions.md, research.md, design.md, structure.md, plan.md, worktree.md, impl-log.md — not source code.)

## Testing Summary

- [x] Slice 1: regression guard — `python3 scripts/qrspi_slice_critic_test.py` — 8 passed, 0 failed (decide reducer reused unchanged)
- [x] Slice 1: regression guard — `python3 scripts/qrspi_critic_body_test.py` — 41 passed, 0 failed (findings-splice CLI reused unchanged)
- [x] Slice 1: syntax — `node --check .claude/workflows/qrspi-batch.js` — parses, no error
- [x] Disabled-path invariant (AC5) — verified by inspection: when `implCriticCfg.enabled` is false, `perSliceFindings` stays `{}`, `coherenceFindings` stays `[]`, `spliceTargets` is empty, `findingsSpliceStep` interpolates to `''` — finalize prompt unchanged
- [ ] Manual e2e (T8, AC7) — multi-slice batch run with critic enabled (per-slice decide+critic+splice, coherence→slice-1, single `gt submit --stack`) AND disabled (identical transcript); failure-path (`ok:false`/null-decide → skip) and empty-bucket (no `qrspi_critic_body.py` call) inspection — deferred, operator-run; not automatable from the implementation agent

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| `sliceCriticDecide` engine-path helper | `engineCmdFor(r, 'scripts/qrspi_slice_critic.py')` | `engineCmd('scripts/qrspi_slice_critic.py')` | The decide worker's cwd is the MAIN REPO ROOT (it pipes the blob on stdin and runs the pure shim there), matching the modeled `criticDecision`. `engineCmd` is the correct anchor for a main-root worker; `engineCmdFor(r, ...)` resolves to the worktree and is for worker-cwd-in-worktree prompts (the in-loop critic/revise and finalize splice, which DO use `engineCmdFor`). Behavior identical to `criticDecision`. |
| `runSliceCritic(...): { ok, residualFindings: string }` | `residualFindings` typed as a string | Existing helper actually returns `residualFindings` as a string ARRAY | Doc-vs-code mismatch in the structure text; resolved in favor of the real (unchanged) signature. Stored the array as-is into `perSliceFindings[s.n]`; the finalize splice writes a JSON array file, which is exactly what `qrspi_critic_body.py --findings-file` expects. No code changed. |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| Disabled path regresses (extra spawn / behavior change), violating AC5 | mitigated — entire critic block wrapped in `if (implCriticCfg.enabled)`; `findingsSpliceStep` is `''` when empty; verified by inspection. Live disabled-transcript check still pending (T8) | Revert the single commit on `.claude/workflows/qrspi-batch.js` |
| `ok:false` falls through to submit — silent ship of an un-critiqued/failed-revise slice | mitigated — both `runSliceCritic` `ok:false` and a null `sliceCriticDecide` map to `return skip(...)` | Revert the single commit |
| `previousNotes` for slice N+1 reflects pre-amend code after a revise of slice N | accepted (known soft-staleness, OQ2 deferred) — revise edits rarely change "notes for next session"; re-deriving notes post-amend is an out-of-scope follow-up | n/a (no behavior to roll back; deferred) |
| Findings spliced into the wrong PR body (per-slice on slice-1 or vice-versa) | mitigated — `perSliceFindings[N]` and `coherenceFindings` kept as distinct buckets; per-slice → `--slice N`, coherence → `--slice 1`; never merged | Revert the single commit |
| `decide`'s `setup` projection omits `id` (yielding `None/slice-N` branch names) | mitigated — `sliceCriticDecide` injects `t.id` into the projected `{id, slices}` blob before piping | Revert the single commit |
| Coherence-findings splice still unwired, leaving a half-finished finalize | mitigated — coherence-findings splice wired into the same finalize step (AC4b); gated by the same `coherence.enabled` that produced the findings | Revert the single commit |

## Open Items

- **T8 / AC7 manual e2e verification deferred (operator-run):** a live multi-slice `qrspi-batch` run with the critic enabled and disabled, plus failure-path (`ok:false`/null-decide → `skip`) and empty-bucket (no `qrspi_critic_body.py` call) inspection. Not automatable from the implementation agent (no Linear/batch invocation, no git/gt mutation in scope). Flagged for the verification reviewer.
- **OQ2 (deferred, accepted):** `previousNotes` for slice N+1 reflects pre-amend code after a revise of slice N — known soft-staleness accepted for first landing. If it proves material, a follow-up ticket should re-derive notes-for-next-session post-amend.
- **Structure doc-vs-code mismatches (informational):** the structure text typed `runSliceCritic`'s `residualFindings` as a string (real signature is a string array) and named `engineCmdFor` for the decide worker (correct anchor is `engineCmd`). Both resolved in implementation; structure.md text could be corrected in a future pass but no code change is owed.
