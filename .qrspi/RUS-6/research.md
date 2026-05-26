# Research — Codebase Map
**Questions source:** questions.md @ 2026-05-26
**Generated:** 2026-05-26T00:00:00Z
**Status:** draft

## Q1: What is the complete file structure and directory layout of each existing skill under `.claude/skills/`, including any `references/`, `scripts/`, or `assets/` subdirectories that exist?

**Answer:** There are 10 skills total under `.claude/skills/`. All skills consist of a single `SKILL.md` file, except `qrspi-work` which also has a `references/` subdirectory with one additional markdown file.

**Directory layout:**

```
.claude/skills/
  qrspi-design/SKILL.md                          (43 lines)
  qrspi-implement/SKILL.md                       (52 lines)
  qrspi-plan/SKILL.md                            (36 lines)
  qrspi-pr/SKILL.md                              (43 lines)
  qrspi-questions/SKILL.md                       (46 lines)
  qrspi-research/SKILL.md                        (57 lines)
  qrspi-structure/SKILL.md                       (41 lines)
  qrspi-ticket/SKILL.md                          (75 lines)
  qrspi-work/SKILL.md                            (500 lines)
    references/review-cascade.md                 (64 lines)
  qrspi-worktree/SKILL.md                        (33 lines)
```

**No `scripts/` or `assets/` subdirectories exist** within any skill.

**Evidence:**

