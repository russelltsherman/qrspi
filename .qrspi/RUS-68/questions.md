# Questions — qrspi_cleanup.py falsely reports remote branch deletion that never happened

**Ticket:** RUS-68
**Generated:** 2026-06-11T00:00:00Z
**Status:** answered

> Answers are integrated inline below, sourced from `research.md` @ 2026-06-11T00:00:00Z
> (the codebase map). Each answer is a one-line summary of the corresponding `research.md`
> section; the full evidence (code excerpts, file:line refs, implicit contracts) lives there.

## Data Flow

- Q1: How does qrspi_cleanup.py discover which remote refs belong to a ticket, and does that discovery read from the now-removed worktree, the main checkout's locally-tracked branches, or directly from origin?
  **Target:** scripts/qrspi_cleanup.py (the remote-ref discovery/reaping path)
  **Answer:** A two-step intersection — branch *names* come from the main checkout's locally-tracked branches (`git branch --list <ticket>/*` in `_stack_branches`, `cwd=REPO_ROOT`), and the refs actually on origin come from `git ls-remote --heads origin` in `_prune_remote_refs`. The reported set is `remotes = [b for b in branches if b in present]`, so an origin ref with no matching local branch name is never even considered. Discovery is therefore local-branch-driven, not origin-driven.
- Q2: In what order does qrspi_cleanup.py remove the worktree, local branches, and remote refs, and does remote-ref deletion run before or after the worktree is removed?
  **Target:** scripts/qrspi_cleanup.py (the reaping sequence)
  **Answer:** Fixed order in the `destroy` branch of `run`: (1) remove worktree, (2) delete local branches, (3) "prune" remote refs. Remote handling runs *after* both the worktree and the local branches are already gone.

## API Surface

- Q4: What is the exact structure of the JSON envelope qrspi_cleanup.py returns (the `removed` object and its `remotes`, `worktree`, and local-branch fields), and which callers consume it?
  **Target:** scripts/qrspi_cleanup.py and the module/workflow that invokes cleanup (the batch Reconcile pass)
  **Answer:** `_envelope` returns `{ ok, repoRoot, decision: "destroy"|"skip"|"blocked", reason, removed: {worktree: bool, branches: [str], remotes: [str]}, dryRun, error? }`. The sole consumer is the qrspi-batch workflow: `runCleanup` invokes the script, `parseCleanupEnvelope` validates `ok`/`decision`, and `doLand` + the Reconcile pass log `removed.worktree`/`.branches`/`.remotes` (`qrspi-batch.js:816-817`).
- Q5: What git mechanism does qrspi_cleanup.py invoke to delete a remote ref (e.g. a push with delete refspec, a branch-delete that piggybacks on a tracked local branch, or a direct origin operation), and what does that command require to exist locally?
  **Target:** scripts/qrspi_cleanup.py (the remote-deletion call site)
  **Answer:** There is **no direct remote-ref deletion** — no `git push origin --delete`, no delete refspec. The only remote-mutating command is `gt sync --force`, which prunes local branches whose PRs merged plus their remote refs in one pass. It requires a **local branch tracking the merged PR** to act — but those local branches were already deleted in step 2 (Q2), so by step 3 it may have nothing to key off.
- Q6: How does qrspi_cleanup.py distinguish dry-run from a real run, and where in the code does the dry-run branch decide what to report as "would delete"?
  **Target:** scripts/qrspi_cleanup.py (the dry-run flag handling)
  **Answer:** `--dry-run` is a `store_true` argparse flag threaded as `dry_run` into each mechanic; the classifier decision is computed identically with or without it ("faithful preview"). Each mechanic gates only the destructive call. For remotes, dry-run returns the presence list before reaching `gt sync` — but because a *real* run also reports presence (Q3), dry-run and real-run produce the same `removed.remotes`: the preview is faithful to presence, not to actual deletion.

## State Management

- Q3: How is the `removed.remotes` field in the returned JSON envelope populated — from the set of refs found present at the start of the run, or from the result of each deletion attempt?
  **Target:** scripts/qrspi_cleanup.py (the envelope assembly / removed.remotes)
  **Answer:** **From presence, NOT from deletion result.** `_prune_remote_refs` returns the `git ls-remote` presence list whether or not any deletion occurred, never re-checks origin after `gt sync`, and never inspects what was actually pruned. This is the root cause: `removed.remotes` is a presence list relabelled as a deletion list.
