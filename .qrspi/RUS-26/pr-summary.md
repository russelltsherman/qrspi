# PR: RUS-26 Add writing-prds skill for authoring PRDs

**Ticket:** RUS-26
**Design:** design.md @ 2026-06-04T00:00:00Z
**Structure:** structure.md @ 2026-06-06T00:00:00Z

## Summary

Adds a new self-contained `writing-prds` agent skill that guides an agent through a
problem-first conversation and produces a structured Product Requirements Document. The
skill ships as two files: a `SKILL.md` body (80 lines, inline-author style like
`qrspi-ticket`, no `.claude/agents/` wrapper) and a `references/prd-template.md` layout
asset holding the lean/expanded skeletons, SMART-metrics table format, and user-story
block. No existing files were modified — the skill router auto-discovers
`.claude/skills/*/SKILL.md`. Reviewers should focus on (a) whether the prompt-level
enforcement of problem-first discipline and mandatory non-goals is strong enough, and
(b) the three open items below, all of which are manual/authoring-time gates the
deterministic implement agent could not execute.

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: agentskills.io directory structure + valid frontmatter | `.claude/skills/writing-prds/SKILL.md` (frontmatter `name`/`description`/`allowed-tools`) | `test -f SKILL.md`; `grep '^name:' SKILL.md` == dir name; `grep 'allowed-tools:'` — pass |
| AC2: Built using the Anthropic skill builder skill | (authoring-time process gate — out-of-repo `skill-creator`) | NOT RUN — manual gate, see Open Items / OQ1 |
| AC3: Body under 500 lines / 5000 tokens | `SKILL.md` (80 lines) | `wc -l SKILL.md` → 80 — pass |
| AC4: Detailed reference material in `references/` | `.claude/skills/writing-prds/references/prd-template.md` | `test -f references/prd-template.md`; `grep 'references/prd-template.md' SKILL.md` resolves — pass |
| AC5: Enforces problem-first structure | `SKILL.md` "Core discipline: problem before solution" (≤2-Q throttle + solution redirect) | Manual e2e — NOT RUN (see Open Items) |
| AC6: Default template with all six core sections | `references/prd-template.md` lean skeleton | Manual e2e — NOT RUN; structure present in template (verified by read) |
| AC7: SMART metrics with baseline/target/timeframe | `references/prd-template.md` "SMART metrics table format" | Manual e2e — NOT RUN; table format present |
| AC8: Mandatory non-goals in every PRD | `SKILL.md` required-section gate + `prd-template.md` "None" fallback | Manual e2e — NOT RUN; gate authored |
| AC9: User stories As a/I want/So that + Given/When/Then | `references/prd-template.md` user-story reference block | Manual e2e — NOT RUN; block present |
| AC10: Asks clarifying questions when evidence missing | `SKILL.md` ≤2-question throttle rule | Manual e2e — NOT RUN |
| AC11: Lean one-pager + expanded formats + when to expand | `SKILL.md` "Format selection" + `prd-template.md` two skeletons | Manual e2e — NOT RUN; both skeletons + selection rule present |

## Changes by Slice

### Slice 1: Author the writing-prds skill (SKILL.md + references template)

| File | Change | Lines |
|------|--------|-------|
| `.claude/skills/writing-prds/SKILL.md` | ✨ new | +80 |
| `.claude/skills/writing-prds/references/prd-template.md` | ✨ new | +121 |

### Workflow artifacts (stacked design/plan commits, not part of slice 1)

| File | Change | Lines |
|------|--------|-------|
| `.qrspi/RUS-26/questions.md` | ✨ new | +49 |
| `.qrspi/RUS-26/research.md` | ✨ new | +383 |
| `.qrspi/RUS-26/design.md` | ✨ new | +107 |
| `.qrspi/RUS-26/structure.md` | ✨ new | +65 |
| `.qrspi/RUS-26/plan.md` | ✨ new | +75 |
| `.qrspi/RUS-26/worktree.md` | ✨ new | +48 |
| `.qrspi/RUS-26/impl-log.md` | ✨ new | +30 |

