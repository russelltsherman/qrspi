# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** draft

## Q1: How does `restack()` determine the stack tip, and what data does `pick_tip` consume to select the highest slice it checks out before running `gt restack --downstack`?

**Answer:** `restack()` does NOT compute the tip itself — `main()` computes it once via `pick_tip(existing_branches(args.ticket), args.ticket)` and passes it in (`scripts/qrspi_restack.py:207, 214`). `existing_branches()` runs `git branch --list "<ticket>/*"` in `REPO_ROOT` and normalizes the lines through `branch_set()` (strips the `* `/`+ `/`  ` markers) into a plain set of bare branch names (`scripts/qrspi_restack.py:136-139`). `pick_tip` (imported from `qrspi_resolve`, defined in `scripts/qrspi_resolve.py:144-159`) consumes that set: it extracts slice numbers via `slice_numbers()` and returns `<ticket>/slice-<max N>` if any slice exists, else `<ticket>/plan`, else `<ticket>/design`, else `None`. Inside `restack()` the tip is `gt checkout`ed and then `gt restack --downstack` runs from it (`scripts/qrspi_restack.py:169, 173`).

**Evidence:**

```python
def pick_tip(branches, ticket):
    snums = slice_numbers(branches)
    if snums:
        return "%s/slice-%d" % (ticket, max(snums))
    for phase in ("plan", "design"):
        name = "%s/%s" % (ticket, phase)
        if name in branches:
            return name
    return None
```

— `scripts/qrspi_resolve.py:144-159`

```python
tip = pick_tip(existing_branches(args.ticket), args.ticket)
```

— `scripts/qrspi_restack.py:207`

**Dependencies:** `qrspi_restack` → `qrspi_resolve.pick_tip` → `qrspi_pr_state.slice_numbers` / `branch_set`. `pick_tip`'s docstring explicitly notes existence is "plain (any branch), NOT the trunk-ahead 'real' gate the resolver uses" (`scripts/qrspi_resolve.py:149-151`).
**Implicit contracts:** `pick_tip` consumes ONLY branch *names* — it has no notion of merge status or tracked parent. A `<ticket>/slice-2` branch is selected as tip whether or not `slice-1` below it has merged. The highest-numbered slice is assumed to be the open frontier.

## Q2: What information about each branch's tracked parent and merge status is currently available to the restack script, and where does that data enter the script?

**Answer:** NONE. `qrspi_restack.py` imports exactly two symbols — `branch_set` and `pick_tip` (`scripts/qrspi_restack.py:57-58`) — and the only external data it gathers is `git branch --list "<ticket>/*"` (`scripts/qrspi_restack.py:138`). It makes NO `gh` calls and NO `gt`-metadata reads about tracked parents; it never imports `stack_merge_state`, `is_stack_fully_merged`, or `_query_pr`. The merge-classification machinery exists in `qrspi_pr_state.py` (`stack_merge_state` at `:207-246`, `is_stack_fully_merged` at `:249-256`) but is not wired into the restack path. The script therefore has zero awareness of which ancestors have landed; it operates purely on local branch names + `gt restack`'s own behavior.

**Evidence:**

```python
from qrspi_pr_state import branch_set  # noqa: E402
from qrspi_resolve import pick_tip      # noqa: E402
```

— `scripts/qrspi_restack.py:57-58`

```python
def existing_branches(ticket):
    rc, out, _ = _run(["git", "branch", "--list", "%s/*" % ticket], cwd=REPO_ROOT)
    return branch_set(out.splitlines()) if rc == 0 else set()
```

— `scripts/qrspi_restack.py:136-139`

**Dependencies:** Restack depends only on local git state + `gt`. The merge-status source (`stack_merge_state`, fed by the MERGED-aware GraphQL `select_pr(nodes, prefer="merged")`) lives a module away and is consumed only by the land/destroy path elsewhere — not by restack.
**Implicit contracts:** The script assumes `gt`'s own stack metadata (tracked parents) is correct and that `gt restack`/`gt submit` will do the right thing for a partially-landed stack. There is no guard for "the lowest open slice is parented on a merged branch."

