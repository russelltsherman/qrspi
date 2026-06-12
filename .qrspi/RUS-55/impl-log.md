# Implementation Log — qrspi critics 1/5: edge-critic loop primitive wired into runPhase

## Session 1 — Slice 1: Pure critic-loop decision module

**Timestamp:** 2026-06-12T22:42:25Z
**Tasks completed:** T1, T2, T3, T4, T5, T6, T7, T8, T9
**Tasks failed:** none
**Tests:**

- `python3 scripts/qrspi_critic_loop_test.py` → 33 passed, 0 failed (exit 0)

**Deviations from structure.md:**

- none. Module exposes `next_action(verdicts, round, max_rounds) -> {action, residual_findings}` and `parse_critic_verdict(text) -> {pass, findings}` exactly as specified in §Contracts.

**Deviations from plan.md:**

- none. All Slice 1 steps (§1.1–§1.10) implemented as written.

**Notes for next session:**

- **Canonical verdict shape:** `{"pass": bool, "findings": list}`. `parse_critic_verdict` fails closed to `{"pass": False, "findings": []}` on any malformed/empty/None/non-dict input and never raises. A scalar `findings` value is wrapped into a single-element list; a truthy non-bool `pass` is coerced to `bool`.
- **`next_action` contract for the JS glue (Slice 3 `runCriticLoop`):** pass the round's parsed verdict(s) as a LIST (single-critic ⇒ one-element list — OQ2). The LAST element is authoritative. Returns `action` ∈ `{"converged","revise","cap_reached"}` and `residual_findings` (a list). `converged` carries an empty `residual_findings`; `revise` and `cap_reached` carry the latest verdict's findings. Cap test is `round + 1 >= max_rounds` (so `max_rounds=2` allows rounds 0 and 1; round 1 non-pass ⇒ `cap_reached`).
- **Fail-closed at the decision layer too:** an empty/`[]` verdict list (or a non-list) reads as NOT-passed, so a missing verdict can never report `converged` — it yields `revise` (rounds remain) or `cap_reached` (at the cap).
- There is also a private `_coerce_verdict(obj)` helper shared by both public functions; it is the single coercion point if the per-finding element shape needs pinning in Slice 2/3 (`CRITIC_VERDICT_SCHEMA`).
- Files added: `scripts/qrspi_critic_loop.py`, `scripts/qrspi_critic_loop_test.py`. Stdlib-only (json, re), no agent/IO/git coupling — matches the `qrspi_*.py` + `_test.py` sibling convention. NOT committed (orchestrator handles commits).

---

## Session 2 — Slice 2: Critic agent + slash-command wrapper

**Timestamp:** 2026-06-12T22:45:18Z
**Tasks completed:** T10, T11, T12, T13a, T13b (static), T13c (static), T13 (static)
**Tasks failed:** none
**Tests:**

- Frontmatter parse (`python3` ad-hoc): agent `name: qrspi-critic` present, `tools` == exactly `[Read]`; skill has all required keys (`name`/`description`/`command`/`argument-hint`/`allowed-tools`), `command: /qrspi-critic` → PASS
- Agent body content check (`python3` ad-hoc): consumes `UPSTREAM_PATH`+`ARTIFACT_PATH`, honors `RUBRIC`, edge-not-node directive, emits `{pass, findings}`, negative case names the dropped requirement, no-write directive → PASS

**Deviations from structure.md:**

