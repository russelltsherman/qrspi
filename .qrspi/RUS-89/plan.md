# Implementation Plan — Phase review-panel commands (/review-*): on-demand node-validity review panels

**Structure basis:** structure.md @ 2026-06-17T21:10:00Z
**Generated:** 2026-06-17T21:40:00Z
**Revised:** 2026-06-17 (plan review — corrected the `next_action` CLI contract against the real script, fixed the `qrspi_comment_reply.py` invocation to carry all required args, reconciled the `build_record` signature, hardened the skill-eval gate for this sandbox, and flagged OQ3 for human ratification)
**Status:** draft
**Total steps:** 44

> **Plan-time open-question resolutions** (the structure flagged these as open):
> - **OQ1:** `/review-plan` and `/review-implementation` do **NOT** resolve open questions in v1 (design-phase-only, per Decision 5 + Out of Scope). Slices 3/4 omit the post-loop producer pass.
> - **OQ3:** `/review` posts **per-phase sub-synopses under one comment** (one toplevel comment whose body concatenates a per-phase section). Simplest faithful reading of "one synopsis to the frontier PR" without inventing a cross-phase verdict reducer. **This is a product-facing default flagged for reviewer ratification** — revisit Slice 5's aggregation if the reviewer wants a single rolled-up whole-stack verdict instead.
> - **OQ5:** `lensModel` is **omitted** in v1 (omit-until-verified). Lens spawns pass named PATH inputs only; no `model` override.
> - **`next_action` CLI (ALREADY EXISTS — corrected at plan review):** `scripts/qrspi_critic_loop.py` already exposes the CLI (RUS-55 Slice 3, `qrspi_critic_loop.py:118-159`) — verified against the real file. It reads a JSON verdict **ARRAY from stdin** with `--round R --max-rounds M` and prints JSON `{action, residual_findings}` where `action ∈ {"converged","revise","cap_reached"}` (**not** the plain tokens `converge|revise|stop` the draft assumed). **No shim is added** — Slice 2 invokes it as-is: `printf '%s' '<verdicts-json>' | python3 scripts/qrspi_critic_loop.py --round R --max-rounds M`. The SKILL loop maps `converged`/`cap_reached` → terminate (post synopsis), `revise` → re-spawn the phase producer against the scratch copy and continue.

> **Verification-gate note (corrected at plan review):** every slice below lists "skill-creator eval loop passes" as a checkpoint. In THIS sandbox the skill-creator `run_eval`/`run_loop` triggering harness returns bogus uniform results (known limitation), so it is **not** a trustworthy gate here. For each new skill, validate triggering with direct `claude -p` routing probes in the real repo (does `/review-design <id>` etc. route to the intended skill) and validate behavior with the manual e2e steps. Treat the eval-loop bullets as "author via skill-creator + probe", not "trust the eval score".

## Slice 1: Pure review seams + toplevel comment relaxation

### Setup

1. ✨ Create `scripts/qrspi_review_agreement.py` — module exposing `compute(panel_pass: bool, human_decision: str | None) -> dict` per Contract `qrspi_review_agreement.compute`. Returns `{panelVerdict, humanVerdict, agreement}` matching the `AgreementResult` type (ref: structure New Types, Contracts; design Decision 4).

### Core Logic

2. ✨ In `scripts/qrspi_review_agreement.py`, implement `compute`: map `panel_pass` → `panelVerdict` (`True→"pass"`, `False→"fail"`); normalize `human_decision` → `humanVerdict` (`"APPROVED"→"approved"`, `"CHANGES_REQUESTED"→"changes_requested"`, `"COMMENTED"→"commented"`, `None→null`, case-insensitive); derive `agreement`: `None→"pending"`; else `"agree"` when (pass+approved) or (fail+changes_requested), `"disagree"` otherwise; `commented` is neither approve nor reject ⇒ treat as `"disagree"` for a `pass` panel and `"agree"` for a `fail` panel? — **no:** `commented` is not a verdict, so map `commented → agreement:"pending"` (no decisive human verdict). Pure, stdlib-only, never raises (ref: design Decision 4, Delta).
3. ✨ In `scripts/qrspi_review_agreement.py`, add a `__main__` smoke block: read `panel_pass` (arg or default) and print the `compute` result as JSON so `python3 scripts/qrspi_review_agreement.py` runs the pass+None smoke (ref: structure Slice 1 verification bullet 3).
4. ✨ Create `scripts/qrspi_review_record.py` — module exposing `build_record(phase: str, rounds: list, terminal_action: str, agreement: dict) -> dict` per Contract `qrspi_review_record.build_record`. Import and reuse `qrspi_critic_metrics.build_record` for the base shape, then add the `agreement` block and `mode: "on-demand-review"` (ref: structure New Types `ReviewRecord`, design Decision 3).
   - **Signature reconciliation (corrected at plan review):** the underlying builder is `qrspi_critic_metrics.build_record(verdicts, terminalAction, usage=None, phase=None)` (`qrspi_critic_metrics.py:54`) — it takes per-lens **verdicts** and *derives* the `rounds` shape itself; it does **not** accept a pre-built `rounds` list. So `qrspi_review_record.build_record` must pass the round **verdicts** (plus `terminalAction` and `phase`) through to it, then wrap the returned record with the `agreement` block + `mode`. The reducer's `rounds: list` param is the verdict list it forwards.

