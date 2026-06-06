# Structure Outline — Create a new agent skill for writing Architecture Decision Records

**Design basis:** design.md @ 2026-06-04T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft

> Note: This is a documentation/skill-authoring ticket. There is no executable code,
> so "types" and "contracts" below describe the markdown/frontmatter schemas and
> linking conventions the artifacts must satisfy, not language-level types or functions.

## New Types

- `SkillFrontmatter { name: string, description: string, command: string, argument-hint: string, allowed-tools: comma-separated-list }` — YAML block delimited by `---` at top of `SKILL.md`; `name` == directory name, `command` == `/` + name, `description` in imperative "Use when… / Trigger on…" form (ref: design §Desired End State, Decision 1; Q3).
- `ADRStatusTransition { from: status, to: status, action: string }` — rows of a prose markdown table in `SKILL.md` encoding `proposed → accepted → deprecated|superseded`, plus `rejected` (ref: design §Desired End State, Decision 4; Q8).
- `MADR4Document { Title, Status, Date, Context-and-Problem-Statement, Decision-Drivers, Considered-Options, Decision-Outcome, Consequences }` — the eight required ordered sections that the `assets/` starter and `references/madr-4.0.md` materialize (ref: design §Desired End State).
- `ADRNaming { path: "docs/decisions/", filename: "NNNN-kebab-case-title.md", numbering: sequential-4-digit }` — adr-tools / log4brains compatible naming convention documented in `SKILL.md` (ref: design §Desired End State).

## Modified Types

- None — no existing code types or schemas change. The three modified files (Contracts → SkillListEntry) gain a row each, not a schema change (ref: design §Delta).

## Contracts

- `SkillListEntry: "- \`/<name> <args>\` — <one-line desc>"` — the bullet format each of the three hand-maintained skill lists uses; the new entry must match the surrounding style in each file (ref: design §Delta; Q12). Cross-slice: Slice 1 fixes the final `name`/`command`/`description`; Slice 2 consumes them.
- `ReferenceLink: "see \`references/<file>.md\`"` — bare relative path in backticks, on-demand load, resolved against the skill dir; the only in-repo convention (ref: Decision 3; Q2). Every `references/` file must be reachable by exactly one such pointer from `SKILL.md`.
- `AssetReference: "\`assets/NNNN-template.md\`"` — bare-relative-path pointer to the copyable starter; first `assets/` use in the repo (ref: Decision 2; Q1, Q6).
- `SupersedeProcedure(oldADR, newADR)` — updates both `oldADR` (`superseded by ADR-NNNN`) and `newADR` (`Supersedes ADR-NNNN`); bidirectional-link invariant documented in `SKILL.md` (ref: design §Desired End State).

## Slice 1: Author the `adr` skill (SKILL.md + references/ + assets/)

**Goal:** A complete, discoverable, self-contained skill at `.claude/skills/<name>/` that the Claude Code runtime lists and that fully encodes MADR-4.0-default authoring, the lifecycle transition table, numbering/naming, when-to-write guidance, and the supersede procedure — with all heavy material pushed into `references/` and a copyable starter in `assets/`. End-to-end testable: the skill appears in the skill list and, when invoked, its body + on-demand references guide an ADR through create/supersede/deprecate.

**Files touched:**

- ✨ `.claude/skills/<name>/SKILL.md` — frontmatter (SkillFrontmatter) + lean body: MADR default sections, ADRStatusTransition table, ADRNaming rules, when-to-write ("architecturally significant") section, SupersedeProcedure, and ReferenceLink/AssetReference pointers.
- ✨ `.claude/skills/<name>/references/madr-4.0.md` — full MADR 4.0 template and per-section guidance (incl. optional sections).
- ✨ `.claude/skills/<name>/references/nygard.md` — Nygard original template.
- ✨ `.claude/skills/<name>/references/y-statements.md` — Y-statement format.
- ✨ `.claude/skills/<name>/references/examples.md` — worked example ADRs.
- ✨ `.claude/skills/<name>/assets/NNNN-template.md` — copyable MADR 4.0 starter ADR.

**Verification:**
- [ ] `SKILL.md` frontmatter has all five fields; `name` == dir name, `command` == `/`+name; inspect manually (no in-repo validator — Q3, Q11).
- [ ] Every `references/*.md` file is pointed to by exactly one bare-relative-backtick `ReferenceLink` from `SKILL.md`, and `assets/NNNN-template.md` by an `AssetReference` (grep).
- [ ] `SKILL.md` body ≤ 500 lines: run `line_count` from `scripts/grade.py` against it as a one-off; token budget (≤5000) checked by inspection (no token counter exists — Q7).
- [ ] `assets/NNNN-template.md` contains the eight ordered MADR sections.
- [ ] Skill authored/validated via `skill-creator` (external/global skill, assumed present — Q4); success confirmed by manual review.
- [ ] Skill appears in the runtime's available-skills list (drop-in discoverability — Q12).

**Context cost:** M
**Depends on:** none (but blocked on resolving OQ1 name and OQ2 allowed-tools — see Unverified Assumptions)

## Slice 2: Sync the three hand-maintained skill lists

**Goal:** The new skill is listed consistently in all three hand-maintained indexes so the docs do not drift (ref: Q12). Independently verifiable: each file contains a SkillListEntry for the skill matching its surrounding format.

**Files touched:**

- ⚠️ `.claude/CLAUDE.md` — add a `SkillListEntry` to the available-skills list.
- ⚠️ `README.md` — add the skill.
- ⚠️ `docs/qrspi_claude_code_guide.md` — add the skill.

**Verification:**
- [ ] `grep -rl "<name>"` returns all three files; each entry uses that file's existing bullet style.
- [ ] The `name`/`command`/`description` in each entry matches Slice 1's final `SKILL.md` frontmatter (no drift).

**Context cost:** S
**Depends on:** Slice 1 (final `name`/`command`/`description` must be fixed first)

---

## Unverified Assumptions

- **OQ1 — final skill slug (BLOCKING):** design proposes `adr` / `writing-adr` / `architecture-decision-records` but does not fix one. `name` == directory == `command` stem (Q3), so every new path above is parameterized as `<name>` and cannot be finalized until a human chooses. Resolve before Slice 1.
- **OQ2 — `allowed-tools` allowlist:** the minimal capability set is undetermined. Likely Read/Write/Edit + Glob (to find existing ADRs for numbering), but the firewall idiom favors the minimum (Q3). Human must confirm the exact set before Slice 1 frontmatter is written.
- **OQ3 — scaffold `docs/decisions/` + `README.md` index, or only document it?** No such directory exists (Q9). If scaffolding is in scope, Slice 1 (or a new slice) would create `docs/decisions/README.md` — currently treated as documentation-only, not file creation. Needs human decision.
- **OQ4 — is the ≤500-line / ≤5000-token budget an enforced gate or an authoring guideline?** No enforcement mechanism exists for either half (Q7). Verification above treats it as a manual guideline; if a real gate is wanted, a new check (and a slice for it) would be required.
- **`skill-creator` availability:** the "built using the skill-builder skill" criterion depends on an external/global skill whose contract is unverifiable from the repo (Q4). Assumed present; confirmed only by manual review, not tooling.
- **First-ever `assets/` convention:** `assets/` has no repo precedent (Q1, Q6); its introduction is ticket-mandated (Decision 2) but unverified against any existing loader behavior.
