# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-04T00:00:00Z
**Generated:** 2026-06-04T00:00:00Z
**Status:** draft

## Q1: What is the on-disk directory structure of an existing skill in this repo (SKILL.md plus any references/, scripts/, assets/ subdirectories), and where do new skills get placed?

**Answer:** Skills live under `.claude/skills/<skill-name>/`. Each skill is a directory whose only required file is `SKILL.md`. Of the 10 existing skills, **9 are SKILL.md-only**; exactly one (`qrspi-work`) carries a `references/` subdirectory with offloaded detail. No existing skill ships a `scripts/` or `assets/` subdirectory (those scripts live at the repo-level `scripts/` dir instead). New skills are placed as a new sibling directory under `.claude/skills/`.

**Evidence:**

```
.claude/skills/
  qrspi-design/SKILL.md
  qrspi-implement/SKILL.md
  qrspi-plan/SKILL.md
  qrspi-pr/SKILL.md
  qrspi-questions/SKILL.md
  qrspi-research/SKILL.md
  qrspi-structure/SKILL.md
  qrspi-ticket/SKILL.md
  qrspi-work/SKILL.md
  qrspi-work/references/review-cascade.md   <-- only references/ in the repo
  qrspi-worktree/SKILL.md
```

— `.claude/skills/` (directory listing)

README documents the intended layout (slash-command wrappers under `skills/`):

```
  skills/              # Slash-command wrappers that invoke the phase agents
    qrspi-ticket/
    ...
    qrspi-work/        # Autonomous orchestrator (PR-gated state machine)
```

— `README.md:84-103`

**Dependencies:** Skills here are thin wrappers that reference agent prompts in `.claude/agents/<name>.md` (see Discovered Patterns). New "using git worktrees" skill is a leaf — nothing in the repo depends on it yet.
**Implicit contracts:** Directory name = skill `name` frontmatter field (verified Q5). A `references/<topic>.md` file is loaded on demand and pointed to from the body via a relative path (see Q7).

## Q2: How does the bare-repo bootstrap script's expected inputs and outputs flow — what arguments does a comparable existing bootstrap/setup script in this repo take, and where does it write output?

**Answer:** NOT FOUND — no bare-repo bootstrap script exists in the repo. The question targets a script the ticket asks to be *created*; there is no prior art for a "bare repo" bootstrap. The closest comparable scripts are the **self-locating Python helpers** `scripts/qrspi_persist.py` and `scripts/qrspi_resolve.py`. Their input/output convention is the relevant precedent:

- They take **short, token-free arguments** (`--ticket`, `--artifact`, `--assigned`), never long paths.
- They **self-locate the repo root** from `__file__` (not cwd, not an argument).
- They **emit a single JSON envelope on stdout** (`{ ok, repoRoot, ..., error? }`) and exit non-zero on failure.

Searched: `grep -rln "git worktree\|bare repo\|--bare\|--bare repo"` across `*.sh`/`*.py` — only worktree-*add* usage found, no bare-repo bootstrap.

**Evidence:**

```python
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(_SCRIPT_DIR)
...
parser.add_argument("--ticket", required=True, help="Ticket id, e.g. RUS-21")
parser.add_argument("--artifact", required=True, choices=ARTIFACTS, ...)
...
json.dump(env, sys.stdout, indent=2)
print()
return 0 if error is None else 1
```

— `scripts/qrspi_persist.py:40-41,91-92,112-114`

Envelope shape is documented in the module docstring:

```
Output: a single JSON envelope on stdout:
    { ok, repoRoot, src, dest, bytes, error? }
```

— `scripts/qrspi_persist.py:27-29`; resolve envelope at `scripts/qrspi_resolve.py:28`

**Dependencies:** Helpers are called by `.claude/workflows/qrspi-batch.js` and the `qrspi-work` skill (see `qrspi-work/SKILL.md:62`).
**Implicit contracts:** stdlib-only (no third-party imports); single JSON envelope on stdout; failure reported once as `ok:false` with a verbatim message, never retried (`scripts/qrspi_persist.py:23-25`).

