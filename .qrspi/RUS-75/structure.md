# Structure Outline — Wire the RUS-58 per-slice edge critic into the doImplementation slice loop

**Design basis:** design.md @ 2026-06-14T00:00:00Z
**Generated:** 2026-06-14T00:00:00Z
**Status:** draft

## New Types

- `SLICE_DECIDE_SCHEMA` (JSON schema constant in qrspi-batch.js, near `LOOP_DECISION_SCHEMA` :619) — validates the `decide()` envelope shape `{ run: boolean, skipReason: string|null, diffBase: string|null, diffHead: string|null }` for the worker round-trip (ref: design §Delta 1, Q5).
- `perSliceFindings: { [sliceN: number]: string }` — cross-iteration accumulator declared beside `let coherenceFindings` / `previousNotes`, keyed by 1-based slice number, holding each slice's `runSliceCritic` `residualFindings` (ref: design §Delta 4, Q8/Q9).

## Modified Types

- None. No new scripts and no changed Python reducer/helper signatures — `runSliceCritic`, `skip`, and `qrspi_slice_critic.py decide` are reused as-is (ref: design §Delta, Constraints).

## Contracts

- `sliceCriticDecide(t, setup, n): dec | null` — NEW worker helper modeled on `criticDecision` (:1251). Pipes `JSON.stringify({ id: t.id, slices: setup.slices })` on stdin to `python3 ${engineCmdFor(r,'scripts/qrspi_slice_critic.py')} --slice-index ${n}`, validates the response against `SLICE_DECIDE_SCHEMA`, post-checks `typeof out.run === 'boolean'`, returns the parsed `dec` envelope or `null` on failure. Caller must inject `t.id` into the projected `{id, slices}` (the worker `setup` object lacks `id`) (ref: design §Delta 2, AC1, Q1/Q5).
- `runSliceCritic(t, r, wd, sliceN, dec, planSlice, structureSlice, maxRounds): { ok: boolean, residualFindings: string }` — EXISTING helper (:1721), reused unchanged. Called with `s.n`, the parsed `dec`, `s.planSlice`, `s.structureSlice`, and `implCriticCfg.maxRounds` (ref: design AC2, Q2/Q4).
- `skip(t, decision, note): { ticketId, action, summary }` — EXISTING helper, reused. The `ok:false` / null-decide mapping target inside the loop (ref: design AC3, Q12).
- `qrspi_critic_body.py --phase slice --slice N --findings-file <file>` — EXISTING but previously-unwired CLI path, invoked from the finalize worker to splice findings into slice-N's commit message. Caller MUST gate invocation on a non-empty (whitespace-stripped) findings array (ref: design AC4/AC4b, Delta 5, Q6).

## Slice 1: Wire the per-slice edge critic into doImplementation (in-loop call + finalize splice)

**Goal:** With `implCriticCfg.enabled: true`, each slice is critiqued in-loop after its commit (decide → runSliceCritic → skip-on-failure → accumulate residual findings), and all residual + coherence findings are spliced into the correct slice commit messages in the finalize worker before the single `gt submit --stack`. With `implCriticCfg.enabled: false` the transcript is byte-for-byte unchanged. Delivers the complete AC1–AC6 end-to-end critic path verifiable by one batch run.
**Files touched:**

- ⚠️ `.claude/workflows/qrspi-batch.js` — five mutually dependent edits, all guarded by `implCriticCfg.enabled` (the disabled-path invariant, AC5):
  1. Add `SLICE_DECIDE_SCHEMA` constant near `LOOP_DECISION_SCHEMA` (:619) (Delta 1).
  2. Add `sliceCriticDecide(t, setup, n)` worker helper, modeled on `criticDecision` (:1251) (Delta 2).
  3. Declare `const perSliceFindings = {}` beside `let coherenceFindings` / `let previousNotes` (Delta 4).
  4. In-loop critic block inside `for (const s of setup.slices)`, placed AFTER the commit (:1885) and gated by `if (implCriticCfg.enabled)`: call `sliceCriticDecide`; `null → return skip(...)`; `!dec.run → log skip line + fall through (slice ships)`; else `runSliceCritic(...)`, `ok:false → return skip(t, r.decision, \`Slice ${s.n} critic spawn failed; stopped without shipping.\`)`, else `perSliceFindings[s.n] = sc.residualFindings`. Add the `dec.run === false` critic-skip log line (Delta 3, Delta 6).
  5. Finalize worker (:1901-1911), before `gt submit --stack`, amending lowest-N-first: (a) if `coherenceFindings` non-empty → `qrspi_critic_body.py --phase slice --slice 1 --findings-file <staged coherence json>`; (b) for each N with non-empty `perSliceFindings[N]` → `qrspi_critic_body.py --phase slice --slice N --findings-file <staged json>`; (c) existing slice-1 `pr-summary` amend; (d) submit. Slice-1 ordering: coherence → slice-1 per-slice findings → pr-summary. Skip-on-empty is caller-side and mandatory at (a) and (b) — never invoke the script for an empty bucket (Delta 5, AC4/AC4b).
**Verification:**
- [ ] Manual end-to-end `qrspi-batch` run on a multi-slice ticket with `implCriticCfg.enabled: true`: confirm per slice a `decide` spawn + `runSliceCritic` run, residual findings spliced into the matching slice-N PR body, coherence findings (if `coherence.enabled`) on slice-1, single `gt submit --stack` (AC1–AC4b, AC6, AC7).
- [ ] `enabled: false` run produces an identical transcript — zero `decide`/critic spawns, no findings splice (AC5).
- [ ] Confirm an `ok:false` runSliceCritic and a null `sliceCriticDecide` each yield a `skip(...)` (no silent ship) (AC3).
- [ ] Confirm an enabled run with empty `perSliceFindings[N]` / empty `coherenceFindings` incurs no `qrspi_critic_body.py` call (no needless `gt modify`/restack) for that bucket (AC4/AC4b, OQ3).
**Context cost:** M
**Depends on:** none

---

## Unverified Assumptions

- **OQ2 (deferred, accepted):** `previousNotes` for slice N+1 reflects pre-amend code after a revise of slice N — a known soft-staleness the design accepts for first landing (Risk row 3). No code maps to re-deriving notes post-amend; if it proves material it is an out-of-scope follow-up. Flagged for human awareness, not blocking.
- **Exact insertion line numbers** (:619, :1251, :1721, :1810, :1885, :1901-1911) are from research against the current `qrspi-batch.js`; the design itself flags the original ticket's line/param references as stale. Implementation must re-locate by anchor (the `LOOP_DECISION_SCHEMA` constant, the `criticDecision` helper, the `for (const s of setup.slices)` loop, the finalize worker) rather than trusting absolute line numbers.
- **`engineCmdFor(r, 'scripts/qrspi_slice_critic.py')`** is the assumed engine-path helper for the new worker (per the batch worker-cwd convention); the design names it but no signature was independently re-verified in this phase.
