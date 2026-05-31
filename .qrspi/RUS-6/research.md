# Research — Codebase Map

**Questions source:** questions.md @ 2026-05-31T10:25:00Z
**Generated:** 2026-05-31T10:30:00Z
**Status:** draft

## Q1: What is the canonical on-disk layout an agent skill must follow in this repo, including the relationship between a skill's SKILL.md, references/, scripts/, and assets/ subdirectories, and where do skill source files live?

**Answer:** Skills in this repo live under `.claude/skills/<skill-name>/`. Each skill directory contains a `SKILL.md` file. The only example of additional subdirectories in this repo is `.claude/skills/qrspi-work/references/` which holds `review-cascade.md`. No skill in the repo currently uses `scripts/` or `assets/` subdirectories — the canonical pattern in use is: one SKILL.md with optional sibling `references/` for long-form material that the SKILL.md links to. Skills can pair with a sub-agent prompt at `.claude/agents/<skill>.md` (used by the qrspi-* family).

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
  qrspi-work/
    SKILL.md
    references/
      review-cascade.md
  qrspi-worktree/SKILL.md
```

— `.claude/skills/` directory listing (observed via `ls .claude/skills/qrspi-work/`)

**Dependencies:** `.claude/agents/<name>.md` is the paired sub-agent prompt for the orchestrator-style skills.
**Implicit contracts:** A skill directory MUST contain `SKILL.md`. `references/` is optional and used only when the SKILL.md needs to offload reference material to keep itself short.

## Q2: How does an existing skill in this repo encode its frontmatter (name, description, allowed-tools, model, etc.), and what fields are required vs optional for the agentskills.io standard?

**Answer:** Every SKILL.md in the repo opens with a YAML frontmatter block delimited by `---`. Observed fields are: `name`, `description`, `command`, `argument-hint`, and `allowed-tools`. `model` is not set in any skill's SKILL.md (it appears only in agent prompts under `.claude/agents/`). All ten skills use the same five frontmatter fields. Agent prompts under `.claude/agents/<name>.md` use a different schema: `name`, `description`, `model`, and a nested `claude.tools` list.

**Evidence:**

```
---
name: qrspi-design
description: Produce a design document by combining the ticket, answered questions, and codebase research. Use after research is approved. This is the brain-surgery phase.
command: /qrspi-design
argument-hint: <ticket-id>
allowed-tools: Agent, Bash(pwd:*), mcp__linear-russelltsherman__get_issue
---
```

— `.claude/skills/qrspi-design/SKILL.md:1-7`

```
---
name: qrspi-questions
description: Internal QRSPI workflow agent — generates 8-15 technical questions from feature ticket content. Spawned by the /qrspi-questions skill or the qrspi-work orchestrator. Not for general-purpose question generation.
model: opus
claude:
  tools: Read, Write
