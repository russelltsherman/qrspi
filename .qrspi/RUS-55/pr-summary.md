# PR: RUS-55 — Edge-critic loop primitive wired into runPhase

**Ticket:** RUS-55
**Design:** design.md @ 2026-06-12T00:00:00Z
**Structure:** structure.md @ 2026-06-12T00:00:00Z

## Summary

This is the foundation slice (1/5) of the QRSPI "critics" feature: a bounded, edge-oriented critic loop (produce→critique→revise) wired into the orchestrator's per-phase `runPhase` pipeline. The critic judges a produced artifact as a faithful derivation of its upstream input (the "edge", not the "node"), looping up to a per-phase `maxRounds` cap; on non-convergence it surfaces residual findings into the design/plan PR body rather than blocking the ticket. The decision logic lives in a pure, fully-tested python module (`qrspi_critic_loop.py`) and the body-splice in `qrspi_critic_body.py`, keeping the untestable JS glue thin. The critical reviewer focus is **AC1 — no-critic phases must be byte-for-byte unchanged**: the loop is gated behind an optional trailing `criticConfig` param so the four existing call sites (questions/research/structure/worktree) pass `undefined` and execute the original control path verbatim. Note: per-AC verification of the JS glue and live agent-spawn was done via a static control-flow harness driving the REAL python decision CLI (no `Agent` tool or live git/Linear mutation is available in the implement-phase context); the live agent-spawn + `gt`-backed PR-body splice is first exercised on a real batch design/plan run.

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: configured critic runs produce→critique→revise ≤ maxRounds; no critic ⇒ byte-for-byte unchanged | `.claude/workflows/qrspi-batch.js:runPhase` (optional trailing `criticConfig`, `if (criticConfig)` guard) | Call-site arity grep (4 sites pass 6 args, `criticConfig` undefined); `runCriticLoop` static control-flow harness case A |
| AC2: maxRounds enforced; non-converging critic terminates and surfaces findings into the PR | `.claude/workflows/qrspi-batch.js:runCriticLoop` + `criticDecision`; `scripts/qrspi_critic_body.py` body splice | `scripts/qrspi_critic_loop_test.py` (fail→cap→cap_reached); harness case C (cap_reached, 2 residual findings); `scripts/qrspi_critic_body_test.py` |
| AC3: critic receives upstream + produced artifact; findings schema-validated | `.claude/agents/qrspi-critic.md` (consumes `UPSTREAM_PATH`+`ARTIFACT_PATH`); `CRITIC_VERDICT_SCHEMA` in `qrspi-batch.js`; `scripts/qrspi_critic_loop.py:parse_critic_verdict` (fail-closed backstop) | `scripts/qrspi_critic_loop_test.py` (malformed/empty verdict fails closed); agent frontmatter + body content checks |
| AC4: all-pass on round 1 ⇒ single critic call, no revise | `scripts/qrspi_critic_loop.py:next_action` (converged on round-0 pass, breaks before revise) | `scripts/qrspi_critic_loop_test.py` (pass-first-round); harness case A (1 critic call / 0 revise) |

## Changes by Slice

### Slice 1: Pure critic-loop decision module

| File | Change | Lines |
|------|--------|-------|
| `scripts/qrspi_critic_loop.py` | new (pure module: `next_action`, `parse_critic_verdict`; thin CLI shim added in Slice 3) | +157 |
| `scripts/qrspi_critic_loop_test.py` | new (stdlib-only, 33 asserts) | +157 |

### Slice 2: Critic agent + slash-command wrapper

| File | Change | Lines |
|------|--------|-------|
| `.claude/agents/qrspi-critic.md` | new (typed `qrspi-critic` agent, `tools: Read`, edge-critic system prompt) | +52 |
| `.claude/skills/qrspi-critic/SKILL.md` | new (slash-command wrapper) | +23 |

### Slice 3: Wire `runCriticLoop` into `runPhase`, enable for design/plan

