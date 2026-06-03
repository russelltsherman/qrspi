# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-03T00:00:00Z
**Generated:** 2026-06-03T00:00:00Z
**Status:** draft

## Q1: What is the standard agentskills.io directory layout and which files are mandatory versus optional, as established by the existing skills in `.claude/skills/` and `.claude/agents/`?

**Answer:** This repo separates **skills** (slash-command wrappers) from **agents** (the prompt bodies they spawn). The convention is documented in `.claude/CLAUDE.md`: "Phase agent definitions live in `.claude/agents/`; their slash-command wrappers live in `.claude/skills/`".

- `.claude/skills/<skill-name>/SKILL.md` — one directory per skill, each containing a **mandatory** `SKILL.md`. All 10 QRSPI skills follow this exactly (`qrspi-design/`, `qrspi-implement/`, `qrspi-plan/`, `qrspi-pr/`, `qrspi-questions/`, `qrspi-research/`, `qrspi-structure/`, `qrspi-ticket/`, `qrspi-work/`, `qrspi-worktree/`).
- `.claude/skills/<skill-name>/references/` — **optional** supplementary docs. Only `qrspi-work/references/review-cascade.md` exists; it is the sole `references/` directory in the repo.
- `.claude/agents/<name>.md` — **optional** for a skill; present when the skill is a "thin wrapper" that spawns an agent. 8 agent files exist (no agent for `qrspi-ticket` or `qrspi-work`, which do the work inline).

**Evidence:**

```
.claude/skills/qrspi-work/SKILL.md
.claude/skills/qrspi-research/SKILL.md
...
.claude/skills/qrspi-work/references/review-cascade.md   <-- only references/ dir
```

```
.claude/agents/qrspi-design.md   qrspi-implement.md   qrspi-plan.md   qrspi-pr.md
qrspi-questions.md   qrspi-research.md   qrspi-structure.md   qrspi-worktree.md
```

— `.claude/CLAUDE.md` (Codebase conventions: "Phase agent definitions live in `.claude/agents/`; their slash-command wrappers live in `.claude/skills/`")
**Dependencies:** A `SKILL.md` with `allowed-tools: Agent` references a sibling `.claude/agents/<name>.md` via `subagent_type`.
**Implicit contracts:** The skill directory name, the `name:` frontmatter field, the `command:` (`/<name>`), and the agent's `name:` all match (`qrspi-research` everywhere). A skill is mandatory; an agent file and a `references/` dir are optional.

## Q2: Where should a newly authored skill physically live in this repo, and what is the naming convention for the skill directory and its `SKILL.md`?

**Answer:** A new skill lives at `.claude/skills/<skill-name>/SKILL.md`. The directory name is the kebab-case skill name and matches the `name:` frontmatter and the `command:` value (without the leading slash). Every existing skill uses the `qrspi-` prefix because they are workflow-phase skills; a glab skill is not a QRSPI phase, so the prefix convention is project-area-specific, not universal — but the kebab-case dir==name==command identity is universal. Optional supporting docs go under `.claude/skills/<skill-name>/references/`.

**Evidence:**

```
name: qrspi-research
description: Map codebase facts ...
command: /qrspi-research
```

— `.claude/skills/qrspi-research/SKILL.md:1-6` (dir `qrspi-research/` == `name` == `command` `/qrspi-research`)
**Dependencies:** None for placement; the slash-command name is derived from the directory/`command:` field.
**Implicit contracts:** dir name == `name:` == `command:` (minus `/`). Frontmatter `command:` always starts with `/`.

## Q3: What frontmatter fields does a valid `SKILL.md` require (name, description, and any others), and what format constraints exist on the `description` field used for trigger matching?

**Answer:** Across all 10 SKILL.md files the frontmatter fields used are: `name`, `description`, `command`, `argument-hint`, and `allowed-tools`. `name` and `description` appear in every file; `command` and `argument-hint` appear in every file; `allowed-tools` appears in every file. The agent files (`.claude/agents/*.md`) use a different, smaller frontmatter: `name`, `description`, and a nested `claude:` block with `tools:` (e.g. `qrspi-research.md:1-6`).