---
```

— `.claude/agents/qrspi-questions.md:1-7`

**Dependencies:** Skill frontmatter is read by the Claude Code harness (skill discovery) and by the eval system indirectly.
**Implicit contracts:** `allowed-tools` is a comma-separated list. Tool restrictions on Bash use the `Bash(<pattern>:*)` form (e.g., `Bash(pwd:*)`). The `command` field is the slash command form. No skill in the repo declares a length budget in frontmatter — length is enforced externally (eval `line_count` assertions and convention).

## Q3: What flags, subcommands, and option signatures does the project already invoke on gt (Graphite CLI), and where in the codebase are those invocations centralized?

**Answer:** The qrspi-work SKILL.md is the single concentrated source of `gt` invocations in this repo (~30 invocations). The pattern is: every `gt` call passes `--no-interactive`. Mutation commits use `-c -m "<message>"` heredocs. Submit commands pair `--no-edit --no-interactive`. Stack submits add `--stack`. Sync uses `--force --no-interactive`. Branch creation uses `gt create`, branch amends use `gt modify`. Tracking new branches uses `gt track --parent <parent> --no-interactive`. The grade.py eval expects `gt sync --force --delete-all --no-interactive` for the cleanup case.

**Evidence:**

```
gt track --parent main --no-interactive
gt get --no-interactive 2>&1 || true
gt modify -c --no-interactive -m "$(cat <<'EOF' … EOF)"
gt modify --no-interactive -m "..."
gt submit --no-edit --no-interactive
gt submit --stack --no-edit --no-interactive
gt checkout <ticket-id>/planning --no-interactive
gt create <ticket-id>/slice-<N> --no-interactive -m "..."
gt log short --no-interactive
gt move --onto main --no-interactive
gt merge --confirm --no-interactive
gt delete <ticket-id>/planning --force --no-interactive
gt sync --force --no-interactive
```

— `.claude/skills/qrspi-work/SKILL.md:78,122,143,165,225,269,277,284,361,387,394,419,443,449,456,476-487,520,530-532,638-661`

```json
{
  "id": 5,
  "prompt": "sync with main and clean up any merged branches",
  "expected_output": "Checks git status for uncommitted changes first, then runs gt sync --force --delete-all --no-interactive."
}
```

— `evals/graphite-evals.json:54-66`

**Dependencies:** Graphite CLI binary (`gt`). PATH lookup in shells.
**Implicit contracts:** The `--no-interactive` flag is universally required. The orchestrator is the only place git/graphite operations happen — "sub-agents never commit" (`.claude/skills/qrspi-work/SKILL.md:636`).

## Q4: Does the repo already define a tool-allowlist or restricted-tools convention for skills that mostly read instructions vs ones that execute commands, and what does that look like in frontmatter?

**Answer:** Yes. Skills declare `allowed-tools` in frontmatter as a comma-separated list. Two patterns are observed: (a) read-mostly orchestrator skills declare `Agent, Bash(pwd:*)` plus optional Linear MCP tools (used by qrspi-design, qrspi-plan, qrspi-pr, qrspi-research, qrspi-structure, qrspi-worktree, qrspi-implement); (b) the qrspi-work orchestrator and qrspi-ticket declare a broader set (Read, Write, Edit, Bash, Glob, Grep, Agent plus Linear MCP tools). The `Bash(pwd:*)` form restricts Bash to a specific prefix. Agent prompts use a different schema (`claude.tools`, single line, no Bash sub-patterning).

**Evidence:**

```
allowed-tools: Agent, Bash(pwd:*)
```

— `.claude/skills/qrspi-plan/SKILL.md:6`

```
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, mcp__linear-russelltsherman__get_issue, mcp__linear-russelltsherman__get_issue_status, mcp__linear-russelltsherman__save_issue, mcp__linear-russelltsherman__list_issue_statuses, mcp__linear-russelltsherman__save_comment
```

— `.claude/skills/qrspi-work/SKILL.md:6`

```
claude:
  tools: Read, Write, Edit, Glob, Grep, Bash
```

— `.claude/agents/qrspi-implement.md:5-6`

**Dependencies:** Claude Code harness reads `allowed-tools` to construct the tool environment for the skill.
**Implicit contracts:** `Bash(<command>:*)` syntax restricts Bash to commands starting with `<command>`. Skills that don't run shell at all omit Bash entirely.

## Q5: How is "trunk branch" detection and configuration persisted by Graphite in this project, and how does that interact with the worktree-based workflow?

**Answer:** NOT FOUND in the repo. The repo does not check in any `.git/config` graphite section, and there is no `.graphite_*` file under version control. The qrspi-work SKILL.md assumes `gt` is already initialized — its preflight runs `gt get --no-interactive` and `gt track --parent main --no-interactive` but never `gt repo init` or `gt repo trunk`. Worktree creation goes through `git worktree add`, then `gt track --parent main --no-interactive` from inside the new worktree to register the branch with Graphite's metadata. Multiple worktrees share `.git/` metadata per the orchestrator's own documentation.

**Evidence:**

```
mkdir -p "<REPO_ROOT>/.worktrees"
git worktree add -b <ticket-id>/planning "<WORKTREE_PATH>" main
cd "<WORKTREE_PATH>"
gt track --parent main --no-interactive
```

— `.claude/skills/qrspi-work/SKILL.md:74-79`

```
- Multiple worktrees share the same `.git/` metadata (branches, graphite stack info).
- You cannot have the same branch checked out in two worktrees simultaneously.
```

— `.claude/skills/qrspi-work/SKILL.md:675-676`

Searched: `grep -rn 'gt repo' .` — only finds it documented in the ticket as a recommendation, never executed.

**Dependencies:** Graphite's local metadata storage (typically `.git/.graphite_*` files or `.git/config` graphite section), not version-controlled.
**Implicit contracts:** Graphite must be pre-initialized in the repo with `gt repo init` before any of these workflows run. The orchestrator does not bootstrap Graphite — it assumes a working state.

## Q6: What does the existing using-graphite-cli reference imply about state we already assume — for example, is gt expected to be pre-authenticated, or is there onboarding text covering gt auth login?

**Answer:** No skill in the repo currently named `using-graphite-cli` exists. Searching `grep -rn 'gt auth'` returns no matches. The repo assumes `gt` is pre-installed and pre-authenticated; no skill or doc walks through `gt auth login`. The closest related artifact is a global memory file referenced in `~/.agents/MEMORY.md` ("[All git actions use the using-graphite-cli skill](memory/feedback_git_delegation.md)") — that file lives outside `REPO_ROOT` and per the project scope firewall I did not read it.

**Evidence:**

```
$ grep -rn 'gt auth' .
(no matches)

