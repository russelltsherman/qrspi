# PR: Add using-git-worktrees skill with bootstrap script

**Ticket:** RUS-30
**Design:** design.md @ 2026-06-04T00:00:00Z
**Structure:** structure.md @ 2026-06-07T00:00:00Z

## Summary

Adds a new self-contained guidance skill at `.claude/skills/using-git-worktrees/`
that teaches agents to use Git worktrees correctly: a bare-repo-primary setup, the
full create→work→PR→merge→remove→prune lifecycle, parallel-agent isolation, the
submodule and shared-stash gotchas, and cleanup/maintenance for long-lived projects.
A thin `SKILL.md` body (85 lines, ~995 tokens) stays well under the 500-line / 5000-token
budget by offloading detail to `references/worktrees.md`, mirroring the in-repo
`qrspi-work` references-split pattern, and bundles `scripts/bootstrap-bare-repo.sh`
(bare clone + fetch refspec + first worktree). Reviewers should focus on two points:
(1) the novel bundled `scripts/` subdirectory — a layout no existing skill uses, mandated
by the agentskills.io AC; and (2) that the bootstrap script ships verified by `bash -n` +
manual e2e rather than `shellcheck`, which is not installed in this environment (see
Deviations).

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: agentskills.io directory structure + valid skill-schema frontmatter (`name` matches dir slug) | `.claude/skills/using-git-worktrees/SKILL.md` frontmatter | impl-log S2 T10/T13 — `grep '^name: using-git-worktrees$'` matches slug; YAML parses with 5 skill-schema keys, no agent-schema keys |
| AC2: Body under 500 lines / 5000 tokens | `SKILL.md` (thin procedural body) | impl-log S2 T10 — 85 lines / ~995 tokens, under budget |
| AC3: Detailed reference material in `references/` | `references/worktrees.md` | impl-log S2 T11 — `references/worktrees.md` reachable by relative path, no dangling refs |
| AC4: `scripts/` directory with bare-repo bootstrap script | `scripts/bootstrap-bare-repo.sh` | impl-log S2 T9 — e2e produces `.bare/`, `.git` pointer, fetch refspec, first worktree |
| AC5: Full lifecycle (create, work, PR, merge, remove, prune) | `references/worktrees.md` §2 | impl-log S2 T12 — lifecycle behavior present §2 |
| AC6: Bare-repo pattern as primary; linked-from-`main` reconciled as secondary | `SKILL.md` body + `references/worktrees.md` §1 | impl-log S2 T12 — bare-vs-linked reconciliation present §1 + SKILL body |
| AC7: Parallel agent isolation (per-worktree `.env`, `.env.local` ports, independent deps, 3–5 ceiling) | `references/worktrees.md` §3 | impl-log S2 T12 — behaviors (3)(4)(5)(6) present §3 |
| AC8: Warns about submodule + shared-stash gotchas | `references/worktrees.md` §7 | impl-log S2 T12 — gotchas (9)(10) present §7 |
| AC9: Naming conventions + directory layout | `references/worktrees.md` §1 + `SKILL.md` | impl-log S2 T12 — bare-repo layout / naming present §1 |
| AC10: Cleanup/maintenance for long-lived projects | `references/worktrees.md` §5/§6 | impl-log S2 T12 — cleanup+maintenance §5, CI+review §6 |
| AC11: Bootstrap arg guard surfaces usage on missing arg | `scripts/bootstrap-bare-repo.sh` (`${1:?Usage…}`) | impl-log S2 T8 — no-args invocation exits 1 with `Usage:` to stderr |
| AC12: `bash -n` syntax validity (shellcheck substitute) | `scripts/bootstrap-bare-repo.sh` | impl-log S1/S2 T7 — `bash -n` syntax OK |

## Changes by Slice

### Slice 1: Authored `using-git-worktrees` skill (body + references + bootstrap script)

| File | Change | Lines |
|------|--------|-------|
| `.claude/skills/using-git-worktrees/SKILL.md` | ✨ new | +85 |
| `.claude/skills/using-git-worktrees/references/worktrees.md` | ✨ new | +277 |
| `.claude/skills/using-git-worktrees/scripts/bootstrap-bare-repo.sh` | ✨ new | +49 |

### Workflow artifacts (QRSPI stack, not feature code)

Committed across the design/plan/slice PRs in this stack; carried in the diff but not part of the shipped skill.

| File | Change | Lines |
|------|--------|-------|
| `.qrspi/RUS-30/design.md` | ✨ new | +107 |
| `.qrspi/RUS-30/impl-log.md` | ✨ new | +53 |
| `.qrspi/RUS-30/plan.md` | ✨ new | +66 |
| `.qrspi/RUS-30/questions.md` | ✨ new | +53 |
| `.qrspi/RUS-30/research.md` | ✨ new | +314 |
| `.qrspi/RUS-30/structure.md` | ✨ new | +58 |
| `.qrspi/RUS-30/worktree.md` | ✨ new | +42 |

