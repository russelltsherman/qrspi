# Research — Codebase Map

**Questions source:** questions.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## Q1: How do existing skills in this repository structure their `SKILL.md` frontmatter (name, description, command, argument-hint, allowed-tools, model), and what fields are required versus optional?

**Answer:** Every skill in `.claude/skills/<name>/SKILL.md` declares YAML frontmatter with: `name`, `description`, `command`, `argument-hint` (optional), and `allowed-tools`. No skill declares a `model` field — that is reserved for agents in `.claude/agents/*.md`. The `description` is a single-line string (sometimes quoted to span phrasing with colons) and acts as the trigger blurb.

**Evidence:**

```
---
name: qrspi-work
description: "Single entry point for autonomous QRSPI feature development. Use when the user asks to 'work on' a ticket..."
command: /qrspi-work
argument-hint: <ticket-id>
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, mcp__linear-russelltsherman__get_issue, ...
---
```

— `.claude/skills/qrspi-work/SKILL.md:1-7`

```
---
name: qrspi-ticket
description: Draft a new feature ticket through guided conversation. Use when starting a new QRSPI workflow or when the user wants to create a ticket.
command: /qrspi-ticket
argument-hint: <initial description>
allowed-tools: Read, Glob, Grep, Write, Bash, mcp__linear-russelltsherman__save_issue
---
```

— `.claude/skills/qrspi-ticket/SKILL.md:1-7`

**Dependencies:** None — frontmatter is consumed by Claude Code's skill loader.
**Implicit contracts:** `allowed-tools` is a comma-separated whitelist; only listed tools are callable inside the skill body. `command` is the slash-command invocation token.

## Q2: What is the canonical directory layout that other skills in this repo use for `references/`, `scripts/`, and `assets/` subdirectories?

**Answer:** Only one skill in this repo uses a subdirectory beyond `SKILL.md`: `qrspi-work` has a `references/` directory containing one markdown file (`review-cascade.md`). No skill in the repo uses `scripts/` or `assets/` subdirectories. The skill content is otherwise self-contained inside `SKILL.md`.

**Evidence:**

```
.claude/skills/qrspi-work/
├── SKILL.md
└── references/
    └── review-cascade.md
```

— `.claude/skills/qrspi-work/` (directory listing)

All other skills (`qrspi-ticket`, `qrspi-design`, `qrspi-plan`, etc.) consist of a lone `SKILL.md`.

**Dependencies:** The `references/` file is referenced from `SKILL.md` via a relative path: `Read references/review-cascade.md`.
**Implicit contracts:** Reference files are read on-demand by the skill body, not auto-injected.

## Q3: Which `gh` CLI subcommands are already used elsewhere in this repo (workflows, scripts, other skills, CLAUDE.md guidance), and what conventions are already established for invoking them?

**Answer:** The `qrspi-work` skill is the only skill that invokes `gh`. It uses six command patterns: `gh repo view`, `gh pr list`, `gh pr view`, `gh api repos/.../pulls/.../comments`, `gh pr edit`, and (implicitly through Graphite) PR creation. Every invocation uses `--json <fields>` with `--jq` for parsing, and HEREDOC blocks for multi-line `--body` content. No `gh issue`, `gh release`, `gh run`, or `gh workflow` usage exists in the repo today. The `gh` binary is installed in the devcontainer image and the host's `~/.config/gh` is bind-mounted read-only.

**Evidence:**

```
gh repo view --json nameWithOwner --jq '.nameWithOwner'
gh pr list --head <ticket-id>/planning --json number,reviewDecision --jq '.[0]'
gh pr view <number> --json reviews,comments --jq '.reviews[] | select(.state != "APPROVED")'
gh api repos/<owner>/<repo>/pulls/<number>/comments --jq '.[] | {path, body, line}'
gh pr edit <slice-1-pr-number> --body "$(cat .qrspi/<ticket-id>/pr-summary.md)"
```

— `.claude/skills/qrspi-work/SKILL.md:240-426`

```
# .devcontainer/Dockerfile:10  — gh installed alongside other dev tooling
gh \
```

— `.devcontainer/Dockerfile:10`

```
"source=${localEnv:HOME}/.config/gh,target=/home/vscode/.config/gh,type=bind,readonly"
```

— `.devcontainer/devcontainer.json:40`

**Dependencies:** Bash + jq (via `--jq` flag, no separate `jq` install required).
**Implicit contracts:** Multi-line PR bodies always use `$(cat <<'EOF' ... EOF)` HEREDOC to preserve formatting. JSON output is always filtered with `--jq` rather than piped through external parsers.

