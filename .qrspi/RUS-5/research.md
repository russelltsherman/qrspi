# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-01T00:00:00Z
**Generated:** 2026-06-01T00:00:00Z
**Status:** draft

> Scope note: Several questions target a "skill-creator" / "skill-builder" skill.
> No such skill exists inside this repository. The `skill-creator` skill referenced
> by the questions is a global/external Claude Code skill (it appears in the harness
> available-skills list but is NOT present under `REPO_ROOT/.claude/skills/`). It is
> out of project scope and cannot be read. Where a question depends on that external
> skill, the answer documents what CAN be observed in-repo (the existing `.claude/skills/`
> SKILL.md convention) and marks the external part NOT FOUND.

## Q1: What is the on-disk directory layout the Anthropic skill builder produces for a new skill (SKILL.md plus which of `references/`, `scripts/`, `assets/`), and where in this repo are generated skills placed?

**Answer:** The skill-builder itself is NOT in this repo (external/global skill — out of
scope). What is observable: this repo's own skills live under `.claude/skills/<skill-name>/`,
each containing a single `SKILL.md`. Only ONE skill in the repo uses a subdirectory:
`qrspi-work` has a `references/` directory holding `review-cascade.md`. No skill in the repo
has a `scripts/` or `assets/` subdirectory. So the de-facto in-repo layout is:
`.claude/skills/<name>/SKILL.md` (mandatory) plus an optional `references/` directory only
when reference material is split out. Generated skills for THIS project would be placed at
`REPO_ROOT/.claude/skills/<skill-name>/`.

**Evidence:**

```
.claude/skills/qrspi-design/SKILL.md
.claude/skills/qrspi-work/SKILL.md
.claude/skills/qrspi-work/references/review-cascade.md   # only references/ dir in repo
.claude/skills/qrspi-questions/SKILL.md
... (10 skill dirs total, each with exactly one SKILL.md)
```

— `.claude/skills/` (directory listing); `.claude/skills/qrspi-work/references/review-cascade.md`
**Dependencies:** None in-repo for scaffolding. The external `skill-creator` is the producer; not present.
**Implicit contracts:** Skill directory name == frontmatter `name` field == command suffix (e.g., dir `qrspi-research`, `name: qrspi-research`, `command: /qrspi-research`). `references/` is created only on demand; `scripts/` and `assets/` are unused by every existing repo skill.

## Q2: How does an authored skill split content between the SKILL.md body and `references/` files — what is the loading/inclusion mechanism that pulls reference material in when the body points to it?

**Answer:** The mechanism in this repo is an explicit instruction in the SKILL.md body telling
the agent to READ the reference file at the moment it is needed — there is no automatic
templating/include. The single in-repo example is `qrspi-work`: its SKILL.md body says
`Read references/review-cascade.md for cascade logic.` The agent performs an on-demand file
read (relative path resolved from the skill directory). Reference files are full standalone
markdown documents; the body stays lean and defers detailed procedures to `references/`.

**Evidence:**

```
.claude/skills/qrspi-work/SKILL.md:281:   c. Read `references/review-cascade.md` for cascade logic.
```

— `.claude/skills/qrspi-work/SKILL.md:281`; target file `.claude/skills/qrspi-work/references/review-cascade.md:1-64`
**Dependencies:** SKILL.md body → `references/<file>.md` via a literal Read instruction. One-directional (body points down to reference).
**Implicit contracts:** Reference paths are written relative to the skill directory (`references/...`, not an absolute path). Loading is lazy/manual — the body must explicitly instruct the read; nothing auto-injects reference content.

## Q3: What fields are required in SKILL.md frontmatter for a valid agentskills.io-pattern skill, and what are their format/length constraints (e.g., name, description)?

