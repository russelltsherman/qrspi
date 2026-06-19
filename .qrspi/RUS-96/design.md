# Design — Design-phase work→review→revise loop at the producer gate

**Ticket:** RUS-96
**Research basis:** research.md @ 2026-06-19T00:00:00Z
**Generated:** 2026-06-19T00:00:00Z
**Status:** draft

## Current State

Today `doDesign(t, r)` runs `questions → research → design` (each ungated through `runPhase`, where the deterministic persist into the worktree IS the per-phase success gate) then a single `Finalize` agent that commits and submits the design PR; there is no review/loop config read inside `doDesign` at all (ref: Q1, Q10). The natural insertion point for a gate is after the design `runPhase` returns true and before `phase('Finalize')`, where `design.md` exists at its canonical worktree path, no design PR yet exists, and commit/submit has not run (ref: Q1). The autonomous batch explicitly "runs no phase critics or node-checks; each phase persists ungated" — and there is **no existing `workflow(...)` call inside `qrspi-batch.js`** (ref: Q1, Q10).

The review engine `qrspi-review.js` has **no `mode` parameter today** — it has exactly one propose-only behavior, called "advisory," whose only input is `{ ticket, phase }`; it operates on a **scratch copy** at `/tmp/phase-stage/<ticket>/review/<artifact>.md`, returns `{ ok, ticket, phase, pr, terminalAction, shaUnchanged, summary }`, and is invoked by three thin SKILL wrappers (ref: Q2, Q4). It runs the panel **once** (round 0, no revise loop); `terminalAction` is the string `converged | exhausted` and is the only convergence signal (no `rounds`/`residualFindings`/`logPath` exist) (ref: Q4). It SHA-locks: the Resolve worker snapshots the PR head SHA before the panel, the Synopsis worker re-reads it after all writes, and **the engine** (not the worker) fails the run if they differ or the after-SHA is blank (ref: Q12).

The design lens agents already exist (`completeness`, `internal-consistency`, `edge-alignment`, `simplicity`, `design-review` node-validity, plus the terminal-advisory `decision-readiness`); every panel lens emits the uniform `{pass, findings, nonBlockingNotes?}` verdict (`CRITIC_VERDICT_SCHEMA`, strict `pass:false ⟺ findings non-empty` for node-validity), and `decision-readiness` emits a distinct `DecisionReadinessVerdict` that is partitioned OUT so it can never drive a revise round (ref: Q8). `scripts/qrspi_critic_synthesize.py` exposes the pure `synthesize(verdicts)` reducer returning `{pass, findings}` — `pass:True` only if every lens passed, `findings` the deduped union (fail-closed on empty/garbled) (ref: Q5). The `qrspi-critic-reviser` agent exists but is **DORMANT (RUS-93)** — retained, with no live caller; it is propose-only/scratch-only (writes ONLY to a `/tmp/phase-stage/<id>/review/` scratch path, forbidden from any tracked-path write or `gt`/`gh`) (ref: Q7).

Fix-A persistence writes producer output to the token-free staging path `/tmp/phase-stage/<id>/<artifact>.md`, then `scripts/qrspi_persist.py` verifies non-empty and `shutil.move`s it to `.worktrees/<id>/.qrspi/<id>/<artifact>.md`; `--artifact` is a closed enum of six names (`questions, research, design, structure, plan, worktree`), and the script knows **no `review/` segment** (ref: Q3). Config readers in `scripts/qrspi_critics_config.py` are uniformly opt-in (default OFF): `resolve_enabled(cfg, default)` flips only on an explicit boolean, `_pos_int_or(value, default)` for positive ints, nested blocks read as dicts only when dicts, optional string overrides omitted when unset (ref: Q6). The design PR is published via `gt submit --publish`; the body is seeded by Graphite from the commit message **at creation only**, and post-creation body changes use `gh api repos/<owner>/<repo>/pulls/<N> -X PATCH -F body=@<file>` (publishing always via `gt`, never `gh`) (ref: Q11). There is **no committed per-round review log today** — `render_synopsis` produces an ephemeral PR comment, and the only committed log (`impl-log.md`) is an implementation producer log, not a review log (ref: Q15). Every pure core has a stdlib-only `*_test.py` sibling auto-discovered by `scripts/run_tests.py`; JS workflow files are deliberately untested (harness-coupled) (ref: Q13, Q14).

