# Design — Upgrade the /review-* advisory review family

**Ticket:** RUS-93
**Research basis:** research.md @ 2026-06-19T00:00:00Z
**Generated:** 2026-06-19T00:00:00Z
**Status:** draft

## Current State

The on-demand `/review-*` family is three `SKILL.md` procedures (~270–306 lines each), hand-executed by the main agent, which fans out `Agent` lenses and pipes JSON between `python3` heredocs (ref: Q4). The control flow itself is prose; determinism lives only in tested pure Python helpers (ref: Q3). The retired batch critic loops (`runCriticPanelLoop`/`runCoherenceCritic`) no longer exist in `qrspi-batch.js`; these three SKILLs are the only surviving callers of the helpers (ref: scope note, Q4).

Each run: resolve via `qrspi_resolve.py` → derive PR → scratch-copy the artifact to `/tmp/phase-stage/<id>/review/<artifact>.md` (ref: Q7) → loop rounds `0..MAX-1` (fan out panel → `synthesize` AND-reduce → `next_action` converge/revise/cap; on revise the shared `qrspi-critic-reviser` rewrites the **scratch** copy in place) (ref: Q2) → (design only) a post-loop decision-readiness lens (ref: Q15) → append a `mode:"on-demand-review"` ledger row (ref: Q6) → render + post the synopsis comment → assert PR head SHA unchanged (ref: Q10).

Key facts behind the six evaluation weaknesses:

- **Finding text is dropped at the render boundary.** `synthesize` preserves and dedupes blocking finding text and `next_action` hands it to the reviser, but `render_synopsis` emits only a per-lens `PASS|FAIL` + integer count — the actual finding strings never reach the comment body. `nonBlockingNotes` text IS rendered, making the omission conspicuous (ref: Q1, Inconsistencies).
- **The signal is dishonest on revise.** The panel is fed the scratch copy every round; round `r>0` reads the reviser-mutated copy. The synopsis and ledger are fed only the FINAL round's pre-reduction array, so a `cap_reached`/`converged` verdict reflects the most-revised scratch, not the artifact as written. No code retains round-0 as a distinct "as-written" datum for the synopsis (ref: Q2).
- **Orchestration is prose.** The loop is an LLM-driven step sequence duplicated across three SKILLs, not a tested function (ref: Q2, Q4).
- **`lensModel` is a dead seam.** `qrspi_critics_config.resolve_design` resolves an optional `critics.design.lensModel` string into the design envelope, and the three `*-review` agents document an Opus-tier intent — but nothing consumes the resolved key and the SKILLs spawn lenses with no `model` override, so the lens silently inherits the session model (ref: Q5, Inconsistencies).

Helpers fail closed (never raise) except `build_record`, which raises `ValueError` on a non-terminal `terminalAction` (ref: Q3, Q9). The JS sandbox cannot run python: every `python3` call is a literal command STRING inside a worker prompt; bare-relative script paths are prefixed via `engineCmdFor(r, rel)` for worker-cwd, scratch/staging uses `stg()`'s `/tmp/phase-stage/<id>/`, and every worker prompt re-provisions the worktree (ref: Q4). The propose-only invariant is procedural: head SHA captured in Step 2, re-asserted in the final step; a PR comment never moves the head, so a failed comment write does not trip the assertion (ref: Q10). Batch lens constants (`DEFAULT_DESIGN_LENSES`) and on-demand constants (`DEFAULT_REVIEW_*_LENSES`) are separate, with explicit "do NOT couple" comments; only `resolve_design` reads the batch set, and the on-demand tuples are declarative names the SKILLs reference (ref: Q11). Test coverage is per-file `_test.py` siblings run by `run_tests.py` as subprocesses; the JS↔Python seam is covered by committed contract fixtures driven through `contract_seam_runner.js` (ref: Q12, Q13). No event-log/observability infrastructure exists; logging is free-text `log()` plus the per-run JSONL ledger row — there is no event convention to "follow" (ref: Q14, Inconsistencies).

## Desired End State