```
$ find .claude/skills -type f | sort
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
.claude/skills find: 1-11

```
$ wc -l .claude/skills/*/SKILL.md
 43 .claude/skills/qrspi-design/SKILL.md
 52 .claude/skills/qrspi-implement/SKILL.md
 36 .claude/skills/qrspi-plan/SKILL.md
 43 .claude/skills/qrspi-pr/SKILL.md
 46 .claude/skills/qrspi-questions/SKILL.md
 57 .claude/skills/qrspi-research/SKILL.md
 41 .claude/skills/qrspi-structure/SKILL.md
 75 .claude/skills/qrspi-ticket/SKILL.md
500 .claude/skills/qrspi-work/SKILL.md
 33 .claude/skills/qrspi-worktree/SKILL.md
926 total
```
.claude/skills wc: 1-11

**Dependencies:** N/A (file system structure question)

**Implicit contracts:** Each skill is self-contained in a single directory. The `qrspi-work` skill is the only one with referenced external documentation (`references/` subdirectory).

---

## Q2: What frontmatter fields does each existing `SKILL.md` contain, and which fields are mandatory versus optional per the agentskills.io standard?

**Answer:** All 10 SKILL.md files use the same set of 6 frontmatter fields, though `qrspi-work` escapes its `description` value with double-quotes (unlike all others which use unquoted values).

**Fields present in every SKILL.md:**

| Field | Present in all 10? | Format |
|---|---|---|
| `name` | Yes | String |
| `description` | Yes | String (qrspi-work quotes it) |
| `command` | Yes | String (slash-prefixed) |
| `argument-hint` | Yes | String in angle brackets |
| `allowed-tools` | Yes | Comma-separated list |
| Missing top-level fields | No `version`, `license`, `trigger` | — |

**Example from qrspi-research:**
```yaml
---
name: qrspi-research
description: Map codebase facts by answering questions from the Questions phase. The feature ticket is intentionally hidden. Use after questions are approved.
command: /qrspi-research
argument-hint: <ticket-id>
allowed-tools: Read, Glob, Grep, Bash(find:*), Bash(wc:*), ...
---
```
.qclaude/skills/qrspi-research/SKILL.md: 1-6

**Example from qrspi-work (quoted description):**
```yaml
---
name: qrspi-work
description: "Single entry point for autonomous QRSPI feature development. Use when the user asks to 'work on' a ticket (e.g., 'work on RUS-42'). Reads the ticket's Linear status, determines the current phase, and executes the appropriate action — planning, implementation, or review response — without manual phase-by-phase invocation. Trigger on any variant of: 'work on <ticket-id>', 'continue <ticket-id>', 'pick up <ticket-id>', or any reference to progressing a QRSPI ticket through its lifecycle."
command: /qrspi-work
argument-hint: <ticket-id>
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, mcp__linear-russelltsherman__get_issue, ...
---
```
.qclaude/skills/qrspi-work/SKILL.md: 1-7

**Fields NOT used by any skill:** `version`, `license`, `icon`, `tags`, `author`, `trigger`, `file-pattern`, `exclude-tools`.

**Mandatory vs optional:** Based on the codebase evidence, the 5 fields present in ALL skills that are clearly functional requirements are:
- **name** — maps to skill directory name and is used by eval harness (`load_skill(skill_path)`)
- **description** — the description shown in CLAUDE.md index
- **command** — the slash-command trigger
- **argument-hint** — tells the user what argument format to expect
- **allowed-tools** — constrains which tools the agent can use within this skill

Without the agentskills.io standard spec in this repo, the mandatory/optional distinction cannot be confirmed from codebase alone.

**Dependencies:** N/A

---

## Q3: How does the CLAUDE.md project config register skills and enable auto-invocation, and what mechanism maps a command (e.g., `/qrspi-research`) to a specific skill directory?

**Answer:** CLAUDE.md registers skills through a **bulleted list under a "Available skills" section**. The mapping from command to skill directory follows a naming convention:

```
command: /qrspi-research    ->  .claude/skills/qrspi-research/SKILL.md
command: /qrspi-implement   ->  .claude/skills/qrspi-implement/SKILL.md
```

The command value in frontmatter (`command: /qrspi-<name>`) matches the directory name under `.claude/skills/`. CLAUDE.md lists each skill with the format:

```markdown
### Available skills (invoke with / or let Claude auto-invoke)

- `/qrspi-ticket <initial description>` — Create a Linear issue through guided conversation
- `/qrspi-questions <ticket-id>` — Generate 8-15 targeted technical questions from a feature ticket
- `/qrspi-research <ticket-id>` — Map the codebase (ticket is hidden from this phase)
```
.claude/CLAUDE.md: 17-26

**There is no explicit registry, mapping table, or code mechanism** that connects the command to the skill directory. The harness must infer this relationship — either by:
1. Extracting the command prefix from frontmatter and matching it to a directory name
2. Scanning `.claude/skills/*/SKILL.md` files and parsing frontmatter to build the index

The CLAUDE.md "Available skills" list is **human-readable documentation**, not machine-readable configuration. Skills are not defined as JSON entries or in settings.

**Implicit contract:** The CLAUDE.md list must be kept in sync with the actual skill directories. Adding a new directory under `.claude/skills/` without updating CLAUDE.md would mean the skill exists but is not discoverable from the project config.

**Dependencies:** The CLAUDE.md is at `.claude/CLAUDE.md` in the project root. The skills live at `.claude/skills/<name>/SKILL.md`.

---

## Q4: What is the minimum set of frontmatter fields (name, description, command, argument-hint, allowed-tools) and which must be present for an agent skill to load successfully?

**Answer:** Based on the codebase, the eval harness (`run_eval.py`) does **not** read frontmatter at all — it reads the entire SKILL.md as raw text:

```python
def load_skill(skill_path: str) -> str:
    """Load the agent prompt / skill text."""
    with open(skill_path) as f:
        return f.read()
```
scripts/run_eval.py:61-64

The harness does not validate frontmatter. It treats the entire file content as the agent prompt.

However, the **functional requirements** inferred from the existing skills are:

| Field | Purpose | Evidence of requirement |
|---|---|---|
| `name` | Identifies the skill (matches directory) | All 10 skills have it |
| `command` | Slash-command trigger | All 10 skills have it, starts with `/` |
| `allowed-tools` | Tool access control | All 10 skills have it |
| `argument-hint` | User guidance | All 10 skills have it |
| `description` | Display text | All 10 skills have it |

The eval harness validates `suite.json` structure (not frontmatter):
```python
required = {"name", "cases"}
missing = required - set(suite.keys())
if missing:
    raise ValueError(f"Suite missing required fields: {missing}")
