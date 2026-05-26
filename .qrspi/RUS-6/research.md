# Research — Codebase Map
**Questions source:** questions.md @ 2026-05-26T00:00:00Z
**Generated:** 2026-05-26T00:45:00Z
**Status:** draft

## Q1: How does the existing skill-creator skill discover and load a SKILL.md file — what directory structure, file naming, and frontmatter fields does it validate during skill ingestion?

**Answer:** The skill-creator relies on two mechanisms for discovery and validation:

1. **Directory structure:** Skills live in a directory named after the skill, containing a required `SKILL.md` file and optional subdirectories (`scripts/`, `references/`, `assets/`). The canonical layout is:
   ```
   skill-name/
   ├── SKILL.md (required)
   ├── scripts/    (optional)
   ├── references/ (optional)
   └── assets/     (optional)
   ```

2. **Validation via `quick_validate.py`:** The `parse_skill_md()` function in `scripts/utils.py` loads the SKILL.md by reading the file, finding the `---` delimiters, and parsing frontmatter line-by-line (not via a full YAML parser). The `quick_validate.py` script does use `yaml.safe_load()` and validates:
   - File must start with `---` (opening frontmatter)
   - Must have a closing `---`
   - Frontmatter must parse as a YAML dictionary
   - **Allowed keys (exhaustive):** `name`, `description`, `license`, `allowed-tools`, `metadata`, `compatibility`
   - **Required keys:** `name`, `description`
   - `name` must be a string, kebab-case (`[a-z0-9-]+`), no leading/trailing hyphens, no consecutive hyphens, max 64 characters
   - `description` must be a string, no angle brackets (`<` or `>`), max 1024 characters
   - `compatibility` (optional) must be a string, max 500 characters

**Evidence:**
```python
# scripts/quick_validate.py:42-43
ALLOWED_PROPERTIES = {'name', 'description', 'license', 'allowed-tools', 'metadata', 'compatibility'}
```
```python
# scripts/quick_validate.py:53-56
if 'name' not in frontmatter:
    return False, "Missing 'name' in frontmatter"
if 'description' not in frontmatter:
    return False, "Missing 'description' in frontmatter"
```
```python
# scripts/quick_validate.py:65-66
if not re.match(r'^[a-z0-9-]+$', name):
    return False, f"Name '{name}' should be kebab-case ..."
```
```python
# scripts/quick_validate.py:84
if len(description) > 1024:
    return False, f"Description is too long ({len(description)} characters). Maximum is 1024 characters."
```

**Dependencies:** `quick_validate.py` imports `yaml` (PyYAML) and `re`. `package_skill.py` calls `validate_skill()` before packaging.

**Implicit contracts:**
- The `utils.py` `parse_skill_md()` function parses frontmatter with a custom line parser (not YAML), while `quick_validate.py` uses `yaml.safe_load()` — these are two different parsing paths.
- The project-level SKILL.md files (e.g., `qrspi-work`) include additional frontmatter keys (`command`, `argument-hint`) that are NOT in the `ALLOWED_PROPERTIES` set. These keys would fail `quick_validate.py` validation. This suggests project skills and the skill-creator validation operate under different schemas.

---

## Q2: When a skill is registered in `.claude/settings.json`, what exact schema and key structure does the harness expect for the skill entry, and how does it resolve the `SKILL.md` path relative to the project root?

**Answer:** Skills are NOT registered in `.claude/settings.json` via an explicit registry entry. The project's settings files (`/home/vscode/.claude/settings.json` and `/home/vscode/.claude/projects/-workspaces-qrspi/settings.json`) contain `permissions`, `env`, `hooks`, and UI preferences — no skill registration keys.

Instead, the Claude Code harness discovers skills through two mechanisms:

1. **Project skills:** Auto-discovered by scanning `.claude/skills/` for subdirectories containing `SKILL.md`. The harness scans `<project-root>/.claude/skills/<skill-name>/SKILL.md` at startup.

2. **User-level skills:** Discovered from `~/.agents/skills/` (e.g., `/home/vscode/.agents/skills/using-graphite-cli/SKILL.md`, `/home/vscode/.agents/skills/skill-creator/SKILL.md`).

3. **Plugin skills:** Discovered from plugin directories under `~/.claude/plugins/marketplaces/`. Plugins declare metadata in `.claude-plugin/plugin.json` and skills live under `skills/<skill-name>/SKILL.md` within the plugin tree.

