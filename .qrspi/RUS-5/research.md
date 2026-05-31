# Research - Codebase Map

**Questions source:** questions.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## Q1: Where does the skill-creator skill store generated skills on disk -- under `.claude/skills/`, `.qrspi/skills/`, or another directory?
  **Target:** the skill-creator skill's output logic

**Answer:** NOT FOUND -- the question targets a resource outside the project scope. The skill-creator skill lives at `/home/vscode/.agents/skills/skill-creator/`, which is outside `REPO_ROOT` (`/workspaces/qrspi/.worktrees/RUS-5/`). Searched all `.md`, `.json`, and `.py` files under `REPO_ROOT` for "skill-creator" references -- zero matches.

The repository's own skills (the QRSPI workflow skills) are stored under `.claude/skills/<skill-name>/SKILL.md`. Each qrspi skill is a thin wrapper: the SKILL.md contains frontmatter (`name`, `description`, `command`, `argument-hint`, `allowed-tools`) and a short steps section that spawns an Agent tool call with a `subagent_type`. The actual prompt logic lives in `.claude/agents/qrspi-<phase>.md`. This is the repo's internal pattern, but it does not describe what skill-creator does.

**Dependencies:** N/A -- skill-creator is outside repo scope.
**Implicit contracts:** N/A

## Q2: How does the agentskills.io directory structure map to qrspi's existing skill layout -- are `references/`, `scripts/`, and `assets/` subdirectories under a single `writing-bash-scripts/` directory, or spread across the workspace?
  **Target:** the skill-creator skill and the `.claude/skills/` directory

**Answer:** NOT FOUND -- the question targets a resource outside the project scope. `agentskills.io` is not referenced anywhere in `REPO_ROOT`. Zero matches for "agentskills.io" across all `.md`, `.json`, and `.py` files.

The repo's skills use a flat per-skill directory with a single SKILL.md:
```
.claude/skills/
  qrspi-work/
    SKILL.md
    references/
      review-cascade.md
```

Only `qrspi-work` has a `references/` subdirectory (containing `review-cascade.md`). No skills in the repo have `scripts/` or `assets/` subdirectories. No skill references `references/`, `scripts/`, or `assets/` in its SKILL.md body.

**Dependencies:** N/A -- agentskills.io is outside repo scope.
**Implicit contracts:** N/A

## Q3: What SKILL.md frontmatter fields are required by the skill-creator skill versus optional, and does the qrspi workflow expect any additional fields beyond agentskills.io?
  **Target:** the skill-creator skill's SKILL.md specification

**Answer:** NOT FOUND -- the question targets the skill-creator skill's SKILL.md specification, which is outside `REPO_ROOT`.

However, the existing repo skills all use the same frontmatter convention (YAML between `---` delimiters at the top of SKILL.md):

```yaml
---
name: <skill-name>
description: <one-line description with trigger language>
command: /<skill-command>
argument-hint: <argument format>
allowed-tools: <tool list, with optional restrictions>
---
```

Fields observed across all 10 repo SKILL.md files:
- `name` -- present in every skill
- `description` -- present in every skill; uses "Use when..." language to trigger the skill
- `command` -- present in every skill; always starts with `/`
- `argument-hint` -- present in every skill
- `allowed-tools` -- present in every skill; some use restrictions (e.g., `Bash(pwd:*)`)

The agent definition files (`.claude/agents/qrspi-*.md`) use a different format:
```yaml
---
name: <agent-name>
description: <agent description>
model: <model name>
claude:
  tools: <tool list>
---
```

These agent files do not have `command`, `argument-hint`, or `allowed-tools` fields. They have `model` and `claude.tools` instead.

**Dependencies:** N/A -- skill-creator spec is outside repo scope.
**Implicit contracts:** N/A

## Q4: How are skill invocation triggers defined -- via the `/` slash command prefix, auto-invoke conditions in the system prompt, or both?
  **Target:** existing skills in `.claude/skills/` or `.agents/skills/`

**Answer:** The repo's QRSPI workflow skills use the `/` slash command prefix exclusively. Each SKILL.md has a `command` frontmatter field with the slash command (e.g., `command: /qrspi-research`). The system prompt in `.claude/CLAUDE.md` lists all available skills with descriptions like:

```
### Available skills (invoke with / or let Claude auto-invoke)

- `/qrspi-ticket <initial description>` -- Create a Linear issue through guided conversation
- `/qrspi-questions <ticket-id>` -- Generate technical questions from a ticket
...
```

The phrasing "invoke with / or let Claude auto-invoke" indicates both modes are supported, but the actual repo skills only define the `/` command in frontmatter. There are no auto-invoke conditions (such as `trigger` or `pattern` fields) in any of the 10 repo SKILL.md files.

The skill-creator's own trigger conventions (for auto-invoke conditions, description-based auto-triggering, etc.) are outside repo scope.

