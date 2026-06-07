# Structure Outline — Create a new agent skill: using git worktrees

**Design basis:** design.md @ 2026-06-04T00:00:00Z
**Generated:** 2026-06-07T00:00:00Z
**Status:** draft

## New Types

None. This is a content/guidance skill (Markdown + one bash script), not a typed code change. No new data structures, classes, or interfaces are introduced.

## Modified Types

None. The design's Delta states "No modifications to existing skills, agents, scripts, or `.claude/CLAUDE.md`" — the new skill is a leaf with no in-repo dependents (ref: design.md §Delta).

## Contracts

The only cross-file interface is the bundled bootstrap script's CLI signature and the relative-path links the body uses to reach its support files.

- `bootstrap-bare-repo.sh <repo-url> [target-dir]` — bare clone + `.git` pointer + fetch-refspec config + first worktree. Shebang + `set -euo pipefail`; required first arg guarded via `${1:?Usage…}`; errors surfaced to stderr with an `error:` prefix and `exit 1` (ref: design.md §Delta, Decision 4, Q8). Exact arg names/optionality are an unverified assumption — see below.
- `SKILL.md` body → `references/<topic>.md` — body cites each reference file by **relative path at the point of use**, mirroring the only in-repo precedent (`qrspi-work` → `references/review-cascade.md`) (ref: design.md Decision 3, Q7).
- `SKILL.md` body → `scripts/bootstrap-bare-repo.sh` — body points to the bundled bootstrap script by relative path (ref: design.md §Delta).
- `SKILL.md` frontmatter — repo **skill schema** (`name`, `description`, `command`, `argument-hint`, `allowed-tools`), copied from an existing SKILL.md (e.g. `qrspi-research`), NOT the agent schema; `name: using-git-worktrees` must exactly match the directory slug; `allowed-tools` reflects a guidance skill (no `Agent` tool) (ref: design.md §Delta, Decision 1, Q4, Q5, Risk Register).

## Slice 1: Authored `using-git-worktrees` skill (body + references + bootstrap script)

**Goal:** A self-contained, loadable skill at `.claude/skills/using-git-worktrees/` that guides agents through correct Git worktree use — bare-repo-primary setup, full lifecycle, parallel-agent isolation, gotchas, and cleanup — with a working bundled bootstrap script. End-to-end verification: the skill loads under the skill loader and its bootstrap script runs against a throwaway repo.

**Rationale for single slice:** All files are mutually dependent and share one testability boundary. `SKILL.md` references the `references/*.md` files and `scripts/bootstrap-bare-repo.sh` by relative path; none of them can be meaningfully verified in isolation — the skill cannot be loaded or validated until the body, its referenced files, and valid frontmatter all exist together. Per the structure rules, directly-related support files that the main file depends on belong in the same slice even when the file count is moderate. There is no intermediate state that provides real verification signal.

**Files touched:**

- ✨ `.claude/skills/using-git-worktrees/SKILL.md` — skill-schema frontmatter (`name: using-git-worktrees`, single-line `description`, guidance `allowed-tools`) + thin procedural body leading with the bare-repo + parallel-agent use case; points to `references/` for detail and to `scripts/bootstrap-bare-repo.sh` for bootstrap; kept under the 500-line / 5000-token budget (ref: design.md §Delta, Decision 3, Decision 1).
- ✨ `.claude/skills/using-git-worktrees/references/<topic>.md` — long-form reference material covering: bare-repo layout, full create→work→PR→merge→remove→prune lifecycle, parallel-agent isolation (per-worktree `.env`, `.env.local` port overrides, independent dep install, 3–5 worktree ceiling), shared-state/config, cleanup/maintenance for long-lived projects, CI/review integration, and the submodule + shared-stash gotchas. Topic split (one combined vs. one-per-concern) is an open question — see Unverified Assumptions (ref: design.md §Delta, OQ4, Q7).
- ✨ `.claude/skills/using-git-worktrees/scripts/bootstrap-bare-repo.sh` — bare clone + `.git` pointer + fetch-refspec config + first worktree; shebang + `set -euo pipefail`, `error:`-to-stderr, `${1:?Usage…}` arg guard (ref: design.md §Delta, Decision 4, Q8).

