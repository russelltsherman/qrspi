# QRSPI Implementation Guide for Claude Code

Step-by-step instructions for installing and running the QRSPI workflow using Claude Code agents, skills, worktrees, and `CLAUDE.md`.

QRSPI decomposes feature work into sequential phases, each producing a reviewable artifact and **its own stacked pull request**. Phase logic lives in purpose-built **agents** (`.claude/agents/qrspi-<phase>.md`) with per-phase tool lockdowns; thin slash-command **skills** (`.claude/skills/qrspi-<phase>/SKILL.md`) wrap them. The `/qrspi-work` orchestrator drives a single ticket forward by reading its **PR review state** — not Linear status — and spawning the typed phase agents, and `.claude/workflows/qrspi-batch.js` drives many tickets at once. Advancement is gated on each phase PR being approved with no unresolved review threads; the decision is computed by the tested resolver in `scripts/qrspi_resolve_state.py`.

---

## 1. Project Structure

Create this directory tree at your project root:

```
your-project/
├── .claude/
│   ├── CLAUDE.md                          # Project-level persistent instructions
│   ├── agents/                            # Phase agents — the actual phase logic the orchestrator spawns
│   │   ├── qrspi-questions.md
│   │   ├── qrspi-research.md
│   │   ├── qrspi-design.md
│   │   ├── qrspi-structure.md
│   │   ├── qrspi-plan.md
│   │   ├── qrspi-worktree.md
│   │   ├── qrspi-implement.md
│   │   └── qrspi-pr.md
│   ├── skills/                            # Slash-command wrappers (thin) + orchestrator + ticket creation
│   │   ├── qrspi-feature/
│   │   │   └── SKILL.md                   # /qrspi-feature — front door: elicit→decompose→gate→create tickets
│   │   ├── qrspi-ticket/
│   │   │   └── SKILL.md                   # /qrspi-ticket — direct single-ticket entry (shared writer)
│   │   ├── qrspi-questions/
│   │   │   └── SKILL.md                   # /qrspi-questions
│   │   ├── qrspi-research/
│   │   │   └── SKILL.md                   # /qrspi-research
│   │   ├── qrspi-design/
│   │   │   └── SKILL.md                   # /qrspi-design
│   │   ├── qrspi-structure/
│   │   │   └── SKILL.md                   # /qrspi-structure
│   │   ├── qrspi-plan/
│   │   │   └── SKILL.md                   # /qrspi-plan
│   │   ├── qrspi-worktree/
│   │   │   └── SKILL.md                   # /qrspi-worktree
│   │   ├── qrspi-implement/
│   │   │   └── SKILL.md                   # /qrspi-implement
│   │   ├── qrspi-pr/
│   │   │   └── SKILL.md                   # /qrspi-pr
│   │   └── qrspi-work/
│   │       └── SKILL.md                   # /qrspi-work — autonomous orchestrator (PR-gated)
│   └── workflows/
│       └── qrspi-batch.js                 # Batch orchestrator — many tickets, one PR-gated step each
├── scripts/
│   ├── qrspi_resolve_state.py             # Tested PR-gated decision logic (the resolver)
│   ├── qrspi_pr_state.py                  # Gathers PR review state (gh GraphQL reviewThreads)
│   ├── qrspi_resolve.py                   # One-shot: worktree + gather + decision + artifact detection
│   ├── qrspi_persist.py                   # Verifies a staged artifact and moves it to the canonical path
│   ├── qrspi_pr_body.py                   # Splices pr-summary.md into the slice-1 commit message
│   └── qrspi_*_test.py                    # stdlib-only unit tests (one _test.py sibling per script)
├── .qrspi/
│   ├── templates/                         # Canonical output formats (reference only — single source of truth)
│   │   ├── ticket.md
│   │   ├── questions.md
│   │   ├── research.md
│   │   ├── design.md
│   │   ├── structure.md
│   │   ├── plan.md
│   │   ├── worktree.md
│   │   ├── impl-log.md
│   │   └── pr-summary.md
│   └── <ticket-id>/                       # Per-ticket artifacts, created at runtime
│       ├── questions.md
│       ├── research.md
│       ├── design.md
│       ├── structure.md
│       ├── plan.md
│       ├── worktree.md
│       ├── impl-log.md
│       └── pr-summary.md
├── .worktrees/                            # Isolated git worktrees per ticket (gitignored)
└── src/
    └── ...
```