### Tests

5. ✨ Create `scripts/qrspi_review_agreement_test.py` — `check(label, got, want)` cases: pass+approved⇒agree, fail+changes_requested⇒agree, pass+changes_requested⇒disagree, fail+approved⇒disagree, pass+None⇒pending, fail+None⇒pending, commented⇒pending (ref: structure Slice 1 file list).
6. ✨ Create `scripts/qrspi_review_record_test.py` — assert the record carries the base `{phase, rounds, terminalAction}` keys, the embedded `agreement` block (verbatim from the passed dict), and `mode == "on-demand-review"` (ref: structure Slice 1 file list).

### Toplevel comment relaxation

7. ⚠️ Modify `scripts/qrspi_comment_reply.py` — relax `--comment-id` to optional in toplevel mode; keep it required in reply mode.
   - **Current:** the parser requires **all** of `--ticket`, `--pr`, `--comment-id`, `--reply-mode`, `--body-file` unconditionally (`qrspi_comment_reply.py:202-210`); `--comment-id` is required even for toplevel (`gh pr comment <pr> --body-file -`) (ref: design Q14, Inconsistencies).
   - **After:** toplevel mode accepts a missing `--comment-id`; reply mode still errors when `--comment-id` is absent (ref: structure Contracts `qrspi_comment_reply.py`, Risk Register row 3).
   - **Scope note (corrected at plan review):** this relaxes **only** `--comment-id`. `--ticket` and `--reply-mode` stay **required**, so every synopsis-post call below MUST pass `--ticket <id> --reply-mode toplevel` (the draft invocations that omitted them were wrong). Also drop the pre-dispatch `error_envelope(args.comment_id, …)` body-read path's reliance on a non-None `--comment-id` (it must tolerate `None`).
8. ⚠️ Modify `scripts/qrspi_comment_reply_test.py` — add a toplevel-without-comment-id passing case and confirm reply mode still rejects a missing id (ref: structure Slice 1 file list).

### Verify Slice 1

9. **Checkpoint:** `python3 scripts/run_tests.py review && python3 scripts/run_tests.py comment_reply && python3 scripts/qrspi_review_agreement.py`
   - [ ] `run_tests.py review` passes (both new test files green).
   - [ ] `run_tests.py comment_reply` passes (relaxation + existing cases green).
   - [ ] `qrspi_review_agreement.py` smoke prints `agreement` of `"pending"` for the pass+None default.

---

## Slice 2: /review-design end-to-end (AC1 + AC2)

### Setup

10. ✨ Read `scripts/qrspi_critic_loop.py` to confirm the **already-existing** CLI contract (verified at plan review, `qrspi_critic_loop.py:118-159`): stdin = JSON verdict array, flags `--round`/`--max-rounds`, stdout = JSON `{action, residual_findings}` with `action ∈ {converged, revise, cap_reached}`. The SKILL prose consumes this contract verbatim; there is no shim to add.
11. ✨ Read `scripts/qrspi_critic_synthesize.py` and `scripts/qrspi_metrics_append.py` to confirm their CLI invocation shapes for the SKILL prose (input/output contract for the synthesize reduce and the JSONL append).

### Core Logic