| File | Change | Lines |
|------|--------|-------|
| `.claude/workflows/qrspi-batch.js` | modified (`CRITIC_VERDICT_SCHEMA` + `LOOP_DECISION_SCHEMA`; `runCriticLoop`/`criticDecision`/`criticBodyStep`; optional `criticConfig` on `runPhase`; `doDesign`/`doPlan` wiring + residual-findings splice) | +192, -7 |
| `scripts/qrspi_critic_body.py` | new (path-A body helper: residual findings → staged JSON → appended commit-message section) | +262 |
| `scripts/qrspi_critic_body_test.py` | new (stdlib-only, 32 asserts) | +155 |

### Phase artifacts (non-source; QRSPI workflow records)

| File | Change | Lines |
|------|--------|-------|
| `.qrspi/RUS-55/questions.md` | new | +51 |
| `.qrspi/RUS-55/research.md` | new | +420 |
| `.qrspi/RUS-55/design.md` | new | +117 |
| `.qrspi/RUS-55/structure.md` | new | +82 |
| `.qrspi/RUS-55/plan.md` | new | +146 |
| `.qrspi/RUS-55/worktree.md` | new | +85 |
| `.qrspi/RUS-55/impl-log.md` | new | +98 |

## Testing Summary

- [x] Slice 1: unit tests — `python3 scripts/qrspi_critic_loop_test.py` — 33 passed, 0 failed
- [x] Slice 3: unit tests — `python3 scripts/qrspi_critic_body_test.py` — 32 passed, 0 failed
- [x] Slice 3: JS syntax — `node --check .claude/workflows/qrspi-batch.js` — exit 0
- [x] Slice 3: decision CLI e2e — `qrspi_critic_loop.py` CLI shim, 5 cases (converged / revise / cap_reached / empty-fail-closed / garbage-fail-closed) — all correct
- [x] Slice 3: `runCriticLoop` static control-flow harness (stubbed `agent`, REAL python decision CLI), 4 cases — all pass: (A) passing ⇒ 1 critic / 0 revise / converged (AC4); (B) fail→revise→pass ⇒ 2 critic / 1 revise; (C) fail→revise→fail ⇒ cap_reached, ok:true, 2 residual (AC2); (D) null verdict ⇒ ok:false (stops ticket)
- [x] Slice 3: `qrspi_critic_body.py` on real RUS-55 worktree — empty findings ⇒ ok:true bytes:0 (no gt invoked); missing file ⇒ ok:false; bad `--phase` ⇒ argparse rejects
- [x] AC1 regression: call-site arity grep — questions/research/structure/worktree pass 6 positional args (`criticConfig` undefined); only design/plan pass the 7th
- [x] Slice 2: agent frontmatter parse (`name: qrspi-critic`, `tools: [Read]`) + skill keys; body content (upstream+artifact inputs, edge-not-node, `{pass, findings}`, negative-case naming, no-write) — PASS
- [ ] Live agent-spawn e2e (passing⇒1 critic/0 revise; degraded⇒critique→revise; cap⇒findings in PR body) — NOT run here (no `Agent` tool / no live git+Linear in implement context); exercised on first real batch design/plan run

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| `CriticConfig` field for upstream | `{ upstream: string, maxRounds?, rubric? }` — loop reads `art(wd, id, criticConfig.upstream)` | `{ upstreamPath, maxRounds?, rubric? }` — absolute path resolved at the `doDesign`/`doPlan` call site | Avoids threading `wd` into `runPhase`/`runCriticLoop`; structure §Unverified Assumptions explicitly deferred the exact signature to implementation |
| `runCriticLoop` signature | `runCriticLoop(name, id, criticConfig, ...ctx)` | `runCriticLoop(name, id, criticConfig)` | Upstream path resolved at call site (see above), so no extra ctx params needed |
| `runPhase` return contract | implied threading `residualFindings` out of `runPhase` | still returns boolean; cap-reached writes findings back onto the passed `criticConfig.residualFindings` | Keeps every no-critic call site's boolean return byte-for-byte unchanged (AC1) |
| Body seam (Decision 4 open choice) | new helper OR fold into finalize prompt | chose PATH A: new `scripts/qrspi_critic_body.py` + `_test.py` | No clean staged-body seam exists in the design/plan finalize prompt; path A mirrors proven `qrspi_pr_body.py` |
| `LOOP_DECISION_SCHEMA` | not separately listed | added | StructuredOutput contract for the `criticDecision` worker running the python CLI; mirrors `PERSIST_SCHEMA` worker-runs-script pattern |
| `qrspi_critic_loop.py` CLI | plan §3.21 assumed a CLI existed | added thin additive `main()`/argparse+stdin shim | Slice 1 shipped pure functions only; shim exposes them to the JS orchestrator (which cannot run python in-sandbox); pure functions unchanged (33/33 regression holds) |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| Critic runs on weak model and stalls against StructuredOutput | mitigated — agent pinned to frontier model; `parse_critic_verdict` fail-closed backstop + cap-out, never loops | Remove `criticConfig` from `doDesign`/`doPlan`; loop becomes dormant |
| Critic/reviser empties the staged artifact ⇒ persist `ok:false` stops ticket | mitigated — reviser instructed to rewrite `stg(id,name)` in place non-empty; persist non-empty check is backstop (verified: emptied artifact ⇒ no `ok:true`) | Persist gate already fails closed; drop `criticConfig` to disable |
| New in-process loop fails to terminate (no precedent) | mitigated — counter-bounded `for (round < maxRounds)`; cap-reached returns success + findings, never loops (harness case C) | n/a (terminates by construction) |
| Malformed/garbled critic verdict silently marks artifact converged | mitigated — fail-closed: empty/`[]`/non-list reads NOT-passed ⇒ revise or cap_reached, never converged (tested) | n/a |
| `runCriticLoop` JS glue untestable (no JS harness) | accepted + mitigated — converge/cap decision extracted to tested `qrspi_critic_loop.py`; only agent-spawn glue stays in untested JS; verified via static harness driving the real CLI | n/a |
| A non-critic phase drifts from byte-for-byte unchanged | mitigated — trailing optional `criticConfig` undefined at 4 sites + `if (criticConfig)` guard; arity grep confirms untouched | Disable via removing `criticConfig` args |
| Live agent-spawn / `gt` PR-body splice unverified in implement context | discovered-new (accepted) — verified only by static harness; first real batch design/plan run is the live e2e | Disable `criticConfig` on design/plan if the live run misbehaves |

