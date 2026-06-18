# Work Tree — Bring the /review-* on-demand review family up to manual-review depth

**Plan basis:** plan.md @ 2026-06-18T02:00:00Z
**Generated:** 2026-06-18T02:30:00Z
**Status:** draft
**Total sessions:** 5
**Critical path:** T1 → T2 → T3 → T4 → T5 → T10 → T12 → T22 → T28 → T29 → T31 → T32 → T33 → T34 → T37 → T39 → T43 → T51 → T53 → T56 → T58

## Session 1 — Per-phase lens config + synopsis/ledger helpers (tested pure core)

**Load:** structure.md §Modified Types, structure.md §Contracts, structure.md §Slice 1, plan.md §Slice 1
**Estimated context:** ~22% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Add `KNOWN_PLAN_LENSES`/`KNOWN_IMPL_LENSES` constants + default panels to `qrspi_critics_config.py` (read file first to confirm `KNOWN_DESIGN_LENSES` shape/naming) | — | §1.1 | S | pending |
| T2 | Create `scripts/qrspi_review_synopsis.py` exposing `render_synopsis()`, `partition_decision_readiness()`, `ledger_row_fields()` | T1 | §1.2 | S | pending |
| T3 | Implement `partition_decision_readiness(verdictArray)` — split decision-readiness lens out of pre-reduction array | T2 | §1.3 | M | pending |
| T4 | Implement `render_synopsis(...)` — axis enumeration + non-blocking section + decision-readiness section + terminal action | T3 | §1.4 | M | pending |
| T5 | Implement `ledger_row_fields(verdictArray)` — derive additive `axes` + `nonBlockingNotes` metrics fields | T3 | §1.5 | S | pending |
| T6 | Create `qrspi_review_synopsis_test.py` covering all three helpers (axis enumeration, non-blocking passthrough, partition incl. absent-lens, ledger shape) | T4, T5 | §1.6 | M | pending |
| T7 | Extend `qrspi_critics_config_test.py` — assert new per-phase constants + default panel membership | T1 | §1.7 | S | pending |
| T8 | Modify `qrspi_critic_summary.py` ONLY IF gap — confirm `.get()`-default reads of new optional row fields (no-op if already lenient) | T5 | §1.8 | S | pending |
| T9 | Extend `qrspi_critic_summary_test.py` — old-style row (no new keys) still parses + new-style row surfaces fields | T8 | §1.9 | S | pending |
| T10 | **Verify Slice 1** — `python3 scripts/run_tests.py` green; `critic` + `synopsis` filters pass; backward-compat fixture holds | T6, T7, T9 | §1.10 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 (pure Python core) complete and tested. Slice 2 authors `.md` agents via skill-creator — a different toolset and concern; fresh context drops the Python implementation detail.

## Session 2 — Shared non-producer reviser + five new lens agents

