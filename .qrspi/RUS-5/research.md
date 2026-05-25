# Research — Codebase Map
**Questions source:** questions.md @ 2025-05-25T00:00:00Z
**Generated:** 2026-05-25T18:30:00Z
**Status:** draft

## Q1: What is the agentskills.io standard directory structure for a skill, and does the project already contain any existing skills that follow this pattern (e.g., a `SKILL.md` with frontmatter, `references/`, `scripts/`, `assets/` directories)?

**Answer:** The project contains 10 skills under `.claude/skills/`, all following the same directory structure. Each skill directory contains a single `SKILL.md` file. Only one skill (`qrspi-work`) has a `references/` subdirectory. No project-level skills contain `scripts/` or `assets/` directories. The canonical skill directory anatomy is documented in the user-level skill-creator skill at `~/.claude/skills/skill-creator/SKILL.md`.

**Evidence:**

Directory listing of all skill directories:
```
.claude/skills/qrspi-design/SKILL.md
.claude/skills/qrspi-implement/SKILL.md
.claude/skills/qrspi-plan/SKILL.md
.claude/skills/qrspi-pr/SKILL.md
.claude/skills/qrspi-questions/SKILL.md
.claude/skills/qrspi-research/SKILL.md
.claude/skills/qrspi-structure/SKILL.md
.claude/skills/qrspi-ticket/SKILL.md
.claude/skills/qrspi-work/SKILL.md
.claude/skills/qrspi-work/references/review-cascade.md
.claude/skills/qrspi-worktree/SKILL.md
```

The skill-creator defines the canonical anatomy (`~/.claude/skills/skill-creator/SKILL.md:76-84`):
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

The user-level skill-creator itself follows this pattern with `references/schemas.md`, `agents/` (3 files), `scripts/` (8 Python files), and `assets/`.

**Dependencies:** Skills are discovered by Claude Code from the `.claude/skills/` directory. No manifest or registration file is used (see Q4).
**Implicit contracts:** Every skill directory must contain a `SKILL.md` at minimum. Subdirectories (`references/`, `scripts/`, `assets/`) are optional and loaded on demand.

---

## Q2: How does the Anthropic skill builder skill (`skill-creator`) expect input to be provided, and what artifacts does it produce — specifically, does it write `SKILL.md` directly or does it return content for the caller to write?

**Answer:** The skill-creator is an interactive, conversational skill. It does not accept structured input; instead it guides the user through a multi-phase process: (1) capture intent, (2) interview and research, (3) write the SKILL.md, (4) create test cases, (5) run evals via subagents, (6) iterate based on feedback. It writes the `SKILL.md` directly and produces additional artifacts in a `<skill-name>-workspace/` sibling directory.

**Evidence:**

From `~/.claude/skills/skill-creator/SKILL.md:46-68`:
```
### Capture Intent
Start by understanding the user's intent...
1. What should this skill enable Claude to do?
2. When should this skill trigger? (what user phrases/contexts)
3. What's the expected output format?
4. Should we set up test cases to verify the skill works?

### Interview and Research
Proactively ask questions about edge cases...

### Write the SKILL.md
Based on the user interview, fill in these components:
- **name**: Skill identifier
- **description**: When to trigger, what it does...
```

From `~/.claude/skills/skill-creator/SKILL.md:143-158`, test cases are saved to `evals/evals.json` within the skill directory. Results go into `<skill-name>-workspace/iteration-N/eval-ID/`.

The skill-creator writes SKILL.md directly (it instructs Claude to fill in the components). It also produces: `evals/evals.json`, `benchmark.json`, `benchmark.md`, `grading.json`, `feedback.json`, and optionally a `.skill` package.

**Dependencies:** The skill-creator depends on subagent capability (Agent tool) for parallel test execution. It uses `generate_review.py` for the HTML eval viewer.
**Implicit contracts:** The skill-creator expects to be invoked interactively and drives the conversation. It produces a SKILL.md at a path the user specifies or in the current skill directory.

---

## Q3: What frontmatter schema does `SKILL.md` require (fields, types, required vs optional) according to the agentskills.io standard as implemented in this project?

**Answer:** The YAML frontmatter uses these fields based on the skill-creator documentation and the 10 existing project skills:

