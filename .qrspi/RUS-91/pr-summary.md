# PR: RUS-91 — Multi-lens /review-* panels at manual-review depth

**Ticket:** RUS-91
**Design:** design.md @ 2026-06-18T01:00:00Z
**Structure:** structure.md @ 2026-06-18T01:30:00Z

## Summary

The on-demand `/review-*` family was thin single-lens orchestration: each phase ran exactly ONE node-validity lens, never saw the ticket text, laundered open questions through the artifact's own producer, and reported a bare "converged / zero findings / pass" that hid real non-blocking inaccuracies. This PR brings all four skills (`/review-design`, `/review-plan`, `/review-implementation`, `/review`) up to manual-review depth: each phase now fans out a full adversarial multi-lens panel, the ticket text is plumbed to the fidelity/completeness/decision-readiness lenses, a non-producer shared reviser replaces the producer-as-reviser circularity, deferred human decisions are surfaced terminal-advisory (never re-spawning a reviser), and the synopsis is axis-enumerated with a distinct non-blocking section. The tested pure-Python core (new `qrspi_review_synopsis.py` helpers + per-phase lens config) lands first with full unit coverage; the agents and skill wiring build on it. **Reviewer focus:** (1) the partition-decision-readiness contract — decision-readiness findings MUST stay out of the synthesize array (Decision 5); (2) the propose-only invariant — no reviser or skill writes a tracked path/branch; (3) the new lens prompts enforcing the adversarial named-counter-example / fail-closed contract.

## Acceptance Criteria Mapping

Acceptance criteria are taken from design.md §Desired End State (each AC maps to concrete behavior; the ticket states them as the named gaps to close).

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: Ticket/AC descoping is caught — fidelity/completeness lenses see the ticket | `.claude/agents/qrspi-{plan,impl}-critic-{plan,impl}-fidelity.md`, `…-completeness.md`; `TICKET_CONTENT_PATH` plumbing in `review-design/SKILL.md` Step 3, `review-plan`, `review-implementation` | LIVE lens run (2026-06-18): `completeness` + `edge-alignment` over `evals/fixtures/design_dropped_criterion_broken.md` + ticket both returned `pass:false` naming the dropped "403 unless admin" AC as blocking (see Testing Summary / impl-log Session 6). The pre-existing `qrspi_teeth_test` is a STRUCTURAL fixture check only, not a lens run |
| AC2: Deferred blocking decisions surfaced, not laundered | `.claude/agents/qrspi-design-critic-decision-readiness.md` (non-producer, terminal-advisory); `partition_decision_readiness()` in `scripts/qrspi_review_synopsis.py` | `scripts/qrspi_review_synopsis_test.py` (decision-readiness partition — kept out of synthesize array) |
| AC3: Completeness gaps caught (every AC + answered question covered) | `…-completeness.md` lenses (plan/impl) + design `completeness` lens added to `DEFAULT_REVIEW_DESIGN_LENSES` in `scripts/qrspi_critics_config.py` | `scripts/qrspi_critics_config_test.py` (panel constants); lens-fixture probe (impl-log Session 5) |
| AC4: Internal inconsistencies caught | `internal-consistency` added to `DEFAULT_REVIEW_DESIGN_LENSES`; plan/impl panels add consistency via fidelity lenses | `scripts/qrspi_critics_config_test.py` |
| AC5: Real non-blocking findings surfaced (not swallowed by the blocking bar) | `nonBlockingNotes` channel rendered by `render_synopsis()` in `scripts/qrspi_review_synopsis.py`, AND all five design panel lenses (`completeness`/`internal-consistency`/`edge-alignment`/`simplicity`/`design-review`) + the plan/impl fidelity+completeness lenses now EMIT it — so the design-phase advisory section has producers (review-fix; the channel was previously a dead pipe on design) | `scripts/qrspi_review_synopsis_test.py` (non-blocking passthrough + advisory section). NOTE: lens *emission* of `nonBlockingNotes` is prompt-level, not unit-testable here |
| AC6: Honest verdict — synopsis enumerates which axes ran + per-lens pass | `render_synopsis()` axis-enumeration table in `scripts/qrspi_review_synopsis.py` | `scripts/qrspi_review_synopsis_test.py` (axis enumeration) |
| AC7: Producer-as-reviser replaced with non-producer reviser | `.claude/agents/qrspi-critic-reviser.md` (shared, phase-parameterized); `subagent_type` swap in all four SKILLs | Agent existence + frontmatter validation (impl-log Sessions 2–5); deferred live routing probe |
| AC8: Regression check — descoping fixture yields no clean pass | REUSE `evals/fixtures/design_dropped_criterion_broken.md` + provenance row in `evals/fixtures/README.md` | **STRUCTURAL fixture-integrity check only** via the pre-existing `scripts/qrspi_teeth_test.py` (RUS-77; a deterministic stated-minus-covered string check — it does NOT spawn or run the review lenses) confirms the fixture carries a detectable dropped "403 unless admin" AC. PLUS a LIVE lens-level regression run (2026-06-18): the `completeness` and `edge-alignment` design lenses were spawned over the fixture (design + `ticket_rest_endpoint.md` + `research_rest_endpoint.md`) and BOTH returned `pass:false`, each naming the dropped "403 unless admin" AC as a blocking finding — confirming the upgraded panel (which runs these lenses; the old `/review-design` ran ONLY `design-review` and missed it) catches the descope. The full `/review-design` *command* run (incl. the new `decision-readiness` agent + PR-comment write) still requires RUS-91 to be landed |
| AC9: Propose-only invariant preserved (scratch copy, unchanged head SHA, comment-only) | head-SHA guard prose + `OUTPUT_PATH`=scratch-verbatim contract in `qrspi-critic-reviser.md`; all four SKILLs' Step 2/8 guards | Deferred to human/e2e pass (see Open Items); encoded in SKILL Hard rules |
| AC10: Whole-stack `/review` composes the upgraded panels | `.claude/skills/review/SKILL.md` binding table + per-phase synopsis sub-sections | Deterministic core probe + agent existence (impl-log Session 5); deferred live e2e |