## Q3: What is the exact set of `gt` subcommands and flags `qrspi_restack.py` invokes today, and which functions wrap each invocation?

**Answer:** Four `gt` invocations across three functions, all via the `_run()` subprocess wrapper (`scripts/qrspi_restack.py:130-133`):

1. `gt checkout <tip> --no-interactive` — in `restack()` (`:169`)
2. `gt restack --downstack --no-interactive` — in `restack()` (`:173`)
3. `gt abort --force --no-interactive` — in `restack()`, best-effort on conflict (`:178`)
4. `gt submit --publish --stack --force --no-edit --no-interactive` — in `submit_stack()` (`:149-151`)

Plus one git read in `existing_branches()`: `git branch --list "<ticket>/*"`.

**Evidence:**

```python
rc, out, err = _run(
    ["gt", "submit", "--publish", "--stack", "--force", "--no-edit", "--no-interactive"],
    cwd=worktree)
return classify_submit(rc, out, err)
```

— `scripts/qrspi_restack.py:149-152`

```python
rc, out, err = _run(["gt", "checkout", tip, "--no-interactive"], cwd=worktree)
...
rc, out, err = _run(["gt", "restack", "--downstack", "--no-interactive"], cwd=worktree)
...
_run(["gt", "abort", "--force", "--no-interactive"], cwd=worktree)
```

— `scripts/qrspi_restack.py:169, 173, 178`

**Dependencies:** All run in the ticket's worktree (`cwd=worktree`) except the branch list which runs in `REPO_ROOT`. `submit_stack()` is only reached when `restack()` reports a branch actually moved.
**Implicit contracts:** `--force` on submit is mandatory (the rebase makes the remote diverge). `--stack` covers the whole chain from the tip downward. `--publish`/`--no-edit`/`--no-interactive` keep PRs published and avoid editor/prompt blocking. The submit assumes every branch in the stack still has an open PR to push to.

## Q4: What signature and return contract does `classify_submit()` expose, and how is its `ok:false` result consumed by the caller?

**Answer:** `classify_submit(rc, stdout, stderr) -> (ok: bool, error: str|None)` (`scripts/qrspi_restack.py:96-107`). Pure. `rc == 0` → `(True, None)`. `rc != 0` → `(False, "restack succeeded but gt submit --stack failed: <detail>")` where `<detail>` is trimmed stderr, falling back to stdout, falling back to `"gt submit failed (rc=%d)"`. The caller is `submit_stack()` (`:152`), whose `(ok, error)` flows up to `restack()` (`:185-187`): if `submit_ok` is False, `restack()` returns `(False, restacked, False, submit_err)` — note `submitted=False` and NO `gt abort` (the comment at `:163-166` explains the tree is already clean after a successful restack, so the push failure surfaces as `ok:false` rather than triggering an abort).

**Evidence:**

```python
def classify_submit(rc, stdout, stderr):
    if rc == 0:
        return True, None
    detail = (stderr or "").strip() or (stdout or "").strip() or "gt submit failed (rc=%d)" % rc
    return False, "restack succeeded but gt submit --stack failed: %s" % detail
```

— `scripts/qrspi_restack.py:96-107`

```python
submit_ok, submit_err = submit_stack(worktree)
if not submit_ok:
    return False, restacked, False, submit_err
```

— `scripts/qrspi_restack.py:185-187`

**Dependencies:** Consumed by `submit_stack` → `restack` → `main` → the JSON envelope (`build_envelope`, `:110-125`) → qrspi-batch `parseRestackEnvelope`.
**Implicit contracts:** The `"restack succeeded but gt submit --stack failed:"` prefix is load-bearing for batch log readability — it tells the operator the local restack was fine but the push diverged. `ok:false` from any source (checkout, restack-conflict, or submit) is collapsed into the same envelope `error` field.

