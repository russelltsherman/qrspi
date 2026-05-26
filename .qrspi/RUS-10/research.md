# Research — Codebase Map
**Questions source:** questions.md @ 2026-05-26T00:00:00Z
**Generated:** 2026-05-26T12:00:00Z
**Status:** draft

## Q1: How does the existing skill-creator skill generate SKILL.md files, and what template or prompt structure does it use to produce the frontmatter and body sections?

**Answer:** The skill-creator skill (`/home/vscode/.agents/skills/skill-creator/SKILL.md`, 486 lines) does not use a static template file. Instead, it follows a conversational interview-then-write process:

1. **Capture Intent** — asks the user 4 questions (what, when, output format, test cases).
2. **Interview and Research** — proactively asks about edge cases, dependencies, formats.
3. **Write the SKILL.md** — fills in frontmatter fields and body from interview data.

The skill defines the frontmatter components inline:

```markdown
- **name**: Skill identifier
- **description**: When to trigger, what it does. This is the primary triggering mechanism...
- **compatibility**: Required tools, dependencies (optional, rarely needed)
- **the rest of the skill :)**
```

The body structure guidance is embedded as prose ("Anatomy of a Skill") rather than a formal template.

**Evidence:**
```
# skill-creator/SKILL.md:66-69
- **name**: Skill identifier
- **description**: When to trigger, what it does. This is the primary triggering mechanism - include both what the skill does AND specific contexts for when to use it.
- **compatibility**: Required tools, dependencies (optional, rarely needed)
- **the rest of the skill :)**
```

**Dependencies:** The skill-creator depends on several sub-scripts: `scripts/run_eval.py`, `scripts/run_loop.py`, `scripts/improve_description.py`, `scripts/quick_validate.py`, `scripts/package_skill.py`, `scripts/aggregate_benchmark.py`, `scripts/generate_report.py`. It also references `agents/grader.md`, `agents/comparator.md`, `agents/analyzer.md`, and `references/schemas.md`.

**Implicit contracts:**
- The skill-creator does not enforce a fixed template — it produces the skill through conversation and iteration.
- It explicitly recommends "pushy" descriptions to combat under-triggering.
- Token/line limits are soft guidance ("under 500 lines ideal"), not hard-enforced by the generator itself.

---

## Q2: What is the agentskills.io standard directory structure, and how do existing skills in this project organize their `SKILL.md`, `references/`, `scripts/`, and `assets/` directories?

**Answer:** The skill-creator defines the canonical directory structure:

```
skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter (name, description required)
│   └── Markdown instructions
└── Bundled Resources (optional)
    ├── scripts/    - Executable code for deterministic/repetitive tasks
    ├── references/ - Docs loaded into context as needed
    └���─ assets/     - Files used in output (templates, icons, fonts)
```

In this project (`/workspaces/qrspi/.worktrees/RUS-10/.claude/skills/`), existing skills are minimal:

| Skill | Structure |
|---|---|
| qrspi-questions | `SKILL.md` only (46 lines) |
| qrspi-research | `SKILL.md` only (57 lines) |
| qrspi-design | `SKILL.md` only (43 lines) |
| qrspi-structure | `SKILL.md` only (41 lines) |
| qrspi-plan | `SKILL.md` only (36 lines) |
| qrspi-worktree | `SKILL.md` only (33 lines) |
| qrspi-implement | `SKILL.md` only (52 lines) |
| qrspi-pr | `SKILL.md` only (43 lines) |
| qrspi-ticket | `SKILL.md` only (75 lines) |
| qrspi-work | `SKILL.md` (500 lines) + `references/review-cascade.md` |

Only `qrspi-work` uses a `references/` directory. No project skill uses `scripts/` or `assets/`.

At the user level (`/home/vscode/.agents/skills/`), skill-creator itself is the richest example:
```
skill-creator/
├── SKILL.md
├── LICENSE.txt
├── eval-viewer/generate_review.py, viewer.html
├── references/schemas.md
├── agents/grader.md, comparator.md, analyzer.md
├── scripts/run_eval.py, run_loop.py, improve_description.py, quick_validate.py, ...
└── assets/eval_review.html
```

