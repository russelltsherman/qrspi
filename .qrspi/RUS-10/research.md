# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-03T00:00:00Z
**Generated:** 2026-06-03T00:00:00Z
**Status:** draft

> **Scope note (read first):** The questions target two external tools — the **cmux CLI** and Anthropic's **skill-creator** skill — neither of which exists inside `REPO_ROOT`. A repo-wide search for `cmux` matched only `.qrspi/RUS-10/questions.md` itself. There is **no `skill-creator` skill** under `.claude/skills/` (the only match for the string `skill-creator` is a passing mention in an agent prompt). The repo *does* contain a fully worked example of the on-disk skill convention this feature must follow: ten `qrspi-*` skills under `.claude/skills/`, each a wrapper over an agent in `.claude/agents/`. Answers below map the in-repo skill convention (the real, citable target) and explicitly mark the external tooling as NOT FOUND.

## Q1: What does the Anthropic skill builder (skill-creator) skill produce as output, and where does it write generated `SKILL.md`, `references/`, `scripts/`, and `assets/` files?

**Answer:** NOT FOUND in `REPO_ROOT`. The skill-creator skill is not vendored into this repo; it is an external/global Claude Code skill. The only occurrence of the term inside the repo is a passing reference in the structure agent's rules (see Evidence), which treats `skill-creator` as an external validation pass to be invoked, not as a file it controls.

What *is* observable in-repo is the output convention any new skill must conform to: a skill is a directory under `.claude/skills/<name>/` containing a `SKILL.md`, optionally a `references/` subdirectory for on-demand auxiliary docs. No skill in this repo currently ships a `scripts/` or `assets/` subdirectory (verified: `find .claude/skills -type d` returns only the skill dirs plus `qrspi-work/references`).

**Evidence:**

```
9. Validation passes (linting, running a review tool, invoking skill-creator) are the final step of the slice that produced the files — not a separate slice.
```

— `.claude/agents/qrspi-structure.md:40`

