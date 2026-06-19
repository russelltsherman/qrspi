# Implementation Plan — Upgrade the /review-* advisory review family

**Structure basis:** structure.md @ 2026-06-19T00:00:00Z
**Generated:** 2026-06-19T00:00:00Z
**Status:** draft
**Total steps:** 27

## Slice 1: Surface blocking finding text in the synopsis render

**Goal:** A failing advisory review's rendered synopsis body contains the actual blocking finding strings (not just a per-lens count), verified by unit test in isolation — independent of the engine that later calls it.

### Setup

1. Read `scripts/qrspi_review_synopsis.py` in full to locate the per-lens table render (cited ~lines 140–147 in structure.md, line numbers UNVERIFIED — confirm the live insertion point) and confirm the finding strings are present on each verdict via `_verdict(..., findings=[str])`.

### Core Logic

2. ⚠️ Modify `scripts/qrspi_review_synopsis.py` — extend `render_synopsis` so that beneath each FAIL row it emits a "Blocking findings" sub-section listing the deduped finding strings for that lens.
   - **Current:** `render_synopsis(...) -> str` emits a per-lens `PASS|FAIL|count` table row only; the finding strings in the input array never reach the body. `nonBlockingNotes` text IS rendered.
   - **After:** `render_synopsis(...) -> str` (signature unchanged) keeps the `PASS|FAIL|count` row AND adds, beneath each FAIL row, a per-lens "Blocking findings" sub-section emitting the deduped finding strings. `ledger_row_fields` / `partition_decision_readiness` signatures unchanged (additive render only).

### Tests