## Changes by Slice

### Slice 1: Per-phase lens config + synopsis/ledger helpers (tested pure core)

| File | Change | Lines |
|------|--------|-------|
| `scripts/qrspi_critics_config.py` | ⚠️ modified | +39 |
| `scripts/qrspi_critics_config_test.py` | ✨ new | +55 |
| `scripts/qrspi_review_synopsis.py` | ✨ new | +182 |
| `scripts/qrspi_review_synopsis_test.py` | ✨ new | +155 |
| `scripts/qrspi_critic_summary_test.py` | ✨ new | +41 |

(`qrspi_critic_summary.py` confirmed a no-op per plan step 8 — the reader is already `.get()`-lenient; only the backward-compat test was added.)

### Slice 2: Shared non-producer reviser + five new lens agents

| File | Change | Lines |
|------|--------|-------|
| `.claude/agents/qrspi-critic-reviser.md` | ✨ new | +71 |
| `.claude/agents/qrspi-plan-critic-plan-fidelity.md` | ✨ new | +107 |
| `.claude/agents/qrspi-plan-critic-plan-completeness.md` | ✨ new | +101 |
| `.claude/agents/qrspi-impl-critic-impl-fidelity.md` | ✨ new | +113 |
| `.claude/agents/qrspi-impl-critic-impl-completeness.md` | ✨ new | +111 |
| `.claude/agents/qrspi-design-critic-decision-readiness.md` | ✨ new | +90 |

### Slice 3: Upgrade /review-design (reference wiring)

| File | Change | Lines |
|------|--------|-------|
| `.claude/skills/review-design/SKILL.md` | ⚠️ modified | +170, -? |

### Slice 4: Upgrade /review-plan and /review-implementation

| File | Change | Lines |
|------|--------|-------|
| `.claude/skills/review-plan/SKILL.md` | ⚠️ modified | +150 |
| `.claude/skills/review-implementation/SKILL.md` | ⚠️ modified | +164 |

### Slice 5: Upgrade whole-stack /review + regression fixture

| File | Change | Lines |
|------|--------|-------|
| `.claude/skills/review/SKILL.md` | ⚠️ modified | +154 |
| `evals/fixtures/README.md` | ⚠️ modified | +12 |

(QRSPI phase artifacts under `.qrspi/RUS-91/` — design.md, plan.md, structure.md, questions.md, research.md, worktree.md, impl-log.md — are also in the diff as workflow bookkeeping, not product changes.)

## Testing Summary