Note there is **no `ticket.md`** in a ticket's artifact directory: the ticket is a **Linear issue**, not a local file. Artifacts are local files under `.qrspi/<ticket-id>/`, carried on the phase branches; Linear holds only an entry-gate status and a best-effort reporting projection of the active phase (see §5) — artifacts are not uploaded to Linear.

Create the scaffolding:

```bash
mkdir -p .claude/agents
mkdir -p .claude/skills/{qrspi-feature,qrspi-ticket,qrspi-questions,qrspi-research,qrspi-design,qrspi-structure,qrspi-plan,qrspi-worktree,qrspi-implement,qrspi-pr,qrspi-work}
mkdir -p .claude/workflows
mkdir -p .qrspi/templates
```

`.worktrees/` and per-ticket `.qrspi/<ticket-id>/` directories are created at runtime by the orchestrator — do not create them by hand.

---

## 2. CLAUDE.md — Project-Level Instructions

This is loaded at the start of every Claude Code session. Keep it lean — it counts against your context budget.

Create `.claude/CLAUDE.md`:

```markdown
# Project: <your-project-name>

## QRSPI Workflow

This project uses the QRSPI structured workflow for feature development.
Tickets are created as Linear issues (team: <your-team>, project: <your-project>).
Ticket IDs follow Linear's format (e.g., RUS-42). Artifacts are stored locally
in `.qrspi/<ticket-id>/` — not uploaded as attachments.

### Lifecycle — PR-gated

**PR review state — not Linear status — is the authority for advancement.** Linear has
exactly two roles: an **entry gate** (a ticket may only begin if it is *assigned* and in
`Selected`) and a **best-effort reporting projection** (agents update status to reflect the
active phase; a failed Linear write never blocks work).

Each ticket is one Graphite stack, built bottom-up and **held open** until the whole feature
is approved, then landed bottom-up:

    Selected (assigned)
      → design PR   [Questions·Research·Design]   ──approved──┐
      → plan PR     [Structure·Plan·WorkTree]      (stacked)  ──approved──┐
      → slice PRs   [Implementation]               (stacked)   ──all approved──→ land → Done

- **Branches:** `<id>/design` → `<id>/plan` → `<id>/slice-1..N`, each its own PR, stacked.
- **Advance** is automatic: approving a phase PR (`reviewDecision == APPROVED` **and** zero
  unresolved review threads) builds the next phase on top.
- **Reset** is automatic: a formal `CHANGES_REQUESTED` on an upstream phase PR discards every
  downstream phase (PRs closed, branches deleted, stale artifacts removed) and returns the
  ticket to that phase. **Revise** is also automatic and is the unified feedback action: a
  *frontier* phase PR carrying a formal `CHANGES_REQUESTED` and/or unaddressed reviewer
  comments is addressed in place (per-comment replies, plus — only when a change request is
  present — amending the phase commit and re-requesting review). Unresolved review *threads*
  alone resolve to `wait` (only the reviewer resolves a thread).
- The `*Approved` Linear states were dropped — approval lives in the PR. Reporting statuses:
  `Selected` → `Design Review` → `Plan Review` → `Code Review` → `Done`.
- The decision is computed by a tested resolver (`scripts/qrspi_resolve_state.py`); the
  orchestrator and batch both call it rather than re-deriving state logic.

### Available skills (invoke with / or let Claude auto-invoke)

- `/qrspi-feature <description>` — Front door for new feature work: elicits requirements, proposes a reviewed ticket decomposition (one ticket vs several + dependency DAG + overlap scan), stops for approval before any Linear write, then creates ticket(s) via the shared writer
- `/qrspi-ticket <description>` — Direct single-ticket entry: drafts/files one already-scoped Linear issue via the same interview + shared writer (no decomposition/gate)
- `/qrspi-work <ticket-id>` — Autonomous orchestrator: reads PR review state, runs the matching action
- `/qrspi-questions <ticket-id>` — Generate technical questions from a ticket (fetched from Linear)
- `/qrspi-research <ticket-id>` — Map the codebase (ticket is hidden from this phase)
- `/qrspi-design <ticket-id>` — Produce a design document
- `/qrspi-structure <ticket-id>` — Define vertical slices and contracts
- `/qrspi-plan <ticket-id>` — Write tactical implementation steps
- `/qrspi-worktree <ticket-id>` — Build a session-aware task DAG
- `/qrspi-implement <ticket-id> <slice-number>` — Implement one vertical slice
- `/qrspi-pr <ticket-id>` — Prepare pull request summary

### Workflow rules

- Phases run sequentially. Never skip ahead.
- Each artifact must exist and be reviewed before the next phase starts.
- Start a fresh `/clear` session between implementation slices.
- Use `/compact` if context grows large within a phase.
- Use `/context` to check utilization. If over 40%, compact or start fresh.

### Codebase conventions
<Add your project-specific conventions here: language, framework,
test runner commands, directory layout, naming patterns, etc.>
```

