# Implementation Log — RUS-52

## Session 1 — Slice 1

**Timestamp:** 2026-06-08
**Tasks completed:** T1, T2, T3, T4, T5, T6, T7
**Tasks failed:** none
**Tests:**

- `python3 scripts/qrspi_pr_state_test.py` → 31 passed, 0 failed (includes 4 new merge-state cases + the additive merged-PR parse case)
- `python3 scripts/qrspi_resolve_state_test.py` → 23 passed, 0 failed (OPEN-path callers unaffected)
- `python3 scripts/qrspi_resolve_test.py` → 52 passed, 0 failed (sibling suite that imports pr_state — also unaffected)

**Deviations from structure.md:**

- none

**Deviations from plan.md:**

- none

**Notes for next session:**

- `qrspi_pr_state.parse_pr_nodes` now returns three additive keys on EVERY record (including the no-PR record): `merged: bool`, `state: str|None`, `mergedAt: str|None`. Existing keys (`prExists`/`number`/`reviewDecision`/`unresolvedThreads`) are untouched.
- The GraphQL `PR_QUERY` no longer filters `states:OPEN` — it now returns MERGED/CLOSED PRs too and selects `state`, `merged`, `mergedAt`. This is required for the merge-state gatherer; OPEN-path callers read `parse_pr_nodes([...])[0]` (most-recent by CREATED_AT desc) as before.
- Two new pure helpers in `qrspi_pr_state.py`: `stack_merge_state(branches, graphql_nodes) -> { branch: {merged, prNumber, state} }` and `is_stack_fully_merged(merge_state) -> bool`. `graphql_nodes` is a dict mapping branch head-ref name -> that branch's GraphQL pullRequests.nodes list. An absent/empty entry (GitHub already deleted the merged head ref) maps to the sentinel `{merged: False, prNumber: None, state: None}` and never crashes.
- `is_stack_fully_merged` is all-or-nothing: empty stack -> False; any single unmerged branch -> False.
- The build_state subprocess path (`_query_pr`) feeds `parse_pr_nodes` a single branch's nodes; it does NOT yet build the `{branch -> nodes}` dict that `stack_merge_state` consumes. Wiring the gatherer/CLI to assemble that dict and expose a stack-merged verdict is downstream slice work, not done here.

---

## Session 2 — Slice 2

**Timestamp:** 2026-06-08
**Tasks completed:** T8, T9, T10, T11, T12, T13, T14, T15, T16, T17, T18
**Tasks failed:** none
**Tests:**

- `python3 scripts/qrspi_cleanup_test.py` → 8 passed, 0 failed (the four required classifier cases — merged→destroy, partial→skip, dirty→blocked, in-flight→skip — plus edges: whitespace-only porcelain treated clean, empty stack→skip, empty+dirty→blocked, dirty blocks even a fully-merged stack)
- T17 e2e: `python3 scripts/qrspi_cleanup.py --ticket RUS-52 --dry-run` → well-formed envelope `{ok:true, decision:"skip", reason:"stack not fully merged", removed:{worktree:false,branches:[],remotes:[]}, dryRun:true}`, exit 0, touched nothing (live gh query against the in-flight stack)
- T18 e2e: blocked path verified functionally against a temp dirty worktree → `{ok:true, decision:"blocked", reason:"…: ?? untracked.txt", error:"?? untracked.txt", dryRun:true}`; confirmed dirty short-circuits before any gh query

**Deviations from structure.md:**

- none on contracts/types. `classify_cleanup(stack_merge_state, dirty_porcelain)` signature, `CleanupDecision`, and `CleanupEnvelope` shape match exactly.

**Deviations from plan.md:**

