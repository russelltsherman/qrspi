# Design — Create a new agent skill using obsidian cli

**Ticket:** RUS-17
**Research basis:** research.md @ 2026-06-04T00:00:00Z
**Generated:** 2026-06-04T00:00:00Z
**Status:** draft

## Current State

Existing skills live under `.claude/skills/<skill-name>/SKILL.md`; there are 10 skills, all `qrspi-*`-prefixed, each its own directory holding a single `SKILL.md` (ref: Q1). Only one skill uses the multi-file pattern: `qrspi-work/` has a `references/` subdirectory (`references/review-cascade.md`); no skill in the repo has a `scripts/` or `assets/` directory (ref: Q1). The "agentskills.io / Anthropic skill-builder" canonical layout named in the ticket is not documented anywhere in this repo — only `references/` has an in-repo precedent (ref: Q1).

The `skill-creator` skill is not present under REPO_ROOT; it is a global/built-in skill outside the project scope, so its scaffolding inputs/outputs cannot be characterized from within the project (ref: Q2). No in-repo tool generates skills; existing skills were authored by hand (ref: Q2).

Every in-repo `SKILL.md` uses YAML frontmatter with five keys in fixed order: `name`, `description`, `command`, `argument-hint`, `allowed-tools` (ref: Q3). `name` equals the directory name and `command` is `/` + that name (ref: Q3, Q6). No explicit line/token limit is encoded anywhere in the repo; the "500 lines / 5000 tokens" cap is an external authoring convention, and `qrspi-work/SKILL.md` is already 565 lines, so the cap is not honored in-repo (ref: Q3). The content-split precedent is `qrspi-work`: core decision/trigger logic stays inline in `SKILL.md`, bounded situational lookup material is factored to `references/*.md` and referenced by relative path `(see references/<file>.md)`; reference files are prose+tables with no frontmatter (ref: Q4).

Skill discovery is filesystem auto-discovery — there is no manifest, registry, or index; a skill becomes available simply by existing as `.claude/skills/<name>/SKILL.md` with valid frontmatter (ref: Q5). The only in-repo list of skills is human-facing prose in `.claude/CLAUDE.md` "Available skills"; no code reads it, but it should be updated for consistency (ref: Q5). The naming convention is lowercase kebab-case with directory == frontmatter `name` == command minus the slash; every existing skill carries the `qrspi-` prefix, but that prefix encodes the QRSPI phase pipeline and no non-qrspi precedent exists in-repo (ref: Q6).

Error-handling guidance precedent is `qrspi-work`: a `## Error Handling` bullet list of `condition → STOP/action`, a strong "HARD STOP" subsection for infrastructure/auth errors, an explicitly-forbidden enumeration, and a rationale paragraph; `qrspi-ticket` shows a lighter inline "report the error and STOP. Do not <fallback>" form (ref: Q7). Tool-preference guidance is expressed two ways: decision tables for multi-case selection, and imperative "prefer X / do NOT Y because <consequence>" sentences each carrying a stated reason (ref: Q8).

No skill bundles runnable scripts; the project-level convention (top-level `scripts/`, separate from skills) is `#!/usr/bin/env python3`, stdlib-only, self-locating paths, executable bit on entry-points, and a `_test.py` sibling — but there is NO precedent for a per-skill `scripts/` directory (ref: Q9). Skill verification in-repo is `_test.py` unit tests for pure logic plus manual end-to-end runs; `scripts/run_eval.py` + `evals/` is a non-functional placeholder, and the skill-creator eval loop is out of project scope (ref: Q10). The `description` field is the auto-invocation trigger surface; the in-repo wording pattern is a capability statement followed by an explicit "Use when…" clause, optionally enumerating literal trigger phrases, naming concrete domain nouns (ref: Q11).

## Desired End State

A new skill directory `.claude/skills/<obsidian-skill-name>/` ships with a valid `SKILL.md` (five-key frontmatter, kebab-case `name` == directory == `command` minus slash) and a `references/` directory holding the detailed lookup material. Mapping each acceptance criterion to concrete behavior:

- **agentskills.io directory structure + valid SKILL.md frontmatter** → `SKILL.md` carries the in-repo five-key frontmatter (ref: Q3); `references/` follows the one in-repo multi-file precedent (ref: Q1, Q4). See Open Questions on the agentskills.io two-key vs in-repo five-key conflict.
- **Built using the Anthropic skill-builder skill** → satisfied at build time by invoking the global skill-creator skill (out of project scope, ref: Q2); the design cannot enforce its internals, only require its use in the plan/implementation phase.
- **Body under 500 lines / 5000 tokens** → target the cap as an authoring discipline; it is not enforced in-repo and `qrspi-work` already exceeds it, so the `references/` split (ref: Q4) is the mechanism for keeping the body small.
- **Detailed reference material in references/ (full CLI reference, URI protocol, Dataview syntax)** → three reference files (or one consolidated file) under `references/`, prose+tables, no frontmatter, linked from the body by relative path (ref: Q4).
- **Covers all official CLI commands (create, read, append, prepend, move, delete, search, daily, properties, tags, links, files, templates)** → the CLI reference file enumerates every command from the ticket with parameters and quoting/encoding notes.
- **Documents frontmatter property conventions for all seven supported types** → a properties section covers Text, Number, Checkbox, Date, Date & Time, List, Links with one example each.
- **Linking best practices (wikilinks vs markdown, headings, block refs)** → a linking section with the `[[wikilink]]`, `[[Note#Heading]]`, `[[Note#^block-id]]`, and pipe-display conventions, plus when to use standard markdown links.
- **Plugin-aware patterns (Dataview, Templater, Tasks) without installation** → a plugin-conventions section documenting data formats only; Dataview query syntax detail lives in `references/`.
- **CLI vs URI vs filesystem guidance** → a decision table plus imperative prefer/forbid prose (ref: Q8).
- **Error handling (Obsidian not running, malformed YAML, link collisions)** → an error-handling section in the `qrspi-work` `condition → action` style (ref: Q7).

## Delta

