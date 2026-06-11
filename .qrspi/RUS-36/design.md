# Design — Backfill 17 missing eval fixtures

**Ticket:** RUS-36
**Research basis:** research.md @ 2026-06-09T00:00:00Z
**Generated:** 2026-06-09T00:00:00Z
**Status:** revised — all reviewer answers incorporated (see Resolved Questions)

## Current State

The eval harness references fixtures from each case as `context.files` entries written relative to `evals/`, e.g. `fixtures/ticket_rest_endpoint.md` (ref: Q1). The only loader is `build_messages()` in `scripts/run_eval.py`; it does not join against `evals/fixtures/` but passes the string straight to `os.path.exists()` and `open()`, so resolution is relative to the process cwd and the harness must run from inside `evals/` (ref: Q1). A missing fixture does not raise — every file is guarded by `if os.path.exists(file_path):`, so an absent fixture is silently skipped with no error, warning, or exit code (ref: Q1, ref: Q14). The per-case console line reports "OK" because the stub `execute_single` never reads the file and never raises; there is no way today to identify which case lost which fixture from harness output (ref: Q14).

Of 21 distinct fixture references in `suite.json`, only 4 exist — all `ticket_*.md` — and 17 are missing; the missing set exactly matches the list in `docs/eval-system.md:80-89` with no drift (ref: Q4). The 4 present fixtures are `ticket_rest_endpoint.md` (DASH-417), `ticket_websocket.md` (ORD-892), `ticket_multi_tenancy.md` (PLAT-1205), and `ticket_15_acceptance_criteria.md` (RPT-2100) (ref: Q3). They establish the naming convention `<phase>_<scenario>.md`, snake_case, phase prefix first, with variant suffixes `_slice1`, `_broken_contract`, `_sparse`, `_session1`, `_session_broken_contract`; one non-`.md` fixture exists by reference, `git_diff_rest_endpoint.txt` (ref: Q3, ref: Q7). Ticket content uses H1 `# Ticket: <ID>` then `## Title`, `## Description`, `## Acceptance Criteria` (as `- [ ]` checkboxes), `## Constraints`, `## Out of Scope`, sized 850–1626 bytes (ref: Q3).

Fixtures share a scenario stem across phases (`ticket_rest_endpoint` → `questions_rest_endpoint` → `research_rest_endpoint` → `design_rest_endpoint` → `structure_rest_endpoint` → `plan_rest_endpoint`), and a case wires same-stem fixtures together — case_005 loads ticket+questions+research for `rest_endpoint` (ref: Q2, ref: Q3). Each phase has a template in `.qrspi/templates/` defining required sections (ref: Q5). "Loads cleanly" means only that the path exists at `build_messages` time; there is no parse, schema, or non-empty check on fixtures inside the harness, and `grade.py` runs against agent output, not fixtures (ref: Q8). No stdlib unit test asserts that every `context.files` reference exists on disk, so the 17 missing fixtures are caught by no automated check (ref: Q13).

The three "broken" fixtures (`structure_broken_contract.md`, `plan_broken_contract_slice1.md`, `worktree_session_broken_contract.md`) feed case_012; success is behavioral — the agent reporting an infeasible contract via `impl_log_has_deviations` and an llm_judge — not a harness error (ref: Q9). `plan_rest_endpoint.md` is the whole multi-slice plan consumed by case_010 (worktree); `plan_rest_endpoint_slice1.md` is the Slice 1 subset consumed by case_011 (implement) (ref: Q10). No orphans exist in either direction between the ticket list, the doc, and suite.json (ref: Q11).

## Desired End State

| Acceptance Criterion | System behavior after this ships |
|---|---|
| All 17 fixtures exist in `evals/fixtures/` | The 17 files enumerated in `docs/eval-system.md:80-89` / suite.json's missing set are present on disk, each named `<phase>_<scenario>.md` (or `.txt` for the diff), scenario-stem-consistent with their ticket (ref: Q3, ref: Q4). |
| Each fixture loads cleanly when referenced by its eval case | Every `context.files` reference in suite.json resolves under cwd=`evals/`; since the loader only checks existence and non-emptiness is not enforced by the harness (ref: Q1, ref: Q8), each new fixture is non-empty and shape-matches its phase template so it is a usable gold-standard input (ref: Q5). |
| A README in `evals/fixtures/` documents which were generated, which were hand-edited, and from what source ticket | `evals/fixtures/README.md` lists each of the 17 (plus the 4 existing tickets for context) in a **machine-readable** table (fixed-vocabulary columns `fixture`, `scenario`, `source_ticket`, `provenance` ∈ {`generated`, `hand-edited`}, `chain`) so a future integrity/freshness check can parse provenance, not only read prose (ref: Q2, ref: Q3; reviewer RQ4). |