---

## 3. Agents and Skills

QRSPI's phase logic lives in two layers:

- **Agents** (`.claude/agents/qrspi-<phase>.md`) hold the heavy phase logic and a per-phase tool lockdown. The orchestrator spawns them via the `Agent` tool with `subagent_type: qrspi-<phase>` and a structured input contract — it never reads the phase SKILL.md files or hand-engineers prompts. This is the agent-vs-skill split: the substance is in agents; skills are thin wrappers.
- **Skills** (`.claude/skills/qrspi-<phase>/SKILL.md`) are the slash-command wrappers (`/qrspi-questions`, etc.) that let a human invoke a single phase directly. They exist primarily for the orchestrator's surface area and for manual re-runs.

Three skills are not phase wrappers:

- `.claude/skills/qrspi-work/SKILL.md` is the autonomous **orchestrator** — it resolves the next action from the ticket's PR review state (see §5).
- `.claude/skills/qrspi-feature/SKILL.md` is the **front door** for new feature work — it elicits requirements, proposes a *reviewed* ticket decomposition (one ticket vs several, a dependency DAG, an overlap scan against in-flight tickets), **stops for approval before any Linear write**, then creates ticket(s) via the shared writer (with `blockedBy` edges and a Linear parent issue).
- `.claude/skills/qrspi-ticket/SKILL.md` is the **direct single-ticket entry** — it drafts and files one already-scoped Linear ticket through the same guided interview and the same shared writer, without the decomposition/gate.

### Per-phase tool lockdowns (firewalls)

Each agent restricts its own tools so a phase structurally cannot do something it shouldn't:

- **Questions** has no `Glob`, `Grep`, or `Bash` — codebase exploration is structurally impossible. It works from the ticket alone.
- **Research** has read/search tools but **no Linear MCP and cannot read the ticket**. The ticket is hidden during research to gather objective codebase facts without anchoring on a proposed solution. The orchestrator reinforces this by never passing ticket content into the research agent's input contract (defense in depth), and by appending a project-scope restriction that confines all reads to the repo.
- **Design, Structure, Plan, Worktree** are read-only planning phases.
- **Implement** opens up `Write`/`Edit`/`Bash` but is scoped to a single slice and forbidden from reading the full design or unrelated slices.

Author each agent and skill from the canonical templates in `.qrspi/templates/`. The phase artifacts (questions, research, design, structure, plan, worktree, impl-log, pr-summary) follow those template formats rather than formats embedded inline in each prompt.

---

## 4. Phase Reference

| Phase | Artifact | What it does |
|-------|----------|--------------|
| **Ticket** | Linear issue | Defines the problem, goals, acceptance criteria. No solutions. Created via `/qrspi-feature` (front door — decomposes + gates) or `/qrspi-ticket` (direct single-ticket entry). |
| **Questions** | `questions.md` | 8–15 targeted technical questions derived from the ticket. |
| **Research** | `research.md` | Answers the questions by reading the codebase. Ticket hidden to prevent anchoring. |
| **Design** | `design.md` | Pattern decisions, risk register, delta, open questions. |
| **Structure** | `structure.md` | Vertical slices, types, cross-slice contracts. |
| **Plan** | `plan.md` | Atomic implementation steps per slice, with verification checkpoints. |
| **Worktree** | `worktree.md` | Session-aware task DAG with per-session context budgets. |
| **Implement** | Code + `impl-log.md` | Implements one slice per fresh session, within the git worktree. |
| **PR** | `pr-summary.md` | Maps acceptance criteria to implementation files and tests. |

