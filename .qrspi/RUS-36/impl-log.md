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

## Session 2 — Slice 2: `websocket` + `multi_tenancy` chains

**Timestamp:** 2026-06-11T00:00:00Z
**Tasks completed:** T12, T13, T14, T15, T16, T17, T18
**Tasks failed:** none
**Tests:**

- `cd evals && test -s <each of 4 fixtures>` → 4 present/non-empty, 0 missing (`questions_websocket.md`, `research_websocket.md`, `questions_multi_tenancy.md`, `research_multi_tenancy_sparse.md`)
- Structural checks (grader-regex, run from cwd=`evals/`): both questions fixtures → 13 `- QN:` lines each (8≤n≤15), 13 `**Target:**` each (≥Q), 6 `## ` sections each; both research fixtures → 13 `## QN:` headers with 13 `**Answer:**` / 13 `**Evidence:**` each
- Chain-consistency: `ORD-892` present in both `questions_websocket`/`research_websocket`; `PLAT-1205` present in both `questions_multi_tenancy`/`research_multi_tenancy_sparse`
- Sparse-for-right-reason: `research_websocket.md` = 14 `file:line` citations / 4 honest NOT FOUND; `research_multi_tenancy_sparse.md` = **0** `file:line` citations / **11** NOT FOUND (genuinely thin)
- `build_messages()` from cwd=`evals/` for case_004 / case_006 / case_014 (+ case_002) → all four new fixtures resolve and their content renders in the user message

**Deviations from structure.md:**

- none

**Deviations from plan.md:**

- none

**Notes for next session:**

- Slice 2 fixtures are **input context** for their consuming cases (case_004 questions→research, case_006 design new-pattern, case_014 design sparse/fabrication, case_002 ticket→questions), NOT graded outputs — the agent produces a fresh output from them. They only need to be well-formed and shape-consistent; grade.py validators run against the agent's `output`, not these files.
- `websocket` is the canonical **NEW PATTERN** chain: `research_websocket.md` deliberately establishes that NO real-time transport (WebSocket/SSE/long-poll), connection registry, or connection metrics exist today (Q3/Q6/Q11/Q13 = NOT FOUND), and that an `order.status_changed` event is already emitted but only audit-logged — this is what case_006 expects the design agent to flag as a new pattern with polling as a viable alternative.
- `multi_tenancy` sparse trait: `research_multi_tenancy_sparse.md` answers all 13 QN with NOT FOUND / "unknown" and ZERO `file:line` citations (Dependencies/Implicit contracts all `unknown`); the leading blockquote explicitly labels it INCOMPLETE/SPARSE and warns against fabrication. This is the case_014 fabrication trap — keep it citation-free if ever edited.
- `questions_multi_tenancy.md` is the backfilled HONEST upstream (RQ2) anchoring the sparse research to a real PLAT-1205 question set; the sparse research's `## QN:` headers are verbatim copies of those question lines, so the chain reads coherently even though the answers are empty.
- All four Slice-2 fixtures follow the exact Slice-1 canonical shapes (see Session 1 notes) — same regexes, same `## QN:` / `**Answer:**` / `**Evidence:**` / fenced-snippet structure. No new shape was introduced.

---

## Session 3 — Slice 3: `billing_migration` chain (new upstream + design leaf)

**Timestamp:** 2026-06-11T00:00:00Z
**Tasks completed:** T19, T20, T21, T22, T23, T24
**Tasks failed:** none
**Tests:**

- `cd evals && test -s <each of 4 fixtures>` → 4 present/non-empty, 0 missing (`ticket_billing_migration.md`, `questions_billing_migration.md`, `research_billing_migration.md`, `design_billing_migration.md`)
- Chain-consistency: ticket ID **PAY-733** present in all 4 fixtures (`grep -lc`)
- Structural shape (grader-regex, run from cwd=`evals/`): questions → 6 `## ` sections, 13 `- Q:` lines, 13 `**Target:**`; research → 13 `## QN:` headers / 13 `**Answer:**` / 13 `**Evidence:**` / 13 `` `file:line` `` citations; design → 6 `## ` sections, **0** code fences
- Design `(ref: QN)` validity: design cites Q1–Q13, all ⊆ the 13 questions in `questions_billing_migration.md` (zero out-of-range), and is consistent with the research (same `Subscriptions.active` accessor, `source_legacy_id` unique-index idempotency, `runBatch`/`job_cursors` resumability, gateway idempotency-key charge dedup)
- cwd render: `build_messages()` from cwd=`evals/` for **case_008** (the consuming case — structure phase, context.files = `fixtures/design_billing_migration.md`) → resolves and renders; `PAY-733` and `Subscriptions.active` present in the rendered user message, no MISSING/not-found markers

**Deviations from structure.md:**

- none

**Deviations from plan.md:**

- none

**Notes for next session:**

- Ticket ID for this fully-new chain is **PAY-733** (no pre-existing ticket; T19 minted it). ACs threaded verbatim: "All active legacy subscriptions are copied into billing_subscriptions", "The migration is idempotent and resumable after an interruption", "No subscription is charged twice during or after the migration", "Migrated rows preserve the original next_renewal_at timestamp".
- `design_billing_migration.md` is the **graded leaf input** for **case_008** (structure phase, "structure_large_feature_splitting" — asserts `slice_count('structure.md') >= 5`). It is the ONLY suite.json reference for this chain; the ticket/questions/research are backfilled upstream (RQ2) to make the design a real chain output, not graded directly.
- All four fixtures follow the exact Slice-1 canonical shapes (Session 1 notes) — `- Q:` lines with `**Target:**`, `## QN:` research headers with `**Answer:**`/fenced `**Evidence:**`/backtick `file:line`/`**Dependencies:**`/`**Implicit contracts:**`, six-section design with `(ref: QN)` and no code fences. No new shape introduced.
- The design deliberately has two `NEW PATTERN? No` decisions (reuse `runBatch`; reuse `active`+gateway-key dedup) — this chain composes existing patterns, in contrast to Slice 2's `websocket` new-pattern chain. Risk Register has 3 rows (≥2). Verification MUST run from `cd evals`.

---
