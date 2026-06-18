# Design — Upgrade the /review-* advisory review family

**Ticket:** RUS-93
**Research basis:** research.md @ /workspaces/qrspi/.worktrees/RUS-93/.qrspi/RUS-93/research.md
**Generated:** 2026-06-18T00:00:00Z
**Status:** draft

## Current State

The on-demand `/review-*` family is four `SKILL.md` prose procedures (`/review-design`, `/review-plan`, `/review-implementation`, `/review`) hand-executed by the main agent; there is no `.js` orchestrator for it today, and the autonomous batch's former in-pipeline critic glue (`runCriticPanelLoop`/`runCoherenceCritic`) no longer exists (ref: scope note). Each run resolves the PR, scratch-copies the artifact to `/tmp/phase-stage/<id>/review/` via a literal `cp` in the SKILL, then loops rounds `0..MAX-1`: the model fans out N lens `Agent`s, hand-assembles their `{lens, pass, findings, nonBlockingNotes?}` verdicts into a pre-reduction array, pipes it through `partition_decision_readiness()` then `synthesize()` to a reduced `{pass, findings}`, then through `qrspi_critic_loop.next_action` for the terminal action (ref: Q1, Q3).

`synthesize(verdicts)` AND-reduces to one `{pass, findings}` carrying the full deduped finding **text**, fail-closed on empty input; it does not model severity (ref: Q2). `next_action(verdicts, round, max_rounds)` is stateless — the model tracks the round index — returning `converged` on a passing latest verdict, `cap_reached` at the bound, else `revise` carrying `residual_findings` text (ref: Q9). On `revise` the shared `qrspi-critic-reviser` (phase-parameterized) reads the scratch copy plus upstream inputs and `RESIDUAL_FINDINGS`, and writes **only** the scratch copy — never a tracked file or branch (ref: Q3).

The single largest defect: `render_synopsis(verdict_array, decision_readiness, terminal_action)` emits only a PASS/FAIL label and `_blocking_count = len(findings)` per lens — the finding **text is dropped at the synopsis step**, even on a `cap_reached` review where surviving findings exist; the body is identical regardless of convergence except a trailing terminal-action line (ref: Q1, Q4, Q10). The ledger's `qrspi_critic_metrics.build_record` likewise reduces each round to `{lens, pass, findingsCount}` (ref: Q4). `synthesize` and `next_action` carry text; `render_synopsis`/`ledger_row_fields`/`build_record` carry counts; `compute` and the config resolver carry no finding detail (ref: Q4).

The advisory signal is dishonest in two ways. First, the loop converges by having the reviser fix a **throwaway scratch copy**, so "converged" can mean "the reviser repaired a copy," not "the original artifact was sound" (ref: ticket AC2; the reviser writes only the scratch path, ref: Q3). Second, `qrspi_review_agreement.compute(panel_pass, human_decision)` reads the PR's `reviewDecision`, but the advisory review almost always runs **before** any human decision exists, so `gh` returns `null`/`COMMENTED` and agreement is structurally always `pending` — a timing artifact, not a missing code path (ref: Q8).

The node-validity `*-review` lens is the panel's hardest reasoning but runs under the inherited **session model**: `lensModel` is a documented-but-unwired seam — `resolve_design` recognizes and emits the config key but nothing consumes it, and the lens agent frontmatter carries no model field (ref: Q6). The MAX-rounds cap is inconsistent: `/review-design` reads it from config (`critics.design.maxRounds`, default 2) while plan/impl/`/review` hardcode 3 (ref: Q9, Inconsistencies #1).

