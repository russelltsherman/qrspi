# PR: RUS-52 Deterministic cleanup for fully-merged QRSPI stacks

**Ticket:** RUS-52
**Design:** design.md @ 2026-06-07T00:00:00Z
**Structure:** structure.md @ 2026-06-07T00:00:00Z

## Summary

Replaces the natural-language `gt sync --force` / `git worktree remove --force 2>/dev/null` land-cleanup prose with a deterministic, self-locating, unit-tested `scripts/qrspi_cleanup.py` that reaps a ticket's worktree, local stack branches, and merged remote refs once — and only once — its entire stack has merged. Merge state is now first-class: `qrspi_pr_state.py` gains a MERGED-aware GraphQL query plus pure `stack_merge_state` / `is_stack_fully_merged` predicates, added additively so existing OPEN-path resolver/restack callers are untouched. The cleanup script computes a pure `destroy`/`skip`/`blocked` decision (a dirty worktree is `blocked`, never force-destroyed — closing the AC3 safety gap) and gates all destruction behind a `--dry-run` flag. Orchestration in `qrspi-batch.js` now invokes the script after the bottom-up merge in `doLand` and adds an opt-in git/GitHub-driven reconciliation pass that reaps stranded already-merged tickets. **Reviewer focus:** (1) the additive GraphQL/field change in `qrspi_pr_state.py` must not perturb OPEN-path callers; (2) the all-or-nothing merge gate and dirty-`blocked` short-circuit in `classify_cleanup`; (3) the unverified real-reap e2e gap — the destroy path (`git worktree remove` + `git branch -D` + `gt sync --force`) was exercised only via `--dry-run` and the classifier, never against a truly-merged ticket.

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: Fully-merged stack → worktree/branches/remotes removed automatically in `doLand` | `.claude/workflows/qrspi-batch.js:doLand` → `runCleanup(...)` → `scripts/qrspi_cleanup.py:run` | `scripts/qrspi_cleanup_test.py` (merged→destroy) + `parseCleanupEnvelope` in-node round-trip (Slice 3 e2e) |
| AC2: Any unmerged/in-review PR → `skip`, strictly all-or-nothing | `scripts/qrspi_pr_state.py:is_stack_fully_merged` + `scripts/qrspi_cleanup.py:classify_cleanup` | `scripts/qrspi_cleanup_test.py` (partial→skip, in-flight→skip); `scripts/qrspi_pr_state_test.py` (merge-state cases) |
| AC3: Dirty worktree → `blocked`, never destroyed; surfaced in `error`/`reason` | `scripts/qrspi_cleanup.py:classify_cleanup` (porcelain non-empty ⇒ blocked) | `scripts/qrspi_cleanup_test.py` (dirty→blocked); T18 e2e blocked envelope |
| AC4: Cleanup on land + reconciliation pass reaps merged-but-uncleaned tickets | `.claude/workflows/qrspi-batch.js:runReconciliation` / `reconcileCandidates` | `parseCleanupEnvelope` + candidate-id filter verified in-node (T23 partial — see Open Items) |
| AC5: Reconciliation clears the stranded backlog | `.claude/workflows/qrspi-batch.js:reconcileCandidates` (dry-run default) | Manual `qrspi_cleanup.py --ticket RUS-52 --dry-run` e2e (well-formed skip envelope, touched nothing) |
| AC6: Decisions key on authoritative GitHub merge state + automated tests for merged/partial/dirty/in-flight | `scripts/qrspi_pr_state.py:stack_merge_state` (GraphQL `merged`/`state`/`mergedAt`) | `scripts/qrspi_pr_state_test.py` (31 cases) + `scripts/qrspi_cleanup_test.py` (8 cases) |

## Changes by Slice

### Slice 1: Merge-state gatherer in qrspi_pr_state.py

| File | Change | Lines |
|------|--------|-------|
| `scripts/qrspi_pr_state.py` | ⚠️ modified | +53, -4 |
| `scripts/qrspi_pr_state_test.py` | ⚠️ modified | +70, -7 |

PR_QUERY no longer filters `states:OPEN`; `parse_pr_nodes` returns additive `merged`/`state`/`mergedAt` on every record. New pure helpers `stack_merge_state(branches, graphql_nodes)` and `is_stack_fully_merged(merge_state)` (all-or-nothing). Absent/empty branch entry → `{merged:False, prNumber:None, state:None}` sentinel.

### Slice 2: qrspi_cleanup.py (pure classifier + impure reap behind --dry-run)

| File | Change | Lines |
|------|--------|-------|
| `scripts/qrspi_cleanup.py` | ✨ new | +257 |
| `scripts/qrspi_cleanup_test.py` | ✨ new | +94 |

Self-locating script (`REPO_ROOT` two levels up from `__file__`). Pure `classify_cleanup(stack_merge_state, dirty_porcelain)` with precedence blocked > destroy > skip. Impure `run(ticket, dry_run)` gathers merge state, runs `git status --porcelain`, and on `destroy` reaps worktree + local branches + merged remote refs (`gt sync --force`) behind `--dry-run`. Emits one `CleanupEnvelope`. Infra errors caught once → `{ok:false, decision:"skip", error}`, never retried.

### Slice 3: Orchestration wiring (batch land + reconciliation, work SKILL prose)

| File | Change | Lines |
|------|--------|-------|
| `.claude/workflows/qrspi-batch.js` | ⚠️ modified | +157, -5 |
| `.claude/skills/qrspi-work/SKILL.md` | ⚠️ modified | +17, -10 |

