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