**Evidence:** File listing from `find /workspaces/qrspi/.worktrees/RUS-10/.claude/skills -type f` and `find /home/vscode/.agents/skills/skill-creator -type f`.

**Dependencies:** Skills are discovered by Claude from the `.claude/skills/` directory. The skill-creator's progressive disclosure model (metadata -> body -> resources) determines what gets loaded into context.

**Implicit contracts:**
- `SKILL.md` is the only required file; everything else is optional.
- Resources are loaded on-demand ("Read these files selectively based on the task at hand").
- The project's existing skills are self-contained single files (no bundled resources needed for simple workflow-phase skills).

---

## Q3: What frontmatter fields are required by the agentskills.io standard for a valid SKILL.md, and what format constraints (YAML, TOML, etc.) apply?

**Answer:** The validation script `quick_validate.py` defines the authoritative schema:

**Required fields:** `name`, `description`

**Allowed fields:** `name`, `description`, `license`, `allowed-tools`, `metadata`, `compatibility`

**Format:** YAML frontmatter between `---` delimiters.

**Constraints:**
- `name`: string, kebab-case (`[a-z0-9-]+`), no leading/trailing hyphens, no double hyphens, max 64 characters.
- `description`: string, max 1024 characters, no angle brackets (`<` or `>`).
- `compatibility`: string, max 500 characters (optional).
- Unexpected keys cause validation failure.

**Evidence:**
```python
# /home/vscode/.agents/skills/skill-creator/scripts/quick_validate.py:42-43
ALLOWED_PROPERTIES = {'name', 'description', 'license', 'allowed-tools', 'metadata', 'compatibility'}
```
```python
# quick_validate.py:64-66
if not re.match(r'^[a-z0-9-]+$', name):
    return False, f"Name '{name}' should be kebab-case (lowercase letters, digits, and hyphens only)"
```
```python
# quick_validate.py:80-84
if '<' in description or '>' in description:
    return False, "Description cannot contain angle brackets (< or >)"
if len(description) > 1024:
    return False, f"Description is too long ({len(description)} characters). Maximum is 1024 characters."
```

**Additional fields observed in this project's skills:** The project skills use `command` and `argument-hint` in frontmatter (e.g., `command: /qrspi-questions`, `argument-hint: <ticket-id>`). These are NOT in the `quick_validate.py` allowed list, which would cause validation failure if run against them.

**Implicit contracts:**
- The `quick_validate.py` script represents the formal spec; the project skills use additional fields (`command`, `argument-hint`) that extend the standard.
- The `description` field has a "no angle brackets" constraint, which conflicts with the description text used in the using-graphite-cli skill (which uses angle brackets like `<ticket-id>`). However, `quick_validate.py` is from the skill-creator plugin; the project skills may not be validated by it.

---

## Q4: What CLI subcommands and flags does `cmux` expose that the skill must document, and is there a canonical source (man page, `--help` output, or docs) that enumerates them?

**Answer:** NOT FOUND in the codebase.

**Search queries attempted:**
- `grep -r "cmux" /workspaces/qrspi/.worktrees/RUS-10` — only found `questions.md` itself
- `which cmux` / `command -v cmux` — not installed in this environment
- `find /workspaces/qrspi/.worktrees/RUS-10 -name "*cmux*"` — no results
- No man page, --help output, README, or external documentation for `cmux` exists in the codebase

There is no local reference material for `cmux`. The skill must document it from external sources (not present in the worktree).

---

## Q5: How does the skill-creator skill's eval loop validate that a generated skill meets token/line limits (e.g., "under 500 lines / 5000 tokens"), and what tooling measures token count?

**Answer:** The skill-creator does NOT enforce hard token/line limits programmatically. The guidance is soft:

From skill-creator SKILL.md line 96-97:
```
- Keep SKILL.md under 500 lines; if you're approaching this limit, add an additional
  layer of hierarchy along with clear pointers...
```

The `quick_validate.py` script validates only frontmatter fields (name, description length). It does NOT check body length, line count, or token count.

The project's own eval suite (`evals/suite.json`) has a programmatic check `line_count` that can verify max lines in output, but this is for generated artifacts (questions, design docs), not for skill body validation:

```python
# scripts/grade.py:35-38
def line_count(filename: str, max_lines: int, result: dict) -> tuple[bool, str]:
    """Check that output is within line limit."""
    output = result.get("output", "")
    count = len(output.splitlines())
```

No token-counting tooling exists in either the skill-creator or the project's eval harness. The 500-line limit is communicated as guidance to the model writing the skill, not enforced by tooling.

**Evidence:** Full read of `quick_validate.py` (validates frontmatter only). Full read of skill-creator SKILL.md (soft "500 lines ideal" language). No `wc`, `tiktoken`, or token-counting utility found.

**Dependencies:** None — no automated enforcement exists.

**Implicit contracts:** The 500-line limit is a convention enforced by the skill-creator's instructions to itself ("if you're approaching this limit, add hierarchy"). The model is expected to self-regulate.

---

## Q6: How do existing skills in this project define their trigger conditions (the description field that tells Claude when to auto-invoke), and what patterns produce reliable triggering?

**Answer:** The `description` field in YAML frontmatter is the sole triggering mechanism. Existing patterns:

**Project skills (qrspi-*)** — short, role-based descriptions:
```yaml
# qrspi-questions:
description: Generate 8-15 targeted technical questions from a feature ticket. Use when starting a new QRSPI feature workflow or when the user says "questions for" a ticket.

# qrspi-work:
description: "Single entry point for autonomous QRSPI feature development. Use when the user asks to 'work on' a ticket (e.g., 'work on RUS-42'). Reads the ticket's Linear status, determines the current phase, and executes the appropriate action — planning, implementation, or review response — without manual phase-by-phase invocation. Trigger on any variant of: 'work on <ticket-id>', 'continue <ticket-id>', 'pick up <ticket-id>', or any reference to progressing a QRSPI ticket through its lifecycle."
```

**User-level skills** — longer, "pushy" descriptions:
```yaml
# using-graphite-cli:
description: "Use for ANY request involving version control, commits, branches, diffs, or pull requests — this is the mandatory, exclusive way to perform all such operations. Trigger whenever the user wants to: see what changed or review a diff, commit or amend their work, push code or submit/update PRs (including drafts)... Even simple read-only checks like viewing a diff or status must go through this skill. Never run raw git or gt commands outside it."
```

**Patterns that produce reliable triggering (per skill-creator guidance):**
1. Include BOTH what the skill does AND specific contexts/phrases that trigger it.
2. Be "pushy" — explicitly state when to trigger, enumerate user phrases.
3. Include negative signals ("Do NOT use for X") to avoid false positives.
4. Use concrete examples of user inputs (e.g., "'work on RUS-42'").

**Evidence:** Frontmatter extracted from all 10 project skills and 3 user-level skills. Skill-creator SKILL.md line 67: "please make the skill descriptions a little bit 'pushy'."

**Implicit contracts:** The description is the ONLY metadata that enters the "available skills" context that Claude uses to decide triggering. Length is capped at 1024 characters per `quick_validate.py`.

---

## Q7: Where does this project store skill artifacts during creation — are they written directly to `.claude/skills/<name>/` or staged in a temporary location before approval?

**Answer:** Skills are written directly to `.claude/skills/<name>/SKILL.md`. There is no staging area or temporary directory in the project.

The skill-creator's instructions say:
```
Write the SKILL.md
```
And for running test cases, it uses a sibling workspace directory:
```
Put results in `<skill-name>-workspace/` as a sibling to the skill directory.
```

