# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-01T00:00:00Z
**Generated:** 2026-06-01T00:00:00Z
**Status:** draft

## Q1: What is the on-disk directory layout a skill occupies in this repo (SKILL.md plus references/, scripts/, assets/), and where are skill source files placed versus their slash-command wrappers?

**Answer:** Skills live under `.claude/skills/<skill-name>/SKILL.md`. Each skill is a directory named for the skill, containing a `SKILL.md` file at its root. A skill may include a `references/` subdirectory for supporting markdown that is loaded on demand. Across the 10 skills in this repo, the only subdirectory observed is `references/` (used by `qrspi-work`). No skill in the repo currently uses `scripts/` or `assets/` subdirectories — repo-level automation scripts live in the top-level `scripts/` directory instead, not inside skill folders.

The QRSPI phase skills are thin wrappers: the `SKILL.md` under `.claude/skills/<name>/` contains a slash-command definition that spawns a corresponding agent, and the substantive prompt lives in `.claude/agents/<name>.md`. So for QRSPI phases, source is split: wrapper at `.claude/skills/<name>/SKILL.md`, agent prompt at `.claude/agents/<name>.md`. (`qrspi-ticket` and `qrspi-work` are exceptions — their full logic is in the SKILL.md, with no paired agent file.)

**Evidence:**

```
.claude/skills/qrspi-research/SKILL.md      (wrapper)
.claude/skills/qrspi-work/SKILL.md          (full logic, 36 KB)
.claude/skills/qrspi-work/references/review-cascade.md
.claude/agents/qrspi-research.md            (agent prompt)
```

Skill wrappers present: qrspi-design, qrspi-implement, qrspi-plan, qrspi-pr, qrspi-questions, qrspi-research, qrspi-structure, qrspi-ticket, qrspi-work, qrspi-worktree.
Agent files present (8): qrspi-design.md, qrspi-implement.md, qrspi-plan.md, qrspi-pr.md, qrspi-questions.md, qrspi-research.md, qrspi-structure.md, qrspi-worktree.md.

— `.claude/skills/` (directory listing), `.claude/agents/` (directory listing)

The wrapper-spawns-agent contract:

```
Thin wrapper that spawns the `qrspi-research` agent. All prompt content lives in `.claude/agents/qrspi-research.md`.
```

— `.claude/skills/qrspi-research/SKILL.md:11`

**Dependencies:** Skill wrappers depend on the `Agent` tool and the paired agent file existing at `.claude/agents/<name>.md`. No build step links them — the wrapper hardcodes the agent path in prose.
**Implicit contracts:** Skill directory name, the `name:` frontmatter field, and the agent `subagent_type` all share the same string (e.g. `qrspi-research`). A wrapper assumes its agent file exists at the conventional path.

## Q2: How does the skill-creator skill take an input description and produce a SKILL.md and supporting files — what files does it read and write during generation?

**Answer:** NOT FOUND — the question targets a resource outside the project scope. The `skill-creator` skill is not present anywhere under `REPO_ROOT`. Searches found the string `skill-creator` only as a passing mention in two files, neither of which is the skill itself: `.claude/agents/qrspi-structure.md:41` (lists "invoking skill-creator" as an example of a validation pass) and the questions artifact. `skill-creator` is a global/plugin skill listed in the session's available-skills list but lives outside this repository, so its file-read/write behavior cannot be observed from the codebase.

**Evidence:**

```
$ find . -iname "*skill-creator*"   → (no results)
$ grep -rli "skill-creator" .       → .claude/agents/qrspi-structure.md, .qrspi/RUS-21/questions.md
```

Reference in qrspi-structure agent:

```
9. Validation passes (linting, running a review tool, invoking skill-creator) are the final step of the slice that produced the files — not a separate slice.
```

— `.claude/agents/qrspi-structure.md:41`

**Dependencies:** None observable in-repo.
**Implicit contracts:** The repo treats `skill-creator` as an external validation tool invoked as a final step of a slice, not as in-repo code.

## Q3: What is the exact required frontmatter schema for a SKILL.md (field names, allowed values, name/description format) that conforms to the agentskills.io standard used here?

**Answer:** No formal/declared schema (e.g. a JSON Schema or validator) exists in-repo. The schema is observable only by convention across the 10 existing `SKILL.md` files. Two distinct frontmatter shapes are in use:

Skill-wrapper frontmatter (slash-command skills) uses these fields:
- `name` — string, matches the skill directory name (e.g. `qrspi-research`).
- `description` — string; for wrappers it states what the skill does and when to use it. May be quoted (double quotes) when it contains special characters / is long (see `qrspi-work`).
- `command` — the slash command, e.g. `/qrspi-research`.
- `argument-hint` — placeholder text, e.g. `<ticket-id>`.
- `allowed-tools` — comma-separated tool list; supports scoped Bash like `Bash(pwd:*)` and MCP tool names like `mcp__linear-russelltsherman__get_issue`.

Agent frontmatter (`.claude/agents/*.md`) uses a different shape:
- `name`, `description`, `model` (e.g. `opus`), and a nested `claude:` block with `tools:` (comma-separated).

**Evidence:**

```
---
name: qrspi-research
description: Map codebase facts by answering questions from the Questions phase. The feature ticket is intentionally hidden. Use after questions are approved.
command: /qrspi-research
argument-hint: <ticket-id>
allowed-tools: Agent, Bash(pwd:*)
---
```

— `.claude/skills/qrspi-research/SKILL.md:1-7`

```
---
name: qrspi-research
description: Internal QRSPI workflow agent — maps codebase facts ...
model: opus
claude:
  tools: Read, Write, Glob, Grep
---
```

— `.claude/agents/qrspi-research.md:1-7`

**Dependencies:** Frontmatter is consumed by the Claude Code harness (skill/agent loader), which is external to the repo. No in-repo parser validates it.
**Implicit contracts:** `name` must equal the directory name; `command` is `/` + name by convention; `description` doubles as the trigger text (see Q6). `allowed-tools` (skills) vs `claude.tools` (agents) are NOT the same field name — the two file types differ.

## Q4: How is a skill registered so it appears in the available-skills list and can be invoked via slash command or auto-invocation?

**Answer:** Registration is purely by file placement and frontmatter — there is no manifest, index, or registry file in the repo. A skill is "registered" by creating a `.claude/skills/<name>/SKILL.md` with valid frontmatter (`name`, `description`, `command`). The Claude Code harness (external) discovers skills from this directory; the `command` field defines the slash invocation and the `description` drives auto-invocation matching. No JSON/YAML manifest enumerating skills was found under `REPO_ROOT`.

**Evidence:**

```
$ ls .claude/skills/
qrspi-design  qrspi-implement  qrspi-plan  qrspi-pr  qrspi-questions
qrspi-research  qrspi-structure  qrspi-ticket  qrspi-work  qrspi-worktree
```

Each contains exactly a `SKILL.md` (plus `references/` for qrspi-work). No `index.json`, `manifest.json`, or registry file present in `.claude/`.

— `.claude/skills/` (directory listing)

**Dependencies:** Discovery/loading is performed by the external harness, not by repo code. The repo only supplies the convention-conformant files.
**Implicit contracts:** Presence in `.claude/skills/<name>/SKILL.md` + valid frontmatter is sufficient and necessary for registration. The `command:` value is what users type; the `name:` is the identity used elsewhere (e.g. agent `subagent_type`).

## Q5: How are reference files under references/ loaded relative to SKILL.md, and what mechanism keeps the SKILL.md body small while deferring detail to references?

**Answer:** The only multi-file skill in-repo is `qrspi-work`, which has `references/review-cascade.md`. References are addressed by relative path from the skill directory and loaded on demand (progressive disclosure) rather than inlined — the SKILL.md body points to the reference when that detail is needed. Notably, `qrspi-work/SKILL.md` is large (36 KB) and still keeps the cascade logic in a separate reference file. The mechanism for "keeping the body small" is editorial convention, not enforced tooling: detail that is only sometimes needed is split into `references/`. (See Q7 — there is no automated size gate in-repo.)

**Evidence:**

```
.claude/skills/qrspi-work/SKILL.md            (36889 bytes)
.claude/skills/qrspi-work/references/review-cascade.md  (2554 bytes)
```

The reference file is a standalone topic ("Review Cascade Logic") factored out of the main body:

```
# Review Cascade Logic

When planning review feedback requires changes to an artifact, downstream artifacts
may be invalidated. The planning artifacts form a dependency chain:
```