`description` format constraints observed:
- It is the trigger-matching string. Most are a short capability sentence plus a "Use when…" clause (e.g. qrspi-research: "Map codebase facts… Use after questions are approved.").
- When the description contains commas/colons or example phrases, it is wrapped in double quotes (only `qrspi-work` does this; its description embeds quoted examples like `'work on RUS-42'` and lists trigger variants).
- Descriptions enumerate concrete trigger phrases for auto-invocation (qrspi-work lists "'work on <ticket-id>', 'continue <ticket-id>', 'pick up <ticket-id>'").

**Evidence:**

```
name: qrspi-work
description: "Single entry point for autonomous QRSPI feature development. Use when
the user asks to 'work on' a ticket (e.g., 'work on RUS-42'). ... Trigger on any
variant of: 'work on <ticket-id>', 'continue <ticket-id>', 'pick up <ticket-id>'..."
command: /qrspi-work
argument-hint: <ticket-id>
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, mcp__linear-russelltsherman__get_issue, ...
```

— `.claude/skills/qrspi-work/SKILL.md:1-9`

```
name: qrspi-research
description: Internal QRSPI workflow agent — maps codebase facts ... Not for general codebase exploration.
claude:
  tools: Read, Write, Glob, Grep
```

— `.claude/agents/qrspi-research.md:1-6`
**Dependencies:** `allowed-tools` gates which tools the skill may call (e.g. `Agent`, `Bash(pwd:*)`, specific Linear MCP tools); agent `claude.tools` gates the spawned agent.
**Implicit contracts:** Required-in-practice fields for a skill: `name`, `description`, `command`, `argument-hint`, `allowed-tools`. Quote the `description` when it contains YAML-significant punctuation. NOTE: the authoritative "required vs optional frontmatter" rules live in the global **skill-creator** skill, which is OUTSIDE `REPO_ROOT` (see Inconsistencies); the above is inferred from in-repo examples only.

## Q4: What subcommand groups and flags must the glab skill body and `references/` enumerate to satisfy coverage (auth, mr, issue, ci/pipeline, release, changelog, repo, api), and how do existing reference-heavy skills split content between `SKILL.md` and `references/`?

**Answer (split pattern):** There is exactly ONE reference-heavy skill in the repo: `qrspi-work`. Its `SKILL.md` (~370 lines) holds the operational procedure (entry point, per-action handlers, git/graphite rules, hard-stop rules) inline, while it factors out a single conceptual deep-dive — the cascade decision logic — into `references/review-cascade.md`. The body links to the reference rather than inlining it: "the cascade is bounded to the phase's own artifacts (see `references/review-cascade.md`)".

**Answer (glab coverage enumeration):** NOT FOUND in the codebase — there is no existing `glab`/GitLab content. Searched `grep -rni 'glab\|gitlab'` across `*.md/*.py/*.js`; the only hits are inside the input artifact `.qrspi/RUS-13/questions.md` itself. The closest analog is the **graphite** CLI skill captured in `evals/graphite-evals.json`, whose 5 eval cases cover commit, submit, log, move, sync — i.e. the eval suite enumerates the CLI subcommands/flags a CLI skill must handle. The actual graphite SKILL.md is not in this repo (it is a global skill).

**Evidence:**

```
2  "skill_name": "graphite",
...
{"text": "Uses gt create or gt modify (not raw git commit)", "type": "command_check"},
{"text": "Includes --no-interactive flag", "type": "flag_check"},
```

— `evals/graphite-evals.json:1-13` (analog CLI-skill coverage pattern)

```
address it ... (see references/review-cascade.md). Do NOT touch downstream phases here
```