- Q7: After the worktree is removed, what record (if any) remains in the main checkout that maps a ticket to its remote branch names, and is that mapping what the remote-deletion step relies on?
  **Target:** scripts/qrspi_cleanup.py (ticket-to-branch resolution) and the main checkout's branch state
  **Answer:** The only mapping is the local branch names in the main checkout (`git branch --list <ticket>/*`), captured once at `run` start before the worktree is removed. There is no separate ticket→remote-branch record (no config, no metadata). If the branches lived only in the now-gone worktree, this set is empty and the remote step has no names to match against `present`.
- Q8: Does qrspi_cleanup.py track per-ref success/failure during deletion, or does it treat the whole remote-ref step as a single all-or-nothing outcome?
  **Target:** scripts/qrspi_cleanup.py (deletion result tracking)
  **Answer:** Neither per-ref tracking nor a per-ref outcome at all — remote deletion is a single all-at-once `gt sync --force` call for the whole stack, with no per-ref loop and no per-ref result capture. The returned list is the presence list unconditionally; the only failure signal is `gt sync`'s overall exit code (Q10).

## Edge Cases

- Q9: How does qrspi_cleanup.py behave when a remote ref it intends to delete is already absent on origin — does it treat that as success, error, or skip?
  **Target:** scripts/qrspi_cleanup.py (idempotency / already-absent ref handling)
  **Answer:** Silently skipped → treated as a clean no-op. A ref not in `present` (the `git ls-remote` snapshot) is excluded from `remotes` by the `if b in present` filter, so it is never reported and never acted on. The docstring calls this out as idempotent; there is no signal that an expected ref was already gone.
- Q10: What does qrspi_cleanup.py do when a remote-deletion git command exits non-zero — is the error captured, surfaced in the envelope, or swallowed while still reporting success?
  **Target:** scripts/qrspi_cleanup.py (deletion error handling)
  **Answer:** Only `gt sync --force`'s exit code is checked. A non-zero rc raises `RuntimeError` → broad `except` → `ok:false`, `decision:"skip"`, `error:str(exc)`. But the false-positive case is the inverse: a **zero-exit-but-pruned-nothing** run still returns the presence list and reports `ok:true` with those refs listed as deleted. The failure path is robust; the silent-no-op success is the unguarded gap.
- Q11: How does qrspi_cleanup.py handle a ticket whose branches were only ever present in a worktree that no longer exists (the RUS-40 scenario), where no local branch in the main checkout maps to the remote refs?
  **Target:** scripts/qrspi_cleanup.py (the worktree-only branch case)
  **Answer:** It reports nothing and classifies the stack as `skip`. `_stack_branches` reads the main checkout; if the branches lived only in a vanished worktree it enumerates an empty set → `_gather_merge_state` queries no PRs → `is_stack_fully_merged({})` is False → `classify_cleanup` returns `skip`, so destroy never runs. Even if it did, `_prune_remote_refs([])` intersects an empty set with origin → `[]`. Genuinely-merged remote refs are stranded with no origin-driven discovery to catch them.

## Testing

- Q12: What existing tests cover qrspi_cleanup.py's remote-ref reporting, and do any of them assert that `removed.remotes` reflects actual deletion rather than presence?
  **Target:** scripts/qrspi_cleanup_test.py (or the cleanup module's `_test.py` sibling)
  **Answer:** None. `qrspi_cleanup_test.py` is stdlib-only and exercises only the pure `classify_cleanup` decision ("NO subprocess mocks"). There is no test of `_prune_remote_refs`, `run`, the envelope, or `removed.remotes` — the false-deletion bug has zero coverage.
- Q13: How do the existing cleanup tests stand in for origin and git remote operations (real temp repo, fake remote, or stubbed subprocess), and can a test observe the post-run state of remote refs?
  **Target:** scripts/qrspi_cleanup_test.py (test harness / git fixtures)
  **Answer:** They do not — no temp repo, no fake remote, no stubbed subprocess. Tests build in-memory `StackMergeState` maps and feed them to the pure classifier, so no test can observe post-run remote-ref state. Validating real deletion would require breaking the stdlib-only/pure-function convention (a temp-repo/fake-remote fixture).

## Observability

- Q14: What does qrspi_cleanup.py emit (logs, envelope fields, exit code) when remote-ref deletion silently leaves refs behind, and is there any signal a maintainer or the batch Reconcile pass could use to detect the stranded-ref condition?
  **Target:** scripts/qrspi_cleanup.py (logging / envelope reporting on the deletion path)
  **Answer:** When `gt sync` exits zero but prunes nothing, it emits `ok:true`, `decision:"destroy"`, `removed.remotes` = the presence list (claiming deletion), exit 0. There is **no logging** at all (only the single JSON envelope on stdout), and **no signal** for the maintainer or Reconcile pass: the script never re-queries origin to confirm absence, so a stranded ref is indistinguishable from a deleted one. Only a hard non-zero `gt sync` exit surfaces a problem.
