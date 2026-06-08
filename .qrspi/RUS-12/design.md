# Design — Create a new agent skill: using GitHub CLI

**Ticket:** RUS-12
**Research basis:** research.md @ 2026-06-03T00:00:00Z
**Generated:** 2026-06-03T00:00:00Z
**Status:** draft

## Current State

Skills in this repo live at `.claude/skills/<name>/SKILL.md`; there are ten, all `qrspi-*` (ref: Q1). Two archetypes exist: thin-wrapper skills (~25-35 lines) that spawn a sibling agent in `.claude/agents/<name>.md`, and self-contained skills (`qrspi-work` at 565 lines, `qrspi-ticket` at 119 lines) that hold all logic in `SKILL.md` itself (ref: Q1). Only one in-repo skill has a supporting subdirectory: `qrspi-work/references/review-cascade.md`, cited by a path relative to the skill directory; no skill has a `scripts/` or `assets/` subdirectory (ref: Q2).

Every in-repo `SKILL.md` carries exactly five frontmatter fields — `name`, `description`, `command`, `argument-hint`, `allowed-tools` — with `name` matching the directory and `command` stem (ref: Q3). There is no documented required-vs-optional split and no schema or validator; the five-field set is convention only (ref: Q3). Agent files use a different frontmatter shape (`name`, `description`, nested `claude.tools`) (ref: Q3).

Trigger conditions are encoded as prose inside the single `description` string ("Use when…", "Trigger on any variant of…"); no in-repo skill uses a structured `TRIGGER when / SKIP` block — that format is a global-skill convention (ref: Q5). The closest in-repo precedent for a CLI-wrapping skill is `qrspi-work`, which orchestrates `gt` and `gh`; it documents non-interactive flags, script-delegated auth/env resolution, stale-state recovery, and an infrastructure-error hard-stop firewall (ref: Q6). In-repo automation documentation centers on passing `--no-interactive` on every CLI call and resolving config via self-locating scripts; env-var routing of auth/config (e.g. `XDG_CONFIG_HOME`) is explicitly forbidden, not a sanctioned CI pattern (ref: Q7).

The project mandates that all git/Graphite/PR mutations go through the orchestration layer — "the orchestrator is the ONLY place git/graphite operations happen — sub-agents never commit"; a global directive also routes all git actions through the `using-graphite-cli` skill (ref: Q8). `gh` is used in-repo only for read/PR-metadata operations inside the orchestrator, never as free-form direct mutation by arbitrary agents (ref: Q8).

No in-repo mechanism enforces the SKILL.md body-size limit; there is no lint, eval assertion, or documented check, and `qrspi-work` itself (565 lines) already exceeds the 500-line cap unflagged (ref: Q9). The eval harness is a non-functional placeholder: `run_eval.py` is an explicit stub returning empty output, and the suite targets workflow artifacts only — no assertion validates a SKILL.md (ref: Q10, ref: Q12). There is no automated test precedent for non-code artifacts; the only tests are stdlib `_test.py` siblings for the four Python orchestration scripts, none of which reference `.claude/skills/` (ref: Q11). The `skill-creator` (Anthropic skill builder) and `using-graphite-cli` skills named in the ticket are global/harness-provided and do not exist under the repo root; their invocation contracts cannot be documented from in-repo evidence (ref: Q4, ref: Q12).

## Desired End State

A new skill `using-github-cli` exists at `.claude/skills/using-github-cli/` and ships these behaviors mapped to the acceptance criteria:

