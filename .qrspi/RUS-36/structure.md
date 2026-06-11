# Structure Outline — Backfill 17 missing eval fixtures

**Design basis:** design.md @ 2026-06-09T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** draft

> This ticket produces **content artifacts** (Markdown/txt fixtures + a README),
> not code. There are no runtime types or function signatures to define. The
> "types" and "contracts" below are therefore the **structural shapes** the
> fixtures and README must conform to — the schemas a downstream consumer
> (eval case, future integrity test, or human curator) relies on. Slices are
> organized by **scenario chain**, the project's own unit of fixture cohesion
> (same ticket-ID/ACs thread down each `<scenario>` stem), because each chain is
> independently authorable and verifiable end-to-end (load from cwd=`evals/`)
> without the others.

## New Types

These are the structural shapes (not runtime types) every produced artifact must match.

- `Ticket.md { H1 "# Ticket: <ID>", "## Title", "## Description", "## Acceptance Criteria" (- [ ] checkboxes), "## Constraints", "## Out of Scope" }` — 850–1626 bytes, snake_case filename `ticket_<scenario>.md` (ref: design §Current State, Q3)
- `Questions.md { six "##" sections, each 8–15 "- QN:" lines, each line with "**Target:**" }` — `questions_<scenario>.md` (ref: design §Desired End State, Q5)
- `Research.md { per-Q "**Answer:**" / "**Evidence:**" / file:line / "**Dependencies:**" / "**Implicit contracts:**", plus "## Discovered Patterns", "## Inconsistencies" }` — `research_<scenario>.md` (ref: design §Desired End State, Q5)
- `Design.md { six design sections, "(ref: QN)" citations, NO code blocks }` — `design_<scenario>.md` (ref: design §Desired End State, Q5)
- `Structure.md { conforms to .qrspi/templates/structure.md }` — `structure_<scenario>.md` (ref: Q5)
- `Plan.md { conforms to .qrspi/templates/plan.md; multi-slice }` — `plan_<scenario>.md`; `plan_<scenario>_slice1.md` is a faithful Slice-1 subset (ref: Q5, Q10)
- `Worktree.md { conforms to .qrspi/templates/worktree.md; session DAG }` — `worktree_<scenario>.md` (ref: Q5)
- `ImplLog.md { conforms to impl-log template }` — `impl_log_<scenario>.md` (ref: Q5)
- `GitDiff.txt { unified-diff text }` — `git_diff_<scenario>.txt` (ref: Q3, Q7)
- `BrokenContract` (fixture trait) — a concretely unimplementable type signature carried verbatim across `structure → plan → worktree-session` so case_012 fails behaviorally for the right reason (ref: Q9, design Risk Register)
- `SparseResearch` (fixture trait) — `research_multi_tenancy_sparse.md` is deliberately thin to trigger case_014 fabrication-detection (ref: Q9, design Risk Register)
- `README.md provenance table row { fixture, scenario, source_ticket, provenance ∈ {generated, hand-edited}, chain }` — machine-readable, fixed-vocabulary columns (ref: AC3, RQ4)

## Modified Types

- none — no runtime/code types are modified. The harness, `suite.json`, and `docs/eval-system.md` are unchanged per design §Delta (suite/doc already in sync, ref: Q11; harness silent-skip left as-is, RQ3).

## Contracts

Cross-slice invariants every slice must uphold (these are the consistency guarantees, not function signatures):

- `chain-consistency(scenario)` — the ticket ID and Acceptance-Criteria text are copied **verbatim** down every same-stem fixture in a chain (`ticket_` → `questions_` → `research_` → `design_` → `structure_` → `plan_` → `worktree_`); a curated leaf is the gold-standard output of its predecessor (ref: design Risk Register, Q2, Q3)
- `slice1-subset(plan_<s>.md, plan_<s>_slice1.md)` — the `_slice1` plan is a faithful Slice-1 subset of the full multi-slice plan (ref: Q10)
- `loads-cleanly(fixture)` — every `context.files` reference in `suite.json` resolves under **cwd=`evals/`** and the file is **non-empty** and shape-matches its phase template; verified by running `build_messages()` from cwd=`evals/`, NOT by harness "OK" (ref: Q1, Q8, Q12, Q14, design Risk Register)
- `broken-contract-carried(structure_broken_contract.md, plan_broken_contract_slice1.md, worktree_session_broken_contract.md)` — the same unimplementable signature appears in all three so case_012 fails behaviorally (ref: Q9)
- `provenance-parsable(README.md)` — every produced fixture has exactly one machine-readable row with a fixed-vocabulary `provenance` value (ref: AC3, RQ4)
- `no-orphans()` — no fixture is produced that lacks a `suite.json` reference, and every referenced-missing fixture is produced (the 17 acceptance fixtures) (ref: Q11, Q4)

## Slice 1: `rest_endpoint` chain (largest, defines the canonical pattern)

