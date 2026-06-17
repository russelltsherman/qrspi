# Work Tree — Phase review-panel commands (/review-*): on-demand node-validity review panels

**Plan basis:** plan.md @ 2026-06-17T21:40:00Z
**Generated:** 2026-06-17T22:00:00Z
**Status:** draft
**Total sessions:** 5
**Critical path:** T1 → T2 → T4 → T7 → T9 (Slice 1) → T12 → T20 → T22 → T23 (Slice 2) → T24 → T25 → T26 → T27 → T29 → T30 (Slice 3) → T31 → T32 → T33 → T35 → T36 (Slice 4) → T37 → T38 → T39 → T40 → T41 → T42 → T44 (Slice 5)

> Sessions follow the plan's slice boundaries one-to-one (one slice per session). Each slice's verify checkpoint is the last task in its session, and downstream slices depend on the prior slice's verify task. The pure-module + relaxation seam (Slice 1) is the foundation the four review skills depend on; the design lens (Slice 2) is the structural template the plan/impl lenses and the comprehensive command reuse.

## Session 1 — Slice 1: Pure review seams + toplevel comment relaxation

**Load:** structure.md §New Types (AgreementResult, ReviewRecord), structure.md §Contracts (qrspi_review_agreement.compute, qrspi_review_record.build_record, qrspi_comment_reply.py), plan.md §Slice 1, design.md §Decision 4 + §Decision 3 + §Q14/Inconsistencies
**Estimated context:** ~20% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create `scripts/qrspi_review_agreement.py` exposing `compute(panel_pass, human_decision) -> AgreementResult` | — | §1 | S | pending |
| T2 | Implement `compute`: map panelVerdict, normalize humanVerdict, derive agreement (commented⇒pending); pure, never raises | T1 | §2 | M | pending |
| T3 | Add `__main__` smoke block printing `compute` result as JSON | T2 | §3 | S | pending |
| T4 | Create `scripts/qrspi_review_record.py` exposing `build_record(...)`, reusing `qrspi_critic_metrics.build_record` base + agreement block + `mode:"on-demand-review"` | — | §4 | M | pending |
| T5 | Create `scripts/qrspi_review_agreement_test.py` (7 agreement cases) | T2 | §5 | S | pending |
| T6 | Create `scripts/qrspi_review_record_test.py` (base keys + embedded agreement + mode) | T4 | §6 | S | pending |
| T7 | Modify `scripts/qrspi_comment_reply.py` — relax `--comment-id` to optional in toplevel mode, still required in reply mode | — | §7 | M | pending |
| T8 | Modify `scripts/qrspi_comment_reply_test.py` — toplevel-without-id pass case + reply-without-id reject case | T7 | §8 | S | pending |
| T9 | **Verify Slice 1** — `run_tests.py review && run_tests.py comment_reply && qrspi_review_agreement.py` smoke | T3, T5, T6, T8 | §9 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete (pure modules + comment relaxation merged). Fresh context for Slice 2, which authors the first review skill on top of these seams.

## Session 2 — Slice 2: /review-design end-to-end (AC1 + AC2)