- none. `.claude/agents/qrspi-critic.md` created with `name: qrspi-critic`, `tools: Read` only (the schema'd-return path of Decision 2 — verdict returns via the runner schema at the Slice 3 `agent({schema})` call site, so no staged verdict file ⇒ no `Write`). `.claude/skills/qrspi-critic/SKILL.md` created as a thin wrapper.

**Deviations from plan.md:**

- **T13b/T13c verified statically, not by live agent invocation.** Plan steps §2.15/§2.16 call for a "direct critic invocation" against fixture artifacts returning `pass:true` / `pass:false`. The implement-phase context has only Read/Write/Edit/Bash — no `Agent` tool — and the critic is pinned to the frontier model spawned by `runCriticLoop` (Slice 3 wiring), so a live invocation is not available here. Verified instead: frontmatter parses with `tools` limited to `Read`, and the body content covers the edge contract (upstream+artifact inputs, edge-not-node judging, `{pass, findings}` emission, negative-case requirement naming). The live faithful⇒pass / degraded⇒fail invocation is exercised when Slice 3 wires the loop (its §3.30 manual e2e: passing artifact ⇒ 1 critic call/0 revise; degraded ⇒ critique→revise).
- **T12 (skill-creator):** the skill-creator skill was invoked per project convention, but its full eval/benchmark loop was not run — this is a thin internal agent-spawn wrapper that mirrors `qrspi-structure/SKILL.md` byte-for-byte in structure (a fixed, deterministic workflow wrapper, not a subjective-output skill the benchmark loop is designed for). The skill-creator's own guidance scopes the benchmark loop to skills with substantive/subjective outputs; the wrapper was authored directly from the established QRSPI template and frontmatter-validated.

**Notes for next session:**

- **Agent type to spawn in `runCriticLoop` (Slice 3):** `agentType: 'qrspi-critic'` resolves to `.claude/agents/qrspi-critic.md` by its `name:` frontmatter (no manifest). It is `tools: Read` only and returns its verdict via the runner schema — pass `schema: CRITIC_VERDICT_SCHEMA` at the `agent(...)` call site; the agent writes no file.
- **Critic prompt input contract (what `runCriticLoop` must pass in the prompt body):** `UPSTREAM_PATH` (absolute path to the upstream artifact = the rubric anchor, read via `art(wd,id,criticConfig.upstream)`), `ARTIFACT_PATH` (absolute path to the produced artifact at `stg(id,name)`), and an optional `RUBRIC` text line (omit when none). The agent reads both paths itself.
- **Verdict shape the agent emits:** `{pass: bool, findings: list}` — `pass:true` ⇒ findings empty; `pass:false` ⇒ findings non-empty, each a self-contained string naming the specific upstream requirement dropped/contradicted/distorted. This matches the Slice 1 `parse_critic_verdict`/`next_action` canonical shape; feed the parsed verdict into `next_action` as a one-element list (single-critic, OQ2).
- **`CRITIC_VERDICT_SCHEMA` (Slice 3) just needs to match `{pass: bool, findings: list}`** — the agent body already instructs `findings` as a list of self-contained strings; pin the per-element shape as string when defining the schema.
- Files added: `.claude/agents/qrspi-critic.md`, `.claude/skills/qrspi-critic/SKILL.md`. NOT committed (orchestrator handles commits).

---

## Session 3 — Slice 3: Wire `runCriticLoop` into `runPhase`, enable for design/plan

**Timestamp:** 2026-06-12T23:05:00Z
**Tasks completed:** T14, T15, T16, T17, T18, T19, T20a, T20b, T20c, T20, T21a, T21, T22
**Tasks failed:** none
**Tests:**

- `python3 scripts/qrspi_critic_loop_test.py` → 33 passed, 0 failed (Slice 1 regression — unchanged pure functions)
- `python3 scripts/qrspi_critic_body_test.py` → 32 passed, 0 failed (new path-A body helper)
- `node --check .claude/workflows/qrspi-batch.js` → exit 0 (syntax OK)
- `qrspi_critic_loop.py` CLI shim end-to-end (5 cases: converged / revise / cap_reached / empty-fail-closed / garbage-fail-closed) → all correct
- `runCriticLoop` static control-flow harness (stubbed `agent`, REAL python decision CLI), 4 cases → all pass: (A) passing artifact ⇒ 1 critic call / 0 revise / converged / no residual (AC4); (B) fail→revise→pass ⇒ 2 critic / 1 revise / converged; (C) fail→revise→fail ⇒ cap_reached, ok:true, 2 residual findings (AC2); (D) null critic verdict ⇒ ok:false (stops ticket)
- `qrspi_critic_body.py` on the real RUS-55 worktree: empty findings ⇒ ok:true bytes:0 (no gt invoked — converged phase never touches the commit); missing findings file ⇒ ok:false "not found"; bad `--phase` ⇒ argparse rejects
- Call-site arity grep: questions/research/structure/worktree pass 6 positional args (criticConfig `undefined`); only design/plan pass the 7th `criticConfig` (AC1 byte-for-byte unchanged no-critic behavior)

**Deviations from structure.md:**

- **`runCriticLoop` signature** is `runCriticLoop(name, id, criticConfig)` — NOT `(name, id, criticConfig, ...ctx)`. The structure's §Contracts sketch reads the upstream via `art(wd, id, criticConfig.upstream)` inside the loop, which would require threading `wd`. Per structure §Unverified Assumptions ("exact `runCriticLoop` signature/context params … resolved at plan/implementation time"), I instead resolve the absolute upstream path AT THE CALL SITE in `doDesign`/`doPlan` (where `wd` is in scope) and put it on `criticConfig.upstreamPath`. So `runPhase`/`runCriticLoop` need no `wd` at all, and `runPhase`'s existing 6 params stay untouched (AC1). `criticConfig` shape is therefore `{ upstreamPath, maxRounds?, rubric? }` rather than `{ upstream, maxRounds?, rubric? }`.
- **`runPhase` return contract preserved as boolean.** Structure/plan implied threading `residualFindings` out of `runPhase`. To keep every no-critic call site byte-for-byte unchanged (they treat the return as a boolean), `runPhase` still returns `true`/`false`; on cap-reached it writes the findings back onto the passed `criticConfig` object as `criticConfig.residualFindings`, which `doDesign`/`doPlan` read after the call. No call-site return-shape change.

**Deviations from plan.md:**

- **T15 body-path decision: chose PATH A** (`scripts/qrspi_critic_body.py` + `_test.py`), per plan §3.19. The design/plan finalize commit messages are bare inline subject strings built in the `agent()` prompt (no clean staged-body seam exists today), and the commit is created by a worker via `gt modify -c` / `gt create`. Path A mirrors `qrspi_pr_body.py`: residual findings → token-free staged JSON file → script appends a "## Residual critic findings" section to the phase commit message.
- **Body splice runs INSIDE the finalize worker, between commit-create and `gt submit`** — NOT as a separate post-finalize worker. Reason: `gt submit` seeds the PR body from the commit message at CREATION ONLY (the same constraint documented for `qrspi_pr_body.py`); amending after the first submit would not update the PR body. So `criticBodyStep(...)` builds a conditional prompt fragment spliced into the design/plan finalize prompt (empty string when there are no findings ⇒ the finalize prompt is byte-for-byte unchanged for the converged/no-critic case). The worker writes the findings JSON to `/tmp/phase-stage/<id>/critic-findings-<phase>.json` and runs `qrspi_critic_body.py` before `gt submit`.
- **Plan §3.21 named `next_action`/`qrspi_critic_loop.py` as the decision delegate but that module had NO CLI** (Slice 1 shipped pure functions only). Added a thin, additive `main()`/argparse + stdin shim to `qrspi_critic_loop.py` (`printf '%s' '<json verdicts array>' | python3 qrspi_critic_loop.py --round R --max-rounds M` → `{action, residual_findings}`). The pure `next_action`/`parse_critic_verdict`/`_coerce_verdict` functions are UNCHANGED (Slice 1 regression test still 33/33); the shim only exposes them to the JS orchestrator (which cannot run python in-sandbox) via the worker-runs-script pattern used by `qrspi_persist.py`/`qrspi_resolve.py`. The shim coerces each stdin verdict fail-closed.
- **Manual e2e §3.30 verified by a static control-flow harness, not a live design run.** The implement-phase context has no `Agent` (subagent-spawn) tool — the critic/reviser are spawned only by the workflow RUNNER (`agent({agentType})`) — and no live Linear/git mutation is permitted here. I instead inlined the `runCriticLoop` body into a Node harness that stubs `agent()`/`log()` but calls the REAL `qrspi_critic_loop.py` decision CLI, and asserted the exact call counts and outcomes the §3.30 checkpoint requires (passing⇒1 critic/0 revise; degraded⇒critique→revise→re-critique; cap⇒success+residual). The live agent-spawn + `gt`-backed PR-body splice is exercised on the first real batch design/plan run.
- **`LOOP_DECISION_SCHEMA` added** (not separately listed in the plan) as the StructuredOutput contract for the `criticDecision` worker that runs the python CLI — mirrors how every other worker-runs-script call (`PERSIST_SCHEMA`) is schema'd.

**Notes for next session:**

- Slice 3 is the final slice — feature complete. No further implementation session.
- **Files changed/added this slice:**
  - ⚠️ `.claude/workflows/qrspi-batch.js` — added `CRITIC_VERDICT_SCHEMA` + `LOOP_DECISION_SCHEMA`; `runCriticLoop(name,id,criticConfig)`, `criticDecision(verdicts,round,maxRounds)`, `criticBodyStep(id,phase,findings,wd)`; trailing optional `criticConfig` param on `runPhase` with a guarded `if (criticConfig)` loop between produce-success and the persist gate; `doDesign`/`doPlan` each pass a `criticConfig` ({upstreamPath, maxRounds:2}) and splice residual findings into the finalize PR body + fold a critic summary into `res.summary`.
  - ✨ `scripts/qrspi_critic_body.py` + `scripts/qrspi_critic_body_test.py` (path A body helper, 32/32).
  - ✨ thin CLI added to `scripts/qrspi_critic_loop.py` (additive; pure functions unchanged).
- **Reviser identity (resolved Unverified Assumption):** the reviser is a generic agent re-prompted with the findings + both paths, instructed to rewrite `stg(id,name)` IN PLACE — NOT a distinctly-registered agent type and NOT the typed phase producer re-spawned with its full original prompt. It carries no `agentType`, so it runs as the default worker model. If a future slice wants a stronger reviser, swap in `agentType: '<phase-producer>'` at the `revise:` `agent(...)` call in `runCriticLoop`.
- **Persist gate still authoritative:** the critic loop runs BEFORE `persistArtifact`, on the still-staged `stg(id,name)`. The reviser is instructed to write a non-empty artifact in place; if it empties it, persist's non-empty check fails and `runPhase` returns false (no `ok:true` from an emptied artifact) — AC preserved.
- **Critic agent prompt contract (matches Slice 2's `qrspi-critic.md`):** `runCriticLoop` passes `UPSTREAM_PATH`, `ARTIFACT_PATH`, and an optional `RUBRIC` line; the critic returns `{pass, findings}` via `CRITIC_VERDICT_SCHEMA`. `maxRounds` default is 2 (OQ4), set explicitly on both design and plan criticConfigs.

---
