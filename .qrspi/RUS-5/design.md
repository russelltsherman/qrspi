# Design — Create a new agent skill called writing bash scripts

**Ticket:** RUS-5
**Research basis:** research.md @ 2026-05-30
**Generated:** 2026-05-30
**Status:** draft

## Current State

The `writing-bash-scripts` skill already exists as a global skill at `~/.claude/skills/writing-bash-scripts/` (273 lines) with a complete directory structure: `SKILL.md` plus four reference files (`conventions.md`, `gotchas.md`, `patterns.md`, `template.sh`) (ref: Q4). The skill was likely created by a prior agent session (RUS-1 through RUS-4), making this ticket appear to be a duplicate request or a refinement mandate (ref: Q4, ref: Q5).

The skill follows the skill-creator recommended directory schema (name + description frontmatter, `references/` subdirectory) but deviates from the ticket's stated conventions in a few ways (ref: Q1, ref: Q2):

- Logging helper naming uses `log_info()`/`log_warn()`/`log_error()` instead of the ticket's `log()`/`info()`/`warn()`/`die()` convention (ref: Q11).
- The ~200-line threshold with language-switching guidance is not encoded anywhere in the skill body or references (ref: Q7).
- ShellCheck evaluation is a manual instruction in SKILL.md but there is no automated check or even ShellCheck installed in the environment (ref: Q8, ref: Inconsistency 6).
- The bash 4+ version check lives in `references/conventions.md` (a detail file) rather than the SKILL.md body (ref: Inconsistency 2).
- No BATS scaffolding files are bundled; BATS is only recommended inline (ref: Q9).
- The skill does not encode a "gotchas" section -- it has a `references/gotchas.md` file but the ticket asks for an inline gotchas section (ref: Q6).

Two-tier skill architecture exists: global skills at `~/.claude/skills/` (no slash commands, register via frontmatter description) and project skills at `.claude/skills/` (slash command wrappers like `/qrspi-*`) (ref: Q3, ref: Discovered 1, ref: Discovered 6).

The `skill-creator` skill is available and structured as a guided workflow (capture intent, interview, write SKILL.md, eval, iterate) but does NOT produce a ready-to-save SKILL.md file (ref: Q5, ref: Discovered 7).

## Desired End State

- [ ] Skill follows agentskills.io directory structure with valid SKILL.md frontmatter: `SKILL.md` at the root with YAML frontmatter (name, description), optional `references/` directory with detailed content, optional `scripts/` or `assets/` (ref: Q2, ref: Discovered 1)
- [ ] Built using the Anthropic skill-creator skill: the skill-creator workflow (intent capture, SKILL.md drafting, eval loop) is used as the creation method (ref: Q1, ref: Q5)
- [ ] SKILL.md body under 500 lines / 5000 tokens: currently 273 lines, within the constraint (ref: Q10, ref: Discovered 2)
- [ ] Detailed reference material in `references/` directory: four reference files exist (`conventions.md`, `gotchas.md`, `patterns.md`, `template.sh`) (ref: Q4, ref: Discovered 4)
- [ ] Produces ShellCheck-clean output when an agent follows the guidance: SKILL.md instructs agents to run ShellCheck, but no automated enforcement exists (ref: Q8)

If the ticket is confirmed as a refinement (not a duplicate), the desired end state also includes:
- Encoding the ~200-line scope limit with language-switching criteria
- Renaming or documenting the logging helper convention to match the ticket spec
- Adding BATS scaffolding files to `references/` or a new `scripts/` directory
- Consolidating the bash 4+ version check into the SKILL.md body

## Delta

### If this is a refinement of the existing skill:

**Modified files:**
- `~/.claude/skills/writing-bash-scripts/SKILL.md` -- add scope guidance section (~200-line threshold with Python/Go switching checklist), reconcile logging helper names, consolidate bash version check from references into body
- `~/.claude/skills/writing-bash-scripts/references/conventions.md` -- update logging convention naming, remove duplicated bash version check (now in SKILL.md body)

**New files:**
- `~/.claude/skills/writing-bash-scripts/references/bats-template.bats` -- BATS scaffolding for common patterns (setup, teardown, assertion helpers)
- `~/.claude/skills/writing-bash-scripts/scripts/install-bats.sh` -- cross-platform BATS install script (Homebrew + source install)

### If this is a fresh creation (unlikely given research):

**New directory structure:**
```
~/.claude/skills/writing-bash-scripts/
├── SKILL.md          (200-300 lines)
├── references/
│   ├── conventions.md (detailed conventions beyond SKILL.md body)
│   ├── gotchas.md     (portability pitfalls)
│   ├── patterns.md    (code patterns with copy-paste examples)
│   ├── template.sh    (full structural example)
│   └── bats-template.bats (new: BATS scaffolding)
└── scripts/
    └── install-bats.sh (new: BATS installer)
```

## Pattern Decisions

### Decision 1: Refine vs. Replace

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Refine the existing skill | Preserves 273 lines of work, minimal disruption | Must reconcile naming mismatches and missing conventions |
| B | Replace with a fresh skill from scratch via skill-creator | Clean slate, fully aligned with ticket specs | Wastes existing work, higher risk of regression |

