# PR: RUS-9 Add using-claude-cli reference skill

**Ticket:** RUS-9
**Design:** design.md @ 2026-06-02T16:00:00Z
**Structure:** structure.md @ 2026-06-06T00:00:00Z

## Summary

Adds a new utility skill `using-claude-cli` that documents how to drive the
Claude Code CLI itself (headless mode, subagents, sessions, MCP, permissions,
cost control, scripted orchestration). The skill follows the established
five-field `.claude/skills/<name>/SKILL.md` frontmatter pattern — not the
agentskills.io fields implied by the ticket — keeping it parseable by existing
consumers; advanced topics are split into four `references/*.md` depth docs to
hold the body under the 500-line budget (it lands at 150). A stdlib-only
structure test (`scripts/using_claude_cli_skill_test.py`) enforces the
frontmatter, body-size, and reference-link contracts. **Reviewer focus:** (1) the
content of the SKILL.md and reference docs is synthesized from the Claude Code
CLI spec and is *not verifiable against this repo* — every externally-derived
claim carries a `[CLI-spec]` provenance banner and needs human accuracy review;
(2) confirm the five-field-frontmatter decision over the ticket's implied schema.

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: valid SKILL.md frontmatter (5 fields) | `.claude/skills/using-claude-cli/SKILL.md` (frontmatter) | `scripts/using_claude_cli_skill_test.py::validate_skill_structure` (asserts keys == EXPECTED_KEYS) |
| AC2: built via skill builder | `.claude/skills/using-claude-cli/SKILL.md` — authored manually following the observed pattern (skill-creator absent; see Deviations/Open Items) | n/a (process AC; structure asserted by `validate_skill_structure`) |
| AC3: body under 500 lines / 5000 tokens | `.claude/skills/using-claude-cli/SKILL.md` (body, 150 lines) | `scripts/using_claude_cli_skill_test.py` (asserts body_lines <= MAX_BODY_LINES) |
| AC4: `references/` directory with 4 docs | `.claude/skills/using-claude-cli/references/{advanced-cli-flags,hook-examples,agent-team-orchestration,permission-rule-patterns}.md` | `scripts/using_claude_cli_skill_test.py::validate_references` (asserts 4 files exist & non-empty) |
| AC5: all CLI modes | `SKILL.md` (modes summary) → `references/advanced-cli-flags.md` | `validate_references` (link resolves) |
| AC6: sub-agent spawning | `SKILL.md` (subagents section) → `references/agent-team-orchestration.md` | `validate_references` (link resolves) |
| AC7: session management | `SKILL.md` (sessions section) | `scripts/using_claude_cli_skill_test.py` (body non-empty / size) |
| AC8: MCP integration | `SKILL.md` (MCP section) → `references/advanced-cli-flags.md` | `validate_references` (link resolves) |
| AC9: permissions | `SKILL.md` (permissions section) → `references/permission-rule-patterns.md` | `validate_references` (link resolves) |
| AC10: cost control | `SKILL.md` (cost-control section) | `scripts/using_claude_cli_skill_test.py` (body non-empty / size) |
| AC11: actionable examples | `SKILL.md` (orchestration examples) | `scripts/using_claude_cli_skill_test.py` (body non-empty / size) |

## Changes by Slice

### Slice 1: Core skill — valid, discoverable, body-complete

| File | Change | Lines |
|------|--------|-------|
| `.claude/skills/using-claude-cli/SKILL.md` | ✨ new | +157 |
| `.claude/CLAUDE.md` | ⚠️ modified (add utility-skill entry) | +4, -0 |
| `scripts/using_claude_cli_skill_test.py` | ✨ new (extended in Slice 2) | +186 |

### Slice 2: Advanced reference docs

| File | Change | Lines |
|------|--------|-------|
| `.claude/skills/using-claude-cli/references/advanced-cli-flags.md` | ✨ new | +122 |
| `.claude/skills/using-claude-cli/references/hook-examples.md` | ✨ new | +127 |
| `.claude/skills/using-claude-cli/references/agent-team-orchestration.md` | ✨ new | +97 |
| `.claude/skills/using-claude-cli/references/permission-rule-patterns.md` | ✨ new | +133 |
| `scripts/using_claude_cli_skill_test.py` | ⚠️ extended (reference-existence + link-resolution assertions) | (counted in Slice 1) |

### Workflow artifacts (not implementation)

QRSPI phase artifacts committed alongside the work; no production behavior.