## Desired End State

- **AC1 (Two-mode engine):** `qrspi-review.js` gains a `mode` input. `advisory` (the existing default when `mode` is absent or `advisory`) is byte-for-byte unchanged — scratch copy, single round, posts a comment, SHA-locked (ref: Q2, Q12, Q14). A new `gate` mode operates on the **real worktree `design.md`** (not the scratch copy), runs a multi-round loop, returns `{converged, rounds, residualFindings, logPath}`, posts **no** PR comment, and does **not** SHA-lock. `doDesign` invokes it via `workflow('qrspi-review', {ticket, phase:'design', mode:'gate'})` at the post-design / pre-finalize seam (ref: Q1, Q4).
- **AC2 (Full panel every round):** every configured design lens runs each round (no lens-skipping), so a reviser-introduced regression is re-caught; the panel set is the existing `cfg.lenses` for design (ref: Q8).
- **AC3 (Cross-critic debate):** after the parallel panel each round, every critic sees every lens's findings and votes agree / dispute-with-reason; debate repeats until positions stabilize (a round with no vote changes) or the configurable `debateCap` (default **3**) is hit. Dissent preservation: a finding still defended by any lens survives even if outvoted; majority-dispute drops only findings **no** lens defends (a tested pure stabilization core).
- **AC4 (Reduce):** surviving post-debate findings reduce to `{pass, residualFindings}`, reusing/extending `synthesize` — `pass` from its all-pass rule, `residualFindings` from its `findings` union (ref: Q5).
- **AC5 (Revise):** on a failing round the un-dormant `qrspi-critic-reviser` rewrites the design addressing the residual findings, writing to the Fix-A staging path `/tmp/phase-stage/<id>/design.md` so `qrspi_persist.py --artifact design` moves it into the worktree (ref: Q3, Q7).
- **AC6 (Post-revise verification = the next-round full panel):** the reviser's self-report is **never** trusted; verification is delivered by AC2's mandated next-round full panel re-run rather than a separate verifier agent. After a revise, the loop re-runs **every** design lens over the rewritten worktree `design.md` (AC2), which independently re-judges the whole artifact: a finding the reviser failed to resolve is simply re-raised ("still failing"), and a regression the reviser introduced anywhere is freshly caught by the full panel (not just at the prior finding's locus). This is a strict superset of a per-finding verifier — it never relies on the reviser's claim that a fix landed — so the design carries **no** standalone `qrspi-critic-verifier` agent and **no** per-finding verification fan-out (advisory-review simplicity finding; the full panel earns the regression/self-report guarantee on its own) (ref: Q7, Q8).
- **AC7 (Convergence + cap):** the loop repeats until the reduced verdict passes (converged) or `maxRounds` is reached (default **5**) — a tested pure convergence/cap core (ref: Q5).
- **AC8 (Publish with residuals — cap-exhaustion only):** on convergence the design PR submits normally; on **cap-exhaustion** (the loop reached `maxRounds` with residual findings — a bounded, converged-enough outcome) it submits **anyway**, and the residual findings live **only in the committed `design-review-log.md` document** (its final-round residual-findings section) — they are **not** attached to the PR body or posted as a PR comment (reviewer decision on OQ4). Publishing stays on `gt submit`; there is **no** `gh api … PATCH` of the PR body and **no** gate comment write (ref: Q11, Q15). This publish-anyway path is scoped to cap-exhaustion and does **not** cover a mid-loop crash (see AC8b).
- **AC8b (Mid-loop crash → hard fail, resolved OQ3):** a reviser failure or a `null` agent return **mid-loop** (the agent-seam failure contract returns bare `null`) is an **unexpected failure**, not a converged outcome. The gate **does not publish**; it **reports the error and aborts** (`failTicket`), leaving the design PR unchanged so the ticket is **retried on the next batch run**. A crash leaves no trustworthy last-good `design.md` to ship, so failing loud + retrying is preferred over publishing a possibly-corrupt artifact.
- **AC9 (Committed review log):** `.qrspi/<id>/design-review-log.md` records per round (panel verdicts, debate outcomes, preserved dissent, residual findings, reviser change summary, verification results) and is committed **alongside** the design artifacts in the design commit (ref: Q15).
- **AC10 (Config + defaults):** new `critics.design.reviewLoop` with **three** keys read via `qrspi_critics_config.py` — `enabled` (default **true**), `maxRounds` (default **5**), and `debateCap` (default **3**, the debate-exchange cap; resolved per OQ2 as a configurable key, not a fixed constant); a missing/disabled config behaves additively → today's ungated `doDesign` (ref: Q6, Q10).
- **AC11 (Tested pure core):** all decision logic (debate stabilization, dissent-preserving reduce, convergence/cap, config readers, residual/log rendering) is stdlib-only Python with `_test.py` siblings; LLM agents are not unit-tested (ref: Q13).
- **AC12 (Docs):** `.claude/CLAUDE.md` and the `qrspi-review.js` engine header document the gate-mode loop, its always-on default, and the publish-with-residuals contract.

## Delta

**Modified — `.claude/workflows/qrspi-review.js`:** parse a `mode` input (default `advisory`); branch a new `runGateMode()` path that loops `panel → debate → reduce → revise → (re-panel)` over the real worktree artifact — the next iteration's full panel re-run IS the post-revise verification (AC6), so there is no separate verify step — returns `{converged, rounds, residualFindings, logPath}`, skips the comment write and the SHA re-assert block. The existing advisory path (Q12 lines `:502-511`) must remain reachable and unchanged.

**Modified — `.claude/workflows/qrspi-batch.js` (`doDesign`):** after the design `runPhase` and before `phase('Finalize')`, read the loop config; when enabled, `await workflow('qrspi-review', {ticket, phase:'design', mode:'gate'})`; carry `residualFindings`/`converged` forward so Finalize commits `design-review-log.md` (whose final-round section carries any residual findings). On non-convergence there is **no** PR-body PATCH and **no** comment — the residuals live solely in the committed log document (reviewer decision on OQ4). With the loop disabled, `doDesign` runs exactly as today.

**Modified — `scripts/qrspi_critics_config.py`:** add a reader for `critics.design.reviewLoop` (`enabled` default **true** via `resolve_enabled(cfg, True)` — note the inverted default vs. the OFF convention; `maxRounds` default 5 and `debateCap` default 3, both via `_pos_int_or`), using the nested-block precedent. Sibling test extended.

**Modified — `scripts/qrspi_critic_synthesize.py`:** reuse/extend `synthesize` to emit `{pass, residualFindings}` (alias of `findings`) for the gate reduce. Sibling test extended.

**New pure cores (each with a `*_test.py` sibling):** debate-stabilization (`agree/dispute` votes → stabilized surviving findings with dissent preservation), convergence/cap evaluator (verdict + round count → `converged | continue | exhausted`), and the `design-review-log.md` renderer (per-round sections).

**Modified — `scripts/qrspi_persist.py`:** add `design-review-log` to the `ARTIFACTS` enum so the rendered log can be staged + moved into the worktree (ref: Q3, Q15).

**Modified agent — `qrspi-critic-reviser`:** un-dormant by adding a gate call site; its write target points at the Fix-A staging path so persist lands it (see Decision 3).

**No new verifier agent** — post-revise verification is the next-round full panel re-run (AC6), so a standalone `qrspi-critic-verifier` and a per-finding verification fan-out are **not** introduced (advisory-review simplicity finding). The panel set the gate already runs each round (AC2) re-judges the reviser's output independently, never trusting its self-report, and catches any reviser-introduced regression.

**Modified — `.claude/CLAUDE.md`** and the `qrspi-review.js` header: document gate mode.

## Pattern Decisions

### Decision 1: How `mode:'gate'` lives inside the engine

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | One `qrspi-review.js` with a `mode` switch: shared resolve/panel/reduce helpers, two terminal paths (advisory: comment+SHA-lock; gate: loop+log) | AC1's literal "generalized two-mode engine"; reuses panel fan-out + `synthesize`; one engine for `doDesign` to call | Larger file; must guard advisory path unchanged (Q14 tests) |
| B | Separate `qrspi-gate.js` workflow, advisory engine untouched | Zero risk to advisory; clean separation | Duplicates panel/resolve glue; contradicts AC1's explicit "generalized into a two-mode engine" wording |

**Recommendation:** Option A
**Rationale:** AC1 names a two-mode engine explicitly, and the panel fan-out, lens agentTypes, and `synthesize` reduce are already in `qrspi-review.js` (ref: Q2, Q8). Advisory is preserved by branching around (not weakening) the comment + SHA-reassert block (ref: Q12), proven by the unchanged Python-core tests (ref: Q14).
**NEW PATTERN?** No — extends the existing single-behavior engine; mode-dispatch on a parsed arg mirrors the existing lenient arg parse (ref: Q4).

### Decision 2: Where the multi-round loop logic lives

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Loop control flow in `qrspi-review.js`; every *decision* (debate-stable, reduce, convergence/cap, log render) in tested Python pure cores the engine drives via the worker seam | Matches "keep loop logic in engine/Python core, not the batch" + the JS↔Python worker-seam pattern; all decisions unit-tested (AC11) | Engine grows; many small worker round-trips |
| B | Put loop + decisions inline in `doDesign` (batch) | Fewer files | Violates the constraint ("`qrspi-batch.js` not unit-testable; keep loop logic in engine/Python") and AC11 |

**Recommendation:** Option A
**Rationale:** The constraint and AC11 require tested pure cores; `qrspi-batch.js` is harness-coupled and untestable (ref: Q13, Q14), while every pure core is auto-discovered and CI-gated (ref: Q13). The JS↔Python worker seam is the established split: JS orchestrates, Python decides (ref: Discovered Patterns).
**NEW PATTERN?** No — this is the existing seam; only the new debate/convergence cores are net-new Python modules following the `synthesize`/`resolve_*` precedent.

### Decision 3: How the gate reviser lands a rewrite into the worktree

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Gate spawns the reviser with `OUTPUT_PATH = /tmp/phase-stage/<id>/design.md` (the Fix-A staging path), then runs `qrspi_persist.py --artifact design` to move it into the worktree | Reuses the exact producer persist contract (ref: Q3); `design` already in the enum; no new persist mode | Reviser's current contract targets a `review/` scratch path — its `OUTPUT_PATH`/spawn must be re-pointed for gate mode |
| B | Teach `qrspi_persist.py` a `review/`-aware mode so the reviser keeps its scratch path | Reviser def unchanged | New persist surface contradicting Fix-A's closed enum (ref: Q3); more risk |

**Recommendation:** Option A
**Rationale:** `qrspi_persist.py` already persists `/tmp/phase-stage/<id>/design.md → .worktrees/<id>/.qrspi/<id>/design.md` and `design` is already an enum member (ref: Q3); AC5 names the Fix-A staging path explicitly. The reviser is parameterized by `OUTPUT_PATH` (the only path it writes), so gate mode passes the staging path rather than the scratch path (ref: Q7) — advisory's scratch-only reviser contract is untouched because advisory never spawns it.
**NEW PATTERN?** No — reuses Fix-A persistence verbatim; only the gate spawn's `OUTPUT_PATH` differs.

### Decision 4: Ledger handling in gate mode

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Gate writes a distinct `mode` discriminator (e.g. `producer-gate`) on its ledger row, or skips the ledger entirely and relies on the committed `design-review-log.md` | Keeps on-demand-review analytics clean (the `mode:"on-demand-review"` + `agreement` discriminator stays untouched) (ref: Q9) | A new mode value to thread through the appender |
| B | Reuse `mode:"on-demand-review"` for gate rows | No new value | Conflates producer-gate rows with on-demand reviews; violates the discriminator's purpose (ref: Q9) |

**Recommendation:** Option A — **log only** (skip the ledger entirely; rely solely on the committed `design-review-log.md`). Reviewer decision on OQ1.
**Rationale:** Q9 establishes `mode:"on-demand-review"` + the `agreement` block as the consumer discriminator that gate mode must not pollute; the comment write and ledger append are already decoupled worker steps (ref: Q9), so gate can simply not append a row. AC9's committed `design-review-log.md` is the primary human-readable record and is sufficient; a `critic-metrics.jsonl` row adds no value for the gate path and keeps on-demand-review analytics clean by omission rather than by a new discriminator.
**NEW PATTERN?** No — gate mode writes no ledger row; `build_record`/`qrspi_metrics_append` remain on-demand-review-only, untouched.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Advisory mode regresses while adding gate mode (`/review-*` must stay byte-for-byte) | med | high | Branch around (never weaken) the comment + SHA-reassert block (ref: Q12); keep advisory inputs to the Python cores identical so Q14's test suite passes unchanged |
| Gate edits the **real** worktree `design.md` (no scratch copy, no SHA-lock) — a bad reviser rewrite or crash mid-loop corrupts the artifact before Finalize | med | high | The next-round full panel re-judges the reviser's output and re-catches any introduced regression — the reviser's self-report is never trusted (AC6/AC2); cap bounds rounds (AC7); persist is fail-closed on empty (ref: Q3); on **cap-exhaustion** publish anyway with residuals recorded in the committed `design-review-log.md` (not the PR body/comment) so a human still gates off the committed document (AC8, OQ4); on a **mid-loop crash** (reviser failure / `null` agent return) the gate hard-fails — reports the error and aborts (`failTicket`), does **not** publish, and the ticket retries next batch run, so a possibly-corrupt artifact is never shipped (AC8b, resolved OQ3) |
| Re-introducing a batch-side consumer of `critics.design.*` partially reverses the RUS-88 retirement of batch critics (config.example says batch runs none) (ref: Q6) | high | low | Document the intentional revival in `.claude/CLAUDE.md` + config.example (AC12); the maintainer's quality-over-cost mandate is explicit in the ticket; default-on is deliberate |
| Debate-until-stable fails to converge or oscillates within the debate cap, dropping a defended finding | low | med | Pure stabilization core with dissent preservation (a finding any lens still defends survives) + the configurable `debateCap` (default 3); unit-tested (AC3, AC11) |
| `design-review-log` not in the persist enum / not in the Finalize commit set → log silently lost | med | med | Add `design-review-log` to `ARTIFACTS` (ref: Q3) and to the Finalize stage-and-commit set (ref: Q15); cover the renderer with a `_test.py` |
| Inverted config default (`enabled: true`) diverges from the uniform opt-in (default OFF) convention, surprising operators | med | low | Explicit `resolve_enabled(cfg, True)` with a documented comment; AC10 + AC12 call out the always-on default; `enabled:false` restores today's path exactly |

## Open Questions

- OQ1: **RESOLVED (reviewer: log only)** — gate mode appends **no** `critic-metrics.jsonl` ledger row; the committed `design-review-log.md` is the sole record. See Decision 4.
- ~~OQ2~~ (RESOLVED, reviewer comment on this line): the debate cap is a **third configurable key** `debateCap` under `critics.design.reviewLoop` (default **3**), not a fixed constant — read via `_pos_int_or`, mirroring `maxRounds`. Folded into AC3, AC10, and the `qrspi_critics_config.py` Delta.
- ~~OQ3~~ (RESOLVED, reviewer comment on this line): a **mid-loop crash is a hard fail**. On reviser failure or a `null` agent return mid-loop (the agent-seam failure contract returns bare `null`), the gate does **not** publish — it **reports the error and aborts** (`failTicket`); the ticket is **retried on the next batch run**. This is deliberately distinct from cap-exhaustion (AC8), which is a *bounded, converged-enough* outcome that publishes-anyway with residuals; a crash is an *unexpected failure* with no trustworthy last-good state to publish, so it surfaces loud and retries rather than shipping a possibly-corrupt artifact. Folded into AC8 (its publish-anyway path is scoped to cap-exhaustion only) and the "bad reviser rewrite or crash mid-loop" Risk Register row.
- ~~OQ4~~ (RESOLVED, reviewer comment on this line): residual findings go in a **committed document** — the `design-review-log.md` already committed alongside the design artifacts (AC9) — **not** the PR body and **not** a PR comment. The gate makes **no** `gh api … PATCH` of the PR body and **no** comment write; the committed log is the single channel for residuals. Folded into AC8 (publish-anyway records residuals in the log, not the PR body), the `doDesign` Delta, and the cap-exhaustion Risk Register row.
