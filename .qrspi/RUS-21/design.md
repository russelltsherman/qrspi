# Design — Create a new agent skill called using codex cli

**Ticket:** RUS-21
**Research basis:** research.md MISSING — the research phase was skipped; design synthesizes from ticket content and questions only. Claims not grounded in codebase exploration are marked [UNVERIFIED].
**Generated:** 2026-06-02T00:00:00Z
**Status:** draft

## Current State

This section describes the codebase's current state relevant to where the new skill will live. No research.md was performed for RUS-21, so all claims below are derived from the ticket description and questions — they remain [UNVERIFIED] pending actual codebase exploration.

**Skill directory pattern.** The workspace stores all skills under `.claude/skills/<name>/`. Each skill directory contains a `SKILL.md` file with YAML frontmatter (name, description, command, argument-hint, allowed-tools) followed by body text. No existing skill has `references/`, `scripts/`, or `assets/` subdirectories — all 10 currently registered skills (qrspi-design, qrspi-implement, qrspi-plan, qrpsi-pr, qrspi-questions, qrspi-research, qrpsi-structure, qrpsi-ticket, qrpsi-work, qrpsi-worktree) are single-file. The `writing-bash-scripts` skill directory exists but has no SKILL.md file (it may be a placeholder or externally managed). [UNVERIFIED]

**Slash-command registration.** Each skill is invoked via a slash command like `/qrspi-design`. The command name typically matches the directory name (minus the `qrspi-` prefix in some cases). The wrapper scripts are thin: they parse `$ARGUMENTS`, fetch ticket data from Linear, then spawn the corresponding agent via the Agent tool. [UNVERIFIED]

**Agent definitions.** Phase agents live in `.claude/agents/` as markdown files (e.g., `qrspi-design.md`) that define the prompts and behavior for each phase. The slash-command skills act as thin wrappers that invoke these agents. This two-level structure (skill wrapper + agent definition) is worth understanding when deciding whether the `using-codex-cli` skill needs an agent or can be a standalone SKILL.md. [UNVERIVED]

**agentskills.io convention.** Per the ticket, the new skill should follow the agentskills.io directory structure: a `SKILL.md` frontmatter block plus optional `references/`, `scripts/`, and/or `assets/` subdirectories. The ticket references agentskills.io but no existing skill in this repo explicitly implements that spec — they use YAML frontmatter which is consistent with the pattern. [UNVERIFIED]

## Desired End State

After the feature ships, the workspace will contain:

1. **A new skill at `.claude/skills/using-codex-cli/`** containing:
   - `SKILL.md` with valid YAML frontmatter (name, description) and body under 500 lines / 5000 tokens
   - Optional `references/` directory with detailed Codex CLI reference material
   - Optional `scripts/` or `assets/` if reusable scripts or templates are included