These nine phases group into three reviewable PRs: a **design PR** (questions, research, design), a **plan PR** (structure, plan, worktree), and an **implementation** stack (one PR per slice, with the PR summary). Each PR is a review gate — approving it auto-builds the next phase on top, as described next.

---

## 5. The Lifecycle and `/qrspi-work`

Each phase is its own **stacked pull request**, and **PR review state — not Linear status — is the authority** for what runs next. `/qrspi-work <ticket-id>` gathers the stack's PR state and resolves the matching action with a tested script rather than a hand-coded status switch:

```bash
python3 scripts/qrspi_pr_state.py --owner <owner> --repo <repo> --ticket <ticket-id> \
    [--assigned] --linear-status "<status>" \
  | python3 scripts/qrspi_resolve_state.py
# → { action, phase, nextPhase, resetToPhase, discardPhases, reason }
```

`qrspi_pr_state.py` gathers each phase PR's `reviewDecision` and unresolved-thread count (via GitHub GraphQL `reviewThreads`); `qrspi_resolve_state.py` turns that into one of the actions below. The orchestrator dispatches on the returned `action` — it does not re-derive state from Linear (after the entry gate).

| `action` | What `/qrspi-work` does |
|----------|--------------------------|
| `entry_blocked` | Entry gate not satisfied (not assigned, or not `Selected`, and no `<id>/design` branch yet). Stop — nothing begins. |
| `run_design` | Entry gate satisfied. Build the **design** phase (questions → research → design) on a fresh `<id>/design` branch off trunk; open the Design PR. Project Linear → `Design Review`. |
| `advance` → plan | Design PR is **READY** (approved + zero unresolved threads). Build **structure → plan → worktree** on a `<id>/plan` branch stacked on `<id>/design`; open the Plan PR. Project Linear → `Plan Review`. |
| `advance` → implementation | Plan PR is READY. Build the **slice PR stack** (`<id>/slice-1..N`, each stacked on the prior). Project Linear → `Code Review`. |
| `wait` | The active phase PR is awaiting the reviewer: not yet approved, OR its only outstanding signal is unresolved review threads with neither a formal change request nor an unaddressed reviewer comment. Nothing to do autonomously — stop. |
| `revise` | The **frontier** phase PR carries a formal `CHANGES_REQUESTED` and/or unaddressed reviewer **comments**. **Automatically** engage each comment per-intent and post in-thread replies; when a change request is present, also address the review summary, amend the phase commit, and re-request review (which clears the change request). Unresolved review *threads alone* resolve to `wait`. |
| `reset` | A formal `CHANGES_REQUESTED` landed on an **upstream** phase PR. **Automatically** discard every downstream phase (close PRs, delete branches, remove stale artifacts) and return the ticket to that phase for revision. |
| `land` | Every PR in the stack is READY. Merge the whole stack **bottom-up**, clean up artifacts and the worktree. Project Linear → `Done`. |

**Advance vs. land are decoupled.** Approving any single phase PR auto-builds the next phase stacked on top, but nothing merges to trunk mid-feature: the stack is **held open** until *every* PR — design, plan, and all slices — is approved with zero unresolved threads, then lands bottom-up in one pass.

**Two kinds of review feedback, handled differently:**

- An **unaddressed reviewer comment** on the frontier PR routes to the autonomous `revise` action: the comment is answered / applied+amended / declined with rationale in place via an in-thread reply, no reset; revise is bounded to the affected phase's own artifacts. An **unresolved review thread alone** (no comment, no change request) resolves to `wait` — left for the reviewer to resolve. Neither resets the stack.
- A formal `CHANGES_REQUESTED` on an upstream PR is a **reset**. Reset is **symmetric** across phases: a change request on phase K discards every phase above K (slices before plan), automatically and without confirmation, because the skip-if-exists resume logic would otherwise treat a stale `plan.md` / `structure.md` (or slice code) as done and ship work derived from a superseded design. The discard is bounded to ticket-local branches and artifacts; nothing is merged, so trunk is never rewritten.

Because the PR state is authoritative, `/qrspi-work` is **resumable** and idempotent: re-running it re-reads the stack's PR state and computes the same action until something changes (a human approves, comments, or requests changes).

---

## 6. Worktrees

