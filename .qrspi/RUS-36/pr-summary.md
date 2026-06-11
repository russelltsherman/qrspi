# PR: RUS-36 Backfill 17 missing eval fixtures + provenance README

**Ticket:** RUS-36
**Design:** design.md @ 2026-06-09T00:00:00Z
**Structure:** structure.md @ 2026-06-11T00:00:00Z

## Summary

The eval suite (`evals/suite.json`) referenced 21 distinct fixtures but only 4
existed on disk; the other 17 silently skipped at load because the harness only
checks `os.path.exists()` (no error, no failing case). This PR backfills all 17
missing fixtures plus the upstream chain predecessors needed to make the curated
leaves reproducible, and adds a machine-readable `evals/fixtures/README.md`
provenance table. No harness, `suite.json`, or `docs/eval-system.md` code was
changed — this is content-only (Markdown/txt fixtures). Reviewer focus areas:
(1) scenario-chain consistency (ticket ID + ACs threaded verbatim down each
`<scenario>` stem), (2) that the `_broken_contract` set carries a genuinely
unimplementable signature byte-identically across its three files, and (3) that
the sparse `multi_tenancy` research is honestly thin (zero `file:line`
citations) so case_014 fabrication-detection triggers for the right reason.

## Acceptance Criteria Mapping

The ACs are content/integrity guarantees, not code paths; "test" here is the
verification command that asserts each (all run from `cwd=evals/`).

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: All 17 fixtures exist in `evals/fixtures/` (the `docs/eval-system.md:80-89` missing set), named `<phase>_<scenario>.md`/`.txt`, scenario-stem-consistent | The 17 new fixtures across Slices 1–5 (`questions_/research_/design_/structure_/plan_/plan_slice1/git_diff/worktree_session1/impl_log_complete/_broken_contract` set) | Slice 6 sweep `[3]`: cross-check vs `docs/eval-system.md:80-89` → 17/17 present, 0 absent (`cd evals && test -s <each>`) |
| AC2: Each fixture loads cleanly when referenced by its eval case (resolves under `cwd=evals/`, non-empty, shape-matches its phase template) | Each chain's fixtures shape-matched to the consuming case's asserted sections (Slices 1–5) | Slice 6 sweep `[1]` loads-cleanly: 21 `context.files` refs, 0 MISSING/EMPTY; per-slice `build_messages()` renders for case_005/010/011/004/006/014/008/012/013 |
| AC3: A README documents which fixtures were generated, which hand-edited, and from what source ticket (machine-readable, RQ4) | `evals/fixtures/README.md` — fixed-vocabulary table (`fixture`, `scenario`, `source_ticket`, `provenance` ∈ {generated, hand-edited}, `chain`) | Slice 6 sweep `[2]` provenance-parsable: 24 rows parsed, 0 bad-provenance values; every referenced fixture has a row, every row maps to a real file |

## Changes by Slice

### Slice 1: `rest_endpoint` chain (canonical reference)

| File | Change | Lines |
|------|--------|-------|
| `evals/fixtures/questions_rest_endpoint.md` | ✨ new | +49 |
| `evals/fixtures/research_rest_endpoint.md` | ✨ new | +193 |
| `evals/fixtures/design_rest_endpoint.md` | ✨ new | +72 |
| `evals/fixtures/structure_rest_endpoint.md` | ✨ new | +69 |
| `evals/fixtures/plan_rest_endpoint.md` | ✨ new | +97 |
| `evals/fixtures/plan_rest_endpoint_slice1.md` | ✨ new | +49 |
| `evals/fixtures/git_diff_rest_endpoint.txt` | ✨ new | +129 |

### Slice 2: `websocket` + `multi_tenancy` chains

| File | Change | Lines |
|------|--------|-------|
| `evals/fixtures/questions_websocket.md` | ✨ new | +49 |
| `evals/fixtures/research_websocket.md` | ✨ new | +195 |
| `evals/fixtures/questions_multi_tenancy.md` | ✨ new | +49 |
| `evals/fixtures/research_multi_tenancy_sparse.md` | ✨ new | +178 |

### Slice 3: `billing_migration` chain (backfilled upstream + design leaf)

| File | Change | Lines |
|------|--------|-------|
| `evals/fixtures/ticket_billing_migration.md` | ✨ new | +31 |
| `evals/fixtures/questions_billing_migration.md` | ✨ new | +49 |
| `evals/fixtures/research_billing_migration.md` | ✨ new | +193 |
| `evals/fixtures/design_billing_migration.md` | ✨ new | +71 |

### Slice 4: broken-contract adversarial set (hand-authored)

| File | Change | Lines |
|------|--------|-------|
| `evals/fixtures/structure_broken_contract.md` | ✨ new | +57 |
| `evals/fixtures/plan_broken_contract_slice1.md` | ✨ new | +48 |
| `evals/fixtures/worktree_session_broken_contract.md` | ✨ new | +33 |

### Slice 5: worktree session + impl-log fixtures