## Testing Summary

- [x] Slice 1: bash syntax — `bash -n .claude/skills/using-git-worktrees/scripts/bootstrap-bare-repo.sh` — syntax OK (T7)
- [x] Slice 1: arg guard — no-args invocation → exit 1, `Usage: bootstrap-bare-repo.sh <repo-url> [target-dir]` to stderr (T8)
- [x] Slice 1: e2e — bootstrap against throwaway `file:///tmp/wt-src` → `/tmp/wt-e2e`: `.bare/` present, `.git` = `gitdir: ./.bare`, `remote.origin.fetch` = `+refs/heads/*:refs/remotes/origin/*`, first worktree created (`git worktree list` confirms) (T9)
- [x] Slice 1: frontmatter/slug — `grep '^name: using-git-worktrees$'` matches dir slug; no agent-schema keys; 85 lines / ~995 tokens under budget (T10, T13)
- [x] Slice 1: no dangling references — `references/worktrees.md` + `scripts/bootstrap-bare-repo.sh` resolve by relative path (T11)
- [x] Slice 1: AC coverage — all ten acceptance behaviors present across SKILL.md + references/worktrees.md (T12)
- [ ] Not run: `shellcheck` — not installed in this environment, no passwordless sudo to install (see Deviations); substituted `bash -n` + writing-bash-scripts conventions

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| Verification: `shellcheck` passes on `bootstrap-bare-repo.sh` (structure.md §Slice 1 Verification; plan step 7) | `shellcheck … exit 0` | Not run — substituted `bash -n` + authoring to writing-bash-scripts shellcheck conventions (strict mode, double-quoted expansions, `command -v` guards, safe `&&`/`||` lists, separated command-substitution assignment) | `shellcheck` is not installed in this environment and no passwordless sudo is available; per HARD STOP discipline the agent did not escalate. To validate: install shellcheck and run `shellcheck .claude/skills/using-git-worktrees/scripts/bootstrap-bare-repo.sh`. |
| `references/` topic split (OQ4 — combined vs. one-per-concern) | Open question | Single combined `references/worktrees.md` | Adopted the working-baseline contract; keeps one reachable reference file, satisfies the body→references split pattern |
| Bootstrap CLI signature (structure Unverified Assumption) | `<repo-url> [target-dir]` (inferred) | `bootstrap-bare-repo.sh <repo-url> [target-dir]`; `target_dir` defaults to `basename "${repo_url%.git}"` | Confirmed the inferred signature; matches the `${1:?Usage…}` guard |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| Reader assumes the skill describes this repo's worktree automation (repo uses linked-from-`main`, not bare-repo) | mitigated — bare-repo scoped as general best-practice; linked-from-`main` reconciled in §1 + SKILL body (T12) | Edit `references/worktrees.md` §1 reconciliation note |
| `SKILL.md` body breaches 500-line / 5000-token budget | mitigated — body is 85 lines / ~995 tokens, well under budget (T10) | Move more body content into `references/worktrees.md` |
| Bundled `scripts/` subdirectory is a novel layout, risking loader/convention surprises | partially mitigated — frontmatter + references validated and e2e ran (T9–T13); full skill-loader load is manual and not exercised in CI | Remove `scripts/` and link an external script, or relocate to top-level `scripts/` |
| `skill-creator` eval loop / skill-builder out-of-repo and unverifiable | accepted — authored with manual structure validation against existing SKILL.md frontmatter (OQ1) | n/a (content-only) |
| Bootstrap script ships without an automated test (TDD directive tension) | accepted — thin shell, no in-repo bash test harness; verified via `bash -n` + manual e2e (OQ2) | Add a bats harness or extract pure logic to a `_test.py` sibling |
| Frontmatter schema conflation (skill vs. agent schema) | mitigated — frontmatter uses the 5 skill-schema keys, no agent-schema keys (T10, T13) | Correct `SKILL.md` frontmatter to skill schema |

## Open Items

- `shellcheck` was never run (not installed, no sudo). If a reviewer requires it, install shellcheck and run it on `bootstrap-bare-repo.sh` — this is the one structure/plan verification step left unsatisfied.
- Skill-loader live load (the novel bundled `scripts/` layout) is validated only by structural checks + e2e, not by an actual loader run; confirm the skill loads cleanly in a real session.
- OQ1 (author via global `skill-creator` eval loop) and OQ2 (bash test harness vs. manual e2e) remain policy-level open questions vs. the user's skill-creator and TDD directives; resolved here by manual validation, but a follow-up could introduce a bats harness for the bootstrap script.
- OQ3 (whether to recommend this repo adopt bare-repo) resolved as "note and stay scoped" per Decision 2 Option A; no active migration recommendation shipped.