Each ticket gets its own git worktree at `.worktrees/<ticket-id>/` (gitignored). The main checkout stays on `main`; all ticket work happens in the worktree. Multiple tickets can be worked concurrently without branch-checkout conflicts, since you cannot have the same branch checked out in two worktrees at once.

Key mechanics the orchestrator handles:

- It sets `REPO_ROOT` (where `.git/` lives) and `WORKTREE_PATH = <REPO_ROOT>/.worktrees/<ticket-id>`.
- `git worktree add` runs from `REPO_ROOT`; the `cd` into the worktree happens after creation.
- The worktree is checked out to the **highest existing phase branch** (the stack tip): a slice branch if any exist, else `<id>/plan`, else `<id>/design`.
- A newly created `<id>/design` branch is tracked once with `gt track --parent main --no-interactive`; each later phase branch (`<id>/plan`, `<id>/slice-N`) is created stacked on the prior phase via `gt create`.

**Sub-agents do not inherit the orchestrator's cwd.** A spawned agent's Bash session starts at the main repo root, not the cd'd worktree. The orchestrator therefore:

1. Tells every sub-agent to `cd <WORKTREE_PATH>` as its first Bash command, and
2. Passes **absolute, worktree-prefixed paths** (`<WORKTREE_PATH>/.qrspi/<ticket-id>/...`) for all file operations — never relative paths.

---

## 7. Running a Single Ticket

For **new feature work**, the front door is `/qrspi-feature <description>` — it elicits requirements, proposes a reviewed decomposition, and may create *several* tickets (with dependency edges and a parent issue). The `/qrspi-ticket` path shown below is the **direct single-ticket entry**, for work you've already scoped to one ticket.

### Step 0 — Create the ticket (Linear)

```
claude
> /qrspi-ticket Add user preference endpoint for notification and display settings
```

`/qrspi-ticket` gathers problem context through guided conversation and creates a **Linear issue** in your team/project (e.g., `RUS-42`). There is no local `ticket.md` — the issue lives in Linear.

### Step 1 — Drive it forward

The normal path is to let the orchestrator run:

```
> /qrspi-work RUS-42
```

`/qrspi-work` resolves the ticket's PR review state into one of the actions from the table in §5 and runs it. On a fresh assigned `Selected` ticket it builds the design phase, opens the Design PR, and stops (`wait`). You then **review the PR on GitHub** — approving it auto-advances on the next invocation; commenting or requesting changes routes to `revise`/`reset` instead. Re-invoke `/qrspi-work` after each review action to let the resolver pick up the new PR state.

A full run therefore looks like:

```
> /qrspi-work RUS-42      # run_design → opens Design PR → waits for review
# ...human approves the Design PR on GitHub...
> /qrspi-work RUS-42      # advance → opens Plan PR (stacked on design) → waits for review
# ...human approves the Plan PR...
> /qrspi-work RUS-42      # advance → opens the slice PR stack → waits for review
# ...human approves every slice PR...
> /qrspi-work RUS-42      # land → merges the whole stack bottom-up, cleans up → Done
```

If a reviewer leaves an unaddressed comment, the next `/qrspi-work` runs `revise` automatically — answering/addressing it in place, then re-requesting review only when a formal change request is present. If the only signal is an unresolved review thread, it returns `wait` until the reviewer resolves it. If a reviewer requests changes on an upstream PR, the next invocation `reset`s — discarding the downstream phases automatically and returning to that phase.

Start a fresh `/clear` session between invocations, especially before implementation.

### Running individual phases manually

The per-phase skills exist for re-running a single phase or working step-by-step outside the orchestrator. Each operates on the Linear ticket and the local artifacts:

```
> /qrspi-questions RUS-42     # reads the ticket from Linear, writes questions.md
> /clear
> /qrspi-research RUS-42       # reads questions.md only — NOT the ticket — writes research.md
> /clear
> /qrspi-design RUS-42         # writes design.md
> /clear
> /qrspi-structure RUS-42      # writes structure.md
> /clear
> /qrspi-plan RUS-42           # writes plan.md
> /clear
> /qrspi-worktree RUS-42       # writes worktree.md
> /clear
> /qrspi-implement RUS-42 1    # implements slice 1, appends to impl-log.md
> /clear
> /qrspi-implement RUS-42 2    # slice 2 in a fresh session
> /clear
> /qrspi-pr RUS-42             # writes pr-summary.md
```