**Evidence:**
```json
// /home/vscode/.claude/settings.json — no skill entries
{
  "env": { "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1" },
  "permissions": { "allow": [...] },
  "hooks": { ... }
}
```
```json
// /home/vscode/.claude/projects/-workspaces-qrspi/settings.json — no skill entries
{ "permissions": { "deny": [...] } }
```

The skill-development documentation states:
```
Claude Code automatically discovers skills:
- Scans `skills/` directory
- Finds subdirectories containing `SKILL.md`
- Loads skill metadata (name + description) always
- Loads SKILL.md body when skill triggers
- Loads references/examples when needed
```
(`plugin-dev/skills/skill-development/SKILL.md:270-276`)

**Dependencies:** Path resolution is relative to the `.claude/` directory for project skills, or relative to the plugin's root for plugin skills. User-level skills reference is via `~/.agents/skills/`.

**Implicit contracts:** The harness resolves skills by directory-scanning convention, not explicit registration. Adding a new skill requires only creating the directory with a valid `SKILL.md` — no settings.json update.

---

## Q3: What is the data flow when a skill's `references/` directory is loaded — are reference files injected into context at skill invocation time, on demand via explicit read, or pre-indexed at registration?

**Answer:** Reference files are loaded **on demand via explicit read** by the model, not injected automatically at invocation time or pre-indexed.

The skill-development documentation describes a three-level progressive disclosure system:
1. **Metadata (name + description):** Always in context (~100 words)
2. **SKILL.md body:** Loaded when skill triggers (<5k words)
3. **Bundled resources (references/, scripts/, assets/):** Loaded as needed by Claude

The SKILL.md body is expected to contain pointers telling the model when and how to read reference files. The model uses `Read` tool calls to load them during execution.

**Evidence:**
```
# skill-development/SKILL.md:77-82
1. **Metadata (name + description)** - Always in context (~100 words)
2. **SKILL.md body** - When skill triggers (<5k words)
3. **Bundled resources** - As needed by Claude (Unlimited*)

*Unlimited because scripts can be executed without reading into context window.
```

```
# skill-creator SKILL.md:89-93 (the three-level system)
1. **Metadata** (name + description) - Always in context (~100 words)
2. **SKILL.md body** - In context whenever skill triggers (<500 lines ideal)
3. **Bundled resources** - As needed (unlimited, scripts can execute without loading)
```

Real-world example: `qrspi-work/SKILL.md` references `references/review-cascade.md` and instructs the model to "Read `references/review-cascade.md` for cascade logic" (line 175). The model performs an explicit `Read` tool call at that point.

**Dependencies:** Reference loading depends on the model's `Read` tool being available. The `allowed-tools` frontmatter field controls which tools a skill can use.

**Implicit contracts:** SKILL.md must explicitly mention reference files for the model to know they exist. Unreferenced files in `references/` will likely never be read.

---

## Q4: What frontmatter fields does the agentskills.io standard require in SKILL.md, and which fields does the skill-creator skill enforce as mandatory vs. optional during generation?

**Answer:** The term "agentskills.io standard" does not appear anywhere in the codebase. The validation logic in the skill-creator defines its own schema.

**Mandatory fields (enforced by `quick_validate.py`):**
- `name` — string, kebab-case, max 64 characters
- `description` — string, no angle brackets, max 1024 characters

**Optional fields (allowed but not required by `quick_validate.py`):**
- `license`
- `allowed-tools`
- `metadata`
- `compatibility` — string, max 500 characters

**Additional fields used by project skills (NOT validated by skill-creator):**
- `command` — slash command alias (e.g., `/qrspi-research`)
- `argument-hint` — user-facing hint for arguments
- `version` — version string (seen in plugin-dev skills)

The project-level SKILL.md files in this repository use `command` and `argument-hint` extensively, but these would FAIL the skill-creator's `quick_validate.py` because they are not in `ALLOWED_PROPERTIES`.

**Evidence:**
```python
# scripts/quick_validate.py:42
ALLOWED_PROPERTIES = {'name', 'description', 'license', 'allowed-tools', 'metadata', 'compatibility'}
```
```yaml
# Project skill example (qrspi-research/SKILL.md:1-7)
---
name: qrspi-research
description: Map codebase facts...
command: /qrspi-research
argument-hint: <ticket-id>
allowed-tools: Read, Glob, Grep, ...
---
```

