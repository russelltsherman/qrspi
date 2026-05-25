# Research — Codebase Map
**Questions source:** questions.md @ 2026-05-25T22:25:00Z
**Generated:** 2026-05-25T22:45:00Z
**Status:** draft

## Q1: How does the existing skill-creator skill discover and validate SKILL.md frontmatter fields, and what schema does it enforce for the frontmatter block?

**Answer:** The skill-creator validates frontmatter via `scripts/quick_validate.py`. It enforces:
- SKILL.md must start with `---` and have a closing `---` delimiter
- Frontmatter must parse as a YAML dictionary
- Required fields: `name`, `description`
- Allowed properties: `{'name', 'description', 'license', 'allowed-tools', 'metadata', 'compatibility'}`
- Unexpected keys cause validation failure
- `name`: must be a string, kebab-case (`[a-z0-9-]+`), no leading/trailing/consecutive hyphens, max 64 characters
- `description`: must be a string, no angle brackets (`<` or `>`), max 1024 characters
- `compatibility`: optional string, max 500 characters

**Evidence:**
```python
# quick_validate.py:42-46
ALLOWED_PROPERTIES = {'name', 'description', 'license', 'allowed-tools', 'metadata', 'compatibility'}
unexpected_keys = set(frontmatter.keys()) - ALLOWED_PROPERTIES
if unexpected_keys:
    return False, (
        f"Unexpected key(s) in SKILL.md frontmatter: {', '.join(sorted(unexpected_keys))}. "
```

```python
# quick_validate.py:53-56
if 'name' not in frontmatter:
    return False, "Missing 'name' in frontmatter"
if 'description' not in frontmatter:
    return False, "Missing 'description' in frontmatter"
```

```python
# quick_validate.py:64-66
if not re.match(r'^[a-z0-9-]+$', name):
    return False, f"Name '{name}' should be kebab-case (lowercase letters, digits, and hyphens only)"
```

The `utils.py` module (`parse_skill_md`) handles parsing frontmatter for runtime use — it extracts `name` and `description` only, supporting YAML multiline indicators (`>`, `|`, `>-`, `|-`).

```python
# utils.py:7
def parse_skill_md(skill_path: Path) -> tuple[str, str, str]:
    """Parse a SKILL.md file, returning (name, description, full_content)."""
```

**Dependencies:** `quick_validate.py` depends on `yaml` (PyYAML) and `re` stdlib. `utils.py` is imported by `run_eval.py`, `run_loop.py`, and `improve_description.py`.

**Implicit contracts:**
- The `allowed-tools` key is listed as an allowed frontmatter property in `quick_validate.py`, but neither `quick_validate.py` nor `utils.py` parses or validates its value.
- The `metadata` key is allowed but never validated for structure.
- `parse_skill_md` in `utils.py` uses simple string parsing (not YAML library), so it only extracts `name` and `description` — other fields are ignored at runtime.

---

## Q2: What is the agentskills.io standard directory structure, and how do existing skills in this project organize their `SKILL.md`, `references/`, `scripts/`, and `assets/` directories?

**Answer:** The canonical directory structure documented in the skill-creator SKILL.md (line 76-84) is:

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

The plugin-dev `skill-development` SKILL.md also documents this structure identically (line 27-39), with `examples/` as an additional standard subdirectory.

**Existing skills in this project** (`/workspaces/qrspi/.claude/skills/`) are minimal — they use only:
- `SKILL.md` (all 10 skills have this)
- `references/` (only `qrspi-work` has this, containing `review-cascade.md`)

No skills in the project use `scripts/`, `assets/`, or `examples/` subdirectories.

Full inventory:
```
qrspi-design/SKILL.md
qrspi-implement/SKILL.md
qrspi-plan/SKILL.md
qrspi-pr/SKILL.md
qrspi-questions/SKILL.md
qrspi-research/SKILL.md
qrspi-structure/SKILL.md
qrspi-ticket/SKILL.md
qrspi-work/SKILL.md
qrspi-work/references/review-cascade.md
qrspi-worktree/SKILL.md
```

**Dependencies:** Skills are auto-discovered by Claude Code by scanning `skills/` for subdirectories containing `SKILL.md` (documented in `plugin-structure` SKILL.md, line 171-176).