## Q5: How does the `qrspi-batch` workflow invoke `qrspi_restack.py`, and how does it map the script's output to the `restack_conflict` outcome that strands the ticket?

**Answer:** The main loop calls `ensureRestacked(t, 'Restack')` once per ticket, AFTER resolve and BEFORE dispatching the resolved action, for EVERY queued ticket regardless of decision (`.claude/workflows/qrspi-batch.js:976-982`). `ensureRestacked` spawns a worker agent instructed to run `python3 scripts/qrspi_restack.py --ticket <id>` verbatim and return the JSON envelope (`:412-432`). The envelope is parsed by `parseRestackEnvelope` (`:155-167`). If `rs.ok` is false, the loop logs `restack CONFLICT`, pushes `{ ticketId, action: 'restack_conflict', summary: rs.error }` to results, and `continue`s — skipping the ticket's resolved action for the run (`:978-982`). This is the stranding: the ticket never reaches its `advance`/`submit`/`land` handler.

**Evidence:**

```javascript
const rs = await ensureRestacked(t, 'Restack')
if (!rs.ok) {
  log(`  ${t.id}: restack CONFLICT — ${rs.error ?? 'unknown'} (surfaced; not advanced this run; tree left clean)`)
  results.push({ ticketId: t.id, action: 'restack_conflict', summary: rs.error ?? 'restack conflict' })
  continue
}
```

— `.claude/workflows/qrspi-batch.js:977-982`

**Dependencies:** Batch → `ensureRestacked` → worker agent → `qrspi_restack.py`; envelope back through `parseRestackEnvelope`. `parseRestackEnvelope` requires a boolean `ok` field or returns its own `ok:false` (`:163`).
**Implicit contracts:** ANY `ok:false` — restack conflict OR submit push failure — is reported under the single `restack_conflict` action label and strands the ticket for that run. The comment notes the drift gate intentionally runs even for `wait/revise/land/reset` tickets (`:969-975`), so a partially-landed stack that trips restack/submit is stranded before any action.

## Q6: Where does the script document or enforce the "never `gt sync` a held stack" rule, and what is recorded about why merged-ancestor pruning is currently absent?

**Answer:** The "never sync" rule is documented in the module docstring (`scripts/qrspi_restack.py:20-24`): "It restacks onto the LOCAL trunk only — it NEVER `gt sync`s (the SKILL forbids syncing a held stack mid-feature) and never rewrites trunk." It is ENFORCED only by omission — there is no `gt sync` call anywhere in the script, and the batch worker prompt explicitly forbids the worker from running `gt sync` itself (`.claude/workflows/qrspi-batch.js:425`). There is NO comment anywhere in `qrspi_restack.py` about merged-ancestor pruning, why it is absent, or the partial-land case. The docstring's failure narrative covers only trunk-divergence and restack *conflicts* (`:7-24`), not the merged-ancestor scenario. **NOT FOUND** — no header comment addresses merged-ancestor pruning (searched `qrspi_restack.py` for "merge", "land", "ancestor", "prune"; zero hits).

**Evidence:**

```python
# It restacks onto the
# LOCAL trunk only — it NEVER `gt sync`s (the SKILL forbids syncing a held stack
# mid-feature) and never rewrites trunk.
```

— `scripts/qrspi_restack.py:20-24` (docstring)

```
no other git/gt commands ... do NOT run gt restack/abort/sync yourself or improvise paths
```

— `.claude/workflows/qrspi-batch.js:415-425` (worker prompt)

**Dependencies:** None — this is a documentation/policy concern.
**Implicit contracts:** The codebase assumes `gt restack --downstack` onto local trunk is always safe and never needs to drop a landed ancestor from the stack. There is no recorded acknowledgement that a merged ancestor could break the restack/submit.

## Q7: How does the resolver (`qrspi_resolve_state.py`) detect a "design branch" and decide entry state, such that a partially-landed stack causes it to misreport `entry_blocked "No design branch"`?

