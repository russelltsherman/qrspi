# Structure Outline — Create a new agent skill using obsidian cli

**Design basis:** design.md @ 2026-06-04T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft

> Note: This ticket produces a prose/documentation skill, not executable code. The
> "types" and "contracts" below are the structural contracts the skill must satisfy
> (frontmatter schema, file-layout/linking conventions, auto-discovery rules) rather
> than language-level types. They are the concrete, mappable obligations from design.md.

## New Types

- `SkillFrontmatter { name: kebab-case-string, description: string, command: "/"+name, argument-hint: string, allowed-tools: string }`
  — the in-repo five-key YAML frontmatter, keys in fixed order `name`, `description`, `command`, `argument-hint`, `allowed-tools` (design.md §Delta, Decision 3 Option A, ref Q3).
- `ReferenceFile { format: "prose+tables", frontmatter: none }`
  — a `references/<topic>.md` lookup file: no YAML frontmatter, prose and tables only (Decision 2 Option A, ref Q4).
- `SkillDirectory { path: ".claude/skills/obsidian/", body: SKILL.md, references: ReferenceFile[] }`
  — directory name == frontmatter `name` == `command` minus the leading slash (Decision 1 Option A, ref Q6).

## Modified Types

- `AvailableSkillsList` (the "Available skills" prose block in `.claude/CLAUDE.md`) — add one bullet for the new `obsidian` skill (design.md §Delta; non-load-bearing, ref Q5).

## Contracts

- `frontmatter-name-invariant`: `SkillFrontmatter.name` == directory basename == `SkillFrontmatter.command` without the leading `/` — required for filesystem auto-discovery (ref Q5, Q6).
- `reference-link-contract`: every detailed CLI / URI / Dataview topic is factored into `references/<topic>.md` and cited from the `SKILL.md` body by relative path `(see references/<file>.md)`; reference files carry no frontmatter (ref Q4).
- `body-budget-contract`: `SKILL.md` body targets < 500 lines / < 5000 tokens as authoring discipline; overflow detail is pushed into `references/` (unenforced in-repo, ref Q3/Q4).
- `cli-coverage-contract`: the CLI reference enumerates every command named in the ticket — create, read, append, prepend, move, delete, search, daily, properties, tags, links, files, templates — each with parameters and quoting/encoding notes (design.md §Desired End State).
- `property-coverage-contract`: the properties section documents all seven supported frontmatter types — Text, Number, Checkbox, Date, Date & Time, List, Links — one example each (design.md §Desired End State).
- `tool-preference-contract`: CLI-vs-URI-vs-filesystem guidance is a decision table plus imperative "prefer X / do NOT Y because <consequence>" prose, each with a stated reason (Decision 4 Option A, ref Q8).
- `error-handling-contract`: an error-handling section in the `qrspi-work` `condition → STOP/action` style covers Obsidian-not-running, malformed YAML, and link collisions (ref Q7).

## Slice 1: Author the `obsidian` skill (body + references + list update)

**Goal:** A complete, auto-discoverable `obsidian` skill that ships valid five-key
frontmatter, a body covering vault conventions / note CRUD / property types / linking /
tags / the CLI-vs-URI-vs-filesystem decision table / idempotency / plugin data
conventions / error handling, with detailed CLI, URI, and Dataview material factored
into `references/`, and the project skills list updated. End-to-end testable path:
the skill is discovered by the harness and its frontmatter + reference links resolve.

**Files touched:**

- ✨ `.claude/skills/obsidian/SKILL.md` — five-key frontmatter (`name: obsidian`, `command: /obsidian`); body with capability/trigger description, vault-structure conventions, note-CRUD overview, frontmatter property conventions (seven types), linking best practices, tags, CLI-vs-URI-vs-filesystem decision table + prefer/forbid prose, idempotency guidance, plugin data conventions (Dataview/Templater/Tasks formats), error-handling section, and relative-path pointers into `references/`.
- ✨ `.claude/skills/obsidian/references/cli-reference.md` — all CLI commands (create, read, append, prepend, move, delete, search, daily, properties, tags, links, files, templates) with parameters + quoting/encoding notes (CLI v1.12.4 per ticket).
- ✨ `.claude/skills/obsidian/references/uri-protocol.md` — `obsidian://` actions and URI encoding.
- ✨ `.claude/skills/obsidian/references/dataview.md` — DQL + inline-field syntax.
- ⚠️ `.claude/CLAUDE.md` — add one bullet to the "Available skills" list for the new `obsidian` skill.

**Verification:**

- [ ] `SKILL.md` frontmatter parses as valid YAML with exactly the five keys in order; `name: obsidian`, `command: /obsidian`, directory basename == `obsidian` (frontmatter-name-invariant).
- [ ] Every `(see references/<file>.md)` link in the body resolves to an existing file under `references/`.
- [ ] CLI reference contains all 13 named commands (cli-coverage-contract); properties section covers all 7 types (property-coverage-contract).
- [ ] Body line/token count checked against the < 500 line / < 5000 token budget; overflow confirmed to live in `references/`.
- [ ] Skill is built via the global skill-creator skill per AC #2 (build-time action; see Unverified Assumptions / OQ3).
- [ ] Human review of `SKILL.md` prose (the in-repo gate, ref Q10) — no functional eval exists.

**Context cost:** M
**Depends on:** none

---

## Unverified Assumptions

These are claims from design.md that could not be mapped to a verifiable in-repo type,
file, or interface and need human attention before/within planning. They correspond to
the design's Open Questions and high-likelihood risks.

- **OQ1 / Frontmatter shape (Decision 3).** Whether AC #1's "agentskills.io directory structure with valid SKILL.md frontmatter" requires the external two-key (`name`/`description`) frontmatter or accepts the in-repo five-key contract. The structure above assumes the in-repo five-key (Option A); if the human mandates the two-key external standard, `SkillFrontmatter` changes and the `allowed-tools`/`command` invariants are dropped. Cannot be verified from project scope (ref Q1, Q2).
- **OQ2 / Skill name (Decision 1).** Assumes bare `obsidian` (no `qrspi-` prefix). If a prefix is required for uniformity, every path above changes to `.claude/skills/qrspi-obsidian/` and `command: /qrspi-obsidian`. First non-`qrspi-` skill in the repo (ref Q6).
- **OQ3 / skill-creator invocation (AC #2).** "Built using the Anthropic skill-builder skill" is a build-time action whose internals/eval loop are outside project scope and cannot be verified from repo artifacts (ref Q2, Q10). Treated as a required step in Slice 1 verification, but compliance is unprovable from the codebase.
- **OQ4 / CLI command behavior unverified.** Obsidian CLI command semantics, quoting/encoding, and the seven property types are documented solely from the ticket text (CLI v1.12.4); there is no running binary or in-repo fixture to validate them against (Risk Register). The reference content is authoritative-by-ticket, not verified.
- **Reference-file granularity (Decision 2).** Assumes three reference files (cli/uri/dataview). The design permits consolidation into one `references/*.md` if the body-cap budget allows; the final file count may collapse to one during authoring without changing the linking contract.
- **Body budget unenforced.** The < 500 line / < 5000 token cap has no in-repo enforcement and an existing skill already exceeds it (ref Q3); the verification step is a manual count, not a mechanical gate.