**Load:** structure.md §Contracts (next_action, scratch-loop contract, qrspi_critic_synthesize, qrspi_metrics_append), structure.md §Unverified Assumptions (next_action CLI shim, OQ5), plan.md §Slice 2, design.md §AC1 + §AC2 + §Decision 1/2/3/5 + §Delta, impl-log.md §Slice 1 (notes only)
**Estimated context:** ~32% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T10 | Read `scripts/qrspi_critic_loop.py` to confirm whether `next_action` already has a usable CLI entrypoint | T9 | §10 | S | pending |
| T11 | Read `qrspi_critic_synthesize.py` + `qrspi_metrics_append.py` to confirm CLI invocation shapes | T9 | §11 | S | pending |
| T12 | Modify `qrspi_critic_loop.py` — add thin CLI `__main__` shim emitting `converge\|revise\|stop` (only if T10 found none) | T10 | §12 | M | pending |
| T13 | Add/extend `qrspi_critic_loop_test.py` CLI-path case (only if T12 added a shim) | T12 | §13 | S | pending |
| T14 | Create `.claude/skills/review-design/SKILL.md` via skill-creator (frontmatter, parse `$ARGUMENTS`) | T9 | §14 | M | pending |
| T15 | Author resolve step: `qrspi_resolve.py <id>` → repoRoot/worktreeDir/existing/design reviewDecision | T14 | §15 | S | pending |
| T16 | Author design-PR-number derivation (`gh pr list --head <id>/design`) | T14 | §16 | S | pending |
| T17 | Author scratch-copy step: design.md → `/tmp/phase-stage/<id>/review/design.md` | T15 | §17 | S | pending |
| T18 | Author scratch loop (rounds 0..2): spawn design-review lens → synthesize → next_action | T11, T12, T17 | §18 | L | pending |
| T19 | Author revise branch: re-spawn `qrspi-design` producer to rewrite scratch copy | T18 | §19 | M | pending |
| T20 | Author post-loop open-question pass: spawn `qrspi-design` (non-strict) to answer Open Questions | T18 | §20 | M | pending |
| T21 | Author record step: `compute` + `build_record(phase="design")` + append via `qrspi_metrics_append.py` | T15, T18 | §21 | M | pending |
| T22 | Author synopsis step: toplevel advisory comment to design PR via `qrspi_comment_reply.py` (no `--comment-id`) | T16, T20, T21 | §22 | M | pending |
| T23 | **Verify Slice 2** — skill-creator eval loop + manual e2e (synopsis posts, ledger row, head SHA unchanged, re-run agreement resolves) | T13, T19, T22 | §23 | M | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 2 complete (/review-design + CLI shim). Slice 3 introduces a new lens agent and skill that reuse Slice 2's design lens as the structural template — fresh context loads only the template references, not the full design-skill authoring history.

## Session 3 — Slice 3: /review-plan + plan node-validity lens (AC3)

**Load:** structure.md §Slice 3 file list + §scratch-loop contract, plan.md §Slice 3 (+ OQ1 resolution), design.md §AC3, `.claude/agents/qrspi-design-critic-design-review.md` (lens template — named PATH inputs, `{pass,findings}` emit, read-only), impl-log.md §Slice 2 (notes only)
**Estimated context:** ~28% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T24 | Read `qrspi-design-critic-design-review.md` as structural template for the plan lens | T23 | §24 | S | pending |
| T25 | Create `.claude/agents/qrspi-plan-critic-plan-review.md` — lens (Read/Grep), PLAN_PATH inputs, `{pass,findings}` per CRITIC_VERDICT_SCHEMA, read-only | T24 | §25 | M | pending |
| T26 | Create `.claude/skills/review-plan/SKILL.md` via skill-creator (frontmatter, parse `$ARGUMENTS`) | T23 | §26 | M | pending |
| T27 | Author scratch-loop pointed at plan.md: resolve → `<id>/plan` PR → scratch copy → rounds 0..2 with plan lens → revise re-spawns `qrspi-plan` | T25, T26 | §27 | L | pending |
| T28 | Omit the open-question-resolution pass (OQ1: design-phase-only) | T27 | §28 | S | pending |
| T29 | Author record + synopsis steps: `compute` vs plan PR, `build_record(phase="plan")`, append, toplevel synopsis to plan PR | T27 | §29 | M | pending |
| T30 | **Verify Slice 3** — skill-creator eval loop + manual e2e (synopsis posts, ledger row phase=plan, head SHA unchanged) | T28, T29 | §30 | M | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 3 complete (/review-plan + plan lens). Slice 4 mirrors the same lens+skill pattern for implementation — fresh context, loading the lens template and impl-specific focus only.

