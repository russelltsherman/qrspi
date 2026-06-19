# Implementation Plan — Resolve project-analysis tech debt: pivot residue, eval docs, doc bloat, untested CI-revise counter

**Structure basis:** structure.md @ 2026-06-19T00:00:00Z
**Generated:** 2026-06-19T00:00:00Z
**Status:** draft
**Total steps:** 51 (47 base + steps 15a, 24a, 37a added in revise; step numbering preserves the original sequence)

## Slice 1: Pivot-residue sweep (agent frontmatter + dead-path comments)

### Setup

1. ⚠️ Modify `.claude/agents/qrspi-design-critic-completeness.md` — replace the `runCriticPanelLoop` spawn line at `:3` with the `/review-design` form, mirroring the impl-review peer.
   - **Current:** `:3` contains `Spawned by runCriticPanelLoop in qrspi-batch.js`
   - **After:** `:3` reads `Spawned by the /review-design command (advisory, propose-only)`
2. ⚠️ Modify `.claude/agents/qrspi-design-critic-edge-alignment.md` — same spawn-line replacement at `:3`.
   - **Current:** `:3` contains `Spawned by runCriticPanelLoop in qrspi-batch.js`
   - **After:** `:3` reads `Spawned by the /review-design command (advisory, propose-only)`
3. ⚠️ Modify `.claude/agents/qrspi-design-critic-internal-consistency.md` — same spawn-line replacement at `:3`.
   - **Current:** `:3` contains `Spawned by runCriticPanelLoop in qrspi-batch.js`
   - **After:** `:3` reads `Spawned by the /review-design command (advisory, propose-only)`
4. ⚠️ Modify `.claude/agents/qrspi-design-critic-simplicity.md` — same spawn-line replacement at `:3`.
   - **Current:** `:3` contains `Spawned by runCriticPanelLoop in qrspi-batch.js`
   - **After:** `:3` reads `Spawned by the /review-design command (advisory, propose-only)`
5. ⚠️ Modify `.claude/agents/qrspi-design-critic-design-review.md` — replace the spawn line at `:3` (carrying its `(opt-in, default-OFF)` qualifier) with the `/review-design` form. Read the exact current line first; preserve any non-residue qualifier text that still applies post-pivot, dropping only the dead `runCriticPanelLoop` reference.
   - **Current:** `:3` references `runCriticPanelLoop in qrspi-batch.js` with an `(opt-in, default-OFF)` qualifier
   - **After:** `:3` names `/review-design` as the spawn path, consistent with the four sibling design-critic files

### Core Logic

6. ⚠️ Modify `.claude/agents/qrspi-impl-critic-impl-review.md` — at `:3` replace the panel-noun only; the spawn line is already correct.
   - **Current:** `:3` says `implementation-phase **critic panel** (IMPL-REVIEW)`
   - **After:** `:3` says `implementation-phase **review panel** (IMPL-REVIEW)`
7. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — remove the genuine dead-path comments. First run `grep -rn "removed\|no longer\|deleted worker\|the old" .claude/workflows/qrspi-batch.js` against the LIVE file to locate candidates; remove ONLY comment lines that describe a removed/no-longer-present code path (the stale `~525–561 / ~810–833` citations are NOT to be trusted — research found those ranges are live code). Edit comment lines only; touch no executable statement. Confirm each removal target is a comment, not code, before deleting.
   - **Current:** dead-path narration comments scattered in the live file (candidate regions per research: 48, 168, 1033, 1169, 1212 — re-verify against the live grep)
   - **After:** those dead-path comment lines removed; all surrounding executable code byte-for-byte unchanged

### Verify Slice 1

8. **Checkpoint:** `grep -rn "runCriticPanelLoop" .claude/agents/`
   - [ ] Returns zero hits across `.claude/agents/`
   - [ ] `grep -rn "runCriticPanelLoop" .claude/workflows/qrspi-review.js .claude/workflows/qrspi-teeth-eval.js` still returns the original hits (legitimate live-code docs untouched)
