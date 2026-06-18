# Eval Fixtures — Provenance

This directory holds the input fixtures consumed by the QRSPI agent eval suite
(`evals/suite.json`). Every fixture referenced by a case's `context.files` lives here.

> **Loading requirement:** the harness resolves `context.files` paths **relative to the
> process cwd**, so all fixtures must be loaded with **cwd=`evals/`** (e.g.
> `python3 scripts/run_eval.py` run from inside `evals/`, or `build_messages()` invoked
> from there). Resolving from the repo root silently skips every fixture.

## Provenance table (machine-readable)

The table below has one row per fixture, with fixed-vocabulary columns so a future
integrity / freshness check can parse provenance rather than only read prose:

- `fixture` — filename under `evals/fixtures/`
- `scenario` — same-stem scenario chain the fixture belongs to
- `source_ticket` — the ticket ID threaded verbatim down the chain (`chain-consistency`)
- `provenance` — one of `generated` | `hand-edited` (closed vocabulary)
  - `generated` = generate-then-curate: the gold-standard output of running the prior
    phase's same-stem fixture through a QRSPI phase agent (design Decision 1, Option A)
  - `hand-edited` = hand-authored; reserved for the deliberately infeasible
    `_broken_contract` adversarial set, which has no honest upstream to curate from
- `chain` — the phase position of the fixture within its scenario chain

| fixture | scenario | source_ticket | provenance | chain |
|---|---|---|---|---|
| ticket_rest_endpoint.md | rest_endpoint | DASH-417 | generated | ticket |
| questions_rest_endpoint.md | rest_endpoint | DASH-417 | generated | questions |
| research_rest_endpoint.md | rest_endpoint | DASH-417 | generated | research |
| design_rest_endpoint.md | rest_endpoint | DASH-417 | generated | design |
| structure_rest_endpoint.md | rest_endpoint | DASH-417 | generated | structure |
| plan_rest_endpoint.md | rest_endpoint | DASH-417 | generated | plan |
| plan_rest_endpoint_slice1.md | rest_endpoint | DASH-417 | generated | plan (slice-1 subset) |
| worktree_session1.md | rest_endpoint | DASH-417 | generated | worktree |
| impl_log_complete.md | rest_endpoint | DASH-417 | generated | implement |
| git_diff_rest_endpoint.txt | rest_endpoint | DASH-417 | generated | pr (diff input) |
| ticket_websocket.md | websocket | ORD-892 | generated | ticket |
| questions_websocket.md | websocket | ORD-892 | generated | questions |
| research_websocket.md | websocket | ORD-892 | generated | research |
| ticket_multi_tenancy.md | multi_tenancy | PLAT-1205 | generated | ticket |
| questions_multi_tenancy.md | multi_tenancy | PLAT-1205 | generated | questions |
| research_multi_tenancy_sparse.md | multi_tenancy | PLAT-1205 | generated | research (sparse variant) |
| ticket_billing_migration.md | billing_migration | PAY-733 | generated | ticket |
| questions_billing_migration.md | billing_migration | PAY-733 | generated | questions |
| research_billing_migration.md | billing_migration | PAY-733 | generated | research |
| design_billing_migration.md | billing_migration | PAY-733 | generated | design |
| structure_broken_contract.md | broken_contract | GUARD-808 | hand-edited | structure |
| plan_broken_contract_slice1.md | broken_contract | GUARD-808 | hand-edited | plan (slice-1) |
| worktree_session_broken_contract.md | broken_contract | GUARD-808 | hand-edited | worktree (session) |
| ticket_15_acceptance_criteria.md | acceptance_criteria_stress | RPT-2100 | generated | ticket |
| design_dropped_criterion_broken.md | dropped_criterion | DASH-417 | hand-edited | design (descoping regression anchor) |

## Notes

- **Pre-existing fixtures (context):** `ticket_rest_endpoint.md`, `ticket_websocket.md`,
  `ticket_multi_tenancy.md`, and `ticket_15_acceptance_criteria.md` existed before this
  backfill; they are the honest roots of their curated chains and are listed here for
  completeness so every consumed fixture has a provenance row.
- **Backfilled upstream (not directly referenced by a case):**
  `ticket_billing_migration.md`, `questions_billing_migration.md`, and
  `research_billing_migration.md` were backfilled (reviewer RQ2) so that the
  case-referenced leaf `design_billing_migration.md` is the reproducible output of a real
  same-stem chain rather than a standalone hand-author. They are intentional chain context,
  not orphans.
- **Curated chains are `generated`; only the `_broken_contract` set is `hand-edited`**
  (design Decision 1): the broken set carries a deliberately unimplementable signature
  verbatim across its three fixtures so case_012 fails behaviorally for the right reason.
- **`design_dropped_criterion_broken.md` is the RUS-91 descoping regression anchor**
  (reused, not newly authored — RUS-77 / AC-TEETH provenance, a different purpose, so it is
  non-circular for the review panels). It is an independently-authored DASH-417 design that
  states four acceptance criteria in its Desired End State but SILENTLY DROPS one — **"403
  unless admin"** — from its Delta and Pattern Decisions (no `canAccess`/403 handler, route
  wiring, test, or decision implements it). It carries a "Do NOT fix this fixture" guard. The
  RUS-91 design review panel (the `completeness`/`edge-alignment` coverage lenses) and the
  deterministic `scripts/qrspi_teeth_test.py` stated-minus-covered check both surface the
  dropped criterion as a blocking finding. Its four ACs (for `TICKET_CONTENT_PATH`) are
  supplied verbatim by the existing `ticket_rest_endpoint.md` (same DASH-417 source ticket),
  so no separate ticket fixture was added.
