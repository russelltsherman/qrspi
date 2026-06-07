# Structure Outline — Create a new agent skill `using-codex-cli`

**Design basis:** design.md @ 2026-06-02T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft

> NOTE: This is a documentation/skill-authoring ticket, not a code change. There
> are no runtime types or function signatures. The "New Types" and "Contracts"
> sections below describe the structural schemas that govern the artifact
> (frontmatter shape, file layout, body→references linking, validation gate)
> instead of program types. Research was skipped for RUS-21, so several design
> claims remain [UNVERIFIED] and are collected at the bottom.

## New Types

These are structural schemas, not code types.

- `SkillFrontmatter { name: string, description: string }` — YAML block delimited
  by `---` at the top of `SKILL.md`. `name` MUST equal `using-codex-cli`. Additional
  fields (command, argument-hint, allowed-tools, version, author) are conditional on
  the agentskills.io spec — see Unverified Assumption UA-1 / design OQ1.
- `SkillBody { sections: Section[] }` — markdown after the closing `---`. Hard limit:
  < 500 lines AND < 5000 tokens (design §Desired End State, Risk row 1).
- `ReferenceFile { path: string, topic: string }` — a focused deep-dive markdown file
  under `references/`, linked from the `SKILL.md` body.

## Modified Types

None. This is a greenfield addition; design §Delta "Modified files: None".

## Contracts

These are the cross-cutting interfaces the single slice must honor end-to-end.

- `frontmatter-contract` — `SKILL.md` opens with a valid YAML `---` block containing
  at minimum `name: using-codex-cli` and a `description`. Consumed by the Claude Code
  harness for skill discovery/triggering. (design §Desired End State item 2 row 1)
- `body-length-contract` — `SkillBody` < 500 lines and < 5000 tokens; enforced as the
  final validation step of the slice. (design Risk row 1; Decisions 1 & 3)
- `body-to-references-link-contract` — every `references/*.md` file is reachable via a
  relative link in the `SKILL.md` body, and every such link resolves to an existing
  file (no dangling links). The body acts as a table-of-contents + quick-reference;
  depth lives in `references/`. (design Decision 1 Option B, Decision 3 Option B)
- `acceptance-coverage-contract` — the union of `SKILL.md` body + `references/` covers
  all 11 acceptance criteria rows in design §Desired End State item 2 (approval modes,
  sandbox modes, codex exec patterns, AGENTS.md hierarchy, MCP server mode, config.toml
  reference, limitations/workarounds, Unix pipe composition, frontmatter validity,
  skill-builder provenance, body length).
- `skill-creator-validation-contract` — the skill is produced/validated through the
  `skill-creator` skill and its eval loop (per global memory directive
  feedback_skill_creator: never ship a SKILL.md ad-hoc). This is the slice's terminal
  gate, not a separate slice. (design §Desired End State item 2 row 2; Risk row 1)

## Slice 1: Author and validate the `using-codex-cli` skill

**Goal:** Deliver a complete, triggerable, length-compliant `using-codex-cli` skill —
`SKILL.md` (frontmatter + in-body sections) plus its `references/` deep-dives — that
satisfies all 11 acceptance criteria and passes `skill-creator` validation. This is a
single end-to-end testable path: a working skill the harness can discover and read.

**Why one slice (not split):** The `SKILL.md` body and the `references/` files are
mutually dependent — the body cross-links the references (body-to-references-link-
contract) and the references exist specifically to keep the body under its length
limit (Decision 1 Option B). Splitting the main file from its support files is the
explicit WRONG example in the structure rules. The whole package is authored in one
sitting and validated as a unit by the `skill-creator` eval loop. File count is 5
core files (≤8 with all optionals), under the 10-file ceiling.

**Files touched:**

- ✨ `.claude/skills/using-codex-cli/SKILL.md` — frontmatter + in-body sections:
  approval modes (suggest/auto-edit/full-auto decision matrix), sandbox modes
  (read-only / workspace-write / danger-full-access; macOS Seatbelt + Linux
  bubblewrap/Landlock; network-off default), session management, AGENTS.md hierarchy
  (override-first cascade, 32 KiB limit, nested rules), plus quick-reference tables
  and TOC links into `references/`. (design Decision 1: keep these in body)
- ✨ `.claude/skills/using-codex-cli/references/config-reference.md` — full
  `config.toml` schema: user vs project level, `[profiles.<name>]`, model settings,
  feature flags, `model_instructions_file`, etc. (design Decision 3 Option B)
