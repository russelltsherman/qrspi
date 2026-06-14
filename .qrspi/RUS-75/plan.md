# Implementation Plan — Wire the RUS-58 per-slice edge critic into the doImplementation slice loop

**Structure basis:** structure.md @ 2026-06-14T00:00:00Z
**Generated:** 2026-06-14T00:00:00Z
**Status:** draft
**Total steps:** 12

> **Locate by anchor, not line number.** All `:NNN` references below are from research against the current `qrspi-batch.js` and the design flags them as potentially stale. Re-locate each edit by its named anchor: the `LOOP_DECISION_SCHEMA` constant, the `criticDecision` helper, the `for (const s of setup.slices)` loop, the `let coherenceFindings` / `let previousNotes` declarations, the post-commit point inside the loop, and the finalize worker that runs `gt submit ... --stack`.

## Slice 1: Wire the per-slice edge critic into doImplementation (in-loop call + finalize splice)

All five edits below modify the single file `.claude/workflows/qrspi-batch.js`. They are mutually dependent and every behavioral addition is gated by `if (implCriticCfg.enabled)` so the disabled path stays byte-for-byte unchanged (AC5).

### Setup

1. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — add the `SLICE_DECIDE_SCHEMA` JSON-schema constant immediately after the `LOOP_DECISION_SCHEMA` constant (anchor: the `LOOP_DECISION_SCHEMA` declaration, ~:619). Schema validates the `decide()` envelope (ref: structure New Types, design Delta 1, Q5).
   - **Current:** only `LOOP_DECISION_SCHEMA` exists in that region; no schema for the slice-decide envelope.
   - **After:** new `const SLICE_DECIDE_SCHEMA = { ... }` validating `{ run: boolean, skipReason: string|null, diffBase: string|null, diffHead: string|null }` (required: `run`; nullable string fields), mirroring the shape/style of `LOOP_DECISION_SCHEMA`.

2. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — add the `sliceCriticDecide(t, setup, n)` worker helper, modeled on `criticDecision` (anchor: the `criticDecision` function definition, ~:1251) and placed adjacent to it (ref: structure Contracts, design Delta 2, Q5).
   - **Current:** no helper invokes `qrspi_slice_critic.py decide`; only `criticDecision` (which invokes `qrspi_critic_loop.py`) exists.
   - **After:** `sliceCriticDecide(t, setup, n): dec | null` — pipes `JSON.stringify({ id: t.id, slices: setup.slices })` on stdin to `python3 ${engineCmdFor(r, 'scripts/qrspi_slice_critic.py')} --slice-index ${n}`, validates the response against `SLICE_DECIDE_SCHEMA`, post-checks `typeof out.run === 'boolean'`, returns the parsed `dec` envelope or `null` on any failure. Must inject `t.id` into the projected object (the worker `setup` lacks `id`) (ref: design Risk row 5).

### Core Logic

3. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — declare the cross-iteration accumulator `const perSliceFindings = {}` beside the existing `let coherenceFindings` / `let previousNotes` declarations (anchor: the `let coherenceFindings` / `let previousNotes` block) (ref: structure New Types, design Delta 4, Q8/Q9).
   - **Current:** only `let coherenceFindings` and `let previousNotes` are declared as cross-iteration state.
   - **After:** `const perSliceFindings = {};` added beside them, keyed by 1-based slice number, holding each slice's `runSliceCritic` `residualFindings`.

4. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — insert the in-loop critic block inside `for (const s of setup.slices)`, placed AFTER the per-slice commit and gated by `if (implCriticCfg.enabled)` (anchor: the post-commit point in the slice loop, after the commit-worker call, ~:1885) (ref: structure Slice 1 edit 4, design Delta 3 & 6, AC1/AC2/AC3/AC6).
   - **Current:** the loop implements then commits each slice with no post-commit critic; cross-iteration state is only `previousNotes`.
   - **After:** inside `if (implCriticCfg.enabled)`, in order:
     - `const dec = await sliceCriticDecide(t, setup, s.n);`
     - `if (!dec) return skip(t, r.decision, \`Slice ${s.n} critic decide failed; stopped without shipping.\`);`
     - `if (!dec.run) { log(<critic-skip line, mirroring the coherence "skipping" lines, naming dec.skipReason>); }` — fall through; the slice still ships (this is a critic-skip, NOT a ticket `skip()`).
     - `else { const sc = await runSliceCritic(t, r, wd, s.n, dec, s.planSlice, s.structureSlice, implCriticCfg.maxRounds); if (!sc.ok) return skip(t, r.decision, \`Slice ${s.n} critic spawn failed; stopped without shipping.\`); perSliceFindings[s.n] = sc.residualFindings; }`
   - Note: `alreadyCommitted` slices `continue` before this block, so they never reach the critic (design Current State, Q10) — `dec.run` is also false for them as a second guard.

5. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — extend the finalize worker prompt to splice findings into the correct slice commit messages, amended lowest-N-first, BEFORE the single `gt submit --stack` (anchor: the finalize worker that currently splices `qrspi_pr_body.py --slice 1` then runs `gt submit --publish --stack`, ~:1901-1911) (ref: structure Slice 1 edit 5, design Delta 5, AC4/AC4b).
   - **Current:** finalize splices only `pr-summary.md` into slice-1's commit via `qrspi_pr_body.py --ticket … --slice 1`, then runs one `gt submit --publish --stack`. `coherenceFindings` and `perSliceFindings` never reach a PR body.
   - **After**, the worker performs, in this exact order, all before submit:
     - (a) if `coherenceFindings` is non-empty (after whitespace-stripping): stage it as a JSON array file and run `qrspi_critic_body.py --phase slice --slice 1 --findings-file <staged coherence json>`.
     - (b) for each slice N with non-empty `perSliceFindings[N]` (whitespace-stripped), lowest-N-first: stage as a JSON array file and run `qrspi_critic_body.py --phase slice --slice N --findings-file <staged json>`.
     - (c) the existing slice-1 `pr-summary.md` amend via `qrspi_pr_body.py --ticket … --slice 1`.
     - (d) the existing single `gt submit --publish --stack`.
   - Slice-1 ordering is coherence → slice-1 per-slice findings → pr-summary. **Skip-on-empty is caller-side and mandatory** at (a) and (b): never invoke `qrspi_critic_body.py` for an empty bucket (its empty-findings handling is message-level only; `set_findings` still runs `gt checkout` + `gt modify`, which restacks — design AC4/OQ3). The entire (a)/(b) extension is gated so it only runs on the enabled path (coherence splice gated by the same `coherence.enabled` that produced the findings; per-slice splice runs only when `perSliceFindings` was populated, i.e. `implCriticCfg.enabled`).

### Tests

6. ✨ No new unit tests. The JS glue in `qrspi-batch.js` is not unit-testable in the non-importable workflow; the pure parts (`qrspi_slice_critic.py decide`, `qrspi_critic_body.py`) are already unit-tested as `_test.py` siblings (ref: design AC7, Q14; structure Modified Types: none).

7. Run: `python3 scripts/qrspi_slice_critic_test.py && python3 scripts/qrspi_critic_body_test.py`
   - **Expected:** both existing reducer test suites still pass (regression guard — these scripts are reused unchanged).

8. Run: `node --check .claude/workflows/qrspi-batch.js`
   - **Expected:** the edited workflow file parses with no syntax error.

### Verify Slice 1

9. **Checkpoint:** Manual end-to-end `qrspi-batch` run on a multi-slice ticket with `implCriticCfg.enabled: true`.
   - [ ] Per slice: a `decide` spawn (`sliceCriticDecide`) followed, when `dec.run`, by a `runSliceCritic` run (log lines present).
   - [ ] Residual findings spliced into the matching slice-N PR body; coherence findings (if `coherence.enabled`) on slice-1.
   - [ ] Exactly one `gt submit --publish --stack` for the stack (AC1–AC4b, AC6).

10. **Checkpoint:** Manual end-to-end run with `implCriticCfg.enabled: false`.
    - [ ] Transcript is identical to pre-change: zero `decide`/critic spawns, no findings splice (AC5).

11. **Checkpoint:** Failure-path inspection (force or observe the two failure modes).
    - [ ] A `runSliceCritic` `ok:false` yields `return skip(...)` (no silent ship).
    - [ ] A null `sliceCriticDecide` yields `return skip(...)` (no silent ship) (AC3).

12. **Checkpoint:** Empty-bucket no-op inspection on an enabled run.
    - [ ] An empty `perSliceFindings[N]` or empty `coherenceFindings` incurs no `qrspi_critic_body.py` call and no extra `gt modify`/restack for that bucket (AC4/AC4b, OQ3).

---

## Rollback Notes

- Steps 1–5 are confined to `.claude/workflows/qrspi-batch.js`. No DB migrations, config schema changes, or destructive operations are introduced — `.qrspi/config.json` is read-only here and the `implCriticCfg.enabled: false` default keeps the new path dormant until explicitly opted in.
- To roll back: revert the five edits to `qrspi-batch.js` (`git checkout -- .claude/workflows/qrspi-batch.js` on the slice branch, or close/delete the slice PR/branch per the QRSPI reset flow). No other file, script, or persisted artifact is touched, so revert is a clean single-file restore.
- The reused scripts (`qrspi_slice_critic.py`, `qrspi_critic_body.py`, `runSliceCritic`, `skip`) are unchanged, so there is nothing to roll back outside the workflow file.