3. ⚠️ Modify `scripts/qrspi_review_synopsis_test.py` — add assertions that the blocking finding strings (already present in the fixtures' `findings=[...]`) surface verbatim in the rendered body, and that `nonBlockingNotes` text still renders unchanged.
4. Run: `python3 scripts/qrspi_review_synopsis_test.py`
   - **Expected:** passes, including the new finding-text and unchanged-`nonBlockingNotes` assertions.

### Verify Slice 1

5. **Checkpoint:** `python3 scripts/qrspi_review_synopsis_test.py`
   - [ ] Test passes, including the new finding-text assertions
   - [ ] A FAIL-fixture render shows the literal finding strings; `nonBlockingNotes` text still renders unchanged

---

## Slice 2: Add the on-demand `critics.review.lensModel` reader

**Goal:** A pure, stdlib-only reader resolves the NEW on-demand `critics.review.lensModel` key to a model id or `None`, with the batch design config path provably untouched — verified by unit test in isolation before the engine wires it.

### Setup

6. Read `scripts/qrspi_critics_config.py` in full to confirm the existing `resolve_design` / `DEFAULT_DESIGN_LENSES` / batch `critics.design.*` envelope and the "do NOT couple" comments, and the fail-closed (never-raise) reader convention to mirror.

### Core Logic

7. ⚠️ Modify `scripts/qrspi_critics_config.py` — add `resolve_review_lens_model(cfg)` reading the NEW on-demand key `critics.review.lensModel`. Leave `resolve_design`, `DEFAULT_DESIGN_LENSES`, the batch `critics.design.*` envelope, and the "do NOT couple" comments untouched.
   - **Current:** module exposes `resolve_design` (reads batch `critics.design.lensModel`); no on-demand review reader exists.
   - **After:** module additionally exposes `resolve_review_lens_model(cfg) -> str | None` — returns the configured `critics.review.lensModel` id, or `None` when absent/malformed (fail closed, never raise). Deliberately separate from `resolve_design`.

### Tests

8. ⚠️ Modify `scripts/qrspi_critics_config_test.py` — assert `resolve_review_lens_model` returns the configured id when set, returns `None` when the key is absent or malformed, and that `resolve_design` output is unchanged (non-coupling regression).
9. Run: `python3 scripts/qrspi_critics_config_test.py`
   - **Expected:** passes, including the new reader cases and the `resolve_design` non-coupling regression.

### Verify Slice 2

10. **Checkpoint:** `python3 scripts/qrspi_critics_config_test.py && python3 scripts/run_tests.py critics`
    - [ ] `qrspi_critics_config_test.py` passes (new reader + non-coupling assertions)
    - [ ] `python3 scripts/run_tests.py critics` is green (batch critics contract fixture unaffected)

---

## Slice 3: Deterministic review engine + thin SKILL wrappers + wired lens model

**Goal:** Invoking any of `/review-design|plan|implementation <ticket>` runs the shared deterministic engine once (round 0, no revise), spawns the `*-review` lens under the configured model, renders findings (Slice 1), posts the synopsis comment + ledger row, and re-asserts the unchanged PR head SHA — replacing the three hand-driven SKILL loops.

### Setup

11. Read `.claude/workflows/qrspi-batch.js` to confirm the harness substrate to mirror: `engineCmdFor(r, rel)`, `stg()` → `/tmp/phase-stage/<id>/`, mandatory `provisionStep` per worker, `agent(prompt, {model})` spawn options, and the python-as-command-string convention.
12. Read the three existing `.claude/skills/review-{design,plan,implementation}/SKILL.md` files to capture the round-0 fan-out, scratch-copy, decision-readiness (design-only), comment, ledger, and SHA-assert prose being collapsed; confirm the `DEFAULT_REVIEW_*` lens tuples each references.
13. Read `scripts/qrspi_critic_synthesize.py`, `scripts/qrspi_review_record.py`, `scripts/qrspi_review_synopsis.py` (`partition_decision_readiness`), `scripts/qrspi_comment_reply.py`, and `scripts/qrspi_metrics_append.py` to confirm the concrete call signatures the engine invokes (esp. `build_record(..., terminalAction, agreement)` `VALID_TERMINAL_ACTIONS`, `synthesize(...)` called once, and how `partition_decision_readiness` is fed round-0 verdicts under no-revise).
14. Decide, from the reads above, whether `qrspi-review.js` actually parses Python stdout at any JS↔Python seam (UNVERIFIED per structure.md Unverified Assumptions). If yes → seam fixtures are required (steps 22–23); if the engine only shell-orchestrates command strings like `qrspi-batch.js`, skip the seam fixtures and record that decision in the engine header comment.

### Core Logic

15. ✨ Create `.claude/workflows/qrspi-review.js` — new deterministic orchestrator taking `{ticket, phase}`. Resolve worktree/PR via `qrspi_resolve.py`; scratch-copy the artifact via `stg()`; capture the PR head SHA; fan the phase's `DEFAULT_REVIEW_*` lenses via `agent(...)` (passing the `resolve_review_lens_model` value as the `model` key on the `*-review` lens spawn ONLY); call `synthesize` ONCE (round 0, no revise loop); run the design-only post-panel decision-readiness lens; compute the terminal action inline (`converged` on a round-0 pass, else `exhausted`); call `render_synopsis`; post the comment via `qrspi_comment_reply.py`; append the ledger row via `qrspi_metrics_append.py` with an empty agreement block `{}`; re-assert the head SHA is unchanged. Use `engineCmdFor(r,rel)`, `stg()`, mandatory `provisionStep`, python-as-command-string. Issue NO branch-mutating command (read-only `gh pr view`/`gh pr list` and the `gh pr comment` write are permitted; see step 26 for the exact mutating-verb guard).
   - **Agreement line intentionally removed (F2 decision):** the current SKILLs compute a lightweight at-review-time agreement from the human's existing `reviewDecision` (no re-run) and append an "Agreement" line to the synopsis. The new engine **does NOT** invoke `qrspi_review_agreement.compute` and appends **no** Agreement line — it passes `agreement={}` to `build_record` purely to satisfy the required positional. Rationale: the ticket's 2026-06-19 scope change drops the agreement signal (the panel-calibration concern relocates to the offline teeth-eval); removing the cheap at-review comparison too keeps the engine consistent with that direction. The pure `qrspi_review_agreement.py` helper remains on disk, unused by this family (no deletion).

### SKILL wrappers

16. ⚠️ Modify `.claude/skills/review-design/SKILL.md` — collapse to a thin wrapper invoking the engine with `{ticket, phase:"design"}`.
    - **Current:** ~270–306 lines of hand-executed loop/scratch/render/SHA prose.
    - **After:** thin wrapper that invokes `qrspi-review.js` with `{ticket, phase:"design"}`; duplicated loop/scratch/render/SHA prose removed.
17. ⚠️ Modify `.claude/skills/review-plan/SKILL.md` — collapse to a thin wrapper invoking the engine with `{ticket, phase:"plan"}`.
    - **Current:** ~270–306 lines of hand-executed loop/scratch/render/SHA prose.
    - **After:** thin wrapper invoking `qrspi-review.js` with `{ticket, phase:"plan"}`.
18. ⚠️ Modify `.claude/skills/review-implementation/SKILL.md` — collapse to a thin wrapper invoking the engine with `{ticket, phase:"impl"}`.
    - **Current:** ~270–306 lines of hand-executed loop/scratch/render/SHA prose.
    - **After:** thin wrapper invoking `qrspi-review.js` with `{ticket, phase:"impl"}`.

### Agent defs

19. ⚠️ Modify `.claude/agents/qrspi-design-critic-design-review.md` — replace the "not wired / documentation only" model note with the now-wired behavior (orchestrator supplies the override at spawn; frontmatter stays model-less).
    - **Current:** model note states the `lensModel` intent is documentation only / not wired.
    - **After:** model note states the orchestrator supplies the `model` override at spawn from `critics.review.lensModel`; frontmatter remains model-less.
20. ⚠️ Modify `.claude/agents/qrspi-plan-critic-plan-review.md` — same model-note update (orchestrator-supplied override; frontmatter model-less).
21. ⚠️ Modify `.claude/agents/qrspi-impl-critic-impl-review.md` — same model-note update (orchestrator-supplied override; frontmatter model-less).
22. ⚠️ Modify `.claude/agents/qrspi-critic-reviser.md` — mark dormant / unused-by-review (the revise loop is dropped). Do NOT delete the `qrspi_critic_loop` MODULE — it is still imported by `qrspi_critic_synthesize.py` (`_coerce_verdict`/`parse_critic_verdict`).

### Tests (conditional on step 14)

23. ✨ Create `scripts/fixtures/contract_seam/review/` fixtures — ONLY IF step 14 found a JS↔Python parser seam in the engine. Add producer/consumer coverage for that seam, driven through `contract_seam_runner.js` (skips when `node` absent). If step 14 found no seam, skip this step and record the decision in the engine header.
24. ⚠️ Modify the seam fixture / engine assertion — add a check that no branch-**mutating** command is emitted by the engine, guarding the propose-only invariant. The check must target the MUTATING subset only and must NOT flag the engine's legitimate read-only GitHub calls (confirmed against the current SKILL: head-SHA capture is `gh pr view <PR> --json headRefOid`, PR derivation is `gh pr list --head`, and the comment write is `gh pr comment` via `qrspi_comment_reply.py` — all non-mutating). Match the mutating verbs: `gt submit`, `gt modify`, `gt create`, `gt restack`, `git push`, `gh pr edit|merge|close|ready`, and write-verb (`-X POST|PATCH|PUT|DELETE`) `gh api` calls on `pulls`/`git/refs`. The head-SHA re-assert (step 15 / the engine's final step) remains the primary guardrail; this grep is a belt-and-suspenders static check.

