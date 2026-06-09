---
name: qrspi-work
description: "Single entry point for autonomous QRSPI feature development. Use when the user asks to 'work on' a ticket (e.g., 'work on RUS-42'). Reads PR review state to determine the current phase and executes the appropriate action — design, plan, implementation, or review response — without manual phase-by-phase invocation. Trigger on any variant of: 'work on <ticket-id>', 'continue <ticket-id>', 'pick up <ticket-id>', or any reference to progressing a QRSPI ticket through its lifecycle."
command: /qrspi-work
argument-hint: <ticket-id>
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, mcp__linear__get_issue, mcp__linear__save_issue, mcp__linear__list_issue_statuses, mcp__linear__save_comment
---

# QRSPI Work Orchestrator (PR-gated)

You are a state machine, but **PR review state — not Linear status — is the authority**
for what to do next. Linear plays exactly two roles:

1. **Entry control:** a ticket may only *begin* if it is assigned to a user and in the
   `Selected` status. Nothing starts otherwise.
2. **Reporting projection:** once work has started, you update Linear status to reflect
   the active phase. These writes are **best-effort** — a failed Linear update logs a
   warning and never blocks git/PR work.

What is "ready to advance" is decided **wholly by PR status**:
`reviewDecision == APPROVED` **and** zero unresolved review threads. You do not read
Linear (after the entry gate) to make any advancement decision.

See `docs/qrspi-pr-gated-lifecycle-design.md` for the full design and rationale.

## Lifecycle at a glance

A single Graphite stack per ticket, built bottom-up and **held open** until the whole
feature is approved, then landed bottom-up:

```
trunk
 └── <id>/design   Design PR   — questions.md, research.md, design.md
      └── <id>/plan  Plan PR    — structure.md, plan.md, worktree.md   (stacked on design)
           └── <id>/slice-1..N   slice PRs — code                       (stacked on plan)
```

- Approving a phase PR **auto-advances**: the next phase is built stacked on top.
- A formal **CHANGES_REQUESTED** on an upstream phase PR **resets**: all downstream
  phases are discarded (PRs closed, branches deleted, stale artifacts removed) and the
  ticket returns to that phase for revision. Discard is **automatic**.
- Addressing a formal **CHANGES_REQUESTED** on a frontier phase PR (revise) is
  **autonomous**: the feedback is addressed in place, the phase commit is amended, and
  review is re-requested (which clears the change request). Review *threads* cannot be
  resolved here (every gh PR-write mutation 403s on this cross-owned repo), so a PR carrying
  unresolved threads but **no** change request is left for the reviewer and routes to
  `wait`, not revise.
- Nothing merges until **every** PR in the stack is approved + clean; then the whole
  stack lands bottom-up.

---

## Entry Point

1. Parse `$ARGUMENTS` to extract `<ticket-id>`.
2. **Fetch the ticket fresh** with `mcp__linear__get_issue` (identifier
   `<ticket-id>`). On failure, retry **once**; if the retry fails, this is a **hard stop**
   — print the exact error and exit.
   - Read `status` (name) and `assignee` (`assigned` = assignee is non-null).
