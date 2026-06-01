# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-01T00:00:00Z
**Generated:** 2026-06-01T00:00:00Z
**Status:** draft

> Scope note: Several questions (Q1, Q5, Q7, Q8, Q9, Q12) target the Anthropic
> skill-creator skill and/or "references material describing Graphite
> conventions." Neither the skill-creator skill nor a `using-graphite-cli`
> skill exists inside `REPO_ROOT` (`/workspaces/qrspi/.worktrees/RUS-6`). They
> live in the global skills directory (`~/.claude/skills/...`), which is
> outside project scope and was NOT read. Where the codebase contains
> equivalent in-repo evidence (e.g. Graphite command conventions encoded in
> `evals/graphite-evals.json` and `.claude/skills/qrspi-work/SKILL.md`), it is
> cited; otherwise the answer is marked NOT FOUND with the searches attempted.

## Q1: What directory does the Anthropic skill builder skill emit generated skill files into, and how does that path map to where this project expects skills to live?

**Answer:** NOT FOUND (skill-creator output logic). The Anthropic skill-creator
(skill builder) skill is a global skill, not present anywhere under
`REPO_ROOT`. Its generation/output logic could not be inspected without
reading outside project scope, which is forbidden.

What CAN be established from the repo: this project expects skills to live at
`.claude/skills/<skill-name>/SKILL.md`, one directory per skill. This is
documented in the README project-structure block and confirmed by the actual
layout (10 skill directories, each containing `SKILL.md`).

**Evidence:**

```
.claude/
  skills/              # Skill definitions (one SKILL.md per phase)
    qrspi-ticket/
    qrspi-questions/
    ...
    qrspi-work/        # Autonomous orchestrator
```

— `README.md:75-87`

```
.claude/skills/qrspi-design/SKILL.md
.claude/skills/qrspi-work/SKILL.md   (+ references/review-cascade.md)
```

— directory listing of `.claude/skills/` (11 entries, each a skill dir)

**Searches attempted:** `grep -rln "skill-creator\|skill builder\|generated skill"` (no in-repo matches); inspection of `.claude/skills/` layout; README structure section.
**Dependencies:** Skill discovery is by Claude Code's loader reading `.claude/skills/*/SKILL.md`; no project code performs this.
**Implicit contracts:** A skill = a directory under `.claude/skills/` whose name matches the `name` frontmatter value, containing a `SKILL.md`.

## Q2: How does a skill's `SKILL.md` reference and load its `references/`, `scripts/`, and `assets/` sub-resources at runtime, and what path resolution rules apply?

