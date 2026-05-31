# Implementation Plan — Create a new agent skill called using-claude-cli

**Structure basis:** structure.md @ 2026-05-31
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft
**Total steps:** 38

## Slice 1: Skill scaffold + SKILL.md + references/

### Setup

1. ✨ Create directory `.claude/skills/using-claude-cli/` and subdirectory `.claude/skills/using-claude-cli/references/`. Action: `mkdir -p .claude/skills/using-claude-cli/references` from the worktree root.
2. (Side-session) Open a separate Claude Code session and invoke the global `skill-creator` skill with the goal "produce a skill named `using-claude-cli` covering Claude Code CLI usage". Capture the produced SKILL.md scaffold as the starting point for step 3. (Per design.md §Decision 5: skill-creator is global and not in-repo; this step satisfies AC #2.)

### Core Logic

3. ✨ Create `.claude/skills/using-claude-cli/SKILL.md` — populate with the five-key frontmatter and body. Frontmatter exactly:
   - `name: using-claude-cli`
   - `description: Guide for using the Claude Code CLI (interactive, headless/print, bare modes), spawning sub-agents, managing sessions, configuring MCP servers, setting permissions, and controlling cost. Use when an agent or user needs to orchestrate Claude Code from the shell, a script, or CI.`
   - `command: /using-claude-cli`
   - `argument-hint: [topic]`
   - `allowed-tools: Read`
   Body sections (in order): "When to use this skill", "CLI modes" (interactive, headless/print, bare with worked examples), "Sub-agent spawning" (overview + link to references/subagents.md), "Session management" (overview + link), "MCP servers" (overview + link), "Permissions" (overview + link), "Cost control" (overview + link), "Common orchestration patterns" (short example + link to references/orchestration-patterns.md), "Reference index" (canonical pointer list to every references/*.md file with one-line summary), "Cross-skill non-overlap" (note that `update-config` owns settings.json edits and `/code-review` owns code review workflows). Hard cap: 500 lines. Use no code longer than 10 lines inline — push longer examples into references/.

4. ✨ Create `.claude/skills/using-claude-cli/references/cli-reference.md` — enumerate every CLI flag mentioned in the ticket grouped by mode and concern. Sections: "Interactive mode flags", "Print mode flags", "Bare mode flags", "Output format flags" (`--output-format text|json|stream-json`, `--json-schema`, `--include-partial-messages`, `--verbose`), "Session flags" (`-c`, `-r`, `-n`, `--continue`, `--resume`, `--fork-session`, `--no-session-persistence`), "Permission flags" (`--allowedTools`, `--disallowedTools`, `--permission-mode`), "Prompt customization" (`--append-system-prompt`, `--append-system-prompt-file`, `--system-prompt`, `--system-prompt-file`), "Cost flags" (`--max-budget-usd`, `--max-turns`, `--model`, `--effort`), "MCP flags" (`--mcp-config`, `--strict-mcp-config`, `--agents`). Each flag entry: signature, allowed values, example. Mark any flag whose behavior is unverified-against-current-CLI with `[VERIFY]`.

5. ✨ Create `.claude/skills/using-claude-cli/references/subagents.md` — sections: "Built-in subagents" (Explore, Plan, General-purpose — what each can/can't do), "Custom subagents" (frontmatter shape mirroring the in-repo `.claude/agents/*.md` precedent: name, description, model, claude.tools — show the qrspi-questions.md frontmatter as an illustrative example), "Ephemeral subagents via `--agents '{JSON}'`", "When to use a subagent vs an agent team", "Hard rule: subagents cannot spawn subagents". Include a worked example dispatching a built-in Explore subagent.

6. ✨ Create `.claude/skills/using-claude-cli/references/sessions.md` — sections: "Session lifecycle" (create, persist, resume, fork, delete), "Flags reference" (`-c`, `-r <id|name>`, `-n <name>`, `--continue`, `--resume`, `--fork-session`, `--no-session-persistence`), "Persistence layout" (`~/.claude/projects/<url-encoded-path>/`), "Capturing session_id from JSON output" with a `jq` recipe: `session_id=$(claude -p "task" --output-format json | jq -r '.session_id')`, "Multi-turn orchestration recipes" (two examples: branching review of a draft, follow-up question on a long-running task).

7. ✨ Create `.claude/skills/using-claude-cli/references/mcp.md` — sections: "Config precedence" (`.mcp.json` project-level > `~/.claude.json` user-level > `--mcp-config` session-level), "Strict mode" (`--strict-mcp-config` ignores all other configs), "Permission rules for MCP tools" (`mcp__<server>__<tool>` pattern — show the in-repo Linear example `mcp__linear-russelltsherman__get_issue`), "Adding a server" (`claude mcp add <name>` and the requirement to restart Claude Code), "Bare-mode behavior" (servers must be passed explicitly via `--mcp-config`).

8. ✨ Create `.claude/skills/using-claude-cli/references/permissions.md` — sections: "Permission modes" (table of `default`, `acceptEdits`, `plan`, `auto`, `dontAsk`, `bypassPermissions` with description + when-to-use), "Rule syntax" (`Tool` and `Tool(specifier)` with glob wildcards; evaluation order deny → ask → allow), "Headless flags" (`--allowedTools`, `--disallowedTools` with example `"Bash(git diff *),Read,Edit"`), "Settings hierarchy" (Managed > CLI args > Local project > Shared project > User settings), "Auto-approved read-only commands" (`ls`, `cat`, `echo`, `pwd`, `head`, `tail`, `grep`, `find`, `wc`, `which`, `diff`, `stat`, `du`, `cd`, read-only `git`), "Sandboxing" (OS-level filesystem/network isolation; complementary to permissions, not a replacement). Include a cross-reference: "For mutating settings.json, see the global `update-config` skill."

9. ✨ Create `.claude/skills/using-claude-cli/references/hooks.md` — sections: "Hook events" (PreToolUse, PostToolUse, UserPromptSubmit, SessionStart, SessionEnd, Notification, Stop, SubagentStop, PreCompact, TeammateIdle, TaskCreated, TaskCompleted — with one-line purpose each), "Matcher syntax" (`"Edit|Write"` to match specific tools; empty matcher = all), "Exit codes" (0 = proceed, 2 = block, 1 = non-blocking error), "Configuration location" (`~/.claude/settings.json`, `.claude/settings.json`, `.claude/settings.local.json` — precedence per the permissions reference), "Example: auto-format after edits" (PostToolUse on `Edit|Write` running `prettier --write $TOOL_INPUT_path`), "Example: enforce project rules" (PreToolUse blocking risky operations), "Example: inject context at session start" (SessionStart), "Example: notify when input is needed" (Stop). Include a note about prompt-based / agent-based hooks for judgment-based evaluation.

10. ✨ Create `.claude/skills/using-claude-cli/references/agent-teams.md` — sections: "Experimental status" (set `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in env or settings; document as experimental, behavior may change), "Team vs subagent decision tree" (teams when agents must communicate/coordinate; subagents when only results matter), "Team communication mechanisms" (shared task list, inter-agent messaging via mailbox, idle notifications), "Worktrees" (`claude -w <name>` creates an isolated worktree for parallel work — note: verify exact flag against current CLI), "Background agents" (`claude agents` to monitor/dispatch parallel sessions; `claude --bg "prompt"` to start one), "Teammate display" (in-process Shift+Down cycle vs split-pane via tmux/iTerm2), "Subagent definitions as teammate roles" (reference an agent type by name when spawning teammates), "Cost note" (teams use significantly more tokens; start with 3-5 teammates).

11. ✨ Create `.claude/skills/using-claude-cli/references/orchestration-patterns.md` — five copy-paste recipes: (a) "Commit automation" — using `claude -p` headless to draft a commit message from a `git diff`; (b) "Code review" — link to `/code-review` skill and show a piped `git diff | claude -p` recipe with `--allowedTools "Read"`; (c) "Piped analysis" — `cat data.json | claude -p "summarize" --output-format json | jq`; (d) "Structured JSON extraction" — full session_id capture pattern with `jq -r '.session_id'`; (e) "GitHub Actions CI/CD" — a 15-25 line YAML snippet showing `claude --bare -p` with `--allowedTools`, `--max-budget-usd`, and `--output-format json`. Each example is preceded by an `--allowedTools` callout per design.md §Risk Register.

12. ✨ Create `.claude/skills/using-claude-cli/references/frontmatter.md` — sections: "Required fields" (the five-field in-repo convention with description of each), "Optional agentskills.io fields" (`version`, `tags`, `license` — when to use, none currently used in this repo), "When to set `model`" (agents always; skills never — cross-reference `.claude/agents/qrspi-questions.md` as the in-repo example), "When to use `claude.tools` allow-list" (only on agents).

13. ✨ Create `.claude/skills/using-claude-cli/references/build-notes.md` — one paragraph: "This skill was authored using the global `skill-creator` skill in a side session on <date>, then committed to this repo. The skill-creator skill is installed globally (not in `REPO_ROOT/.claude/skills/`); see <link to skill-creator docs> for details on its production process."

14. ⚠️ Modify `.claude/CLAUDE.md` — add a single bullet to the "Available skills" list announcing `/using-claude-cli`.
   - **Current:** the bullet list does not mention `/using-claude-cli`.
   - **After:** the bullet list contains a line `- `/using-claude-cli [topic]` — Guide for using the Claude Code CLI; pass an optional topic for deeper reference content`.

### Tests

15. Run: `head -10 .claude/skills/using-claude-cli/SKILL.md`
    - **Expected:** the first 10 lines show the five-key YAML frontmatter exactly (name, description, command, argument-hint, allowed-tools — each on its own line, between `---` delimiters).
16. Run: `awk '/^---$/{count++; if(count==2) exit} count==1' .claude/skills/using-claude-cli/SKILL.md | grep -E '^(name|description|command|argument-hint|allowed-tools):' | wc -l`
    - **Expected:** `5` (exactly five required keys present).
17. Run: `wc -l .claude/skills/using-claude-cli/SKILL.md`
    - **Expected:** the line count is ≤ 500.
18. Run: `ls .claude/skills/using-claude-cli/references/ | sort`
    - **Expected:** ten file names printed in this order: `agent-teams.md`, `build-notes.md`, `cli-reference.md`, `frontmatter.md`, `hooks.md`, `mcp.md`, `orchestration-patterns.md`, `permissions.md`, `sessions.md`, `subagents.md`.
19. Run: `for f in agent-teams build-notes cli-reference frontmatter hooks mcp orchestration-patterns permissions sessions subagents; do grep -q "references/$f.md" .claude/skills/using-claude-cli/SKILL.md && echo "OK $f" || echo "MISSING $f"; done`
    - **Expected:** all ten lines start with `OK` (every references file is linked from SKILL.md).
20. Run: `grep -E '^- `/using-claude-cli' .claude/CLAUDE.md`
    - **Expected:** exactly one match.
21. Run: `grep -E '^(interactive|headless|bare|sub-agent|session|MCP|permission|cost|orchestration|reference index)' -i .claude/skills/using-claude-cli/SKILL.md | wc -l`
    - **Expected:** at least 10 matches (each of the major SKILL.md sections is present).

### Verify Slice 1

22. **Checkpoint:** `wc -l .claude/skills/using-claude-cli/SKILL.md .claude/skills/using-claude-cli/references/*.md`
   - [ ] SKILL.md ≤ 500 lines.
   - [ ] Each `references/*.md` exists and is non-empty (≥ 20 lines each).
   - [ ] `.claude/CLAUDE.md` announces `/using-claude-cli`.
   - [ ] Spot-read SKILL.md confirms: three CLI modes documented, subagent rules present (including the single-level constraint), sessions covered, MCP covered, permissions covered, cost control covered, examples present (or referenced).

---

## Slice 2: Eval coverage + fixture

### Setup

23. ✨ Create `evals/fixtures/skill_using_claude_cli.md` — a short orchestration-task fixture (~20 lines) describing: "Set up a headless CI job that invokes `claude -p` with a JSON output contract and a restricted permissions allow-list, capturing the result and session_id for a follow-up turn." Include enough detail that the llm_judge cases can score whether SKILL.md plus its references answer the fixture's needs.

### Core Logic

24. ⚠️ Modify `evals/suite.json` — append three new objects to the `cases` array.
    - **Current:** `cases` contains 15 entries covering the QRSPI phases (case_001 through case_015).
    - **After:** `cases` contains 18 entries. The three new entries:
      - `case_016` — `name: "meta_using_claude_cli_structure"`, `phase: "meta"`, `prompt: "Validate the structure of the using-claude-cli skill."`, `context: {files: [".claude/skills/using-claude-cli/SKILL.md"]}`, assertions: programmatic (`output_file_exists`, `line_count <= 500`, `has_frontmatter_field('name')`, `has_frontmatter_field('description')`, `has_frontmatter_field('command')`, `has_frontmatter_field('argument-hint')`, `has_frontmatter_field('allowed-tools')`, `references_dir_has_files >= 9`), weights as in existing cases (1.0 default).
      - `case_017` — `name: "meta_using_claude_cli_mode_coverage"`, `phase: "meta"`, `prompt: "Does the using-claude-cli skill correctly cover all three CLI modes with worked examples?"`, `context: {files: [".claude/skills/using-claude-cli/SKILL.md", ".claude/skills/using-claude-cli/references/cli-reference.md"]}`, assertions: llm_judge with criteria string "The skill must explain interactive mode (`claude`), headless/print mode (`claude -p`), and bare mode (`claude --bare -p`) with a worked example for each. Each example must be runnable shell.", weight 1.5.
      - `case_018` — `name: "meta_using_claude_cli_subagent_accuracy"`, `phase: "meta"`, `prompt: "Does the using-claude-cli skill accurately document subagent rules and frontmatter?"`, `context: {files: [".claude/skills/using-claude-cli/references/subagents.md"]}`, assertions: llm_judge with criteria string "The skill must (a) list the three built-in subagents (Explore, Plan, General-purpose), (b) show the custom subagent frontmatter shape matching the in-repo `.claude/agents/*.md` convention (`name`, `description`, `model`, `claude.tools`), and (c) state the hard rule that subagents cannot spawn other subagents.", weight 1.5.

25. (Verification only — no separate code) — the `phase: "meta"` value is new. If `scripts/run_eval.py` validates against a fixed phase enum, switch all three cases to an existing phase that allows free assertions (likely none do exactly — verify by reading `run_eval.py`'s phase handling). Default assumption: `phase` is free-form (per research.md Q14, no validator on this field is documented).

### Tests

26. Run: `python -c "import json; d=json.load(open('evals/suite.json')); cases=[c for c in d['cases'] if c['phase']=='meta']; print(len(cases))"`
    - **Expected:** `3`.
27. Run: `python -c "import json; d=json.load(open('evals/suite.json')); ids=[c['id'] for c in d['cases']]; assert 'case_016' in ids and 'case_017' in ids and 'case_018' in ids, ids; print('OK')"`
    - **Expected:** `OK`.
28. Run: `python -c "import json; d=json.load(open('evals/suite.json')); print(len(d['cases']))"`
    - **Expected:** `18`.
29. Run: `cat evals/fixtures/skill_using_claude_cli.md | wc -l`
    - **Expected:** between 10 and 50 lines.
30. Run: `python -c "import json; d=json.load(open('evals/suite.json')); [c for c in d['cases'] if c['id']=='case_016'][0]['assertions']" | python -c "import sys, ast; a=ast.literal_eval(sys.stdin.read()); assert any('line_count' in str(x.get('check','')) for x in a); print('OK')"`
    - **Expected:** `OK` (the line-count assertion is present in case_016).
31. Run: `python scripts/run_eval.py --suite evals/suite.json --case case_016 --trials 1 2>&1 | tail -20` (only if the run_eval CLI supports `--case` selection — otherwise skip this step and run the full suite).
    - **Expected:** transcript produced and programmatic assertions pass (file exists, line ≤ 500, frontmatter fields present, references count ≥ 9). If `run_eval.py` does not support case selection, the implementer should add `--case` support OR run the full suite and verify case_016 pass status in the output.

### Verify Slice 2

32. **Checkpoint:** `python -c "import json; d=json.load(open('evals/suite.json')); print('total:', len(d['cases']), 'meta:', sum(1 for c in d['cases'] if c['phase']=='meta'))"`
   - [ ] Output reads `total: 18 meta: 3`.
   - [ ] `evals/fixtures/skill_using_claude_cli.md` exists and is 10–50 lines.
   - [ ] All three new cases have assertions matching the design.

---

## Rollback Notes

- **Step 14 (modify `.claude/CLAUDE.md`):** if the slice is reverted, delete the added bullet for `/using-claude-cli`. No data loss; CLAUDE.md is small and the change is one line.
- **Step 24 (modify `evals/suite.json`):** if the slice is reverted, remove the three appended case objects (case_016, case_017, case_018). The file's `cases` array returns to 15 entries. No persistent state or DB to roll back.
- **Step 2 (skill-creator side session):** the side session writes nothing to this repo automatically; the only artifact is the SKILL.md content the implementer copies in at step 3. If reverted, nothing to roll back.
- **No destructive operations:** no DB migrations, no config purges, no `git push --force`. The slice can be reverted by reverting the slice-1 and slice-2 commits.
