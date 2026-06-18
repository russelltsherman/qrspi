# Structure Outline — Upgrade the /review-* advisory review family

**Design basis:** design.md @ 2026-06-18T00:00:00Z
**Generated:** 2026-06-18T00:00:00Z
**Status:** draft

## New Types

- `ReviewConfig { phase: "design"|"plan"|"impl", maxRounds: int, lensModel: str|None, reviewLenses: list[str] }` — the per-phase on-demand review-panel config envelope emitted by the extended config resolver (consumed by the JS engine).
- `RoundVerdict { lens: str, pass: bool, findings: list[str], nonBlockingNotes: list[str]|None }` — one lens's verdict in the pre-reduction array (already implicit today; named here as the seam contract).
- `HeadlineVerdict { pass: bool, perLens: list[RoundVerdict] }` — the round-0 pre-reduction array pinned as the honest headline (AC2), independent of later rounds.
- `ProposedDiffAppendix { hasChanges: bool, diffText: str }` — the scratch-vs-original unified diff rendered as a labeled fix suggestion (AC2), never the verdict.
- `ReviewRunEnvelope { ticket, phase, headRefOid, reviewConfig: ReviewConfig, prNumber, reviewDecision }` — the resolve→engine seam the workflow consumes at run start (head SHA captured early for the propose-only bracket; `reviewDecision` carried so the engine's post-loop agreement step records `agree`/`disagree` after a human decides — AC6, RUS-93 plan PR change request, defect #1/#2). `prNumber`/`headRefOid`/`reviewDecision` are derived **per-phase** (NOT uniformly): design/plan resolve a single PR by branch (`gh pr list --head <id>/<phase> --state all`); impl rolls up to the **top slice** PR (`tip`/`slices[-1]`, `gh pr list --head <tip> --state all`) — dodging the partially-landed-stack misfire (RUS-93 plan PR change request, M1). The gh I/O lives in the engine; `build_review_envelope` is the pure shaper.

## Modified Types

- `SynopsisInput` — add per-lens finding **text** (currently only `_blocking_count`); add `headline: HeadlineVerdict` and `proposedDiff: ProposedDiffAppendix` (ref: design.md §Delta, AC1/AC2).
- `ReviewLedgerRecord` (from `qrspi_review_record.build_record`, the on-demand **review** ledger row — NOT the batch `qrspi_critic_metrics` row) — optionally carry per-lens finding text alongside `{lens, pass, findingsCount}` if AC1 ledger text is wanted (ref: design.md §Delta). The batch `qrspi_critic_metrics.build_record` is left untouched so the batch path cannot regress (RUS-93 plan PR change request, defect #3; Risk Register row 2).
- `AgreementInput` (to `qrspi_review_agreement.compute`) — **unchanged**; `compute` already returns `agree`/`disagree` when a present `reviewDecision` is supplied. The post-decision re-run path that supplies the present `reviewDecision` lives in the **engine** (Slice 4), not in this reducer (AC6) (RUS-93 plan PR change request, defect #2).

## Contracts

- `resolve_review_config(phase, raw_config) -> ReviewConfig` — per-phase resolver emitting `maxRounds` (default 2) and `lensModel` for design **and** plan **and** impl (extends today's design-only `resolve_design`); `scripts/qrspi_critics_config.py`.
- `render_synopsis(verdict_array, decision_readiness, terminal_action, *, headline: HeadlineVerdict | None = None, proposed_diff: ProposedDiffAppendix | None = None) -> str` — **backward-compatible** signature (RUS-93 plan PR change request, L1): the verdict array stays the first positional and `headline`/`proposed_diff` are optional keyword args, so the three live 3-arg SKILL callers keep working until Slice 5 (no orphaning window). Emits per-lens finding **text** plus a count header; headline pinned to round-0 (supplied `headline=` from the engine, or derived via `pin_headline(verdict_array)` when omitted); renders the design-phase `decision_readiness` section when present (`None` for plan/impl); appends the labeled proposed-diff appendix when `proposed_diff` is supplied; `scripts/qrspi_review_synopsis.py`. (`decision_readiness` retained to match `plan.md` and the design-phase decision-readiness lens — RUS-93 plan PR change request, Medium #2.)
- `pin_headline(pre_reduction_round0_array) -> HeadlineVerdict` — selects the round-0 verdict as the honest advisory headline (AC2); `scripts/qrspi_review_synopsis.py` (or a sibling helper).
- `diff_scratch_vs_original(original_path, scratch_path) -> ProposedDiffAppendix` — unified-diff the converged reviser copy against the original artifact for the fix-suggestion appendix (AC2).
- `compute(panel_pass, human_decision) -> "agree"|"disagree"|"pending"` — **unchanged** (already takes the decision as a parameter and reduces correctly); AC6's present-`reviewDecision` caller path is in the **engine** (Slice 4), not this reducer (`scripts/qrspi_review_agreement.py`) (RUS-93 plan PR change request, defect #2).
- `parse_review_envelope(jsonStr) -> ReviewRunEnvelope` and `parse_round_panel(jsonStr) -> list[RoundVerdict]` — pure JSON-seam parsers in the JS engine, each backed by `scripts/fixtures/contract_seam/<seam>/<variant>.json` goldens asserted on both producer (Python) and consumer (JS) sides (ref: Q15).
- `sha_unchanged(before: str, after: str) -> bool` — tested propose-only SHA-equality decision (`True` iff both non-empty SHAs are byte-identical; empty/`None` → `False`, fail-safe); `scripts/qrspi_review_sha.py`. The engine's terminal gate calls it (the JS keeps only the two `gh pr view --json headRefOid` reads + fail-loud abort) so the highest-stakes invariant is unit-covered (RUS-93 plan PR change request, M2).
- Engine entrypoint: `qrspi-review.js` invoked with `{ ticket, phase }` — performs resolve → **per-phase PR derivation** (design/plan by branch; impl top-slice `tip`, `--state all` — M1) → SHA capture → `reviewDecision` fetch → scratch-copy → round loop (fan-out lens Agents, threading `lensModel` into the `*-review` spawn; synthesize; next_action) → (design-only) post-loop decision-readiness lens → render → comment post → agreement compute + agreement-extended ledger append (`qrspi_review_record.build_record` → `ledger_row_fields` → `qrspi_metrics_append`) → `sha_unchanged` compare (propose-only terminal gate, M2).

## Slice 1: Honest synopsis rendering (AC1 + AC2 reporting layer)

**Goal:** The synopsis Python emits per-lens finding **text** (not just a count), pins the headline verdict to the round-0 pre-reduction array, and appends a labeled scratch-vs-original proposed-diff. Verifiable end-to-end purely in Python: feed a `cap_reached` panel fixture in, assert the rendered synopsis string contains the finding text, a round-0 headline, and a clearly-labeled fix-suggestion appendix that never reads as "passed."
**Files touched:**

- ⚠️ `scripts/qrspi_review_synopsis.py` — extend `render_synopsis` to emit finding text + count header; add `pin_headline` (round-0 headline) and `diff_scratch_vs_original` helpers (AC1, AC2 reporting).
- ⚠️ `scripts/qrspi_review_synopsis_test.py` — add cases: finding text appears for a `cap_reached` review; headline tracks round-0 not later rounds; proposed-diff appendix is present and labeled a suggestion.
- ⚠️ `scripts/qrspi_review_record.py` — (only if AC1 ledger text is wanted) carry per-lens finding text in the **review-ledger** `build_record` (retargeted off the batch `qrspi_critic_metrics` — RUS-93 plan PR change request, defect #3).
- ⚠️ `scripts/qrspi_review_record_test.py` — assert the review-ledger record carries finding text; regression-assert the batch `qrspi_critic_metrics.build_record` shape is unchanged.

**Verification:**
- [ ] `python3 scripts/run_tests.py synopsis` passes, including the new `cap_reached`-text and round-0-headline assertions.
- [ ] `python3 scripts/run_tests.py metrics` passes (if ledger text added).
**Context cost:** M
**Depends on:** none

## Slice 2: Per-phase review config + lensModel resolution (AC5 config layer)

**Goal:** Config resolution emits `maxRounds` (default 2) and `lensModel` for **all three** phases (design, plan, impl), normalizing plan/impl off their hardcoded 3 and exposing the today-unconsumed `lensModel` key for plan/impl which have no resolver. Verifiable in Python: resolve each phase from a raw config dict and assert the envelope's `maxRounds`/`lensModel`, including the default-2 normalization and the documented 3→2 behavior change. `DEFAULT_REVIEW_*_LENSES` stay strictly decoupled from `DEFAULT_DESIGN_LENSES` (do-NOT-recouple, ref: Q5).
**Files touched:**

- ⚠️ `scripts/qrspi_critics_config.py` — add `resolve_review_config(phase, raw_config)` (or extend the design-only path) emitting `maxRounds` default 2 + `lensModel` for design/plan/impl; keep batch `DEFAULT_DESIGN_LENSES` separate.
- ⚠️ `scripts/qrspi_critics_config_test.py` — assert per-phase `maxRounds` default 2, `lensModel` resolution for plan/impl, and the pinned default; assert batch lens sets unchanged.

**Verification:**
- [ ] `python3 scripts/run_tests.py critics_config` passes, pinning `maxRounds=2` per phase and `lensModel` for plan/impl.
- [ ] `python3 scripts/run_tests.py` passes (no batch critic regression from the shared-config touch).
**Context cost:** M
**Depends on:** none

## Slice 3: Document the AC6 re-run trigger (compute is already correct)

**Goal:** `compute(panel_pass, human_decision)` ALREADY returns `agree`/`disagree` when a present `reviewDecision` is supplied (it takes the decision as a parameter — RUS-93 plan PR change request, defect #2). The real AC6 work — re-fetching `reviewDecision` and re-appending the ledger row each run — lives in the **engine (Slice 4)**, not this pure reducer. This slice is reduced to a docstring note documenting the v1 trigger (OQ3 — manual `/review-<phase>` re-invocation). No new agreement tests (the proposed cases already exist verbatim: `qrspi_review_agreement_test.py:17,20,24,28,32`).
**Files touched:**

- ⚠️ `scripts/qrspi_review_agreement.py` — **docstring only** documenting the AC6 v1 trigger and that the engine owns the re-fetch/re-append; `compute` signature + behavior unchanged.

**Verification:**
- [ ] `python3 scripts/run_tests.py agreement` still passes UNCHANGED (non-functional docstring edit; existing `agree`/`disagree`/`pending` cases prove no regression).
**Context cost:** S
**Depends on:** none

## Slice 4: Deterministic review engine + contract-seam parsers (AC3 + AC4 + AC5 + AC6 wiring)

**Goal:** Replace the hand-executed markdown loop with `.claude/workflows/qrspi-review.js`, invoked by phase, that does resolve → head-SHA capture → **`reviewDecision` fetch (AC6)** → scratch-copy → round loop (fan-out lens Agents, threading the resolved `lensModel` into each phase's `*-review` lens spawn) → synthesize/next_action → **(design-only) post-loop decision-readiness lens** → render (using Slice 1 synopsis, with the design decision-readiness section) → comment post → **agreement compute + agreement-extended ledger append (`qrspi_review_record.build_record` → `ledger_row_fields` merge → `qrspi_metrics_append`)** → final head-SHA compare (propose-only terminal gate, fail loud on mismatch). The engine OWNS AC6 and the on-demand-review ledger row so Slice 5's thin-wrapper deletion does not orphan them (RUS-93 plan PR change request, defect #1); the design decision-readiness lens is wired so routing design through the engine does not lose its section (Medium #1). New pure JSON-seam parsers are each backed by two-sided contract-seam goldens (the `review_envelope` golden carries `reviewDecision`). Verifiable: the Python seam producers + JS parsers agree on the `scripts/fixtures/contract_seam/` goldens; a focused Python test covers the relocated agreement→build_record→append chain; and a manual end-to-end run confirms the synopsis posts (with the design decision-readiness section), a `mode:"on-demand-review"` ledger row is appended, the AC6 `agreement` flips after a human decision, and the PR head SHA is byte-identical before/after.
**Files touched:**

- ✨ `.claude/workflows/qrspi-review.js` — the deterministic review engine (meta-block + injected-globals shape mirroring `qrspi-batch.js`); resolve, SHA bracket, reviewDecision fetch, scratch loop, lensModel threading, design-only decision-readiness lens, render, comment post, agreement compute + ledger append.
- ✨ `scripts/fixtures/contract_seam/review_envelope/*.json` — goldens for the resolve→engine envelope seam.
- ✨ `scripts/fixtures/contract_seam/round_panel/*.json` — goldens for the panel/round verdict seam.
- ✨ `scripts/qrspi_review_seam_test.py` — Python side asserting the producers emit the goldens (JS side asserted in-engine against the same files, per Q15 pattern).
- ✨ `scripts/qrspi_review_sha.py` + `scripts/qrspi_review_sha_test.py` — the tested `sha_unchanged` propose-only decision helper extracted out of untestable JS (RUS-93 plan PR change request, M2).
- ⚠️ `.claude/agents/qrspi-design-critic-design-review.md` — wire the model seam the engine threads `lensModel` into; refresh the stale "Spawned by `runCriticPanelLoop`" note (Inconsistencies #2).
- ⚠️ `.claude/agents/qrspi-plan-critic-plan-review.md` — same model-seam wiring + stale-note refresh.
- ⚠️ `.claude/agents/qrspi-impl-critic-impl-review.md` — same model-seam wiring + stale-note refresh.

**Verification:**
- [ ] `python3 scripts/run_tests.py review_seam` passes; the engine's JS parsers assert against the identical goldens.
- [ ] Manual end-to-end: invoke the engine for one phase on a real ticket; the synopsis comment posts and the PR head SHA is unchanged (propose-only bracket holds).
**Context cost:** L
**Depends on:** Slice 1, Slice 2, Slice 3

## Slice 5: SKILLs to thin wrappers + remove /review + dereference (AC4 + AC7)

**Goal:** Reduce the three remaining per-stage SKILL.md files to thin wrappers over the Slice-4 engine (the duplicated loop prose deleted), delete `.claude/skills/review/` entirely, and remove every `/review` reference so none is orphaned. Verifiable: a repo-wide grep for `/review` (whole-stack command) and `runCriticPanelLoop` returns no stale hits, and the three SKILLs delegate to the engine rather than carrying the loop.
**Files touched:**

- ⚠️ `.claude/skills/review-design/SKILL.md` — thin wrapper over the engine; drop the "for the whole stack use /review" cross-link.
- ⚠️ `.claude/skills/review-plan/SKILL.md` — thin wrapper; drop the cross-link.
- ⚠️ `.claude/skills/review-implementation/SKILL.md` — thin wrapper; drop the cross-link.
- ⚠️ `.claude/skills/review/` (whole directory) — **delete** (AC7).
- ⚠️ `.claude/CLAUDE.md` — drop the `/review` blurb (line 129); refresh the three stale per-stage blurbs (126-128) to the engine/panel behavior.
- ⚠️ `docs/testing-dynamic-workflows.md` — remove the `/review` reference at lines 200-201.

**Verification:**
- [ ] Repo-wide grep finds no orphaned `/review` whole-stack reference and no `runCriticPanelLoop`/`runCoherenceCritic` mention in the three SKILLs.
- [ ] Manual: each of the three commands invokes the engine and posts a synopsis (no remaining hand-executed loop prose).
**Context cost:** M
**Depends on:** Slice 4

---

## Unverified Assumptions

- **OQ3 (AC6 trigger) — RESOLVED (owner, round-5, 2026-06-19): manual re-run satisfies AC6 (v1); auto-hook DROPPED.** The post-decision agreement re-run is a **manual `/review-<phase>` re-invocation**; the engine re-fetches/re-appends at steps 32/34a (built as-is in Slice 4, no new trigger step). The additive approve-path auto-hook is **explicitly deferred** (future ticket), not part of RUS-93. Accepted trade-off (Risk Register row 4): `agreement` reads `pending` in essentially every normal run — AC6 accepted as **mechanism-only**, correct when the re-run path is exercised.
- **Ledger finding-text (AC1 in the ledger) is optional in the design** ("if AC1 text is wanted in the ledger"). Slice 1 includes the **`qrspi_review_record`** edit conditionally (retargeted off the batch `qrspi_critic_metrics` — RUS-93 plan PR change request, defect #3); whether the ledger must carry text or only the synopsis must is unconfirmed.
- **Exact `lensModel` config key shape** (`critics.<phase>.lensModel`) and the "strongest configured model" value are described by example only; the concrete model identifier to default to is not pinned and the config-reader's single-top-level-key limitation (project memory: `qrspi_config.py` reads one top-level key, no dot-path) may require a specific nested-read mechanism the design does not specify. Needs the plan to nail the read mechanism.
- **The engine's exact lens fan-out / Agent-spawn interface** (how `qrspi-batch.js` injected globals expose `Agent` with a `model` parameter) is asserted to mirror `qrspi-batch.js` but the precise spawn signature for threading `lensModel` is not quoted in the design; Slice 4 assumes the `qrspi-batch.js` Agent shape carries a `model` field.
