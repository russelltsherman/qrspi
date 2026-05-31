# Structure Outline — Create a new agent skill: writing Architecture Decision Records

**Design basis:** design.md @ 2026-05-31T16:33:00Z
**Generated:** 2026-05-31T16:36:00Z
**Status:** draft

## New Types

This deliverable is a documentation/skill artifact, not code, so "types" here are the file artifacts and their required internal shapes (the contracts other files and agents rely on).

- `SKILL.md` frontmatter `{ name: kebab-case-string, description: string (capability + "Use when/Trigger on" + negative scope), allowed-tools?: comma-list }` (ref: design.md §Delta, Decision 1)
- `ADRDocument { title: "ADR-NNNN: <noun phrase>", status: proposed|accepted|deprecated|superseded|rejected, date: ISO-8601, context: prose, decisionDrivers: bullet-list, consideredOptions: numbered-list, decisionOutcome: "Chosen option: <name>, because <justification>", consequences: { good[], bad[], neutral[] }, optional: { deciders, consulted, informed, prosConsPerOption, confirmation, moreInformation } }` — the MADR 4.0 shape the skill must produce (ref: design.md §Desired End State)
- `ADRFilename = "NNNN-kebab-case-title.md"` — zero-padded 4-digit, sequential, never reused (ref: design.md Decision 3)
- `IndexEntry { number, title, status, link }` — a row in `docs/decisions/README.md` (ref: design.md §Desired End State)

## Modified Types

- None. The deliverable is additive; no existing repo file is modified (ref: design.md §Delta, ref: research.md Q5).

## Contracts

- `create-adr`: agent reads `assets/adr-template.md`, determines next `NNNN` (max existing + 1, zero-padded), fills placeholders, writes `docs/decisions/NNNN-kebab-title.md` with status `proposed`, and adds an `IndexEntry` to `docs/decisions/README.md` (ref: design.md §Desired End State, Decision 3).
- `supersede-adr`: agent creates the new ADR (status `accepted`) with a "Supersedes ADR-NNNN" back-reference, sets the old ADR's status to `superseded by ADR-NNNN` and adds a forward reference, and updates both index entries — bidirectional links required (ref: design.md §Desired End State).
- `deprecate-adr`: agent sets an ADR's status to `deprecated` (only the status/date field changes; body immutable) and updates the index.
- `choose-format`: given decision weight/ceremony, recommend MADR (default), Nygard (minimal-ceremony), or Y-statement (rapid capture) via an option/recommendation table (ref: design.md Decision 1, ref: research.md Q6).
- `when-to-write-adr`: apply the architecturally-significant test (hard to reverse, multi-component, affects non-functional requirements, would confuse future developers) (ref: design.md §Desired End State).
- `body-references-loading`: SKILL.md body instructs "Read `references/<file>`" on demand and "copy `assets/adr-template.md`" — keeping body under 500 lines / 5000 tokens (ref: research.md Q2, Q7).

## Slice 1: Author the ADR-writing skill via skill-creator

**Goal:** A complete, valid, self-contained ADR-writing skill at `.claude/skills/<adr-skill-name>/`, authored and validated through the runtime `skill-creator` skill, satisfying every acceptance criterion. This is one testable end-to-end deliverable: a skill is only meaningful when its SKILL.md, references, and asset exist together and validate as a unit — no file can be verified in isolation (ref: structure rule 8; design.md Decision 1, Decision 2).

**Files touched:**

- ✨ `.claude/skills/<adr-skill-name>/SKILL.md` — frontmatter + lean body (when-to-write test, MADR default sections, format selection, numbering/naming, status lifecycle + immutability, supersede/deprecate with bidirectional links, index maintenance, writing style, reference/asset pointers)
- ✨ `.claude/skills/<adr-skill-name>/references/madr-4.0.md` — full MADR 4.0 template, required + optional sections explained
- ✨ `.claude/skills/<adr-skill-name>/references/nygard.md` — Nygard original template + when to prefer
- ✨ `.claude/skills/<adr-skill-name>/references/y-statements.md` — Y-statement format + when to prefer
- ✨ `.claude/skills/<adr-skill-name>/references/examples.md` — 2+ worked example ADRs (lightweight + heavy) and a worked supersede pair demonstrating bidirectional links
- ✨ `.claude/skills/<adr-skill-name>/assets/adr-template.md` — copyable MADR 4.0 starter with angle-bracket placeholders
- ✨ `.claude/skills/<adr-skill-name>/assets/index-README-template.md` — copyable `docs/decisions/README.md` index starter

**Verification:**
- [ ] Skill authored through the `skill-creator` skill (not hand-written), per the ticket and the user directive
- [ ] `SKILL.md` frontmatter is valid (`name`, `description`); `name` is unique kebab-case with no collision (ref: research.md Q9)
- [ ] `SKILL.md` body is under 500 lines AND under ~5000 tokens (measured)
- [ ] `references/` contains madr-4.0, nygard, y-statements, and examples files, all non-empty
- [ ] `assets/adr-template.md` exists, is copyable, and uses angle-bracket placeholders matching the repo convention (ref: research.md Q8)
- [ ] Body encodes the MADR 4.0 required section order and the optional sections
- [ ] Body documents the full lifecycle (create, supersede, deprecate, index maintenance) and bidirectional linking on supersede
- [ ] Body documents the architecturally-significant "when to write" test and the level-of-detail / supersede-vs-amend judgment calls
- [ ] Numbering/naming and default paths match adr-tools + log4brains (`NNNN-kebab-case-title.md`, `docs/decisions/` default, `docs/adr/` accepted)
- [ ] skill-creator's eval loop / structural validation passes (final step of this slice)

**Context cost:** M
**Depends on:** none

---

## Unverified Assumptions

- **skill-creator interface:** The slice assumes the runtime `skill-creator` skill can scaffold a skill with `references/` and `assets/` subdirectories and that its eval loop accepts a standalone content skill. skill-creator lives outside repo scope (ref: research.md Q4), so its exact inputs/outputs are unverified until invoked. If its behavior differs, the implementer must STOP and report (per design.md Risk 2 and the error-surfacing directive), not hand-author around it.
- **Skill name/directory (OQ1):** The exact `name` is unconfirmed. The slice proceeds with a descriptive kebab-case name derived from the ticket title unless the reviewer specifies otherwise; this does not block authoring but should be confirmed at plan review.
- **Optional `scripts/` helper (OQ2):** Assumed out of scope (docs-only) unless the reviewer requests a next-number/index helper. The ticket lists `scripts/` as optional and prefers "no special tooling required."
- **Seeding `docs/decisions/` in this repo (OQ3):** Assumed the skill documents how to create ADRs rather than seeding this repo with live ADRs; the `assets/index-README-template.md` is a copyable starter, not an installed index. Unverified pending reviewer preference.
- **Token budget measurement:** "Under 5000 tokens" is assumed measurable with a line-count proxy plus skill-creator's own checks; no exact tokenizer is wired into the repo eval harness for this skill (ref: research.md Q10).