**Implicit contracts:**
- The `SKILL.md` filename is required (not `README.md` or any other name).
- Directory name determines the skill's slug used in invocation.

---

## Q3: How does the skill-creator skill handle the generation of reference material files — does it produce them as separate documents in `references/`, or inline within SKILL.md?

**Answer:** The skill-creator instructs users to break content into `references/` when SKILL.md approaches the size budget. This is guidance-driven, not automatic.

From `SKILL.md:96-109`:
```markdown
**Key patterns:**
- Keep SKILL.md under 500 lines; if you're approaching this limit, add an additional
  layer of hierarchy along with clear pointers about where the model using the skill
  should go next to follow up.
- Reference files clearly from SKILL.md with guidance on when to read them
- For large reference files (>300 lines), include a table of contents

**Domain organization**: When a skill supports multiple domains/frameworks, organize by variant:
    cloud-deploy/
    ├── SKILL.md (workflow + selection)
    └── references/
        ├── aws.md
        ├── gcp.md
        └── azure.md
Claude reads only the relevant reference file.
```

The skill-creator also has its own `references/` directory containing `schemas.md` (JSON schema documentation for evals, grading, benchmark, etc.) and `agents/` directory with subagent prompts (`grader.md`, `comparator.md`, `analyzer.md`).

The decision to create reference files is left to Claude during skill authoring — there is no automated mechanism that detects oversized SKILL.md and splits content into reference files.

**Evidence:** The skill-creator SKILL.md body text at line 304:
```markdown
if all 3 test cases resulted in the subagent writing a `create_docx.py` or a
`build_chart.py`, that's a strong signal the skill should bundle that script. Write
it once, put it in `scripts/`, and tell the skill to use it.
```

This shows the pattern: observation during eval drives the decision to extract content.

**Dependencies:** The `agents/` directory (containing `grader.md`, `comparator.md`, `analyzer.md`) is functionally equivalent to `references/` — loaded on demand by subagents.

**Implicit contracts:** Reference files must be explicitly pointed to from SKILL.md body text with guidance on when to read them. Claude will not discover unreferenced files.

---

## Q4: What trigger patterns (description field, keyword matching) do existing skills use to ensure Claude auto-invokes them, and what conventions exist for avoiding trigger collisions between skills that operate on overlapping CLI tooling?

**Answer:** Two conventions exist for trigger descriptions, and they contradict each other:

**Convention A — Skill-creator (pushy, imperative):** From skill-creator SKILL.md line 67:
```markdown
currently Claude has a tendency to "undertrigger" skills -- to not use them when
they'd be useful. To combat this, please make the skill descriptions a little bit
"pushy". So for instance, instead of "How to build a simple fast dashboard...",
you might write "How to build a simple fast dashboard... Make sure to use this skill
whenever the user mentions dashboards, data visualization..."
```

**Convention B — Plugin-dev/skill-development (third-person):** From `skill-development/SKILL.md:164-168`:
```yaml
description: This skill should be used when the user asks to "specific phrase 1",
"specific phrase 2", "specific phrase 3".
```

Existing skills in this project use a mix of styles:
- `qrspi-work`: Long quoted description with explicit trigger phrases: `"work on <ticket-id>"`, `"continue <ticket-id>"`, etc.
- `qrspi-questions`: Short functional: `"Generate 8-15 targeted technical questions from a feature ticket."`
- `qrspi-research`: Short functional with intent signaling: `"Map codebase facts by answering questions from the Questions phase."`
- `qrspi-ticket`: Short functional: `"Draft a new feature ticket through guided conversation."`

**No explicit collision-avoidance mechanism exists** in any of the examined skills or the skill-creator. The skill-creator's description optimization loop (see Q13) is the closest mechanism — it tests should-trigger and should-not-trigger queries to tune discrimination, but there is no cross-skill collision detection.

**Evidence:** All 10 qrspi skill descriptions from frontmatter (lines 2-3 of each SKILL.md):
- `qrspi-work`: 398 characters — most verbose, with explicit slash-command triggers
- `qrspi-questions`: 101 characters — shortest
- `qrspi-research`: 96 characters
- `qrspi-implement`: 110 characters
- All others: 60-120 characters