**Answer:** The authoritative spec lives in the external skill-builder (NOT FOUND in repo).
Observed from every in-repo SKILL.md, the consistent frontmatter schema is: `name`,
`description`, `command`, `argument-hint`, `allowed-tools`. The first 7 lines of all 10
SKILL.md files follow this exact ordering. `description` is a single sentence-to-paragraph
trigger string; when it contains a colon or special chars it is quoted (see `qrspi-work`,
`qrspi-design`). No explicit length/format CONSTRAINT (max chars, regex) is enforced anywhere
in-repo — there is no validator. `name` always equals the directory name.

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

— `.claude/skills/qrspi-research/SKILL.md:1-7` (pattern repeats across all 10 SKILL.md files)
**Dependencies:** Frontmatter consumed by the Claude Code harness for registration/triggering (external to repo).
**Implicit contracts:** Five keys in fixed order. `description` quoted only when it embeds a colon/apostrophe (`qrspi-work`, `qrspi-questions` use quotes). `allowed-tools` is a comma-separated tool allowlist, optionally scoped (`Bash(pwd:*)`). No in-repo length enforcement — constraints (≤500 lines / 5000 tokens) are external conventions, not validated here.

## Q4: How is a skill registered so it appears in the available-skills list and triggers via `/` or auto-invocation — what governs the `description` used for trigger matching?

**Answer:** Registration is by file presence: dropping a `SKILL.md` with valid frontmatter
under `.claude/skills/<name>/` makes the harness expose it. This is performed by the Claude
Code harness, which is EXTERNAL to the repo (NOT FOUND as in-repo code — there is no
discovery/registration module in this codebase). Trigger matching is governed by the
frontmatter `description` field; the repo's skills encode trigger phrases directly in it
(e.g., qrspi-work lists `'work on <ticket-id>'`, `'continue <ticket-id>'`, `'pick up
<ticket-id>'`). The `command` field defines the `/`-slash invocation name.

**Evidence:**

```
description: "Single entry point for autonomous QRSPI feature development. Use when the user
asks to 'work on' a ticket ... Trigger on any variant of: 'work on <ticket-id>',
'continue <ticket-id>', 'pick up <ticket-id>', or any reference to progressing a QRSPI ticket
through its lifecycle."
command: /qrspi-work
```

— `.claude/skills/qrspi-work/SKILL.md:3-4`
**Dependencies:** Harness skill-loader (external) reads `.claude/skills/*/SKILL.md` frontmatter. No repo code implements discovery.
**Implicit contracts:** `description` doubles as the trigger-match corpus — concrete trigger phrases are embedded verbatim. `command` must start with `/` and match the skill name. The description-optimization step the question references belongs to the external skill-builder — NOT FOUND in repo.

## Q5: Does the skill builder include an eval/benchmark step, and what artifacts or state (eval cases, scores, variance reports) does it create and persist alongside the skill?

**Answer:** The skill-builder's own eval step is NOT FOUND (external skill). However the repo
HAS a full eval/benchmark harness for skill/agent prompts: a 5-stage pipeline driven by
`run_loop.sh` over `scripts/run_eval.py → grade.py → report.py → diagnose.py → revise.py`.
Eval CASES are defined in `evals/suite.json` (15 cases across QRSPI phases) and
`evals/graphite-evals.json` (5 cases for the Graphite skill). Persisted state: `run_eval.py`
writes `results.json` (per-trial outputs, tokens, transcripts, a `skill_hash`) into an output
dir; `report.py` builds a version ledger with score progression, regression/plateau/overfitting
flags; results land under `results/`. Cases carry weighted assertions and a 65/35 train/test
split (seed 42), 3 trials/case default.

**Evidence:**

```
output = {
    "skill_hash": skill_hash,
    "skill_path": config.skill_path,
    "suite": suite["name"],
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "config": {"trials": config.trials, "timeout_ms": config.timeout_ms},
    "results": all_results,
}
output_path = os.path.join(config.output_dir, "results.json")
```