- `name` (string, required) — Skill identifier
- `description` (string, required) — When to trigger, what it does. This is the primary triggering mechanism.
- `command` (string, observed in all project skills) — Slash command for invocation, e.g., `/qrspi-ticket`
- `argument-hint` (string, observed in all project skills) — Placeholder for arguments, e.g., `<ticket-id>`
- `allowed-tools` (string, observed in all project skills) — Comma-separated list of tools the skill may use

The skill-creator explicitly states `name` and `description` are required. It also mentions `compatibility` as optional and "rarely needed."

**Evidence:**

Skill-creator states required fields (`~/.claude/skills/skill-creator/SKILL.md:76-78`):
```
├── SKILL.md (required)
│   ├── YAML frontmatter (name, description required)
│   └── Markdown instructions
```

Example from `qrspi-ticket/SKILL.md:1-7`:
```yaml
---
name: qrspi-ticket
description: Draft a new feature ticket through guided conversation...
command: /qrspi-ticket
argument-hint: <initial description>
allowed-tools: Read, Glob, Grep, Write, Bash, mcp__linear-russelltsherman__save_issue
---
```

The skill-creator's own frontmatter is minimal (`~/.claude/skills/skill-creator/SKILL.md:1-3`):
```yaml
---
name: skill-creator
description: Create new skills, modify and improve existing skills...
---
```
(No `command`, `argument-hint`, or `allowed-tools` fields.)

**Dependencies:** Claude Code reads frontmatter to determine triggering (description field) and tool access (allowed-tools field).
**Implicit contracts:** The `command`, `argument-hint`, and `allowed-tools` fields are not documented as required by the skill-creator but are used consistently across all 10 project skills. The skill-creator itself omits them, suggesting they are conventions of this project rather than schema requirements.

---

## Q4: Where do completed skills get installed or registered so that Claude Code can discover and invoke them — is there a settings file, a directory convention, or a manifest that indexes available skills?

**Answer:** Skills are discovered by directory convention. Any directory under `.claude/skills/` containing a `SKILL.md` is automatically available to Claude Code. There is no manifest, no registration step, and no settings.json entry required. The project has no `.claude/settings.json` or `.claude/settings.local.json` file. User-level skills live at `~/.claude/skills/`.

**Evidence:**

The project's `.claude/` directory contains only:
```
.claude/CLAUDE.md
.claude/skills/  (10 skill directories)
```

No `settings.json` was found anywhere under `.claude/`:
```bash
find /Users/russelltsherman/src/github.com/russelltsherman/qrspi -name "settings.json" -path "*/.claude/*"
# (no output)
```

The skill-creator mentions packaging via `package_skill.py` which produces a `.skill` file for distribution, but discovery is directory-based.

User-level skills at `~/.claude/skills/` (graphite-workspace, mcp-builder, skill-creator, using-graphite-cli, workflow-creator) are also discovered automatically — they appear in the system reminder's available skills list.

**Dependencies:** Claude Code runtime reads the `.claude/skills/` directory at session start.
**Implicit contracts:** The skill directory name becomes the skill identifier used in slash commands and auto-invocation. There is a two-level hierarchy: project-level (`.claude/skills/`) and user-level (`~/.claude/skills/`).

---

## Q5: What is the exact invocation interface the skill-creator skill exposes — what arguments does it accept, and does it have an eval loop that must be run before a skill is considered complete?

**Answer:** The skill-creator does not define a `command` or `argument-hint` in its frontmatter — it is triggered by description matching, not slash command. It does have an eval loop, but it is not strictly mandatory; the skill-creator says "if the user is like 'I don't need to run a bunch of evaluations, just vibe with me', you can do that instead."

The eval loop has these stages:
1. Spawn parallel subagent runs (with-skill and baseline) for each test case
2. Draft quantitative assertions while runs execute
3. Capture timing data from task notifications
4. Grade, aggregate into benchmark.json, launch HTML viewer
5. User reviews in browser, submits feedback
6. Read feedback.json, improve skill, repeat

Additionally, there is a separate description optimization loop using `scripts/run_loop.py` that generates trigger-eval queries and iteratively improves the skill's description for triggering accuracy.

**Evidence:**

Skill-creator frontmatter (`~/.claude/skills/skill-creator/SKILL.md:1-3`):
```yaml
---
name: skill-creator
description: Create new skills, modify and improve existing skills...
---
```

