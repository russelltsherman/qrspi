# PR: RUS-10 Add cmux agent skill (knowledge skill + references + doc sync)

**Ticket:** RUS-10
**Design:** design.md @ 2026-06-03T00:00:00Z
**Structure:** structure.md @ 2026-06-06T00:00:00Z

## Summary

Adds `cmux`, a self-contained knowledge skill at `.claude/skills/cmux/` that documents
how to drive the cmux terminal multiplexer for AI agents — its workspace/surface/pane
model, the OSC 9/99/777 + `cmux notify` notification system, Claude Code Teams, session
restore / per-agent resume, and multi-agent orchestration. The SKILL.md body stays an
overview-plus-pointers document (155 lines, ~2.3k tokens — within the 500-line / 5000-token
budget) and pushes exhaustive material into three on-demand `references/` files (keyboard
shortcuts, CLI + socket API, agent hooks). Per reviewer feedback, the skill is NOT indexed in
any markdown file (no README.md / `.claude/CLAUDE.md` listing) — discovery is by file presence
alone. **Reviewer focus:** (1) the three open-question defaults below, which a
human was asked to confirm — `command: /cmux` with `argument-hint: [topic]`, the ticket body
treated as the v1 cmux spec (cmux is external and unverifiable in-repo), and the agent-hooks
coverage (Claude Code in detail + a generic pattern for the other ~10 agents); (2) the
factual accuracy of documented cmux commands/config keys/shortcuts against a real cmux build.

## Acceptance Criteria Mapping

> No automated tests exist — this is a content/knowledge skill and the in-repo eval harness
> is a non-functional placeholder (design §Risk Register, Q11). "Test" below is the manual
> structural verification recorded in impl-log.md Session 2 (a `python3` structural check) plus
> the external skill-creator authoring pass; each AC area maps to the file(s) that satisfy it.

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: agentskills.io directory structure with valid five-key frontmatter | `.claude/skills/cmux/SKILL.md:1-7` | impl-log Session 2 structural check: 5 keys, `name: cmux`/`command: /cmux`, double-quoted description with "Use when…" triggers, no escape bytes in frontmatter → PASS |
| AC2: Built using the skill-creator skill | skill-creator invoked as authoring guide (impl-log Session 1, T2) | Manual structural checklist (plan step 14) — eval/variance loop non-runnable autonomously; see Deviations |
| AC3: SKILL.md body < 500 lines / < 5000 tokens | `.claude/skills/cmux/SKILL.md` (155 lines) | impl-log Session 2: 148 body lines / ~2252 tokens counted → PASS |
| AC4: Detailed reference material in `references/` | `references/keyboard-shortcuts.md`, `references/cli-and-socket-api.md`, `references/agent-hooks.md` | impl-log Session 2: all 3 files present, all 3 body pointers resolve → PASS |
| AC5: Workspace / surface / pane lifecycle | `SKILL.md:60-79` ("Workspaces, surfaces, and panes") | impl-log Session 2: AC area present → PASS |
| AC6: Notification system integration (OSC 9/99/777, `cmux notify`, hooks) | `SKILL.md:82-100` + `references/cli-and-socket-api.md`, `references/keyboard-shortcuts.md` | impl-log Session 2: AC area present; escape bytes only inside code fences in references → PASS |
| AC7: Claude Code Teams workflow | `SKILL.md:102-109` (`cmux claude-teams`, native split) | impl-log Session 2: AC area present → PASS |
| AC8: Session restore & agent resume | `SKILL.md:111-125` + `references/agent-hooks.md` (`cmux hooks setup`, `terminal.autoResumeAgentSessions`) | impl-log Session 2: AC area present → PASS |
| AC9: Multi-agent orchestration patterns | `SKILL.md:127-156` (one-workspace-per-task, notification-driven monitoring, metadata, macOS caveat) | impl-log Session 2: AC area present → PASS |
| AC10: Skill discoverable | `.claude/skills/cmux/SKILL.md` (discovery by file presence); per reviewer feedback the skill is NOT indexed in any markdown file (no README.md / `.claude/CLAUDE.md` listing) | impl-log Session 2: discovery by file presence → PASS |

## Changes by Slice

### Slice 1: Author the cmux content skill (SKILL.md + references + doc sync)

