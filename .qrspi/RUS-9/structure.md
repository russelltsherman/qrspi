# Structure — using-claude-cli skill

**Ticket:** RUS-9
**Generated:** 2026-05-26
**Status:** draft

## Types & Signatures (Pseudo-code)

This is a content-only skill (no runtime code). The "types" here are the file structures and schemas.

### SKILL.md Frontmatter Schema

```yaml
name: using-claude-cli           # kebab-case identifier
description: |                   # max 1024 chars, imperative trigger style
  Use when the user asks about Claude CLI flags, modes, invocation patterns,
  sub-agent spawning, session management, or script-level orchestration.
  Trigger on: 'run claude', 'spawn a subagent', 'claude headless',
  'claude bare mode', 'claude session', 'claude MCP config',
  'claude permission rules', 'claude cost control', ...
command: using-claude-cli        # slash command for explicit invocation
argument-hint: <topic>           # placeholder shown in help
allowed-tools: Read, Glob, Grep, Bash(claude:*), Bash(cat:*), Bash(jq:*)
```

### SKILL.md Body Structure (~200 lines target)

```
# using-claude-cli

## CLI Modes (interactive / headless / bare)          # core topics
## Sub-Agent Spawning (built-in / custom types)       # core topics
## Session Management (continue / resume / name)      # core topics
## Output Formats (text / json / stream-json)         # core topics
## Cost Control (--max-budget-usd / --max-turns)      # core topics

For deep reference:
  Advanced flag tables, Read `references/advanced-flags.md`
  Hook event types and configuration, Read `references/hooks-config.md`
  Multi-agent orchestration patterns, Read `references/agent-teams.md`
  Permission rule patterns and settings hierarchy, Read `references/permission-patterns.md`
```

### Reference File Schema (flat `references/` directory)

Each reference file follows:

```markdown
# <Topic Title>
<!-- last-verified: 2026-05-26 -->

## <Subsection>
<Flag table or pattern with examples>
```

### Eval Case Schema (graphite-evals.json format)

```json
{
  "id": number,
  "prompt": string,
  "expected_output": string,
  "files": [],
  "assertions": [
    { "text": string, "type": "command_check" | "flag_check" | "content_check" | "safety_check" | "workflow_check" }
  ]
}
```

## Contracts

### Contract 1: SKILL.md -> Reference files

The SKILL.md body references each reference file by relative path with explicit Read instructions. Every file mentioned in a Read instruction MUST exist in `references/` and every file in `references/` MUST be mentioned in the SKILL.md body.

### Contract 2: Main body line budget

The SKILL.md body (excluding frontmatter and frontmatter separator) MUST stay under 500 lines. The design targets ~200 lines by pushing detailed flag tables and advanced patterns into reference files.

### Contract 3: Eval coverage

Each major section in the SKILL.md body (CLI modes, sub-agents, sessions, output formats, cost control) must have at least one eval case testing whether the skill produces correct guidance for that topic.

### Contract 4: skill-creator validation

The completed skill must pass the skill-creator's eval loop, meaning frontmatter fields are well-formed, body is under 500 lines, and trigger description matches test prompts with high recall.

### Contract 5: Experimental feature marking

The agent-teams reference file must include an explicit experimental status warning and the runtime requirement `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`.

## Vertical Slices

### Slice 1: Core skill files (SKILL.md + 4 references + CLAUDE.md update)

**Goal:** Create the complete `using-claude-cli` skill directory with SKILL.md covering the five core topics (CLI modes, sub-agents, sessions, output formats, cost control) and four reference files for advanced content. Update project `.claude/CLAUDE.md` to register the new skill. This is one cohesive unit — the SKILL.md body explicitly references each reference file, the reference files provide the deep content that keeps the main body under 500 lines, and no reference is independently testable without the main skill to load it.

**Files touched:**
- `NEW` `.claude/skills/using-claude-cli/SKILL.md` (~200 lines, core topics)
- `NEW` `.claude/skills/using-claude-cli/references/advanced-flags.md` (advanced CLI flags, mode-dependent behavior tables)
- `NEW` `.claude/skills/using-claude-cli/references/hooks-config.md` (hook event types, configuration, exit codes, use cases)
- `NEW` `.claude/skills/using-claude-cli/references/agent-teams.md` (multi-agent orchestration, worktrees, background agents, experimental warning)
- `NEW` `.claude/skills/using-claude-cli/references/permission-patterns.md` (permission rule syntax, settings hierarchy, CI/CD examples)
- `MODIFY` `.claude/CLAUDE.md` (add using-claude-cli to the available skills list)

**Verification:**
- SKILL.md body line count < 500 (target ~200)
- SKILL.md frontmatter contains all five required fields
- Every reference file exists and is referenced from SKILL.md body via Read instructions
- Reference files cover: advanced flags with mode-dependent tables, hook config, agent teams (with experimental warning), permission patterns
- CLAUDE.md includes the new skill in the available skills list
- skill-creator invoked for scaffolding then hand-edited to match project style (PD-3)

**Context cost:** L (5 new files, substantial content authoring, skill-creator scaffolding iteration)

**Dependencies:** None

### Slice 2: Eval cases

**Goal:** Create eval cases that exercise the skill's trigger matching and content accuracy across all five core topic areas.

**Files touched:**
- `NEW` `evals/claude-cli-evals.json` (one case per core topic area)

**Verification:**
- Eval file parses as valid JSON
- At least 5 test cases (one per core topic: CLI modes, sub-agents, sessions, output formats, cost control)
- Assertions use types from the graphite-evals.json pattern (command_check, flag_check, content_check, safety_check)
- Each eval tests a distinct section of the SKILL.md body

**Context cost:** M (1 new file)

**Dependencies:** Slice 1 (needs the skill to exist before it can be evaluated)

## Unverified Assumptions

1. **`Bash(claude:*)` pattern works in allowed-tools** — The design notes this is a new pattern not used by any existing skill. If the Claude Code permission system does not support this glob, the skill will need to either drop Bash access entirely (pure advisory) or use a different pattern. Cannot verify without a live runtime test.

2. **`command` field is harmless for an auto-trigger skill** — PD-3 recommends using `command: using-claude-cli` even though the skill is primarily auto-triggered via description matching. This keeps the schema uniform but means a slash command `/using-claude-cli` may appear in help without being functional. Cannot verify without a runtime test.

3. **Five reference files is within practical context limits** — No existing skill in this project has more than one reference file. The design asserts four is justified by subject breadth, but there is no precedent for whether Claude Code handles multiple reference pointers gracefully (context budget, progressive loading).

4. **skill-creator produces compatible scaffolding** — PD-3 recommends using skill-creator for scaffolding then hand-editing. skill-creator is a system-level capability with unknown implementation details. If it diverges significantly from the established five-field pattern, the hand-editing effort increases. The eval loop with skill-creator may also have assumptions about QRSPI workflow skills that do not apply to an advisory skill.

5. **agentskills.io standard does not exist** — Research Q1 confirmed zero evidence of this standard in the codebase. The implementation defaults to the established 5-field pattern. If a real external standard exists, the skill may need revision. The design notes this risk as "high likelihood, medium impact."

6. **CLI flags in the skill match a live Claude Code instance** — The ticket's conventions come from a specification that is unverified within this codebase. Documentation accuracy depends on the actual Claude CLI behavior, which requires a live instance to validate.