The frontmatter reference doc (`plugin-dev/skills/command-development/references/frontmatter-reference.md`) lists `description`, `allowed-tools`, `model`, `argument-hint`, and `disable-model-invocation` as supported fields for commands. These overlap with but differ from the skill-creator's allowed set.

**Dependencies:** The skill-creator's validator and the Claude Code harness's skill loader appear to be separate systems with different schema expectations.

**Implicit contracts:** The `allowed-tools` key is shared between both schemas, but `command`, `argument-hint`, `model`, and `disable-model-invocation` exist only in the harness schema, while `license`, `metadata`, and `compatibility` exist only in the skill-creator schema.

---

## Q5: What is the maximum token budget the harness enforces for a skill's SKILL.md body content, and how is that limit measured (raw token count, line count, or both)?

**Answer:** There is no programmatic enforcement of a token or line budget in the codebase. The limits are stated as guidance in documentation, not as validated constraints.

The skill-creator SKILL.md states:
- `<500 lines ideal` for SKILL.md body (line 92)
- Body content described as `<5k words` in the skill-development docs (line 82)

The skill-development documentation also recommends:
- `1,500-2,000 words` for the body (ideal)
- `<5k words` as max (line 82)
- `<3,000 words` without references files (line 477)

The `quick_validate.py` script does NOT check line count, word count, or token count for the body. It only validates frontmatter fields. No other validation script in the codebase measures body size.

**Evidence:**
```python
# scripts/quick_validate.py — complete validation logic
# Lines 12-94: Only validates frontmatter (name, description, compatibility)
# No body-size check exists
```

```
# skill-creator SKILL.md:91-92
2. **SKILL.md body** - In context whenever skill triggers (<500 lines ideal)
3. **Bundled resources** - As needed (unlimited, scripts can execute without loading)
```

```
# skill-development/SKILL.md:82
2. **SKILL.md body** - When skill triggers (<5k words)
```

**Dependencies:** None — there is no enforcement code.

**Implicit contracts:** The `<500 lines` and `<5k words` limits are soft guidance. The only hard limits are on frontmatter fields: `name` max 64 chars, `description` max 1024 chars, `compatibility` max 500 chars.

---

## Q6: How does the skill-creator skill's eval loop work — what inputs does it accept, what assertions does it run, and what output format does it produce for pass/fail determination?

**Answer:** The skill-creator has two eval systems:

### 1. Trigger eval (`run_eval.py` / `run_loop.py`)
Tests whether the skill description causes Claude to invoke the skill for given queries.

**Inputs:**
- `--eval-set`: JSON file with `[{"query": "...", "should_trigger": true/false}, ...]`
- `--skill-path`: Path to the skill directory
- `--model`: Claude model ID
- `--runs-per-query`: Number of runs per query (default 3)
- `--trigger-threshold`: Fraction threshold (default 0.5)

**Mechanism:** Creates a temporary command file in `.claude/commands/`, runs `claude -p <query> --output-format stream-json --verbose --include-partial-messages`, monitors stream events for Skill or Read tool calls targeting the skill name.

**Output format:**
```json
{
  "skill_name": "...",
  "description": "...",
  "results": [
    { "query": "...", "should_trigger": true, "trigger_rate": 0.67, "triggers": 2, "runs": 3, "pass": true }
  ],
  "summary": { "total": 20, "passed": 18, "failed": 2 }
}
```

### 2. Qualitative eval (SKILL.md instructions + subagents)
Tests whether the skill produces correct outputs.

**Inputs:** Test prompts in `evals/evals.json`:
```json
{
  "skill_name": "...",
  "evals": [
    { "id": 1, "prompt": "...", "expected_output": "...", "files": [], "expectations": ["..."] }
  ]
}
```

**Mechanism:** Spawns subagent pairs (with-skill, without-skill), runs the grader agent (`agents/grader.md`) which evaluates each expectation against transcript and outputs.

**Grading output format (`grading.json`):**
```json
{
  "expectations": [{ "text": "...", "passed": true, "evidence": "..." }],
  "summary": { "passed": 2, "failed": 1, "total": 3, "pass_rate": 0.67 }
}
```

