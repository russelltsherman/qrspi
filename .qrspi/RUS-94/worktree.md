# Work Tree — Self-verifying design & plan producers: codebase-grounded claim checks + pre-persist verification gate

**Plan basis:** plan.md @ 2026-06-19
**Generated:** 2026-06-19T00:00:00Z
**Status:** draft
**Total sessions:** 4
**Critical path:** T1 → T2 → T3 → T4 → T6 → T7 → T16 (Slice 1 core) ⇒ T17 → T19 (Slice 2 sink) ⇒ T20→T21→T22→T23 / T24→T25→T26→T27 → T28 (Slice 3 producers) ⇒ T29 / T30 → T31 → T32 → T33 → T37 → T38 (Slice 4 gate)
Longest dependency chain (16 tasks): **T1 → T2 → T3 → T4 → T6 → T7 → T16 → T17 → T19 → T20 → T26 → T28 → T31 → T32 → T37 → T38**

> Sessions are aligned 1:1 with plan slices: each slice ends in a fresh context per the QRSPI workflow rule ("Start a fresh `/clear` session between implementation slices"). Slice 1 ships the verified Python core + seam fixtures; Slice 2 adds the plan-side Open Questions sink that the Slice 1 constant must match; Slice 3 rewires both producer agents to read code and fail closed into that sink; Slice 4 wires the pre-persist gate into the orchestrator. Each load manifest references only the sections needed for that slice.

## Session 1 — Slice 1: Verification core + tests + seam fixtures

**Load:** structure.md §Types, structure.md §Contracts, plan.md §Slice 1, design.md §Decision 1, §AC3/§AC4/§AC6, §Delta; reference module `scripts/qrspi_persist.py` (helper convention only)
**Estimated context:** ~22%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create `scripts/qrspi_verify_artifact.py` scaffold (docstring, stdlib imports, self-locating root, placeholder `main()` exit 0) | — | §1.1 | S | pending |
| T2 | Add `extract_acs(ticket_text) -> list[dict]` (parse `## Acceptance Criteria`; missing/malformed → `[]`) | T1 | §1.2 | M | pending |
| T3 | Add `build_coverage_map(acs, artifact_text) -> list[dict]` (set `mapped=True` iff AC id referenced) | T2 | §1.3 | S | pending |
| T4 | Add `scan_dangling_refs(artifact_text, valid_sinks) -> list[dict]` (Open Questions heading is a valid sink) | T2 | §1.4 | M | pending |
| T5 | Add module constant `OPEN_QUESTIONS_HEADING = "## Open Questions"` (single source of truth) | T1 | §1.5 | S | pending |
| T6 | Add `decide(acs, coverage, dangling, has_signal) -> tuple` tri-state; enforce `pass:false ⟺ findings non-empty` | T3, T4, T5 | §1.6 | M | pending |
| T7 | Replace placeholder `main()` with real argparse CLI emitting `VerifyEnvelope` JSON; exit mirrors `ok` | T6 | §1.7 | M | pending |
| T8 | Create `scripts/qrspi_verify_artifact_test.py`; add `extract_acs` cases (wellformed/missing/malformed) | T2 | §1.8 | S | pending |
| T9 | Add `build_coverage_map` test cases (AC3 unmapped; all mapped) | T3, T8 | §1.9 | S | pending |
| T10 | Add `scan_dangling_refs` test cases (missing heading → finding; Open Questions sink → none) | T4, T8 | §1.10 | S | pending |
| T11 | Add `decide` tri-state test cases; assert `pass:false ⟺ findings non-empty` | T6, T8 | §1.11 | S | pending |
| T12 | Create fixture `verify-artifact/wellformed.json` (signal `pass`, ok true, empty findings) | T7 | §1.12 | S | pending |
| T13 | Create fixture `verify-artifact/fail.json` (signal `fail`; one `unmapped_ac` + one `dangling_ref`) | T7 | §1.13 | S | pending |
| T14 | Create fixture `verify-artifact/none.json` (signal `none` pass-through) | T7 | §1.14 | S | pending |
| T15 | Create fixture `verify-artifact/malformed.json` (missing/wrong-type field for rejection test) | T7 | §1.15 | S | pending |
| T16 | **Verify Slice 1** — `run_tests.py verify_artifact` green; `main()` prints well-formed envelope; tri-state covered | T7, T11, T12, T13, T14, T15 | §1.16 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 ships the standalone, tested verification core + golden fixtures. Slice 2 touches a disjoint file set (templates + plan agent) and only needs the `OPEN_QUESTIONS_HEADING` literal from Slice 1, not the whole module-build context. Fresh context.

## Session 2 — Slice 2: Plan-side Open Questions sink (template + agent)

**Load:** plan.md §Slice 2, design.md §AC4/§Delta plan.md note; `.qrspi/templates/design.md` §Open Questions (mirror source); impl-log §Slice 1 — the literal value of `OPEN_QUESTIONS_HEADING` (notes only)
**Estimated context:** ~12%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T17 | Add `## Open Questions` section to `.qrspi/templates/plan.md` after `## Rollback Notes` (OQ`N:` bullets, prose-only); heading literal MUST match `OPEN_QUESTIONS_HEADING` | T16 | §2.17 | S | pending |
| T18 | Add Open-Questions authoring step to `.claude/agents/qrspi-plan.md` (route unconfirmable claims to the sink) | T17 | §2.18 | S | pending |
| T19 | **Verify Slice 2** — `## Open Questions` in plan template + agent prose; heading matches Slice 1 constant | T17, T18 | §2.19 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 2 establishes the fail-closed sink heading. Slice 3 rewires both producer agents (design + plan) to read code and route unconfirmable claims into that sink; it is a larger, agent-prose-heavy slice needing the design ACs and RUS-82 lens posture, not the template-diff context. Fresh context.