9. **Checkpoint:** `grep -n "review panel" .claude/agents/qrspi-impl-critic-impl-review.md && grep -n "critic panel" .claude/agents/qrspi-impl-critic-impl-review.md`
   - [ ] `review panel` is present at `:3`
   - [ ] `critic panel` returns zero hits in that file
10. **Checkpoint:** `git diff .claude/workflows/qrspi-batch.js && python3 scripts/run_tests.py`
    - [ ] The diff shows only comment-line deletions (no executable-line changes)
    - [ ] Full unit suite passes (no behavioral change introduced)

---

## Slice 2: CI-revise verdict moved into the resolver + tests

### Setup

11. ⚠️ Modify `scripts/qrspi_resolve_state.py` — add the `ciCounterAction` field to the `decision()` factory, defaulted at the single construction point so every action branch emits it.
    - **Current:** `decision(...) -> dict` factory builds the fixed-key dict with sibling verdict fields `ciFailing` / `ciGaveUp` but no `ciCounterAction`
    - **After:** `decision(...) -> dict` factory sets `ciCounterAction` defaulted to `"none"` (typed `str ∈ {"bump","reset","none"}`), present on every returned decision dict

### Core Logic

12. ⚠️ Modify `scripts/qrspi_resolve_state.py` — set `ciCounterAction = "bump"` on EVERY revise branch whose `ciFailing` is True, i.e. wherever a red CI signal drives (or co-drives) the revise. There are TWO such branches, not one (review correction — the prior single-branch version regressed the combined feedback+red-CI counter bump):
    - **Branch 2b — unified feedback handler** (`scripts/qrspi_resolve_state.py:264-272`, the `decision("revise", ..., ciFailing=ci_red, ...)` return). When the frontier feedback PR ALSO has red CI (`ci_red` True), this is a combined `changeRequested && ciFailing` revise — it MUST emit `ciCounterAction = "bump"`. Set it to `"bump" if ci_red else "reset"` at this return site (the not-red feedback case is the `"reset"` of step 13). The real `doRevise` bumps the counter whenever `ciFailing` is true, for BOTH the combined and pure-CI revise (`.claude/workflows/qrspi-batch.js:1019-1031`), so omitting the bump here would write NO trailer on a CHANGES_REQUESTED+red-CI frontier and break the AC6 "unfixable red marches toward the cap" guarantee.
    - **Branch 2c — red-frontier-under-cap CI revise** (`scripts/qrspi_resolve_state.py:290-298`, where `fci == "red"` and `attempt < cap`): emit `ciCounterAction = "bump"`.
    - **Current:** neither the 2b combined-revise return nor the 2c red-under-cap return sets `ciCounterAction` (factory default `"none"` applies — wrong for the bump)
    - **After:** the verdict is `"bump"` on any revise where `ciFailing` is True (both 2b-with-red-CI and 2c); derived only from existing inputs (`ci_red` / `fci`, `attempt`, `cap`), no new params
13. ⚠️ Modify `scripts/qrspi_resolve_state.py` — set `ciCounterAction = "reset"` on every NOT-red revise branch (a revise driven by `changeRequested` / feedback where CI is NOT red): the 2b unified-feedback return when `ci_red` is False — covered by the `"bump" if ci_red else "reset"` expression from step 12 at that same return site. Leave the at/above-cap (`ciGaveUp`/`wait`, `scripts/qrspi_resolve_state.py:299-303`) branch and ALL non-revise branches at the `"none"` factory default. Invariant: `ciFailing → "bump"`; not-red revise → `"reset"`; everything else → `"none"`.
    - **Current:** the not-red revise return does not set `ciCounterAction`
    - **After:** the 2b not-red return emits `ciCounterAction = "reset"`; cap-exceeded (`wait`/`ciGaveUp`) and non-revise branches remain `"none"`

### Tests