**Answer:** `qrspi_resolve_state.resolve()` itself is pure — it reads `phase_exists(phases, "design")`, which returns `bool(phases["design"]["branchExists"])` (`scripts/qrspi_resolve_state.py:78-81, 134`). If `design` is absent from `existing`, it falls to the entry gate and returns `entry_blocked`/`run_design` (`:134-148`). The misreport originates UPSTREAM in `qrspi_pr_state.build_state()`: `branchExists` is set to `head in real` where `real = real_branches(branches, ahead)` (`scripts/qrspi_pr_state.py:390-398`). `real_branches` keeps a branch only if it is `>= 1 commit ahead of trunk` (`:301-318`), computed by `_commits_ahead(branch, "main")` = `git rev-list --count main..<branch>` (`:329-339`).

**Root cause of the partial-land misreport:** Once `slice-1` (or any ancestor) merges into `main`, the design branch's commits become reachable from trunk, so `git rev-list --count main..<id>/design` returns 0. `real_branches` then drops `<id>/design`, `branchExists` becomes False, `phase_exists` returns False, and the resolver — seeing no design branch — falls into the entry gate and emits `entry_blocked "No design branch..."` even though the branch still physically exists. The gate is described as designed to catch only the *empty fresh* design branch (`:305-317`), but it also fires for a *landed-ancestor* design branch.

**Evidence:**

```python
def real_branches(branches, ahead_counts):
    """The branches that both exist AND carry real work — at least one commit ahead
    of trunk.
    ...
    NOTE: the gate is trunk-relative, so it
    reliably catches an empty *design* branch (whose parent IS trunk)..."""
    return {b for b in branches if ahead_counts.get(b, 0) > 0}
```

— `scripts/qrspi_pr_state.py:301-318`

```python
ahead = {b: _commits_ahead(b, trunk) for b in branches}
real = real_branches(branches, ahead)
def phase_pr(name):
    head = "%s/%s" % (ticket, name)
    exists = head in real
```

— `scripts/qrspi_pr_state.py:390-398`

**Dependencies:** `resolve()` ← `build_state()` ← `real_branches` ← `_commits_ahead` (git). The bug is a trunk-relative ahead-count gate that conflates "empty placeholder" with "ancestor already landed."
**Implicit contracts:** `branchExists` is defined as "branch is >=1 commit ahead of trunk," NOT "branch exists in git." This conflation is the documented gotcha in MEMORY.md ("Resolver: partially-landed stack bug"). The pr_state regression docstring explicitly anticipated only the empty-design case, not landed ancestors.

## Q8: What does the script do when `gt restack` reports that no branch moved versus when a branch moved — does the submit path run only conditionally, and what triggers it?

**Answer:** The submit path is strictly conditional on `restacked == True`. `classify_result(rc, stdout, stderr)` (`scripts/qrspi_restack.py:75-93`) computes `restacked`: on `rc == 0`, `restacked` is True iff any output line does NOT contain the no-op phrase `"does not need to be restacked"` (`_NOOP_PHRASE`, `:64`); empty output or all-no-op lines → `restacked=False`. In `restack()`: if `not restacked`, it returns early `(ok, False, False, None)` and the push is SKIPPED entirely (`:181-183`). Only when `restacked` is True does it call `submit_stack()` (`:185`). So "nothing moved" → no push (remote assumed already aligned); "moved" → force-push the stack.

**Evidence:**

```python
# Nothing moved -> remote already matches local; skip the push entirely.
if not restacked:
    return ok, restacked, False, None

submit_ok, submit_err = submit_stack(worktree)
```

— `scripts/qrspi_restack.py:181-185`

```python
restacked = any(_NOOP_PHRASE not in ln for ln in lines) if lines else False
return True, restacked, None
```

— `scripts/qrspi_restack.py:90-91`

