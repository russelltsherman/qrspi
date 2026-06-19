# Structure Outline — Upgrade the /review-* advisory review family

**Design basis:** design.md @ 2026-06-19T00:00:00Z
**Generated:** 2026-06-19T00:00:00Z
**Status:** draft

## New Types

No new data types. The work introduces one new pure reader and one new JS orchestration substrate; both operate over existing dict/JSON shapes.

- (conceptual) `ReviewEngineInput { ticket: str, phase: "design" | "plan" | "impl" }` — the parameterization the three thin SKILL wrappers pass to the shared engine (ref: design.md §Delta, OQ4). Not a serialized type — a workflow `args` object.

## Modified Types

- No serialized type/struct definitions change. `ledger_row_fields` / `partition_decision_readiness` signatures are **unchanged** — the synopsis change is additive render only (ref: design.md §Delta). The ledger row's `agreement` positional is passed an empty block `{}` (former AC #6 dropped; `qrspi_review_agreement.compute` not invoked).

## Contracts

Cross-slice interfaces — the pure Python functions Slice 1/2 produce and Slice 3's JS engine consumes as command-string invocations:

- `render_synopsis(...): str` — **MODIFIED.** Existing per-lens `PASS|FAIL|count` table preserved; gains a per-failing-lens block emitting the deduped blocking finding **text** (already present in the input array via `_verdict(..., findings=[str])`). Output-only change (ref: design.md §Delta, AC #1).
- `resolve_review_lens_model(cfg): str | None` — **NEW** (`scripts/qrspi_critics_config.py`). Stdlib-only reader of the NEW on-demand key `critics.review.lensModel`; returns the configured model id or `None`. Deliberately **separate** from `resolve_design` / `DEFAULT_DESIGN_LENSES` / batch `critics.design.*` (which stay untouched). Applied symmetrically to all three phases (ref: design.md §Delta, Decision 3, OQ3).
- `qrspi_review_record.build_record(..., terminalAction, agreement)` — **CONSUMED unchanged.** Engine passes a terminal action of `converged` (round-0 pass) or `exhausted` (else) — both in `VALID_TERMINAL_ACTIONS`; `revise` is non-terminal and correctly rejected. `agreement` passed `{}` (ref: design.md §Delta, OQ2).
- `synthesize(...)` (`qrspi_critic_synthesize.py`) — **CONSUMED unchanged, called ONCE** (round 0, no revise loop). Still imports `_coerce_verdict`/`parse_critic_verdict` from `qrspi_critic_loop` — that module is RETAINED, not deleted (ref: design.md Risk Register, OQ1).
- Engine → Python invocation seam: every Python call is a literal command STRING in a worker prompt, bare-relative script paths prefixed via `engineCmdFor(r, rel)`, scratch/staging via `stg()` → `/tmp/phase-stage/<id>/`, mandatory `provisionStep` re-provisioning the worktree per worker (ref: design.md §Delta, Q4).
- Propose-only invariant (engine): head SHA captured before the panel, re-asserted at the end; ONLY the comment write (`qrspi_comment_reply.py`) and ledger append (`qrspi_metrics_append.py`) are issued — no `gt`/`gh` branch-mutating command. A comment never moves the head (ref: design.md §Delta, Q10, Risk Register).
- `lensModel` spawn override: engine passes the resolved `resolve_review_lens_model` value as the `model` key on the `*-review` lens `agent(...)` spawn ONLY (the single lens AC #5 names); other lenses inherit the session model (ref: design.md Decision 3, AC #5).

## Slice 1: Surface blocking finding text in the synopsis render

**Goal:** A failing advisory review's rendered synopsis body contains the actual blocking finding strings (not just a per-lens count), verified by unit test in isolation — independent of the engine that will later call it.
**Files touched:**

- ⚠️ `scripts/qrspi_review_synopsis.py` — extend `render_synopsis` (and the per-lens table render at lines ~140–147): keep the `PASS|FAIL|count` row, add beneath each FAIL row a "Blocking findings" sub-section emitting the deduped finding strings. `ledger_row_fields`/`partition_decision_readiness` signatures unchanged.
- ⚠️ `scripts/qrspi_review_synopsis_test.py` — add assertions that blocking finding strings (already present in fixtures' `findings=[...]`) surface in the rendered body.
**Verification:**
- [ ] `python3 scripts/qrspi_review_synopsis_test.py` passes, including the new finding-text assertions
- [ ] A FAIL-fixture render shows the literal finding strings; `nonBlockingNotes` text still renders unchanged
**Context cost:** S
**Depends on:** none

## Slice 2: Add the on-demand `critics.review.lensModel` reader

**Goal:** A pure, stdlib-only reader resolves the NEW on-demand `critics.review.lensModel` key to a model id or `None`, with the batch design config path provably untouched — verified by unit test in isolation before the engine wires it.
**Files touched:**

- ⚠️ `scripts/qrspi_critics_config.py` — add `resolve_review_lens_model(cfg) -> str | None` reading `critics.review.lensModel`; leave `resolve_design` / `DEFAULT_DESIGN_LENSES` / the batch `critics.design.*` envelope and the "do NOT couple" comments untouched.
- ⚠️ `scripts/qrspi_critics_config_test.py` — assert the new reader returns the configured id, returns `None` when absent/malformed, and that `resolve_design` output is unchanged (non-coupling regression).
**Verification:**
- [ ] `python3 scripts/qrspi_critics_config_test.py` passes, including the new reader + non-coupling assertions
- [ ] `python3 scripts/run_tests.py critics` is green (batch critics contract fixture unaffected)
**Context cost:** S
**Depends on:** none

## Slice 3: Deterministic review engine + thin SKILL wrappers + wired lens model

**Goal:** Invoking any of `/review-design|plan|implementation <ticket>` runs the shared deterministic engine once (round 0, no revise), spawns the `*-review` lens under the configured model, renders findings (Slice 1), posts the synopsis comment + ledger row, and re-asserts the unchanged PR head SHA — replacing the three hand-driven SKILL loops. This is one cohesive unit: the engine cannot be meaningfully verified without the wrappers that invoke it, the wrappers are meaningless without the engine, and the agent-def + fixture changes are direct dependencies of the wire.
**Files touched:**

- ✨ `.claude/workflows/qrspi-review.js` — new deterministic orchestrator `{ticket, phase}`: resolve worktree/PR via `qrspi_resolve.py`, scratch-copy artifact, capture head SHA, fan `DEFAULT_REVIEW_*` lenses via `agent(...)` (passing the `resolve_review_lens_model` value as `model` on the `*-review` spawn only), `synthesize` ONCE, design-only post-panel decision-readiness lens, inline binary terminal pick (`converged`/`exhausted`), `render_synopsis`, post comment via `qrspi_comment_reply.py`, append ledger via `qrspi_metrics_append.py` with empty agreement `{}`, re-assert head SHA. Uses `engineCmdFor(r,rel)`, `stg()`, mandatory `provisionStep`, python-as-command-string.
- ⚠️ `.claude/skills/review-design/SKILL.md` — collapse to a thin wrapper invoking the engine with `{ticket, phase:"design"}`; remove duplicated loop/scratch/render/SHA prose.
- ⚠️ `.claude/skills/review-plan/SKILL.md` — thin wrapper `{phase:"plan"}`.
- ⚠️ `.claude/skills/review-implementation/SKILL.md` — thin wrapper `{phase:"impl"}`.
- ⚠️ `.claude/agents/qrspi-design-critic-design-review.md` — replace the "not wired / documentation only" model note with the now-wired behavior (orchestrator supplies the override at spawn; frontmatter stays model-less).
- ⚠️ `.claude/agents/qrspi-plan-critic-plan-review.md` — same model-note update.
- ⚠️ `.claude/agents/qrspi-impl-critic-impl-review.md` — same model-note update.
- ✨ `scripts/fixtures/contract_seam/review/` (+ producer/consumer coverage) — contract fixtures for any JS↔Python parser the engine adds at the seam, driven through `contract_seam_runner.js` (skips when `node` absent).
- ⚠️ `.claude/agents/qrspi-critic-reviser.md` — mark dormant/unused-by-review (the revise loop is dropped); the `qrspi_critic_loop` MODULE is RETAINED (still imported by `qrspi_critic_synthesize.py`).
**Verification:**
- [ ] `python3 scripts/run_tests.py` is green (seam fixtures + all helpers)
- [ ] Manual end-to-end: run each of the three commands against a real ticket PR; confirm the synopsis comment posts, the ledger row appends with terminal `converged`/`exhausted`, and `gh pr view` shows the PR head SHA **unchanged** (no branch push)
- [ ] Confirm no `gt`/`gh` branch-mutating command is emitted by the engine (grep the workflow + the seam-fixture assertion)
- [ ] Confirm the `*-review` lens spawn carries the `model` override when `critics.review.lensModel` is set
**Context cost:** L
**Depends on:** Slice 1, Slice 2

---

## Unverified Assumptions

- **Existence of a JS↔Python parser seam in the engine.** The design hedges the contract fixtures with "**if** the engine adds a JS parser at the seam" (§Delta, Q13). Whether `qrspi-review.js` needs to *parse* Python stdout (vs. only shell-orchestrate command strings like `qrspi-batch.js`) is not pinned to concrete code — the plan must decide during engine authoring whether the `scripts/fixtures/contract_seam/review/` fixtures are actually needed.
- **`render_synopsis` table line numbers (~140–147).** The design cites specific lines for the per-lens table render; the exact insertion point must be confirmed against the live file during Slice 1 (the reads constraint barred verifying them here).
- **Decision-readiness lens placement under no-revise.** The design states the design-only post-panel decision-readiness lens runs after `synthesize` (§Delta), but the precise data it consumes now that there is exactly one (round-0) panel pass — and whether `partition_decision_readiness` is fed round-0 verdicts directly — is described behaviorally, not as a concrete call signature. To confirm in Slice 3 against the existing helper.
- **Agent-def model-note format.** The design offers two equivalent options for the three `*-review` agent defs (update the note vs. leave model-less + document the engine wire). The exact frontmatter/body edit per file is a choice deferred to implementation, not a mapped concrete change.
