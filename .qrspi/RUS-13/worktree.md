# Work Tree — Create a new agent skill using glab cli

**Plan basis:** plan.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total sessions:** 3
**Critical path:** T1 → T3 → T4 → T5 → T6 → T7 → T8 → T9 → T10 → T15 → T16 (11 tasks)

> Note: This ticket produces Markdown skill content, not executable code. All
> SKILL.md body steps (T3–T10) edit the same file and are therefore strictly
> sequential. The four reference files (T11–T14) are additive and mutually
> independent, but each is linked from the body, so they follow the body in a
> dependency sense. Authoring runs through the global `skill-creator` skill
> (design Decision 4). Single slice → session splits are by authoring stage, not
> by slice, chosen to keep each context budget well under 40%.

## Session 1 — Scaffold + SKILL.md body

**Load:** structure.md §Types, structure.md §Contracts, plan.md §Slice 1 (Setup + Core Logic — SKILL.md body), design.md Decision 4
**Estimated context:** ~25% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Invoke `skill-creator` to scaffold `.claude/skills/glab-cli/` + starter SKILL.md (stop+report if it can't run) | — | §1 | M | pending |
| T2 | Create `.claude/skills/glab-cli/references/` directory | T1 | §2 | S | pending |
| T3 | Write five-field `SkillFrontmatter` (name/command/description/argument-hint/allowed-tools; dir==name==command-minus-slash) | T1 | §3 | S | pending |
| T4 | Add Overview section (scope: glab CLI for agents, gitlab.com + self-hosted, non-interactive) | T3 | §4 | S | pending |
| T5 | Add condensed Authentication summary + link to references/authentication.md | T4 | §5 | S | pending |
| T6 | Add condensed eight-subcommand-group section + link to references/commands.md | T5 | §6 | S | pending |
| T7 | Add Workflow Patterns (merge-after-green, stacked MRs, fork flow) + link to references/ci-scripting.md | T6 | §7 | S | pending |
| T8 | Add RecognizedState section (named judgment-call branches, distinct from infra failures) | T7 | §8 | S | pending |
| T9 | Add agent/scripted-use rules (non-interactive + JSON-parsed CLI) + link to references/error-handling.md | T8 | §9 | S | pending |
| T10 | Append verbatim HardStopBlock for auth/config/tooling failures | T9 | §10 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** SKILL.md body complete. The four reference files are a distinct authoring concern (full command/flag detail) that needs only the body's links/contracts as context, not the full body-drafting working set. Fresh context keeps the references session lean.

## Session 2 — Reference files

**Load:** structure.md §Contracts, plan.md §Slice 1 (Core Logic — reference files), impl-log.md §Session 1 (SKILL.md links + section names, notes only)
**Estimated context:** ~20% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T11 | Create references/commands.md — all eight groups (auth, mr, issue, ci/pipeline, release, changelog, repo, api) | T2, T6 | §11 | L | pending |
| T12 | Create references/authentication.md (login OAuth/PAT, GITLAB_TOKEN, --hostname self-hosted, multi-host; flag OQ4) | T2, T5 | §12 | M | pending |
| T13 | Create references/ci-scripting.md (merge-after-green, `glab ci status --wait`, jq parsing, single-envelope) | T2, T7 | §13 | M | pending |
| T14 | Create references/error-handling.md (exit codes, RecognizedState vs HARD-STOP, verbatim propagation) | T2, T9 | §14 | M | pending |

--- SESSION BOUNDARY ---
**Reason:** All authoring complete. Tests + verification are validation-only — they read the finished files and run checks, needing no drafting context. Fresh context isolates the gate from authoring state.

## Session 3 — Tests + Verify Slice 1

**Load:** plan.md §Slice 1 (Tests + Verify Slice 1), design.md Decision 4, impl-log.md §Session 1–2 (files created, notes only)
**Estimated context:** ~15% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T15 | Run the skill-creator eval loop against `glab-cli` (well-formed; no description trigger collision) | T10, T11, T12, T13, T14 | §15 | M | pending |
| T16 | **Checkpoint:** frontmatter assertion — name/command/dir all `glab-cli`, description quoted, argument-hint + allowed-tools present | T15 | §16 | S | pending |
| T17 | **Checkpoint:** `wc -l` body within ~500-line soft budget; all four reference files exist; body links each | T16 | §17 | S | pending |
| T18 | **Verify Slice 1:** commands.md enumerates all eight groups; verbatim HARD STOP + distinct RecognizedState present; human spot-check of glab accuracy | T17 | §18 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Final session. Single slice → on T18 pass the feature is complete and ready for PR.