Manual runs do not create branches, submit PRs, or project Linear status on their own — those belong to `/qrspi-work`. Use manual phases for spot fixes on a checked-out phase branch, then hand control back to the orchestrator to commit, stack, and submit.

---

## 8. Batch: Many Tickets at Once

`.claude/workflows/qrspi-batch.js` drives **many assigned tickets** one PR-gated step forward by resolving each ticket's PR review state (with the same `qrspi_pr_state.py` → `qrspi_resolve_state.py` pipeline) and spawning the typed phase agents from the workflow script itself. It runs only the **autonomously-runnable** actions that need no human judgment:

- `run_design` — entry-gate-satisfied tickets get their design PR built
- `advance` — an approved phase PR auto-builds the next phase stacked on top
- `submit` — finish/open a phase PR left dangling by a crashed run
- `land` — an all-green stack is merged bottom-up
- automatic `reset` — an upstream change request discards the stale downstream phases
- `revise` — a frontier PR with a change request and/or unaddressed comments is addressed in place, then review is re-requested

It **deliberately leaves only `wait` untouched** — a PR not yet approved, or whose only outstanding signal is unresolved review threads (neither a change request nor an unaddressed comment), so a human reviews each PR on GitHub. Run the batch after assigning tickets and moving them to `Selected`, or after approving phase PRs; it processes each one to its next gate.

---

## 9. Context Management During a Session

Use these built-in Claude Code commands throughout:

| Command | When to use |
|---------|-------------|
| `/context` | Check context utilization. If over 40%, take action. |
| `/compact` | Compress conversation history. Use within a phase if context is growing. |
| `/clear` | Full reset. Use between phases and between implementation slices. |
| `/cost` | Check token spend. Useful for budgeting. |

The workflow is designed so that a fresh session per phase (and per slice) is the default. Each agent loads only the artifacts named in its input contract — `worktree.md`'s per-session budgets keep each implementation session under the 40% target. This is the primary defense against context degradation.

---

## 10. Handling Revisions

Revisions are driven through **GitHub PR review**, not by typing "revise" in a session. How a piece of feedback is handled depends on its kind and which PR it lands on:

- **An unaddressed reviewer comment and/or formal `CHANGES_REQUESTED` on the frontier phase PR → `revise` (autonomous, in-phase).** On any `/qrspi-work` or batch pass, the orchestrator engages each comment per-intent (answer / apply+amend / decline with rationale) and posts an in-thread reply via `scripts/qrspi_comment_reply.py`; only when a formal change request is present does it also address the review summary, amend the phase commit, and re-request review (which clears the change request — the loop-safe termination signal). The cascade is bounded to *that phase's own artifacts*; for the implementation stack, comments are grouped by slice and addressed from the lowest-numbered affected slice (changes restack upward). An **unresolved review thread alone** (no comment, no change request) is left for the reviewer and resolves to `wait` — threads can only be resolved by the reviewer.
- **A formal change request on an upstream PR → `reset` (automatic, cross-phase).** Requesting changes on the Design PR after the Plan PR (or slice PRs) already exist discards every downstream phase — closing its PRs, deleting its branches, and removing the now-stale artifacts — and returns the ticket to the design phase. The downstream work is regenerated, not patched in place, when the upstream phase is re-approved. The same is true for a change request on the Plan PR relative to the slice stack.

For substantial design redirects, the cleanest path is a `CHANGES_REQUESTED` on the Design PR: the reset discards plan/slice work cleanly and the orchestrator regenerates it from the corrected design. Avoid hand-editing a downstream artifact to "patch around" an upstream design change — the existence-detection resume logic would treat the stale artifact as done. Approval lives entirely in the PR; there is no separate Linear approval step.

---

## 11. Adapting to Your Project

### Configure Linear

Tickets live in Linear. The harness references the Linear MCP server by the fixed name `linear` (its binding is committed in `.mcp.json`; authenticate it to your workspace on first use), and the ticket-creation skills (`/qrspi-feature` and `/qrspi-ticket`, which share the same writer) read the team/project from `.qrspi/config.json` (`linearTeam`/`linearProject`; see `.qrspi/config.example.json`) so they file issues in the right place. Linear is **not** the state machine — it is an entry gate plus a best-effort reporting projection — so only the reporting statuses need to exist in your Linear team: `Selected`, `Design Review`, `Plan Review`, `Code Review`, `Done`. (The `*Approved` statuses were dropped; approval lives in the PR.) You also need GitHub PRs reachable via the `gh` CLI, since PR review state is the authority.