— `.claude/skills/qrspi-work/references/review-cascade.md:1-5`

**Dependencies:** Loading of references is performed by the agent/harness reading the relative path; no code in-repo performs the load.
**Implicit contracts:** References sit under `<skill-dir>/references/` and are referenced by relative path. The body is expected to summarize and defer; the reference holds the expanded detail.

## Q6: What naming and description conventions govern skill trigger matching, and how does the description field affect when the skill auto-invokes?

**Answer:** The `description` field is the trigger surface. The convention observed across skills is a two-part description: (1) what the skill does, (2) when to use it — often with explicit trigger phrases. `qrspi-work` is the clearest example: its description enumerates trigger variants ("'work on <ticket-id>'", "'continue <ticket-id>'", "'pick up <ticket-id>'") so the matcher can fire on those phrasings. Phase skills use "Use after X is approved" / "Use when starting a new QRSPI feature workflow" to scope auto-invocation. Agent descriptions add negative scoping ("Not for general codebase exploration") to suppress mis-triggering. Naming convention: `qrspi-<phase>` for the workflow family; the skill name equals the directory name and (minus the slash) the command.

**Evidence:**

```
description: "Single entry point for autonomous QRSPI feature development. Use when the user asks to 'work on' a ticket (e.g., 'work on RUS-42'). ... Trigger on any variant of: 'work on <ticket-id>', 'continue <ticket-id>', 'pick up <ticket-id>', or any reference to progressing a QRSPI ticket through its lifecycle."
```

— `.claude/skills/qrspi-work/SKILL.md:3`

Negative scoping in an agent description:

```
description: Internal QRSPI workflow agent — maps codebase facts ... Spawned by /qrspi-research or qrspi-work. Not for general codebase exploration.
```

— `.claude/agents/qrspi-research.md:3`

**Dependencies:** Auto-invocation matching is done by the external harness against the `description` text.
**Implicit contracts:** Put concrete trigger phrases and "Use when…" / "Not for…" clauses in `description`; keep `name` aligned with the directory and command. No in-repo tooling scores description quality.

## Q7: How does the project enforce or measure the SKILL.md body size limits (under 500 lines / 5000 tokens) called out in the acceptance criteria, and is there tooling that flags overage?

**Answer:** NOT FOUND for SKILL.md specifically. There is NO in-repo tooling that measures or enforces SKILL.md body size (no line/token check targeting `.claude/skills/**`). The eval/grade tooling does implement size checks, but only for QRSPI artifact outputs, not for skill bodies: `grade.py` has `line_count(filename, max_lines)` and the suite applies `line_count('design.md') <= 300` and `code_snippets_under_limit('research.md', 20)`. No analogous check is wired to skill files, and `run_loop.sh` evaluates a skill prompt's behavior, not its size. (Searched `grep -ri "500\|5000\|token" scripts/ evals/` context and the grade.py CHECKS registry.)

**Evidence:**

```python
def line_count(filename: str, max_lines: int, result: dict) -> tuple[bool, str]:
    """Check that output is within line limit."""
    output = result.get("output", "")
    count = len(output.splitlines())
    ok = count <= max_lines
    return ok, f"Line count: {count} (limit: {max_lines})"
```

— `scripts/grade.py:35-40`

```json
{ "type": "programmatic", "check": "line_count('design.md') <= 300", "weight": 1.5 }
```

— `evals/suite.json:241-244` (applies to a generated `design.md`, not a SKILL.md)

**Dependencies:** `line_count` is invoked by `grade.py`'s check dispatcher (`CHECKS` registry, `scripts/grade.py:146-157`) against execution `result["output"]`.
**Implicit contracts:** Size checks in this repo operate on agent OUTPUT artifacts identified by filename, not on skill source files. Any SKILL.md size limit is currently manual/editorial.

## Q8: How do existing skills handle content that exceeds the body budget — what is the established pattern for splitting overflow into references/ versus scripts/?

**Answer:** The only in-repo example of overflow handling is `qrspi-work`, which factors a self-contained topic ("Review Cascade Logic") into `references/review-cascade.md`. The established pattern is: extract a cohesive, occasionally-needed section into a single-topic file under `references/`. No skill in the repo uses a `scripts/` subdirectory for overflow — executable logic lives in the top-level `scripts/` directory (eval harness), not inside skill folders. So the observed split is: prose/detail → `references/`; there is no in-repo precedent for skill-local `scripts/`.

