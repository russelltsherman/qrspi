# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-11T14:10:00Z
**Status:** draft

## Q1: What stack information (branches, PRs, merge states, ticket assignment/status) does the resolver receive as input, and in what shape is it structured?

**Answer:** The resolver `resolve(state)` is a pure function consuming a single normalized `state` dict produced by `qrspi_pr_state.build_state(...)`. Top-level keys: `ticketId`, `assigned` (bool), `linearStatus` (str), `blockedOpen` (bool), `blockedBy` (list), and `phases`. `phases` has fixed keys `design`, `plan`, `implementation`. `design`/`plan` are per-phase PR dicts; `implementation` is a stack wrapper holding `branchExists`, `slices` (list of per-slice PR dicts each carrying `n`), `expectedSlices`, `prSummaryCommitted`. Each phase/slice PR dict carries: `prExists`, `number`, `reviewDecision`, `unresolvedThreads`, `merged`, `state`, `mergedAt`, `commentTargets`, and (for phases) `branchExists`.

**Evidence:**

```python
return {
    "ticketId": ticket, "assigned": assigned, "linearStatus": linear_status,
    "blockedOpen": blocked_open, "blockedBy": list(blocked_by or []),
    "phases": {
        "design": phase_pr("design"),
        "plan": phase_pr("plan"),
        "implementation": {
            "branchExists": bool(real_snums), "slices": slices,
            "expectedSlices": expected_slices,
            "prSummaryCommitted": pr_summary_committed,
        },
    },
}
```

— `scripts/qrspi_pr_state.py:423-439`
**Dependencies:** `qrspi_pr_state.build_state` → `parse_pr_nodes`, `real_branches`, `slice_numbers`, `count_plan_slices`; consumed by `qrspi_resolve_state.resolve` and `qrspi_resolve.py`.
**Implicit contracts:** The per-PR `merged`/`state`/`mergedAt` fields are present on every phase/slice dict (`scripts/qrspi_pr_state.py:195-204`, defaults at `:189-192`) but are documented as ADDITIVE and the resolver reads NONE of them (see Q2, Q7, Q9). The resolver only ever reads `branchExists`, `prExists`, `reviewDecision`, `unresolvedThreads`, `commentTargets`, plus implementation's `expectedSlices`/`prSummaryCommitted`/`slices`.

## Q2: How does the gather step represent a PR that has already merged versus one still open, and does that representation distinguish merged-lower PRs from open-upper slice PRs?

**Answer:** `parse_pr_nodes(nodes, bot_login)` selects ONE node via `select_pr(nodes, prefer="active")`, which is identity `nodes[0]` (newest by `CREATED_AT DESC` from the GraphQL query). It surfaces `merged`, `state` (`OPEN`/`CLOSED`/`MERGED`), and `mergedAt` on that single chosen node. A separate primitive `select_pr(nodes, prefer="merged")` picks "any MERGED node wins" — but `build_state`'s per-phase `phase_pr()` and per-slice loop both call `parse_pr_nodes` (prefer="active"), so the resolver-facing state uses the newest-PR-on-head selection, NOT the merged-preferring one. The merge-aware path (`stack_merge_state` / `is_stack_fully_merged`) exists but is consumed only by `qrspi_cleanup.py`, never by `build_state` or the resolver.

The representation does carry a `merged` boolean per phase, so the data is THERE to distinguish merged-lower from open-upper — but nothing in the resolver consults it, and `build_state` never aggregates it into a stack-level merge verdict for the resolver.

**Evidence:**

```python
def phase_pr(name):
    head = "%s/%s" % (ticket, name)
    exists = head in real
    pr = parse_pr_nodes(_query_pr(owner, repo, head), bot_login=bot) if exists else \
        parse_pr_nodes([], bot_login=bot)
    pr["branchExists"] = exists
    return pr
```

— `scripts/qrspi_pr_state.py:393-399`

```python
node = select_pr(nodes, prefer="active")   # identity nodes[0]
...
"merged": bool(node.get("merged")),
"state": node.get("state"),
"mergedAt": node.get("mergedAt"),
```

