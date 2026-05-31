# Design — Create a new agent skill named using git worktrees

**Ticket:** RUS-30
**Research basis:** research.md @ 2026-05-31
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## Current State

This repo stores skills under `.claude/skills/<skill-name>/`, each with a `SKILL.md` at its root (ref: Q1). Nine of ten existing skills are thin wrappers (~25-35 lines) that delegate to an agent in `.claude/agents/`; only `qrspi-work` is a self-contained 730-line orchestrator, and only it uses a `references/` subdirectory (`review-cascade.md`) (ref: Q2). No skill in the repo currently ships a `scripts/` or `assets/` directory — RUS-30 introduces the first `scripts/` under a skill (ref: Q1, ref: Q5). Frontmatter consistently carries `name`, `description`, and `allowed-tools`; workflow skills add `command` and `argument-hint` (ref: Q3). The established naming style is `qrspi-<phase>` for workflow skills and gerund `using-<tool>` for knowledge skills such as the global `using-graphite-cli` (ref: Q4). No project-local skill-creator exists, but a global `skill-creator` skill is available and user memory mandates using it plus its eval loop whenever authoring a skill (ref: Q6, ref: Q13). Skill deliverables for a ticket must live inside the repo at `.claude/skills/`, never in the home directory (ref: Q7). This repo itself uses the LINKED worktree pattern (`.worktrees/<ticket-id>/`, gitignored, main checkout stays on `main`), not the bare-repo pattern the ticket asks the skill to recommend (ref: Q8). The body size budget is under 500 lines / 5000 tokens; existing self-contained skill `qrspi-ticket` is 119 lines, a good reference scale (ref: Q9). The repo's `evals/` harness is keyed to QRSPI phases and has no shape for a standalone reference skill, so validation falls to the skill-creator eval loop (ref: Q11, ref: Q13). There is no repo-local ShellCheck config and no existing `.sh` files; user memory mandates the `writing-bash-scripts` skill (ShellCheck-clean) for any bash script (ref: Q12).

## Desired End State

A new project-local skill at `.claude/skills/using-git-worktrees/` that guides agents to use git worktrees correctly. Mapping each acceptance criterion to concrete behavior:

- **agentskills.io directory structure with valid frontmatter** → `using-git-worktrees/SKILL.md` with valid YAML frontmatter (`name: using-git-worktrees`, a WHEN-to-use `description`, minimal `allowed-tools`) (ref: Q3, Q4).
- **Built using the Anthropic skill builder skill** → the implementation invokes the global `skill-creator` skill to scaffold and to run its triggering eval loop (ref: Q6, Q13).
- **SKILL.md body under 500 lines / 5000 tokens** → body targeted at ~120-180 lines, modeled on `qrspi-ticket` scale (ref: Q9).
- **Detailed reference material in references/** → exhaustive gotcha tables, alias set, and full command transcripts live in `references/` (ref: Q2, Q10).
- **scripts/ with a bare-repo bootstrap script** → `scripts/bootstrap-bare-worktree.sh`, executable, `#!/usr/bin/env bash`, ShellCheck-clean (ref: Q5, Q12).
- **Full lifecycle: create, work, PR, merge, remove, prune** → the SKILL.md body is organized around this lifecycle.
- **Bare-repo pattern documented as primary** → SKILL.md leads with bare-repo; the bootstrap script automates it (ref: Q8).
- **Parallel agent isolation (env, ports, deps)** → a dedicated body section on per-worktree `.env` copies, `.env.local` port overrides, and independent dependency installs.
- **Submodule and shared-stash gotchas** → captured in `references/gotchas.md`, linked from the body (ref: Q10).
- **Naming conventions and directory layout** → a body section with the `<type>-<short-description>` convention and the bare-repo tree.
- **Cleanup/maintenance for long-lived projects** → a body section on `git worktree list` audits, prune, lock, and merged-branch cleanup.

## Delta

New files (all under `.claude/skills/using-git-worktrees/`):

- `SKILL.md` — frontmatter + lifecycle-organized body (~120-180 lines). Sections: When to use; Primary pattern (bare-repo) with pointer to bootstrap script; Lifecycle (create → work → PR → merge → remove → prune); Naming & layout; Parallel-agent isolation; Cleanup/maintenance; Gotchas (one-line warnings linking to references); Secondary pattern (single linked worktree).
- `scripts/bootstrap-bare-worktree.sh` — bare clone + `.git` pointer file + fetch refspec config + first worktree, parameterized by repo URL and project dir. Executable, ShellCheck-clean.
- `references/gotchas.md` — submodules (incomplete support, `--force` on removal, manual moves), shared `git stash`, shared hooks, IDE caveats, tools that walk up for `.git`.
- `references/cheatsheet.md` — full command transcripts for each lifecycle stage plus an optional shell alias set for the bare-repo bootstrap.

No existing repo files are modified except adding the skill tree (and, optionally, OQ2, a one-line entry to the skill list in `.claude/CLAUDE.md`). The host repo's own `.worktrees/` convention is untouched.

## Pattern Decisions

### Decision 1: Skill body shape — self-contained vs. agent-wrapper

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Self-contained knowledge skill (body holds the guidance; references hold overflow) — like `qrspi-ticket` | Matches a reference/knowledge skill's purpose; no agent indirection; honors body-size budget by pushing detail to references | First self-contained non-workflow skill in repo (minor novelty) |
| B | Thin wrapper delegating to a `.claude/agents/using-git-worktrees.md` agent | Matches the dominant wrapper pattern | Wrong fit — there is no per-invocation task to dispatch; adds an agent file with no behavior; over-engineering |

**Recommendation:** Option A
**Rationale:** RUS-30 is a knowledge skill, not a workflow phase. The dominant wrapper pattern exists to dispatch per-invocation agent work (ref: Q2); this skill has none. `qrspi-ticket` is the in-repo precedent for a self-contained skill at an appropriate size (ref: Q9).
**NEW PATTERN?** No — `qrspi-ticket` already demonstrates a self-contained skill; this reuses it.

### Decision 2: Skill name

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | `using-git-worktrees` | Matches global knowledge-skill style `using-graphite-cli`; matches ticket title "named using git worktrees" | None material |
| B | `qrspi-worktrees` | Matches workflow-skill prefix | Misleading — this is not a QRSPI phase; collides conceptually with existing `qrspi-worktree` skill |

**Recommendation:** Option A
**Rationale:** The `qrspi-` prefix is reserved for workflow phases (ref: Q4); a `qrspi-worktree` skill already exists and means something else. The gerund `using-<tool>` style is the established convention for tool-knowledge skills (ref: Q4).
**NEW PATTERN?** No — mirrors `using-graphite-cli`.

### Decision 3: How to reconcile bare-repo recommendation with the host repo's linked pattern

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Lead with bare-repo as primary; document the single linked worktree as the secondary pattern for an existing checkout | Satisfies ticket scope guidance; acknowledges the repo's own pattern; gives agents both paths | Two patterns to keep consistent |
| B | Recommend only the bare-repo pattern | Simplest body | Contradicts the host repo's documented convention (ref: Q8); ignores the "secondary pattern" scope requirement |

**Recommendation:** Option A
**Rationale:** The ticket explicitly requires bare-repo primary AND single-worktree secondary; the research surfaced that this repo uses the linked pattern, so omitting it would make the skill appear to contradict its own host (ref: Q8).
**NEW PATTERN?** No.

### Decision 4: Bootstrap script authoring path and `allowed-tools`

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Author `bootstrap-bare-worktree.sh` via the `writing-bash-scripts` skill (ShellCheck-clean, `set -euo pipefail`); set `allowed-tools` minimal (`Read, Bash`) | Honors user mandate for bash skill; minimal tool surface | Requires invoking another skill during implementation |
| B | Hand-write the script; broad `allowed-tools` | Faster | Violates user memory (bash skill mandatory); larger tool surface than needed |

**Recommendation:** Option A
**Rationale:** User global memory mandates `writing-bash-scripts` for any `.sh` and ShellCheck-cleanliness; there is no repo-local lint to fall back on (ref: Q12). Minimal `allowed-tools` follows the repo's restrictive convention (ref: Q3).
**NEW PATTERN?** Yes — first `.sh` script and first `scripts/` directory under a skill in this repo; justified because the acceptance criteria explicitly require a bootstrap script and no existing skill provides one (ref: Q5).

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Bootstrap script not ShellCheck-clean / fails on edge inputs, violating user bash directive | med | med | Author via `writing-bash-scripts` skill; run ShellCheck; use `set -euo pipefail`; validate the script against a throwaway repo before commit |
| SKILL.md body exceeds the 500-line / 5000-token budget | low | med | Cap body at ~120-180 lines (qrspi-ticket scale); push gotcha tables, transcripts, and alias set into `references/` (ref: Q2, Q9) |
| Skill description triggers poorly (too broad/narrow), so agents don't invoke it when relevant | med | med | Use `skill-creator`'s description-triggering eval loop to tune the `description` WHEN-to-use phrasing (ref: Q13) |
| Skill written to a home-dir path instead of in-repo, breaching the project-scope boundary | low | high | Implementation writes only under `.claude/skills/using-git-worktrees/`; the qrspi-work scope block already forbids out-of-repo writes (ref: Q7) |
| Skill content contradicts host repo's linked-worktree convention, confusing readers | med | low | Present bare-repo as primary and linked-worktree as documented secondary; note both are valid (Decision 3, ref: Q8) |

## Open Questions

- OQ1: Should the bootstrap script default the project layout to the bare-repo tree (`.bare/` + `.git` pointer + per-branch worktrees), or also offer a flag for the linked pattern? Recommendation: bare-repo only for the script (primary pattern), document linked pattern in prose.
- OQ2: Should `.claude/CLAUDE.md`'s skill list be updated to mention `using-git-worktrees`? It is not a QRSPI phase, so it may not belong in that workflow list. Default: leave the QRSPI list unchanged unless the reviewer wants the skill advertised there.
- OQ3: Does the reviewer want a repo `evals/` case added for this skill? The harness is phase-keyed and has no reference-skill shape (ref: Q11); default is to rely on the skill-creator eval loop and skip a repo eval case.
