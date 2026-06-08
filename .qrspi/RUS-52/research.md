# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-07T00:00:00Z
**Generated:** 2026-06-07T00:00:00Z
**Status:** draft

## Q1: How does the land step currently determine that a ticket's stack is complete, and where does the prose cleanup instruction to the worker live within it?

**Answer:** Stack completeness is NOT determined inside the land step — it is decided
upstream by the pure resolver `qrspi_resolve_state.resolve()`, which returns
`action == "land"` only when design + plan are approved/clean AND every slice PR is
`reviewDecision == "APPROVED"` with `unresolvedThreads == 0`. The batch's `doLand(t, r)`
is reached only via `case 'land':` in the dispatch switch. The cleanup instruction is
PROSE embedded in a single `agent(...)` prompt string (the LAND worker), which delegates
to the `action: land` steps of `qrspi-work/SKILL.md`. There is no dedicated land/cleanup
Python script — cleanup is entirely a natural-language instruction to a worker agent.

**Evidence:**

```js
async function doLand(t, r) {
  phase('Finalize')
  const fin = await agent(
    `You are the LAND worker for ${t.id}, in ${r.worktreeDir}. Every PR in the stack is approved+clean. Follow the "action: land" steps of ${SKILL}: ensure the stack is current (gt submit --publish --stack), merge bottom-up (gt merge --confirm), gt sync, remove leftover .qrspi/${t.id}/ artifacts (cleanup PR if needed), remove the worktree, and BEST-EFFORT project Linear → "Done". Treat any infrastructure/merge error as a HARD STOP (return ok:false, verbatim error).
Return: ok, prUrl, newStatus, summary.`,
    { label: `land:${t.id}`, phase: 'Finalize', schema: WORKER_SCHEMA }
  )
  return finResult(t, fin, 'land')
}
```

— `.claude/workflows/qrspi-batch.js:563-571`
The land predicate that gates this:

```python
    if any(s.get("reviewDecision") != "APPROVED" for s in slices):
        return decision("wait", phase="implementation", ...)
    return decision("land", phase="implementation",
                    reason="All phases approved and clean; land the whole stack bottom-up.")
```

— `scripts/qrspi_resolve_state.py:133-137`
The cleanup prose the worker follows (`gt merge`, `gt sync --force`, `git worktree remove --force`, `git worktree prune`) lives at — `.claude/skills/qrspi-work/SKILL.md:373-397`

**Dependencies:** `doLand` ← dispatch switch (`qrspi-batch.js:665`) ← `r.decision.action`
from `parseResolveEnvelope` ← `qrspi_resolve.py` ← `qrspi_resolve_state.resolve`. The
worker prompt references `SKILL` constant (`.claude/skills/qrspi-work/SKILL.md`).
**Implicit contracts:** The land worker must return `{ ok, prUrl, newStatus, summary }`
(WORKER_SCHEMA). Any merge/infra error is a HARD STOP returning `ok:false`. Cleanup is
"best-effort" prose, not deterministic/idempotent code — this is the gap a cleanup script
would close.

## Q2: How does `scripts/qrspi_pr_state.py` enumerate the PRs that belong to a single ticket's stack, and what fields does it report for each PR's merge state?

**Answer:** It enumerates branches via `git branch --list "<ticket>/*"`, normalizes them
with `branch_set()`, extracts slice numbers with `slice_numbers()` (regex `/slice-(\d+)$`),
then gates each branch through `real_branches()` (must be ≥1 commit ahead of trunk). For
each real branch it runs a GitHub GraphQL query (`PR_QUERY`) keyed on `headRefName` with
`states:OPEN`. CRITICAL: the query filters to `states:OPEN` only — it has NO visibility
into MERGED or CLOSED PRs. Per PR it reports `prExists`, `number`, `reviewDecision`,
`unresolvedThreads` (plus `branchExists`, and `n` for slices). There is NO `merged`/`state`
field — merge state is not modeled at all (the lifecycle never merges until land).

**Evidence:**

```python
PR_QUERY = """
query($owner:String!, $repo:String!, $head:String!) {
  repository(owner:$owner, name:$repo) {
    pullRequests(headRefName:$head, first:5, states:OPEN, orderBy:{field:CREATED_AT, direction:DESC}) {
      nodes { number reviewDecision reviewThreads(first:100) { nodes { isResolved } } }
    }
  }
}
"""
```

— `scripts/qrspi_pr_state.py:26-38`

