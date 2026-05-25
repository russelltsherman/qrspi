# QRSPI Implementation Guide for Claude Code

Step-by-step instructions for installing and running the QRSPI workflow using Claude Code skills, subagents, hooks, and `CLAUDE.md`.

---

## 1. Project Structure

Create this directory tree at your project root:

```
your-project/
├── .claude/
│   ├── CLAUDE.md                          # Project-level persistent instructions
│   └── skills/
│       ├── qrspi-questions/
│       │   └── SKILL.md                   # /qrspi-questions slash command
│       ├── qrspi-research/
│       │   └── SKILL.md                   # /qrspi-research
│       ├── qrspi-design/
│       │   └── SKILL.md                   # /qrspi-design
│       ├── qrspi-structure/
│       │   └── SKILL.md                   # /qrspi-structure
│       ├── qrspi-plan/
│       │   └── SKILL.md                   # /qrspi-plan
│       ├── qrspi-worktree/
│       │   └── SKILL.md                   # /qrspi-worktree
│       ├── qrspi-implement/
│       │   └── SKILL.md                   # /qrspi-implement
│       └── qrspi-pr/
│           └── SKILL.md                   # /qrspi-pr
├── .qrspi/                                # Artifact output directory (gitignored or committed)
│   └── <ticket-id>/                       # Created per feature
│       ├── ticket.md
│       ├── questions.md
│       ├── research.md
│       ├── design.md
│       ├── structure.md
│       ├── plan.md
│       ├── worktree.md
│       ├── impl-log.md
│       └── pr-summary.md
└── src/
    └── ...
```

Create it:

```bash
mkdir -p .claude/skills/{qrspi-questions,qrspi-research,qrspi-design,qrspi-structure,qrspi-plan,qrspi-worktree,qrspi-implement,qrspi-pr}
mkdir -p .qrspi
```

---

## 2. CLAUDE.md — Project-Level Instructions

This is loaded at the start of every Claude Code session. Keep it lean — it counts against your context budget.

Create `.claude/CLAUDE.md`:

```markdown
# Project: <your-project-name>

## QRSPI Workflow

This project uses the QRSPI structured workflow for feature development.
Artifacts are stored in `.qrspi/<ticket-id>/`.

### Available skills (invoke with / or let Claude auto-invoke)
- `/qrspi-questions <ticket-id>` — Generate technical questions from a ticket
- `/qrspi-research <ticket-id>` — Map the codebase (ticket is hidden)
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

## 3. Skill Files

Each skill is a `SKILL.md` file with YAML frontmatter and markdown instructions. Below are all eight. Copy each into its respective directory.

### 3a. `.claude/skills/qrspi-questions/SKILL.md`

```markdown
---
name: qrspi-questions
description: Generate 8-15 targeted technical questions from a feature ticket. Use when starting a new QRSPI feature workflow or when the user says "questions for" a ticket.
command: /qrspi-questions
argument-hint: <ticket-id>
allowed-tools: Read, Glob, Grep
---

# Questions Phase (Q)

Read the ticket file at `.qrspi/$ARGUMENTS/ticket.md`.

Produce `.qrspi/$ARGUMENTS/questions.md` with 8-15 technical questions.

## Rules
1. Questions must be answerable by reading the codebase, not by speculation.
2. Categorize into: Data Flow, API Surface, State Management, Edge Cases, Testing, Observability.
3. Each question names a specific file, module, or "the module responsible for X".
4. Do NOT propose solutions or architectures.
5. Include at least 2 Edge Cases questions and 1 Observability question.
6. No question uses solution language: "should we", "we could", "best way to".

## Output format
```
# Questions — <ticket title>
**Ticket:** <ticket-id>
**Generated:** <ISO-8601>
**Status:** draft

## Data Flow
- Q1: <question>
  **Target:** <file or module>
...
```

