# Structure Outline — Create a new agent skill for writing Product Requirements Documents

**Design basis:** design.md @ 2026-06-04T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft

## New Types

These are not language types — this skill is freeform markdown + YAML. They are
the structural "shapes" the artifact must conform to, expressed as schemas.

- `SkillFrontmatter { name: string ("writing-prds", == directory name), description: string (two-part: what-it-does + "Use when…" trigger phrasings), allowed-tools: string ("Read, Write") }` (ref: design §Delta, Decision 1)
- `PrdHeader { sourceLine: string, timestamp: ISO-8601, status: enum["Draft","In Review","Approved"] }` — metadata block emitted at top of every produced PRD (ref: design §Desired End State, Risk Register row 4)
- `PrdSection` — the six mandatory core sections: `Title & Metadata`, `Problem Statement`, `Goals & Non-Goals`, `Solution Overview`, `Success Metrics`, `Scope/Milestones/Open Questions` (ref: design §Desired End State)
- `SmartMetric { metric: string, baseline: value, target: value, timeframe: string }` — table row format encoded as a reference example (ref: design §Desired End State)
- `UserStory { as: role, want: capability, soThat: outcome, acceptance: GivenWhenThen[] }` — reference format block (ref: design §Desired End State)

## Modified Types

- none — no existing file is modified; the skill router auto-discovers `.claude/skills/*/SKILL.md` (ref: design §Delta "Modified files: none")

## Contracts

These are the interfaces between the two files of the skill (and between the
skill and its runtime). Both files ship in one slice, so these are intra-slice
coupling contracts the author must honor.

- `SKILL.md frontmatter` — must declare `name: writing-prds` (matching the directory name), a `description` carrying explicit trigger phrasings ("write a PRD", "product requirements document for…") plus a "Use when…" clause, and `allowed-tools: Read, Write` (ref: Q3, Q4, Q5; Decision 1)
- `body → references/prd-template.md` — the SKILL.md body references the template by relative path and instructs the agent to read it on demand at draft time; the body summarizes/links rather than inlining the full template (ref: Q7; Decision 2)
- `formatSelection(context): "lean" | "expanded"` — prose rule in the body, a model decision (not a code branch); both skeletons live in the template and the body states when to expand (ref: Q6; Decision 3)
- `requiredSectionGate(prd): pass | fail` — prompt-level checklist that every core section, especially Goals & Non-Goals, is emitted with a "None" fallback; enforced by a solution-blind self-review step, not tooling (ref: Q9, Q10; Decision 4)
- `clarifyThrottle` — when problem evidence is missing the body asks ≤2 clarifying questions at a time and redirects premature solution detail back to the problem (ref: Q8; Decision 4)

## Slice 1: Author the writing-prds skill (SKILL.md + references template)

**Goal:** A complete, auto-discoverable `writing-prds` skill that, when invoked,
runs a problem-first guided conversation and produces a PRD with all six core
sections, a metadata header, SMART metrics, user stories, and lean/expanded
format selection — pulling its layout from the bundled reference template.

**Files touched:**

- ✨ `.claude/skills/writing-prds/SKILL.md` — self-contained inline author (no `.claude/agents/` sibling). Frontmatter per the `SkillFrontmatter` contract; body holds the problem-first conversation discipline (≤2-question throttle + solution redirect), lean-vs-expanded format-selection rules, the required-section checklist with "None" fallback for non-goals, the reference-by-path link to the template, and the solution-blind self-review gate (ref: design §Delta; Decisions 1, 3, 4)
- ✨ `.claude/skills/writing-prds/references/prd-template.md` — default lean six-section skeleton + expanded sections (Personas, Technical Considerations, Dependencies, Launch Plan), the SMART metrics table format, the "As a / I want / So that" + Given/When/Then user-story block, and the PRD metadata-header convention (ref: design §Delta; Decision 2)

**Verification:**

- [ ] Invoke `skill-creator` against the authored skill (authoring-time process gate per OQ1 / Risk Register row 3) and apply its eval-loop feedback
- [ ] Manual end-to-end: invoke `writing-prds` and confirm it (a) asks ≤2 clarifying questions and redirects premature solution detail, (b) emits all six core sections including a Goals & Non-Goals section with a "None" fallback, (c) produces both a lean run and, when prompted, an expanded run, (d) renders a SMART metrics table with baseline/target/timeframe and at least one "As a / I want / So that" + Given/When/Then story, (e) writes a PRD header with source line, ISO-8601 timestamp, and Status marker
- [ ] Confirm the SKILL.md `description` fires the skill on a natural request ("write a PRD for X") (ref: Q4)
- [ ] Author self-check: SKILL.md body ≤ 500 lines / 5000 tokens (unenforced by tooling — manual count) (ref: Q7, Q12)
- [ ] Confirm directory name `writing-prds` == frontmatter `name`, and the body's reference path to `references/prd-template.md` resolves (ref: Q2)

**Context cost:** M
**Depends on:** none

---

## Unverified Assumptions

- **OQ1 — skill-creator gate is a process step, not in-repo tooling.** The "Built using the Anthropic skill builder skill" criterion targets a global, out-of-repo asset (NOT FOUND in-repo). This structure assumes it is satisfied by *invoking* `skill-creator` at authoring time. If instead it is purely an output-conformance gate, the verification step changes. Needs human confirmation before planning (ref: design OQ1, Risk Register row 3).
- **OQ2 — PRD `version` field + changelog vocabulary is undecided.** The ticket asks for both, but no in-repo template carries either. The `PrdHeader` type above includes only source/timestamp/Status; whether to add `version` and a changelog section (a convention that does not yet exist in the repo) is unresolved (ref: design OQ2, Q13).
- **OQ3 — registration scope is undecided.** Whether the skill should be listed in `.claude/CLAUDE.md`'s "Available skills" block (which would make "Modified files: none" inaccurate and add a second file to Slice 1) or remain auto-discovery-only is unconfirmed (ref: design OQ3).
- **PRD Status vocabulary ("Draft / In Review / Approved") matches no existing template exactly.** Adopted because the PRD is a skill-owned artifact, but the exact enum is an assumption, not derived from a concrete in-repo source (ref: design Risk Register row 4).
- **Dual lean/expanded output format is a NEW pattern with no in-repo precedent.** Encoded as prose rules + two skeletons (Decision 3). Its effectiveness cannot be mapped to an existing verified pattern and rests on the model following prose rules (ref: design Decision 3, Q6).