## Q3: What does the Anthropic skill-builder skill require as inputs, and what artifacts does it emit (SKILL.md, references, scripts)?

**Answer:** NOT FOUND — the question targets a resource outside the project scope. The `skill-creator` skill is a globally-installed Claude Code skill, not vendored into `REPO_ROOT`. There is no `.claude/skills/skill-creator/` directory in this worktree, and the project firewall forbids reading global/`~/.claude` paths. What *can* be stated from in-repo evidence: the repo's own skills demonstrate the expected emitted artifacts — a `SKILL.md` with YAML frontmatter (Q4) plus optional `references/*.md` (Q1/Q7). No skill in this repo emits a bundled `scripts/` dir.

Searched: `ls .claude/skills/ | grep -i graphite` and `find . -iname "*skill-creat*"` — no match in repo.

**Dependencies:** N/A (out of scope).
**Implicit contracts:** The project's user-memory directive (CLAUDE.md / MEMORY index) states skills must be authored via the `skill-creator` skill and its eval loop — but that tooling lives outside the repo.

## Q4: What is the exact required SKILL.md frontmatter schema (required fields, name format, description format/length) per the agentskills.io standard as encoded in existing skills here?

**Answer:** Every existing SKILL.md opens with a YAML frontmatter block delimited by `---` lines. The fields used across all 10 skills are: `name`, `description`, `command`, `argument-hint`, `allowed-tools`. `name` is a lowercase-hyphen slug matching the directory. `description` is a single line stating what the skill does + when to use it ("Use when/after ..."), kept to ~1–3 sentences; the longest (`qrspi-work`) is multi-sentence and wrapped in double quotes because it contains colons/commas. The phase **agent** files (`.claude/agents/*.md`) use a different frontmatter (`name`, `description`, and a `claude:`/`tools:` block) — do not conflate the two.

**Evidence (skill frontmatter):**

```yaml
---
name: qrspi-research
description: Map codebase facts by answering questions from the Questions phase. The feature ticket is intentionally hidden. Use after questions are approved.
command: /qrspi-research
argument-hint: <ticket-id>
allowed-tools: Agent, Bash(pwd:*)
---
```

— `.claude/skills/qrspi-research/SKILL.md:1-7`

Quoted multi-sentence description when it contains punctuation:

```yaml
description: "Single entry point for autonomous QRSPI feature development. Use when the user asks to 'work on' a ticket (e.g., 'work on RUS-42'). ..."
```

— `.claude/skills/qrspi-work/SKILL.md:3`

**Dependencies:** The `command:` field wires the skill to a slash command; `allowed-tools` gates the tools the wrapper may use (most phase wrappers allow only `Agent, Bash(pwd:*)`).
**Implicit contracts:** `name` must equal the directory slug. `description` should encode a trigger ("Use when/after ..."). Frontmatter is required; bodies are markdown starting with an H1 `# /<command>` or `# <name>`.

## Q5: What naming convention do existing skills use for the skill name field and directory name (lowercase-hyphen), and does the new "using git worktrees" skill name need to match a directory slug?

**Answer:** All skill `name` fields are **lowercase-hyphen slugs** (`qrspi-design`, `qrspi-work`, etc.) and each **exactly matches its directory name**. Yes — the new skill's `name` must match its directory slug. A natural-language title like "using git worktrees" must be slugified, e.g. directory `.claude/skills/using-git-worktrees/` with `name: using-git-worktrees` (mirroring the existing global `using-graphite-cli` naming style referenced in available skills).

**Evidence:**

```
.claude/skills/qrspi-research/SKILL.md  ->  name: qrspi-research
.claude/skills/qrspi-work/SKILL.md      ->  name: qrspi-work
.claude/skills/qrspi-worktree/SKILL.md  ->  name: qrspi-worktree
```