## Session 3 — Slice 3: Code-grounded producers (design + plan agents)

**Load:** plan.md §Slice 3, design.md §AC1/§AC2/§AC3/§AC5, §Risk rows 1/3, OQ3/OQ4; RUS-82 lens posture reference; impl-log §Slice 2 (Open Questions sink heading, notes only)
**Estimated context:** ~24%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T20 | `.claude/agents/qrspi-design.md` — change tools to `Read, Grep, Glob` | T19 | §3.20 | S | pending |
| T21 | `qrspi-design.md` — document new `REPO_ROOT` input (RUS-82 lens posture) | T20 | §3.21 | S | pending |
| T22 | `qrspi-design.md` — reframe research-as-map / code-as-verification; state fail-closed rule (unconfirmable claim → Open Question); leave stale FRAMING/N-select prose (OQ4) | T21 | §3.22 | M | pending |
| T23 | `qrspi-design.md` — add self-verification pass covering AC2/AC3/AC4/AC5 | T22 | §3.23 | M | pending |
| T24 | `.claude/agents/qrspi-plan.md` — change tools to `Read, Grep, Glob` | T19 | §3.24 | S | pending |
| T25 | `qrspi-plan.md` — document new `REPO_ROOT` and `TICKET_CONTENT_PATH` inputs | T24 | §3.25 | S | pending |
| T26 | `qrspi-plan.md` — reframe research-as-map / code-as-verification; route unconfirmable claims to the Slice 2 `## Open Questions` sink | T25 | §3.26 | M | pending |
| T27 | `qrspi-plan.md` — add self-verification pass (AC coverage vs ticket text per OQ3, AC2/AC4/AC5) | T26 | §3.27 | M | pending |
| T28 | **Verify Slice 3** — both agents declare `Read, Grep, Glob` + document inputs; prose reframes + fail-closed rule; manual e2e converts ≥1 unconfirmable claim to an Open Question | T23, T27 | §3.28 | M | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 3 finishes the producer-agent rewiring. Slice 4 is the orchestration wiring in `qrspi-batch.js` plus its `node:vm` consumer test and CLAUDE.md docs — a JS/orchestration context disjoint from the agent-prose context of Slice 3, depending only on the Slice 1 CLI contract and Slice 3's input names. Fresh context.

## Session 4 — Slice 4: Pre-persist gate wiring in qrspi-batch.js

**Load:** plan.md §Slice 4, design.md §Decision 2/§Decision 3, §AC6/§AC7, §Risk row 5, §Delta Q12; structure.md §JS gate contract, §Modified Types, §Unverified Assumptions; impl-log §Slice 1 (`VerifyEnvelope` CLI contract) + §Slice 3 (`REPO_ROOT`/`TICKET_CONTENT_PATH` input names), notes only
**Estimated context:** ~26%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T29 | `qrspi-batch.js` — add `REPO_ROOT = wd` to the design producer spawn input splice | T28 | §4.29 | S | pending |
| T30 | `qrspi-batch.js` — add `REPO_ROOT = wd` and `TICKET_CONTENT_PATH = r.ticketContentPath` to the plan producer spawn splice | T28 | §4.30 | S | pending |
| T31 | `qrspi-batch.js` — add `runVerifyGate(id, name, repoRoot)` helper (shell the CLI, parse stdout → `VerifyEnvelope`) | T16, T29, T30 | §4.31 | M | pending |
| T32 | `qrspi-batch.js` — insert bounded producer loop in `runPhase`: produce → verify; `fail` re-produce up to bound 2; `pass`/`none` → persist; exhaustion → return `false` | T31 | §4.32 | M | pending |
| T33 | `qrspi-batch.js` — on exhaustion set `verifyFailed` ride-along flag + distinct `log()` line (gate/phase/findings count) | T32 | §4.33 | S | pending |
| T34 | `.claude/CLAUDE.md` — document the producer self-verification gate (Python core, JS gate, tri-state, bound 2, `verifyFailed` terminal path) (AC7) | T33 | §4.34 | S | pending |
| T35 | (Conditional) add extra `verify-artifact/*` fixture only if Slice 4 consumer needs one beyond Slice 1 (else no-op) | T32 | §4.35 | S | pending |
| T36 | (Conditional) add `node:vm` `parseVerify*` consumer test only if `runPhase` parses the envelope beyond a presence check (wellformed parses / malformed rejected) | T32, T15 | §4.36 | M | pending |
| T37 | **Verify Slice 4** — `python3 scripts/run_tests.py` green; `node:vm` consumer test (if added) asserts wellformed parses + malformed rejected | T33, T34, T36 | §4.37 | S | pending |
| T38 | **Verify Slice 4 (manual e2e)** — design+plan spawns include `REPO_ROOT` (plan also `TICKET_CONTENT_PATH`); clean persists; unmapped-AC re-produces to bound 2 then `runPhase`→`false` + `failTicket` records `verifyFailed` (nothing persisted); no-signal persists (backward-compat) | T37 | §4.38 | M | pending |

--- SESSION BOUNDARY ---
**Reason:** All four slices complete. End of feature; nothing follows.