```python
def parse_pr_nodes(nodes):
    if not nodes:
        return {"prExists": False, "number": None,
                "reviewDecision": None, "unresolvedThreads": 0}
    node = nodes[0]
    threads = (node.get("reviewThreads") or {}).get("nodes", [])
    return {"prExists": True, "number": node.get("number"),
            "reviewDecision": node.get("reviewDecision"),
            "unresolvedThreads": unresolved_thread_count(threads)}
```

— `scripts/qrspi_pr_state.py:49-65`. State assembly (design/plan/implementation slices) —
`scripts/qrspi_pr_state.py:147-183`.

**Dependencies:** shells out to `git branch --list`, `git rev-list --count`, and
`gh api graphql`. Pure parsers (`unresolved_thread_count`, `parse_pr_nodes`,
`slice_numbers`, `branch_set`, `real_branches`) are unit-tested; subprocess wrappers are not.
**Implicit contracts:** A "phase" exists only if its branch is ≥1 commit ahead of trunk
(`real_branches`, line 94-111) — empty placeholder branches are excluded. `reviewDecision`
null normalizes to `None` (awaiting review). **There is no merged-state field**, so any
cleanup logic that needs "is this PR merged?" must add a new GraphQL state (e.g.
`states:MERGED` or a `merged`/`state`/`mergedAt` field) — it does not exist today.

## Q3: How are a ticket's worktree path and its stack branch names derived from the ticket ID elsewhere in the harness?

**Answer:** Worktree path: `<repo>/.worktrees/<ticket>` — computed in two places:
`qrspi_resolve.setup_worktree` (`os.path.join(REPO_ROOT, ".worktrees", ticket)`) and
`qrspi_restack.worktree_path(repo_root, ticket)`. In JS, `r.worktreeDir` is consumed (not
re-derived) and validated to end with `/.worktrees/${ticketId}`. Branch names are string
templates: `<ticket>/design`, `<ticket>/plan`, `<ticket>/slice-<n>`. Slice numbers are
parsed back out via the regex `/slice-(\d+)\s*$`. `pick_tip()` selects the highest phase
branch (slice-N > plan > design) to reuse a worktree.

**Evidence:**

```python
def worktree_path(repo_root, ticket):
    return os.path.join(repo_root, ".worktrees", ticket)
```

— `scripts/qrspi_restack.py:69-72`

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

— `scripts/qrspi_resolve.py:144-159`. Branch-name templates in `qrspi_pr_state.py:159`
(`"%s/%s" % (ticket, name)`), `:166` (`"%s/slice-%d"`). JS branch-name literals:
`.claude/workflows/qrspi-batch.js:489` (`${t.id}/slice-${s.n}`), `:550` (`${t.id}/${d.resetToPhase}`).
worktreeDir validation — `.claude/workflows/qrspi-batch.js:123`.

**Dependencies:** `qrspi_restack.py` imports `pick_tip` from `qrspi_resolve`; both import
`branch_set`/`slice_numbers` from `qrspi_pr_state`. REPO_ROOT is self-located from `__file__`.
**Implicit contracts:** Branch namespace is flat `<ticket>/<phase>`. Slice branches MUST
match `/slice-<int>$`. The worktree dir is always exactly `<repo>/.worktrees/<ticket>`. A
cleanup script can reuse `worktree_path`, `pick_tip`, `slice_numbers`, `branch_set` directly.

## Q4: What is the established invocation contract shared by `qrspi_resolve.py`, `qrspi_persist.py`, and the restack script that a new cleanup script must match?

**Answer:** All three self-locating scripts follow an identical pattern:
(1) derive `REPO_ROOT` from `__file__` (two levels up: `os.path.dirname(os.path.dirname(os.path.abspath(__file__)))`),
never from cwd or an argument; (2) `argparse` with `--ticket` required plus a few short
token-free flags; (3) emit a SINGLE JSON envelope on stdout via `json.dump(env, sys.stdout, indent=2)` then `print()`;
(4) every envelope has `ok: bool`, `repoRoot`, and an `error?` key present only on failure;
(5) `return 0 if ok else 1` from `main()`, wired via `sys.exit(main())`;
(6) ALL infrastructure errors caught and reported ONCE as `ok:false` with a verbatim
message — NEVER retried (so a weak worker model cannot thrash).

**Evidence:**

```python
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(_SCRIPT_DIR)
```

— identical in `scripts/qrspi_resolve.py:40-41`, `scripts/qrspi_persist.py:40-41`,
`scripts/qrspi_restack.py:53-54`.

```python
    json.dump(env, sys.stdout, indent=2)
    print()
    return 0 if env["ok"] else 1
```

