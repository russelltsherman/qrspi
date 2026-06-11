# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** draft

All questions target `scripts/qrspi_cleanup.py` (10911 bytes), with supporting
functions in `scripts/qrspi_pr_state.py`, `scripts/qrspi_restack.py`,
`scripts/qrspi_resolve.py`, the caller in `.claude/workflows/qrspi-batch.js`, and
tests in `scripts/qrspi_cleanup_test.py`.

## Q1: How does qrspi_cleanup.py discover which remote refs belong to a ticket, and does that discovery read from the now-removed worktree, the main checkout's locally-tracked branches, or directly from origin?

**Answer:** Discovery is a two-step intersection. (a) The ticket's branch names come
from the **main checkout's locally-tracked branches** via `git branch --list <ticket>/*`
in `_stack_branches` (run with `cwd=REPO_ROOT`, the main checkout). (b) The set of refs
actually on origin comes **directly from origin** via `git ls-remote --heads origin` in
`_prune_remote_refs`. The "remotes belonging to the ticket" is the intersection:
`remotes = [b for b in branches if b in present]`. Critically, `branches` is sourced
from local branch names, NOT from origin — so if a branch name is absent locally, it is
never considered for remote pruning even if its ref still exists on origin.

**Evidence:**

```python
def _stack_branches(ticket):
    rc, out, _ = _run(["git", "branch", "--list", "%s/*" % ticket], cwd=REPO_ROOT)
    return branch_set(out.splitlines()) if rc == 0 else set()

def _prune_remote_refs(branches, dry_run):
    rc, out, _ = _run(["git", "ls-remote", "--heads", "origin"], cwd=REPO_ROOT)
    present = set()
    if rc == 0:
        for line in out.splitlines():
            parts = line.split()
            if len(parts) == 2 and parts[1].startswith("refs/heads/"):
                present.add(parts[1][len("refs/heads/"):])
    remotes = [b for b in branches if b in present]
```

— `scripts/qrspi_cleanup.py:109-113` and `scripts/qrspi_cleanup.py:164-175`
**Dependencies:** `branch_set` from `qrspi_pr_state.py:286`; relies on `git` and the
`origin` remote being reachable from `REPO_ROOT`.
**Implicit contracts:** A ticket's remote refs are only ever discovered through the
intersection with locally-tracked branch names. Origin-only refs (no local branch) are
invisible to the discovery path — this is the structural seam behind the RUS-40 scenario
(Q11).

## Q2: In what order does qrspi_cleanup.py remove the worktree, local branches, and remote refs, and does remote-ref deletion run before or after the worktree is removed?

**Answer:** Order is fixed in the `destroy` branch of `run`: (1) worktree removed, (2)
local branches deleted, (3) remote refs "pruned". Remote-ref handling runs **after** the
worktree is removed and after local branches are deleted.

**Evidence:**

```python
if decision["decision"] == "destroy":
    removed["worktree"] = _remove_worktree(wt_path, dry_run)
    removed["branches"] = sorted(
        b for b in branches if _delete_local_branch(b, dry_run))
    removed["remotes"] = sorted(_prune_remote_refs(branches, dry_run))
```

— `scripts/qrspi_cleanup.py:229-233`
**Dependencies:** `_remove_worktree` (`:133`), `_delete_local_branch` (`:148`),
`_prune_remote_refs` (`:164`).
**Implicit contracts:** `branches` (the local-branch set captured at `run` start, line
209) is reused for the remote-prune call even though local branches were just deleted in
step 2. The set is captured once before any destruction, so the remote step still sees
the pre-deletion branch names. But `_prune_remote_refs` invokes `gt sync --force`, which
prunes based on *local* branch+PR state — and those local branches are already gone by
step 3, which undermines what `gt sync` can prune.

## Q3: How is the `removed.remotes` field populated — from refs found present at the start, or from the result of each deletion attempt?

**Answer:** **From presence, NOT from deletion result.** `_prune_remote_refs` returns
`remotes` — the list of branch names whose ref was present on origin at the time of the
`git ls-remote` snapshot. It returns that same `remotes` list whether or not any deletion
actually occurred. It never re-checks origin after the `gt sync --force` call, never
inspects `gt sync`'s output to learn which refs it actually pruned, and never deletes
the refs itself with a delete refspec. This is the root cause of "falsely reports remote
branch deletion that never happened": `removed.remotes` is a presence list relabelled as
a deletion list.