## Open Items

- **Live e2e deferred to first real batch run.** The passing⇒1-critic / degraded⇒revise / cap⇒PR-body-findings path was verified via a static control-flow harness against the real python decision CLI, not a live agent-spawn — the implement-phase context has no `Agent` tool and no live git/Linear mutation. Watch the first real `doDesign`/`doPlan` batch run for: round-0 critique logged, correct critic/revise call counts, and residual findings appearing in the PR body on cap.
- **Reviser is the default worker model**, re-prompted with findings + both paths to rewrite `stg(id,name)` in place (not a distinct agent type, not the typed phase producer re-spawned). A future slice wanting a stronger reviser can set `agentType: '<phase-producer>'` at the `revise:` `agent(...)` call.
- **Single critic per edge (OQ2).** This primitive supports exactly one critic agent per round (no `parallel()` fan-out). Multi-critic fan-out and phase-specific rubrics are deferred to the per-phase tickets (2/5..5/5).
- **skill-creator eval loop not fully run** on the `qrspi-critic` wrapper — it is a thin deterministic agent-spawn wrapper mirroring `qrspi-structure/SKILL.md`; authored from the established template and frontmatter-validated rather than benchmark-looped (the benchmark loop targets subjective-output skills).
- **Follow-up tickets:** per-phase critic enablement and rubrics land in the remaining critics tickets (2/5 through 5/5); this PR ships only the foundation primitive enabled for design/plan.
