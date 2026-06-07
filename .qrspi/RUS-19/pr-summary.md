# PR: RUS-19 — Add `atmos` CLI agent skill + acceptance checker

**Ticket:** RUS-19
**Design:** design.md @ 2026-06-04T00:00:00Z
**Structure:** structure.md @ 2026-06-06T00:00:00Z

## Summary

Adds a new self-contained `atmos` agent skill at `.claude/skills/atmos/` that
guides Cloud Posse atmos CLI usage across the full component lifecycle, plus a
stdlib-only Python acceptance checker (`scripts/atmos_skill_check.py`) that
mechanically enforces three of the skill's acceptance criteria (frontmatter
shape, body line/token budget, presence of the five reference docs). The skill
follows the in-repo self-contained precedent (`qrspi-ticket`/`qrspi-work`): no
`.claude/agents/` wrapper, with depth offloaded to five `references/*.md` files
cited by backticked prose pointers to keep the body under the 500-line / 5000-token
budget. Reviewers should focus on (1) atmos factual accuracy in the reference docs
(flags, YAML functions, inheritance — see Risks) and (2) the checker's failure-mode
coverage. Note one process deviation: the `skill-creator` eval/triggering loop was
applied as authoring guidance but its interactive subagent eval was not run (no
human at the viewer in an autonomous slice) — the deterministic checker is the gate.

## Acceptance Criteria Mapping