— `.claude/skills/qrspi-work/SKILL.md` (action: revise section) and `references/review-cascade.md:1-77`
**Dependencies:** A glab skill would have no existing in-repo precedent for GitLab subcommands; the graphite skill (external) and `graphite-evals.json` are the structural analog.
**Implicit contracts:** Split rule observed: keep the runnable procedure + safety rules in `SKILL.md`; extract a single cohesive conceptual topic into one `references/*.md` and link to it from the body.

## Q5: How is authentication state and multi-host configuration represented for glab (`~/.config/glab-cli/config.yml`, `GITLAB_TOKEN`, `--hostname`), and is there an existing repo convention for documenting credential/config handling in a skill?

**Answer:** NOT FOUND for glab specifically — no `glab-cli`, `GITLAB_TOKEN`, or `~/.config/glab-cli/config.yml` reference exists in the repo (searched `grep -rni glab\|gitlab`; only the questions.md input mentions them). The paths the question names (`~/.config/glab-cli/`) are also OUTSIDE `REPO_ROOT` and outside research scope.

**Repo convention for credential/config in a skill:** The existing pattern is to NOT touch global config and to treat auth/config failures as HARD STOPs rather than documenting credential setup. `qrspi-work` SKILL.md's "HARD STOP: Infrastructure Errors" section explicitly forbids "routing around config via env vars (`XDG_CONFIG_HOME`); copying config files elsewhere; deleting/recreating config dirs" and treats expired auth / inaccessible config as a stop-and-report event. The agent files repeat a one-line HARD STOP on "auth failure, config error".

**Evidence:**

```
Explicitly forbidden: chmod/chown; routing around config via env vars
(XDG_CONFIG_HOME); copying config files elsewhere; deleting/recreating config dirs;
using raw git to bypass a broken gt; sudo/escalation; any action whose purpose is
"make the failing tool work again."
```

— `.claude/skills/qrspi-work/SKILL.md` (HARD STOP: Infrastructure Errors section)
**Dependencies:** Global tool config (`~/.config/...`) is out of scope; the convention is to defer to the human, not document credential setup procedurally.
**Implicit contracts:** Skills assume the CLI is already authenticated in the environment; auth/config errors are surfaced verbatim and the skill exits, never self-heals.

## Q6: What invocation/eval mechanism does the skill-creator skill provide for measuring trigger accuracy and skill performance, and what state does it persist between eval runs?

**Answer:** The **skill-creator** skill itself is OUTSIDE `REPO_ROOT` (a global skill, not present in `.claude/skills/`) — NOT FOUND in project scope. What exists in-repo is the QRSPI **eval harness** (`scripts/run_eval.py` + `scripts/grade.py` + `report.py` + `diagnose.py` + `revise.py`, driven by `evals/suite.json` and `evals/graphite-evals.json`). Mechanism per `docs/eval-system.md`: a 5-stage pipeline — execute (`run_eval.py`), score (`grade.py`), compare/regression (`report.py`), categorize failures (`diagnose.py`), propose edits (`revise.py`).

State persisted between runs: `run_eval.py` computes a `skill_hash` (sha256[:12] of the skill text) and writes a `results.json` to the output dir containing `skill_hash`, `skill_path`, `suite`, timestamp, config, and per-trial results; `report.py` "builds a version ledger and checks promotion criteria." Trigger accuracy specifically: `evals/graphite-evals.json` carries trigger/command/flag/safety assertions; trial count default is 3, seed 42, 65/35 train/test split.

**CRITICAL:** `.claude/CLAUDE.md` states the eval harness is a **non-functional placeholder** — `run_eval.py:execute_single` returns empty output (a stub awaiting real agent-runtime integration).

**Evidence:**

```python
# ── Placeholder for agent execution ──
# Replace this block with actual agent invocation:
...
result.output = ""
result.tokens = {"input": 0, "output": 0}
```

— `scripts/run_eval.py:116-137`