3. **Resolve everything in ONE deterministic command.** Worktree setup, GitHub
   `OWNER/REPO`, the PR-state gather, the tested decision, and artifact detection are all
   folded into a single script (`scripts/qrspi_resolve.py`). Run it verbatim — do **not**
   hand-derive paths, repo names, or the decision:
   ```bash
   python3 scripts/qrspi_resolve.py --ticket "<ticket-id>" \
     $( [ "<assigned>" = "true" ] && echo --assigned ) \
     --linear-status "<status>"
   ```
   It self-locates the repo root from its own location, so it works from any cwd, and it
   creates **nothing** unless the decision is `run_design`. It prints one JSON envelope:
   ```json
   { "ok": true, "repoRoot": "…", "worktreeDir": "…",
     "existing": { "questions": false, … },
     "decision": { "action": "…", "phase": null, "nextPhase": null,
                   "resetToPhase": null, "discardPhases": [], "reason": "…" } }
   ```
   Set `REPO_ROOT` and `WORKTREE_PATH` from `repoRoot`/`worktreeDir`. If `ok` is `false`,
   that is a **hard stop** — print the verbatim `error` and exit. Never retry it with an
   alternative command or improvised path. (The [Worktree Setup](#worktree-setup) section
   below documents what the script does internally, for reference.)
4. **Print the decision** (`action` + `reason`) so the operator can observe.
5. Dispatch on `action`:

| `action` | Handler |
|---|---|
| `entry_blocked` | → [Entry Blocked](#action-entry_blocked) |
| `run_design` | → [Run Design](#action-run_design) |
| `advance` | → [Advance](#action-advance) (build `nextPhase`) |
| `submit` | → [Submit](#action-submit) (finish/submit `phase`) |
| `wait` | → [Wait](#action-wait) |
| `revise` | → [Revise](#action-revise) (address feedback on `phase`) |
| `reset` | → [Reset](#action-reset) (discard `discardPhases`, return to `resetToPhase`) |
| `land` | → [Land](#action-land) |

If the resolver errors (bad state, gh/git failure), treat it as a **hard stop** —
print the error and exit. Never guess the action.

---

## Worktree Setup

Every ticket gets its own git worktree at `.worktrees/<ticket-id>/` (relative to
`REPO_ROOT`). Multiple agents can work different tickets concurrently.

**Set `WORKTREE_PATH`** = `<REPO_ROOT>/.worktrees/<ticket-id>`.

The worktree should be checked out to the **highest existing phase branch** for the
ticket (the stack tip): a slice branch if any exist, else `<id>/plan`, else `<id>/design`.
For a brand-new ticket no branch exists yet — `run_design` creates `<id>/design`.

```bash
mkdir -p "$REPO_ROOT/.worktrees"
if [ -d "$WORKTREE_PATH" ]; then
  cd "$WORKTREE_PATH"          # reuse
else
  # Pick the tip branch if one exists, newest phase first.
  tip=$(git -C "$REPO_ROOT" branch --list '<ticket-id>/*' \
        | sed 's/[* ]//g' | sort -t- -k2 -n | tail -1)
  if [ -n "$tip" ]; then
    git -C "$REPO_ROOT" worktree add "$WORKTREE_PATH" "$tip"
    cd "$WORKTREE_PATH"
  fi
  # else: no branch yet — run_design will create the worktree+branch.
fi
```

If `git worktree add` fails because the path is broken, see
[Stale worktree recovery](#stale-worktree-recovery).

**CRITICAL — sub-agents do NOT inherit your cwd.** The Agent tool starts a fresh Bash
session at the main repo root. Every sub-agent prompt must include (1) `cd <WORKTREE_PATH>`
as its first Bash command and (2) absolute, `<WORKTREE_PATH>/`-prefixed paths for ALL file
operations. Never pass relative `.qrspi/...` paths to a sub-agent.

---

## action: entry_blocked

The ticket has no `<id>/design` branch and is not assigned + `Selected`.

Print: "Ticket `<ticket-id>` is not ready to start — it must be assigned to a user and in
the `Selected` status. Current: assignee=`<…>`, status=`<…>`. Nothing started." Then exit.

---

## action: run_design

Build the **design** phase: questions → research → design on a fresh `<id>/design`
branch off trunk, then submit the Design PR.

### Create the branch (if needed)

If the worktree/branch doesn't exist yet:
```bash
mkdir -p "$REPO_ROOT/.worktrees"
git -C "$REPO_ROOT" worktree add -b <ticket-id>/design "$WORKTREE_PATH" main
cd "$WORKTREE_PATH"
gt track --parent main --no-interactive
```
Save the ticket title + description from the Linear fetch — you pass it to some agents below.

### Phases (spawn one sub-agent each; see [Phase Agent Contracts](#phase-agent-contracts))

1. **Questions** — `subagent_type: qrspi-questions`. Verify `questions.md` non-empty.
2. **Research** — `subagent_type: qrspi-research`. **Research firewall: do NOT pass ticket
   content.** Verify `research.md` non-empty.
3. **Design** — `subagent_type: qrspi-design`. Verify `design.md` non-empty.

### Commit + submit

Single commit on the design branch (Graphite single-commit-per-branch convention). Worktree
setup already created the `<id>/design` branch with `git worktree add -b`, so it exists with
**no commit yet** — use `gt modify -c` to add the first commit. (Do NOT use `gt create`: the
branch already exists, so `gt create` fails.)
```bash
git add .qrspi/<ticket-id>/questions.md .qrspi/<ticket-id>/research.md .qrspi/<ticket-id>/design.md
gt modify -c --no-interactive -m "$(cat <<'EOF'
<ticket-id> [QR]: Design — <ticket-title>

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"     # first run adds the single commit; on resume it amends the same commit
```
Then submit as a **published** PR — review gates need a reviewable (non-draft) PR, and
`gt submit` defaults to draft in non-interactive mode. Clear any stale closed-PR association
FIRST (see [Resubmitting](#resubmitting-when-the-prior-pr-was-closed-or-merged)):
```bash
python3 <repo-root>/scripts/qrspi_clear_stale_pr.py --ticket <id>
gt submit --publish --no-edit --no-interactive
```
Capture the PR URL. **Project Linear** → `Design Review` (best-effort; see
[Linear projection](#linear-projection)). Print: "Design submitted. PR: `<url>`. → Design Review."

---

## action: advance

The active phase PR is approved + clean. Build `nextPhase`, stacked on the active phase.

### nextPhase == plan  (design was approved)

```bash
gt checkout <ticket-id>/design --no-interactive
git branch --show-current | grep -q '<ticket-id>/design'   # sanity
```
Spawn, in order (see contracts): **Structure** (`qrspi-structure`), **Plan** (`qrspi-plan`),
**Work Tree** (`qrspi-worktree`). Verify each artifact non-empty. Then create the plan branch
**stacked on design** and submit:
```bash
git add .qrspi/<ticket-id>/structure.md .qrspi/<ticket-id>/plan.md .qrspi/<ticket-id>/worktree.md
gt create <ticket-id>/plan --no-interactive -m "$(cat <<'EOF'
<ticket-id> [SP]: Plan — <ticket-title>

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
gt submit --publish --no-edit --no-interactive
```
**Project Linear** → `Plan Review`. Print: "Plan submitted. PR: `<url>`. → Plan Review."

### nextPhase == implementation  (plan was approved)

Build the slice stack on top of `<id>/plan`. Read `structure.md` to count slices and
extract each slice's goal; read `plan.md` and `worktree.md`.

For each slice N (1..total), parent = `<id>/plan` for slice 1 else `<id>/slice-<N-1>`:
```bash
gt checkout <parent-branch> --no-interactive
```
Spawn the implement agent (`qrspi-implement`; append the
[project-scope block](#project-scope-firewall-implement)) with the slice-scoped
`STRUCTURE_SLICE` / `PLAN_SLICE` / `WORKTREE_SESSION` / `PREVIOUS_NOTES`. After it returns,
stage EVERY changed/untracked file **except generated caches** (`__pycache__/`, `*.pyc`) —
see [Staging](#staging) — and create the slice branch (`<total>` = the slice count from
structure.md):
```bash
git status --short
git add <every file shown, but NOT __pycache__/ or *.pyc>
gt create <ticket-id>/slice-<N> --no-interactive -m "$(cat <<'EOF'
<ticket-id> [I] <N>/<total>: <goal>

Part <N>/<total> of <ticket-id>. See the slice-1 PR for the full feature summary.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```
The slice commit **message body is the PR description** — Graphite seeds each PR's body
from its branch commit message when it *creates* the PR (this is also how the design/plan
PRs get their bodies). So every slice from 2..N gets the focused "Part N/total" body above
at creation; slice 1 gets the full `pr-summary.md` (next paragraph). **Do not** set PR
bodies with `gh pr edit` — the gh PAT cannot write PRs on this repo (see
[Why bodies are authored at creation](#why-pr-bodies-are-authored-at-graphite-creation)).

After all slices: spawn `qrspi-pr` to produce `pr-summary.md`, amend it into the **last**
slice commit as the durable artifact
(`git add .qrspi/<ticket-id>/pr-summary.md && gt modify --no-interactive`). Then splice
`pr-summary.md` into the **slice-1** commit *message* (so the slice-1 PR body is the full
summary at creation) with the deterministic, self-locating helper — never hand-build this:
```bash
python3 scripts/qrspi_pr_body.py --ticket <ticket-id> --slice 1 \
  --body-file .qrspi/<ticket-id>/pr-summary.md
```
It preserves the slice-1 commit subject + trailer, splices the summary in between, amends
via `gt modify -m` (auto-restacking the slices above), and prints
`{ ok, branch, subject, bytes, error? }`. If it reports `ok:false`, HARD STOP — do not
improvise a `gh`/`gt` alternative. Then submit the whole stack (bodies are already in the
commit messages, so `--no-edit` keeps them):
```bash
gt submit --publish --stack --no-edit --no-interactive
```
**Project Linear** → `Code Review`. Print: "Implementation submitted: `<N>` slice PRs. → Code Review."

> Resumability: skip any slice whose branch already exists with code committed.

---

## action: submit

A phase branch exists but its PR was never opened (e.g. a crashed prior run). Ensure the
phase's artifacts are present and non-empty; if any are missing, finish them by spawning
the remaining phase agents (same as `run_design`/`advance`). This path **creates** the PR,
so for implementation seed the slice-1 body into its commit message first (the PR body is
authored at creation — see [Why PR bodies are authored at Graphite creation](#why-pr-bodies-are-authored-at-graphite-creation)):
```bash
# implementation only: splice pr-summary into the slice-1 commit message before submit
python3 scripts/qrspi_pr_body.py --ticket <ticket-id> --slice 1 \
  --body-file .qrspi/<ticket-id>/pr-summary.md
gt submit --publish --no-edit --no-interactive   # add `--stack` if the active phase is implementation
```
Project the matching Linear status. If artifacts are missing **and** cannot be produced,
hard-stop with the error — never fabricate.

---

## action: wait

The active phase PR exists but cannot be advanced autonomously. Either it is **awaiting
review** (not yet approved, no change request), or it carries **unresolved review threads
but no formal change request**. Threads cannot be resolved here — every authenticated gh
PR-write mutation 403s on this cross-owned repo — so a thread-only PR is left for the
reviewer to resolve rather than looped through revise (which could never clear the thread
gate). Advancement waits on the human reviewer.

Print: "`<ticket-id>` `<phase>` PR is awaiting review (`<reviewDecision>`)`<, N unresolved
thread(s) left for the reviewer>`. Nothing to do until it is approved. Re-run
`work on <ticket-id>` after review." Then exit.

---

## action: revise

The frontier phase PR carries a formal **CHANGES_REQUESTED**. This is now **autonomous**:
address the feedback **within this phase only** — the cascade is bounded to the phase's own
artifacts (see `references/review-cascade.md`). Do NOT touch downstream phases here; a
design-level change that invalidates plan/impl is handled by `reset`, not revise.

> The resolver emits `revise` **only** for a CHANGES_REQUESTED frontier PR, never for
> threads alone — re-requesting review clears the change request (the loop-safe termination
> signal), whereas threads cannot be cleared here, so a thread-only PR routes to `wait`.

1. Ensure you're on the phase branch:
   ```bash
   gt checkout <ticket-id>/<phase> --no-interactive    # for implementation, the affected slice branch(es), lowest first
   ```
2. Read the change request — these are **read-only queries** (writes 403; see below):
   ```bash
   gh pr view <number> --json reviews,comments --jq '.reviews[] | select(.state == "CHANGES_REQUESTED")'
   gh api graphql -f query='query($o:String!,$r:String!,$n:Int!){repository(owner:$o,name:$r){pullRequest(number:$n){reviewThreads(first:100){nodes{isResolved comments(first:20){nodes{path body}}}}}}}' \
     -F o="$OWNER" -F r="$REPO" -F n=<number> --jq '.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved==false)'
   ```
3. Address the feedback (edit artifacts/code, cascading within the phase from the earliest
   affected artifact). For implementation, group comments by slice and start from the
   lowest-numbered affected slice (changes restack upward).
4. Amend the phase commit **in place, keeping its existing subject** (`<id> [QR]: Design — <ticket-title>`,
   `<id> [SP]: Plan — <ticket-title>`, or `<id> [I] <N>/<total>: <goal>` for a slice). Single-commit-per-branch means
   there is only the one phase commit — do NOT rename it to an "Address feedback" subject:
   ```bash
   git add <changed files>
   gt modify --no-interactive -m "$(cat <<'EOF'
   <the branch's existing commit subject, verbatim — e.g. `<id> [QR]: Design — <ticket-title>`, `<id> [SP]: Plan — <ticket-title>`, or `<id> [I] <N>/<total>: <goal>`>

   Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
   EOF
   )"
   ```
5. **Re-request review** so the stale `CHANGES_REQUESTED` is cleared (this is what lets the
   next pass return `wait` rather than re-firing revise):
   ```bash
   gt submit --publish --no-edit --rerequest-review --no-interactive  # --stack if implementation
   ```
6. **Do NOT resolve or reply to review threads, and do NOT run any `gh pr`/GraphQL
   mutation.** Every authenticated gh PR write 403s here (the bot's fine-grained PAT cannot
   write a repo owned by a *different* user — see the gh-cross-account note). Thread
   resolution is the reviewer's job; leave threads as-is. Re-requesting review (via
   Graphite's write-capable App credential) flips `reviewDecision` back to
   `REVIEW_REQUIRED`; the reviewer must still re-review to approve. Print which
   artifacts/files changed.

---

## action: reset

A formal `CHANGES_REQUESTED` landed on an **upstream** phase PR (`resetToPhase`), so every
downstream phase in `discardPhases` is now derived from a superseded upstream and must be
**discarded automatically** (decision 10 in the design doc). Nothing is merged, so this never
rewrites trunk — it is bounded to ticket-local branches and artifacts.

For each phase in `discardPhases` (highest first — slices before plan):
1. Close its PR(s) and delete its branch(es):
   ```bash
   # implementation: every slice branch, tip-down
   gt delete <ticket-id>/slice-<k> --force --close --no-interactive
   # plan:
   gt delete <ticket-id>/plan --force --close --no-interactive
   ```
2. Ensure the stale downstream artifacts are gone from the worktree working tree, so the
   skip-if-exists resume logic does not treat them as done:
   ```bash
   gt checkout <ticket-id>/<resetToPhase> --no-interactive
   # plan-half artifacts removed when discarding plan:
   rm -f .qrspi/<ticket-id>/structure.md .qrspi/<ticket-id>/plan.md .qrspi/<ticket-id>/worktree.md
   git clean -fd .qrspi/<ticket-id>/    # drop any untracked downstream leftovers
   ```
   (Deleting the branch already removes committed artifacts; this guards untracked remnants.)

Then **project Linear** → `<resetToPhase>` review status (e.g. `Design Review`) and print:
"Reset `<ticket-id>` to `<resetToPhase>`: discarded `<discardPhases>` after an upstream
change request. Address the `<resetToPhase>` feedback (revise) and the stack will rebuild on
re-approval." Stop — addressing the feedback itself is the manual `revise` path on a
subsequent invocation.

---

## action: land

Every PR in the stack is approved + clean. Land the whole stack bottom-up and finalize.

1. Confirm the stack is current and approved (the resolver already gated this), then land
   from the bottom up:
   ```bash
   gt checkout <ticket-id>/slice-1 --no-interactive   # or <id>/design if no slices/plan-only feature
   gt submit --publish --stack --no-edit --no-interactive   # ensure remotes current
   gt merge --no-interactive                           # merges bottom-up (NOT --confirm: it forces a prompt that --no-interactive cannot satisfy)
   ```
2. Reap the worktree, local branches, and remote refs with the deterministic, tested
   cleanup script — **do NOT** hand-run `gt sync --force` or `git worktree remove --force`
   here. The script self-locates `REPO_ROOT` from its own path, so run it from the **main
   checkout** (never from inside the worktree) so it sees the real `.worktrees/<ticket-id>`:
   ```bash
   cd "$REPO_ROOT"
   python3 scripts/qrspi_cleanup.py --ticket <ticket-id>
   ```
   It computes a classifier verdict (`blocked` > `destroy` > `skip`) and reaps **only** a
   fully-merged clean stack: it removes the worktree, deletes the merged local branches, and
   prunes their remote refs, printing one JSON envelope
   `{ ok, decision, reason, removed{worktree,branches[],remotes[]}, dryRun, error? }`. A dirty
   worktree comes back `decision:"blocked"` (left for a human, never forced); an infra error
   is `ok:false` (HARD STOP — do not retry or improvise). Pass `--dry-run` first to preview
   without destroying anything.
3. Remove planning artifacts from `main` (they were only needed during review) — open a
   small cleanup PR if `.qrspi/<ticket-id>/` survived the merge, mirroring the old Cleanup
   flow; otherwise skip.
4. **Project Linear** → `Done`. Print: "`<ticket-id>` landed and cleaned up. → Done."

---

## Linear projection

After the entry gate, Linear status is a **best-effort reporting projection**, never a gate.
The `*Approved` states are **dropped** — approval lives in the PR. Mapping:

| Active phase / event | Linear status to project |
|---|---|
| Design PR open / in review | `Design Review` |
| Plan PR open / in review | `Plan Review` |
| Implementation stack open / in review | `Code Review` |
| Reset to design / plan | `Design Review` / `Plan Review` |
| Stack landed | `Done` |

To project a status:
```
Call mcp__linear__save_issue with id "<ticket-id>" and state "<name>".
```
**Best-effort rule:** if the Linear write fails, print a one-line warning
(`WARN: Linear projection to <state> failed: <error>`) and **continue** — never hard-stop
or roll back git/PR work because of a Linear write. (To confirm a status after writing, read
it back with `get_issue` and check `status`; do NOT use `get_issue_status`, which takes a
WorkflowState ID, not a ticket ID.)

---

## Phase Agent Contracts

The orchestrator dispatches each phase to a purpose-built agent in
`.claude/agents/qrspi-<phase>.md` via the `Agent` tool (`subagent_type: qrspi-<phase>`,
`mode: "auto"`). It does NOT hand-engineer prompts — it passes a labelled input contract
with absolute `<WORKTREE_PATH>/`-prefixed paths. After each agent returns, verify the output
artifact exists and is non-empty; on failure, print the error and STOP (no Linear write).

| Phase | subagent_type | Inputs (all paths `<WORKTREE_PATH>/`-prefixed) |
|---|---|---|
| Questions | `qrspi-questions` | TICKET_ID, TICKET_CONTENT, ARTIFACT_PATH=…/questions.md, TEMPLATE_PATH=…/templates/questions.md |
| Research | `qrspi-research` | TICKET_ID, QUESTIONS_PATH, RESEARCH_PATH, TEMPLATE_PATH, REPO_ROOT=`<WORKTREE_PATH>` **(NO ticket content)** + scope block |
| Design | `qrspi-design` | TICKET_ID, TICKET_CONTENT, QUESTIONS_PATH, RESEARCH_PATH, DESIGN_PATH, TEMPLATE_PATH |
| Structure | `qrspi-structure` | TICKET_ID, DESIGN_PATH, STRUCTURE_PATH, TEMPLATE_PATH |
| Plan | `qrspi-plan` | TICKET_ID, STRUCTURE_PATH, DESIGN_PATH, PLAN_PATH, TEMPLATE_PATH |
| Work Tree | `qrspi-worktree` | TICKET_ID, PLAN_PATH, WORKTREE_PATH=…/worktree.md, TEMPLATE_PATH |
| Implement | `qrspi-implement` | TICKET_ID, SLICE_NUMBER, WORKTREE_DIR, STRUCTURE_SLICE, PLAN_SLICE, WORKTREE_SESSION, PREVIOUS_NOTES, IMPL_LOG_PATH, IMPL_LOG_TEMPLATE_PATH + scope block |
| PR summary | `qrspi-pr` | TICKET_ID, IMPL_LOG_PATH, DESIGN_PATH, STRUCTURE_PATH, PR_SUMMARY_PATH, TEMPLATE_PATH, REPO_ROOT |

### Research firewall

The research agent's tool definition includes no Linear MCP and forbids reading the ticket.
The orchestrator must ALSO omit `TICKET_CONTENT` from the research contract — only
`QUESTIONS_PATH`, `RESEARCH_PATH`, `TEMPLATE_PATH`, `REPO_ROOT`. Defense in depth.

### Project scope firewall (research)

Append this block to every research agent prompt; replace `REPO_ROOT_VALUE` with the actual
`REPO_ROOT` (the worktree path):

```
## Project scope restriction

You are researching the codebase for a specific ticket. ALL file reads must be inside the project repository at REPO_ROOT_VALUE/.

BEFORE reading ANY file, validate its path starts with REPO_ROOT_VALUE/. If it does not, skip it and note the gap.

DO NOT read:
- ~/.claude/, ~/.config/, ~/ (home directory)
- System config files (/etc/, /usr/, /var/)
- Files in any other project's directories
- Global skill definitions outside the repo
- Any path that does not start with REPO_ROOT_VALUE/

This is a hard boundary. If the questions imply information that may live outside the repo, note it as an unanswerable gap rather than escaping the project.
```

### Questions firewall

The questions agent excludes `Glob`, `Grep`, and `Bash` so codebase exploration is
structurally impossible. No special orchestrator handling required.

### Project scope firewall (implement)

Append this block to every implement agent prompt; replace `WORKTREE_DIR_VALUE` with the
actual `WORKTREE_DIR`:

```
## Project scope restriction

You are implementing work for a ticket. ALL file reads and modifications must be inside the project repository at WORKTREE_DIR_VALUE/.

BEFORE reading or writing ANY file, validate its path starts with WORKTREE_DIR_VALUE/. If it does not, skip it and report the error.

DO NOT modify:
- ~/.claude/, ~/.config/, ~/ (home directory)
- System config files (/etc/, /usr/, /var/)
- Global skill definitions in ~/.claude/skills/
- Any path that does not start with WORKTREE_DIR_VALUE/

The plan may contain paths like `~/.claude/skills/...`. If the plan targets global scope, refuse to make those changes and report the issue. The deliverable for a ticket must live within the project repo.

This is a hard boundary. If the plan references files outside the project, report the error and STOP.
```

---

## Git/Graphite Rules

- All `gt` commands include `--no-interactive`.
- All commit messages use heredoc format and include the co-authorship trailer.
- The orchestrator is the ONLY place git/graphite operations happen — sub-agents never commit.
- **One commit per phase branch** (Graphite convention): `gt create` opens the branch with
  its commit; re-running within the same phase amends with `gt modify` (no `-c`). Commit
  subjects: `<id> [QR]: Design — <ticket-title>`, `<id> [SP]: Plan — <ticket-title>`, `<id> [I] <N>/<total>: <goal>` (slices, e.g. `RUS-44 [I] 1/2: …`).
- After mutations, run `gt log short --no-interactive` to verify stack state.
- Never use `gt sync` mid-feature on a held stack except in `land` cleanup — it deletes
  branches whose PRs were closed (which is correct only after merge).
- **Clear any stale PR association before every `gt submit`.** Run the idempotent
  `python3 <repo-root>/scripts/qrspi_clear_stale_pr.py --ticket <id>` FIRST — no `gt info`
  pre-check needed (the helper is a no-op when nothing is stale), and do not wait for the
  submit to fail. See [Resubmitting](#resubmitting-when-the-prior-pr-was-closed-or-merged).
  This happens routinely on reset→rerun: a reset closes a phase PR, and recreating the
  same-named branch re-hydrates the dead association from `.git/.graphite_pr_info`.

### Staging — NEVER use `-a`

`-a` stages unrelated untracked files and makes `gt undo` destroy them. Stage specific files.
For design/plan phases, stage only that phase's artifacts. For implementation slices, run
`git status --short` and stage EVERY file shown (code + tests + artifacts are all the slice's
deliverable) **except generated caches** — never stage `__pycache__/` or `*.pyc` (a worktree
off trunk may not inherit a `.gitignore` rule for them). Verify with `git status --short`
before committing.

### Resubmitting when the prior PR was closed or merged

Graphite pins each branch to the first PR it created, in the SHARED `.git/.graphite_pr_info`
cache (keyed by `headRefName` → PR number + state). After a reset/rework closed a PR — or a
previously-landed ticket is rerun — that association is stale and `gt submit` refuses to open
a fresh PR under the same name. `--force` does not help (it governs the force-push, not the
association), and the interactive "publish a new PR?" prompt is unreachable to agents: gt
collapses to non-interactive whenever stdin is not a TTY and silently drops any piped
selection.

Recovery is a single idempotent command — run it before the submit:
```bash
python3 <repo-root>/scripts/qrspi_clear_stale_pr.py --ticket <id>
```
It removes ONLY this ticket's `(Closed)`/`(Merged)` entries from the cache (OPEN associations
and other tickets are left untouched), so the branch resubmits as a brand-new PR under the
SAME name — no rename, no temp branch, no `--force`. Safe to run before every submit: with
nothing stale it is a no-op, and a missing/garbled cache degrades to a no-op (the submit then
aborts visibly, never worse). It supersedes the old `gt rename <branch>-stale` roundtrip,
whose fixed temp name COLLIDES across cycles when a recovery is interrupted between its two
renames (`fatal: a branch named '<branch>-stale' already exists`). This is a recognized
state, not an infrastructure error — the HARD STOP rule does not apply.

### Why PR bodies are authored at Graphite creation

PR descriptions are set **only** through the branch commit message, which Graphite uses to
seed the PR title (subject line) and body (the rest) **when it creates the PR**. There is no
`gh pr edit` step anywhere in this lifecycle, by design:

- `gt submit` (1.8.x) has **no** `--body`/`--body-file` flag — the commit message is the
  only non-interactive lever for the description, and Graphite reads it **at creation only**
  (re-submitting an existing PR does *not* re-sync its body from the commit message).
- The `gh`-authenticated token is a fine-grained PAT owned by a **different personal account**
  than the repo owner. It can read this public repo but every authenticated PR write returns
  `403 Resource not accessible by personal access token` (REST `PATCH /pulls`, GraphQL
  `updatePullRequest`, and `gh pr edit` all fail). `gt submit` itself works because Graphite
  authenticates through its own GitHub-App credential — a separate, write-capable path.

So: design/plan PRs carry their heredoc commit message as the body; implementation slice PRs
get a focused "Part N/total" body from the slice commit, and slice 1's commit message is
overwritten with the full `pr-summary.md` via `scripts/qrspi_pr_body.py` **before** the
creating `gt submit`. Trying to set a body with `gh` is a guaranteed 403 — do not add it back.

---

## Worktree Management

- One worktree per ticket at `<REPO_ROOT>/.worktrees/<ticket-id>/`; `.worktrees/` is gitignored.
- All `git worktree add` commands run from `REPO_ROOT`, never from inside a worktree.
- New branches created via `git worktree add -b` must be tracked once: `gt track --parent <parent> --no-interactive`.

### Stale worktree recovery
```bash
git worktree remove "$WORKTREE_PATH" --force 2>/dev/null
git worktree prune
git worktree add ...   # retry
```

---

## Error Handling

- Sub-agent fails or its artifact is missing → print the error, STOP, no Linear write.
- A `gt`/`git`/`gh` command fails for non-infrastructure reasons → print command + error, STOP.
- Resolver errors or returns an unrecognized action → print it, STOP. Never guess.
- Linear projection write fails → WARN and continue (best-effort; it is not a gate).
- Never partially update state — a phase transition fully succeeds or nothing changes.

### HARD STOP: Infrastructure Errors Are Not Puzzles To Solve

Non-negotiable, no exceptions. When ANY operation fails due to permissions, authentication,
configuration, or tooling errors (`EACCES`, `permission denied`, expired auth, config
inaccessible, tool not found, "repo not synced with Graphite", etc.):

1. **STOP. Do not execute another command.** Not "one more try."
2. **Print the exact error verbatim** — the failing command and full output, unmodified.
3. **Exit the skill.** Do not continue to subsequent phases or attempt partial progress.

**Explicitly forbidden:** `chmod`/`chown`; routing around config via env vars
(`XDG_CONFIG_HOME`); copying config files elsewhere; deleting/recreating config dirs; using
raw `git` to bypass a broken `gt`; `sudo`/escalation; any action whose purpose is "make the
failing tool work again."

**Why absolute:** the orchestrator rationalizes "just one quick thing," then tries five, each
more destructive. The only safe response is to stop and let the human fix their environment.
The thought "I know I should stop, but let me just…" is the exact failure mode this prevents.
```
