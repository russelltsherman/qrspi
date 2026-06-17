# Implementation Log — Phase review-panel commands (/review-*): on-demand node-validity review panels

## Session 1 — Slice 1: Pure review seams + toplevel comment relaxation

**Timestamp:** 2026-06-17T20:38:01Z
**Tasks completed:** T1, T2, T3, T4, T5, T6, T7, T8, T9
**Tasks failed:** none
**Tests:**

- `python3 scripts/run_tests.py review` → 2 passed, 0 failed (qrspi_review_agreement_test.py, qrspi_review_record_test.py)
- `python3 scripts/run_tests.py comment_reply` → 1 passed, 0 failed (qrspi_comment_reply_test.py, with the new relaxation cases)
- `python3 scripts/qrspi_review_agreement.py` smoke → prints `{"panelVerdict": "pass", "humanVerdict": null, "agreement": "pending"}` (pass+None ⇒ pending, as required)
- `python3 scripts/run_tests.py` (full suite) → 41 passed, 0 failed (no regressions)

**Deviations from structure.md:**

- none

**Deviations from plan.md:**

- none

**Notes for next session:**

- New pure modules landed: `scripts/qrspi_review_agreement.py` (exposes `compute(panel_pass, human_decision) -> {panelVerdict, humanVerdict, agreement}`) and `scripts/qrspi_review_record.py` (exposes `build_record(phase, rounds, terminal_action, agreement) -> ReviewRecord`).
- `build_record` signature is exactly `build_record(phase, rounds, terminal_action, agreement)`. Its `rounds` argument is the per-lens/per-round VERDICT list (each `{lens, pass, findings}`) — it is forwarded to `qrspi_critic_metrics.build_record(rounds, terminal_action, phase=phase)`, which derives the `{lens, pass, findingsCount}` rounds shape itself. Do NOT pass a pre-built `{lens, pass, findingsCount}` rounds list; pass the raw verdicts. The returned record is the base `{phase, rounds, terminalAction}` plus `agreement` (verbatim) and `mode: "on-demand-review"`.
- `terminal_action` must be one of the base builder's `VALID_TERMINAL_ACTIONS = {converged, cap_reached, exhausted, aborted}`. `revise` is NON-terminal and raises `ValueError` (fail-closed) — only build a record once the loop has terminated. Map `next_action` CLI's `converged`/`cap_reached` → those same tokens; `exhausted`/`aborted` are the defensive tails.
- `compute` NEVER raises. Human decision normalization is case-insensitive and whitespace-tolerant: `APPROVED→approved`, `CHANGES_REQUESTED→changes_requested`, `COMMENTED→commented`, `None`/unknown/non-string → `humanVerdict: null`. `commented` and `null` both yield `agreement: "pending"` (a comment is not a decisive verdict; never a false disagreement).
- `scripts/qrspi_comment_reply.py` relaxation: `--comment-id` is now OPTIONAL at the parser level (default `None`). A guard in `main()` still rejects inline mode without an id (fail-closed, returns error envelope). `--ticket` and `--reply-mode` remain REQUIRED — every toplevel synopsis-post call MUST pass `--ticket <id> --pr <n> --reply-mode toplevel --body-file <path>` and may OMIT `--comment-id`. The `error_envelope(None, ...)` path tolerates a `None` id (reports `inReplyToId: null`).
- `qrspi_review_record.py` does a sibling import of `qrspi_critic_metrics` via a `sys.path.insert(0, dirname(__file__))` preamble, matching the other scripts' self-locating import pattern.

---

## Session 2 — Slice 2: /review-design end-to-end (AC1 + AC2)

**Timestamp:** 2026-06-17T21:00:00Z
**Tasks completed:** Steps 10, 11, 12 (no-op), 13 (no-op), 14, 15, 16, 17, 18, 19, 20, 21, 22, 23
**Tasks failed:** none
**Tests:**