**Load:** structure.md §Slice 2, structure.md §Contracts (qrspi-critic-reviser, lens agents), structure.md §New Types (DecisionReadinessVerdict), plan.md §Slice 2, impl-log.md §Slice 1 (notes only)
**Estimated context:** ~26% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T11 | Invoke `skill-creator` skill before authoring any agent (use its authoring + eval loop for each) | T10 | §2.11 | S | pending |
| T12 | Create `.claude/agents/qrspi-critic-reviser.md` — shared phase-parameterized (`PHASE`) non-producer reviser | T11 | §2.12 | M | pending |
| T13 | Encode reviser contract: writes ONLY to `OUTPUT_PATH`; propose-only; `RESIDUAL_FINDINGS` excludes decision-readiness | T12 | §2.13 | S | pending |
| T14 | Create `.claude/agents/qrspi-plan-critic-fidelity.md` — adversarial plan fidelity lens (`LensVerdict`) | T11 | §2.14 | M | pending |
| T15 | Encode plan-fidelity adversarial contract: `TICKET_CONTENT_PATH` input; named counter-example OR per-AC checklist; fail-closed | T14 | §2.15 | S | pending |
| T16 | Create `.claude/agents/qrspi-plan-critic-completeness.md` — plan completeness lens (`LensVerdict`) | T11 | §2.16 | M | pending |
| T17 | Encode plan-completeness adversarial contract (counter-example OR per-AC checklist; fail-closed; `TICKET_CONTENT_PATH`) | T16 | §2.17 | S | pending |
| T18 | Create `.claude/agents/qrspi-impl-critic-fidelity.md` — adversarial impl fidelity lens (`LensVerdict`) | T11 | §2.18 | M | pending |
| T19 | Encode impl-fidelity adversarial contract (counter-example OR per-AC checklist; fail-closed) | T18 | §2.19 | S | pending |
| T20 | Create `.claude/agents/qrspi-impl-critic-completeness.md` — impl completeness lens (`LensVerdict`; `TICKET_CONTENT_PATH`) | T11 | §2.20 | M | pending |
| T21 | Encode impl-completeness adversarial contract (counter-example OR per-AC checklist; fail-closed) | T20 | §2.21 | S | pending |
| T22 | Create `.claude/agents/qrspi-design-critic-decision-readiness.md` — non-producer decision-readiness lens emitting `DecisionReadinessVerdict` (blockingDecisions vs answerable) | T11 | §2.22 | M | pending |
| T23 | Run skill-creator eval/authoring loop for all six agents until convergence | T13, T15, T17, T19, T21, T22 | §2.23 | M | pending |
| T24 | Validate triggering for each new agent via direct `claude -p` routing probes (sandbox `run_eval` invalid) | T23 | §2.24 | M | pending |
| T25 | Manual descoped-sample probe: each fidelity/completeness lens emits counter-example OR per-AC checklist; defaults `pass:false` | T24 | §2.25 | S | pending |
| T26 | Manual probe: `qrspi-critic-reviser` writes ONLY to `OUTPUT_PATH`, no tracked-path/branch mutation | T24 | §2.26 | S | pending |
| T27 | **Verify Slice 2** — routing probes per agent + descoped-sample probe; loop converged; lenses emit correct verdict shapes; reviser propose-only | T25, T26 | §2.27 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Agents authored and validated in isolation. Slice 3 wires them into the reference SKILL.md end-to-end — a wiring/orchestration concern; fresh context drops the per-agent authoring detail and loads SKILL.md structure.

## Session 3 — Upgrade /review-design end-to-end (reference wiring)

**Load:** structure.md §Slice 3, structure.md §Contracts, plan.md §Slice 3, impl-log.md §Slice 1–2 (notes only: helper signatures + agent subagent_types)
**Estimated context:** ~28% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T28 | Read `.claude/skills/review-design/SKILL.md` in full to map current fan-out, synthesize pipe, Step 5, reviser invocation | T27 | §3.28 | S | pending |
| T29 | Fan-out: replace single `design-review` lens with full five-lens design panel (from config default) | T28 | §3.29 | M | pending |
| T30 | Ticket plumbing: fetch via `mcp__linear__get_issue`, stage to `TICKET_CONTENT_PATH`, pass to edge-alignment/completeness/decision-readiness lenses ONLY | T28 | §3.30 | M | pending |
| T31 | Partition step: call `partition_decision_readiness()` before `qrspi_critic_synthesize.py` pipe | T29 | §3.31 | S | pending |
| T32 | Replace Step 5 self-grading open-question pass with `qrspi-design-critic-decision-readiness` lens spawn (feeds synopsis only) | T30, T31 | §3.32 | M | pending |
| T33 | Reviser swap: change revise-loop `subagent_type` to `qrspi-critic-reviser` (`PHASE=design`, residual findings only) | T31 | §3.33 | S | pending |
| T34 | Synopsis widening: replace prose synopsis with `render_synopsis()`; append `ledger_row_fields()` to ledger row | T32, T33 | §3.34 | M | pending |
| T35 | End-to-end `/review-design <id>` over a ticket with a design PR; verify five-lens synopsis + non-blocking section + ticket plumbing | T34 | §3.35 | M | pending |
| T36 | Checkpoint guard: capture PR head SHA before/after; assert equality (propose-only) | T35 | §3.36 | S | pending |
| T37 | **Verify Slice 3** — axis-enumerated five-lens synopsis; head SHA unchanged; decision-readiness surfaces but triggers no reviser round; ticket to fidelity/completeness/decision-readiness lenses only | T36 | §3.37 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Reference wiring proven on review-design. Slice 4 replicates the same pattern across review-plan and review-implementation; fresh context carries the proven pattern as notes rather than the full design-wiring transcript.

## Session 4 — Upgrade /review-plan and /review-implementation

