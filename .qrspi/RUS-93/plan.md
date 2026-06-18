# Implementation Plan — Upgrade the /review-* advisory review family

**Structure basis:** structure.md @ 2026-06-18T00:00:00Z
**Generated:** 2026-06-18T00:00:00Z
**Status:** revised x3 (RUS-93 plan PR change requests — round 1: three blocking + two medium defects; round 2: the `panel_pass`/ledger-axes round-0 honesty blocking defect + round-0-vs-final-round inconsistency, plus the SKILL-orphaning window, AC5 seam re-location, config-namespace, and ledger finding-text index-zip advisories; round 3: per-phase PR-derivation contract for `build_review_envelope` (M1), a tested Python `sha_unchanged` helper for the propose-only bracket (M2), OQ3/AC6 owner-confirmation escalation (M3), a back-compatible `render_synopsis` signature to close the SKILL-orphaning window (L1), the `lensModel` fixed-token value space (L2), and a ledger-rounds pass-rate consumer check (L3))
**Total steps:** 47 numbered + 5 inserted lettered steps (5a Slice-1 SKILL round-0 render repoint, 33a engine decision-readiness lens, 34a engine agreement+ledger append, 34b tested `sha_unchanged` helper, 39a structure.md reconciliation)

**Round-5 owner decisions (RUS-93 plan PR, 2026-06-19 — two open questions answered):**
- 🟠 **AC6 trigger (Q1) → manual re-run, auto-hook DROPPED.** The owner accepts the **manual `/review-<phase>` re-run** as satisfying AC6 (v1); the additive approve-path auto-hook is **NOT built** (deferred to a future ticket). Slice 4 builds the steps 32/34a manual path as-is — no new trigger step. AC6 accepted as **mechanism-only**, with `agreement` reading `pending` in normal use (Risk Register row 4) understood and accepted. The "Owner Decision" section + the OQ3 bullet are flipped from open-gate to RESOLVED.
- 🟡 **Ledger finding-text (Q2) → KEPT.** Steps 5/9 (carry per-lens finding **text** on the on-demand **review** ledger row, `qrspi_review_record`) are now **firm**, not conditional. The batch `qrspi_critic_metrics` path stays untouched (step 9 regression assertion).

**Round-4 owner edits (RUS-93 plan PR, 2026-06-18 — applied directly by the owner during manual plan review):**
- 🟡 **Slice-1 SKILL round-0 render repoint (new step 5a) — closes the L1 gap:** L1's back-compat signature prevents the `decision_readiness → proposed_diff` argument mis-bind, but its *secondary* claim — that a hand-run `/review-*` mid-stack "renders a correct round-0 headline" — was **not delivered**, because the three live SKILLs feed `render_synopsis` the **final-round** pre-reduction array (`review-design/SKILL.md:249,263`; `review-plan/SKILL.md:185`), so `pin_headline(verdict_array)` would pin the headline to the *final* round (the exact AC2 masking case round-0 honesty exists to kill). New **step 5a** repoints the three SKILL render calls onto the **retained round-0** array during Slices 1–4, so the back-compat hand-run path is honest BEFORE Slice 5 rewrites the SKILLs into thin engine wrappers. The L1 text (step 4) now references 5a as the thing that makes the round-0 claim true.
- 🟠 **AC6 owner-gate reframed (honest framing) — the gate does NOT block building Slice 4:** the prior "BLOCKS Slice 4" heading overstated the constraint. The engine's manual-re-run path (steps 32/34a) is fully buildable now; the gate actually controls only (i) whether AC6 may be marked **done** on the manual path, and (ii) whether the **additive** auto-hook step is added. The reframe also records the honest practical reality (design Risk Register row 4): under the manual-re-run interpretation, `agreement` is `pending` in essentially every normal run, because nothing re-invokes `/review-<phase>` after a human decides — the *mechanism* is delivered but the *intent* (a usually-populated, meaningful agreement signal) is realized only by an auto-hook on the approve path. The owner decides which interpretation AC6 requires.

**Round-3 change-request fixes (RUS-93 plan PR, review @ 2026-06-18T23:39Z):**
- 🟠 **M1 — per-phase PR-derivation contract:** step 29 (`build_review_envelope`) now carries an explicit per-phase `prNumber` derivation contract — design/plan resolve a single PR by branch (`gh pr list --head <id>/<phase> --json number,reviewDecision,state --state all`), impl rolls up to the **top slice** PR (`tip`/`slices[-1]`, `gh pr list --head <tip> --state all`), dodging the partially-landed-stack misfire. Uniform `phase ∈ {design,plan,impl}` PR derivation is replaced by the per-phase contract the existing SKILLs already use (`review-design/SKILL.md:69`, `review-implementation/SKILL.md:62`).
- 🟠 **M2 — propose-only SHA bracket extracted to tested Python:** new step 34b adds `scripts/qrspi_review_sha.sha_unchanged(before, after) -> bool` (+ `_test.py`), and step 35 now calls it (the engine JS only captures the two SHAs + fail-louds on `False`), so the single most safety-critical invariant is unit-covered instead of living only in untestable JS.
- 🟠 **M3 — OQ3/AC6 escalated to owner confirmation, now RESOLVED (round-5):** the central acceptance question — does "manual `/review-<phase>` re-run only" satisfy AC6, or did the owner expect agreement captured automatically (e.g. on the approve path)? — was escalated to an **Owner Decision** gate (below). **Owner answer (2026-06-19): manual re-run satisfies AC6 (v1); the auto-hook is NOT built (deferred).** Slice 4 builds the steps 32/34a manual path as-is, no new trigger step; AC6 accepted as mechanism-only (`agreement` reads `pending` in normal use — Risk Register row 4).
- 🟡 **L1 — SKILL-orphaning window closed by a back-compatible signature:** step 4 keeps `render_synopsis`'s FIRST positional as the verdict array and adds `headline`/`proposed_diff` as **optional keyword args** (deriving the headline from the array via `pin_headline` when absent), so the three live 3-arg SKILL calls keep working until Slice 5 — the broken mid-stack window is eliminated, not merely caveated.
- 🟡 **L2 — `lensModel` value space pinned:** steps 13/L2 note `agent()`'s `model` accepts a fixed token set (`sonnet`/`opus`/`haiku`/`fable`), not arbitrary model ids; `resolve_review_config` validates `lensModel` against that set (unknown → `None` + warn) so a bad config value never silently no-ops the spawn.
- 🟡 **L3 — ledger-rounds pass-rate consumer check:** step 34a.2 gains an explicit confirmation that `qrspi_critic_summary.summarize` does not derive a misleading pass-rate from the accumulated N×R `rounds` (axes/agreement come from round-0, but the multi-round trace must not be read as the headline verdict by a downstream consumer).

**Round-2 change-request fixes (RUS-93 plan PR, review @ 2026-06-18T23:21Z):**
- 🔴 **BLOCKING — `panel_pass` source (AC2 honesty):** step 34a.1 now pins `panel_pass` to the round-0 headline verdict `pin_headline(round0)["pass"]`, NOT `(terminal_action == "converged")` — the agreement + ledger reflect the artifact as written, not the reviser-fixed scratch copy.
- 🔴 **round-0-vs-final-round inconsistency:** step 33's stale "final round for the synopsis axes" parenthetical reconciled — round-0 is the single source for the headline, synopsis axes, `panel_pass`, and ledger axes.
- 🟠 **ledger-axes asymmetry:** step 34a.3 `ledger_row_fields` now reads the round-0 array (was the final-round array).
- 🟡 SKILL-orphaning window acknowledged (step 4); AC5 model seam re-anchored to `agent()`'s `opts.model` at spawn, steps 37-39 made doc-only; config-namespace `critics.impl.*` vs `critics.implementation.*` flagged (step 11).
- ⚪ ledger finding-text index-zip mechanism specified (step 5); step 36 gains a round-0 honesty unit assertion.