- `python3 scripts/run_tests.py review` → 2 passed, 0 failed (Slice 1 dependency modules green)
- `python3 scripts/run_tests.py comment_reply` → 1 passed, 0 failed (toplevel relaxation the synopsis post relies on)
- `python3 scripts/run_tests.py` (full suite) → 41 passed, 0 failed (no regressions)
- Contract-chain smoke (the exact invocations the SKILL prescribes): `qrspi_critic_synthesize.py` → `{pass, findings}`; `qrspi_critic_loop.py --round/--max-rounds` → `converged`/`revise`/`cap_reached` for the round 0-pass / round 0-fail / round 2-fail cases respectively; `qrspi_review_record.build_record(phase="design", rounds=[{lens,pass,findings}], terminal_action="converged", agreement=compute(True, None))` → `{phase:"design", rounds:[{lens,pass,findingsCount}], terminalAction:"converged", agreement:{panelVerdict:"pass", humanVerdict:null, agreement:"pending"}, mode:"on-demand-review"}` — matches AC2 (no human review ⇒ `agreement:"pending"`).
- Referenced agents exist: `qrspi-design-critic-design-review` (lens) and `qrspi-design` (producer-as-reviser / open-question pass).

**Deviations from structure.md:**

- none

**Deviations from plan.md:**

- none — Steps 12/13 are no-ops by design (the `next_action` CLI already exists at `qrspi_critic_loop.py:118-159`; no shim added, no test added). Steps 10/11 are read-to-confirm-contracts.

**Verification notes (sandbox limitations — flagged in plan):**

- `.claude/skills/review-design/SKILL.md` was present as a faithful, complete artifact in the worktree (untracked) matching plan Steps 14-22; validated via the **skill-creator** skill rather than regenerated. skill-creator review confirms: frontmatter `name: review-design`, `allowed-tools: Agent, Bash, Read`; the description is strong for triggering (pushy + concrete trigger phrases `/review-design RUS-89` / "review the design for RUS-42" / "is the design for RUS-50 sound?" + disambiguation against `/review-plan` / `/review-implementation` / `/review`); the 8-step body is coherent and contract-faithful (correct `converged|revise|cap_reached` branching, `--max-rounds 3`, `{lens,pass,findings}` round-entry shape the base builder wants, `converged|cap_reached` terminal action, relaxed toplevel `qrspi_comment_reply.py` invocation with `--ticket`/`--reply-mode` required + `--comment-id` omitted, and a head-SHA propose-only invariant check).
- The skill-creator `run_eval`/`run_loop` triggering harness is **not** trustworthy in this sandbox (returns bogus uniform results — plan verification-gate note). The substitute direct `claude -p` routing probe is also **not runnable to completion** from inside this sandboxed implement subagent: an agentic `claude -p` review run exceeds a workable timeout (timed out at 180s). Triggering quality was therefore assessed via the direct description-quality review (above) only. The manual e2e bullets (synopsis posts to a live `<id>/design` PR; ledger gains a `mode:"on-demand-review"` row; PR head SHA unchanged; re-run resolves `agreement` against a present `reviewDecision`) require a live PR + network and are deferred to a real-repo run — NOT verifiable from this isolated worktree.

**Notes for next session:**

- Slice 2's `.claude/skills/review-design/SKILL.md` is the structural template for Slices 3 (`review-plan`) and 4 (`review-implementation`): copy its scratch-loop contract verbatim and swap lens/producer/artifact/PR-branch. Slice 3 first creates the lens agent `.claude/agents/qrspi-plan-critic-plan-review.md` (mirror `qrspi-design-critic-design-review.md`'s named-PATH-input + `{pass, findings}` + read-only contract); Slice 4 creates `.claude/agents/qrspi-impl-critic-impl-review.md` likewise.
- Per plan-time OQ1 resolution: Slices 3/4 OMIT the post-loop open-question pass (Step 20 here is design-phase-only). Drop that step in those SKILLs.
- The synopsis post invocation to reuse verbatim: `python3 scripts/qrspi_comment_reply.py --ticket <id> --pr <n> --reply-mode toplevel --body-file <path>` (`--comment-id` omitted; `--ticket` + `--reply-mode` required).
- The ledger append invocation requires `--ticket`, `--record`, AND `--run-id` (it stamps `ticketId`/`timestamp`/`runId`). Slice 2 uses a per-invocation run id like `review-design-<id>-$(date -u +%Y%m%dT%H%M%SZ)`; mirror that pattern (`review-plan-...`, `review-implementation-...`).
- The leftover stray `.review-scratch/` dir (a prior-run scratch copy, NOT produced by the authored SKILL — the SKILL writes scratch to `/tmp/phase-stage/<id>/review/`) was removed; the authored SKILL never writes into the worktree's `.review-scratch/`.

---
