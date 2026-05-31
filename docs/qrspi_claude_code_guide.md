# QRSPI Implementation Guide for Claude Code

Step-by-step instructions for installing and running the QRSPI workflow using Claude Code agents, skills, worktrees, and `CLAUDE.md`.

QRSPI decomposes feature work into sequential phases, each producing a reviewable artifact. Phase logic lives in purpose-built **agents** (`.claude/agents/qrspi-<phase>.md`) with per-phase tool lockdowns; thin slash-command **skills** (`.claude/skills/qrspi-<phase>/SKILL.md`) wrap them. The `/qrspi-work` orchestrator drives a single ticket through its Linear-status state machine by spawning the typed phase agents, and `.claude/workflows/qrspi-batch.js` drives many tickets at once.

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
│   │   ├── qrspi-ticket/
│   │   │   └── SKILL.md                   # /qrspi-ticket — guided Linear ticket creation
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
│   │       └── SKILL.md                   # /qrspi-work — autonomous orchestrator (state machine)
│   └── workflows/
│       └── qrspi-batch.js                 # Batch orchestrator — many tickets through autonomous states
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

Note there is **no `ticket.md`** in a ticket's artifact directory: the ticket is a **Linear issue**, not a local file. Artifacts are local files under `.qrspi/<ticket-id>/`; Linear holds status and phase-transition comments only — artifacts are not uploaded to Linear.

Create the scaffolding:

```bash
mkdir -p .claude/agents
mkdir -p .claude/skills/{qrspi-ticket,qrspi-questions,qrspi-research,qrspi-design,qrspi-structure,qrspi-plan,qrspi-worktree,qrspi-implement,qrspi-pr,qrspi-work}
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
in `.qrspi/<ticket-id>/`. Linear is used for status tracking and phase-transition
comments only — artifacts are not uploaded as attachments.

### Lifecycle and review gates

Planning is split into two halves, each ending at a human review gate. The Linear
status is the authoritative state machine:

    Selected → [Questions·Research·Design] → Design Review → Design Approved
      → [Structure·Plan·WorkTree] → Plan Review → Plan Approved
      → [Implementation] → Code Review → Code Approved → Done

- Design Review / Design Approved gate the design half; Plan Review / Plan Approved
  gate the plan half. The two review statuses are human turns — the orchestrator
  waits (or addresses PR feedback) and never advances autonomously past them.
- All six planning artifacts live on one `<ticket-id>/planning` branch as a single
  amended commit. The PR is submitted at Design Review and re-submitted (grown with
  the plan-half artifacts) at Plan Review.

### Available skills (invoke with / or let Claude auto-invoke)

- `/qrspi-ticket <description>` — Create a Linear issue through guided conversation
- `/qrspi-work <ticket-id>` — Autonomous orchestrator: reads Linear status, runs the matching phase
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

Two skills are not phase wrappers:

- `.claude/skills/qrspi-work/SKILL.md` is the autonomous **orchestrator** — a state machine keyed on the ticket's Linear status (see §5).
- `.claude/skills/qrspi-ticket/SKILL.md` creates a new Linear ticket through guided conversation.

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
| **Ticket** | Linear issue | Defines the problem, goals, acceptance criteria. No solutions. Created with `/qrspi-ticket`. |
| **Questions** | `questions.md` | 8–15 targeted technical questions derived from the ticket. |
| **Research** | `research.md` | Answers the questions by reading the codebase. Ticket hidden to prevent anchoring. |
| **Design** | `design.md` | Pattern decisions, risk register, delta, open questions. |
| **Structure** | `structure.md` | Vertical slices, types, cross-slice contracts. |
| **Plan** | `plan.md` | Atomic implementation steps per slice, with verification checkpoints. |
| **Worktree** | `worktree.md` | Session-aware task DAG with per-session context budgets. |
| **Implement** | Code + `impl-log.md` | Implements one slice per fresh session, within the git worktree. |
| **PR** | `pr-summary.md` | Maps acceptance criteria to implementation files and tests. |

These nine phases group into a **design half** (questions, research, design), a **plan half** (structure, plan, worktree), and **implementation** (slices + PR summary), separated by the two human review gates described next.

---

## 5. The Lifecycle and `/qrspi-work`

Planning is split into two halves separated by two human review gates. The **Linear status is the authoritative state machine** — it, not artifact presence, decides what runs next. `/qrspi-work <ticket-id>` reads that status and executes the matching action:

| Linear Status | `/qrspi-work` action |
|---------------|----------------------|
| Backlog / Selected | Run the **design half** (questions → research → design); submit the planning PR; move ticket to **Design Review**. |
| **Design Review** | **Human gate.** Review the design-half PR. The orchestrator addresses PR feedback (bounded to Questions → Research → Design) or waits. The **human** moves the ticket to Design Approved. |
| Design Approved | Run the **plan half** (structure → plan → worktree) by amending the same planning commit; update the planning PR; move ticket to **Plan Review**. |
| **Plan Review** | **Human gate.** Review the full plan PR. The orchestrator addresses PR feedback or waits. The **human** moves the ticket to Plan Approved. |
| Plan Approved | Implement all slices; submit stacked PRs (one per slice); move ticket to **Code Review**. |
| **Code Review** | Address implementation review feedback on the stack. The **human** moves the ticket to Code Approved. |
| Code Approved | Report ready to merge — merging is human-owned. |
| Done | Clean up artifacts and worktree. |

The two review gates (Design Review, Plan Review) are **human turns**. The orchestrator waits or addresses PR feedback there; it never advances past them autonomously. Likewise, the human owns the Code Review → Code Approved transition and the final merge.

All six planning artifacts live on **one `<ticket-id>/planning` branch as a single amended commit**. The questions phase creates the commit; every subsequent planning phase amends it. The planning PR is submitted at Design Review and re-submitted — grown with the plan-half artifacts — at Plan Review.

Because the status is authoritative, `/qrspi-work` is **resumable**: re-running it re-reads the Linear status and resumes from the next incomplete artifact within the current half.

---

## 6. Worktrees

Each ticket gets its own git worktree at `.worktrees/<ticket-id>/` (gitignored). The main checkout stays on `main`; all ticket work happens in the worktree. Multiple tickets can be worked concurrently without branch-checkout conflicts, since you cannot have the same branch checked out in two worktrees at once.

Key mechanics the orchestrator handles:

- It sets `REPO_ROOT` (where `.git/` lives) and `WORKTREE_PATH = <REPO_ROOT>/.worktrees/<ticket-id>`.
- `git worktree add` runs from `REPO_ROOT`; the `cd` into the worktree happens after creation.
- New planning branches are tracked once with `gt track --parent main --no-interactive`.

**Sub-agents do not inherit the orchestrator's cwd.** A spawned agent's Bash session starts at the main repo root, not the cd'd worktree. The orchestrator therefore:

1. Tells every sub-agent to `cd <WORKTREE_PATH>` as its first Bash command, and
2. Passes **absolute, worktree-prefixed paths** (`<WORKTREE_PATH>/.qrspi/<ticket-id>/...`) for all file operations — never relative paths.

---

## 7. Running a Single Ticket

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

`/qrspi-work` reads the ticket's Linear status and runs the matching action from the table in §5. On a fresh `Selected` ticket it produces the design half and stops at the Design Review gate. Re-invoke it after each human transition (Design Approved, Plan Approved, Code Approved) to advance to the next stage.

A full run therefore looks like:

```
> /qrspi-work RUS-42      # Selected → design half → Design Review (waits for human)
# ...human reviews the planning PR, moves ticket to Design Approved...
> /qrspi-work RUS-42      # Design Approved → plan half → Plan Review (waits for human)
# ...human reviews, moves ticket to Plan Approved...
> /qrspi-work RUS-42      # Plan Approved → implement all slices → stacked PRs → Code Review
# ...human reviews PRs, moves ticket to Code Approved...
> /qrspi-work RUS-42      # Code Approved → reports merge instructions (human merges)
# ...human merges, marks ticket Done...
> /qrspi-work RUS-42      # Done → cleans up artifacts + worktree
```

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

Manual runs do not move Linear status or submit PRs on their own — those transitions belong to `/qrspi-work`. Use manual phases for spot fixes, then hand control back to the orchestrator.

---

## 8. Batch: Many Tickets at Once

`.claude/workflows/qrspi-batch.js` drives **many assigned tickets** through the autonomously-runnable states by spawning the typed phase agents from the workflow script itself. It only touches the states that need no human judgment:

- **Selected** → run the design half
- **Design Approved** → run the plan half
- **Plan Approved** → implement all slices

It **deliberately leaves the human review gates (Design Review, Plan Review) untouched** — tickets parked at those statuses are skipped so a human can review the PR and advance them. Run the batch after you have moved a set of tickets into Selected, Design Approved, or Plan Approved; it processes each one to its next gate.

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

Revisions are driven through the **PR review gates**, not by typing "revise" in a session:

- At **Design Review**, leave review comments on the planning PR. The next `/qrspi-work` invocation reads the comments and addresses them, with the cascade bounded to Questions → Research → Design (the plan-half artifacts don't exist yet). It amends the single planning commit and re-pushes.
- At **Plan Review**, comment on the same planning PR. The orchestrator re-runs the earliest affected artifact and cascades forward through the plan half.
- At **Code Review**, comment on the slice PRs. The orchestrator addresses feedback starting from the lowest-numbered affected slice (changes restack upward through the stack).

For substantial design redirects, edit `design.md` directly in the worktree and commit it before re-running — the orchestrator treats the on-disk artifact as the source of truth for downstream phases. The human always owns moving the ticket from a Review status to the corresponding Approved status.

---

## 11. Adapting to Your Project

### Configure Linear

Tickets live in Linear. Configure the Linear MCP server for your workspace and set the team/project in `.claude/CLAUDE.md` so `/qrspi-ticket` files issues in the right place. The orchestrator's status names (Backlog, Selected, Design Review, Design Approved, Plan Review, Plan Approved, Code Review, Code Approved, Done) must exist as statuses in your Linear team.

### Customize test commands

The verification commands live in the templates and the plan/implement agents. Edit them to match your test runner (e.g., `pytest` vs `npm test`) so each slice's Verify checkpoint runs the right command.

### Customize tool lockdowns

Each agent's `allowed-tools` frontmatter controls what that phase can do. The Questions, Research, and planning phases intentionally restrict tools; Implement opens up `Write`/`Edit`/`Bash`. Adjust per your security requirements, but keep the Research firewall (no ticket access, no Linear) intact — it is what prevents anchoring.

### Add project conventions to CLAUDE.md

Your `.claude/CLAUDE.md` should include project-specific patterns: naming conventions, directory layout, preferred libraries, test patterns. The Research agent discovers these from the codebase, but explicit documentation reduces hallucination.

### Team sharing

Commit `.claude/agents/`, `.claude/skills/`, and `.claude/workflows/` to your repo so every team member gets the same workflow. Per-ticket `.qrspi/<ticket-id>/` artifacts are committed on the planning branch and cleaned up at Done; the `.qrspi/templates/` directory is the shared single source of truth for artifact formats.

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

**"`/qrspi-work` won't advance past a Review status"**
That is by design. Design Review and Plan Review are human gates — the orchestrator only addresses PR feedback or waits there. Move the ticket to Design Approved / Plan Approved in Linear (after reviewing the PR) and re-invoke `/qrspi-work`.

**"The planning PR's prior PR was closed/merged and `gt submit` refuses"**
This is a recognized Graphite stale-association state, handled by the orchestrator's resubmit recovery (detach the dead PR by renaming the branch away and back, then submit with `--force`). It is not an infrastructure error.