$ grep -rn 'using-graphite-cli' .
(no matches in repo files)
```

— Bash exploration in `REPO_ROOT`

**Dependencies:** Assumption that `gt` is on PATH and authenticated before any qrspi workflow runs.
**Implicit contracts:** Onboarding (install, auth, trunk init) is implicit and not documented in any in-repo skill. This is a gap the new skill could fill if its scope includes onboarding.

## Q7: What does the project currently do when a gt command fails inside a sub-agent or orchestrator, and how should the new skill instruct agents to recover without escalating with raw git commands?

**Answer:** The qrspi-work orchestrator has an explicit "HARD STOP: Infrastructure Errors Are Not Puzzles To Solve" section (lines 709-730). The rule: on any tool/auth/config error, STOP, print the exact error verbatim, and exit. Forbidden recovery actions include using `git` to bypass a broken `gt`, modifying configuration, escalating with `sudo`, or "any action whose purpose is 'make the failing tool work again'." For semantic gt failures (conflicts), the convention is `gt continue` (never `git rebase --continue`) but this is not currently documented inline — it appears only in the ticket itself, not in the existing skill.

**Evidence:**

```
**Explicitly forbidden responses to infrastructure errors:**
- Changing directory ownership or permissions (`chmod`, `chown`)
- Setting environment variables to route around config paths
- Copying config files to alternate locations
- Deleting or recreating configuration directories
- Using an alternate tool (e.g., raw `git` instead of `gt`) to bypass the broken one
- Retrying with `sudo` or escalated permissions
```

— `.claude/skills/qrspi-work/SKILL.md:719-726`

```
### Stale worktree recovery

If `git worktree add` fails because a worktree path already exists but is broken:
```
git worktree remove "<WORKTREE_PATH>" --force 2>/dev/null
git worktree prune
git worktree add ...  # retry
```
```

— `.claude/skills/qrspi-work/SKILL.md:691-697`

**Dependencies:** No CI or hook intercepts gt failures today.
**Implicit contracts:** The "never use raw git" rule has one documented exception: `git worktree` operations, which gt does not wrap.

## Q8: How are multi-commit branches prevented or detected today, and is there an existing automated check that the new skill should reference?

**Answer:** No automated check exists. The convention is enforced by skill instructions only. The qrspi-work orchestrator explicitly states "Planning uses a single commit. Phase 1 (Questions) creates the commit with `gt modify -c`. Phases 2–6 amend it with `gt modify` (no `-c`)" (line 639). For slices, each slice is its own branch with one commit (`gt create <ticket-id>/slice-<N>`). There is no pre-commit hook, CI workflow, or lint that enforces single-commit-per-branch. No `.github/workflows/` directory exists. No `.pre-commit-config.yaml` exists.

**Evidence:**

```
- **Planning uses a single commit.** Phase 1 (Questions) creates the commit with `gt modify -c`. Phases 2–6 amend it with `gt modify` (no `-c`). The commit message is always `<ticket-id>: Planning`.
```

— `.claude/skills/qrspi-work/SKILL.md:639`

```
$ ls .github 2>&1
ls: cannot access '.github': No such file or directory

