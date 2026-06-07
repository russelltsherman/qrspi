# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-04T00:00:00Z
**Generated:** 2026-06-04T00:00:00Z
**Status:** draft

## Q1: Where do existing agent skills physically live in this repo, and what is the on-disk layout of a single skill (SKILL.md plus any references/, scripts/, assets/ subdirectories)?

**Answer:** Skills live in `.claude/skills/<skill-name>/SKILL.md`. There are 10 skill directories, each containing exactly one `SKILL.md`. Only ONE skill has a subdirectory: `qrspi-work/references/` (containing `review-cascade.md`). No skill in this repo has a `scripts/` or `assets/` subdirectory. Companion **agent definitions** live separately in `.claude/agents/qrspi-<phase>.md` (8 files) — most skills are thin wrappers that spawn an agent of the same name. The README documents this split.
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

— `.claude/skills/` directory listing

```
  agents/              # phase agent definitions (qrspi-questions.md … qrspi-pr.md)
  skills/              # Slash-command wrappers that invoke the phase agents
    qrspi-ticket/  qrspi-questions/  …  qrspi-work/   # references/ subdir
```

— `README.md:78-96`
**Dependencies:** Skills wrappers depend on the sibling `.claude/agents/qrspi-*.md` definitions (each wrapper spawns its agent via `subagent_type`). The `qrspi-work` SKILL depends on `references/review-cascade.md`.
**Implicit contracts:** A skill is a directory whose name matches the `name:` frontmatter field, containing a `SKILL.md`. Subdirectories (`references/`) are optional and referenced by relative path from the body. There is no skill-storage "module" in code — discovery is performed by the Claude Code harness itself, not by any file in this repo.

## Q2: How is a skill's content surfaced to an agent at invocation time — is the full SKILL.md body loaded, or only the frontmatter description until triggered, and where is that loading defined?

**Answer:** NOT FOUND in code — no skill loader/registration module exists inside REPO_ROOT. Skill loading is performed by the Claude Code harness (outside the repo), not by repo code. However, the repo's own design demonstrates the convention indirectly: SKILL.md `description` fields are written as triggering hints ("Use when…", "Trigger on any variant of…"), implying the description is what the harness reads to decide triggering, with the body loaded on invocation. This is inferred from how descriptions are authored (see `qrspi-work` description below), not from a loader definition.
**Evidence:**

```
description: "Single entry point for autonomous QRSPI feature development. Use when
the user asks to 'work on' a ticket (e.g., 'work on RUS-42'). … Trigger on any variant
of: 'work on <ticket-id>', 'continue <ticket-id>', 'pick up <ticket-id>', …"
```

— `.claude/skills/qrspi-work/SKILL.md:3` (frontmatter description authored as a trigger signal)
**Dependencies:** The loader is the host harness (Claude Code), not a repo module. No `*.py`/`*.js` in REPO_ROOT loads or registers skills.
**Implicit contracts:** Descriptions are written in trigger-oriented language; the body is the operative prompt. A new skill must put its triggering cues in `description` and its full instructions in the body.

## Q3: What exact frontmatter fields does a SKILL.md require and which are optional, according to the agentskills.io / skill-creator convention already used in this repo?

**Answer:** Observed frontmatter fields across the 10 SKILL.md files (the de-facto convention, since no validator enforces them): `name`, `description`, `command`, `argument-hint`, `allowed-tools`. The wrapper skills (questions/research/design/structure/plan/worktree/implement/pr/work/ticket) all carry all five. `name` and `description` are universal. `command`/`argument-hint` are present on every skill here (all are slash-commands). `allowed-tools` scopes the tools the skill may use. Note: the separate **agent** files in `.claude/agents/` use a DIFFERENT frontmatter shape — `name`, `description`, and a nested `claude: { tools: … }` block (not `allowed-tools`).
**Evidence:**

```
---
name: qrspi-research
description: Map codebase facts by answering questions from the Questions phase. …
command: /qrspi-research
argument-hint: <ticket-id>
allowed-tools: Agent, Bash(pwd:*)
---
```

— `.claude/skills/qrspi-research/SKILL.md:1-7`

```
---
name: qrspi-questions
description: Internal QRSPI workflow agent — generates 8-15 technical questions …
claude:
  tools: Read, Write
---
```