### Customize test commands

The verification commands live in the templates and the plan/implement agents. Edit them to match your test runner (e.g., `pytest` vs `npm test`) so each slice's Verify checkpoint runs the right command.

### Customize tool lockdowns

Each agent's `allowed-tools` frontmatter controls what that phase can do. The Questions, Research, and planning phases intentionally restrict tools; Implement opens up `Write`/`Edit`/`Bash`. Adjust per your security requirements, but keep the Research firewall (no ticket access, no Linear) intact — it is what prevents anchoring.

### Add project conventions to CLAUDE.md

Your `.claude/CLAUDE.md` should include project-specific patterns: naming conventions, directory layout, preferred libraries, test patterns. The Research agent discovers these from the codebase, but explicit documentation reduces hallucination.

### Team sharing

Commit `.claude/agents/`, `.claude/skills/`, `.claude/workflows/`, and `scripts/` (the resolver, the PR-state gatherer, and their unit tests) to your repo so every team member gets the same workflow and the same tested decision logic. Per-ticket `.qrspi/<ticket-id>/` artifacts ride on the phase branches and are cleaned up at land; the `.qrspi/templates/` directory is the shared single source of truth for artifact formats.

---

## 12. Troubleshooting

**"Claude skipped a section in the artifact"**
The agent prompt may be too long. Keep each agent file focused and under its instruction budget. The phase artifacts follow the formats in `.qrspi/templates/` — verify the template is being referenced rather than re-specified inline.

**"Research read the ticket"**
The research agent's tool definition excludes Linear MCP and forbids ticket reads, and the orchestrator never passes ticket content into the research input contract. If you are running research manually, do not paste the ticket into the session. This firewall is the anchoring-prevention mechanism — don't bypass it.

**"Questions tried to explore the codebase"**
The questions agent has no `Glob`/`Grep`/`Bash`, so this is structurally impossible. If you see it happening, the agent's tool lockdown has been edited — restore it.

**"Context is degrading mid-implementation"**
Run `/context`. If over 40%, `/clear` and restart the current slice. The worktree's per-session budgets are designed to prevent this — respect the session boundaries.

**"Claude invented a pattern not in the codebase"**
This should be caught at Design Review — the design's citation requirements make uncited claims visible. The Structure phase's "Unverified Assumptions" section is the second safety net.

**"Slices feel too large"**
If a slice touches more than ~10 files or fills a context window, go back to Structure and split it, then re-run Plan and Worktree. The workflow supports re-running any phase.

**"`/qrspi-work` keeps returning `wait` and won't advance"**
That is by design. A phase PR advances only when it is **approved with zero unresolved review threads**. Approve the PR on GitHub (and resolve any open threads) and re-invoke `/qrspi-work` — there is no Linear status to flip. If you left comments without approving, the PR is in `revise` territory: invoke `/qrspi-work` explicitly to address them.

**"A change request blew away my plan/slice work"**
Expected. A formal `CHANGES_REQUESTED` on an upstream PR triggers an **automatic reset**: the downstream phases are discarded (PRs closed, branches deleted, artifacts removed) because they were derived from a now-superseded upstream. Re-approve the upstream phase after revision and the stack rebuilds. To request a small in-phase tweak without a reset, leave a plain comment instead of requesting changes.

**"A phase's prior PR was closed/merged and `gt submit` refuses"**
This is a recognized Graphite stale-association state — common after a reset closes a phase PR — handled by the orchestrator's resubmit recovery (detach the dead PR by renaming the branch away and back, then submit with `--force`). It is not an infrastructure error.

**"The resolver returned an action I don't understand / errored"**
The decision comes from `scripts/qrspi_resolve_state.py` (fed by `scripts/qrspi_pr_state.py`). Both are stdlib-only and unit-tested (each script has a `_test.py` sibling, e.g. `scripts/qrspi_resolve_state_test.py`) — run the tests to confirm the logic, and check the PR-state JSON the gatherer produced. The orchestrator treats an unrecognized action as a hard stop rather than guessing.