— directory listing of `.claude/skills/` cross-referenced with each `name:` line (e.g. `.claude/skills/qrspi-research/SKILL.md:2`)

**Dependencies:** Claude Code's skill loader matches the directory/name pair to register the `command`.
**Implicit contracts:** No spaces, no uppercase, hyphen-separated; `name` == directory == (skill identity used by the Skill/Agent loader).

## Q6: How does this repo itself already use worktrees (the `.worktrees/<ticket-id>/` convention), and does that established pattern conflict with or differ from the bare-repo pattern the ticket asks the skill to recommend?

**Answer:** This repo uses **linked worktrees off a normal (non-bare) checkout**: the main checkout stays on `main`, and each ticket gets an isolated worktree at `.worktrees/<ticket-id>/` created with `git worktree add` (or `git worktree add -b <id>/design`). The orchestrator's `setup_worktree()` is the canonical implementation. This is the **`git worktree add`-from-main** model, NOT a bare-repo model where the `.git` itself is bare and *every* checkout (including the trunk) is a linked worktree. So there is a genuine difference: if the new skill recommends the bare-repo layout, that pattern differs from how this repo's own automation provisions worktrees.

**Evidence:**

```python
def setup_worktree(ticket, trunk="main", create_design=False):
    ...
    worktrees_dir = os.path.join(REPO_ROOT, ".worktrees")
    worktree = os.path.join(worktrees_dir, ticket)
    if os.path.isdir(worktree):
        return worktree  # reuse
    ...
    rc, _, err = _run(["git", "worktree", "add", "-b", "%s/design" % ticket, worktree, trunk], ...)
```

— `scripts/qrspi_resolve.py:130-167`

Convention documented:

```
**Worktree isolation.** Each ticket gets its own git worktree at `.worktrees/<ticket-id>/`.
Multiple agents can work on different tickets concurrently without branch checkout conflicts.
```

— `README.md:132`; also `.claude/CLAUDE.md` "### Worktrees" section ("The main repo checkout stays on `main`; all ticket work happens in worktrees. `.worktrees/` is gitignored.")

**Dependencies:** `qrspi_resolve.py` → `git worktree add` / `gt track`; consumed by `qrspi-batch.js` and `qrspi-work`.
**Implicit contracts:** Trunk is `main`; worktrees nest under `.worktrees/` (gitignored); each worktree is one Graphite-tracked branch (`gt track --parent main`). Reuse-if-exists, never leave a stray worktree for a no-op ticket (`scripts/qrspi_resolve.py:148-160`).

## Q7: How do existing skills keep SKILL.md bodies short and offload detail (under-500-line / under-5000-token constraint) — are large bodies split into `references/` files, and what is the splitting pattern?

**Answer:** Most phase-wrapper skills are **tiny** (25–35 lines) because they are thin wrappers that delegate all real content to the agent prompt in `.claude/agents/<name>.md` (see Q1/Discovered Patterns). The two larger bodies are `qrspi-ticket` (119 lines) and `qrspi-work` (565 lines). `qrspi-work` is the only skill that offloads detail into a `references/` file: heavy cascade logic lives in `references/review-cascade.md` and the body points to it with a relative-path mention rather than inlining it. That is the splitting pattern: keep procedural steps in `SKILL.md`, push large conditional/explanatory detail into `references/<topic>.md`, and reference it by relative path at the point of use.

**Evidence:**

```
282: phase's own artifacts (see `references/review-cascade.md`). Do NOT touch downstream phases
```

— `.claude/skills/qrspi-work/SKILL.md:282`, pointing at `.claude/skills/qrspi-work/references/review-cascade.md` (4158 bytes)

Line counts: research/structure/plan/worktree ~25–26; design/pr/questions ~26–28; implement 35; ticket 119; work 565.

**Dependencies:** Wrapper bodies depend on `.claude/agents/*.md` for substance; `qrspi-work` body depends on its `references/review-cascade.md`.
**Implicit contracts:** `references/*.md` is loaded on demand, not auto-injected; the body must explicitly cite it ("see `references/...`"). Thin wrappers stay short by delegating, not by truncating.

