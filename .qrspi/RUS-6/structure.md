# Structure — using graphite cli skill

**Design basis:** design.md @ 2026-05-27
**Generated:** 2026-05-27
**Status:** draft

## New Types

None. This deliverable is a single documentation file.

## Modified Types

None. No existing files are modified.

## Contracts

- `SKILL.md` frontmatter — must include: `name`, `description`, `command`, `argument-hint`, `allowed-tools` matching the project skill convention
- `SKILL.md` sections — must contain all 11 sections from the design's content structure: Graphite CLI Primer, Initialization, Core Workflow, Branch Navigation, Single Commit Per Branch, Restacking, Submitting PRs, Downstack/Upstack Operations, Merging Stacks, Integration with GitHub, Scope Guidance

## Slice 1: Create using-graphite-cli SKILL.md

**Goal:** Produce the complete `using-graphite-cli` skill file that covers all Graphite CLI operations needed by QRSPI agents, from initialization through stack merging.

**Files touched:**

- ✨ `.claude/skills/using-graphite-cli/SKILL.md` — new skill file with YAML frontmatter and 11 content sections

**Verification:**

- [ ] File exists at `.claude/skills/using-graphite-cli/SKILL.md`
- [ ] YAML frontmatter contains all 5 required keys (name, description, command, argument-hint, allowed-tools)
- [ ] Section "Graphite CLI Primer" covers stack, trunk, downstack, upstack concepts
- [ ] Section "Initialization" documents `gt init` and `gt auth`
- [ ] Section "Core Workflow" documents the create-modify-submit loop with `--no-interactive`
- [ ] Section "Branch Navigation" documents checkout, up, down, bottom, top, trunk
- [ ] Section "Single Commit Per Branch" documents the planning convention (modify -c, then amends)
- [ ] Section "Restacking" covers automatic restack via modify vs. explicit gt sync
- [ ] Section "Submitting PRs" distinguishes narrow submit from --stack submit
- [ ] Section "Downstack/Upstack Operations" covers move --onto and delete --force
- [ ] Section "Merging Stacks" documents gt merge --confirm and cleanup
- [ ] Section "Integration with GitHub" defines gt vs gh division of labor
- [ ] Section "Scope Guidance" provides tool selection guidance

**Context cost:** S (single file, no code changes)

**Depends on:** none

**AC coverage:** All 11 acceptance criteria from the design are addressed in this slice. Each section of the SKILL.md maps directly to one or more ACs (initialization, core workflow, branch navigation, single commit, restacking, submitting PRs, downstack/upstack operations, merging stacks, GitHub integration, scope guidance).

## Unverified Assumptions

1. **Skill auto-discovery:** The system prompt already lists `using-graphite-cli` as an available skill. If the skill system requires the skill to be registered in CLAUDE.md, a separate update to that file would be needed — but the design says "no files modified," so either auto-discovery works or CLAUDE.md update is deferred.
2. **gt CLI command surface is stable:** The design was produced by `gt --help` and `gt <cmd> --help` exploration. The skill content assumes the current command surface won't change significantly between when the skill is written and when it's used.
3. **Single slice is appropriate:** All 11 sections are directly related (they form one skill), so they belong in a single slice per rule 8. No file can be meaningfully tested/verified without the others — the entire skill is one unit of work.