### Verify Slice 3

25. **Checkpoint:** `python3 scripts/run_tests.py`
    - [ ] Full suite green (seam fixtures, if added, + all helpers including Slices 1–2)
26. **Checkpoint:** `grep -nE "gt (submit|modify|create|restack)|git push|gh pr (edit|merge|close|ready)|gh api[^|]*-X *(POST|PATCH|PUT|DELETE)" .claude/workflows/qrspi-review.js`
    - [ ] No match — no branch-mutating command present. (Read-only `gh pr view`/`gh pr list` for head-SHA capture + PR derivation, the `gh pr comment` comment write via `qrspi_comment_reply.py`, and the ledger append `qrspi_metrics_append.py` are all expected and MUST NOT be flagged.)
    - [ ] The `model` override is passed on the `*-review` lens spawn only
27. **Checkpoint (manual end-to-end):** run each of `/review-design`, `/review-plan`, `/review-implementation` against a real ticket PR
    - [ ] The synopsis comment posts and contains blocking finding text on FAIL
    - [ ] The ledger row appends with terminal action `converged`/`exhausted` and empty agreement `{}`
    - [ ] The posted synopsis contains NO "Agreement" line (intentionally removed — F2); `qrspi_review_agreement.compute` is not invoked
    - [ ] `gh pr view` shows the PR head SHA unchanged (no branch push)
    - [ ] The `*-review` lens spawn carries the `model` override when `critics.review.lensModel` is set

---

## Rollback Notes

- **Step 7 (config reader):** purely additive — no config schema migration. Reverting removes `resolve_review_lens_model`; the new `critics.review.lensModel` key is read-only and absent by default, so no `.qrspi/config.json` change is required and none must be rolled back. Untouched `resolve_design`/batch path means no batch-side regression to reverse.
- **Step 15 (new engine):** the engine is propose-only and issues NO branch-mutating `gt`/`gh` command, so a partially-built or reverted engine leaves PR branches and history untouched. Rollback = delete `.claude/workflows/qrspi-review.js` and restore the three original `SKILL.md` files (steps 16–18) from git.
- **Steps 16–18 (SKILL collapse):** these replace working hand-driven loops. If the engine is not yet trustworthy, restore the prior `SKILL.md` bodies from git history (`b7d8c96` era) before re-running any `/review-*` command, so the family does not point at a half-built engine.
- **Step 22 (reviser dormancy):** documentation-only; the `qrspi_critic_loop` module is NOT removed (still imported by `qrspi_critic_synthesize.py`). Reverting the note is non-destructive.
