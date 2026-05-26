# Research — Codebase Map
**Questions source:** questions.md @ 2026-05-26T01:15:00Z
**Generated:** 2026-05-26T03:45:00Z
**Status:** draft

## Q1: What is the agentskills.io standard directory structure for a skill, and what files are required vs optional (`SKILL.md`, `references/`, `scripts/`, `assets/`)?

**Answer:** In this codebase, each skill lives in its own directory under `.claude/skills/<skill-name>/`. The only universally present file is `SKILL.md`. There are 10 skill directories total. Only one skill (`qrspi-work`) has a `references/` subdirectory containing one file (`review-cascade.md`). No skill in this codebase has a `scripts/` or `assets/` subdirectory. There is no explicit schema or spec file defining required vs optional contents -- the convention is established purely by existing practice.

**Evidence:**
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
├── qrspi-work/SKILL.md
├── qrspi-work/references/review-cascade.md
└── qrspi-worktree/SKILL.md
```
-- `find .claude/skills -type f` output

**Dependencies:** Claude Code runtime discovers skills by scanning `.claude/skills/*/SKILL.md` (directory convention, not a registry file).

**Implicit contracts:** A skill directory must contain exactly one `SKILL.md`. The `references/` directory is optional and used for supplementary material that the skill body references (e.g., cascade logic). No other subdirectory names (`scripts/`, `assets/`) are used in existing skills.

---

## Q2: What frontmatter fields does a valid `SKILL.md` require according to the agentskills.io standard, and what are valid values for each?

**Answer:** Every `SKILL.md` in this codebase uses YAML frontmatter delimited by `---`. The fields observed across all 10 skills are:

| Field | Required? | Values observed |
|-------|-----------|-----------------|
| `name` | Yes (all 10 have it) | Kebab-case string matching directory name (e.g., `qrspi-design`) |
| `description` | Yes (all 10 have it) | Free-form string, quoted when containing special characters. Ranges from 71 chars (`qrspi-plan`) to 342 chars (`qrspi-work`). Describes trigger conditions. |
| `command` | Yes (all 10 have it) | Slash-prefixed string matching `/<name>` (e.g., `/qrspi-design`) |
| `argument-hint` | Yes (all 10 have it) | Angle-bracket placeholder (e.g., `<ticket-id>`, `<ticket-id> <slice-number>`, `<initial description>`) |
| `allowed-tools` | Yes (all 10 have it) | Comma-separated list of tool names. Bash permissions use glob syntax: `Bash(wc:*)`, `Bash(find:*)`, `Bash(git diff:*)`. Unrestricted Bash is just `Bash`. |

**Evidence:**
```yaml
# qrspi-research/SKILL.md:1-7
---
name: qrspi-research
description: Map codebase facts by answering questions from the Questions phase. The feature ticket is intentionally hidden. Use after questions are approved.
command: /qrspi-research
argument-hint: <ticket-id>
allowed-tools: Read, Glob, Grep, Bash(find:*), Bash(wc:*), Bash(head:*), Bash(tail:*), Bash(curl:*), mcp__linear-russelltsherman__prepare_attachment_upload, mcp__linear-russelltsherman__create_attachment_from_upload
---
```
-- `.claude/skills/qrspi-research/SKILL.md:1-7`

**Dependencies:** The `allowed-tools` field scopes the skill's permissions. Skills that need external API access include MCP tool names. Skills that need file mutation include `Write` and `Edit`.

**Implicit contracts:** The `name` field matches the directory name. The `command` field is `/<name>`. The `description` field doubles as a trigger description -- it tells Claude when to auto-invoke the skill. MCP tool names follow the pattern `mcp__<server>__<tool>`.

---

## Q3: How does the Anthropic skill builder skill (`skill-creator`) expect input, and what is the sequence of operations it performs to produce a new skill?

**Answer:** The `skill-creator` skill does not exist as a `SKILL.md` file within this codebase. It is listed in the system-reminder as a Claude Code built-in skill available globally:

> "skill-creator: Create new skills, modify and improve existing skills, and measure skill performance. Use when users want to create a skill from scratch, edit, or optimize an existing skill, run evals to test a skill, benchmark skill performance with variance analysis, or optimize a skill's description for better triggering accuracy."

No local file defines its behavior, input format, or operational sequence. The structure SKILL.md references it indirectly in rule 9:

```
9. Validation passes (linting, running a review tool, invoking skill-creator) are the final step of the slice that produced the files — not a separate slice.
```
-- `.claude/skills/qrspi-structure/SKILL.md:29`

**Evidence:** Search queries attempted:
- `find .claude/skills -name 'skill-creator' -type d` -- no results
- `grep -r "skill-creator" --include="*.md" --include="*.json"` -- found only in `qrspi-structure/SKILL.md:29` and `questions.md`

**Dependencies:** The `skill-creator` is a platform-provided capability, not a project artifact. Its internal logic is not inspectable from this codebase.

**Implicit contracts:** The structure skill assumes `skill-creator` can be invoked as a validation step after skill files are produced.

---

## Q4: When the ticket says "Detailed reference material in references/ directory if needed," what format and structure do existing skills use for their `references/` content?

**Answer:** Only one skill (`qrspi-work`) has a `references/` directory. It contains a single file: `review-cascade.md` (64 lines, plain markdown). The file is structured as:

1. A title (`# Review Cascade Logic`)
2. A prose explanation of the dependency chain: `Questions -> Research -> Design -> Structure -> Plan -> Work Tree`
3. A `## Cascade Rules` section with sub-sections: "Identify the earliest affected artifact", "Determine cascade depth" (with a table), "Re-running a downstream phase", "Commit strategy", "Example"

The orchestrator (`qrspi-work/SKILL.md`) explicitly references this file at line 175:

```
c. Read `references/review-cascade.md` for cascade logic.
```
-- `.claude/skills/qrspi-work/SKILL.md:175`

**Evidence:**
```markdown
# Review Cascade Logic

When planning review feedback requires changes to an artifact, downstream artifacts
may be invalidated. The planning artifacts form a dependency chain:

Questions → Research → Design → Structure → Plan → Work Tree

## Cascade Rules
### Identify the earliest affected artifact
...
### Determine cascade depth
| Change type | Cascade? |
|---|---|
| Typo, wording fix, clarification | No cascade — fix only the targeted artifact |
...
```
-- `.claude/skills/qrspi-work/references/review-cascade.md:1-30`

**Dependencies:** The reference file is consumed only by the `qrspi-work` orchestrator during the "Plan Review -> Address Feedback" state.

**Implicit contracts:** Reference files are plain markdown. They are loaded by explicit `Read` instructions in the skill body, not auto-loaded. The skill body must tell the agent when and why to read the reference.

---

## Q5: What CLI command groups does the `argo` binary expose (submit, list, get, logs, watch, delete, cron, lint, retry, resubmit, stop, terminate, suspend, resume), and are there any additional groups not mentioned in the ticket that a comprehensive skill must cover?

**Answer:** NOT FOUND. The `argo` CLI binary is not installed in this environment.

```
$ which argo
argo not found
```

No files in this codebase reference the `argo` CLI, contain Argo Workflow manifests, or document Argo command groups. The codebase is exclusively focused on the QRSPI workflow framework and its agent skills.

Search queries attempted:
- `which argo` -- not found
- `grep -r "argo" --include="*.md" --include="*.json" --include="*.yaml" --include="*.yml"` -- no hits outside questions.md
- `find . -name '*.yaml' -o -name '*.yml'` -- no workflow manifests found

**Dependencies:** None in this codebase.

**Implicit contracts:** N/A -- the argo CLI surface area must be researched from external documentation or a system with argo installed.

---

## Q6: How do existing agent skills in this project structure their SKILL.md body to stay under the 500-line / 5000-token acceptance criterion while still covering a broad CLI surface?

**Answer:** The 10 existing skills range from 33 to 500 lines and 241 to 3,051 words. None of the per-phase skills exceeds 75 lines. Only the orchestrator (`qrspi-work`) reaches 500 lines / 3,051 words / 22,312 bytes.

| Skill | Lines | Words | Bytes |
|-------|-------|-------|-------|
| qrspi-worktree | 33 | 241 | 1,881 |
| qrspi-plan | 36 | 254 | 1,955 |
| qrspi-structure | 41 | 438 | 3,180 |
| qrspi-design | 43 | 335 | 2,698 |
| qrspi-pr | 43 | 298 | 2,341 |
| qrspi-questions | 46 | 296 | 2,338 |
| qrspi-implement | 52 | 445 | 3,351 |
| qrspi-research | 57 | 321 | 2,634 |
| qrspi-ticket | 75 | 388 | 2,609 |
| qrspi-work | 500 | 3,051 | 22,312 |

Structural patterns used to stay compact:

1. **Numbered rules** -- concise imperatives, not explanations (e.g., "No code blocks. Prose and tables only." at `qrspi-design/SKILL.md:27`)
2. **Output format as a fenced template** -- shows structure without explaining each field (e.g., `qrspi-research/SKILL.md:27-44`)
3. **Separation of concerns** -- complex logic is offloaded to `references/` files (e.g., cascade logic in `qrspi-work/references/review-cascade.md`)
4. **No inline examples** -- no worked examples in any per-phase skill body
5. **Upload boilerplate** -- identical 6-line upload section appended to most skills, using a consistent pattern

**Evidence:**
```
$ wc -l .claude/skills/*/SKILL.md
  43 qrspi-design/SKILL.md
  52 qrspi-implement/SKILL.md
  36 qrspi-plan/SKILL.md
  ...
 500 qrspi-work/SKILL.md
 926 total