**Implicit contracts:**
- Description is the sole triggering mechanism — it appears in Claude's `available_skills` list.
- Hard limit of 1024 characters on description field (enforced by `quick_validate.py`).
- Skills with `command:` frontmatter field can also be invoked explicitly as slash commands (e.g., `/qrspi-work`), bypassing description-based triggering entirely.

---

## Q5: What is the token/line budget enforcement mechanism for SKILL.md body content, and does the skill-creator skill validate the 500-line / 5000-token acceptance criterion during generation?

**Answer:** The skill-creator states a soft guideline of 500 lines but does NOT programmatically enforce it during generation. There is no validation check in `quick_validate.py` for body length.

From skill-creator SKILL.md line 91-92:
```markdown
2. **SKILL.md body** - In context whenever skill triggers (<500 lines ideal)
```

And line 96:
```markdown
- Keep SKILL.md under 500 lines; if you're approaching this limit, add an additional
  layer of hierarchy
```

The word "ideal" and the phrasing "if you're approaching this limit" confirm this is advisory, not enforced.

The `quick_validate.py` script validates only frontmatter (name, description, compatibility fields and their constraints). It does not check body line count, word count, or token count.

The plugin-dev `skill-development` SKILL.md suggests a different budget: "1,500-2,000 words" for body, with "<5k words" as max. This is also advisory only.

Notably, the skill-creator's own SKILL.md is 485 lines / 5,138 words — right at its own stated limit, and exceeding the plugin-dev recommendation.

**Evidence:**
```python
# quick_validate.py — entire function validate_skill()
# Lines 12-94: validates frontmatter only, no body size checks
```

**Dependencies:** None — no body size validation exists anywhere in the codebase.

**Implicit contracts:** The 500-line budget is a convention communicated through the skill-creator SKILL.md instructions to Claude during skill authoring. Enforcement relies on Claude following the instruction.

---

## Q6: How do existing skills reference environment variables — are these documented inline in the SKILL.md body, or is there a separate configuration or prerequisites section?

**Answer:** No existing skill in this project (`/workspaces/qrspi/.claude/skills/`) references environment variables like `ARGOCD_AUTH_TOKEN` or `ARGOCD_SERVER`. The skills reference MCP tools and file paths, but not environment variables.

The only mention of environment variables in the project's skills is in the context of error handling — the `qrspi-work` SKILL.md forbids setting environment variables as workarounds:
```markdown
# qrspi-work/SKILL.md:467
- Setting environment variables to route around config paths (`XDG_CONFIG_HOME`, etc.)
```

The skill-creator SKILL.md has a `compatibility` frontmatter field for documenting dependencies (line 69):
```markdown
- **compatibility**: Required tools, dependencies (optional, rarely needed)
```

The plugin-dev `plugin-structure` SKILL.md shows environment variable usage in MCP server configs:
```json
"env": {
    "API_KEY": "${API_KEY}"
}
```

But there is no standardized "prerequisites" or "configuration" section pattern in any existing SKILL.md in this project.

**Evidence:** Searched all SKILL.md files in `/workspaces/qrspi/.claude/skills/` for `env`, `environment`, `prerequisite`, `AUTH_TOKEN` — only the error-handling negative reference was found.

**Dependencies:** N/A

**Implicit contracts:** Environment variable documentation is ad-hoc. The `compatibility` frontmatter field is the closest standard mechanism, but it is documented as "rarely needed" and no existing skill uses it.

---

## Q7: How does the skill-creator eval loop measure skill quality, and what metrics or rubric does it apply to determine whether a generated skill meets acceptance criteria?

**Answer:** The skill-creator uses a multi-layered quality measurement system:

**1. Quantitative eval (test case assertions):**
- Defined in `evals/evals.json` per skill
- Each eval has `expectations` (verifiable statements)
- Graded by `agents/grader.md` subagent producing `grading.json`
- Metrics: `pass_rate`, `passed`, `failed`, `total` per expectation
- Additional: `execution_metrics` (tool calls, output chars), `timing` (duration, tokens)

**2. Benchmark aggregation:**
- `scripts/aggregate_benchmark.py` produces `benchmark.json` and `benchmark.md`
- Compares `with_skill` vs `without_skill` (or old vs new skill)
- Statistics: mean, stddev, min, max for pass_rate, time_seconds, tokens
- Delta calculation between configurations

