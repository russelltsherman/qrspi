# Structure — writing-bash-scripts agent skill

**Design basis:** design.md @ 2026-05-31
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## New Types

- `SkillFrontmatter { name: string, description: string, command: string, argument-hint: string, allowed-tools: string[] }` — YAML frontmatter keys parsed by the project harness (not TypeScript; the format is YAML at the top of SKILL.md).

## Modified Types

- None. The skill is a new directory under `.claude/skills/`; no existing files are modified.

## Contracts

- `SkillHarness(SKILL.md) => SkillFrontmatter + guidance body` — The project harness reads the YAML frontmatter from the top of any `.claude/skills/*/SKILL.md` to determine invocation metadata, then passes the remainder to the agent as context guidance. No interface file exists; the contract is defined by the project convention documented in research.md.

## Slice 1: Create writing-bash-scripts skill

**Goal:** Produce a complete, eval-ready `writing-bash-scripts` skill with a self-contained SKILL.md body and an optional reference template, following the project frontmatter convention and agentskills.io directory layout.

**Files touched:**

- ✨ `.claude/skills/writing-bash-scripts/SKILL.md` — Complete skill document (~180-250 lines) with frontmatter, all bash conventions (strict mode, error handling, argument parsing, subcommand dispatcher, logging, quoting, dependency checking, help, temp files, testing/linting, portability), gotchas section, and scope guidance.
- ✨ `.claude/skills/writing-bash-scripts/references/bash-template.sh` — Minimal working bash script (~60-80 lines) demonstrating all conventions in a single copy-paste base. (Optional per design, but recommended for eval quality.)
- Modify `.claude/skills/writing-bash-scripts/references/` — Directory already exists (scaffolded but empty of files); template file populates it.

**Verification:**
- [ ] SKILL.md frontmatter parses correctly: `name`, `description`, `command: /writing-bash-scripts`, `argument-hint`, `allowed-tools` keys present.
- [ ] SKILL.md body is under 500 lines / 5000 tokens.
- [ ] SKILL.md covers all 12 convention sections: strict mode, error handling, argument parsing, subcommand dispatcher, logging, quoting & variables, dependency checking, usage/help, temp files, testing & linting, portability, gotchas, scope guidance.
- [ ] Gotchas section covers: unquoted variables, missing `--` in commands, `cd` without error check.
- [ ] BATS-core is mentioned by name with an inline example.
- [ ] Dependency checking uses generic pattern (exit code 1, stderr message) -- no per-dependency mapping.
- [ ] Bash template in `references/bash-template.sh` is syntactically valid (run `bash -n` on it).

**Context cost:** S
**Depends on:** none

---

## Unverified Assumptions

- A1: The `references/` directory at `.claude/skills/writing-bash-scripts/references/` is confirmed empty (no files inside) -- design says it is scaffolded with no content, but the directory creation itself was noted as incomplete. This should be verified by the implementer before writing.
- A2: The ticket references "produces ShellCheck-clean output" as a goal but does not mandate adding ShellCheck to the eval harness. The structure assumes this is a design goal for the skill's guidance content, not an eval assertion -- the implementer should confirm.
- A3: No `scripts/` subdirectory is created for BATS test files. The design recommends against it (no existing skill uses `scripts/`), but if the user wants inline BATS examples in the SKILL.md body, those would be placed in the "Testing & Linting" section rather than a separate file.
