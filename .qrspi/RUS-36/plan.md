# Implementation Plan — Backfill 17 missing eval fixtures

**Structure basis:** structure.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** draft
**Total steps:** 51

> This ticket produces **content artifacts** (Markdown/txt fixtures + a README), not code.
> Every "Create" step authors one fixture file conforming to a structural shape from
> structure.md. Authors MUST copy the ticket ID + Acceptance-Criteria text **verbatim** from
> the existing `evals/fixtures/ticket_<scenario>.md` down each same-stem chain
> (`chain-consistency` contract). All verification is run from **cwd=`evals/`** — never from
> the repo root (the loader resolves `context.files` relative to process cwd; verifying from
> root silently skips every fixture).

## Slice 1: `rest_endpoint` chain (largest, defines the canonical pattern)

### Setup

1. Read `evals/fixtures/ticket_rest_endpoint.md` — capture the verbatim ticket ID (DASH-417) and full Acceptance-Criteria text to thread down every `rest_endpoint` fixture (`chain-consistency`).
2. Read `.qrspi/templates/structure.md`, `.qrspi/templates/plan.md`, and `.qrspi/templates/worktree.md` — the literal required section lists for the `structure_`/`plan_`/`worktree_` shapes (Unverified Assumption #1).
3. Read `evals/suite.json` and `scripts/run_eval.py` `build_messages()` — confirm the exact `context.files` paths for case_005 / case_010 / case_011 and the cwd resolution behavior.

### Core Logic

4. ✨ Create `evals/fixtures/questions_rest_endpoint.md` — questions fixture: six `##` sections, each with 8–15 `- QN:` lines, each line carrying `**Target:**`. Anchor ticket ID/ACs verbatim from step 1. (ref: structure §New Types `Questions.md`)
5. ✨ Create `evals/fixtures/research_rest_endpoint.md` — research fixture: per-Q `**Answer:**`/`**Evidence:**`/`file:line`/`**Dependencies:**`/`**Implicit contracts:**`, plus `## Discovered Patterns` and `## Inconsistencies`. (ref: structure §New Types `Research.md`)
6. ✨ Create `evals/fixtures/design_rest_endpoint.md` — design fixture: six design sections with `(ref: QN)` citations and **no code blocks**. (ref: structure §New Types `Design.md`)
7. ✨ Create `evals/fixtures/structure_rest_endpoint.md` — structure fixture conforming to `.qrspi/templates/structure.md` (sections from step 2). (ref: structure §New Types `Structure.md`)
8. ✨ Create `evals/fixtures/plan_rest_endpoint.md` — full multi-slice plan conforming to `.qrspi/templates/plan.md`, consumed by case_010. (ref: structure §New Types `Plan.md`)
9. ✨ Create `evals/fixtures/plan_rest_endpoint_slice1.md` — a **faithful Slice-1 subset** of `plan_rest_endpoint.md` (same Slice-1 steps verbatim), consumed by case_011 (`slice1-subset` contract).
10. ✨ Create `evals/fixtures/git_diff_rest_endpoint.txt` — unified-diff text fixture (the one non-`.md` reference). (ref: structure §New Types `GitDiff.txt`)

### Verify Slice 1

11. **Checkpoint:** `cd evals && for f in fixtures/questions_rest_endpoint.md fixtures/research_rest_endpoint.md fixtures/design_rest_endpoint.md fixtures/structure_rest_endpoint.md fixtures/plan_rest_endpoint.md fixtures/plan_rest_endpoint_slice1.md fixtures/git_diff_rest_endpoint.txt; do test -s "$f" && echo "OK $f" || echo "MISSING/EMPTY $f"; done`
    - [ ] All 7 files exist and are non-empty
    - [ ] Ticket ID (DASH-417) + AC text appear verbatim in each `.md` fixture (grep the ID; cross-check ACs against `ticket_rest_endpoint.md`)
    - [ ] `plan_rest_endpoint_slice1.md` Slice-1 content is a strict subset of `plan_rest_endpoint.md`'s Slice 1
    - [ ] From cwd=`evals/`, `build_messages()` resolves each path and the content renders for case_005 / case_010 / case_011 (manual — do NOT trust harness "OK")

---

## Slice 2: `websocket` + `multi_tenancy` chains

### Setup

12. Read `evals/fixtures/ticket_websocket.md` — capture ticket ID (ORD-892) + ACs verbatim for the `websocket` chain.
13. Read `evals/fixtures/ticket_multi_tenancy.md` — capture ticket ID (PLAT-1205) + ACs verbatim for the `multi_tenancy` chain.

### Core Logic

14. ✨ Create `evals/fixtures/questions_websocket.md` — questions fixture (six `##`, 8–15 `- QN:` w/ `**Target:**`), anchored to ORD-892. (ref: structure Slice 2)
15. ✨ Create `evals/fixtures/research_websocket.md` — research fixture for websocket (Answer/Evidence/file:line/Dependencies/Implicit contracts + Discovered Patterns + Inconsistencies). (ref: structure Slice 2)
16. ✨ Create `evals/fixtures/questions_multi_tenancy.md` — backfilled questions anchored to PLAT-1205 (RQ2), so the sparse research has a real upstream. (ref: structure Slice 2)
17. ✨ Create `evals/fixtures/research_multi_tenancy_sparse.md` — **deliberately thin/sparse** research (missing/under-specified answers) to trigger case_014 fabrication-detection for the right reason (`SparseResearch` trait). (ref: structure §New Types `SparseResearch`)

### Verify Slice 2

18. **Checkpoint:** `cd evals && for f in fixtures/questions_websocket.md fixtures/research_websocket.md fixtures/questions_multi_tenancy.md fixtures/research_multi_tenancy_sparse.md; do test -s "$f" && echo "OK $f" || echo "MISSING/EMPTY $f"; done`
    - [ ] All 4 files exist and are non-empty
    - [ ] ORD-892 / PLAT-1205 IDs + ACs appear verbatim in their respective chain fixtures
    - [ ] `research_multi_tenancy_sparse.md` is genuinely thin (under-specified) so case_014 detects fabrication for the right reason
    - [ ] From cwd=`evals/`, paths resolve and content renders for the consuming cases (manual)

---

## Slice 3: `billing_migration` chain (backfilled upstream + design leaf)

### Setup

19. Decide the `billing_migration` ticket ID + AC set (no existing ticket; this chain is fully new) — record it so it threads verbatim through all four files (`chain-consistency`).

### Core Logic

20. ✨ Create `evals/fixtures/ticket_billing_migration.md` — backfilled root ticket: `# Ticket: <ID>`, `## Title`, `## Description`, `## Acceptance Criteria` (`- [ ]` checkboxes), `## Constraints`, `## Out of Scope`, ~850–1626 bytes. (ref: structure §New Types `Ticket.md`)
21. ✨ Create `evals/fixtures/questions_billing_migration.md` — backfilled questions (six `##`, 8–15 `- QN:` w/ `**Target:**`) anchored to step 20's ticket. (ref: structure Slice 3)
22. ✨ Create `evals/fixtures/research_billing_migration.md` — backfilled research (Answer/Evidence/file:line/Dependencies/Implicit contracts + Discovered Patterns + Inconsistencies). (ref: structure Slice 3)
23. ✨ Create `evals/fixtures/design_billing_migration.md` — the acceptance leaf: six design sections, `(ref: QN)` citing questions that exist in step 21, no code blocks, consistent with step 22's research. (ref: structure §New Types `Design.md`)

### Verify Slice 3

24. **Checkpoint:** `cd evals && for f in fixtures/ticket_billing_migration.md fixtures/questions_billing_migration.md fixtures/research_billing_migration.md fixtures/design_billing_migration.md; do test -s "$f" && echo "OK $f" || echo "MISSING/EMPTY $f"; done`
    - [ ] All 4 files exist and are non-empty
    - [ ] One ticket ID + AC set threads verbatim through all four (grep the ID across the chain)
    - [ ] `design_billing_migration.md` cites only `(ref: QN)` questions present in `questions_billing_migration.md` and is consistent with the research
    - [ ] From cwd=`evals/`, the design fixture resolves and renders for its consuming case (manual)

---

## Slice 4: broken-contract adversarial set (hand-authored)

### Setup

25. Define ONE concretely **unimplementable** type signature (genuinely infeasible, not merely hard) to carry verbatim across the three broken fixtures (`BrokenContract` trait / `broken-contract-carried` contract). (ref: structure §New Types `BrokenContract`)

### Core Logic

26. ✨ Create `evals/fixtures/structure_broken_contract.md` — structure fixture that introduces the unimplementable contract from step 25 (deviates from the honest template shape intentionally). (ref: structure Slice 4)
27. ✨ Create `evals/fixtures/plan_broken_contract_slice1.md` — plan slice carrying the SAME broken contract verbatim into the plan. (ref: structure Slice 4)
28. ✨ Create `evals/fixtures/worktree_session_broken_contract.md` — session-DAG fixture carrying the SAME broken contract verbatim. Confirm the exact filename matches the `suite.json` reference before writing (Unverified Assumption #5). (ref: structure Slice 4)

### Verify Slice 4

29. **Checkpoint:** `cd evals && for f in fixtures/structure_broken_contract.md fixtures/plan_broken_contract_slice1.md fixtures/worktree_session_broken_contract.md; do test -s "$f" && echo "OK $f" || echo "MISSING/EMPTY $f"; done`
    - [ ] All 3 files exist and are non-empty
    - [ ] The SAME unimplementable signature appears **verbatim** in all three (`broken-contract-carried` — grep the signature, confirm identical)
    - [ ] The contract is genuinely infeasible (not merely hard) so case_012 cannot pass by accident
    - [ ] The filename matches its `suite.json` `context.files` reference exactly (no cwd-skip)
    - [ ] From cwd=`evals/`, the three paths resolve and render for case_012 (manual)

---

## Slice 5: worktree session + impl-log fixtures

### Setup

30. Read `.qrspi/templates/worktree.md` and the impl-log template — confirm the exact required sections for the honest `worktree_session1.md` and `impl_log_complete.md` (Unverified Assumption #1 and #2).

### Core Logic

31. ✨ Create `evals/fixtures/worktree_session1.md` — honest worktree session-DAG fixture matching the worktree template, scenario-stem consistent with the `rest_endpoint` chain (Slice 1). (ref: structure §New Types `Worktree.md`)
32. ✨ Create `evals/fixtures/impl_log_complete.md` — complete implementation-log fixture matching the impl-log template, anchored to the `rest_endpoint` chain. (ref: structure §New Types `ImplLog.md`)

### Verify Slice 5

33. **Checkpoint:** `cd evals && for f in fixtures/worktree_session1.md fixtures/impl_log_complete.md; do test -s "$f" && echo "OK $f" || echo "MISSING/EMPTY $f"; done`
    - [ ] Both files exist, are non-empty, and match their templates
    - [ ] Scenario-stem consistent with the `rest_endpoint` chain (ticket ID/ACs threaded)
    - [ ] From cwd=`evals/`, paths resolve and render for the consuming cases (manual)

---

## Slice 6: machine-readable provenance README + full integrity sweep

### Setup

34. Read `evals/suite.json` in full — enumerate every distinct `context.files` reference (the 21) and the consuming case for each.
35. Read `docs/eval-system.md:80-89` — capture the authoritative list of the 17 acceptance fixtures for the final cross-check.
36. Enumerate every fixture produced in Slices 1–5 plus the 4 existing tickets, reconciling the acceptance set vs. backfilled-upstream set boundary before writing the table (Unverified Assumption #4).

### Core Logic

37. ✨ Create `evals/fixtures/README.md` — machine-readable provenance table with fixed-vocabulary columns `fixture`, `scenario`, `source_ticket`, `provenance` ∈ {`generated`, `hand-edited`}, `chain`; exactly one row per produced fixture; broken set marked `hand-edited`, curated chains per Decision 1; note the cwd=`evals/` loading requirement. (ref: structure §New Types `README.md provenance table row`, `provenance-parsable` contract)

### Verify Slice 6

38. **Checkpoint:** `cd evals && python3 -c "import json,os; refs={f for c in json.load(open('suite.json')).get('cases',[]) for f in c.get('context',{}).get('files',[])}; missing=[f for f in sorted(refs) if not (os.path.exists(f) and os.path.getsize(f)>0)]; print('MISSING/EMPTY:', missing or 'none'); print('total refs:', len(refs))"`
    - [ ] Every `context.files` reference in `suite.json` exists and is non-empty from cwd=`evals/` (whole-suite `loads-cleanly` + `no-orphans` sweep — adjust the JSON key path in the one-liner to suite.json's actual schema after step 34)
    - [ ] README has exactly one row per produced fixture, all `provenance` values from the fixed vocabulary (`provenance-parsable`)
    - [ ] The 17 acceptance fixtures from `docs/eval-system.md:80-89` are all present (cross-check against that list)
    - [ ] No orphans in either direction: no produced fixture lacks a `suite.json` reference, and no referenced-missing fixture remains (`no-orphans`)

---

## Rollback Notes

- This ticket is **purely additive content** — every step creates a new file under `evals/fixtures/`; none modifies existing code, the harness, `suite.json`, or `docs/eval-system.md` (structure §Modified Types: none). No DB migrations, config changes, or destructive operations are involved.
- To roll back any single step: delete the file it created (`rm evals/fixtures/<file>`). No state or schema is affected; the harness silently skips a now-absent fixture exactly as before this ticket.
- To roll back the whole ticket: remove the 17 acceptance fixtures + the backfilled upstream (`ticket_/questions_/research_billing_migration.md`, `questions_multi_tenancy.md`) + `evals/fixtures/README.md`. The 4 pre-existing `ticket_*.md` fixtures are NOT created here and must NOT be deleted.
