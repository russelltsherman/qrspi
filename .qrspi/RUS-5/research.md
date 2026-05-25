# Research — Codebase Map

**Questions source:** questions.md @ 2026-05-25T00:00:00Z
**Generated:** 2026-05-25T21:00:00Z
**Status:** draft

## Q1: How does the skill-creator skill discover and validate the `SKILL.md` frontmatter schema — what file defines the required fields and their types?

**Answer:** The skill-creator uses `scripts/quick_validate.py` to validate SKILL.md frontmatter. This script defines a hardcoded `ALLOWED_PROPERTIES` set and checks required fields. The allowed frontmatter properties are: `name`, `description`, `license`, `allowed-tools`, `metadata`, `compatibility`. Required fields are `name` and `description`. Parsing uses the `scripts/utils.py` module's `parse_skill_md()` function which extracts frontmatter by splitting on `---` delimiters and parsing YAML key-value lines (including multiline indicators `>`, `|`, `>-`, `|-`).

**Evidence:**

```python
# Define allowed properties
ALLOWED_PROPERTIES = {'name', 'description', 'license', 'allowed-tools', 'metadata', 'compatibility'}

# Check for unexpected properties (excluding nested keys under metadata)
unexpected_keys = set(frontmatter.keys()) - ALLOWED_PROPERTIES
if unexpected_keys:
    return False, (
        f"Unexpected key(s) in SKILL.md frontmatter: {', '.join(sorted(unexpected_keys))}. "
        f"Allowed properties are: {', '.join(sorted(ALLOWED_PROPERTIES))}"
    )

# Check required fields
if 'name' not in frontmatter:
    return False, "Missing 'name' in frontmatter"
if 'description' not in frontmatter:
    return False, "Missing 'description' in frontmatter"
```

— `/home/vscode/.agents/skills/skill-creator/scripts/quick_validate.py:42-57`

**Dependencies:** `quick_validate.py` is imported by `package_skill.py` (validation runs before packaging). `utils.py` is imported by `run_eval.py`, `improve_description.py`, and `run_loop.py`.

**Implicit contracts:**
- Name must be kebab-case (`[a-z0-9-]+`), max 64 characters, no leading/trailing/consecutive hyphens.
- Description must be a string, max 1024 characters, no angle brackets (`<` or `>`).
- Compatibility (optional) must be a string, max 500 characters.
- Frontmatter must start with `---` on line 1 and have a closing `---`.

---

## Q2: What is the directory structure the skill-creator produces on disk, and which module enforces the `SKILL.md` + optional `references/`, `scripts/`, `assets/` layout?

**Answer:** The skill-creator's SKILL.md documents the canonical layout as:

```
skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter (name, description required)
│   └── Markdown instructions
└── Bundled Resources (optional)
    ├── scripts/    - Executable code for deterministic/repetitive tasks
    ├── references/ - Docs loaded into context as needed
    └── assets/     - Files used in output (templates, icons, fonts)
```

No module programmatically enforces this directory layout. The only enforcement is in `quick_validate.py` which checks that `SKILL.md` exists and has valid frontmatter. The `package_skill.py` module packages whatever files exist in the skill directory (excluding `__pycache__`, `node_modules`, `.DS_Store`, `*.pyc`, and root-level `evals/` directory).

**Evidence:**

```python
# package_skill.py: exclusion logic — no structural enforcement
EXCLUDE_DIRS = {"__pycache__", "node_modules"}
EXCLUDE_GLOBS = {"*.pyc"}
EXCLUDE_FILES = {".DS_Store"}
ROOT_EXCLUDE_DIRS = {"evals"}
```

— `/home/vscode/.agents/skills/skill-creator/scripts/package_skill.py:19-24`

**Dependencies:** `package_skill.py` imports `quick_validate.validate_skill` for pre-packaging validation.

**Implicit contracts:** The layout is convention-driven, not schema-enforced. The skill-creator SKILL.md describes the structure as guidance for the agent creating skills, not as a validated constraint.

---

## Q3: Where are existing agent skills stored in this repository (or referenced externally), and what naming convention do their directories follow?

**Answer:** Skills are stored in two locations relevant to this project:

1. **Project-local skills:** `/workspaces/qrspi/.claude/skills/<skill-name>/SKILL.md`
   - Current skills: `qrspi-design`, `qrspi-implement`, `qrspi-plan`, `qrspi-pr`, `qrspi-questions`, `qrspi-research`, `qrspi-structure`, `qrspi-ticket`, `qrspi-work`, `qrspi-worktree`

2. **User-global skills:** `/home/vscode/.agents/skills/<skill-name>/`
   - Current skills: `using-graphite-cli`, `skill-creator`, `graphite-workspace`, `mcp-builder`, `workflow-creator`

3. **Plugin-installed skills:** `/home/vscode/.claude/plugins/marketplaces/claude-plugins-official/plugins/skill-creator/skills/skill-creator/`

All directories follow **kebab-case** naming. Project-local skills all share the `qrspi-` prefix.

**Evidence:**

```
/workspaces/qrspi/.claude/skills/
├── qrspi-design/
├── qrspi-implement/
├── qrspi-plan/
├── qrspi-pr/
├── qrspi-questions/
├── qrspi-research/
├── qrspi-structure/
├── qrspi-ticket/
├── qrspi-work/
└── qrspi-worktree/
```

— `find /workspaces/qrspi/.claude/skills -type d -maxdepth 1` output

**Dependencies:** Claude Code discovers skills in `.claude/skills/` relative to the project root, and in the user's `~/.agents/skills/` directory.

**Implicit contracts:** Directory name must match the `name` field in SKILL.md frontmatter (enforced by kebab-case naming convention in `quick_validate.py`, though the directory-name-matches-frontmatter-name rule is convention, not validated).

---

## Q4: What frontmatter fields does the agentskills.io standard require in a `SKILL.md`, and is there a local schema or validation script that checks conformance?

**Answer:** The local validation script (`quick_validate.py`) defines the schema. Required fields are `name` and `description`. Optional fields are `license`, `allowed-tools`, `metadata`, and `compatibility`. There is no reference to an "agentskills.io" standard in any file in this repository or in the skill-creator. The constraints are:

| Field | Required | Type | Constraints |
|-------|----------|------|-------------|
| name | Yes | string | kebab-case, max 64 chars |
| description | Yes | string | max 1024 chars, no angle brackets |
| license | No | any | — |
| allowed-tools | No | any | — |
| metadata | No | any | — |
| compatibility | No | string | max 500 chars |

However, the project-local QRSPI skills also use additional frontmatter fields not in the official allowed set: `command` and `argument-hint`. These fields would fail the `quick_validate.py` check.

**Evidence:**

```yaml
# From qrspi-ticket/SKILL.md frontmatter:
---
name: qrspi-ticket
description: Draft a new feature ticket through guided conversation...
command: /qrspi-ticket
argument-hint: <initial description>
allowed-tools: Read, Glob, Grep, Write, Bash, mcp__linear-russelltsherman__save_issue
---
```

— `/workspaces/qrspi/.claude/skills/qrspi-ticket/SKILL.md:1-7`

**Dependencies:** `quick_validate.py` uses `yaml.safe_load` (PyYAML library) and `re` for validation.

**Implicit contracts:** The `command` and `argument-hint` fields appear to be Claude Code runtime extensions not covered by the skill-creator's validation schema. This suggests the skill-creator's schema may be narrower than what the Claude Code runtime actually accepts.

---

## Q5: How does the skill-creator skill accept input parameters (e.g., skill name, description, conventions) — through interactive prompts, a structured input file, or CLI arguments?

**Answer:** The skill-creator operates as a **conversational agent** — it accepts input through an interactive multi-turn conversation. The SKILL.md describes a "Capture Intent" phase where it asks the user questions:

1. What should this skill enable Claude to do?
2. When should this skill trigger?
3. What's the expected output format?
4. Should we set up test cases?

It does not accept a structured input file or CLI arguments directly. It is invoked as a Claude Code skill via the `Skill` tool (or via `/skill-creator` command), and the conversation history provides all context.

**Evidence:**

```markdown
### Capture Intent

Start by understanding the user's intent. The current conversation might already
contain a workflow the user wants to capture (e.g., they say "turn this into a
skill"). If so, extract answers from the conversation history first — the tools
used, the sequence of steps, corrections the user made, input/output formats
observed.
```