Mapping each acceptance criterion (AC #6 dropped per the ticket's 2026-06-19 scope change) to concrete behavior:

- **AC #1 — Findings visible.** `render_synopsis` emits, per failing lens, the actual blocking finding TEXT (not just a count), so a non-converged review's comment lets the reviewer read the specific problems. The text already reaches the renderer's input array via `_verdict(..., findings=[str])` (ref: Q12) — only the render and its SKILL heredoc step change.
- **AC #2 — Honest panel signal.** The advisory review reports the artifact **as written**. We adopt the ticket's first option: **drop the revise loop for advisory mode** — run the panel exactly once (round 0) against the unmutated scratch copy and report round-0 findings verbatim. The panel verdict reflects the original artifact; no reviser mutation can launder a FAIL into a converged PASS (ref: Q2, AC #2).
- **AC #3 — Deterministic orchestration.** A single deterministic orchestrator (a `.claude/workflows` review engine) replaces the hand-executed markdown loop for all three commands, preserving the propose-only invariant: the head-SHA capture/assert moves into the orchestrator and no `gt`/`gh` branch write is ever issued (ref: Q4, Q10, AC #3).
- **AC #4 — Single source of truth.** The orchestration logic lives in one shared place (the workflow engine + a pure Python decision helper); the three SKILLs become thin wrappers parameterized by phase. A loop/render change is made once (ref: Q4, AC #4).
- **AC #5 — Adversarial lens has teeth.** The node-validity `*-review` lens runs under the strongest configured model via a wired `lensModel` seam: the resolved `lensModel` from `qrspi_critics_config` is read and passed as the `model` override when the orchestrator spawns the `*-review` lens, instead of silently inheriting the session model (ref: Q5, AC #5).

Non-regression: batch behavior is untouched (`DEFAULT_DESIGN_LENSES`/`resolve_design` unchanged); the `DEFAULT_REVIEW_*` constants and the decoupling comments remain (ref: Q11, Constraints).

## Delta

**Modified — `scripts/qrspi_review_synopsis.py`:** `render_synopsis` (and the per-lens table render at lines 140–147) gains a per-failing-lens finding-text block. Keep the existing `PASS|FAIL|count` row; add, beneath each FAIL row (or as a "Blocking findings" sub-section per lens), the deduped finding strings. `ledger_row_fields`/`partition_decision_readiness` signatures unchanged (additive render only) (ref: Q1, Q12).

**Modified — `scripts/qrspi_review_synopsis_test.py`:** add assertions that blocking finding strings surface in the rendered body (fixtures already carry `findings=[...]`; today no test asserts text appears) (ref: Q12).

**New — `.claude/workflows/qrspi-review.js`** (or equivalent shared engine): a deterministic orchestrator that, given `{ticket, phase}`, resolves the worktree/PR (`qrspi_resolve.py`), scratch-copies the artifact, captures the head SHA, fans the phase's `DEFAULT_REVIEW_*` lenses out via `agent(...)` (passing the `lensModel` override to the `*-review` lens), runs `synthesize` **once** (round 0, no revise), runs the design-only **post-panel** decision-readiness lens, calls `render_synopsis`, posts the comment via `qrspi_comment_reply.py`, appends the ledger row via `qrspi_metrics_append.py`, and re-asserts the head SHA. Matches batch patterns: `engineCmdFor(r,rel)`, `stg()`, mandatory `provisionStep`, python-as-command-string (ref: Q4, Q7, Q10).

The no-revise **terminal action is a binary pick computed inline in the engine** — `converged` on a round-0 pass, else `exhausted` — and passed to `qrspi_review_record.build_record`. Both values are already in `VALID_TERMINAL_ACTIONS`; `revise` is non-terminal and correctly rejected by `build_record`. No new decision module is introduced (see Decision 1 / OQ2 — a single binary choice does not warrant a helper). The ledger row's required `agreement` positional is passed an **empty agreement block** (`{}`) — former AC #6 is dropped, so no re-run path populates it and `qrspi_review_agreement.compute` is not invoked (ref: Q3, Q6, Q9).

**Modified — `scripts/qrspi_critics_config.py`:** add a **single on-demand read path** for the `*-review` lens model, sourced from a NEW on-demand key **`critics.review.lensModel`** (not `critics.design.lensModel`) and applied symmetrically across all three phases. This is deliberately SEPARATE from `resolve_design`: `resolve_design`/`DEFAULT_DESIGN_LENSES` and the batch `critics.design.*` envelope are left **untouched**, so on-demand model selection does not couple to the batch design config (which only ever resolved `lensModel` for the design phase and has no plan/impl equivalent). A small `resolve_review_lens_model(cfg)` reader (stdlib-only, `_test.py` sibling) returns the configured id or `None`; the engine passes it as the `model` override only on the `*-review` spawn (ref: Q5, Q11; resolves OQ3).

**Modified — three `*-review` agent defs** (`qrspi-{design,plan,impl}-critic-*-review.md`): replace the "documentation only / not wired" model note with the now-wired behavior, or leave frontmatter model-less and document that the orchestrator supplies the override at spawn (the wire lives in the engine, not frontmatter) (ref: Q5).

**Reduced — three `SKILL.md` files:** collapse to thin wrappers that invoke the shared engine with `{ticket, phase}`; remove the duplicated loop/scratch/render/SHA prose (ref: Q4, AC #4). (The whole-stack `/review` command and skill were **already removed** in commit `b7d8c96` "remove unified /review skill" — there is no `.claude/skills/review/` to delete; this is recorded only to confirm the scope decision is already realized, not as an action item.)

**New — contract fixtures** under `scripts/fixtures/contract_seam/review/` + producer/consumer coverage, if the engine adds a JS parser at the seam, reusing `contract_seam_runner.js` (skips when `node` absent) (ref: Q13).

## Pattern Decisions

### Decision 1: AC #2 honesty mechanism — drop revise vs. surface diff

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Drop the revise loop for advisory mode; run panel once (round 0), report verbatim | Verdict = artifact-as-written by construction; simplest; removes the scratch-laundering class entirely; `lensModel`/render are the only other moving parts | Loses the reviser's "here is a concrete fix" value; reviser agent becomes unused by this family |
| B | Keep revise but surface the reviser's change as a diff and report round-0 verdict separately | Reviewer gets both the as-written verdict and a proposed fix | More moving parts; must retain round-0 as a distinct datum (Q2 says no such retention exists); higher token cost; diff rendering is new surface |

**Recommendation:** Option A
**Rationale:** The ticket's AC #2 explicitly offers "either drop the revise loop … (round-0 findings reported verbatim) or surface … a concrete diff." The goal is a trustworthy *automated* second opinion; the reviser only ever mutated a throwaway scratch copy and never the PR (ref: Q2, Q7), so its output was already advisory-only and never landed. Dropping it removes the dishonest-signal root cause directly and shrinks the engine, aligning with the "single source of truth" and "cheaper" goals (ref: AC #3, AC #4). Round-0-only also sidesteps the absent round-0-retention machinery (ref: Q2).
**NEW PATTERN?** No — running `synthesize` once and rendering is the existing reduce/render path with the loop removed (ref: Q3, Q8).

### Decision 2: Orchestrator substrate — `.claude/workflows` engine vs. richer Python core

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | A `.claude/workflows/qrspi-review.js` engine matching `qrspi-batch.js` patterns; pure decision in a small Python helper | Consistent with the established substrate (ref: Q4); agent fan-out + comment + SHA assert in JS; logic stays testable in Python | JS is harness-coupled and not unit-testable in isolation; must cover the seam with contract fixtures |
| B | Push more orchestration into Python CLIs and keep the SKILL as a thin caller | More directly unit-testable | Python cannot spawn `Agent`s or run `gt`/`gh` in the JS sandbox model; the agent fan-out MUST live in the harness layer (ref: Q4) — this option cannot host the lens spawns |

**Recommendation:** Option A
**Rationale:** AC #3 explicitly permits "a `.claude/workflows` script, or a shared JS engine the workflows call." Only the harness layer can spawn typed agents and issue the comment write; Python cannot (ref: Q4). The proven split is pure-core/harness-shell (ref: Discovered Patterns): the substantive testable logic already lives in the existing tested helpers (`synthesize` AND-reduce, `render_synopsis`, `partition_decision_readiness`, `build_record`); the only new decision under the no-revise model is a trivial binary terminal pick (`converged`/`exhausted`) which is **inlined in the engine** rather than spun out into a new module. The irreducible imperative shell goes in the JS engine, covered at the seam by contract fixtures exactly as `qrspi-batch.js` is (ref: Q13).
**NEW PATTERN?** Yes — a NEW `.claude/workflows` script for on-demand review (today only `qrspi-batch.js` exists). Justified: the retired batch critic loops left no review orchestrator, and the SKILLs' hand-driven loop is precisely what AC #3 removes; no existing harness-layer review engine fits.

### Decision 3: `lensModel` wiring point — engine spawn override vs. agent frontmatter

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Engine reads resolved `lensModel` and passes it as the `model` override on the `*-review` lens `agent(...)` spawn | Single wire in one place (the new engine); per-phase; honors the existing config seam (ref: Q5); keeps the "do NOT couple" decoupling | Requires the engine (Decision 2) to exist; agents stay model-less in frontmatter |
| B | Hard-code the strong model in each `*-review` agent's frontmatter | No engine dependency | Bakes a model id into three files; ignores the configurable `critics.*.lensModel` seam; drifts from config; three-place edit |

**Recommendation:** Option A
**Rationale:** The agents already document the Opus-tier intent and a config seam already proves the shape — the only missing piece is the wire (ref: Q5, Inconsistencies). The model id is sourced from the NEW on-demand key `critics.review.lensModel` (Delta — distinct from the batch `critics.design.lensModel` so the families stay decoupled), read once and passed at spawn, keeping model selection configurable and centralized in the engine that AC #3 introduces (ref: Discovered Patterns). The `*-review` lens is the only lens AC #5 names, so only its spawn takes the override.
**NEW PATTERN?** No — `agent(prompt, {…})` already accepts spawn options (ref: Q4); adding a `model` key is using the existing seam.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Batch panels regress when `qrspi_critics_config.py` is touched to expose `lensModel` for plan/impl | med | high | Keep `DEFAULT_DESIGN_LENSES`/`resolve_design` untouched; add a separate read path for on-demand; retain the "do NOT couple" comments and assert with the existing critics contract fixture (ref: Q11, Q13) |
| Propose-only invariant lost in the JS port (a stray `gt`/`gh` branch write, or the SHA assert dropped) | low | high | Port the Step-2 capture + final re-assert into the engine verbatim; issue ONLY the comment write; add a contract-fixture/test asserting no branch-mutating command is emitted; the comment never moves the head (ref: Q10) |
| Dropping the revise loop orphans `qrspi-critic-reviser` and the `next_action` call site, leaving dead/confusing surface | med | low | RETAIN the `qrspi_critic_loop` MODULE — it is NOT deletable: `qrspi_critic_synthesize.py` imports `_coerce_verdict`/`parse_critic_verdict` from it and the engine still calls `synthesize`. Only the `qrspi-critic-reviser` AGENT and the `next_action` call site become unused-by-review; retire/mark those, keep the module. Ensure `terminal_action` is valid for `build_record` (no `revise`) (ref: Q3; resolves OQ1) |
| JS engine is not unit-testable in isolation, so the orchestration ships under-tested | high | med | Keep all substantive decision logic in the existing tested helpers (`synthesize`, `render_synopsis`, `partition_decision_readiness`, `build_record`) plus the new `resolve_review_lens_model` reader, each with `_test.py`; the engine's only residual logic is the inlined binary terminal pick. Cover the JS↔Python seam with `contract_seam_runner.js` fixtures; verify end-to-end manually (the documented strategy) (ref: Q13) |
| Render change leaks finding text in a way that breaks the additive-ledger/summary readers | low | med | Render is output-only; `ledger_row_fields` shape unchanged; summary reads via `.get()` so additive fields are safe — keep changes confined to `render_synopsis` body (ref: Q6, Q12) |

## Open Questions

All four prior open questions were resolved during design review (2026-06-19); retained here as a decision record.

- OQ1 — **RESOLVED: retain the module, retire only the agent + call site.** The `qrspi_critic_loop` module is NOT deletable — `qrspi_critic_synthesize.py` imports `_coerce_verdict`/`parse_critic_verdict` from it and the engine still calls `synthesize`. Only the `qrspi-critic-reviser` agent and the `next_action` call site become unused-by-review; mark those dormant, keep the module (ref: Q2, verified against source).
- OQ2 — **RESOLVED: inline binary pick.** The no-revise `terminal_action` is `converged` on a round-0 pass else `exhausted` — both in `VALID_TERMINAL_ACTIONS`, both honest in synopsis/ledger. Computed inline in the engine; no new helper (ref: Q3, Decision 1/2).
- OQ3 — **RESOLVED: new on-demand key.** The model id is sourced from a NEW `critics.review.lensModel` key, read by a single `resolve_review_lens_model` reader applied symmetrically to all three phases — deliberately separate from the batch `critics.design.lensModel`/`resolve_design`, which stays untouched (ref: Q5, Q11, Delta).
- OQ4 — **RESOLVED: one engine parameterized by phase.** A single `.claude/workflows/qrspi-review.js` invoked as `{ticket, phase}` from the three thin SKILL wrappers — satisfies AC #4 (single source of truth) directly (ref: Q4, AC #4).