**Dependencies:** `restack` ← `classify_result` (parsing gt stdout). The trigger is purely the presence/absence of non-no-op output lines.
**Implicit contracts:** `restacked` is a string-parse of `gt`'s human output — it relies on `gt` printing exactly the `"<branch> does not need to be restacked on <trunk>."` phrase for no-ops (`:60-64`). A `gt` phrasing change would silently break the no-op detection. `restacked` never influences ok/not-ok — only whether to push.

## Q9: How does the script behave when the lowest open slice's tracked parent is a merged branch — is there any branch/module in the codebase that classifies a branch as merged-into-trunk?

**Answer:** `qrspi_restack.py` has NO handling for this — it has no merge awareness (see Q2). It will `gt checkout` the highest slice as tip and run `gt restack --downstack`, delegating entirely to `gt`'s behavior when an ancestor has landed; whatever `gt` does (rebase against a merged parent, or error) is what the script reports. There is NO code in the restack path that detects "parent is merged."

A merged-into-trunk classifier DOES exist elsewhere: `qrspi_pr_state.stack_merge_state(branches, graphql_nodes)` (`scripts/qrspi_pr_state.py:207-246`) maps each branch to `{merged, prNumber, state, mergedByPr}` using `select_pr(nodes, prefer="merged")` ("any fetched MERGED node wins, order-independent", `:140-166, 238-244`), and `is_stack_fully_merged(merge_state)` (`:249-256`) is the all-or-nothing predicate. But these are GraphQL-PR-merged classifiers, NOT trunk-reachability classifiers, and they are NOT consumed by `qrspi_restack.py`, `qrspi_resolve_state.py`, or `qrspi-batch.js` (verified: zero references). The closest trunk-relative signal is `_commits_ahead`/`real_branches` (`:301-339`), which indirectly treats a landed branch as "not real" (0 commits ahead) — the Q7 bug.

**Evidence:**

```python
node = select_pr(nodes, prefer="merged")
merged = bool(node.get("merged"))
out[b] = {"merged": merged, "prNumber": node.get("number"),
          "state": node.get("state"),
          "mergedByPr": node.get("number") if merged else None}
```

— `scripts/qrspi_pr_state.py:238-244`

**Dependencies:** `stack_merge_state`/`is_stack_fully_merged` are defined and unit-tested in `qrspi_pr_state.py` but currently have no production consumer in the three files this ticket touches. `real_branches`/`_commits_ahead` provide the only trunk-reachability signal in use.
**Implicit contracts:** Two SEPARATE notions of "merged" exist: (a) PR `merged: True` via GraphQL (`stack_merge_state`), and (b) "0 commits ahead of local trunk" (`real_branches`). The restack script uses neither; the resolver gather uses (b). They can disagree (a PR can be MERGED while a worktree's local trunk hasn't advanced yet, or vice-versa).

## Q10: What happens when ALL slices have merged (fully landed) versus when none have merged — how does the restack/submit path distinguish these from the partial-land case?