**Evidence:**

```
.claude/skills/qrspi-work/references/review-cascade.md  (one cohesive topic, 64 lines)
```

```
# Review Cascade Logic
... The planning artifacts form a dependency chain:
Questions → Research → Design → Structure → Plan → Work Tree
```

— `.claude/skills/qrspi-work/references/review-cascade.md:1-8`

Top-level (non-skill) scripts directory holds executable logic:

```
scripts/check_scope.py  scripts/diagnose.py  scripts/grade.py
scripts/report.py  scripts/revise.py  scripts/run_eval.py
```

— `scripts/` (directory listing)

**Dependencies:** None enforced.
**Implicit contracts:** `references/<topic>.md` holds one factored topic. Skill-local `scripts/` is unprecedented here; the agentskills convention for scripts is not exercised in this repo.

## Q9: What validation exists for malformed or missing frontmatter, and what happens when a SKILL.md fails that validation?

**Answer:** NOT FOUND in-repo for SKILL.md frontmatter. No code under `REPO_ROOT` parses or validates skill/agent frontmatter — validation is the responsibility of the external Claude Code harness. The only validation code in the repo validates EVAL SUITE JSON, not skills: `run_eval.py:load_suite()` requires top-level `{"name", "cases"}` and per-case `{"id", "prompt", "assertions"}`, raising `ValueError` on missing fields. There is no equivalent for SKILL.md, so a malformed SKILL.md would fail (if at all) only in the external loader, with no in-repo error path.

**Evidence:**

```python
def load_suite(suite_path: str) -> dict:
    with open(suite_path) as f:
        suite = json.load(f)
    required = {"name", "cases"}
    missing = required - set(suite.keys())
    if missing:
        raise ValueError(f"Suite missing required fields: {missing}")
    for case in suite["cases"]:
        case_required = {"id", "prompt", "assertions"}
        case_missing = case_required - set(case.keys())
        if case_missing:
            raise ValueError(f"Case {case.get('id', '?')} missing: {case_missing}")
    return suite
```

— `scripts/run_eval.py:42-58`

**Dependencies:** This validator is for `evals/suite.json`, consumed by `run_eval.py` / `run_loop.sh`. Unrelated to skill frontmatter.
**Implicit contracts:** In-repo, only eval suite JSON has a hard schema gate. SKILL.md correctness is enforced externally.

## Q10: What eval harness exists for skills in this repo, and what inputs/fixtures does it require to benchmark a newly authored skill?

**Answer:** A 5-stage Python eval pipeline drives skill/agent-prompt evaluation: `run_eval.py` (execute) → `grade.py` (score) → `report.py` (compare/regression) → `diagnose.py` (categorize failures) → `revise.py` (propose edits), orchestrated by `run_loop.sh`. Inputs to benchmark a skill: (1) the skill/agent prompt file path (`--skill`), (2) an eval suite JSON (`--suite`, e.g. `evals/suite.json`), and (3) per-case fixture files referenced by `context.files`. The suite defines cases with `id`, `prompt`, `context` (files, conversation_history, user_preferences), `assertions` (programmatic / llm_judge / script, each weighted), `tags`, `difficulty`, and a train/test `split`. Fixtures live in `evals/fixtures/`; golden outputs in `evals/golden/`.

IMPORTANT current-state caveat (from docs/eval-system.md): the harness is largely stubbed. `run_eval.py:117-137` does not actually invoke an agent (returns empty output); LLM-judge and script checks return `None` (`grade.py:208-241`); and only 4 of 21 referenced fixtures exist. So the pipeline runs end-to-end but currently produces zero scores until agent execution, judge integration, and fixtures are supplied. The existing suite covers the QRSPI phases only; a brand-new non-QRSPI skill would need its own suite (compare `evals/graphite-evals.json`, a separate 5-case suite for the Graphite skill with its own assertion vocabulary).

**Evidence:**

```python
parser.add_argument("--skill", required=True, help="Path to skill/agent prompt file")
parser.add_argument("--suite", required=True, help="Path to eval suite JSON")
parser.add_argument("--output", required=True, help="Output directory for results")
parser.add_argument("--trials", type=int, default=3, ...)
```

