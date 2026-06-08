# Implementation Plan — Create a new agent skill "using-claude-cli"

**Structure basis:** structure.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total steps:** 14

## Slice 1: Core skill — valid, discoverable, body-complete

### Setup

1. ✨ Create `.claude/skills/using-claude-cli/SKILL.md` — write the five-field YAML frontmatter block only, exactly the keys `name`, `description`, `command`, `argument-hint`, `allowed-tools` as valid parseable YAML, matching the `SkillFrontmatter` contract. No agentskills.io fields (`model`, `permissionMode`, `mcpServers`, `hooks`). Set `name: using-claude-cli`, a description per AC, `command`, `argument-hint`, and an `allowed-tools` value consistent with the existing 10 skills (ref: structure §Contracts "SKILL.md frontmatter", Decision 1).

### Core Logic

2. ✨ Append to `.claude/skills/using-claude-cli/SKILL.md` — body sections for AC5 (CLI modes summary) and AC11 (orchestration examples: commit automation, code review piped diff, stdin piping). Mark externally-derived (CLI-spec) vs in-project-verified concepts with provenance notes (ref: structure §Slice 1, Decision 3).
3. ✨ Append to `.claude/skills/using-claude-cli/SKILL.md` — body sections for AC6 (subagents), AC7 (sessions), AC9 (permissions summary), AC10 (cost control). Keep common-path content inline; defer depth to `references/` links (ref: structure §Slice 1, Decision 2).
4. ✨ Append to `.claude/skills/using-claude-cli/SKILL.md` — a "References" section linking to exactly the four filenames Slice 2 creates: `references/advanced-cli-flags.md`, `references/hook-examples.md`, `references/agent-team-orchestration.md`, `references/permission-rule-patterns.md` (ref: structure §Contracts "references/ link set"). Ensure total body stays ≤ 500 lines (ref: §Contracts "SKILL.md body").

### Registration

5. ⚠️ Modify `.claude/CLAUDE.md` — add `using-claude-cli` to the "Available skills" list, noted as a utility skill (not a QRSPI phase wrapper) (ref: structure §Modified Types, Decision 4).
   - **Current:** "Available skills" list contains the 10 `/qrspi-*` entries only.
   - **After:** list additionally contains a `using-claude-cli` entry marked utility/infra, distinct from the phase wrappers.

### Tests

6. ✨ Create `scripts/using_claude_cli_skill_test.py` — stdlib-only structure test implementing `validate_skill_structure()`: assert frontmatter parses as YAML with exactly the five keys, body line count ≤ 500, body non-empty. Runnable like existing `scripts/qrspi_*_test.py` (ref: structure §Contracts "validate_skill_structure()", Decision 5). Reference-existence assertions are deferred to Slice 2.
7. Run: `python3 scripts/using_claude_cli_skill_test.py`
   - **Expected:** exits 0; frontmatter 5-key parse passes, line-count ≤ 500 passes, non-empty body passes.

### Verify Slice 1

8. **Checkpoint:** `python3 scripts/using_claude_cli_skill_test.py`
   - [ ] Test passes (frontmatter 5-key parse, line-count ≤ 500, non-empty body).
   - [ ] `using-claude-cli` appears in the `.claude/CLAUDE.md` "Available skills" list.
   - [ ] Manual read confirms common-path coverage (headless, subagents, sessions, permissions) is inline; advanced topics deferred to `references/` links.

---

## Slice 2: Advanced reference docs

### Setup

9. ✨ Create `.claude/skills/using-claude-cli/references/advanced-cli-flags.md` — all five CLI modes (interactive, headless, bare, piped, background), output formats (`text|json|stream-json`), streaming, model selection. Non-empty `ReferenceDoc` (ref: structure §Slice 2, AC5/AC8).
10. ✨ Create `.claude/skills/using-claude-cli/references/hook-examples.md` — matcher syntax, exit-code semantics, pre/post tool-use patterns, prompt- vs agent-based hooks; provenance-marked (ref: structure §Slice 2, OQ4).
11. ✨ Create `.claude/skills/using-claude-cli/references/agent-team-orchestration.md` — agent teams (experimental), git worktrees for parallel branches, background agents, teammate communication (ref: structure §Slice 2, AC6).
12. ✨ Create `.claude/skills/using-claude-cli/references/permission-rule-patterns.md` — rule syntax (Tool vs Tool(specifier) globs), evaluation order (deny→ask→allow), read-only command lists, CI/CD safety; provenance-marked (ref: structure §Slice 2, AC9, OQ4).

### Core Logic

13. ⚠️ Modify `scripts/using_claude_cli_skill_test.py` — extend `validate_skill_structure()` to assert all four `references/*.md` exist and are non-empty, and that every `references/` link in SKILL.md resolves to a created file (ref: structure §Slice 2, §Contracts).
    - **Current:** `validate_skill_structure()` asserts frontmatter 5-key parse, body ≤ 500 lines, body non-empty.
    - **After:** also asserts the four reference files exist and are non-empty, and every `references/` link in SKILL.md resolves (no dangling links).

### Verify Slice 2

14. **Checkpoint:** `python3 scripts/using_claude_cli_skill_test.py`
    - [ ] Test passes with the new reference-existence assertions.
    - [ ] Each of the four reference files exists and is non-empty.
    - [ ] Every `references/<name>.md` link in SKILL.md points to a file created here (no dangling links).

---

## Rollback Notes

- Step 5 (`.claude/CLAUDE.md` edit): the only modification to existing tracked code. To reverse, remove the added `using-claude-cli` line from the "Available skills" list, restoring the 10-entry QRSPI-phase-only list. No other existing files are modified.
- Steps 1–4, 6, 9–13 create new files; rollback is deleting the `.claude/skills/using-claude-cli/` directory and `scripts/using_claude_cli_skill_test.py`. No DB migrations, config changes, or destructive ops are involved.
