# PR: Add using-gemini-cli agent skill (SKILL.md + references)

**Ticket:** RUS-22
**Design:** design.md @ 2026-06-03T00:00:00Z
**Structure:** structure.md @ 2026-06-06T00:00:00Z

## Summary

Adds a new self-contained agent skill at `.claude/skills/using-gemini-cli/` that
teaches agents how to install, authenticate, invoke, and orchestrate the Google
Gemini CLI. It follows the in-repo self-contained precedent (`qrspi-ticket`,
`qrspi-work`): a concise `SKILL.md` overview (221 lines / ~2,652 tokens, under the
500-line / 5,000-token cap) plus three `references/*.md` deep dives reachable by
relative path. No code, queries, or automated tests are introduced — this is a
pure-markdown skill, which carries no automated test under repo conventions.
**Reviewer focus:** (1) accuracy of the Gemini-specific facts, especially the
CRITICAL June 18 2026 Antigravity deprecation note and the `⚠ UNVERIFIED` honesty
flags; (2) the two human-only verification items deferred below; (3) whether the
README skill list should mention the skill (OQ1, human-discretionary).

## Acceptance Criteria Mapping

> No automated tests exist for markdown skills (ref: design.md Q12/Q13). "Test"
> below names the verification command/check run during implementation.

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: agentskills.io structure + valid `SKILL.md` frontmatter | `SKILL.md` frontmatter (`name`, `description`, `allowed-tools`) | stdlib frontmatter parser — PASS |
| AC2: Built using the Anthropic skill-builder skill | authored via `skill-creator` conventions | process check (full eval loop deferred — see Open Items) |
| AC3: Body under 500 lines / 5000 tokens | `SKILL.md` | `wc -l` → 221 (≤500); token count → ~2,652 (≤5000) — PASS |
| AC4: Detailed reference material in `references/` | `references/{permissions-and-sandbox,orchestration,subagents-mcp-extensions}.md` | reference link resolution — 3/3 linked, no orphans — PASS |
| AC5: Install / auth / invocation (interactive, `-p`, piped) | `SKILL.md` §Install & Authenticate, §Invocation | section-presence check — PASS |
| AC6: Permission/approval model (default, auto_edit, yolo) | `SKILL.md` §Permission & Approval Model; `references/permissions-and-sandbox.md` | section-presence check — PASS |
| AC7: Sandbox mode config + when to enable | `SKILL.md` §Sandbox; `references/permissions-and-sandbox.md` | section-presence check — PASS |
| AC8: GEMINI.md context-file hierarchy | `SKILL.md` §GEMINI.md Context Hierarchy | section-presence check — PASS |
| AC9: MCP server config + extension install | `SKILL.md` §MCP & Extensions; `references/subagents-mcp-extensions.md` | section-presence check — PASS |
| AC10: Subagent definition, routing, tool grants | `SKILL.md` §Subagents; `references/subagents-mcp-extensions.md` | section-presence check — PASS |
| AC11: Multi-agent orchestration patterns | `SKILL.md` §Multi-Agent Orchestration; `references/orchestration.md` | section-presence check — PASS |
| AC12: June 2026 deprecation / Antigravity note | `SKILL.md` §Deprecation (CRITICAL) | fact verification vs. official docs — PASS (June 18 2026 confirmed) |
| AC13: Actionable examples for common workflows | `SKILL.md` §Worked Examples (code review, test gen, exploration) | section-presence check — PASS |

## Changes by Slice

### Slice 1: Author the `using-gemini-cli` skill (SKILL.md + references)

| File | Change | Lines |
|------|--------|-------|
| `.claude/skills/using-gemini-cli/SKILL.md` | ✨ new | +221 |
| `.claude/skills/using-gemini-cli/references/orchestration.md` | ✨ new | +101 |
| `.claude/skills/using-gemini-cli/references/permissions-and-sandbox.md` | ✨ new | +107 |
| `.claude/skills/using-gemini-cli/references/subagents-mcp-extensions.md` | ✨ new | +90 |

### Workflow artifacts (QRSPI process, not feature code)

These are the persisted phase artifacts carried in the stack; no application behavior.