$ ls .pre-commit-config.yaml 2>&1
ls: cannot access '.pre-commit-config.yaml': No such file or directory
```

— Bash exploration in `REPO_ROOT`

**Dependencies:** None — convention only.
**Implicit contracts:** Multi-commit-per-branch is forbidden by convention. The new skill must teach the agent that `gt modify` amends (single commit preserved), and that `git commit` followed by no amend will create a second commit and break Graphite tracking.

## Q9: When a worktree has the same branch already checked out elsewhere, what is the established recovery path, and how should the skill describe that to an agent encountering the failure mode?

**Answer:** The orchestrator describes a three-step recovery: (1) detect the situation via `gt log short --no-interactive` or via `git worktree add` failure; (2) if the branch is checked out in the main repo, return it to main with `git -C "<REPO_ROOT>" checkout main`; (3) for genuinely broken worktrees, `git worktree remove --force` then `git worktree prune`, then retry the add. The constraint is documented as an invariant: "You cannot have the same branch checked out in two worktrees simultaneously."

**Evidence:**

```
If a branch is found but is currently checked out in the main repo, free it first:
current_branch=$(git -C "<REPO_ROOT>" branch --show-current)
if echo "$current_branch" | grep -q '<ticket-id>'; then
  git -C "<REPO_ROOT>" checkout main
fi
```

— `.claude/skills/qrspi-work/SKILL.md:56-60`

```
If `git worktree add` fails because a worktree path already exists but is broken:
git worktree remove "<WORKTREE_PATH>" --force 2>/dev/null
git worktree prune
git worktree add ...  # retry
```

— `.claude/skills/qrspi-work/SKILL.md:691-697`

**Dependencies:** `git worktree` subcommands (gt has no equivalent).
**Implicit contracts:** Worktree mutations always run from `REPO_ROOT`, not from inside an existing worktree.

## Q10: What evaluation harness exists for skills in this repo, and what interface must a new skill expose so it can be benchmarked the same way as existing ones?

**Answer:** The eval harness lives under `evals/` (data) and `scripts/` (runners). The qrspi-* family is benchmarked via `evals/suite.json` (15 weighted cases, train/test split). The Graphite CLI skill already has its own separate eval at `evals/graphite-evals.json` containing 5 cases that exercise commit, submit, log, move, and sync intent prompts. Each case has assertions of three types: `programmatic` (checks in `grade.py`), `llm_judge` (criteria string), and `script` (external script). For a new skill to plug in, it needs an evals JSON file referencing prompt-style cases with weighted assertions. `scripts/run_eval.py` executes cases, `scripts/grade.py` scores them, `scripts/report.py` ledgers versions.

**Evidence:**

```json
{
  "skill_name": "graphite",
  "evals": [
    {
      "id": 1,
      "prompt": "I just made some changes to the auth module. commit my changes with a message about adding JWT validation",
      "expected_output": "Uses gt create or gt modify with -a -m flags, --no-interactive, and includes co-authorship trailer."
    }
  ]
}
```

— `evals/graphite-evals.json:1-15`

```
1. **`scripts/run_eval.py`** — Execute test cases against a skill prompt (multi-trial, parallel)
2. **`scripts/grade.py`** — Score results using programmatic checks + LLM judges
3. **`scripts/report.py`** — Compare versions, detect regressions/plateaus/overfitting
```

— `docs/eval-system.md:6-8`

**Dependencies:** `scripts/run_eval.py`, `scripts/grade.py`, JSON schema implied by `evals/suite.json` and `evals/graphite-evals.json`.
**Implicit contracts:** New skills can reuse `evals/graphite-evals.json` as a starting template (5 cases, mostly command_check / flag_check / safety_check assertions). Eval runner contract beyond reading the JSON is not documented in-repo.

## Q11: Is there a reference example of a "skill built with the skill-builder" already in the repo that demonstrates the expected references/scripts/assets layout, and what conventions does it set?

**Answer:** NOT FOUND. The repo has no skill that internally documents itself as built by the skill-creator/skill-builder. Every existing skill is a hand-written SKILL.md. The closest reference is `qrspi-work/references/review-cascade.md` which demonstrates the `references/` offload pattern. The `qrspi-structure` agent mentions `skill-creator` (`.claude/agents/qrspi-structure.md:41`) in passing as a validation gate ("Validation passes (linting, running a review tool, invoking skill-creator) are the final step of the slice that produced the files") but no local skill-creator definition exists in the repo. The skill-creator lives globally outside `REPO_ROOT` (per the project-scope firewall I did not inspect it).

**Evidence:**

```
$ grep -rn 'skill-creator\|skill-builder' . --include='*.md'
.claude/agents/qrspi-structure.md:41: invoking skill-creator
.qrspi/RUS-6/questions.md: (this ticket only)
```

— Bash exploration in `REPO_ROOT`

```
.claude/skills/qrspi-work/
  SKILL.md             (730 lines — exceeds proposed 500-line budget)
  references/
    review-cascade.md  (64 lines — offloaded conditional logic)