| File | Change | Lines |
|------|--------|-------|
| `.qrspi/RUS-9/design.md` | ✨ new | +137 |
| `.qrspi/RUS-9/impl-log.md` | ✨ new | +51 |
| `.qrspi/RUS-9/plan.md` | ✨ new | +68 |
| `.qrspi/RUS-9/questions.md` | ✨ new | +53 |
| `.qrspi/RUS-9/research.md` | ✨ new | +441 |
| `.qrspi/RUS-9/structure.md` | ✨ new | +84 |
| `.qrspi/RUS-9/worktree.md` | ✨ new | +43 |

## Testing Summary

- [x] Slice 1: structure test — `python3 scripts/using_claude_cli_skill_test.py` — exit 0 (frontmatter exactly 5 keys; body non-empty; body 150 lines ≤ 500)
- [x] Slice 2: structure test (extended) — `python3 scripts/using_claude_cli_skill_test.py` — exit 0 (4 reference files present & non-empty; 4 body `references/` links resolve, no dangling)
- [x] Manual verification: common-path coverage (headless, subagents, sessions, permissions) is inline in SKILL.md; advanced topics deferred to `references/` links; all four reference docs carry `[CLI-spec]` provenance banners
- [ ] Manual accuracy review of CLI-spec-derived content (DEFERRED — not verifiable in-repo; see Risks & Open Items)

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| `SkillFrontmatter.allowed-tools` | five-field frontmatter (value unspecified) | `allowed-tools: Read, Bash` | Reference skill (documents the CLI in its body) rather than an Agent-spawning phase wrapper, so it does not list `Agent`/Linear tools. Field set still matches the five-key contract exactly; no agentskills.io fields introduced. |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| `skill-creator` tool does not exist | accepted — skill authored manually following the observed pattern; AC2 satisfied in spirit, not via a builder tool | Follow-up ticket to implement `skill-creator`; no rollback of this PR needed |
| agentskills.io fields don't match existing frontmatter | mitigated — used only the five observed fields; external-standard concepts live in prose body | Revert is a clean file delete; no consumer touched the new fields |
| Adding non-QRSPI skill to CLAUDE.md may confuse discovery | mitigated — listed under an explicit "Utility skills (not QRSPI phase wrappers)" subsection | Revert the 4-line CLAUDE.md addition |
| SKILL.md body exceeds 500 lines / 5000 tokens | mitigated — body is 150/500 lines; enforced by the structure test | n/a (test guards regressions) |
| Hook/permission/CLI-mode docs are synthesized, not codebase-verified — may be inaccurate | discovered-new / accepted — all externally-derived claims carry `[CLI-spec]` provenance banners; accuracy is unverifiable in-repo and needs human review before wide adoption | Delete the skill directory + test + CLAUDE.md entry; no production code depends on it |
| Duplicates existing QRSPI doc content | mitigated — positioned as the canonical CLI reference, cross-references in-project facts (`--dangerously-skip-permissions` in `post-create.sh`, worktree-per-ticket pattern) | n/a |

**Rollback (whole PR):** the change is additive and isolated — delete
`.claude/skills/using-claude-cli/`, `scripts/using_claude_cli_skill_test.py`, and
revert the 4-line `.claude/CLAUDE.md` addition. No existing skill, agent, or
script is modified, so removal carries no downstream impact.

## Open Items

- **Manual accuracy review required:** all `[CLI-spec]`-banner content
  (CLI modes, hooks, permission modes, session flags, MCP config, cost flags) is
  synthesized from the Claude Code CLI specification and cannot be validated
  against this repo. Verify against authoritative CLI docs before relying on it
  (design Risk #5, OQ4).
- **`skill-creator` follow-up (OQ1):** AC2 ("built via skill builder") was met by
  manual authoring because no `skill-creator` exists in this repo. Decide whether
  to implement `skill-creator` as a prerequisite/follow-up ticket.
- **Frontmatter spec decision (OQ2):** human judgment still pending on whether the
  five-field format or the ticket's implied agentskills.io fields
  (`model`, `permissionMode`, `mcpServers`, `hooks`) should govern skill frontmatter.
- **Test-mechanism deviation (OQ5):** design Decision 5 recommended `evals/suite.json`
  cases, but that runner is a non-executing stub; this PR ships a standalone stdlib
  `scripts/using_claude_cli_skill_test.py` instead to give the verification step real
  signal. Confirm this is the preferred mechanism.