**Evidence:**

```python
    remotes = [b for b in branches if b in present]
    if dry_run or not remotes:
        return remotes
    # gt sync --force prunes local branches whose PRs have merged and their remote
    # refs in one pass (Decision 2/3). We invoke it once for the whole stack.
    src, out2, err2 = _run(["gt", "sync", "--force"], cwd=REPO_ROOT)
    if src != 0:
        raise RuntimeError("gt sync --force failed: %s"
                           % (err2.strip() or out2.strip()))
    return remotes   # <-- presence list, unchanged by what gt sync actually did
```

— `scripts/qrspi_cleanup.py:175-184`
**Dependencies:** `gt sync --force`.
**Implicit contracts:** The caller and the envelope treat `removed.remotes` as "refs that
were deleted", but the producer only guarantees "refs that were present at scan time."
This mismatch is the documented-vs-actual gap (see Inconsistencies).

## Q4: What is the exact structure of the JSON envelope, and which callers consume it?

**Answer:** The envelope is assembled by `_envelope`:
`{ ok: bool, repoRoot: str, decision: "destroy"|"skip"|"blocked", reason: str,
removed: {worktree: bool, branches: [str], remotes: [str]}, dryRun: bool, error?: str }`.
`removed` is initialized at `run` start as `{"worktree": False, "branches": [], "remotes": []}`.
The single consumer is the qrspi-batch workflow: `runCleanup` invokes the script,
`parseCleanupEnvelope` validates `ok`/`decision`, and `doLand` (post-merge) plus the
Reconcile pass log `cl.removed?.worktree`, `cl.removed?.branches`, `cl.removed?.remotes`.

**Evidence:**

```python
def _envelope(ok, decision, reason, removed, dry_run, error=None):
    env = {"ok": ok, "repoRoot": REPO_ROOT, "decision": decision,
           "reason": reason, "removed": removed, "dryRun": dry_run}
    if error is not None:
        env["error"] = error
    return env
```

— `scripts/qrspi_cleanup.py:189-200`; init at `:206`; output at `:250-253`.

```javascript
} else if (cl.decision === 'destroy') {
    log(`  ${t.id}: cleaned up — worktree ${cl.removed?.worktree ? 'removed' : 'absent'}, branches [${(cl.removed?.branches ?? []).join(', ')}], remotes [${(cl.removed?.remotes ?? []).join(', ')}]`)
```

— `.claude/workflows/qrspi-batch.js:816-817` (consumer); parser at `:172-180`;
invocation at `:781-792`.
**Dependencies:** `.claude/workflows/qrspi-batch.js` `doLand` (`:798`) and the Reconcile
pass (`:837+`).
**Implicit contracts:** The batch log line directly prints `removed.remotes` as the list
of remotes it "cleaned up" — so the false-deletion list (Q3) is surfaced verbatim to the
operator as a deletion claim.

## Q5: What git mechanism deletes a remote ref, and what does that command require to exist locally?

**Answer:** There is **no direct remote-ref deletion** — no `git push origin --delete`,
no `:refs/heads/...` delete refspec, no `gh api` ref delete. The only remote-mutating
command is `gt sync --force` (Graphite), invoked once for the whole stack. Per the inline
comment, `gt sync --force` "prunes local branches whose PRs have merged and their remote
refs." This requires (a) the `gt` CLI installed and authenticated, and (b) a **local
branch tracking the merged PR** for `gt` to recognize and prune — but by the time it runs
(step 3, Q2), the local branches were already deleted with `git branch -D` in step 2.

**Evidence:**

```python
    # gt sync --force prunes local branches whose PRs have merged and their remote
    # refs in one pass (Decision 2/3). We invoke it once for the whole stack.
    src, out2, err2 = _run(["gt", "sync", "--force"], cwd=REPO_ROOT)
```

— `scripts/qrspi_cleanup.py:178-180`
**Dependencies:** `gt` CLI; `origin`.
**Implicit contracts:** Remote pruning is delegated entirely to `gt sync`'s own
heuristic, which keys off local branch + PR state. The script assumes `gt sync` will
prune the same refs it scanned in `present`, but it never verifies this, and the
prerequisite local branches no longer exist when `gt sync` runs. `grep` for
`push.*delete` / `--delete` in the file returns nothing — confirming no direct deletion.

