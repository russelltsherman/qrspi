# PR: RUS-57 critics 3/5 — single edge critics + citation validator

**Ticket:** RUS-57
**Design:** design.md @ 2026-06-13T00:00:00Z
**Structure:** structure.md @ 2026-06-13T00:00:00Z

## Summary

Wires a single edge critic into each QRSPI planning phase (questions, research,
structure, plan), each anchored on its correct upstream artifact, and adds a new
deterministic citation validator that gates the research phase. The new
stdlib-only `scripts/qrspi_verify_citations.py` parses research.md `file:line`
citations and hard-fails the phase only when a cited file exists but the line is
out of bounds — a wholly-absent file is tolerated as a same-stack forward
reference (reviewer-resolved OQ3). Per-phase critic `maxRounds` is now
config-overridable via `critics.<phase>.maxRounds`, mirroring the existing design
phase. Reviewers should focus on two load-bearing invariants: the **research
firewall** (research's critic upstream is `questions.md`, never the ticket) and
**worktree-root resolution** (the validator joins citations against `--worktree-root wd`,
never `resolve_repo_root()`, which returns the main checkout). Note the JS glue is
unverifiable by automated test (no JS test runner per project convention); all
testable logic lives in the fully unit-tested Python validator.

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: each planning phase runs its single edge critic before submit, upstream supplied as anchor | `.claude/workflows/qrspi-batch.js` `doDesign`/`doPlan` (questions→`r.ticketContentPath`, research→`art(wd,id,'questions.md')`, structure→`art(wd,id,'design.md')`, plan→`art(wd,id,'structure.md')`) + `resolveEdgeCriticMaxRounds` | Manual e2e (per-round `log()` upstream-anchor confirmation); no JS test runner — `node --check` syntax OK |
| AC2: research runs `qrspi_verify_citations.py`; a non-resolving citation fails the phase with the verbatim token | `scripts/qrspi_verify_citations.py` (`parse_citations`, `resolve_citation`, CLI) + `runPhase` `criticConfig.nodeCheck` branch in `.claude/workflows/qrspi-batch.js` | `scripts/qrspi_verify_citations_test.py` (16 passed); CLI smoke: out-of-range `real.py:99` → `ok:false`, `["real.py:99"]`, exit 1 |
| AC3: per-phase eval scores reported before/after | Not implemented in code — eval harness is a non-functional placeholder; routed to per-round `log()` + manual e2e spliced into PR body (design OQ1) | None — carried-forward unverified assumption, human-confirmation item (see Open Items) |

## Changes by Slice

### Slice 1: Citation validator script + unit tests

| File | Change | Lines |
|------|--------|-------|
| `scripts/qrspi_verify_citations.py` | new | +201 |
| `scripts/qrspi_verify_citations_test.py` | new | +139 |

### Slice 2: Wire four edge critics + research node check into the orchestrator

| File | Change | Lines |
|------|--------|-------|
| `.claude/workflows/qrspi-batch.js` | modified | +162, -24 |
| `.qrspi/config.example.json` | modified | +13, -1 |

### Phase artifacts (non-slice, this PR's own QRSPI trail)

| File | Change | Lines |
|------|--------|-------|
| `.qrspi/RUS-57/questions.md` | new | +53 |
| `.qrspi/RUS-57/research.md` | new | +462 |
| `.qrspi/RUS-57/design.md` | new | +113 |
| `.qrspi/RUS-57/structure.md` | new | +65 |
| `.qrspi/RUS-57/plan.md` | new | +125 |
| `.qrspi/RUS-57/worktree.md` | new | +54 |
| `.qrspi/RUS-57/impl-log.md` | new | +64 |

## Testing Summary

- [x] Slice 1: unit tests — `python3 scripts/qrspi_verify_citations_test.py` — 16 passed, 0 failed
- [x] Slice 1: CLI smoke — out-of-range `real.py:99` → `{"ok": false, "unresolved": ["real.py:99"]}` exit 1; clean (valid `file:line` + absent-file forward ref) → `{"ok": true, "unresolved": []}` exit 0
- [x] Slice 2: JS syntax — `node --check .claude/workflows/qrspi-batch.js` — OK
- [x] Slice 2: ad-hoc node unit test of `parseCriticsObject` + `resolveEdgeCriticMaxRounds` — 14 passed, 0 failed (positive-int honored; 0/negative/non-int/absent-phase/undefined/empty-obj fall back to 2)
- [x] Slice 2: config — `python3 -c json.load(.qrspi/config.example.json)` — valid JSON
- [x] Slice 2: validator CLI against exact `nodeCheck.cmd` form (`--artifact-path <staged> --worktree-root <wd>`) — in-bounds + absent-file → `ok:true` exit 0; out-of-bounds → `ok:false` exit 1
- [x] Slice 1 regression after Slice 2 — 16 passed, 0 failed
- [ ] Manual e2e (deferred to reviewer — no JS test runner): design-phase batch run confirming each phase spawns an edge critic with the expected upstream anchor (questions→ticket, research→questions.md NEVER ticket, structure→design.md); staged research.md with out-of-range citation fails research and persists nothing; absent-file citation does NOT fail; `critics.research.maxRounds` honored via `log()`

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| `NodeCheckSpec` shape | TBD in implementation (structure left it unpinned) | `{ cmd: <full command string> }`, command built at the `doDesign` call site where `wd`/`r` are in scope and carried verbatim | Minimal shape consistent with `runPhase` plumbing; `runPhase`/`runNodeCheck` need no path context. Resolves the structure's explicit `NodeCheckSpec` TBD. |
| T16 residual-findings splice | Per-phase `criticBodyStep(t.id,'questions',…)` splice | Aggregated: questions+research residuals fold into the single `<id>/design` commit splice (tagged `[questions]`/`[research]`); structure into the `<id>/plan` splice (tagged `[structure]`) | `scripts/qrspi_critic_body.py` only knows `design`/`plan` branch suffixes (`--phase` is `choices=['design','plan']`); there is no questions/research/structure branch. The literal per-phase call would have been rejected by the script. Realizes design intent (same `criticBodyStep`/`criticSummary` mechanism) without inventing unaddressable branches. |
| `doPlan` config read | Thread doDesign's existing parsed `critics` result | `doPlan` does its own `--key critics` read via extended `readDesignCriticConfig()` returning `parsedCritics` | `doDesign`/`doPlan` are separate batch actions/invocations; doDesign's read is not reachable from doPlan. Still one read per invocation (Q6/Q8 honored). |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| Validator resolves citations against the main checkout instead of the worktree (med/high) | mitigated — `nodeCheck.cmd` passes `--worktree-root ${wd}` (never `r.repoRoot`); test asserts resolution against a tempdir root, not `resolve_repo_root()` | Revert `.claude/workflows/qrspi-batch.js`; validator is unreferenced and inert |
| Research edge critic anchored on the ticket, breaching the research firewall (med/high) | mitigated — `researchCritic.upstreamPath = art(wd,t.id,'questions.md')` with a guard comment that it is NEVER `r.ticketContentPath`; verified present | Revert the `doDesign` research `criticConfig` wiring |
| Citation validator false-positives on placeholder/glob tokens (med/med) | mitigated — `parse_citations` excludes `*`/`<`/`>` tokens; `_test.py` covers excluded forms; bare code-words (no `/` or extension) not treated as citations | Set `critics.research` nodeCheck off / revert validator wiring |
| Node check runs against canonical instead of staged path, persisting a bad artifact (low/high) | mitigated — node check runs on `stg(id,'research')` before `persistArtifact`; `runPhase` returns false on non-ok so nothing persists | n/a (gate is pre-persist by construction) |
| New JS wiring untested — no JS test runner (high/med) | accepted — all testable logic kept in fully-unit-tested Python; JS glue verified by `node --check` + ad-hoc helper test + manual e2e per project convention | Revert `.claude/workflows/qrspi-batch.js` (single file) |

## Open Items

- **AC3 (per-phase before/after eval scores)** is not satisfied by code — the `evals/`/`run_eval.py` harness is a non-functional placeholder. Routed to per-round `log()` output + manual e2e spliced into the PR body (design OQ1). Needs human confirmation that `log()`-derived observation satisfies AC3, or AC3 is deferred to a follow-up ticket.
- **OQ2 — phase-tailored `rubric` lines** are undecided. `EdgeCriticConfig` allows an optional `rubric`, but generic single critics are wired by default (no per-phase framing such as questions = "high-leverage ambiguities", structure = "no scope creep"). Non-blocking enhancement pending the human's OQ2 answer.
- **Manual e2e is unrun in this environment** — the four e2e checks in the Testing Summary (upstream-anchor confirmation, out-of-range fail-and-persist-nothing, absent-file tolerance, `maxRounds` honored) are deferred to the reviewer, since no JS test runner exists per project convention.
