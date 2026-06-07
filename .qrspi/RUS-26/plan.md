# Implementation Plan — Create a new agent skill for writing Product Requirements Documents

**Structure basis:** structure.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total steps:** 14

## Slice 1: Author the writing-prds skill (SKILL.md + references template)

### Setup

1. ✨ Create `.claude/skills/writing-prds/references/prd-template.md` — empty file scaffold for the PRD layout asset (per `body → references/prd-template.md` contract; directory `references/` mirrors the `qrspi-work` overflow pattern). This file is authored first because the SKILL.md body references it by relative path.

### Core Logic — references/prd-template.md (the layout source-of-truth)

2. ⚠️ Modify `.claude/skills/writing-prds/references/prd-template.md` — add the PRD metadata-header convention block per `PrdHeader` type: `sourceLine: string`, `timestamp: ISO-8601`, `status: enum["Draft","In Review","Approved"]` (ref: structure `PrdHeader`; design §Desired End State, Risk Register row 4).
   - **Current:** empty file
   - **After:** header block with `**Source:**`, `**Generated:** <ISO-8601>`, `**Status:** Draft | In Review | Approved` fields
3. ⚠️ Modify `.claude/skills/writing-prds/references/prd-template.md` — add the default **lean** six-section skeleton per `PrdSection` type: `Title & Metadata`, `Problem Statement`, `Goals & Non-Goals`, `Solution Overview`, `Success Metrics`, `Scope/Milestones/Open Questions` (ref: structure `PrdSection`; design Decision 2).
   - **Current:** file with header block only
   - **After:** header block + lean six-section skeleton with section headings and one-line guidance each
4. ⚠️ Modify `.claude/skills/writing-prds/references/prd-template.md` — add the **expanded** sections appended to the lean skeleton: `Personas`, `Technical Considerations`, `Dependencies`, `Launch Plan` (ref: design Decision 3 dual lean/expanded format; structure Slice 1 files-touched).
   - **Current:** lean six-section skeleton
   - **After:** lean skeleton + expanded sections block clearly marked as "expanded format only"
5. ⚠️ Modify `.claude/skills/writing-prds/references/prd-template.md` — add the SMART metrics table format per `SmartMetric` type: columns `metric | baseline | target | timeframe` with one example row (ref: structure `SmartMetric`; design §Desired End State).
   - **Current:** lean + expanded skeletons
   - **After:** adds a SMART metrics markdown table reference example under Success Metrics
6. ⚠️ Modify `.claude/skills/writing-prds/references/prd-template.md` — add the user-story reference block per `UserStory` type: `As a <role> / I want <capability> / So that <outcome>` plus `Given/When/Then` acceptance-criteria format with at least one filled example (ref: structure `UserStory`; design §Desired End State, Q10).
   - **Current:** template with skeletons + metrics table
   - **After:** adds "As a / I want / So that" + Given/When/Then user-story format block

### Core Logic — SKILL.md (the inline author)

7. ✨ Create `.claude/skills/writing-prds/SKILL.md` — author the YAML frontmatter per `SkillFrontmatter` type and the `SKILL.md frontmatter` contract: `name: writing-prds` (== directory name), two-part `description` (what-it-does + "Use when…" clause with explicit trigger phrasings "write a PRD", "product requirements document for…"), `allowed-tools: Read, Write` (ref: structure `SkillFrontmatter` + contract; design Decision 1, Q3/Q4/Q5).
8. ⚠️ Modify `.claude/skills/writing-prds/SKILL.md` — add the problem-first conversation discipline body section per `clarifyThrottle` contract: ask ≤2 clarifying questions at a time when problem evidence is missing, and redirect premature solution detail back to the problem (ref: structure `clarifyThrottle`; design Decision 4, Q8).
   - **Current:** SKILL.md with frontmatter only
   - **After:** frontmatter + "Problem-first conversation" body section encoding the ≤2-question throttle and solution-redirect rule