— `scripts/qrspi_pr_state.py:187,200-202`
**Dependencies:** `select_pr`, `unaddressed_reviewer_comments`, `unresolved_thread_count` (all `scripts/qrspi_pr_state.py`). `stack_merge_state`/`is_stack_fully_merged` callers: only `scripts/qrspi_cleanup.py:48-49,80,130`.
**Implicit contracts:** A phase "exists" only when its branch survives the `real_branches` trunk-ahead gate (Q7). After a merge, Graphite's `gt sync --force` prunes the merged local branch (noted at `scripts/qrspi_cleanup.py:178`), so a merged-lower phase's branch can vanish from `git branch --list` entirely — at which point `branchExists` becomes False and the `merged` field is moot because `phase_pr` returns the empty `parse_pr_nodes([])` shape.

## Q3: How does the one-shot orchestrator (qrspi_resolve.py) detect existing branches/artifacts and pass that detection into the resolver's decision?

**Answer:** `qrspi_resolve.py` derives the repo root from `__file__`, calls `build_state(...)` (which does the branch/PR gather), then `resolve(state)`. It detects WORKTREE/branch presence via `_existing_branches(ticket)` (`git branch --list <ticket>/*` → `branch_set`) feeding `pick_tip` for worktree reuse — but this branch detection is used ONLY for worktree setup, NOT passed into the resolver. The resolver's branch awareness comes entirely from `build_state`'s `real_branches` gate inside `state`. Artifact detection (`detect_existing`) probes `<worktree>/.qrspi/<ticket>/<name>.md` file sizes and is reported in the envelope's `existing{}` map but is also NOT fed into the resolver's decision — it is downstream metadata for the batch workflow.

**Evidence:**

```python
state = build_state(owner, repo, args.ticket, args.assigned, args.linear_status,
                    trunk=args.trunk, blocked_open=args.blocked_open,
                    blocked_by=blocked_by)
decision = resolve(state)
worktree = setup_worktree(args.ticket, trunk=args.trunk,
                          create_design=(decision["action"] == "run_design"))
existing = detect_existing(os.path.join(worktree, ".qrspi", args.ticket))
```

— `scripts/qrspi_resolve.py:357-363`
**Dependencies:** `build_state`, `resolve`, `branch_set`, `slice_numbers` (imported `scripts/qrspi_resolve.py:44-45`), `setup_worktree` → `pick_tip` (`:144-159`), `detect_existing` (`:130-141`).
**Implicit contracts:** The resolver decision is made from shared git refs BEFORE the worktree is provisioned (read-only ordering, `scripts/qrspi_resolve.py:352-360`). `existing{}` artifact booleans and `pick_tip` branch detection never alter the resolver's action — they only steer worktree creation and the JS phase agents. So a partially-landed stack's classification is fully determined by `build_state`'s `real_branches` + `resolve`'s entry gate, independent of artifact presence.

## Q4: What is the set of action/state values the resolver can return, and what is the signature of the function that produces them?

**Answer:** Signature: `resolve(state) -> dict` with keys `action`, `phase`, `nextPhase`, `resetToPhase`, `discardPhases`, `commentTargets`, `reason` (built by the inner `decision(action, **kw)` helper). The legal action vocabulary is the `ACTIONS` tuple: `entry_blocked`, `run_design`, `submit`, `wait`, `revise`, `respond_comment`, `advance`, `land`, `reset`. Notably there is NO distinct action for "finish landing remaining slices" (see Q5) — `land` is all-or-nothing.

**Evidence:**

```python
ACTIONS = (
    "entry_blocked", "run_design", "submit", "wait", "revise",
    "respond_comment", "advance", "land", "reset",
)
```

— `scripts/qrspi_resolve_state.py:61-71`

```python
def resolve(state):
    phases = state.get("phases", {})
    existing = [p for p in PHASES if phase_exists(phases, p)]
    def decision(action, **kw): ...
```

— `scripts/qrspi_resolve_state.py:116-131`
**Dependencies:** `PHASES = ["design","plan","implementation"]` (`:57`); JS mirror `RESOLVE_ACTIONS` in `.claude/workflows/qrspi-batch.js:112-113` must stay in sync.
**Implicit contracts:** `decision()` always emits the full key set (`scripts/qrspi_resolve_state.py:122-130`) so consumers can read any field unconditionally. The JS validates `decision.action` against `RESOLVE_ACTIONS` and rejects unknown actions (`.claude/workflows/qrspi-batch.js:150-151`).

## Q5: Which return value corresponds to "finish landing the remaining slices", and what inputs currently cause the resolver to emit it?