— `.claude/agents/qrspi-questions.md:1-6` (agent frontmatter, distinct from skill frontmatter)
**Dependencies:** None enforced in-repo. The agentskills.io / skill-creator convention referenced in the question is an external standard — NOT FOUND as a file in REPO_ROOT (no `skill-creator` skill or schema is checked into this repo; searched `find . -iname '*skill-creator*'` and `grep -rl skill-creator`, found only mentions in `.claude/agents/qrspi-structure.md` and the questions artifact).
**Implicit contracts:** A skill SKILL.md uses `allowed-tools`; an agent definition uses `claude.tools`. `allowed-tools` can scope a tool to a subcommand, e.g. `Bash(pwd:*)`.

## Q4: What is the Anthropic "skill builder" skill referenced in the ticket — is it the `skill-creator` skill present in this environment, and what inputs/invocation does it expect?

**Answer:** NOT FOUND — the question targets a resource outside the project scope. The `skill-creator` skill is NOT checked into REPO_ROOT. Searches `find . -iname '*skill-creator*'` (no hits) and `grep -rl "skill-creator" . --include="*.md"` returned only two non-definition mentions: `.claude/agents/qrspi-structure.md` and `.qrspi/RUS-28/questions.md`. `skill-creator` exists only as an environment-provided skill (listed in the session's available-skills, outside the repo), so its definition, inputs, and invocation cannot be observed from within REPO_ROOT.
**Evidence:**

```
$ grep -rl "skill-creator" . --include="*.md"   # excluding .git
.claude/agents/qrspi-structure.md
.qrspi/RUS-28/questions.md
$ find . -iname '*skill-creator*'   # no output
```

— search results scoped to REPO_ROOT
**Dependencies:** None in-repo.
**Implicit contracts:** N/A — out of project scope.

## Q5: How are slash-command wrappers wired to skills in this repo, and would a new "writing GitLab pipelines" skill need a wrapper or only a SKILL.md?

**Answer:** In this repo a "skill" IS the slash-command wrapper (the `SKILL.md` carries `command: /<name>`). The QRSPI pattern is a TWO-FILE split for workflow phases: a thin `SKILL.md` wrapper in `.claude/skills/<name>/` declares the slash command and `allowed-tools`, then spawns a heavyweight agent definition in `.claude/agents/<name>.md` via the `Agent` tool (`subagent_type: <name>`). The wrapper holds almost no logic — it parses `$ARGUMENTS`, resolves `REPO_ROOT` from `pwd`, fetches the ticket (if needed), spawns the agent, and verifies the output artifact. A self-contained skill that does NOT delegate to an agent is also valid: `qrspi-ticket/SKILL.md` (119 lines) holds its full prompt inline with no agent companion. A new "writing GitLab pipelines" skill that is purely instructional (no sub-agent fan-out) would need only a `SKILL.md` — the agent split is a QRSPI orchestration convention, not a requirement.
**Evidence:**

```
4. Spawn the agent via the `Agent` tool:
   - `subagent_type: qrspi-design`
   - Prompt body containing the six inputs:
     - `TICKET_ID = <ticket-id>`
     …
All prompt content lives in `.claude/agents/qrspi-design.md`.
```

— `.claude/skills/qrspi-design/SKILL.md:11,17-25`
**Dependencies:** Wrapper → `Agent` tool → `.claude/agents/<name>.md`. A non-delegating skill (`qrspi-ticket`) has no such dependency.
**Implicit contracts:** Wrappers list `Agent` in `allowed-tools` and reference the agent by `subagent_type` equal to the agent's `name`. Self-contained skills list the concrete tools they use (e.g. `Read, Glob, Grep, Write, Bash`).

## Q6: Is there a naming convention or registry that skill directory names must conform to (e.g., kebab-case, prefix), and where is that constraint enforced or documented?

**Answer:** No enforcement exists in REPO_ROOT — there is no registry file and no validator. The convention is OBSERVED, not enforced: every skill directory is kebab-case and every QRSPI skill carries the `qrspi-` prefix. The directory name equals the `name:` frontmatter value. No file in the repo documents or checks a naming rule (grep for "kebab"/"naming convention"/"skill name" found only `qrspi-ticket/SKILL.md:55` — an unrelated reference about ticket content — and `docs/qrspi_claude_code_guide.md:381` about CLAUDE.md project conventions generally, neither constraining skill directory names).
**Evidence:**

```
$ grep -rin "kebab|naming convention|directory name|skill name" .claude docs
.claude/skills/qrspi-ticket/SKILL.md:55:- Directory structures, file layouts, or naming conventions
docs/qrspi_claude_code_guide.md:381:Your `.claude/CLAUDE.md` should include project-specific patterns: naming conventions, …
```

— search scoped to REPO_ROOT; neither hit constrains skill directory naming
**Dependencies:** None.
**Implicit contracts:** Directory name == frontmatter `name`; kebab-case; project skills prefixed `qrspi-`. A new skill should follow kebab-case (e.g. `writing-gitlab-pipelines`) to match the observed convention, but nothing mechanically rejects a deviation.

## Q7: What is enforced when a SKILL.md exceeds the body size limits the ticket cites (under 500 lines / 5000 tokens) — is there validation tooling, or is it convention only?

**Answer:** Convention only — NO validation tooling enforces SKILL.md size in REPO_ROOT. No script checks line count or token count of a SKILL.md. Observed line counts show the convention is NOT uniformly honored: `qrspi-work/SKILL.md` is **565 lines** (well over a 500-line guideline), while the thin wrappers are 25-35 lines and `qrspi-ticket` is 119. The eval suite (`evals/suite.json`) does include a `line_count` assertion, but it targets generated artifacts (`design.md <= 300`), NOT SKILL.md files. There is no eval case whose subject is a SKILL.md.
**Evidence:**

```
   28 .claude/skills/qrspi-design/SKILL.md
  119 .claude/skills/qrspi-ticket/SKILL.md
  565 .claude/skills/qrspi-work/SKILL.md
   25 .claude/skills/qrspi-worktree/SKILL.md
```

— `wc -l .claude/skills/*/SKILL.md` (qrspi-work exceeds a 500-line limit)

```
"check": "line_count('design.md') <= 300",
```

— `evals/suite.json:242` (size check targets design.md artifacts, not SKILL.md)
**Dependencies:** None.
**Implicit contracts:** Body-size limits are a documentation guideline, not enforced. The one large skill (`qrspi-work`, 565 lines) shows the limit is aspirational in this repo.

## Q8: How do existing skills handle reference material that would otherwise bloat SKILL.md — what is the established pattern for splitting content into `references/` and how are those files referenced from the body?

**Answer:** Exactly one skill uses the pattern: `qrspi-work` splits its review-cascade logic into `references/review-cascade.md` and refers to it by relative path from the body. The body cites it inline as `references/review-cascade.md`. The referenced file is a standalone Markdown doc (begins with an H1 `# Review Cascade Logic (PR-gated)`).
**Evidence:**

```
phase's own artifacts (see `references/review-cascade.md`). Do NOT touch downstream phases
```

— `.claude/skills/qrspi-work/SKILL.md:282` (the only in-body reference to a references/ file)

```
# Review Cascade Logic (PR-gated)

Artifacts form a dependency chain, now split across **per-phase PR branches**:
```

— `.claude/skills/qrspi-work/references/review-cascade.md:1-3`
**Dependencies:** `qrspi-work/SKILL.md` → `qrspi-work/references/review-cascade.md` (relative path).
**Implicit contracts:** A `references/` file is a sibling Markdown doc under the skill directory, referenced by relative path `references/<file>.md` from the body, and reads as a self-contained topic document with its own H1. This is the single established example to mirror.

## Q9: Are there existing skills with `scripts/` or `assets/` subdirectories, and what conventions (shebang, permissions, language) do those scripts follow that a new skill must match?

**Answer:** NOT FOUND — no skill under `.claude/skills/` has a `scripts/` or `assets/` subdirectory. The only skill subdirectory in the repo is `qrspi-work/references/`. Scripts in this repo live at the top-level `scripts/` directory (NOT inside any skill). For reference on script conventions there: executable scripts use `#!/usr/bin/env python3` shebangs and `0755` permissions (e.g. `run_eval.py`, `check_scope.py`, `grade.py` are `-rwxr-xr-x`), while importable modules with `_test.py` siblings are `0644` (e.g. `qrspi_resolve_state.py`). Language is Python 3, stdlib-only for the tested modules.
**Evidence:**

```
$ find .claude/skills -type d
.claude/skills
.claude/skills/qrspi-work
.claude/skills/qrspi-work/references     # only subdir; no scripts/ or assets/
…
```

```
-rwxr-xr-x  scripts/run_eval.py      # #!/usr/bin/env python3, 0755
-rw-r--r--  scripts/qrspi_resolve_state.py   # importable module, 0644
```

— `scripts/` listing
```
#!/usr/bin/env python3
"""Execute an eval suite against a skill/agent prompt version."""
```

— `scripts/run_eval.py:1-2`
**Dependencies:** None for skills (no skill bundles scripts). Top-level `scripts/` is a separate concern.
**Implicit contracts:** If a new skill needed a script, the repo's prevailing script convention is `#!/usr/bin/env python3`, executable bit set, stdlib-only, with a `_test.py` sibling for any logic — but there is NO precedent for a script living inside a skill directory.

## Q10: How are skills validated or eval-tested in this repo — does `skill-creator` provide an eval loop, and is there a `scripts/run_eval.py` or `evals/` harness that applies to skills?

**Answer:** There is a `scripts/run_eval.py` + `evals/` harness, but it is a NON-FUNCTIONAL PLACEHOLDER — its agent-execution core is a stub. `execute_single()` does not invoke any agent; it returns empty output with an inline comment marking where real execution would go. The suite (`evals/suite.json`) defines 15 cases targeting QRSPI workflow PHASES (questions/research/design/structure/plan/worktree/implement/pr), NOT skill-definition authoring. So skills are not eval-tested by this harness in any executable sense. The `skill-creator` eval loop referenced in the question is external (not in REPO_ROOT — see Q4). The repo's actual validation is the stdlib unit tests for the Python resolver/persist/pr-state modules (`scripts/qrspi_*_test.py`).
**Evidence:**

```
    In a real implementation, this would:
    1. Spin up an isolated container/sandbox
    …
        # ── Placeholder for agent execution ──
        # Replace this block with actual agent invocation:
        messages = build_messages(case)
        result.output = ""
        result.files = []
```

— `scripts/run_eval.py:101-137` (stubbed execution; the harness produces no real agent output)
**Dependencies:** `run_eval.py` reads `evals/suite.json` and fixtures under `evals/fixtures/`; writes `results.json`. None of it targets `.claude/skills/`.
**Implicit contracts:** `evals/suite.json` must have top-level `name` + `cases`; each case needs `id`, `prompt`, `assertions` (validated in `load_suite`, `run_eval.py:42-58`). Assertions are typed `programmatic` / `script` / `llm_judge`. But because execution is stubbed, running it yields empty transcripts — confirmed placeholder.

## Q11: What does the skill-creator eval loop measure for a skill's description (triggering accuracy), and what format must eval cases take?

**Answer:** NOT FOUND — the question targets the external `skill-creator` skill, which is outside project scope (see Q4). No in-repo component measures a skill description's triggering accuracy; the local `evals/suite.json` cases measure ARTIFACT quality of workflow phases (question counts, section presence, citation compliance, scope enforcement), not whether a skill description triggers. For the format of the LOCAL eval harness (the only one present): each case is a JSON object with required `id`, `prompt`, `assertions`, plus optional `name`, `phase`, `context.files`, `context.conversation_history`, `tags`, `difficulty`, `split`. Assertions carry a `type` (`programmatic` | `script` | `llm_judge`), a `check`/`criteria`, and a `weight`. This local format is NOT the skill-creator triggering-eval format the question asks about.
**Evidence:**

```
"assertions": [
  { "type": "programmatic", "check": "question_count('questions.md') >= 8", "weight": 1.0 },
  { "type": "llm_judge",
    "criteria": "Questions are specific and answerable by reading code …", "weight": 2.0 }
]
```

— `evals/suite.json:26-77` (local case shape: programmatic + llm_judge assertions on artifacts)

```
case_required = {"id", "prompt", "assertions"}
```

— `scripts/run_eval.py:53` (required fields for a local eval case)
**Dependencies:** Local harness only. skill-creator's triggering-eval mechanics are out of scope.
**Implicit contracts:** Local eval cases are JSON with `id`/`prompt`/`assertions`; triggering-accuracy measurement is not a feature of the in-repo harness.

## Q12: How is skill invocation or triggering observable during a session — is there logging, a hook, or a transcript signal that confirms a skill was loaded and used?

**Answer:** NOT FOUND inside REPO_ROOT — there is no hooks directory, no `settings.json`/`settings.local.json`, and no skill-invocation logging committed in the worktree. `find … -type d -name hooks` returns nothing in the repo; the only "hook" mentions in docs are unrelated (a sample webhook ticket title, React hooks in fixtures). The repo's CLAUDE.md references a PreToolUse hook at `~/.agents/hooks/pre-tool-memory.sh`, but that path is OUTSIDE REPO_ROOT (home directory) and must not be read per scope rules — it is a host-level memory hook, not skill-invocation observability. The `evals/` harness has fields for `transcript`/`tool_calls`/`tool_trace` in `ExecutionResult`, but they are populated only by the stubbed (non-functional) executor, so they confirm nothing at runtime.
**Evidence:**

```
$ find . -type d -name hooks    # (excluding .git) — no output
$ find . -name 'settings*.json' # — no output
```

— searches scoped to REPO_ROOT

```
    tool_calls: list = field(default_factory=list)
    transcript: list = field(default_factory=list)
```

— `scripts/run_eval.py:27-28` (transcript/tool-call capture fields exist but are filled only by the stub)
**Dependencies:** Any real observability is provided by the host harness / a home-directory hook (`~/.agents/hooks/pre-tool-memory.sh`, out of scope), not by repo code.
**Implicit contracts:** None in-repo. Skill-invocation observability is a host concern; the repo carries no hook or logging configuration for it.

---

## Discovered Patterns

- **Two-file phase pattern:** Workflow phases are split into a thin `SKILL.md` wrapper (`.claude/skills/<name>/`, ~25-35 lines: parse args, resolve REPO_ROOT from `pwd`, optionally fetch the ticket, spawn `subagent_type: <name>`, verify artifact) and a heavyweight agent definition (`.claude/agents/<name>.md`, ~70-565 lines, the real prompt). Wrappers carry `allowed-tools` including `Agent`; agents carry `claude.tools`.
- **Self-contained skill variant:** `qrspi-ticket` is the one non-delegating skill — full prompt inline, no agent companion, broader `allowed-tools` (`Read, Glob, Grep, Write, Bash, mcp__linear-…`). A purely instructional new skill would follow this shape.
- **Naming:** every skill directory is kebab-case, prefixed `qrspi-`, and the directory name equals the frontmatter `name`. Convention only — unenforced.
- **Tool-exclusion firewalls:** agents constrain capability via their `claude.tools` list (e.g. the questions agent has only `Read, Write` to make codebase exploration structurally impossible; the research agent has `Read, Write, Glob, Grep` but no MCP/Bash mutation).
- **Frontmatter description as trigger:** descriptions are authored in "Use when… / Trigger on…" language, treated as the matching signal for auto-invocation.
- **Script conventions (top-level `scripts/`, not in skills):** `#!/usr/bin/env python3`, executables `0755`, importable modules `0644` with `_test.py` siblings, stdlib-only.
- **references/ splitting:** the single precedent (`qrspi-work/references/review-cascade.md`) is a standalone H1 Markdown doc referenced by relative path `references/<file>.md` from the body.

## Inconsistencies

- **Body-size limit vs. reality:** the ticket-cited "<500 lines" guideline is contradicted by `qrspi-work/SKILL.md` at **565 lines** (`wc -l`). No tooling enforces the limit, so it has already been exceeded in-repo.
- **Two distinct frontmatter shapes for similar files:** skills use `allowed-tools` (flat); agents use a nested `claude: { tools: … }`. A new author could easily mix them; nothing validates which is correct.
- **`evals/` harness is documented and shipped but non-functional:** `scripts/run_eval.py:101-137` is an explicit placeholder (empty output, no agent invocation), yet `evals/suite.json` ships 15 fully-specified cases as if runnable. CLAUDE.md correctly labels it "a non-functional placeholder," but the presence of a complete suite implies otherwise.
- **`skill-creator` referenced but absent from the repo:** `.claude/agents/qrspi-structure.md` mentions `skill-creator`, and the environment lists it, but no `skill-creator` definition is checked into REPO_ROOT — questions Q4/Q11 about its eval loop cannot be answered from project files.
- **Memory hook lives outside the project:** CLAUDE.md wires a PreToolUse hook at `~/.agents/hooks/pre-tool-memory.sh`, but no hook configuration (or `settings.json`) exists inside the repo, so skill-invocation observability is entirely host-side.
