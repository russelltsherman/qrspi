# Plan — Create the `using-claude-cli` skill

**Ticket:** RUS-9
**Generated:** 2026-05-26
**Status:** draft

---

## Slice 1: Core skill files (SKILL.md + 4 references + CLAUDE.md update)

### Step 1: Scaffold skill directory

Create `.claude/skills/using-claude-cli/` and `.claude/skills/using-claude-cli/references/` directories.

**Verify:** `ls .claude/skills/using-claude-cli/references/` shows the empty references directory.

---

### Step 2: Invoke skill-creator for SKILL.md scaffold

Invoke the `skill-creator` skill to generate a SKILL.md scaffold with the five-field frontmatter pattern. Pass the topic "Claude CLI invocation patterns: modes, sub-agents, sessions, output formats, cost control" as the initial description.

**After skill-creator completes:** Review the output SKILL.md. If frontmatter deviates from the five-field pattern (name, description, command, argument-hint, allowed-tools), hand-edit to match.

**Accept:** `.claude/skills/using-claude-cli/SKILL.md` exists with valid frontmatter.

---

### Step 3: Write SKILL.md body — five core topics

Write the SKILL.md body covering the five core topics from structure.md's body structure:

1. **CLI Modes** (interactive / headless / bare) — mode dispatch table, when to use each, key flags per mode
2. **Sub-Agent Spawning** (built-in types: Explore, Plan, General-purpose; custom types via frontmatter)
3. **Session Management** (continue, resume, name, fork, no-persistence)
4. **Output Formats** (text, json, stream-json with jq extraction guidance)
5. **Cost Control** (--max-budget-usd, --max-turns, --model, --effort)

Body targets ~200 lines. Push advanced flag tables, hook config, agent teams, and permission patterns into reference files via Read instructions.

**Current:** File does not exist yet (new).
**After:** `.claude/skills/using-claude-cli/SKILL.md` with frontmatter (5 fields) and body (~200 lines) covering five topics, with four Read instructions to reference files.

**Line budget check:** Count body lines (excluding frontmatter and separator). Must be < 500.

**Verify:** `wc -l .claude/skills/using-claude-cli/SKILL.md` shows body < 500 lines.

---

### Step 4: Write references/advanced-flags.md

Create `.claude/skills/using-claude-cli/references/advanced-flags.md` with:

- Advanced CLI flag tables organized by mode (interactive, headless, bare)
- Mode-dependent behavior tables (e.g., flags that are exclusive to bare mode)
- Mutually exclusive flag combinations
- Flag tables follow the structure.md pattern: header row, mode columns

**Current:** File does not exist yet (new).
**After:** Reference file with mode-dependent flag tables.

---

### Step 5: Write references/hooks-config.md

Create `.claude/skills/using-claude-cli/references/hooks-config.md` with:

- Hook event types and their payloads
- Configuration schema (settings.json / settings.local.json paths)
- Exit code meanings
- Use case examples per hook event type

**Current:** File does not exist yet (new).
**After:** Reference file with hook configuration details.

---

### Step 6: Write references/agent-teams.md

Create `.claude/skills/using-claude-cli/references/agent-teams.md` with:

- Multi-agent orchestration patterns (teams, task lists, inter-agent coordination)
- Worktree-based parallel work patterns
- Background agent patterns
- **Required:** Explicit experimental status warning at the top: "**Experimental:** Agent Teams require `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`"

**Current:** File does not exist yet (new).
**After:** Reference file with experimental warning prominently displayed.

**Contract 5 check:** The experimental warning must be present.

---

### Step 7: Write references/permission-patterns.md

Create `.claude/skills/using-claude-cli/references/permission-patterns.md` with:

- Permission rule syntax (allowed-tools, disallowed-tools, Bash patterns)
- Settings hierarchy (global CLAUDE.md -> project CLAUDE.md -> settings.json -> settings.local.json)
- CI/CD configuration examples
- Common patterns for scripting (commit automation, code review, piped analysis)

**Current:** File does not exist yet (new).
**After:** Reference file with permission patterns and CI/CD examples.

---

### Step 8: Update project CLAUDE.md to register the new skill

Append `using-claude-cli` to the available skills list in `.claude/CLAUDE.md`:

```markdown
- `/using-claude-cli <topic>` — Claude CLI invocation patterns: modes, subagents, sessions, cost control, permissions
```

**Current:** `.claude/CLAUDE.md` lists existing skills but not `using-claude-cli`.
**After:** `.claude/CLAUDE.md` includes the new skill in the available skills list.