After writing the file, tell the user: "Questions written to `.qrspi/<id>/questions.md`. Review, edit, then tell me 'approved' to proceed to Research."
```

### 3b. `.claude/skills/qrspi-research/SKILL.md`

```markdown
---
name: qrspi-research
description: Map codebase facts by answering questions from the Questions phase. The feature ticket is intentionally hidden. Use after questions are approved.
command: /qrspi-research
argument-hint: <ticket-id>
allowed-tools: Read, Glob, Grep, Bash(find:*), Bash(wc:*), Bash(head:*), Bash(tail:*)
---

# Research Phase (R)

Read `.qrspi/$ARGUMENTS/questions.md`.

CRITICAL: Do NOT read `.qrspi/$ARGUMENTS/ticket.md`. The ticket is intentionally hidden during this phase so you gather objective facts without forming implementation opinions.

Produce `.qrspi/$ARGUMENTS/research.md`.

## Rules
1. Answer each question with FACTS: file paths, function signatures, data types, call chains.
2. Include code snippets (< 20 lines) as evidence with `file:line` citations.
3. Do NOT form opinions about what should change.
4. If a question can't be answered, state "NOT FOUND" with search queries attempted.
5. Document implicit contracts and dependency directions.
6. Note inconsistencies between code and comments/docs.
7. Include a "Discovered Patterns" section and an "Inconsistencies" section.

## Output format
```
# Research — Codebase Map
**Questions source:** questions.md @ <timestamp>
**Generated:** <ISO-8601>
**Status:** draft

## Q1: <question text>
**Answer:** <facts>
**Evidence:** <code + file:line>
**Dependencies:** <upstream/downstream>
**Implicit contracts:** <conventions>
...

## Discovered Patterns
...

## Inconsistencies
...
```

After writing, tell the user: "Research written to `.qrspi/<id>/research.md`. Review for factual accuracy, then tell me 'approved' to proceed to Design."
```

### 3c. `.claude/skills/qrspi-design/SKILL.md`

```markdown
---
name: qrspi-design
description: Produce a design document by combining the ticket, answered questions, and codebase research. Use after research is approved. This is the brain-surgery phase.
command: /qrspi-design
argument-hint: <ticket-id>
allowed-tools: Read, Glob, Grep
---

# Design Discussion Phase (D)

Read ALL THREE inputs:
1. `.qrspi/$ARGUMENTS/ticket.md`
2. `.qrspi/$ARGUMENTS/questions.md`
3. `.qrspi/$ARGUMENTS/research.md`

Produce `.qrspi/$ARGUMENTS/design.md` — target ~200 lines, hard max 300.

## Required sections
1. **Current State** — every claim cites research.md: "(ref: Q1)"
2. **Desired End State** — maps every acceptance criterion to system behavior
3. **Delta** — concrete changes: new files, modified files, new queries
4. **Pattern Decisions** — 2+ options per decision, table format, mark recommendation, flag any NEW PATTERN
5. **Risk Register** — table with likelihood/impact/mitigation, minimum 2 entries
6. **Open Questions** — things only a human can answer

## Rules
1. No code blocks. Prose and tables only.
2. Every Current State sentence must have a `(ref: QN)` citation.
3. Every acceptance criterion from the ticket appears in Desired End State.
4. Pattern Decisions must reference existing codebase patterns from research. Flag new patterns explicitly.
5. Write for editability, not persuasion. The human will rewrite sections.

After writing, tell the user: "Design written to `.qrspi/<id>/design.md`. This is the highest-leverage review — check Pattern Decisions and Current State citations carefully. Edit anything that's wrong, then tell me 'approved'."
```

### 3d. `.claude/skills/qrspi-structure/SKILL.md`

```markdown
---
name: qrspi-structure
description: Define vertical slices, types, and contracts from the approved design. Use after design is approved.
command: /qrspi-structure
argument-hint: <ticket-id>
allowed-tools: Read, Glob, Grep
---

# Structure Outline Phase (S)

Read `.qrspi/$ARGUMENTS/design.md` (must have Status: approved in it or user must have said approved).

Produce `.qrspi/$ARGUMENTS/structure.md`.