— `scripts/run_eval.py:196-211`; suite definition `evals/suite.json:1-15`; pipeline doc `docs/eval-system.md:1-12`
**Dependencies:** `run_loop.sh` → `run_eval.py` (reads `suite.json`, the skill prompt file) → `grade.py` → `report.py`/`diagnose.py`/`revise.py`. Results persisted to `results/`.
**Implicit contracts:** A suite case requires `id`, `prompt`, `assertions` (validated in `run_eval.py:52-56`); a suite requires `name`, `cases` (`run_eval.py:47-50`). Assertions are weighted with types `programmatic` | `llm_judge` | `script`. NOTE: `execute_single` is a STUB — actual agent invocation is a placeholder (`run_eval.py:99-137`), so persisted `results.json` from the current code contains empty outputs until wired to a runtime.

## Q6: What conventions in this repo govern skill versioning or naming collisions — how is the skill name `writing-bash-scripts` validated against existing skills?

**Answer:** NOT FOUND — there is no skill-name validation, versioning, or collision-detection
code in the repo. Skills are not versioned per-skill; `run_eval.py` computes a `skill_hash`
(first 12 hex of SHA-256 of the prompt text) purely for eval-result tracking, not for naming.
The only de-facto collision rule is filesystem uniqueness: `.claude/skills/<name>/` directories
are unique by path, and the existing 10 skills are all `qrspi-*` plus `qrspi-work`. `writing-
bash-scripts` does not collide with any existing skill directory.
Search queries attempted: `grep -ri "skill name\|collision\|validate.*name\|kebab"` across repo —
no validator found; only filesystem-level uniqueness.

**Evidence:**

```
skill_hash = hashlib.sha256(skill_text.encode()).hexdigest()[:12]   # eval tracking only, not naming
```

— `scripts/run_eval.py:155`; existing skill set: `.claude/skills/` (qrspi-design/implement/plan/pr/questions/research/structure/ticket/work/worktree)
**Dependencies:** None — no validation module exists.
**Implicit contracts:** Skill names are lowercase kebab-case matching their directory (observed convention, not enforced). Uniqueness is guaranteed only by the filesystem. No semantic versioning of skills.

## Q7: How is the SKILL.md body size limit (under 500 lines / 5000 tokens) measured and enforced — is there a check that fails when the body exceeds it, and how are tokens counted?

**Answer:** NOT FOUND for SKILL.md specifically — there is no in-repo lint/check that measures
or enforces a SKILL.md body size limit, and no token counter for SKILL.md. The closest existing
mechanism is in the EVAL grader, which has line-count assertions for generated ARTIFACTS (not
SKILL.md): `grade.py` defines `line_count(filename, max_lines, ...)` and `suite.json` uses it
for design docs (`line_count('design.md') <= 300`). Token counting in the eval harness is a
config/usage field (`max_tokens`, `result.tokens`), not a body-size gate. No tool in the repo
counts SKILL.md tokens or fails on a 500-line / 5000-token threshold.
Search queries attempted: `grep -ri "500\|5000\|token.*count\|line.*limit\|max_lines" .claude scripts` —
matches only in eval artifact checks, none targeting SKILL.md.

**Evidence:**

```
def line_count(filename: str, max_lines: int, result: dict) -> tuple[bool, str]:
    output = result.get("output", "")
    count = len(output.splitlines())
    ok = count <= max_lines
    return ok, f"Line count: {count} (limit: {max_lines})"
```

— `scripts/grade.py:33-39`; usage `evals/suite.json:242` (`line_count('design.md') <= 300`)
**Dependencies:** Eval grader only; applies to output artifacts, not skill bodies.
**Implicit contracts:** Line counting = `len(output.splitlines())` (newline-based, not token-based). Token usage is recorded as `{"input": ..., "output": ...}` (`run_eval.py:135`) but never used as a size gate. The 500-line/5000-token SKILL.md limit is an external convention with no in-repo enforcement.

## Q8: What mechanism, if any, verifies the "ShellCheck-clean output" acceptance criterion — is ShellCheck available in this environment, and how would the skill's guidance be exercised to confirm output passes with zero warnings?