- **agentskills.io structure + valid frontmatter** → `SKILL.md` carries the five-field frontmatter convention (`name`, `description`, `command`, `argument-hint`, `allowed-tools`) with `name` matching the directory, plus a `references/` subdirectory (ref: Q2, ref: Q3).
- **Built using the Anthropic skill builder** → authored via the global `skill-creator` skill; because it is out of repo, this is a process record, not an in-repo dependency (ref: Q4). See OQ1.
- **Body under 500 lines / 5000 tokens** → `SKILL.md` body stays under the cap by self-discipline; detail offloads to `references/` (no automated gate exists) (ref: Q9).
- **Detailed `references/` covering advanced `gh api`, GraphQL examples, automation recipes, extension recommendations** → four reference files under `references/`, cited by skill-relative paths (ref: Q2).
- **Auth for interactive and CI contexts** → `SKILL.md` documents `gh auth status` verification, interactive `gh auth login`, and `GH_TOKEN`/CI patterns — while honoring the in-repo prohibition on env-var auth workarounds as a routing-around-config trick (ref: Q7). See OQ2.
- **Opinionated defaults (squash merge, branch deletion, HEREDOC body)** → encoded as explicit rules in `SKILL.md`.
- **Scripting patterns for non-interactive agent use** → a section codifying `--json`+`--jq`, `--no-pager`/`GH_PAGER=""`, `GH_PROMPT_DISABLED=1`, and exit-code logic, mirroring the `--no-interactive` discipline of `qrspi-work` (ref: Q6, ref: Q7).
- **Clear trigger conditions for activation** → trigger phrasing in the prose `description` field, matching the in-repo convention rather than a structured block (ref: Q5).

## Delta

New files:

- `.claude/skills/using-github-cli/SKILL.md` — self-contained skill (no paired agent file), under 500 lines.
- `.claude/skills/using-github-cli/references/gh-api.md` — advanced `gh api` REST patterns (pagination, `--jq`, `-X` mutations, `--cache`, `--header`).
- `.claude/skills/using-github-cli/references/graphql.md` — GraphQL query examples for multi-resource joins.
- `.claude/skills/using-github-cli/references/automation.md` — non-interactive/CI recipes, scripting patterns, env vars.
- `.claude/skills/using-github-cli/references/extensions.md` — extension and alias recommendations.

Modified files:

- `.claude/CLAUDE.md` (and/or the worktree copy) — optional: add `using-github-cli` to the available-skills list and clarify the boundary with the git-delegation mandate. See OQ3.

No new agent file (the skill is self-contained; see Decision 1). No new scripts, no new tests (no in-repo test path exists for skills) (ref: Q11). No DB/query changes.

## Pattern Decisions

### Decision 1: Skill archetype

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Self-contained `SKILL.md` (like `qrspi-work`/`qrspi-ticket`) plus `references/` | Knowledge skill, not an orchestration step; no sub-agent dispatch needed; matches `qrspi-work`'s reference-offload pattern | `SKILL.md` must stay disciplined to fit under 500 lines |
| B | Thin wrapper `SKILL.md` + `.claude/agents/using-github-cli.md` | Matches the dominant phase-skill pattern | Agents exist to do isolated work; this skill is reference guidance, not a spawned task — wrapper adds a pointless indirection |

**Recommendation:** Option A
**Rationale:** The wrapper archetype exists to spawn isolated work agents for QRSPI phases (ref: Q1); this skill is reference guidance an agent consults inline, so the self-contained archetype (`qrspi-work`, `qrspi-ticket`) plus a `references/` directory is the correct fit (ref: Q1, ref: Q2).
**NEW PATTERN?** No — both archetypes exist in-repo; this reuses the self-contained one.

### Decision 2: Frontmatter shape and trigger encoding

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Five-field convention (`name`, `description`, `command`, `argument-hint`, `allowed-tools`); triggers in prose `description` | Matches every in-repo skill exactly; consistent registration | `argument-hint` is awkward for a no-argument knowledge skill |
| B | Structured `TRIGGER when: / SKIP:` block in description (global-skill style) | More explicit triggering signal | Not used by any in-repo skill; diverges from local convention (ref: Q5) |

**Recommendation:** Option A
**Rationale:** Every in-repo `SKILL.md` carries the same five fields and encodes triggers in prose; consistency with the local convention outweighs the global `TRIGGER/SKIP` style (ref: Q3, ref: Q5). `argument-hint` can be empty or describe an optional topic.
**NEW PATTERN?** No.

