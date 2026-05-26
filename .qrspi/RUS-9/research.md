# Research — Codebase Map
**Questions source:** questions.md @ 2026-05-26T00:38:36Z
**Generated:** 2026-05-26T00:00:00Z
**Status:** draft

## Q1: How does the existing skill-creator skill discover and validate SKILL.md frontmatter fields during skill generation, and what validation logic does it apply?

**Answer:** The skill-creator plugin includes a `quick_validate.py` script that performs validation. It checks:
1. `SKILL.md` file exists in the skill directory
2. File starts with `---` (YAML frontmatter delimiter)
3. Frontmatter is parseable YAML dictionary
4. Only allowed properties are present: `{name, description, license, allowed-tools, metadata, compatibility}`
5. `name` is required, must be kebab-case (`^[a-z0-9-]+$`), max 64 chars, no leading/trailing/consecutive hyphens
6. `description` is required, must be a string, no angle brackets (`<` or `>`), max 1024 chars
7. `compatibility` optional, max 500 chars

The skill-creator SKILL.md body also describes a multi-step workflow: capture intent, interview, write SKILL.md, run test cases, iterate via eval loop, then optimize the description.

**Evidence:**
```python
# /home/vscode/.claude/plugins/.../skill-creator/scripts/quick_validate.py:42-43
ALLOWED_PROPERTIES = {'name', 'description', 'license', 'allowed-tools', 'metadata', 'compatibility'}
```
```python
# quick_validate.py:64-66
if not re.match(r'^[a-z0-9-]+$', name):
    return False, f"Name '{name}' should be kebab-case (lowercase letters, digits, and hyphens only)"
```
```python
# quick_validate.py:83-84
if len(description) > 1024:
    return False, f"Description is too long ({len(description)} characters). Maximum is 1024 characters."
```

**Dependencies:** Upstream: `yaml` Python library for parsing. Downstream: consumed by the skill-creator's eval/iteration loop.

**Implicit contracts:**
- Name must be kebab-case
- Description cannot contain angle brackets (likely because they conflict with argument-hint template syntax)
- The validator's allowed-properties set does NOT include `command` or `argument-hint`, which are used by this project's skills

## Q2: What is the directory structure and file layout convention used by existing skills in this project?

**Answer:** All project-level skills live in `.claude/skills/<skill-name>/SKILL.md`. The project has 10 skills:

```
.claude/skills/
├── qrspi-design/SKILL.md
├── qrspi-implement/SKILL.md
├── qrspi-plan/SKILL.md
├── qrspi-pr/SKILL.md
├── qrspi-questions/SKILL.md
├── qrspi-research/SKILL.md
├── qrspi-structure/SKILL.md
├── qrspi-ticket/SKILL.md
├── qrspi-work/
│   ├── SKILL.md
│   └── references/review-cascade.md
└── qrspi-worktree/SKILL.md
```

Only `qrspi-work` uses a `references/` subdirectory. No skill uses `scripts/`, `assets/`, or `examples/` directories.

**Evidence:**
```
# find /workspaces/qrspi/.claude/skills -type f | sort
.claude/skills/qrspi-work/references/review-cascade.md
.claude/skills/qrspi-work/SKILL.md
... (10 SKILL.md files total)
```

**Dependencies:** Claude Code auto-discovers skills by scanning `skills/` for subdirectories containing `SKILL.md`.

**Implicit contracts:**
- Each skill directory is named identically to its frontmatter `name` field
- Directory name = kebab-case skill identifier
- Only SKILL.md is required; references/ is optional

## Q3: How are skills registered and discovered by Claude Code at session start?

**Answer:** Claude Code uses two discovery mechanisms:

1. **Project-level skills:** Auto-scanned from `.claude/skills/` in the project root. Any subdirectory containing a `SKILL.md` is registered. No explicit configuration in `settings.json` is needed.

