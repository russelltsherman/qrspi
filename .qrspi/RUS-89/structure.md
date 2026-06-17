# Structure Outline — Phase review-panel commands (/review-*): on-demand node-validity review panels

**Design basis:** design.md @ 2026-06-17T20:40:00Z
**Generated:** 2026-06-17T21:10:00Z
**Status:** draft

## New Types

- `AgreementResult { panelVerdict: "pass"|"fail", humanVerdict: "approved"|"changes_requested"|"commented"|"pending"|null, agreement: "agree"|"disagree"|"pending" }` — output of the agreement reducer; `pending` when the human `reviewDecision` is absent (ref: design.md Decision 4, AC2).
- `ReviewRecord { phase: str, rounds: [{lens, pass, findingsCount}], terminalAction: str, agreement: AgreementResult, mode: "on-demand-review" }` — the agreement-extended ledger record; superset of `CriticStepMetrics` plus the `agreement` block and `mode` discriminator (ref: design.md Decision 3, AC2).

## Modified Types

- (none — the lens `CRITIC_VERDICT_SCHEMA` `{pass, findings}` is reused unchanged and deliberately NOT extended; open-question answers are carried out-of-band per Decision 5.)

## Contracts

- `qrspi_review_agreement.compute(panel_pass: bool, human_decision: str | None) -> AgreementResult` — pure reducer mapping a panel `{pass}` and a human `reviewDecision` string (or None) to `{panelVerdict, humanVerdict, agreement}`, with `None → agreement:"pending"` (never a false disagreement). Pure, stdlib-only, never raises (ref: design.md Decision 4, Delta).
- `qrspi_review_record.build_record(phase: str, rounds: list, terminal_action: str, agreement: AgreementResult) -> ReviewRecord` — builds the agreement-extended ledger record by reusing the `qrspi_critic_metrics.build_record` shape and adding the `agreement` block + `mode:"on-demand-review"` (ref: design.md Decision 3, Delta).
- `qrspi_comment_reply.py --ticket <id> --pr <n> --reply-mode toplevel [--comment-id <id>] --body-file <path>` — toplevel mode no longer requires `--comment-id` (relaxed to optional so a synopsis with no parent comment can post); reply mode still requires it. **`--ticket` and `--reply-mode` remain required in both modes** (the relaxation is `--comment-id`-only; corrected at plan review against `qrspi_comment_reply.py:202-210`) (ref: design.md Delta, Risk Register row 3).
- `next_action` CLI — REUSED UNCHANGED and **already present** at `scripts/qrspi_critic_loop.py:118-159` (RUS-55 Slice 3; no shim to add). Contract (corrected at plan review): `printf '%s' '<verdicts-json-array>' | python3 scripts/qrspi_critic_loop.py --round R --max-rounds M` → prints JSON `{action, residual_findings}` with `action ∈ {"converged","revise","cap_reached"}`. The SKILL loop reads stdin verdicts → CLI → branches `converged`/`cap_reached` (terminate) vs `revise` (re-spawn producer). Not authored here; listed as the cross-slice loop contract (ref: design.md Decision 1, Delta).
- `qrspi_critic_synthesize.synthesize(verdicts) -> {pass, findings}` — REUSED UNCHANGED for per-round multi-lens reduction (ref: design.md Decision 1).
- Skill scratch-loop contract (prose, per command): `resolve (qrspi_resolve.py) → derive PR number (gh pr list --head <id>/<phase> --json number) → copy artifact to /tmp/phase-stage/<id>/review/<artifact>.md → for round in 0..2: spawn lens(es) against scratch copy + codebase → synthesize → next_action CLI (stdin verdicts → `{action}`) → (`revise` ⇒ re-spawn phase producer to rewrite scratch copy and continue | `converged`/`cap_reached` ⇒ terminate) → [design only] post-loop open-question pass (phase producer) → build ReviewRecord → append via qrspi_metrics_append.py → post synopsis via qrspi_comment_reply.py`. No `gt submit`/`gt modify`/`gh`-write to the branch (ref: design.md AC1, Decision 1, Decision 2).

## Slice 1: Pure review seams + toplevel comment relaxation

**Goal:** Land the tested pure-Python foundation the skills depend on — the agreement reducer, the record builder, and the `--comment-id`-optional toplevel comment path — each verifiable in isolation before any skill wiring exists.
**Files touched:**

