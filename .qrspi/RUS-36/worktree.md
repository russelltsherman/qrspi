# Work Tree — Backfill 17 missing eval fixtures

**Plan basis:** plan.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** draft
**Total sessions:** 6
**Critical path:** T1 → T4 → T5 → T6 → T7 → T8 → T9 → T10 → T11 → (Slice 1 done) → T16 → T17 → T18 → (Slice 2) → T22 → T23 → T24 → T25 → (Slice 3) → T28 → T29 → T30 → T31 → (Slice 4) → T34 → T35 → T36 → (Slice 5) → T39 → T40 → T41 (38 tasks, critical path = 38)

> Each slice maps to one session and already terminates in a verify checkpoint — natural
> session boundaries. All verification runs from **cwd=`evals/`**. Authors thread the ticket
> ID + Acceptance-Criteria text **verbatim** down each same-stem chain (`chain-consistency`).

## Session 1 — Slice 1: `rest_endpoint` chain

**Load:** structure.md §New Types, structure.md §Contracts (chain-consistency, slice1-subset),
        plan.md §Slice 1, `.qrspi/templates/{structure,plan,worktree}.md` §section-lists,
        `evals/suite.json` (case_005/010/011), `evals/fixtures/ticket_rest_endpoint.md`
**Estimated context:** ~28%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Read `ticket_rest_endpoint.md`; capture DASH-417 + ACs verbatim | — | §1.1 | S | pending |
| T2 | Read structure/plan/worktree templates for required section lists | — | §1.2 | S | pending |
| T3 | Read `suite.json` + `build_messages()` for case_005/010/011 paths + cwd | — | §1.3 | S | pending |
| T4 | Create `questions_rest_endpoint.md` (6 §, 8–15 `- QN:` w/ Target) | T1,T2,T3 | §1.4 | M | pending |
| T5 | Create `research_rest_endpoint.md` (Answer/Evidence/file:line/Deps/contracts) | T4 | §1.5 | M | pending |
| T6 | Create `design_rest_endpoint.md` (6 sections, `(ref: QN)`, no code) | T4,T5 | §1.6 | M | pending |
| T7 | Create `structure_rest_endpoint.md` (template-conforming) | T2,T6 | §1.7 | M | pending |
| T8 | Create `plan_rest_endpoint.md` (full multi-slice, case_010) | T2,T7 | §1.8 | L | pending |
| T9 | Create `plan_rest_endpoint_slice1.md` (faithful Slice-1 subset, case_011) | T8 | §1.9 | M | pending |
| T10 | Create `git_diff_rest_endpoint.txt` (unified diff) | T1 | §1.10 | S | pending |
| T11 | **Verify Slice 1** (7 files non-empty, ID/ACs verbatim, subset, cwd render) | T4,T5,T6,T7,T8,T9,T10 | §1.11 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete and verified. The canonical `rest_endpoint` pattern is established; subsequent chains reuse the shape but not its content. Fresh context for Slice 2.

## Session 2 — Slice 2: `websocket` + `multi_tenancy` chains

**Load:** structure.md §Slice 2, structure.md §New Types (SparseResearch), plan.md §Slice 2,
        `evals/fixtures/ticket_websocket.md`, `evals/fixtures/ticket_multi_tenancy.md`,
        plan.md §Slice 1 (pattern reference only — do not reload Slice 1 fixtures)
**Estimated context:** ~22%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T12 | Read `ticket_websocket.md`; capture ORD-892 + ACs verbatim | T11 | §2.12 | S | pending |
| T13 | Read `ticket_multi_tenancy.md`; capture PLAT-1205 + ACs verbatim | T11 | §2.13 | S | pending |
| T14 | Create `questions_websocket.md` (6 §, 8–15 `- QN:` w/ Target, ORD-892) | T12 | §2.14 | M | pending |
| T15 | Create `research_websocket.md` (full research shape) | T14 | §2.15 | M | pending |
| T16 | Create `questions_multi_tenancy.md` (anchored PLAT-1205, RQ2) | T13 | §2.16 | M | pending |
| T17 | Create `research_multi_tenancy_sparse.md` (deliberately thin, case_014) | T16 | §2.17 | M | pending |
| T18 | **Verify Slice 2** (4 files non-empty, IDs/ACs verbatim, sparse-for-right-reason) | T14,T15,T16,T17 | §2.18 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 2 complete. The `multi_tenancy` sparse fixture is the only cross-slice subtlety and is now closed out. Fresh context for the fully-new `billing_migration` chain in Slice 3.