**Search queries attempted:** `grep -rli "skill-creator\|skill_creator\|skill creator"` → only `.claude/agents/qrspi-structure.md`; `grep -rli "agentskills"` → only `questions.md`; `find -iname "*skill*"` → only the ten `qrspi-*` skill dirs.
**Dependencies:** None in-repo. External skill-creator is upstream tooling outside project scope.
**Implicit contracts:** A new skill is expected to pass a `skill-creator` validation as the final step of its implementing slice (per the structure agent's slicing rule).

## Q2: What is the canonical on-disk location and directory layout for installed skills in this repo, and how does a new skill's directory get named relative to its skill identifier?

**Answer:** Installed skills live under `.claude/skills/<skill-name>/`, one directory per skill, each containing a `SKILL.md`. The directory name is identical to the skill's `name` frontmatter field and to its slash `command` (minus the leading `/`). Example: directory `qrspi-research/` ↔ `name: qrspi-research` ↔ `command: /qrspi-research`. This 1:1:1 naming is consistent across all ten skills. Multi-file skills add subdirectories (only `qrspi-work/` does, with a `references/` dir).

**Evidence:**

```
qrspi-design  qrspi-implement  qrspi-plan  qrspi-pr  qrspi-questions
qrspi-research  qrspi-structure  qrspi-ticket  qrspi-work  qrspi-worktree
```

— `.claude/skills/` (directory listing)

```
---
name: qrspi-research
description: Map codebase facts by answering questions from the Questions phase. ...
command: /qrspi-research
argument-hint: <ticket-id>
allowed-tools: Agent, Bash(pwd:*)
---
```

— `.claude/skills/qrspi-research/SKILL.md:1-7`

**Dependencies:** README documents this layout (`.claude/skills/` with one subdir per skill) at `README.md:86-95`. CLAUDE.md states "their slash-command wrappers live in `.claude/skills/`".
**Implicit contracts:** `name` == directory name == `command` without the leading slash. A new skill must create `.claude/skills/<name>/SKILL.md` following this convention.

## Q3: What is the exact required `SKILL.md` frontmatter schema (field names, allowed values, required vs. optional) that the agentskills.io standard / skill-creator enforces?

**Answer:** No formal schema or validator exists in `REPO_ROOT` (NOT FOUND for an enforced/validated schema). The *de facto* schema, inferred from the ten existing `SKILL.md` files, is YAML frontmatter delimited by `---` with these fields:

- `name` (string, required) — matches the directory name.
- `description` (string, required) — trigger/usage sentence; for `qrspi-work` it is quoted and multi-clause.
- `command` (string, required in these examples) — the slash command, e.g. `/qrspi-research`.
- `argument-hint` (string, optional) — e.g. `<ticket-id>`, `<ticket-id> <slice-number>`, `<initial description>`.
- `allowed-tools` (comma-separated list, present in all) — e.g. `Agent, Bash(pwd:*)`, or with scoped MCP tools like `mcp__linear-russelltsherman__get_issue`.

All ten files use exactly these five keys (no more). No allowed-value enumeration is enforced anywhere in-repo; values are free-form.

**Evidence:**

```
---
name: qrspi-implement
description: Implement one vertical slice per invocation. ...
command: /qrspi-implement
argument-hint: <ticket-id> <slice-number>
allowed-tools: Agent, Read, Bash(pwd:*)
---
```

— `.claude/skills/qrspi-implement/SKILL.md:1-7`

**Dependencies:** None — there is no parser or validator file in-repo that reads this frontmatter.
**Implicit contracts:** `allowed-tools` uses tool-name tokens, optionally argument-scoped with `(...)` (e.g. `Bash(pwd:*)`); MCP tools use the `mcp__<server>__<tool>` form. `description` is the trigger signal for auto-invocation (see Q8).
**Inconsistency flagged:** the question's reference to "agentskills.io standard" cannot be verified — no such standard doc exists in the repo.

## Q4: What invocation interface does the skill-creator skill expose (arguments, sub-commands, or eval-loop entry points) for creating vs. modifying a skill?

**Answer:** NOT FOUND in `REPO_ROOT`. skill-creator's invocation interface is external. No SKILL.md, scripts, or docs for skill-creator exist in the repo.

For context on how *this repo's own* skills expose an interface: each skill is invoked via its `command` slash form with `argument-hint` arguments, and the skill body is a numbered "Steps" procedure that typically spawns an agent via the `Agent` tool. There is no create-vs-modify branching in any in-repo skill.

**Evidence:**

```
## Steps
1. Parse `$ARGUMENTS` to get `<ticket-id>`.
2. Resolve `REPO_ROOT` from `pwd` ...
3. Spawn the agent via the `Agent` tool:
   - `subagent_type: qrspi-research`
```

— `.claude/skills/qrspi-research/SKILL.md` (Steps section)

**Search queries attempted:** same as Q1; no skill-creator entry point found.
**Dependencies:** External skill outside project scope.

## Q5: How are skills registered or discovered so they become available via `/` invocation — is there an index, manifest, or generated listing that must be updated?

**Answer:** Discovery is by directory convention, not a manifest. There is **no index, manifest, or generated listing file** in `REPO_ROOT` that enumerates skills (NOT FOUND for a manifest). `.claude/` contains only `CLAUDE.md`, `agents/`, `skills/`, `workflows/` — no `settings.json`, no plugin/marketplace JSON. The Claude Code harness discovers a skill by the presence of `.claude/skills/<name>/SKILL.md` with valid frontmatter. The only human-facing "listings" are documentation that must be kept in sync manually: `README.md` (skills tables) and `.claude/CLAUDE.md` (the "Available skills" bullet list).

**Evidence:**

```
$ ls -la .claude/
CLAUDE.md  agents  skills  workflows      # no settings.json, no manifest
$ find . -name "*.json" -path "*claude*"  # (no results)
```

— `.claude/` (directory listing) and repo-wide find

```
| Skill | Command |
... (Individual phase skills table)
```

— `README.md:52-56`

**Dependencies:** README.md and .claude/CLAUDE.md are downstream documentation consumers that must be manually updated when a skill is added (no generator regenerates them).
**Implicit contracts:** Adding `.claude/skills/<name>/SKILL.md` is sufficient for `/` availability; updating README + CLAUDE.md listings is a documentation convention, not an enforced gate.

## Q6: How do existing skills structure and reference auxiliary `references/` files from the main `SKILL.md` body so the agent loads them on demand?

**Answer:** Only one skill in the repo uses a `references/` directory: `qrspi-work`, which has `references/review-cascade.md`. It is referenced from the SKILL.md body by relative path in prose ("see `references/review-cascade.md`"), not by frontmatter or any include mechanism — the agent is expected to read it on demand when it reaches that instruction. This is the lone in-repo example of the on-demand reference pattern.

**Evidence:**

```
phase's own artifacts (see `references/review-cascade.md`). Do NOT touch downstream phases
```

— `.claude/skills/qrspi-work/SKILL.md:282`

```
.claude/skills/qrspi-work/SKILL.md
.claude/skills/qrspi-work/references/review-cascade.md
```

— `find .claude/skills/qrspi-work -type f`

**Dependencies:** `qrspi-work/SKILL.md` → `qrspi-work/references/review-cascade.md` (prose reference, relative path).
**Implicit contracts:** Reference path is relative to the skill directory; loading is on-demand (the body instructs the agent to consult it at the relevant step rather than inlining the content).

## Q7: What enforces or measures the "SKILL.md body under 500 lines / 5000 tokens" acceptance constraint — is there a linter, token counter, or eval check?

**Answer:** NOT FOUND. There is no linter, token counter, or line-count check for SKILL.md anywhere in `REPO_ROOT`. No script under `scripts/` measures SKILL.md size; the eval harness (`scripts/run_eval.py`) does not assert on skill length. For reference, the largest existing SKILL.md body in-repo is `qrspi-work/SKILL.md` (referenced content extends past line 282), so the constraint, if it applies, is currently unenforced and only manually checkable. This constraint is presumably owned by the external skill-creator skill, which is out of scope.

**Search queries attempted:** `ls scripts/` (no token/lint tool); grep for `500\|5000\|token` budget tooling in scripts — none found relevant.
**Dependencies:** None in-repo.
**Implicit contracts:** None enforced; budget is a convention from external tooling.

## Q8: How is a skill's `description` field optimized for trigger accuracy, and is there an eval/benchmark step (variance analysis) that must pass before shipping?

**Answer:** NOT FOUND for an in-repo description-optimization or variance-analysis step tied to skills. The `description` field is the trigger signal (it carries explicit "Use when..." / "Trigger on any variant of..." phrasing — see `qrspi-work`'s description, which enumerates trigger phrases). However, there is **no eval or benchmark that scores description trigger accuracy** in the repo. The repo's eval harness (`scripts/run_eval.py` + `evals/`) is a non-functional placeholder (see Q11) and its fixtures are ticket/prompt fixtures, not skill-trigger cases. Variance analysis is part of the external skill-creator eval loop, outside project scope.

**Evidence:**

```
description: "Single entry point for autonomous QRSPI feature development. Use when the user asks to 'work on' a ticket ... Trigger on any variant of: 'work on <ticket-id>', 'continue <ticket-id>', 'pick up <ticket-id>' ..."
```

— `.claude/skills/qrspi-work/SKILL.md:3` (frontmatter)

**Dependencies:** None in-repo for trigger scoring.
**Implicit contracts:** Convention is to pack the `description` with explicit usage triggers and negative/variant phrasing to improve auto-invocation; this is observed practice, not validated by tooling.

## Q9: What are the documented constraints/escaping rules for content within `SKILL.md` (code fences, `Cmd+N` notation, OSC escapes) that could break frontmatter parsing or rendering?

**Answer:** NOT FOUND — there are no documented escaping rules, and no SKILL.md parser/loader exists in `REPO_ROOT` to inspect. Observable conventions from existing files: frontmatter is delimited by leading/trailing `---`; a `description` containing special characters or a multi-clause string is wrapped in double quotes (only `qrspi-work` does this — all others use unquoted single-line descriptions). Bodies freely use triple-backtick code fences and inline backticks below the frontmatter without issue. No example in-repo contains keyboard-shortcut notation (`Cmd+N`) or OSC escape sequences, so their handling is unverified here.

**Evidence:**

```
description: "Single entry point for autonomous QRSPI feature development. ..."   # quoted (contains commas, quotes, colons)
```
vs.
```
description: Map codebase facts by answering questions from the Questions phase. ...  # unquoted single line
```

— `.claude/skills/qrspi-work/SKILL.md:3` and `.claude/skills/qrspi-research/SKILL.md:3`

**Dependencies:** None — no parser to cite.
**Inconsistency flagged:** Quoting of `description` is inconsistent across skills (one quoted, nine unquoted), driven by whether the value contains YAML-special characters.

## Q10: How are skills tested or evaluated in this repo, and what does the skill-creator eval harness require as inputs?

**Answer:** Two distinct testing mechanisms exist in-repo, neither of which is the (external) skill-creator harness:

1. **Unit tests (functional):** Pure-logic Python scripts have stdlib-only `_test.py` siblings under `scripts/` — `qrspi_persist_test.py`, `qrspi_pr_state_test.py`, `qrspi_resolve_state_test.py`, `qrspi_resolve_test.py`. These test orchestration/resolver logic, NOT skills.
2. **Eval harness (placeholder):** `scripts/run_eval.py` consumes a suite JSON (`evals/suite.json`) of `cases`, each requiring `id`, `prompt`, `assertions`; optional `context.files` (e.g. `evals/fixtures/ticket_*.md`) and `context.conversation_history`. It runs N trials per case. **But it does not actually execute an agent** (see Q11).

The skill-creator eval harness itself is NOT FOUND in-repo.

**Evidence:**

```
for case in suite["cases"]:
    case_required = {"id", "prompt", "assertions"}
    case_missing = case_required - set(case.keys())
    if case_missing:
        raise ValueError(f"Case {case.get('id', '?')} missing: {case_missing}")
```

— `scripts/run_eval.py` (`load_suite`)

**Dependencies:** `run_eval.py` reads `evals/suite.json` and `evals/fixtures/*.md`. CLAUDE.md/MEMORY both label the eval harness a placeholder.
**Implicit contracts:** A suite needs `name` + `cases`; each case needs `id`, `prompt`, `assertions`. Fixture files are injected into the user message if `context.files` paths exist.

## Q11: Is the `evals/` + `scripts/run_eval.py` harness functional for skill testing, or must verification rely on the skill-creator's own eval loop and manual checks?

**Answer:** **Non-functional placeholder.** `run_eval.py`'s `execute_single()` is an explicit stub: it builds messages but never invokes an agent, returning empty output, zero tokens, and no tool calls. The code comments say "In a real implementation, this would..." and "Placeholder for agent execution." This matches CLAUDE.md ("The `evals/` + `scripts/run_eval.py` harness is a **non-functional placeholder**") and project MEMORY ("eval harness is a placeholder; verify with unit tests + manual e2e"). Therefore skill verification must rely on the external skill-creator eval loop and manual checks; the in-repo harness produces no real signal.

**Evidence:**

```
# ── Placeholder for agent execution ──
# Replace this block with actual agent invocation:
#   response = agent.run(...)
messages = build_messages(case)
result.output = ""
result.files = []
result.tokens = {"input": 0, "output": 0}
result.tool_calls = []
result.transcript = messages
```

— `scripts/run_eval.py` (`execute_single`)

**Dependencies:** Consumed by no functional pipeline; `run_loop.sh` and `scripts/grade.py`/`report.py` exist but the executor returning empty output means downstream grading has nothing real to grade.
**Implicit contracts:** Until `execute_single` is wired to a real runtime, results.json is structurally valid but semantically empty.

## Q12: How does the skill-creator surface results, warnings, and failures during skill generation and eval?

**Answer:** NOT FOUND for skill-creator specifically (external). For the in-repo eval harness, `run_eval.py` surfaces progress and status to **stdout** (per-execution `[n/total] case trial OK|ERROR (Nms)` lines, plus a header with run count and skill hash) and writes a **`results.json`** report into the configured `output_dir`. Per-trial errors are captured in `ExecutionResult.error` rather than raised, so failures appear as `ERROR` rows and an `error` field in the JSON.

**Evidence:**

```
print(f"  [{completed}/{total_runs}] {case_id} trial={trial} {status} ({result.duration_ms:.0f}ms)")
...
output_path = os.path.join(config.output_dir, "results.json")
with open(output_path, "w") as f:
```

— `scripts/run_eval.py` (`run_suite`)

**Dependencies:** Output JSON likely consumed by `scripts/grade.py` / `scripts/report.py` (present in `scripts/`); not traced further since the executor is a stub.
**Implicit contracts:** Console = live progress; `results.json` = machine-readable record. (Skill-creator's own surfacing is external and unverifiable here.)

---

## Discovered Patterns

- **Skill = directory under `.claude/skills/<name>/` with a `SKILL.md`.** Ten skills follow this; naming is 1:1:1 across directory name, frontmatter `name`, and `command` (sans `/`). (`.claude/skills/`, `README.md:86-95`)
- **Thin wrapper → agent split.** Most skills are thin wrappers whose body is a numbered "Steps" procedure that spawns a `qrspi-*` agent (`.claude/agents/<name>.md`) via the `Agent` tool. The substantive prompt lives in the agent, not the skill. (`.claude/skills/qrspi-research/SKILL.md`)
- **Frontmatter is a fixed 5-key set:** `name`, `description`, `command`, `argument-hint`, `allowed-tools`. No skill deviates. `allowed-tools` supports argument-scoping (`Bash(pwd:*)`) and MCP tokens (`mcp__linear-russelltsherman__get_issue`).
- **On-demand references via relative prose path.** `qrspi-work` is the sole multi-file skill; it cites `references/review-cascade.md` in prose for lazy loading. No skill uses `scripts/` or `assets/` subdirs.
- **Convention over manifest.** No registry/index/manifest/settings.json governs skill discovery; presence of the directory + SKILL.md is the contract. Human-facing listings in `README.md` and `.claude/CLAUDE.md` are maintained manually.
- **Two-tier testing philosophy** (from CLAUDE.md + MEMORY): functional `_test.py` unit tests for pure logic; the eval harness is a placeholder; orchestration verified by manual e2e.
- **Self-locating, staging-based persistence** (`scripts/qrspi_persist.py`, `qrspi_resolve.py`) is a repo-wide pattern to defend against a weak worker model mangling the `qrspi` path token — relevant if a new skill writes artifacts.

## Inconsistencies

- **Feature target is absent from the codebase.** Both `cmux` and `skill-creator` (the feature's core tools) exist nowhere in `REPO_ROOT` except the questions file. The implementation will introduce a skill *about/using* external tooling; the repo provides only the on-disk skill convention to conform to, not the tools themselves.
- **`description` quoting is inconsistent:** `qrspi-work` quotes its multi-clause `description`; the other nine use unquoted single-line strings. Driven by YAML-special characters, but not standardized.
- **CLAUDE.md / README skill listings vs. actual directory.** Both docs list the ten skills, but there is no generator keeping them in sync with `.claude/skills/` — a new skill requires three manual edits (directory, README table, CLAUDE.md bullet list) with nothing enforcing consistency.
- **Eval harness claims vs. reality (consistent, but worth flagging):** `run_eval.py`'s docstring describes "isolated environments" and full transcript capture, while `execute_single` is an explicit stub returning empty output — the docstring describes intent, not current behavior. This matches the documented "placeholder" status.
- **Acceptance constraints with no enforcer:** the "500 lines / 5000 tokens" budget (Q7) and "trigger-accuracy variance analysis" (Q8) implied by the feature have no in-repo linter, counter, or eval — they are owned by the external skill-creator and cannot be verified within this repo.
