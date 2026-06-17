# Design — Retire the fidelity-only edge critic (qrspi-critic / runCriticLoop)

**Ticket:** RUS-88
**Research basis:** research.md @ 2026-06-17T00:00:00Z
**Generated:** 2026-06-17T00:00:00Z
**Status:** draft (revised 2026-06-17 — added live-config cleanup + documentation sweep; reconciled to RUS-84 abandoned)

## Current State

The QRSPI critic layer hosts four distinct critic mechanisms that share one tested decision core (`scripts/qrspi_critic_loop.py` via `criticDecision`) and one verdict schema (`CRITIC_VERDICT_SCHEMA`) (ref: Discovered Patterns). The fidelity-only **edge critic** is the function `runCriticLoop` (`.claude/workflows/qrspi-batch.js:739`), which spawns the `qrspi-critic` agent per round, reads `criticConfig.upstreamPath`/`rubric`/`maxRounds`, derives the produced artifact as `stg(id, name)`, and on a `revise` decision re-spawns the producer agent to rewrite the staged artifact in place (ref: Q2). It returns `{ ok, residualFindings, metrics }`; `ok:false` arises only on a spawn or decision failure (ref: Q2, Q10).

`runCriticLoop` has exactly ONE call site — the false branch of the `lenses?.length` ternary inside `runPhase` (`.claude/workflows/qrspi-batch.js:1499`); the true branch selects `runCriticPanelLoop` (the design panel) (ref: Q1, Q4). The ternary is reached only when `criticConfig` is truthy (`if (criticConfig)` at line 1469); a disabled-by-config phase passes `criticConfig = undefined`, so the whole critic block is skipped and the artifact persists with no critic gate — the existing "ungated" path (ref: Q9). The edge critic gates the four planning phases: `doDesign` builds `questionsCritic`/`researchCritic` (no `lenses`) and `doPlan` builds `structureCritic`/`planCritic` (no `lenses`) (ref: Q4, Q9).

The same `qrspi-critic` AGENT is also spawned by `runSliceCritic` (per-slice implementation critic, line 1968) — a structurally independent function with its own loop and reviser (`qrspi_revise_amend.py`), wired into `doImplementation`'s slice loop after each commit, gated by `implCriticCfg.enabled` (ref: Q3, Q4). Removing `runCriticLoop` does NOT by itself remove the per-slice path; that path reuses only the shared agent and `criticDecision` (ref: Q3).

`gateBehindEdge` is a RUS-77 cost-lever resolved by `resolve_design` (`scripts/qrspi_critics_config.py:178-180`), mirrored in the JS `DEFAULT_CRITIC_PHASES.design` (line 638), and consumed in `runPhase` (line 1478) only when `lenses?.length` AND `enabled`. It is a DESIGN-PANEL lever, default OFF, and a documented no-op for its stated purpose (the design phase routes to panel OR edge, never a sequence, so no in-scope edge outcome exists to gate behind) (ref: Q5, Inconsistencies).

The Python resolver enumerates six phases in `resolve_critics`: four edge phases via `resolve_edge_phase` (shape `{enabled, maxRounds}`, listed in `EDGE_PHASES`), `design` via `resolve_design`, `implementation` via `resolve_implementation` (per-slice + nested `coherence`) (ref: Q6). All phases default OFF (`resolve_enabled(cfg, False)`), so the shipped default already runs every planning phase ungated (ref: Q7, Q9). The `qrspi-coherence-critic` whole-stack pass (`runCoherenceCritic`, line 1900) and the design panel (`runCriticPanelLoop` + five `qrspi-design-critic-*` lens agents, including the `edge-alignment` lens) are independent of `runCriticLoop`, sharing only `criticDecision`/`CRITIC_VERDICT_SCHEMA` (ref: Q8, Q11).

No `_test.py` is dedicated solely to the edge critic: `qrspi_critic_loop_test.py` covers the shared core, and `resolve_edge_phase`/`gateBehindEdge` cases live inside `qrspi_critics_config_test.py` (ref: Q12). `run_tests.py` auto-discovers any `scripts/*_test.py` by filename pattern, with no manifest (ref: Q13). `runCriticLoop`'s metrics flow into `out.criticMetrics` (alongside `designCritic`) and its residual findings into the PR-body summary; a disabled phase already surfaces no record because the array filters `undefined` (ref: Q14).