**Dependencies:** `.claude/CLAUDE.md` lists skills; `.claude/skills/<name>/SKILL.md` defines the `command` field.
**Implicit contracts:** The `description` frontmatter field contains "Use when..." language that is expected to match user utterances for auto-triggering, but this behavior is not defined within the repo itself.

## Q5: Does the skill-creator skill maintain any persistent state (e.g., a registry of all skills, version tracking, or eval history), and if so, where is it stored?
  **Answer:** NOT FOUND -- the question targets the skill-creator skill's storage backend, which is outside `REPO_ROOT`.

The repo's qrspi-work skill references `.agents/skills/skill-creator/` as a directory that exists (found via filesystem scan outside repo), but its contents are not accessible per the research firewall rules. The `skill-creator` directory contains:
- `SKILL.md` -- the skill definition
- `eval-viewer/` -- HTML/Python for viewing eval results
- `references/schemas.md` -- schema documentation
- `agents/` -- grader.md, comparator.md, analyzer.md
- `scripts/` -- run_eval.py, package_skill.py, quick_validate.py, improve_description.py, etc.
- `assets/` -- eval_review.html
- `LICENSE.txt`

None of the script filenames inside `skill-creator/` suggest a persistent registry. `package_skill.py` and `quick_validate.py` suggest packaging/validation workflow, not state management.

**Dependencies:** N/A -- skill-creator storage is outside repo scope.
**Implicit contracts:** N/A

## Q6: When a bash script skill is invoked, how should the agent distinguish between writing a new script from scratch versus editing an existing one -- does the skill guidance need to encode discovery logic, or is that always the agent's responsibility?
  **Answer:** NOT FOUND -- the question targets the writing-bash-scripts skill's SKILL.md body, which is outside `REPO_ROOT` at `/home/vscode/.agents/skills/writing-bash-scripts/`.

The repo does not contain any bash script skills. The only scripts in the repo are Python eval harness scripts (`scripts/run_eval.py`, `scripts/grade.py`, `scripts/check_scope.py`, `scripts/diagnose.py`, `scripts/report.py`, `scripts/revise.py`). No SKILL.md in the repo addresses bash script creation logic.

**Dependencies:** N/A -- writing-bash-scripts is outside repo scope.
**Implicit contracts:** N/A

## Q7: The ticket calls out bash 3.2 on macOS versus bash 4+ features like associative arrays -- should the skill include a conditional detection mechanism (e.g., `bash --version` check at skill invocation time), or is the documentation note sufficient?
  **Answer:** NOT FOUND -- the question targets the writing-bash-scripts skill's references or SKILL.md body, which is outside `REPO_ROOT`.

The repo contains zero references to bash 3.2, bash 4, `bash --version`, or any bash version detection logic. Searched all `.md`, `.json`, and `.py` files under `REPO_ROOT` -- zero matches for "ShellCheck", "bash 3", or "bash --version".

**Dependencies:** N/A -- writing-bash-scripts references are outside repo scope.
**Implicit contracts:** N/A

## Q8: The ticket requires ShellCheck-clean output -- should the skill itself invoke ShellCheck as a post-generation verification step, or is that a manual gate the agent performs?
  **Answer:** NOT FOUND -- the question targets the writing-bash-scripts skill's SKILL.md guidance, which is outside `REPO_ROOT`.

ShellCheck is not referenced anywhere in the repo's codebase, configs, or documentation. The eval harness (`scripts/grade.py`, `evals/suite.json`) has no programmatic checks related to ShellCheck. The eval cases test file existence, section presence, line counts, citation compliance, scope enforcement, and LLM judges -- but no static analysis of generated scripts.

**Dependencies:** N/A -- writing-bash-scripts SKILL.md is outside repo scope.
**Implicit contracts:** N/A

## Q9: How should the skill's correctness be evaluated -- does the eval harness look at generated scripts passing ShellCheck, functional test results, or both?
  **Answer:** The repo's eval harness answers this question for the QRSPI workflow skills, though not specifically for a bash script skill.

The eval system at `evals/suite.json` defines 15 test cases across phases (questions, research, design, structure, plan, worktree, implement, pr). Each case has assertions of three types:

1. **programmatic** -- runs Python check functions from `scripts/grade.py`. Examples: `output_file_exists`, `has_section`, `line_count`, `no_solution_language`, `all_evidence_has_file_citations`, `current_state_has_citations`.
2. **llm_judge** -- subjective quality scoring (currently stubbed, returns `passed: null`). Examples: "Questions cover data isolation and tenant resolution", "Agent correctly identifies WebSocket as a NEW PATTERN".
3. **script** -- runs an external script and checks exit code. Example: `scripts/check_scope.py --log impl-log.md --allowed fixtures/worktree_session1.md`.

The eval harness (`scripts/run_eval.py`) takes a skill path, suite path, and output directory. It runs N trials per case (default 3) in parallel, captures outputs and errors, then `scripts/grade.py` scores each trial against the assertions.