- Plan step §2.9 lists `worktree_path`/`pick_tip` as imports "from `qrspi_pr_state.py`", but those two live in `qrspi_restack.py` (`worktree_path`) and `qrspi_resolve.py` (`pick_tip`) — only `branch_set`/`slice_numbers`/`real_branches`/`stack_merge_state`/`is_stack_fully_merged` are in `qrspi_pr_state.py`. Imported each from its actual module (the structure's "Reused as-is from existing scripts" wording is satisfied; no helper was re-derived). `pick_tip` was not needed (the script enumerates the full stack via `git branch --list <ticket>/*`, not a single tip), so it is not imported.

**Real e2e gaps (need a real landed/dirty ticket, not available in-flight):**

- T17's *destroy* envelope and T18's *blocked* envelope were verified by exercising the decision paths (live gh on the in-flight stack for the wiring/shape; a temp dirty git worktree for blocked) rather than against an actually-merged ticket. The destroy reap (`git worktree remove`, `git branch -D`, `gt sync --force`) has NOT been run for real — only the dry-run gate (which executes none of it) and the classifier were exercised.

**Notes for next session:**

- `scripts/qrspi_cleanup.py` is self-locating (`REPO_ROOT` = two levels up from `__file__`) exactly like `qrspi_resolve.py`. Run from the MAIN checkout, `REPO_ROOT` is the main repo and `worktree_path(REPO_ROOT, id)` = `<repo>/.worktrees/<id>` (the real worktree). Run from inside a worktree (as in this slice), `REPO_ROOT` is the worktree and the target `.worktrees/<id>` is absent → treated as clean/missing (Q11) → skip. The orchestrator should invoke it from the main checkout for the destroy path to see the real worktree.
- Public API: pure `classify_cleanup(stack_merge_state, dirty_porcelain) -> {decision, reason}` (blocked > destroy > skip), and `run(ticket, dry_run) -> CleanupEnvelope`. CLI: `--ticket <id> [--dry-run]`, single envelope to stdout, exit 0 on `ok:true` / 1 on `ok:false`.
- Remote-ref prune uses `gt sync --force` (one pass for the whole stack), gated entirely by `--dry-run`. `removed.remotes` lists branches whose `refs/heads/<b>` was present on `origin` (via `git ls-remote --heads origin`); a dry run reports what WOULD be pruned without running `gt`.
- Infra errors (gh/git/gt failures) are caught once in `run()` and surfaced as `{ok:false, decision:"skip", error:"<verbatim>"}` — never retried.

---

## Session 3 — Slice 3

**Timestamp:** 2026-06-08
**Tasks completed:** T19, T20, T21, T24 (T22/T23 partial — see e2e gaps)
**Tasks failed:** none
**Tests:**

- `node --check .claude/workflows/qrspi-batch.js` → SYNTAX_OK (ESM + top-level await parse clean)
- `python3 scripts/qrspi_cleanup_test.py` → 8 passed, 0 failed (contract unchanged; confirms no incidental break)
- `parseCleanupEnvelope` verified in-node against the REAL `qrspi_cleanup.py --dry-run` stdout plus destroy/blocked/infra/garbled edges → all 5 PASS; candidate-id filter (`/^[A-Z]+-[0-9]+$/` + dedup + sort) verified → drops non-ticket/lowercase, dedups, sorts
- T24 grep `grep -nE 'git worktree remove --force|gt sync --force' .claude/skills/qrspi-work/SKILL.md` → the only remaining hit (line 406) is the new *prohibition* ("do NOT hand-run …") inside the script-invocation prose; the old executable land-cleanup commands are gone

**Deviations from structure.md:**

- none on contracts. `doLand` now invokes `qrspi_cleanup.py --ticket <id>` as a single verbatim command and folds the parsed `CleanupEnvelope` into `results` (per the batch-invocation contract); reconciliation invokes the same script per candidate.

**Deviations from plan.md:**

- none. T19/T20/T21 implemented as specified. One scope clarification on T24: `git worktree remove "$WORKTREE_PATH" --force 2>/dev/null` in the SKILL's "Stale worktree recovery" section (the pre-`git worktree add` retry path, now line 603) is INTENTIONALLY preserved — it is not land-cleanup and the cleanup script does not cover that path. Only the `action: land` executable cleanup prose was replaced. The remaining `--force` grep hit (line 406) is a negated reference instructing the worker NOT to hand-run those mutations.

**Real e2e gaps (carried from Slice 2 — still need a real merged ticket + the live Workflow runner):**

- T22 (e2e land) and T23 (e2e reconciliation real-reap) were NOT run against an actually-merged ticket: the JS Workflow runner is not executable in this sandbox and no merged ticket exists in-flight. Verified instead: the JS parses cleanly; the cleanup script's `--dry-run` envelope (the exact shape `doLand`/reconciliation consume) is well-formed and round-trips through `parseCleanupEnvelope`; the classifier `destroy`/`blocked`/`skip` paths are unit-tested (Slice 2). The destroy reap (`git worktree remove` + `git branch -D` + `gt sync --force`, all inside the script) has STILL not been run for real — only the dry-run gate and classifier.

**Notes for next session:**

- `doLand` (`.claude/workflows/qrspi-batch.js`) now: (1) runs the land worker for merge + Linear→Done ONLY (the worker no longer removes the worktree / deletes branches / runs `gt sync --force` — its prompt forbids it); (2) iff `fin.ok`, calls `runCleanup(t.id, dryRun=false, 'Finalize')`. A failed/partial land skips the reap (the idempotent script reaps on a later run / reconciliation). The cleanup outcome is attached as `res.cleanup`.
- New `runCleanup(ticketId, dryRun, phaseLabel)` worker: cwd MUST be the MAIN repo root (the script self-locates REPO_ROOT and needs the real `.worktrees/<id>` for destroy). Returns the parsed `CleanupEnvelope`. `parseCleanupEnvelope` mirrors `parseRestackEnvelope` (text-return + JS-parse, no StructuredOutput) and validates `ok` + `decision`; garbled echo → clean `{ok:false, decision:"skip", error}`.
- Reconciliation pass (`runReconciliation(processed)` + `reconcileCandidates()`): OPT-IN via input `reconcile:true` (default OFF), DRY-RUN by default via `reconcileDryRun` (default true — pass `false` to actually reap). Candidates are enumerated from `ls -1 .worktrees` filtered to `^[A-Z]+-[0-9]+$` (git/disk state, NOT a Linear `Done` sweep — Q8/OQ1). Excludes tickets this run's main loop already processed. Per-ticket: `blocked` is logged and SKIPPED, `skip` (in-flight) left untouched, `destroy` reaped — one ticket never halts the pass (OQ2). Runs even when the in-flight queue is empty (the early-return path also fires it). New meta phase `Reconcile`; outcomes returned under top-level `reconciliation`.
- SKILL `action: land`: step 2 now invokes `python3 scripts/qrspi_cleanup.py --ticket <ticket-id>` from `$REPO_ROOT`; the standing rule (former line 538) now names the script as the only sanctioned `gt sync`/worktree-removal path.

---