**Goal:** Produce the full `rest_endpoint` scenario chain — the reference example every other chain copies — so its eval cases (case_005 questions+research, case_010 worktree-from-plan, case_011 implement-from-slice1, plus the diff/PR consumer) load cleanly from cwd=`evals/`. Establishes the canonical shape and the `plan` ↔ `plan_slice1` subset relationship.
**Files touched:**

- ✨ `evals/fixtures/questions_rest_endpoint.md` — questions fixture (six `##`, 8–15 `- QN:` w/ `**Target:**`)
- ✨ `evals/fixtures/research_rest_endpoint.md` — research fixture (per-Q Answer/Evidence/file:line/Dependencies/Implicit contracts + Discovered Patterns + Inconsistencies)
- ✨ `evals/fixtures/design_rest_endpoint.md` — design fixture (six sections, `(ref: QN)`, no code blocks)
- ✨ `evals/fixtures/structure_rest_endpoint.md` — structure fixture (matches structure template)
- ✨ `evals/fixtures/plan_rest_endpoint.md` — full multi-slice plan (case_010)
- ✨ `evals/fixtures/plan_rest_endpoint_slice1.md` — faithful Slice-1 subset of the above (case_011)
- ✨ `evals/fixtures/git_diff_rest_endpoint.txt` — unified-diff fixture (the one non-`.md` reference)
**Verification:**
- [ ] All 7 files exist, non-empty, scenario-stem-consistent (ticket ID + ACs copied verbatim from existing `evals/fixtures/ticket_rest_endpoint.md`)
- [ ] `plan_rest_endpoint_slice1.md` content is a strict subset of `plan_rest_endpoint.md`'s Slice 1
- [ ] From cwd=`evals/`, `build_messages()` resolves each path and its content appears in the rendered message for case_005 / case_010 / case_011 (manual, do NOT trust harness "OK")
**Context cost:** L
**Depends on:** none (anchors to the existing `ticket_rest_endpoint.md`)

## Slice 2: `websocket` + `multi_tenancy` chains

**Goal:** Produce the `websocket` questions/research and the `multi_tenancy` questions + sparse research, both anchored to their existing tickets, so their eval cases (incl. case_014 fabrication-detection for the sparse variant) load cleanly. `multi_tenancy` questions backfill anchors the sparse research to a real upstream (RQ2).
**Files touched:**

- ✨ `evals/fixtures/questions_websocket.md` — anchored to existing `ticket_websocket.md`
- ✨ `evals/fixtures/research_websocket.md` — research fixture for websocket
- ✨ `evals/fixtures/questions_multi_tenancy.md` — anchored to existing `ticket_multi_tenancy.md` (backfilled upstream, RQ2)
- ✨ `evals/fixtures/research_multi_tenancy_sparse.md` — deliberately thin/sparse research (case_014 fabrication-detection)
**Verification:**
- [ ] All 4 files exist, non-empty; ticket IDs/ACs copied verbatim from `ticket_websocket.md` and `ticket_multi_tenancy.md`
- [ ] `research_multi_tenancy_sparse.md` is genuinely thin (missing/under-specified answers) so case_014 detects fabrication for the right reason
- [ ] From cwd=`evals/`, paths resolve and content renders for the consuming cases (manual)
**Context cost:** M
**Depends on:** Slice 1 (reuses the questions/research shape established there)

## Slice 3: `billing_migration` chain (backfilled upstream + design leaf)

**Goal:** Backfill the entire `billing_migration` upstream so `design_billing_migration.md` is the gold-standard output of a real `ticket → questions → research → design` chain rather than a standalone author (RQ2). This chain has no existing ticket, so all four files are new and must be internally consistent.
**Files touched:**

- ✨ `evals/fixtures/ticket_billing_migration.md` — backfilled root ticket (`# Ticket: <ID>` shape)
- ✨ `evals/fixtures/questions_billing_migration.md` — backfilled questions
- ✨ `evals/fixtures/research_billing_migration.md` — backfilled research
- ✨ `evals/fixtures/design_billing_migration.md` — the acceptance leaf (six sections, `(ref: QN)`, no code blocks)
**Verification:**
- [ ] All 4 files exist, non-empty; one ticket ID + AC set threads verbatim through all four
- [ ] `design_billing_migration.md` cites questions that exist in `questions_billing_migration.md` and is consistent with `research_billing_migration.md`
- [ ] From cwd=`evals/`, the design fixture resolves and renders for its consuming case (manual)
**Context cost:** M
**Depends on:** Slice 1 (reuses ticket/questions/research/design shapes)

## Slice 4: broken-contract adversarial set (hand-authored)

**Goal:** Hand-author the deliberately infeasible `_broken_contract` set so case_012 fails behaviorally (agent reports infeasibility via `impl_log_has_deviations` + llm_judge) for the right reason — a concretely unimplementable signature carried verbatim across structure → plan → worktree-session.
**Files touched:**