**3. Qualitative human review:**
- `eval-viewer/generate_review.py` generates an HTML viewer
- User reviews outputs side-by-side, leaves feedback per test case
- Feedback collected in `feedback.json`

**4. Blind comparison (optional):**
- `agents/comparator.md` — blind A/B comparison
- Rubric: content (correctness, completeness, accuracy) and structure (organization, formatting, usability), each scored 1-5
- Overall score: 1-10

**5. Post-hoc analysis:**
- `agents/analyzer.md` — surfaces patterns in benchmark data
- Identifies non-discriminating assertions, high-variance evals, resource tradeoffs

**Evidence:**
```json
// references/schemas.md — grading.json structure
{
  "expectations": [
    { "text": "...", "passed": true, "evidence": "..." }
  ],
  "summary": { "passed": 2, "failed": 1, "total": 3, "pass_rate": 0.67 }
}
```

**Dependencies:** The eval loop requires subagents (Agent tool) for parallel execution. In Cowork/Claude.ai, some features are degraded (see SKILL.md sections on Cowork and Claude.ai).

**Implicit contracts:**
- `grading.json` must use fields `text`, `passed`, `evidence` (not `name`/`met`/`details`) — the viewer depends on exact field names.
- `benchmark.json` must use `configuration` (not `config`), and nest `pass_rate` under `result` — the viewer depends on exact structure.

---

## Q8: When a skill covers both interactive and CI/CD automation contexts, how do existing skills structure conditional guidance?

**Answer:** The skill-creator SKILL.md is the primary example of multi-context skill structure. It uses separate top-level sections with explicit headers:

```markdown
## Claude.ai-specific instructions     (line 420)
## Cowork-Specific Instructions         (line 445)
```

These sections override or modify the main workflow for each context. The pattern is:
1. Main body describes the default (Claude Code CLI) workflow
2. Named sections at the end describe what changes per context
3. Each context section lists what to skip, what to adapt, and what works differently

The skill-creator SKILL.md also handles the `present_files` tool availability conditionally (line 409):
```markdown
### Package and Present (only if `present_files` tool is available)
Check whether you have access to the `present_files` tool. If you don't, skip this step.
```

No other skill in this project differentiates between interactive and automated contexts. All qrspi skills are single-context (Claude Code CLI with subagents).

**Evidence:** Skill-creator SKILL.md lines 420-456 contain two complete context-override sections, each listing which parts of the main workflow to skip, adapt, or replace.

**Dependencies:** Context detection relies on tool availability checks and environmental signals (display availability, subagent support), not explicit configuration.

**Implicit contracts:** The default path is always defined first. Context-specific sections only describe deltas from the default.

---

## Q9: How do existing skills handle escalation paths (simple to complex patterns)? Is there a convention for progressive disclosure of advanced topics?

**Answer:** The skill-creator SKILL.md documents the progressive disclosure pattern explicitly (lines 87-93):

```markdown
Skills use a three-level loading system:
1. **Metadata** (name + description) - Always in context (~100 words)
2. **SKILL.md body** - In context whenever skill triggers (<500 lines ideal)
3. **Bundled resources** - As needed (unlimited, scripts can execute without loading)
```

For within-SKILL.md escalation, the skill-creator uses a sequential disclosure pattern:
1. Core loop (lines 10-21) — overview of the full process
2. Detailed sections for each step — progressive drill-down
3. "Advanced: Blind comparison" (line 325) — explicitly labeled optional/advanced
4. "Description Optimization" (line 333) — separate advanced topic

The `references/` directory is the primary mechanism for deferring complex content. The skill-creator itself defers JSON schemas to `references/schemas.md` and subagent prompts to `agents/`.

The plugin-dev `skill-development` SKILL.md codifies this (lines 79-85):
```markdown
1. **Metadata (name + description)** - Always in context (~100 words)
2. **SKILL.md body** - When skill triggers (<5k words)
3. **Bundled resources** - As needed by Claude (Unlimited*)
```

And recommends (lines 190-196):
```markdown
**Keep SKILL.md lean:** Target 1,500-2,000 words for the body. Move detailed content to references/:
- Detailed patterns → `references/patterns.md`
- Advanced techniques → `references/advanced.md`
- Migration guides → `references/migration.md`
```