```python
skill_hash = hashlib.sha256(skill_text.encode()).hexdigest()[:12]
...
output_path = os.path.join(config.output_dir, "results.json")
```

— `scripts/run_eval.py:155, 209-211`
**Dependencies:** `grade.py`/`report.py`/`diagnose.py` consume `results.json` produced by `run_eval.py`.
**Implicit contracts:** Eval results are keyed by a content hash of the skill prompt so versions are comparable; persisted state is `results.json` + a version ledger. The execution stage is currently a no-op stub.

## Q7: How should the skill document non-interactive/scripted use — exit codes, JSON output parsing via `jq`, and `glab ci status --wait` for merge-after-green — and do existing skills establish a pattern for agent-specific scripted guidance?

**Answer (glab specifics):** NOT FOUND for glab (`glab ci status --wait`, etc.) — no glab content exists.

**Repo pattern for scripted/non-interactive CLI guidance:** Yes, strongly established by `qrspi-work` SKILL.md's "Git/Graphite Rules": every CLI invocation appends `--no-interactive`, commit messages use heredoc, and the skill instructs verifying state after mutations (`gt log short --no-interactive`). JSON output + parsing is demonstrated with `gh`: the revise section shows `gh pr view <number> --json reviews,comments --jq '...'` and a raw `gh api graphql ... --jq '...'`. The deterministic-resolver pattern (`scripts/qrspi_resolve.py`, `qrspi_pr_state.py`) wraps multi-step CLI flows into one self-locating script that emits a single JSON envelope (`{"ok": true, ...}`) the caller parses — the repo's preferred way to make scripted CLI use robust.

**Evidence:**

```
gh pr view <number> --json reviews,comments --jq '.reviews[] | select(.state != "APPROVED")'
gh api graphql -f query='...reviewThreads...' -F o="$OWNER" -F r="$REPO" -F n=<number> \
  --jq '.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved==false)'
```

— `.claude/skills/qrspi-work/SKILL.md` (action: revise, step 2)

```
- All gt commands include --no-interactive.
- After mutations, run gt log short --no-interactive to verify stack state.
```

— `.claude/skills/qrspi-work/SKILL.md` (Git/Graphite Rules)
**Dependencies:** `qrspi_pr_state.py` shells out to `gh` GraphQL and raises `RuntimeError` on failure (`qrspi_pr_state.py:142`).
**Implicit contracts:** Non-interactive flag on every CLI call; parse JSON with `--jq`/`jq`; prefer a single self-locating script emitting one JSON envelope over multi-step shell. Exit-code handling: scripts raise on non-zero subprocess results.

## Q8: How are self-hosted GitLab instances (`--hostname gitlab.company.com`) versus gitlab.com handled, and what conflicts arise when multiple authenticated hosts exist in `config.yml`?

**Answer:** NOT FOUND — no GitLab host/hostname handling exists in the repo (searched `glab`/`gitlab`/`hostname`; only matches are in the questions.md input). The repo's only multi-target precedent is GitHub `OWNER/REPO` resolution inside `scripts/qrspi_resolve.py` / `qrspi_pr_state.py` (uses `gh` against a single inferred repo). The `~/.config/glab-cli/config.yml` path is outside `REPO_ROOT` and out of scope. No convention for resolving host conflicts exists to cite.

**Evidence:** Search returned zero in-repo hits outside the input artifact:

```
.qrspi/RUS-13/questions.md:36: Q8: How are self-hosted GitLab instances (--hostname ...) ...
```

— (only occurrence of "--hostname" in scope is the question text itself)
**Dependencies:** None in scope.
**Implicit contracts:** None established; this is greenfield for the codebase.

## Q9: What is the documented behavior when an MR already exists on the current branch, when a release tag does not yet exist (`--ref`), or when a pipeline is failing at merge time — and how should the skill encode these judgment-call branches?

**Answer (glab MR/release/CI specifics):** NOT FOUND — no glab/MR/release content.