## Rules
1. Define new/modified types and function signatures (pseudo-code, not implementations).
2. Organize into VERTICAL SLICES — each delivers a testable end-to-end path.
   - CORRECT: "Slice 1: Mock API → UI component → hardcoded data"
   - WRONG: "Phase 1: All database changes"
3. Each slice has: Goal, Files touched (✨ new / ⚠️ modify), Verification step, Context cost (S/M/L), Dependencies.
4. No slice touches > 10 files. Split if it does.
5. Order slices so dependencies flow forward.
6. Include a Contracts section for cross-slice interfaces.
7. Include an Unverified Assumptions section — claims from design.md you can't map to concrete code.

After writing, tell the user: "Structure written to `.qrspi/<id>/structure.md`. Check slice boundaries and contracts. If any slice is too large, I'll split it. Tell me 'approved' to proceed to Plan."
```

### 3e. `.claude/skills/qrspi-plan/SKILL.md`

```markdown
---
name: qrspi-plan
description: Write atomic implementation steps per vertical slice. Use after structure is approved.
command: /qrspi-plan
argument-hint: <ticket-id>
allowed-tools: Read
---

# Plan Phase (P)

Read:
1. `.qrspi/$ARGUMENTS/structure.md`
2. `.qrspi/$ARGUMENTS/design.md` (for reference only)

Produce `.qrspi/$ARGUMENTS/plan.md`.

## Rules
1. Each step is atomic: one file, one action.
2. Steps reference exact types/signatures from structure.md.
3. ⚠️ steps (modify) include Current and After signatures.
4. ✨ steps (new) name the file and its purpose.
5. Each slice ends with a Verify checkpoint with a runnable command.
6. Total steps ≤ 100. If exceeded, structure slices are too large — stop and say so.
7. Include Rollback Notes for DB migrations, config changes, destructive ops.

After writing, tell the user: "Plan written to `.qrspi/<id>/plan.md`. This should be a spot-check, not a deep review — alignment happened during Design. Tell me 'approved' to proceed to WorkTree."
```

### 3f. `.claude/skills/qrspi-worktree/SKILL.md`

```markdown
---
name: qrspi-worktree
description: Build a session-aware task DAG from the plan. Use after plan is approved.
command: /qrspi-worktree
argument-hint: <ticket-id>
allowed-tools: Read
---

# Work Tree Phase (W)

Read `.qrspi/$ARGUMENTS/plan.md`.

Produce `.qrspi/$ARGUMENTS/worktree.md`.

## Rules
1. Each plan step maps to one task with: ID, Description, Depends On, Plan Step ref, Cost (S/M/L), Status.
2. Group tasks into sessions. Each session has a Load manifest listing ONLY the artifacts needed.
3. Load manifests reference sections, not whole files (e.g., "structure.md §Contracts").
4. Estimated context per session must stay under 40%.
5. Insert SESSION BOUNDARY markers with a Reason between sessions.
6. Identify and list the critical path at the top.

After writing, tell the user: "Work tree written to `.qrspi/<id>/worktree.md`. Review session boundaries — each session will be a fresh `/clear`. Tell me 'approved' to start implementation."
```

### 3g. `.claude/skills/qrspi-implement/SKILL.md`

```markdown
---
name: qrspi-implement
description: Implement one vertical slice per invocation. Always start with a fresh context. Use after worktree is approved or after completing the previous slice.
command: /qrspi-implement
argument-hint: <ticket-id> <slice-number>
allowed-tools: Read, Write, Glob, Grep, Bash
---

# Implement Phase (I)

Parse $ARGUMENTS to extract <ticket-id> and <slice-number>.

Read ONLY these files (context firewall):
1. `.qrspi/<ticket-id>/structure.md` — only §Types, §Contracts, and §Slice <slice-number>
2. `.qrspi/<ticket-id>/plan.md` — only §Slice <slice-number>
3. `.qrspi/<ticket-id>/worktree.md` — only the session for this slice
4. `.qrspi/<ticket-id>/impl-log.md` — only the "Notes for next session" from the previous slice (if any)

Do NOT read the full design, full plan, or earlier slice details beyond the notes.