- ✨ `scripts/qrspi_review_agreement.py` — `compute(panel_pass, human_decision)` agreement reducer with the `None→"pending"` category.
- ✨ `scripts/qrspi_review_agreement_test.py` — `check(label, got, want)` cases: pass+approved⇒agree, fail+changes_requested⇒agree, pass+changes_requested⇒disagree, fail+approved⇒disagree, any+None⇒pending, commented decision handling.
- ✨ `scripts/qrspi_review_record.py` — `build_record(...)` composing `qrspi_critic_metrics.build_record` shape + agreement block + `mode:"on-demand-review"`.
- ✨ `scripts/qrspi_review_record_test.py` — asserts record shape, the embedded agreement block, and the `mode` discriminator.
- ⚠️ `scripts/qrspi_comment_reply.py` — relax `--comment-id` to optional in toplevel mode; keep it required in reply mode.
- ⚠️ `scripts/qrspi_comment_reply_test.py` — add a toplevel-without-comment-id case; confirm reply mode still rejects a missing id.
**Verification:**
- [ ] `python3 scripts/run_tests.py review` passes (both new test files green).
- [ ] `python3 scripts/run_tests.py comment_reply` passes (relaxation + existing cases green).
- [ ] `python3 scripts/qrspi_review_agreement.py` smoke: pass+None prints `agreement:"pending"`.
**Context cost:** S
**Depends on:** none

## Slice 2: /review-design end-to-end (AC1 + AC2)

**Goal:** A working `/review-design <id>` that runs the scratch loop on `design.md` using the existing read-only design lens, re-spawns `qrspi-design` as scratch-copy reviser on `revise`, runs the post-loop open-question pass, appends an agreement-extended ledger row, and posts an advisory synopsis to the design PR — with the PR branch head SHA unchanged.
**Files touched:**

- ✨ `.claude/skills/review-design/SKILL.md` — authored via skill-creator; parses `$ARGUMENTS` for ticket id, runs the scratch-loop contract (resolve → derive `<id>/design` PR number → scratch copy → spawn `qrspi-design-critic-design-review` lens / `synthesize` / `next_action` loop → re-spawn `qrspi-design` reviser on revise → post-loop open-question pass via `qrspi-design` → build/append `ReviewRecord` → post synopsis).
**Verification:**
- [ ] skill-creator eval loop passes for the new skill (triggering + steps).
- [ ] Manual e2e on a real `<id>/design` PR: synopsis comment (verdict + findings + open-question answers) posts; ledger gains a `mode:"on-demand-review"` row; with no human review yet the row shows `agreement:"pending"`.
- [ ] PR head SHA is identical before and after the run (no branch mutation/push — Risk Register row 1).
- [ ] Re-run after a human review records a fresh row whose `agreement` resolves against the present `reviewDecision`.
**Context cost:** L
**Depends on:** Slice 1

## Slice 3: /review-plan + plan node-validity lens (AC3)

**Goal:** A `/review-plan <id>` command plus a new plan lens that judges whether plan steps are technically sound against the real code, posting a synopsis to the plan PR.
**Files touched:**

- ✨ `.claude/agents/qrspi-plan-critic-plan-review.md` — new lens agent (tools Read/Grep) mirroring the design-review lens contract: named PATH inputs (`PLAN_PATH`, `RESEARCH_PATH`, `CODEBASE_PATH`, optional upstream paths), emits `{pass, findings}` validated as `CRITIC_VERDICT_SCHEMA`, reads real source, writes no files.
- ✨ `.claude/skills/review-plan/SKILL.md` — authored via skill-creator; same scratch-loop contract pointed at `plan.md`, `<id>/plan` PR, lens = `qrspi-plan-critic-plan-review`, reviser = `qrspi-plan`. Open-question resolution NOT included (OQ1 deferred).
**Verification:**
- [ ] skill-creator eval loop passes for the new skill.
- [ ] Manual e2e on a real `<id>/plan` PR: synopsis posts; ledger row with `mode:"on-demand-review"`, phase `plan`.
- [ ] PR head SHA unchanged after the run.
**Context cost:** M
**Depends on:** Slice 1, Slice 2

## Slice 4: /review-implementation + impl node-validity lens (AC4)