**Repo pattern for encoding judgment-call branches (the structural analog):** `qrspi-work` SKILL.md encodes "PR already exists / stale association" and "PR was closed/merged" as **named, recognized states** with explicit recovery sequences, NOT as errors. Examples: "Resubmitting when the prior PR was closed or merged" (rename-stale → rename-back → `gt submit --force`) and "Proactively check for a stale PR association before every `gt submit`." The rule of thumb is encoded as a one-line decision ("same phase → revise in place; upstream phase with downstream open → reset" in `review-cascade.md:76`). The pattern: enumerate each branch as a state, give a deterministic handler, and distinguish "recognized state" from "infrastructure HARD STOP."

**Evidence:**

```
Graphite pins each branch to the first PR it created ... After a reset/rework closed a PR,
that association is stale and gt submit refuses to open a fresh PR. Recovery (...):
gt rename <branch>-stale --no-interactive   # detaches the dead PR
gt rename <branch>        --no-interactive   # restores the canonical name
gt submit --publish --force --no-edit --no-interactive # creates a brand-new PR
... This is a recognized state, not an infrastructure error — the HARD STOP rule does not apply.
```

— `.claude/skills/qrspi-work/SKILL.md` (Resubmitting section)
**Dependencies:** Recovery handlers depend on the CLI's own state model (Graphite's `.git/.graphite_pr_info`).
**Implicit contracts:** Judgment-call branches are documented as discrete named states with deterministic handlers; "recognized state" is explicitly differentiated from "HARD STOP infrastructure error."

## Q10: What constitutes a passing verification for a skill in this repo (the SKILL.md body under 500 lines / 5000 tokens, valid frontmatter, eval harness status), and which checks are real versus placeholder?

**Answer:** Two verification mechanisms exist, with a sharp real-vs-placeholder split documented in `.claude/CLAUDE.md`:

- **REAL:** stdlib-only unit tests (`scripts/qrspi_*_test.py`, run with `python3`) verify pure logic; orchestration is verified by manual end-to-end runs. `.claude/CLAUDE.md`: "verify pure logic with the unit tests and orchestration changes with manual end-to-end runs."
- **PLACEHOLDER:** the `evals/` + `scripts/run_eval.py` harness is explicitly "a **non-functional placeholder**." Its `grade.py` check registry IS real code (e.g. `line_count`, `output_file_exists`, `has_section`, `question_count`, `no_solution_language`), but the executor (`run_eval.py:execute_single`) returns empty output, so scores are not meaningful end-to-end.

The "500 lines / 5000 tokens" acceptance threshold from the question is NOT a documented repo rule — NOT FOUND. The only line-limit machinery is `grade.py:line_count(filename, max_lines)` which checks `len(output.splitlines()) <= max_lines` against a per-assertion `max_lines` (no hardcoded 500). No token-count check exists in `grade.py`. The 500-line/5000-token figure likely originates from the global skill-creator skill (out of scope). The repo does have a 500-**word** convention, but it is for ticket bodies, not SKILL.md (`qrspi-ticket/SKILL.md:33`: "500 words max for the entire ticket body").

**Evidence:**

```python
def line_count(filename: str, max_lines: int, result: dict) -> tuple[bool, str]:
    output = result.get("output", "")
    count = len(output.splitlines())
    ok = count <= max_lines
    return ok, f"Line count: {count} (limit: {max_lines})"
```

— `scripts/grade.py:35-40`

```
- The evals/ + scripts/run_eval.py harness is a non-functional placeholder — verify
  pure logic with the unit tests and orchestration changes with manual end-to-end runs
```

— `.claude/CLAUDE.md` (Codebase conventions)
**Dependencies:** `grade.py` checks consume `run_eval.py` output (currently empty/stub).
**Implicit contracts:** A passing skill = valid frontmatter + (for logic) green unit tests + manual e2e. Eval scores are NOT a real gate. There is no in-repo 500-line/5000-token threshold.