**Recommendation:** Option A (refine)
**Rationale:** The existing skill already covers 80%+ of the ticket's conventions (strict mode, quoting, error handling, subcommand pattern, temp files, logging helpers). The gaps are narrow: scope guidance, logging naming, and BATS scaffolding. Refactoring in place is lower risk and preserves the reference files that agents already depend on (ref: Q4).
**NEW PATTERN?** No.

### Decision 2: Logging Helper Naming

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Use ticket spec: `log()`, `info()`, `warn()`, `die()` | Matches ticket requirements exactly, simpler names | Breaks existing scripts using `log_info()`/`log_warn()`/`log_error()` |
| B | Keep existing: `log_info()`, `log_warn()`, `log_error()` | Backwards compatible with existing scripts | Deviates from ticket specification, creates naming inconsistency |
| C | Support both: alias `log_info` to `info`, etc. | Best of both worlds | Adds indirection, increases skill complexity |

**Recommendation:** Option A
**Rationale:** This is a skill definition, not a deployment to existing scripts. The convention the skill encodes is the canonical reference; scripts following it should adopt the convention. The existing skill's naming was likely a drafting oversight (ref: Q11, ref: Inconsistency 4).
**NEW PATTERN?** No -- the skill already defines a logging convention, just needs alignment.

### Decision 3: Bash Version Enforcement Location

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Keep in `references/conventions.md` | Keeps SKILL.md body shorter | Agents may miss the requirement (it's a reference file, not always loaded) |
| B | Move to SKILL.md body | Harder to miss, becomes a primary convention | Increases SKILL.md body length |
| C | Keep in conventions.md but cross-reference from SKILL.md body | Best of both: discoverable from body, detail in references | Slightly more complex document structure |

**Recommendation:** Option C
**Rationale:** SKILL.md body should mention the bash 4+ requirement as a hard constraint with a link to the `check_bash_version()` function in `references/conventions.md` (ref: Q6, ref: Inconsistency 2).
**NEW PATTERN?** No.

### Decision 4: BATS Scaffolding Depth

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Inline BATS example only (current state) | Minimal, no extra files | Agents must figure out BATS setup themselves |
| B | Add `bats-template.bats` with common patterns + `install-bats.sh` | Drop-in scaffolding, reduces friction | More files to maintain |
| C | Full BATS project template (Makefile, CI integration) | Complete solution | Over-engineered for a skill's reference material |

**Recommendation:** Option B
**Rationale:** The ticket explicitly recommends BATS for testable scripts but the current skill only gives an inline example. A minimal scaffold (setup/teardown/assertion helpers) plus an install script bridges the gap between recommendation and usability without over-committing (ref: Q9, ref: Inconsistency 3).
**NEW PATTERN?** No -- BATS is already recommended; this adds supporting files.

### Decision 5: Scope Enforcement (200-line threshold)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Add an inline checklist in SKILL.md: "if script >200 lines, consider Python/Go" | Simple, always visible | Advisory only, easy to ignore |
| B | Add a decision tree with concrete criteria (I/O complexity, data structures, etc.) | Actionable, specific | More content, may be opinionated |
| C | No explicit encoding -- leave as agent judgment | Zero complexity | Ticket explicitly asks for this guidance |

**Recommendation:** Option B
**Rationale:** The ticket says "never exceed ~200 lines without strong justification" -- this is a hard convention, not a suggestion. A concrete decision tree (e.g., "using more than 3 associative arrays?" "parsing JSON?" "building a web server?") gives agents actionable criteria rather than a vague line count (ref: Q7).
**NEW PATTERN?** Partially -- the skill already has conventions but not scope-exit criteria.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Ticket is a duplicate and work should be abandoned | medium | low | Confirm with human before investing in refinement. Check Linear history for RUS-5 closure status. |
| Refactoring breaks existing agents that depend on current naming (`log_info`/`log_warn`) | low | medium | Use option A for logging naming (follows ticket spec exactly) -- since this is a skill definition, not a deployed library, existing scripts just need to adopt the new convention on next rewrite. |
| ShellCheck not installed in environment means acceptance criteria cannot be verified | high | medium | Add a note that ShellCheck must be installed locally. The skill's guidance is the artifact, not an automated gate. Document this explicitly. |
| macOS bash 3.2 incompatibility affects skill usability | medium | medium | The skill already enforces bash 4+. Add a warning in the SKILL.md body about Homebrew `bash` installation on macOS (ref: Q6). |
| Skill body grows beyond 500 lines during refinement | low | low | The current SKILL.md is 273 lines with ~150 lines of headroom. Scope guidance + naming changes + BATS references should fit within budget. Monitor line count during implementation. |

## Open Questions

- OQ1: Is RUS-5 a duplicate of work already completed (the skill exists), or is the ticket explicitly asking for a refinement pass? A human should confirm before investing in design-to-implementation.
- OQ2: Should the `writing-bash-scripts` skill be a global skill (`~/.claude/skills/`) or a project skill (`.claude/skills/` in the qrspi repo)? The current placement is global -- changing it affects cross-project availability.
- OQ3: The ticket says "Built using the Anthropic skill builder skill" -- should the skill-creator workflow be explicitly invoked for this refinement, or is manual editing sufficient given the existing skill is already well-structured?