**Answer:** ShellCheck is NOT installed in this environment (`which shellcheck` → not found) and
is NOT in the devcontainer Dockerfile's apt install list. BATS is also absent. There is no
in-repo mechanism that runs ShellCheck against generated output. The only ShellCheck reference
in the entire repo is a `# shellcheck disable=SC2053` inline directive in a devcontainer config
script — i.e., the repo's own bash is WRITTEN to be ShellCheck-clean, but nothing automatically
verifies it. The Dockerfile installs: ca-certificates, curl, gh, git, gnupg, iptables, jq,
squid, nodejs (and npm globals incl. graphite-cli). No shellcheck/bats.
To confirm "zero warnings" one would need to install shellcheck first; no harness does this.

**Evidence:**

```
RUN apt-get update && apt-get install -y \
    ca-certificates \  curl \  gh \  git \  gnupg \  iptables \  jq \  squid \
    && rm -rf /var/lib/apt/lists/*
```

— `.devcontainer/Dockerfile:7-16` (no shellcheck/bats); only repo mention: `.devcontainer/config/protect-paths:116` (`# shellcheck disable=SC2053`)
**Dependencies:** None — no ShellCheck integration exists. Devcontainer would need a Dockerfile change to add `shellcheck`.
**Implicit contracts:** Existing repo bash scripts already follow ShellCheck-clean conventions (`#!/usr/bin/env bash`, `set -euo pipefail`) by hand — see `run_loop.sh:1-2`, `.devcontainer/config/*.sh:1-2`. The acceptance criterion is currently human/convention-enforced, not tooled.

## Q9: How does the skill builder handle the case where optional directories (`references/`, `scripts/`, `assets/`) are not needed — does it create empty directories, omit them, or leave placeholders?

**Answer:** The skill-builder's behavior is NOT FOUND (external skill). The OBSERVABLE repo
convention is omission: optional directories are simply not created when unneeded. 9 of 10
in-repo skills have only `SKILL.md` and no subdirectory at all; only `qrspi-work` created a
`references/` directory, and it did so because it actually contains content
(`review-cascade.md`). No skill in the repo contains an empty `references/`, `scripts/`, or
`assets/` directory or a placeholder/`.gitkeep` inside one. (Note: empty-dir omission is partly
a git artifact — git does not track empty directories — but the consistent pattern is
"directory exists only when it holds a file.")

**Evidence:**

```
.claude/skills/qrspi-design/      → SKILL.md only
.claude/skills/qrspi-questions/   → SKILL.md only
.claude/skills/qrspi-work/        → SKILL.md + references/review-cascade.md
(no empty references|scripts|assets dirs; no .gitkeep placeholders found except evals/golden/.gitkeep)
```

— `.claude/skills/` directory tree
**Dependencies:** None in-repo (external builder).
**Implicit contracts:** A subdirectory is present only when it holds at least one file. Placeholders are avoided. (The repo does use `.gitkeep` elsewhere — `evals/golden/.gitkeep` — but never inside a skill's optional dirs.)

## Q10: What test or eval harness exists for validating a skill's behavior in this repo, and what is the expected format of skill eval cases?

**Answer:** The harness is `evals/` + `scripts/` driven by `run_loop.sh`. Eval cases are JSON
objects in `evals/suite.json` (and `evals/graphite-evals.json`). Each case requires `id`,
`prompt`, `assertions` (enforced by `run_eval.py:52-56`); cases also carry `name`, `phase`,
`context` (`files`, `conversation_history`, `user_preferences`), `tags`, `difficulty`, and
`split`. Assertions are weighted objects with `type` ∈ {`programmatic`, `llm_judge`, `script`}:
programmatic checks name a function in `grade.py`'s registry (e.g., `output_file_exists(...)`,
`has_section(...)`, `line_count(...)`); `llm_judge` carries a natural-language `criteria`;
`script` runs an external script (e.g., `scripts/check_scope.py`) and reads its exit code.
A new "writing-bash-scripts" skill would add cases following this same schema.

**Evidence:**