12. ✅ **No-op (corrected at plan review): no shim is added.** The CLI already exists (`qrspi_critic_loop.py:128-159`, `main()` + `__main__`), reading the stdin verdict array and printing `{action, residual_findings}` with `action ∈ {converged, revise, cap_reached}`. `scripts/qrspi_critic_loop.py` is **not modified** by this ticket — the SKILL loop calls the existing CLI as-is. (The draft's "add a thin shim emitting `converge|revise|stop`" was based on a research miss; both the existence and the action tokens were wrong.)
13. ✅ **No-op: no new test.** Since no shim is added, `scripts/qrspi_critic_loop_test.py` is untouched; the existing CLI path is already its own tested surface (RUS-55 Slice 3).
14. ✨ Create `.claude/skills/review-design/SKILL.md` via the **skill-creator** skill (constraint — do not hand-author). Frontmatter: name `review-design`, description triggering on `/review-design <id>`. Parse `$ARGUMENTS` for the ticket id (ref: structure Slice 2 file list, design Delta).
15. ✨ In `review-design/SKILL.md`, author step: run `python3 scripts/qrspi_resolve.py <id>` and read `repoRoot`/`worktreeDir`/`existing`/`reviewDecision`-for-design from the envelope (ref: design AC1, Decision 4; Slice 2 contract).
16. ✨ In `review-design/SKILL.md`, author step: derive the design PR number via `gh pr list --head <id>/design --json number` (ref: design AC1, Risk Register row 4).
17. ✨ In `review-design/SKILL.md`, author step: copy `<worktreeDir>/.qrspi/<id>/design.md` to the scratch path `/tmp/phase-stage/<id>/review/design.md` (ref: design Decision 2 — scratch isolation).
18. ✨ In `review-design/SKILL.md`, author the scratch loop (rounds 0..2): each round spawn the `qrspi-design-critic-design-review` lens (`subagent_type`) against the scratch copy + real codebase (named PATH inputs `DESIGN_PATH`=scratch copy, `RESEARCH_PATH`, `CODEBASE_PATH`, optional upstream paths; no `model` override per OQ5), reduce the round's verdict(s) via `qrspi_critic_synthesize.py`, then pipe the reduced verdict(s) into the existing `next_action` CLI — `printf '%s' '<verdicts-json>' | python3 scripts/qrspi_critic_loop.py --round <r> --max-rounds 3` — and branch on the emitted JSON `action`: `converged`/`cap_reached` → terminate the loop; `revise` → Step 19 (ref: design AC1, Decision 1; structure scratch-loop contract; corrected `next_action` contract above).
19. ✨ In `review-design/SKILL.md`, author the revise branch: on `revise`, re-spawn the phase producer `qrspi-design` (`subagent_type`) to rewrite the **scratch copy** in place (the producer-as-reviser pattern), then continue the loop (ref: design Delta, Decision 5; structure contract).
20. ✨ In `review-design/SKILL.md`, author the post-loop open-question pass: spawn `qrspi-design` (full upstream context + codebase access, NOT the strict lens) to answer the design's Open Questions section in free text; capture the answers for the synopsis (ref: design AC1, Decision 5).
21. ✨ In `review-design/SKILL.md`, author the record step: call `qrspi_review_agreement.compute(panel_pass, design_reviewDecision)` and `qrspi_review_record.build_record(phase="design", rounds, terminal_action, agreement)`, then append via `qrspi_metrics_append.py` to the per-ticket `critic-metrics.jsonl` (ref: design AC2, Decision 3).
22. ✨ In `review-design/SKILL.md`, author the synopsis step: post a toplevel advisory comment (verdict + findings + resolved open-question answers) to the design PR via `python3 scripts/qrspi_comment_reply.py --ticket <id> --pr <n> --reply-mode toplevel --body-file <path>` (toplevel; `--comment-id` omitted, relying on Slice 1's relaxation; `--ticket` and `--reply-mode` are still required — corrected at plan review). No `gt submit`/`gt modify`/branch write (ref: design AC1, Risk Register row 1).

### Verify Slice 2

23. **Checkpoint:** skill-creator eval loop for `review-design` + manual e2e on a real `<id>/design` PR.
    - [ ] skill-creator eval loop passes for the new skill (triggering + steps).
    - [ ] Manual e2e: synopsis comment (verdict + findings + open-question answers) posts; ledger gains a `mode:"on-demand-review"` row; with no human review yet the row shows `agreement:"pending"`.
    - [ ] PR head SHA is identical before and after the run (no branch mutation/push).
    - [ ] Re-run after a human review records a fresh row whose `agreement` resolves against the present `reviewDecision`.

---

## Slice 3: /review-plan + plan node-validity lens (AC3)

### Setup

24. ✨ Read `.claude/agents/qrspi-design-critic-design-review.md` to use it as the structural template for the new plan lens (named PATH inputs, `{pass, findings}` emit, read-only) (ref: structure Slice 3 file list).

### Core Logic

25. ✨ Create `.claude/agents/qrspi-plan-critic-plan-review.md` — new lens agent (tools Read/Grep) mirroring the design-review lens contract: named PATH inputs `PLAN_PATH`, `RESEARCH_PATH`, `CODEBASE_PATH`, optional upstream paths; emits exactly `{pass, findings}` validated as `CRITIC_VERDICT_SCHEMA` (`pass:false ⟺ findings non-empty`); reads real source; writes no files. Focus: whether plan steps are technically sound against the real code (ref: structure Slice 3, design AC3).
26. ✨ Create `.claude/skills/review-plan/SKILL.md` via **skill-creator**. Frontmatter: name `review-plan`, triggering on `/review-plan <id>`; parse `$ARGUMENTS` for the ticket id (ref: structure Slice 3 file list).
27. ✨ In `review-plan/SKILL.md`, author the same scratch-loop contract as Slice 2 pointed at `plan.md`: resolve → derive `<id>/plan` PR number (`gh pr list --head <id>/plan --json number`) → copy to `/tmp/phase-stage/<id>/review/plan.md` → rounds 0..2 with lens `qrspi-plan-critic-plan-review` / `synthesize` / `next_action` → revise re-spawns producer `qrspi-plan` to rewrite the scratch copy (ref: structure Slice 3, design AC3).
28. ✨ In `review-plan/SKILL.md`, **omit** the open-question-resolution pass (OQ1 resolved: design-phase-only in v1) (ref: plan-time OQ1 resolution, structure Unverified Assumptions OQ1).
29. ✨ In `review-plan/SKILL.md`, author the record + synopsis steps mirroring Slice 2: `compute` agreement against the plan PR's `reviewDecision`, `build_record(phase="plan", ...)`, append via `qrspi_metrics_append.py`, post toplevel synopsis to the plan PR via `qrspi_comment_reply.py` (full invocation per Step 22: `--ticket <id> --pr <n> --reply-mode toplevel --body-file <path>`) (ref: design AC3, Decision 3).

### Verify Slice 3

30. **Checkpoint:** skill-creator eval loop for `review-plan` + manual e2e on a real `<id>/plan` PR.
    - [ ] skill-creator eval loop passes for the new skill.
    - [ ] Manual e2e: synopsis posts; ledger row with `mode:"on-demand-review"`, phase `plan`.
    - [ ] PR head SHA unchanged after the run.

---

## Slice 4: /review-implementation + impl node-validity lens (AC4)

### Core Logic

31. ✨ Create `.claude/agents/qrspi-impl-critic-impl-review.md` — new lens agent (tools Read/Grep) mirroring the lens contract: named PATH inputs (slice artifacts, `RESEARCH_PATH`, `CODEBASE_PATH`, optional upstream); emits `{pass, findings}` as `CRITIC_VERDICT_SCHEMA`; writes no files. Focus: correctness/security/efficiency/performance against real code + tests (ref: structure Slice 4, design AC4).
32. ✨ Create `.claude/skills/review-implementation/SKILL.md` via **skill-creator**. Frontmatter: name `review-implementation`, triggering on `/review-implementation <id>`; parse `$ARGUMENTS` for the ticket id (ref: structure Slice 4 file list).
33. ✨ In `review-implementation/SKILL.md`, author the scratch-loop contract against the slice artifacts: resolve → derive the **top slice** PR number via `gh pr list --head <id>/slice-N --json number` (N = highest slice from the resolve envelope's `slices`) → copy slice artifact(s) to `/tmp/phase-stage/<id>/review/` → rounds 0..2 with lens `qrspi-impl-critic-impl-review` / `synthesize` / `next_action` → revise re-spawns producer `qrspi-implement` to rewrite the scratch copy (ref: structure Slice 4, design AC4).
34. ✨ In `review-implementation/SKILL.md`, **omit** the open-question-resolution pass (OQ1 resolved: design-phase-only) (ref: plan-time OQ1 resolution).
35. ✨ In `review-implementation/SKILL.md`, author the record + **single rolled-up synopsis** steps: `compute` agreement against the top slice PR's `reviewDecision`, `build_record(phase="implementation", ...)`, append via `qrspi_metrics_append.py`, post ONE rolled-up toplevel synopsis comment to the top slice PR via `qrspi_comment_reply.py` (full invocation per Step 22: `--ticket <id> --pr <n> --reply-mode toplevel --body-file <path>`) (ref: design AC4, structure Slice 4).

### Verify Slice 4

36. **Checkpoint:** skill-creator eval loop for `review-implementation` + manual e2e on a real implementation stack.
    - [ ] skill-creator eval loop passes for the new skill.
    - [ ] Manual e2e: a single rolled-up synopsis posts to the top slice PR; ledger row with `mode:"on-demand-review"`, phase `implementation`.
    - [ ] PR head SHA(s) unchanged after the run.

---

## Slice 5: /review comprehensive + docs (AC5 + AC7)

### Core Logic

37. ✨ Create `.claude/skills/review/SKILL.md` via **skill-creator**. Frontmatter: name `review`, triggering on `/review <id>`; parse `$ARGUMENTS` for the ticket id (ref: structure Slice 5 file list).
38. ✨ In `review/SKILL.md`, author the frontier-resolution step: determine the frontier (highest existing) phase using `gh pr list --state all` to dodge the partially-landed misfire (ref: design AC5, Q11; structure Slice 5).
39. ✨ In `review/SKILL.md`, author the per-phase pass: for each reviewed phase up to the frontier, run the per-phase lens (`qrspi-design-critic-design-review` / `qrspi-plan-critic-plan-review` / `qrspi-impl-critic-impl-review`) via the same scratch loop (`synthesize` + `next_action`); collect each phase's `{pass, findings}` (ref: design AC5, structure Slice 5).
40. ✨ In `review/SKILL.md`, author the aggregation + synopsis step per **OQ3 resolution (per-phase sub-synopses under one comment)**: build one toplevel comment body with a per-phase section (verdict + findings) and post it to the frontier PR via `qrspi_comment_reply.py` (full invocation per Step 22: `--ticket <id> --pr <n> --reply-mode toplevel --body-file <path>`) (ref: plan-time OQ3 resolution, design AC5).
41. ✨ In `review/SKILL.md`, author the record step: append one `mode:"on-demand-review"` ledger row **per reviewed phase** via `build_record` + `qrspi_metrics_append.py`, each with that phase's `agreement` computed against its PR's `reviewDecision` (ref: structure Slice 5, design AC2).
42. ⚠️ Modify `.claude/CLAUDE.md` (worktree copy) — document the `/review-*` family under "Available skills".
    - **Current:** "Available skills" lists the `qrspi-*` family only; no `/review-*` entries.
    - **After:** adds `/review-design`, `/review-plan`, `/review-implementation`, `/review` with one-line descriptions (advisory, propose-only, no branch push) (ref: design AC7).
43. ⚠️ Modify `CLAUDE.md` (repo root) — apply the same `/review-*` documentation, kept in sync with the worktree copy.
    - **Current:** repo-root `CLAUDE.md` "Available skills" lists the `qrspi-*` family only.
    - **After:** identical `/review-*` entries as Step 42 (ref: design AC7).

### Verify Slice 5

44. **Checkpoint:** skill-creator eval loop for `review` + manual e2e on a multi-phase stack + docs check.
    - [ ] skill-creator eval loop passes for the new skill.
    - [ ] Manual e2e: one synopsis (per-phase sub-sections) posts to the frontier PR; no misfire on a partially-landed stack.
    - [ ] PR head SHA unchanged after the run.
    - [ ] `CLAUDE.md` (both copies) documents `/review-design`, `/review-plan`, `/review-implementation`, `/review`.

---

## Rollback Notes

- **Steps 1–6 (new pure modules + tests):** delete `scripts/qrspi_review_agreement.py`, `scripts/qrspi_review_record.py`, and their `_test.py` siblings. No state to unwind (pure, no I/O).
- **Steps 7–8 (`qrspi_comment_reply.py` relaxation):** revert the argument-parsing change to restore `--comment-id` as required in both modes; revert the test addition. Behavioral-only; no data migration.
- **Step 12 (`next_action` CLI shim, conditional):** remove the added `__main__` block from `scripts/qrspi_critic_loop.py`; the pure `next_action` function is untouched, so the batch path is unaffected.
- **Steps 14–22, 26–29, 32–35, 37–41 (new skills + lens agents):** delete the new `.claude/skills/review*/` directories and `.claude/agents/qrspi-{plan,impl}-critic-*-review.md`. The on-demand path reuses but never modifies `runCriticPanelLoop` or batch config, so removal cannot regress the batch gate (AC6).
- **Steps 42–43 (CLAUDE.md docs):** revert the "Available skills" additions in both copies. Documentation-only.
- **Ledger rows:** review runs append `mode:"on-demand-review"` rows to `critic-metrics.jsonl`. These are additive and tagged; if a run must be discarded, drop the tagged lines for the run's `runId` — old consumers ignore the rows regardless.
- **No DB migrations, no destructive ops, no config-schema changes** are introduced by this plan.
