# Implementation Plan — qrspi critics 1/5: edge-critic loop primitive wired into runPhase

**Structure basis:** structure.md @ 2026-06-12T00:00:00Z
**Generated:** 2026-06-12T00:00:00Z
**Status:** draft
**Total steps:** 31

## Slice 1: Pure critic-loop decision module

**Goal:** A standalone, fully-tested decision module that, given parsed verdict(s) + round + cap, returns the converge/revise/cap_reached action — and a fail-closed verdict parser. Verifiable end-to-end via its `_test.py` sibling with zero dependency on `agent()` or the JS orchestrator.

### Setup

1. ✨ Create `scripts/qrspi_critic_loop.py` — new pure decision module, stdlib-only, no agent/IO coupling (ref: structure §Contracts, design §Delta, Pattern 7). Add a module docstring naming it as the testable critic-loop decision core consumed by `runCriticLoop` JS glue.

### Core Logic

2. ✨ In `scripts/qrspi_critic_loop.py`, implement `parse_critic_verdict(text: str) -> dict` — fail-closed parser: extract a JSON object from `text`, coerce to `{pass: bool, findings: list}`; on malformed/empty/unreadable input return `{"pass": False, "findings": []}`; never raises (ref: structure §Contracts, design Decision 2, Q11). Signature: `parse_critic_verdict(text: str) -> dict`.

3. ✨ In `scripts/qrspi_critic_loop.py`, implement `next_action(verdicts: list, round: int, max_rounds: int) -> dict` — returns `{"action": "converged"|"revise"|"cap_reached", "residual_findings": [...]}`: `converged` when the latest verdict's `pass` is truthy; `cap_reached` when not passed and `round + 1 >= max_rounds` (surfacing the latest verdict's findings as `residual_findings`); else `revise` (ref: structure §Contracts, design §Delta, AC2, AC4). Signature: `next_action(verdicts: list, round: int, max_rounds: int) -> dict`.

### Tests

4. ✨ Create `scripts/qrspi_critic_loop_test.py` — stdlib-only assert-based sibling importing `qrspi_critic_loop`; no third-party deps, no test runner (ref: structure §Slice 1 tests, Pattern 7).

5. ✨ In `scripts/qrspi_critic_loop_test.py`, add assertion: `next_action` with a passing verdict at `round == 0` returns `action == 'converged'` and triggers no revise (AC4).

6. ✨ In `scripts/qrspi_critic_loop_test.py`, add assertion: fail→revise→pass sequence — a non-passing verdict at `round == 0`, `max_rounds == 2` returns `action == 'revise'`; a passing verdict on the next round returns `action == 'converged'` (AC2).

7. ✨ In `scripts/qrspi_critic_loop_test.py`, add assertion: a non-passing verdict at `round == max_rounds - 1` returns `action == 'cap_reached'` with `residual_findings` carrying the latest findings (AC2, AC4).

8. ✨ In `scripts/qrspi_critic_loop_test.py`, add assertion: `parse_critic_verdict` on a malformed string, empty string, and non-JSON garbage each return `{"pass": False, ...}` and never raise (Q11).

9. Run: `python3 scripts/qrspi_critic_loop_test.py`
   - **Expected:** exits 0 with all asserts passing.

### Verify Slice 1

10. **Checkpoint:** `python3 scripts/qrspi_critic_loop_test.py`
    - [ ] Exits 0 with all asserts passing.
    - [ ] A malformed/empty string into `parse_critic_verdict` returns `{pass: False, ...}` (never raises).
    - [ ] `next_action` with a passing verdict on round 0 returns `action == 'converged'`; with a non-passing verdict at `round == max_rounds - 1` returns `action == 'cap_reached'` carrying residual findings.

---

## Slice 2: Critic agent + slash-command wrapper

**Goal:** A registered typed critic agent (frontier model, edge-oriented system prompt) plus its slash-command wrapper, so `runCriticLoop` has a concrete `agentType` to spawn. Verifiable by direct invocation against a sample upstream+produced artifact pair, independent of the JS loop wiring.

### Setup