Flexibility clause (`~/.claude/skills/skill-creator/SKILL.md:26`):
```
Of course, you should always be flexible and if the user is like
"I don't need to run a bunch of evaluations, just vibe with me",
you can do that instead.
```

Description optimization (`~/.claude/skills/skill-creator/SKILL.md:335-404`):
The `scripts/run_loop.py` command runs up to 5 iterations, using 60/40 train/test split, evaluating each query 3 times.

**Dependencies:** Eval loop requires subagent capability (Agent tool), `claude -p` CLI for description optimization, Python for scripts, and a browser for the HTML viewer (or `--static` fallback).
**Implicit contracts:** A user-facing memory directive exists at `~/.agents/memory/feedback_skill_creator.md` stating: "Always invoke the skill-creator skill (and its eval loop) when creating or substantially modifying a skill; never ship a SKILL.md ad-hoc."

---

## Q6: Does the project enforce a token or line budget for `SKILL.md` files, and if so, where is that constraint defined and how is it validated?

**Answer:** The skill-creator defines a soft budget of 500 lines for SKILL.md, with guidance to use references for overflow. There is no automated validation — no linting script, CI check, or pre-commit hook enforces this limit.

**Evidence:**

From `~/.claude/skills/skill-creator/SKILL.md:88-98`:
```
#### Progressive Disclosure
Skills use a three-level loading system:
1. **Metadata** (name + description) - Always in context (~100 words)
2. **SKILL.md body** - In context whenever skill triggers (<500 lines ideal)
3. **Bundled resources** - As needed (unlimited, scripts can execute without loading)

These word counts are approximate and you can feel free to go longer if needed.

**Key patterns:**
- Keep SKILL.md under 500 lines; if you're approaching this limit,
  add an additional layer of hierarchy along with clear pointers
```

The project has no CI configuration (no `.github/workflows/`, no YAML files, no Makefile). The skill-creator's own SKILL.md is 486 lines — close to but under the 500-line guidance.

Current line counts for project skills (all well under budget):
- qrspi-work: 448 lines (largest)
- qrspi-ticket: 76 lines
- qrspi-questions: 47 lines
- qrspi-research: 58 lines
- Other skills: 37-58 lines each

**Dependencies:** None (soft guideline only).
**Implicit contracts:** The 500-line limit is advisory. The three-level loading system (metadata → body → resources) implies that skill authors are expected to self-regulate and move content to `references/` when SKILL.md grows large.

---

## Q7: When a skill references supplementary material in `references/`, how are those files linked or included from the `SKILL.md` body — via relative paths, `@`-includes, or another mechanism?

**Answer:** References are linked by prose description with relative paths — there is no `@`-include or automatic injection mechanism. The SKILL.md body tells the reader (Claude) when and what to read using natural language instructions.

**Evidence:**

The only project skill with a `references/` directory is `qrspi-work`. It references the file at `.claude/skills/qrspi-work/SKILL.md:175`:
```
c. Read `references/review-cascade.md` for cascade logic.
d. Address feedback starting from the earliest affected artifact —
   read the cascade reference for the re-run rules.
```

The skill-creator describes this pattern (`~/.claude/skills/skill-creator/SKILL.md:96-109`):
```
- Reference files clearly from SKILL.md with guidance on when to read them
- For large reference files (>300 lines), include a table of contents

**Domain organization**: When a skill supports multiple domains/frameworks,
organize by variant:
    cloud-deploy/
    ├── SKILL.md (workflow + selection)
    └── references/
        ├── aws.md
        ├── gcp.md
        └── azure.md
Claude reads only the relevant reference file.
```

The skill-creator's own SKILL.md references its bundled files via prose (`~/.claude/skills/skill-creator/SKILL.md:459-467`):
```
The agents/ directory contains instructions for specialized subagents.
Read them when you need to spawn the relevant subagent.
- `agents/grader.md` — How to evaluate assertions against outputs
- `agents/comparator.md` — How to do blind A/B comparison
- `agents/analyzer.md` — How to analyze why one version beat another

The references/ directory has additional documentation:
- `references/schemas.md` — JSON structures for evals.json, grading.json, etc.
```

**Dependencies:** Claude Code's `Read` tool is used at runtime to load referenced files.
**Implicit contracts:** References are loaded lazily — only when the skill's execution flow reaches the point where the reference is needed. This is by design to minimize context window usage.

