# PR: RUS-89 On-demand /review-* node-validity review panels

**Ticket:** RUS-89
**Design:** design.md @ 2026-06-17T20:40:00Z
**Structure:** structure.md @ 2026-06-17T21:10:00Z

## Summary

Adds a net-new, human-invoked `/review-*` skill family (`/review-design`, `/review-plan`, `/review-implementation`, `/review`) that runs the node-validity critic lenses on a ticket's design/plan/implementation against the real codebase and posts an advisory synopsis comment to the corresponding PR. The path is **advisory and propose-only**: it copies the artifact to a `/tmp` scratch path, runs a ≤3-round scratch loop (lens emits `{pass,findings}` → `synthesize` → tested `next_action` → re-spawn the phase *producer* as scratch reviser), and **never** invokes `gt submit`/`gt modify`/`gh`-write on the branch (PR head SHA is unchanged after a run). Each run appends an agreement-extended row (`mode:"on-demand-review"`, panel-verdict-vs-human `reviewDecision`) to the RUS-78 critic-metrics JSONL via the existing append mechanism. The on-demand engine reuses only the lens *agents* and pure `synthesize`/`next_action`/append seams — it touches **no** batch JS (`runCriticPanelLoop`) and leaves all critic config OFF by default, so batch behavior is byte-for-byte unchanged. **Reviewer focus:** the no-push invariant (Risk 1), the AC6 batch-isolation guarantee, and that the four SKILLs and two new lens agents could not be exercised end-to-end in the sandbox (see Testing Summary / Open Items).

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: `/review-design` end-to-end (scratch loop + open-question pass + synopsis to design PR) | `.claude/skills/review-design/SKILL.md` (reuses lens `qrspi-design-critic-design-review`, reviser `qrspi-design`) | Contract-chain smoke (impl-log S2); e2e deferred — sandbox |
| AC2: agreement instrumentation (`mode:"on-demand-review"`, `pending` on no human verdict) | `scripts/qrspi_review_agreement.py:compute`, `scripts/qrspi_review_record.py:build_record` | `scripts/qrspi_review_agreement_test.py`, `scripts/qrspi_review_record_test.py` |
| AC3: `/review-plan` + plan node-validity lens | `.claude/agents/qrspi-plan-critic-plan-review.md`, `.claude/skills/review-plan/SKILL.md` | Contract-chain smoke (impl-log S2 notes); e2e deferred — sandbox |
| AC4: `/review-implementation` + impl lens (one rolled-up synopsis to top slice PR) | `.claude/agents/qrspi-impl-critic-impl-review.md`, `.claude/skills/review-implementation/SKILL.md` | Contract-chain smoke (impl-log S4); e2e deferred — sandbox |
| AC5: `/review` comprehensive (frontier via `gh pr list --state all`, per-phase sub-synopses) | `.claude/skills/review/SKILL.md` | Contract-chain smoke (impl-log S5); e2e deferred — sandbox |
| AC6: separate path, no batch regression (reuse lens agents + scripts only; config OFF) | No batch JS touched; `scripts/qrspi_comment_reply.py` relaxation only | `python3 scripts/run_tests.py` → 41 passed (no regressions) |
| AC7: tests + docs | new `_test.py` siblings green; `.claude/CLAUDE.md` documents the family | `scripts/qrspi_review_agreement_test.py`, `scripts/qrspi_review_record_test.py`, `scripts/qrspi_comment_reply_test.py` |
| (toplevel comment relaxation — AC1/AC2/AC3/AC4/AC5 enabler) | `scripts/qrspi_comment_reply.py` (`--comment-id` optional in toplevel; required+fail-closed in inline) | `scripts/qrspi_comment_reply_test.py` (toplevel-without-id + inline-still-rejects cases) |

## Changes by Slice

### Slice 1: Pure review seams + toplevel comment relaxation

| File | Change | Lines |
|------|--------|-------|
| `scripts/qrspi_review_agreement.py` | ✨ new | +118 |
| `scripts/qrspi_review_agreement_test.py` | ✨ new | +87 |
| `scripts/qrspi_review_record.py` | ✨ new | +72 |
| `scripts/qrspi_review_record_test.py` | ✨ new | +73 |
| `scripts/qrspi_comment_reply.py` | ⚠️ modified | +12, -2 |
| `scripts/qrspi_comment_reply_test.py` | ⚠️ modified | +41 |

### Slice 2: /review-design end-to-end (AC1 + AC2)

| File | Change | Lines |
|------|--------|-------|
| `.claude/skills/review-design/SKILL.md` | ✨ new | +227 |

### Slice 3: /review-plan + plan node-validity lens (AC3)

| File | Change | Lines |
|------|--------|-------|
| `.claude/agents/qrspi-plan-critic-plan-review.md` | ✨ new | +73 |
| `.claude/skills/review-plan/SKILL.md` | ✨ new | +219 |

### Slice 4: /review-implementation + impl node-validity lens (AC4)

| File | Change | Lines |
|------|--------|-------|
| `.claude/agents/qrspi-impl-critic-impl-review.md` | ✨ new | +74 |
| `.claude/skills/review-implementation/SKILL.md` | ✨ new | +223 |

### Slice 5: /review comprehensive + docs (AC5 + AC7)

| File | Change | Lines |
|------|--------|-------|
| `.claude/skills/review/SKILL.md` | ✨ new | +230 |
| `.claude/CLAUDE.md` | ⚠️ modified | +4 |

### Phase artifacts (committed on the upstream design/plan PRs, carried in `main...HEAD`)