## Q6: How does qrspi_cleanup.py distinguish dry-run from a real run, and where does the dry-run branch decide what to report as "would delete"?

**Answer:** `--dry-run` is a `store_true` argparse flag threaded as `dry_run` through
`run` into each mechanic. The classifier decision (`classify_cleanup`) is computed
**identically** regardless of `dry_run` (documented "faithful preview", Decision 4).
Each mechanic gates only the destructive call: when `dry_run` is True, `_remove_worktree`
and `_delete_local_branch` return the presence boolean without acting; `_prune_remote_refs`
returns the presence list `remotes` before reaching the `gt sync` call. So in dry-run mode
the script reports the *presence* set as "would delete." NOTE: because a real run ALSO
reports presence (Q3), dry-run and real-run produce the same `removed.remotes` — the
preview is only faithful to presence, not to actual deletion outcome.

**Evidence:**

```python
def _prune_remote_refs(branches, dry_run):
    ...
    remotes = [b for b in branches if b in present]
    if dry_run or not remotes:
        return remotes
```

— `scripts/qrspi_cleanup.py:164-176`; flag def at `:246-247`; identical-decision comment
at `:212`.
**Dependencies:** argparse.
**Implicit contracts:** "Dry-run is a faithful preview" holds for the *decision* and for
*presence*, but not for actual remote-deletion success — there is no code path that
distinguishes "would be deleted" from "was deleted" because no path observes deletion.

## Q7: After the worktree is removed, what record maps a ticket to its remote branch names, and is that mapping what the remote-deletion step relies on?

**Answer:** The only mapping is the **local branch names in the main checkout**
(`git branch --list <ticket>/*`), captured once at `run` start (`branches = _stack_branches(ticket)`,
line 209) BEFORE the worktree is removed. The remote-prune step relies on this local-branch
set: `_prune_remote_refs(branches, ...)`. There is no separate ticket→remote-branch record
(no config file, no metadata). If the ticket's branches were never tracked in the main
checkout (only in the now-gone worktree), `branches` is empty and the mapping yields
nothing — so the remote step has no names to match against `present`.

**Evidence:**

```python
        wt_path = worktree_path(REPO_ROOT, ticket)
        branches = _stack_branches(ticket)
        dirty = _dirty_porcelain(wt_path)
```

— `scripts/qrspi_cleanup.py:208-210`; reused at `:233`.
**Dependencies:** `git branch --list`; `worktree_path` (`qrspi_restack.py:69`).
**Implicit contracts:** Branch-name resolution is entirely main-checkout-local. The system
assumes ticket branches are visible to the main checkout. Per `branch_set`'s own docstring
(`qrspi_pr_state.py:286-292`), branches checked out in a worktree DO appear in
`git branch --list` from the main checkout — carrying a `+` marker that `branch_set` strips
— but ONLY while that worktree still exists. Once the worktree is gone, those branches may
no longer be enumerable from the main checkout (the RUS-40 case, Q11).

## Q8: Does qrspi_cleanup.py track per-ref success/failure during deletion, or all-or-nothing?

**Answer:** **Neither per-ref tracking nor a per-ref outcome at all.** Remote deletion is a
single all-at-once `gt sync --force` call for the whole stack. There is no per-ref loop,
no per-ref result capture, and no per-ref success/failure recording. By contrast, local
branches and the worktree ARE tracked per-item (each `_delete_local_branch`/`_remove_worktree`
returns a presence bool the comprehension filters on), but even there the bool reflects
*pre-deletion presence*, not confirmed deletion. For remotes, the returned list is the
presence list unconditionally.

**Evidence:**

```python
    removed["branches"] = sorted(
        b for b in branches if _delete_local_branch(b, dry_run))
    removed["remotes"] = sorted(_prune_remote_refs(branches, dry_run))
```

— `scripts/qrspi_cleanup.py:231-233`; `_prune_remote_refs` returns the whole `remotes`
list (`:184`).
**Dependencies:** `gt sync --force`.
**Implicit contracts:** Remote pruning is treated as a single opaque operation whose
per-ref outcome is never inspected; the only failure signal is `gt sync`'s overall exit
code (Q10).