## Session 3 — Slice 3: `billing_migration` chain (new upstream + design leaf)

**Load:** structure.md §Slice 3, structure.md §New Types (Ticket.md, Design.md), plan.md §Slice 3,
        plan.md §Slice 1 (chain-shape reference only)
**Estimated context:** ~20%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T19 | Decide `billing_migration` ticket ID + AC set; record for chain | T18 | §3.19 | S | pending |
| T20 | Create `ticket_billing_migration.md` (root ticket, ~850–1626 bytes) | T19 | §3.20 | M | pending |
| T21 | Create `questions_billing_migration.md` (6 §, 8–15 `- QN:`) | T20 | §3.21 | M | pending |
| T22 | Create `research_billing_migration.md` (full research shape) | T21 | §3.22 | M | pending |
| T23 | Create `design_billing_migration.md` (leaf; `(ref: QN)` ⊆ T21, no code) | T21,T22 | §3.23 | M | pending |
| T24 | **Verify Slice 3** (4 files, ID/AC threaded, refs valid, cwd render) | T20,T21,T22,T23 | §3.24 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 3 complete. The honest chains are done; Slice 4 deliberately authors a *broken* contract and must not be contaminated by the honest-shape context. Fresh context.

## Session 4 — Slice 4: broken-contract adversarial set

**Load:** structure.md §Slice 4, structure.md §New Types (BrokenContract),
        structure.md §Contracts (broken-contract-carried), plan.md §Slice 4,
        `evals/suite.json` (exact worktree_session_broken_contract filename / case_012)
**Estimated context:** ~18%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T25 | Define ONE genuinely unimplementable type signature to carry verbatim | T24 | §4.25 | S | pending |
| T26 | Create `structure_broken_contract.md` (introduces broken contract) | T25 | §4.26 | M | pending |
| T27 | Create `plan_broken_contract_slice1.md` (same signature verbatim) | T25,T26 | §4.27 | M | pending |
| T28 | Create `worktree_session_broken_contract.md` (same signature; confirm filename vs suite.json) | T25,T27 | §4.28 | M | pending |
| T29 | **Verify Slice 4** (3 files, signature identical+infeasible, filename match, case_012) | T26,T27,T28 | §4.29 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 4 complete. Slice 5 returns to honest fixtures (worktree session + impl-log), needing the template shapes rather than the broken-contract context. Fresh context.

## Session 5 — Slice 5: worktree session + impl-log fixtures

**Load:** structure.md §New Types (Worktree.md, ImplLog.md), plan.md §Slice 5,
        `.qrspi/templates/worktree.md`, impl-log template,
        plan.md §Slice 1 (rest_endpoint chain ID/ACs reference)
**Estimated context:** ~18%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T30 | Read worktree + impl-log templates; confirm required sections | T29 | §5.30 | S | pending |
| T31 | Create `worktree_session1.md` (honest, rest_endpoint-stem consistent) | T30 | §5.31 | M | pending |
| T32 | Create `impl_log_complete.md` (complete, rest_endpoint-anchored) | T30 | §5.32 | M | pending |
| T33 | **Verify Slice 5** (both files, template-match, stem-consistent, cwd render) | T31,T32 | §5.33 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 5 complete. Slice 6 is the whole-suite integrity sweep + provenance README, which must enumerate every fixture produced across Slices 1–5 — it needs the full suite.json/docs context, not any single-slice context. Fresh context.

## Session 6 — Slice 6: provenance README + full integrity sweep

**Load:** `evals/suite.json` (full — all 21 refs + consuming cases),
        `docs/eval-system.md:80-89` (17 acceptance fixtures),
        structure.md §New Types (README provenance row), structure.md §Contracts
        (provenance-parsable, loads-cleanly, no-orphans), plan.md §Slice 6
**Estimated context:** ~24%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T34 | Read `suite.json` fully; enumerate all 21 `context.files` + consuming cases | T33 | §6.34 | S | pending |
| T35 | Read `docs/eval-system.md:80-89`; capture the 17 acceptance fixtures | T33 | §6.35 | S | pending |
| T36 | Enumerate Slices 1–5 fixtures + 4 existing tickets; reconcile acceptance vs backfilled set | T34,T35 | §6.36 | M | pending |
| T37 | Create `evals/fixtures/README.md` (provenance table, fixed vocab, 1 row/fixture) | T36 | §6.37 | M | pending |
| T38 | **Verify Slice 6** (suite loads-cleanly from cwd=evals, no-orphans both ways, 17 present, README parsable) | T37 | §6.38 | M | pending |