There are no ShellCheck assertions in any eval case. No case produces a "generated bash script" and checks it. The evals focus on artifact quality (questions, research, design, structure, plan, worktree, implementation, PR summary) -- not on generated script correctness.

**Dependencies:** `evals/suite.json` defines cases and assertions. `scripts/run_eval.py` executes trials. `scripts/grade.py` scores against assertions. `scripts/check_scope.py` verifies implementation scope.
**Implicit contracts:** Eval assertions reference `output` and `files` from the agent's execution result. The `output` field is the agent's stdout/returned text. The `files` field lists produced files.

## Q10: When the skill-creator skill runs, what logging or output does it produce that would help debug a failed skill generation -- and should the writing-bash-scripts skill add its own instrumentation?
  **Answer:** NOT FOUND -- the question targets the skill-creator skill's execution output, which is outside `REPO_ROOT`.

The `skill-creator/scripts/run_loop.py` and `skill-creator/scripts/run_eval.py` files exist outside repo scope. The repo has no logging infrastructure for skill execution. The qrspi-work skill orchestrates phases by spawning sub-agents and verifying artifact existence (`Verify the artifact exists and is non-empty`), but does not capture agent stdout or error output beyond the artifact check.

**Dependencies:** N/A -- skill-creator execution output is outside repo scope.
**Implicit contracts:** N/A

---

## Discovered Patterns

1. **Two-file skill pattern**: Each QRSPI workflow skill consists of a thin SKILL.md wrapper (in `.claude/skills/<name>/SKILL.md`) that delegates to a full prompt definition in `.claude/agents/qrspi-<name>.md`. The SKILL.md frontmatter defines tool access (`allowed-tools`); the agent file defines model (`model: opus`) and hard constraints.

2. **Trigger definition**: All 10 repo skills use the `command` frontmatter field with a `/` prefix (e.g., `command: /qrspi-research`). The `description` field uses "Use when..." language for auto-trigger matching, as listed in `.claude/CLAUDE.md`.

3. **Reference subdirectory convention**: Only one skill (`qrspi-work`) uses a `references/` subdirectory, containing `review-cascade.md` with dependency cascade logic for planning feedback resolution. No skills use `scripts/` or `assets/` subdirectories.

4. **Eval harness architecture**: Three-file pipeline. `run_eval.py` orchestrates trial execution (loads skill text + suite, runs N parallel trials, captures results). `suite.json` defines test cases with typed assertions (programmatic, llm_judge, script). `grade.py` scores assertions against results using weighted scoring with train/test split.

5. **Thematic consistency**: All skills and agents enforce "HARD STOP: Infrastructure Errors" -- identical wording across qrspi-work, qrspi-implement, and qrspi-research agent files. The firewall pattern (research firewall, project scope boundary) is repeated across all agent definitions.

6. **Orchestrator-subagent split**: `qrspi-work/SKILL.md` is the only file that spawns sub-agents (orchestrator). All other SKILL.md files are "thin wrappers" that each spawn a single sub-agent type. The orchestrator handles all git/graphite operations; sub-agents are read/write only.

## Inconsistencies

1. **Skill file count mismatch**: `.claude/CLAUDE.md` lists 11 available skills, but only 10 SKILL.md files exist under `.claude/skills/`. The "update-config" skill listed in the system prompt is not present as a file in `.claude/skills/` or `.agents/skills/` -- it is provided as a built-in skill definition (not a file).

2. **Agent definitions missing from repo**: The `.claude/agents/` directory has 8 agent files (design, implement, plan, pr, questions, research, structure, worktree) but no `qrspi-work.md` file. The orchestrator skill (qrspi-work) defines its own prompt inline in the SKILL.md rather than delegating to a separate agent file. This is the only skill that does not follow the two-file pattern.

3. **Eval harness completeness gap**: `scripts/grade.py` defines 11 programmatic check functions in its `CHECKS` registry, but the eval suite references additional check names that are NOT in the registry: `question_count`, `all_questions_answered`, `all_answers_have_evidence`, `no_slice_exceeds_file_limit`, `all_slices_have_context_cost`, `all_files_marked_new_or_modify`, `total_steps`, `all_modify_steps_have_current_after`, `all_slices_have_verify_checkpoint`, `all_steps_are_atomic`, `has_critical_path`, `all_tasks_have_required_fields`, `session_boundaries_have_reasons`, `sessions_have_load_manifests`, `impl_log_has_required_fields`, `impl_log_has_deviations`, `output_file_exists` (used in suite but registered as check). Several checks (like `all_questions_answered`, `no_slice_exceeds_file_limit`) are called in the suite but have no corresponding implementation in `grade.py` -- they would fall through to "Unknown check function" and be skipped.

4. **Script check stub**: `scripts/grade.py`'s `run_script_check` function is a stub that returns `passed: null` with evidence "Script checks not yet integrated". Yet the eval suite has a script-type assertion (case_011: `scripts/check_scope.py --log impl-log.md --allowed fixtures/worktree_session1.md`) that would never actually execute.