14. ⚠️ Modify `scripts/qrspi_resolve_state_test.py` — add a `case(...)` asserting `ciCounterAction == "bump"` for a red frontier under cap (`ci_state="red"`, `ci_attempt < cap`), reusing the existing `_phase` / `_slice` builders with `ci_state=` / `ci_attempt=` / `cap=` overrides (covers branch 2c).
15. ⚠️ Modify `scripts/qrspi_resolve_state_test.py` — add a `case(...)` asserting `ciCounterAction == "reset"` for a green frontier carrying a change request (non-CI revise via branch 2b, `ci_red` False).
15a. ⚠️ Modify `scripts/qrspi_resolve_state_test.py` — add a `case(...)` asserting `ciCounterAction == "bump"` AND `changeRequested == True` AND `ciFailing == True` for the COMBINED case: a frontier feedback PR (change request and/or unaddressed comment) that ALSO has red CI under cap (branch 2b with `ci_red` True). This case is the one the prior plan regressed — it must prove the combined revise still bumps the counter, guarding AC6.
16. ⚠️ Modify `scripts/qrspi_resolve_state_test.py` — add a `case(...)` asserting `ciCounterAction == "none"` (with `ciGaveUp` set) for a red frontier at/above cap (`ci_attempt >= cap`).
17. Run: `python3 scripts/run_tests.py resolve`
    - **Expected:** the four new `ciCounterAction` cases (2c bump / 2b reset / 2b-combined bump / cap→none) pass AND the existing CI cases at `qrspi_resolve_state_test.py:343-474` still pass (field added via factory → all actions defaulted).

### Integration

18. ⚠️ Modify `scripts/qrspi_resolve.py` — echo `ciCounterAction` through the envelope ONLY if the resolver decision dict is not already passed verbatim into the envelope. First read the file to confirm how the decision dict reaches the envelope: if the whole dict is forwarded as-is, this step is a verified no-op (record that and make no edit); if individual keys are copied, add `ciCounterAction` to the copied set.
    - **Current:** envelope construction in `qrspi_resolve.py` (verify whether decision dict is forwarded verbatim or key-by-key)
    - **After:** `ciCounterAction` reaches the JS consumer — either already-present (no-op) or explicitly added to the echoed keys
19. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — thin `doRevise` (≈918–1045) so its TWO existing trailer writes dispatch on `decision.ciCounterAction` instead of re-deriving from `ciFailing` / `changeRequested`, while PRESERVING each path's existing gating semantics verbatim (review correction — the prior step-19 rewrite regressed the change-request reset from unconditional to applied-gated). There are TWO distinct writers, each with a DIFFERENT gate that must be kept:
    - **change-request (non-CI) path** (`.claude/workflows/qrspi-batch.js:1032-1038`, the `else if (changeRequested)` branch that calls `resetCiReviseTrailer` UNCONDITIONALLY — its own comment documents "Call resetCiReviseTrailer UNCONDITIONALLY — it is idempotent ... preserving the CLAUDE.md invariant 'every non-CI amend overwrites the trailer to 0'"). Re-key the branch condition to `decision.ciCounterAction === "reset"` (instead of re-deriving `else if (changeRequested)`), but KEEP the reset call UNCONDITIONAL — do NOT add an `answered.some(a => a.applied)` gate here. A pure change-request revise with no comment targets (resolver 2b: `commentTargets=[]` → JS `answered=[]`) still amends content via `qrspi_revise_amend.py` (which preserves the message verbatim, carrying a stale trailer), so gating the reset on `answered.some()` would leave a stale `CI-Revise-Attempt: N` on the committed head — the exact hygiene bug the unconditional reset fixes.
    - **CI path** (`.claude/workflows/qrspi-batch.js:1019-1031`, the `if (ciFailing)` branch calling `bumpCiReviseTrailers` unconditionally): re-key to `decision.ciCounterAction === "bump"`, keeping the bump UNCONDITIONAL (it must fire even when the worker pushed no amend, so an unfixable red marches toward the cap — AC6).
    - **comment-only path** (`.claude/workflows/qrspi-batch.js:955-965`, the `if (!changeRequested && !ciFailing)` early-return block): leave its `if (answered.some(a => a.applied)) resetCiReviseTrailer(...)` gate EXACTLY as-is. This is the ONLY path where the `answered.some(applied)` gate is correct (a comment-only PR only amends when a comment was applied). This path is reached BEFORE the `ciCounterAction` dispatch and is not re-keyed.
    - **Current:** `doRevise` selects `bumpCiReviseTrailers` (CI path, unconditional) vs `resetCiReviseTrailer` (change-request path, unconditional) by re-deriving from `ciFailing` / `changeRequested`; the comment-only early-return separately gates its reset on `answered.some(applied)`
    - **After:** the CI bump dispatches on `ciCounterAction === "bump"` (still unconditional); the change-request reset dispatches on `ciCounterAction === "reset"` (still UNCONDITIONAL — NOT applied-gated); the comment-only path's `answered.some(applied)`-gated reset is untouched. Keep edits inside the `doRevise` region only (disjoint from Slice 1's comment-line edits).