## Rules
1. Implement ONLY the tasks in this session. Do not anticipate future slices.
2. Match types and signatures from structure.md exactly. If you must deviate, STOP and report before changing.
3. After completing tasks, run the verification command from the plan.
4. If tests fail: fix (max 2 retries). If still failing, report failure with output, hypothesis, and whether it's your code or upstream.
5. Follow existing codebase conventions.
6. Do NOT refactor code outside your slice scope.
7. Append results to `.qrspi/<ticket-id>/impl-log.md`.

## impl-log entry format
```
## Slice <N> — <ISO-8601>
**Tasks completed:** T1, T2, ...
**Tasks failed:** none
**Tests:** <command> → N passed, N failed
**Deviations from structure.md:** none
**Deviations from plan.md:** <describe or "none">
**Notes for next session:** <facts the next slice needs>
```

After completing, tell the user: "Slice <N> implemented. Tests: <result>. Run `/clear` then `/qrspi-implement <ticket-id> <next-slice>` for the next slice, or review the code first."
```

### 3h. `.claude/skills/qrspi-pr/SKILL.md`

```markdown
---
name: qrspi-pr
description: Prepare a pull request summary after all slices are implemented. Use when implementation is complete.
command: /qrspi-pr
argument-hint: <ticket-id>
allowed-tools: Read, Bash(git diff:*), Bash(git log:*)
---

# PR Phase

Read:
1. `.qrspi/$ARGUMENTS/impl-log.md` (full)
2. `.qrspi/$ARGUMENTS/design.md` (for risk register)
3. `.qrspi/$ARGUMENTS/structure.md` (for contracts)
4. Git diff: run `git diff main...HEAD --stat` and `git diff main...HEAD`

Produce `.qrspi/$ARGUMENTS/pr-summary.md`.

## Required sections
1. **Summary** — 3-5 sentences: what changed, why, reviewer focus areas
2. **Acceptance Criteria Mapping** — table: criterion → implementation file → test
3. **Changes by Slice** — table per slice: file, change type, lines changed
4. **Testing Summary** — checklist of verification commands and results
5. **Deviations from Structure** — table (even if empty)
6. **Risks & Rollback** — from design.md risk register, updated with implementation findings
7. **Open Items** — deferred work, tech debt, follow-up tickets

## Rules
1. PR title under 72 characters.
2. Every acceptance criterion from the ticket maps to a file and a test.
3. Every file in the git diff is accounted for in Changes by Slice.

After writing, tell the user: "PR summary at `.qrspi/<id>/pr-summary.md`. Use this as your PR description. Read and own the code before merging."
```

---

## 4. Running the Workflow

### Step 0 — Write the ticket

```bash
mkdir -p .qrspi/DASH-417
cat > .qrspi/DASH-417/ticket.md << 'EOF'
# Ticket: DASH-417

## Title
Add user preference endpoint for notification and display settings

## Description
Users need a dedicated API endpoint to retrieve notification and display
preferences without loading the full profile.

## Acceptance Criteria
- [ ] GET /api/users/:id/preferences returns prefs
- [ ] Response < 200ms p95
- [ ] 401 for unauthenticated, 403 for other users (unless admin)

## Constraints
- Use existing auth middleware
- Use existing user_preferences table