11. ✨ Create `.claude/agents/qrspi-critic.md` — new typed agent file. Frontmatter: `name: qrspi-critic`, `tools: Read` (the schema'd-return path of Decision 2 means no staged verdict file ⇒ no `Write`; add `Write` only if Slice 2 verification reveals a staged-verdict path is needed) (ref: structure §Slice 2, design §Delta, Decision 2, Q5).

### Core Logic

12. ⚠️ In `.claude/agents/qrspi-critic.md`, author the edge-critic system prompt body — consumes `UPSTREAM_PATH` (the rubric anchor) and `ARTIFACT_PATH` (the produced artifact) plus `RUBRIC`/phase inputs; instructs the agent to judge the produced artifact as a faithful *derivation of its upstream input* (review the EDGE not the node), and to emit `{pass: bool, findings: [...]}` per `CRITIC_VERDICT_SCHEMA` (ref: structure §Slice 2, design AC3, Decision 2).
    - **Current:** file does not exist.
    - **After:** edge-critic prompt that reads both paths and returns a schema-shaped `{pass, findings}` verdict.

13. ✨ Create `.claude/skills/qrspi-critic/SKILL.md` — slash-command wrapper for the critic agent per the project convention (ref: structure §Slice 2, design §Delta, Q5). Authored via the skill-creator skill (project convention for skill creation).

### Tests

14. ✨ Prepare a sample fixture pair: an upstream artifact and a faithful produced artifact (a derivation that preserves every upstream requirement), plus a degraded produced artifact that drops one upstream requirement (for the negative case in step 16).

15. Direct critic invocation on the faithful produced artifact (fixture from step 14).
    - **Expected:** returns `pass: true`.

16. Direct critic invocation on the degraded produced artifact (fixture from step 14, drops an upstream requirement).
    - **Expected:** returns `pass: false` with a finding naming the dropped requirement.

### Verify Slice 2

17. **Checkpoint:** parse agent frontmatter and run the two direct invocations from steps 15-16
    - [ ] `name: qrspi-critic` frontmatter present; `tools` limited to `Read` (+`Write` iff a staged verdict file is used).
    - [ ] Direct critic invocation on a faithful produced artifact returns `pass: true`.
    - [ ] Direct critic invocation on an artifact dropping an upstream requirement returns `pass: false` with a finding naming the dropped requirement.
    - [ ] skill-creator eval loop run on the wrapper (per project convention for skill creation).

---

## Slice 3: Wire `runCriticLoop` into `runPhase` and enable it for design/plan

**Goal:** End-to-end critic loop active in the orchestrator: `runPhase` gains the optional `criticConfig`; the guarded loop runs produce→critique→revise within the pre-persist staging window; `doDesign`/`doPlan` pass a per-phase `criticConfig`; residual findings on cap-reached are spliced into the design/plan finalize commit body (which seeds the PR). No-critic phases remain byte-for-byte unchanged.

### Setup

18. Read the schemas section, `runPhase`, `doDesign`, and `doPlan` in `.claude/workflows/qrspi-batch.js` to confirm the exact `runPhase` body, the `stg`/`art` helper call shapes, and the existing design/plan finalize-prompt seam. This read resolves the structure's Unverified Assumptions (exact `runCriticLoop` signature/context params; whether the reviser is a re-prompted phase agent or a distinct agent; the finalize-body seam) before any edit.

19. **Decision point (from structure §Unverified Assumptions):** Against the finalize code read in step 18, choose ONE body path: (A) new `scripts/qrspi_critic_body.py` helper mirroring `qrspi_pr_body.py` (token-free staged file spliced into the finalize commit message), or (B) fold a staged-body splice directly into the existing design/plan finalize prompt if it already exposes a clean staged-body seam (ref: design Decision 4, Inconsistency 4). Record the chosen path; it governs whether steps 28-29 execute.

### Core Logic

20. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — add `CRITIC_VERDICT_SCHEMA` in the schemas section: a JS-object JSON-Schema for `{pass: bool, findings: list}` (findings as a free-form list; pin the per-element shape here) (ref: structure §Modified Types, design Decision 2, Q6).
    - **Current:** no `CRITIC_VERDICT_SCHEMA` in the schemas section.
    - **After:** `CRITIC_VERDICT_SCHEMA` defined alongside the other StructuredOutput schemas.

21. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — add `runCriticLoop(name, id, criticConfig, ...ctx)` returning `{ok: bool, residualFindings: list}`. Reads the upstream artifact via `art(wd, id, criticConfig.upstream)` and the produced artifact via `stg(id, name)`; loops `for (let round = 0; round < (criticConfig.maxRounds ?? 2); round++)`, spawning exactly ONE critic agent per round (single-critic, not `parallel()` — OQ2) with `agent({schema: CRITIC_VERDICT_SCHEMA, agentType:'qrspi-critic'})`; passes the parsed verdict(s) + round + cap to `qrspi_critic_loop.py`'s `next_action`; breaks on `converged`; on `revise` spawns a reviser that rewrites `stg(id, name)` in place; on `cap_reached` returns success with `residualFindings` (ref: structure §Contracts JS glue, design Decision 1/3, AC1-AC4). Use the exact context-param list and reviser agent-type resolved in step 18.
    - **Current:** no `runCriticLoop` function.
    - **After:** `runCriticLoop(name, id, criticConfig, ...ctx) -> {ok, residualFindings}` present, delegating the converge/continue/cap decision to the python module.

22. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — add trailing OPTIONAL `criticConfig` param to `runPhase` and insert the guarded loop between produce-success and the persist gate (ref: structure §Modified Types, design Decision 1, AC1, Q9).
    - **Current:** `runPhase(name, agentType, prompt, existing, id, phaseLabel)` — produce, persist, log+return.
    - **After:** `runPhase(name, agentType, prompt, existing, id, phaseLabel, criticConfig)` — after produce-success, `if (criticConfig) { const cr = await runCriticLoop(name, id, criticConfig, ...ctx); /* thread cr.residualFindings */ }`, then the unchanged persist gate; `criticConfig` absent ⇒ `undefined` ⇒ guard false ⇒ four current statements run verbatim.

23. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — in `doDesign`, pass a `criticConfig` to the design artifact's `runPhase` call: `{upstream: 'research.md', maxRounds: <N>}` (its own `maxRounds`, default 2 when omitted) (ref: structure §Slice 3, design §Delta, OQ4).
    - **Current:** `doDesign` calls `runPhase(...)` with 6 positional args for the design artifact.
    - **After:** the design `runPhase` call passes a 7th `criticConfig` arg anchored on `research.md`.

24. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — in `doPlan`, pass a `criticConfig` to the plan artifact's `runPhase` call: `{upstream: 'structure.md', maxRounds: <N>}` (its own `maxRounds`, default 2 when omitted) (ref: structure §Slice 3, design §Delta, OQ4).
    - **Current:** `doPlan` calls `runPhase(...)` with 6 positional args for the plan artifact.
    - **After:** the plan `runPhase` call passes a 7th `criticConfig` arg anchored on its upstream artifact.

25. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — thread `runCriticLoop`'s `residualFindings` from `runPhase` back to `doDesign`/`doPlan` and into the finalize commit body via the body path chosen in step 19 (ref: structure §Slice 3, design Decision 4).
    - **Current:** design/plan finalize commit body is a bare commit subject; no residual-findings channel.
    - **After:** on cap-reached, residual findings are spliced into the finalize commit message that seeds the PR body.

26. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — surface critic rounds / per-round pass-fail / cap-reached via `log(...)` lines inside `runCriticLoop`/`runPhase`, and fold a one-line critic summary into `res.summary` (ref: structure §Slice 3, design §Delta, Q14).
    - **Current:** `runPhase` reports via `log(...)` and a bare boolean only.
    - **After:** per-round critic outcomes logged; a critic summary folded into `res.summary`.

### Tests

27. ✨ (Body path A only — per step 19) Create `scripts/qrspi_critic_body.py` mirroring `qrspi_pr_body.py`: write residual findings to a token-free staged file and splice it into the design/plan finalize commit message (ref: structure §Slice 3, design Decision 4). Skip if step 19 chose path B.

28. ✨ (Body path A only — per step 19) Create `scripts/qrspi_critic_body_test.py` — stdlib-only assert-based sibling covering the splice/staging behavior (ref: structure §Slice 3). Skip if step 19 chose path B.

29. Run (body path A only): `python3 scripts/qrspi_critic_body_test.py`
    - **Expected:** exits 0 with all asserts passing.

### Verify Slice 3

30. **Checkpoint:** diff inspection of `.claude/workflows/qrspi-batch.js` plus a manual e2e on one design run
    - [ ] Diff confirms all existing `runPhase(...)` call sites still pass 6 positional args (`criticConfig` is `undefined`) — byte-for-byte unchanged no-critic behavior (AC1, Q9).
    - [ ] `python3 scripts/qrspi_critic_body_test.py` exits 0 (if the helper was created in step 27).
    - [ ] Manual e2e: with a `criticConfig`, logs show round 0 critique; a passing artifact ⇒ exactly one critic call, zero revise calls (AC4); a deliberately-degraded artifact ⇒ critique→revise→re-critique within the cap; cap-reached ⇒ loop returns success, phase finalizes, residual findings appear in the PR body (AC2).
    - [ ] Persist still gates: reviser rewrites `stg(id,name)` non-empty; persist moves it to `art(...)` (no `ok:false` from an emptied artifact).

---

## Rollback Notes

- **Step 22** (`runPhase` signature change): the trailing param is optional and `undefined` for all existing call sites, so reverting is a clean removal of the param + the `if (criticConfig)` block; no call-site edits needed to roll back.
- **Steps 23-24** (`doDesign`/`doPlan` `criticConfig` args): remove the 7th positional arg from those two `runPhase` calls to disable the critic loop entirely while leaving Slice 1/2 artifacts in place.
- **Step 25** (finalize-body splice): if the residual-findings splice corrupts the design/plan commit message (heredoc shell-quoting), revert to the bare commit subject; the loop still functions, only the PR-body surfacing is lost.
- **No DB migrations, no destructive ops, no config changes** — this is orchestration + new-file additions only; the only mutated file is `.claude/workflows/qrspi-batch.js`, reversible via git.