In this project, `qrspi-work/SKILL.md` uses a state-machine pattern as an escalation structure — simple dispatch table at the top (line 23-30), with detailed state-specific sections below.

**Evidence:** The skill-creator's "Domain organization" example (line 100-109) shows how variant-specific content is deferred:
```
cloud-deploy/
├── SKILL.md (workflow + selection)
└── references/
    ├── aws.md
    ├── gcp.md
    └── azure.md
```

**Implicit contracts:** SKILL.md body should contain core workflow and selection logic. Reference files contain the detailed per-variant or advanced content. SKILL.md must explicitly reference these files with guidance on when to read them.

---

## Q10: What happens when the skill-creator generates a skill that exceeds the line/token budget — does it truncate, error, or restructure content into reference files automatically?

**Answer:** The skill-creator does NOT automatically detect or handle oversized SKILL.md content. There is no truncation, error, or automatic restructuring mechanism.

The only automated size enforcement in the skill-creator is for the **description** field (not the body). In `improve_description.py` (lines 163-176), if a generated description exceeds 1024 characters, it makes a follow-up call to Claude to shorten it:

```python
# improve_description.py:163-176
if len(description) > 1024:
    shorten_prompt = (
        f"{prompt}\n\n"
        f"---\n\n"
        f"A previous attempt produced this description, which at "
        f"{len(description)} characters is over the 1024-character hard limit:\n\n"
        ...
    )
    shorten_text = _call_claude(shorten_prompt, model)
```

For the SKILL.md body, the skill-creator relies entirely on the instruction at line 96-98:
```markdown
- Keep SKILL.md under 500 lines; if you're approaching this limit, add an additional
  layer of hierarchy along with clear pointers about where the model using the skill
  should go next to follow up.
```

This is guidance to Claude during authoring, not a programmatic check.

**Evidence:** `quick_validate.py` validates only frontmatter. There is no call to validate body size anywhere in the codebase. The skill-creator's own SKILL.md is 485 lines — nearly at the 500-line guidance limit.

**Dependencies:** None — body size management is entirely advisory.

**Implicit contracts:** If a skill exceeds the budget, the human operator or the iterating Claude instance must notice during review and manually restructure content into `references/` files.

---

## Q11: How do existing skills encode opinionated defaults that vary by environment?

**Answer:** No existing skill in this project encodes environment-conditional defaults (e.g., "manual sync for prod, auto sync for dev"). The qrspi skills are environment-agnostic — they operate identically regardless of deployment context.

The skill-creator SKILL.md's multi-context sections (Claude.ai, Cowork) are the closest analog, but those are tool-availability conditions, not deployment-environment conditions.

The skill-creator's writing guidance at line 139 is relevant:
```markdown
### Writing Style
Try to explain to the model why things are important in lieu of heavy-handed musty
MUSTs. Use theory of mind and try to make the skill general and not super-narrow to
specific examples.
```

This suggests the convention is to explain the reasoning behind recommendations rather than encoding rigid environment-specific rules, allowing Claude to apply judgment per situation.

**Evidence:** Searched all SKILL.md files in the project for patterns like "prod", "production", "staging", "dev", "environment" — no environment-conditional guidance found.

**Dependencies:** N/A

**Implicit contracts:** The skill-creator philosophy favors explaining "why" over prescriptive "do X in environment Y" rules, trusting Claude's judgment to apply appropriately.

---

## Q12: What eval cases exist for the skill-creator skill, and what format do eval inputs/expected outputs follow?

**Answer:** Two eval systems exist in this project, serving different purposes:

**1. Project eval suite (`evals/suite.json`):**
- Tests the QRSPI workflow skills (not the skill-creator itself)
- 15 cases across all QRSPI phases: questions (3), research (2), design (3), structure (2), plan (1), worktree (1), implement (2), PR (1)
- Each case has: `id`, `name`, `phase`, `prompt`, `context` (files, conversation_history), `assertions` (programmatic + llm_judge), `tags`, `difficulty`, `split` (train/test)
- Train/test split: 65%/35% with seed 42
- Assertion types: `programmatic` (regex-based checks), `llm_judge` (subjective quality criteria), `script` (external script execution)
- Grading: `scripts/grade.py` runs programmatic checks; LLM judge is stubbed (`"LLM judge not yet integrated"`)