— `/home/vscode/.agents/skills/skill-creator/SKILL.md:47-50`

**Dependencies:** The skill-creator relies on Claude Code's skill invocation system (the `Skill` tool or `/` command syntax).

**Implicit contracts:** The skill-creator expects to operate within an interactive session where it can ask follow-up questions and receive responses.

---

## Q6: What is the mechanism for a skill's `references/` directory to be loaded into agent context — does the runtime read all files in that directory, or must they be explicitly referenced in `SKILL.md`?

**Answer:** References are **not automatically loaded**. The skill-creator's documentation uses the term "Progressive Disclosure" with three levels:

1. **Metadata** (name + description) — always in context
2. **SKILL.md body** — loaded when skill triggers
3. **Bundled resources** — loaded "as needed"

The SKILL.md body must contain explicit pointers directing the agent to read reference files when relevant. The agent using the skill then calls the `Read` tool on those files as needed.

**Evidence:**

```markdown
#### Progressive Disclosure

Skills use a three-level loading system:
1. **Metadata** (name + description) - Always in context (~100 words)
2. **SKILL.md body** - In context whenever skill triggers (<500 lines ideal)
3. **Bundled resources** - As needed (unlimited, scripts can execute without loading)

**Key patterns:**
- Keep SKILL.md under 500 lines; if you're approaching this limit, add an
  additional layer of hierarchy along with clear pointers about where the model
  using the skill should go next
- Reference files clearly from SKILL.md with guidance on when to read them
```

— `/home/vscode/.agents/skills/skill-creator/SKILL.md:86-98`

The skill-creator itself demonstrates this pattern: its SKILL.md contains explicit pointers like `See references/schemas.md for the full schema` and a "Reference files" section listing what each file contains and when to read it.

**Dependencies:** The agent runtime (Claude Code) provides the `Read` tool which skills use to access reference files on demand.

**Implicit contracts:** Reference files are never auto-injected. The agent consuming the skill must be told (in SKILL.md) when and why to read a reference file. Scripts can be executed via `Bash` without being read into context.

---

## Q7: After the skill-creator generates a skill, where is the resulting artifact persisted, and is there a registry or index file that must be updated to activate the new skill?

**Answer:** There is **no registry or index file**. Skills are activated by placement in the filesystem. Claude Code discovers skills by scanning:

- `.claude/skills/` in the project root (project-scoped)
- `~/.agents/skills/` or similar user-level directories (user-scoped)
- Plugin-installed locations (`~/.claude/plugins/.../skills/`)

The skill-creator simply writes files to disk (SKILL.md and optional subdirectories). The `package_skill.py` script can create a distributable `.skill` file (zip format) for sharing.

No configuration file, settings.json entry, or explicit registration step is required — Claude Code picks up skills by filesystem discovery.

**Evidence:**

The project settings (`/home/vscode/.claude/projects/-workspaces-qrspi/settings.json`) contains no skill references — only permissions. The global settings (`/home/vscode/.claude/settings.json`) similarly has no skill registry. Yet all skills in `.claude/skills/` appear in the system's `available-skills` list (visible in the system-reminder messages).

**Dependencies:** Claude Code's internal skill discovery mechanism (not user-accessible code).

**Implicit contracts:** Placing a valid `SKILL.md` in the correct directory is sufficient for activation. Removing it deactivates the skill. No reload or restart is documented as necessary.

---

## Q8: Does the skill-creator maintain any intermediate state (drafts, revision history) during multi-turn skill authoring, and if so, where is that state stored?

**Answer:** The skill-creator maintains intermediate state in a **workspace directory** created as a sibling to the skill directory. The naming convention is `<skill-name>-workspace/`. Within the workspace, results are organized by iteration (`iteration-1/`, `iteration-2/`, etc.).

For description optimization, `run_loop.py` tracks iteration history in-memory and optionally persists to a `results-dir` with timestamped subdirectories containing `results.json`, `report.html`, and a `logs/` directory with per-iteration transcripts.

The `references/schemas.md` documents a `history.json` schema for tracking version progression in "Improve mode".

**Evidence:**