```
scripts/run_eval.py:47-50

**Cannot determine from codebase:** Whether the harness will fail to load a skill with missing frontmatter, or whether frontmatter is silently stripped before the agent prompt is processed. The eval harness bypasses the harness entirely and reads files directly.

**Dependencies:** `scripts/run_eval.py:61-64` loads skills as raw text. The harness registration logic (which parses frontmatter) is not present in the codebase.

---

## Q5: How are the `allowed-tools` values scoped -- are they workspace-wide or per-skill, and what happens when a skill references a tool that is not listed?

**Answer:** The `allowed-tools` values are **per-skill**, stored in each SKILL.md's frontmatter.

**Per-skill scoping evidence:**

```yaml
# qrspi-research
allowed-tools: Read, Glob, Grep, Bash(find:*), Bash(wc:*), Bash(curl:*), mcp__linear-russelltsherman__prepare_attachment_upload, mcp__linear-russelltsherman__create_attachment_from_upload

# qrspi-ticket
allowed-tools: Read, Glob, Grep, Write, Bash, mcp__linear-russelltsherman__save_issue

# qrspi-work
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, mcp__linear-russelltsherman__get_issue, mcp__linear-russelltsherman__get_issue_status, mcp__linear-russelltsherman__save_issue, mcp__linear-russelltsherman__list_issue_statuses, mcp__linear-russelltsherman__prepare_attachment_upload, mcp__linear-russelltsherman__create_attachment_from_upload
```
.claude/skills/*/SKILL.md frontmatter

Each skill lists only the tools it needs. This is a **scope-limiting** pattern — the harness should enforce that an agent running a skill can only use the tools listed in that skill's `allowed-tools`.

**Tool naming conventions observed:**
- Built-in tools: `Read`, `Write`, `Edit`, `Glob`, `Grep`, `Agent`, `Bash`
- Bash with glob restrictions: `Bash(find:*), Bash(wc:*), Bash(curl:*), Bash(git diff:*), Bash(git log:*)`
- MCP tools: `mcp__linear-russelltsherman__<method>`
- `qrspi-implement` uses bare `Bash` (no glob filter) — the most permissive skill

**Cannot determine from codebase:** What happens when a skill references an unlisted tool. The enforcement mechanism (harness-level blocking, warning, or silent failure) is not implemented in the codebase.

**Implicit contract:** The `allowed-tools` list should be a superset of all tools actually called in the skill's instructions. For example, `qrspi-research` lists `Bash(find:*), Bash(wc:*)` and its instructions call `wc -c` (line 52), but does not call `find`.

---

## Q6: What scope does the `$ARGUMENTS` variable have -- is it passed per-invocation from CLAUDE.md, cached across calls, or parsed from the command string by the harness?

**Answer:** `$ARGUMENTS` is **passed per-invocation from the command string**. It is not cached.

**Evidence from skill instructions — all skills parse `$ARGUMENTS` at entry:**

```yaml
# qrspi-questions: argument-hint: <ticket-id>
Parse $ARGUMENTS to extract <ticket-id>.
```
.qclaude/skills/qrspi-questions/SKILL.md: 11

```yaml
# qrspi-implement: argument-hint: <ticket-id> <slice-number>
Parse $ARGUMENTS to extract <ticket-id> and <slice-number>.
```
.qclaude/skills/qrspi-implement/SKILL.md: 11

```yaml
# qrspi-work: argument-hint: <ticket-id>
Parse `$ARGUMENTS` to extract `<ticket-id>`.
```
.qclaude/skills/qrspi-work/SKILL.md: 15

**Usage pattern:** `$ARGUMENTS` is used as a runtime substitution variable. When the user invokes `/qrspi-research RUS-6`, the harness replaces `$ARGUMENTS` with `RUS-6` before feeding the prompt to the agent.

The variable is used throughout instructions for path construction:
- `.qrspi/$ARGUMENTS/questions.md`
- `.qrspi/$ARGUMENTS/research.md`
- `mcp__linear-russelltsherman__save_issue` with `id: "$ARGUMENTS"`

**Evidence of per-invocation scope:** Each skill treats `$ARGUMENTS` as a fresh value at the start of execution. There is no caching or session-level persistence. The `/qrspi-implement RUS-6 1` skill parses two values from the same `$ARGUMENTS` string.

**Dependencies:** Upstream: CLAUDE.md command registration. Downstream: skill instructions parse and use the value.

**Implicit contracts:** The argument format must match the skill's `argument-hint`. For single-value skills, `$ARGUMENTS` = ticket-id. For two-value skills like implement, `$ARGUMENTS` = "RUS-6 1".

---

## Q7: Are there any environment variables, config files, or session state that skills can read at runtime, and how is skill isolation enforced between parallel invocations?

**Answer:** Based on the codebase, skills have **no direct access to environment variables or config files** beyond the project directory.

**Isolation mechanisms observed:**

1. **Session isolation via `/clear`:** CLAUDE.md instructs: "Start a fresh `/clear` session between implementation slices." This resets agent context.
.claude/CLAUDE.md: 35

2. **Context firewalls within skills:**
   - `qrspi-research` explicitly forbids reading the ticket: "CRITICAL: Do NOT read the ticket."
   - `qrspi-implement` limits reads: "Read ONLY these files" (4 files max)
   - `qrspi-work` enforces: "Do NOT read the full design, full plan, or earlier slice details beyond the notes."
   - `qrspi-work` sub-agent rules: "Sub-agents must not read, explore, or reference files outside the project."
.claude/skills/qrspi-research/SKILL.md: 13
.claude/skills/qrspi-implement/SKILL.md: 13-19
.claude/skills/qrspi-work/SKILL.md: 408-424

3. **Sub-agent isolation:** `qrspi-work` spawns sub-agents with only specific inputs, not full context:
   - Research sub-agent gets questions.md but NOT ticket content
   - Implement sub-agent gets ONLY its slice's sections, not full artifacts
.claude/skills/qrspi-work/SKILL.md: 217-222

**No environment variables are referenced** in any skill. The only external system accessed is Linear via MCP tools (`mcp__linear-russelltsherman__*`).

**Cannot determine from codebase:** Whether the harness enforces parallel invocation isolation at the process/container level. Skills that reference `.qrspi/<ticket-id>/` paths could theoretically conflict if two skills for different tickets run simultaneously on the same filesystem.

---

## Q8: What happens when two skills define the same command prefix (e.g., `/gt` vs `/gtx`) -- how does the auto-invocation resolver disambiguate?

**Answer:** The codebase has **no disambiguation logic** implemented. All 10 skills use unique command prefixes (`/qrspi-*`), so there is no collision in the current codebase.

**Command values in all skills:**

| Skill | Command |
|---|---|
| qrspi-ticket | `/qrspi-ticket` |
| qrspi-questions | `/qrspi-questions` |
| qrspi-research | `/qrspi-research` |
| qrspi-design | `/qrspi-design` |
| qrspi-structure | `/qrspi-structure` |
| qrspi-plan | `/qrspi-plan` |
| qrspi-worktree | `/qrspi-worktree` |
| qrspi-implement | `/qrspi-implement` |
| qrspi-pr | `/qrspi-pr` |
| qrspi-work | `/qrspi-work` |

**No codebase mechanism for disambiguation was found.** There is no skill registry, no dispatch table, no resolver logic in the scripts or evals.

**Inference from CLAUDE.md:** The phrase "invoke with / or let Claude auto-invoke" (line 17) suggests two modes:
1. **Manual invocation:** User types `/qrspi-implement RUS-6 1` — the harness matches by exact command string
2. **Auto-invocation:** Claude decides to invoke based on the `description` field — disambiguation would be a language-model decision, not a code-level one

**Cannot determine from codebase:** The auto-invocation resolver lives in the Claude Code harness, not in this project. Collision behavior is undefined.

---

## Q9: If a skill references files outside its own directory (e.g., `.qrspi/<ticket-id>/`), what happens when that target path does not exist yet -- does the skill fail silently, produce an error, or create the path?

**Answer:** Skills **produce errors** when target paths do not exist. The harness `Read` tool will fail with an error if the file does not exist. Skills themselves do not create directories or files at those paths.

**Evidence from qrspi-work orchestrator (creation of directories):**

The only skill that creates `.qrspi/<ticket-id>/` directories is `qrspi-work` (the orchestrator), and it explicitly creates them:
```bash
gt create <ticket-id>/planning --no-interactive -m "..."
# Creates .qrspi/<ticket-id>/questions.md
```
.qclaude/skills/qrspi-work/SKILL.md: 68-74

**Skill behavior (not orchestrator):** A skill like `qrspi-research` instructs "Read `.qrspi/$ARGUMENTS/questions.md`" but does NOT create it. The file must already exist (produced by the questions phase).

**Evidence from template files:** Template files exist at `.qrspi/templates/*.md` but the instructions say "(reference only -- not written locally)". So templates are **not** used to auto-create artifacts.
.claude/CLAUDE.md: 42

**Error behavior:** When the `Read` tool encounters a non-existent file, the agent receives an error. Skills do not have try/catch patterns — they assume prerequisites exist and stop on failure.

**Implicit contract:** Skills form a **pipeline** where each phase's output is the next phase's input. Reading a non-existent file means the pipeline was broken at an earlier phase.

---

## Q10: The ticket specifies SKILL.md body under 500 lines / 5000 tokens -- is this enforced by the harness or is it a human-review gate? What happens to a skill that exceeds this limit?

**Answer:** The limit is a **human-review gate**, not enforced by the harness. One skill already exceeds it:

**Line counts:**

| Skill | Lines | Under 500? |
|---|---|---|
| qrspi-worktree | 33 | Yes |
| qrspi-plan | 36 | Yes |
| qrspi-design | 43 | Yes |
| qrspi-pr | 43 | Yes |
| qrspi-structure | 41 | Yes |
| qrspi-ticket | 75 | Yes |
| qrspi-questions | 46 | Yes |
| qrspi-implement | 52 | Yes |
| qrspi-research | 57 | Yes |
| **qrspi-work** | **500** | **Boundary** |

.qclaude/skills wc output: 1-11

The `qrspi-work` skill is exactly at 500 lines (the boundary of the stated limit). This is the orchestrator skill that coordinates all other phases.

**No enforcement mechanism found.** The eval harness (`grade.py`, `run_eval.py`) does not have any check for skill file length. The `line_count` check function in `grade.py` is only used for **artifacts** (design.md, questions.md), not for skill definitions:

```python
def line_count(filename: str, max_lines: int, result: dict) -> tuple[bool, str]:
    """Check that output is within line limit."""
    output = result.get("output", "")
    count = len(output.splitlines())
    ...
```
scripts/grade.py:35-40

**Cannot determine:** Token-level enforcement. The 5000-token limit would require actual tokenization to check — no codebase tool does this.

---

## Q11: Is there an eval harness or testing mechanism for skills (e.g., `evals/` directory), and has any existing skill been evaluated with a benchmark or regression test suite?

**Answer:** Yes, there is a **sophisticated but partially stubbed eval harness**. It exists in `evals/` and `scripts/` but the LLM judge and script-based assertions are **not yet integrated** (return `passed: null`).

**Eval suite structure:**

```
evals/
  suite.json           — 15 test cases across all QRSPI phases
  graphite-evals.json  — 5 test cases for Graphite CLI commands
  fixtures/            — 4 ticket fixture files
  golden/              — empty (.gitkeep)
```
evals structure

**Eval scripts (all Python):**

```
scripts/
  run_eval.py    — Execute suite, run trials, capture results
  grade.py       — Run assertions, compute weighted scores
  report.py      — Generate iteration reports, detect regressions
  diagnose.py    — Categorize failures, suggest fixes
  revise.py      — Apply targeted skill revisions
  check_scope.py — Verify implementation stayed within allowed scope
```
scripts/: 1-7

**suite.json structure:**
```json
{
  "name": "qrspi-agent-evals",
  "version": "0.1.0",
  "split": { "train_ratio": 0.65, "test_ratio": 0.35, "seed": 42 },
  "defaults": { "trials_per_case": 3, "timeout_ms": 120000, "max_tokens": 128000 },
  "cases": [15 test cases]
}
```
evals/suite.json: 1-14

**Test case categories by phase:**
- `questions`: cases 001, 002, 015 (happy-path, complex, adversarial)
- `research`: cases 003, 004 (factual accuracy, NOT FOUND handling)
- `design`: cases 005, 006, 014 (citations, new pattern, plan-reading illusion)
- `structure`: cases 007, 008 (vertical slices, large feature splitting)
- `plan`: case 009 (atomicity)
- `worktree`: case 010 (session boundaries)
- `implement`: cases 011, 012 (scope enforcement, deviation reporting)
- `pr`: case 013 (acceptance criteria mapping)

**Assertion types used:**
- `programmatic` — regex checks against output text (8 registered check functions in grade.py)
- `llm_judge` — subjective quality assessment (stub: `passed: null`)
- `script` — external script execution (stub: `passed: null`)

**Graphite evals** (`graphite-evals.json`) are separate — 5 test cases for Graphite CLI behavior with assertions on command usage, flags, and safety checks.

**Not yet evaluated:** No results files exist in `results/` (only `.gitkeep`). No skill has been run through the eval harness.

**Dependencies:** Upstream: evals/suite.json defines tests. Downstream: scripts/run_eval.py executes, scripts/grade.py grades, scripts/report.py reports.

---

## Q12: Are there integration tests that validate a skill actually loads and executes its instructions when invoked with a command like `/qrspi-implement`?

**Answer:** **No integration tests exist.** The eval harness is designed for evaluation but has never been executed. The `results/` directory is empty (only `.gitkeep`).

**What exists instead:**

1. **Fixture files** that represent ticket content for test cases:
   ```
   evals/fixtures/
     ticket_rest_endpoint.md
     ticket_multi_tenancy.md
     ticket_websocket.md
     ticket_15_acceptance_criteria.md
   ```
   evals/fixtures: 1-5

2. **Template files** that define expected output structure:
   ```
   .qrspi/templates/
     questions.md, research.md, design.md, structure.md, plan.md,
     worktree.md, impl-log.md, pr-summary.md, ticket.md, revision-log.md
   ```
   templates: 1-11

3. **Programmatic check functions** in `grade.py` that validate output structure:
   - `output_file_exists` — file was produced
   - `has_section` — markdown section exists
   - `line_count` — under max lines
   - `no_solution_language` — regex ban
   - `current_state_has_citations` — (ref: QN) citations
   - `no_code_blocks` — no markdown code blocks
   - etc.
   scripts/grade.py: 146-157

4. **Scope checking** — `check_scope.py` compares impl-log against allowed files

**What does NOT exist:**
- No test that invokes `/qrspi-implement RUS-6 1` end-to-end
- No test that verifies the harness loads a SKILL.md, parses frontmatter, and dispatches
- No integration test connecting CLAUDE.md command dispatch to skill execution
- No CI pipeline configuration

**Inference:** The eval harness is a **one-shot evaluation tool** — you run it manually against a skill version, get scores, diagnose failures, and iterate. It is not set up as continuous integration tests.

---

## Q13: When a skill fails to load (e.g., bad frontmatter, missing SKILL.md, syntax error in allowed-tools), what does the agent see in the console -- a silent skip, an error message, or a warning?

**Answer:** **This cannot be determined from the codebase.** The skill loading/dispatch logic lives in the Claude Code harness, which is external to this project.

**What can be inferred:**

1. The eval harness (`run_eval.py`) reads SKILL.md files directly and will **raise FileNotFoundError** if the file is missing:
   ```python
   def load_skill(skill_path: str) -> str:
       with open(skill_path) as f:
           return f.read()
   ```
   scripts/run_eval.py:61-64

2. The eval harness **does not validate frontmatter** at all — it reads the entire file as raw text.

3. The `suite.json` validation in the eval harness will raise a `ValueError` if required fields are missing:
   ```python
   if missing:
       raise ValueError(f"Suite missing required fields: {missing}")
   ```
   scripts/run_eval.py:49-50

4. The CLAUDE.md lists skills as a human-readable index. If a skill is listed in CLAUDE.md but the SKILL.md file is missing or has bad frontmatter, behavior is determined by the harness — not this codebase.

**Cannot determine:** The exact console output when the Claude Code harness encounters a bad skill file. This behavior is in the proprietary Claude Code runtime.

**Evidence of defensive coding in skills themselves:** Skills that upload artifacts include error handling:
```
If any upload step fails, report the error but do NOT fail the phase — the local artifact is already written.
```
.claude/skills/*/SKILL.md upload sections (all 10 skills)