2. **The SKILL.md body encodes the following Codex CLI conventions:**

   | Acceptance Criterion | Concrete System Behavior |
   |---|---|
   | Follows agentskills.io directory structure with valid frontmatter | SKILL.md starts with `---` frontmatter block containing `name: using-codex-cli`, `description`, and any other required fields per the spec |
   | Built using Anthropic skill builder skill | The design guides implementation through the `skill-creator` skill (invoked via `/skill-creator` or the mcp-builder pattern) |
   | SKILL.md body under 500 lines / 5000 tokens | Body text (after frontmatter delimiter `---`) must be counted at validation time; design keeps reference material lean and in separate files if needed |
   | Covers all three approval modes with guidance | Section documents suggest, auto-edit, and full-auto modes with a decision matrix: local dev → suggest; trusted iterative → auto-edit; CI/containers → full-auto |
   | Documents sandbox modes and platform enforcement | Section covers read-only, workspace-write, danger-full-access across macOS (Seatbelt/sandbox-exec) and Linux (bubblewrap+bwrap+Landlock), with explicit guidance to keep network off by default |
   | Includes codex exec patterns for automation | Dedicated section for `codex exec` covering positional arg, stdin `-`, prompt-plus-stdin piping, `--json` output, `--quiet` mode, `--ignore-user-config`, and `--ignore-rules` |
   | Covers AGENTS.md hierarchy and custom instructions | Section documents the cascading discovery: `AGENTS.override.md` first, then `AGENTS.md`, concatenated with deeper precedence; 32 KiB size limit enforcement; nested directory rules |
   | Documents MCP server exposure and multi-agent orchestration | Section covers `codex()` and `codex-reply()` tools, agents SDK integration patterns, subagent spawning discipline (only when explicitly requested), git worktrees for parallel agents, and custom agent definitions |
   | Includes configuration reference for config.toml | Section documents user-level (`~/.codex/config.toml`) and project-level (`.codex/config.toml`), profiles via `[profiles.<name>]`, model settings, feature flags (`codex features enable/disable`), and `model_instructions_file` |
   | Addresses known limitations and workarounds | Documents: re-run non-determinism (use unit tests as guardrails), macOS network access bugs (use `--sandbox` flag override), long-chain limits (prefer Claude Code for those), context window pressure (fresh sessions for discrete tasks), sandbox config bugs (verify with explicit CLI flags) |
   | Provides Unix pipe composition examples | Concrete examples: `command | codex exec "analyze this"`, multi-codex chaining via stdout, `codex exec -` for stdin-as-prompt, and CI pipeline patterns with `--json` piping |

3. **A design document that guides the implementer** through building this skill. This document must be reviewed before implementation begins.

## Delta

### New files to create

| Path | Purpose |
|---|---|
| `.claude/skills/using-codex-cli/SKILL.md` | Primary skill definition; frontmatter + body with all Codex CLI conventions |
| `.claude/skills/using-codex-cli/references/approval-modes.md` (optional) | Deep-dive on approval mode selection with concrete scenarios |
| `.claude/skills/using-codex-cli/references/sandbox-modes.md` (optional) | Platform-specific sandbox enforcement details for macOS and Linux |
| `.claude/skills/using-codex-cli/references/config-reference.md` (optional) | Full config.toml schema with profile examples |
| `.claude/skills/using-codex-cli/references/codex-exec-patterns.md` (optional) | `codex exec` patterns, pipe compositions, CI integration examples |
| `.claude/skills/using-codex-cli/references/mcp-server-mode.md` (optional) | MCP server wire protocol, tool call schemas, orchestration patterns |
| `.claude/skills/using-codex-cli/references/agents-hierarchy.md` (optional) | AGENTS.md / AGENTS.override.md cascade rules and size enforcement |
| `.claude/skills/using-codex-cli/references/limitations-and-workarounds.md` (optional) | Known bugs, edge cases, recommended workarounds |

### Modified files

None. This skill is a greenfield addition; no existing files need modification.

### Patterns to reference in implementation

1. **SKILL.md frontmatter schema** — Follow the pattern from existing skills: YAML `---` delimiters with `name`, `description`, and any additional fields required by agentskills.io.
2. **Directory structure** — The new skill is the first to use optional subdirectories (`references/`). All 10 existing skills are single-file. This introduces a precedent for splitting reference material out of the main SKILL.md body.
3. **No agent definition needed** — Unlike the qrspi-* skills, this skill is a reference/tool skill invoked directly (not as a wrapper around a phase agent). It likely lives in `.claude/skills/` without a corresponding `.claude/agents/` entry.

## Pattern Decisions

### Decision 1: Single-file SKILL.md vs. Split into references/

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Single SKILL.md body only | Simpler; matches all 10 existing skills in the repo; no new pattern introduced | Body must stay under 500 lines and 5000 tokens; risks becoming a wall of text covering 8+ topics with examples |
| B | Split into references/ subdirectory | Each reference file stays focused and readable; easier for humans to locate specific info; SKILL.md body stays lean as a table-of-contents + quick-reference | Introduces a new pattern (subdirectories) not seen in existing skills; agents must know to read references/ in addition to SKILL.md |

**Recommendation:** Option B, but constrained. Split only the heaviest sections into `references/`: config reference, codex exec patterns, MCP server mode, and limitations/workarounds. Keep approval modes, sandbox modes, session management, and AGENTS.md hierarchy directly in SKILL.md body. This keeps the body under ~250 lines while giving depth where needed.