**Evidence:**
```python
# scripts/run_eval.py:184-256 — run_eval function signature and return format
# scripts/run_eval.py:36-178 — run_single_query detection logic
```
```python
# scripts/run_loop.py:47-241 — run_loop with train/test split, improvement iterations
```

**Dependencies:** `run_eval.py` depends on `claude` CLI (`claude -p`). `run_loop.py` depends on `run_eval.py` and `improve_description.py`. Grading depends on subagent spawning.

**Implicit contracts:**
- The trigger eval uses `select.select()` for non-blocking I/O — POSIX-only, will not work on Windows.
- The `CLAUDECODE` environment variable is stripped to allow nested `claude -p` calls.
- Temporary command files are created in `.claude/commands/` and cleaned up in a `finally` block.

---

## Q7: When multiple skills are registered, how does the harness determine trigger priority — is there an explicit ordering, a scoring mechanism based on the description field, or first-match semantics?

**Answer:** The harness presents all registered skills as an `available_skills` list in system-reminder messages. The model (Claude) decides which skill to invoke based on the description text. There is no explicit ordering, scoring mechanism, or first-match logic in the harness itself — it is an LLM-based decision.

**Evidence:** The system-reminder at the start of this session shows:
```
The following skills are available for use with the Skill tool:
- using-graphite-cli: Use for ANY request involving version control...
- skill-creator: Create new skills...
- qrspi-work: Single entry point for autonomous QRSPI feature development...
[etc.]
```

The skill-creator's description optimization section confirms:
```
# skill-creator SKILL.md:396-398
Understanding the triggering mechanism helps design better eval queries.
Skills appear in Claude's `available_skills` list with their name + description,
and Claude decides whether to consult a skill based on that description.
```

The `run_eval.py` trigger detection mechanism (`run_single_query`) monitors for `Skill` or `Read` tool calls — this confirms the model decides via tool use, not a harness-side dispatch.

**Dependencies:** Triggering depends entirely on the model's inference.

**Implicit contracts:** Skills compete for attention via their description text. The skill-creator docs note a tendency to "undertrigger" and recommend "pushy" descriptions. There is no guaranteed priority order.

---

## Q8: If a skill references CLI tools that may not be installed (e.g., `gt`), does the harness or skill loader perform any pre-invocation availability check, or is failure deferred to runtime execution?

**Answer:** There is no pre-invocation availability check. Failure is deferred to runtime execution.

The `compatibility` frontmatter field exists in the skill-creator schema, but the `quick_validate.py` only checks that it is a string under 500 characters — it does not parse or act on the value. No code in the codebase reads the `compatibility` field to check tool availability.

The harness does not inspect `allowed-tools` to verify that referenced CLI tools exist on the system. If a skill instructs the model to run `gt` and `gt` is not installed, the `Bash` tool call will fail at execution time with a "command not found" error.

**Evidence:**
```python
# scripts/quick_validate.py:87-93
compatibility = frontmatter.get('compatibility', '')
if compatibility:
    if not isinstance(compatibility, str):
        return False, f"Compatibility must be a string, got {type(compatibility).__name__}"
    if len(compatibility) > 500:
        return False, f"Compatibility is too long ({len(compatibility)} characters). Maximum is 500 characters."
```

No code in the skill loader, harness, or validation scripts performs `which`, `command -v`, or any other CLI availability check.

**Dependencies:** None — the check simply does not exist.

**Implicit contracts:** Skills are responsible for handling CLI unavailability gracefully in their instructions. The `using-graphite-cli` skill assumes `gt` is available without verifying.

---

## Q9: What happens when two registered skills have overlapping trigger descriptions — for example, if both a `using-graphite-cli` skill and a generic `git-workflow` skill match a user request involving branch creation?

**Answer:** The harness does not prevent or warn about overlapping trigger descriptions. Disambiguation is handled entirely by the model at inference time, based on the description text in the `available_skills` list.

The `using-graphite-cli` skill uses an extremely aggressive description to win over generic git skills:

```yaml
description: "Use for ANY request involving version control, commits, branches, diffs,
or pull requests — this is the mandatory, exclusive way to perform all such operations.
... Even simple read-only checks like viewing a diff or status must go through this skill.
Never run raw git or gt commands outside it."
```

This "pushy" pattern is recommended by the skill-creator:
```
# skill-creator SKILL.md:67
Note: currently Claude has a tendency to "undertrigger" skills -- to not use them when
they'd be useful. To combat this, please make the skill descriptions a little bit "pushy".
```

