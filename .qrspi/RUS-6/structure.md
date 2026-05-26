# Structure Outline -- Create a new agent skill called using graphite cli

**Design basis:** design.md @ 2026-05-26
**Generated:** 2026-05-26
**Status:** draft

## New Types

None. This ticket produces markdown skill definitions and JSON eval fixtures, not application code with typed interfaces.

## Modified Types

None.

## Contracts

### SKILL.md Frontmatter Contract

Every SKILL.md in this project uses exactly this YAML frontmatter schema. The new skill must conform:

```yaml
---
name: string           # matches directory name under .claude/skills/
description: string    # quoted; doubles as trigger-matching text for Claude Code dispatcher
command: string        # /<name>
argument-hint: string  # e.g. "<subcommand>" or empty
allowed-tools: string  # comma-separated list of tool names
---
```

No additional fields (`triggers`, `version`, etc.) are permitted.

### Reference File Loading Contract

Reference files are loaded by explicit `Read` instructions in the SKILL.md body. There is no auto-loading mechanism. Each reference file must be referenced by its path relative to the skill directory:

```
Read `.claude/skills/using-graphite-cli/references/command-reference.md`
Read `.claude/skills/using-graphite-cli/references/conflict-resolution.md`
```

### Eval Suite Contract (graphite-evals.json)

The eval file uses this assertion schema (distinct from `suite.json`):

```json
{
  "skill_name": "using-graphite-cli",
  "evals": [
    {
      "id": number,
      "prompt": string,
      "expected_output": string,
      "files": [],
      "assertions": [
        {"text": string, "type": "command_check" | "flag_check" | "content_check" | "workflow_check" | "safety_check"}
      ]
    }
  ]
}
```

### Staging Rule Contract

The skill must enforce explicit staging (never `-a` flag), consistent with `qrspi-work/SKILL.md` lines 444-457. The eval assertion in case 1 must be updated to match:

- OLD: `"Includes -a or -u flag to stage changes"`
- NEW: `"Requires explicit git add before gt create/modify (never -a flag)"`

## Slice 1: Skill definition, reference files, and eval alignment

**Goal:** Deliver the complete `using-graphite-cli` skill (SKILL.md + two reference files) and fix the contradictory eval assertions in `graphite-evals.json`, then validate via skill-creator.

**Rationale for single slice:** The SKILL.md loads both reference files via Read instructions -- it cannot be verified without them. The evals test the skill -- they cannot pass with a mismatched `skill_name` or contradictory `-a` flag assertion. The skill-creator eval loop is the verification step, and it requires all files to be in place. Splitting these into multiple slices would create artificial dependencies where each slice is unverifiable without the next.

**Files touched:**

- New `.claude/skills/using-graphite-cli/SKILL.md` -- Main skill definition with frontmatter, core workflow rules (create/submit/modify/sync loop, single-commit-per-branch, no raw git), and Read instructions pointing to both reference files. Target: 150-300 lines body (under 500-line limit).
- New `.claude/skills/using-graphite-cli/references/command-reference.md` -- Complete gt command reference: `gt create`, `gt modify`, `gt submit`, `gt sync`, `gt log`, `gt move`, `gt checkout`, `gt delete`, `gt bu`, `gt bd`, `gt stack top`, `gt restack`. Flag details, examples, directionality conventions (downstack = toward trunk, upstack = away from trunk). Target: 200-400 lines.
- New `.claude/skills/using-graphite-cli/references/conflict-resolution.md` -- Conflict resolution procedures using `gt continue` (never `git rebase --continue`), restack flows, recovery from common errors. Target: 50-100 lines.
- Modify `evals/graphite-evals.json` -- (1) Change `skill_name` from `"graphite"` to `"using-graphite-cli"`. (2) In eval case 1, replace the `-a or -u` flag assertion with an assertion requiring explicit `git add` staging (no `-a` flag), aligning with the skill's staging rule.

**Verification:**