```markdown
Put results in `<skill-name>-workspace/` as a sibling to the skill directory.
Within the workspace, organize results by iteration (`iteration-1/`,
`iteration-2/`, etc.) and within that, each test case gets a directory
(`eval-0/`, `eval-1/`, etc.).
```

— `/home/vscode/.agents/skills/skill-creator/SKILL.md:167-168`

```json
// history.json schema from references/schemas.md
{
  "started_at": "2026-01-15T10:30:00Z",
  "skill_name": "pdf",
  "current_best": "v2",
  "iterations": [...]
}
```

— `/home/vscode/.agents/skills/skill-creator/references/schemas.md:40-72`

**Dependencies:** The workspace directory is created by the agent following skill-creator instructions; no scaffolding script creates it automatically.

**Implicit contracts:** The workspace is ephemeral working state, not part of the final skill artifact. It is excluded from packaging via `ROOT_EXCLUDE_DIRS = {"evals"}` (though workspace dirs themselves are not explicitly excluded — they would only be excluded if nested inside the skill directory).

---

## Q9: What happens if a generated `SKILL.md` exceeds the 500-line / 5000-token limit stated in acceptance criteria — is there an existing enforcement mechanism or lint rule?

**Answer:** There is **no automated enforcement** of the 500-line limit. The skill-creator's SKILL.md describes it as guidance ("under 500 lines ideal") and suggests moving content to reference files if approaching the limit. There are no pre-commit hooks, CI checks, or lint rules that validate skill file sizes. The `quick_validate.py` script does not check line count or token count.

**Evidence:**

```markdown
**Key patterns:**
- Keep SKILL.md under 500 lines; if you're approaching this limit, add an
  additional layer of hierarchy along with clear pointers about where the model
  using the skill should go next to follow up.
```

— `/home/vscode/.agents/skills/skill-creator/SKILL.md:96-97`

The project has no `.pre-commit-config.yaml`, no `.github/` directory, and no CI configuration files. The `scripts/` directory contains only eval-related scripts, not lint scripts.

**Dependencies:** None — the limit is advisory only.

**Implicit contracts:** The 500-line guidance is a soft convention. The skill-creator's own SKILL.md is 486 lines, close to but under the stated limit.

---

## Q10: How does the system handle a skill whose `references/` directory contains files that conflict with or duplicate guidance already present in `SKILL.md` body?

**Answer:** NOT FOUND. There is no deduplication mechanism or conflict detection. The skill-creator documentation does not address this scenario. Since reference files are loaded on-demand via explicit `Read` calls (not auto-injected), the consuming agent would simply see both the SKILL.md instructions and the reference file content in its context window. No code performs content comparison or deduplication between SKILL.md body and reference files.

Search queries attempted:
- `grep -r "dedup\|conflict\|duplicate" /home/vscode/.agents/skills/skill-creator/` — no results
- `grep -r "overlap\|redundan" /home/vscode/.agents/skills/skill-creator/` — no results
- Reviewed all scripts in the skill-creator — none perform content comparison

**Dependencies:** N/A

**Implicit contracts:** It is the skill author's responsibility to avoid redundancy. The progressive disclosure model implicitly assumes SKILL.md is a summary/index and references provide depth — but this is convention, not enforced.

---

## Q11: If the skill-creator is invoked for a skill name that already exists, what conflict resolution behavior applies — overwrite, error, or interactive prompt?

**Answer:** The skill-creator does not have explicit conflict resolution logic. Its SKILL.md addresses this scenario only in the context of updates:

- For Claude.ai: "Preserve the original name" and "Copy to a writeable location before editing"
- For the eval loop: The `package_skill.py` uses `zipfile.ZipFile(skill_filename, 'w', ...)` which overwrites the output `.skill` file without warning

The skill-creator operates conversationally and would detect existing files via the `Read` tool during the "Interview and Research" phase. The SKILL.md includes specific guidance for the "Updating an existing skill" case (preserve name, copy to temp before editing).

**Evidence:**

```markdown
**Updating an existing skill**: The user might be asking you to update an
existing skill, not create a new one. In this case:
- **Preserve the original name.** Note the skill's directory name and `name`
  frontmatter field -- use them unchanged.
- **Copy to a writeable location before editing.** The installed skill path may
  be read-only. Copy to `/tmp/skill-name/`, edit there, and package from the copy.
```

