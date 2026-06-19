# Work Tree — Upgrade the /review-* advisory review family

**Plan basis:** plan.md @ 2026-06-19T00:00:00Z
**Generated:** 2026-06-19T00:00:00Z
**Status:** draft
**Total sessions:** 4
**Critical path:** T2 → T3 → T5 (Slice 1) → T8 → T9 → T11 (Slice 2) → T18 → T20 (engine) → T21–T24 (wrappers/agents) → T25 → T28 (Verify Slice 3)

Critical path length = 13 tasks. Slices 1 and 2 are independent of each other on
their core logic, but the plan stacks them bottom-up (Slice 1 → Slice 2 → Slice 3),
and Slice 3 depends on the rendering of Slice 1 and the reader of Slice 2.

## Session 1 — Slice 1: Surface blocking finding text in the synopsis render

**Load:** plan.md §Slice 1, structure.md §Contracts (render_synopsis),
        `scripts/qrspi_review_synopsis.py`, `scripts/qrspi_review_synopsis_test.py`
**Estimated context:** ~12% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Read `qrspi_review_synopsis.py`; locate per-lens table render; confirm findings present via `_verdict(..., findings=[str])` | — | §1.1 | S | pending |
| T2 | Modify `render_synopsis` to emit a "Blocking findings" sub-section beneath each FAIL row (deduped strings); signatures unchanged | T1 | §1.2 | M | pending |
| T3 | Modify `qrspi_review_synopsis_test.py` — assert finding strings surface verbatim; `nonBlockingNotes` still renders | T2 | §1.3 | S | pending |
| T4 | Run `python3 scripts/qrspi_review_synopsis_test.py` (expect green) | T3 | §1.4 | S | pending |
| T5 | **Verify Slice 1** — checkpoint test passes; FAIL render shows literal findings; `nonBlockingNotes` unchanged | T4 | §1.5 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete and independently verified. Slice 2 touches a
different file (`qrspi_critics_config.py`) with no shared state — fresh context.

## Session 2 — Slice 2: Add the on-demand `critics.review.lensModel` reader

**Load:** plan.md §Slice 2, structure.md §Contracts (resolve_review_lens_model),
        `scripts/qrspi_critics_config.py`, `scripts/qrspi_critics_config_test.py`
**Estimated context:** ~12% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T6 | Read `qrspi_critics_config.py`; confirm `resolve_design`/`DEFAULT_DESIGN_LENSES`/batch envelope, "do NOT couple" comments, fail-closed convention | — | §2.6 | S | pending |
| T7 | Modify `qrspi_critics_config.py` — add `resolve_review_lens_model(cfg) -> str \| None` reading `critics.review.lensModel`; never raise; leave batch path untouched | T6 | §2.7 | M | pending |
| T8 | Modify `qrspi_critics_config_test.py` — assert configured id, None on absent/malformed, `resolve_design` non-coupling regression | T7 | §2.8 | S | pending |
| T9 | Run `python3 scripts/qrspi_critics_config_test.py` (expect green) | T8 | §2.9 | S | pending |
| T10 | **Verify Slice 2** — `qrspi_critics_config_test.py` green; `run_tests.py critics` green (batch contract unaffected) | T9 | §2.10 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 2 complete and verified. Slice 3 is large (engine + wrappers +
agent defs) and front-loaded with 4 broad codebase reads — isolate the
read/decision work in its own session so the build session starts with a clean,
fact-grounded context.

## Session 3 — Slice 3a: Substrate reads + JS↔Python seam decision

**Load:** plan.md §Slice 3 (Setup + step 14), structure.md §Unverified Assumptions,
        `.claude/workflows/qrspi-batch.js`, the three `.claude/skills/review-*/SKILL.md`,
        `scripts/qrspi_critic_synthesize.py`, `scripts/qrspi_review_record.py`,
        `scripts/qrspi_review_synopsis.py` (`partition_decision_readiness`),
        `scripts/qrspi_comment_reply.py`, `scripts/qrspi_metrics_append.py`
