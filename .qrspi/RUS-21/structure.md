# Structure Outline — Create a new agent skill: using-codex-cli

**Design basis:** design.md @ 2026-05-31T17:08:00Z
**Generated:** 2026-05-31T17:11:00Z
**Status:** draft

## New Types

This is a documentation/skill-authoring deliverable; there are no programming types. The structural "types" are file artifacts with a fixed shape:

- `SkillFrontmatter { name: string (kebab, == dir name), description: string (capability + trigger phrases), command: "/using-codex-cli", argument-hint: string, allowed-tools: csv }` (ref: design.md §Pattern Decisions D2)
- `SkillBody { Overview, Approval Modes, Sandbox Modes, AGENTS.md, Configuration, Session Management, Non-Interactive Automation, Multi-Agent Integration, Limitations & Pitfalls, Quick Decision Rules }` — markdown H2 sections, body ≤ 500 lines (ref: design.md §Desired End State)
- `ReferenceFile { relative path under references/, linked from body by relative path }` (ref: design.md §Delta)

## Modified Types

- None. No existing code or eval types change (ref: design.md §Delta).

## Contracts

- `.claude/skills/using-codex-cli/SKILL.md` exists with valid YAML frontmatter and all required H2 sections — primary deliverable; auto-discovered by harness (ref: research Q12).
- `references/<topic>.md` files exist and are each linked by relative path from SKILL.md body (ref: research Q2).
- `validate_skill(skill_dir) -> pass/fail` — structural validator: frontmatter parses, required keys present, body line count ≤ 500, each required section header present, every referenced `references/*.md` link resolves (ref: design.md §Pattern Decisions D4).

## Slice 1: Skeleton skill — frontmatter, body sections, and validator (TDD)

**Goal:** A discoverable `using-codex-cli` skill whose SKILL.md has valid frontmatter and all required (initially stub) H2 section headers, with an executable validator that proves the structure. End-to-end testable: run the validator → pass.
**Files touched:**

- ✨ `.claude/skills/using-codex-cli/SKILL.md` — frontmatter + all required H2 section headers (content stubbed/brief), body ≤ 500 lines
- ✨ `.claude/skills/using-codex-cli/references/.gitkeep` or first stub reference — ensure references dir exists and is linkable
- ✨ `.claude/skills/using-codex-cli/scripts/validate_skill.py` (or repo `scripts/`) — structural validator implementing the `validate_skill` contract
- ✨ `.claude/skills/using-codex-cli/scripts/test_validate_skill.py` — tests for the validator (valid skill passes; missing-section/oversize/broken-link cases fail)
**Verification:**
- [ ] `python .../scripts/test_validate_skill.py` passes (validator correctly flags missing section, oversize body, broken reference link, and accepts a well-formed skill)
- [ ] `python .../scripts/validate_skill.py .claude/skills/using-codex-cli` returns pass on the stub skill
- [ ] Skill directory name equals frontmatter `name` (`using-codex-cli`)
**Context cost:** M
**Depends on:** none

## Slice 2: Author body content + reference files (full acceptance coverage)

**Goal:** Fill every required body section with the actual Codex CLI guidance and create all reference files, such that all content acceptance criteria are met and the validator still passes (body ≤ 500 lines, all sections present, all reference links resolve).
**Files touched:**

- ⚠️ `.claude/skills/using-codex-cli/SKILL.md` — replace stubs with real content: Approval Modes (all 3 + when-to-use), Sandbox Modes (3 + platform note), AGENTS.md hierarchy, Configuration summary, Session Management, codex exec automation + pipe examples, Multi-Agent Integration, Limitations & Pitfalls, Quick Decision Rules
- ✨ `references/sandbox-and-approvals.md` — full approval×sandbox matrix; macOS Seatbelt vs Linux Bubblewrap+Landlock; network gotchas
- ✨ `references/config.md` — config.toml sections, profiles, model_instructions_file, feature flags, project-root detection, user vs project precedence
- ✨ `references/agents-md.md` — AGENTS.md/AGENTS.override.md discovery order, concatenation/precedence, 32 KiB cap, fallback filenames, nested rules
- ✨ `references/automation.md` — codex exec input patterns, --json/--quiet, hermetic-CI flags, Unix pipe composition, CODEX_API_KEY
- ✨ `references/multi-agent.md` — MCP server mode (codex()/codex-reply()), Agents SDK pipelines, subagents, git-worktree parallelism, custom agents
- ⚠️ `README.md` and `.claude/CLAUDE.md` — optional one-line discoverability entry (ref: design.md OQ2)
**Verification:**
- [ ] `python .../scripts/validate_skill.py .claude/skills/using-codex-cli` passes with full content (body still ≤ 500 lines, all reference links resolve)
- [ ] Manual acceptance-criteria checklist: all three approval modes, all sandbox modes + platform enforcement, codex exec/CI patterns, AGENTS.md hierarchy, MCP/multi-agent, config.toml+profiles, limitations, pipe examples — each present (in body or linked reference)
- [ ] Each `references/*.md` referenced from the body actually exists and is non-empty
**Context cost:** L
**Depends on:** Slice 1

---

## Unverified Assumptions

- The Codex CLI behavioral facts (flag names, mode names, enforcement mechanisms) are taken from the ticket's documented conventions, not verified against a live Codex CLI install or upstream docs (not available in this repo). If a Codex install or network access were available at implementation, claims should be spot-checked; otherwise they are sourced to the ticket and marked version-sensitive (ref: design.md §Risk Register).
- Whether a harness-provided skill-creator skill must be invoked (AC "built using the skill builder skill") is unresolved (ref: design.md OQ1). Structure proceeds to the in-repo SKILL.md contract; if the skill-creator is available at implement time, run it to generate/refine the SKILL.md, then apply the validator.
- Placement of the validator (`scripts/` inside the skill dir vs repo `scripts/`) is a minor open choice (ref: design.md OQ3); structure assumes the skill's own `scripts/` to keep the skill self-contained per agentskills.io.