Panel constants live in `qrspi_critics_config.py`: `DEFAULT_DESIGN_LENSES` (4 batch edge lenses, `design-review` default-OFF) is deliberately decoupled from the on-demand `DEFAULT_REVIEW_DESIGN_LENSES` (5, including `design-review`), `DEFAULT_REVIEW_PLAN_LENSES`, `DEFAULT_REVIEW_IMPL_LENSES` — the latter three are referenced only narratively in SKILL prose, read by no code (ref: Q5). The propose-only invariant is a two-point hand-executed assertion: capture `headRefOid` early, re-read and compare after the comment post; no helper mediates it (ref: Q11). The design-only decision-readiness lens runs once post-loop, partitioned out of `synthesize` so it never drives a revise round; plan/impl call `partition_decision_readiness()` as a harmless guard returning `(panel, None)` (ref: Q13). `/review` references live in `.claude/CLAUDE.md` "Available skills" (lines 126-129, the three per-stage blurbs also stale vs RUS-91), each of the four SKILL `description` cross-links, and `docs/testing-dynamic-workflows.md:200-201`; `qrspi-work/references/review-cascade.md` does **not** reference the family (ref: Q12, Inconsistencies #3, #4). Workflow scripts follow Functional Core / Imperative Shell: deterministic logic lives in tested `scripts/*.py`, the JS keeps only pure JSON parsers covered by contract-seam fixtures asserted on both sides (`scripts/fixtures/contract_seam/<seam>/<variant>.json`); `run_tests.py` auto-discovers every `_test.py` as a subprocess and is the CI gate (ref: Q14, Q15).

## Desired End State

- **AC1 — Findings visible.** The posted synopsis renders the actual blocking finding **text** per lens, not only a count. On a non-converged review the reviewer reads the specific problems from the comment. Realized by extending `render_synopsis` (and the SKILL render steps) to emit each lens's finding strings, with a count retained as a header.
- **AC2 — Honest panel signal.** The advisory review no longer conflates "converged after the reviser fixed a scratch copy" with "the original artifact was sound." Realized by reporting **round-0 panel findings verbatim** and treating the round-0 panel verdict as the headline advisory verdict; the panel verdict and agreement reflect the artifact **as written**. The revise loop is **retained as a configurable multi-pass engine** (per-phase `critics.<phase>.maxRounds`), but it is **demoted to producing a surfaced proposed-diff appendix** — "here is how the reviser would fix it," derived by diffing the converged scratch copy against the original — and it **never** overrides the round-0 headline verdict. Convergence of the scratch copy is reported as a *fix suggestion*, not as the artifact passing. (Owner decision 2026-06-18: multi-pass engine, not single-pass.)
- **AC3 — Deterministic orchestration.** The hand-executed markdown loop is replaced by a deterministic orchestrator (a `.claude/workflows` review engine the three commands invoke) so the loop is testable and cheaper. The propose-only invariant (no branch mutation; head SHA byte-identical) is preserved in the new orchestrator via the early-capture / final-compare bracket.
- **AC4 — Single source of truth.** The loop procedure duplicated across the three per-stage SKILL files lives in one shared place (the engine plus the existing Python helpers); a loop change is made once. The three SKILLs become thin wrappers.
- **AC5 — Adversarial lens has teeth.** The node-validity `*-review` lens runs under the strongest configured model via a wired `lensModel` seam threaded from the config envelope into the lens `Agent` spawn's model parameter — not silently the session model. This applies to **all three** phases: `design-review`, `plan-review`, and `impl-review` (owner decision 2026-06-18 — wire `lensModel` for all phases, not design-only). Since only `resolve_design` emits `lensModel` today, the config resolution is extended so the plan and impl review panels resolve the same `lensModel` key (e.g. `critics.<phase>.lensModel`), and the engine threads it into each phase's `*-review` lens spawn.
- **AC6 — Meaningful agreement.** Agreement is captured/recomputed at a point where a human `reviewDecision` actually exists — a **post-decision re-run path** that reads the now-present `reviewDecision` and records `agree`/`disagree` rather than structural `pending`.
- **AC7 — Remove `/review`.** `.claude/skills/review/` is deleted along with every reference: the `.claude/CLAUDE.md` "Available skills" entry, the `/review-*` cross-links in the three remaining SKILL descriptions, and `docs/testing-dynamic-workflows.md`. No orphaned `/review` reference remains. (`review-cascade.md` needs no edit — it never referenced the family, ref: Q12.)

## Delta

- **Delete:** `.claude/skills/review/` (whole directory). **Edit:** `.claude/CLAUDE.md` (drop the `/review` blurb at line 129, refresh the three stale per-stage blurbs at 126-128 to the panel behavior); the three SKILL `description` frontmatters (drop the "for the whole stack use /review" cross-link); `docs/testing-dynamic-workflows.md:200-201` reference.
- **New file:** a `.claude/workflows/` review engine script (e.g. `qrspi-review.js`) implementing the deterministic loop (resolve → SHA capture → scratch-copy → round loop fan-out/synthesize/next_action → render → comment post → SHA compare), invoked by the three commands with a `phase` argument. Follows `qrspi-batch.js`'s meta-block + injected-globals shape (ref: Q15).
- **New JSON-envelope parser(s)** in the engine for the panel/round seam, each covered by new `scripts/fixtures/contract_seam/<seam>/<variant>.json` goldens asserted on both the Python producer and JS consumer sides (ref: Q15).
- **Modify `scripts/qrspi_review_synopsis.py`:** `render_synopsis` (and `ledger_row_fields` if AC1 text is wanted in the ledger) to emit per-lens finding text; add a `_test.py` case asserting the text appears for a `cap_reached` review.
- **Modify `scripts/qrspi_critics_config.py`:** make the `lensModel` resolution reachable by the engine and **extend resolution to the plan and impl review panels** (AC5 spans all three phases — owner decision). Today only `resolve_design` emits `lensModel`; the plan/impl on-demand panels have no config resolver at all (their lenses are narrative-only in SKILL prose), so this adds a per-phase review-config resolution path that emits `lensModel` (and `maxRounds`) for `plan`/`impl` alongside `design`. Also normalize the MAX-rounds source so all three phases resolve from config, default `2` (fixes Inconsistencies #1). Each new resolution path ships `_test.py` coverage.
- **Modify the three node-validity lens agents** (`qrspi-{design,plan,impl}-critic-*-review.md`): wire a model seam the engine threads `lensModel` into; update the stale "Spawned by `runCriticPanelLoop`" note (Inconsistencies #2).
- **New / modified Python for AC2 and AC6:** (a) a round-0-verbatim headline path in the synopsis layer (pin the headline verdict to the round-0 pre-reduction array, independent of later rounds), **and** (b) a scratch-vs-original diff surfacer that renders the converged reviser copy as a proposed-diff appendix (clearly labeled a fix suggestion, never the verdict), **and** (c) a post-decision agreement re-run path that reads `reviewDecision` when present. Each ships a `_test.py` sibling auto-discovered by `run_tests.py`.
- **Reduce the three SKILL.md** to thin wrappers over the engine (AC4).

## Pattern Decisions

### Decision 1: Orchestration substrate for the loop (AC3/AC4)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | A single shared `.claude/workflows/qrspi-review.js` engine the three commands invoke with a `phase` arg | One source of truth (AC4); mirrors `qrspi-batch.js` Functional-Core/Imperative-Shell; `log()` run-trace available; loop logic testable via Python helpers + contract fixtures | New JS surface; JS itself stays harness-coupled / not unit-testable in isolation (ref: Q15) |
| B | Keep SKILL prose but factor the shared loop into a referenced procedure file | Smaller change; no new JS | Still hand-executed and non-deterministic (fails AC3); "single place" is prose, not tested code |

**Recommendation:** Option A
**Rationale:** AC3 explicitly demands a deterministic orchestrator and the ticket's own slice sketch names a `.claude/workflows` script. The repo's law is Functional Core / Imperative Shell — push every decision into tested `scripts/*.py`, keep the JS as a thin shell with pure parsers covered by contract-seam fixtures (ref: Q15, Discovered Patterns). Option A is the only one satisfying AC3 and AC4 together.
**NEW PATTERN?** No — it extends the established `qrspi-batch.js` workflow + contract-fixture pattern to a second orchestrator.

### Decision 2: How to make the panel signal honest (AC2)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Drop the revise loop for advisory mode; report round-0 panel findings verbatim as the verdict | Verdict = artifact as written (exactly AC2); simplest; removes the scratch-fix-masks-defect confusion entirely | Loses the reviser's "here is a fix" value-add |
| B | Keep a configurable multi-pass loop but surface the reviser's proposed change as a concrete diff appendix; headline verdict stays round-0 | Preserves fix suggestions; verdict still honest; retains the existing loop/`next_action`/reviser/scratch-copy machinery (smaller delta to AC3's engine) | More moving parts; must diff scratch vs original and render it |

**Recommendation:** Option B (owner decision 2026-06-18 — multi-pass engine, not single-pass)
**Rationale:** AC2 offers both as acceptable, and the owner has chosen to **keep the engine multi-pass and configurable** rather than collapse it to a single round. Honesty is preserved by *what is reported*, not by removing the loop: the **round-0 panel verdict on the artifact as written is the headline**, and the loop's product (the converged scratch copy) is rendered only as a **proposed-diff appendix** — a fix suggestion that never reads as "the artifact passed." This keeps the largest source of misleading signal closed (Q8/Q10 count-only + scratch-fix) while retaining the reviser's value-add and leaving the existing loop / `next_action` / scratch-copy machinery in place for the AC3 port to wrap. Round-count is config-driven per phase (see OQ2).
**NEW PATTERN?** No — it reuses the existing pre-reduction array, loop, and `render_synopsis`; it adds a scratch-vs-original diff renderer and pins the headline to round 0.

### Decision 3: Wiring the `lensModel` seam (AC5)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Engine reads resolved `lensModel` from the config envelope and passes it as the `model` parameter on the node-validity lens `Agent` spawn | Uses the already-resolved (today unconsumed) config key (ref: Q6); per-lens, no frontmatter coupling | Requires the engine (Decision 1) to exist first |
| B | Add a `model:` frontmatter key to the lens agent definitions | Declarative, local to the agent | Static — cannot be overridden by config; the agent docs explicitly note the seam is config-threaded, not frontmatter |

**Recommendation:** Option A, applied to **all three** `*-review` lenses
**Rationale:** The seam was deliberately designed as a config→spawn thread; `resolve_design` already emits `lensModel` and the lens doc records the intent as config-wired, not frontmatter (ref: Q6). Option A consumes the existing dead config key and keeps model choice operator-controllable. Per the owner decision (OQ4), it is wired for `design-review`, `plan-review`, **and** `impl-review` — which requires extending config resolution to the plan/impl review panels (they have no resolver today; see Delta).
**NEW PATTERN?** No — it completes a documented, partially-built seam; extending the same resolution shape to plan/impl is mechanical, not a new pattern.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Propose-only invariant regressed by the new orchestrator (a branch write slips in) | low | high | Keep the head-SHA early-capture / final-compare bracket inside the engine (ref: Q11); reviser still writes only the scratch path; assert SHA unchanged as the run's terminal gate and fail loud on mismatch |
| Batch critic panels regress when shared helpers/config are touched | med | high | Keep `DEFAULT_REVIEW_*_LENSES` strictly separate from `DEFAULT_DESIGN_LENSES` (do-NOT-recouple note, ref: Q5); run `python3 scripts/run_tests.py` (the CI gate) and exercise batch end-to-end (ref: ticket constraint, Q14) |
| New JS engine is not unit-testable in isolation, hiding orchestration bugs | med | med | Push all decisions into tested Python helpers; cover every new JS parser with two-sided contract-seam fixtures; verify the engine end-to-end manually (ref: Q15, eval-harness-placeholder) |
| AC6 post-decision re-run path rarely exercised, so agreement stays `pending` in practice | med | low | Document the re-run trigger explicitly; ship `compute` tests proving `agree`/`disagree` once a decision exists (ref: Q8) — structural correctness even if usage is occasional |
| Normalizing the MAX-rounds cap silently changes design (2→3) or plan/impl (3→2) behavior | low | med | Choose one config-driven default deliberately and pin it in tests; call out the change so reviewers expect it (ref: Q9, Inconsistencies #1) |

## Open Questions

- OQ1: **RESOLVED (owner, 2026-06-18) — Option B.** Keep a **configurable multi-pass** engine (not single-pass): the round-0 panel verdict is the honest headline (artifact as written), and the reviser's converged scratch copy is surfaced as a **proposed-diff appendix** in v1. The loop / `next_action` / reviser / scratch-copy all remain (consistent with the AC3/Delta engine description).
- OQ2: **RESOLVED — all three phases become config-driven under `critics.<phase>.maxRounds`, default `2`** (the existing `DEFAULT_MAX_ROUNDS`), normalizing plan/impl off their hardcoded 3. Pin the chosen default in tests and call out the plan/impl 3→2 behavior change for reviewers (ref: Risk Register row 5).
- OQ3: For AC6, what concretely triggers the post-decision re-run — a manual re-invocation of `/review-<phase>` after the human decides, or an automatic hook? (Affects whether agreement is ever non-`pending` in normal use.)
- OQ4: **RESOLVED (owner, 2026-06-18) — all three phases.** `lensModel` wiring extends to the `plan-review` and `impl-review` lenses, not design-only. Because only `resolve_design` emits the key today and the plan/impl review panels have no config resolver, this requires adding a per-phase review-config resolution path (emitting `lensModel` + `maxRounds` for `plan`/`impl`) so the engine can thread the strongest model into each phase's `*-review` spawn (ref: Q6, Delta).