— `/home/vscode/.agents/skills/skill-creator/SKILL.md:438-441`

**Dependencies:** The agent's ability to detect existing files depends on having `Read`/`Glob` tool access.

**Implicit contracts:** Behavior depends on the agent's judgment during conversation. For new skills, there is no guard against overwriting an existing skill directory. For updates, the convention is to preserve names and copy before editing.

---

## Q12: What existing test infrastructure (if any) validates that a generated skill produces correct output when used by an agent — are there eval harnesses, snapshot tests, or BATS-style integration tests?

**Answer:** Two eval systems exist:

1. **Project-level eval harness** (`/workspaces/qrspi/scripts/run_eval.py` + `evals/suite.json`): Defines test cases with programmatic assertions and LLM-judge assertions. Currently a stub — the `execute_single()` function has placeholder comments where actual agent invocation would go. Supports ThreadPoolExecutor parallelism, per-case trials, and structured output.

2. **Skill-creator eval system** (`/home/vscode/.agents/skills/skill-creator/scripts/run_eval.py`): Specifically tests skill **triggering** — whether a description causes Claude to invoke the skill for given queries. Uses `claude -p` subprocess with stream-json output to detect tool_use events. Fully functional (not a stub).

The project also has a grading script (`/workspaces/qrspi/scripts/grade.py`) with a registry of programmatic check functions and an orchestration shell script (`/workspaces/qrspi/run_loop.sh`).

**Evidence:**

```python
# Project run_eval.py — stub execution
# ── Placeholder for agent execution ──
# Replace this block with actual agent invocation:
#   response = agent.run(
#       system_prompt=skill_text,
#       messages=build_messages(case),
#       tools=<tool_set>,
#       sandbox=IsolatedContainer(),
#   )
```

— `/workspaces/qrspi/scripts/run_eval.py:117-127`

```json
// evals/suite.json defines 15 test cases across phases
{
  "name": "qrspi-agent-evals",
  "cases": [
    {
      "id": "case_001",
      "assertions": [
        {"type": "programmatic", "check": "output_file_exists('questions.md')"},
        {"type": "llm_judge", "criteria": "Questions are specific and answerable..."}
      ]
    }
  ]
}
```

— `/workspaces/qrspi/evals/suite.json:1-10` (abbreviated)

**Dependencies:** Project eval harness depends on `scripts/grade.py`, `scripts/diagnose.py`, `scripts/revise.py`, `scripts/report.py`. Skill-creator eval depends on `claude` CLI being available.

**Implicit contracts:** The project eval harness is not yet functional for end-to-end testing (execution is stubbed). The grading and assertion infrastructure is in place but requires an agent runtime integration to produce actual outputs.

---

## Q13: Is there an existing mechanism to verify that code samples embedded in a skill's `SKILL.md` or `references/` pass ShellCheck (or equivalent linting) as part of CI?

**Answer:** NOT FOUND. There is no ShellCheck configuration, no CI pipeline (no `.github/` directory, no `.pre-commit-config.yaml`), and no lint scripts targeting embedded code samples. The `scripts/` directory contains only eval-related Python scripts. No BATS tests exist.

Search queries attempted:
- `find /workspaces/qrspi -name ".shellcheck*"` — no results
- `find /workspaces/qrspi -name "*.yml" -not -path "*/.git/*"` — no results
- `find /workspaces/qrspi -name "pre-commit" -not -path "*/.git/*" -not -path "*sample*"` — no results
- Checked `scripts/` directory — only `check_scope.py`, `diagnose.py`, `grade.py`, `report.py`, `revise.py`, `run_eval.py`

**Dependencies:** N/A

**Implicit contracts:** Code quality in skills is entirely the responsibility of the skill author and the skill-creator agent's judgment during authoring.

---

## Q14: When an agent invokes a skill at runtime, what logging or telemetry captures whether the skill was triggered, how much context it consumed, and whether the agent followed its guidance?

**Answer:** NOT FOUND in the project codebase. There is no local logging or telemetry system for skill invocation. The skill-creator's `run_eval.py` can detect triggering events by parsing `claude -p --output-format stream-json --verbose --include-partial-messages` output (looking for `tool_use` events with the `Skill` or `Read` tool targeting the skill name), but this is only used during eval testing, not runtime monitoring.