— `scripts/run_eval.py:219-223`

```
4 of 21 referenced fixtures exist (the ticket files). Missing fixtures: ...
The pipeline runs end-to-end but produces zeros — the three critical gaps are
agent execution, LLM judge integration, and the 17 missing fixture files.
```

— `docs/eval-system.md:80-108`

Example of a separate per-skill suite shape:

```json
{ "skill_name": "graphite", "evals": [ { "id": 1, "prompt": "...", "expected_output": "...", "files": [], "assertions": [ {"text": "...", "type": "command_check"} ] } ] }
```

— `evals/graphite-evals.json:1-15`

**Dependencies:** `run_loop.sh` calls the four scripts in sequence; `grade.py` reads `results.json` from `run_eval.py`; `report.py` reads the `results/` dir.
**Implicit contracts:** A skill is benchmarked via a suite JSON whose cases name fixture files under `evals/`; fixture paths in `context.files` are resolved relative to the eval working directory (the harness opens them with `os.path.exists`/`open`, `run_eval.py:78-82`). Missing fixtures silently drop from context rather than erroring.

## Q11: How are skill description triggering accuracy and skill performance measured, and what command runs those evals?

**Answer:** Two different things. (a) Skill PERFORMANCE (output quality / behavior) is measured by the eval suite scoring: per-case weighted sum of passed assertions normalized 0–1, aggregated to suite mean/stddev/min/max, split train vs test with a train-test gap to flag overfitting (`grade.py:score_case`, `score_suite`, `grade_results`). The command to run a full optimization cycle is `./run_loop.sh <skill_path> <eval_suite> [max_iter] [target_score]` (default target 0.85, 3 trials); a single grade pass is `python3 scripts/grade.py --results <results.json> --suite <suite.json>`. (b) Description TRIGGERING ACCURACY: NOT FOUND — there is no in-repo tooling that measures whether a description fires on the right prompts. The suites test behavior given that the skill is already invoked; none score trigger/no-trigger classification.

**Evidence:**

```python
def score_case(assertion_results: list) -> dict:
    max_score = 0.0; actual_score = 0.0
    for ar in assertion_results:
        weight = ar.get("weight", 1.0); max_score += weight
        if ar.get("passed") is True: actual_score += weight
        elif ar.get("score") is not None:
            actual_score += weight * (ar["score"] - 1) / 4
    normalized = actual_score / max_score if max_score > 0 else 0.0
```

— `scripts/grade.py:246-265`

```bash
./run_loop.sh .qrspi/agents/01-questions.md evals/suite.json 5 0.85
```

— `run_loop.sh:10` (usage example) ; loop body `run_loop.sh:32-112`

Promotion/regression criteria:

```
Test score must not regress vs. previous version; No per-case drops > 0.2;
Train-test gap must be <= 0.1
```

— `docs/eval-system.md:50-55`

**Dependencies:** `run_loop.sh` → `run_eval.py` → `grade.py` → `report.py`/`diagnose.py`/`revise.py`. Score read back via inline `python3 -c` in `run_loop.sh:59-64`.
**Implicit contracts:** "Performance" == assertion-weighted output score on a fixed suite with train/test split. Trigger accuracy is not part of this harness.

## Q12: How are skill invocations, trigger matches, and eval results surfaced or logged so an author can confirm a new skill triggers and performs as intended?

**Answer:** Eval results are surfaced as JSON artifacts plus console output; trigger matches are NOT logged in-repo. `run_eval.py` writes `<output_dir>/results.json` (skill_hash, per-trial output/tokens/tool_calls/transcript) and prints a per-execution OK/ERROR line with duration. `grade.py` writes `grades.json` (train_score, test_score, train_test_gap, per-case mean/stddev/trials) and prints the train/test/gap summary. `run_loop.sh` writes versioned dirs `results/v1..vN/` and a final `results/report.json` via `report.py`. The execution result schema includes `transcript` and `tool_calls` fields intended to capture invocations — but these are stubbed empty today (`run_eval.py:132-137`). There is no logging that records when a description matched or which skill auto-invoked; that observability lives (if anywhere) in the external harness.

**Evidence:**