## Session 4 — Slice 4: /review-implementation + impl node-validity lens (AC4)

**Load:** structure.md §Slice 4 file list, plan.md §Slice 4 (+ OQ1 resolution), design.md §AC4, `.claude/agents/qrspi-design-critic-design-review.md` (lens template), impl-log.md §Slice 3 (notes only)
**Estimated context:** ~28% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T31 | Create `.claude/agents/qrspi-impl-critic-impl-review.md` — lens (Read/Grep), slice-artifact inputs, `{pass,findings}` per CRITIC_VERDICT_SCHEMA, read-only; focus correctness/security/efficiency vs code+tests | T30 | §31 | M | pending |
| T32 | Create `.claude/skills/review-implementation/SKILL.md` via skill-creator (frontmatter, parse `$ARGUMENTS`) | T30 | §32 | M | pending |
| T33 | Author scratch-loop against slice artifacts: resolve → top-slice PR (`<id>/slice-N`, N=highest) → scratch copy → rounds 0..2 with impl lens → revise re-spawns `qrspi-implement` | T31, T32 | §33 | L | pending |
| T34 | Omit the open-question-resolution pass (OQ1: design-phase-only) | T33 | §34 | S | pending |
| T35 | Author record + single rolled-up synopsis: `compute` vs top-slice PR, `build_record(phase="implementation")`, append, ONE toplevel synopsis to top slice PR | T33 | §35 | M | pending |
| T36 | **Verify Slice 4** — skill-creator eval loop + manual e2e (single rolled-up synopsis, ledger row phase=implementation, head SHA(s) unchanged) | T34, T35 | §36 | M | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 4 complete (/review-implementation + impl lens). Slice 5 composes all three per-phase lenses into the comprehensive `/review` command plus docs — fresh context loads the three lens names and the frontier/aggregation contract, not each slice's authoring detail.

## Session 5 — Slice 5: /review comprehensive + docs (AC5 + AC7)

**Load:** structure.md §Slice 5 file list, plan.md §Slice 5 (+ OQ3 resolution), design.md §AC5 + §Q11 + §AC7 + §AC2, the three lens agent names (`qrspi-design-critic-design-review`, `qrspi-plan-critic-plan-review`, `qrspi-impl-critic-impl-review`), `.claude/CLAUDE.md` + repo-root `CLAUDE.md` §Available skills, impl-log.md §Slice 4 (notes only)
**Estimated context:** ~30% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T37 | Create `.claude/skills/review/SKILL.md` via skill-creator (frontmatter, parse `$ARGUMENTS`) | T36 | §37 | M | pending |
| T38 | Author frontier-resolution step: determine frontier phase via `gh pr list --state all` (dodge partially-landed misfire) | T37 | §38 | M | pending |
| T39 | Author per-phase pass: run each reviewed phase's lens via the scratch loop (synthesize + next_action); collect `{pass,findings}` | T38 | §39 | L | pending |
| T40 | Author aggregation + synopsis (OQ3: per-phase sub-synopses under one comment) posted to frontier PR | T39 | §40 | M | pending |
| T41 | Author record step: one `mode:"on-demand-review"` ledger row per reviewed phase, agreement vs each PR's reviewDecision | T39 | §41 | M | pending |
| T42 | Modify `.claude/CLAUDE.md` (worktree copy) — document `/review-*` family under "Available skills" | T36 | §42 | S | pending |
| T43 | Modify repo-root `CLAUDE.md` — identical `/review-*` documentation, kept in sync | T42 | §43 | S | pending |
| T44 | **Verify Slice 5** — skill-creator eval loop + manual e2e (one per-phase synopsis to frontier, no partial-land misfire, head SHA unchanged, both CLAUDE.md copies documented) | T40, T41, T43 | §44 | M | pending |

--- SESSION BOUNDARY ---
**Reason:** All slices complete. Next session is the PR-summary phase (out of scope for the work tree).