**Rationale:** The ticket explicitly allows `references/` as optional ("Detailed reference material in references/ directory if needed"). The content scope (8+ topics with examples) makes a single file unwieldy. Existing skills are all small; this is the first large one. Splitting follows the precedent that reference-heavy documentation lives separately (see `.claude/skills/qrspi-work/references/` which already exists in this repo). NEW PATTERN: Yes — this is the first skill to use subdirectories. The existing `qrpsi-work/references/` directory suggests the pattern is latent but unproven. Justify: the ticket explicitly invites `references/`, and at least one other skill uses it.

### Decision 2: Agent definition for using-codex-cli

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Standalone SKILL.md only (no agent) | Simpler; matches the nature of this skill as a reference/tool skill rather than a workflow phase; avoids over-engineering | Agents cannot be spawned with specialized prompts for codex tasks; less structured invocation |
| B | Create `.claude/agents/using-codex-cli.md` | Provides a dedicated prompt for complex multi-agent codex orchestration tasks; aligns with the agent-centric philosophy of this repo | Overkill for a reference skill; no evidence that agents are needed for this ticket's scope |

**Recommendation:** Option A. The ticket describes a skill (a knowledge document guiding agents when *they* use Codex CLI), not an agent that runs Codex on their own behalf. This is a reference skill like `writing-bash-scripts` — it encodes how-to knowledge for the Claude Code harness, not autonomous behavior.

**Rationale:** The qrpsi-* skills are all workflow phases (design, research, plan, implement) that have both a slash-command wrapper and a phase agent. This skill is different: it guides the *invoking* agent on how to use Codex CLI for coding tasks. It is knowledge, not an autonomous worker. No `.claude/agents/` entry is needed. NEW PATTERN: No — standalone SKILL.md without a matching agent already exists (e.g., `writing-bash-scripts` may follow this pattern).

### Decision 3: Scope of config.toml documentation in the skill

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Inline all config.toml fields as a reference table | Self-contained; agents see everything they need without reading separate files | Bloates the body toward the 500-line limit; tables become hard to scan |
| B | Put full config schema in `references/config-reference.md`; provide a quick-start table in SKILL.md body | Body stays lean; detailed config lives where it is easier to update | Slight cognitive load: agents must know to consult references/ for deep config info |

**Recommendation:** Option B. The ticket describes 12+ distinct config.toml fields (model, model_provider, sandbox settings, approval policies, MCP server definitions, profiles, feature flags, model_instructions_file, project_doc_max_bytes, project_doc_fallback_filenames). This warrants a dedicated reference file. A condensed table in the SKILL.md body suffices for quick access.

**Rationale:** The ticket explicitly allows `references/` for this purpose. Config schemas are inherently large and change independently of Codex CLI operational patterns. Separation improves maintainability. NEW PATTERN: No — config references as separate files is standard documentation practice.

### Decision 4: MCP Server mode depth in the skill

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Surface-level: describe what MCP server mode does, point to external docs | Minimal body expansion; reduces risk of stale internal documentation | Agents lack actionable detail for actually configuring and using MCP mode |
| B | Practical depth: include wire protocol parameter names, example tool call schemas, and a concrete multi-agent orchestration pattern with `codex()` and `codex-reply()` | Actionable; agents can implement real multi-agent pipelines from the skill alone | Body weight increases; must keep examples concise |

**Recommendation:** Option B, but limited to 2-3 concrete examples. The ticket explicitly calls out preferring MCP server mode over ad-hoc subagent spawning for reproducibility and auditability. Agents need enough detail to implement this, not just be told it exists. Keep the section to ~40 lines with two worked examples: (1) orchestrator → `codex()` tool call pattern, (2) nested pipeline with `codex-reply()`.

**Rationale:** The ticket calls multi-agent MCP server mode a key judgment area ("prefer MCP over ad-hoc subagent spawning"). Surface-level docs would undermine this guidance. But the scope must be bounded — detailed protocol specs belong in `references/mcp-server-mode.md` while the body has just enough for practical use. NEW PATTERN: No — MCP tool usage follows existing patterns (agents invoke tools via function calls).