- [x] Slice 1: unit tests — `python3 scripts/run_tests.py` — 42 passed, 0 failed
- [x] Slice 1: filtered — `python3 scripts/run_tests.py critic` — 6 passed; `… synopsis` — 1 passed
- [x] Slice 1: backward-compat — old-style `critic-metrics.jsonl` row (no `axes`/`nonBlockingNotes`) still parses
- [x] Slice 2: agent-frontmatter validation — all 6 agents well-formed, `name` == filename, `description`+`tools` present
- [x] Slice 2: regression gate — `python3 scripts/run_tests.py` — 42 passed (no new Python)
- [x] Slice 3: embedded-snippet verification — Steps 4b/6/7 Python blocks asserted against a 6-element verdict array; all assertions pass
- [x] Slice 4: referenced-agent existence — all 7 `subagent_type`s exist; embedded snippets over plan/impl panels pass
- [x] Slice 5: STRUCTURAL fixture-integrity check — the pre-existing `qrspi_teeth_test.py` (RUS-77; does NOT spawn the review lenses) confirms `design_dropped_criterion_broken.md` carries a detectable dropped "403 unless admin" AC
- [x] Slice 5: LIVE lens-level regression run (2026-06-18) — `completeness` + `edge-alignment` lenses spawned over `design_dropped_criterion_broken.md` + `ticket_rest_endpoint.md` + `research_rest_endpoint.md`; BOTH returned `pass:false` flagging the dropped "403 unless admin" AC as blocking (the old single-lens `/review-design` missed it). This is the real lens run the earlier structural check was mislabeled as.
- [ ] Full `/review-design` command e2e (incl. the new `decision-readiness` lens spawn + propose-only head-SHA guard + PR-comment write) — requires RUS-91 landed so the new agents are in the registry; DEFERRED, see Open Items
- [x] Slice 5: regression gate — `python3 scripts/run_tests.py` — 42 passed, 0 failed
- [ ] Manual verification (DEFERRED): live `/review-*` e2e over real PRs + head-SHA before/after propose-only guard — see Open Items

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| (none) | | | Structure §New Types/§Contracts followed; all six agent filenames use the phase-qualified authoritative names from structure.md/plan.md (NOT the worktree.md shorthand) per the load-bearing `qrspi-<phase>-critic-<lens-id>` mapping |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| New plan/impl lenses written fidelity-only reproduce the rubber-stamp bug | mitigated — lens prompts enforce a named descoping counter-example OR affirmative per-AC checklist + fail-closed `pass:false`; lens-level fixture probe confirms a blocking finding on the descoped fixture | Revert the lens agent files (Slice 2) |
| Passing `TICKET_CONTENT_PATH` conflicts with the research-firewall intent | mitigated — ticket scoped to fidelity/completeness/decision-readiness lenses ONLY; node-validity `*-review` lenses stay research+code-only | Revert ticket plumbing in the SKILL Step 3 edits |
| Multi-lens panel changes convergence, breaking synthesize/loop tests | mitigated — reducers unchanged; `run_tests.py` green (42 passed) across all slices | Revert config/synopsis helpers (Slice 1) |
| Partially-landed-stack misfire in `/review-implementation` (no `--state all`) | mitigated — `/review-implementation` now resolves the top slice PR via `gh pr list --head <tip> --state all` (Slice 4) | Revert the frontier-guard edit in `review-implementation/SKILL.md` |
| Non-blocking channel makes synopsis noisy / never-passing | mitigated — gate keys on blocking `findings` only; `nonBlockingNotes` rendered as a clearly-advisory section | Revert `render_synopsis()` non-blocking section |
| Propose-only invariant regressed by a new reviser writing a tracked path/branch | accepted-pending-verification — reviser contract is `OUTPUT_PATH`=scratch-verbatim + `Write`-only-to-scratch; LIVE head-SHA before/after guard NOT yet exercised (deferred) | Revert `qrspi-critic-reviser.md` and the four `subagent_type` swaps |

## Open Items

- **Live e2e validation deferred to a human/e2e pass** (consistent across Slices 3–5): T35–T37, T49–T51, T57 — live `/review-design`/`/review-plan`/`/review-implementation`/`/review` runs over real Linear tickets with existing phase PRs, plus the frontier-PR head-SHA before/after propose-only guard. These require live `mcp__linear__get_issue`, live `Agent`-tool subagent spawns, and `gh` PR-comment writes — out of scope for the deterministic implement-phase agent. The deterministic core (helpers, fixture probe, agent existence, full test suite) is verified green.
- **Subagent triggering (`claude -p` routing probes) deferred** (T24–T27): the six new `.claude/agents/*.md` are subagents, not SKILL.md skills, and the sandbox `skill-creator` `run_eval`/`run_loop` returns bogus uniform results (per MEMORY directive). Agents were authored to exact fidelity with the three already-shipped sibling lens agents and validated structurally; live routing validation of the new `subagent_type`s remains for a human pass.
- **AC8 honesty correction + live lens-level run (PERFORMED 2026-06-18):** the pre-existing RUS-77 `qrspi_teeth_test.py` is a STRUCTURAL fixture-integrity string check, NOT a run of the review lenses — the earlier "lens-level regression probe" wording overstated it. The genuine lens-level run was then performed: the `completeness` and `edge-alignment` design lenses were spawned over `design_dropped_criterion_broken.md` + `ticket_rest_endpoint.md` + `research_rest_endpoint.md`, and BOTH returned `pass:false` naming the dropped "403 unless admin" AC as a blocking finding (the old single-lens `/review-design` ran only `design-review` and missed it). What remains open is the full `/review-design` *command* e2e — incl. the new `decision-readiness` lens spawn, the propose-only head-SHA guard, and the PR-comment write — which needs RUS-91 landed so the new agents are in the registry. (The originally-cited anchor RUS-86 / PR #347 is now CLOSED and its `RUS-86/design` branch is gone, so the fixture was used instead.)
- **worktree.md filename shorthand mismatch** (documentation-only): the worktree.md task table lists shorter agent filenames (`qrspi-plan-critic-fidelity.md` etc.); structure.md/plan.md phase-qualified names are authoritative and were followed. No code impact, but worktree.md could be reconciled in a follow-up.