| File | Change | Lines |
|------|--------|-------|
| `.qrspi/RUS-22/questions.md` | ✨ new | +59 |
| `.qrspi/RUS-22/research.md` | ✨ new | +487 |
| `.qrspi/RUS-22/design.md` | ✨ new | +102 |
| `.qrspi/RUS-22/structure.md` | ✨ new | +112 |
| `.qrspi/RUS-22/plan.md` | ✨ new | +135 |
| `.qrspi/RUS-22/worktree.md` | ✨ new | +74 |
| `.qrspi/RUS-22/impl-log.md` | ✨ new | +81 |

## Testing Summary

- [x] Slice 1: size cap — `wc -l SKILL.md` → 221 lines (≤500) — PASS
- [x] Slice 1: token budget — body ~2,652 tokens (≤5000) — PASS
- [x] Slice 1: frontmatter — stdlib parser asserts `name: using-gemini-cli`, `description` present, `allowed-tools ⊇ {Bash}` — PASS
- [x] Slice 1: reference links — all 3 `references/*.md` mentioned in prose exist; no orphans — PASS
- [x] Slice 1: section coverage — 12/12 Desired-End-State acceptance sections present — PASS
- [x] Slice 1: fact verification — Gemini flags/env vars/sandbox profiles/deprecation date checked vs. official docs (June 2026, v0.38.x); unconfirmable facts flagged `⚠ UNVERIFIED` — PASS
- [x] Slice 1: scope check (Risk 3) — no cross-reference to in-repo `yolo()` wrapper or JS workflow "sandbox" — PASS
- [ ] Manual: `skill-creator` eval loop on `using-gemini-cli` — DEFERRED (needs human reviewer + browser/display)
- [ ] Manual: end-to-end read-through confirming an agent can install, authenticate, and invoke Gemini from the doc alone — DEFERRED (human)

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| `frontmatter.allowed-tools ⊇ { Bash }` | superset of `{Bash}` | `Bash, Read, Write` | Permitted superset; Read/Write back the filesystem-coordination guidance in the orchestration sections. No contract violation. |
| Frontmatter validation method (plan Step 18) | PyYAML-based check | stdlib-equivalent parser asserting the same 3 conditions | PyYAML and `pip` unavailable in worktree; stdlib substitution matches repo's stdlib-only convention. Result identical (PASS). |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| Gemini-specific facts may be stale/wrong | Mitigated — facts verified vs. official docs (June 2026, v0.38.x); unconfirmable items flagged `⚠ UNVERIFIED` inline | Edit/remove offending facts in `SKILL.md` + references; whole skill is additive markdown |
| `SKILL.md` exceeds 500-line / 5000-token cap | Mitigated — 221 lines / ~2,652 tokens via references split | Move more detail into `references/*.md` |
| "sandbox"/"yolo" conflated with in-repo `yolo()` wrapper / workflow sandbox | Mitigated — all terms scoped to Gemini CLI; scope check PASS | n/a |
| Skill description triggers poorly | Accepted/open — description authored in `using-graphite-cli` style; eval-loop tuning deferred (human) | Re-run `skill-creator` description optimization |
| No automated test can prove the skill works | Accepted — manual end-to-end verification per repo convention; two manual items deferred | n/a |

**Rollback (whole skill):** delete `.claude/skills/using-gemini-cli/`. The change is
purely additive (no modified files, no registry edits — discovery is by convention),
so removal fully reverts with zero side effects.

## Open Items

- **Deferred manual verification (reviewer checklist):**
  - Run the `skill-creator` eval loop on `using-gemini-cli` (needs human reviewer + browser/display; not runnable headless).
  - Manual end-to-end read-through confirming an agent can install, authenticate, and invoke Gemini from the document alone.
- **`⚠ UNVERIFIED` honesty flags** in the docs (yolo/auto_edit coupling per issue #13792, exact `--output-format json` schema, subagent concurrency limits) are intentional — do not "fix" by asserting unconfirmed facts; confirm against official docs before removing the flag.
- **OQ1:** Whether to add `using-gemini-cli` to the README skill list — auto-discovery does not require it; human-discretionary.
- **OQ2:** `using-gemini-cli` name assumed final (drives `frontmatter.name` + all four paths).
- **OQ4:** Depth of Antigravity-CLI migration content (forward-pointer vs. fuller treatment) left brief; revisit nearer the June 18 2026 deprecation.
- **Env note:** the literal PyYAML-based frontmatter check requires PyYAML/pip to be installed in the environment to run as written.
