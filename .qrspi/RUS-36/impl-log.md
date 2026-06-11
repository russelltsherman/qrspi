# Implementation Log — Backfill 17 missing eval fixtures

## Session 1 — Slice 1: `rest_endpoint` chain

**Timestamp:** 2026-06-11T00:00:00Z
**Tasks completed:** T1, T2, T3, T4, T5, T6, T7, T8, T9, T10, T11
**Tasks failed:** none
**Tests:**

- `cd evals && test -s <each of 7 fixtures>` → 7 present/non-empty, 0 missing
- `grade.py` gold-standard checks against the fixtures (run from cwd=`evals/`) → 14 passed, 0 failed (all_questions_have_target, no_solution_language ×2, all_answers_have_evidence, all_evidence_has_file_citations, current_state_has_citations, no_code_blocks, all_slices_have_verification, all_slices_have_context_cost, all_files_marked_new_or_modify, risk_register_min_entries≥2, pattern_decisions_have_options≥2, all_modify_steps_have_current_after, all_slices_have_verify_checkpoint)
- `build_messages()` from cwd=`evals/` for case_005 / case_010 / case_011 → all Slice-1 fixtures resolve and render with DASH-417 present

**Deviations from structure.md:**

- none

**Deviations from plan.md:**

- none

**Notes for next session:**

- Anchor ticket is `evals/fixtures/ticket_rest_endpoint.md`, ticket ID **DASH-417**. ACs copied verbatim down the chain (`GET /api/users/:id/preferences`, p95 < 200ms, 401 unauthorized, 403 unless admin).
- Canonical fixture shapes are now established and validated against `scripts/grade.py`:
  - Questions: `- QN:` lines (hyphen-space-Q-number-colon), each followed by `**Target:**`; six `## ` sections.
  - Research: `## QN: <verbatim question>` headers, each with `**Answer:**`, a fenced `**Evidence:**` snippet, a `` `path:line` `` citation, `**Dependencies:**`, `**Implicit contracts:**`; plus `## Discovered Patterns` and `## Inconsistencies`. The grader counts one `**Answer:**`/`**Evidence:**` per `## QN:` and requires ≥1 backtick `file:line` citation per Evidence block.
  - Design: six `##` sections (Current State, Desired End State, Delta, Pattern Decisions, Risk Register, Open Questions); every Current-State paragraph carries a `(ref: QN)`; NO fenced code blocks; Pattern Decisions use Option A/B tables; Risk Register ≥2 rows.
- `plan_rest_endpoint_slice1.md` is a STRICT verbatim line-subset of Slice 1 in `plan_rest_endpoint.md` (verified). Keep this relationship when authoring other `_slice1` plans (Slices 3/4 if applicable).
- All `suite.json` `context.files` are resolved relative to **process cwd**, so every verification MUST run from `cd evals` — never repo root (root silently skips).
- Slice 5 (`worktree_session1.md`) and other downstream fixtures are NOT yet present; case_011 currently renders only its two Slice-1 inputs, as expected.

---
