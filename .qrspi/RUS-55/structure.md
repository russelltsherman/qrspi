# Structure Outline — qrspi critics 1/5: edge-critic loop primitive wired into runPhase

**Design basis:** design.md @ 2026-06-12T00:00:00Z
**Generated:** 2026-06-12T00:00:00Z
**Status:** draft

## New Types

- `CriticConfig { maxRounds?: int, upstream: string, rubric?: string }` — per-phase critic configuration object passed as the trailing optional arg to `runPhase`; `maxRounds` defaults to 2 when omitted, `upstream` names the upstream artifact basename (e.g. `"research.md"`) used as the edge rubric anchor (ref: design §Delta, OQ2, OQ4).
- `CriticVerdict { pass: bool, findings: list[Finding] }` — the critic agent's reply, schema-validated by `CRITIC_VERDICT_SCHEMA` at the runner boundary (ref: design §Pattern Decision 2).
- `Finding { ... }` — one critic finding (free-form text item in the `findings` list; surfaced into the finalize commit body on cap-reached) (ref: design §Desired End State AC2).
- `LoopDecision { action: 'converged'|'revise'|'cap_reached', residual_findings: list }` — return shape of the pure python decision function (ref: design §Delta `qrspi_critic_loop.py`).

## Modified Types

- `runPhase(name, agentType, prompt, existing, id, phaseLabel)` — add trailing OPTIONAL param `criticConfig` ⇒ `runPhase(name, agentType, prompt, existing, id, phaseLabel, criticConfig)`. Absent ⇒ `undefined` ⇒ guard false ⇒ four current statements run verbatim (ref: design §Delta, AC1, Q9).
- `CRITIC_VERDICT_SCHEMA` — new entry in the schemas section of `qrspi-batch.js` (a JS-object JSON-Schema for `{pass, findings}`) (ref: design §Delta, Decision 2).

## Contracts

Python module `scripts/qrspi_critic_loop.py` (pure, no agent/IO coupling):

- `next_action(verdicts: list, round: int, max_rounds: int) -> dict` — given the parsed verdict(s) for the current round, returns `{action: 'converged'|'revise'|'cap_reached', residual_findings: [...]}`. `converged` when latest verdict passes; `cap_reached` when not passed and `round + 1 >= max_rounds`; else `revise` (ref: design §Delta, AC2, AC4).
- `parse_critic_verdict(text: str) -> dict` — fail-closed parser; returns `{pass: False, findings: [...]}` on malformed/empty/unreadable input; never throws (defensive backstop for residual weak-model-stall risk) (ref: design §Delta, Decision 2, Q11).

JS glue in `.claude/workflows/qrspi-batch.js`:

- `runCriticLoop(name, id, criticConfig, ...ctx) -> {ok: bool, residualFindings: list}` — agent-spawn glue: reads upstream artifact from `art(wd, id, criticConfig.upstream)` and the produced artifact from `stg(id, name)`; loops `for (let round = 0; round < (criticConfig.maxRounds ?? 2); round++)`, spawns exactly ONE critic agent per round (single-critic, not `parallel()` — OQ2), critiques first, breaks on `pass`, else spawns a reviser that rewrites `stg(id, name)` in place; delegates the converge/continue/cap decision to the python module; returns success + residual findings (ref: design §Delta, Decision 1, Decision 3, AC1-AC4).
- `CRITIC_VERDICT_SCHEMA` — StructuredOutput contract for `agent({schema})` critic calls (ref: design Decision 2).

## Slice 1: Pure critic-loop decision module

**Goal:** A standalone, fully-tested decision module that, given parsed verdict(s) + round + cap, returns the converge/revise/cap_reached action — and a fail-closed verdict parser. Verifiable end-to-end via its `_test.py` sibling with zero dependency on `agent()` or the JS orchestrator.
**Files touched:**

- ✨ `scripts/qrspi_critic_loop.py` — `next_action(verdicts, round, max_rounds)` returning `{action, residual_findings}`; `parse_critic_verdict(text)` failing closed to `{pass:false}` (ref: design §Delta).
- ✨ `scripts/qrspi_critic_loop_test.py` — stdlib-only assert-based sibling covering: pass-first-round (no revise / `converged` on round 0), fail→revise→pass, fail→cap→`cap_reached` surfaces residual findings, malformed/empty verdict fails closed to NOT-passed (ref: design §Delta tests, AC2, AC4, Q11/Q12/Q13).
**Verification:**
- [ ] `python3 scripts/qrspi_critic_loop_test.py` exits 0 with all asserts passing.
- [ ] A malformed/empty string into `parse_critic_verdict` returns `{pass: False, ...}` (never raises).
- [ ] `next_action` with a passing verdict on round 0 returns `action == 'converged'`; with a non-passing verdict at `round == max_rounds - 1` returns `action == 'cap_reached'` carrying the residual findings.
**Context cost:** S
**Depends on:** none

## Slice 2: Critic agent + slash-command wrapper

**Goal:** A registered typed critic agent (frontier model, edge-oriented system prompt) plus its slash-command wrapper, so `runCriticLoop` has a concrete `agentType` to spawn. Verifiable by direct invocation against a sample upstream+produced artifact pair, independent of the JS loop wiring.
**Files touched:**