If two skills have overlapping descriptions, the model will use one based on its judgment. The `Skill` tool accepts a `skill` parameter with the skill name, so the model must name exactly one. There is no mechanism for the harness to invoke both or to detect the conflict.

**Evidence:** The system-reminder `available_skills` list is a flat, unordered enumeration. The `Skill` tool call schema requires a single `skill` name.

**Dependencies:** Resolution depends entirely on the model.

**Implicit contracts:** Skill authors must write descriptions that are distinctive enough to avoid confusion. The skill-creator's description optimization loop (`run_loop.py`) specifically tests for false triggers on near-miss queries.

---

## Q10: If a skill's SKILL.md body exceeds the 500-line or 5000-token limit specified in the acceptance criteria, does the skill-creator skill reject it at generation time, at registration time, or does it silently truncate?

**Answer:** Neither. There is no programmatic rejection or truncation at any stage.

- **Generation time:** The skill-creator SKILL.md provides guidance ("Keep SKILL.md under 500 lines" on line 97), but the generation process is conversational — it relies on the model following the guidance, not on code enforcement.
- **Registration time:** The harness auto-discovers skills by scanning directories for SKILL.md files. There is no size check during discovery.
- **Validation time:** `quick_validate.py` does NOT check body size (line count, word count, or token count). It only validates frontmatter fields.
- **Runtime:** The entire SKILL.md body is loaded into context when the skill triggers. Oversized skills consume more context but are not rejected.

The existing `qrspi-work/SKILL.md` in this project is 500 lines — exactly at the recommended limit.

**Evidence:**
```bash
# Line counts of project skills
# qrspi-work/SKILL.md: 500 lines
# qrspi-ticket/SKILL.md: 75 lines
# qrspi-research/SKILL.md: 57 lines
```

```python
# scripts/quick_validate.py — complete function ends at line 94
# No body size validation exists
```

**Dependencies:** None.

**Implicit contracts:** The 500-line/5k-word limit is a soft convention enforced by the skill-creator's instructions to the model, not by code. Exceeding it degrades performance (more context consumed) but does not cause an error.

---

## Q11: How does the harness behave when a skill's SKILL.md references a `scripts/` or `assets/` subdirectory that does not exist on disk — does it fail loudly, skip silently, or produce a warning?

**Answer:** The harness skips silently. There is no directory existence check at skill discovery or load time.

The harness only requires `SKILL.md` to exist in the skill directory. The presence of `scripts/`, `references/`, or `assets/` subdirectories is not checked. If the SKILL.md body instructs the model to read a reference file or execute a script, and the file does not exist, the `Read` or `Bash` tool call will fail at runtime with a standard "file not found" error.

**Evidence:** The skill-development documentation states:
```
# plugin-dev/skills/skill-development/SKILL.md:270-276
Claude Code automatically discovers skills:
- Scans `skills/` directory
- Finds subdirectories containing `SKILL.md`
- Loads skill metadata (name + description) always
- Loads SKILL.md body when skill triggers
- Loads references/examples when needed
```

Only `SKILL.md` existence is required. No subdirectory validation occurs.

The `package_skill.py` also only checks for `SKILL.md`:
```python
# scripts/package_skill.py:65-67
skill_md = skill_path / "SKILL.md"
if not skill_md.exists():
    print(f"Error: SKILL.md not found in {skill_path}")
```

**Dependencies:** None.

**Implicit contracts:** Skills should only reference subdirectories and files that actually exist. Missing file errors manifest as runtime tool failures, not loader errors.

---

## Q12: What existing eval patterns or test fixtures exist for other skills in this project, and what is the expected structure of a skill eval (input prompt, expected behavior, assertion format)?

**Answer:** Two eval artifacts exist in this project:

### 1. `evals/suite.json` — QRSPI phase-level eval suite

Contains 15 test cases covering all QRSPI phases (questions, research, design, structure, plan, worktree, implement, pr). Each case has:

```json
{
  "id": "case_001",
  "name": "questions_happy_path",
  "phase": "questions",
  "prompt": "Generate questions for the following ticket.",
  "context": { "files": ["fixtures/ticket_rest_endpoint.md"] },
  "assertions": [
    { "type": "programmatic", "check": "output_file_exists('questions.md')", "weight": 1.0 },
    { "type": "llm_judge", "criteria": "Questions are specific and answerable...", "weight": 2.0 }
  ],
  "tags": ["questions", "happy-path"],
  "difficulty": "easy",
  "split": "train"
}
```