- ✨ `.claude/skills/using-codex-cli/references/codex-exec-patterns.md` — `codex exec`
  positional arg, stdin `-`, prompt+stdin piping, `--json`, `--quiet`,
  `--ignore-user-config`, `--ignore-rules`, Unix pipe composition + CI patterns.
- ✨ `.claude/skills/using-codex-cli/references/mcp-server-mode.md` — `codex()` /
  `codex-reply()` tool schemas, 2-3 worked multi-agent orchestration examples,
  worktrees-for-parallel-agents, subagent-only-when-requested discipline.
- ✨ `.claude/skills/using-codex-cli/references/limitations-and-workarounds.md` —
  re-run non-determinism flowchart (re-run → diff → run tests → accept/rollback),
  macOS network/sandbox bugs (prefer `--sandbox` flag over config.toml),
  long-chain limits, context-window pressure / fresh-session guidance.

Optional (create only if a body section would breach the length contract; design
§Delta lists them as optional, Decision 1 keeps the topics in-body by default):
`references/approval-modes.md`, `references/sandbox-modes.md`,
`references/agents-hierarchy.md`.

**Verification:**

- [ ] `skill-creator` skill + its eval loop run and report the skill valid
      (skill-creator-validation-contract).
- [ ] `SKILL.md` frontmatter parses as YAML, `name: using-codex-cli` present, a
      non-empty `description` present (frontmatter-contract).
- [ ] Skill triggers in the harness on a Codex-CLI-related prompt (discoverable).
- [ ] `SkillBody` < 500 lines and < 5000 tokens (body-length-contract) — measured
      after the closing `---`.
- [ ] Every `references/*.md` is linked from the body and every body link resolves
      to an existing file; no dangling links (body-to-references-link-contract).
- [ ] All 11 acceptance-criteria rows from design §Desired End State item 2 are
      covered by body + references (acceptance-coverage-contract).

**Context cost:** L (greenfield authoring of ~5-8 documentation files spanning 8+
topics, plus a skill-creator eval pass).
**Depends on:** none

---

## Unverified Assumptions

These are design claims that could not be mapped to a concrete, confirmed file or
schema. Research (research.md) was skipped for RUS-21, so the design itself flagged
most of these [UNVERIFIED]. They need human attention before/at planning.

- **UA-1 (frontmatter schema, blocks frontmatter-contract specifics):** The exact
  set of agentskills.io-required frontmatter fields is unknown. Design assumes only
  `name` + `description` (matching existing qrspi-* skills) but cannot confirm
  agentskills.io doesn't mandate `version`/`author`/`command`. (design OQ1, Risk row 2)
- **UA-2 (skills are single-file):** "All 10 existing skills are single-file" and the
  `.claude/skills/<name>/SKILL.md` layout — derived from the ticket, not verified
  against the codebase. (design §Current State, [UNVERIFIED])
- **UA-3 (references/ precedent):** Design claims `qrspi-work/references/` already
  exists, making `references/` a "latent" pattern — unverified; if false, this skill
  introduces a brand-new directory convention with no precedent. (design Decision 1,
  OQ5, Risk row 3)
- **UA-4 (no agent definition needed):** Assumption that `using-codex-cli` needs no
  `.claude/agents/` entry and that `writing-bash-scripts` is the standalone-skill
  precedent — unverified; design also notes `writing-bash-scripts` "has no SKILL.md
  file." (design Decision 2, §Current State)
- **UA-5 (agentskills.io conformance of existing skills):** Whether existing skills
  actually follow agentskills.io or a qrspi-local YAML convention is unknown; if they
  diverge, this skill must pick a side (conform vs match-repo). Human design-level
  decision. (design Risk row 3)
- **UA-6 (skill-builder identity):** "Anthropic skill builder skill" is assumed to be
  `skill-creator`, but the design lists `skill-creator`/`mcp-builder`/other as
  candidates. The validation gate depends on resolving this. (design OQ3)
- **UA-7 (slash-command wrapper):** Whether the skill needs a `/using-codex-cli`
  wrapper or directory placement alone suffices for discovery is undecided — affects
  whether any wrapper file is added to the slice. (design OQ2)
- **UA-8 (MCP example fidelity):** Required depth of MCP wire payloads (param names vs
  full JSON) is open; affects mcp-server-mode.md scope. (design OQ4)
- **UA-9 (Codex CLI factual content):** All Codex CLI behavioral claims (sandbox
  enforcement mechanisms, config.toml fields, `codex exec` flags, macOS network bugs,
  32 KiB AGENTS.md limit) originate from the ticket, not from verified Codex docs or
  the codebase. Implementer should validate against current Codex CLI docs before
  encoding them as authoritative guidance.