## Testing Summary

- [x] Slice 1: file existence — `test -f .claude/skills/writing-prds/SKILL.md && test -f .../references/prd-template.md` — both exist, pass
- [x] Slice 1: name match — `grep '^name:' SKILL.md` → `name: writing-prds` == directory name — pass
- [x] Slice 1: reference path resolves — `grep 'references/prd-template.md' SKILL.md` — present and resolves, pass
- [x] Slice 1: frontmatter tools — `grep 'allowed-tools:' SKILL.md` → `allowed-tools: Read, Write` — pass
- [x] Slice 1: body cap self-check — `wc -l SKILL.md` → 80 lines (≤500-line / ≤5000-token cap) — pass
- [ ] Manual e2e: invoke `writing-prds`, confirm ≤2 clarifying Qs + solution redirect, all six sections incl. Goals & Non-Goals "None" fallback, lean + expanded runs, SMART table, As-a/Given-When-Then story, PRD header — NOT RUN (no interactive HITL available to implement agent)
- [ ] Manual: `description` fires on a natural "write a PRD for X" request — NOT RUN
- [ ] `skill-creator` eval loop applied — NOT RUN (out-of-repo global asset, OQ1)

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| `SkillFrontmatter` | `name`, `description`, `allowed-tools` only | Exactly those three fields | Matched contract verbatim; existing repo skills (e.g. `qrspi-ticket`) also carry `command`/`argument-hint`, intentionally omitted to match the contract. Flagged for the router/future slice in case those keys are expected. |
| Verification steps 12–13 (structural) | pass | pass | runnable checkpoints all pass |
| Verification step 14 (skill-creator eval + manual e2e) | run | NOT run | plan marks it "manual + authoring-time process gate (no in-repo tooling)"; requires interactive HITL unavailable to the deterministic implement agent |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| SKILL.md body exceeds 500-line / 5000-token cap (no validator) | mitigated — body is 80 lines; bulky template pushed to `references/` | Trim body / move more detail to `references/` |
| Problem-first / non-goals enforcement is prompt-level only; model may skip | accepted — reuses `qrspi-ticket` mechanisms (≤2-Q throttle, solution redirect, "None" fallback, self-review gate); unverified by manual e2e | Strengthen prompt wording or add self-review steps |
| "Built using the Anthropic skill builder" unverifiable in-repo | open/accepted — treated as authoring-time process step; NOT executed (OQ1) | N/A — process gate, no code rollback |
| PRD Status vocabulary ("Draft/In Review/Approved") matches no existing template | accepted — adopted as skill-owned artifact vocabulary; header shape consistent with convention | Adjust enum in `prd-template.md` |
| `description` trigger wording may fail to fire skill | accepted — follows `qrspi-work` richest-description pattern with explicit trigger phrasings; unverified by manual fire test | Revise `description` trigger phrasings |
| Whole-feature rollback | n/a — two new files, no existing file modified | `git rm -r .claude/skills/writing-prds/` |

## Open Items

- **OQ1 (manual gate):** Invoke the global `skill-creator` eval loop against the authored skill and apply feedback. Not runnable by the implement agent. Blocks AC2 verification.
- **Manual e2e (HITL):** Confirm at runtime — ≤2 clarifying questions + solution redirect, all six core sections incl. Goals & Non-Goals "None" fallback, lean + expanded runs, SMART table, As-a/Given-When-Then story, PRD header, and that `description` fires on "write a PRD for X". Covers ACs 5–11.
- **OQ2:** PRD `version` field + changelog were requested in the ticket but not added — header carries only Source/Generated/Status (no in-repo precedent for a changelog). Confirm desired metadata vocabulary.
- **OQ3:** Skill left auto-discovery-only; NOT registered in `.claude/CLAUDE.md` "Available skills". Confirm whether it should be listed there (would make "Modified files: none" inaccurate).
- **Dual lean/expanded format is a NEW pattern** with no in-repo precedent (design Decision 3) — effectiveness rests on the model following prose rules; worth scrutiny in review.