```
{
  "id": "case_001", "name": "questions_happy_path", "phase": "questions",
  "prompt": "Generate questions for the following ticket.",
  "context": { "files": ["fixtures/ticket_rest_endpoint.md"], "conversation_history": [], "user_preferences": {} },
  "assertions": [
    { "type": "programmatic", "check": "output_file_exists('questions.md')", "weight": 1.0 },
    { "type": "llm_judge", "criteria": "Questions are specific and answerable by reading code", "weight": 2.0 }
  ],
  "tags": ["questions","happy-path","rest-endpoint"], "difficulty": "easy", "split": "train"
}
```

— `evals/suite.json:16-81`; case validation `scripts/run_eval.py:52-56`; assertion-type taxonomy `docs/eval-system.md` ("Assertion Types")
**Dependencies:** `run_loop.sh` → `run_eval.py` (loads suite + skill prompt) → `grade.py` (assertion registry) → `report.py`. Fixtures under `evals/fixtures/`.
**Implicit contracts:** `check` strings are literal calls into the `grade.py` registry — a new check name must have a matching function. `script` assertions interpret exit code + stdout. Train/test split is per-case (`"split": "train"|"test"`), 65/35 seed 42. CAVEAT: `run_eval.py:execute_single` is a stub (no real agent invocation yet — `run_eval.py:99-137`).

## Q11: How are the BATS-core and `BASH_SOURCE` testing recommendations the skill encodes themselves validated — is there existing tooling in the repo that runs bash tests the skill's guidance should align with?

**Answer:** NOT FOUND — there is no BATS installation and no bash-test runner in the repo. `bats`
is not on PATH and not in the Dockerfile. No `*.bats` test files exist, and no script invokes
BATS. The only bash test-runner-like tooling is the Python eval harness (`run_eval.py`), which
tests AGENT PROMPTS, not bash scripts. The repo's own bash scripts (`run_loop.sh`,
`.devcontainer/config/*.sh`) use conventions the skill should align with — `#!/usr/bin/env bash`
or `#!/bin/bash`, and `set -euo pipefail` — but there is no test harness exercising them and no
`BASH_SOURCE`-guarded "main" pattern present in any repo script.
Search queries attempted: `grep -ril "bats\|BASH_SOURCE\|BATS_"` → only matches in this ticket's
questions.md and a `protect-paths` comment; `find -name "*.bats"` → none.

**Evidence:**

```
run_loop.sh:1:#!/bin/bash
run_loop.sh:2:set -euo pipefail
.devcontainer/config/post-create.sh:1:#!/usr/bin/env bash
.devcontainer/config/post-create.sh:2:set -euo pipefail
```

— `run_loop.sh:1-2`; `.devcontainer/config/{initialize,post-create,post-start}.sh:1-2` (no BATS, no `BASH_SOURCE`)
**Dependencies:** None — no bash test runner. The Python eval harness is the only test tooling and it does not run bash.
**Implicit contracts:** Repo bash convention to align with: shebang + `set -euo pipefail` at top; positional-arg validation via `${1:?...}` (`run_loop.sh:11-12`). BATS-core and `BASH_SOURCE` guidance the skill encodes is currently UNvalidated by any repo tooling.

## Q12: How does the skill-builder report success, failures, and warnings during skill generation (e.g., frontmatter validation errors, size-limit violations) — where does that diagnostic output surface?

**Answer:** The skill-builder's reporting is NOT FOUND (external skill). The repo's analogous
diagnostic surface is the eval harness's stdout + JSON outputs. `run_eval.py` prints per-trial
`OK`/`ERROR` lines with durations to stdout and writes `results.json`; suite/case validation
raises `ValueError` with explicit missing-field messages (`run_eval.py:47-56`). `grade.py`
returns `(bool, message)` tuples per check (e.g., `"Section 'X' found/not found"`,
`"Line count: N (limit: M)"`). `report.py` builds a version ledger and flags
regressions/plateaus/overfitting; `diagnose.py` categorizes failures into 8 root causes
(`docs/eval-system.md`). So diagnostics surface as: stdout logs, `results.json`, and the
report/diagnose stages — not as a skill-generation validator.