— `scripts/qrspi_resolve.py:345-347` (mirrored at `qrspi_persist.py:112-114`,
`qrspi_restack.py:217-219`). The one-shot error envelope idiom —
`scripts/qrspi_resolve.py:338-343`.

**Dependencies:** envelopes are parsed JS-side by `extractJsonObject` + bespoke
`parse*Envelope` validators (`qrspi-batch.js:92-140`), NOT via StructuredOutput (the weak
worker stalled on that — see comment `qrspi-batch.js:76-86`).
**Implicit contracts:** A new cleanup script MUST: self-locate REPO_ROOT from `__file__`;
take `--ticket` (+ optional flags like `--dry-run`); print exactly one stdout JSON envelope
with `ok`/`repoRoot`/`error?`; exit 0/1; and report any failure once as `ok:false` without
retrying. The JS caller will wrap it in a worker-agent prompt that says "run EXACTLY this
one command verbatim ... output the JSON as your FINAL message ... HARD STOP on ok:false."

## Q5: What Graphite commands does the harness already shell out to for remote-affecting operations, and which one performs remote ref pruning?

**Answer:** Graphite commands used (all with `--no-interactive`):
`gt track --parent <trunk>` (resolve worktree setup), `gt restack --downstack` (restack),
`gt abort --force` (conflict recovery), `gt checkout <tip>`, `gt submit --publish --stack --force --no-edit`
(force-push realigned stack / restack push), `gt create` / `gt modify` (commits),
`gt delete <branch> --force --close` (reset discard), `gt merge --confirm` (land), and
`gt sync --force` (land cleanup). **Remote/branch pruning is done by `gt sync --force`** —
it deletes merged branches and prunes. There is NO standalone Python invocation of
`gt sync`/pruning today; it lives only in SKILL prose and the land worker prompt.

**Evidence:**

```python
    rc, out, err = _run(
        ["gt", "submit", "--publish", "--stack", "--force", "--no-edit", "--no-interactive"],
        cwd=worktree)
```

— `scripts/qrspi_restack.py:149-151` (the only Python that runs a remote-affecting `gt`).
`gt restack --downstack` — `scripts/qrspi_restack.py:173`. `gt abort --force` — `:178`.
`gt track --parent` — `scripts/qrspi_resolve.py:298`. The prune command (SKILL prose):

```bash
   gt sync --force --no-interactive       # deletes merged branches, prunes
```

— `.claude/skills/qrspi-work/SKILL.md:388`; also `git worktree prune` at SKILL `:395`, `:576`.
Land worker prompt references `gt sync` — `.claude/workflows/qrspi-batch.js:566`.

**Dependencies:** `gt` is invoked via `subprocess.run` with `cwd=worktree`. Only
`qrspi_restack.py` runs remote-affecting `gt` from Python; everything else (merge, sync,
delete, prune) is worker-agent prose.
**Implicit contracts:** Never `gt sync` a held stack mid-feature — only during `land`
cleanup (`SKILL.md:511-512`). `--force` is reserved for the realigned-stack push and the
resubmit-recovery path; "never use `--force` on the normal submit path" (`SKILL.md:542`).
`git worktree prune` reconciles the worktree registry after a `git worktree remove`.

## Q6: How do the existing scripts expose a preview/dry-run mode or report intended actions without performing them?

**Answer:** NOT FOUND — no existing script exposes a `--dry-run` / `--preview` / `--check`
flag. Searched `scripts/` for `dry-run`, `dry_run`, `--check`, `preview`, `--no-op` — zero
matches. The closest existing "decide-without-acting" pattern is the resolver SEPARATION:
`qrspi_resolve_state.resolve()` is a PURE decision function that performs NO I/O (it returns
the action the caller should take), and `qrspi_resolve.py` deliberately decides FIRST
(read-only `build_state`) and only THEN provisions a worktree as the decision requires —
so an `entry_blocked` ticket "never leaves a stray branch behind." That pure-decide /
then-act split is the idiom a cleanup `--dry-run` should follow.

**Evidence:**

```python
        # Decide first (read-only: build_state reads shared git refs + gh, no worktree
        # needed), THEN provision the worktree only as the decision requires — so an
        # entry_blocked ticket never leaves a stray branch behind.
        owner, repo = parse_name_with_owner(_gh_name_with_owner())
        state = build_state(...)
        decision = resolve(state)
        worktree = setup_worktree(args.ticket, ..., create_design=(decision["action"] == "run_design"))
```

— `scripts/qrspi_resolve.py:324-332`. Pure no-I/O decision contract —
`scripts/qrspi_resolve_state.py:8-11, 68-69`.