**Answer:** There is NO dedicated "finish landing remaining slices" return value. `land` is emitted ONLY when the implementation phase is the active phase AND complete AND every slice PR exists, has no unresolved threads, and is `APPROVED`. The decision is all-or-nothing: any not-yet-merged/not-approved slice routes elsewhere (`wait` / `submit` / `advance`). Crucially, `land` is reachable only while `active == "implementation"`, which requires the implementation phase to "exist" via `real_branches`. If lower phases (design/plan) merged and their branches were pruned, AND the slice branches were also pruned post-merge, the resolver can fall through to the entry gate instead of `land` (see Q9, Q11).

**Evidence:**

```python
if any(s.get("unresolvedThreads", 0) > 0 for s in slices): ... wait
if any(s.get("reviewDecision") != "APPROVED" for s in slices): ... wait
return decision("land", phase="implementation",
                reason="All phases approved and clean; land the whole stack bottom-up.")
```

— `scripts/qrspi_resolve_state.py:233-244`
**Dependencies:** depends on `_impl_slices`, `phase_exists("implementation")`, the completeness gate at `:217-227`.
**Implicit contracts:** `land` presumes ALL slice branches are still present locally as "real" branches AND all carry open, approved PRs. There is no handling for a stack where some lower slice PRs already merged (and were pruned) while upper slices remain open — the resolver has no concept of "resume landing from the highest unmerged slice."

## Q6: What condition produces the "No design branch and ticket is not assigned+Selected; nothing begins" entry_blocked reason, and which input fields are checked to reach it?

**Answer:** The entry gate fires when `"design" not in existing`, i.e. the design phase branch does NOT pass the `phase_exists`/`real_branches` gate (no design branch with ≥1 commit ahead of trunk). Within that branch, if `assigned` AND `linearStatus == "Selected"` it returns `run_design` (or `entry_blocked` if `blockedOpen`); OTHERWISE it returns the `entry_blocked` "nothing begins" reason. Fields checked: `phases.design.branchExists` (via `existing`), `state.assigned`, `state.linearStatus`, `state.blockedOpen`, `state.blockedBy`.

**Evidence:**

```python
if "design" not in existing:
    if state.get("assigned") and state.get("linearStatus") == "Selected":
        if state.get("blockedOpen"): ... entry_blocked (blocker)
        return decision("run_design", phase="design", reason="Entry gate satisfied ...")
    return decision("entry_blocked",
                    reason="No design branch and ticket is not assigned+Selected; nothing begins.")
```

— `scripts/qrspi_resolve_state.py:133-148`
**Dependencies:** `phase_exists` (`:78-81`) → `phases["design"]["branchExists"]`, set by `build_state` via `real_branches`.
**Implicit contracts:** The entry gate assumes "no design branch" ALWAYS means "un-started ticket." It does NOT check `merged`/`mergedAt`/`state` on the design phase, nor any sibling phase. A design phase whose branch was pruned after merging looks identical to a never-created one — this is the load-bearing conflation behind the partially-landed misclassification.

## Q7: How does the resolver determine whether a ticket has "started", and does that determination depend on the design branch/PR still being open rather than merged?

**Answer:** "Started" = `"design" in existing`, i.e. `phase_exists(phases,"design")` = `phases["design"]["branchExists"]` is truthy. `branchExists` is set by `build_state`: a phase branch counts only if it is in `real` = `real_branches(branches, ahead)`, i.e. it appears in `git branch --list <ticket>/*` AND has ≥1 commit ahead of trunk. This is entirely LOCAL-branch-presence based and is blind to merge status. So YES — it implicitly depends on the design branch still EXISTING LOCALLY (typically while its PR is open); once the design PR merges and `gt sync --force` prunes the local branch, `branchExists` flips to False and the ticket reads as "not started."

**Evidence:**

```python
def phase_exists(phases, name):
    """A phase exists once its branch exists. implementation 'exists' once any
    slice branch exists."""
    return bool(phases.get(name, {}).get("branchExists", False))
```

— `scripts/qrspi_resolve_state.py:78-81`

```python
ahead = {b: _commits_ahead(b, trunk) for b in branches}
real = real_branches(branches, ahead)
```

— `scripts/qrspi_pr_state.py:390-391`

```python
def real_branches(branches, ahead_counts):
    return {b for b in branches if ahead_counts.get(b, 0) > 0}
```