| File | Change | Lines |
|------|--------|-------|
| `.qrspi/RUS-89/questions.md` | ✨ new | +53 |
| `.qrspi/RUS-89/research.md` | ✨ new | +406 |
| `.qrspi/RUS-89/design.md` | ✨ new | +124 |
| `.qrspi/RUS-89/structure.md` | ✨ new | +109 |
| `.qrspi/RUS-89/plan.md` | ✨ new | +159 |
| `.qrspi/RUS-89/worktree.md` | ✨ new | +108 |
| `.qrspi/RUS-89/impl-log.md` | ✨ new (accreted across slices) | +135 |

## Testing Summary

- [x] Slice 1: pure reducers — `python3 scripts/run_tests.py review` — 2 passed, 0 failed
- [x] Slice 1: toplevel relaxation — `python3 scripts/run_tests.py comment_reply` — 1 passed, 0 failed
- [x] Full suite (no regression — AC6) — `python3 scripts/run_tests.py` — 41 passed, 0 failed
- [x] Contract-chain smoke (Slices 2/4/5): `qrspi_critic_synthesize.py` → `{pass,findings}`; `qrspi_critic_loop.py --round/--max-rounds` → `converged`/`revise`/`cap_reached`; `qrspi_review_record.build_record(...)` → `mode:"on-demand-review"` row with `agreement:"pending"` when no human verdict; `build_record(..., terminal_action="revise", ...)` raises `ValueError` (terminal-only, fail-closed)
- [ ] Manual e2e (synopsis posts to live PR; ledger gains `mode:"on-demand-review"` row; PR head SHA unchanged; re-run resolves agreement against a present `reviewDecision`) — **DEFERRED to a real-repo run**; not runnable from the isolated worktree (needs live PR + network)
- [ ] skill-creator triggering eval for the four SKILLs — **NOT trustworthy in this sandbox** (returns bogus uniform results); SKILLs were instead validated via direct skill-creator description-quality review (frontmatter, trigger phrases, disambiguation)

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| `CRITIC_VERDICT_SCHEMA` `{pass, findings}` | reused unchanged | reused unchanged | clean — open-question answers carried out-of-band (Decision 5) |
| `next_action` CLI shim (early research framing) | possibly a new shim | no shim — already at `scripts/qrspi_critic_loop.py:118-159` | resolved at plan review; CLI pre-existed (RUS-55), no code added |
| Slice 5 repo-root `CLAUDE.md` (`/workspaces/qrspi/.claude/CLAUDE.md`) | edited in sync with worktree copy | only the **worktree** `.claude/CLAUDE.md` edited | the repo-root copy lives on `main`, outside the worktree's hard scope boundary; reconciles at land (see Open Items) |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| Accidental branch mutation/push during scratch revise | mitigated (design); **e2e head-SHA check deferred** — sandbox | SKILLs never call `gt`/`gh`-write to the branch; remove the SKILL dirs to disable |
| Coupling on-demand path back into `runCriticPanelLoop` (AC6 regression) | mitigated — no batch JS touched; full suite 41/41; config OFF by default | revert the slice commits; batch path is untouched |
| `--comment-id` required even for toplevel blocks synopsis post | mitigated — relaxed to optional in toplevel (tested), still required+fail-closed in inline | revert `scripts/qrspi_comment_reply.py` (+ test) |
| PR number absent from resolve envelope → wrong/no PR | mitigated by design (`gh pr list --head`/`--state all`) | **unverified e2e** — confirm on first real run |
| Codebase-access panels token-heavy (≤3 rounds × lenses) | accepted — human-invoked/advisory; rounds capped at 3 | n/a (cost, not correctness) |
| Agreement ledger conflated with batch-gate rows | mitigated — `mode:"on-demand-review"` discriminator + tested reducer | filter rows by `mode` in analysis |
| Shared critic files also edited by RUS-77/88 family | mitigated — design lens reused read-only; new lenses are net-new files | rebase whoever lands second |

## Open Items

- **Manual e2e is deferred** for every SKILL (AC1–AC5): synopsis posting to a live PR, the `mode:"on-demand-review"` ledger row, the unchanged-PR-head-SHA no-push invariant, and agreement reconciliation against a present `reviewDecision` were **not runnable** from the isolated sandbox worktree (need a live PR + network). These must be exercised on a real-repo run before relying on the commands.
- **skill-creator triggering eval is unreliable in this sandbox** (bogus uniform results); the four SKILLs were validated only via direct description-quality review. Re-validate triggering with a real `claude -p` routing probe in the real repo.
- **Repo-root `CLAUDE.md` doc sync (Slice 5 deviation):** `/workspaces/qrspi/.claude/CLAUDE.md` on `main` does not yet carry the four `/review-*` entries (only the worktree copy was in scope). Confirm the land merge reconciles the two copies, or apply the identical four-entry block to `main` directly.
- **OQ1 (open):** `/review-plan` and `/review-implementation` OMIT the post-loop open-question pass (design-phase-only in v1). Revisit if plan/impl phases should also resolve open questions.
- **OQ3 (resolved at plan time, flagged for ratification):** `/review` posts **per-phase sub-synopses under one comment** (no invented cross-phase verdict reducer). If a single rolled-up whole-stack verdict is wanted, `/review`'s aggregation step changes.
- **OQ5 (open, leaning omit):** `lensModel` may be inert (no evidence the harness honors `agent().model`); not wired in v1.
- **Token-cost dimension deferred (OQ4):** the harness exposes no per-subagent token usage, so `tokensIn`/`tokensOut` are omitted from the agreement record in v1.
