# Implementation Plan — Create a new agent skill called writing Product Requirements Documents

**Structure basis:** structure.md @ 2026-05-31
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft
**Total steps:** 23

## Slice 1: Author the writing-prds skill (SKILL.md + references)

### Setup

1. ✨ Create directory `.claude/skills/writing-prds/references/` (the skill dir and its references subdir) — mirrors `qrspi-work` overflow layout (structure §Contracts).
2. If using the external skill-creator skill: invoke it to scaffold the skill, then conform its output to the in-repo layout (`.claude/skills/writing-prds/SKILL.md` + `references/`). If skill-creator is unavailable, author the files directly to the same layout (structure §Unverified Assumptions, design Decision 1).

### Core Logic

3. ✨ Create `.claude/skills/writing-prds/SKILL.md` — author frontmatter per `SkillFrontmatter` contract:
   - `name: writing-prds`, `description:` (single line naming PRD / Product Requirements Document triggers), `command: /writing-prds`, `argument-hint:` (e.g. `<feature or initiative>`), `allowed-tools: Read, Write` (plus `Glob, Grep` if it must locate related artifacts) — match `qrspi-ticket` frontmatter shape (structure §New Types).
4. ✨ In `SKILL.md` body — write the conversational evidence gate: restate understanding, ask the most important unanswered question first, ≤2 questions at once, continue until the Problem Statement can answer all four questions (what / who / evidence / why now). Copy the `qrspi-ticket` gating pattern (design Decision 3).
5. ✨ In `SKILL.md` body — write the problem-first ordering rule: the agent MUST NOT author Solution Overview until the Problem Statement is complete and evidence-backed; if evidence is missing, ask rather than invent (structure §Contracts).
6. ✨ In `SKILL.md` body — write the default-vs-expanded selection block: default to the lean 6-section one-pager; list explicit "expand when X" triggers; point to `references/expanded-format.md` for the scale-up (design Decision 4).
7. ✨ In `SKILL.md` body — point to `references/prd-template.md` as the canonical template to follow (lazy-load, like `qrspi-work` reads its reference) (design Decision 2).
8. ✨ In `SKILL.md` body — write the finalize checklist: PRD MUST contain an explicit Non-Goals section (refuse to finalize without it); metrics use the SMART baseline/target/timeframe table; user stories use the standard format; include a changelog. Add a self-review checkpoint mirroring `qrspi-ticket` (structure §Contracts).
9. ✨ Create `.claude/skills/writing-prds/references/prd-template.md` — the canonical lean 6-section template:
   1. Title & Metadata (name, author, date, status Draft/In Review/Approved, version)
   2. Problem Statement (the four questions; 3-5 sentences; link out for evidence)
   3. Goals & Non-Goals (outcome-oriented goals with target+timeframe; mandatory non-goals marked deferred vs permanently out)
   4. Solution Overview (approach, key features, user flows)
   5. Success Metrics (SMART; primary/secondary/guardrail; embed `| Metric | Baseline | Target | Timeframe | Measurement Method |`)
   6. Scope, Milestones & Open Questions (in/out scope with WHY-excluded, phased plan, open questions)
   — plus a User Stories block (As a / I want / So that + Given/When/Then) and a changelog footer (structure §New Types, §Contracts).
10. ✨ Create `.claude/skills/writing-prds/references/expanded-format.md` — when-to-expand triggers (cross-team, high-risk, multi-quarter, regulatory) and the additional sections: Target Audience & Personas, Technical Considerations, Dependencies, Launch Plan, Timeline & Milestones (per-phase deliverables/dates/dependencies/go-no-go), and an Open Questions table (question/owner/target date/impact) (structure §Contracts).

### Tests

11. Run frontmatter sanity check: confirm `SKILL.md` YAML frontmatter parses and contains the five required keys.
    - **Expected:** keys `name, description, command, argument-hint, allowed-tools` present; `name` == `writing-prds`.
12. Run content checks on `references/prd-template.md`: grep for the six section headers, the SMART table header row, a `Non-Goals` header, `As a` / `Given` story markers.
    - **Expected:** all present.