```

The 500-line guidance appears in `docs/qrspi_claude_code_guide.md:592`:
```
The skill prompt may be too long. Check that each SKILL.md is under 500 lines
and under ~40 distinct instructions. The instruction budget ceiling is real.
```
-- `docs/qrspi_claude_code_guide.md:592`

**Dependencies:** N/A

**Implicit contracts:** Per-phase skills stay under ~75 lines. Only the orchestrator approaches the 500-line ceiling. Broad CLI surface coverage is not demonstrated by any existing skill -- all skills in this codebase are workflow/document-generation skills, not CLI-wrapping skills.

---

## Q7: How does the skill-creator skill track progress across its generation phases -- does it produce intermediate artifacts, require user approval between steps, or run to completion in one pass?

**Answer:** NOT FOUND within this codebase. The `skill-creator` is a Claude Code platform built-in, not a project-level skill. Its internal phasing logic is not accessible from the project files. The system-reminder description states it supports: "create a skill from scratch, edit, or optimize an existing skill, run evals to test a skill, benchmark skill performance with variance analysis, or optimize a skill's description for better triggering accuracy."

No local configuration, hook, or settings file modifies or extends the `skill-creator` behavior.

Search queries attempted:
- `find . -path '*skill-creator*'` -- no results
- `grep -r "skill-creator" --include="*.md" --include="*.json"` -- only `qrspi-structure/SKILL.md:29` and `questions.md`

**Dependencies:** Platform-level dependency. Not inspectable.

**Implicit contracts:** Unknown from codebase alone.

---

## Q8: Where in the project are skills registered so that Claude Code can discover and invoke them (e.g., `.claude/settings.json`, a skills index, or directory convention)?

**Answer:** Skills are discovered by directory convention alone. There is no `settings.json`, `settings.local.json`, or skill registry file anywhere in `.claude/`.

```
$ find .claude -name 'settings.json' -o -name 'settings.local.json'
(no results)
```

The convention is: any directory under `.claude/skills/` that contains a `SKILL.md` file is automatically discovered by Claude Code. This is documented in `.claude/CLAUDE.md`:

```markdown
### Available skills (invoke with / or let Claude auto-invoke)
- `/qrspi-ticket <initial description>` — Create a Linear issue...
- `/qrspi-questions <ticket-id>` — Generate technical questions...
```
-- `.claude/CLAUDE.md:12-20`

And in `docs/qrspi_claude_code_guide.md:17-28`:
```
├── .claude/
│   ├── CLAUDE.md
│   └── skills/
│       ├── qrspi-questions/
│       │   └── SKILL.md
```

**Evidence:** No `settings.json` exists. The 10 skills are all discovered from `.claude/skills/*/SKILL.md`.

**Dependencies:** Claude Code runtime must scan `.claude/skills/` on session start.

**Implicit contracts:** The `CLAUDE.md` file lists skills for human reference, but discovery is automatic. The `name` field in frontmatter must match the directory name. The `command` field defines the slash-command syntax.

---

## Q9: What happens when the skill body exceeds the 500-line / 5000-token limit -- does the skill-creator enforce this constraint, or must it be validated separately?

**Answer:** The 500-line limit is mentioned only as troubleshooting guidance in `docs/qrspi_claude_code_guide.md:592`:

```
The skill prompt may be too long. Check that each SKILL.md is under 500 lines
and under ~40 distinct instructions. The instruction budget ceiling is real.
```

There is no automated enforcement in this codebase. No pre-commit hook, CI check, or eval assertion validates SKILL.md size. The eval suite (`evals/suite.json`) does not include any assertion checking skill file size. The `scripts/` directory contains `run_eval.py`, `grade.py`, `diagnose.py`, `revise.py`, `report.py`, and `check_scope.py` -- none check skill file size.

The `skill-creator` is a platform built-in whose internal validation logic is not inspectable from this codebase.

**Evidence:**
```
$ grep -r "500" scripts/ --include="*.py"
(no results for line-count validation)

$ grep -r "wc -l" scripts/ --include="*.py"
(no results)
```

**Dependencies:** None -- this is an unenforced guideline.

**Implicit contracts:** The largest existing skill (`qrspi-work`) is exactly 500 lines, hitting the documented ceiling. This suggests the 500-line limit is a soft constraint respected by authors, not enforced by tooling.

---

## Q10: How does the skill handle the case where `argo` CLI is not installed or not on the PATH in the agent's environment -- do existing skills include prerequisite checks or guards?

**Answer:** No existing skill in this codebase includes prerequisite checks for external CLI tools. No skill checks `which`, `command -v`, or tests for binary availability before proceeding.

The closest pattern is the HARD STOP error handling in `qrspi-implement/SKILL.md:29` and `qrspi-work/SKILL.md:420,479-498`, which instructs agents to stop immediately on infrastructure errors (including "command not found"):

```
8. **HARD STOP on infrastructure errors.** If ANY command fails with permissions,
auth, config, or tooling errors (EACCES, permission denied, token expired,
command not found, config inaccessible): print the exact failing command and
exact error output, then STOP.
```
-- `.claude/skills/qrspi-implement/SKILL.md:29`

This is reactive (fail-then-stop) rather than proactive (check-before-use). No skill performs an upfront `which <tool>` check.

**Evidence:**
```
$ grep -rn "prerequisite\|guard\|installed\|which\|command -v" .claude/skills/
(no results for proactive CLI checks)
```

The only `Bash`-scoped skills use fine-grained permissions like `Bash(wc:*)`, `Bash(find:*)`, `Bash(git diff:*)` -- none scope to an external CLI binary.

**Dependencies:** N/A

**Implicit contracts:** The existing pattern is "attempt and hard-stop on failure" rather than "check prerequisites upfront." The `allowed-tools` frontmatter field scopes Bash access but does not verify binary presence.

---

## Q11: If the skill references both `--dry-run` (client-side) and `--server-dry-run` (server-side), how does it guide the agent when the Argo server is unreachable and server-dry-run fails?

**Answer:** NOT FOUND. No skill in this codebase references `--dry-run`, `--server-dry-run`, or any Argo-specific flags. No skill addresses server reachability or fallback behavior.

The only error-handling pattern documented in skills is the HARD STOP rule (stop on any infrastructure failure, do not attempt workarounds). This is explicitly stated in `qrspi-work/SKILL.md:479-498` and `qrspi-implement/SKILL.md:29`.

Search queries attempted:
- `grep -r "dry-run" --include="*.md"` -- no results
- `grep -r "server.*reachable\|unreachable\|fallback" --include="*.md"` -- no results
- `grep -r "argo" --include="*.md"` -- only in `questions.md`

**Dependencies:** N/A

**Implicit contracts:** The existing error-handling contract is: on any infrastructure failure, stop and report. There is no pattern for graceful degradation or fallback modes.

---

## Q12: What eval harness exists in this project for testing skills, and what does a skill eval look like (input prompt, expected behavior, scoring)?

**Answer:** The eval harness consists of:

1. **Suite definition** (`evals/suite.json`) -- 15 test cases across 6 phases (questions, research, design, structure, plan, worktree, implement, pr). Each case has:
   - `id`, `name`, `phase`, `prompt` -- identification
   - `context.files` -- fixture files loaded as input
   - `assertions` -- array of checks, each with `type`, `check`/`criteria`, and `weight`
   - `tags`, `difficulty` (easy/medium/hard), `split` (train/test)

2. **Assertion types:**
   - `programmatic` -- deterministic checks like `output_file_exists('questions.md')`, `question_count('questions.md') >= 8`, `no_solution_language('questions.md')`, `has_section('design.md', 'Risk Register')`
   - `llm_judge` -- subjective quality checks with a `criteria` string (e.g., "Questions are specific and answerable by reading code, not speculative or opinion-seeking")
   - `script` -- external script execution (e.g., `scripts/check_scope.py --log impl-log.md --allowed fixtures/worktree_session1.md`)

3. **Scoring** -- weighted sum normalized to 0-1 per case. LLM judge scores on a 1-5 scale, normalized to 0-1. Train/test split with 65/35 ratio and seed 42.

4. **Scripts** (all in `scripts/`):
   - `run_eval.py` -- executes cases in parallel with `ThreadPoolExecutor`, captures output (agent execution is a stub/placeholder)
   - `grade.py` -- runs assertions against results, computes per-case and suite scores
   - `diagnose.py` -- categorizes failures (MISSING_INSTRUCTION, CONFLICTING_INSTRUCTION, OVER_CONSTRAINED, UNDER_SPECIFIED, TOOL_MISUSE, CONTEXT_LOSS, MODEL_LIMITATION, EVAL_ISSUE)
   - `revise.py` -- proposes targeted edits to skill text based on diagnosis (meta-agent integration is a stub)
   - `report.py` -- tracks score trajectory across versions, detects plateaus and overfitting
   - `check_scope.py` -- verifies implementation stayed within allowed file scope

5. **Loop orchestrator** (`run_loop.sh`) -- runs the full cycle: eval -> grade -> check target -> diagnose -> revise, up to N iterations or until target score is met.

**Evidence:**
```python
# evals/suite.json (case_001 assertions excerpt)
{
    "type": "programmatic",
    "check": "output_file_exists('questions.md')",
    "weight": 1.0
},
{
    "type": "llm_judge",
    "criteria": "Questions are specific and answerable by reading code",
    "weight": 2.0
}
```
-- `evals/suite.json:29-42,69-72`

```python
# scripts/run_eval.py:93-143 (execution stub)
def execute_single(skill_text, case, trial_id, timeout_ms):
    # Placeholder for agent execution
    # Replace this block with actual agent invocation
    messages = build_messages(case)
    result.output = ""
    result.files = []
```
-- `scripts/run_eval.py:93-137`

**Dependencies:** `run_eval.py` -> `grade.py` -> `diagnose.py` -> `revise.py` -> `report.py`. The `run_loop.sh` orchestrates this pipeline. Fixtures live in `evals/fixtures/`.

**Implicit contracts:** The agent execution in `run_eval.py` is a stub -- actual agent invocation is not yet integrated. LLM judge scoring in `grade.py` is also a stub. The harness infrastructure exists but does not yet run real agent sessions.

---

## Q13: How are existing skills tested for correctness -- are there snapshot tests of SKILL.md output, integration tests that invoke the skill, or manual checklists?

**Answer:** There are no snapshot tests, integration tests, or unit tests that directly test skill behavior in this codebase. The test infrastructure is the eval harness described in Q12, which is currently a stub (agent execution and LLM judge scoring are placeholder implementations).

There is also a separate eval file for the Graphite CLI skill (`evals/graphite-evals.json`) with 5 test cases using a different assertion schema (`command_check`, `flag_check`, `content_check`, `workflow_check`, `safety_check`). This file is not referenced by `suite.json` or `run_eval.py`.

```json
{
  "skill_name": "graphite",
  "evals": [
    {
      "id": 1,
      "prompt": "I just made some changes to the auth module...",
      "assertions": [
        {"text": "Uses gt create or gt modify", "type": "command_check"},
        ...
      ]
    }
  ]
}
```
-- `evals/graphite-evals.json:1-15`

The validation checklists in `docs/qrspi_quick_reference.md:105-153` are manual:
```
After PHASE 1 (Questions):
  ☐ 12+ questions generated
  ☐ Each question references specific files
  ☐ Zero "should" language
  ☐ Covers 4+ system areas
```
-- `docs/qrspi_quick_reference.md:118-123`

No `test/`, `__tests__/`, or `spec/` directories exist. No test runner configuration exists.

**Evidence:**
```
$ find . -name '*test*' -o -name '*spec*' -o -name '__tests__'
(no results outside evals/)
```

**Dependencies:** The eval harness depends on fixture files in `evals/fixtures/` (4 ticket fixtures exist). The Graphite evals file appears orphaned from the main eval pipeline.

**Implicit contracts:** Skill correctness is currently validated through manual use and review, not automated testing. The eval harness is scaffolded but not operational.

---

## Q14: Do existing skills include any observability guidance (logging, metrics, tracing) for the CLI operations they wrap, and if so, what pattern do they follow?

**Answer:** No existing skill includes observability guidance. No skill mentions logging, metrics, tracing, or monitoring for CLI operations.

```
$ grep -rn "observability\|logging\|metrics\|tracing\|monitor" .claude/skills/ --include="*.md"
(no results)
```

The closest pattern is the `impl-log.md` entry format in `qrspi-implement/SKILL.md:33-40`, which records execution results:

```markdown
## Slice <N> — <ISO-8601>
**Tasks completed:** T1, T2, ...
**Tasks failed:** none
**Tests:** <command> → N passed, N failed
**Deviations from structure.md:** none
```
-- `.claude/skills/qrspi-implement/SKILL.md:33-40`

This is execution logging for the QRSPI workflow itself, not observability guidance for wrapped CLI tools.

**Evidence:** No observability patterns found in any skill.

**Dependencies:** N/A

**Implicit contracts:** Skills in this codebase are document-generation and workflow-orchestration skills. None wraps an external CLI tool with operational concerns like logging or monitoring.

---

## Q15: What conventions exist for surfacing workflow node status transitions (Pending, Running, Succeeded, Failed, Error, Skipped, Omitted) in agent output so the user can observe progress?

**Answer:** The closest convention is the verbose progress printing in `qrspi-work/SKILL.md`. The orchestrator prints status messages at phase boundaries:

```
5. Print: "Questions generated. Moving to Research..."
```
-- `.claude/skills/qrspi-work/SKILL.md:76`

```
5. Print: "Research complete. Moving to Design..."
```
-- `.claude/skills/qrspi-work/SKILL.md:97`

```
6. Print: "Slice `<N>`/`<total>` complete — `<goal>`"
```
-- `.claude/skills/qrspi-work/SKILL.md:248`

The worktree task DAG uses a `Status` column with value `pending` in its template (`docs/qrspi-orientation.md:404`):

```markdown
| Task | Description | Depends On | Plan Step | Cost | Status |
|------|-------------|-----------|-----------|------|--------|
| T1   | Create preferences route | — | 1.1 | S | pending |
```
-- `docs/qrspi-orientation.md:403-406`

However, there is no convention for Argo-specific node status transitions (Pending, Running, Succeeded, Failed, Error, Skipped, Omitted). No skill surfaces real-time status transitions from an external system.

The orchestrator's progress pattern is: print a completion message after each phase/slice, not a real-time status stream.

**Evidence:**
```
# qrspi-work/SKILL.md line 9:
"Run autonomously — no approval gates between phases. Print verbose progress
so the operator can observe."
```
-- `.claude/skills/qrspi-work/SKILL.md:11`

**Dependencies:** N/A

**Implicit contracts:** Progress output uses the pattern `Print: "<phase> complete. Moving to <next>..."`. Slice progress uses `"Slice N/total complete — goal"`. No structured status object or event stream exists.

---

## Discovered Patterns

1. **Consistent frontmatter schema**: All 10 skills use identical YAML frontmatter fields: `name`, `description`, `command`, `argument-hint`, `allowed-tools`. No skill deviates from this set.

2. **Upload boilerplate**: 8 of 10 skills (all except `qrspi-work` and `qrspi-ticket`) end with an identical "Upload artifact" section using a 4-step pattern: `wc -c` -> `prepare_attachment_upload` -> `curl PUT` -> `create_attachment_from_upload`. This is copy-pasted, not abstracted.

3. **Context firewalls**: The codebase intentionally restricts what each agent can see. The research agent cannot see the ticket (anti-anchoring). The implement agent sees only its slice's section of structure/plan/worktree. This is enforced by instruction, not by tooling.

4. **Per-phase skills are tiny**: Phase skills average 47 lines (excluding the orchestrator). They achieve brevity through numbered rules, template output formats, and no inline examples.

5. **Orchestrator concentration**: The `qrspi-work` skill (500 lines) is an order of magnitude larger than any other skill. It contains all git/graphite operations, state dispatch, sub-agent spawning, error handling, and resumability logic.

6. **Error handling is reactive, not proactive**: The HARD STOP pattern (attempt, fail, stop, report) appears in `qrspi-work` and `qrspi-implement`. No skill performs upfront environment validation.

7. **No CLI-wrapping skills exist**: All 10 skills are document-generation or workflow-orchestration skills. None wraps an external CLI binary. The new Argo skill would be the first CLI-wrapping skill in this codebase.

8. **Eval harness is scaffolded but not operational**: The full pipeline (run -> grade -> diagnose -> revise -> report) exists in code but agent execution and LLM judge scoring are stubs. The infrastructure demonstrates the intended eval-driven development workflow.

9. **Bash permission granularity**: Skills use fine-grained Bash permissions like `Bash(wc:*)`, `Bash(find:*)`, `Bash(git diff:*)`. Only `qrspi-implement` and `qrspi-ticket` have unrestricted `Bash` access.

---

## Inconsistencies

1. **Line count claim vs reality**: `docs/qrspi_quick_reference.md:19` states "12-15 specific exploration questions" for the Questions phase, but the SKILL.md at `.claude/skills/qrspi-questions/SKILL.md:13` specifies "8-15 technical questions", and the eval suite at `evals/suite.json:38-39` tests for `question_count >= 8` and `question_count <= 15`. The quick reference overstates the minimum.

2. **Graphite evals orphaned**: `evals/graphite-evals.json` uses a different assertion schema (`command_check`, `flag_check`, `safety_check`) than `evals/suite.json` (`programmatic`, `llm_judge`, `script`). No code in `scripts/` references or processes `graphite-evals.json`.

3. **Ticket phase numbering**: `docs/qrspi_quick_reference.md` labels the Ticket phase as "PHASE 0" and counts 9 total phases. The CLAUDE.md and skill files do not use phase numbers, and the orientation guide refers to 8 slash commands (no `/qrspi-ticket` in the quick-reference `## Quick Commands` section -- it does appear at line 309). The numbering is internally consistent within the quick reference but diverges from other docs that use letter abbreviations (T, Q, R, D, S, P, W, I, PR).

4. **Upload section in qrspi-ticket**: The `qrspi-ticket` skill does NOT have an upload section (it creates the Linear issue directly via `save_issue`), while the `qrspi-work` orchestrator has its own upload logic. The upload pattern is inconsistent: 8 skills upload artifacts, 2 do not (ticket, work).

5. **500-line limit documentation**: The 500-line / 40-instruction limit appears only in the troubleshooting section of `docs/qrspi_claude_code_guide.md:592`. It is not in CLAUDE.md, not in any skill, and not enforced programmatically. The `qrspi-work` skill itself is exactly 500 lines, suggesting it was written to the limit rather than validated against it.
