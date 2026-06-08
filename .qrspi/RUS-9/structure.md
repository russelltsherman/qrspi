# Structure Outline — Create a new agent skill "using-claude-cli"

**Design basis:** design.md @ 2026-06-02T16:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft

## New Types

This ticket produces documentation artifacts (Markdown), not program types. The
"types" here are the file-shape contracts the validation test enforces.

- `SkillFrontmatter { name: string, description: string, command: string, argument-hint: string, allowed-tools: string }`
  — the exact five-field YAML frontmatter block at the top of `SKILL.md`, matching the pattern observed across all 10 existing skills (ref: design §Decision 1, AC1).
- `SkillDir { SKILL.md, references/ }` — directory layout under `.claude/skills/using-claude-cli/`. No `scripts/` or `assets/` (ref: design AC4).
- `ReferenceDoc { path: string, body: markdown }` — one of four advanced-topic reference files under `references/` (ref: design §Delta New files).

## Modified Types

- `.claude/CLAUDE.md` "Available skills" section — add one entry for `using-claude-cli`, marked as a utility/infra skill distinct from the `/qrspi-*` phase wrappers (ref: design §Delta, Decision 4, OQ3).

## Contracts

These are the cross-slice interfaces. Slice 1 defines them; Slice 2 fulfills the reference half.

- `SKILL.md frontmatter` — MUST contain exactly the five keys `name`, `description`, `command`, `argument-hint`, `allowed-tools`, as valid parseable YAML. No agentskills.io fields (`model`, `permissionMode`, `mcpServers`, `hooks`) in frontmatter; those concepts live in prose body (ref: Decision 1, Risk #2).
- `SKILL.md body` — under 500 lines / ~5000 tokens; covers the common patterns inline (headless mode, subagents, sessions, permissions); links out to `references/<name>.md` for advanced topics (ref: AC3, Decision 2).
- `references/` link set — SKILL.md body references exactly these four filenames, which Slice 2 must create: `advanced-cli-flags.md`, `hook-examples.md`, `agent-team-orchestration.md`, `permission-rule-patterns.md` (ref: §Delta New files).
- `validate_skill_structure()` — test entrypoint that asserts: frontmatter parses as YAML with the five keys; body line count ≤ 500; each referenced `references/*.md` file exists and is non-empty. Stdlib-only, runnable like the existing `scripts/qrspi_*_test.py` (ref: Decision 5, Q11).

## Slice 1: Core skill — valid, discoverable, body-complete

**Goal:** A registered, structurally-valid `using-claude-cli` skill that documents
the common-path CLI patterns inline and passes an actually-runnable structure test.
End-to-end testable path: skill file exists → frontmatter parses (5 fields) → body
≤ 500 lines → skill listed in CLAUDE.md → structure test passes.

**Files touched:**

- ✨ `.claude/skills/using-claude-cli/SKILL.md` — five-field frontmatter + body covering AC5 (CLI modes summary), AC6 (subagents), AC7 (sessions), AC9 (permissions), AC10 (cost control), AC11 (orchestration examples), with links out to the four `references/` docs for depth. Provenance notes mark externally-derived (CLI-spec) vs in-project-verified concepts (ref: Decision 3).
- ⚠️ `.claude/CLAUDE.md` — add `using-claude-cli` to "Available skills", noted as a utility skill (not a QRSPI phase).
- ✨ `scripts/using_claude_cli_skill_test.py` — stdlib structure-validation test: YAML frontmatter has exactly the 5 keys, body ≤ 500 lines, body non-empty. (Reference-existence assertions are added in Slice 2.)

**Verification:**

- [ ] `python3 scripts/using_claude_cli_skill_test.py` passes (frontmatter 5-key parse, line-count ≤ 500, non-empty body).
- [ ] `using-claude-cli` appears in the `.claude/CLAUDE.md` "Available skills" list.
- [ ] Manual read confirms common-path coverage (headless, subagents, sessions, permissions) is inline, advanced topics are deferred to `references/` links.

**Context cost:** M
**Depends on:** none

## Slice 2: Advanced reference docs

**Goal:** The four `references/` depth docs exist and are non-empty, resolving every
`references/` link in the SKILL.md body; the structure test is extended to enforce
their presence. End-to-end testable path: each SKILL.md reference link → resolves to
a real non-empty file → structure test asserts it.

**Files touched:**

- ✨ `.claude/skills/using-claude-cli/references/advanced-cli-flags.md` — all five CLI modes (interactive, headless, bare, piped, background), output formats (`text|json|stream-json`), streaming, model selection (ref: AC5, AC8).
- ✨ `.claude/skills/using-claude-cli/references/hook-examples.md` — matcher syntax, exit-code semantics, pre/post tool-use patterns, prompt- vs agent-based hooks (ref: §Delta, OQ4; provenance-marked).
- ✨ `.claude/skills/using-claude-cli/references/agent-team-orchestration.md` — agent teams (experimental), git worktrees for parallel branches, background agents, teammate communication (ref: §Delta, AC6).
- ✨ `.claude/skills/using-claude-cli/references/permission-rule-patterns.md` — rule syntax (Tool vs Tool(specifier) globs), evaluation order (deny→ask→allow), read-only command lists, CI/CD safety (ref: AC9, OQ4; provenance-marked).
- ⚠️ `scripts/using_claude_cli_skill_test.py` — extend `validate_skill_structure()` to assert all four `references/*.md` exist and are non-empty, and that every `references/` link in SKILL.md resolves.

**Verification:**

- [ ] `python3 scripts/using_claude_cli_skill_test.py` passes with the new reference-existence assertions.
- [ ] Each of the four reference files exists and is non-empty.
- [ ] Every `references/<name>.md` link in SKILL.md points to a file created here (no dangling links).

**Context cost:** M
**Depends on:** Slice 1

---

## Unverified Assumptions

- **Externally-derived CLI behavior (CLI modes, hooks, permission modes, session flags, MCP config, cost flags).** Design §Current State and Decision 3 confirm none of these are encoded in this repo; the only in-project evidence is `--dangerously-skip-permissions` in `post-create.sh`. AC5–AC10 content is synthesized from the Claude Code CLI specification and cannot be mapped to project source. The slices mitigate by requiring explicit provenance notes, but the *accuracy* of this content is unverifiable from the codebase and needs human review before adoption (ref: Risk #5, OQ4).
- **`skill-creator` does not exist in this repo** (Decision 5, Risk #1, OQ1). AC2 ("built via skill builder") cannot be satisfied as written; the slices author the skill manually following the observed `.claude/skills/<name>/SKILL.md` pattern. Whether `skill-creator` is a prerequisite is an open question for the human.
- **Test mechanism choice.** Design Decision 5 recommends Option A (add cases to `evals/suite.json`), but the same section states the eval runner is a stub that "would not actually execute." To give the verification step real signal, this structure proposes a standalone stdlib `scripts/using_claude_cli_skill_test.py` (mirroring the existing `qrspi_*_test.py` pattern) instead of/in addition to a non-executing `suite.json` entry. This deviates from the literal Decision 5 wording — confirm the preferred mechanism (ref: Q11, OQ5).
- **agentskills.io frontmatter standard.** OQ2 / Risk #2: the ticket implies fields (`model`, `permissionMode`, `mcpServers`, `hooks`) that conflict with the five-field format. The slices follow the five-field format and push the other concepts to prose. Human judgment is still pending on which spec governs.
- **Exact body/token budget.** "≤ 500 lines / ~5000 tokens" is enforced as a line-count check in the test; the token estimate is not independently verified by tooling (Risk #4).