**Goal:** A `/review-implementation <id>` command plus a new implementation lens that judges correctness/security/efficiency/performance against the real code + tests, posting one rolled-up synopsis to the top slice PR.
**Files touched:**

- ✨ `.claude/agents/qrspi-impl-critic-impl-review.md` — new lens agent (tools Read/Grep) mirroring the lens contract; correctness/security/efficiency/performance focus over real code + tests; emits `{pass, findings}`; writes no files.
- ✨ `.claude/skills/review-implementation/SKILL.md` — authored via skill-creator; scratch-loop contract against the slice artifacts, top slice PR (derive via `gh pr list --head <id>/slice-N`), lens = `qrspi-impl-critic-impl-review`, reviser = `qrspi-implement`; one rolled-up synopsis comment. Open-question resolution NOT included (OQ1 deferred).
**Verification:**
- [ ] skill-creator eval loop passes for the new skill.
- [ ] Manual e2e on a real implementation stack: a single rolled-up synopsis posts to the top slice PR; ledger row with `mode:"on-demand-review"`, phase `implementation`.
- [ ] PR head SHA(s) unchanged after the run.
**Context cost:** M
**Depends on:** Slice 1, Slice 2

## Slice 5: /review comprehensive + docs (AC5 + AC7)

**Goal:** A whole-stack coherence `/review <id>` that reuses the per-phase lenses, posts one synopsis to the frontier PR (checking `gh pr list --state all` to dodge the partially-landed misfire), and documents the whole `/review-*` family in CLAUDE.md.
**Files touched:**

- ✨ `.claude/skills/review/SKILL.md` — authored via skill-creator; resolves the frontier phase (using `gh pr list --state all`, ref: Q11), runs the per-phase lenses, aggregates into a whole-stack synopsis (aggregation shape per OQ3 resolution at plan time), posts to the frontier PR; appends a ledger row per reviewed phase.
- ⚠️ `.claude/CLAUDE.md` (worktree copy) — document the `/review-*` family under "Available skills".
- ⚠️ `CLAUDE.md` (repo root) — same documentation (kept in sync).
**Verification:**
- [ ] skill-creator eval loop passes for the new skill.
- [ ] Manual e2e on a multi-phase stack: one synopsis posts to the frontier PR; no misfire on a partially-landed stack.
- [ ] PR head SHA unchanged after the run.
- [ ] CLAUDE.md documents `/review-design`, `/review-plan`, `/review-implementation`, `/review`.
**Context cost:** M
**Depends on:** Slice 1, Slice 2, Slice 3, Slice 4

---

## Unverified Assumptions

- **OQ1 (open):** Whether `/review-plan` and `/review-implementation` also resolve their phases' open questions. Slices 3/4 currently OMIT open-question resolution (design-phase-only in v1). If the plan phase decides to include it, the scratch-loop contract for those slices gains a post-loop producer pass. Needs a decision before planning those slices' steps.
- **OQ3 (resolved at plan time, flagged for ratification):** Slice 5 posts **per-phase sub-synopses under one comment** (no cross-phase verdict reducer invented). This is a product-facing default surfaced for reviewer ratification — if a single whole-stack verdict is wanted, Slice 5's aggregation changes (plan-time OQ3 resolution).
- **OQ5 (open, leaning omit):** `lensModel` may be inert (no evidence the harness honors `agent().model`). The slices assume `lensModel` is NOT wired in v1; if it must be, the lens-spawn steps change. Mapped to "omit-until-verified".
- ~~**`next_action` CLI shim**~~ **RESOLVED at plan review:** the CLI already exists (`scripts/qrspi_critic_loop.py:118-159`, RUS-55 Slice 3) — **no shim to add**. Verified contract: stdin JSON verdict array + `--round`/`--max-rounds` → JSON `{action, residual_findings}`, `action ∈ {converged, revise, cap_reached}`. The earlier "research saw it only as a pure seam / Slice 2 may add a shim emitting converge|revise|stop" was wrong on both existence and action tokens; plan Steps 10/12/13 corrected.
- **Frontier/PR-number derivation in skills:** The design specifies deriving PR numbers via `gh pr list --head <id>/<phase>` and the frontier via `--state all`, but the resolve envelope has no PR-number field (ref: Q1). This relies on the gh-derivation working from inside SKILL prose with the bot's auth; assumed sound from research but verified only at e2e.