```

— Directory listing

**Dependencies:** Global skill-creator skill (outside repo scope).
**Implicit contracts:** Long-form material should be offloaded to `references/` when SKILL.md grows large. The qrspi-work SKILL.md at 730 lines is itself an outlier and is not a great length model.

## Q12: When a gt invocation fails or behaves unexpectedly, what information should the skill instruct agents to capture, and where does that information get surfaced today?

**Answer:** The orchestrator prints `gt log short --no-interactive` "after mutations" to verify stack state (line 638). The hard-stop rule for infrastructure errors mandates printing the exact failing command and exact error output. There is no built-in routing of gt error output to Linear comments — `mcp__linear-russelltsherman__save_comment` is in `allowed-tools` for qrspi-work but never used for error reporting in the SKILL.md. The orchestrator's only Linear write is `save_issue` to transition status. Reviewer feedback for slice PRs is fetched via `gh pr view` and `gh api repos/<owner>/<repo>/pulls/<n>/comments`, not gt.

**Evidence:**

```
- After mutations, run `gt log short --no-interactive` to verify stack state.
```

— `.claude/skills/qrspi-work/SKILL.md:638`

```
2. **Print the exact error verbatim** — the full command that failed and the full error output, unmodified.
3. **Exit the skill.** Do not continue to subsequent phases.
```

— `.claude/skills/qrspi-work/SKILL.md:715-717`

```
gh pr view <number> --json reviews,comments --jq '.reviews[] | select(.state != "APPROVED")'
gh api repos/<owner>/<repo>/pulls/<number>/comments --jq '.[] | {path, body, line}'
```

— `.claude/skills/qrspi-work/SKILL.md:252-254`

**Dependencies:** `gt log short`, `gh pr view`, stdout/stderr capture by the harness.
**Implicit contracts:** "Print verbose progress so the operator can observe" (`.claude/skills/qrspi-work/SKILL.md:11`). Observability is operator-facing console output, not Linear comments.

## Q13: Does the repo already enforce a SKILL.md length budget via a check or only by convention?

**Answer:** Only by convention. There is no script under `scripts/` that lints SKILL.md size. The eval suite has a `line_count('design.md') <= 300` programmatic assertion for the design phase (`evals/suite.json:243`), demonstrating that the assertion mechanism exists, but no equivalent assertion is wired for SKILL.md files of new skills. Current sizes vary widely: most qrspi-* skills are 25-35 lines (thin wrappers), qrspi-ticket is 119 lines, and qrspi-work is 730 lines (the only outlier).

**Evidence:**

```
   28 .claude/skills/qrspi-design/SKILL.md
   35 .claude/skills/qrspi-implement/SKILL.md
   26 .claude/skills/qrspi-plan/SKILL.md
   28 .claude/skills/qrspi-pr/SKILL.md
   26 .claude/skills/qrspi-questions/SKILL.md
   26 .claude/skills/qrspi-research/SKILL.md
   25 .claude/skills/qrspi-structure/SKILL.md
  119 .claude/skills/qrspi-ticket/SKILL.md
  730 .claude/skills/qrspi-work/SKILL.md
   25 .claude/skills/qrspi-worktree/SKILL.md