But the skill file itself is written directly. This project has no evidence of a staging workflow — all 10 skills under `.claude/skills/` exist directly in their final locations.

The skill-creator also mentions for Claude.ai: "Copy to a writeable location before editing... stage in /tmp/ first" — but this is for permissions issues in read-only plugin paths, not a general staging pattern.

**Evidence:** `find /workspaces/qrspi/.worktrees/RUS-10/.claude/skills -type f` shows all skills in their final `<name>/SKILL.md` paths. No `/tmp/`, `staging/`, or `draft/` directories exist.

**Implicit contracts:** Skills are written in-place. The iteration loop (draft -> test -> improve) modifies the same file repeatedly rather than versioning drafts.

---

## Q8: How does the skill-creator skill handle `references/` subdirectory content — is reference material generated inline, split from the main SKILL.md, or provided separately?

**Answer:** The skill-creator's guidance for references is:

From SKILL.md lines 93-108:
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

In practice, the `qrspi-work` skill demonstrates the pattern: its `references/review-cascade.md` (68 lines) is a standalone document referenced by a pointer in the main SKILL.md:
```markdown
# qrspi-work/SKILL.md:175
c. Read `references/review-cascade.md` for cascade logic.
```

The skill-creator does not auto-generate reference files. It leaves it to the model to decide when content should be split out. The trigger is approaching the 500-line SKILL.md limit or domain-specific content that only applies conditionally.

**Evidence:** `qrspi-work/references/review-cascade.md` exists (68 lines). Skill-creator SKILL.md line 95-97 guidance. Only 1 of 10 project skills has a references directory.

**Implicit contracts:**
- Reference files are loaded on-demand by the skill's instructions (not automatically).
- SKILL.md must contain explicit "Read X when Y" pointers.
- References are for content that only some invocations need.

---

## Q9: What happens when a skill's SKILL.md body exceeds the 500-line or 5000-token limit — does the skill-creator skill enforce this with a hard error, a warning, or does it silently truncate?

**Answer:** No enforcement mechanism exists. The skill-creator uses soft guidance only:

```markdown
# skill-creator/SKILL.md:96-97
- Keep SKILL.md under 500 lines; if you're approaching this limit, add an additional
  layer of hierarchy along with clear pointers about where the model using the skill
  should go next to follow up.
```

The `quick_validate.py` script does NOT check body length — only frontmatter field validity. There is no truncation, no warning, and no hard error for exceeding 500 lines.

In this project, `qrspi-work/SKILL.md` is exactly 500 lines — it sits right at the recommended limit. This appears to be the result of manual constraint by the author, not automated enforcement.

**Evidence:** `wc -l` on all project skills shows `qrspi-work` at 500 lines. `quick_validate.py` source has no body-length check. No other validation scripts check line or token counts.

**Dependencies:** None — purely convention.

**Implicit contracts:** The 500-line limit is a "should" not a "must." The skill-creator relies on the model self-regulating during the interview/write loop.

---

## Q10: How does the project handle platform-specific skills (macOS-only in this case) — is there a convention for documenting platform constraints or conditionally disabling the skill on unsupported systems?

**Answer:** NOT FOUND — no platform-specific skill conventions exist in this codebase.

**Search results:**
- No skill in `.claude/skills/` or `/home/vscode/.agents/skills/` uses platform-conditional logic.
- The `compatibility` field exists in `quick_validate.py`'s allowed properties but is optional and unused by any skill in this project.
- The `using-graphite-cli` skill does not check for `gt` availability before running commands.
- No conditional `if [[ "$(uname)" == "Darwin" ]]` patterns found in any skill.
- The skill-creator SKILL.md mentions `compatibility` as an optional frontmatter field: "Required tools, dependencies (optional, rarely needed)."

The closest available mechanism is the `compatibility` frontmatter field, but its semantics are undocumented — no existing skill demonstrates its use.