**Dependencies:** none — this is an absence.
**Implicit contracts:** The codebase favors a pure decision layer (returns intent) cleanly
separated from a thin subprocess execution layer. A cleanup script's `--dry-run` would
naturally compute the destroy/skip/blocked decision purely (unit-testable) and gate the
actual `git worktree remove` / `gt sync` behind the flag.

## Q7: What is treated as the authoritative source of PR merge state in the resolver, and how is "merged" distinguished from "in-review" and "closed-unmerged"?

**Answer:** The authoritative inputs are `reviewDecision` and `unresolvedThreads` from
GitHub GraphQL (NOT Linear status, NOT a merged flag). The resolver classifies on
`reviewDecision`: `"APPROVED"` + 0 threads ⇒ ready (advance/land); `"CHANGES_REQUESTED"` ⇒
reset/revise; anything else (e.g. `null`/`REVIEW_REQUIRED`) ⇒ wait. CRITICAL FINDING:
the resolver and `qrspi_pr_state.py` query `states:OPEN` only, so MERGED and
CLOSED-UNMERGED PRs are INVISIBLE — there is no code path that distinguishes "merged" from
"closed-unmerged." A merged phase PR simply disappears from the OPEN query, making its
branch read as PR-missing. The lifecycle never merges until the final `land`, so the
current design assumes PRs stay OPEN throughout review; post-merge state is unmodeled.

**Evidence:**

```python
def _pr_ready(pr):
    return pr.get("reviewDecision") == "APPROVED" and pr.get("unresolvedThreads", 0) == 0

def _pr_changes_requested(pr):
    return pr.get("reviewDecision") == "CHANGES_REQUESTED"
```

— `scripts/qrspi_resolve_state.py:48-53`. OPEN-only query (no merged state) —
`scripts/qrspi_pr_state.py:29` (`states:OPEN`). reviewDecision-null normalized to "awaiting
review" — `scripts/qrspi_pr_state.py:53-54`.

**Dependencies:** `resolve(state)` consumes the dict from `build_state`. PR-gated design
authority: `docs/qrspi-pr-gated-lifecycle-design.md` (referenced `qrspi_resolve_state.py:6`).
**Implicit contracts:** "PR review state — not Linear status — is the authority"
(`.claude/CLAUDE.md`). Merge detection for a cleanup pass would require NEW queries — the
current state model has booleans for branchExists/prExists/reviewDecision/unresolvedThreads
but **no `merged`/`mergedAt`/`state` field** for any PR.

## Q8: How does the harness currently track which git worktrees and branches exist for in-flight tickets versus finished ones?

**Answer:** There is NO persistent registry/manifest of in-flight vs finished tickets.
"In-flight" is recomputed live each run from two sources: (1) git itself —
`git branch --list "<ticket>/*"` enumerates branches, `os.path.isdir(worktree)` checks
worktree presence, and `git rev-list --count trunk..branch` decides if a branch is "real";
(2) Linear status (the batch QUERY phase lists tickets in `Selected`/`*Review` statuses via
`mcp__linear__list_issues`). A ticket is "finished" only implicitly: its branches were
deleted by `gt sync --force` and its worktree removed by `git worktree remove` at land, and
its Linear status is `Done`. `.worktrees/` is gitignored. Nothing records "this ticket was
cleaned up" — so re-running relies on git/Linear state being current.

**Evidence:**

```python
def _existing_branches(ticket):
    rc, out, _ = _run(["git", "branch", "--list", "%s/*" % ticket], cwd=REPO_ROOT)
    return branch_set(out.splitlines()) if rc == 0 else set()
```

— `scripts/qrspi_resolve.py:255-257`. Worktree reuse/idempotency —
`scripts/qrspi_resolve.py:278-287`. Batch ticket enumeration by Linear status —
`.claude/workflows/qrspi-batch.js:52, 590-613`. `.worktrees/` gitignored — `.gitignore:3`.

**Dependencies:** `git`, `gh`, and Linear MCP. The STATUSES sweep
(`['Selected','Design Review','Plan Review','Code Review']`) defines the in-flight set;
`Done` is never swept.
**Implicit contracts:** Truth is derived live from git refs + filesystem + Linear, never
from a stored manifest. A cleanup pass must therefore detect "fully-merged stack" from
git/GitHub, not from any local bookkeeping file. The `Done` status is the only "finished"
signal and it is best-effort/projection (can fail silently).

## Q9: How does existing harness code detect uncommitted changes in a worktree, and where is `git worktree remove` (or any force-removal flag) currently invoked?