## Owner Decision — AC6 trigger RESOLVED: manual re-run (M3 / OQ3 / AC6)

> **RESOLVED (owner, round-5, 2026-06-19) — Outcome 1: the manual `/review-<phase>` re-run satisfies AC6 (v1). No auto-hook.**
>
> **Decision.** AC6 is delivered by the **manual-re-run** path: the engine re-fetches the present
> `reviewDecision` each run (step 32) and re-appends the agreement-extended ledger row (step 34a), so a
> `/review-<phase>` re-invocation **after** a human decides records `agree`/`disagree` instead of
> `pending`. The **additive auto-hook is NOT built** — OQ3 is confirmed, not left open.
>
> **Accepted trade-off (eyes open).** Under this interpretation `agreement` reads `pending` in
> essentially every *normal* run, because nothing re-invokes `/review-<phase>` after the human decides
> (design Risk Register row 4). AC6 is accepted as **mechanism-only**: the signal is correct *when the
> re-run path is exercised*, and the owner accepts that it usually is not. An approve-path auto-hook is
> the only thing that would make agreement usually-populated; it is **explicitly deferred** (a future
> ticket if ever wanted), NOT part of RUS-93.
>
> **Build consequence.** Slice 4 builds the manual path exactly as steps 32/34a specify — **no extra
> step, no new trigger**. AC6 may be marked **done** on the manual path once the Slice-4 manual
> end-to-end (checkpoint 40) shows a post-decision re-run flips `agreement` from `pending` to
> `agree`/`disagree`. Do NOT build the auto-hook.

## Slice 1: Honest synopsis rendering (AC1 + AC2 reporting layer)

### Setup

1. ⚠️ Modify `scripts/qrspi_review_synopsis.py` — add a `HeadlineVerdict`-shaped helper `pin_headline(pre_reduction_round0_array) -> dict` that returns `{ "pass": bool, "perLens": [...] }`, selecting the round-0 pre-reduction verdict array as the honest advisory headline (AC2).
   - **Current:** no headline pinning; `render_synopsis(verdict_array, decision_readiness, terminal_action)` derives the body from the (possibly later-round) reduced verdict.
   - **After:** a `pin_headline` function exists that takes the round-0 pre-reduction array and returns a `HeadlineVerdict` dict `{pass, perLens:[{lens, pass, findings, nonBlockingNotes?}]}`.

2. ⚠️ Modify `scripts/qrspi_review_synopsis.py` — add `diff_scratch_vs_original(original_path, scratch_path) -> dict` returning a `ProposedDiffAppendix` `{ "hasChanges": bool, "diffText": str }` built from `difflib.unified_diff` of the original artifact vs the converged scratch copy (AC2).
   - **Current:** no scratch-vs-original diff surfacer exists.
   - **After:** `diff_scratch_vs_original` reads both files, returns `{hasChanges: False, diffText: ""}` when identical, else the unified diff text.

### Core Logic

3. ⚠️ Modify `scripts/qrspi_review_synopsis.py` — extend `render_synopsis` to emit per-lens finding **text** under each lens, with the existing `_blocking_count` retained as a count header line (AC1).
   - **Current:** `render_synopsis(verdict_array, decision_readiness, terminal_action)` emits only a PASS/FAIL label and `_blocking_count = len(findings)` per lens; finding text dropped.
   - **After:** each lens section lists its finding strings verbatim beneath a `N blocking finding(s)` header.

4. ⚠️ Modify `scripts/qrspi_review_synopsis.py` — extend `render_synopsis` to render the round-0 `HeadlineVerdict` as the headline and append the `ProposedDiffAppendix` as a clearly-labeled "Proposed fix (suggestion — NOT the verdict)" section (AC2), using a **backward-compatible signature** so the three live SKILL callers keep working until Slice 5 (L1).
   - **Current:** `render_synopsis(verdict_array, decision_readiness, terminal_action) -> str` — headline reflects reduced/late verdict; no diff appendix; body identical regardless of convergence except a trailing terminal-action line. The three live SKILLs call this 3-arg positional form (`review-design/SKILL.md:263`, `review-plan/SKILL.md:237`, `review-implementation/SKILL.md:241`).
   - **After (back-compatible, L1):** keep the **FIRST positional** as the verdict array and add the new fields as **optional keyword args**:
     `render_synopsis(verdict_array, decision_readiness, terminal_action, *, headline: HeadlineVerdict | None = None, proposed_diff: ProposedDiffAppendix | None = None) -> str`.
     - When `headline` is **omitted** (the live 3-arg SKILL call), derive it from the first positional via `pin_headline(verdict_array)`. **This is an honest round-0 headline ONLY if the SKILL passes the round-0 array as that first positional** — which the live SKILLs do NOT do today (they feed the **final-round** array, `review-design/SKILL.md:249,263`). New **step 5a** repoints the three SKILL render calls onto the retained round-0 array during Slices 1–4, so the hand-run mid-stack path is honest (no broken window) before Slice 5 rewrites the SKILLs.
     - When `headline` is **supplied** (the Slice-4 engine passes the explicit round-0 `HeadlineVerdict`), use it directly.
     - `proposed_diff` absent → no appendix (the SKILL path, which has no scratch diff); supplied → append the labeled fix-suggestion appendix that never reads as "passed".
   - **L1 — SKILL-orphaning window CLOSED (RUS-93 plan PR change request):** because the verdict array stays the first positional and the new fields are keyword-only with safe defaults, the three live 3-arg SKILL calls bind correctly throughout Slices 1–4 (no `decision_readiness → proposed_diff` mis-bind). The previous revision merely *caveated* the broken window ("don't hand-run mid-stack"); this revision **eliminates** it — the reviewers of this very stack are the people most likely to hand-run `/review-design`, so back-compat is worth the small extra cost. **Two distinct halves close the window:** the back-compat signature closes the *argument mis-bind* (no `decision_readiness → proposed_diff`), and **step 5a** (round-4) closes the *round-0 headline honesty* half — without 5a, the back-compat call would `pin_headline` the SKILL's **final-round** array and re-introduce the AC2 masking the headline fix exists to remove. Slice 5 still rewrites the SKILLs into thin engine wrappers, but correctness no longer depends on that ordering.

