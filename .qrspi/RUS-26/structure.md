# Structure Outline — Create a new agent skill called writing Product Requirements Documents

**Design basis:** design.md @ 2026-05-31
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## New Types

This is a content/skill-authoring deliverable, not code. The "types" are the file artifacts and their required structural shape (contracts).

- `SkillFrontmatter { name: string, description: string, command: string, argument-hint: string, allowed-tools: string }` — valid YAML frontmatter on `.claude/skills/writing-prds/SKILL.md` (ref: design §Delta, Decision 1).
- `PrdTemplate { sections: [Title&Metadata, ProblemStatement, Goals&Non-Goals, SolutionOverview, SuccessMetrics, Scope&Milestones&OpenQuestions] }` — the canonical 6-section lean PRD, with mandatory Non-Goals and the SMART metrics table (ref: design §Desired End State).
- `SmartMetricRow { metric, baseline, target, timeframe, measurementMethod }` — the table contract embedded in the template; rows categorized primary / secondary / guardrail.
- `UserStory { asA: persona, iWant: action, soThat: benefit, acceptanceCriteria: GivenWhenThen[] }` — story + acceptance-criteria contract in the template.
- `EvalCase { id, name, prompt, context.files, assertions[] }` — a new case added to `evals/suite.json` (ref: design §Delta).

## Modified Types

- `evals/suite.json` — add one `EvalCase` (or two) for `writing-prds`, asserting on output structure and SKILL.md size (ref: design §Delta).
- `scripts/grade.py` — add a check function ONLY if existing checks (`output_file_exists`, `has_section`, `line_count`, `no_solution_language`) cannot express a needed assertion (ref: design §Delta, Decision 3).
- `evals/fixtures/` — add a PRD-request fixture only if no existing fixture suits (ref: design §Delta, OQ3).

## Contracts

- `SKILL.md` body MUST stay under 500 lines / 5000 tokens — verified by `line_count('SKILL.md', 500)` (ref: design Decision 2, Risk row 2).
- `SKILL.md` MUST enforce problem-first ordering: Solution Overview cannot be authored until the Problem Statement answers all four required questions (ref: design Decision 3).
- `SKILL.md` MUST require an explicit Non-Goals section in every generated PRD and refuse to finalize without it (ref: design §Desired End State).
- `references/prd-template.md` MUST contain all six core sections, the `| Metric | Baseline | Target | Timeframe | Measurement Method |` table, and the As-a/I-want/So-that + Given/When/Then story format.
- `references/expanded-format.md` MUST define when-to-expand triggers and the additional sections (Personas, Technical Considerations, Dependencies, Launch Plan, Timeline/Milestones, Open Questions table).
- Skill is self-contained — NO companion `.claude/agents/writing-prds.md` is created (ref: design Decision 1).
- Directory name == frontmatter `name` == `command` (minus `/`) (ref: design §Current State, OQ1).

## Slice 1: Author the writing-prds skill (SKILL.md + references)

**Goal:** A complete, self-contained, discoverable PRD-authoring skill — SKILL.md plus its two reference files — that conforms to repo layout and frontmatter conventions and encodes every required convention (problem-first, mandatory non-goals, SMART metrics, user-story format, lean-default-with-expand). Validation (invoking skill-creator if used, line/frontmatter check) is the final step of this slice per structure rule 9.

**Files touched:**

- ✨ `.claude/skills/writing-prds/SKILL.md` — lean procedure: trigger, conversational evidence gate, problem-first ordering, default-vs-expanded selection, finalize checklist (mandatory non-goals).
- ✨ `.claude/skills/writing-prds/references/prd-template.md` — canonical 6-section PRD template with SMART metrics table, mandatory non-goals, and user-story/acceptance-criteria format.
- ✨ `.claude/skills/writing-prds/references/expanded-format.md` — when-to-expand criteria and the additional expanded sections.

**Verification:**
- [ ] `ls .claude/skills/writing-prds/SKILL.md .claude/skills/writing-prds/references/prd-template.md .claude/skills/writing-prds/references/expanded-format.md` all exist.
- [ ] Frontmatter parses and contains `name: writing-prds`, `description`, `command`, `argument-hint`, `allowed-tools` (matches `qrspi-ticket` shape).
- [ ] `wc -l .claude/skills/writing-prds/SKILL.md` ≤ 500 lines (and token estimate < 5000).
- [ ] `prd-template.md` contains all six section headers, the SMART metrics table header row, a Non-Goals header, and the As a / I want / So that + Given/When/Then format.
- [ ] SKILL.md body states the problem-first gate and the mandatory-non-goals finalize check.
- [ ] `expanded-format.md` lists expansion triggers and the additional sections.

**Context cost:** M
**Depends on:** none

## Slice 2: Wire and run the eval gate

**Goal:** Behavioral verification of the skill via the in-repo eval harness — a new case in `evals/suite.json` that exercises the PRD skill and asserts on output structure and SKILL.md size, graded successfully by `scripts/grade.py`, run via `run_eval.py`/`run_loop.sh`.

**Files touched:**

- ⚠️ `evals/suite.json` — add `writing-prds` case(s) with assertions: `output_file_exists`, `has_section` (e.g. Non-Goals, Success Metrics, Problem Statement), `line_count('SKILL.md', 500)`, and problem-before-solution ordering.
- ⚠️ `scripts/grade.py` — add a check function ONLY if a needed assertion (e.g. "problem section precedes solution section") is not expressible with existing checks.
- ✨ `evals/fixtures/<prd-request>.md` — add a fixture PRD-request prompt only if no existing fixture suits (resolve OQ3).

**Verification:**
- [ ] `python scripts/run_eval.py` (or `run_loop.sh`) runs the new case without harness error.
- [ ] `scripts/grade.py` scores the new case; required assertions pass.
- [ ] Any new `grade.py` check function has its behavior covered (manual or fixture).

**Context cost:** M
**Depends on:** Slice 1

---

## Unverified Assumptions

- The external Anthropic skill-creator skill's exact output contract is unknown from repo facts (ref: design Q2, OQ2). Implementation must conform skill-creator output to the in-repo layout; if skill-creator is unavailable, the skill is authored directly to the same layout. This does not block Slice 1 but affects HOW files are produced.
- It is assumed `run_eval.py` can execute a non-QRSPI-phase skill case. The harness was built for QRSPI phases (case `phase` field); whether a generic skill case runs cleanly is unverified (ref: design OQ4). If the harness assumes a `phase`, Slice 2 may need a phase value or a minimal harness accommodation — surface as a blocker if so.
- The skill `command`/`name` (`writing-prds` vs `prd` vs `write-prd`) is assumed `writing-prds` pending OQ1 confirmation. A rename is cheap (dir + two frontmatter lines) if changed.
- Whether passing evals is a hard done-gate (OQ4) is assumed yes for diligence; if the harness cannot run the case, Slice 2's deliverable degrades to the suite.json case definition plus a documented manual verification, not a green run.