Content shape per fixture follows the consuming case's asserted sections: questions fixtures carry the six `##` sections with 8–15 `- QN:` lines each with `**Target:**`; research fixtures carry per-Q `**Answer:**/**Evidence:**/file:line/**Dependencies:**/**Implicit contracts:**` plus `## Discovered Patterns` and `## Inconsistencies`; design fixtures carry the six design sections with `(ref: QN)` citations and no code blocks; structure/plan/worktree/impl-log/pr fixtures match their templates (ref: Q5). Broken fixtures contain a genuinely unimplementable contract carried consistently across structure→plan→worktree-session (ref: Q9). `plan_rest_endpoint_slice1.md` is a faithful Slice-1 subset of `plan_rest_endpoint.md`, and the same ticket ID/ACs thread down each scenario chain (ref: Q3, ref: Q10).

## Delta

New files — the 17 fixtures required by the missing set in `docs/eval-system.md:80-89` / suite.json (the acceptance target):
- Questions: `questions_rest_endpoint.md`, `questions_websocket.md`, `questions_multi_tenancy.md`
- Research: `research_rest_endpoint.md`, `research_websocket.md`, `research_multi_tenancy_sparse.md`
- Design: `design_rest_endpoint.md`, `design_billing_migration.md`
- Structure: `structure_rest_endpoint.md`, `structure_broken_contract.md`
- Plan: `plan_rest_endpoint.md`, `plan_rest_endpoint_slice1.md`, `plan_broken_contract_slice1.md`
- Worktree: `worktree_session1.md`, `worktree_session_broken_contract.md`
- Implement: `impl_log_complete.md`
- PR/diff: `git_diff_rest_endpoint.txt`

Backfill of the missing upstream chain (reviewer RQ2: "backfill") — so a curated leaf fixture is the reproducible output of a real same-stem chain rather than a standalone hand-author:
- `billing_migration` chain predecessors for `design_billing_migration.md`: `ticket_billing_migration.md`, `questions_billing_migration.md`, `research_billing_migration.md` (so the design fixture is the gold-standard output of a complete `ticket → questions → research → design` chain, not authored against a void) (ref: Q3, Q4).
- `multi_tenancy_sparse` chain context for `research_multi_tenancy_sparse.md`: it stays the thin/sparse research output for fabrication-detection, but is now anchored to its present upstream `ticket_multi_tenancy.md` + the backfilled `questions_multi_tenancy.md` so the same ticket ID/ACs thread down the chain (ref: Q3, Discovered Patterns).

These backfilled upstream files are recorded in the README provenance table alongside the 17 acceptance fixtures.

New file: `evals/fixtures/README.md` — a **machine-readable** provenance table (required by AC3; reviewer RQ4): one row per fixture (the 17 + the backfilled upstream + the 4 existing tickets for context) with fixed-vocabulary columns `fixture`, `scenario`, `source_ticket`, `provenance` ∈ {`generated`, `hand-edited`}, `chain`, so a future integrity/freshness check can parse it.

Modified files: none required for the ACs as written. Optionally `docs/eval-system.md` if any provenance is cross-linked, but the doc list is already in sync (ref: Q11) so no change is mandated.

No new DB queries, middleware, or harness code changes are in scope. The harness's silent-skip behavior (ref: Q1, ref: Q14) and the absence of an integrity test (ref: Q13) are pre-existing and out of this ticket's acceptance criteria — per the reviewer these are left as-is (RQ3) and routed to a follow-up ticket (RQ1); see Resolved Questions.

## Pattern Decisions

### Decision 1: How to produce fixture content (generate-then-curate vs hand-author)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Generate-then-curate: run QRSPI phase agents on each source ticket, then hand-edit the output to gold standard | Faster than blind authoring; output already matches current agent shape; acceptable bias for a regression baseline | Depends on the runtime/ticket-landing path being available; some fixtures (billing_migration) lack an upstream chain |
| B | Hand-author every fixture against the templates | Fully controllable; no runtime dependency; unblocked today | Much slower; higher risk of drifting from real agent output shape |

**Recommendation:** Option A (generate-then-curate) for every scenario that has — or can be given — a same-stem upstream chain: `rest_endpoint`, `websocket`, `multi_tenancy`, and `billing_migration`. Per reviewer RQ2 ("backfill"), `billing_migration` is **not** authored standalone; its missing upstream (`ticket_`/`questions_`/`research_billing_migration.md`) is backfilled so `design_billing_migration.md` is the curated output of a real chain. Option B (hand-author) is reserved only for the deliberately `_broken_contract` adversarial set, which has no honest upstream to curate from.
**Rationale:** Matches the ticket's own recommended approach and the scenario-stem chaining pattern in research — curated fixtures are the gold-standard OUTPUT of running a phase agent on the prior phase's same-stem fixture (ref: Q2, ref: Q3). The reviewer chose reproducible chains over standalone leaves, so the only hand-authored fixtures are those that must be intentionally infeasible (ref: Q9, Discovered Patterns).
**NEW PATTERN?** No — reuses existing fixture naming, scenario-stem chaining, and template shapes already established by the 4 present tickets (ref: Q3, ref: Q5).