## Out of Scope
- PUT endpoint (separate ticket)
EOF
```

### Step 1 — Questions

```
claude
> /qrspi-questions DASH-417
```

Claude reads the ticket, writes `questions.md`, and asks you to review. Edit the file if needed, then:

```
> approved
```

### Step 2 — Research

```
> /clear
> /qrspi-research DASH-417
```

Claude reads `questions.md` (NOT the ticket), maps the codebase, writes `research.md`. Review for factual accuracy:

```
> approved
```

### Step 3 — Design

```
> /clear
> /qrspi-design DASH-417
```

Claude reads ticket + questions + research, writes `design.md`. **This is your highest-leverage review.** Edit Pattern Decisions, redirect to correct architectural patterns, fix any uncited claims. This is the "brain surgery" step. Then:

```
> approved
```

### Step 4 — Structure

```
> /clear
> /qrspi-structure DASH-417
```

Claude writes vertical slices with contracts. Check that slices are genuinely vertical (end-to-end), not horizontal layers. Then:

```
> approved
```

### Step 5 — Plan

```
> /clear
> /qrspi-plan DASH-417
```

Spot-check only — alignment already happened. Verify test commands are correct. Then:

```
> approved
```

### Step 6 — Work Tree

```
> /clear
> /qrspi-worktree DASH-417
```

Review session boundaries. Each session becomes a separate Claude Code invocation. Then:

```
> approved
```

### Step 7 — Implement (repeat per slice)

```
> /clear
> /qrspi-implement DASH-417 1
```

Claude implements Slice 1 only, runs tests, appends to `impl-log.md`. Review the code. Then start a fresh session for the next slice:

```
> /clear
> /qrspi-implement DASH-417 2
```

Repeat until all slices are done.

### Step 8 — PR

```
> /clear
> /qrspi-pr DASH-417
```

Claude writes `pr-summary.md`. Copy it into your PR description. **Read and own every line of code before merging.**

---

## 5. Context Management During a Session

Use these built-in Claude Code commands throughout:

| Command | When to use |
|---------|-------------|
| `/context` | Check context utilization. If over 40%, take action. |
| `/compact` | Compress conversation history. Use within a phase if context is growing. |
| `/clear` | Full reset. Use between phases and between implementation slices. |
| `/cost` | Check token spend. Useful for budgeting. |

The workflow is designed so that `/clear` between every phase is the default. Each skill loads only the artifacts it needs. This is the primary defense against context degradation.

---

## 6. Handling Revisions

When you reject an artifact (say "revise: <your notes>" instead of "approved"):

1. Claude re-runs the same skill with your notes as additional context.
2. The artifact is overwritten with the revised version.
3. Keep a manual note of what you changed and why — useful for future pipeline tuning.

For substantial design redirects (e.g., "don't use WebSocket, use long-polling"), edit `design.md` directly in your editor, then tell Claude "I've updated design.md, proceed to Structure."

---

## 7. Adapting to Your Project

### Customize test commands

Edit each skill's Verification sections to match your test runner. For example, if you use `pytest` instead of `npm test`:

In `qrspi-plan/SKILL.md`, change the example verify command convention. In `qrspi-implement/SKILL.md`, update the verification instructions.

### Customize allowed tools

Each skill's `allowed-tools` frontmatter controls what Claude can do. The Research and Design phases intentionally restrict to read-only tools. Implementation opens up `Bash` and `Write`. Adjust these per your security requirements.

### Add project conventions to CLAUDE.md

Your `.claude/CLAUDE.md` should include project-specific patterns: naming conventions, directory layout, preferred libraries, test patterns. The Research agent will discover these from the codebase, but explicit documentation reduces hallucination.

### Team sharing

Commit `.claude/skills/` to your repo. Every team member gets the same workflow. Artifact outputs in `.qrspi/` can be committed too — they serve as design documentation for the feature.

---

## 8. Troubleshooting

**"Claude skipped a section in the artifact"**
The skill prompt may be too long. Check that each `SKILL.md` is under 500 lines and under ~40 distinct instructions. The instruction budget ceiling is real.

**"Claude read the ticket during Research"**
The Research skill explicitly says not to. If it still does, add `ticket.md` to a `.gitignore`-style exclusion, or temporarily move it out of the `.qrspi/<id>/` directory during research.

**"Context is degrading mid-implementation"**
Run `/context`. If over 40%, run `/compact` or `/clear` and restart the current slice. The worktree's session boundaries are designed to prevent this — respect them.

**"Claude invented a pattern not in the codebase"**
This should be caught during Design review. The `(ref: QN)` citation requirement makes uncited claims visible. If it slips through, the Structure agent's "Unverified Assumptions" section is the second safety net.

**"Slices feel too large"**
If a slice touches > 10 files or takes a full context window, go back to Structure and split it. The workflow supports re-running any phase.