**Answer:** Exactly one skill in the repo uses a `references/` sub-resource:
`qrspi-work`. Its `SKILL.md` refers to the reference file by a path **relative
to the skill directory** — `references/review-cascade.md` — and instructs the
agent to read it on demand (lazy load), not eagerly. No skill in the repo uses
`scripts/` or `assets/` subdirectories; only `references/` is exercised. There
is no project code that resolves these paths — resolution is performed by the
Claude Code runtime / the agent following the `Read` instruction. The
reference is loaded by an explicit instruction ("Read
`references/review-cascade.md` for cascade logic"), so resolution is relative
to the skill's own directory.

**Evidence:**

```
   c. Read `references/review-cascade.md` for cascade logic.
```

— `.claude/skills/qrspi-work/SKILL.md:281`

```
# Review Cascade Logic

When planning review feedback requires changes to an artifact, downstream
artifacts may be invalidated. ...
```

— `.claude/skills/qrspi-work/references/review-cascade.md:1-4`

**Dependencies:** `qrspi-work/SKILL.md` → `qrspi-work/references/review-cascade.md` (sibling-relative reference). No `scripts/`/`assets/` consumers exist in-repo.
**Implicit contracts:** Reference files live in a `references/` subdir of the skill and are loaded on demand via a `Read` instruction with a skill-relative path; they are NOT inlined into `SKILL.md` (keeps `SKILL.md` small).

## Q3: What fields are required versus optional in `SKILL.md` frontmatter, and what are the constraints on the `name` and `description` fields?

**Answer:** No formal schema/spec file exists in the repo; the contract is
established empirically by the 10 existing skills. Every `SKILL.md` frontmatter
block contains four fields consistently and a fifth on most:
`name`, `description`, `command`, `argument-hint`, `allowed-tools`.
Observed conventions:
- `name` always equals the skill directory name (e.g. `qrspi-research` in
  `.claude/skills/qrspi-research/`). Lowercase, hyphen-separated.
- `description` is a single line for most skills; `qrspi-work` uses a
  double-quoted multi-sentence string containing trigger phrases — quoting is
  required when the value contains a colon (`e.g.,`) or embedded quotes.
- `command` is the slash command (`/qrspi-<name>`), matching `name`.
- `argument-hint` documents positional args (`<ticket-id>`, etc.).
- `allowed-tools` is a comma-separated allowlist that locks down each skill's
  tool surface (the firewall mechanism — see Q4).

There is no in-repo validator enforcing required vs optional; the "spec" is
convention only.

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
description: "Single entry point for autonomous QRSPI feature development. Use when the user asks to 'work on' a ticket (e.g., 'work on RUS-42'). ..."
```

— `.claude/skills/qrspi-work/SKILL.md:3` (quoted multi-sentence description)

**Dependencies:** Consumed by the Claude Code skill loader (external to repo).
**Implicit contracts:** `name` == directory name == `command` stem; `description` doubles as the auto-invocation trigger text; `allowed-tools` is the security boundary, not decorative.

## Q4: How is a skill registered so it becomes invocable as a slash command (e.g. `/using-graphite-cli`) versus auto-invoked, and is any wrapper file required beyond `SKILL.md`?

**Answer:** No project code performs registration — discovery is implicit:
placing a `SKILL.md` (with a `command:` and `name:` field) under
`.claude/skills/<name>/` makes it invocable as `/<name>`. The `command:`
frontmatter field declares the slash command; the `description:` field is what
drives auto-invocation. No separate wrapper file is required beyond `SKILL.md`
itself. Note: the project's `.claude/CLAUDE.md` describes an OLDER layout
("Agent prompt definitions live in `.qrspi/agents/`"), but the actual current
layout puts thin slash-command skills in `.claude/skills/` and the heavier
agent prompts in `.claude/agents/` (see Inconsistencies). The QRSPI phase
skills are themselves thin wrappers that spawn a matching `subagent_type`
agent; that two-file pattern is QRSPI-specific, NOT a general requirement.

**Evidence:**

```
# /qrspi-research

Thin wrapper that spawns the `qrspi-research` agent. All prompt content lives in `.claude/agents/qrspi-research.md`.
```

— `.claude/skills/qrspi-research/SKILL.md:9-11`

```
The orchestrator dispatches each phase to a purpose-built agent defined in
`.claude/agents/qrspi-<phase>.md`. ... The orchestrator does NOT read phase
SKILL.md files or hand-engineer prompts — it spawns by `subagent_type` ...
```

— `.claude/skills/qrspi-work/SKILL.md:589-591`

**Dependencies:** Slash-command skill (`.claude/skills/<name>/SKILL.md`) optionally → agent prompt (`.claude/agents/<name>.md`) via the Agent tool. A standalone skill like `using-graphite-cli` would only need `SKILL.md` (+ optional `references/`); no agent file required unless it spawns sub-agents.
**Implicit contracts:** Auto-invocation is description-driven; explicit invocation is `command`-driven. A skill that just provides knowledge (no sub-agent) needs no `.claude/agents/` companion.

## Q5: Where is the repo-level Graphite trunk configuration persisted (`.git/`) versus the global user config (`~/.config/graphite/`), and which of these does an agent need to read or verify before operating?

**Answer:** Partial. The repo-level vs global split is visible in the
devcontainer setup, not in any "references material" (which does not exist
in-repo).
- Global user config: `~/.config/graphite/` containing `aliases` and
  `user_config` — created/touched by the devcontainer initialize script and
  bind-mounted into the container.
- Repo-level Graphite metadata: `qrspi-work/SKILL.md` documents that Graphite
  stores each branch's PR association in `.git/.graphite_pr_info` (the
  branch→PR mapping that survives `untrack`/`track`). This is the only
  `.git/`-scoped Graphite state named in the repo. The trunk/parent
  relationship is established at branch-creation time via
  `gt track --parent main` (a `.git/`-scoped operation), shown in worktree
  setup.

The repo does not contain documentation prescribing which config an agent must
verify before operating; that prescriptive "references material" is NOT FOUND
in scope.

**Evidence:**

```
mkdir -p "$HOME/.config/graphite/"
touch "$HOME/.config/graphite/aliases"
touch "$HOME/.config/graphite/user_config"
```

— `.devcontainer/config/initialize.sh:68-70`

```
"source=${localEnv:HOME}/.config/graphite/,target=/home/vscode/.config/graphite/,type=bind"
```

— `.devcontainer/devcontainer.json:46`

```
Graphite pins each branch to the first PR it created for it, in `.git/.graphite_pr_info`.
```

— `.claude/skills/qrspi-work/SKILL.md:665`

```
gt track --parent main --no-interactive
```

— `.claude/skills/qrspi-work/SKILL.md:78` (new-branch trunk/parent tracking)

**Searches attempted:** `grep -rn ".config/graphite\|graphite_pr_info\|trunk\|gt track"`; devcontainer scan.
**Dependencies:** Global `~/.config/graphite/` (auth/aliases) is OUTSIDE project scope. Repo-level `.git/.graphite_pr_info` and `gt track` state are per-clone.
**Implicit contracts:** A new branch must be `gt track`-ed to a parent before `gt` stack ops work; `.git/.graphite_pr_info` persists branch→PR mapping and can go stale on closed/merged PRs (see Q8/recovery in SKILL.md:663-700).

## Q6: What is the canonical naming convention for the skill directory and the `name` frontmatter value, and does this repo already contain a using-graphite-cli skill or related git-delegation skill that this would conflict with or replace?

**Answer:** Canonical convention: the skill directory name, the `name`
frontmatter value, and the `command` stem are all identical, lowercase, and
hyphen-separated (e.g. directory `qrspi-research/`, `name: qrspi-research`,
`command: /qrspi-research`). For a Graphite skill this implies directory
`.claude/skills/using-graphite-cli/`, `name: using-graphite-cli`,
`command: /using-graphite-cli`.

The repo does NOT already contain a `using-graphite-cli` skill or any
git-delegation skill. `.claude/skills/` holds only the 10 QRSPI skills. No
`SKILL.md` mentions git delegation. There is therefore no in-repo skill to
conflict with or replace. (A global `using-graphite-cli` skill exists at
`~/.claude/skills/`, out of scope and not inspected.) The repo DOES already
contain `evals/graphite-evals.json`, an eval suite explicitly named for a
"graphite" skill — i.e. tests appear to predate the skill itself (see Q10/Q11).

**Evidence:**

```
=== search using-graphite-cli (in-repo) ===
README.md
docs/eval-system.md
.devcontainer/etc/squid/allowlist.conf
.qrspi/RUS-6/questions.md
```

— grep across `REPO_ROOT` (no `.claude/skills/using-graphite-cli/`; only doc/eval/config mentions)

```
{ "skill_name": "graphite", "evals": [ ... ] }
```

— `evals/graphite-evals.json:1-3`

**Dependencies:** None in-repo to displace.
**Implicit contracts:** dir == `name` == `command` stem; all lowercase-hyphenated.

## Q7: When a branch ends up with more than one commit, what failure mode does the ticket's "single commit per branch" rule guard against, and how should the skill instruct an agent to detect and recover that state?

**Answer:** Partial / mostly NOT FOUND. No "references material" on a
single-commit-per-branch convention exists in the project. The closest in-repo
evidence is the QRSPI planning rule in `qrspi-work/SKILL.md`: all six planning
artifacts live on ONE planning branch as a SINGLE amended commit — Phase 1
creates it with `gt modify -c`, Phases 2–6 amend with `gt modify` (no `-c`).
The stated purpose there is to keep planning as one reviewable unit. The repo
does NOT document a detect/recover procedure for a branch that has accidentally
accumulated multiple commits; that prescriptive guidance is NOT FOUND in scope.

**Evidence:**

```
**Planning uses a single commit.** Phase 1 (Questions) creates the commit with
`gt modify -c`. Phases 2–6 amend it with `gt modify` (no `-c`). The commit
message is always `<ticket-id>: Planning`.
```

— `.claude/skills/qrspi-work/SKILL.md:661`

**Searches attempted:** `grep -rln "single commit\|gt continue\|gt restack"` (matches only in `qrspi-work/SKILL.md`, its `references/review-cascade.md`, `evals/graphite-evals.json`, and this ticket's `questions.md`).
**Dependencies:** `gt modify` / `gt modify -c` semantics (Graphite CLI, external).
**Implicit contracts:** `gt modify -c` = new commit; `gt modify` (no `-c`) = amend the existing single commit. Detect/recover guidance is absent in-repo.

## Q8: During a restack conflict, what exact sequence distinguishes correct recovery (`gt continue`) from the forbidden path (`git rebase --continue`), and how should the skill instruct the agent to verify the stack is fully propagated afterward?

**Answer:** NOT FOUND (restack-conflict references material). No file under
`REPO_ROOT` documents a `gt continue` vs `git rebase --continue` recovery
sequence. `grep` for `gt continue` and `rebase --continue` across the repo
returns no matches (only `gt move`/`gt modify` restacking is mentioned, without
conflict-resolution steps). The repo's only adjacent fact: `gt modify`
"automatically restacks all descendant branches" (`qrspi-work/SKILL.md:478`),
and the post-mutation verification convention is to run
`gt log short --no-interactive` (SKILL.md:660). The forbidden-vs-correct
recovery sequence itself is NOT in scope (it would live in the global
using-graphite-cli skill).

**Evidence:**

```
- After mutations, run `gt log short --no-interactive` to verify stack state.
```

— `.claude/skills/qrspi-work/SKILL.md:660`

```
   - `gt modify` automatically restacks all descendant branches.
```

— `.claude/skills/qrspi-work/SKILL.md:478`

**Searches attempted:** `grep -rln "gt continue"`, `grep -rln "rebase --continue"`, `grep -rln "restack"` across `REPO_ROOT` — no recovery-sequence content found.
**Dependencies:** Graphite restack engine (external).
**Implicit contracts:** Verification convention in-repo is `gt log short --no-interactive` after any mutation.

## Q9: What does the skill instruct an agent to do when raw `git branch` or `git rebase` commands have already been run on a Graphite-tracked branch and metadata has drifted?

**Answer:** Partial. No general "git/Graphite mixing warning" references file
exists. The repo DOES contain one concrete metadata-drift recovery procedure,
but only for a specific case: a branch pinned to a CLOSED/MERGED PR in
`.git/.graphite_pr_info`. The documented recovery is a two-step
rename-detach + force-submit sequence, run as one uninterrupted block; it
explicitly notes `gt untrack` + `gt track` does NOT clear the stale
association. The repo also states the general rule "Never run raw `git`
commands when a `gt` equivalent exists" (prevention), but provides no recovery
for arbitrary `git branch`/`git rebase`-induced drift — that broader guidance
is NOT FOUND in scope.

**Evidence:**

```
gt rename <branch>-stale --no-interactive   # 1a. detaches the dead PR
gt rename <branch>        --no-interactive   # 1b. restores the canonical name
gt info <branch> --no-interactive            #     confirm: no "PR #… (Closed)/(Merged)" line remains
gt submit --force --no-edit --no-interactive #  2. creates a brand-new PR
```

— `.claude/skills/qrspi-work/SKILL.md:685-688`

```
- Never run raw `git` commands when a `gt` equivalent exists.
```

— `.claude/skills/qrspi-work/SKILL.md:659`

**Searches attempted:** `grep -rln "git branch\|git rebase\|metadata\|drift\|untrack"`; only the closed-PR recovery in `qrspi-work/SKILL.md` matched.
**Dependencies:** `.git/.graphite_pr_info` (per-clone), `gt rename`/`gt info`/`gt submit --force`.
**Implicit contracts:** Stale PR association is cleared by renaming away+back (not untrack/track); the rename→confirm→submit steps must run with nothing in between or the stale association re-hydrates (SKILL.md:691-694).

## Q10: How are skills evaluated for correctness in this repo, and what eval format does the harness expect for a newly authored skill?

**Answer:** The repo has a 5-stage eval pipeline under `scripts/`, driven by
`run_loop.sh`: `run_eval.py` (execute) → `grade.py` (score) → `report.py`
(compare) → `diagnose.py` (categorize failures) → `revise.py` (propose edits).
A suite is a JSON file with a top-level `name` and `cases` array; `load_suite`
hard-requires `name` and `cases`, and each case requires `id`, `prompt`,
`assertions`. The QRSPI agent suite is `evals/suite.json` (15 cases, 65/35
train/test split). A SEPARATE suite already exists for the Graphite skill:
`evals/graphite-evals.json`, `"skill_name": "graphite"`, 5 cases (commit,
submit, log, move, sync). Its case shape differs from `suite.json`: it uses
`id`, `prompt`, `expected_output`, `files`, and an `assertions` array whose
entries are `{text, type}` objects (types: `command_check`, `flag_check`,
`content_check`, `workflow_check`, `safety_check`). Note this differs from
`suite.json`'s assertion shape (`{type, check/criteria, weight}`), so
`grade.py` as written cannot grade `graphite-evals.json` directly (see
Inconsistencies). Running: `./run_loop.sh <skill_path> <eval_suite>`.

**Evidence:**

```
required = {"name", "cases"}
...
for case in suite["cases"]:
    case_required = {"id", "prompt", "assertions"}
```

— `scripts/run_eval.py:47-55`

```
"assertions": [
  {"text": "Uses gt create or gt modify (not raw git commit)", "type": "command_check"},
  {"text": "Includes --no-interactive flag", "type": "flag_check"},
  ...
]
```

— `evals/graphite-evals.json:9-15`

```
python3 scripts/run_eval.py --skill "$SKILL_PATH" --suite "$EVAL_SUITE" ...
python3 scripts/grade.py --results "${OUTPUT_DIR}/results.json" --suite "$EVAL_SUITE"
```

— `run_loop.sh:43-55`

**Dependencies:** `run_loop.sh` → `scripts/run_eval.py` → `scripts/grade.py` → `report.py`/`diagnose.py`/`revise.py`; suites in `evals/`; fixtures in `evals/fixtures/`; goldens in `evals/golden/`.
**Implicit contracts:** Suite JSON must have `name` + `cases`; each case needs `id`+`prompt`+`assertions`. `run_eval.py`'s `execute_single` is a STUB (no real agent invocation) — running today produces empty outputs / zero scores.

## Q11: What measurable checks correspond to the acceptance criteria (SKILL.md under 500 lines / 5000 tokens, valid frontmatter, `references/` present), and is there an existing lint or validation step that enforces them?

**Answer:** NO existing lint/validation step enforces SKILL.md-specific
acceptance criteria (line/token limits, frontmatter validity, `references/`
presence). The check registry in `grade.py` is QRSPI-artifact-oriented. The
ONLY directly reusable check is `line_count(filename, max_lines, result)`,
which counts `output.splitlines()` against a limit — usable for a "under N
lines" assertion. There is `has_section` (markdown heading presence) but no
frontmatter parser, no token counter, and no `references/`-presence check. The
eval-system docs confirm only "14 of ~37 referenced checks implemented" and
that `graphite-evals.json`'s assertion types (`command_check`, `flag_check`,
etc.) are not in the `grade.py` registry at all. So the RUS-6 acceptance
criteria would require NEW checks; none exist today.

**Evidence:**

```
def line_count(filename: str, max_lines: int, result: dict) -> tuple[bool, str]:
    output = result.get("output", "")
    count = len(output.splitlines())
    ok = count <= max_lines
    return ok, f"Line count: {count} (limit: {max_lines})"
```

— `scripts/grade.py:35-40`

```
CHECKS = {
    "output_file_exists": ..., "has_section": ..., "line_count": ...,
    "no_solution_language": ..., "all_questions_have_target": ...,
    "current_state_has_citations": ..., "no_code_blocks": ...,
    "all_evidence_has_file_citations": ..., "all_slices_have_verification": ...,
    "pr_title_under_limit": ...,
}
```

— `scripts/grade.py:146-157` (10 registered checks; no frontmatter/token/references check)

```
| Programmatic check registry | Partial | 14 of ~37 referenced checks implemented in `grade.py` |
```

— `docs/eval-system.md:96`

**Searches attempted:** read of full `grade.py` check registry; `grep` for `token`, `frontmatter`, `references` in `scripts/`.
**Dependencies:** `grade.py` CHECKS registry; unknown checks return `passed=None` and are skipped (`grade.py:194-197`).
**Implicit contracts:** A check named in a suite but absent from `CHECKS` is silently skipped (not a failure) — so a SKILL.md-size assertion would be a no-op unless the check is added.

## Q12: How does an agent surface or log which Graphite command it ran and the resulting stack state (e.g. `gt log short`) so the outcome is auditable, and does the skill prescribe any output the agent must report back?

**Answer:** Partial. No standalone "references material" on stack
visualization exists, but the in-repo orchestrator (`qrspi-work/SKILL.md`)
establishes the auditability convention the questions describe: after any
mutation the agent runs `gt log short --no-interactive` to verify/surface stack
state, and each phase ends with a mandatory `Print:` statement reporting the
outcome (e.g. PR URL, slice completion). `gt log short` is also used to
enumerate stack branches for stale-PR detection and review. The
`graphite-evals.json` suite encodes "show me the current stack" as a case
requiring `gt log short`/`gt log` (read-only, no mutations). The repo does not
contain a separate doc dedicated to `gt log short`; that is NOT FOUND in scope.

**Evidence:**

```
- After mutations, run `gt log short --no-interactive` to verify stack state.
```

— `.claude/skills/qrspi-work/SKILL.md:660`

```
2. Submit the entire stack ...
3. Capture PR URLs and PR numbers from the output.
...
7. Print: "Implementation complete. `<N>` PRs submitted. Ticket moved to Code Review."
```

— `.claude/skills/qrspi-work/SKILL.md:413-429`

```
"expected_output": "Runs gt log short --no-interactive or gt log --no-interactive to display the stack visualization. ...",
"assertions": [
  {"text": "Uses gt log or gt log short (not just git branch or git log)", "type": "command_check"},
  {"text": "Includes --no-interactive flag", "type": "flag_check"},
  {"text": "Does not attempt any write/mutation operations", "type": "safety_check"}
]
```

— `evals/graphite-evals.json:33-39`

**Dependencies:** `gt log short` (read), `gt info` (per-branch PR state); orchestrator `Print:` convention.
**Implicit contracts:** Every `gt` command carries `--no-interactive`; read-only commands must not mutate; outcome must be surfaced via an explicit `Print:` line after each phase; stack state is audited via `gt log short --no-interactive`.

---

## Discovered Patterns

- **Skill = directory whose name == `name` frontmatter == `command` stem**, all
  lowercase-hyphenated, under `.claude/skills/`. Verified across all 10 skills.
  (`.claude/skills/*/SKILL.md:1-7`).
- **Thin-skill / heavy-agent split (QRSPI-specific):** each phase
  `.claude/skills/qrspi-<phase>/SKILL.md` is a thin wrapper that spawns
  `subagent_type: qrspi-<phase>` defined in `.claude/agents/qrspi-<phase>.md`.
  (`.claude/skills/qrspi-research/SKILL.md:9-11`, `qrspi-work/SKILL.md:589-591`).
- **`allowed-tools` as a security firewall:** skills lock their tool surface
  (e.g. `qrspi-research` allows only `Agent, Bash(pwd:*)`; the questions agent
  deliberately excludes Glob/Grep/Bash). (`qrspi-work/SKILL.md:624-630`).
- **`references/` are lazy-loaded sibling files**, read on demand by explicit
  instruction, not inlined — keeps `SKILL.md` small. Only `qrspi-work` uses
  this. (`qrspi-work/SKILL.md:281`, `references/review-cascade.md`).
- **Graphite command conventions encoded in evals:** every `gt` command uses
  `--no-interactive`; commits use `gt create`/`gt modify` (never raw
  `git commit`); commit messages carry a `Co-Authored-By` trailer; mutating
  commands (`submit`, `sync`) require user confirmation / safety checks.
  (`evals/graphite-evals.json`, `qrspi-work/SKILL.md:656-725`).
- **Eval suite shape:** top-level `name`+`cases`; case needs
  `id`+`prompt`+`assertions`; QRSPI suite adds `phase`, `context.files`,
  weighted `{type, check|criteria}` assertions and a 65/35 split.
  (`run_eval.py:47-55`, `suite.json`).
- **Unknown grade checks are skipped, not failed** (`passed=None`) — adding a
  suite assertion without a matching `CHECKS` entry is a silent no-op.
  (`grade.py:194-197`).
- **Devcontainer bind-mounts global Graphite config** from the host
  (`~/.config/graphite/`) and pins `@withgraphite/graphite-cli@1.8.6`.
  (`.devcontainer/devcontainer.json:46`, `.devcontainer/Dockerfile:33`).

## Inconsistencies

- **CLAUDE.md vs actual layout (agents location):** Project
  `.claude/CLAUDE.md` says "Agent prompt definitions live in `.qrspi/agents/`",
  but agents actually live in `.claude/agents/` and `.qrspi/agents/` does not
  exist. The root `.claude/CLAUDE.md` injected via system context also lists
  the older single-review-gate phrasing; the worktree's `.claude/CLAUDE.md`
  omits the Design/Plan review gate split that the system-context version
  describes. Code/layout is the source of truth; CLAUDE.md is stale.
- **`graphite-evals.json` assertion shape is ungradeable by `grade.py`:** its
  assertions are `{text, type}` with types `command_check`/`flag_check`/
  `content_check`/`workflow_check`/`safety_check`, none of which are in
  `grade.py`'s `CHECKS` registry or its type dispatcher (which handles only
  `programmatic`/`llm_judge`/`script`). The Graphite eval suite therefore
  cannot be scored by the existing harness without new code. (`grade.py:146-157`,
  `grade.py:308-318` vs `evals/graphite-evals.json:9-16`).
- **Eval harness is a stub:** `run_eval.py:117-137` does not invoke any agent
  (placeholder), and `grade.py`'s `run_llm_judge`/`run_script_check` return
  `passed=None`. `docs/eval-system.md:108` confirms the pipeline "runs
  end-to-end but produces zeros." Any acceptance criterion relying on eval
  scores cannot currently be measured.
- **Graphite skill name mismatch:** `evals/graphite-evals.json` declares
  `"skill_name": "graphite"` while the ticket/questions and naming convention
  point to `using-graphite-cli`. The pre-existing eval suite is named for a
  skill that does not (yet) exist in-repo under either name.
- **Skill-creator / Graphite references out of scope:** Q1, Q5, Q7, Q8, Q9, Q12
  target the Anthropic skill-creator skill and Graphite "references material"
  that live in the global `~/.claude/skills/` tree, outside `REPO_ROOT`. These
  could not be read under the project-scope firewall and are answered from
  in-repo equivalents only.