9. ⚠️ Modify `.claude/skills/writing-prds/SKILL.md` — add the reference-by-path instruction per `body → references/prd-template.md` contract: instruct the agent to read `references/prd-template.md` on demand at draft time; summarize/link rather than inline the full template (ref: structure contract; design Decision 2, Q7).
   - **Current:** frontmatter + problem-first section
   - **After:** adds a "Draft from the template" body section linking `references/prd-template.md` by relative path
10. ⚠️ Modify `.claude/skills/writing-prds/SKILL.md` — add the lean-vs-expanded `formatSelection(context): "lean" | "expanded"` prose rule per contract: state when to default to lean and when to expand; both skeletons live in the template, the choice is a model decision not a code branch (ref: structure `formatSelection`; design Decision 3, Q6).
    - **Current:** SKILL.md through the template-link section
    - **After:** adds a "Format selection" body section with prose rules for lean vs. expanded
11. ⚠️ Modify `.claude/skills/writing-prds/SKILL.md` — add the `requiredSectionGate(prd): pass | fail` checklist per contract: every core section must be emitted, especially Goals & Non-Goals with a "None" fallback; enforced by a solution-blind self-review step (ref: structure `requiredSectionGate`; design Decision 4, Q9/Q10).
    - **Current:** SKILL.md through the format-selection section
    - **After:** adds a "Required-section checklist + solution-blind self-review gate" body section with the non-goals "None" fallback

### Verify Slice 1

12. **Checkpoint:** `test -f .claude/skills/writing-prds/SKILL.md && test -f .claude/skills/writing-prds/references/prd-template.md && echo OK`
    - [ ] Both files exist
    - [ ] Directory name `writing-prds` == frontmatter `name` (ref: structure verification, Q2)
13. **Checkpoint:** `grep -n 'references/prd-template.md' .claude/skills/writing-prds/SKILL.md` and confirm the relative path resolves
    - [ ] Body references the template by relative path and the path resolves (ref: structure verification, Q2)
    - [ ] `allowed-tools: Read, Write` present in frontmatter (ref: `SkillFrontmatter` contract)
14. **Checkpoint:** manual + authoring-time process gate (no in-repo tooling — verification is manual e2e per design Q11)
    - [ ] Invoke `skill-creator` against the authored skill and apply eval-loop feedback (OQ1 / Risk Register row 3)
    - [ ] Manual e2e: skill (a) asks ≤2 clarifying questions and redirects premature solution detail, (b) emits all six core sections incl. Goals & Non-Goals with a "None" fallback, (c) produces a lean run and, when prompted, an expanded run, (d) renders a SMART metrics table (baseline/target/timeframe) + at least one "As a / I want / So that" + Given/When/Then story, (e) writes a PRD header with source line, ISO-8601 timestamp, Status marker
    - [ ] `description` fires the skill on a natural request ("write a PRD for X") (ref: Q4)
    - [ ] Author self-check: SKILL.md body ≤ 500 lines / 5000 tokens (manual count — unenforced by tooling) (ref: Q7, Q12)

---

## Rollback Notes

- Steps 1–11 create only two new files under `.claude/skills/writing-prds/`. To roll back: `rm -rf .claude/skills/writing-prds/`. No existing files are modified (structure §Modified Types: none), so removal fully reverts the change with no residual state.
- No DB migrations, config changes, or destructive operations are involved.

---

## Blocking Open Questions (carried from structure — confirm before/at implementation)

- **OQ1** — Whether the "Built using the Anthropic skill builder skill" criterion is a process gate (invoke `skill-creator`) or an output-conformance gate. Step 14 assumes the process-gate reading; if it is output-only, the `skill-creator` invocation item is dropped.
- **OQ2** — Whether the PRD header gains a `version` field + changelog section. Steps 2 and 3 currently encode only source/timestamp/Status per `PrdHeader`; adding `version`/changelog would extend step 2.
- **OQ3** — Whether to register the skill in `.claude/CLAUDE.md`'s "Available skills" block. If yes, this adds one ⚠️ Modify step to Slice 1 and makes "Modified files: none" inaccurate.