`doLand` runs the land worker for merge + Linear→Done only (worktree/branch removal removed from its prompt), then on `fin.ok` calls `runCleanup(id, dryRun=false)`. New `runCleanup` / `parseCleanupEnvelope` (text-return + JS-parse, no StructuredOutput). New opt-in `runReconciliation` / `reconcileCandidates` (gated by `reconcile:true`, `reconcileDryRun` default true) enumerating `.worktrees/*` candidates via `^[A-Z]+-[0-9]+$`; `blocked` logged-and-skipped (OQ2). SKILL `action: land` step 2 now invokes the script; the standing rule names it the only sanctioned `gt sync`/worktree-removal path.

## Testing Summary

- [x] Slice 1: `python3 scripts/qrspi_pr_state_test.py` — 31 passed, 0 failed (4 new merge-state cases)
- [x] Slice 1: `python3 scripts/qrspi_resolve_state_test.py` — 23 passed, 0 failed (OPEN-path callers unaffected)
- [x] Slice 1: `python3 scripts/qrspi_resolve_test.py` — 52 passed, 0 failed (imports pr_state, unaffected)
- [x] Slice 2: `python3 scripts/qrspi_cleanup_test.py` — 8 passed, 0 failed (merged→destroy, partial→skip, dirty→blocked, in-flight→skip + edges)
- [x] Slice 2: `python3 scripts/qrspi_cleanup.py --ticket RUS-52 --dry-run` — well-formed `skip` envelope, exit 0, touched nothing (live gh)
- [x] Slice 2: dirty-worktree e2e → `blocked` envelope with dirty state in `error`/`reason`, short-circuits before gh query
- [x] Slice 3: `node --check .claude/workflows/qrspi-batch.js` — SYNTAX_OK (ESM + top-level await)
- [x] Slice 3: `parseCleanupEnvelope` in-node vs real `qrspi_cleanup.py --dry-run` stdout + destroy/blocked/infra/garbled edges — all 5 pass; candidate-id filter verified
- [x] Slice 3: `grep -nE 'git worktree remove --force|gt sync --force' SKILL.md` — only remaining hit is the new prohibition prose; old executable cleanup commands gone
- [ ] **Not run:** real destroy reap against an actually-merged ticket (see Open Items)

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| Import sources for reused helpers | plan.md §2.9 lists `worktree_path`/`pick_tip` as imports from `qrspi_pr_state.py` | `worktree_path` imported from `qrspi_restack.py`, `pick_tip` from `qrspi_resolve.py` (and `pick_tip` unused) | Those helpers actually live in those modules; structure's "reused as-is, no helper re-derived" is satisfied. `pick_tip` not needed — script enumerates the full stack via `git branch --list <ticket>/*`. (Plan deviation, not a contract deviation.) |
| `classify_cleanup` / `CleanupDecision` / `CleanupEnvelope` | per structure | exact match | No contract/type deviation. |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| Backlog sweep destroys a worktree wrongly judged "merged" | mitigated — pure predicate unit-tested; `--dry-run` default in reconciliation; all-or-nothing gate | Revert Slice 3 reconciliation wiring; reconciliation is opt-in (`reconcile:true`) so default runs are unaffected |
| Extending `qrspi_pr_state.py` query breaks OPEN-path resolver/restack callers | mitigated — fields added additively; resolver (23) + resolve (52) + pr_state (31) suites pass | Revert Slice 1 commit `2fefe99`; cleanup script loses its merge-state source but no other caller regresses |
| Reconciliation can't find finished tickets (batch never sweeps `Done`) | mitigated — reconciliation is git/GitHub-driven (`.worktrees/*` dirs), not a Linear `Done` sweep | Disable via `reconcile:false` (default) |
| Partial merge mid-sweep leaves stack half-reaped | mitigated — strict all-or-nothing classifier; destroy only when every real branch's PR is merged | N/A — gate prevents partial reap |
| `gt sync --force` errors on already-deleted remote refs | mitigated — absent refs / missing worktree treated as clean no-op success | N/A |
| **Discovered-new:** real destroy reap never run against a truly-merged ticket | accepted — JS runner not executable in sandbox, no merged ticket in-flight; only `--dry-run` gate + classifier exercised | First real land/reconciliation run is the de-facto test; reconciliation defaults to dry-run for a safe preview before any real reap |

## Open Items

- **Real-reap e2e gap (carried Slice 2→3):** T17 destroy envelope, T18 blocked envelope, T22 e2e land, and T23 reconciliation real-reap were verified via decision paths (live gh on the in-flight stack, a temp dirty worktree, in-node envelope round-trip) but NOT against an actually-merged ticket. The destroy reap (`git worktree remove` + `git branch -D` + `gt sync --force`) has not been run for real — exercise it on the first live land/reconciliation.
- **OQ3 (deleted-ref query shape):** whether `headRefName` + `states:MERGED` is sufficient, or GitHub-already-deleted refs need explicit reconciliation, remains unconfirmed; a defensive deleted-ref test fixture is included but canonical handling is unverified.
- **OQ4 (`--dry-run` default polarity):** the standalone CLI defaults to destroy-on (no `--dry-run`); `doLand` passes destroy explicitly and reconciliation defaults to dry-run. Whether the CLI should default to dry-run for safety is undecided.
- **Cwd contract for destroy:** `runCleanup` must be invoked from the MAIN repo root so the script self-locates the real `.worktrees/<id>`; running from inside a worktree treats the target as missing → `skip`. The orchestrator wiring honors this, but it is a standing operational constraint to preserve.