— `scripts/qrspi_pr_state.py:301-318`
**Dependencies:** `_git_branches` (`git branch --list`, `:323-326`), `_commits_ahead` (`git rev-list --count trunk..branch`, `:329-339`).
**Implicit contracts:** `real_branches` gates on LOCAL branch presence only — a merged-and-pruned branch is absent. Comment at `scripts/qrspi_cleanup.py:178` confirms `gt sync --force` prunes local branches whose PRs merged. So "started" is really "has a local, trunk-ahead phase branch right now," which a partially-landed (mid-merge) stack can fail to satisfy for the lower/design phase.

## Q8: How does the batch orchestrator consume the resolver's returned action, and which actions does it treat as terminal skips versus actionable?

**Answer:** `.claude/workflows/qrspi-batch.js` reads `r.decision.action` and switches on it. Actionable (dispatch to a worker): `run_design`→`doDesign`, `advance`→`doPlan`/`doImplementation` (by `nextPhase`), `submit`→`doSubmit`, `reset`→`doReset`, `revise`→`doRevise`, `respond_comment`→`doRespondComment`, `land`→`doLand`. Terminal SKIPS: `wait` and `entry_blocked` (and the `default` case) all fall through to `skip(t, r.decision, ...)`.

**Evidence:**

```javascript
switch (a) {
  case 'run_design': res = await doDesign(t, r); break
  case 'advance': res = r.decision.nextPhase === 'plan' ? await doPlan(t, r)
        : r.decision.nextPhase === 'implementation' ? await doImplementation(t, r)
        : skip(t, r.decision, `advance to unknown phase ${r.decision.nextPhase}`); break
  case 'submit': res = await doSubmit(t, r); break
  case 'reset': res = await doReset(t, r); break
  case 'revise': res = await doRevise(t, r); break
  case 'respond_comment': res = await doRespondComment(t, r); break
  case 'land': res = await doLand(t, r); break
  case 'wait':
  case 'entry_blocked':
  default: res = skip(t, r.decision, `Skipped (${a}): ${r.decision.reason}`)
}
```

— `.claude/workflows/qrspi-batch.js:987-1003`
**Dependencies:** `skip()` (`:266-268`), `RESOLVE_ACTIONS` validation (`:112-113,150-151`).
**Implicit contracts:** `entry_blocked` is treated as a benign skip — the ticket is left untouched with `summary = "Skipped (entry_blocked): <reason>"`. There is no special-casing to detect that an `entry_blocked` ticket might actually be a partially-landed in-flight stack; the batch trusts the resolver's verdict verbatim. This is exactly how a misclassified partially-landed stack gets stranded: the orchestrator skips it every run.

## Q9: How does the resolver behave when the design and plan PRs are merged but one or more slice PRs remain open and approved — what action does it currently return for that stack shape?

**Answer:** It depends entirely on whether the local branches survive the `real_branches` gate. Two regimes:

(a) If the merged design/plan local branches are STILL present and ≥1 commit ahead of trunk (not yet pruned), `existing` includes `design`, `plan`, and `implementation`; `active == implementation`; and if the slice completeness gate passes and all slice PRs are approved+clean it returns `land`. The resolver IGNORES that design/plan already merged (it never reads `merged`).

(b) If, mid-merge, the design (and/or plan) local branch was pruned by `gt sync --force` after its PR merged, `phases.design.branchExists` is False → `"design" not in existing` → the entry gate fires FIRST (it is the very first check, before the active-phase logic) and returns `entry_blocked` "No design branch and ticket is not assigned+Selected; nothing begins" — even though slice branches and approved open PRs still exist. The open-upper-slice state is never examined because the entry gate short-circuits.

**Evidence:**

```python
existing = [p for p in PHASES if phase_exists(phases, p)]
# 1. Entry gate — nothing exists yet.
if "design" not in existing:
    ...
    return decision("entry_blocked",
                    reason="No design branch and ticket is not assigned+Selected; nothing begins.")
```

— `scripts/qrspi_resolve_state.py:119,133-148`
**Dependencies:** entry-gate branch (`:133-148`), implementation/land branch (`:205-244`).
**Implicit contracts:** The resolver assumes phases never "disappear from below" — it has no notion that design/plan can be merged-and-gone while implementation is still in flight. The entry gate's `"design" not in existing` precondition is the single point where a partially-landed stack is misread, because design-branch absence is treated as un-started rather than already-landed.