2. **Plugin-level skills:** Installed plugins in `~/.claude/plugins/marketplaces/*/plugins/*/skills/` are scanned similarly. Each plugin has a `.claude-plugin/plugin.json` with name/description/author metadata, but individual skills within the plugin are still discovered by the `skills/<name>/SKILL.md` convention.

There is no `settings.json` entry in this project's `.claude/` directory (only `CLAUDE.md` exists). The project-level settings at `~/.claude/projects/-workspaces-qrspi/settings.json` contains only a deny list for `.env` files — no skill registration entries.

**Evidence:**
```
# No .claude/settings.json in the project
$ find /workspaces/qrspi/.claude -name "settings*" → (empty)
```
```json
// ~/.claude/projects/-workspaces-qrspi/settings.json
{
  "permissions": {
    "deny": ["Read(path:**/.env)", "Read(path:**/.env.local)", "Read(path:**/.env.*.local)"]
  }
}
```
From plugin-dev skill-development SKILL.md:
```
### Auto-Discovery
Claude Code automatically discovers skills:
- Scans `skills/` directory
- Finds subdirectories containing `SKILL.md`
- Loads skill metadata (name + description) always
- Loads SKILL.md body when skill triggers
- Loads references/examples when needed
```

**Dependencies:** Upstream: Claude Code runtime (skill scanner). No code in this repo handles registration.

**Implicit contracts:**
- Convention-over-configuration: directory placement IS registration
- No manifest file listing skills is required
- The `skills/` directory must be a direct child of `.claude/` (project-level) or the plugin root (plugin-level)

## Q4: What frontmatter fields are required vs optional in a SKILL.md file, and what are the valid values for each?

**Answer:** Based on analysis of both the skill-creator's validator AND this project's actual usage:

**Required fields:**
- `name` — kebab-case identifier, max 64 chars, `^[a-z0-9-]+$`
- `description` — trigger text, max 1024 chars, no angle brackets

**Optional fields (per quick_validate.py):**
- `license` — string
- `allowed-tools` — comma-separated list of tool permissions
- `metadata` — nested YAML object
- `compatibility` — string, max 500 chars

