# Work Tree — qrspi critics 1/5: edge-critic loop primitive wired into runPhase

**Plan basis:** plan.md @ 2026-06-12T00:00:00Z
**Generated:** 2026-06-12T00:00:00Z
**Status:** draft
**Total sessions:** 3
**Critical path:** T1 → T2 → T3 → T9 (Verify S1) → T11 → T13 (Verify S2) → T15 → T16 → T17 → T19 → T22 (Verify S3)

> Each plan slice maps to one session — the slices are already vertical and
> independently verifiable, and the plan mandates a fresh `/clear` between
> implementation slices. Critical path runs the build → test → checkpoint spine
> of each slice; intra-session test-authoring tasks (T4–T7, T12) fan out from the
> core-logic tasks and are not on the longest dependency chain.

## Session 1 — Slice 1: Pure critic-loop decision module

**Load:** structure.md §Contracts, structure.md §Slice 1 tests, plan.md §Slice 1,
        design.md §Delta + Decision 2 (Pattern 7)
**Estimated context:** ~18% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create `scripts/qrspi_critic_loop.py` — pure stdlib-only decision module, no agent/IO coupling, with module docstring | — | §1.1 | S | pending |
| T2 | Implement `parse_critic_verdict(text)` — fail-closed JSON parser coercing to `{pass, findings}`, never raises | T1 | §1.2 | M | pending |
| T3 | Implement `next_action(verdicts, round, max_rounds)` — returns converged/revise/cap_reached + residual_findings | T1 | §1.3 | M | pending |
| T4 | Create `scripts/qrspi_critic_loop_test.py` — stdlib assert-based sibling, no runner | T1 | §1.4 | S | pending |
| T5 | Add assert: passing verdict at round 0 ⇒ `converged`, no revise (AC4) | T3, T4 | §1.5 | S | pending |
| T6 | Add assert: fail→revise→pass sequence ⇒ `revise` then `converged` (AC2) | T3, T4 | §1.6 | S | pending |
| T7 | Add assert: non-passing verdict at `round == max_rounds-1` ⇒ `cap_reached` with residual_findings (AC2, AC4) | T3, T4 | §1.7 | S | pending |
| T8 | Add assert: malformed/empty/garbage into `parse_critic_verdict` ⇒ `{pass: False, ...}`, never raises (Q11) | T2, T4 | §1.8 | S | pending |
| T9 | **Verify Slice 1** — run `python3 scripts/qrspi_critic_loop_test.py`, all asserts pass (steps 9-10 checkpoint) | T5, T6, T7, T8 | §1.9–1.10 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete and verified. Fresh context for Slice 2 — moves
from the pure python module to authoring agent/skill markdown, a distinct
artifact set with no shared in-context state beyond the verdict schema shape.

## Session 2 — Slice 2: Critic agent + slash-command wrapper

**Load:** structure.md §Slice 2, plan.md §Slice 2, design.md §Delta + Decision 2 + AC3 (Q5),
        qrspi_critic_loop.py §verdict-shape (signature only, from S1 notes)
**Estimated context:** ~22% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T10 | Create `.claude/agents/qrspi-critic.md` — frontmatter `name: qrspi-critic`, `tools: Read` (no Write unless staged-verdict path needed) | T9 | §2.11 | S | pending |
| T11 | Author edge-critic system prompt body — consumes `UPSTREAM_PATH`+`ARTIFACT_PATH`, judges the EDGE, emits `{pass, findings}` per `CRITIC_VERDICT_SCHEMA` (AC3) | T10 | §2.12 | M | pending |
| T12 | Create `.claude/skills/qrspi-critic/SKILL.md` wrapper via skill-creator (project convention) | T11 | §2.13 | M | pending |
| T13a | Prepare sample fixture pair — faithful produced artifact + degraded artifact dropping one upstream requirement | T11 | §2.14 | S | pending |
| T13b | Direct critic invocation on faithful artifact ⇒ `pass: true` | T11, T13a | §2.15 | S | pending |
| T13c | Direct critic invocation on degraded artifact ⇒ `pass: false` naming dropped requirement | T11, T13a | §2.16 | S | pending |
| T13 | **Verify Slice 2** — frontmatter parse + invocations from T13b/T13c + skill-creator eval loop (step 17 checkpoint) | T12, T13b, T13c | §2.17 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 2 complete and verified. Fresh context for Slice 3 — the
orchestrator-wiring slice opens a large file (`qrspi-batch.js`) and a body-path
decision; clearing avoids carrying the agent/skill authoring context into the
JS-heavy edit work.