## Q8: What conventions does this repo follow for bash scripts (shellcheck cleanliness, shebang, error handling) that the bare-repo bootstrap script must conform to?

**Answer:** The repo's `.sh` files use a consistent header: a shebang of either `#!/usr/bin/env bash` (devcontainer scripts) or `#!/bin/bash` (`run_loop.sh`), immediately followed by `set -euo pipefail`. Errors are surfaced to **stderr** with an `error:` prefix and an explicit `exit 1` (fail-fast). Required positional args use the `${1:?Usage: ...}` parameter-expansion guard. There is no in-repo `.shellcheckrc`, but the patterns (quoted expansions, `set -euo pipefail`) are shellcheck-clean in spirit.

**Evidence:**

```bash
#!/usr/bin/env bash
set -euo pipefail
...
if ! docker info &>/dev/null; then
  echo "error: Docker Desktop is not running. Please start Docker and try again." >&2
  exit 1
fi
```

— `.devcontainer/config/initialize.sh:1-12`

```bash
#!/bin/bash
set -euo pipefail
...
SKILL_PATH=${1:?Usage: run_loop.sh <skill_path> <eval_suite> [max_iter] [target_score]}
```

— `run_loop.sh:1-12`

**Dependencies:** None special; scripts are invoked by the devcontainer lifecycle (`initializeCommand`/`postCreate`/`postStart`) or directly by the user.
**Implicit contracts:** shebang + `set -euo pipefail` on the first two lines; errors to stderr with `error:` prefix + `exit 1`; required args guarded with `${N:?...}`. (Project memory also mandates the `writing-bash-scripts` skill for shellcheck-clean output — that skill is global/out of scope.)

## Q9: For the submodule and shared-stash gotchas the skill must warn about, is there any existing repo guidance or script behavior that already touches git submodules or stash that the skill should stay consistent with?

**Answer:** NOT FOUND (in-repo). No script, doc, or skill in this worktree references `git submodule`, `git stash`, or the worktree-shared-stash gotcha. `grep -rln "submodule\|git stash"` across `*.md`/`*.py`/`*.sh`/`*.js` (excluding `.git/` and the RUS-30 questions artifact) returned **no functional match** — the grep hits for "worktree"/"bare" in `.claude/CLAUDE.md`, `README.md`, `docs/*.md`, `scripts/qrspi_pr_state.py`, `scripts/qrspi_resolve.py` are all about `git worktree add`, not submodules/stash. The only git-mutation guidance is the global `using-graphite-cli` skill (not vendored in this worktree — no `.claude/skills/*graphite*` dir). So there is no existing in-repo behavior the skill must stay consistent with on submodules/stash; the skill would be introducing that guidance fresh.

**Dependencies:** N/A.
**Implicit contracts:** Git mutations in this project are funneled through Graphite (`gt`), per `.claude/CLAUDE.md` and the global `using-graphite-cli` skill; any worktree skill should respect that `gt`-first posture.

## Q10: How are skills verified in this repo — does the skill-creator skill provide an eval loop, and what is the status of the `evals/` + `scripts/run_eval.py` harness?

**Answer:** The `evals/` + `scripts/run_eval.py` harness is a **non-functional placeholder**. `run_eval.py`'s `execute_case()` is an explicit stub: it never invokes an agent, returns empty output/zero tokens, and its docstring says "In a real implementation, this would..." with a commented-out `agent.run(...)` block. `evals/` contains fixtures, a `suite.json`, and a `golden/.gitkeep` but no working runner. `.claude/CLAUDE.md` states verbatim that the harness is "a **non-functional placeholder** — verify pure logic with the unit tests and orchestration changes with manual end-to-end runs." The `skill-creator` eval loop is a global skill, out of scope (Q3). So in-repo skill verification = unit tests (Q11) + manual e2e, NOT the eval harness.

**Evidence:**