**Load:** structure.md §Slice 4, structure.md §Contracts, plan.md §Slice 4, impl-log.md §Slice 3 (notes only: the proven review-design wiring pattern)
**Estimated context:** ~30% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T38 | Read `.claude/skills/review-plan/SKILL.md` + `review-implementation/SKILL.md` in full; mirror Slice 3 step map (+ impl frontier step) | T37 | §4.38 | S | pending |
| T39 | review-plan fan-out: replace single `plan-review` lens with `KNOWN_PLAN_LENSES` panel | T38 | §4.39 | M | pending |
| T40 | review-plan ticket plumbing: fetch + stage to `TICKET_CONTENT_PATH`; pass to fidelity/completeness lenses ONLY | T38 | §4.40 | S | pending |
| T41 | review-plan reviser swap: `subagent_type` → `qrspi-critic-reviser` (`PHASE=plan`) | T39 | §4.41 | S | pending |
| T42 | review-plan synopsis widening: `render_synopsis()` + `ledger_row_fields()` | T40, T41 | §4.42 | S | pending |
| T43 | review-implementation fan-out: replace single `impl-review` lens with `KNOWN_IMPL_LENSES` panel | T38 | §4.43 | M | pending |
| T44 | review-implementation: define lens input granularity — aggregated slice stack (one panel pass), not per-slice | T43 | §4.44 | S | pending |
| T45 | review-implementation ticket plumbing: fetch + stage to `TICKET_CONTENT_PATH`; pass to fidelity/completeness lenses ONLY | T38 | §4.45 | S | pending |
| T46 | review-implementation reviser swap: `subagent_type` → `qrspi-critic-reviser` (`PHASE=impl`) | T43 | §4.46 | S | pending |
| T47 | review-implementation synopsis widening: `render_synopsis()` + `ledger_row_fields()` | T44, T45, T46 | §4.47 | S | pending |
| T48 | review-implementation frontier guard: resolve frontier via `gh pr list --state all` (dodge partially-landed misfire) | T43 | §4.48 | S | pending |
| T49 | End-to-end `/review-plan <id>`; capture head SHA before/after; verify plan-panel synopsis + ticket plumbing | T42 | §4.49 | M | pending |
| T50 | End-to-end `/review-implementation <id>`; capture top-slice head SHA before/after; verify rolled-up synopsis + `--state all` frontier | T47, T48 | §4.50 | M | pending |
| T51 | **Verify Slice 4** — both axis-enumerated synopses; both head SHAs unchanged; ticket to fidelity/completeness lenses only; impl frontier via `--state all` | T49, T50 | §4.51 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Per-phase skills upgraded. Slice 5 composes them in the whole-stack /review and authors the regression fixture; fresh context loads the /review binding table rather than the per-phase wiring transcripts.

## Session 5 — Upgrade whole-stack /review + author regression fixture

**Load:** structure.md §Slice 5, structure.md §Contracts, plan.md §Slice 5, impl-log.md §Slice 1–4 (notes only: panel constants, helper signatures, proven per-phase wiring)
**Estimated context:** ~26% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T52 | Read `.claude/skills/review/SKILL.md` in full; map binding table + Step 3b per-phase fan-out / sub-section assembly | T51 | §5.52 | S | pending |
| T53 | Bind upgraded per-phase panels in `review/SKILL.md`; render per-phase synopsis sub-sections via `render_synopsis()`; one ledger row per phase via `ledger_row_fields()` | T52 | §5.53 | M | pending |
| T54 | Create `evals/fixtures/descoping-design.md` — independently-authored design quietly narrowing a chosen AC (NOT a RUS-86/#347 reconstruction); document descoped AC inline | T51 | §5.54 | M | pending |
| T55 | Add provenance-table row for `descoping-design.md` to `evals/fixtures/README.md` | T54 | §5.55 | S | pending |
| T56 | Re-run upgraded `/review-design` over `descoping-design.md`; assert NON-clean pass (descoping finding AND decision-readiness blocking item both surfaced) | T53, T54 | §5.56 | M | pending |
| T57 | End-to-end `/review <id>` over a ticket with a frontier PR; capture frontier head SHA before/after | T53 | §5.57 | M | pending |
| T58 | **Verify Slice 5** — one rolled-up per-phase-sectioned synopsis; one ledger row per phase; head SHA unchanged; fixture non-clean pass; `run_tests.py` green | T55, T56, T57 | §5.58 | S | pending |