**Evidence:** `grep -r "Darwin\|macos\|macOS\|platform\|uname" /home/vscode/.agents/skills/` yields no results. `quick_validate.py` line 42 lists `compatibility` as allowed but validates only that it's a string under 500 chars.

**Implicit contracts:** Platform constraints would need to be documented in the skill's description/body as prose guidance (e.g., "This skill requires macOS"), since no automated platform-gating mechanism exists.

---

## Q11: If a skill references external CLI tools that may not be installed (e.g., `cmux`, `brew`), how do existing skills handle the absence of those tools at invocation time?

**Answer:** Existing skills do NOT pre-check for tool availability. They assume the tool is present and let execution fail naturally.

The `using-graphite-cli` skill (387 lines) is the primary example of a skill depending on an external CLI (`gt`). It:
1. Does NOT include a "check if gt is installed" step.
2. Does NOT include a `command -v gt` guard.
3. Simply provides instructions for using `gt` and relies on the error surfacing if it's missing.

The `writing-bash-scripts` skill references ShellCheck as a linting tool but does not check for its installation.

The project's `qrspi-work` skill has a HARD STOP rule for infrastructure errors that would apply if a tool is missing:
```markdown
# qrspi-work/SKILL.md:479-483
When ANY operation fails due to permissions, authentication, configuration, or tooling errors
(e.g., EACCES, permission denied, auth token expired, config file inaccessible, tool not found):
1. STOP. Do not execute another command.
2. Print the exact error verbatim
3. Exit the skill.
```

This is the project's convention: don't pre-check, but stop immediately on failure and surface the error.

**Evidence:**
```markdown
# using-graphite-cli/SKILL.md:8-10
All version control in this environment uses the Graphite CLI (`gt`), which manages
stacked pull requests on top of Git. Every git or gt operation — including read-only
ones like status, diff, and log — must go through the patterns in this skill.
```
No `which gt` or `command -v gt` guard anywhere in the skill.

**Implicit contracts:**
- Skills assume their dependencies are installed in the environment.
- Failure is handled by the error-surfacing convention (stop and report), not by graceful degradation.
- The `compatibility` frontmatter field could theoretically declare dependencies, but is unused.

---

## Q12: What eval harness exists for testing generated skills, and how are skill evals structured (input scenarios, expected outputs, pass/fail criteria)?

**Answer:** Two eval systems exist:

### 1. Project eval harness (`evals/` and `scripts/`)

Located at `/workspaces/qrspi/.worktrees/RUS-10/evals/suite.json` and `scripts/`.

**Structure:**
```json
{
  "name": "qrspi-agent-evals",
  "split": { "train_ratio": 0.65, "test_ratio": 0.35, "seed": 42 },
  "defaults": { "trials_per_case": 3, "timeout_ms": 120000 },
  "cases": [
    {
      "id": "case_001",
      "phase": "questions",
      "prompt": "Generate questions for the following ticket.",
      "context": { "files": ["fixtures/ticket_rest_endpoint.md"] },
      "assertions": [
        { "type": "programmatic", "check": "output_file_exists('questions.md')", "weight": 1.0 },
        { "type": "llm_judge", "criteria": "Questions are specific...", "weight": 2.0 }
      ],
      "tags": ["questions", "happy-path"],
      "difficulty": "easy",
      "split": "train"
    }
  ]
}
```

**Pipeline:** `run_eval.py` (execute) -> `grade.py` (score) -> `diagnose.py` (categorize failures) -> `revise.py` (propose edits) -> `report.py` (track iterations)

**Note:** `run_eval.py` has a stub execution — the actual agent invocation is a placeholder comment: "Replace this block with actual agent invocation."

### 2. Skill-creator eval system (global)

The skill-creator uses a separate, more mature eval loop:
- Test prompts saved to `evals/evals.json` with the schema from `references/schemas.md`.
- Runs spawned via subagents (with-skill and baseline).
- Grading via `agents/grader.md`.
- Results viewed via `eval-viewer/generate_review.py`.
- Iteration tracked in workspace directories.