## Q11: How can token/line count of `SKILL.md` be measured against the 500-line / 5000-token acceptance threshold using existing repo tooling or scripts?

**Answer:** No dedicated token/line-count tool for SKILL.md exists in the repo — NOT FOUND. The only line-counting code is `grade.py:line_count` (Q10), which operates on eval `result["output"]`, not on a SKILL.md file path, and takes `max_lines` as a parameter (no 500 default). There is NO token-counting utility anywhere: `grep -rni 'token' scripts/` returns only (a) the eval `tokens` dataclass field stubbed to `{"input":0,"output":0}` in `run_eval.py`, and (b) the unrelated "qrspi-token" path-mangling discussion in `qrspi_persist.py`/`qrspi_resolve.py` (a different meaning of "token" — the literal substring "qrspi"). To measure a SKILL.md today one would use a generic shell tool (e.g. `wc -l`); no project script wraps it.

**Evidence:**

```python
result.tokens = {"input": 0, "output": 0}   # stubbed, not a real measurement
```

— `scripts/run_eval.py:135`

```
scripts/grade.py:35: def line_count(filename, max_lines, result)   # eval-output only, param-driven limit
```

— grep results: no `wc -l`, no tokenizer, no 5000 constant in scripts.
**Dependencies:** None — no tooling.
**Implicit contracts:** None established; measuring SKILL.md size is currently ad-hoc (shell `wc`), and the 500/5000 thresholds are external (skill-creator), not repo-enforced.

## Q12: How do existing skills surface command failures and errors to the agent (exit-code handling, error-message conventions), and what does the skill-creator skill recommend documenting for observable failure modes in a CLI skill?

**Answer (in-repo conventions — REAL):** Every QRSPI skill/agent uses a uniform error-surfacing convention:

1. **HARD STOP block** — repeated verbatim across `qrspi-work/SKILL.md` and every `.claude/agents/*.md`: on permissions/auth/config/tooling errors (EACCES, permission denied, expired auth, "command not found", config inaccessible) → "STOP IMMEDIATELY. Print the exact failing command and exact error output. Do not execute another command… Do not attempt workarounds."
2. **Verbatim error propagation** — print the exact command + full unmodified output; never paraphrase.
3. **Recognized-state vs infrastructure-error distinction** — recoverable CLI states (stale PR, closed PR) get handlers and are explicitly excluded from HARD STOP (Q9).
4. **Best-effort vs gating writes** — Linear projection failures `WARN` and continue; git/PR failures STOP.
5. **Script-level**: Python helpers raise `RuntimeError` with the failing command + stderr (e.g. `qrspi_pr_state.py:142`: `raise RuntimeError("gh graphql failed for %s: %s" % (head, res.stderr.strip()))`), and `qrspi_resolve.py` emits `{"ok": false, "error": ...}` for the caller to hard-stop on.

**Answer (skill-creator recommendations):** NOT FOUND — skill-creator is a global skill outside `REPO_ROOT`; its CLI-failure-documentation recommendations cannot be cited from project scope.

**Evidence:**

```
If ANY command fails with a permissions error, auth failure, config error, or tooling
error (EACCES, permission denied, token expired, command not found, config inaccessible):
STOP IMMEDIATELY. Print the exact failing command and exact error output. Do not execute
another command. ... Do not attempt workarounds. ... Exit and report the error.
```

— `.claude/agents/qrspi-research.md:58` (identical block in qrspi-implement.md:59, qrspi-pr.md:54)

```python
raise RuntimeError("gh graphql failed for %s: %s" % (head, res.stderr.strip()))
```

— `scripts/qrspi_pr_state.py:142`
**Dependencies:** Skills depend on subprocess exit codes / raised exceptions from the helper scripts; orchestrator branches on the `{"ok": ...}` envelope.
**Implicit contracts:** Errors are surfaced verbatim; infrastructure errors are a non-negotiable HARD STOP (no self-healing); recognized recoverable states are handled explicitly; non-gating side-effects (Linear) warn-and-continue.