**Answer:** Dirty-state detection is `git status --short` — but ONLY as worker-agent PROSE
in the SKILL (staging steps), never in Python and never as a guard before destruction.
There is NO programmatic check that a worktree is clean before removing it. `git worktree
remove` is invoked ONLY in SKILL prose with the `--force` flag (always force, suppressing
errors with `2>/dev/null`), followed by `git worktree prune`. No Python script removes a
worktree. So today removal is unconditionally forced — it does not detect or refuse on
uncommitted changes.

**Evidence:**

```bash
git worktree remove "$REPO_ROOT/.worktrees/<ticket-id>" --force 2>/dev/null; git worktree prune
```

— `.claude/skills/qrspi-work/SKILL.md:395` (land); also `:575-576` (generic). Dirty check
prose (staging only, not a teardown guard):

```
git status --short
git add <every file shown, but NOT __pycache__/ or *.pyc>
```

— `.claude/skills/qrspi-work/SKILL.md:231-232, 525-527`. The qrspi-pr agent is read-only
git: `git diff`, `git log`, `git status` — `.claude/agents/qrspi-pr.md:47`.

**Dependencies:** all in worker prose; no script dependency.
**Implicit contracts:** `--force` + `2>/dev/null` means removal currently SWALLOWS the
"worktree contains modified/untracked files" safety error git would otherwise raise. A
deterministic cleanup that wants a "blocked-by-dirty" decision must run `git status
--porcelain` itself and decide BEFORE forcing — that guard does not exist today.

## Q10: How does the current reset/discard path remove downstream phase branches and worktrees, and what does it do when a stack is only partially merged?

**Answer:** `doReset(t, r)` runs a RESET worker prompt that, per `discardPhases` (highest
first — slices before plan): (1) `gt delete <branch> --force --close` to close each PR and
delete each branch; (2) `gt checkout <resetToPhase>`; (3) remove stale downstream artifacts
(`rm -f structure.md/plan.md/worktree.md`) and `git clean -fd .qrspi/<id>/` so skip-if-exists
resume logic sees them absent; (4) best-effort Linear projection. It explicitly does NOT
touch trunk ("nothing was merged"). PARTIAL-MERGE: reset is only ever triggered by a
CHANGES_REQUESTED on an OPEN upstream PR (resolver decision 7/8), which by design happens
BEFORE any merge — the whole stack is held open until land. So reset has no partial-merge
handling: it assumes nothing is merged. It does NOT remove the worktree (the worktree is
reused at the reset-to phase).

**Evidence:**

```js
1. For each discarded phase (highest first — slices before plan): close its PR(s) and delete its branch(es) with gt delete --force --close.
2. gt checkout ${t.id}/${d.resetToPhase}; remove the now-stale downstream artifacts from the working tree (e.g. structure.md/plan.md/worktree.md when discarding plan) and git clean -fd .qrspi/${t.id}/ so the skip-if-exists resume logic sees them absent. Trunk is never touched (nothing was merged).
```

— `.claude/workflows/qrspi-batch.js:549-550`; full `doReset` — `:544-558`. SKILL detail —
`.claude/skills/qrspi-work/SKILL.md:340-369`. Reset decision (only on OPEN upstream
CHANGES_REQUESTED) — `scripts/qrspi_resolve_state.py:92-103`.

**Dependencies:** RESET worker ← `case 'reset'` dispatch (`qrspi-batch.js:664`) ← resolver
decision with `resetToPhase` + `discardPhases`.
**Implicit contracts:** Reset is "bounded to ticket-local branches and artifacts" and
"never rewrites trunk." `gt delete --force --close` both closes the PR and deletes the
branch in one call. Reset NEVER removes the worktree (unlike land). There is no
partial-merge code path because the lifecycle forbids mid-feature merges.

## Q11: How does the harness handle remote refs already deleted (e.g. GitHub auto-deletes head branch on merge) so a pruning step does not error on missing refs?

**Answer:** Pruning is delegated to `gt sync --force` (deletes merged branches, prunes) and
`git worktree prune` — both in SKILL/land-worker prose. `git worktree remove` uses `--force
2>/dev/null` which suppresses errors. There is no explicit "ref already gone" guard in
Python. The restack script's force-push (`gt submit --publish --stack --force`) and abort
handle drift, but missing-remote-ref tolerance relies on: (a) `gt sync --force` being
idempotent re: already-deleted branches; (b) the `2>/dev/null` error suppression on
worktree removal; (c) `qrspi_restack.py` treating "no worktree / no branch" as a clean
no-op success. There is NO targeted handling of "GitHub auto-deleted the head ref on merge"
beyond `gt sync`'s own behavior — this is a thin spot for any new pruning step.