---

## Q8: If the bash-scripts skill needs to exceed the 500-line / 5000-token SKILL.md budget, what is the established pattern for splitting content between the main `SKILL.md` and the `references/` directory?

**Answer:** The established pattern has two examples in the codebase:

1. **qrspi-work skill** — SKILL.md (448 lines) keeps the primary workflow and state machine logic. A single reference file (`references/review-cascade.md`, 64 lines) holds the review cascade logic, loaded only when the skill enters the "Plan Review" state.

2. **skill-creator skill** — SKILL.md (486 lines) keeps the core workflow. Three agent prompt files live in `agents/` (grader, comparator, analyzer) and one schema reference in `references/schemas.md` (431 lines). These are loaded only when their specific subagent or schema validation step is needed.

The general pattern is: SKILL.md contains the primary control flow and decision logic; `references/` contains domain-specific detail, lookup tables, or subagent prompts that are only needed in specific branches of execution.

**Evidence:**

`qrspi-work/SKILL.md:175-176` — conditional reference load:
```
c. Read `references/review-cascade.md` for cascade logic.
```

Skill-creator domain organization pattern (`~/.claude/skills/skill-creator/SKILL.md:100-109`):
```
**Domain organization**: When a skill supports multiple
domains/frameworks, organize by variant:
    cloud-deploy/
    ├── SKILL.md (workflow + selection)
    └── references/
        ├── aws.md
        ├── gcp.md
        └── azure.md
Claude reads only the relevant reference file.
```

Progressive disclosure hierarchy (`~/.claude/skills/skill-creator/SKILL.md:88-92`):
```
1. **Metadata** (name + description) - Always in context (~100 words)
2. **SKILL.md body** - In context whenever skill triggers (<500 lines ideal)
3. **Bundled resources** - As needed (unlimited, scripts can execute without loading)
```

**Dependencies:** Splitting depends on Claude's ability to Read files at runtime.
**Implicit contracts:** The SKILL.md body must contain clear "when to read" guidance for each reference file so Claude knows the trigger condition.

---

## Q9: The ticket specifies "bash 4+" as the target but notes macOS ships bash 3.2. Are there any existing project scripts or CI environments that run bash 3.2, which would conflict with bash 4+ guidance in the skill?

**Answer:** The host macOS system runs bash 3.2.57. One project script (`initialize.sh`) runs on the host machine before the container starts. The devcontainer runs Ubuntu 24.04, which ships bash 5.x. There is no CI configuration in the project.

**Evidence:**

Host bash version:
```
GNU bash, version 3.2.57(1)-release (arm64-apple-darwin25)
```

`initialize.sh` explicitly states it runs on the host (`initialize.sh:4`):
```
# initializeCommand — runs on the HOST machine before the container is built or started.
# $HOME here is the host user's home directory (e.g. /Users/you on macOS).
```

`initialize.sh` uses bash 3.2-compatible features only: `[[ ]]`, string comparisons, `local`, `printf`, `security` CLI. It uses `#!/usr/bin/env bash`.

The devcontainer Dockerfile is based on `mcr.microsoft.com/devcontainers/base:ubuntu-24.04` (`.devcontainer/Dockerfile:1`), which includes bash 5.x.

Scripts that run inside the container (`protect-paths`, `protect-egress`, `show-motd`, `start-squid`, `post-create.sh`, `post-start.sh`) use bash features available in 3.2+ (`BASH_REMATCH`, `[[ =~ ]]`, arrays, `set -euo pipefail`). However, `protect-paths` uses `${!PRUNE_NAMES[@]}` (indirect expansion of array indices) which requires bash 3.0+, and `(( i > 0 ))` arithmetic which is bash 3.0+.

`run_loop.sh` uses `#!/bin/bash` (not `#!/usr/bin/env bash`) and only uses bash 3.2-compatible features (`set -euo pipefail`, `$()`, `${}`, `for`/`seq`, `if`/`[`).

**Dependencies:** The `initialize.sh` script must remain bash 3.2 compatible as it runs on the macOS host.
**Implicit contracts:** All existing scripts use `#!/usr/bin/env bash` except `run_loop.sh` which uses `#!/bin/bash`. None use bash 4+ exclusive features like `declare -A` (associative arrays), `readarray`/`mapfile`, `local -n` (namerefs), or `${var,,}` (lowercase transform).