```python
output_path = os.path.join(config.output_dir, "results.json")
with open(output_path, "w") as f:
    json.dump(output, f, indent=2)
print(f"\nResults written to {output_path}")
```

— `scripts/run_eval.py:209-213`

```python
print(f"Train score: {train_scores['mean']:.4f} (+/- {train_scores['stddev']:.4f})")
print(f"Test score:  {test_scores['mean']:.4f} (+/- {test_scores['stddev']:.4f})")
print(f"Train-test gap: {output['train_test_gap']:.4f}")
print(f"Grades written to {grades_path}")
```

— `scripts/grade.py:367-370`

Intended-but-stubbed invocation capture:

```python
result.tool_calls = []
result.transcript = messages
```

— `scripts/run_eval.py:136-137`

**Dependencies:** `report.py` consumes `results/` to build a version ledger (`run_loop.sh:119-121`). `grade.py` consumes `results.json`.
**Implicit contracts:** Authors confirm performance by reading `grades.json` / `report.json` and the console summary. Per-invocation transcripts are a planned field (`ExecutionResult.transcript`, `run_eval.py:28`) not yet populated.

---

## Discovered Patterns

- **Wrapper/agent split for QRSPI phases.** Every QRSPI phase skill is a thin `SKILL.md` wrapper (frontmatter + a short "Steps" list) that resolves paths and spawns a same-named agent from `.claude/agents/<name>.md` via the `Agent` tool. Substance lives in the agent file. (`.claude/skills/qrspi-research/SKILL.md:11`, all phase wrappers.)
- **Two exceptions to the split:** `qrspi-ticket` and `qrspi-work` carry full logic in their SKILL.md and have no paired agent file.
- **Convention over configuration for registration.** No manifest/registry — discovery is by `.claude/skills/<name>/SKILL.md` placement and frontmatter alone.
- **Description = trigger surface.** Descriptions follow a "what it does + when to use + (sometimes) literal trigger phrases + (agents) negative scoping" template.
- **`allowed-tools` scoping.** Skills narrow tools precisely, e.g. `Bash(pwd:*)` and explicit MCP tool names like `mcp__linear-russelltsherman__get_issue`.
- **Eval-as-iteration loop.** `run_loop.sh` runs execute→grade→diagnose→revise with a target score (default 0.85), regression rollback (>0.05 drop), and a train/test split (65/35, seed 42) to detect overfitting.
- **Stubbed harness.** The eval pipeline is structurally complete but functionally stubbed: no real agent execution, LLM-judge/script checks return None, ~14/37 programmatic checks implemented, 4/21 fixtures present (`docs/eval-system.md:93-108`).
- **Per-skill suites can differ.** `evals/graphite-evals.json` uses an entirely different case/assertion vocabulary than `evals/suite.json`, showing a new skill gets its own suite shape rather than reusing the QRSPI one.

## Inconsistencies

- **Agent directory path: docs vs reality.** `.claude/CLAUDE.md` (project instructions) states "Agent prompt definitions live in `.qrspi/agents/`", and `run_loop.sh:10` example uses `.qrspi/agents/01-questions.md`. The actual agent prompts live in `.claude/agents/*.md` (e.g. `.claude/agents/qrspi-research.md`), and no `.qrspi/agents/` directory exists in the worktree. The root `CLAUDE.md` referenced in the workflow guide elsewhere says "Phase agent definitions live in `.claude/agents/`" — so the two CLAUDE.md variants disagree, and the in-worktree `.claude/CLAUDE.md` is stale.
- **`run_loop.sh` example skill paths don't exist.** The usage example references `.qrspi/agents/01-questions.md`; no numeric-prefixed agent files exist (actual: `.claude/agents/qrspi-questions.md`).
- **Frontmatter field name divergence.** Skills declare tools via `allowed-tools:` (flat list); agents declare them via a nested `claude.tools:` block. Same concept, two field shapes across the two file types.
- **Size limits asserted on artifacts, not skills.** The eval suite enforces `line_count`/`code_snippets_under_limit` on generated artifacts (design.md, research.md) but nothing enforces any SKILL.md body budget, despite size being a common skill-authoring concern.
- **`skill-creator` referenced but absent.** `.claude/agents/qrspi-structure.md:41` names `skill-creator` as a validation step, but the skill is not in-repo (it is an external/global skill), so the repo depends on a tool it does not contain.
