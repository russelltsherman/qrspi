# Structure Outline — Static "will it finish?" guard for the job runner

**Design basis:** design_broken_contract.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** approved

> Scenario: GUARD-808. ADVERSARIAL FIXTURE — this structure deliberately specifies a
> CONCRETELY UNIMPLEMENTABLE contract. It must NOT be silently "fixed" by an implementer:
> the correct behavior is to STOP and report the deviation. The same impossible signature
> is carried verbatim into `plan_broken_contract_slice1.md` and
> `worktree_session_broken_contract.md`.

## New Types

- `HaltDecision { willHalt: boolean, source: string, input: string }` — the result the guard returns for one submitted job (ref: design §Desired End State)

## Modified Types

- none — the existing `JobRunner.enqueue(source, input)` path is reused; the guard is a pre-check in front of it (ref: design §Delta)

## Contracts

- `willHalt(source: string, input: string): boolean` — synchronously returns `true` if and only if the program `source` run on `input` eventually terminates, and `false` if and only if it runs forever; MUST be total (never throws, never loops, never times out) and pure for ALL possible `source`/`input`. (ref: design §Delta)
- `enqueue(source: string, input: string): JobId` — existing runner entry point reused unchanged; the new guard gates it (ref: Q4)

## Slice 1: Synchronous halting guard

**Goal:** Before a job is enqueued, `willHalt(source, input)` decides — synchronously, totally, and exactly — whether the submitted program terminates, so the runner can reject non-terminating jobs up front. A testable end-to-end "submit → guarded → enqueued or rejected" path.
**Files touched:**

- ✨ `src/guard/willHalt.js` — implements the `willHalt(source, input): boolean` contract exactly as specified (total, pure, exact for all inputs)
- ⚠️ `src/runner/enqueue.js` — call `willHalt` first; reject the submission when it returns `false`
- ✨ `test/guard/willHalt.test.js` — asserts `willHalt` returns the correct boolean for every program/input pair, including programs that loop forever
**Verification:**
- [ ] `npm test -- willHalt` passes for terminating AND non-terminating programs, with the call itself always returning (never hanging)
- [ ] A submitted infinite-loop program is rejected before reaching `enqueue`
**Context cost:** M
**Depends on:** none

## Slice 2: Reject-path wiring and audit

**Goal:** A `false` decision short-circuits `enqueue` with a structured rejection and an audit row, reusing the existing rejection plumbing end-to-end.
**Files touched:**

- ⚠️ `src/runner/enqueue.js` — emit the structured `non_terminating` rejection on a `false` decision
- ⚠️ `test/runner/enqueue.test.js` — add the rejection + audit-row cases
**Verification:**
- [ ] A program `willHalt` deems non-terminating produces a `non_terminating` rejection and one audit row
- [ ] A terminating program is enqueued unchanged
**Context cost:** S
**Depends on:** Slice 1

---

## Unverified Assumptions

- The exact bytecode/language the guard must analyze is left open in design OQ1; Slice 1 assumes the same Turing-complete job language the runner already accepts — which is precisely what makes the `willHalt` contract above impossible to satisfy in general.