5. ⚠️ Modify `scripts/qrspi_review_record.py` — extend the **review-ledger** `build_record(phase, rounds, terminal_action, agreement)` so each per-lens rounds entry carries finding **text** alongside `findingsCount` (AC1 ledger text; **owner-confirmed KEPT, round-5 2026-06-19** — the design left it optional, the owner has decided the ledger row carries the text, so steps 5/9 are firm, not conditional).
   - **Reviewer correction (RUS-93 plan PR change request, defect #3):** the original step 5
     targeted `scripts/qrspi_critic_metrics.build_record(verdicts, terminalAction, usage, phase)`
     — the **batch** critic-metrics module (a different signature serving the batch panel), NOT
     the review ledger row. Adding finding text there never reaches the on-demand review ledger
     and risks the batch path the design explicitly protects (Risk Register row 2). The on-demand
     review ledger row is built by `qrspi_review_record.build_record(phase, rounds,
     terminal_action, agreement)` (`scripts/qrspi_review_record.py:48`), called from
     `review-plan/SKILL.md:200`. Retargeted here.
   - **Current:** `qrspi_review_record.build_record` forwards `rounds` to
     `qrspi_critic_metrics.build_record`, which reduces each round to `{lens, pass, findingsCount}`
     — the finding text is dropped at the ledger step.
   - **After:** `qrspi_review_record.build_record` carries a per-lens `findings: list[str]` field
     onto each rounds entry **after** the base reduction (additive — `qrspi_critic_summary.summarize`
     reads via `.get()` and is unaffected, and `qrspi_critic_metrics.build_record` is left
     UNTOUCHED so the batch path cannot regress). `findingsCount` retained for back-compat.
   - **Finding-text re-attachment mechanism (RUS-93 plan PR change request, ⚪ order nit):** re-attach
     the finding text onto the reduced rounds **by index against the input verdict list** — i.e.
     zip `reduced_rounds[i]` with `input_verdicts[i]`. This is cardinality-safe because
     `qrspi_critic_metrics.build_record` iterates the verdicts in order, one round/entry per input
     entry (`qrspi_critic_metrics.py:84-90`), so the reduction is order-preserving and the index-zip
     aligns each reduced entry with its source findings. State this explicitly so the implementer
     does not re-derive that the reduction preserves order.

5a. ⚠️ Modify the three on-demand SKILL render steps — `.claude/skills/review-design/SKILL.md` (Step 7, lines 249/263), `.claude/skills/review-plan/SKILL.md` (Step 7, ~line 237), and `.claude/skills/review-implementation/SKILL.md` (Step 7, ~line 241) — to feed `render_synopsis` the **retained round-0** pre-reduction per-lens verdict array as the **first positional**, NOT the final round's (round-4 owner edit — closes the L1 round-0-headline gap).
   - **Why (the L1 gap):** step 4 derives the headline via `pin_headline(verdict_array)` when the SKILL omits the `headline=` keyword. The live SKILLs pass the **final-round** array (`review-design/SKILL.md:249` — `last_round_verdicts = <the FINAL round's pre-reduction per-lens verdict array>`; `:263` passes it positionally; `review-plan/SKILL.md:185` derives `ledger_row_fields` from "the last round's pre-reduction verdict array"). So without this repoint a hand-run `/review-*` during Slices 1–4 would `pin_headline` the FINAL round → a PASS headline on a round-0 FAIL the reviser repaired in scratch — the exact AC2 masking the headline fix exists to kill, hitting precisely the reviewers most likely to hand-run this stack.
   - **Current:** the SKILL captures only the loop's final-round pre-reduction array and passes it to `render_synopsis` (and `ledger_row_fields`); the round-0 array is not retained across the loop.
   - **After:** each SKILL **retains the round-0 pre-reduction array** when the loop starts and feeds THAT array to `render_synopsis` as the first positional (so the axis table + the `pin_headline`-derived headline both reflect the artifact as written) AND to `ledger_row_fields` (so the SKILL-path ledger axes match — the same round-0 source the engine uses in step 34a.3). The proposed-diff appendix stays absent on the SKILL path (no scratch diff supplied), consistent with step 4.
   - **Supersession:** these are minimal prose repoints, not the Slice-5 rewrite. Slice 5 deletes this loop prose wholesale and replaces the SKILLs with thin engine wrappers (the engine then supplies the explicit round-0 `headline=`), so 5a is superseded by Slice 5 and the two do not conflict (Slice 1 lands first).
   - **Verify:** grep each SKILL Step 7 confirms the `render_synopsis(` / `ledger_row_fields(` first argument is the retained round-0 array variable (e.g. `round0_verdicts`), not `last_round_verdicts`. (The round-0-vs-later-round honesty itself is unit-pinned by step 7 in `qrspi_review_synopsis_test.py`; 5a only ensures the SKILL FEEDS round-0.)

### Tests

6. ⚠️ Modify `scripts/qrspi_review_synopsis_test.py` — add a case feeding a `cap_reached` panel fixture and asserting the rendered synopsis string contains each surviving lens's finding **text** (not just a count).

7. ⚠️ Modify `scripts/qrspi_review_synopsis_test.py` — add a case asserting the headline tracks the **round-0** verdict even when a later round passes (a round-0 FAIL with a later-round PASS still renders a FAIL headline).

8. ⚠️ Modify `scripts/qrspi_review_synopsis_test.py` — add a case asserting the proposed-diff appendix is present, contains the unified-diff text, and is labeled a suggestion (the string never reads as "the artifact passed").

9. ⚠️ Modify `scripts/qrspi_review_record_test.py` — add a case asserting the **review-ledger** record's per-lens rounds entries carry the `findings` text list (and `findingsCount` is still present). Targets `qrspi_review_record`, not the batch `qrspi_critic_metrics` (defect #3 retarget); add a regression assertion that `qrspi_critic_metrics.build_record`'s output shape is unchanged so the batch path is provably untouched.

### Verify Slice 1

10. **Checkpoint:** `python3 scripts/run_tests.py synopsis && python3 scripts/run_tests.py review_record && python3 scripts/run_tests.py metrics`
    - [ ] synopsis suite passes including `cap_reached`-text, round-0-headline, and labeled-appendix assertions
    - [ ] review_record suite passes including the ledger finding-text assertion (defect #3 retarget)
    - [ ] metrics suite still passes UNCHANGED — proves the batch `qrspi_critic_metrics` path was not touched
    - [ ] (step 5a) `grep -n 'render_synopsis\|ledger_row_fields' .claude/skills/review-{design,plan,implementation}/SKILL.md` shows each Step-7 first argument is the retained round-0 array (not `last_round_verdicts`)

---

## Slice 2: Per-phase review config + lensModel resolution (AC5 config layer)

### Setup

11. ⚠️ Modify `scripts/qrspi_critics_config.py` — confirm/establish the nested-config read mechanism for `critics.<phase>.maxRounds` and `critics.<phase>.lensModel`; add a private helper `_phase_critic_block(raw_config, phase) -> dict` that reads the `critics` top-level key then indexes `[phase]` (works around `qrspi_config.py` single-top-level-key limitation by reading the whole `critics` object once).
    - **Current:** only `resolve_design` reads `critics.design.*`; plan/impl have no resolver and `qrspi_config.py` reads one top-level key with no dot-path.
    - **After:** `_phase_critic_block` returns the per-phase sub-dict (`{}` when absent) for design/plan/impl from one `critics` read.
    - **Config-namespace note (RUS-93 plan PR change request, 🟡 namespace not called out):** the review config for the implementation phase resolves under **`critics.impl.*`** (this step + step 12), which is a **distinct key** from the batch implementation-coherence config at **`critics.implementation.*`** (read by `resolve_implementation`, `qrspi_critics_config.py:242` → `c.get("implementation")`). This is intentional — the decoupling intent keeps the on-demand review config separate from the batch coherence config — but an operator/reviewer will trip over `impl` vs `implementation`. Document this distinction in the helper docstring + the config example so it is not mistaken for a typo/bug. (Design's review config shares `critics.design.*` read-only with the batch `resolve_design`, which is the deliberate exception.)

### Core Logic

12. ⚠️ Modify `scripts/qrspi_critics_config.py` — add `resolve_review_config(phase, raw_config) -> ReviewConfig` emitting `{phase, maxRounds, lensModel, reviewLenses}` for `phase in {"design","plan","impl"}`, defaulting `maxRounds` to `2` (the existing `DEFAULT_MAX_ROUNDS`) when unset (AC5; OQ2 normalization).
    - **Current:** `resolve_design` emits `maxRounds` (default 2) + `lensModel` for design only; plan/impl hardcode 3 in SKILL prose.
    - **After:** `resolve_review_config` resolves all three phases from config; `maxRounds` default 2 for every phase (normalizes plan/impl 3→2).

13. ⚠️ Modify `scripts/qrspi_critics_config.py` — wire `lensModel` resolution for plan/impl via `resolve_review_config` reading `critics.<phase>.lensModel` (today-unconsumed for plan/impl), returning `None` when unset so the engine falls back to the session model (AC5).
    - **L2 — `lensModel` value space pinned (RUS-93 plan PR change request):** the engine threads `lensModel` through the Workflow `agent(prompt, {model})` hook, whose `model` accepts a **fixed token set** — `sonnet` / `opus` / `haiku` / `fable` — NOT arbitrary model ids. So `resolve_review_config` must **validate** the configured `lensModel` against that accepted set: a value in the set passes through; an unrecognized value resolves to `None` (session-model fallback) **with a warning** rather than being threaded verbatim (which would silently no-op the spawn / be rejected by the hook). Define the accepted-token constant alongside the resolver and assert it in step 16. This stops a typo'd or full-model-id config value from silently disabling the AC5 strong-model override.
    - **Current:** `lensModel` emitted only by `resolve_design`; plan/impl key unread; no value-space validation.
    - **After:** `resolve_review_config("plan"|"impl", cfg)` returns the configured `lensModel` (validated against `{sonnet,opus,haiku,fable}`) or `None`.

14. ⚠️ Modify `scripts/qrspi_critics_config.py` — select `reviewLenses` per phase from the existing `DEFAULT_REVIEW_DESIGN_LENSES` / `DEFAULT_REVIEW_PLAN_LENSES` / `DEFAULT_REVIEW_IMPL_LENSES` constants, keeping `DEFAULT_DESIGN_LENSES` (batch edge lenses) strictly **decoupled** (do-NOT-recouple, Q5; Risk Register row 2).
    - **Current:** the three `DEFAULT_REVIEW_*_LENSES` are read by no code; `DEFAULT_DESIGN_LENSES` is the batch set.
    - **After:** `resolve_review_config` returns the matching `DEFAULT_REVIEW_<PHASE>_LENSES`; the batch `DEFAULT_DESIGN_LENSES` is untouched and not referenced by the new path.

### Tests

15. ⚠️ Modify `scripts/qrspi_critics_config_test.py` — add cases asserting `resolve_review_config` returns `maxRounds == 2` by default for each of design/plan/impl, and honors an explicit `critics.<phase>.maxRounds` override.

16. ⚠️ Modify `scripts/qrspi_critics_config_test.py` — add cases asserting `lensModel` resolves for `plan` and `impl` (set to an accepted token → value, unset → `None`), **plus an L2 value-space case**: a `lensModel` outside the accepted `{sonnet,opus,haiku,fable}` token set (e.g. a full model id or a typo) resolves to `None` (session-model fallback), proving a bad config value cannot silently no-op the AC5 spawn.

17. ⚠️ Modify `scripts/qrspi_critics_config_test.py` — add a case asserting `reviewLenses` per phase equals the corresponding `DEFAULT_REVIEW_<PHASE>_LENSES`, and a regression case asserting `DEFAULT_DESIGN_LENSES` (batch set) is unchanged / not recoupled.

### Verify Slice 2

18. **Checkpoint:** `python3 scripts/run_tests.py critics_config && python3 scripts/run_tests.py`
    - [ ] critics_config suite passes pinning `maxRounds=2` per phase and `lensModel` for plan/impl
    - [ ] full suite passes (no batch critic regression from the shared-config touch)

---

## Slice 3: Post-decision agreement re-fetch + re-append in the engine (AC6)

> **Reviewer correction (RUS-93 plan PR change request, defect #2):** the original Slice 3
> rested on a false claim — `compute(panel_pass, human_decision)` does NOT read the PR
> `reviewDecision`; it takes the decision as a **parameter** (the SKILL fetches it at Step 2,
> `review-plan/SKILL.md:59-62`). So a `recompute_with_decision` wrapper adds nothing `compute`
> doesn't already do, and the proposed Slice-3 tests already exist verbatim
> (`qrspi_review_agreement_test.py:17,28,32`). The REAL AC6 work is not in `compute` at all — it
> is the **engine's re-fetch of `reviewDecision` on each run and re-append of the
> agreement-extended ledger row** so that a re-invocation **after** a human decides records
> `agree`/`disagree` instead of the structural `pending` of the no-decision-yet run. That work
> lives in the engine (Slice 4) and is specified here as the AC6 acceptance contract; the
> `compute` function and its tests are left UNCHANGED.

### Core Logic

19. ✅ **No code change to `scripts/qrspi_review_agreement.py`.** `compute(panel_pass, human_decision)`
    already returns `agree`/`disagree` when a present `reviewDecision` is supplied and `pending`
    only when it is absent/`COMMENTED` (verified: `qrspi_review_agreement.py:59-102`). The AC6 gap
    is **not** in this pure reducer — it is that the engine must *fetch* the current
    `reviewDecision` and *re-append* the ledger row on each run. That is implemented in Slice 4
    (engine steps 32a/34a/34b below) and documented as the AC6 contract in step 20.
    - **Current:** `compute` already takes the decision as a parameter and reduces correctly; the
      SKILL fetches `reviewDecision` via `gh pr view ... --json reviewDecision`
      (`review-plan/SKILL.md:54-62`) and passes it in at ledger-build time.
    - **After:** unchanged. The re-fetch/re-append behavior that makes AC6 observable across a
      post-decision re-invocation is owned by the engine (Slice 4), not this module.

20. ⚠️ Modify `scripts/qrspi_review_agreement.py` — **docstring only** (no signature/behavior
    change): add a note documenting the AC6 v1 trigger as a **manual `/review-<phase>`
    re-invocation after the human decides**, and that the engine (not this reducer) is responsible
    for re-fetching the present `reviewDecision` and re-appending the agreement-extended ledger row
    each run (OQ3 assumption; flagged Unverified below). This is the only edit in this slice.

### Tests

21. ✅ **No new agreement tests.** The `agree`/`disagree`/`pending` cases the original plan proposed
    already exist verbatim — `test_pass_approved_agrees` (`:17`), `test_fail_changes_requested_agrees`
    (`:20`), `test_pass_changes_requested_disagrees` (`:24`), `test_fail_approved_disagrees` (`:28`),
    `test_pass_none_is_pending` (`:32`). Adding them again would be duplicate dead weight. The AC6
    re-fetch/re-append behavior is exercised by the engine seam tests in Slice 4 (the
    `review_envelope` golden carries `reviewDecision`, asserted on both producer + consumer sides)
    and the Slice-4 manual end-to-end (re-run after a decision flips `agreement` from `pending` to
    `agree`/`disagree`).

### Verify Slice 3

22. **Checkpoint:** `python3 scripts/run_tests.py agreement`
    - [ ] agreement suite still passes UNCHANGED (the docstring edit is non-functional; the existing
          `agree`/`disagree`/`pending` cases continue to pass — proves no regression).

---

## Slice 4: Deterministic review engine + contract-seam parsers (AC3 + AC4 + AC5 + AC6 wiring)

> Depends on: Slice 1, Slice 2, Slice 3.
> **Owns AC6** (per defect #1/#2): the engine fetches `reviewDecision` (step 32), computes
> agreement, and re-appends the agreement-extended ledger row (step 34a). Slice 3 contributes
> only the docstring + the unchanged pure `compute`.

### Setup

25. ✨ Create `scripts/fixtures/contract_seam/review_envelope/valid.json` — golden for the resolve→engine `ReviewRunEnvelope` seam `{ ticket, phase, headRefOid, reviewConfig: {phase, maxRounds, lensModel, reviewLenses}, prNumber, reviewDecision }`. The `reviewDecision` field carries the human's current PR decision (or `null` pre-decision) so the engine's AC6 agreement step (34a) records `agree`/`disagree` after a human decides (defect #1/#2).

26. ✨ Create `scripts/fixtures/contract_seam/review_envelope/null_lensmodel.json` — golden variant with `reviewConfig.lensModel: null` (session-model fallback path).

27. ✨ Create `scripts/fixtures/contract_seam/round_panel/pass.json` — golden for the `parse_round_panel` seam: a pre-reduction `[RoundVerdict]` array with all `pass: true`.

28. ✨ Create `scripts/fixtures/contract_seam/round_panel/findings.json` — golden variant: a `[RoundVerdict]` array with `pass: false` and non-empty `findings` (the `cap_reached`-shape input).

### Core Logic

29. ✨ Create `scripts/qrspi_review_seam.py` — the Python producers for the two seams: `build_review_envelope(...) -> dict` (emitting `{ticket, phase, headRefOid, reviewConfig, prNumber, reviewDecision}`, the `reviewDecision` carried for AC6) and `serialize_round_panel(verdicts) -> str`, emitting exactly the golden shapes (the tested producer side of Q15).
    - **M1 — per-phase `prNumber`/`headRefOid` derivation contract (RUS-93 plan PR change request):** the original step assumed `prNumber` was "already known" and treated `phase ∈ {design,plan,impl}` **uniformly** for PR derivation. It is not uniform — the impl phase is a stack of N slice PRs and rolls the synopsis up to the **top slice** PR (and that is exactly where the partially-landed-stack landmine lives). `build_review_envelope` MUST carry an explicit per-phase derivation contract, mirroring what the existing SKILLs already do:
      - **design / plan:** resolve the single phase PR by branch name —
        `gh pr list --head <ticket-id>/<phase> --state all --json number,reviewDecision,state --jq '.[0]'`
        (`--state all` dodges the partially-landed misfire; branch-name based, yields `number` **and** `reviewDecision` in one call — `review-design/SKILL.md:69`). `headRefOid` from `gh pr view <number> --json headRefOid`.
      - **impl:** the synopsis goes to the **top slice** PR. Take the tip branch from the resolve envelope's `tip` (equivalently `slices[-1]`; if `slices` is empty there is no implementation — fail loud), then
        `gh pr list --head <tip> --state all --json number,reviewDecision,state --jq '.[0]'`
        (`--state all` is mandatory here — lower slices may already be merged while the top slice PR is open/merged — `review-implementation/SKILL.md:62`). `headRefOid` from the top slice PR.
      - The function takes the already-resolved `prNumber`, `reviewDecision`, and `headRefOid` from this per-phase derivation as inputs (the gh calls live in the JS engine's resolve head, step 32) and is itself the **pure** shaper of the envelope — keeping the I/O in the engine and the shape in tested Python. State the per-phase derivation explicitly so the implementer does not treat impl like design/plan and misfire on the slice stack.

30. ✨ Create `.claude/workflows/qrspi-review.js` — the deterministic review engine (meta-block + injected-globals shape mirroring `qrspi-batch.js`), invoked with `{ ticket, phase }`; scaffold the meta block, injected-globals destructure, and the top-level `run` entry. Full run sequence (built across steps 32-35): resolve → SHA capture → reviewDecision fetch → scratch-copy → round loop → (design-only) decision-readiness lens → render+post → **agreement compute + ledger append** → final SHA compare.

31. ⚠️ Modify `.claude/workflows/qrspi-review.js` — add pure JSON-seam parsers `parse_review_envelope(jsonStr) -> ReviewRunEnvelope` and `parse_round_panel(jsonStr) -> list[RoundVerdict]`, with no I/O (Functional-Core seam, Q15).
    - **Current:** file does not exist (new in step 30).
    - **After:** two pure parsers present, each returning the typed shape from a JSON string.

32. ⚠️ Modify `.claude/workflows/qrspi-review.js` — implement the run sequence head: resolve (call `resolve_review_config` via the python shell) → **derive the phase PR per the step-29 per-phase contract** (design/plan: `gh pr list --head <id>/<phase> --state all`; impl: top-slice `tip`/`slices[-1]`, `gh pr list --head <tip> --state all`) yielding `prNumber` + `reviewDecision` in one call → capture `headRefOid` early via `gh pr view <prNumber> --json headRefOid` (propose-only bracket open) → pass `prNumber`/`reviewDecision`/`headRefOid` into the pure `build_review_envelope` (step 29) → **the fetched `reviewDecision`** feeds the post-loop agreement step so it records `agree`/`disagree` after a human decides (AC6 re-fetch; defect #1/#2 — this is the engine half of AC6 the SKILL did via `gh` at its Step 2) → scratch-copy the artifact to `/tmp/phase-stage/<id>/review/`. The branch-name → PR resolution and the I/O live here in the engine; the envelope **shape** is the tested Python `build_review_envelope`.
    - **M1 (RUS-93 plan PR change request):** the impl branch is `tip` (`slices[-1]`), NOT `<id>/impl` — do not treat impl like design/plan. An empty `slices` list means no implementation to review: fail loud (mirrors `review-implementation/SKILL.md:44`).
    - **Current:** scaffold-only `run` (step 30).
    - **After:** run performs resolve → per-phase PR derivation (`prNumber` + `reviewDecision`) → SHA capture → `build_review_envelope` → scratch-copy in order.

33. ⚠️ Modify `.claude/workflows/qrspi-review.js` — implement the round loop `0..maxRounds-1`: fan-out the resolved `reviewLenses` as lens `Agent`s, threading the resolved `lensModel` into each `*-review` spawn's `model` parameter (AC5); assemble verdicts, pipe through `partition_decision_readiness` → `synthesize` → `next_action`. **Keep the full pre-reduction per-lens verdict array for every round** — and **the round-0 pre-reduction array is the single source for the headline, the synopsis axes, the `panel_pass` (step 34a.1), AND the ledger axes (step 34a.3)** (artifact as written, AC2). Also **accumulate the per-lens rounds entries** (N lenses × R rounds) — these feed the ledger `build_record` in step 34a (the accumulated rounds give the multi-round observability; the headline/axes/panel_pass do NOT come from the final round).
    - **Reviewer correction (RUS-93 plan PR change request, 🔴 round-0-vs-final-round inconsistency):** the original parenthetical here read "the final round for the synopsis axes + ledger rounds," but step 4 (`render_synopsis` derives its headline/axes from the round-0 `HeadlineVerdict` — supplied via the `headline=` keyword by the engine, or `pin_headline(verdict_array)` of the first positional — never a final-round axes argument), step 34 (passes the explicit round-0 `HeadlineVerdict`), and step 34a (panel_pass + ledger axes from round-0) all source the headline/axes from round-0. The "final round for the synopsis axes" wording was stale/wrong and contradicted AC2 (design.md:25 — axes reflect the artifact as written). Reconciled: round-0 is the source for the headline, synopsis axes, panel_pass, and ledger axes; only the accumulated per-lens **rounds** list (the multi-round trace) spans all rounds.
    - **Current:** run stops after scratch-copy (step 32).
    - **After:** the round loop fans out lenses with `lensModel` threaded, computes the terminal action, and retains the round-0 array (the headline/axes/panel_pass source) + the accumulated per-lens rounds list (the multi-round trace).

33a. ⚠️ Modify `.claude/workflows/qrspi-review.js` — **design phase ONLY:** after the loop terminates, spawn the post-loop `qrspi-design-critic-decision-readiness` lens once (it is partitioned OUT of `synthesize` so it never drives a revise round — design.md:20, Q13), and capture its `decision_readiness` verdict so step 34 can render its section. For `plan`/`impl`, `decision_readiness` is `None` (the plan/impl panels carry no such lens; `partition_decision_readiness` returns `(panel, None)` as a harmless guard).
    - **Reviewer correction (RUS-93 plan PR change request, Medium #1):** routing design through the
      engine must NOT lose the design-only decision-readiness lens that the design phase runs
      post-loop and renders as its own section (design.md:20). The original Slice 4 mentioned only
      the `partition_decision_readiness` guard, never spawning the lens or rendering its section.
    - **Current:** the engine round loop computes only the panel terminal action (step 33).
    - **After:** the design phase additionally runs the decision-readiness lens post-loop and threads
      its verdict into the render (step 34); plan/impl pass `None`.

34. ⚠️ Modify `.claude/workflows/qrspi-review.js` — render the synopsis via the Slice-1 `render_synopsis`, passing the round-0 pre-reduction array as the first positional, `decision_readiness` (the design-phase verdict from step 33a or `None`) and the loop's terminal action positionally, and the explicit round-0 `HeadlineVerdict` from `pin_headline(<round-0 array>)` + the `ProposedDiffAppendix` from `diff_scratch_vs_original` as the **keyword args** (`headline=`, `proposed_diff=`) of the back-compatible signature (step 4, L1). Then post ONE comment to the resolved PR.
    - **Current:** loop computes terminal action but does not render/post (step 33).
    - **After:** the engine renders the honest synopsis (including the design decision-readiness section when present) and posts the comment.

34a. ⚠️ Modify `.claude/workflows/qrspi-review.js` — **after the comment post, build and append the agreement-extended ledger row** (defect #1 — this is the central gap the original plan dropped; it is the engine home for the work the SKILL did at `review-plan/SKILL.md:177-220`). In order, via the python shell:
    1. `agreement = qrspi_review_agreement.compute(panel_pass, reviewDecision)` where **`panel_pass` is the round-0 headline verdict — `pin_headline(<round-0 pre-reduction array>)["pass"]`, the SAME source the synopsis headline uses (step 34)** — and `reviewDecision` is the value fetched in step 32 (so a post-decision re-run records `agree`/`disagree`, AC6).
       - **Reviewer correction (RUS-93 plan PR change request, BLOCKING — panel_pass source):** `panel_pass` MUST NOT be `(terminal_action == "converged")`. `terminal_action == "converged"` is `True` whenever any round passes — including the exact masking case AC2 exists to kill: round-0 FAIL → reviser repairs the *scratch* copy → round-1 passes → `converged`. Porting `panel_pass = converged` (the old `review-plan/SKILL.md:183,193` logic) into the engine would record `pass` in the ledger and compute agreement against a "pass" the artifact-as-written never earned (a human `CHANGES_REQUESTED` agreeing with the honest round-0 FAIL would be mis-recorded as `disagree`). Design AC2 (design.md:25) is explicit: "the panel verdict and **agreement** reflect the artifact **as written**." So `panel_pass` is pinned to the **round-0 reduced verdict** (`pin_headline(round0)["pass"]`), NOT `terminal_action`.
    2. `record = qrspi_review_record.build_record(phase=<phase>, rounds=<accumulated per-lens rounds from step 33>, terminal_action=<terminal>, agreement=agreement)`.
       - **L3 — ledger-rounds pass-rate consumer check (RUS-93 plan PR change request):** the `rounds` here is the accumulated N×R multi-round trace, so it contains a later-round PASS even when round-0 (the headline/axes/`panel_pass`) is a FAIL. Before relying on this, **confirm no downstream consumer derives a misleading headline/pass-rate from `rounds`** — specifically `qrspi_critic_summary.summarize`: verify it reads `rounds` only as the per-round trace (observability) and does NOT compute the panel verdict / a pass-rate from it (the headline verdict and agreement come from round-0 via `pin_headline`/`panel_pass`, step 34a.1). If a consumer *does* derive a pass signal from `rounds`, it must read the round-0 entry, not the max/last round, or it would re-introduce the exact AC2 dishonesty the headline fix removed. Add a Slice-4 (step 36) assertion that the ledger record's `panel_pass`/agreement reflect round-0 even though `rounds` carries a later PASS, so the trace-vs-headline distinction is regression-pinned.
    3. `record.update(qrspi_review_synopsis.ledger_row_fields(<round-0 pre-reduction array>))` — merge the additive axis / nonBlockingNotes fields, **sourced from the SAME round-0 array as the headline and `panel_pass`** so the ledger axes reflect the artifact as written, not the post-reviser-convergence final round. (Reviewer correction, RUS-93 plan PR change request, 🟠 ledger-axes asymmetry: the original `ledger_row_fields(<final-round pre-reduction array>)` made the ledger's axes reflect post-reviser convergence while the synopsis headline reflected round-0 — the ledger would be the dishonest record the synopsis was fixed to avoid being. Both the synopsis axes AND the ledger axes now derive from round-0 for AC2 consistency.)
    4. `python3 scripts/qrspi_metrics_append.py --ticket <id> --run-id "review-<phase>-<id>-<UTC>" --record <record-json>` — the appended line carries `mode: "on-demand-review"`, `phase`, and the `agreement` block. If `qrspi_metrics_append.py` returns `ok:false`, **fail loud** (do not invent a verdict).
    - **Reviewer correction (RUS-93 plan PR change request, defect #1):** without these explicit
      engine steps, Slice 5's deletion of the SKILL loop prose leaves AC6 (agreement) and the
      `mode:"on-demand-review"` ledger row with no home — they vanish. These steps relocate that
      exact post-loop work into the engine.
    - **Current:** the engine renders/posts but never computes agreement, builds the review-ledger record, or appends it (the no-engine-ledger gap).
    - **After:** the engine computes `compute` → `build_record` → `ledger_row_fields` merge → `qrspi_metrics_append`, with `panel_pass` AND the ledger axes both pinned to round-0 (artifact as written), preserving AC6 + AC2 + the on-demand-review ledger row after the SKILLs become thin wrappers.

34b. ✨ Create `scripts/qrspi_review_sha.py` (+ `scripts/qrspi_review_sha_test.py`) — extract the propose-only SHA-equality **decision** into a tiny tested Python helper `sha_unchanged(before: str, after: str) -> bool` (returns `True` iff the two non-empty head SHAs are byte-identical; an empty/`None` either side → `False`, i.e. fail-safe toward "changed"/abort). The engine's terminal gate (step 35) calls it and fail-louds on `False`.
    - **Reviewer correction (RUS-93 plan PR change request, M2):** the propose-only SHA bracket is the single most safety-critical invariant in the whole engine, yet the original plan left the equality compare **inline in untestable JS** (`qrspi-review.js`, not covered by `run_tests.py`), guarded only by manual end-to-end. The repo convention pushes every decision into tested Python — this highest-stakes one was the lone exception. Extracting `sha_unchanged` gives it a regression test so a future engine edit cannot silently break propose-only. The JS keeps only the I/O (the two `gh pr view --json headRefOid` reads) + the fail-loud abort; the **decision** is the tested Python.
    - **Tests:** equal non-empty SHAs → `True`; differing → `False`; empty/`None` before or after → `False` (fail-safe); whitespace-trimmed compare so a trailing newline from `gh ... --jq` does not spuriously flip it.
    - **Current:** the SHA equality lives inline in JS (step 35), untested.
    - **After:** `sha_unchanged` is a tested pure helper; the engine calls it.

35. ⚠️ Modify `.claude/workflows/qrspi-review.js` — re-read `headRefOid` after the comment post + ledger append and call `qrspi_review_sha.sha_unchanged(before, after)` (step 34b) to compare it with the early capture; **fail loud** when it returns `False` (propose-only terminal gate, Risk Register row 1). (The ledger append writes only the local metrics file, never the PR branch — the SHA bracket still holds.)
    - **M2 (RUS-93 plan PR change request):** the equality **decision** is the tested Python `sha_unchanged` (step 34b) — the JS only performs the two `gh pr view --json headRefOid` reads and the fail-loud abort, so the safety-critical invariant has a regression test instead of living solely in untestable JS.
    - **Current:** no final SHA compare (steps 32/34).
    - **After:** the run's terminal gate calls the tested `sha_unchanged` and aborts on mismatch.

### Tests

36. ✨ Create `scripts/qrspi_review_seam_test.py` — assert `build_review_envelope` emits both `review_envelope` goldens (including the `reviewDecision` field, present + `null` variants — the AC6 carrier) and `serialize_round_panel` emits both `round_panel` goldens (Python producer side); document that the engine's JS parsers assert against the identical files (consumer side, Q15). Also add a focused test of the engine's ledger-append composition done in pure Python — `panel_pass = pin_headline(<round-0 array>)["pass"]` → `qrspi_review_agreement.compute(panel_pass, reviewDecision)` → `qrspi_review_record.build_record` → `qrspi_review_synopsis.ledger_row_fields(<round-0 array>)` merge produces a record whose `agreement` flips `pending`→`agree`/`disagree` when `reviewDecision` is present — so defect #1's relocated post-loop chain is unit-covered, not only manually checked.
    - **Round-0 honesty assertion (RUS-93 plan PR change request, BLOCKING — panel_pass source):** add a case feeding the masking shape — a **round-0 FAIL** array with a **later round-1 PASS** (`terminal_action == "converged"`) and `reviewDecision = "CHANGES_REQUESTED"` — and assert (a) `panel_pass` derived from `pin_headline(round0)["pass"]` is `False` (NOT the `converged`-derived `True`); (b) the resulting `agreement` is `agree` (human CHANGES_REQUESTED agrees with the honest round-0 FAIL), NOT the `disagree` a `terminal_action`-sourced `panel_pass` would have produced; and (c) the merged `ledger_row_fields` axes come from the round-0 array (the FAIL axes), not the round-1 PASS axes. This pins the AC2 honesty invariant — the agreement + ledger reflect the artifact as written — at the unit layer.

37. ⚠️ Modify `.claude/agents/qrspi-design-critic-design-review.md` — refresh the stale "Spawned by `runCriticPanelLoop`" note to reference the `qrspi-review.js` engine (Inconsistencies #2). **Doc-only:** the `lensModel` override is threaded at **spawn time** by the engine via `agent(prompt, { agentType, model: lensModel })` (step 33), NOT by frontmatter/`.md` wiring — the lens `.md` carries no model field. So this step is the stale-note refresh; it adds no executable model wiring.
    - **Reviewer correction (RUS-93 plan PR change request, 🟡 AC5 seam mis-located):** the original step said "wire the model seam the engine threads `lensModel` into (the `model` spawn parameter)" in the `.md`, implying a `.md`-level binding. `qrspi-batch.js` spawns via `agent(prompt, { label, phase, agentType })` (qrspi-batch.js:517) and threads model through the Workflow `agent()` hook's `opts.model` — there is no `Agent(` global or `model:` frontmatter field in the `.md`. The real override is `agent(..., { agentType, model: lensModel })` in the engine (step 33); these agent-`.md` edits are purely the stale-`runCriticPanelLoop`-note refresh.

38. ⚠️ Modify `.claude/agents/qrspi-plan-critic-plan-review.md` — same stale-note refresh to the engine (doc-only; the model override is threaded at spawn via `agent(..., { agentType, model: lensModel })` in step 33, not in the `.md`).

39. ⚠️ Modify `.claude/agents/qrspi-impl-critic-impl-review.md` — same stale-note refresh to the engine (doc-only; model override threaded at spawn per step 33, not in the `.md`).

39a. ✅ **Plan-phase artifact reconciliation (Medium #2, done in round 2):** `structure.md:24`
    originally dropped `decision_readiness` from the `render_synopsis` Contract signature while
    `plan.md:28` kept it. The plan is correct — the design phase needs the decision-readiness
    argument (step 33a/34) — so `structure.md` was reconciled to keep `decision_readiness`. In
    round 3 (L1) the signature became **backward-compatible** —
    `render_synopsis(verdict_array, decision_readiness, terminal_action, *, headline=None, proposed_diff=None)`
    — which still carries `decision_readiness` as a positional, so the round-2 reconciliation holds;
    `structure.md:24` has been updated to the back-compatible form to stay in sync with `plan.md`
    step 4. No implementation action; the artifacts agree.

### Verify Slice 4

40. **Checkpoint:** `python3 scripts/run_tests.py review_seam && python3 scripts/run_tests.py review_sha`
    - [ ] review_seam suite passes; the engine's JS parsers assert against the identical `scripts/fixtures/contract_seam/` goldens; the ledger-append composition test passes
    - [ ] review_sha suite passes — `sha_unchanged` returns `True` on equal SHAs, `False` on differing/empty (M2 propose-only decision is unit-covered)
    - [ ] Manual end-to-end (design phase): invoke `qrspi-review.js phase:design` on a real ticket; the synopsis comment posts **with a decision-readiness section** (Medium #1), a `mode:"on-demand-review"` ledger row is appended (defect #1), and `gh pr view --json headRefOid` is byte-identical before/after (propose-only bracket holds)
    - [ ] Manual end-to-end (AC6 flip): re-invoke the engine **after** a human posts a PR review; the newly-appended ledger row's `agreement` shows `agree`/`disagree` (not `pending`), confirming the engine's `reviewDecision` re-fetch + re-append (defect #1/#2)

---

## Slice 5: SKILLs to thin wrappers + remove /review + dereference (AC4 + AC7)

> Depends on: Slice 4.

### Core Logic

> **Precondition (defect #1):** the SKILLs' post-loop work — agreement compute,
> `qrspi_review_record.build_record`, `ledger_row_fields` merge, `qrspi_metrics_append`, and (for
> design) the decision-readiness lens + section — must ALREADY be relocated into the engine
> (Slice 4 steps 33a/34/34a) before this slice deletes the prose. The loop prose is **moved, not
> dropped**: thinning the SKILLs is safe only because the engine now owns that behavior.

41. ⚠️ Modify `.claude/skills/review-design/SKILL.md` — reduce to a thin wrapper that invokes the `qrspi-review.js` engine with `phase: "design"` (delete the duplicated loop prose, **now that the engine owns the round loop + decision-readiness lens + agreement/ledger post-loop work**); drop the "for the whole stack use /review" cross-link from the description.

42. ⚠️ Modify `.claude/skills/review-plan/SKILL.md` — thin wrapper invoking the engine with `phase: "plan"`; drop the cross-link.

43. ⚠️ Modify `.claude/skills/review-implementation/SKILL.md` — thin wrapper invoking the engine with `phase: "impl"`; drop the cross-link.

44. ⚠️ Delete `.claude/skills/review/` (whole directory) — remove the whole-stack `/review` command entirely (AC7).
    - **Current:** `.claude/skills/review/SKILL.md` (and any siblings) define the `/review` whole-stack command.
    - **After:** the directory no longer exists.

45. ⚠️ Modify `.claude/CLAUDE.md` — delete the `/review` blurb (line 129) and refresh the three stale per-stage blurbs (lines 126-128) to describe the engine/panel behavior (round-0 headline + proposed-diff appendix + per-phase `lensModel`).

46. ⚠️ Modify `docs/testing-dynamic-workflows.md` — remove the `/review` reference at lines 200-201.

### Verify Slice 5

47. **Checkpoint:** `grep -rn "/review\b" .claude docs ; grep -rn "runCriticPanelLoop\|runCoherenceCritic" .claude/skills`
    - [ ] no orphaned `/review` whole-stack reference remains in `.claude` or `docs`
    - [ ] the three remaining SKILLs contain no `runCriticPanelLoop`/`runCoherenceCritic` mention and no hand-executed loop prose
    - [ ] Manual: each of the three `/review-*` commands invokes the engine and posts a synopsis

---

## Rollback Notes

- **Step 44 (delete `.claude/skills/review/`):** destructive directory removal. To reverse, restore the directory from git history (`gt`/git checkout of the prior commit's `.claude/skills/review/` path). Confirm no remaining reference re-introduced by steps 45-46 before deleting.
- **Steps 25-28 (new fixture files):** additive; rollback is deletion of the new `scripts/fixtures/contract_seam/review_envelope/` and `round_panel/` JSON files.
- **Steps 12-14 (config `maxRounds` 3→2 normalization for plan/impl):** behavior change — plan/impl review now caps at 2 rounds instead of 3. To restore the old cap, set `critics.plan.maxRounds`/`critics.impl.maxRounds` to `3` in `.qrspi/config.json` (no code rollback needed; the default is config-overridable).
- **Steps 37-39 (lens agent model-seam wiring):** if a configured `lensModel` is unavailable, set `critics.<phase>.lensModel` unset/`null` to fall back to the session model (step 13 path); no code rollback needed.
- **Steps 33a/34a (engine decision-readiness lens + agreement/ledger append):** these are pure additions to the new `qrspi-review.js` (the file does not exist before Slice 4), so rollback is reverting the engine to the render+post-only sequence. If the relocated post-loop chain regresses, the prior behavior lived in the SKILL prose (still present until Slice 5) — do NOT delete the SKILL loop prose (Slice 5) until the engine's ledger append + AC6 + design decision-readiness section are verified by the Slice-4 manual end-to-end (checkpoint 40).

---

## Unverified Assumptions

- **OQ3 (AC6 re-run trigger) — RESOLVED (owner, round-5, 2026-06-19): manual re-run satisfies AC6 (v1); no auto-hook.** The v1 trigger **is** a **manual `/review-<phase>` re-invocation** after the human decides; the engine re-fetches `reviewDecision` (step 32) and re-appends the agreement-extended ledger row (step 34a) — that path is built as-is in Slice 4 with **no extra trigger step**. The additive auto-hook is **explicitly deferred** (future ticket if ever wanted), NOT part of RUS-93. Accepted trade-off (eyes open): `agreement` reads `pending` in essentially every normal run (design Risk Register row 4) — AC6 is accepted as **mechanism-only**, correct when the re-run path is exercised. (Per defect #2: `compute` was never the gap — the engine re-fetch/re-append is; per M3 the *trigger* was the acceptance question, now answered.)
- **`lensModel` config key shape / value space / default:** steps 11-13 assume the nested `critics.<phase>.lensModel` shape read via a whole-`critics`-object read (`_phase_critic_block`), and that the concrete strongest model is operator-supplied (default `None` → session model). Per L2 (RUS-93 plan PR change request) the **value space is now pinned** to the `agent()` hook's accepted token set `{sonnet,opus,haiku,fable}` (validated by `resolve_review_config`, unknown → `None`+warn) — it is NOT an arbitrary model id. What remains operator-supplied is *which* of those tokens to default to for the "strongest configured model" (the design does not pin one); the accepted set itself is no longer unverified.
- **Agent spawn `model` parameter shape + value space:** the `lensModel` override is threaded via the Workflow `agent(prompt, opts)` hook's **`opts.model`** at spawn time (step 33), not via an injected `Agent` global or any `.md` frontmatter field. `qrspi-batch.js` spawns with `agent(prompt, { label, phase, agentType })` (qrspi-batch.js:517) and does not itself thread a model, so the exact `opts.model` plumbing is verified against the `agent()` hook during Slice 4 (RUS-93 plan PR change request, 🟡 AC5 seam re-location: re-anchored from "qrspi-batch.js-style injected Agent exposes a model field" to "`agent()` accepts `opts.model`"). Steps 37-39 are therefore doc-only stale-note refreshes, not frontmatter model wiring. **Per L2 (round 3):** `opts.model` accepts a **fixed token set** `{sonnet,opus,haiku,fable}`, not arbitrary model ids — `resolve_review_config` validates `lensModel` against that set (step 13) so a config value outside it falls back to `None` rather than silently no-opping the spawn.
- **Decision-readiness lens spawn (step 33a):** the design-only post-loop `qrspi-design-critic-decision-readiness` lens is assumed to be spawnable from the engine the same way the SKILL spawns it today (an `Agent` call with the lens's named PATH inputs); verify the exact contract against the current design SKILL prose during Slice 4.
- **Ledger finding-text (step 5) — RESOLVED (owner, round-5, 2026-06-19): KEPT.** The design marked it optional ("if AC1 text is wanted in the ledger"); the owner has decided the on-demand **review** ledger row carries the finding text, so steps 5/9 are **firm** (retargeted to `qrspi_review_record`, defect #3). The batch `qrspi_critic_metrics.build_record` stays untouched (step 9 regression assertion), so the batch path cannot regress.