Acceptance criteria are taken from design.md §Desired End State (the Linear ticket is
hidden from the QRSPI design phase, so the design encodes the ticket's ACs).

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: Valid frontmatter, in-repo 5-field schema, `name`==dir, agentskills.io `name`/`description` core present | `.claude/skills/atmos/SKILL.md` (frontmatter); `scripts/atmos_skill_check.py:check_skill` (checks a,b) | `scripts/atmos_skill_check_test.py` (missing-field, name-mismatch cases); `python3 scripts/atmos_skill_check.py .claude/skills/atmos` → exit 0 |
| AC2: Body under 500 lines / ~5000 tokens | `.claude/skills/atmos/SKILL.md` (220 lines incl. frontmatter; ~213 body lines / ~2606 tokens) | `scripts/atmos_skill_check_test.py` (over-budget case); CLI exit 0 |
| AC3: `references/` covers the five named docs, each cited by prose pointer | `.claude/skills/atmos/references/{stack-yaml-schema,vendoring,workflows,cli-reference,troubleshooting}.md` | `scripts/atmos_skill_check_test.py` (missing/empty-reference cases); CLI exit 0 |
| AC4: Full component lifecycle (vendor/create → configure → plan → apply → share state) | `.claude/skills/atmos/SKILL.md` (lifecycle body sections); `references/vendoring.md`, `references/cli-reference.md` | Manual review (impl-log Session 2); CLI exit 0 |
| AC5: Multi-environment hierarchy (namespace/tenant/environment/stage, `stacks.name_pattern`) | `.claude/skills/atmos/SKILL.md` (stack-targeting section); `references/stack-yaml-schema.md` | Manual review (impl-log Session 2) |
| AC6: Catalog-driven inheritance + abstract components (`metadata.type: abstract`, `metadata.inherits`) | `.claude/skills/atmos/SKILL.md` (configure-in-stack section); `references/stack-yaml-schema.md` | Manual review (impl-log Session 2) |
| AC7: Two-stage plan/apply (`plan --out` → `apply --from-plan`) + `deploy` auto-approval safety | `.claude/skills/atmos/SKILL.md` (plan/apply section); `references/cli-reference.md` | Manual review (impl-log Session 2) |
| AC8: Cross-component data sharing (`!terraform.state` vs `!terraform.output`, remote-state module) | `.claude/skills/atmos/SKILL.md` (remote-state section); `references/stack-yaml-schema.md`, `references/cli-reference.md` | Manual review (impl-log Session 2) |
| AC9: Debugging + troubleshooting (`describe component`, `validate stacks`, `ATMOS_LOGS_LEVEL`) | `.claude/skills/atmos/SKILL.md` (debugging section); `references/troubleshooting.md` | Manual review (impl-log Session 2) |
| AC10 (process): Authored via the `skill-creator` skill | Authoring guidance applied; see Deviations | Process criterion — not a repo artifact (see Deviations) |

## Changes by Slice

### Slice 1: Acceptance checker (TDD)

| File | Change | Lines |
|------|--------|-------|
| `scripts/atmos_skill_check.py` | ✨ new | +164 |
| `scripts/atmos_skill_check_test.py` | ✨ new | +184 |

### Slice 2: The atmos skill (SKILL.md + five references)

| File | Change | Lines |
|------|--------|-------|
| `.claude/skills/atmos/SKILL.md` | ✨ new | +220 |
| `.claude/skills/atmos/references/stack-yaml-schema.md` | ✨ new | +217 |
| `.claude/skills/atmos/references/vendoring.md` | ✨ new | +130 |
| `.claude/skills/atmos/references/cli-reference.md` | ✨ new | +121 |
| `.claude/skills/atmos/references/troubleshooting.md` | ✨ new | +93 |
| `.claude/skills/atmos/references/workflows.md` | ✨ new | +92 |

### Workflow artifacts (not feature code)

| File | Change | Lines |
|------|--------|-------|
| `.qrspi/RUS-19/research.md` | ✨ new | +446 |
| `.qrspi/RUS-19/plan.md` | ✨ new | +104 |
| `.qrspi/RUS-19/design.md` | ✨ new | +98 |
| `.qrspi/RUS-19/structure.md` | ✨ new | +73 |
| `.qrspi/RUS-19/worktree.md` | ✨ new | +62 |
| `.qrspi/RUS-19/impl-log.md` | ✨ new | +55 |
| `.qrspi/RUS-19/questions.md` | ✨ new | +47 |

## Testing Summary

- [x] Slice 1: unit tests — `python3 scripts/atmos_skill_check_test.py` — 15 passed, 0 failed
- [x] Slice 2: acceptance gate — `python3 scripts/atmos_skill_check.py .claude/skills/atmos` — exit 0 (no violations)
- [x] Slice 2: no checker regression — `python3 scripts/atmos_skill_check_test.py` — 15 passed, 0 failed
- [x] Manual verification: every body lifecycle section ends in a prose pointer to its matching reference; all nine §Desired End State criteria map to a present body section or reference (impl-log Session 2)

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| Slice 1 contracts (`parse_frontmatter`, `check_skill`, CLI) | per structure.md §Contracts | Implemented as specified; `Violation = str`, `Frontmatter = dict[str, str]` | None — clean (impl-log Session 1: "Deviations from structure.md: none") |
| Slice 2 file set | 6 files under `.claude/skills/atmos/` | All 6 present | None — clean (impl-log Session 2: "Deviations from structure.md: none") |
| AC10 process criterion (author via `skill-creator` eval loop) | full skill-creator eval/triggering loop run | skill-creator authoring guidance applied; interactive eval loop NOT run | Plan deviation: autonomous non-interactive slice has no human at the eval viewer; the deterministic checker (OQ3=Option A) is the verification gate the design intended for mechanically-checkable criteria (impl-log Session 2) |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| agentskills.io schema conflicts with in-repo 5-field schema (OQ1) | Mitigated — kept the in-repo 5-field schema with `name`/`description` (agentskills.io core) non-empty; checker enforces it; no conflict observed | Revert `.claude/skills/atmos/SKILL.md` frontmatter |
| Body exceeds 500-line / 5000-token budget with no enforcement | Mitigated — depth offloaded to 5 references; body ~213 lines / ~2606 tokens, well under caps; checker enforces the 500-line bound exactly | n/a — within budget |
| Skill auto-triggers too aggressively or not at all (no triggering metric) | Accepted/open — trigger-phrase-rich `description` applied (qrspi-work pattern); skill-creator triggering eval NOT run (out-of-scope, no viewer) | Tune `description` field in `SKILL.md`; remove skill dir to fully disable |
| skill-creator / writing-bash-scripts internals unreadable; authoring assumptions may diverge | Accepted — treated as a live process step; no internals hard-coded | n/a |
| Reference content factual drift vs current atmos CLI | Accepted/open — CLI specifics localized to `references/cli-reference.md`; version numbers (e.g. `1.398.0`) are illustrative placeholders, not real pins; not independently verified against atmos docs in-slice | Correct specific reference doc(s); changes are localized |

## Open Items

- Token-budget check is approximate (`len(body) // 4` heuristic, no in-repo tokenizer); exact 5000-token conformance relies on out-of-scope skill-creator tooling.
- skill-creator interactive eval/triggering loop deferred — re-run with a human at the eval viewer to validate auto-invocation accuracy before relying on the skill in production.
- atmos factual claims in references not independently verified against current atmos docs; recommend a doc-accuracy pass (version numbers are illustrative placeholders).
- OQ2 (name `atmos`, unprefixed): adopted as proposed — confirm acceptable.
- OQ4 (list the skill in `README.md` / `.claude/CLAUDE.md` skill catalogs): deferred; not included in this PR. Add a follow-up if discoverability in docs is wanted.