### Decision 5: How to handle re-run non-determinism guidance

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Encode a strict rule: "Never re-run the same prompt without first running tests" | Simple, actionable, prevents regression at the behavioral level | May be too opinionated; doesn't explain *how* to run tests from within Codex |
| B | Provide a decision flowchart: before re-running, check for existing unit tests → if present, run them → if they pass, accept the new output → if they fail, investigate the diff | More thorough; covers edge cases where no tests exist | Adds ~20 lines to the body; slightly complex for what should be a simple guardrail |

**Recommendation:** Option B in SKILL.md body (condensed flowchart form), with full examples and CI integration patterns in `references/limitations-and-workarounds.md`. The flowchart should show: (1) re-run same prompt → (2) compare diff → (3) run test suite → (4) accept or rollback.

**Rationale:** The ticket flags re-run non-determinism as a known limitation. This is one of the most operationally important sections because agents will invoke Codex multiple times on the same task. A flowchart format (decision tree using text arrows) keeps it scannable while being thorough. NEW PATTERN: No — deterministic guardrails via test suites are standard engineering practice.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| SKILL.md body exceeds 500 lines / 5000 tokens during implementation | medium | high | Split heavy sections into references/ during design (Decisions 1 and 3); implement a line-count validation step in the plan phase; use the `skill-creator` skill which may have built-in length checks |
| agentskills.io frontmatter schema changes between spec version and implementation time | low | medium | Pin the SKILL.md frontmatter to the latest known stable fields (name, description); add a comment referencing the agentskills.io URL; validate with the skill-creator's validation logic |
| The existing skills in this repo do not actually follow agentskills.io — they use YAML frontmatter that may be a qrspi-specific convention, not an agentskills.io standard | medium | high | During design revision, verify whether existing skills' frontmatter matches agentskills.io spec. If not, either (a) update all existing skills or (b) accept this skill diverges. Flag as a design-level decision for the human. |
| Over-documenting reduces agent adoption; agents skip sections they perceive as too long | medium | medium | Keep SKILL.md body focused on actionable guidance (<250 lines); move deep references to subdirectory; use tables and code blocks for scannability; lead with a mode-selection matrix agents can copy-paste |
| Research phase was skipped — design lacks codebase grounding | low (mitigated) | high | This design explicitly notes where claims are [UNVERIFIED]; during the plan phase, require that an actual research pass runs before implementation to validate assumptions about directory structure and patterns |
| macOS Seatbelt sandbox config bugs mean documented `network_access = true` in config.toml does not work; agents follow broken guidance | low | medium | The design explicitly recommends using `--sandbox` CLI flag override rather than relying on config.toml. Document this as a workaround, not an afterthought. Test with `--sandbox workspace-write` before escalating to full-auto. |

## Open Questions

- OQ1: Does the agentskills.io spec require any frontmatter fields beyond `name` and `description`? The existing qrspi-* skills only use those two. If additional fields are mandatory (e.g., `version`, `author`, `command`), should this skill diverge from all existing skills in the repo?
- OQ2: Should `using-codex-cli` be given a slash-command wrapper (e.g., `/using-codex-cli`) to make it discoverable alongside the qrspi-* commands, or is directory placement under `.claude/skills/` sufficient for discovery by the harness?
- OQ3: The ticket says "Use the Anthropic skill builder skill to generate the skill." Which concrete skill name does this refer to — `skill-creator`, `mcp-builder`, or another mechanism? Is there a pre-existing skill whose output I should examine as a template before writing this one?
- OQ4: For the MCP server mode examples in the skill, what level of protocol detail is appropriate — just parameter names and return types, or actual JSON wire payloads that an orchestrator agent could copy into its tool calls?
- OQ5: The `references/` subdirectory pattern is new to this repo (except for `qrspi-work/references/`). Should the plan phase create example placeholder files in `references/` to establish the convention, or are they purely empty scaffolding?