```python
#   response = agent.run(
#       system_prompt=skill_text, ...
#   )
...
messages = build_messages(case)
result.output = ""
result.files = []
result.tokens = {"input": 0, "output": 0}
```

— `scripts/run_eval.py:101-137` (docstring line 107: "This stub captures the structure for integration with / the actual agent runtime.")

**Dependencies:** `run_loop.sh` orchestrates `run_eval.py` + `grade.py` + `report.py` + `diagnose.py` + `revise.py` — but all bottom out on the stubbed executor.
**Implicit contracts:** Do not rely on the eval harness for correctness; it is structural scaffolding only. (Confirmed also in project MEMORY: "Eval harness is a placeholder.")

## Q11: What test pattern do existing repo scripts follow (the stdlib-only `_test.py` siblings), and would the bare-repo bootstrap shell script need a comparable test?

**Answer:** Every tested helper has a sibling `<module>_test.py` in the same `scripts/` dir, using **stdlib `unittest` only** (no pytest, no third-party). Tests import the module under test directly (`import qrspi_persist as qp`), target the module's **pure helper functions** (e.g. `staging_path`, `dest_path`, `persist`), and run with `python3 scripts/<module>_test.py`. Filesystem tests use `tempfile.TemporaryDirectory()`. Existing test siblings: `qrspi_persist_test.py`, `qrspi_pr_state_test.py`, `qrspi_resolve_state_test.py`, `qrspi_resolve_test.py`. A bare-repo bootstrap **shell** script has no Python sibling pattern to mirror directly; the repo precedent is that *pure logic* gets stdlib-only unit tests. To follow the convention, a bash bootstrap would either be kept thin and verified via manual e2e (per Q10) or have its testable logic extracted; there is no existing `.sh`-test harness (e.g. bats) in the repo to mirror.

**Evidence:**

```python
#!/usr/bin/env python3
"""Stdlib-only unit tests for qrspi_persist.py. Run: python3 scripts/qrspi_persist_test.py"""
import os, tempfile, unittest
import qrspi_persist as qp

class StagingPathTest(unittest.TestCase):
    def test_token_free_construction(self):
        p = qp.staging_path("/tmp/phase-stage", "RUS-21", "plan")
        self.assertEqual(p, "/tmp/phase-stage/RUS-21/plan.md")
        self.assertNotIn("qrspi", p)
```

— `scripts/qrspi_persist_test.py:1-16`

**Dependencies:** Tests import the sibling module by name (requires running from `scripts/` or with it on the path).
**Implicit contracts:** stdlib-only; test file named `<module>_test.py`; tests cover pure helpers; run with `python3`. No bash test framework present.

## Q12: How do existing skills and scripts surface errors and progress (logging, echoed status, error-surfacing conventions) so the bare-repo bootstrap script reports its steps consistently?

**Answer:** Two distinct conventions:
1. **Python helpers** report a single JSON envelope on stdout with `ok`/`error` keys and exit non-zero on failure; they never retry (`scripts/qrspi_persist.py:23-25,102-114`).
2. **Bash scripts** echo human-readable progress and send errors to stderr with an `error:` prefix + `exit 1` (Q8 evidence).
3. **Skills/agents** follow a strict **HARD STOP / error-surfacing** discipline: on any infra/auth/config/tooling error, print the *exact* failing command and *verbatim* error and stop immediately — no workarounds, no retries (beyond an at-most-once retry where explicitly allowed). This matches the user's global "error surfacing over workarounds" directive. A bootstrap script should therefore: echo each step (create/configure/first-worktree), surface failures verbatim to stderr, exit non-zero, and not attempt recovery.

**Evidence:**

```
3. `gh`/`git`/`gt` ... that is a **hard stop** — print the verbatim `error` and exit. Never retry it
...
### HARD STOP: Infrastructure Errors Are Not Puzzles To Solve
... permission denied, expired auth, config ...
1. **STOP. Do not execute another command.** Not "one more try."
```