---

## Q10: The ticket mandates ShellCheck-clean output. Does the project already have ShellCheck configured (e.g., `.shellcheckrc`), and are there existing ShellCheck directives or exclusions that the new skill must be aware of?

**Answer:** No `.shellcheckrc` file exists in the project. No ShellCheck CI integration exists. One existing script contains a ShellCheck inline directive. ShellCheck is not installed in the Dockerfile.

**Evidence:**

Search results for `.shellcheckrc`:
```bash
find /Users/russelltsherman/src/github.com/russelltsherman/qrspi -name ".shellcheckrc"
# (no output)
```

The single ShellCheck directive found is in `.devcontainer/config/protect-paths:116`:
```bash
# shellcheck disable=SC2053  # intentional fnmatch via unquoted RHS
[[ "$base" == $p ]] && return 0
```

This disables SC2053 (warning about glob/fnmatch via unquoted right-hand side of `==` inside `[[ ]]`), which is intentional — the script uses fnmatch pattern matching.

The Dockerfile (`.devcontainer/Dockerfile:7-15`) installs: `ca-certificates`, `curl`, `git`, `gnupg`, `iptables`, `jq`, `squid`. No `shellcheck` package.

No CI configuration files (no `.github/`, no YAML, no Makefile) exist in the project.

**Dependencies:** None — ShellCheck is absent from the project toolchain.
**Implicit contracts:** The one existing SC2053 directive in `protect-paths` establishes a precedent that inline ShellCheck disable comments should include a justification comment explaining the intent.

---

## Q11: The ticket says to use the subcommand dispatcher pattern when a script has 2+ distinct operations. Are there existing bash scripts in the project that use a different pattern (e.g., separate scripts per operation) that would create inconsistency if the skill enforces the dispatcher pattern?

**Answer:** The project has 8 bash scripts. None use a subcommand dispatcher pattern (no `case "$1" in` dispatch). The existing scripts follow two patterns:
1. **Single-purpose scripts** — Each script does one thing (e.g., `start-squid` starts squid, `protect-egress` sets iptables rules)
2. **Parameterized runner** — `run_loop.sh` takes positional arguments but has a single execution path, not multiple subcommands

**Evidence:**

All 8 scripts and their patterns:
- `run_loop.sh` — Takes 4 positional args, single execution flow (eval loop)
- `.devcontainer/config/initialize.sh` — No args, single-purpose (host prereqs + keychain export)
- `.devcontainer/config/post-create.sh` — No args, single-purpose (one-time container setup)
- `.devcontainer/config/post-start.sh` — No args, single-purpose (per-start container setup)
- `.devcontainer/config/protect-paths` — No args, single-purpose (bind-mount secrets)
- `.devcontainer/config/protect-egress` — No args, single-purpose (iptables rules)
- `.devcontainer/config/start-squid` — No args, single-purpose (exec squid)
- `.devcontainer/config/show-motd` — No args, single-purpose (display banner)

Search for `case`, `getopts`, `dispatch`, `subcommand`, `usage()`, `main()` across all scripts returned no relevant matches.

**Dependencies:** None — no script depends on another's argument parsing.
**Implicit contracts:** The existing codebase favors the "one script, one purpose" pattern. The devcontainer scripts are lifecycle hooks (initialize, post-create, post-start) where this pattern is natural. There is no conflict with the dispatcher pattern because no existing script would need to be changed — the dispatcher pattern would apply only to new scripts created using the skill.

---

## Q12: Does the project have BATS-core installed or configured as a test dependency, and is there an existing test harness or directory convention for bash script tests?

**Answer:** BATS-core is not present in the project. There is no bash test harness. The project's test infrastructure is Python-based, focused on evaluating QRSPI agent prompts via `evals/suite.json` and `scripts/` (Python scripts).

**Evidence:**

Search for BATS references:
```bash
grep -r "bats" /Users/russelltsherman/src/github.com/russelltsherman/qrspi/ --include="*.sh" --include="*.md" --include="*.json"
# (no output)
```

No `test/`, `tests/`, or `spec/` directories exist. No `package.json`, `Makefile`, `go.mod`, `requirements.txt`, or other dependency manifest files exist in the project root.