- ✨ `.claude/agents/qrspi-critic.md` — `name: qrspi-critic`, `tools: Read` (plus `Write` only if it stages a verdict file); body is the edge-critic system prompt consuming `UPSTREAM_PATH`, `ARTIFACT_PATH`, `RUBRIC`/phase inputs; emits `{pass, findings}` per `CRITIC_VERDICT_SCHEMA` (ref: design §Delta, Decision 2, Q5).
- ✨ `.claude/skills/qrspi-critic/SKILL.md` (+ any reference files) — slash-command wrapper per the convention (ref: design §Delta, Q5). Authored via the skill-creator skill.
**Verification:**
- [ ] Agent file parses: `name: qrspi-critic` frontmatter present; `tools` limited to Read (+Write iff staging).
- [ ] Direct critic invocation on a faithful produced artifact returns `pass: true`; on an artifact that drops an upstream requirement returns `pass: false` with a finding naming the dropped requirement (edge-oriented: judges the produced artifact as a derivation of its upstream).
- [ ] skill-creator eval loop run on the wrapper (per project convention for skill creation).
**Context cost:** M
**Depends on:** none

## Slice 3: Wire `runCriticLoop` into `runPhase` and enable it for design/plan

**Goal:** End-to-end critic loop active in the orchestrator: `runPhase` gains the optional `criticConfig`; the guarded loop runs produce→critique→revise within the pre-persist staging window; `doDesign`/`doPlan` pass a per-phase `criticConfig`; residual findings on cap-reached are spliced into the design/plan finalize commit body (which seeds the PR). No-critic phases remain byte-for-byte unchanged.
**Files touched:**

- ⚠️ `.claude/workflows/qrspi-batch.js` — (1) add `CRITIC_VERDICT_SCHEMA` in the schemas section; (2) add `runCriticLoop(...)` JS glue calling `qrspi_critic_loop.py` for the decision and spawning single critic + reviser per round, rewriting `stg(id,name)` in place; (3) add trailing optional `criticConfig` param to `runPhase`, inserting `if (criticConfig) { ... }` guarded loop between produce-success and the persist gate; (4) in `doDesign`/`doPlan`, pass a `criticConfig` per artifact (each with its own `maxRounds`, default 2) and thread residual findings into the finalize commit body; (5) surface rounds / per-round pass-fail / cap-reached via `log(...)` and fold a summary into `res.summary` (ref: design §Delta, Decision 1/3/4, AC1-AC4, Q7/Q8/Q9/Q14).
- ✨ `scripts/qrspi_critic_body.py` (+ `scripts/qrspi_critic_body_test.py`) — small helper that writes residual findings to a token-free staged file and is spliced into the design/plan finalize commit message, mirroring `qrspi_pr_body.py` to dodge heredoc shell-quoting (ref: design §Delta Decision 4, Inconsistency 4). [If the existing finalize prompt already exposes a clean staged-body seam, fold the splice into prompt-fed staging instead of a new helper — see Unverified Assumptions.]
**Verification:**
- [ ] Diff confirms all existing `runPhase(...)` call sites are untouched (each still passes 6 positional args; `criticConfig` is `undefined`) — byte-for-byte unchanged no-critic behavior (AC1, Q9).
- [ ] `python3 scripts/qrspi_critic_body_test.py` exits 0 (if the helper is created).
- [ ] Manual e2e on one design run: with a `criticConfig`, logs show round 0 critique; a passing artifact ⇒ exactly one critic call, zero revise calls (AC4); a deliberately-degraded artifact ⇒ critique→revise→re-critique within the cap; cap-reached ⇒ loop returns success, phase finalizes, residual findings appear in the PR body (AC2).
- [ ] Persist still gates: reviser rewrites `stg(id,name)` non-empty; persist moves it to `art(...)` (no `ok:false` from an emptied artifact).
**Context cost:** M
**Depends on:** Slice 1, Slice 2

---

## Unverified Assumptions

- **Finalize-body seam (Decision 4).** The design says design/plan have NO body mechanism today (the body is a bare commit subject) and Decision 4 is "mirror `qrspi_pr_body.py`'s file-splice … a small new helper or prompt-fed staged body is required." Whether the cleaner implementation is a new `scripts/qrspi_critic_body.py` helper vs. folding a staged-body splice directly into the existing design/plan finalize prompt cannot be decided without reading the finalize-prompt code in `qrspi-batch.js`. Slice 3 carries both options; the plan phase must pick one against the actual finalize code.
- **Exact `runCriticLoop` signature / context params.** The design names the function and its responsibilities but not the precise parameter list (which of `wd`, `id`, `log`, `res`, prompt-builders it needs). Resolved at plan/implementation time against the real `runPhase` body.
- **`CRITIC_VERDICT_SCHEMA` field types for `findings`.** Design specifies `{pass: bool, findings: [...]}` but not the per-finding shape (string vs object). Modeled here as a free-form list; final element schema is an implementation detail pinned in Slice 2/3.
- **Whether the critic agent needs `Write`.** Design says `tools: Read` "(plus `Write` only if it stages a verdict file)" — depends on whether the verdict returns via the runner schema (no Write) or via a staged file (Write). Decision 2's schema'd-return path implies Read-only; confirm in Slice 2.
- **Reviser as a distinct agent vs. re-invoking the phase agent.** The design refers to "spawns critic(s) and reviser" but does not specify whether the reviser is the same `agentType` as the phase producer re-prompted with findings, or a separate agent type. Resolved in Slice 3.