## Q10: How does the resolver distinguish a genuinely un-started ticket (not assigned, not Selected, zero merged PRs) from a partially-landed in-flight ticket (some merged PRs, open upper slices)?

**Answer:** It does NOT distinguish them. Both collapse to the same `"design" not in existing` precondition. The entry gate checks only `assigned`, `linearStatus`, `blockedOpen`, `blockedBy` — never any merge signal (`merged`, `mergedAt`, `state`) and never slice-branch presence. A genuinely un-started ticket and a partially-landed ticket whose design branch was pruned both yield `entry_blocked` when the ticket is no longer `assigned+Selected` (e.g., Linear was moved to a review/Done-ish status, or assignment changed). The only difference in the actual world — merged lower PRs and live upper slice branches — is invisible to the entry-gate logic.

**Evidence:**

```python
if "design" not in existing:
    if state.get("assigned") and state.get("linearStatus") == "Selected":
        ...
    return decision("entry_blocked",
                    reason="No design branch and ticket is not assigned+Selected; nothing begins.")
```

— `scripts/qrspi_resolve_state.py:134-148`
**Dependencies:** `phase_exists` for design only; no reference to `slices`, `merged`, or implementation `branchExists` inside the entry gate.
**Implicit contracts:** The entry gate never inspects `phases.implementation.branchExists` or `phases.implementation.slices`. A partially-landed stack with live slice branches still satisfies `phase_exists("implementation")`, but because the entry gate runs FIRST and only on design, that signal is unreachable. NOT FOUND: any code path where the resolver consults merged-lower-PR state to override the design-absence entry gate.

## Q11: How does the resolver handle a stack mid-merge where only some lower PRs are merged and the design branch no longer exists locally/remotely?

**Answer:** It mis-handles it. `build_state` builds `phases.design` via `phase_pr("design")`, which sets `branchExists = ("RUS-x/design" in real)`. Once the design branch is pruned (post-merge `gt sync --force`), it is absent from `git branch --list`, so `real` excludes it and `branchExists=False`. `resolve` then hits `"design" not in existing` and returns `entry_blocked` (when not `assigned+Selected`) or `run_design` (when still `assigned+Selected`) — `run_design` would attempt to RE-create a design branch for an already-landed design phase. Neither path advances the open, approved upper slices toward landing. The merge-aware machinery that COULD detect this (`stack_merge_state`, `is_stack_fully_merged`, `select_pr(prefer="merged")`) is present in `qrspi_pr_state.py` but is wired ONLY into `qrspi_cleanup.py`'s reaper, not into `build_state`'s resolver-facing output.

**Evidence:**

```python
# build_state: design phase existence is pure local-branch presence
def phase_pr(name):
    head = "%s/%s" % (ticket, name)
    exists = head in real     # 'real' = trunk-ahead LOCAL branches only
    ...
```

— `scripts/qrspi_pr_state.py:393-396`

```
# gt sync --force prunes local branches whose PRs have merged and their remote ...
```

— `scripts/qrspi_cleanup.py:178` (comment confirming post-merge local pruning)
**Dependencies:** `real_branches`/`_commits_ahead` (local only), `_query_pr` (per-head GraphQL). The merged-state aggregation `stack_merge_state` is NOT called by `build_state`.
**Implicit contracts:** `build_state` never re-queries a pruned design head ref to learn it merged; absence is absence. The resolver has no "the design phase merged already, so don't re-gate on it" branch. This is the structural gap producing the RUS-69 symptom (resolver mis-classifies partially-landed stacks as `entry_blocked`).

## Q12: What existing resolver unit tests cover stack shapes, and is there any test fixture representing merged-lower / open-upper PRs?

**Answer:** `scripts/qrspi_resolve_state_test.py` covers entry-gate (assigned/Selected/blocked), submit, wait, revise, advance (plan/impl), the implementation completeness gate, the land path, reset/revise precedence, and respond_comment precedence (RUS-54). NONE of the resolver test fixtures model a MERGED PR — `_phase()` and `_slice()` only ever set `prExists`, `reviewDecision`, `unresolvedThreads`, `commentTargets`; there is no `merged` field and no fixture where design/plan are merged-and-gone while slices remain open. The merged-vs-open distinction is tested ONLY in `scripts/qrspi_pr_state_test.py` (against `select_pr`/`stack_merge_state`/`is_stack_fully_merged`), which never flows into a `resolve()` assertion.

**Evidence:**

