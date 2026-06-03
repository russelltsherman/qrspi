# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-03T00:00:00Z
**Generated:** 2026-06-03T13:44:56Z
**Status:** draft

## Q1: What is the exact on-disk directory layout of an existing skill (SKILL.md plus the optional `references/`, `scripts/`, `assets/` subdirectories), and where do skills physically live in this repo?

**Answer:** Skills live under `.claude/skills/<skill-name>/`, one directory per skill, each containing a `SKILL.md`. There are 10 skill directories, all named `qrspi-*`. Only ONE skill uses an optional subdirectory: `qrspi-work/references/review-cascade.md`. No skill in this repo uses `scripts/` or `assets/` subdirectories. The convention is: directory name == frontmatter `name`, with `SKILL.md` (uppercase) as the body file. Wrapper skills are tiny (25-35 lines); `qrspi-ticket` (119 lines) and `qrspi-work` (565 lines) are the only large ones.
**Evidence:**

```
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

— `.claude/skills/` (directory listing)
**Dependencies:** README.md documents this layout (`.claude/skills/` = "Slash-command wrappers", `.claude/agents/` = phase logic).
**Implicit contracts:** One directory per skill; the body file is `SKILL.md` (uppercase); `references/` is the only optional subdir actually used. `assets/` and `scripts/` subdirs are supported by the spec mentioned in the question but unused in this repo.

## Q2: How does a skill's content get loaded and surfaced to an agent at invocation time — is the SKILL.md body read whole, and are `references/` files loaded lazily or eagerly?

**Answer:** NOT FOUND (in-repo loader). There is no skill-loading harness code in this repository — `.claude/` contains only data (CLAUDE.md, `agents/`, `skills/`, `workflows/`); there is no settings.json or runtime that reads SKILL.md. The loading is performed by the Claude Code harness, which is external to the repo. However, the repo's OWN convention is observable: `references/` files are loaded **lazily** — the SKILL.md body references them inline ("see `references/review-cascade.md`") rather than inlining their content, implying the harness loads referenced files on demand, not eagerly. The wrapper skills are deliberately "thin" and defer all body content to `.claude/agents/*.md`, also implying selective/lazy loading.
**Evidence:**

```
phase's own artifacts (see `references/review-cascade.md`). Do NOT touch downstream phases
```

— `.claude/skills/qrspi-work/SKILL.md:282`

```
Thin wrapper that spawns the `qrspi-research` agent. All prompt content lives in `.claude/agents/qrspi-research.md`.
```

— `.claude/skills/qrspi-research/SKILL.md:11`
**Dependencies:** The loader is the external Claude Code harness (outside REPO_ROOT — not inspectable per scope rules).
**Implicit contracts:** References are pointed to, not inlined — the body assumes the reader can pull `references/<file>` lazily. Search attempted: `grep -rn "references/" .claude docs`; `ls -la .claude/` (no manifest/settings file present).

## Q3: What fields are required in the SKILL.md YAML frontmatter (e.g. name, description, and any others), and what are their format/length constraints?

**Answer:** Every SKILL.md opens with YAML frontmatter (`---` delimited) carrying five keys consistently: `name`, `description`, `command`, `argument-hint`, `allowed-tools`. `name` matches the directory name. `description` is a single sentence describing purpose + a "Use when…" trigger clause. `command` is the slash command (`/qrspi-<x>`). `argument-hint` shows expected args (e.g. `<ticket-id>`). `allowed-tools` is a comma-separated tool allowlist. No numeric length constraint is enforced in-repo; descriptions range from ~15 words to a multi-sentence quoted block (`qrspi-work`). When the description contains commas/colons/quotes it is wrapped in double quotes (qrspi-work).
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
**Dependencies:** `allowed-tools` values map to harness tool names (Agent, Read, Write, Edit, Bash, Glob, Grep, and `mcp__linear-*` MCP tools). `Bash(pwd:*)` shows the scoped-permission syntax.
**Implicit contracts:** Frontmatter is the first thing in the file; `name` must equal the directory name (Q5); multi-clause descriptions get double-quoted to stay valid YAML.

## Q4: How is a skill exposed as a slash command, and is a separate wrapper file required (the project notes "slash-command wrappers live in `.claude/skills/`")?

**Answer:** A skill is exposed as a slash command via the `command:` frontmatter key inside its own SKILL.md (e.g. `command: /qrspi-research`). For the QRSPI phase skills, the architecture splits responsibilities: a **thin wrapper** SKILL.md in `.claude/skills/<x>/` declares the command and spawns a heavyweight **agent** defined in `.claude/agents/<x>.md` via the `Agent` tool (`subagent_type: <x>`). The wrapper itself is the slash-command surface; the agent file is NOT a skill and has no slash command. Not every skill needs a paired agent — `qrspi-ticket` and `qrspi-work` are self-contained skills (no `.claude/agents/qrspi-ticket.md` or `qrspi-work.md` exist). So: the wrapper file IS the skill; pairing with an agent is the QRSPI phase pattern, not a universal requirement.
**Evidence:**

```
3. Spawn the agent via the `Agent` tool:
   - `subagent_type: qrspi-research`
```

— `.claude/skills/qrspi-research/SKILL.md:17-18`

```
  skills/              # Slash-command wrappers that invoke the phase agents
```

— `README.md:86`
**Dependencies:** Wrapper → agent (one-way spawn). `qrspi-ticket`/`qrspi-work` have no agent dependency.
**Implicit contracts:** The slash command lives in `command:`; a skill self-contained in its SKILL.md needs no separate agent file. The `.claude/agents/` directory holds 8 phase agents (questions, research, design, structure, plan, worktree, implement, pr) — none for ticket or work.

## Q5: What naming convention governs the skill's directory name and frontmatter `name` (e.g. `using-graphite-cli` vs `using graphite cli`), and how must it match the ticket's intended invocation?

**Answer:** Names are **lowercase, hyphen-separated (kebab-case)**, with NO spaces. The directory name, the frontmatter `name`, and the `command` slug are all identical: directory `qrspi-research/` ↔ `name: qrspi-research` ↔ `command: /qrspi-research`. All 10 skills follow this exactly. Therefore a "using graphite cli" skill must be `using-graphite-cli` (directory `using-graphite-cli/`, `name: using-graphite-cli`, `command: /using-graphite-cli`) — the spaced form is invalid by convention. This matches the global-memory reference exactly (Q6).
**Evidence:**

```
### .claude/skills/qrspi-design/SKILL.md
name: qrspi-design   command: /qrspi-design
### .claude/skills/qrspi-implement/SKILL.md
name: qrspi-implement   command: /qrspi-implement
### .claude/skills/qrspi-worktree/SKILL.md
name: qrspi-worktree   command: /qrspi-worktree
```

— frontmatter across `.claude/skills/*/SKILL.md` (dir name == name == command slug, all kebab-case)
**Dependencies:** The slash-command invocation (`/<name>`) is derived directly from `name`.
**Implicit contracts:** dir == name == command-slug, kebab-case, no spaces. A space in the name would break the slash command and the directory mapping.

## Q6: Does the project already contain a graphite-related skill, memory note, or convention (the global memory references "All git actions use the using-graphite-cli skill") that this skill must align with or supersede?

**Answer:** NO graphite skill exists in-repo yet (`.claude/skills/` has only `qrspi-*`). The `using-graphite-cli` skill referenced by global memory lives OUTSIDE REPO_ROOT (in `~/.claude/` / global config) and is out of scope — NOT FOUND within the project per scope rules. However, the repo is heavily graphite-dependent and carries a strong in-repo CONVENTION the new skill must align with: (1) `evals/graphite-evals.json` is a dedicated 5-case eval suite named `"graphite"` covering commit/submit/log/move/sync — effectively a behavioral spec for the skill; (2) `qrspi-work/SKILL.md` and `qrspi-batch.js` encode extensive `gt` usage rules (always `--no-interactive`, single-commit-per-branch, `gt create`/`gt modify`, `gt submit --publish`, co-authorship trailer, never `gt sync` mid-feature, HARD STOP on infrastructure errors). The README lists Graphite CLI as a core dependency.
**Evidence:**

```
{
  "skill_name": "graphite",
  "evals": [
    { "id": 1, "prompt": "...commit my changes...",
      "expected_output": "Uses gt create or gt modify with -a -m flags, --no-interactive, and includes co-authorship trailer..." },
```

— `evals/graphite-evals.json:1-7`

```
- [Graphite CLI](https://graphite.dev) (`gt`) for stacked PRs
```

— `README.md:166`
**Dependencies:** `evals/graphite-evals.json` (behavioral spec); `qrspi-work/SKILL.md` "Git/Graphite Rules" section (lines 480-521); `qrspi-batch.js` (gt orchestration). Global `using-graphite-cli` skill is out of scope.
**Implicit contracts:** Any new graphite skill should be consistent with the eval suite's assertions and the qrspi-work git rules. Note a tension: graphite-evals.json case 1 expects `-a`/`-u` staging, while qrspi-work/SKILL.md:498 says "NEVER use `-a`" — see Inconsistencies.

## Q7: What governs the SKILL.md size limit referenced in acceptance criteria (under 500 lines / 5000 tokens) — is it enforced anywhere, or purely a convention to follow?

**Answer:** NOT enforced anywhere in this repo. There is no in-repo validator, linter, hook, or test that checks SKILL.md line/token counts (`.claude/` has no settings/manifest; the eval harness `grade.py` has a `line_count` check but it is wired only to artifact files like `design.md`, never to SKILL.md). It is purely a convention — and an aspirational one: of the existing skills, all wrappers are far under 500 lines (25-35), but `qrspi-work/SKILL.md` is **565 lines**, already exceeding a 500-line target. So the codebase neither enforces nor uniformly honors the limit.
**Evidence:**

```
  565 .claude/skills/qrspi-work/SKILL.md
  119 .claude/skills/qrspi-ticket/SKILL.md
   35 .claude/skills/qrspi-implement/SKILL.md
   28 .claude/skills/qrspi-design/SKILL.md
```

— `wc -l .claude/skills/*/SKILL.md`

```
def line_count(filename: str, max_lines: int, result: dict) -> tuple[bool, str]:
```

— `scripts/grade.py:35` (a generic check; suite.json only applies it to `design.md` ≤300, never to any SKILL.md)
**Dependencies:** None — no enforcement path exists.
**Implicit contracts:** Size is a convention; existing skills mostly stay small but qrspi-work breaks 500. A skill-size limit would have to be self-policed by the author.

## Q8: How do existing skills encode hard rules versus soft guidance (the ticket requires the single-commit-per-branch convention as a "hard rule")?

**Answer:** Hard rules are encoded with strong formatting signals: **bold** lead-ins, ALL-CAPS imperatives, dedicated named sections, and explicit "rule" framing. `qrspi-work/SKILL.md` is the canonical example — it has a "Git/Graphite Rules" bulleted section, a "Staging — NEVER use `-a`" subsection, and a "HARD STOP" section. Single-commit-per-branch specifically appears as a bolded bullet "**One commit per phase branch** (Graphite convention)". Soft guidance is plain prose or numbered procedural steps without caps/bold. Prohibitions get a section header and capitalized verbs (NEVER, Do NOT, HARD STOP).
**Evidence:**

```
- **One commit per phase branch** (Graphite convention): `gt create` opens the branch with
  its commit; re-running within the same phase amends with `gt modify` (no `-c`).
```

— `.claude/skills/qrspi-work/SKILL.md:485-487`

```
### Staging — NEVER use `-a`

`-a` stages unrelated untracked files and makes `gt undo` destroy them. Stage specific files.
```

— `.claude/skills/qrspi-work/SKILL.md:498-500`
**Dependencies:** None.
**Implicit contracts:** Hard rule = bold + CAPS + dedicated section + a rationale ("why"). The "why" sentence after each rule is a consistent pattern (rule, then justification).

## Q9: How do existing skills handle "never do X" warnings such as forbidding raw `git rebase`/`git commit --amend` on tracked branches — formatting, placement, and emphasis?

**Answer:** Prohibitions are placed in dedicated sections near the end of the relevant rules block, formatted with ALL-CAPS keywords (NEVER, Do NOT, forbidden, HARD STOP), bold emphasis, and each followed by a rationale. The strongest example is the "HARD STOP: Infrastructure Errors Are Not Puzzles To Solve" section, which uses a numbered imperative list and an "Explicitly forbidden:" enumeration (chmod, env-var routing, "raw `git` to bypass a broken `gt`", sudo). The `qrspi-ticket` skill uses an "Anti-patterns — do NOT include" section with a bullet list of forbidden content. Pattern: name the forbidden action, mark it forbidden in caps/bold, give the consequence/reason.
**Evidence:**

```
**Explicitly forbidden:** `chmod`/`chown`; routing around config via env vars
(`XDG_CONFIG_HOME`); copying config files elsewhere; ... using
raw `git` to bypass a broken `gt`; `sudo`/escalation; ...
```

— `.claude/skills/qrspi-work/SKILL.md:557-560`

```
### Anti-patterns — do NOT include in the ticket body

Before drafting, verify the ticket contains NONE of these:
- Specific technical approaches, tool choices, or library recommendations
```

— `.claude/skills/qrspi-ticket/SKILL.md:51-54`
**Dependencies:** None.
**Implicit contracts:** Prohibitions cluster in named sections ("Anti-patterns", "HARD STOP", "Staging — NEVER…"), use caps + bold, and pair each "never" with a reason. Note: raw `git rebase`/`commit --amend` are addressed only indirectly (the "one commit per branch" + "use `gt modify`" rules); there is no explicit "never run git rebase" line in any existing skill.

## Q10: Are there existing references in the repo to `gt continue`, `gt sync`, or Graphite workflow steps that this skill must stay consistent with?

**Answer:** Yes — extensive. `gt sync` appears with a strict guardrail: never mid-feature, only in `land` cleanup, run as `gt sync --force --no-interactive` (qrspi-work) or `gt sync --force --delete-all --no-interactive` (graphite-evals case 5). `gt continue` is NOT referenced anywhere (NOT FOUND for `gt continue` specifically). Other documented gt steps the skill must align with: `gt create`/`gt modify -c`/`gt modify` (single commit), `gt submit --publish --no-edit --no-interactive` (+`--stack` for implementation), `gt move --onto`, `gt log short --no-interactive`, `gt info`, `gt track --parent`, `gt merge --confirm`, `gt delete --force --close`, `gt rename` (stale-PR recovery). All gt commands carry `--no-interactive`.
**Evidence:**

```
- Never use `gt sync` mid-feature on a held stack except in `land` cleanup — it deletes
  branches whose PRs were closed (which is correct only after merge).
```

— `.claude/skills/qrspi-work/SKILL.md:489-490`

```
{"text": "Uses gt sync (not git pull or git fetch/merge)", "type": "command_check"},
{"text": "Includes --delete-all flag for cleaning merged branches", "type": "flag_check"},
```

— `evals/graphite-evals.json:59-61`
**Dependencies:** `qrspi-work/SKILL.md` (lines 480-521 Git/Graphite Rules), `evals/graphite-evals.json`, `qrspi-batch.js` (land worker uses gt sync), `docs/qrspi_quick_reference.md:374`.
**Implicit contracts:** `--no-interactive` on every gt command; `gt sync` only at land; `gt submit` defaults to draft non-interactively so `--publish` is required for reviewable PRs. `gt continue` is not part of this repo's vocabulary.

## Q11: How is a skill validated or evaluated in this repo — does the skill-creator eval loop or `scripts/run_eval.py` apply, and is that harness functional or a placeholder?

**Answer:** The repo has a 5-stage eval pipeline (`run_eval.py` → `grade.py` → `report.py` → `diagnose.py` → `revise.py`) driven by `evals/suite.json` (15 QRSPI cases) and a SEPARATE `evals/graphite-evals.json` (5 graphite cases). The harness is a **NON-FUNCTIONAL PLACEHOLDER**: `run_eval.py` has no real agent invocation (the execution block is a stub returning empty output), LLM-judge and script-check execution in `grade.py` are stubs returning None, only 14 of ~37 programmatic checks are implemented, and 17 of 21 fixtures are missing. `docs/eval-system.md` states "The pipeline runs end-to-end but produces zeros." CLAUDE.md confirms: "The `evals/` + `scripts/run_eval.py` harness is a **non-functional placeholder**." The skill-creator eval loop is external (global skill, out of scope). Net: the only working validation in-repo is the stdlib unit tests (`scripts/qrspi_*_test.py`) for the resolver/persist logic — NOT for skills.
**Evidence:**

```
        # ── Placeholder for agent execution ──
        # Replace this block with actual agent invocation:
        ...
        result.output = ""
        result.files = []
```

— `scripts/run_eval.py:117-134`

```
The pipeline runs end-to-end but produces zeros — the three critical gaps are agent
execution, LLM judge integration, and the 17 missing fixture files.
```

— `docs/eval-system.md:108`
**Dependencies:** `evals/suite.json`, `evals/graphite-evals.json`, `evals/fixtures/` (4/21 present), `scripts/grade.py` registry. Working tests: `scripts/qrspi_resolve_state_test.py`, `qrspi_persist_test.py`, `qrspi_pr_state_test.py`, `qrspi_resolve_test.py`.
**Implicit contracts:** A graphite skill's behavior is *specified* by `evals/graphite-evals.json` even though the harness can't execute it — that file is the de facto acceptance spec. Real verification = manual e2e + the python unit tests, per CLAUDE.md.

## Q12: What does the skill-creator skill require as inputs/process steps, since the ticket mandates the skill be built using it?

**Answer:** NOT FOUND — the question targets a resource outside the project scope. The `skill-creator` skill is a global skill (`~/.claude/...`), not present under REPO_ROOT. Searched `grep -rl "skill-creator" .` → only two in-repo mentions, neither a definition: `.claude/agents/qrspi-structure.md:40` ("Validation passes (linting, running a review tool, invoking skill-creator) are the final step of the slice") and the questions.md itself. So the repo references skill-creator as a validation step but does not define its inputs/process. Its requirements cannot be determined without reading outside REPO_ROOT, which scope rules forbid.
**Evidence:**

```
9. Validation passes (linting, running a review tool, invoking skill-creator) are the final
   step of the slice that produced the files — not a separate slice.
```

— `.claude/agents/qrspi-structure.md:40`
**Dependencies:** skill-creator is external; in-repo it is only named as a slice-final validation step.
**Implicit contracts:** Per qrspi-structure convention, invoking skill-creator (validation) belongs in the same slice that produces the skill files, not a separate slice. Search attempted: `grep -rl "skill-creator" .` (2 hits, both references not definitions).

## Q13: How is a newly created skill registered or made discoverable to the agent runtime (does it auto-appear, require a manifest update, or a restart), so its presence can be confirmed after creation?

**Answer:** NOT FOUND (no in-repo registration mechanism) — but the repo evidence strongly implies **auto-discovery by directory convention, no manifest**. There is no skill registry, index, or manifest file anywhere in `.claude/` (only `CLAUDE.md`, `agents/`, `skills/`, `workflows/`; no settings.json). New skills are added simply by creating `.claude/skills/<name>/SKILL.md` — that is how all 10 existing skills exist. The actual discovery/registration is performed by the external Claude Code harness (out of scope). README documents the directory as the registration surface ("skills/ # Slash-command wrappers"). No restart/manifest step is documented in-repo.
**Evidence:**

```
total 8
-rw-r--r--  CLAUDE.md
drwxr-xr-x  agents
drwxr-xr-x  skills
drwxr-xr-x  workflows
```

— `ls -la .claude/` (no manifest/registry/settings file)

```
  skills/              # Slash-command wrappers that invoke the phase agents
    qrspi-ticket/
    qrspi-questions/
```

— `README.md:86-95`
**Dependencies:** External harness performs discovery (outside REPO_ROOT). The `Skill` tool / slash-command surface is harness-provided.
**Implicit contracts:** Drop a `<name>/SKILL.md` into `.claude/skills/` and it is discoverable — no manifest edit. Confirming presence in-repo = verifying the directory + frontmatter exist; runtime confirmation depends on the external harness re-scanning. Search attempted: `ls -la .claude/`; `find .claude -name "*.json" -o -name "settings*"` → none.

---

## Discovered Patterns

- **Wrapper/agent split for phase skills:** Phase skills are thin SKILL.md wrappers (25-35 lines) that spawn a heavyweight agent in `.claude/agents/<x>.md` via the `Agent` tool. Self-contained skills (`qrspi-ticket`, `qrspi-work`) skip the agent and put logic directly in SKILL.md.
- **Five-key frontmatter contract:** every SKILL.md carries `name`, `description`, `command`, `argument-hint`, `allowed-tools`, in that order, `---` delimited.
- **kebab-case identity triple:** directory name == frontmatter `name` == `command` slug, always lowercase-hyphenated.
- **Rule + rationale pairing:** every hard rule/prohibition is immediately followed by a one-sentence "why" (e.g. "NEVER use `-a`. `-a` stages unrelated untracked files…").
- **Emphasis grammar for severity:** bold for important rules, ALL-CAPS keywords (NEVER, Do NOT, HARD STOP, forbidden) for prohibitions, dedicated named sections for rule clusters.
- **Templates as single source of truth:** skills reference `.qrspi/templates/*` rather than inlining output formats (README.md:126).
- **Heavy graphite coupling:** `gt` with `--no-interactive`, single-commit-per-branch, `--publish` on submit, `gt sync` only at land, and a HARD-STOP-on-infra-error stance pervade the orchestration layer.
- **Behavioral specs as JSON eval files:** `evals/graphite-evals.json` (named `"graphite"`) already encodes the expected behavior of a graphite skill in 5 cases — a ready-made acceptance spec independent of the (broken) harness.
- **Real verification = python unit tests + manual e2e**, never the eval harness, per CLAUDE.md.

## Inconsistencies

- **`-a` staging contradiction:** `evals/graphite-evals.json:13` asserts a commit should "Include `-a` or `-u` flag to stage changes", but `qrspi-work/SKILL.md:498` mandates "**Staging — NEVER use `-a`**" (because `-a` stages unrelated files and `gt undo` then destroys them). A new graphite skill cannot satisfy both; the eval file and the orchestrator rules disagree on staging policy.
- **`gt sync` flag mismatch:** `graphite-evals.json:60-61` expects `gt sync --force --delete-all`, while `qrspi-work/SKILL.md:365` uses `gt sync --force` (no `--delete-all`). Same command, different documented flag set.
- **SKILL.md size convention vs. reality:** the ~500-line/5000-token convention (Q7) is honored by every wrapper but violated by `qrspi-work/SKILL.md` at 565 lines, and nothing enforces it.
- **`gt submit` confirmation policy:** `graphite-evals.json:27` requires "Asks user for confirmation before submitting (safety rule)", whereas the qrspi-work orchestrator submits non-interactively (`gt submit --publish --no-edit --no-interactive`) with no confirmation. Interactive-skill expectations and autonomous-orchestrator behavior diverge.
- **Co-authorship trailer drift:** commit trailers in `qrspi-work/SKILL.md` and `qrspi-batch.js` cite "Claude Opus 4.7 (1M context)", while this environment's model is Opus 4.8 — the documented trailer string is stale relative to the running model (cosmetic, but a code/reality mismatch).
- **skill-creator referenced but absent:** `.claude/agents/qrspi-structure.md:40` and the ticket both rely on `skill-creator`, but no such skill exists under REPO_ROOT (it is global/out-of-scope), so its contract is unverifiable from within the project.