## Q9: How does qrspi_cleanup.py behave when a remote ref it intends to delete is already absent on origin?

**Answer:** Already-absent remote refs are silently skipped → treated as a clean no-op.
A ref that is not in `present` (the `git ls-remote` snapshot) is excluded from `remotes`
by the `if b in present` filter, so it is never reported and never acted on. The docstring
explicitly calls this out as idempotent (Q12). No error, no skip-record — it simply is not
in the output list.

**Evidence:**

```python
    remotes = [b for b in branches if b in present]
```

— `scripts/qrspi_cleanup.py:175`; idempotency claim in module docstring at `:24-25` and
function docstring at `:164-167`.
**Dependencies:** `git ls-remote --heads origin`.
**Implicit contracts:** Absence-on-origin is indistinguishable from never-existed in the
output — both yield exclusion. There is no signal that a ref the operator expected was
already gone.

## Q10: What does qrspi_cleanup.py do when a remote-deletion git command exits non-zero?

**Answer:** Only the **`gt sync --force` exit code** is checked. A non-zero rc raises
`RuntimeError`, which propagates to `run`'s broad `except Exception`, producing an
envelope with `ok: False`, `decision: "skip"`, `reason: "infrastructure error"`, and
`error: str(exc)`. CRITICAL: because `removed["remotes"]` is assigned the
`_prune_remote_refs(...)` return value LAST in the destroy block (line 233), a `gt sync`
failure raises BEFORE that assignment completes — so on failure `removed.remotes` stays
`[]` and the envelope is `ok:false`. But the false-positive case is the inverse: when
`gt sync` exits **zero** but prunes *nothing* (e.g. local branches already deleted so it
has nothing to recognize), the presence list is still returned and reported as deleted
with `ok:true`. The error is only captured when `gt sync` itself fails; a no-op success
is reported as a successful deletion.

**Evidence:**

```python
    src, out2, err2 = _run(["gt", "sync", "--force"], cwd=REPO_ROOT)
    if src != 0:
        raise RuntimeError("gt sync --force failed: %s"
                           % (err2.strip() or out2.strip()))
```

— `scripts/qrspi_cleanup.py:180-183`; broad catch at `:237-239`.
**Dependencies:** `gt`.
**Implicit contracts:** Error surfacing keys on `gt sync`'s exit code only. A
zero-exit-but-pruned-nothing run is silently reported as a successful deletion of the
presence list — the exact false-success the ticket title describes.

## Q11: How does qrspi_cleanup.py handle a ticket whose branches were only ever present in a worktree that no longer exists (the RUS-40 scenario)?

**Answer:** It reports **nothing** for that ticket's branches and remotes, and likely
classifies the stack as `skip`. `_stack_branches` reads `git branch --list <ticket>/*`
from the MAIN checkout; if those branches lived only in a worktree that is now gone, the
main checkout enumerates an empty/partial set. With an empty `branches` set:
(a) `_gather_merge_state` queries no PRs → `merge_state == {}` → `is_stack_fully_merged({})`
returns False → `classify_cleanup` returns `skip` (the stack is never seen as fully
merged, so the destroy branch never runs); (b) even if destroy did run, `_prune_remote_refs([])`
intersects an empty branch set with origin → returns `[]`. So genuinely-merged remote
refs from a vanished worktree are neither discovered nor deleted nor reported — they are
stranded, and the envelope claims `skip`/"stack not fully merged" rather than flagging the
orphaned refs.

**Evidence:**

```python
def is_stack_fully_merged(merge_state):
    if not merge_state:
        return False
    return all(entry.get("merged") for entry in merge_state.values())
```

— `scripts/qrspi_pr_state.py:249-256`; empty-branch path: `_stack_branches`
(`qrspi_cleanup.py:109-113`) → `_gather_merge_state` (`:125-130`) → `classify_cleanup`
(`:80-88`). Note `branch_set` docstring (`qrspi_pr_state.py:286-292`) documents that
worktree-checked-out branches normally appear with a `+` marker — implying they are only
visible while the worktree exists.
**Dependencies:** `git branch --list`, `_gather_merge_state`, `is_stack_fully_merged`.
**Implicit contracts:** Discovery is wholly local-branch-driven. A worktree-only branch set
that vanished with its worktree is invisible to the whole pipeline — there is no
origin-driven discovery path to catch it.

