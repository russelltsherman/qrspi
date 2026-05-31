# Design — Create a new agent skill: writing Architecture Decision Records

**Ticket:** RUS-25
**Research basis:** research.md @ 2026-05-31T16:30:00Z
**Generated:** 2026-05-31T16:33:00Z
**Status:** draft

## Current State

The repository hosts ten skills, all under `.claude/skills/<name>/`, each a directory whose `SKILL.md` carries `name`, `description`, `command`, `argument-hint`, and `allowed-tools` frontmatter (ref: Q1, ref: Q3). There is no ADR skill and no decision-record content anywhere in the skill set (ref: Q9). The repository has no `docs/decisions/`, `docs/adr/`, or `architecture/decisions/` directory and no pre-existing ADRs, so ADR conventions are defined greenfield (ref: Q5). The QRSPI skills follow a thin-wrapper pattern that delegates to agent prompts under `.claude/agents/`; only `qrspi-work` carries substantial inline content and the only existing `references/` subdirectory, loaded on demand by an explicit "Read `references/<file>`" instruction (ref: Q1, ref: Q2). No skill in the repo ships an `assets/` directory or a per-skill `scripts/` directory; the closest precedent for copyable, placeholder-driven templates is the `.qrspi/templates/` set, which agents read and populate (ref: Q8). Size is governed by convention, not enforcement: thin skills run 25-35 lines, `qrspi-ticket` is 119, and `qrspi-work` is 730 (ref: Q7). The `skill-creator` ("Anthropic skill builder") skill is not a repository asset; it is provided by the runtime harness and is the authority on naming, sizing, description tuning, and its own eval loop (ref: Q4, ref: Q7, ref: Q11). The `evals/` harness is purpose-built for QRSPI phase agents and cannot validate an ADR skill without a new case, so validation for this skill is structural plus skill-creator's eval loop (ref: Q10). Descriptions are the trigger surface: capability summary plus explicit "Use when/Trigger on" phrasing plus optional negative scope (ref: Q11).

## Desired End State

A new self-contained skill exists at `.claude/skills/<adr-skill-name>/` that guides agents to write and manage ADRs. Each acceptance criterion maps to concrete behavior:

- **agentskills.io directory structure with valid SKILL.md frontmatter** → the skill directory contains a `SKILL.md` with valid frontmatter (`name`, `description`, plus optional `allowed-tools`) and the standard `references/` and `assets/` subdirectories (ref: Q1, ref: Q3).
- **Built using the Anthropic skill builder skill** → the skill is authored/validated through the runtime `skill-creator` skill and its eval loop, satisfying the user's standing directive to never ship a SKILL.md ad-hoc (ref: Q4).
- **SKILL.md body under 500 lines / 5000 tokens** → the body holds only orientation, decision procedures, lifecycle rules, and "when to write an ADR" judgment, pushing full templates and examples into `references/` (ref: Q2, ref: Q7).
- **Detailed reference material in references/** → `references/` covers the MADR 4.0 full template, the Nygard original template, the Y-statement format, and example ADRs (ref: Q2).
- **Starter ADR template in assets/** → `assets/` holds a copyable MADR 4.0 starter file using angle-bracket placeholders that an agent reads-then-writes to create a new ADR (ref: Q8).
- **Encodes MADR 4.0 section structure as default** → the body specifies the required ordered sections (Title, Status, Date, Context and Problem Statement, Decision Drivers, Considered Options, Decision Outcome, Consequences) and the optional ones, marking MADR as default with Nygard/Y-statement as alternatives via the repo's option-plus-recommendation idiom (ref: Q6).
- **Full lifecycle: create, supersede, deprecate, index maintenance** → the body defines status transitions (proposed → accepted → deprecated|superseded; proposed → rejected), immutability after acceptance, and `docs/decisions/README.md` index upkeep.
- **Guidance on when to write an ADR** → the body encodes the "architecturally significant" test and the judgment calls (when to write, level of detail, supersede vs. amend).
- **adr-tools and log4brains compatibility** → numbering/naming (`NNNN-kebab-case-title.md`, zero-padded, sequential, never reused) and default paths (`docs/decisions/`, with `docs/adr/` accepted) match those tools' conventions.
- **Bidirectional links when superseding** → the body and examples require updating the old ADR's status to `superseded by ADR-NNNN` with a forward reference and adding a back-reference ("Supersedes ADR-NNNN") to the new ADR.

## Delta

New skill directory `.claude/skills/<adr-skill-name>/` with:

- `SKILL.md` — new. Frontmatter (`name`, `description` with "Use when/Trigger on" phrasing and negative scope, optional `allowed-tools`), plus a lean body: purpose; the architecturally-significant test for when to write an ADR; MADR 4.0 default section structure; format-selection guidance (MADR default; Nygard/Y-statement alternatives) using an option/recommendation table; numbering/naming and directory rules; status lifecycle and immutability; supersede/deprecate procedures with bidirectional linking; index maintenance; writing-style and level-of-detail guidance; and explicit "Read `references/<file>`" pointers and "copy `assets/<starter>`" instructions.
- `references/madr-4.0.md` — new. Full MADR 4.0 template with all required and optional sections explained.
- `references/nygard.md` — new. Nygard original template (Title, Status, Context, Decision, Consequences) and when to prefer it.
- `references/y-statements.md` — new. Y-statement one-liner format and when to prefer it for rapid capture.
- `references/examples.md` — new. Two-plus worked example ADRs (a lightweight one and a heavier one) and a worked supersede pair showing bidirectional links.
- `assets/adr-template.md` — new. Copyable MADR 4.0 starter with angle-bracket placeholders, following the repo's template-placeholder convention (ref: Q8).
- `references/README-index-template.md` (or an index section inside an existing reference) — new. A `docs/decisions/README.md` index starter the skill can copy/populate.

No modifications to existing files are required. The new skill is additive and self-contained (ref: Q5 — no prior ADR state to reconcile).

## Pattern Decisions

### Decision 1: Skill shape — thin wrapper vs. self-contained content skill

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Thin SKILL.md wrapper delegating to a `.claude/agents/` prompt (QRSPI pattern) | Consistent with the 10 existing repo skills | Adds an agent indirection unsuited to a standalone guidance skill; not how agentskills.io standalone skills are shaped; the ticket explicitly wants references/assets, not an agent |
| B | Self-contained content skill: body + `references/` + `assets/`, no agent | Matches agentskills.io standard the ticket mandates; keeps all ADR knowledge in one discoverable place; body stays lean by offloading to references | Introduces `assets/` and per-skill `scripts/`-style structure not yet used in this repo |

**Recommendation:** Option B
**Rationale:** The ticket mandates the agentskills.io structure and references/assets; the thin-wrapper/agent pattern is a QRSPI-orchestration idiom, not a general skill requirement (ref: Q1, ref: Q2). On-demand reference loading already exists (qrspi-work) and directly supports keeping the body under 500 lines (ref: Q2, ref: Q7).
**NEW PATTERN?** Yes — first skill in this repo to ship `assets/` and to be a standalone (non-wrapper) content skill (ref: Q8). Justified because existing wrapper skills serve workflow orchestration, whereas this skill is reusable authoring guidance that should match the external agentskills.io standard.

### Decision 2: Authoring path — hand-write vs. skill-creator

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Hand-write SKILL.md and references directly | Fewer moving parts | Violates the ticket criterion "Built using the Anthropic skill builder skill" and the user's standing directive to never ship a SKILL.md ad-hoc |
| B | Author and validate via the runtime `skill-creator` skill and its eval loop | Satisfies the ticket and the user directive; gets description-trigger tuning and structural validation for free | Depends on a runtime skill outside repo scope (ref: Q4) |

**Recommendation:** Option B
**Rationale:** Both the ticket and the user's global directive require skill-creator for any skill work (ref: Q4). The implementation slice must invoke skill-creator rather than hand-authoring.
**NEW PATTERN?** No — using the harness-provided skill-creator is the prescribed mechanism.

### Decision 3: Default ADR location and numbering

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Default to `docs/decisions/`, accept `docs/adr/`; sequential zero-padded `NNNN-kebab-case-title.md` | Matches adr-tools and log4brains; matches MADR docs; no repo collision (ref: Q5) | Subdirectory-by-domain splits make numbering local (a documented caveat) |
| B | Single flat directory only | Simplest numbering | Loses monorepo/domain flexibility the ticket calls for |

**Recommendation:** Option A
**Rationale:** Tooling compatibility is an explicit acceptance criterion and there is no existing ADR layout to conflict with (ref: Q5). The subdirectory caveat is encoded as guidance, not forbidden.
**NEW PATTERN?** No — these are external-standard conventions the skill documents; it does not create ADRs in this repo as part of the skill itself.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| SKILL.md body grows past the 500-line / 5000-token budget while covering full lifecycle + judgment calls | med | med | Keep body to procedures and pointers; move every template and worked example into `references/`; verify line/token count as a slice check (ref: Q2, ref: Q7) |
| skill-creator is unavailable or its interface differs from expectation at implementation time | low | high | skill-creator is listed as an available runtime skill; if invocation fails, STOP and report per the error-surfacing directive rather than hand-authoring (ref: Q4) |
| Description over- or under-triggers (fires on unrelated requests, or misses ADR requests) | med | med | Use skill-creator's description-optimization eval loop; include explicit "Use when/Trigger on" phrasing plus negative scope per repo idiom (ref: Q11) |
| `assets/` copy mechanism is novel in this repo and an agent may not reliably copy the starter | low | med | Mirror the proven `TEMPLATE_PATH` read-then-write idiom; give an explicit "read `assets/adr-template.md`, fill placeholders, write `docs/decisions/NNNN-...md`" instruction in the body (ref: Q8) |
| Existing QRSPI eval harness gives no signal for this skill, leaving it unvalidated | med | low | Rely on skill-creator's own eval loop and structural checks (frontmatter valid, required files present, body under budget); do not attempt to bolt the ADR skill onto the QRSPI suite (ref: Q10) |

## Open Questions

- OQ1: Exact skill `name`/directory — the ticket title is "writing Architecture Decision Records." Confirm the kebab-case name (e.g., `writing-architecture-decision-records` vs. a shorter `adr` / `writing-adrs`). Shorter names trigger and type more easily; the title is descriptive. Human to confirm.
- OQ2: Should the skill ship an optional `scripts/` helper (e.g., a next-ADR-number / index-regeneration script), or stay docs-only? The ticket lists `scripts/` as optional and emphasizes "no special tooling required to author"; default is docs-only unless the reviewer wants a helper.
- OQ3: Should the skill create an initial `docs/decisions/` directory and README index in this repo as a usage example, or only document how — given the skill's own scope is authoring guidance, not seeding this repo with ADRs?