However, the user-level settings at `~/.claude/settings.json` includes a permission entry: `"Bash(bats:*)"`, indicating BATS is an expected tool in the user's workflow.

The existing eval harness is Python:
- `scripts/run_eval.py` — Runs eval suite
- `scripts/grade.py` — Grades results
- `scripts/diagnose.py` — Diagnoses failures
- `scripts/revise.py` — Proposes revisions
- `scripts/report.py` — Generates reports
- `scripts/check_scope.py` — Checks implementation scope
- `evals/suite.json` — 15 eval cases with programmatic and LLM-judge assertions

The Dockerfile does not install BATS. The Ubuntu 24.04 base image does not include BATS.

**Dependencies:** None currently.
**Implicit contracts:** The user has `Bash(bats:*)` in their global allowed permissions, which signals expectation that BATS will be used for bash testing across projects.

---

## Q13: How does the skill-creator's eval loop validate a skill — does it generate test scenarios, invoke the skill against sample prompts, or check structural conformance only?

**Answer:** The skill-creator uses a multi-faceted validation approach that goes well beyond structural conformance. It:

1. **Spawns subagent test runs** — For each test case, spawns two parallel subagents: one with the skill, one without (baseline). Each receives the test prompt and input files.
2. **Quantitative grading** — A grader subagent (`agents/grader.md`) evaluates assertions against outputs, producing `grading.json` with pass/fail per expectation and evidence.
3. **Programmatic checks** — Scripts can verify assertions (e.g., file existence, content checks).
4. **Benchmark aggregation** — `scripts/aggregate_benchmark.py` computes pass_rate, time, tokens with mean/stddev per configuration.
5. **Human review** — `eval-viewer/generate_review.py` generates an HTML viewer for qualitative assessment; user feedback is captured in `feedback.json`.
6. **Blind comparison** (optional) — `agents/comparator.md` does A/B comparison without revealing which output came from which skill version.
7. **Description optimization** — `scripts/run_loop.py` evaluates trigger accuracy with should-trigger/should-not-trigger queries, iterating up to 5 times.

**Evidence:**

From `~/.claude/skills/skill-creator/SKILL.md:169-175`:
```
**With-skill run:**
Execute this task:
- Skill path: <path-to-skill>
- Task: <eval prompt>
- Input files: <eval files if any, or "none">
- Save outputs to: <workspace>/iteration-<N>/eval-<ID>/with_skill/outputs/
```

Grading step (`~/.claude/skills/skill-creator/SKILL.md:222-225`):
```
1. **Grade each run** — spawn a grader subagent (or grade inline)
   that reads `agents/grader.md` and evaluates each assertion against
   the outputs. Save results to `grading.json` in each run directory.
```

The project-level eval suite (`evals/suite.json`) uses a different but parallel approach with `programmatic` and `llm_judge` assertion types — this is the QRSPI workflow eval system, not the skill-creator's system.

**Dependencies:** Subagents (Agent tool), Python, `claude -p` CLI (for description optimization), browser or `--static` flag (for viewer).
**Implicit contracts:** The skill-creator's eval loop validates runtime behavior, not just structural conformance. A skill is considered ready when: user is satisfied with qualitative review, assertion pass rate is acceptable, and description triggers correctly.

---

## Q14: Does the project have any existing conventions for how skills report their activation, usage, or failure modes — e.g., structured logs, metrics, or error patterns that the bash-scripts skill must conform to?

**Answer:** The project has no observability infrastructure for skill activation or metrics. Skills report status to the user via conversational messages (print statements). Error handling is defined per-skill with explicit stop-and-report patterns.

**Evidence:**

The qrspi-work skill defines error handling conventions (`.claude/skills/qrspi-work/SKILL.md:441-447`):
```
## Error Handling
- If a sub-agent fails → print the error, stop, do not update Linear.
- If a `gt` command fails → print the command and error, stop.
- If the Linear status is unrecognized → print the status, ask the user.
- If a PR can't be found for a branch → report the error, suggest checking GitHub.
- Never partially update state — either a full phase transition succeeds or nothing changes.
```

Each phase skill ends with a closing message pattern. Examples:
- qrspi-questions (`SKILL.md:36`): `"Questions written to '.qrspi/<id>/questions.md'. Review, edit, then tell me 'approved'..."`
- qrspi-research (`SKILL.md:47`): `"Research written to '.qrspi/<id>/research.md'. Review for factual accuracy..."`
- qrspi-implement (`SKILL.md:41`): `"Slice <N> implemented. Tests: <result>. Run '/clear' then..."`

