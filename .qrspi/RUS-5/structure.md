# Structure Outline — Create a new agent skill called writing-bash-scripts

**Design basis:** design.md @ 2026-06-03T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft

## New Types

This ticket produces markdown/skill artifacts, not code. The "types" here are
the structural schemas the artifacts must satisfy.

- `SkillFrontmatter { name: string, description: string, command: string, argument-hint: string, allowed-tools: string }` — YAML frontmatter block at the top of SKILL.md, matching the in-repo five-key schema (ref: design §Desired End State, Q3). `description` is the trigger surface (enumerated positive triggers + "Use when" scope + explicit skip clause).
- `ReferenceCatalog { files: ReferenceFile[] }` — the `references/` subdirectory; one or more `*.md` files holding overflow convention detail.
- `ReferenceFile { path: string, topic: string }` — a single long-form convention document (e.g. strict-mode, error-handling/traps, argument-parsing/getopts, subcommand-dispatch, logging, quoting, dependency-checks, usage-heredoc, temp-files, testing/linting, portability).

## Modified Types

- `README.md` — append skill row to the skill table; add `writing-bash-scripts/` node to the Project Structure tree (ref: design §Delta, non-load-bearing for discovery).
- `.claude/CLAUDE.md` — append the skill to the "Available skills" list (ref: design §Delta, non-load-bearing for discovery).

## Contracts

- `SKILL.md frontmatter → YAML.parse()` — the frontmatter block MUST parse as valid YAML and contain exactly the five in-repo keys (`name`, `description`, `command`, `argument-hint`, `allowed-tools`). `name` MUST equal `writing-bash-scripts`.
- `SKILL.md body → references/<file>.md` — every detail topic offloaded from the body is reachable via a relative-path link from SKILL.md (mirrors the `qrspi-work/references/review-cascade.md` precedent). No reference file is orphaned; no SKILL.md link dangles.
- `SKILL.md.description → trigger boundary` — description enumerates positive bash-authoring triggers AND an explicit "do NOT use for…" skip clause (NEW PATTERN per design Decision 3) to bound a broad topic.
- `SKILL.md.body → size limit` — body (excluding references) stays under 500 lines / ~5000 tokens (AC).
- `guidance → ShellCheck-clean output` — guidance is concrete enough that a script authored by an agent following it passes ShellCheck with zero warnings (AC; verification deferred where ShellCheck binary is absent, per design Decision 4 / OQ2).

## Slice 1: Author the writing-bash-scripts skill (SKILL.md + references + doc mirrors)

**Goal:** A discoverable, self-contained `writing-bash-scripts` knowledge skill that auto-triggers on bash-authoring requests and supplies guidance sufficient to produce ShellCheck-clean scripts, with overflow detail in `references/` and the two human-facing skill lists updated for consistency. This is one cohesive unit: the SKILL.md links its references and cannot be verified without them, and the doc-mirror edits are trivial consistency changes with no independent verification signal — splitting them would create false boundaries (ref: design §Delta; structure rule 8).

**Files touched:**

- ✨ `.claude/skills/writing-bash-scripts/SKILL.md` — frontmatter (five-key schema, engineered description with positive + skip triggers), opinionated defaults, a "code organization" ordering, a gotchas section, and relative-path links into `references/`. Self-contained archetype, no agent file (ref: design Decision 1).
- ✨ `.claude/skills/writing-bash-scripts/references/*.md` — one or more long-form convention files (strict mode, error handling/traps, argument parsing/getopts, subcommand dispatch, logging, quoting, dependency checks, usage heredoc, temp files, testing/linting, portability), so the SKILL body stays under the size limit (ref: design Decision 2, Q7).
- ⚠️ `README.md` — add the skill to the skill table and the Project Structure tree (ref: design §Delta, Q6/Q12).
- ⚠️ `.claude/CLAUDE.md` — add the skill to the "Available skills" list (ref: design §Delta, Q6/Q12).

**Authoring method:** invoke the external skill-creator skill (and its eval loop) to author/validate the skill where available; if unavailable in the implementation session, author by hand to the in-repo five-key schema and note the deviation (ref: design Decision 1, Risk row, Q4; user MEMORY: always use skill-creator for skills). Validation is the final step of this slice, not a separate slice (structure rule 9).

**Verification:**
- [ ] `SKILL.md` frontmatter parses as YAML and carries exactly the five in-repo keys with `name: writing-bash-scripts`.
- [ ] SKILL.md body is under 500 lines and ~5000 tokens (e.g. `wc -l`).
- [ ] Every `references/` link in SKILL.md resolves to an existing file; no reference file is orphaned.
- [ ] A sample script authored by following the guidance passes ShellCheck with zero warnings WHERE ShellCheck is available; otherwise record that the check is deferred (OQ2).
- [ ] `description` contains both enumerated positive triggers and an explicit skip/negative clause.
- [ ] `README.md` and `.claude/CLAUDE.md` both list the new skill.
- [ ] skill-creator validation/eval passes (or hand-authoring deviation is noted).

**Context cost:** M
**Depends on:** none

---

## Unverified Assumptions

- **agentskills.io frontmatter standard (OQ1).** The design treats the in-repo five-key schema as compatible with the external agentskills.io standard, which cannot be fetched in this environment. If the human requires specific agentskills.io fields beyond the five keys, the frontmatter contract above is incomplete. Needs human confirmation before planning.
- **ShellCheck-clean AC verifiability (OQ2).** ShellCheck is not installed in this container and is not provisioned by the Dockerfile/post-create. The "ShellCheck-clean output" AC cannot be runnably verified here; whether this ticket should also provision ShellCheck is an unresolved scope call. The verification step above is conditional on ShellCheck availability.
- **Whether a `command`/`argument-hint` is meaningful for an auto-invoked knowledge skill (OQ3).** The in-repo schema treats both keys as standard, but knowledge skills are typically auto-triggered, not invoked as slash commands. The frontmatter contract includes both keys per repo convention; confirm whether a nominal `/writing-bash-scripts` command should exist.
- **Number and partition of `references/` files.** The design says "one or more" reference files covering ~11 convention topics but does not fix the file count or how topics are grouped. Left to the implementer; not mapped to concrete file paths.
- **skill-creator availability in the implementation session.** The design assumes the external skill-creator skill is reachable from the implementation phase; it is not committed in-repo. If unavailable, the authoring method falls back to hand-authoring with a noted deviation.