| File | Change | Lines |
|------|--------|-------|
| `evals/fixtures/worktree_session1.md` | ✨ new | +87 |
| `evals/fixtures/impl_log_complete.md` | ✨ new | +115 |

### Slice 6: machine-readable provenance README + full integrity sweep

| File | Change | Lines |
|------|--------|-------|
| `evals/fixtures/README.md` | ✨ new | +67 |

### Workflow artifacts (not fixtures; QRSPI phase outputs for this ticket)

| File | Change | Lines |
|------|--------|-------|
| `.qrspi/RUS-36/questions.md` | ✨ new | +51 |
| `.qrspi/RUS-36/research.md` | ✨ new | +321 |
| `.qrspi/RUS-36/design.md` | ✨ new | +93 |
| `.qrspi/RUS-36/structure.md` | ✨ new | +152 |
| `.qrspi/RUS-36/plan.md` | ✨ new | +160 |
| `.qrspi/RUS-36/worktree.md` | ✨ new | +124 |
| `.qrspi/RUS-36/impl-log.md` | ✨ new | +185 |

## Testing Summary

All verification runs from `cwd=evals/` (the loader resolves `context.files`
relative to process cwd; running from repo root silently skips every file).

- [x] Slice 1: 7 fixtures present/non-empty; `grade.py` gold-standard checks — 14 passed, 0 failed; `plan_slice1` is a strict line-subset of `plan_rest_endpoint.md`; `build_messages()` renders case_005/010/011 with DASH-417 present
- [x] Slice 2: 4 fixtures present/non-empty; both questions = 13 `- QN:`/`**Target:**`, 6 `##` sections; sparse research = **0** `file:line` / **11** NOT FOUND (genuinely thin); `build_messages()` renders case_004/006/014/002
- [x] Slice 3: 4 fixtures present/non-empty; **PAY-733** threads through all 4; design cites Q1–Q13 ⊆ questions, consistent with research; `build_messages()` renders case_008
- [x] Slice 4: 3 fixtures present/non-empty; `willHalt(source, input): boolean` (Halting Problem) appears exactly once, byte-identical in all three; filenames byte-exact to case_012 refs; `build_messages()` renders case_012
- [x] Slice 5: 2 fixtures present/non-empty, template-shaped; DASH-417 + all 4 ACs verbatim in each; scope file list parses via `check_scope.py`; `build_messages()` renders case_011/013 (`p95 = 142ms` present)
- [x] Slice 6 integrity sweep: `[1]` 21 refs, 0 MISSING/EMPTY · `[2]` 24 README rows, 0 bad-provenance · `[3]` 17/17 acceptance fixtures present, all with a README row
- [x] Manual verification: each slice confirmed content rendered in `build_messages()` output run from `cwd=evals/`, never trusting harness "OK" status

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| (none) | | | All six slices report "Deviations from structure.md: none". The `_broken_contract` set's intentional departure from the honest structure shape (one impossible Contracts line) is specified by structure §New Types `BrokenContract` and the `broken-contract-carried` contract — it is the fixture's purpose, not an implementation deviation. |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| "Loads cleanly" gives false confidence — harness only checks existence | Mitigated — every fixture verified non-empty and rendered via `build_messages()` from `cwd=evals/`; not relying on harness "OK" | Revert the slice's fixture commit |
| Scenario-chain inconsistency (curated fixture uses different ID/ACs than its upstream) | Mitigated — ticket IDs + AC text copied verbatim down each chain; cross-checked (DASH-417/ORD-892/PLAT-1205/PAY-733 grep-confirmed per chain) | Revert the affected chain's commit |
| Broken/sparse fixtures not genuinely infeasible/thin | Mitigated — `willHalt` is the undecidable Halting Problem (byte-identical ×3); sparse research has 0 citations / 11 NOT FOUND | Revert Slice 4 / Slice 2 commit |
| Generate path blocked (generate-then-curate depends on runtime) | Accepted — broken/sparse/billing fixtures hand-authored regardless; chains authored directly to template shape | n/a (no runtime dependency taken) |
| Cwd footgun — fixtures verified from repo root silently skip | Mitigated — all verification run from `cwd=evals/`; requirement documented in `evals/fixtures/README.md` | n/a |

## Open Items

- **Deferred (RQ1):** A stdlib suite↔fixture integrity test (assert every `suite.json` `context.files` reference exists and is non-empty) is the real root-cause fix for the gap that let 17 fixtures go missing. Per the reviewer it is routed to a **separate follow-up ticket**, not done here. This PR's Slice 6 manual sweep covers the assertion once; the test would make it permanent.
- **As-is (RQ3):** The harness's silent-skip behavior (`if os.path.exists`) and the inability to identify which case lost which fixture from harness output are left unchanged — out of this ticket's scope.
- **Backfilled upstream not directly case-referenced:** `ticket_/questions_/research_billing_migration.md` exist to make `design_billing_migration.md` a reproducible chain leaf; they are intentionally not `suite.json`-referenced (the `no-orphans()` contract permits this and the README records them as backfilled chain context).