### Verify Slice 1

13. **Checkpoint:** `ls .claude/skills/writing-prds/SKILL.md .claude/skills/writing-prds/references/prd-template.md .claude/skills/writing-prds/references/expanded-format.md && wc -l .claude/skills/writing-prds/SKILL.md`
    - [ ] All three files exist.
    - [ ] `SKILL.md` ≤ 500 lines (token estimate < 5000).
    - [ ] Frontmatter valid with `name: writing-prds`.
    - [ ] `prd-template.md` has all six sections + SMART table + mandatory Non-Goals + user-story format.
    - [ ] `SKILL.md` states problem-first gate + mandatory-non-goals finalize check + default-vs-expanded selection.
    - [ ] `expanded-format.md` lists expansion triggers + additional sections.

---

## Slice 2: Wire and run the eval gate

### Setup

14. ⚠️ Read `evals/suite.json` to learn the exact case schema (`id, name, phase, prompt, context.files, assertions[]`) and the assertion `check` grammar before editing.
15. ✨ Create `evals/fixtures/prd_request_lean.md` — a fixture prompt describing a small feature needing a lean PRD (with enough problem evidence to avoid the clarifying-question gate) — only if no existing fixture suits (resolve OQ3) (structure §Modified Types).

### Core Logic

16. ⚠️ Modify `evals/suite.json` — add a `writing-prds` case:
    - **Current:** cases array ends at the last QRSPI-phase case.
    - **After:** append `{ id, name: "prd_happy_path", phase: "writing-prds" (or harness-required value), prompt, context.files: ["fixtures/prd_request_lean.md"], assertions: [...] }`.
17. ⚠️ In the new case's `assertions` — add: `output_file_exists('prd.md')`, `has_section('prd.md', 'Problem Statement')`, `has_section('prd.md', 'Non-Goals')` (or 'Goals & Non-Goals'), `has_section('prd.md', 'Success Metrics')`, and a skill-size guard `line_count('SKILL.md', 500)` (reuse existing `grade.py` checks — design Decision 3, structure §Contracts).
18. ⚠️ Modify `scripts/grade.py` — add a check function ONLY IF a needed assertion (e.g. "Problem Statement section appears before Solution Overview") is not expressible with existing checks.
    - **Current:** check functions end at `pr_title_under_limit`.
    - **After:** add `problem_before_solution(filename, result) -> tuple[bool,str]` returning whether the Problem Statement heading index precedes the Solution Overview heading index. Register it in the dispatch if `grade.py` uses an explicit registry. Skip this step entirely if `has_section` ordering is deemed sufficient.

### Tests

19. Run: `python scripts/run_eval.py --skill .claude/skills/writing-prds --suite evals/suite.json` (consult `run_eval.py --help` / `run_loop.sh` for exact flags).
    - **Expected:** the new case executes without harness error and produces a `prd.md` output.
20. Run: `python scripts/grade.py` against the produced results.
    - **Expected:** required assertions pass; report renders the new case.

### Verify Slice 2

21. **Checkpoint:** run the eval loop for the new case and inspect the grade report.
    - [ ] New case runs without harness error.
    - [ ] `output_file_exists('prd.md')` and the `has_section` assertions pass.
    - [ ] `line_count('SKILL.md', 500)` passes.
    - [ ] If `problem_before_solution` was added, it passes and has been exercised.

22. **Checkpoint (blocker handling):** if `run_eval.py` cannot execute a non-QRSPI-phase skill (structure §Unverified Assumptions), STOP and report the exact harness error rather than working around it; degrade the deliverable to the suite.json case definition + documented manual verification, and note it in impl-log.

23. Record outcomes, any harness limitations, and notes-for-next-session in `impl-log.md`.

---

## Rollback Notes

- Step 16-18 (eval wiring): `evals/suite.json` and `scripts/grade.py` are additive; revert by removing the appended case and the added check function. No data migration, no destructive ops.
- Step 1-10 (skill files): all new files under `.claude/skills/writing-prds/`; revert by deleting the directory. No existing files modified in Slice 1.
- No DB migrations, no config changes to shared infrastructure.