```python
def _phase(branch=True, pr=True, decision="REVIEW_REQUIRED", threads=0, comments=None):
    return {"branchExists": branch, "prExists": pr,
            "reviewDecision": decision, "unresolvedThreads": threads,
            "commentTargets": comments or []}
def _slice(n, pr=True, decision="REVIEW_REQUIRED", threads=0, comments=None):
    return {"n": n, "prExists": pr, "reviewDecision": decision,
            "unresolvedThreads": threads, "commentTargets": comments or []}
```

— `scripts/qrspi_resolve_state_test.py:14-18,29-31`
**Dependencies:** `resolve` under test; fixtures `_phase`, `_impl`, `_slice`, `state`.
**Implicit contracts:** Resolver fixtures omit `merged` entirely, mirroring the resolver's blindness to it — so no existing resolver test can catch the partially-landed misclassification. NOT FOUND: any resolver test case with a merged-lower / open-upper stack shape, or any test asserting `resolve()` does NOT return `entry_blocked` for a started-but-design-pruned ticket.

## Q13: How do existing resolver tests construct PR-state input fixtures (merged vs open, approved vs not), and what helper or data structure builds them?

**Answer:** Builders are local module functions in `scripts/qrspi_resolve_state_test.py`: `_phase(...)` (design/plan PR dict), `_slice(n, ...)` (one slice PR dict), `_impl(slices, expected, pr_summary)` (implementation wrapper), `_ct(cid)` (a minimal CommentTarget), and `state(assigned, linear, phases, blockedOpen, blockedBy)` (top-level envelope). "Approved vs not" is set via the `decision=` kwarg (`"APPROVED"` / `"REVIEW_REQUIRED"` / `"CHANGES_REQUESTED"` / `None`). "Merged vs open" is NOT representable — no builder accepts a `merged` argument. Cases are registered via `case(name, st, expect)` into `CASES` and asserted in `run()` (supports the `_reasonContains` substring key).

**Evidence:**

```python
def _impl(slices, expected=None, pr_summary=True):
    return {"branchExists": bool(slices), "slices": slices,
            "expectedSlices": len(slices) if expected is None else expected,
            "prSummaryCommitted": pr_summary}

def state(assigned=True, linear="Selected", phases=None, blockedOpen=False, blockedBy=None):
    return {"ticketId": "RUS-1", "assigned": assigned, "linearStatus": linear,
            "blockedOpen": blockedOpen, "blockedBy": list(blockedBy or []),
            "phases": phases or {}}
```

— `scripts/qrspi_resolve_state_test.py:20-27,41-45`
**Dependencies:** `case`/`CASES`/`run` harness (`:55-58,291-317`); `contains` substring helper (`:48-53`).
**Implicit contracts:** A new merged-aware test would need to extend `_phase`/`_slice` (or `state`) with a `merged`/merge-signal field, since none exists today. The fixture vocabulary deliberately mirrors the resolver's input keys — extending the resolver to read merge state would require extending these builders in lockstep.

## Q14: What diagnostic reason strings does the resolver attach to each returned action, and how are entry_blocked reasons surfaced in the batch run output?

**Answer:** Every decision carries a human-readable `reason`. Key strings: entry_blocked = "No design branch and ticket is not assigned+Selected; nothing begins." (`:147-148`) or the blocker variant naming each open blocker (`:142-144`); run_design = "Entry gate satisfied (assigned + Selected); no design branch yet." (`:145-146`); submit, wait (threads / awaiting-review variants), advance, land, reset, revise, respond_comment each have a templated reason. In the batch, the reason is logged at dispatch (`log("  ${t.id}: decision=${a} — ${r.decision.reason}")`) and, for `entry_blocked`/`wait`, embedded in the skip summary `Skipped (${a}): ${r.decision.reason}` which becomes `results[].summary`.

**Evidence:**

```python
return decision("entry_blocked",
                reason="No design branch and ticket is not assigned+Selected; nothing begins.")
```

— `scripts/qrspi_resolve_state.py:147-148`

```javascript
log(`  ${t.id}: decision=${a} — ${r.decision.reason}`)
...
default: res = skip(t, r.decision, `Skipped (${a}): ${r.decision.reason}`)
```