This pattern suggests a "fail gracefully" philosophy but applies to runtime operations, not skill loading.

---

## Discovered Patterns

1. **Standard artifact format:** All QRSPI artifacts (questions.md, research.md, design.md, etc.) follow a consistent format with frontmatter metadata (Title, Ticket, Generated, Status) and sectioned content. Templates enforce this at `.qrspi/templates/<artifact>.md`.

2. **Upload pattern is identical across skills:** Every skill that produces an artifact uses the same 4-step Linear upload sequence: wc -c -> prepare_attachment_upload -> curl PUT -> create_attachment_from_upload. The pattern is DRY-violated (copy-pasted) across 10 files instead of being abstracted.

3. **Progressive permission model:** Skills grant increasing levels of tool access:
   - Read-only skills (worktree, plan, structure): Read, Bash(wc:*), Bash(curl:*)
   - Read-write skills (implement, ticket, work): Read/Write/Edit/Bash
   - MCP-extended skills: All internal tools + specific MCP calls

4. **Bash glob restrictions:** When Bash access is restricted, it uses glob patterns (`Bash(find:*), Bash(wc:*)`). When unrestricted, it uses bare `Bash`. The `qrspi-implement` and `qrspi-work` skills use bare `Bash` — this is the most permissive.

5. **Context firewall pattern:** Multiple skills implement "firewalls" to limit what the agent sees:
   - Research: hidden from ticket content
   - Implement: limited to 4 specific files
   - Sub-agents: scoped to project directory only