```

— `wc -l .claude/skills/*/SKILL.md`

```
{
  "type": "programmatic",
  "check": "line_count('design.md') <= 300",
  "weight": 1.5
}
```

— `evals/suite.json:242-246`

**Dependencies:** Eval assertion infrastructure exists but is unused for SKILL.md size enforcement.
**Implicit contracts:** The convention is "thin wrapper skills" (~30 lines) plus offload to `references/` for everything else. The ticket's proposed 500-line budget is generous relative to existing thin wrappers but consistent with the qrspi-work outlier.

## Q14: What naming convention does the repo use for skill directories and the name frontmatter field — kebab-case, snake_case, or something else — and does "using-graphite-cli" already match a pattern in use?

**Answer:** All ten existing skills use kebab-case for both directory names and the `name` frontmatter field, with a `qrspi-` prefix on every qrspi-* skill. Agent prompts under `.claude/agents/` mirror the same kebab-case convention. The proposed name `using-graphite-cli` is kebab-case and would NOT inherit the `qrspi-` prefix (correctly — it isn't a QRSPI workflow phase). It matches the structural pattern but introduces a new top-level skill family.

**Evidence:**

```
.claude/skills/
  qrspi-design/      qrspi-implement/   qrspi-plan/        qrspi-pr/
  qrspi-questions/   qrspi-research/    qrspi-structure/   qrspi-ticket/
  qrspi-work/        qrspi-worktree/
```

— Directory listing

```
name: qrspi-design
name: qrspi-implement
…
```

— All ten SKILL.md frontmatter `name:` fields

**Dependencies:** None — convention only.
**Implicit contracts:** Skill directory name == `name` frontmatter field. Lowercase kebab-case. No underscores observed in skill names.

---

## Discovered Patterns

1. **Thin-wrapper skill pattern.** Most qrspi-* skills are ~25-35 line wrappers whose body is a numbered "Steps" list that fetches inputs and spawns a sub-agent. The real per-phase prompt lives in `.claude/agents/<phase>.md`. Each agent has its own `claude.tools` lockdown, hard-constraints block, and project-scope firewall.
2. **Mandatory `--no-interactive` flag on all gt calls.** Every observed gt invocation includes it. This is the strongest convention in the repo.
3. **Single-commit-per-branch is doctrinal.** Both planning (amend with `gt modify`) and slice branches (`gt create` once, amend with `gt modify`) embody this. There is no automated check; it is enforced by skill instruction only.
4. **Heredoc commit messages with co-authorship trailer.** Every commit-producing snippet uses `$(cat <<'EOF' … EOF)"` form and appends `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`.
5. **HARD STOP on infrastructure errors.** The qrspi-work SKILL.md devotes a full section to forbidding workarounds. This is the right pattern to mirror in any new skill that wraps a CLI.
6. **Project scope firewall in every agent.** Each agent prompt includes a hardcoded "BEFORE reading ANY file, validate its path starts with REPO_ROOT/" boundary. This is reinforced at the orchestrator level by appending scope-restriction blocks to agent prompts.
7. **`Bash(<command>:*)` allow-listing.** Several skills tighten Bash to a single command prefix in frontmatter (e.g., `Bash(pwd:*)`).
8. **No README inside `.claude/skills/`.** Skills are self-documenting via SKILL.md frontmatter `description` only. No additional discovery file exists.
9. **`gt sync` is explicitly banned during planning.** "Never use `gt sync` here; it deletes branches whose PRs are merged/closed, destroying ticket work-in-progress." (`.claude/skills/qrspi-work/SKILL.md:120`). `gt get` is the safe sync alternative for planning branches.
10. **Sub-agents never commit.** "The orchestrator is the ONLY place git/graphite operations happen — sub-agents never commit." (`.claude/skills/qrspi-work/SKILL.md:636`). This is a hard split between planning logic and git mutation.

## Inconsistencies

1. **`Bash(pwd:*)` is too narrow for skills that need `cd`.** Several qrspi-* skills declare `Bash(pwd:*)` but their accompanying agents need `cd` to enter the worktree. The orchestrator handles this by spawning agents that have unrestricted `Bash`; the discrepancy works in practice but suggests the SKILL.md frontmatter is decorative — the agent prompt's tool list is what counts.
2. **qrspi-work SKILL.md (730 lines) vs proposed 500-line budget for new skills.** The new skill's ticket says "under 500 lines / 5000 tokens" but the largest existing skill exceeds 500 lines by 46%. The new skill should not use qrspi-work as a length model.
3. **`gt sync` documentation is split.** The orchestrator forbids it during planning preflight (line 120) but uses it as the final cleanup step in the Done state (line 504). Both are correct in context, but a standalone Graphite skill must explain when each is safe.
4. **`evals/graphite-evals.json` schema differs from `evals/suite.json`.** suite.json wraps cases under top-level `cases`; graphite-evals.json wraps under `evals` and uses different assertion types (`command_check`, `flag_check`, `safety_check`, `workflow_check`, `content_check`) not registered as `programmatic`/`llm_judge`/`script` in `docs/eval-system.md`. The Graphite eval will not run through `scripts/run_eval.py` as-is without an adapter or a schema update.
5. **`evals/graphite-evals.json` case 1 expects `-a` or `-u` flags** ("Includes -a or -u flag to stage changes") which directly contradicts the qrspi-work SKILL.md instruction "NEVER use `-a` flag" (line 642). The eval and the orchestrator disagree on staging convention. The new skill must pick one and justify it.
6. **Onboarding gap.** No skill or doc covers `gt auth login`, `gt repo init`, or `brew install graphite`. The new skill is the first natural home for that material.