**Additional fields used by this project (NOT in quick_validate.py's allowed set):**
- `command` — slash command path (e.g., `/qrspi-research`). All 10 project skills use this.
- `argument-hint` — user-facing placeholder text (e.g., `<ticket-id>`)
- `version` — semantic version (used by example-plugin's skills but not by this project)

The `allowed-tools` field in this project uses a format like: `Read, Glob, Grep, Bash(wc:*), Bash(curl:*)` — comma-separated with optional glob-style patterns for Bash subcommands.

**Evidence:**
```yaml
# .claude/skills/qrspi-research/SKILL.md:1-7
---
name: qrspi-research
description: Map codebase facts by answering questions from the Questions phase. The feature ticket is intentionally hidden. Use after questions are approved.
command: /qrspi-research
argument-hint: <ticket-id>
allowed-tools: Read, Glob, Grep, Bash(find:*), Bash(wc:*), Bash(head:*), Bash(tail:*), Bash(curl:*), mcp__linear-russelltsherman__prepare_attachment_upload, mcp__linear-russelltsherman__create_attachment_from_upload
---
```
```python
# quick_validate.py:42
ALLOWED_PROPERTIES = {'name', 'description', 'license', 'allowed-tools', 'metadata', 'compatibility'}
```

**Dependencies:** The `allowed-tools` field integrates with Claude Code's permission system defined in `settings.json`.

**Implicit contracts:**
- `command` must start with `/`
- `argument-hint` uses angle-bracket placeholders
- `allowed-tools` uses comma-separated values with parenthetical Bash subprocess patterns
- `model` field is also mentioned in the example-plugin documentation as valid (e.g., "haiku", "sonnet", "opus")

## Q5: What is the exact trigger/description syntax that controls when Claude auto-invokes a skill versus requiring explicit `/` invocation?

**Answer:** The `description` field is the primary mechanism for auto-triggering. When a skill has a `command` field, it can also be explicitly invoked via slash command. Both mechanisms coexist — a skill with `command: /qrspi-work` can be triggered either by the user typing `/qrspi-work RUS-42` OR by Claude matching the description to user intent.

From the skill-creator documentation on how triggering works:
- Skills appear in Claude's `available_skills` list with their name + description
- Claude decides whether to consult a skill based on that description
- Claude only consults skills for tasks it can't easily handle on its own
- Simple, one-step queries may not trigger even if the description matches

The description style in this project uses imperative sentences: "Use when...", "Use after...", "Trigger on any variant of...". The skill-creator's `skill-development` skill recommends third-person format: "This skill should be used when the user asks to..."

**Evidence:**
```yaml
# qrspi-work/SKILL.md description (auto-trigger focused):
description: "Single entry point for autonomous QRSPI feature development. Use when the user asks to 'work on' a ticket (e.g., 'work on RUS-42'). ... Trigger on any variant of: 'work on <ticket-id>', 'continue <ticket-id>', 'pick up <ticket-id>', or any reference to progressing a QRSPI ticket through its lifecycle."
```
```
# From skill-creator SKILL.md:67-68
To combat this, please make the skill descriptions a little bit "pushy". So for instance, instead of "How to build a simple fast dashboard to display internal Anthropic data.", you might write "How to build a simple fast dashboard to display internal Anthropic data. Make sure to use this skill whenever the user mentions dashboards..."
```
From the system-reminder in this conversation, each skill appears with format:
```
- skill-name: <description text>
```

**Dependencies:** The triggering system is part of Claude Code's runtime, not application code.

**Implicit contracts:**
- Descriptions should be "pushy" per skill-creator guidance — enumerate trigger phrases
- Including specific user phrases in quotes helps matching
- Skills with `command` field appear as slash commands AND in auto-trigger list simultaneously
- The `argument-hint` appears in help output for slash commands

## Q6: How do existing skills reference supplementary material in `references/` from within the main SKILL.md body?

**Answer:** Only one skill in this project uses `references/`: `qrspi-work`. It references the file by relative path in prose instructions:

```
c. Read `references/review-cascade.md` for cascade logic.
d. Address feedback starting from the earliest affected artifact — read the cascade reference for the re-run rules.
```

There is no include directive or special syntax. The skill body simply instructs Claude to "Read" the file by its relative path from the skill directory. Claude Code handles the resolution — when loaded, the `references/` directory contents are available alongside the SKILL.md.

The plugin-dev skill-development documentation shows the convention:
```markdown
## Additional Resources
### Reference Files
For detailed patterns and techniques, consult:
- **`references/patterns.md`** - Common patterns
- **`references/advanced.md`** - Advanced use cases
```

The skill-creator's own `SKILL.md` references its agents and references directories similarly:
```
- `agents/grader.md` — How to evaluate assertions against outputs
- `references/schemas.md` — JSON structures for evals.json, grading.json, etc.
```

**Evidence:**
```markdown
# .claude/skills/qrspi-work/SKILL.md:175-176
   c. Read `references/review-cascade.md` for cascade logic.
   d. Address feedback starting from the earliest affected artifact — read the cascade reference for the re-run rules.
```

**Dependencies:** Claude Code's skill loading system makes bundled resources available; the skill body must explicitly instruct reading them.

**Implicit contracts:**
- Use relative paths from the skill directory
- Bold backtick-wrapped paths with dash-separated descriptions is the recommended pattern
- No automatic inclusion — Claude must be told when to read reference files
- References are "loaded as needed" per progressive disclosure principle

## Q7: How does the skill-creator skill manage intermediate state during multi-step skill generation?

**Answer:** The skill-creator uses a workspace directory pattern: `<skill-name>-workspace/` as a sibling to the skill directory, organized by iteration (`iteration-1/`, `iteration-2/`, etc.) with per-eval subdirectories (`eval-0/`, `eval-1/`, etc.).

Key state artifacts:
1. `evals/evals.json` — test case definitions
2. `<workspace>/iteration-N/eval-ID/with_skill/outputs/` — skill outputs
3. `<workspace>/iteration-N/eval-ID/without_skill/outputs/` — baseline outputs
4. `eval_metadata.json` — per-eval assertions
5. `timing.json` — captured from task notifications (total_tokens, duration_ms)
6. `grading.json` — graded results
7. `benchmark.json` — aggregate statistics
8. `feedback.json` — user feedback from the HTML viewer

The iteration loop: draft skill → run test cases (parallel subagents for with/without skill) → draft assertions while waiting → grade → aggregate → generate HTML viewer → collect user feedback → revise skill → repeat.

**Evidence:**
```
# From skill-creator SKILL.md:167-168
Put results in `<skill-name>-workspace/` as a sibling to the skill directory. Within the workspace, organize results by iteration (`iteration-1/`, `iteration-2/`, etc.) and within that, each test case gets a directory (`eval-0/`, `eval-1/`, etc.).
```
```
# From skill-creator SKILL.md:145-146
Save test cases to `evals/evals.json`. Don't write assertions yet — just the prompts.
```

**Dependencies:** The eval loop depends on subagents (TaskCreate), the HTML viewer (`eval-viewer/generate_review.py`), and model API access for grading.

**Implicit contracts:**
- Workspace is sibling to skill directory, not inside it
- Each iteration gets its own subdirectory
- feedback.json triggers the next iteration
- Timing data must be captured immediately from task notifications — not persisted elsewhere

## Q8: Where are user-level vs project-level skills stored, and what is the resolution order when both define a skill with the same name?

**Answer:** Based on the filesystem layout observed:

- **Project-level:** `.claude/skills/<skill-name>/SKILL.md` (relative to project root)
- **Plugin-level (user-wide):** `~/.claude/plugins/marketplaces/<marketplace>/<plugin-path>/skills/<skill-name>/SKILL.md`

There is no `~/.claude/skills/` directory — user-level skills are distributed exclusively through plugins. The system-reminder in this conversation shows skills from both sources merged into a single `available_skills` list.

No evidence of resolution order for name collisions was found in the codebase. The system-reminder shows plugin skills with plugin-namespaced format (`plugin:skill`) mentioned in the Skill tool documentation: "For plugin-namespaced skills use the fully qualified `plugin:skill` form." This suggests namespace separation rather than priority-based resolution.

**Evidence:**
```
# User-level: only plugins, no direct skills directory
$ find /home/vscode/.claude -maxdepth 1 -type d
→ no 'skills' directory exists at user level

# Plugin skills are namespaced
# From Skill tool description in system prompt:
"For plugin-namespaced skills use the fully qualified `plugin:skill` form."
```

**Dependencies:** Claude Code runtime manages the discovery and namespace resolution.

**Implicit contracts:**
- Plugin skills may require `plugin:skill` qualified form to disambiguate
- Project-level skills override or coexist with plugin skills (exact priority undetermined)
- There is no user-level `~/.claude/skills/` convention — plugins are the mechanism

## Q9: What happens when a SKILL.md body exceeds the 500-line / 5000-token limit?

**Answer:** The skill-creator provides guidance but does NOT enforce a hard limit programmatically. The `quick_validate.py` script validates only frontmatter — it does not check body length. The 500-line limit is soft guidance from the SKILL.md body itself.

Guidance from skill-creator:
- "Keep SKILL.md under 500 lines; if you're approaching this limit, add an additional layer of hierarchy along with clear pointers about where the model using the skill should go next to follow up."
- The plugin-dev skill-development says: "Keep under 3,000 words, ideally 1,500-2,000 words"

In this project, `qrspi-work/SKILL.md` is 501 lines — it exceeds the guidance. No tooling error occurs; it simply loads fully when triggered.

**Evidence:**
```
# Line count of largest skill in this project:
$ wc -l .claude/skills/qrspi-work/SKILL.md → 501 lines
```
```
# skill-creator SKILL.md:96-97
Keep SKILL.md under 500 lines; if you're approaching this limit, add an additional layer of hierarchy along with clear pointers...
```
```python
# quick_validate.py checks only frontmatter — no body length validation
# The function returns after validating frontmatter fields; body is not inspected
```

**Dependencies:** None — this is soft guidance only.

**Implicit contracts:**
- The 500-line limit is a recommendation, not a hard constraint
- Exceeding it works but increases context consumption when the skill triggers
- The mitigation is to move content to `references/` files
- Progressive disclosure: metadata always in context, body on trigger, references on demand

## Q10: How are skills with overlapping trigger descriptions disambiguated?

**Answer:** The codebase contains no explicit disambiguation mechanism in application code. Based on the skill-creator's documentation:

1. Claude decides which skill to invoke based on description matching against user intent
2. The Skill tool documentation states: "Only invoke a skill that appears in that list"
3. For explicit invocation, skills are identified by exact name (or `plugin:skill` namespace)

In this project, skill descriptions are intentionally non-overlapping — each phase is distinct: "Use when starting..." (ticket), "Use after questions are approved" (research), "Use after research is approved" (design), etc. The `qrspi-work` skill has the broadest trigger ("work on", "continue", "pick up") and explicitly dispatches to the correct phase internally.

**Evidence:**
```
# From Skill tool description:
"Only invoke a skill that appears in that list, or one the user explicitly typed as `/<name>` in their message. Never guess or invent a skill name..."
```
```
# skill-creator SKILL.md guidance on overlap:
# From skill-development SKILL.md (plugin-dev):
"Avoid overlap with other skills' trigger conditions"
```
```yaml
# Descriptions in this project are phase-ordered:
# qrspi-questions: "Use when starting a new QRSPI feature workflow..."
# qrspi-research: "Use after questions are approved."
# qrspi-design: "Use after research is approved."
```

**Dependencies:** Claude Code's runtime handles skill selection; no user-accessible priority mechanism exists.

**Implicit contracts:**
- Disambiguation relies on description specificity, not priority ordering
- Phase-gating language ("Use after X is approved") prevents ambiguity in sequential workflows
- Plugin namespacing (`plugin:skill`) prevents cross-plugin collisions
- Skill designers are responsible for non-overlapping descriptions

## Q11: What constraints exist on `references/` file size or count, and how does Claude Code handle a skill whose total content exceeds context limits?

**Answer:** No hard constraints on references/ file size or count were found in the codebase or validator. The guidance from the skill-creator and plugin-dev documentation:

- "Bundled resources — As needed (unlimited, scripts can execute without loading)"
- "For large reference files (>300 lines), include a table of contents"
- "If files are large (>10k words), include grep search patterns in SKILL.md"
- Progressive disclosure: references are loaded "as needed" — only when Claude decides to read them, not automatically on skill trigger

The `qrspi-work/references/review-cascade.md` is 64 lines — well within any practical limit. No mechanism for automatic truncation or chunking of large reference files was observed.

**Evidence:**
```
# From skill-development SKILL.md:79
*Unlimited because scripts can be executed without reading into context window.
```
```
# From skill-development SKILL.md:66
- **Best practice**: If files are large (>10k words), include grep search patterns in SKILL.md
```
```
# From skill-creator SKILL.md:92-93
Skills use a three-level loading system:
1. Metadata (name + description) - Always in context (~100 words)
2. SKILL.md body - In context whenever skill triggers (<500 lines ideal)
3. Bundled resources - As needed (unlimited, scripts can execute without loading)
```

**Dependencies:** Context window management is handled by Claude Code's runtime.

**Implicit contracts:**
- References are lazy-loaded, never auto-included
- No programmatic size limit exists; practical limit is context window capacity
- Best practice: large references should have a TOC or grep patterns
- Scripts can execute without being read into context — size is irrelevant for them

## Q12: What eval harness or test pattern does the skill-creator skill use to validate a newly generated skill works correctly?

**Answer:** The skill-creator uses a multi-component eval system:

1. **Test case definition:** `evals/evals.json` with id, prompt, expected_output, files, expectations
2. **Execution:** Spawn parallel subagents (with-skill and baseline/without-skill) via TaskCreate
3. **Grading:** `agents/grader.md` evaluates assertions — uses `grading.json` with `text`, `passed`, `evidence` fields
4. **Aggregation:** `scripts/aggregate_benchmark.py` produces `benchmark.json` with pass_rate, time, tokens per configuration
5. **Analysis:** `agents/analyzer.md` surfaces patterns hidden by aggregate stats
6. **Review:** `eval-viewer/generate_review.py` generates an HTML viewer for qualitative human review

The project-level eval system (`/workspaces/qrspi/evals/suite.json` + `scripts/`) is a separate, purpose-built harness for QRSPI phase skills with:
- Programmatic assertions (regex-based checks)
- LLM judge assertions (subjective quality)
- Script assertions (external programs like `check_scope.py`)
- Train/test split (65/35) with per-case difficulty and tagging
- Multi-trial execution with variance tracking

**Evidence:**
```json
// evals/suite.json:8-10
"split": {
  "train_ratio": 0.65,
  "test_ratio": 0.35,
  "seed": 42
}
```
```python
# scripts/run_eval.py:93-143 (stub — placeholder for actual agent invocation)
def execute_single(skill_text, case, trial_id, timeout_ms) -> ExecutionResult:
    # ── Placeholder for agent execution ──
    # Replace this block with actual agent invocation
```
```python
# scripts/grade.py:146-157
CHECKS = {
    "output_file_exists": output_file_exists,
    "has_section": has_section,
    "no_solution_language": no_solution_language,
    ...
}
```

**Dependencies:** `run_eval.py` has placeholder agent execution — not yet integrated with a real agent runtime. `grade.py` has LLM judge stubs returning `None`. The `run_loop.sh` orchestrates the full cycle.

**Implicit contracts:**
- Eval cases must have `id`, `prompt`, `assertions`
- Assertions use a `check` string parsed as function calls: `function_name('arg1', 'arg2')`
- The harness uses a hash of skill text to track versions
- Results live in `results/<version>/` directories

## Q13: Are there existing test cases or eval prompts for other skills in this project that demonstrate the expected test coverage pattern?

**Answer:** Yes. Two eval files exist:

1. **`evals/suite.json`** — 15 cases covering all QRSPI phases (questions, research, design, structure, plan, worktree, implement, pr). Demonstrates:
   - Happy path + edge case + adversarial coverage
   - Difficulty ratings (easy, medium, hard)
   - Train/test split annotations
   - Weighted assertions with programmatic + LLM judge mix
   - Tags for filtering

2. **`evals/graphite-evals.json`** — 5 cases testing the graphite CLI skill. Demonstrates:
   - User-realistic prompts (casual language)
   - Assertion types: `command_check`, `flag_check`, `content_check`, `workflow_check`, `safety_check`
   - Simpler format without train/test split

**Evidence:**
```json
// evals/suite.json case_003 (research phase):
{
  "id": "case_003",
  "name": "research_factual_accuracy",
  "phase": "research",
  "prompt": "Research the codebase to answer these questions.",
  "assertions": [
    {"type": "programmatic", "check": "all_evidence_has_file_citations('research.md')", "weight": 1.5},
    {"type": "llm_judge", "criteria": "Research contains only factual observations...", "weight": 2.0}
  ],
  "tags": ["research", "happy-path", "factual"],
  "difficulty": "medium",
  "split": "train"
}
```
```json
// evals/graphite-evals.json eval 1:
{
  "id": 1,
  "prompt": "I just made some changes to the auth module. commit my changes with a message about adding JWT validation",
  "assertions": [
    {"text": "Uses gt create or gt modify (not raw git commit)", "type": "command_check"},
    {"text": "Includes Co-Authored-By trailer in the commit message", "type": "content_check"}
  ]
}
```

**Dependencies:** `suite.json` references fixture files (`fixtures/ticket_rest_endpoint.md`, etc.) that do not exist in the repo — they are placeholders for future test data.

**Implicit contracts:**
- Each QRSPI phase gets at minimum one happy-path and one edge-case eval
- Assertions are weighted (higher weight = more critical)
- LLM judge criteria are full sentences describing the quality dimension
- Cases reference fixture files by relative path

## Q14: What logging or telemetry exists when a skill is triggered, loaded, or fails to match?

**Answer:** No application-level logging for skill triggering exists in this codebase. The project has:

- `~/.claude/telemetry/` directory (exists but contents not inspected — likely Claude Code internal telemetry)
- No custom hooks or scripts that log skill invocation events
- The `PreToolUse` hook in `settings.json` runs `~/.agents/hooks/pre-tool-memory.sh` on every tool call — this is memory injection, not skill telemetry

For a developer confirming skill invocation:
1. The system-reminder includes the available-skills list — visible at session start
2. When a skill triggers, its body loads into context (observable in verbose mode via `"viewMode": "verbose"` in settings.json)
3. The Skill tool call appears in the conversation transcript

The `eval-viewer/generate_review.py` in skill-creator provides post-hoc analysis of skill behavior via test case outputs, but this is for development iteration, not runtime observability.

**Evidence:**
```json
// ~/.claude/settings.json:51-52
"viewMode": "verbose",
"verbose": true
```
```json
// ~/.claude/settings.json:38-49 (PreToolUse hook)
"PreToolUse": [{
  "matcher": "*",
  "hooks": [{
    "type": "command",
    "command": "bash ~/.agents/hooks/pre-tool-memory.sh",
    "timeout": 5
  }]
}]
```

**Dependencies:** Claude Code's verbose mode is the primary observability mechanism.

**Implicit contracts:**
- No runtime metrics are emitted for skill matching/loading
- Developers must rely on verbose output and conversation transcripts
- The `Skill` tool call in the conversation is the observable signal that a skill was invoked
- The eval harness (scripts/run_eval.py) captures tool_calls and transcripts for offline analysis

## Q15: Does the skill-creator skill emit any structured output that can be captured for CI or review purposes?

**Answer:** Yes. The skill-creator's eval loop produces several structured artifacts suitable for CI:

1. **`benchmark.json`** — Machine-readable aggregate scores with pass_rate, time, tokens per configuration (with mean/stddev/delta)
2. **`grading.json`** — Per-run assertion results with evidence
3. **`timing.json`** — Token count and duration from each run
4. **Results from `run_loop.py`** — Returns JSON with `best_description` field
5. **`history.json`** — Version progression tracking expectation_pass_rate

The project-level harness produces:
1. **`results/<version>/results.json`** — Raw execution results with skill_hash, per-trial outputs
2. **`results/<version>/grades.json`** — Scored results with train_score, test_score, train_test_gap, per-case breakdowns
3. **`results/report.json`** — Cross-version comparison with regression detection

The `run_loop.sh` script orchestrates an automated optimization loop that could run in CI: run evals → grade → check target → diagnose → revise → repeat.

**Evidence:**
```bash
# run_loop.sh:60-63
SCORE=$(python3 -c "
import json
with open('${OUTPUT_DIR}/grades.json') as f:
    g = json.load(f)
print(g.get('test_score', 0))
")
```
```bash
# run_loop.sh:67-71
TARGET_MET=$(python3 -c "print(1 if float('${SCORE}') >= float('${TARGET_SCORE}') else 0)")
if [ "$TARGET_MET" = "1" ]; then
    echo "  Target score reached!"
    break
fi
```
```python
# scripts/grade.py output structure:
# {timestamp, skill_hash, train_score, test_score, train_test_gap, train_details, test_details, cases}
```

**Dependencies:** `run_loop.sh` depends on `scripts/run_eval.py`, `scripts/grade.py`, `scripts/diagnose.py`, `scripts/revise.py`, `scripts/report.py`. The actual agent execution in `run_eval.py` is a stub — not yet integrated with a real runtime.

**Implicit contracts:**
- `grades.json` is the primary CI-readable artifact
- `test_score` is the metric used to determine if target is met (not train_score — prevents overfitting)
- Regression detection uses a 0.05 threshold
- The loop supports a configurable target score (default 0.85)

## Discovered Patterns

1. **Convention-over-configuration for skill discovery:** No manifest or registration file needed — place a `SKILL.md` in `.claude/skills/<name>/` and it appears in the available-skills list.

2. **Progressive disclosure (3-tier):** Metadata always loaded → SKILL.md body loaded on trigger → references loaded on demand. This is the core architectural pattern for managing context budget.

3. **Frontmatter as contract surface:** The YAML frontmatter serves dual purposes: (a) machine-readable metadata for discovery/triggering, (b) permission scoping via `allowed-tools`.

4. **Phase-gated sequential workflow:** Each skill's description includes temporal ordering ("Use after X is approved") which prevents ambiguous triggering in a multi-phase pipeline.

5. **Context firewall pattern:** Skills deliberately restrict what inputs agents receive (e.g., research phase cannot see ticket, implement phase only sees its slice) to prevent bias and scope creep.

6. **Eval-driven skill development:** Both the skill-creator and this project's `run_loop.sh` implement iterative improvement cycles with train/test splits and regression detection.

7. **Allowed-tools as least-privilege:** Each skill declares exactly which tools it needs. The `qrspi-research` skill gets `Bash(find:*)` but not `Bash` (unrestricted). The `qrspi-implement` skill gets full `Bash` access because it needs to run arbitrary test commands.

8. **Workspace isolation for eval artifacts:** Test outputs go in `<skill-name>-workspace/` (skill-creator) or `results/` (project-level), never mixed with skill source files.

## Inconsistencies

1. **Frontmatter allowed-properties mismatch:** The skill-creator's `quick_validate.py` allows only `{name, description, license, allowed-tools, metadata, compatibility}`, but ALL project skills use `command` and `argument-hint` fields which would FAIL validation. This suggests the validator was written for a different skill format (plugin marketplace skills without slash commands) and has not been updated for project-level skills.

2. **Description style inconsistency:** The skill-creator and plugin-dev skill recommend third-person descriptions ("This skill should be used when the user asks to...") but ALL project-level skills use imperative/second-person style ("Use when...", "Use after..."). Both apparently work for triggering — the style recommendation may be aspirational rather than functional.

3. **`qrspi-work` exceeds the 500-line guidance** at 501 lines but has no references to offload — only one reference file exists (`review-cascade.md`) and it's relatively small. The bulk of the skill (implementation orchestration, error handling) lives directly in the SKILL.md body.

4. **Eval harness is stub-only:** `scripts/run_eval.py`'s `execute_single` function is a placeholder that returns empty results. `scripts/grade.py`'s LLM judge returns `None`. The infrastructure exists but cannot actually run evaluations against a live agent. The `run_loop.sh` would execute but produce meaningless scores.

5. **Missing fixture files:** `evals/suite.json` references fixture paths (`fixtures/ticket_rest_endpoint.md`, etc.) that do not exist in the repository. The eval suite is defined but not executable.

6. **`allowed-tools` format divergence:** The example-plugin shows `allowed-tools: [Read, Glob, Grep, Bash]` (array syntax with brackets) while this project uses `allowed-tools: Read, Glob, Grep, Bash` (plain comma-separated string). Both apparently work, suggesting the parser is flexible.