Assertion types: `programmatic` (code-checkable), `llm_judge` (model-judged), `script` (external script).

Suite-level config:
```json
{
  "split": { "train_ratio": 0.65, "test_ratio": 0.35, "seed": 42 },
  "defaults": { "trials_per_case": 3, "timeout_ms": 120000, "max_tokens": 128000 }
}
```

### 2. `evals/graphite-evals.json` — Graphite CLI skill trigger eval

Contains 5 test cases in skill-creator `evals.json` format:
```json
{
  "skill_name": "graphite",
  "evals": [
    { "id": 1, "prompt": "...", "expected_output": "...", "files": [],
      "assertions": [{ "text": "...", "type": "command_check" }] }
  ]
}
```

Assertion types used: `command_check`, `flag_check`, `content_check`, `workflow_check`, `safety_check`.

### Fixture files
Located in `evals/fixtures/`:
- `ticket_rest_endpoint.md`
- `ticket_multi_tenancy.md`
- `ticket_websocket.md`
- `ticket_15_acceptance_criteria.md`
- `evals/golden/.gitkeep` (empty, placeholder for golden outputs)

**Evidence:** Full contents at `/workspaces/qrspi/evals/suite.json` (780 lines) and `/workspaces/qrspi/evals/graphite-evals.json` (68 lines).

**Dependencies:** The suite.json eval cases reference fixture files that may or may not all exist (e.g., `fixtures/questions_rest_endpoint.md` is referenced but its existence is unverified).

**Implicit contracts:** The suite.json format is custom to this project and differs from the skill-creator's `evals.json` format. The graphite-evals.json follows the skill-creator format.

---

## Q13: Does the skill-creator skill produce eval cases automatically as part of skill generation, or must they be authored separately after the SKILL.md is created?

**Answer:** Eval cases are authored as a separate step after the SKILL.md draft is written. They are NOT automatically generated during skill creation.

The skill-creator's workflow is explicitly sequential:
1. Capture intent
2. Interview and research
3. Write the SKILL.md
4. **Then:** "After writing the skill draft, come up with 2-3 realistic test prompts" (line 143)
5. Save test cases to `evals/evals.json`
6. Run test cases and evaluate

The trigger eval queries (for description optimization) are also a separate post-creation step:
1. Generate 20 eval queries (8-10 should-trigger, 8-10 should-not-trigger)
2. Review with user via HTML template
3. Run the optimization loop

**Evidence:**
```
# skill-creator SKILL.md:143-145
After writing the skill draft, come up with 2-3 realistic test prompts — the kind of
thing a real user would actually say. Share them with the user...
Save test cases to `evals/evals.json`. Don't write assertions yet — just the prompts.
```

```
# skill-creator SKILL.md:339-341
### Step 1: Generate trigger eval queries
Create 20 eval queries — a mix of should-trigger and should-not-trigger.
```

**Dependencies:** Eval authoring depends on having a completed SKILL.md draft first.

**Implicit contracts:** The skill-creator expects human involvement in eval creation — the model proposes test prompts and the user reviews/modifies them. Assertions are drafted while test runs are in progress (a concurrent step).

---

## Q14: When a skill is triggered and executed, what logging or tracing does the harness emit — are there log lines indicating which skill was selected, why it matched, and how long execution took?

**Answer:** NOT FOUND in the project codebase. The harness logging behavior is not implemented in any code within this repository.

The closest observable behavior is the system-reminder mechanism, which injects the `available_skills` list into the conversation. When a skill is invoked, the `Skill` tool call is visible in the conversation transcript, showing which skill was selected and the arguments passed. However, this is conversational output, not structured logging.

The `run_eval.py` script provides observability during eval runs via `--verbose` flag, printing per-query trigger status:
```python
# scripts/run_eval.py:299-304
for r in output["results"]:
    status = "PASS" if r["pass"] else "FAIL"
    rate_str = f"{r['triggers']}/{r['runs']}"
    print(f"  [{status}] rate={rate_str} expected={r['should_trigger']}: {r['query'][:70]}", file=sys.stderr)
```

But this is eval-time instrumentation, not runtime production logging.