The skill-creator's eval system tracks per-run metrics in `metrics.json` (`~/.claude/skills/skill-creator/references/schemas.md:166-183`):
```json
{
  "tool_calls": {"Read": 5, "Write": 2, "Bash": 8},
  "total_tool_calls": 18,
  "total_steps": 6,
  "errors_encountered": 0
}
```

But this is specific to the skill-creator's eval framework, not a project-wide convention.

**Dependencies:** None.
**Implicit contracts:** Skills communicate status to the user via plain-text messages, not structured data. Error handling follows a "stop and report" pattern — no silent failure or partial state updates.

---

## Discovered Patterns

1. **Minimal skill structure**: All 10 project skills use a single SKILL.md file with YAML frontmatter. Only `qrspi-work` (the most complex skill at 448 lines) uses a `references/` directory.

2. **Consistent frontmatter fields**: All project skills include `name`, `description`, `command`, `argument-hint`, and `allowed-tools`. The user-level `skill-creator` skill only requires `name` and `description` — the other fields are a project convention.

3. **Shebang convention**: 7 of 8 scripts use `#!/usr/bin/env bash`. The exception is `run_loop.sh` which uses `#!/bin/bash`.

4. **Strict mode convention**: All `.sh` scripts use `set -euo pipefail`. The non-.sh scripts (`protect-paths`, `protect-egress`, `start-squid`) also use `set -euo pipefail` except `show-motd` which only has a shebang (no `set` options).

5. **Single-purpose scripts**: Every existing bash script does exactly one thing. No script has subcommands, `getopts`, or argument dispatch logic.

6. **Two execution contexts**: Scripts split between host-side (macOS bash 3.2) and container-side (Ubuntu 24.04 bash 5.x). The `initialize.sh` script is the only one that must run on the macOS host.

7. **Conversational skill closings**: Every QRSPI phase skill ends with a message telling the user what to do next, following the pattern: "Artifact written to `<path>`. <review instruction>. Tell me 'approved' to proceed to <next phase>."

8. **Upload-after-write**: Every phase skill includes an "Upload artifact" section that pushes the artifact to Linear after writing it locally. The upload is non-blocking — if it fails, the local artifact is preserved.

9. **No CI or automation**: The project has zero CI configuration. No GitHub Actions, no pre-commit hooks, no Makefile. Validation happens through the QRSPI eval suite (Python scripts + `evals/suite.json`) and the skill-creator's eval loop.

10. **Two-level skill discovery**: Skills are discovered from both project-level (`.claude/skills/`) and user-level (`~/.claude/skills/`). The user has 5 user-level skills (including skill-creator) and the project has 10 project-level skills.

---

## Inconsistencies

1. **Shebang inconsistency**: `run_loop.sh` uses `#!/bin/bash` while all other scripts use `#!/usr/bin/env bash`. This could produce different behavior if `/bin/bash` and `env bash` resolve to different versions (which they do on macOS when a newer bash is installed via Homebrew).

2. **Strict mode inconsistency**: `show-motd` is the only script that omits `set -euo pipefail` (or any `set` options). All other 7 scripts include it.

3. **Frontmatter field inconsistency**: Project skills consistently include `command`, `argument-hint`, and `allowed-tools` in frontmatter, but the skill-creator documentation only requires `name` and `description`. The skill-creator's own SKILL.md omits `command`, `argument-hint`, and `allowed-tools`. This makes it unclear whether these fields are part of the standard or are project-specific additions.

4. **Script extension inconsistency**: Some scripts have `.sh` extensions (`initialize.sh`, `post-create.sh`, `post-start.sh`, `run_loop.sh`) while others have no extension (`protect-paths`, `protect-egress`, `start-squid`, `show-motd`). The extensionless scripts are all sbin utilities installed as system commands.

5. **Questions file refers to "agentskills.io standard"**: The questions reference "agentskills.io" as a standard, but no agentskills.io documentation or references exist anywhere in the project or user-level configuration. The actual skill standard is defined by the skill-creator skill at `~/.claude/skills/skill-creator/SKILL.md`. The term "agentskills.io" does not appear in any project or user-level file outside the questions.md itself.