### Verify Slice 2

20. **Checkpoint:** `python3 scripts/run_tests.py resolve`
    - [ ] Passes, including the three new `ciCounterAction` cases (bump / reset / cap→none)
    - [ ] Existing `qrspi_resolve_state_test.py:343-474` CI cases still pass
21. **Checkpoint:** manual e2e read-through of `doRevise` in `.claude/workflows/qrspi-batch.js`
    - [ ] The `answered.applied` gate still short-circuits the trailer write on a comment-only PR (the file is not unit-testable; confirm by reading)
    - [ ] No re-derivation of bump-vs-reset from `ciFailing` / `changeRequested` remains; dispatch is on `decision.ciCounterAction`

---

## Slice 3: Eval-doc wording correction + lifecycle-narrative dedup + guide-pack consolidation

### Setup — eval-string corrections

22. ⚠️ Modify `.claude/CLAUDE.md` — at `:187` correct the eval string.
    - **Current:** `:187` calls the eval harness a `non-functional placeholder`
    - **After:** `:187` describes it as `functional but unwired/orphaned`
23. ⚠️ Modify `scripts/eval_all.py` — at `:11` correct the comment.
    - **Current:** `:11` comment reads `non-functional placeholder`
    - **After:** `:11` comment reads `functional but unwired`
24. ⚠️ Modify `docs/eval-system.md` — re-verify the eval-string occurrences against the LIVE file first (`grep -n "non-functional placeholder" docs/eval-system.md`), then correct each occurrence found. NOTE (review correction): the live `docs/eval-system.md` currently contains ZERO occurrences of the literal string `non-functional placeholder` (verified via grep on the live tree), so the prior "lines 7 / 97 / 101" enumeration is stale — the string-correction portion of this step is a no-op against non-existent text. If the live grep returns no hits, record that and make no string edit here (the stale line citations are corrected separately in step 25). The live set of files that DO carry the string is enumerated authoritatively in step 24a.
    - **Current:** `docs/eval-system.md` carries no `non-functional placeholder` string (the stale "lines 7/97/101" claim does not match the live tree)
    - **After:** no string edit if the live grep returns zero hits; otherwise correct each live occurrence to `functional but unwired/orphaned`