**2. Graphite skill evals (`evals/graphite-evals.json`):**
- 5 test cases for the `graphite` (using-graphite-cli) skill
- Format follows the skill-creator's `evals/evals.json` schema: `skill_name`, `evals[].id`, `evals[].prompt`, `evals[].expected_output`, `evals[].files`, `evals[].assertions`
- Assertion types: `command_check`, `flag_check`, `content_check`, `workflow_check`, `safety_check`

**3. Skill-creator's own eval format (`references/schemas.md`):**
```json
{
  "skill_name": "example-skill",
  "evals": [
    {
      "id": 1,
      "prompt": "User's example prompt",
      "expected_output": "Description of expected result",
      "files": ["evals/files/sample1.pdf"],
      "expectations": ["The output includes X", "The skill used script Y"]
    }
  ]
}
```

**Evidence:**
```json
// evals/suite.json:1-10
{
  "name": "qrspi-agent-evals",
  "version": "0.1.0",
  "description": "Eval suite for QRSPI workflow agent prompts",
  "split": { "train_ratio": 0.65, "test_ratio": 0.35, "seed": 42 },
  "defaults": { "trials_per_case": 3, "timeout_ms": 120000, "max_tokens": 128000 }
}
```

**Dependencies:** `scripts/run_eval.py` (project) is a stub — `execute_single()` has placeholder comments for agent runtime integration. `scripts/grade.py` has working programmatic checks but stubbed LLM judge.

**Implicit contracts:** The project uses two different eval schemas — the skill-creator's `evals.json` format (for per-skill evals) and the project's `suite.json` format (for QRSPI workflow evals). These are incompatible formats.

---

## Q13: How are skills tested for correct triggering — is there an eval or test harness that verifies a skill activates on expected user prompts and does not activate on unrelated prompts?

**Answer:** Yes. The skill-creator includes a complete trigger evaluation system.