**Evidence:**

```python
    # Nothing to restack if the ticket has no worktree or no branch yet ...
    # That is a clean no-op success.
    if not os.path.isdir(worktree):
        env = build_envelope(args.ticket, worktree, None, ok=True, restacked=False)
        ...
        return 0
```

— `scripts/qrspi_restack.py:199-205` (missing-ref-as-no-op idiom). `gt sync --force`
pruning — `.claude/skills/qrspi-work/SKILL.md:388`. Force/suppress on worktree removal —
`.claude/skills/qrspi-work/SKILL.md:395`.

**Dependencies:** `gt sync`, `git worktree prune` (worker prose); `qrspi_restack.py`
self-guards on missing worktree/branch.
**Implicit contracts:** Idempotent re-runs treat absent refs/worktrees as clean no-op
successes rather than errors. A new pruning step should follow that idiom: check
`os.path.isdir`/`git branch --list` first and treat absence as success, and/or tolerate
non-zero rc on a delete of an already-gone ref instead of HARD-STOPping.

## Q12: What guarantees idempotency in the existing self-locating scripts when re-run against already-processed tickets?

**Answer:** Idempotency is structural: (1) `qrspi_resolve.setup_worktree` returns an
existing worktree dir as-is, and creates branches only when the decision requires
(`create_design`), never leaving stray branches for tickets it won't act on; (2)
`qrspi_persist.persist` uses `shutil.move` (consuming the staged file) — a second run finds
no staged source and reports `ok:false "not found"` rather than re-moving; (3)
`qrspi_restack` treats missing worktree/branch as a clean no-op success, and `gt restack`
itself is idempotent (no-op when aligned, detected via the "does not need to be restacked"
phrase) — it only force-pushes when a branch actually moved; (4) `detect_existing` /
skip-if-exists logic (`runPhase` reuses non-empty canonical artifacts). All re-derive truth
live from git/filesystem, so re-running reconciles partial work.

**Evidence:**

```python
    if os.path.isdir(worktree):
        return worktree  # reuse
    ...
    if not create_design:
        return worktree  # read-only: nothing to act on, create nothing
```

— `scripts/qrspi_resolve.py:278-290`. Restack no-op idempotency —
`scripts/qrspi_restack.py:181-183` and classify_result `:84-93`. Persist move-once —
`scripts/qrspi_persist.py:65-83`. Resume/skip-if-exists — `.claude/workflows/qrspi-batch.js:249-253`.

**Dependencies:** filesystem (`os.path.isdir`, `os.path.getsize`), git refs, `gt restack`.
**Implicit contracts:** Re-running any step against an already-processed ticket must be safe
and converge to the same state. A cleanup script must be idempotent: removing an
already-removed worktree / already-deleted branch must be a clean success, not an error.
The comment "the idempotent resolver reconciles on the next run" recurs as the recovery
model (`qrspi-batch.js:629, 677`).

## Q13: What is the stdlib-only unit-test structure and fixture/mocking convention used by `scripts/qrspi_*_test.py` for simulating PR merge states?

**Answer:** TWO coexisting stdlib-only conventions (no pytest): (A) an assert/`check()`
style with a global `failures/total` counter, printing `ok:`/`FAIL:` and `sys.exit(1 if
failures else 0)` — used by `qrspi_resolve_state_test.py`, `qrspi_resolve_test.py`,
`qrspi_restack_test.py`, `qrspi_pr_state_test.py`; and (B) `unittest.TestCase` with
`setUp`/`tearDown` and `tempfile.TemporaryDirectory` — used by `qrspi_persist_test.py`.
PR/merge states are simulated as PLAIN DICT FIXTURES via tiny builders: `_phase(...)`,
`_slice(n, decision=...)`, `_impl(slices)`, `state(assigned=, linear=, phases=)` — fed
directly into the PURE `resolve()`. "merged/partial/dirty/in-flight" are expressed as
combinations of `branchExists`/`prExists`/`reviewDecision`/`unresolvedThreads` flags; there
is currently no fixture for an actual MERGED PR (the OPEN-only model has no such state).

**Evidence:**

```python
def _phase(branch=True, pr=True, decision="REVIEW_REQUIRED", threads=0):
    return {"branchExists": branch, "prExists": pr,
            "reviewDecision": decision, "unresolvedThreads": threads}
def _slice(n, pr=True, decision="REVIEW_REQUIRED", threads=0):
    return {"n": n, "prExists": pr, "reviewDecision": decision, "unresolvedThreads": threads}
def state(assigned=True, linear="Selected", phases=None):
    return {"ticketId": "RUS-1", "assigned": assigned, "linearStatus": linear, "phases": phases or {}}
```