- ✨ `evals/fixtures/structure_broken_contract.md` — introduces the unimplementable contract
- ✨ `evals/fixtures/plan_broken_contract_slice1.md` — same broken contract carried into the plan slice
- ✨ `evals/fixtures/worktree_session_broken_contract.md` — same broken contract in the session DAG
**Verification:**
- [ ] All 3 files exist, non-empty; the SAME unimplementable type signature appears verbatim in all three (`broken-contract-carried` contract)
- [ ] The contract is genuinely infeasible (not merely hard), so case_012 cannot pass by accident
- [ ] From cwd=`evals/`, the three paths resolve and render for case_012 (manual)
**Context cost:** M
**Depends on:** Slice 1 (reuses structure/plan/worktree shapes; the broken signature deviates from those shapes intentionally)

## Slice 5: worktree session + impl-log fixtures

**Goal:** Produce the remaining honest leaf fixtures — the worktree session DAG and the complete implementation log — anchored to the `rest_endpoint` chain from Slice 1, so their consuming cases load cleanly.
**Files touched:**

- ✨ `evals/fixtures/worktree_session1.md` — worktree session-DAG fixture (matches worktree template)
- ✨ `evals/fixtures/impl_log_complete.md` — complete implementation-log fixture
**Verification:**
- [ ] Both files exist, non-empty, and match their templates
- [ ] Scenario-stem consistent with the `rest_endpoint` chain (ticket ID/ACs threaded)
- [ ] From cwd=`evals/`, paths resolve and render for the consuming cases (manual)
**Context cost:** S
**Depends on:** Slice 1 (anchors to the `rest_endpoint` plan/structure)

## Slice 6: machine-readable provenance README + full integrity sweep

**Goal:** Author `evals/fixtures/README.md` as the machine-readable provenance table covering all produced fixtures (the 17 acceptance + the backfilled upstream + the 4 existing tickets for context), then run the final cross-fixture integrity sweep: every `suite.json` `context.files` reference resolves and is non-empty from cwd=`evals/`, and no orphans exist in either direction. This is the closing validation step for the whole ticket.
**Files touched:**

- ✨ `evals/fixtures/README.md` — fixed-vocabulary table: `fixture`, `scenario`, `source_ticket`, `provenance` ∈ {`generated`, `hand-edited`}, `chain`
**Verification:**
- [ ] README has exactly one row per produced fixture, all `provenance` values from the fixed vocabulary (`provenance-parsable` contract); broken set marked `hand-edited`, curated chains marked per Decision 1
- [ ] Every `context.files` reference in `suite.json` now exists and is non-empty when checked from cwd=`evals/` (whole-suite `loads-cleanly` + `no-orphans` sweep)
- [ ] The 17 acceptance fixtures from `docs/eval-system.md:80-89` are all present (cross-check against that list)
**Context cost:** S
**Depends on:** Slices 1–5 (must enumerate every produced fixture)

---

## Unverified Assumptions

These design claims could not be mapped to a concrete file shape from the design + research alone and need confirmation during planning/implementation (the structure agent is read-restricted to design + template, so the templates themselves and `suite.json` were not inspected):

- **Exact required sections of the structure / plan / worktree / impl-log / PR templates.** The design says fixtures "match their templates" (ref: Q5) but the literal section list for `structure_*`, `plan_*`, `worktree_*`, `impl_log_*`, and any PR fixture is only known for questions/research/design/ticket. The implementer must read `.qrspi/templates/{structure,plan,worktree,...}.md` to author conforming content.
- **Which eval case consumes `git_diff_rest_endpoint.txt` and `impl_log_complete.md`, and the exact unified-diff/impl-log shape those cases assert.** The design names the files (ref: Q3, Q7) but does not pin the consuming case's assertions, so the diff/log content shape is unverified.
- **The precise `suite.json` `context.files` paths** (e.g. whether referenced as `fixtures/<name>` and the full count of references per case). Design says 21 references / 17 missing (ref: Q4) and "no orphans" (ref: Q11), but the literal mapping of file→case was not re-read here; the final integrity sweep in Slice 6 must read `suite.json` to confirm.
- **The README row count.** Design says "the 17 + the backfilled upstream + the 4 existing tickets" — that enumerates to roughly 17 + 3 (billing upstream) + 1 (multi_tenancy questions, if counted as upstream not acceptance) + 4 existing = ~24–25 rows, but the exact backfilled-upstream set vs. acceptance set boundary should be reconciled against the final file list before writing the table.
- **Whether any `_session_broken_contract` vs `worktree_session_broken_contract` naming is exact.** Design uses `worktree_session_broken_contract.md` in the Delta list (ref: §Delta) but the suite.json reference name must be confirmed at implementation time to avoid a silent cwd-skip.