Additionally, `evals/graphite-evals.json` shows a lighter-weight eval format for the graphite skill with `assertions` using informal types like `command_check`, `flag_check`, `safety_check`, `workflow_check`.

**Evidence:** `evals/suite.json` (full), `scripts/grade.py` (full), `evals/graphite-evals.json` (full).

**Implicit contracts:** The project eval harness is a framework (scripts exist) but execution is not yet wired to a live agent runtime.

---

## Q13: How does the skill-creator skill's eval loop work end-to-end — what does it measure, how many iterations does it run, and what constitutes a passing result?

**Answer:** The skill-creator has two eval subsystems:

### A. Test case eval loop (qualitative + quantitative)

1. **Spawn runs** — for each test prompt, launch a with-skill subagent and a baseline subagent in parallel.
2. **Grade** — run `agents/grader.md` against outputs, checking `expectations` (assertions).
3. **Aggregate** — run `scripts/aggregate_benchmark.py` to produce `benchmark.json` with pass_rate, time, tokens per configuration (mean +/- stddev).
4. **Analyze** — surface patterns (non-discriminating assertions, high variance, time tradeoffs).
5. **Present** — launch `eval-viewer/generate_review.py` for human review.
6. **Iterate** — read `feedback.json`, improve skill, rerun into `iteration-<N+1>/`.

**Pass criteria:** The user says they're happy OR feedback is all empty. No numeric threshold is hard-coded.

**Iterations:** No fixed limit on the test case loop — continues "until the user says they're happy."

### B. Description optimization loop (`scripts/run_loop.py`)

```python
# run_loop.py:47-60
def run_loop(
    eval_set: list[dict],
    skill_path: Path,
    ...
    max_iterations: int,  # default 5
    runs_per_query: int,
    trigger_threshold: float,
    holdout: float,
    ...
```

- Splits eval queries into 60% train / 40% test.
- Evaluates current description (3 runs per query for reliability).
- Calls Claude to propose improvements based on failures.
- Re-evaluates each iteration.
- **Max iterations:** 5 (configurable).
- **Selection criterion:** best_description selected by test score (not train) to avoid overfitting.
- Uses `claude -p` subprocess with `--output-format stream-json` to detect triggering.

**Evidence:** `scripts/run_loop.py:24-44` (split logic), `scripts/run_eval.py:36-80` (single query execution), skill-creator SKILL.md lines 377-394 (description optimization section).

**Implicit contracts:** The test case loop is human-gated (no auto-pass threshold). The description loop is auto-scored but capped at 5 iterations.

---

## Q14: After a skill is created, what feedback or logs does the skill-creator skill produce to confirm successful generation, and how can the user verify the skill is correctly registered and triggerable?

**Answer:** The skill-creator produces:

1. **The skill file itself** — written to `<skill-name>/SKILL.md` (and optionally bundled resources).
2. **Test case results** — stored in `<skill-name>-workspace/iteration-<N>/` directories with outputs, grading.json, timing.json, benchmark.json.
3. **Eval viewer** — HTML report generated by `eval-viewer/generate_review.py` showing qualitative outputs and quantitative benchmark.
4. **Packaged file** — (if `present_files` tool available) `scripts/package_skill.py` produces a `.skill` file.

**Registration mechanism:** Skills are registered by their presence in the `.claude/skills/` directory. There is no explicit registry file (no `settings.json` entry needed). Claude discovers skills by scanning this directory.

**Verification that a skill triggers correctly:** The description optimization loop (`scripts/run_loop.py`) creates a temporary command file in `.claude/commands/` and runs `claude -p` with test queries to check if the skill is triggered:

```python
# run_eval.py:53-67
clean_name = f"{skill_name}-skill-{unique_id}"
project_commands_dir = Path(project_root) / ".claude" / "commands"
command_file = project_commands_dir / f"{clean_name}.md"
...
cmd = ["claude", "-p", query, "--output-format", "stream-json", "--verbose", "--include-partial-messages"]
```