## Q12: What existing tests cover the remote-ref reporting, and do any assert `removed.remotes` reflects actual deletion?

**Answer:** **None.** `scripts/qrspi_cleanup_test.py` is stdlib-only and exercises ONLY the
pure `classify_cleanup` decision (destroy/skip/blocked across merged/partial/in-flight/
dirty/empty cases). It explicitly states "NO subprocess mocks — only the pure classifier
is exercised." There is no test of `_prune_remote_refs`, `_remove_worktree`,
`_delete_local_branch`, `run`, the envelope, or `removed.remotes`. No test asserts anything
about presence-vs-deletion for remotes.

**Evidence:**

```python
"""Unit tests for qrspi_cleanup.classify_cleanup (the pure destroy/skip/blocked
decision). Stdlib-only, assert/check() style, NO subprocess mocks — only the pure
classifier is exercised (ref: Q13, Q14). Run: python3 scripts/qrspi_cleanup_test.py
"""
...
from qrspi_cleanup import classify_cleanup
```

— `scripts/qrspi_cleanup_test.py:1-9` (only import is `classify_cleanup`); the 8 `check(...)`
cases at `:33-85` all call `classify_cleanup`.
**Dependencies:** `classify_cleanup`, `stack_merge_state`.
**Implicit contracts:** The reaping/envelope/remote-deletion layer is entirely untested —
the false-deletion bug has zero test coverage that would catch it.

## Q13: How do the existing cleanup tests stand in for origin and git remote operations, and can a test observe post-run state of remote refs?

**Answer:** They do not stand in for them at all. There is no temp repo, no fake remote,
no stubbed subprocess. The tests construct `StackMergeState` maps in-memory via
`stack_merge_state` + a `_node` fixture helper and feed them to the pure classifier. No
test sets up git/origin, so no test can observe post-run remote-ref state. (Other scripts
in the repo, e.g. the broader `qrspi_*_test.py` siblings, follow the same stdlib-only,
pure-function testing convention — see Discovered Patterns.)

**Evidence:**

```python
def _node(number, state, merged):
    return [{"number": number, "state": state, "merged": merged,
             "reviewDecision": "APPROVED", "reviewThreads": {"nodes": []}}]
```

— `scripts/qrspi_cleanup_test.py:26-30`; in-memory state built at `:34-37`.
**Dependencies:** none beyond `qrspi_cleanup` + `qrspi_pr_state` imports.
**Implicit contracts:** The test harness convention is "test pure functions only; do not
touch git/gh/subprocess." Validating actual remote deletion would require breaking this
convention (a temp-repo/fake-remote fixture) or refactoring the deletion logic into a pure
testable seam.

## Q14: What does qrspi_cleanup.py emit when remote-ref deletion silently leaves refs behind, and is there any signal to detect the stranded-ref condition?

**Answer:** When `gt sync --force` exits zero but prunes nothing, the script emits
`ok: true`, `decision: "destroy"`, and `removed.remotes` = the **presence list** (claiming
those refs were deleted), exit code 0. There is **no logging** at all in the script (no
`logging`, no stderr diagnostics — only the single JSON envelope on stdout). There is NO
signal a maintainer or the Reconcile pass could use to detect stranded refs: the envelope
positively asserts deletion, and the batch log line prints that list as cleaned-up
remotes. The script never re-queries origin after `gt sync` to confirm the refs are gone,
so a stranded ref is indistinguishable from a deleted one in the output. The only thing
that surfaces a problem is a hard non-zero `gt sync` exit (Q10) — a partial/no-op success
is invisible.

**Evidence:**

```python
        if decision["decision"] == "destroy":
            removed["worktree"] = _remove_worktree(wt_path, dry_run)
            removed["branches"] = sorted(
                b for b in branches if _delete_local_branch(b, dry_run))
            removed["remotes"] = sorted(_prune_remote_refs(branches, dry_run))
        return _envelope(True, decision["decision"], decision["reason"],
                         removed, dry_run)
```