## Session 3 — Slice 3: Wire `runCriticLoop` into `runPhase`, enable for design/plan

**Load:** structure.md §Modified Types + §Contracts + §Slice 3 + §Unverified Assumptions,
        plan.md §Slice 3 + §Rollback Notes, design.md Decisions 1/3/4 (AC1–AC4, Q6/Q9/Q14),
        impl-log.md §Slice 1 + §Slice 2 (notes only)
**Estimated context:** ~34% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T14 | Read schemas / `runPhase` / `doDesign` / `doPlan` in `qrspi-batch.js` — resolve Unverified Assumptions (signature, reviser identity, finalize seam) | T13 | §3.18 | S | pending |
| T15 | **Decision point:** choose body path A (`scripts/qrspi_critic_body.py`) vs B (fold into existing finalize seam); record choice — governs T20–T21 | T14 | §3.19 | S | pending |
| T16 | Add `CRITIC_VERDICT_SCHEMA` to the schemas section of `qrspi-batch.js` (Q6) | T15 | §3.20 | S | pending |
| T17 | Add `runCriticLoop(name, id, criticConfig, ...ctx) -> {ok, residualFindings}` — single critic per round, delegates decision to `qrspi_critic_loop.py` (AC1–AC4) | T16 | §3.21 | L | pending |
| T18 | Add optional trailing `criticConfig` param to `runPhase`; insert guarded loop between produce-success and persist gate; absent ⇒ verbatim current behavior (AC1, Q9) | T17 | §3.22 | M | pending |
| T19 | In `doDesign`, pass `criticConfig {upstream: 'research.md', maxRounds: N}` to the design `runPhase` call | T18 | §3.23 | S | pending |
| T20a | In `doPlan`, pass `criticConfig {upstream: 'structure.md', maxRounds: N}` to the plan `runPhase` call | T18 | §3.24 | S | pending |
| T20b | Thread `residualFindings` from `runCriticLoop` → `runPhase` → `doDesign`/`doPlan` into finalize commit body via chosen path (T15) | T18, T19, T20a | §3.25 | M | pending |
| T20c | Surface critic rounds / per-round pass-fail / cap-reached via `log(...)`; fold critic summary into `res.summary` (Q14) | T18 | §3.26 | S | pending |
| T20 | (Path A only) Create `scripts/qrspi_critic_body.py` mirroring `qrspi_pr_body.py` — staged-file splice into finalize commit (skip if path B) | T15, T20b | §3.27 | M | pending |
| T21a | (Path A only) Create `scripts/qrspi_critic_body_test.py` — stdlib assert sibling for splice/staging (skip if path B) | T20 | §3.28 | S | pending |
| T21 | (Path A only) Run `python3 scripts/qrspi_critic_body_test.py` ⇒ exits 0 (skip if path B) | T21a | §3.29 | S | pending |
| T22 | **Verify Slice 3** — diff confirms 6-arg call sites unchanged; body test (if path A); manual e2e design run (round 0 critique, pass⇒1 call, degraded⇒revise, cap⇒success+PR body); persist still gates (step 30 checkpoint) | T20b, T20c, T21 | §3.30 | M | pending |

--- SESSION BOUNDARY ---
**Reason:** Final slice. Feature complete — no further session required; the
stack is ready for the implementation PRs to be assembled and submitted.