**Estimated context:** ~30% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T11 | Read `qrspi-batch.js` — confirm `engineCmdFor(r,rel)`, `stg()`, `provisionStep`, `agent(prompt,{model})`, python-as-command-string convention | T5, T10 | §3.11 | M | pending |
| T12 | Read the three `review-{design,plan,implementation}/SKILL.md` — capture round-0 fan-out, scratch-copy, decision-readiness (design-only), comment, ledger, SHA-assert prose; confirm `DEFAULT_REVIEW_*` tuples | T11 | §3.12 | M | pending |
| T13 | Read `qrspi_critic_synthesize.py`, `qrspi_review_record.py`, `qrspi_review_synopsis.py` (`partition_decision_readiness`), `qrspi_comment_reply.py`, `qrspi_metrics_append.py` — confirm `build_record(..., terminalAction, agreement)`, `VALID_TERMINAL_ACTIONS`, `synthesize(...)` signatures | T12 | §3.13 | M | pending |
| T14 | Decide whether `qrspi-review.js` parses Python stdout at any JS↔Python seam; record decision (drives steps 23–24) | T13 | §3.14 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** All Slice 3 reads and the seam decision are captured. Drop the bulky
read context and build the engine + wrappers + agent defs in a fresh session
carrying only the decision and the confirmed call signatures.

## Session 4 — Slice 3b: Build engine, collapse wrappers, update agent defs, verify

**Load:** plan.md §Slice 3 (Core Logic onward), structure.md §Contracts,
        impl-log.md §Slice 3a (seam decision + confirmed signatures, notes only)
**Estimated context:** ~32% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T15 | Create `.claude/workflows/qrspi-review.js` — deterministic `{ticket, phase}` orchestrator: resolve via `qrspi_resolve.py`, scratch-copy via `stg()`, capture head SHA, fan `DEFAULT_REVIEW_*` lenses (model override on `*-review` spawn only), `synthesize` ONCE (round 0), design-only decision-readiness, inline terminal action, `render_synopsis`, post comment, append ledger (agreement `{}`), re-assert SHA; NO `gt`/`gh` branch mutation | T14 | §3.15 | L | pending |
| T16 | Modify `review-design/SKILL.md` — collapse to thin wrapper invoking engine `{ticket, phase:"design"}` | T15 | §3.16 | S | pending |
| T17 | Modify `review-plan/SKILL.md` — collapse to thin wrapper `{ticket, phase:"plan"}` | T15 | §3.17 | S | pending |
| T18 | Modify `review-implementation/SKILL.md` — collapse to thin wrapper `{ticket, phase:"impl"}` | T15 | §3.18 | S | pending |
| T19 | Modify `qrspi-design-critic-design-review.md` — model note now-wired (orchestrator supplies override; frontmatter model-less) | T15 | §3.19 | S | pending |
| T20 | Modify `qrspi-plan-critic-plan-review.md` — same model-note update | T15 | §3.20 | S | pending |
| T21 | Modify `qrspi-impl-critic-impl-review.md` — same model-note update | T15 | §3.21 | S | pending |
| T22 | Modify `qrspi-critic-reviser.md` — mark dormant/unused-by-review; do NOT delete `qrspi_critic_loop` module | T15 | §3.22 | S | pending |
| T23 | Create `scripts/fixtures/contract_seam/review/` fixtures ONLY IF T14 found a seam; else skip + record in engine header | T14, T15 | §3.23 | M | pending |
| T24 | Modify seam fixture / engine assertion — check NO `gt`/`gh` branch-mutating command emitted (propose-only guard) | T23 | §3.24 | S | pending |
| T25 | **Checkpoint:** `python3 scripts/run_tests.py` — full suite green (seam fixtures if added + Slices 1–2) | T16, T17, T18, T19, T20, T21, T22, T24 | §3.25 | S | pending |
| T26 | **Checkpoint:** `grep -nE "\bgt \|\bgh " .claude/workflows/qrspi-review.js` — no branch-mutating command; model override on `*-review` spawn only | T25 | §3.26 | S | pending |
| T27 | **Checkpoint (manual e2e):** run `/review-design`, `/review-plan`, `/review-implementation` on a real ticket PR | T26 | §3.27 | M | pending |
| T28 | **Verify Slice 3** — synopsis posts with blocking findings on FAIL; ledger row `converged`/`exhausted` + agreement `{}`; PR head SHA unchanged; model override carried when key set | T27 | §3.27 | S | pending |