— `scripts/qrspi_cleanup.py:229-236`; batch log at `.claude/workflows/qrspi-batch.js:816-817`.
**Dependencies:** envelope (`_envelope` `:189`), batch consumer.
**Implicit contracts:** The envelope's `removed.remotes` is contractually a deletion claim
to its consumer, but is only ever a presence list. There is no post-deletion verification
ref-check (no second `git ls-remote`) anywhere in the pipeline.

---

## Discovered Patterns

- **Self-locating REPO_ROOT.** `qrspi_cleanup.py` derives `REPO_ROOT` from `__file__`
  (`:42-43`), mirroring `qrspi_resolve.py`/`qrspi_pr_state.py`. The caller never types a
  path. CONSEQUENCE: the script MUST run from the MAIN checkout, not a worktree — the batch
  prompt enforces this (`qrspi-batch.js:773-775, 784`); run from a worktree, `REPO_ROOT`
  would be the worktree and the target absent → skip.
- **Pure-classifier + impure-mechanics split.** A pure, unit-tested decision function
  (`classify_cleanup`) is paired with subprocess-backed mechanics that are NOT unit-tested
  (the `# --- subprocess-backed mechanics (not unit-tested)` header at `:91`). This is the
  repo-wide convention (`scripts/qrspi_*_test.py` test pure logic only).
- **Presence-bool as deletion proxy.** Every reap mechanic
  (`_remove_worktree`, `_delete_local_branch`, `_prune_remote_refs`) returns
  *pre-deletion presence* and uses it as the "removed" signal. For worktree/local-branch
  this is mostly harmless (the destructive command runs right after and raises on failure).
  For remotes it is broken: the destructive step (`gt sync`) is decoupled from the presence
  list and the list is returned regardless.
- **Single-JSON-envelope-on-stdout contract.** All one-shot scripts emit exactly one JSON
  object on stdout, exit 0/1, and surface infra errors once as `ok:false` (no logging).
  The JS callers parse text → JSON via `extractJsonObject`/`parseCleanupEnvelope`
  (`qrspi-batch.js:172-180`) rather than StructuredOutput.
- **Idempotency via absence-as-no-op.** Missing worktree (`_dirty_porcelain` `:119`,
  `_remove_worktree` `:134`), absent local branch (`_delete_local_branch` `:151-154`), and
  absent remote ref (`_prune_remote_refs` `:175`) are all clean no-ops, never errors.

## Inconsistencies

1. **Docstring/field name vs. behavior — `removed.remotes` claims deletion but reports
   presence.** The module docstring (`:29-31`) and `_prune_remote_refs` docstring
   (`:164-167`) describe pruning/deleting remote refs, and the field is named `remotes`
   under `removed`. But the value is computed purely from `git ls-remote` presence
   (`:175`) and returned unchanged regardless of whether `gt sync --force` actually pruned
   anything (`:184`). This is the core defect named by the ticket title.

2. **Order vs. `gt sync` prerequisite.** `_prune_remote_refs` relies on `gt sync --force`
   pruning "local branches whose PRs have merged and their remote refs" (`:178-179`), but
   it runs in step 3 *after* step 2 has already `git branch -D`-deleted those very local
   branches (`:231-232`). `gt sync` may therefore have no local branch to key off,
   pruning nothing while the presence list still reports success.

3. **Comment "faithful preview" overstated.** `:23, :212` claim the decision is computed
   identically with/without `--dry-run` so a dry run is a faithful preview. True for the
   *decision* and for *presence*, but the preview of `removed.remotes` is identical to a
   real run precisely because neither observes actual deletion — so it cannot preview
   deletion outcome, only presence.

4. **Idempotency claim references Q11/Q12 in code comments** (`:24-25`) but those Q-numbers
   refer to this script's OWN design notes, not the current questions.md numbering — a stale
   cross-reference. The worktree-only-branch case (current Q11) is NOT actually handled
   (it silently strands refs; see Q11 answer), despite the docstring asserting idempotent
   no-op coverage.

5. **Error surfacing asymmetry.** A `gt sync` non-zero exit is surfaced as `ok:false`
   (`:180-183`), but a `gt sync` zero-exit-pruned-nothing is reported as a successful
   deletion (`ok:true` + presence list). The failure path is robust; the silent-no-op
   path is the unguarded gap.