**Answer:** `qrspi_restack.py` does NOT distinguish any of these cases — it has no merge data (Q2/Q9). It always: picks the highest-numbered slice as tip, checks it out, runs `gt restack --downstack`, and pushes only if something moved. The fully-landed / none-landed / partial-land distinction is invisible to the restack script. The distinction IS available via `is_stack_fully_merged` in `qrspi_pr_state.py` (`:249-256`: True only when every branch's PR is `merged`; empty stack → False; any unmerged → False), but that predicate is not called from the restack/submit path. If all slices have merged, `pick_tip` still returns the highest slice name (branch names persist until deleted) and the restack would run against a fully-landed stack with no merge-aware short-circuit.

**Evidence:**

```python
def is_stack_fully_merged(merge_state):
    if not merge_state:
        return False
    return all(entry.get("merged") for entry in merge_state.values())
```

— `scripts/qrspi_pr_state.py:249-256`

```python
def pick_tip(branches, ticket):
    snums = slice_numbers(branches)
    if snums:
        return "%s/slice-%d" % (ticket, max(snums))
```

— `scripts/qrspi_resolve.py:144-154`

**Dependencies:** The fully/none/partial distinction would require feeding `stack_merge_state` output into the restack path; currently no such wiring exists.
**Implicit contracts:** The restack path treats every stack identically by branch name. The "any MERGED node wins" semantics of `select_pr(prefer="merged")` only matter to consumers of `stack_merge_state` — and the restack/submit path is not one of them.

## Q11: What pure-logic units in `qrspi_restack.py` are already covered by its `_test.py` sibling, and how do those tests stub or fake the `gt`/`gh` calls?

**Answer:** `scripts/qrspi_restack_test.py` covers four pure helpers: `worktree_path` (`:38-39`), `classify_result` (9 cases, `:42-68` — rc=0 restack output, real-gt no-op phrasing, multiline all-no-op, mixed moved/no-op, empty output, rc!=0 conflict/stdout-fallback/synthesized/whitespace-trim), `classify_submit` (5 cases, `:71-83` — rc=0, rc=0 no output, rc!=0 prefixed stderr, stdout fallback, synthesized), and `build_envelope` (ok/no-op/err envelopes, `:86-106`). It also re-tests `pick_tip` (`:108-117`). The subprocess-backed parts are NOT stubbed/faked — they are intentionally EXCLUDED: the test docstring states "The subprocess-backed parts (gt checkout/restack/abort, git branch) are intentionally NOT tested here... verified by a manual end-to-end run" (`:5-9`). The tests pass `(rc, stdout, stderr)` tuples directly to the pure classifiers — no subprocess mocking, because the impure boundary (`_run`, `restack`, `submit_stack`, `existing_branches`) is never invoked.

**Evidence:**

```python
check("rc=0 mixed (one moved, one no-op) -> ok, restacked",
      classify_result(0,
                      "RUS-1/design does not need to be restacked on main.\n"
                      "Restacking RUS-1/plan on RUS-1/design.", ""),
      (True, True, None))
```

— `scripts/qrspi_restack_test.py:52-56`

```python
The subprocess-backed parts (gt checkout/restack/abort, git branch) are intentionally
NOT tested here — same convention as qrspi_resolve_test.py / qrspi_persist_test.py — and
are verified by a manual end-to-end run against a deliberately-stale branch.
```

— `scripts/qrspi_restack_test.py:6-8`

**Dependencies:** Tests import `worktree_path, classify_result, classify_submit, build_envelope, REPO_ROOT` from `qrspi_restack` and `pick_tip` from `qrspi_resolve` (`:14-21`). Stdlib-only, assert-based via a `check()` helper (`:27-34`).
**Implicit contracts:** The test convention is to make impure functions thin shells over pure classifiers, then test only the classifiers by passing synthetic `(rc, out, err)`. No fakes/mocks for `gt`/`gh` exist anywhere in this suite — any new merge-aware behavior would need its decision logic factored into a pure helper to be testable under this convention.

## Q12: What test fixtures or helpers exist in the resolver test for representing a partially-landed stack (merged ancestors + open slices)?

**Answer:** `scripts/qrspi_resolve_state_test.py` has NO fixture for a partially-landed stack. Its helpers — `_phase`, `_impl`, `_slice`, `_ct`, `state` (`:14-45`) — model only `branchExists`/`prExists`/`reviewDecision`/`unresolvedThreads`/`commentTargets`/`expectedSlices`/`prSummaryCommitted`. There is NO `merged` field, no merged-ancestor concept, and no test where a design/plan branch is "gone from trunk" — because the resolver operates on the already-computed `branchExists` boolean and never sees commit-ahead counts. The partial-land *bug* lives upstream in `qrspi_pr_state.real_branches`/`_commits_ahead`, and `scripts/qrspi_pr_state_test.py` is where the merge fixtures live: `stack_merge_state` Case 2 "partially-merged" (`:225-231`: slice-1 MERGED, slice-2 OPEN → `is_stack_fully_merged` False) and the `real_branches` regression cases (`:158-173`). However, `qrspi_pr_state_test.py`'s `real_branches` tests cover only the *empty-placeholder* (0 ahead) case — there is NO test asserting behavior when a *populated* branch reads 0-ahead because its commits landed in trunk. **NOT FOUND** in the resolver test; the relevant fixtures are in the pr_state test, and a *landed-ancestor design branch* fixture is absent from both.

**Evidence:**

```python
def _phase(branch=True, pr=True, decision="REVIEW_REQUIRED", threads=0, comments=None):
    return {"branchExists": branch, "prExists": pr, ...}
```

— `scripts/qrspi_resolve_state_test.py:14-17` (no merged/ancestor field)

```python
_partial = stack_merge_state(
    ["RUS-1/slice-1", "RUS-1/slice-2"],
    {"RUS-1/slice-1": _node(10, "MERGED", True),
     "RUS-1/slice-2": _node(11, "OPEN", False)})
check("partially-merged: predicate False", is_stack_fully_merged(_partial), False)
```

— `scripts/qrspi_pr_state_test.py:225-231`

**Dependencies:** Resolver tests depend on synthetic `branchExists` booleans, so they cannot reproduce the trunk-reachability bug (it never reaches the resolver as a flag). The merge fixtures (`_node`, `_nodes`, `stack_merge_state` cases) are in `qrspi_pr_state_test.py:206-283`.
**Implicit contracts:** The resolver test convention hand-builds `branchExists`, deliberately decoupling resolver tests from gather logic. Any fix that changes how a landed-ancestor branch is classified must be tested in `qrspi_pr_state_test.py` (where git-relative `real_branches`/`_commits_ahead` semantics are modeled), not the resolver test.

## Q13: How does `qrspi_restack.py` surface the abort to the batch — what fields does it emit, and where is the verbatim `gt` WARNING/ERROR output captured or logged?

**Answer:** It emits a single JSON envelope on stdout via `build_envelope()` (`scripts/qrspi_restack.py:110-125, 215-218`): `{ ok, repoRoot, ticket, worktreeDir, tip, restacked, submitted, error? }`. On a restack conflict, `restack()` runs `gt abort --force --no-interactive` (best-effort) then returns `error` = the verbatim trimmed `gt` stderr (falling back to stdout) from `classify_result` (`:92, 174-179`). The abort itself is NOT classified — its rc/output is discarded so its own failure can't mask the original conflict message (`:177-179`). On a submit push failure, `error` is the `classify_submit` prefixed string and `submitted=False` (no abort, `:185-187`). `main()` returns exit code `0 if ok else 1` (`:219`). The batch reads only the JSON (via `parseRestackEnvelope`, `.claude/workflows/qrspi-batch.js:155-167`) and logs `rs.error` to the run log + `summary` field (`:429, 980`). The verbatim `gt` WARNING/ERROR text is captured by `_run`'s `capture_output=True` (`:130-133`) and propagated ONLY through the `error` string — there is no separate logging/persisting of the raw `gt` transcript.

**Evidence:**

```python
ok, restacked, error = classify_result(rc, out, err)
if not ok:
    _run(["gt", "abort", "--force", "--no-interactive"], cwd=worktree)
    return ok, restacked, False, error
```

— `scripts/qrspi_restack.py:174-179`

```python
def _run(cmd, cwd=None):
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return res.returncode, res.stdout, res.stderr
```

— `scripts/qrspi_restack.py:130-133`

**Dependencies:** Envelope → stdout → batch worker → `parseRestackEnvelope` → `results.push({action:'restack_conflict', summary: rs.error})` (`.claude/workflows/qrspi-batch.js:980`).
**Implicit contracts:** The ONLY channel for the verbatim `gt` message is the envelope `error` string — there is no debug log file, no stderr passthrough. A conflict and a push failure are indistinguishable to the batch except by the `error` text (the submit failure carries the `"restack succeeded but gt submit --stack failed:"` prefix). `restacked`/`submitted` booleans are the only structured observability of what the operation actually did.

---

## Discovered Patterns

- **Pure-core / impure-shell split (testability convention):** Every QRSPI script splits a unit-tested pure decision layer from an untested subprocess shell. `qrspi_restack.py` factors `classify_result`/`classify_submit`/`build_envelope`/`worktree_path` (pure, tested) away from `_run`/`restack`/`submit_stack`/`existing_branches` (impure, "manual e2e"). Same pattern in `qrspi_resolve_state.py` (pure `resolve()`) vs `qrspi_pr_state.py` (impure `build_state`). Any new merge-aware logic must be a pure helper to fit the test convention.
- **Self-locating scripts:** `qrspi_restack.py` derives `REPO_ROOT` from `__file__` (`:50-54`), explicitly to remove "the path a weak worker model keeps corrupting" — matching `qrspi_resolve.py`/`qrspi_persist.py`.
- **Two distinct definitions of "merged"/"landed":** (a) GraphQL PR `merged: True` via `stack_merge_state`/`select_pr(prefer="merged")` in `qrspi_pr_state.py`; (b) "0 commits ahead of local trunk" via `real_branches`/`_commits_ahead`. The restack path uses neither; the resolver gather uses only (b). They are not reconciled anywhere.
- **String-parsing `gt` human output:** `restacked` is decided by substring-matching `gt`'s `"does not need to be restacked"` phrase (`:60-64, 90`) — a fragile coupling to `gt`'s display text, not an exit code.
- **`branchExists` ≠ "branch exists in git":** Across the gather, a phase "exists" only if its branch is >=1 commit ahead of trunk (`real_branches`). This trunk-relative definition is the shared root of the entry-gate misreport.
- **JSON-envelope-over-stdout contract between Python scripts and the JS workflow:** every script (`restack`, `resolve`, `pr_body`, etc.) returns one JSON object the batch parses with a dedicated `parse*Envelope` validator requiring a boolean `ok`.

## Inconsistencies

- **`real_branches` docstring vs. actual coverage (the Q7 bug):** The docstring (`qrspi_pr_state.py:305-317`) claims the trunk-relative gate "reliably catches an empty *design* branch (whose parent IS trunk)" and frames the gate as solving only the empty-placeholder regression. In fact the SAME 0-ahead condition fires for a *populated* design branch whose commits have landed in trunk via a merged slice — producing the documented "partially-landed stack" misreport (`entry_blocked "No design branch"`). The comment does not acknowledge this second trigger. Confirmed in MEMORY.md ("Resolver: partially-landed stack bug").
- **Merge-classification machinery exists but is unused by the affected paths:** `stack_merge_state` / `is_stack_fully_merged` (`qrspi_pr_state.py:207-256`) are fully implemented and unit-tested (`qrspi_pr_state_test.py:205-283`) but have NO consumer in `qrspi_restack.py`, `qrspi_resolve_state.py`, or `qrspi-batch.js`. The restack/submit path that strands partially-landed stacks is blind to the very classifier that could detect a landed ancestor.
- **Restack docstring narrates only conflict/divergence, never partial-land:** The `qrspi_restack.py` module docstring (`:1-42`) treats `gt restack` conflicts and trunk-divergence as the failure classes, and asserts `gt restack` is "idempotent: an already-aligned stack is a no-op." It is silent on what happens when an ancestor in the stack has merged into trunk — the scenario these questions target.
- **Two "merged" notions can disagree:** A slice PR can be GraphQL-`merged: True` while a particular worktree's *local* `main` has not yet advanced to contain it (or vice-versa). `stack_merge_state` would say merged; `real_branches`/`_commits_ahead` (which compares to the local trunk ref) could say still-ahead. Nothing reconciles the two views.