---

## Discovered Patterns

- **Skill = thin wrapper, agent = prompt body.** Most QRSPI skills (`qrspi-research`, `-design`, `-plan`, `-pr`, `-questions`, `-structure`, `-worktree`, `-implement`) are "thin wrappers that spawn the `<name>` agent. All prompt content lives in `.claude/agents/<name>.md`" (`qrspi-research/SKILL.md`). Skills that do work inline (`qrspi-ticket`, `qrspi-work`) have no agent file and broader `allowed-tools`.
- **Frontmatter dialects differ between skills and agents.** Skills: `name`, `description`, `command`, `argument-hint`, `allowed-tools` (flat). Agents: `name`, `description`, nested `claude.tools` (`.claude/agents/qrspi-research.md:1-6`).
- **Tool-firewalling by frontmatter.** Capabilities are restricted at the frontmatter level — research agent's `claude.tools` lists only `Read, Write, Glob, Grep` (no Bash, no MCP) to structurally enforce the research firewall; questions agent omits Glob/Grep/Bash so codebase exploration is impossible (`qrspi-work/SKILL.md`, "Questions firewall").
- **Determinism via self-locating one-shot scripts emitting JSON envelopes.** `qrspi_resolve.py`, `qrspi_persist.py`, `qrspi_pr_state.py` fold multi-step path-sensitive shell into single commands that self-locate the repo root and print `{"ok": ...}` — driven by a documented need to avoid a weak local worker model corrupting the "qrspi" path token.
- **Uniform HARD STOP boilerplate** is copy-pasted across every agent and the orchestrator — the single most repeated convention in the codebase.
- **`references/` is used sparingly** — only one exists (`qrspi-work/references/review-cascade.md`), and only for a cohesive conceptual topic too large to inline.
- **CLI-skill coverage is captured as eval assertions** (`evals/graphite-evals.json`): command_check / flag_check / safety_check / workflow_check / content_check assertion types enumerate the required subcommands and flags.

## Inconsistencies

- **Several question premises target the global `skill-creator` skill, which is NOT in `REPO_ROOT`.** Q3, Q4, Q6, Q10, Q12 reference skill-creator's authoring/eval rules. skill-creator is a global Claude skill outside project scope (confirmed: `find -iname '*skill-creator*'` → no results). Those sub-parts are answered from in-repo analogs only and flagged NOT FOUND where they strictly require skill-creator.
- **The "500 lines / 5000 tokens" SKILL.md threshold (Q10, Q11) is NOT a repo-documented rule.** The only "500" convention in the repo is **500 words** for a *ticket body* (`qrspi-ticket/SKILL.md:33`), a different artifact. No 5000-token rule and no token counter exist in scope. The thresholds in the questions appear to originate from external (skill-creator) guidance, not this codebase.
- **The eval harness advertises capability it does not have.** `docs/eval-system.md` and `evals/suite.json` describe a full 5-stage scoring pipeline with trials, train/test split, and token metrics, but `.claude/CLAUDE.md` flags it "non-functional placeholder" and `run_eval.py:execute_single` returns empty output with stubbed `tokens={"input":0,"output":0}`. Code (stub) contradicts the doc narrative (full pipeline).
- **Two distinct meanings of "token" in the codebase.** The questions use "token" = LLM tokens (size budget). The persistence scripts use "token" = the literal substring "qrspi" in a path (`qrspi_persist.py:8`, `qrspi_resolve.py:10`). A `grep token` mixes the two; they are unrelated.
- **No GitLab/glab footprint at all.** Q4, Q5, Q8, Q9 presuppose glab patterns; the repo has zero glab/gitlab code or config. The only CLI skills with precedent are GitHub `gh` (in `qrspi-work` + `qrspi_pr_state.py`) and Graphite `gt` (external skill, `graphite-evals.json`). A glab skill is greenfield relative to this codebase.
