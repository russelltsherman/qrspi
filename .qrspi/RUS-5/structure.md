# Structure — writing-bash-scripts agent skill

**Design basis:** design.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31
**Status:** draft

## New Types

- None — this is a guidance-only skill with no new code types.

## Modified Types

- None.

## Contracts

- `SKILL.md frontmatter` — YAML block with `name: writing-bash-scripts`, `description` using "Use when..." trigger language, `command: /writing-bash-scripts`, `argument-hint: <script-path>`, `allowed-tools: [Read, Write, Bash, Edit]`
- `SKILL.md body` — agentskills.io-standard structured markdown with sections: trigger, conventions (13 topics), steps, and scope boundary
- `CLAUDE.md listing` — new bullet under "Available skills" in the QRSPI Workflow section, following existing format: `-/writing-bash-scripts <args>` — description text

## Slice 1: Create writing-bash-scripts skill

**Goal:** Ship the `writing-bash-scripts` skill as a loadable, triggerable skill covering all 13 convention topics, ShellCheck rule references, and bash 3.2 portability guidance.
**Files touched:**

- ✨ `.claude/skills/writing-bash-scripts/SKILL.md` — the complete skill definition (~150-200 lines) with frontmatter and structured body following agentskills.io pattern
- ⚠️ `.claude/CLAUDE.md` — add `writing-bash-scripts` entry to the "Available skills" list in the QRSPI Workflow section
**Verification:**
- [ ] SKILL.md has valid YAML frontmatter with all required fields (`name`, `description`, `command`, `argument-hint`, `allowed-tools`)
- [ ] SKILL.md body covers all 13 convention topics: strict mode, error handling, argument parsing, subcommand dispatch, logging, quoting, dependency checking, usage/help, temp files, code organization, testing/linting, portability, ShellCheck compliance
- [ ] `description` field uses "Use when..." language matching all trigger scenarios from AC3
- [ ] `.claude/CLAUDE.md` lists `writing-bash-scripts` in the Available skills section
- [ ] skill-creator validation passes (invoked as the final step of this slice)
**Context cost:** S
**Depends on:** none

## Unverified Assumptions

- A1: `argument-hint` should be `<script-path>` — the design lists OQ1 but does not resolve it. Using `<script-path>` as the most descriptive default.
- A2: `allowed-tools` includes `Bash` so the skill's agent can run `shellcheck` — the design lists OQ3 but does not resolve it. Adding `Bash` is necessary for the ShellCheck post-generation gate to work.
- A3: The skill should be ~150-200 lines as noted in the Delta — the design flags this as a risk but does not set a hard cap. Targeting the lower end to avoid context pressure.
- A4: No `references/` subdirectory — the design unanimously rejects the two-file and hybrid patterns in Decision 2. All guidance is inline in SKILL.md.
