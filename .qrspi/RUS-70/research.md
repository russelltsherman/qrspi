# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** draft

## Q1: How does the land action determine which branch to check out before invoking the Graphite stack merge, and where is the hard-coded slice-1 reference set?

**Answer:** Two layers are involved. (1) The orchestration layer (`doLand` in `qrspi-batch.js`) does NOT check out a branch itself — it spawns a LAND worker agent and hands it a free-text prompt that says "merge bottom-up (gt merge --no-interactive)" with no explicit checkout branch. (2) The authoritative checkout instruction lives in the `## action: land` section of the qrspi-work SKILL the worker is told to follow. There the hard-coded reference is `gt checkout <ticket-id>/slice-1`. So the land step deterministically checks out **slice-1 (the stack bottom)** and then runs `gt merge`. There is no logic that computes or checks out the stack **tip** (top slice) for the merge.

**Evidence:**

```
1. Confirm the stack is current and approved (the resolver already gated this), then land
   from the bottom up:
   ```bash
   gt checkout <ticket-id>/slice-1 --no-interactive   # or <id>/design if no slices/plan-only feature
   gt submit --publish --stack --no-edit --no-interactive   # ensure remotes current
   gt merge --no-interactive                           # merges bottom-up (NOT --confirm: ...)
```

— `.claude/skills/qrspi-work/SKILL.md:446-452`

```
const fin = await agent(
  `You are the LAND worker for ${t.id}, in ${r.worktreeDir}. Every PR in the stack is approved+clean. Follow the "action: land" steps of ${SKILL}: ensure the stack is current (gt submit --publish --stack), merge bottom-up (gt merge --no-interactive ...
```

— `.claude/workflows/qrspi-batch.js:802-803` (`SKILL = '.claude/skills/qrspi-work/SKILL.md'`, line 55)

**Dependencies:** `doLand` (qrspi-batch.js) → LAND worker agent → SKILL.md `action: land` prose → `gt checkout` / `gt merge`. The branch name `<ticket-id>/slice-1` is constructed by string interpolation in the SKILL prose; the JS prompt never passes a branch name.
**Implicit contracts:** The worker is trusted to read the SKILL and check out slice-1. The merge is assumed to consume the whole stack from slice-1. No branch name is threaded from the resolver envelope; the worker reconstructs `<ticket-id>/slice-1` from the ticket id.

## Q2: How is the set of slice branches for a ticket enumerated, and is the actual stack tip (top slice) computed anywhere or only the bottom slice-1?

**Answer:** Slice branches are enumerated by `slice_numbers()` in `qrspi_pr_state.py`, which regex-matches `/slice-(\d+)` over `git branch --list` lines and returns a sorted unique int list. The stack **tip IS computed** — but only in `pick_tip()` in `qrspi_resolve.py`, which returns `<ticket>/slice-<max N>`. Critically, `pick_tip()` is used ONLY to choose a branch to **check out when re-creating a worktree** (worktree reuse), and its result is NOT placed in the resolver envelope nor passed to the land step. The land step has access to neither the slice count nor the computed tip — it hard-codes slice-1.

**Evidence:**

```
def slice_numbers(branch_lines):
    """Extract slice numbers from `git branch --list` output lines for a ticket.
    Accepts raw lines like '  RUS-1/slice-2'. Returns a sorted unique int list."""
    nums = set()
    for line in branch_lines:
        m = re.search(r"/slice-(\d+)\s*$", line.strip())
        if m:
            nums.add(int(m.group(1)))
    return sorted(nums)
```

— `scripts/qrspi_pr_state.py:259-267`

```
def pick_tip(branches, ticket):
    """Pick the highest existing phase branch to reuse a worktree on, newest phase
    first: slice-N (largest N) > plan > design. ..."""
    snums = slice_numbers(branches)
    if snums:
        return "%s/slice-%d" % (ticket, max(snums))
    for phase in ("plan", "design"):
        ...
```

— `scripts/qrspi_resolve.py:144-159`; `pick_tip` is consumed only by `_reuse_or_create_worktree` (`qrspi_resolve.py:304`, `git worktree add ... tip`), not by the land decision.

**Dependencies:** `pick_tip` → `slice_numbers` → `branch_set`/`git branch --list`. The tip computation exists but is siloed in worktree-reuse, decoupled from land.
**Implicit contracts:** `slice_numbers` relies on branch naming `<ticket>/slice-<n>`. `pick_tip` assumes max-N is the tip (true for a linearly-stacked feature). The land path does not reuse this.

## Q3: What exact Graphite command and flags are issued to perform the stack merge, and what is its documented behavior regarding which branches in the upstack get merged relative to the checked-out branch?

**Answer:** The exact command is `gt merge --no-interactive` (explicitly NOT `--confirm`). It is preceded by `gt submit --publish --stack --no-edit --no-interactive` to refresh remotes. The repo's Graphite skill (`using-graphite-cli`) does **NOT document `gt merge` at all** — there is no entry for it in the command reference; the only documented directionality note is "downstack = toward trunk (older/parent branches), upstack = away from trunk (newer/child branches)." Because the merge is initiated after checking out slice-1 (the bottom), and `gt merge` operates on the current branch and its **downstack** (its ancestors toward trunk), this lands slice-1 + plan + design but does **not** climb the upstack to slices 2..N. The SKILL comment claims `gt merge` "merges bottom-up", which is the unverified assumption at the heart of the bug.

**Evidence:**

```
gt merge --no-interactive                           # merges bottom-up (NOT --confirm: it forces a prompt that --no-interactive cannot satisfy)
```

— `.claude/skills/qrspi-work/SKILL.md:451`

```
Directionality: **downstack = toward trunk** (older/parent branches),
**upstack = away from trunk** (newer/child branches).
```

— `.claude/skills/using-graphite-cli/references/command-reference.md:70-71` (no `gt merge` row exists in this reference; grep for "gt merge" in `using-graphite-cli/` returns only `gt fold`/`gt sync` rows).

**Dependencies:** `gt merge` (external Graphite CLI) — behavior is NOT documented in-repo. The SKILL relies on an inline comment ("merges bottom-up") that the repo cannot substantiate from its own docs.
**Implicit contracts:** The code assumes `gt merge` from the bottom merges the entire upstack. This contract is undocumented and is the suspected source of the half-landed-stack defect. NOT FOUND in-repo: any authoritative statement of which branches `gt merge` consumes relative to the checked-out branch.

## Q4: What inputs (ticket id, branch names, slice count) does the land step receive from the resolver envelope, and does that envelope already expose the slice count or tip branch?

**Answer:** The envelope assembled by `build_envelope()` (`qrspi_resolve.py`) exposes: `ok`, `repoRoot`, `worktreeDir`, `existing` (per-phase booleans), `decision`, `commentTargets`, `reviewers`, `teamReviewers`, `ticketContent`, and optionally `error`. The `decision` dict for a land verdict contains only `action`, `phase`, `nextPhase`, `resetToPhase`, `discardPhases`, `commentTargets`, `reason`. **Neither the slice count nor the tip branch is exposed anywhere in the envelope.** The land worker receives the ticket id (`t.id`) and `worktreeDir` from the JS prompt and reconstructs `<ticket-id>/slice-1` itself.

**Evidence:**

```
env = {
    "ok": ok,
    "repoRoot": REPO_ROOT,
    "worktreeDir": worktree_dir,
    "existing": existing,
    "decision": decision,
    "commentTargets": comment_targets_of(decision),
    "reviewers": reviewers,
    "teamReviewers": team_reviewers,
    "ticketContent": ticket_content,
}
```

— `scripts/qrspi_resolve.py:213-223`

```
out = {
    "action": action, "phase": kw.get("phase"), "nextPhase": kw.get("nextPhase"),
    "resetToPhase": kw.get("resetToPhase"), "discardPhases": kw.get("discardPhases", []),
    "commentTargets": kw.get("commentTargets", []), "reason": kw.get("reason", ""),
}
```

— `scripts/qrspi_resolve_state.py:122-129`

**Dependencies:** `doLand` reads `t.id` and `r.worktreeDir` from the envelope; `r.decision.reason` is logged. No slice metadata flows through.
**Implicit contracts:** The land step is expected to derive all branch names from the ticket id alone. To pass a tip branch or slice count to land, the envelope (`build_envelope`) and/or `decision()` would need a new field — neither exists today.

## Q5: Does the codebase have a dedicated land helper script (analogous to qrspi_persist.py / qrspi_pr_body.py), or is land expressed entirely as inline shell in the workflow/prompt?

**Answer:** **NOT FOUND — there is no dedicated land helper script.** A search of `scripts/` for a `*land*` file returns nothing. Land is expressed as free-text prompt steps (`doLand` in `qrspi-batch.js` → SKILL.md `action: land` prose) executed by the LAND worker agent via raw `gt checkout` / `gt submit` / `gt merge` shell. The only deterministic, tested script in the land PATH is `qrspi_cleanup.py`, which runs AFTER the merge to reap the worktree/branches — it does not perform or order the merge itself.

**Evidence:**

```
$ ls scripts/ | grep -i land   →   (no output)
```

Land-adjacent scripts: `scripts/qrspi_cleanup.py` (post-merge reaper, invoked at `qrspi-batch.js:813` via `runCleanup`). The merge itself is unscripted prose at `.claude/skills/qrspi-work/SKILL.md:446-452`.

**Dependencies:** Contrast with `qrspi_persist.py`, `qrspi_pr_body.py`, `qrspi_resolve.py`, `qrspi_cleanup.py`, `qrspi_revise_amend.py` — all deterministic tested scripts. The merge step is the one phase action with no script wrapper; it is fully delegated to the worker model + prose.
**Implicit contracts:** Because the merge is unscripted prose, correctness depends entirely on the SKILL text being right (and it hard-codes slice-1) and on `gt merge`'s undocumented upstack behavior.

## Q6: How does the workflow "square up local state" before the merge, and which commands are used so that already-approved remote PR heads are not force-pushed or overwritten?

**Answer:** Before merging, the land step runs `gt submit --publish --stack --no-edit --no-interactive` to "ensure remotes current." The `--no-edit` flag avoids the description editor; `--publish` marks PRs non-draft. The SKILL explicitly forbids `gt sync --force` and `git worktree remove --force` in the land step (those are reserved for the tested cleanup script). The land worker prompt repeats this: "Do NOT remove the worktree, delete branches, or run `gt sync --force`." There is no `git push --force` in the land path; `gt submit` is the only remote-mutating command and it updates PR heads via Graphite's normal (non-force-by-default) push.

**Evidence:**

```
gt submit --publish --stack --no-edit --no-interactive   # ensure remotes current
```

— `.claude/skills/qrspi-work/SKILL.md:450`

```
Do NOT remove the worktree, delete branches, or run \`gt sync --force\` — a separate deterministic cleanup step (qrspi_cleanup.py) handles all reaping AFTER the merge.
```

— `.claude/workflows/qrspi-batch.js:803`

```
- Never use `gt sync` mid-feature on a held stack except in `land` cleanup — it deletes ...
```

— `.claude/skills/qrspi-work/SKILL.md:586`

**Dependencies:** `gt submit --publish --stack` (remote refresh) → `gt merge` (merge) → `qrspi_cleanup.py` (reap, which itself may run `gt sync --force` internally — see `qrspi_cleanup.py:178` comment).
**Implicit contracts:** The land step assumes `gt submit --stack` does not overwrite approved remote heads destructively. Force operations are quarantined to the post-merge cleanup script. `--no-edit` is required so PR bodies (seeded at creation) are not disturbed.

## Q7: After a land completes, what condition does the workflow use to mark the ticket Done, and does it confirm every slice PR reached MERGED rather than assuming success from the merge command's exit code?

**Answer:** The "Done" status is **self-reported by the LAND worker** via its `newStatus` field — the worker is told to "BEST-EFFORT project Linear → Done" and to return `{ ok, prUrl, newStatus, summary }`. `finResult()` copies `fin.newStatus` straight into the result. **The workflow does NOT independently confirm every slice PR reached MERGED before declaring Done.** The only MERGED verification anywhere is inside `qrspi_cleanup.py` (`is_stack_fully_merged`), which runs AFTER and gates only the worktree REAP — not the Done projection. If the merge left the tip slice OPEN, cleanup returns `skip` (no reap) but the ticket is still reported landed with `newStatus: Done`, because Done depends on the worker's self-report, not on a MERGED check.

**Evidence:**

```
then BEST-EFFORT project Linear → "Done". ... Treat any infrastructure/merge error as a HARD STOP (return ok:false, verbatim error).
Return: ok, prUrl, newStatus, summary.
```

— `.claude/workflows/qrspi-batch.js:803-804`

```
return { ticketId: t.id, action, newStatus: fin.newStatus, summary: fin.summary, prUrl: fin.prUrl }
```

— `.claude/workflows/qrspi-batch.js:834` (`finResult`)

```
def is_stack_fully_merged(merge_state):
    """True only when EVERY real branch's PR is merged (all-or-nothing, AC2)..."""
    if not merge_state: return False
    return all(entry.get("merged") for entry in merge_state.values())
```

— `scripts/qrspi_pr_state.py:249-256` (used only by `qrspi_cleanup.py`, not by the Done transition)

**Dependencies:** Done ← LAND worker `newStatus` (self-report). MERGED verification ← `is_stack_fully_merged` ← `qrspi_cleanup.py` (reap gate only). The two are decoupled.
**Implicit contracts:** Done is trusted from the worker's word + a non-zero `ok`. The exit-code/`ok` of `gt merge` is the only success signal feeding the Done projection; per-PR MERGED state is never asserted on the Done path.

## Q8: For a single-slice stack (slice-1 is also the tip), what branch does land check out, and does the current bottom-up-from-slice-1 logic still land the full stack correctly in that case?

**Answer:** For a single-slice stack, slice-1 IS the tip, so checking out `<ticket-id>/slice-1` and running `gt merge` covers the entire upstack (there is nothing above slice-1). In this case the bottom-up-from-slice-1 logic lands the full stack correctly. The defect only manifests when N>1: checking out slice-1 (bottom) leaves slices 2..N (the upstack above slice-1) unmerged. This is why the bug is specific to multi-slice stacks — the single-slice path is coincidentally correct.

**Evidence:** Same checkout instruction regardless of slice count:

```
gt checkout <ticket-id>/slice-1 --no-interactive   # or <id>/design if no slices/plan-only feature
```

— `.claude/skills/qrspi-work/SKILL.md:449`

Stack shape (slice-2 stacked on slice-1, etc.):

```
└── <id>/slice-1  PR     — slice 1 code            (stacked on plan)
     └── <id>/slice-2 PR — slice 2 code            (stacked on slice-1)
```

— `docs/qrspi-pr-gated-lifecycle-design.md:58-59`

**Dependencies:** Same as Q1/Q3. Single-slice correctness is incidental — slice-1 == tip when N==1.
**Implicit contracts:** The hard-coded slice-1 checkout is correct iff slice-1 is the tip, which holds only for N==1 (or plan-only features where `<id>/design` is checked out instead).

## Q9: How does the land action behave when slice branches are non-contiguous or partially merged already (e.g., lower PRs MERGED, tip open) — does it re-attempt the full upstack or skip merged branches?

**Answer:** The land merge itself (`gt merge` from slice-1) has no explicit skip/re-attempt logic in-repo — it is whatever `gt merge` does (undocumented here). On the cleanup side, the partial-merge case is explicitly handled and classified as `skip`: `qrspi_cleanup.py`'s `classify_cleanup` returns `decision: "skip", reason: "stack not fully merged"` when slice-1 is MERGED and slice-2 is OPEN. This is exactly the half-landed scenario. The cleanup does NOT re-attempt the merge; it just declines to reap. There is a separate documented gotcha (MEMORY.md `resolver-partially-landed-stack`) that the resolver can misread a partially-landed stack as `entry_blocked "No design branch"` when lower PRs are merged but the top slice is open.

**Evidence:**

```
# --- Case 2: partially-merged stack, clean worktree -> skip -----------------
_partial = stack_merge_state(
    ["RUS-1/slice-1", "RUS-1/slice-2"],
    {"RUS-1/slice-1": _node(10, "MERGED", True),
     "RUS-1/slice-2": _node(11, "OPEN", False)})
check("partial + clean -> skip",
      classify_cleanup(_partial, ""),
      {"decision": "skip", "reason": "stack not fully merged"})
```

— `scripts/qrspi_cleanup_test.py:43-50`

**Dependencies:** Partial-merge handling lives entirely in `qrspi_cleanup.py` (reap gate). The merge command does not consult merge state. The resolver's partial-stack misread is a known separate hazard (see Inconsistencies).
**Implicit contracts:** `is_stack_fully_merged` is all-or-nothing; any single OPEN branch → `skip`. The merge re-attempt, if any, would happen only on a future batch run when the resolver re-decides `land` — but see Q11/Inconsistencies: the resolver decides `land` from review approval state, not from per-branch MERGED state, so a re-run may not cleanly re-attempt only the unmerged tip.

## Q10: Is there any enforcement that the bottom-up merge order is preserved, and what happens to that ordering when the merge is initiated from the tip rather than slice-1?

**Answer:** There is **no in-repo enforcement of merge ordering** beyond the prose instruction to check out slice-1 first and the inline comment "merges bottom-up." Ordering is delegated entirely to `gt merge`'s behavior, which the repo does not document. The design doc asserts the policy ("Land the whole stack bottom-up", "LAND the whole stack bottom-up") but no code or test verifies that slices merge in order or that the merge starts from the bottom. If the merge were initiated from the tip instead of slice-1, Graphite would need to merge the tip's full downstack — the opposite of the current bottom-anchored approach — and nothing in the repo guards which anchor is used; the anchor is a single hard-coded string in SKILL.md.

**Evidence:**

```
| 3 | Merge cadence | **Land the whole stack bottom-up only when all phases are approved** |
```

— `docs/qrspi-pr-gated-lifecycle-design.md:36`

```
LAND the whole stack bottom-up. Project Linear → "Done".
```

— `docs/qrspi-pr-gated-lifecycle-design.md:115`

No code/test references enforce order; grep for ordering enforcement around the merge returns only the SKILL prose at `.claude/skills/qrspi-work/SKILL.md:446-452`.

**Dependencies:** Ordering ← `gt merge` (external, undocumented in-repo) + the SKILL's hard-coded slice-1 anchor.
**Implicit contracts:** "Bottom-up" is policy, not enforced mechanism. The merge anchor is a literal `<ticket-id>/slice-1` with no validation that it is the bottom or that the upstack will follow.

## Q11: What existing tests cover the land action or the resolver's land decision, and do any assert that all N slice PRs reach MERGED?

**Answer:** `qrspi_resolve_state_test.py` has two land cases: "all slices approved+clean -> land" (2 slices) and "no commentTargets, approved slices -> land, NOT respond_comment." Both assert ONLY that the resolver returns `{action: "land", phase: "implementation"}` from APPROVED review state — they do **not** assert anything about branch checkout, merge order, or that all N slice PRs reach MERGED (the resolver decides land from `reviewDecision == APPROVED` + zero unresolved threads, never from MERGED state). The only tests asserting MERGED are `qrspi_cleanup_test.py` and `qrspi_pr_state_test.py`, which cover the post-merge REAP gate (`is_stack_fully_merged`, `stack_merge_state`), not the land/merge action. There is **no test that exercises `gt merge` actually landing every slice** — the merge is unscripted prose.

**Evidence:**

```
case("all slices approved+clean -> land",
     state(phases={"design": _phase(decision="APPROVED"),
                   "plan": _phase(decision="APPROVED"),
                   "implementation": _impl([_slice(1, decision="APPROVED"),
                                            _slice(2, decision="APPROVED")])}),
     {"action": "land", "phase": "implementation"})
```

— `scripts/qrspi_resolve_state_test.py:139-144`

```
return decision("land", phase="implementation",
                reason="All phases approved and clean; land the whole stack bottom-up.")
```

— `scripts/qrspi_resolve_state.py:243-244` (land decided from approval, not MERGED)

MERGED assertions exist only for cleanup: `qrspi_pr_state_test.py:222-223` (`is_stack_fully_merged(_fully_merged) == True`), `qrspi_cleanup_test.py:35-50`.

**Dependencies:** Resolver land test ← review state fixtures. Cleanup/pr_state MERGED tests ← `stack_merge_state`. The two test suites never meet on the merge action.
**Implicit contracts:** The resolver's land decision is decoupled from merge outcome; tests reflect that. No test would catch a land that merges slice-1 but leaves slice-2 open, because the merge itself is untested.

## Q12: How are multi-slice stacks represented in the existing test fixtures, and is there a fixture with N>1 slices that a land test could exercise?

**Answer:** Yes. Multi-slice (N=2) fixtures already exist and are reusable. In `qrspi_resolve_state_test.py`, `_impl([_slice(1,...), _slice(2,...)])` builds a 2-slice implementation phase; `_impl(slices, expected=None)` sets `expectedSlices = len(slices)` (or an explicit `expected` for short-stack cases). In `qrspi_pr_state_test.py` and `qrspi_cleanup_test.py`, multi-slice stacks are represented as branch lists `["RUS-1/slice-1", "RUS-1/slice-2"]` mapped to per-branch `_node(prNumber, state, merged)` GraphQL stubs, covering fully-merged, partial (slice-1 MERGED / slice-2 OPEN), and all-OPEN. A land test exercising N>1 could reuse the `["RUS-1/slice-1","RUS-1/slice-2"]` + `stack_merge_state` pattern to assert that after land every branch is MERGED.

**Evidence:**

```
def _impl(slices, expected=None, pr_summary=True):
    return {"branchExists": bool(slices), "slices": slices,
            "expectedSlices": len(slices) if expected is None else expected, ...}
```

— `scripts/qrspi_resolve_state_test.py:20-25`

```
_partial = stack_merge_state(
    ["RUS-1/slice-1", "RUS-1/slice-2"],
    {"RUS-1/slice-1": _node(10, "MERGED", True),
     "RUS-1/slice-2": _node(11, "OPEN", False)})
```

— `scripts/qrspi_cleanup_test.py:44-47`

**Dependencies:** Fixtures use helpers `_slice`, `_impl`, `_node`, `stack_merge_state`, `slice_numbers`. All stdlib-only, run with `python3`.
**Implicit contracts:** Branch naming `<ticket>/slice-<n>` is the fixture convention. `_node(number, state, merged)` is the per-PR GraphQL stub shape (`scripts/qrspi_cleanup_test.py` / `qrspi_pr_state_test.py`).

## Q13: What does the land step log or report on completion, and would a partially-landed outcome (tip slice left open) currently surface as an error or pass silently?

**Answer:** On completion `doLand` returns `{ ticketId, action: "land", newStatus, summary, prUrl, cleanup{...} }` and the main loop logs `[i/N] <id> → land (<newStatus>)`. The cleanup outcome is logged separately. For a partially-landed outcome (tip slice left open), it **passes silently as a success**: the worker's `gt merge` of slice-1 likely exits 0 (slice-1 + ancestors merged), so `fin.ok` is true and `newStatus` is the worker's self-reported "Done"; cleanup then returns `decision: "skip"` ("stack not fully merged"), which `doLand` logs as `cleanup decision=skip — ... (no reap)` — an informational line, NOT an error. No code raises, sets `ok:false`, or downgrades the action when the stack is only partially merged. The half-landed state surfaces only as a leftover worktree for a future reconciliation pass.

**Evidence:**

```
} else {
  log(`  ${t.id}: cleanup decision=${cl.decision} — ${cl.reason ?? ''} (no reap)`)
}
```

— `.claude/workflows/qrspi-batch.js:818-820` (the `skip` branch — informational, not an error)

```
log(`[${i + 1}/${tickets.length}] ${t.id} → ${res.action}${res.newStatus ? ` (${res.newStatus})` : ''}`)
```

— `.claude/workflows/qrspi-batch.js:1007`

**Dependencies:** `doLand` log lines + `finResult` summary + main-loop log. None inspect per-PR MERGED state.
**Implicit contracts:** A `skip` cleanup verdict is treated as a benign "in-flight, try later" signal, indistinguishable from a genuinely half-landed stack. There is no severity escalation for "merge ran but did not fully land."

## Q14: Does any post-land verification query PR states (e.g., via scripts/qrspi_pr_state.py / gh GraphQL) to confirm MERGED status, and where would such a check be wired in?

**Answer:** Yes, but only indirectly and only as a reap gate. `qrspi_cleanup.py` calls `stack_merge_state` + `is_stack_fully_merged` (from `qrspi_pr_state.py`) over real gh GraphQL nodes to confirm EVERY branch's PR is MERGED before destroying the worktree. This is the ONLY post-land MERGED check. It is NOT wired into the land success/Done decision — it runs after, and a `False` result yields `skip` (no reap), not a failed land. To make land verify completion, the natural wiring point is between the `gt merge` and the Done projection in `doLand` (`qrspi-batch.js:807-812`) and/or before `finResult` sets `newStatus: Done` — calling `is_stack_fully_merged(stack_merge_state(...))` there and failing/looping the land if any slice is still OPEN.

**Evidence:**

```
if is_stack_fully_merged(stack_merge_state):
    return {"decision": "destroy", "reason": "stack fully merged"}
return {"decision": "skip", "reason": "stack not fully merged"}
```

— `scripts/qrspi_cleanup.py:80-87` (the only post-land MERGED consult; gates reap, not Done)

```
if (!fin || !fin.ok) return res
const cl = await runCleanup(t.id, /* dryRun */ false, 'Finalize')
```

— `.claude/workflows/qrspi-batch.js:812-813` (the seam where a MERGED-confirmation gate could be inserted)

**Dependencies:** `qrspi_cleanup.py` → `stack_merge_state`/`is_stack_fully_merged` (`qrspi_pr_state.py`) → gh GraphQL nodes. The Done path bypasses this entirely.
**Implicit contracts:** PR MERGED state IS already queryable via `qrspi_pr_state.py` (it gathers per-branch merge fields with `prefer="merged"`), so a land-completion verifier could reuse the existing gather rather than building new GraphQL. The data exists; it is just not consulted before declaring the land done.

---

## Discovered Patterns

- **Deterministic-script vs. prose-worker split.** Nearly every phase action is backed by a self-locating, unit-tested Python script (`qrspi_resolve.py`, `qrspi_persist.py`, `qrspi_pr_body.py`, `qrspi_cleanup.py`, `qrspi_revise_amend.py`). The **land/merge action is the lone exception** — it is unscripted free-text prose executed by a worker agent against `gt checkout`/`gt merge`. This is the structural reason the slice-1 hard-code and the "merges bottom-up" assumption went unguarded by any test.
- **MERGED state is computed but only used for reaping.** `stack_merge_state` + `is_stack_fully_merged` (with `prefer="merged"`, "any MERGED node wins") give an authoritative per-branch MERGED verdict, but the only consumer is `qrspi_cleanup.py`. The land success/Done path never consults it.
- **The tip IS computable.** `pick_tip()` already returns `<ticket>/slice-<maxN>`. The repo has the building blocks (`slice_numbers`, `pick_tip`, `stack_merge_state`) to land from/verify the full stack — they are just not wired into the land action.
- **Envelope is the deterministic contract.** Phase workers are deliberately given minimal trusted inputs via the resolver envelope (the worker "never hand-assembles JSON"). Land breaks this pattern: it reconstructs branch names from the ticket id inside prose rather than receiving them in the envelope.
- **`gt merge --no-interactive` (not `--confirm`)** is the established autonomous-merge idiom; `gt sync --force` is quarantined to cleanup. Force pushes are avoided on the land path.

## Inconsistencies

- **SKILL comment vs. actual `gt merge` behavior (the core defect).** `.claude/skills/qrspi-work/SKILL.md:449-451` checks out `<ticket-id>/slice-1` (the stack BOTTOM) and comments that `gt merge` "merges bottom-up". `gt merge` operates on the current branch and its downstack (toward trunk); from slice-1 that lands slice-1 + plan + design but leaves the upstack slices 2..N OPEN. The comment asserts an upstack-climbing behavior the repo never documents or tests, producing the half-landed multi-slice stack. The repo's own Graphite reference does not document `gt merge` at all (`using-graphite-cli/references/command-reference.md`).
- **Design doc policy vs. mechanism.** `docs/qrspi-pr-gated-lifecycle-design.md:36,115` mandate "Land the whole stack bottom-up," but no code or test enforces full-stack landing or ordering; the mechanism is a single hard-coded slice-1 string + an unverified `gt merge` assumption.
- **Done depends on self-report, not MERGED truth.** The Done projection comes from the LAND worker's `newStatus` (qrspi-batch.js:803-804, 834), while the only MERGED verification (`is_stack_fully_merged`) gates only the post-merge reap (qrspi_cleanup.py:80-87). A partially-landed stack can therefore report `Done` while cleanup independently says `skip`/"stack not fully merged" — two subsystems reaching contradictory conclusions about the same land.
- **`skip` is overloaded.** `qrspi_cleanup.py`'s `skip` covers both "legitimately in-flight, nothing merged yet" (all OPEN) and "partially landed, tip left open" (Case 2). These have very different severities but emit the identical benign `skip` log line (qrspi-batch.js:818-820), so a genuinely half-landed stack is indistinguishable from a not-yet-started one.
- **Known resolver hazard on partial stacks (MEMORY.md).** Project memory `resolver-partially-landed-stack` notes that with lower PRs merged + top slice open, the resolver can wrongly report `entry_blocked "No design branch"` (because the design branch was reaped by `gt sync` on merge) — meaning a half-landed stack may not cleanly re-trigger `land` on a subsequent batch run to finish the job.