- **New directory:** `.claude/skills/<obsidian-skill-name>/`.
- **New file:** `.claude/skills/<obsidian-skill-name>/SKILL.md` — five-key frontmatter; body holds capability/trigger description, vault-structure conventions, note CRUD overview, frontmatter/property conventions (seven types), linking best practices, tags, the CLI-vs-URI-vs-filesystem decision table, idempotency guidance, plugin data conventions, and an error-handling section; relative-path pointers into `references/`.
- **New file(s):** `.claude/skills/<obsidian-skill-name>/references/cli-reference.md` (all CLI commands + quoting/encoding), `references/uri-protocol.md` (obsidian:// actions, URI encoding), `references/dataview.md` (DQL + inline-field syntax). May be consolidated into one `references/*.md` if the body-cap budget allows.
- **Modified file:** `.claude/CLAUDE.md` "Available skills" list — add the new skill for documentation consistency (not load-bearing, ref: Q5).
- **No code changes, no manifest/registry edit** — discovery is auto-discovery (ref: Q5).
- **No `scripts/` directory** unless a concrete script need emerges (no in-repo precedent, ref: Q9).

## Pattern Decisions

### Decision 1: Skill name / prefix

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | `obsidian` (no prefix) | Domain-accurate; reflects that this is not a QRSPI phase | No in-repo precedent for non-qrspi names; could collide with future generic names |
| B | `qrspi-obsidian` (carry prefix) | Matches the only existing convention exactly | Misleading — implies it is a QRSPI workflow phase, which it is not (ref: Q6) |
| C | `obsidian-vault` | Domain-accurate and specific; describes the capability | Slightly longer; still no prefix precedent |

**Recommendation:** Option A (`obsidian`)
**Rationale:** The only firm in-repo rule is lowercase kebab-case with directory == `name` == command; the `qrspi-` prefix encodes the workflow phase pipeline, which this skill is not part of (ref: Q6). A bare domain name is the honest fit; there is no non-qrspi precedent to violate.
**NEW PATTERN?** Yes — first non-`qrspi-`-prefixed skill in the repo. Justified because every existing prefix denotes a QRSPI phase and this capability is unrelated to that pipeline (ref: Q6).

### Decision 2: Reference-file granularity

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Three files (cli, uri, dataview) | Clear topical separation; matches the AC's three named reference topics | More files than the single in-repo precedent (one reference file) |
| B | One consolidated `references/reference.md` | Closest to the lone in-repo precedent (`qrspi-work`) | Large single file; weaker topical addressing |

**Recommendation:** Option A
**Rationale:** The AC explicitly names three reference topics (CLI, URI, Dataview); the in-repo precedent establishes the `references/<file>.md` relative-path mechanism but not a one-file rule (ref: Q4). Splitting keeps each file focused and lets the body cite the exact topic.
**NEW PATTERN?** No — extends the existing `references/` precedent to multiple files; the addressing mechanism is unchanged (ref: Q4).

### Decision 3: Frontmatter shape (agentskills.io vs in-repo five-key)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | In-repo five-key (`name`, `description`, `command`, `argument-hint`, `allowed-tools`) | Consistent with all 10 existing skills and the repo's auto-discovery/firewall conventions (ref: Q3) | May diverge from the agentskills.io two-key (`name`/`description`) standard the ticket cites |
| B | agentskills.io minimal (`name`, `description`) | Matches the external standard named in the AC | Breaks repo uniformity; loses `allowed-tools` firewall and `command` invocation (ref: Q3) |
| C | Superset (five-key + any extra agentskills.io keys) | Satisfies both | Risk of harness rejecting unknown keys; unverified |

**Recommendation:** Option A, pending Open Question OQ1
**Rationale:** The repo's frontmatter contract is uniform and load-bearing (`allowed-tools` is a security firewall; `command` is the invocation) (ref: Q3). The agentskills.io standard cannot be verified from project scope (ref: Q1, Q2). Defaulting to the in-repo contract is the safe, consistent choice unless the human confirms the external standard takes precedence.
**NEW PATTERN?** No (for Option A) — reuses the established five-key frontmatter exactly (ref: Q3).

### Decision 4: Tool-preference encoding (CLI vs URI vs filesystem)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Decision table + imperative prefer/forbid prose | Matches both in-repo precedents for >2-case selection with rationale (ref: Q8) | Slightly more verbose |
| B | Prose-only "prefer X" sentences | Lighter | Three discrete cases (CLI/URI/filesystem) read better as a table (ref: Q8) |

**Recommendation:** Option A
**Rationale:** With three discrete selection cases, the in-repo convention is a selection table plus "prefer X / do NOT Y because <consequence>" sentences, each justified (ref: Q8). This directly fits the ticket's CLI-over-URI-over-filesystem and idempotency guidance.
**NEW PATTERN?** No — direct application of the documented in-repo tool-preference pattern (ref: Q8).

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| agentskills.io standard conflicts with in-repo five-key frontmatter, failing AC #1 either way | med | high | Resolve OQ1 with the human before implementation; default to in-repo five-key (ref: Q3) and document the deviation |
| "Built using the Anthropic skill-builder skill" (AC #2) is unverifiable in project scope — cannot prove compliance from artifacts | med | med | Require the skill-creator invocation explicitly in the plan phase; note it is a build-time action outside repo verification (ref: Q2) |
| Body exceeds 500 lines / 5000 tokens given the breadth of required content | med | med | Aggressively factor CLI/URI/Dataview detail into `references/`; cap is unenforced (ref: Q3) but treat as authoring discipline (ref: Q4) |
| Obsidian CLI command behavior is documented only from the ticket text, not verified against a running binary | high | med | Treat the ticket's command list as authoritative source-of-record; mark in the skill that examples reflect CLI v1.12.4 conventions; no in-repo way to verify |
| No functional eval to validate the prose skill before merge | high | low | Rely on `_test.py`/manual review precedent (ref: Q10); human review of the SKILL.md is the gate; frontmatter validity is mechanically checkable |
| First non-`qrspi-` skill name sets an un-precedented convention | low | low | Document the naming rationale (Decision 1); confirm via OQ2 if a prefix is desired |

## Open Questions

- OQ1: Does AC #1's "agentskills.io directory structure with valid SKILL.md frontmatter" require the external two-key frontmatter, or is the repo's five-key contract acceptable (and preferred for consistency)? This determines Decision 3.
- OQ2: Should the skill carry the `qrspi-` prefix for repo uniformity, or a bare `obsidian` name reflecting that it is not a QRSPI phase? (Decision 1.)
- OQ3: Is invoking the global skill-creator skill (AC #2) a hard build-time requirement, given its internals and eval loop are outside project scope and cannot be verified from the repo (ref: Q2, Q10)?
- OQ4: Is there a running Obsidian instance or CLI available to validate the documented commands, or should the skill be authored purely from the ticket's command spec (CLI v1.12.4)?