## Q4: Does this repo already have any documented pattern for shell snippets in skills (e.g., HEREDOC commit bodies, `--json`/`--jq` parsing), and where is that pattern codified?

**Answer:** Yes — the `qrspi-work` skill codifies the canonical pattern: HEREDOC bodies for commit messages and PR bodies, and `--json <fields> --jq '<filter>'` for any structured CLI output. There is no separate style guide; the pattern is only by example inside `qrspi-work/SKILL.md`. The repo also has a strong "no `git add -a`" rule documented in `qrspi-work/SKILL.md:642-664`.

**Evidence:**

```
gt modify -c --no-interactive -m "$(cat <<'EOF'
<ticket-id>: Planning

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

— `.claude/skills/qrspi-work/SKILL.md:143-149`

**Dependencies:** Bash 3.2+ (HEREDOC with single-quoted delimiter to prevent variable expansion).
**Implicit contracts:** Quoted HEREDOC delimiter (`'EOF'`) is mandatory so `$ARGUMENTS` etc. inside commit bodies are not interpolated.

## Q5: Where does the qrspi workflow currently document its trigger conditions (the YAML `description` field) and how do other skills format that description string to maximize triggering accuracy?

**Answer:** Trigger conditions are encoded entirely in the `description:` frontmatter line. The most elaborate example is `qrspi-work` which uses a single quoted string with multiple "Trigger on any variant of …" phrases naming literal user utterances. Other skills use shorter declarative sentences. No external trigger config exists.

**Evidence:**

```
description: "Single entry point for autonomous QRSPI feature development. Use when the user asks to 'work on' a ticket (e.g., 'work on RUS-42'). ... Trigger on any variant of: 'work on <ticket-id>', 'continue <ticket-id>', 'pick up <ticket-id>', or any reference to progressing a QRSPI ticket through its lifecycle."
```

— `.claude/skills/qrspi-work/SKILL.md:3`

**Dependencies:** None.
**Implicit contracts:** Descriptions that name literal user utterances ("work on X", "continue X") appear to be the preferred pattern for high-recall triggering in this repo.

## Q6: How does this repo's skill-creator skill expect new skills to be authored and evaluated — what is its end-to-end flow, and what evals harness exists?

**Answer:** No `skill-creator` skill exists locally in `.claude/skills/`. The skill-creator referenced in system prompts is a global plugin outside this repo (in `~/.claude/` or the harness). The repo's own evals harness lives in `evals/` and `scripts/`: `evals/suite.json` defines named test cases with `programmatic` assertions (e.g., `output_file_exists('questions.md')`, `question_count >= 8`); `scripts/run_eval.py` is the runner. The harness is designed for QRSPI workflow agents, not arbitrary skills.

**Evidence:**

```
{
  "name": "qrspi-agent-evals",
  "version": "0.1.0",
  "description": "Eval suite for QRSPI workflow agent prompts",
  ...
  "cases": [
    {
      "id": "case_001",
      "name": "questions_happy_path",
      "phase": "questions",
      "assertions": [
        {"type": "programmatic", "check": "output_file_exists('questions.md')", "weight": 1.0},
        ...
```

— `evals/suite.json:1-50`

```
evals/
├── fixtures/
│   ├── ticket_15_acceptance_criteria.md
│   ├── ticket_multi_tenancy.md
│   ├── ticket_rest_endpoint.md
│   └── ticket_websocket.md
├── graphite-evals.json
└── suite.json
scripts/
├── check_scope.py
├── diagnose.py
├── grade.py
├── report.py
├── revise.py
└── run_eval.py
```

— `evals/`, `scripts/` directory listings

**Dependencies:** Python 3 (no requirements file visible in research scope).
**Implicit contracts:** Eval cases target QRSPI phase agents (`phase: "questions"`, etc.). A new general-purpose skill like the gh-cli skill would have to define its own assertions or run outside this harness.

## Q7: What is the established convention for skills that wrap external CLIs (like the using-graphite-cli skill) regarding tool lockdown, allowed bash patterns, and forbidding raw invocations of the underlying tool outside the skill?

**Answer:** NOT FOUND — the using-graphite-cli skill is not present in this repo. The repo's own CLI-wrapping examples are limited to `qrspi-work`'s internal `gh` and `gt` calls; that skill achieves "lockdown" by listing `Bash` in `allowed-tools` and documenting strict rules in its body (`## Git/Graphite Rules`, `## HARD STOP: Infrastructure Errors Are Not Puzzles To Solve`). There is no `Bash(gh:*)` style fine-grained tool restriction in evidence inside this repo's skills.

**Evidence:**

```
## Git/Graphite Rules

- All `gt` commands include `--no-interactive`.
- All commit messages use heredoc format and include the co-authorship trailer.
- The orchestrator is the ONLY place git/graphite operations happen — sub-agents never commit.
- Never run raw `git` commands when a `gt` equivalent exists.
```

— `.claude/skills/qrspi-work/SKILL.md:632-639`

**Dependencies:** None.
**Implicit contracts:** Strict rules are enforced via prose in the skill body, not via tool-permission narrowing.

## Q8: How do existing skills handle the case where the wrapped CLI is unauthenticated or misconfigured (e.g., expired tokens, missing config) — is there a documented "hard stop" pattern?

**Answer:** Yes — `qrspi-work` has a "HARD STOP: Infrastructure Errors Are Not Puzzles To Solve" section that explicitly forbids workarounds (no `chmod`, no env-var routing, no alternate tools, no `sudo`). The mandate is: print the exact error verbatim and exit. The global `feedback_error_surfacing` memory rule reinforces this.

**Evidence:**

```
### HARD STOP: Infrastructure Errors Are Not Puzzles To Solve

This is a non-negotiable constraint. There is NO exception.

When ANY operation fails due to permissions, authentication, configuration,
or tooling errors (e.g., `EACCES`, `permission denied`, auth token expired,
config file inaccessible, tool not found):

1. **STOP. Do not execute another command.**
2. **Print the exact error verbatim** ...
3. **Exit the skill.**
```

— `.claude/skills/qrspi-work/SKILL.md:709-728`

**Dependencies:** None.
**Implicit contracts:** A new external-CLI skill should adopt the same "hard stop, print error, exit" rule rather than retrying.

## Q9: How do existing skills handle non-interactive / CI versus interactive developer-workstation contexts when the underlying CLI behaves differently between them?

**Answer:** The `qrspi-work` skill always uses `--no-interactive` on `gt` commands. For `gh`, no analogous flag is set explicitly in the skill body, but the devcontainer bind-mounts the host's `~/.config/gh` so authentication is inherited. There is no documented branching on "developer vs CI" in skill bodies — every skill runs as if non-interactive.

**Evidence:**

```
- All `gt` commands include `--no-interactive`.
```

— `.claude/skills/qrspi-work/SKILL.md:634`

```
"source=${localEnv:HOME}/.config/gh,target=/home/vscode/.config/gh,type=bind,readonly"
```

— `.devcontainer/devcontainer.json:40`

**Dependencies:** Devcontainer setup.
**Implicit contracts:** Skills assume a single non-interactive execution mode. Any new skill should default to non-interactive flags and rely on out-of-band auth (env var, bind mount, or pre-existing login).

## Q10: What test conventions, if any, exist for skill content in this repo (the evals harness mentioned in `.claude/CLAUDE.md`), and what does the eval contract look like for a new skill?

**Answer:** The eval contract uses programmatic assertions over markdown output files (e.g., counting sections, validating frontmatter, checking field presence). Each case lives in `evals/suite.json` with: `id`, `name`, `phase`, `prompt`, `context.files`, and a list of `assertions`. The harness is QRSPI-phase-oriented; it does not have generic "skill" cases.

**Evidence:**

```
"assertions": [
  {"type": "programmatic", "check": "output_file_exists('questions.md')", "weight": 1.0},
  {"type": "programmatic", "check": "section_count('questions.md', '## ') >= 5", "weight": 1.0},
  {"type": "programmatic", "check": "question_count('questions.md') >= 8", "weight": 1.0},
  {"type": "programmatic", "check": "all_questions_have_target('questions.md')", "weight": 1.5}
]
```

— `evals/suite.json:26-50`

**Dependencies:** `scripts/grade.py`, `scripts/run_eval.py`.
**Implicit contracts:** Assertions are inspectable strings, parsed and executed by `scripts/grade.py`. A new general-purpose skill would need either a custom assertion grammar or no formal eval.

## Q11: Are there any sample skill evals that exercise an external-CLI wrapping skill (graphite, gh, etc.) that can serve as a template for evaluating this new skill?

**Answer:** `evals/graphite-evals.json` exists — a separate eval suite specifically for the Graphite CLI wrapping skill. Its presence demonstrates that external-CLI skills do get their own eval files alongside `suite.json`. The convention for a new gh-cli skill would be a parallel `evals/gh-evals.json`. The full contents were not read in this research pass.

**Evidence:**

```
evals/
├── graphite-evals.json
├── suite.json
```

— `evals/` directory listing

**Dependencies:** Same runner as `suite.json`.
**Implicit contracts:** External-CLI skills get their own `*-evals.json` file. The pattern suggests a `gh-evals.json` for this ticket's deliverable.

## Q12: Where in the repo are skill versions, changelogs, or commit conventions for skill modifications documented, so that this new skill follows the same revision-tracking pattern?

**Answer:** No separate CHANGELOG file or version field exists per skill. Revision tracking is purely git-based. QRSPI ticket artifacts include a `revision-log.md` template (`.qrspi/templates/revision-log.md`) but that template lives at the ticket artifact level, not the skill level. Recent commit messages (e.g., `63ff906 refactor skills to agents with skills as agent invocation wrapper`, `5c1ab12 qrspi skills read templates rather than inline output formats`) demonstrate that skill changes ship as ordinary refactor/feat commits.

**Evidence:**

```
63ff906 refactor skills to agents with skills as agent invocation wrapper
d2fd397 add readme inspiration note
a8a4f7f eval system doc analysis
cda6247 generate readme content
5c1ab12 qrspi skills read templates rather than inline output formats
```

— `git log --oneline -20` output (current branch)

**Dependencies:** None.
**Implicit contracts:** Skill commits use lowercase descriptive subjects, no scope prefix, no semantic-version tags.

## Q13: How do existing skills surface errors and progress (verbose progress logs, structured output, etc.) so that the new gh-cli skill follows the same observability pattern?

**Answer:** `qrspi-work` mandates "verbose progress" prints between phases (e.g., `Print: "Questions generated. Moving to Research..."`) so the operator can observe. Errors are surfaced by printing the exact failing command and its error output, then exiting. No structured logging facility is used.

**Evidence:**

```
4. Print: "Questions generated. Moving to Research..."
...
3. Print: "Research complete. Moving to Design..."
...
2. **Print the exact error verbatim** — the full command that failed and the full error output, unmodified.
```

— `.claude/skills/qrspi-work/SKILL.md:150,172,718`

**Dependencies:** None.
**Implicit contracts:** Progress messages between sub-steps are mandatory; errors are printed raw, not paraphrased.

---

## Discovered Patterns

- **Skill body structure:** every QRSPI skill opens with a brief role statement, then an "Inputs" or "Workflow context" section, then numbered procedural steps. The new gh-cli skill should follow this shape.
- **Tool whitelisting via `allowed-tools`:** every skill declares an explicit whitelist. The new skill should whitelist `Bash` (for `gh`) plus any other tools (Read, Write, Grep) it actually uses.
- **HEREDOC-with-quoted-delimiter** is the only multi-line body pattern in use.
- **`--json` + `--jq` always paired** for any `gh` JSON output — never raw JSON piped through external tools.
- **Devcontainer pre-configures `gh`** via bind-mount of `~/.config/gh`. The new skill can assume `gh auth status` will succeed in supported environments and must hard-stop if it does not.
- **External CLI wrapper skills get a dedicated eval file** (`evals/<tool>-evals.json`), separate from `suite.json`.
- **No `model:` field in skill frontmatter** — that is reserved for the agent layer (`.claude/agents/*.md`).

## Inconsistencies

- The ticket (in `TICKET_CONTENT`, which I cannot read in this phase) reportedly references the "Anthropic skill builder skill" — no such skill exists locally in `.claude/skills/`. It is a global plugin outside the project repo. The plan/design phase will need to decide whether the new skill is authored manually following the agentskills.io standard, or whether the global skill-creator is invoked out-of-band. NOTE — flagged from the questions phase wording; no in-repo evidence either way.
- `qrspi-work/SKILL.md:6` declares `Agent` in `allowed-tools` as if it were a first-class tool, but the codebase has no other consumer of that token; it appears to be a Claude Code harness primitive consumed only by `qrspi-work` itself. A new skill that does NOT spawn sub-agents should omit `Agent` from its whitelist.
- `qrspi-design/SKILL.md:6` uses fine-grained Bash scoping (`Bash(pwd:*)`); `qrspi-work` uses bare `Bash`. The repo does not document when to prefer one form over the other.