6. **Template-artifact separation:** Templates at `.qrspi/templates/` are for reference only (CLAUDE.md states "not written locally"). The actual artifacts are written directly at `.qrspi/<ticket-id>/.`

7. **Split ratio convention:** The eval suite uses 65/35 train/test split with seed 42 — a standard ML evaluation pattern.

8. **Weighed assertions:** Eval assertions use weighted scoring (0.5 to 3.0) with higher weights for LLM-judged quality checks vs. programmatic checks.

## Inconsistencies

1. **Template vs. actual output format mismatch:** The research.md template at `.qrspi/templates/research.md` uses a `---` separator between Q2 and the Discovered Patterns section, but the research SKILL.md instruction and the questions.md do not show this separator. The template format may not match what skills actually instruct.

2. **`qrspi-work` at exactly 500 lines:** The ticket's stated limit is "under 500 lines" but `qrspi-work` is exactly 500 lines. This is either intentional boundary-pushing or a violation of the constraint.

3. **Description quoting inconsistency:** `qrspi-work` wraps its `description` value in double-quotes while all other skills use unquoted values. If the harness strips quotes, this has no effect, but it is a stylistic inconsistency.

4. **Missing fixture for questions output:** The eval suite references fixture files like `fixtures/questions_rest_endpoint.md` and `fixtures/research_rest_endpoint.md` in the `context.files` arrays, but these files do not exist in `evals/fixtures/`. Only 4 ticket fixtures exist. This means 11 of 15 eval cases reference missing fixture files.

5. **CLAUDE.md version mismatch:** The CLAUDE.md at the project root (`/workspaces/qrspi/.claude/CLAUDE.md`) has an older artifact upload pattern (artifacts are "uploaded to the corresponding Linear issue as attachments on phase approval") while the root-level CLAUDE.md says "Artifacts are stored locally in `.qrspi/<ticket-id>/`" without mentioning uploads. The skill files themselves contain the upload instructions.

6. **Eval harness empty at runtime:** The `results/` directory contains only `.gitkeep` — no actual evaluation results exist. The harness infrastructure is complete (15 test cases, 6 scripts) but has never been run.

7. **Programmatic check registry is incomplete:** `grade.py` defines `CHECKS` dict with 8 functions, but suite.json references check functions like `section_question_count`, `all_slices_have_context_cost`, `no_slice_exceeds_file_limit`, `all_files_marked_new_or_modify`, `has_critical_path`, `all_tasks_have_required_fields` that are NOT implemented in the `CHECKS` registry. These checks will return `"passed": null` with `"Unknown check function"` evidence.