— `.claude/workflows/qrspi-batch.js:985,1002`
**Dependencies:** `decision()` reason kwarg (`scripts/qrspi_resolve_state.py:129`); `skip()` → `summary` (`.claude/workflows/qrspi-batch.js:266-268`); final `return { ... results }` (`:1019`).
**Implicit contracts:** The reason string is the ONLY diagnostic surfaced for a skipped ticket — there is no structured field flagging "this entry_blocked might be a stranded partially-landed stack." An operator reading the batch output sees a plausible-but-wrong "nothing begins" message for a stranded in-flight stack, which masks the bug.

---

## Discovered Patterns

- **Pure-logic / I/O split is consistent.** Decision logic (`resolve`) and all parsers (`parse_pr_nodes`, `select_pr`, `stack_merge_state`, `unaddressed_reviewer_comments`, `real_branches`, `count_plan_slices`) are pure and unit-tested; subprocess/`gh`/`git` calls are isolated in clearly-labeled "(not unit-tested)" sections (`scripts/qrspi_pr_state.py:321-377`, `scripts/qrspi_resolve.py:229-324`).
- **`decision()` always emits a fixed key set** (`action`/`phase`/`nextPhase`/`resetToPhase`/`discardPhases`/`commentTargets`/`reason`) so consumers read fields unconditionally (`scripts/qrspi_resolve_state.py:121-131`).
- **Branch "existence" everywhere means trunk-ahead LOCAL presence** via `real_branches` — the harness has no concept of a remembered/merged-and-pruned phase. `pick_tip` (worktree reuse) deliberately uses plain presence instead, and comments call out the difference (`scripts/qrspi_resolve.py:148-151`).
- **Merge-awareness is fully built but siloed.** `select_pr(prefer="merged")`, `stack_merge_state`, `is_stack_fully_merged`, and the per-PR `merged`/`state`/`mergedAt` fields exist and are tested, but their ONLY consumer is the cleanup reaper (`scripts/qrspi_cleanup.py`). The RUS-53 "index-0 bug" fix (a newer non-merged PR masking an earlier MERGED one) was applied to `select_pr`/`stack_merge_state` for cleanup, but `build_state`'s resolver-facing path still uses `prefer="active"` (newest-PR identity) and never aggregates a stack-level merge verdict.
- **JS action vocabulary mirrors the Python `ACTIONS` tuple** and is validated (`RESOLVE_ACTIONS`, `.claude/workflows/qrspi-batch.js:112-113,150-151`); any new resolver action requires a matched JS update.

## Inconsistencies

- **The `merged` field is gathered but unused by the resolver.** `parse_pr_nodes` surfaces `merged`/`state`/`mergedAt` on every phase/slice dict (`scripts/qrspi_pr_state.py:195-204`) and the module docstring calls them "ADDITIVE" — but `qrspi_resolve_state.resolve` reads none of them. The data needed to distinguish merged-lower from open-upper is present in the state envelope yet structurally ignored by the decision logic. This is the direct mismatch underlying the partially-landed misclassification.
- **Entry-gate comment vs reality.** The entry gate is commented "Entry gate — nothing exists yet" (`scripts/qrspi_resolve_state.py:133`) and its reason says "nothing begins," but the precondition is merely `"design" not in existing`, which is ALSO true for a started ticket whose design branch was merged-and-pruned. The comment asserts un-started; the condition does not guarantee it.
- **`run_design` reason vs a merged design.** When a design-pruned-but-still-`assigned+Selected` ticket hits the entry gate, it returns `run_design` ("no design branch yet") — which would re-create design for an already-landed phase. The reason string asserts a fresh start that is not necessarily true.
- **Cross-module merge-detection asymmetry.** `qrspi_cleanup.py` correctly re-queries pruned/absent head refs and maps them to a documented sentinel (`stack_merge_state`, `scripts/qrspi_pr_state.py:231-236`; tested at `scripts/qrspi_pr_state_test.py:243-251`), so the reaper survives deleted head refs. `build_state` does the OPPOSITE: a pruned design head ref silently becomes `branchExists=False` with no merge re-query, so the resolver loses the information the reaper preserves. Two modules consuming the same GraphQL shape treat a deleted-merged head ref in contradictory ways.
- **Resolver tests cannot exercise merge state.** `qrspi_resolve_state_test.py` fixtures (`_phase`/`_slice`/`state`) have no `merged` dimension (`:14-45`), while `qrspi_pr_state_test.py` tests merge selection thoroughly (`:84-260`) — the two test suites disagree on whether merge state is part of the resolver's contract.