It detects triggering from stream events rather than waiting for full execution.

**Validation:** `scripts/quick_validate.py` can be run to confirm frontmatter validity:
```bash
python quick_validate.py <skill_directory>
# Output: "Skill is valid!" or error message
```

**Evidence:** `run_eval.py:36-80` (trigger detection), `quick_validate.py:12-94` (validation), skill-creator SKILL.md line 167 (workspace directory pattern).

**Implicit contracts:**
- No explicit registration step — file presence in `.claude/skills/` is sufficient.
- The `quick_validate.py` only checks frontmatter; body quality is assessed via the eval loop.
- Trigger verification requires `claude -p` CLI tool (Claude Code specific).

---

## Discovered Patterns

1. **Skills are self-contained SKILL.md files by default.** Only the most complex skill (qrspi-work, 500 lines) uses a `references/` directory. Simple phase skills are single files under 80 lines.

2. **Progressive disclosure architecture.** Three levels: (a) name+description always in context (~100 words), (b) SKILL.md body loaded on trigger (<500 lines), (c) bundled resources loaded on-demand by the skill's instructions.

3. **Frontmatter extends the standard.** Project skills use `command` and `argument-hint` fields not in the `quick_validate.py` allowed list. This suggests the project has its own skill loading system that accepts these additional fields.

4. **"Pushy" description convention.** Descriptions are written to over-trigger rather than under-trigger. They enumerate specific user phrases, use "Trigger whenever...", and include negative examples.

5. **Error surfacing over graceful degradation.** When external tools are missing, the convention is to fail fast and report verbatim errors, not to check prerequisites or provide fallback behavior.

6. **Eval harness exists but is partially stubbed.** `scripts/run_eval.py` has placeholder agent execution. The skill-creator's eval loop is fully functional but requires `claude -p` CLI and subagents. The project eval suite defines cases but cannot execute them without the agent runtime.

7. **No token counting anywhere.** Neither the project nor the skill-creator measure token counts for skill bodies. The "500 lines" guidance is the only size constraint.

8. **Dual eval format.** The project uses a formal `suite.json` format with `programmatic` and `llm_judge` assertions. The graphite skill uses an informal format with ad-hoc assertion types (`command_check`, `flag_check`, etc.).

---

## Inconsistencies

1. **Frontmatter field mismatch.** `quick_validate.py` allows exactly `{name, description, license, allowed-tools, metadata, compatibility}`. But project skills use `command` and `argument-hint`, and the using-graphite-cli skill uses `command` as well. Running `quick_validate.py` against these skills would fail with "Unexpected key(s) in SKILL.md frontmatter."

2. **Description angle bracket constraint vs. usage.** `quick_validate.py` rejects descriptions containing `<` or `>`. But the qrspi-work skill description contains `<ticket-id>`: `"'work on <ticket-id>'"`. This would fail validation.

3. **`allowed-tools` field not in skill-creator documentation.** The skill-creator's "Write the SKILL.md" section lists `name`, `description`, and `compatibility` as frontmatter fields. It does not mention `allowed-tools`, yet every project skill uses it, and `quick_validate.py` allows it.

4. **500-line guidance vs. 500-line reality.** Skill-creator says "under 500 lines ideal." The qrspi-work skill is exactly 500 lines. The skill-creator itself is 486 lines. Both are at or near the stated limit, suggesting the limit may be too low for complex orchestration skills.

5. **Eval harness disconnected from skill creation.** The project's `evals/suite.json` tests QRSPI workflow phases (questions, research, design, etc.) but has no test cases for "skill creation" itself. The skill-creator has its own separate eval system. These two systems do not interoperate.

6. **`command` field semantics.** Project skills use `command: /qrspi-questions` (with slash). The using-graphite-cli uses `command: writing-bash-scripts` style (this specific skill uses no `command` field actually — it just has name and description). The writing-bash-scripts skill uses `command: writing-bash-scripts` (no slash). The convention is inconsistent.