The closest mechanisms are:
- The `run_eval.py` stream parsing captures whether a skill was triggered (binary yes/no)
- The skill-creator's eval framework captures `total_tokens` and `duration_ms` from subagent task notifications
- The project's `run_eval.py` defines an `ExecutionResult` dataclass with `tokens`, `tool_calls`, and `transcript` fields (but execution is stubbed)

**Evidence:**

```python
# Skill-creator run_eval.py: detecting skill trigger in stream
if se_type == "content_block_start":
    cb = se.get("content_block", {})
    if cb.get("type") == "tool_use":
        tool_name = cb.get("name", "")
        if tool_name in ("Skill", "Read"):
            pending_tool_name = tool_name
```

— `/home/vscode/.agents/skills/skill-creator/scripts/run_eval.py:136-141`

**Dependencies:** Depends on `claude` CLI's `--output-format stream-json` capability for any triggering detection.

**Implicit contracts:** There is no production observability for skill usage. Telemetry is available only during explicit eval runs. Whether an agent "followed guidance" can only be assessed post-hoc via transcript analysis (as done by the grader and analyzer agents in the skill-creator framework).

---

## Discovered Patterns

1. **Convention-over-configuration:** The entire skill system relies on filesystem conventions rather than explicit configuration. Placing a valid SKILL.md in the right directory activates a skill; no registry update is needed.

2. **Progressive disclosure via explicit Read:** Reference files are never auto-loaded. The SKILL.md body must contain clear pointers (e.g., "See `references/schemas.md` for...") that tell the consuming agent when and why to read additional files.

3. **Dual validation paths:** The skill-creator's `quick_validate.py` enforces a strict set of allowed frontmatter properties (`name`, `description`, `license`, `allowed-tools`, `metadata`, `compatibility`), but the project-local QRSPI skills use additional fields (`command`, `argument-hint`) that would fail this validation.

4. **Stub execution in project evals:** The project's eval harness (`scripts/run_eval.py`) has full orchestration infrastructure (threading, config, output structure) but the actual agent execution is a placeholder awaiting runtime integration.

5. **Two distinct eval systems:** The skill-creator's `run_eval.py` tests description triggering (does Claude invoke the skill?), while the project's `run_eval.py` tests skill output quality (does the skill produce correct results?). These serve complementary but different purposes.

6. **Workspace-as-sibling pattern:** Working artifacts during skill development go in `<skill-name>-workspace/` next to the skill directory, organized by iteration.

7. **Frontmatter fields diverge from platform to platform:** The skill-creator validates 6 fields, but Claude Code's runtime accepts at least `command` and `argument-hint` in addition. The actual runtime schema is broader than the skill-creator's validator knows about.

## Inconsistencies

1. **Frontmatter schema mismatch:** The `quick_validate.py` script defines `ALLOWED_PROPERTIES = {'name', 'description', 'license', 'allowed-tools', 'metadata', 'compatibility'}`, but all 10 project-local QRSPI skills use `command` and `argument-hint` fields that would fail this validation. This means the skill-creator's validation cannot be run against this project's own skills without errors.

2. **Documentation vs. code on line limits:** The skill-creator's SKILL.md says "Keep SKILL.md under 500 lines" as a guideline, but its own SKILL.md is 486 lines (very close to the limit). No enforcement mechanism exists despite the questions.md referencing a "500-line / 5000-token limit stated in acceptance criteria."

3. **Package exclusion gap:** `package_skill.py` excludes root-level `evals/` directories from packages, but the workspace directory (`<skill-name>-workspace/`) used during development is not in the exclusion list. If a workspace directory were accidentally placed inside a skill directory, it would be included in the package.

4. **Missing `run_loop` module reference:** The skill-creator SKILL.md references running `python -m scripts.run_loop` but the `scripts/` package in the agents directory has no `__main__.py`, relying on `-m scripts.run_loop` to work via the `scripts/__init__.py` being present (which it is — but the import path assumes CWD is the skill-creator root).

5. **No "agentskills.io" standard found:** Q4 asks about an "agentskills.io standard" but no reference to this exists anywhere in the codebase or skill-creator. The standard is either external/undocumented or does not exist in this context.