— `.claude/skills/qrspi-work/SKILL.md:74,547-553` (also lines 53-54, 91-92, 409, 541-543)

Linear/projection writes are deliberately *best-effort* and warn-and-continue rather than hard-stop:

```
(`WARN: Linear projection to <state> failed: <error>`) and **continue** — never hard-stop
```

— `.claude/skills/qrspi-work/SKILL.md:396`

**Dependencies:** Skills call the JSON-emitting Python helpers and parse `ok`/`error`; they translate a helper's `ok:false` into a hard stop.
**Implicit contracts:** Reversible/projection steps warn-and-continue; irreversible/infra failures hard-stop with the verbatim error. Progress is echoed step-by-step; errors go to stderr (bash) or the `error` envelope key (python).

---

## Discovered Patterns

- **Skill = thin wrapper, agent = substance.** The phase skills under `.claude/skills/qrspi-*/SKILL.md` are 25–35-line wrappers; the real prompt logic lives in the paired `.claude/agents/qrspi-*.md` file. The skill body's job is to parse `$ARGUMENTS`, resolve `REPO_ROOT` from `pwd`, and spawn the agent via the `Agent` tool (`.claude/skills/qrspi-research/SKILL.md:9-26`). A "using git worktrees" skill that is *content* (guidance), not an agent-spawner, would be self-contained in SKILL.md (+ optional `references/`), more like a global how-to skill than these phase wrappers.
- **Self-locating, token-free script design.** Helpers derive `REPO_ROOT` from `__file__` and accept only short args, specifically to defeat a weak worker model that mangles the literal `qrspi` token in long paths (`scripts/qrspi_persist.py:8-25,37-41`; project MEMORY "Ollama worker path mangling"). Any new script should follow this.
- **Single-JSON-envelope stdout contract** for every Python helper (`{ok, ..., error?}`), non-zero exit on failure, no retries.
- **Worktrees are `git worktree add` off `main`**, gitignored under `.worktrees/`, one Graphite-tracked branch each — not a bare-repo layout.
- **stdlib-only `unittest` siblings** named `<module>_test.py`, run with `python3`.
- **Bash header standard:** shebang + `set -euo pipefail` on lines 1–2; errors to stderr with `error:` prefix; required args via `${N:?...}`.

## Inconsistencies

- **Worktree model mismatch (bare-repo vs. linked-from-main).** The repo's own automation provisions worktrees with `git worktree add ... <trunk>` from a normal checkout on `main` (`scripts/qrspi_resolve.py:130-167`, `README.md:132`), i.e. NOT a bare-repo layout. If the ticket's skill recommends the bare-repo pattern, that guidance differs from this repo's established convention — worth flagging so the skill either reconciles the two or scopes its bare-repo advice as general/external rather than "how this repo does it."
- **Two different frontmatter schemas under `.claude/`.** Skill files use `name/description/command/argument-hint/allowed-tools` (`.claude/skills/qrspi-research/SKILL.md:1-7`), while agent files use `name/description/claude:{tools:...}` (`.claude/agents/qrspi-research.md:1-6`). Easy to conflate; a new skill must use the *skill* schema.
- **`.claude/CLAUDE.md` drift between worktree and main.** This worktree's `.claude/CLAUDE.md` omits the `using-graphite-cli` reviewer/`qrspi_resolve.py reviewers` sections present in the main checkout's instructions, and names the Linear team/project inline ("team: Russelltsherman, project: QRSPI") rather than sourcing from config. Not load-bearing for this skill, but the worktree is a slightly older snapshot of project instructions.
- **Eval harness claims vs. reality.** `run_eval.py`'s module docstring describes "Runs each test case multiple trials in isolated environments, capturing full transcripts" (`scripts/run_eval.py:3-6`), but `execute_case()` is an explicit stub returning empty output (`scripts/run_eval.py:101-137`). The docstring overstates current capability; `.claude/CLAUDE.md` correctly labels the harness a non-functional placeholder.