**Evidence:**

```
status = "ERROR" if result.error else "OK"
print(f"  [{completed}/{total_runs}] {case_id} trial={trial} {status} ({result.duration_ms:.0f}ms)")
...
raise ValueError(f"Case {case.get('id', '?')} missing: {case_missing}")
```

— `scripts/run_eval.py:186-187` (stdout) and `:56` (validation error); grader message format `scripts/grade.py:27,39`; pipeline `docs/eval-system.md` ("Reporting", "Diagnosis")
**Dependencies:** `run_eval.py` (stdout + results.json) → `grade.py` (per-assertion messages) → `report.py`/`diagnose.py` (ledger, regression/plateau/overfitting flags, 8 failure categories).
**Implicit contracts:** Errors are raised as `ValueError` with the offending field set; per-check results are `(passed, human_message)` tuples; trial-level failures recorded in `result.error` and surfaced as `ERROR` in stdout and in `results.json`. There is no skill-generation-time frontmatter/size validator in-repo.

---

## Discovered Patterns

- **Skill = directory + single SKILL.md.** All 10 repo skills live at `.claude/skills/<name>/SKILL.md` with frontmatter keys in fixed order: `name`, `description`, `command`, `argument-hint`, `allowed-tools`. `name` always equals the directory name and the `command` suffix.
- **Lean body + lazy references.** Only `qrspi-work` splits content into `references/`; inclusion is a manual "Read references/<file>.md" instruction in the body, never an automatic include. (`SKILL.md:281`)
- **Thin-wrapper skills delegate to agents.** Most qrspi SKILL.md files are thin wrappers that spawn a `subagent_type` agent defined in `.claude/agents/qrspi-*.md`; prompt content lives in the agent, not the skill (`qrspi-research/SKILL.md:9-11`).
- **Bash convention in-repo:** `#!/usr/bin/env bash` (or `#!/bin/bash`) + `set -euo pipefail` + `${1:?usage}` arg guards. Written ShellCheck-clean by hand (`# shellcheck disable=` used surgically).
- **Eval harness is prompt-focused, three assertion types** (`programmatic` / `llm_judge` / `script`), weighted, with a train/test split (seed 42) and a 5-stage pipeline (`run_eval → grade → report → diagnose → revise`).
- **`.gitkeep` for intentionally-empty dirs** is used in `evals/golden/`, but never inside skill subdirectories.

## Inconsistencies

- **`run_eval.py` is a stub vs. its docstring/doc claims.** `docs/eval-system.md` and the module docstring describe executing cases "against a skill prompt" and collecting transcripts/tokens, but `execute_single` is an explicit placeholder that returns empty `output`/`files`/`tokens` and never invokes an agent (`scripts/run_eval.py:99-137`). Persisted `results.json` would be empty under the current code.
- **CLAUDE.md path drift.** `.claude/CLAUDE.md` (worktree copy) says "Agent prompt definitions live in `.qrspi/agents/`", but they actually live in `.claude/agents/` (`qrspi-research.md` etc.). The root project `.claude/CLAUDE.md` (main) correctly says `.claude/agents/`. `run_loop.sh:9` likewise references `.qrspi/agents/01-questions.md`, a path that does not exist in the repo.
- **External-skill assumption in the questions.** The questions repeatedly target a "skill-builder/skill-creator" as if it were in-repo; it is not. Any plan must treat skill scaffolding/validation conventions (frontmatter schema, ≤500-line limit, ShellCheck/BATS verification) as UN-enforced by repo tooling — they exist only as conventions or in the external global skill.
- **ShellCheck/BATS referenced but absent.** The skill's acceptance criteria (ShellCheck-clean, BATS-core testing) have NO supporting tooling installed: neither `shellcheck` nor `bats` is in the Dockerfile or on PATH (`.devcontainer/Dockerfile:7-16`).
