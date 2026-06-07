# Design — Create a new agent skill: using git worktrees

**Ticket:** RUS-30
**Research basis:** research.md @ 2026-06-04T00:00:00Z
**Generated:** 2026-06-04T00:00:00Z
**Status:** draft

## Current State

Skills live under `.claude/skills/<skill-name>/`, each a directory whose only required file is `SKILL.md`; new skills are added as a new sibling directory there (ref: Q1). Of 10 existing skills, 9 are SKILL.md-only and exactly one (`qrspi-work`) carries a `references/` subdirectory; no existing skill ships a bundled `scripts/` or `assets/` subdirectory — repo scripts live at the top-level `scripts/` dir instead (ref: Q1). Every `SKILL.md` opens with a YAML frontmatter block delimited by `---` lines using the fields `name`, `description`, `command`, `argument-hint`, `allowed-tools`; `name` is a lowercase-hyphen slug, and `description` is 1–3 sentences encoding a "Use when/after…" trigger, quoted when it contains punctuation (ref: Q4). All skill `name` fields are lowercase-hyphen slugs that exactly match their directory name (ref: Q5). Note there are two distinct frontmatter schemas under `.claude/`: skill files use the schema above, while agent files use `name/description/claude:{tools}` — they must not be conflated (ref: Q4).

Most phase-wrapper skills are 25–35 lines because they are thin wrappers that delegate substance to a paired `.claude/agents/<name>.md` prompt; the only skill that offloads detail does so into `references/review-cascade.md` and points to it by relative path at the point of use (ref: Q7). A "using git worktrees" skill is content (guidance), not an agent-spawner, so it would be self-contained in `SKILL.md` plus optional `references/`, unlike the phase wrappers (ref: Q7, Discovered Patterns).

This repo provisions worktrees with `git worktree add` off a normal (non-bare) checkout on `main`, one isolated worktree per ticket at `.worktrees/<ticket-id>/` (gitignored), each a single Graphite-tracked branch — this is the linked-from-`main` model, NOT a bare-repo model (ref: Q6). There is no bare-repo bootstrap script in the repo today; the question targets a script the ticket asks to be created (ref: Q2). No script, doc, or skill references `git submodule` or `git stash`, so the skill introduces that guidance fresh (ref: Q9). Git mutations in this project are funneled through Graphite (`gt`) per the global `using-graphite-cli` skill (ref: Q9).

The closest precedent for a new script is the self-locating Python helpers (`qrspi_persist.py`, `qrspi_resolve.py`): they take short token-free args, self-locate the repo root from `__file__`, and emit a single JSON envelope on stdout, exiting non-zero on failure (ref: Q2). Bash scripts in the repo use a shebang plus `set -euo pipefail` on lines 1–2, surface errors to stderr with an `error:` prefix and `exit 1`, and guard required args with `${N:?Usage…}` (ref: Q8). Tested helpers have stdlib-only `unittest` siblings named `<module>_test.py`, run with `python3`; there is no bash test harness (e.g. bats) in the repo (ref: Q11). The `evals/` + `scripts/run_eval.py` harness is a non-functional placeholder; in-repo verification is unit tests plus manual end-to-end runs (ref: Q10). Error-surfacing discipline: infra/tooling failures hard-stop with the verbatim error and no workaround; reversible/projection steps warn-and-continue (ref: Q12). The Anthropic `skill-builder`/`skill-creator` skill is a global skill outside repo scope and cannot be read from this worktree (ref: Q3).

## Desired End State

A new self-contained skill exists at `.claude/skills/using-git-worktrees/` that guides agents to use Git worktrees correctly. Each acceptance criterion maps to concrete behavior:

- **agentskills.io directory structure + valid frontmatter** → `SKILL.md` with the repo's skill schema frontmatter (`name: using-git-worktrees` matching the directory slug, single-line trigger `description`) (ref: Q4, Q5).
- **Built using the Anthropic skill builder skill** → the skill is authored via the global `skill-creator` skill and its eval loop (out-of-repo tooling; see Open Questions) (ref: Q3).
- **Body under 500 lines / 5000 tokens** → procedural "how to use worktrees correctly" steps stay in `SKILL.md`; bulk detail is offloaded to `references/` following the `qrspi-work` splitting pattern (ref: Q7).
- **Detailed reference material in `references/`** → a `references/` subdirectory holds the long-form bare-repo layout, lifecycle, parallel-agent isolation, and gotchas content, referenced by relative path (ref: Q1, Q7).
- **`scripts/` directory with a bare-repo bootstrap script** → the skill bundles its own `scripts/bootstrap-bare-repo.sh` (clone `--bare` + configure fetch refspec + first worktree). This is bundled *inside the skill directory*, a layout no existing skill uses (ref: Q1).
- **Full lifecycle: create, work, PR, merge, remove, prune** → documented as a single create→work→PR→merge→remove→prune flow.
- **Bare-repo pattern as primary recommended setup** → leads the skill; the linked-from-`main` model (this repo's own convention) is reconciled as a secondary pattern (ref: Q6).
- **Parallel agent isolation (env, ports, deps)** → covers per-worktree `.env` copies, `.env.local` port overrides, independent dependency install, 3–5 worktree ceiling.
- **Warns about submodule and shared-stash gotchas** → dedicated gotchas section; fresh guidance, no in-repo conflict (ref: Q9).
- **Naming conventions + directory layout** → lowercase-hyphen `<type>-<short-desc>` convention and the bare-repo tree, consistent with the repo's slug convention (ref: Q5).
- **Cleanup/maintenance guidance for long-lived projects** → `git worktree list` audits, post-merge prune lifecycle, lock for removable media, periodic review.

## Delta

**New directory:** `.claude/skills/using-git-worktrees/`

**New files:**
- `.claude/skills/using-git-worktrees/SKILL.md` — frontmatter (skill schema) + a short procedural body that leads with the bare-repo + parallel-agent use case, points to `references/` for detail and to `scripts/bootstrap-bare-repo.sh` for bootstrap.
- `.claude/skills/using-git-worktrees/references/<topic>.md` — one or more reference files for: bare-repo layout, full lifecycle, parallel-agent isolation, shared-state/config, cleanup, CI/review integration, and the submodule + shared-stash gotchas. Split per the `qrspi-work` body→references pattern (ref: Q7).
- `.claude/skills/using-git-worktrees/scripts/bootstrap-bare-repo.sh` — bare clone + `.git` pointer + fetch-refspec config + first worktree; shebang + `set -euo pipefail`, `error:`-to-stderr, `${1:?Usage…}` arg guard (ref: Q8).

**No modifications** to existing skills, agents, scripts, or `.claude/CLAUDE.md` are required — the new skill is a leaf with no in-repo dependents (ref: Q1). The `allowed-tools` frontmatter should reflect that this is a guidance skill, not an agent-spawner (no `Agent` tool needed).

## Pattern Decisions

### Decision 1: Where the bootstrap script lives

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Bundle `scripts/` inside the skill dir (`.claude/skills/using-git-worktrees/scripts/`) | Self-contained skill; portable; satisfies AC literally ("Includes a `scripts/` directory") | No existing skill in this repo bundles `scripts/` — new layout (ref: Q1) |
| B | Place the script at the repo-level `scripts/` dir like `qrspi_*` helpers | Matches where every other repo script lives (ref: Q1) | Violates the AC wording; couples a portable how-to skill to this repo's tree |

**Recommendation:** Option A
**Rationale:** The acceptance criteria explicitly require a `scripts/` directory *within the skill* following the agentskills.io structure, and the skill is meant to be portable guidance rather than repo-coupled automation. Existing repo scripts live at the top level only because the phase skills are agent-spawning wrappers, not self-contained skills (ref: Q1, Q7).
**NEW PATTERN?** Yes — no existing skill bundles a `scripts/` (or `assets/`) subdirectory (ref: Q1). Justified because the ticket's AC mandates the agentskills.io layout, which existing thin wrappers never exercised.

### Decision 2: Reconciling the bare-repo recommendation with this repo's linked-from-`main` convention

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Lead with bare-repo as primary; add a short note that this repo's own automation uses linked-from-`main`, framing bare-repo advice as general/external | Satisfies "bare-repo primary" AC; honest about the mismatch (ref: Q6, Inconsistencies) | Two patterns to document; reader must understand both |
| B | Rewrite the skill around the repo's actual linked-from-`main` model | Matches in-repo reality (ref: Q6) | Directly violates the "bare-repo pattern as primary recommended setup" AC |

**Recommendation:** Option A
**Rationale:** The ticket explicitly scopes bare-repo as the primary recommended approach and linked single-worktree usage as secondary; the skill is portable guidance, not a description of this repo's pipeline. The mismatch with `scripts/qrspi_resolve.py`'s `git worktree add … main` provisioning is real and must be acknowledged so readers do not assume the skill describes this repo's automation (ref: Q6, Inconsistencies).
**NEW PATTERN?** No — documenting an external best-practice that differs from internal automation is a content choice, not a new code pattern.

### Decision 3: How to keep `SKILL.md` under the 500-line / 5000-token budget

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Thin procedural `SKILL.md` body; offload bare-repo/lifecycle/gotchas detail into `references/*.md`, cited by relative path | Mirrors the only in-repo precedent (`qrspi-work` → `references/review-cascade.md`); keeps body well under budget (ref: Q7) | Detail not auto-injected — body must explicitly point to each reference file |
| B | Inline everything in `SKILL.md` | One file, simplest navigation | Risks breaching the 500-line/5000-token AC given the breadth of ticket content (ref: Q7) |

**Recommendation:** Option A
**Rationale:** The repo's established splitting pattern keeps procedural steps in the body and pushes large conditional/explanatory detail into `references/<topic>.md`, loaded on demand and referenced at the point of use; the ticket's content volume (lifecycle, parallel agents, shared state, multiple gotcha classes, CI integration) makes a single body likely to breach the budget (ref: Q7).
**NEW PATTERN?** No — this is the existing `qrspi-work` references pattern (ref: Q7).

### Decision 4: Whether the bootstrap script gets an automated test

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Keep the bash script thin and verify by manual end-to-end run | Matches repo precedent: no bash test harness exists; eval harness is a placeholder (ref: Q10, Q11) | No regression net for the script |
| B | Add a stdlib-only `_test.py` covering any extractable pure logic | Mirrors the `<module>_test.py` convention (ref: Q11) | The script is shell, not Python; little pure logic to extract; no bats harness to mirror (ref: Q11) |

**Recommendation:** Option A (with B applied only if non-trivial pure logic emerges)
**Rationale:** The repo precedent is that *pure logic* gets stdlib-only unit tests, but a bare-repo bootstrap is thin shell orchestration with no Python sibling pattern to mirror and no bash test framework present; per Q10 the verification path is manual e2e (ref: Q10, Q11). This sits in tension with the user's TDD directive — see Open Questions.
**NEW PATTERN?** No (Option A); Option B would reuse the existing `_test.py` convention.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Reader assumes the skill describes this repo's worktree automation, but the repo uses linked-from-`main`, not bare-repo (ref: Q6, Inconsistencies) | high | med | Explicitly scope bare-repo advice as general best-practice; add a short note pointing to the repo's actual `.worktrees/<id>/` linked model |
| `SKILL.md` body breaches the 500-line / 5000-token AC due to breadth of required content (ref: Q7) | med | med | Apply the `qrspi-work` references-split pattern; keep only procedural steps in the body |
| Bundled `scripts/` subdirectory is a layout no existing skill uses, risking loader/convention surprises (ref: Q1) | low | med | Validate the skill loads after authoring via manual e2e; keep the script invocable by relative path from the skill dir |
| `skill-creator` eval loop and skill-builder are out-of-repo and unverifiable from this worktree (ref: Q3) | med | low | Author with the global skill where available; fall back to manual structure validation against existing skill frontmatter (Q4) |
| Bootstrap script ships without an automated test, conflicting with the TDD directive (ref: Q10, Q11) | med | med | Keep the script thin; verify via manual e2e; extract and unit-test any pure logic if it grows |
| Frontmatter schema conflation (skill vs. agent schema) produces an invalid skill (ref: Q4, Inconsistencies) | low | high | Copy the skill-schema frontmatter from an existing `SKILL.md` (e.g. `qrspi-research`), never an agent file |

## Open Questions

- OQ1: The user's global directive mandates authoring skills via the `skill-creator` skill and its eval loop, but that tooling and the in-repo `evals/` harness are out-of-scope / non-functional placeholders (ref: Q3, Q10). Should we author via the global `skill-creator` skill and accept manual structure validation, or is a different verification bar acceptable for this content-only skill?
- OQ2: The TDD directive expects tests for any coded task, but the bare-repo bootstrap is thin shell with no in-repo bash test harness (ref: Q11). Is manual end-to-end verification (per Q10) acceptable here, or should we introduce a bash test harness (e.g. bats) — a new repo dependency?
- OQ3: Should the skill actively reconcile the bare-repo vs. linked-from-`main` mismatch by recommending this repo adopt bare-repo, or merely note the difference and stay scoped to external best-practice (ref: Q6)?
- OQ4: How many `references/` files and what topic split is preferred (one combined reference vs. one per concern: bare-repo, lifecycle, parallel agents, gotchas, CI)?