**Verification:**
- [ ] `name` in `SKILL.md` frontmatter exactly equals the directory slug `using-git-worktrees`, and the frontmatter uses the skill schema (fields `name`/`description`/`command`/`argument-hint`/`allowed-tools`), not the agent schema (ref: Q4, Q5).
- [ ] `SKILL.md` body is under 500 lines and ~5000 tokens; every `references/*.md` file and the bootstrap script are reachable by a relative path actually written in the body (no dangling references) (ref: Q7, Decision 3).
- [ ] All ten acceptance-criteria behaviors from §Desired End State are present (bare-repo primary, lifecycle, parallel isolation, submodule + shared-stash gotchas, naming/layout, cleanup, references split, bundled scripts/).
- [ ] `bootstrap-bare-repo.sh` runs clean against a throwaway remote (manual e2e): produces a bare repo, configured fetch refspec, and a first worktree; missing-arg invocation prints the `${1:?Usage…}` guard to stderr and exits non-zero (ref: Q8, Q10).
- [ ] `shellcheck` passes on `bootstrap-bare-repo.sh` (no bash test harness exists in-repo; verification is shellcheck + manual e2e per Q10/Q11/Decision 4).
- [ ] Skill loads without loader/convention errors despite the novel bundled `scripts/` layout (manual e2e; ref: Risk Register, Q1).
- [ ] Authored via the global `skill-creator` skill + eval loop where available; otherwise frontmatter validated against an existing `SKILL.md` (ref: OQ1, Q3). Validation is the final step of this slice, not a separate slice.

**Context cost:** M
**Depends on:** none

---

## Unverified Assumptions

- **`bootstrap-bare-repo.sh` CLI signature.** The design specifies behavior (bare clone + fetch refspec + first worktree) and error conventions but not the exact argument list/optionality. The contract above (`<repo-url> [target-dir]`) is inferred from `${1:?Usage…}`; the second arg and any branch/worktree-name args are unconfirmed (ref: design.md §Delta, Q8). Needs confirmation before planning.
- **`references/` topic split.** OQ4 is explicitly open: one combined reference file vs. one file per concern (bare-repo, lifecycle, parallel agents, gotchas, CI). The slice lists the content but not the file count/boundaries (ref: design.md OQ4, §Delta).
- **Authoring/verification bar (OQ1).** The user's directive mandates authoring skills via the global `skill-creator` skill and its eval loop, but that tooling and the in-repo `evals/` harness are out-of-scope / non-functional placeholders (ref: Q3, Q10). Whether manual structure validation is an acceptable substitute is unresolved and cannot be mapped to a concrete in-repo step.
- **Bootstrap-script testing vs. TDD directive (OQ2).** The user's TDD directive expects tests for any coded task, but there is no in-repo bash test harness (e.g. bats) and the eval harness is a placeholder. Whether manual e2e + shellcheck is acceptable, or a new bash test dependency must be introduced, is unresolved (ref: OQ2, Q10, Q11, Decision 4). This affects the slice's verification step.
- **Bare-repo vs. linked-from-`main` reconciliation depth (OQ3).** Whether the skill should actively recommend this repo adopt bare-repo or merely note the difference is open; the design picks "note and stay scoped" (Decision 2 Option A) but flags OQ3 as unresolved. The body's exact reconciliation wording cannot be pinned to concrete content until decided (ref: OQ3, Decision 2).
- **`allowed-tools` exact value.** The design states it should reflect a guidance (non-agent-spawner) skill with no `Agent` tool, but the concrete tool list is not enumerated (ref: design.md §Delta).
- **Skill loader tolerance for a bundled `scripts/` subdirectory.** No existing skill bundles `scripts/`; the design flags possible loader/convention surprises (low likelihood) but this cannot be confirmed without the manual e2e load (ref: Q1, Risk Register).