### Decision 2: Whether to add an automated suite↔fixture integrity test in this ticket

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Scope strictly to the 17 fixtures + README; no test | Smallest change; matches AC exactly; harness is a documented placeholder | The gap that let 17 fixtures go missing (ref: Q13) remains; regression can recur silently |
| B | Also add a stdlib `_test.py` asserting every `context.files` reference exists and is non-empty | Closes the real root-cause gap; follows project "verify with unit tests" convention | Beyond the stated ACs; "loads cleanly" is undefined by the harness today (ref: Q8) so the test defines new behavior |

**Recommendation:** Option A for this ticket. Per reviewer RQ1 ("follow up"), Option B (the integrity test) is **confirmed deferred to a separate follow-up ticket** — see Resolved Questions / RQ1.
**Rationale:** The ACs ask only for fixtures + README; "loads cleanly" today means existence only, with no harness validation (ref: Q8), so adding a test introduces new behavior not requested. Research flags the missing integrity test as a real gap (ref: Q13) worth a separate ticket rather than silently expanding scope — the reviewer agreed and routed it to a follow-up.
**NEW PATTERN?** Yes — an integrity test would be the first stdlib test touching the eval harness/fixtures (ref: Q13); existing `_test.py` files cover only the PR-gated resolver/persist logic. Deferred to a follow-up ticket (RQ1), so no new pattern is introduced by this ticket.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| "Loads cleanly" gives false confidence: a malformed or empty fixture still "loads" because the harness only checks existence (ref: Q8, ref: Q14) | high | med | Verify each fixture is non-empty and shape-matches its template by hand; manually confirm content appears in `build_messages()` output run from cwd=`evals/`; do not rely on harness "OK" status (ref: Q12, ref: Q14) |
| Scenario-chain inconsistency: a curated fixture uses a different ticket ID or ACs than its same-stem upstream, breaking multi-file cases like case_005 (ref: Q3) | med | high | When curating, copy the ticket ID and AC text verbatim from the matching `ticket_*.md` down the chain; cross-check design `Desired End State` maps the exact ACs of its scenario ticket (ref: Q2, ref: Q3) |
| Broken/sparse fixtures not genuinely infeasible/thin: case_012 and case_014 assert behavioral failure, so a too-plausible fixture makes the eval pass for the wrong reason (ref: Q9) | med | med | Author the broken-contract set with a concretely unimplementable type signature carried across structure→plan→worktree-session; keep `research_multi_tenancy_sparse.md` deliberately thin to trigger fabrication detection (ref: Q9, Discovered Patterns) |
| Generate path blocked: generate-then-curate depends on the runtime/ticket-landing path; if unavailable, generated scenarios stall (ref: ticket Dependencies, Q2) | low | med | Fall back to hand-authoring (Decision 1 Option B) for any blocked scenario; the broken/sparse/billing fixtures are hand-authored regardless |
| Cwd footgun: fixtures verified from repo root silently skip (every `os.path.exists` false), masking real problems (ref: Q1, Inconsistencies) | med | low | Always verify fixture loading with cwd=`evals/`; note the cwd requirement in the fixtures README |

## Resolved Questions

All four open questions were answered by the reviewer on the design PR; each answer is incorporated below and reflected in the sections above (Desired End State, Delta, Pattern Decisions).

- RQ1 (reviewer: "follow up"): The stdlib suite↔fixture integrity test (Decision 2 Option B) is **deferred to a separate follow-up ticket**, not done here. This ticket stays scoped to the 17 fixtures + README, confirming Decision 2 Option A. A follow-up ticket should add the test that asserts every `context.files` reference exists and is non-empty (ref: Q13).
- RQ2 (reviewer: "backfill"): For the scenarios with no present upstream fixture chain (`billing_migration`, and the thin `multi_tenancy_sparse` variant), **backfill the missing upstream so the chain is reproducible** rather than authoring the leaf fixtures standalone. The `billing_migration` chain is completed by adding its missing predecessors so `design_billing_migration.md` is the curated output of a real same-stem chain (ref: Q3, Q4). See the Delta and Decision 1 updates below.
- RQ3 (reviewer: "as-is"): The pre-existing silent-skip behavior of the harness (`if os.path.exists`) is **left as-is** — out of this ticket's scope. The "11 vs 12 erroring cases" wording discrepancy is treated as non-authoritative narrative; the authoritative target is the 17-fixture missing set in `docs/eval-system.md:80-89` / suite.json (ref: Q4, Q6, Q14). No harness behavior change is in scope.
- RQ4 (reviewer: "machine-readable"): The `evals/fixtures/README.md` provenance tags **must be machine-readable** (not prose only), so a future integrity/freshness check can parse them — a structured table with fixed-vocabulary columns (`fixture`, `scenario`, `source_ticket`, `provenance` ∈ {`generated`, `hand-edited`}, `chain`). This is reflected in the AC3 row of Desired End State.