— `scripts/qrspi_resolve_state_test.py:14-30`. Case table + runner —
`:32-36, 136-154`. unittest+tempfile style — `scripts/qrspi_persist_test.py:34-48`.
classify_* table-driven cases — `scripts/qrspi_restack_test.py:42-83`.

**Dependencies:** tests import the module under test directly (e.g. `from qrspi_resolve_state
import resolve`); run as `python3 scripts/qrspi_X_test.py` (cwd = scripts/ implied for the
bare imports, per the run instructions).
**Implicit contracts:** Tests cover ONLY pure functions; subprocess-backed code is
"intentionally NOT tested here ... verified by a manual end-to-end run" (stated in
`qrspi_resolve_test.py:6-8`, `qrspi_restack_test.py:6-8`). A cleanup test would build dict
fixtures for its pure decision function and assert the destroy/skip/blocked outcome.

## Q14: How do existing tests stub out git and Graphite subprocess calls so cleanup decision logic can be verified without touching a real repository?

**Answer:** They DON'T stub subprocess at all — there are no mocks, no `unittest.mock`, no
`monkeypatch`, no fake subprocess. The architecture AVOIDS the need: every script is split
into a PURE layer (functions taking/returning plain data — `resolve`, `classify_result`,
`classify_submit`, `parse_pr_nodes`, `real_branches`, `persist`, `detect_existing`,
`pick_tip`, `select_source`, `resolve_reviewers`) and a thin SUBPROCESS layer (`_run`,
`_git_branches`, `_query_pr`, `setup_worktree`, `restack`). Tests exercise ONLY the pure
layer with literal inputs (dicts, rc/stdout/stderr tuples, temp dirs). The subprocess layer
is explicitly left to manual e2e. `qrspi_persist_test.py` touches the filesystem via real
`tempfile.TemporaryDirectory` (not a mock) because `persist` is filesystem-only.

**Evidence:**

```python
def classify_result(rc, stdout, stderr):
    """Map a `gt restack` (rc, stdout, stderr) to (ok, restacked, error). Pure, so the
    success/failure/no-op decision is unit-testable without running gt."""
```

— `scripts/qrspi_restack.py:75-83`; tested with literal tuples at
`scripts/qrspi_restack_test.py:42-68`. "subprocess-backed parts ... intentionally NOT
tested here" — `scripts/qrspi_restack_test.py:6-8`, `scripts/qrspi_resolve_test.py:6-8`.
Grep for `mock`/`MagicMock`/`monkeypatch` in `scripts/` returned zero matches.

**Dependencies:** none — the design eliminates the dependency by passing subprocess
RESULTS (rc, stdout, stderr) into pure classifiers.
**Implicit contracts:** To make cleanup decision logic testable, factor it as a pure
function that accepts already-gathered data (e.g. PR merged-flags, `git status` porcelain
text, branch list) and returns a destroy/skip/blocked decision + an error string — exactly
the `classify_result(rc, stdout, stderr)` shape. Do NOT introduce mocking; pass raw
subprocess output into pure functions instead.

## Q15: How do the existing land and reset actions surface their decisions and outcomes so a cleanup pass's skip/destroy/blocked-by-dirty decisions are visible to an operator?

**Answer:** Three layers: (1) the resolver's `decision.reason` string (human-readable
rationale, logged by the batch as `decision=<action> — <reason>`); (2) the batch `log(...)`
calls throughout the per-ticket loop (e.g. restack outcomes, "skipped (action)", per-slice
commits, finalize failures); (3) each finalize worker returns `{ ok, prUrl, newStatus,
summary }` (WORKER_SCHEMA), folded by `finResult` into a per-ticket result object, and the
workflow returns `{ ticketsProcessed, results }`. Scripts surface outcomes via their stdout
JSON envelope (`ok`, `restacked`, `submitted`, `error`, `bytes`, `dest`, etc.). So an
operator sees: resolver reason → batch log lines → per-ticket result summary → final
results array.

**Evidence:**

```js
    const a = r.decision.action
    log(`  ${t.id}: decision=${a} — ${r.decision.reason}`)
    ...
    results.push(res)
    log(`[${i + 1}/${tickets.length}] ${t.id} → ${res.action}${res.newStatus ? ` (${res.newStatus})` : ''}`)
```