24a. ⚠️ Modify `scripts/qrspi_teeth_test.py` — at `:17` correct the eval string. This is the SEVENTH real, git-tracked occurrence of `non-functional placeholder`, inherited-miss from the upstream questions/research six-location list; it lives inside the step-38 grep scope (`scripts/`) and is touched by NO other plan step, so without this step AC2 (and the step-38 zero-hits checkpoint) cannot pass. The authoritative LIVE occurrence set (re-verified for this plan via `grep -rn "non-functional placeholder" .claude/ docs/ scripts/`) is FIVE files: `.claude/CLAUDE.md:187` (step 22), `scripts/eval_all.py:11` (step 23), `docs/qrspi-orientation.md:76` (step 34), `docs/qrspi_practical_application.md:185` (satisfied by the step-32 deletion), and `scripts/qrspi_teeth_test.py:17` (THIS step). `docs/eval-system.md` and `docs/qrspi_quick_reference.md` carry NO live occurrence (the prior steps 24/28/33 enumerations were stale). Re-run the live grep at implementation and correct EVERY occurrence it returns, not just the enumerated set, so AC2's unconditional "no source/doc file describes the eval harness as a 'non-functional placeholder'" holds.
    - **Current:** `scripts/qrspi_teeth_test.py:17` reads `...require reviving ``evals/run_eval.py`` (a non-functional placeholder) and are deferred...`
    - **After:** `:17` describes the harness as `functional but unwired/orphaned` (preserving the surrounding sentence's meaning); zero `non-functional placeholder` hits remain anywhere under `.claude/ docs/ scripts/`
25. ⚠️ Modify `docs/eval-system.md` — re-verify and fix the embedded line citations. NOTE (review correction): the live files are at `scripts/run_eval.py` and `scripts/revise.py`, NOT `evals/run_eval.py`/`evals/revise.py` (verified by find — there is no `evals/run_eval.py`). First open the live `scripts/run_eval.py` and `scripts/revise.py` and read the true line ranges for the cited regions; then correct the `run_eval.py:117-137` and `revise.py:26-44` citations to the actual numbers (e.g. `execute_single` is at `scripts/run_eval.py:151`, not 117). Derive the exact target numbers by reading the live files in this step.
    - **Current:** citations `run_eval.py:117-137` and `revise.py:26-44` are stale and name the wrong directory
    - **After:** citations match the live `scripts/run_eval.py` / `scripts/revise.py` line numbers

### Core Logic — guide-pack consolidation + lifecycle dedup

26. ✨ Create `docs/qrspi-guide.md` — a fresh consolidated guide absorbing the kept (non-redundant) content of the five `docs/qrspi_*` guide-pack files (`qrspi_claude_code_guide.md`, `qrspi_complete_guide.md`, `qrspi_practical_application.md`, `qrspi_quick_reference.md`, `qrspi_working_example.md`). The lifecycle narrative stays a pointer to `docs/qrspi-pr-gated-lifecycle-design.md` rather than a restatement. Where a source file carried an eval string, the corrected `functional but unwired` wording is used in the merged text.
27. ⚠️ Modify `docs/qrspi_practical_application.md` — fold its kept content into `docs/qrspi-guide.md` (step 26). The `:185` eval-string correction is satisfied by deletion below; do not separately edit if deleting. Confirm no unique signal is dropped before deletion.
28. ⚠️ Modify `docs/qrspi_quick_reference.md` — fold its kept content into `docs/qrspi-guide.md` (step 26). The `:208` eval-string correction is satisfied by deletion below. Confirm no unique signal is dropped before deletion.
29. ⚠️ Modify `docs/qrspi_claude_code_guide.md` — **DELETE** (kept content merged into `docs/qrspi-guide.md` in step 26).
30. ⚠️ Modify `docs/qrspi_complete_guide.md` — **DELETE** (merged in step 26).
31. ⚠️ Modify `docs/qrspi_working_example.md` — **DELETE** (merged in step 26).
32. ⚠️ Modify `docs/qrspi_practical_application.md` — **DELETE** (merged in step 26; supersedes the step-27 in-place correction).
33. ⚠️ Modify `docs/qrspi_quick_reference.md` — **DELETE** (merged in step 26; supersedes the step-28 in-place correction).
34. ⚠️ Modify `docs/qrspi-orientation.md` — at `:76` correct the eval string; strip the meta-index content that only describes the now-deleted sibling guides; point its lifecycle narrative at `docs/qrspi-pr-gated-lifecycle-design.md`. Keep any content that carries unique signal (editorial judgment per Unverified Assumptions).
    - **Current:** `:76` reads `non-functional placeholder`; body restates lifecycle and indexes deleted siblings
    - **After:** `:76` reads `functional but unwired/orphaned`; sibling-only index content removed; lifecycle is a pointer
35. ⚠️ Modify `.claude/CLAUDE.md` — replace the duplicated `Lifecycle — PR-gated` narrative with a reference to `docs/qrspi-pr-gated-lifecycle-design.md`, preserving the `Selected` / `Design Review` / `Plan Review` / `Code Review` / `Done` status invariants and the entry-gate wording verbatim.
    - **Current:** full restated `Lifecycle — PR-gated` section
    - **After:** a short pointer to the canonical doc; status invariants + entry-gate wording retained verbatim
36. ⚠️ Modify `.claude/skills/qrspi-work/SKILL.md` — replace the restated lifecycle narrative (lines 9, 28–29, 197–198, 432) with a reference to `docs/qrspi-pr-gated-lifecycle-design.md`, preserving the resolver-keyed status invariants verbatim.
    - **Current:** lifecycle narrative restated at lines 9, 28–29, 197–198, 432
    - **After:** those restatements replaced by a canonical-doc pointer; status invariants retained verbatim
37. ⚠️ Modify `docs/qrspi-pr-gated-lifecycle-design.md` — confirm (and, if any restatement was canonicalized here, ensure) the `Selected` / `Design Review` / `Plan Review` / `Code Review` / `Done` sequence and the entry-gate wording survive verbatim as the single canonical home. Edit only if an invariant is missing; otherwise this is a verified no-op.
37a. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — point the `revise`-action lifecycle/CI narrative COMMENT block (the multi-line description of the advance/revise/CI/cap mechanics above `doRevise`, verified live at `.claude/workflows/qrspi-batch.js:887-917`) at the canonical home `docs/qrspi-pr-gated-lifecycle-design.md`, so the third referencer the ticket names by hand ("`CLAUDE.md`, `qrspi-work/SKILL.md`, **and the batch comments**", AC3) is deduplicated alongside the other two. Strip the restated lifecycle/revise/CI/cap narrative down to a short pointer at the canonical doc, KEEPING only the comment lines that describe THIS function's local mechanics that are NOT lifecycle narrative — specifically the `r.commentTargets` / `r.decision.changeRequested` / `r.ciFailing` / `r.ciFailingChecks` / `r.ciRedBranches` decision-field documentation (those describe the local data contract, not the lifecycle) and the new `ciCounterAction` dispatch behavior from step 19. Edit COMMENT lines only; touch no executable statement (the `async function doRevise` signature at `:918` and below is unchanged). This step is DISJOINT from Slice 1 step 7 (dead-path comment removal of removed code paths) — step 7 removes comments narrating no-longer-present code; this step re-homes a still-accurate lifecycle restatement to its canonical pointer.
    - **Current:** `.claude/workflows/qrspi-batch.js:887-917` restates the PR-gated revise/advance/CI/cap lifecycle narrative inline (a near-clone of the `CLAUDE.md` / `qrspi-work` lifecycle prose)
    - **After:** that block is a short pointer to `docs/qrspi-pr-gated-lifecycle-design.md`; only the local decision-field contract + `ciCounterAction` dispatch note remain; all executable code byte-for-byte unchanged
    - **Alternative if re-homing proves to drop load-bearing local signal:** record an explicit, justified deferral in the plan (and the PR body) rather than silently omitting batch.js from AC3's three-referencer set.

### Verify Slice 3

38. **Checkpoint:** `grep -rn "non-functional placeholder" .claude/ docs/ scripts/`
    - [ ] Returns zero hits (this now PASSES because step 24a corrects the previously-omitted `scripts/qrspi_teeth_test.py:17` — the seventh occurrence inside this grep scope)
    - [ ] Replacement wording (`functional but unwired/orphaned`) is consistent across every LIVE original location (`.claude/CLAUDE.md:187`, `scripts/eval_all.py:11`, `docs/qrspi-orientation.md:76`, `scripts/qrspi_teeth_test.py:17`, plus `docs/qrspi_practical_application.md:185` handled via deletion) and does not contradict the project MEMORY "Eval harness is a placeholder" record
39. **Checkpoint:** open `scripts/run_eval.py` and `scripts/revise.py`; compare against `docs/eval-system.md` citations
    - [ ] The `docs/eval-system.md` line citations match the live files
40. **Checkpoint:** `ls docs/qrspi_*.md docs/qrspi-guide.md; grep -rn "qrspi_claude_code_guide\|qrspi_complete_guide\|qrspi_working_example\|qrspi_practical_application\|qrspi_quick_reference" .claude/ docs/`
    - [ ] The five `qrspi_*` guide files are gone; `docs/qrspi-guide.md` exists
    - [ ] No dangling links to the deleted files remain (or only the new guide's own provenance note)
41. **Checkpoint:** `grep -rn "Selected" docs/qrspi-pr-gated-lifecycle-design.md`
    - [ ] `Selected/Design Review/Plan Review/Code Review/Done` and the entry-gate wording survive verbatim in the canonical doc; restatements elsewhere are now pointers

---

## Slice 4: Collapse the four `/review-*` skills onto a shared loop reference

### Setup

42. ✨ Create `.claude/skills/review-design/references/shared-loop.md` (confirm this location at implementation; a shared location reachable by all three skills) — the single canonical deterministic-round-0 review loop reference that `review-design`, `review-plan`, and `review-implementation` will point at. Author it from the loop body currently restated across the three SKILL.md files, parameterized over the per-skill lens/phase wiring so each skill supplies only its distinct lens name and phase.

### Core Logic

43. ⚠️ Modify `.claude/skills/review-design/SKILL.md` — replace the restated round-0 loop body with a reference to the shared loop doc (step 42); keep the design-lens (`design-review`) and phase wiring intact. Do not alter the skill's triggering description.
    - **Current:** SKILL.md restates the deterministic-round-0 loop verbatim
    - **After:** SKILL.md references `references/shared-loop.md`; design-lens/phase wiring preserved
44. ⚠️ Modify `.claude/skills/review-plan/SKILL.md` — same collapse; reference the shared loop doc; preserve the plan-lens (`plan-review`) and phase wiring. Do not alter the triggering description.
    - **Current:** SKILL.md restates the round-0 loop verbatim
    - **After:** SKILL.md references the shared loop doc; plan-lens/phase wiring preserved
45. ⚠️ Modify `.claude/skills/review-implementation/SKILL.md` — same collapse; reference the shared loop doc; preserve the impl-lens (`impl-review`) and phase wiring. Do not alter the triggering description.
    - **Current:** SKILL.md restates the round-0 loop verbatim
    - **After:** SKILL.md references the shared loop doc; impl-lens/phase wiring preserved

### Verify Slice 4

46. **Checkpoint:** `grep -ln "shared-loop" .claude/skills/review-design/SKILL.md .claude/skills/review-plan/SKILL.md .claude/skills/review-implementation/SKILL.md`
    - [ ] Each of the three SKILL.md files references the shared loop doc and no longer restates the round-0 loop verbatim
    - [ ] Each skill's distinct lens name and phase (`design-review` / `plan-review` / `impl-review`) is preserved and correct
47. **Checkpoint:** manual read of the three `/review-*` SKILL.md `description:` fields
    - [ ] No `/review-*` skill's triggering description regressed (descriptions are load-bearing for auto-invocation)

---

## Rollback Notes

- **Steps 29–33 (guide-file deletions):** destructive. Before deleting, confirm `docs/qrspi-guide.md` (step 26) contains all kept content. To roll back, `git checkout HEAD -- docs/qrspi_claude_code_guide.md docs/qrspi_complete_guide.md docs/qrspi_working_example.md docs/qrspi_practical_application.md docs/qrspi_quick_reference.md` restores the deleted files; `git rm docs/qrspi-guide.md` (or `git checkout` if it pre-existed) reverses step 26.
- **Step 7 (qrspi-batch.js comment deletions):** if any deletion accidentally removed executable code, `git checkout HEAD -- .claude/workflows/qrspi-batch.js` reverts the whole file. The step-10 `git diff` + `run_tests.py` gate is the guard.
- **Steps 11–13, 19 (resolver verdict + doRevise):** behavioral. To roll back, `git checkout HEAD -- scripts/qrspi_resolve_state.py .claude/workflows/qrspi-batch.js` restores the prior bump/reset derivation. No DB or config migration is involved; `ciReviseCap` config key is unchanged.
- **Steps 34–37a (lifecycle dedup):** if an invariant was dropped, `git checkout HEAD -- .claude/CLAUDE.md .claude/skills/qrspi-work/SKILL.md docs/qrspi-orientation.md .claude/workflows/qrspi-batch.js` restores the restated narratives (step 37a re-homes the `qrspi-batch.js:887-917` lifecycle comment to the canonical doc — comment-only, so the step-21 `doRevise` read-through plus `python3 scripts/run_tests.py` confirm no executable change). The step-41 verbatim-invariant grep is the guard for the status invariants.
- No DB migrations and no destructive config changes are introduced by this plan.