| File | Change | Lines |
|------|--------|-------|
| `.claude/skills/cmux/SKILL.md` | ✨ new | +155 |
| `.claude/skills/cmux/references/keyboard-shortcuts.md` | ✨ new | +115 |
| `.claude/skills/cmux/references/cli-and-socket-api.md` | ✨ new | +125 |
| `.claude/skills/cmux/references/agent-hooks.md` | ✨ new | +116 |

> Workflow artifacts (not part of the feature): `.qrspi/RUS-10/{questions,research,design,structure,plan,worktree,impl-log}.md`
> are QRSPI phase outputs carried on the stack (+733 lines total), not product changes.

## Testing Summary

- [x] Slice 1: structural verification — `python3` structural check (impl-log Session 2) — frontmatter 5 keys, body 148 lines / ~2252 tokens, 3 reference files present, all 3 body pointers resolve, all 8 AC areas present, no escape bytes/`Cmd+` in frontmatter → PASS
- [x] Manual verification: every relative `references/…` pointer in SKILL.md resolves to an existing file; escape/keystroke notation appears only inside code fences or inline code spans in references
- [ ] Not run: external skill-creator eval/variance + browser-review loop — requires a human reviewer and is non-runnable in an autonomous slice (in-repo eval harness is a placeholder); skill-creator was used as an authoring guide instead (see Deviations)
- [ ] Not verified in-repo: factual accuracy of cmux commands/config keys/shortcuts — cmux is external and absent from the repo (reviewer to confirm against a real build)

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| skill-creator build (AC2 / structure Verification) | Skill built and validated via the external skill-creator eval/variance + browser-review loop | skill-creator applied as an authoring guide (five-key frontmatter, progressive disclosure, references for depth, < 500-line body); verification via manual structural checklist | The eval/variance loop requires a human reviewer and is non-runnable in an autonomous slice; the in-repo eval harness is a placeholder. Recorded in impl-log Sessions 1 & 2. No deviation from structure.md's on-disk contracts (frontmatter, discovery, reference-pointer, body-budget, escape-safety) — all satisfied. |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| Documented cmux commands/shortcuts/config keys inaccurate or outdated (external, unverifiable in-repo) | accepted / open — ticket body used as v1 spec; uncertainty surfaced via the SKILL.md "Version caveat" + "Scope caveats" and OQ3; reviewer must confirm against a real cmux build | `rm -rf .claude/skills/cmux/` (skill de-registers by file absence) |
| Body exceeds 500-line / 5000-token budget (no in-repo enforcer) | mitigated — body counted at 148 lines / ~2252 tokens; exhaustive lists offloaded to references | Trim body / move content into `references/` |
| `Cmd+N` notation or OSC escape sequences break frontmatter/render (no in-repo precedent) | mitigated — frontmatter is plain text only; all keystroke/escape content lives inside code fences or inline code spans in references; structural check confirms no escape bytes/`Cmd+` in frontmatter | Edit offending content back into a code fence in `references/` |
| Markdown index drifts from the new skill (manual edits) | eliminated — per reviewer feedback the skill is NOT indexed in any markdown file (no README.md / `.claude/CLAUDE.md` listing); discovery is by file presence, so there is no listing to drift | n/a (no listing to maintain) |
| In-repo eval harness gives no real verification signal (placeholder) | accepted — relied on manual structural check + skill-creator authoring conventions; did not depend on `run_eval.py` | n/a (no harness change) |

## Open Items

- **OQ1 (confirm):** `command: /cmux`, `argument-hint: [topic]` (optional topic = `shortcuts` | `cli` | `hooks`); skill is primarily auto-invoked. Default applied — reviewer to confirm.
- **OQ3 (confirm):** documented cmux commands/config keys/shortcuts target the ticket spec as v1; the cmux version baseline is unverified (cmux is absent from the repo). Reviewer to confirm the version baseline.
- **OQ4 (confirm):** `references/agent-hooks.md` covers Claude Code in detail plus a generic per-agent resume pattern for the other ~10 listed agents (bounded for maintenance) rather than exhaustive per-agent detail. Reviewer to confirm the chosen breadth.
- **Deferred:** running the skill-creator eval/variance + browser-review loop with a human reviewer (could be a follow-up once the OQ defaults are confirmed).
- **Tech debt:** no automated test guards this skill — discovery, body budget, and pointer resolution rely on a manual structural check; an in-repo skill linter/token-counter would close the gap (none exists today).