- [ ] SKILL.md has exactly 5 frontmatter fields: `name`, `description`, `command`, `argument-hint`, `allowed-tools`
- [ ] `name` field is `using-graphite-cli`, `command` is `/using-graphite-cli`
- [ ] SKILL.md body (excluding frontmatter) is under 500 lines
- [ ] SKILL.md body contains Read instructions for both `references/command-reference.md` and `references/conflict-resolution.md`
- [ ] SKILL.md body contains the single-commit-per-branch rule as a hard directive
- [ ] SKILL.md body documents the Create -> Submit -> Modify -> Sync workflow loop
- [ ] SKILL.md body specifies `--no-edit --publish --no-interactive` as default `gt submit` flags
- [ ] SKILL.md body prohibits `git branch`, `git rebase`, `git commit --amend` on Graphite-tracked branches
- [ ] `references/command-reference.md` covers navigation commands: `gt bu`, `gt bd`, `gt stack top`, `gt log short`
- [ ] `references/command-reference.md` documents directionality: downstack = toward trunk, upstack = away from trunk
- [ ] `references/conflict-resolution.md` documents `gt continue` as the only permitted resolution command
- [ ] `evals/graphite-evals.json` has `skill_name` set to `"using-graphite-cli"`
- [ ] Eval case 1 no longer asserts `-a or -u` flag usage
- [ ] `evals/graphite-evals.json` is valid JSON
- [ ] Invoke skill-creator to validate and refine the SKILL.md through its eval loop

**Context cost:** M

**Depends on:** none

---

## Unverified Assumptions

1. **skill-creator availability and behavior.** The design states the skill must be "built using the Anthropic skill builder skill." The skill-creator is external to this project (provided by the Claude Code harness). Its exact validation logic, frontmatter schema enforcement, and eval loop behavior are not inspectable from within this codebase. If skill-creator is unavailable, has changed its interface, or enforces constraints not documented here, the verification step may fail in ways that cannot be predicted from this structure document. (ref: research Q1, Q3)

2. **`--no-interactive` flag universality.** The design specifies `--no-interactive` on all `gt` commands. Research Q11 confirms this is necessary since agents cannot respond to interactive prompts, but notes that not all `gt` subcommands may support this flag. No verification against the actual Graphite CLI version has been performed. If specific subcommands reject `--no-interactive`, the command reference will need per-command flag tables rather than a blanket rule. (ref: design Risk Register item 3)

3. **`--publish` flag on `gt submit`.** The design specifies `--no-edit --publish --no-interactive` as default submit flags. The existing `qrspi-work` skill uses `--no-edit --no-interactive` without `--publish`. The `--publish` flag behavior (whether it marks a draft PR as ready for review or creates a non-draft PR) has not been verified against the installed Graphite CLI version. (ref: design Desired End State, AC on submit flag defaults)

4. **Eval assertion types without grading implementation.** The `graphite-evals.json` uses assertion types (`command_check`, `flag_check`, `content_check`, `workflow_check`, `safety_check`) that have no corresponding grading implementation in `grade.py`. Updating the eval file aligns assertions with the skill, but the assertions remain unrunnable through the automated eval pipeline. The design explicitly scopes grading infrastructure changes as out-of-scope, but this means the "invoke skill-creator" verification step may not be able to run these specific evals programmatically. (ref: research Q12, Q13; design "No Changes Required" table)

5. **Open Question 1 resolution: staging convention.** The design flagged a contradiction between three sources (ticket says `--all`, `qrspi-work` forbids `-a`, evals assert `-a or -u`). This structure assumes the resolution is "explicit `git add`, never `-a`" (consistent with `qrspi-work`), but this has not received explicit human sign-off as the design's Open Question 1 requested. (ref: design Open Questions item 1)

6. **Open Question 3 resolution: eval updates in scope.** This structure includes the eval file update as part of the slice, following the design's recommendation. The design noted this is a scope question ("the ticket says 'create a skill,' not 'fix existing evals'"). If the eval update is ruled out of scope during review, the eval assertion will remain contradictory and the `skill_name` will remain mismatched. (ref: design Open Questions item 3)