### Decision 3: `allowed-tools` scope

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Permit `Bash(gh:*)` (and read tools) so the skill can run `gh` directly | Skill is actionable, not just advisory | Tension with the in-repo mandate that mutations route through the orchestrator/`using-graphite-cli` (ref: Q8) |
| B | Read-only / minimal tools; skill is pure guidance an agent applies in its own context | Avoids any conflict with the git-delegation mandate | Less self-actuating |

**Recommendation:** Option A, narrowly scoped to `gh` read/metadata and explicitly deferring all mutating git/PR operations to the orchestration layer per the project mandate (ref: Q8). `allowed-tools` is a structural capability firewall in this repo, so the scope must be deliberate (ref: Q3).
**Rationale:** The ticket requires actionable `gh` scripting patterns, but the project centralizes mutations; scoping the tool grant and documenting the boundary honors both (ref: Q3, ref: Q8). See OQ3.
**NEW PATTERN?** No — mirrors the tightly-scoped `allowed-tools` firewall pattern (ref: Q3).

### Decision 4: Verification of the new skill

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Human review + manual checks (frontmatter present, line count, reference links resolve) | Matches the only real verification path in-repo (ref: Q10, ref: Q11) | No regression gate |
| B | Add a SKILL.md eval assertion / unit test | Automated gate | No precedent exists; eval harness is a stub; would be net-new scope (ref: Q9, ref: Q10, ref: Q11) |

**Recommendation:** Option A
**Rationale:** There is no functional eval or test path for skills in-repo; verification is human review plus manual line-count/link checks, consistent with CLAUDE.md guidance (ref: Q9, ref: Q10, ref: Q11).
**NEW PATTERN?** No.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Skill encouraging direct `gh` usage conflicts with the project's "orchestrator-only mutation" / `using-graphite-cli` mandate (ref: Q8) | high | med | Scope `allowed-tools` to `gh` reads/metadata; add an explicit "defer mutations to the orchestration layer" boundary section; resolve OQ3 |
| `SKILL.md` body exceeds the 500-line / 5000-token cap with no automated guard (ref: Q9) | med | med | Offload detail to the four `references/` files; manually `wc -l` and check token budget before finishing |
| `skill-creator` (Anthropic builder) is out of repo, so the "built using the skill builder" criterion cannot be verified in-repo (ref: Q4, ref: Q12) | high | low | Treat as a process step performed in the harness; record its use; do not encode an in-repo dependency on it |
| Reference links use the wrong path style (absolute/repo-relative instead of skill-relative) (ref: Q2) | med | low | Cite all `references/*.md` by skill-directory-relative paths, matching `qrspi-work` |
| Documented CI auth via env vars is read as endorsing the forbidden env-var config workaround (ref: Q7) | med | med | Distinguish legitimate `GH_TOKEN` CI auth from routing-around-config hacks; cite the in-repo prohibition explicitly |

## Open Questions

- OQ1: The ticket mandates building this skill via the global Anthropic `skill-creator` skill, which is out of repo (ref: Q4). Should the implementer invoke `skill-creator` in the harness and treat its output as the artifact, or hand-author the skill following its conventions? How is "built using the skill builder" evidenced?
- OQ2: How far should CI auth guidance go given the in-repo prohibition on env-var config workarounds (ref: Q7)? Is `GH_TOKEN` in CI an accepted exception to that rule, or must it be framed only as a documented external-context pattern?
- OQ3: Should the new skill's `allowed-tools` permit running `gh` at all, given the "orchestrator-only mutation" / `using-graphite-cli` mandate (ref: Q8)? Is this skill advisory-only, or actionable for read/metadata `gh` operations?
- OQ4: Should `.claude/CLAUDE.md` be updated to list `using-github-cli` and codify its boundary with the git-delegation rule, or does the skill live independently of project docs?