**Search queries attempted:**
- `find /workspaces/qrspi -name "*.py" -exec grep -l "logging\|logger\|log\." {} \;` — no relevant results
- `find /workspaces/qrspi -name "*.ts" -o -name "*.js" | head` — no TypeScript/JavaScript source files exist in this project
- Searched for "trace", "telemetry", "metric" in project files — no matches

**Dependencies:** N/A

**Implicit contracts:** The harness is a closed-source component of Claude Code. Its internal logging behavior is not configurable or observable from the project codebase.

---

## Discovered Patterns

1. **Two-schema divergence:** The skill-creator's `quick_validate.py` enforces a schema (`name`, `description`, `license`, `allowed-tools`, `metadata`, `compatibility`) that differs from the project-level SKILL.md schema (`name`, `description`, `command`, `argument-hint`, `allowed-tools`). Keys like `command` and `argument-hint` are used by every project skill but would fail skill-creator validation.

2. **Progressive disclosure as architecture:** All skill documentation consistently describes a three-tier loading model (metadata → body → resources). This is a design convention, not enforced by code.

3. **Description as trigger mechanism:** Skill triggering is entirely model-driven, based on description text quality. The skill-creator's description optimization system (`run_eval.py`, `run_loop.py`, `improve_description.py`) is the most sophisticated code in the skill ecosystem, treating description tuning as an ML-style optimization problem with train/test splits and iterative improvement.

4. **Dual parsing paths:** `utils.py:parse_skill_md()` uses a custom line-by-line parser for frontmatter, while `quick_validate.py` uses `yaml.safe_load()`. The line parser handles YAML multiline indicators (`>`, `|`, `>-`, `|-`) but may diverge from full YAML spec on edge cases.

5. **Convention over configuration:** Skills are discovered by directory structure convention (any directory with a `SKILL.md` under `.claude/skills/` or `~/.agents/skills/`). No registration, no manifest file, no settings entry.

6. **Eval format bifurcation:** This project has two distinct eval formats: the QRSPI `suite.json` (with `programmatic`/`llm_judge`/`script` assertion types and `weight` fields) and the skill-creator `evals.json` (with text-based assertions and `expectations` lists). These are incompatible schemas serving different evaluation needs.

7. **Soft limits only:** All size constraints (500 lines, 5k words, 1024 chars for description, 64 chars for name) are either guidance in documentation or validated only for frontmatter metadata. Body content has no programmatic enforcement.

---

## Inconsistencies

1. **`command` and `argument-hint` frontmatter keys:** Every project-level SKILL.md in `.claude/skills/` uses `command` and `argument-hint` frontmatter fields, but these are NOT in the skill-creator's `ALLOWED_PROPERTIES` set. Running `quick_validate.py` on any project skill would fail with "Unexpected key(s) in SKILL.md frontmatter: argument-hint, command."

2. **Description style guidance conflicts:** The skill-creator SKILL.md says to make descriptions "pushy" and does not mandate any particular grammatical person (line 67). The skill-development skill from plugin-dev says to use third person: "This skill should be used when..." (line 163). The project's actual skills use second-person imperative ("Use when...", "Use after...") — matching neither recommendation.

3. **Word vs. line limits:** The skill-creator recommends `<500 lines ideal` for SKILL.md body. The skill-development documentation recommends `1,500-2,000 words` ideal and `<5k words` max. These are different units measuring different things (a 500-line file could contain ~2,500 words, which is within the word budget but over the skill-development ideal).

4. **YAML parsing inconsistency:** `utils.py:parse_skill_md()` parses frontmatter with a custom line-based approach that handles YAML multiline indicators. `quick_validate.py` uses `yaml.safe_load()`. If a SKILL.md uses a YAML feature that the line parser handles differently from the YAML spec (e.g., complex nested structures), the two functions could return different results for the same file.

5. **Missing fixture files:** `evals/suite.json` references fixture files like `fixtures/questions_rest_endpoint.md`, `fixtures/research_rest_endpoint.md`, `fixtures/design_rest_endpoint.md`, etc. Only four fixture files exist in `evals/fixtures/`. The remaining referenced fixtures would cause eval failures.

6. **`version` field in plugin-dev skills:** The `skill-development/SKILL.md` uses `version: 0.1.0` in its frontmatter, but `version` is not in the skill-creator's `ALLOWED_PROPERTIES` set and would fail validation.