**`scripts/run_eval.py`** (skill-creator, not the project's `scripts/run_eval.py`):
- Tests whether a skill's description causes Claude to invoke the skill for given queries
- Creates a temporary command file in `.claude/commands/` with the skill's description
- Runs `claude -p <query> --output-format stream-json --verbose --include-partial-messages`
- Detects triggering by monitoring stream events for `content_block_start` with tool_use of type `Skill` or `Read` targeting the skill name
- Supports parallel execution via `ProcessPoolExecutor`
- Configurable: `runs_per_query` (default 3), `trigger_threshold` (default 0.5), `timeout` (default 30s)

**`scripts/run_loop.py`** (skill-creator):
- Wraps `run_eval.py` + `improve_description.py` in an optimization loop
- Splits eval set 60% train / 40% test (stratified by `should_trigger`)
- Runs up to `max_iterations` (default 5) improvement cycles
- Selects best description by test score (not train) to prevent overfitting
- Generates live HTML report during optimization

**Eval set format:**
```json
[
  {"query": "the user prompt", "should_trigger": true},
  {"query": "another prompt", "should_trigger": false}
]
```

**Evidence:**
```python
# skill-creator/scripts/run_eval.py:36-42
def run_single_query(
    query: str,
    skill_name: str,
    skill_description: str,
    timeout: int,
    project_root: str,
    model: str | None = None,
) -> bool:
```

```python
# skill-creator/scripts/run_loop.py:24-44
def split_eval_set(eval_set: list[dict], holdout: float, seed: int = 42) -> tuple[list[dict], list[dict]]:
    """Split eval set into train and test sets, stratified by should_trigger."""
```

**Dependencies:** Requires `claude` CLI tool (`claude -p`) — only available in Claude Code, not Claude.ai. Removes `CLAUDECODE` env var to allow nesting.

**Implicit contracts:** Trigger testing is per-skill (one skill at a time). There is no cross-skill collision testing — you cannot test whether a query triggers skill A instead of skill B.

---

## Q14: Does the project have any mechanism for tracking skill invocation frequency, failure modes, or user overrides after deployment?

**Answer:** NOT FOUND. No observability, logging, analytics, or telemetry infrastructure for skill invocation exists in this project.

Search queries attempted:
- `grep -r "observability\|logging\|analytics\|invocation.*frequency\|telemetry\|tracking" /workspaces/qrspi/.claude/skills/` — no results
- `find /workspaces/qrspi -name "*.py" -exec grep -l "log\|metric\|telemetry" {} \;` — only `scripts/grade.py` (eval metrics, not runtime observability)
- Reviewed all files in `scripts/` — `run_eval.py`, `grade.py`, `report.py`, `revise.py`, `diagnose.py`, `check_scope.py` — all are eval-time tools, not runtime monitoring

The skill-creator captures timing/token data during eval runs (`timing.json`) but this is eval-time instrumentation, not production observability.

No hooks, middleware, or logging configuration exists for tracking skill invocations in production use.

**Dependencies:** N/A

**Implicit contracts:** Skills are fire-and-forget from an observability perspective. Quality is measured pre-deployment via evals, not post-deployment via monitoring.

---

## Discovered Patterns

1. **Dual skill-authoring conventions:** The skill-creator and the plugin-dev `skill-development` skill provide overlapping but inconsistent guidance. Skill-creator says "pushy" imperative descriptions; plugin-dev says third-person with quoted trigger phrases. Both are available in this environment.

2. **Frontmatter schema tension:** The project's own skills use `command` and `argument-hint` frontmatter fields (all 10 skills), but `quick_validate.py` does not list these as allowed properties. Running `quick_validate.py` on any qrspi skill would fail validation. The `allowed-tools` field IS in the allowed set.

3. **Eval schema divergence:** The project has two incompatible eval formats — the skill-creator's `evals.json` (simple prompt + expectations) and the project's `suite.json` (phase-tagged, split-aware, multi-assertion-type). These serve different purposes but share no common structure.

4. **Stub infrastructure:** The project's `scripts/run_eval.py` has `execute_single()` as a stub with placeholder comments — it does not actually run agents. The grading pipeline's LLM judge is also stubbed. The eval infrastructure is designed but not yet functional for end-to-end execution.

5. **Progressive disclosure is guidance-only:** No automated enforcement of SKILL.md size budgets exists. The 500-line limit, 5k-word suggestion, and reference-file restructuring are all advisory instructions to Claude during authoring.

6. **Context firewalling pattern:** The qrspi skills use strict input scoping — each phase skill specifies exactly which files to read and which to exclude (e.g., research cannot see the ticket). This is enforced by instructions, not by tool permissions.

7. **Single reference file pattern:** Only one skill (`qrspi-work`) uses `references/`. All other skills are self-contained in SKILL.md. The pattern exists but is rarely used in this project.

---

## Inconsistencies

1. **`command` and `argument-hint` frontmatter fields are used by all 10 project skills but are NOT in `quick_validate.py`'s `ALLOWED_PROPERTIES` set.** Running the validator on any project skill would produce: `"Unexpected key(s) in SKILL.md frontmatter: argument-hint, command"`. This suggests the project's skills predate or diverge from the skill-creator's validation schema.

2. **Description style conflict:** The skill-creator SKILL.md (line 67) recommends "pushy" descriptions with "Make sure to use this skill whenever..." language. The plugin-dev `skill-development` SKILL.md (line 164) recommends third-person: "This skill should be used when the user asks to..." The project's existing skills follow neither convention consistently — most use short functional descriptions without trigger phrases.

3. **Body size guidance conflict:** Skill-creator says "<500 lines ideal" (SKILL.md line 91). Plugin-dev says "1,500-2,000 words" target, "<5k words" max, and "<3,000 words without references/" (skill-development SKILL.md lines 191, 329). The skill-creator's own SKILL.md is 485 lines / 5,138 words — it passes its own line limit but exceeds the plugin-dev word limit.

4. **Eval format incompatibility:** `evals/suite.json` uses `assertions[].type` with values `programmatic`, `llm_judge`, `script`. `evals/graphite-evals.json` uses `assertions[].type` with values `command_check`, `flag_check`, `content_check`, `workflow_check`, `safety_check`. The skill-creator's schema uses `expectations` (string array) instead of typed assertions. No shared grading pipeline handles all three formats.

5. **`allowed-tools` is in the validator's allowed properties but no validation logic exists for it.** The field is accepted but its value is never checked — it could contain arbitrary content and `quick_validate.py` would pass it.