— `.claude/workflows/qrspi-batch.js:653-674`. finResult summary fold — `:577-583`. Final
return — `:682`. WORKER_SCHEMA (`ok/prUrl/newStatus/summary`) — `:142-152`. Restack outcome
log — `:350-351`. Reset/land summaries flow through `finResult`/`doReset` return objects
(`:556-557`, `:570`). Script envelopes carry `error`/`restacked`/`submitted`/`bytes`/`dest`.

**Dependencies:** `log()` and the returned results object are the operator-facing surface;
`decision.reason` originates in `qrspi_resolve_state.py`.
**Implicit contracts:** Every action returns a `summary` (1-2 sentences) and an `action`
tag; failures are recorded (not thrown) so the batch continues
(`resolve_failed`/`restack_conflict`/`errored`/`failed` tags at `:634, 649, 575, 678`). A
cleanup pass should mirror this: emit a `reason` per ticket, log skip/destroy/blocked
distinctly, and return a `{ ok, action, summary }`-shaped result (and a script envelope
with an explicit `error` on blocked-by-dirty) so it folds into the existing results array.

---

## Discovered Patterns

- **Pure/impure split as the universal idiom.** Every Python script isolates pure,
  data-in/data-out functions (decision logic, classifiers, path builders, envelope
  assembly) from a thin subprocess layer (`_run`, `gt`/`git`/`gh` shells). Only the pure
  layer is unit-tested; the impure layer is "manual e2e." A new cleanup script is expected
  to follow this exactly. (`qrspi_resolve.py`, `qrspi_restack.py`, `qrspi_pr_state.py`)
- **Self-locating one-shot scripts** derive `REPO_ROOT` from `__file__` (two levels up),
  take only short token-free flags (`--ticket`, `--artifact`), and emit one stdout JSON
  envelope with `ok`/`repoRoot`/`error?`, exit 0/1. Driven by a "run EXACTLY this one
  command verbatim, output the JSON, HARD STOP on ok:false" worker prompt. Motivated by a
  weak local worker model mangling the literal `qrspi` token in long paths.
- **One-shot error reporting, never retry.** All scripts catch infra errors and report once
  as `ok:false` with the verbatim message; the resolver reconciles partial work on the next
  idempotent run rather than retrying in place.
- **Truth is recomputed live from git/GitHub/Linear**, never from a stored manifest. There
  is no persistent record of which tickets are in-flight vs finished.
- **Destructive ops are currently worker-agent PROSE, not deterministic code.** Land/reset
  cleanup (`gt sync --force`, `git worktree remove --force`, `gt delete --force --close`,
  `git clean -fd`) live only in SKILL.md and JS prompt strings — exactly the class of
  path-sensitive multi-step shell that `qrspi_resolve.py`/`qrspi_persist.py`/`qrspi_restack.py`
  were created to replace with deterministic self-locating scripts.

## Inconsistencies

- **Merge state is unmodeled.** `qrspi_pr_state.py` queries `states:OPEN` only and reports
  no `merged`/`state` field, yet the questions and lifecycle speak of "fully-merged stacks"
  and the SKILL's land cleanup assumes branches were merged. There is no code that can
  currently distinguish merged from closed-unmerged from in-review — any cleanup pass that
  keys on "fully merged" must add new GitHub queries. (`qrspi_pr_state.py:29` vs
  `SKILL.md:373-397`)
- **No dirty-worktree guard before forced removal.** `git status --short` appears only as
  staging prose; worktree removal is always `--force 2>/dev/null`, which SWALLOWS the very
  "uncommitted changes" error a blocked-by-dirty decision would need. The destroy path is
  unconditional today. (`SKILL.md:395, 525-527`)
- **Two divergent test styles** coexist with no stated rule: assert/`check()` +
  `sys.exit` (resolve_state, resolve, restack, pr_state) vs `unittest.TestCase` (persist).
  A new `_test.py` could pick either; the assert/`check()` style is the majority for
  decision-logic tests.
- **`gt sync` guidance is split.** SKILL says never `gt sync` a held stack mid-feature
  except in land cleanup (`SKILL.md:511-512`), while `qrspi_restack.py` deliberately uses
  `gt restack` + force-push and explicitly NEVER `gt sync`s (`qrspi_restack.py:18-20`) — two
  different "keep the stack current" mechanisms for two different lifecycle moments. Not a
  bug, but a subtlety a cleanup author must respect (land is the only place pruning/sync is
  allowed).
- **Co-authorship trailer drift.** SKILL heredoc examples use
  `Co-Authored-By: Claude Opus 4.7 (1M context)` (`SKILL.md:235`) while the repo's project
  convention (and recent commits) use a different model string — a stale literal in the
  skill template, harmless but inconsistent.