**Dependency status (RUS-84 abandoned).** The ticket frames RUS-88 as `blockedBy` RUS-84 and instructs a rebase on "RUS-84's landed routing." As of 2026-06-17 RUS-84 never landed: both its PRs are CLOSED unmerged (#335 `RUS-84/design`, #336 `RUS-84/plan`), and there is no `blockedBy` edge on RUS-88 in Linear. `main` therefore still holds the **pre-RUS-84** form this design's Delta line numbers describe (`runCriticLoop@739`, ternary@1499, `EDGE_PHASES`/`resolve_edge_phase`/`gateBehindEdge` all present), and there is **nothing to reconcile against** — the "no lenses ⇒ runCriticLoop fallback" routing the ticket attributes to RUS-84 does not exist. Research Q1's phrasing "the source after RUS-84's restructuring" is stale: it describes plain `main`. AC3 is satisfied directly against `main`.

**Live config (`.qrspi/config.json`, gitignored).** On this repo the per-user `.qrspi/config.json` currently has every critic ON: `design.gateBehindEdge.enabled: true`, `questions`/`research`/`structure`/`plan` all `enabled: true`, and `implementation.enabled: true` (per-slice). After removal the resolver no longer reads those keys, so they become **inert (silently ignored), not a crash** — but they are dead config no PR can touch (the file is gitignored). This is the repo where retirement changes real behavior (those phases + the per-slice critic go ungated here), so the now-meaningless `enabled: true` flags must be pruned manually to avoid the false impression the critics are still active (see Delta → Operator cleanup + Risk Register).

## Desired End State

Maps each acceptance criterion to concrete behavior.

- **AC1 (remove loop + agent + skill).** `runCriticLoop` is gone from `qrspi-batch.js`; `.claude/agents/qrspi-critic.md` and `.claude/skills/qrspi-critic/` are deleted. No JS path references `runCriticLoop` (ref: Q4). The shared agent's other consumer (`runSliceCritic`) is also removed under AC2, so deleting the agent leaves no dangling spawn (ref: Q3, Q4).
- **AC2 (remove per-slice edge critic).** The `implCriticCfg.enabled`-gated block in `doImplementation` (lines 2130-2147) and `runSliceCritic` (line 1955) and its `sliceCriticDecide` shim are removed; each slice ships without an edge-fidelity judgment. The `runCoherenceCritic` seam pass remains byte-for-byte intact (ref: Q3, Q11).
- **AC3 (reconcile routing to ungated).** In `runPhase`, when `criticConfig.lenses?.length` is truthy → `runCriticPanelLoop`; otherwise the critic block is skipped (ungated), identical to today's disabled-phase path — no edge fallback (ref: Q1, Q9). The design panel and coherence pass are unaffected (ref: Q8, Q11).
- **AC4 (remove gateBehindEdge + config).** `gateBehindEdge` is removed from `resolve_design`, the JS `DEFAULT_CRITIC_PHASES.design` mirror, the `runPhase` short-circuit (lines 1478-1493), and `.qrspi/config.example.json`. The four `resolve_edge_phase` entries and `EDGE_PHASES` are removed from the resolver (ref: Q5, Q6). The committed template `.qrspi/config.example.json` loses `gateBehindEdge`, the four planning-phase sub-blocks, and their explanatory `$comment` strings. The live gitignored `.qrspi/config.json` **cannot** be changed by this PR; its now-inert keys are pruned manually as a documented post-merge step (see Delta → Operator cleanup).
- **AC5 (tests + docs).** Edge-phase and `gateBehindEdge` test cases are removed from `qrspi_critics_config_test.py` (and the `qrspi_contract_fixtures_consumer_test.py:81` assertion); new assertions pin "no lenses ⇒ resolver emits no edge phase / panel+coherence still resolve." Suite green under `python3 scripts/run_tests.py`. **Documentation sweep** — every reference to the edge critic / `runCriticLoop` / per-slice edge critic / `gateBehindEdge` is reviewed and revised across `CLAUDE.md` and `.claude/CLAUDE.md` (critic + lifecycle prose), any `docs/*.md` (notably the testing-dynamic-workflows + PR-gated-lifecycle docs), and the `.qrspi/config.example.json` inline `$comment` strings; stale `qrspi-critic`-naming descriptions vanish with their deleted files. Completeness check: `git grep -n 'runCriticLoop\|gateBehindEdge\|edge critic'` returns only intentional/historical mentions (ref: Q12, Q13, Inconsistencies).

Preserved (not in scope): `qrspi_critic_loop.py`, `criticDecision`, `CRITIC_VERDICT_SCHEMA`, `recordCriticMetrics`, the design panel + five lens agents (incl. `edge-alignment`), `runCoherenceCritic`, and their tests (ref: Q8, Q11, Q12).

## Delta

**`.claude/workflows/qrspi-batch.js`** — Delete `runCriticLoop` (739-836). In `runPhase`, replace the ternary (1497-1499) so the panel branch is the only critic branch and a non-panel `criticConfig` falls through to the ungated persist (the simplest reconcile: gate the whole block on `criticConfig?.lenses?.length`). Delete the `gateBehindEdge` short-circuit (1478-1493) and the `.design` mirror key (638). Delete `runSliceCritic` (1955) and `sliceCriticDecide` (1387); remove the `implCriticCfg.enabled` slice block (2130-2147) and `perSliceFindings` plumbing tied only to it. Remove `questionsCritic`/`researchCritic`/`structureCritic`/`planCritic` config builds, their `out.criticMetrics`/summary folds, **and every `critics.<phase>.enabled` reader** in `doDesign`/`doPlan` so no `undefined.enabled` access survives the resolver's 6→2-key shape change (ref: Q4, Q9, Q14, Decision 3).

**`scripts/qrspi_critics_config.py`** — Delete `EDGE_PHASES`, `resolve_edge_phase`, the four phase entries in `resolve_critics`, and `gateBehindEdge` from `resolve_design` (ref: Q5, Q6). `resolve_critics` then returns `{design, implementation}` (implementation minus per-slice; coherence kept) (ref: Q6, Q11).

**Deletions:** `.claude/agents/qrspi-critic.md`; `.claude/skills/qrspi-critic/`; `scripts/qrspi_slice_critic.py` (per-slice decide) if it has no other consumer.

**Modified tests:** `scripts/qrspi_critics_config_test.py` (drop `TestResolveEdgePhase`, the four `gateBehindEdge` cases, the edge-phase toggle test; add ungated/no-edge-phase assertions and keep the JS-mirror lockstep test updated). `scripts/qrspi_contract_fixtures_consumer_test.py` (drop line-81 `gateBehindEdge` assertion). `scripts/qrspi_slice_critic_test.py` removed with its module (ref: Q12).

**Docs/config:** `.qrspi/config.example.json` — remove `gateBehindEdge`, the four planning-phase critic sub-blocks, and their explanatory `$comment` strings. **Documentation sweep** (ref: AC5): revise `CLAUDE.md` + `.claude/CLAUDE.md` critic/lifecycle prose, scan `docs/*.md` for edge-critic/`gateBehindEdge` mentions, and verify with `git grep` that only intentional mentions remain.

**Operator cleanup (out of PR scope, manual):** the live gitignored `.qrspi/config.json` retains inert `gateBehindEdge` + `questions`/`research`/`structure`/`plan` (+ `implementation` per-slice) keys after merge; prune them by hand so the dead `enabled: true` flags don't misrepresent active critics. The PR cannot edit a gitignored file, so this is recorded in the PR body and as a Structure-phase task rather than committed.

## Pattern Decisions

### Decision 1: How `runPhase` reconciles to "ungated when no lenses"

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Gate the whole critic block on `criticConfig?.lenses?.length`; a non-panel `criticConfig` falls straight through to persist | Minimal diff; reuses the existing skip-the-block ungated path verbatim (ref: Q9); panel byte-for-byte unchanged | A leftover non-panel `criticConfig` would be silently ignored if a future caller built one |
| B | Keep the `if (criticConfig)` guard; replace the ternary false branch with an explicit "no-op / log ungated" inline | Explicit log line documents the ungated decision | Adds a dead branch; non-panel configs no longer exist after AC4 so the log is unreachable |

**Recommendation:** Option A
**Rationale:** The existing ungated path is exactly "critic block skipped → `persistArtifact` is the sole gate" (ref: Q9). Routing all non-panel configs through that single path collapses two equivalent code paths into one and keeps the panel branch (`runCriticPanelLoop`) and its `ok`-based contract untouched (ref: Q1, Q10). After AC4 no caller builds a non-panel `criticConfig`, so the risk in A's cons is theoretical.
**NEW PATTERN?** No — it generalizes the existing "disabled ⇒ ungated" path (ref: Q9).

### Decision 2: Fate of the shared `qrspi-critic` agent

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Delete `qrspi-critic.md` + skill because BOTH consumers (`runCriticLoop`, `runSliceCritic`) are removed | No dead agent/skill; descriptions naming `runCriticLoop` (ref: Inconsistencies) vanish | Couples AC1 and AC2 — the agent can only be deleted once the per-slice critic also goes |
| B | Keep the agent, only delete `runCriticLoop` | Smaller blast radius | Stale `runCriticLoop` references remain; per-slice critic still runs, contradicting AC2 (ref: Q3, Q4) |

**Recommendation:** Option A
**Rationale:** The ticket's AC1 and AC2 jointly remove both consumers, so the agent has no remaining caller (ref: Q4, Q3). Keeping it would leave a stale `runCriticLoop`-naming description and an active per-slice critic the ticket explicitly retires.
**NEW PATTERN?** No.

### Decision 3: Edge-phase removal vs. neutering in the Python resolver

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Delete `EDGE_PHASES` + `resolve_edge_phase` + the four entries; resolver returns only `{design, implementation}` | Resolver shape matches reality; no dead opt-in knob | Must update the JS-mirror lockstep test and `parseCriticsConfig` merge to not expect four phases |
| B | Keep the entries but hard-force `enabled:false` / document no-op | Smaller test churn | Leaves a config surface the ticket says to remove (AC4); contradicts "no longer reference the edge critic" |

**Recommendation:** Option A
**Rationale:** AC4 requires `DEFAULT_CRITIC_PHASES`, the resolver, and `config.example.json` to no longer reference the edge critic (ref: Q6). The JS/Python lockstep is test-asserted (ref: Q6), so both sides drop the four phases together and the lockstep test is updated to the new shape.
**NEW PATTERN?** No.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Deleting a shared pure module (`qrspi_critic_loop.py`, `criticDecision`, `CRITIC_VERDICT_SCHEMA`, `recordCriticMetrics`) breaks the panel/coherence critics | med | high | Treat these as explicitly KEPT; the structure/plan phases must enumerate them as no-touch; rely on the preserved `qrspi_critic_loop_test.py` + panel/coherence tests as the regression signal (ref: Q8, Q11, Q12) |
| `edge-alignment` panel lens deleted by namesake confusion with the edge critic | med | high | The lens is a separate agent file (`qrspi-design-critic-edge-alignment.md`) under the KEPT design panel; removal touches only `qrspi-critic.md` + `runCriticLoop` + `runSliceCritic`, never `qrspi-design-critic-*` (ref: Q8, Inconsistencies) |
| JS `runPhase`/`doImplementation` edits are harness-coupled and uncovered by the Python gate | high | med | Per CLAUDE.md, verify JS via a Python contract fixture (the JS/Python mirror lockstep test) plus a manual end-to-end design+plan+implementation run; keep the design-phase regression green (ref: Q13, Constraints) |
| ~~RUS-84 lands a different routing line than research recorded~~ — **VOID: RUS-84 abandoned** (PRs #335/#336 closed unmerged; no `blockedBy` edge) | n/a | n/a | No reconcile needed — `main` holds the pre-RUS-84 form. Still re-confirm the ternary text + line numbers against `main` HEAD immediately before editing, since RUS-82 landed nearby (ref: Current State → Dependency status) |
| Resolver 6→2-key shape change leaves a stray `critics.<phase>.enabled` reader → `undefined.enabled` crash | med | high | Grep every `critics.questions/research/structure/plan` access in `qrspi-batch.js` and remove with the config builds; the JS/Python lockstep test + a manual e2e catch a missed reader (ref: Delta, Decision 3) |
| Stale live `.qrspi/config.json` keys read as "critics still active" after removal | high | low | Keys become inert (resolver stops reading them) — no crash; prune manually post-merge and note in the PR body (ref: Delta → Operator cleanup) |
| `runSliceCritic`/`sliceCriticDecide` removal leaves orphan `perSliceFindings` plumbing or a dangling `qrspi_slice_critic.py` import | med | med | Trace `perSliceFindings` and `sliceCriticDecide` consumers during Structure; remove the module only if no other caller; run `python3 scripts/run_tests.py` to catch a broken import (ref: Q3, Q13) |

## Open Questions

- OQ1: ~~After RUS-84 lands…~~ **Moot — RUS-84 abandoned** (PRs #335/#336 closed unmerged). There is no RUS-84 routing to reconcile against; Decision 1 Option A applies directly to `main`, where the only `lenses`-carrying caller is the design panel (ref: Current State → Dependency status, Q1).
- OQ2: Should `qrspi_slice_critic.py` be deleted outright or retained as a no-op? AC2 removes the per-slice critic; the module's deletion depends on it having no other consumer — confirm at Structure.
- OQ3: RUS-79 is recommended for cancellation by this ticket (it cannot tune a deleted critic). Is canceling RUS-79 a human action outside this PR, or should the PR body note it? (No code impact.)
- OQ4: The ticket declares RUS-88 `blockedBy` RUS-84, but no `blockedBy` edge exists in Linear (harmless now RUS-84 is dead). Confirm RUS-84 is formally **Canceled** so a future batch run cannot resurrect a "wait on RUS-84" framing (Linear housekeeping, no code impact).