---

### Step 9: Verify Slice 1 contracts

Run all verification checks from structure.md Slice 1:

1. **Body line count:** `awk '/^---$/,0' .claude/skills/using-claude-cli/SKILL.md | wc -l` should show body < 500 lines.
2. **Frontmatter fields:** Confirm five fields present: name, description, command, argument-hint, allowed-tools.
3. **Reference file existence:** All four files exist in `references/`.
4. **Read instruction coverage:** SKILL.md body contains Read instructions for all four reference files.
5. **Reference file content:** Each reference file covers its topic (advanced flags with mode tables, hook config, agent teams with experimental warning, permission patterns).
6. **CLAUDE.md update:** Skill appears in the available skills list.

**Verify command:**
```bash
echo "=== Line count ===" && awk '/^---$/,0' .claude/skills/using-claude-cli/SKILL.md | wc -l && echo "=== Frontmatter fields ===" && grep -cE '^(name|description|command|argument-hint|allowed-tools):' .claude/skills/using-claude-cli/SKILL.md && echo "=== Reference files ===" && ls .claude/skills/using-claude-cli/references/ && echo "=== Read instructions ===" && grep 'Read.*references/' .claude/skills/using-claude-cli/SKILL.md && echo "=== CLAUDE.md ===" && grep 'using-claude-cli' .claude/CLAUDE.md
```

---

## Slice 2: Eval cases

### Step 10: Create eval cases for all five core topics

Create `evals/claude-cli-evals.json` with at least 5 test cases — one per core topic area:

1. **CLI modes** — prompt asking about headless/bare mode invocation
2. **Sub-agents** — prompt asking about spawning sub-agents
3. **Sessions** — prompt about continuing/resuming sessions
4. **Output formats** — prompt about JSON output with jq
5. **Cost control** — prompt about budget/turn limits

Each case follows the graphite-evals.json schema from structure.md:

```json
{
  "id": number,
  "prompt": string,
  "expected_output": string,
  "files": [],
  "assertions": [
    {"text": string, "type": "command_check" | "flag_check" | "content_check" | "safety_check" | "workflow_check"}
  ]
}
```

**Current:** File does not exist yet (new). Eval file wraps in `{"skill_name": "claude-cli", "evals": [...]}` wrapper similar to graphite-evals.json.
**After:** Valid JSON file with 5+ eval cases, each testing a distinct section of the SKILL.md body.

**Verify command:**
```bash
python3 -c "import json; d=json.load(open('evals/claude-cli-evals.json')); print(f'Valid JSON, {len(d[\"evals\"])} evals')"
```

---

### Step 11: Verify Slice 2 contracts

Run all verification checks from structure.md Slice 2:

1. **Valid JSON:** File parses without errors.
2. **Coverage:** At least 5 test cases, one per core topic.
3. **Assertion types:** Cases use types from the schema (command_check, flag_check, content_check, safety_check).
4. **Distinct sections:** Each eval maps to a different SKILL.md body section.

**Verify command:**
```bash
python3 -c "
import json
d = json.load(open('evals/claude-cli-evals.json'))
cases = d['evals']
print(f'Case count: {len(cases)}')
topics = [c['assertions'][0]['text'][:40] for c in cases]
for t in topics: print(f'  - {t}')
types = set(a['type'] for c in cases for a in c['assertions'])
print(f'Assertion types: {types}')
"
```

---

## Rollback Notes

- This slice creates new files only. No existing code is modified except `.claude/CLAUDE.md` (append-only skill list).
- If a reference file needs to be removed, simply delete it from `references/` and remove the corresponding Read instruction from SKILL.md.
- If the SKILL.md body exceeds 500 lines, move additional content to a reference file rather than deleting content.
- No database migrations, no config schema changes, no destructive operations.

## Unverified Assumptions (from structure.md)

These assumptions are carried forward from the structure phase and should be validated during implementation:

1. **Assumption 1:** `Bash(claude:*)` pattern works in allowed-tools — new pattern, not used by any existing skill.
2. **Assumption 2:** `command` field is harmless for an auto-trigger skill — slash command may appear in help without being functional.
3. **Assumption 3:** Five reference files is within practical context limits — no existing skill has more than one reference file.
4. **Assumption 4:** skill-creator produces compatible scaffolding — system-level capability with unknown implementation details.
5. **Assumption 5:** agentskills.io standard does not exist — implementation defaults to the established 5-field pattern.
6. **Assumption 6:** CLI flags in the skill match a live Claude Code instance — requires runtime validation.
