# Design — Create a new agent skill for using the Gemini CLI

**Ticket:** RUS-22
**Research basis:** research.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## Current State

Skills in this repository live at `.claude/skills/<skill-name>/SKILL.md`, one `SKILL.md` per directory, with the directory name matching the `name:` frontmatter field (ref: Q1). All ten existing skills are `qrspi-*` workflow phases (ref: Q1). The only subdirectory used by any skill is `qrspi-work/references/`, which holds one long-form file factored out of the body; `scripts/` and `assets/` subdirectories have no in-repo precedent (ref: Q1).

Every in-repo `SKILL.md` uses YAML frontmatter with five fields: `name`, `description`, `command`, `argument-hint`, and `allowed-tools` (ref: Q3). No JSON schema or loader enforces these fields in-repo — skill loading is handled by the external Claude Code harness — so "required" is inferred from consistent convention (ref: Q3). Descriptions follow a "capability + explicit trigger" shape, using "Use when…/Use after…/Trigger on any variant of…" phrasing, sometimes enumerating example invocations; names are lowercase, hyphenated, domain-prefixed (ref: Q4).

Most skills are thin wrappers (25–35 lines) that parse `$ARGUMENTS`, resolve `REPO_ROOT` from `pwd`, and spawn a `subagent_type` agent, deferring all domain content to `.claude/agents/<name>.md` (ref: Q2, Q6). The two exceptions embed content directly: `qrspi-ticket` (119 lines, inline prompt) and `qrspi-work` (730 lines, orchestrator) (ref: Q6). The 500-line / 5000-token budget is not enforced anywhere, and `qrspi-work` overruns it (ref: Q6). The only demonstrated body→reference link pattern is `qrspi-work` delegating cascade logic to `references/review-cascade.md` (ref: Q5).

No in-repo skill wraps an external CLI (ref: Q5). The closest model for evaluating an external-CLI skill is `evals/graphite-evals.json`, which grades produced commands, flags, and safety behavior with assertion types `command_check`, `flag_check`, `content_check`, `workflow_check`, and `safety_check` (ref: Q5, Q11). The skill-builder/`skill-creator` skill named in the ticket is global (under `~/.claude/`) and outside repo scope — it is NOT FOUND in-repo (ref: Q2).

Three safety-surfacing patterns exist: `allowed-tools` allowlisting with argument scoping (e.g., `Bash(pwd:*)`); named "Hard constraints" and "HARD STOP: Infrastructure Errors" prose blocks in agent prompts; and `safety_check` eval assertions requiring confirmation before destructive operations (ref: Q8). No in-repo convention documents tool deprecation/migration notices (ref: Q7) or config-precedence hierarchies (ref: Q9). The eval harness is a 5-stage Python pipeline but agent execution, LLM-judge, and script checks are stubs, with 17/21 fixtures missing — "runs end-to-end but produces zeros" (ref: Q10, Q11). No in-repo module records skill invocation at runtime; observability is via operator stdout, Linear status, and offline eval results (ref: Q12).

## Desired End State

A new self-contained skill exists at `.claude/skills/using-gemini-cli/SKILL.md` with a `references/` directory for deep material. Acceptance criteria map to behavior as follows:

- **agentskills.io structure + valid frontmatter** → directory follows `.claude/skills/<name>/SKILL.md` with `references/` (ref: Q1); frontmatter carries the five in-repo fields (ref: Q3).
- **Built using the skill-builder skill** → satisfied at authoring time by invoking the global `skill-creator` skill; not an in-repo artifact (ref: Q2). See OQ1.
- **Body under 500 lines / 5000 tokens** → body holds control-flow + quick reference; deep tables move to `references/` (ref: Q5, Q6).
- **Detailed reference material in `references/`** → `references/` files cover sandbox profiles, configuration hierarchy, subagents, MCP/extensions (ref: Q5).
- **Installation, auth, invocation (interactive/non-interactive/piped)** → covered in body.
- **Full permission/approval model (default, auto_edit, yolo) with when-to-use** → body section + a named risk block following the Hard-constraints pattern (ref: Q8).
- **Sandbox mode configuration + when to enable** → body summary + `references/sandbox.md`.
- **GEMINI.md context hierarchy + best practices** → reference file (ref: Q9 — new precedence-doc territory).
- **MCP server config + extension installation** → reference file.
- **Subagent definition, routing, tool grants** → reference file (primary multi-agent pattern).
- **Multi-agent orchestration from external agents** → body section, emphasizing non-interactive `-p`, stdin piping, filesystem coordination, `--sandbox`.
- **June 2026 deprecation / Antigravity note** → a named, dated caveat block — a new convention since none exists (ref: Q7).
- **Actionable examples (code review, test gen, codebase exploration)** → body workflow examples, prose-only per QRSPI artifact rules.

## Delta

- **New file** `.claude/skills/using-gemini-cli/SKILL.md` — frontmatter (`name: using-gemini-cli`, capability+trigger `description`, `command: /using-gemini-cli`, `argument-hint`, `allowed-tools`); body with installation/auth/invocation, approval model, sandbox summary, orchestration patterns, workflow examples, deprecation note, and links into `references/`.
- **New files** under `.claude/skills/using-gemini-cli/references/` — candidate split: `sandbox.md`, `configuration.md` (GEMINI.md hierarchy + settings precedence), `subagents.md`, `mcp-and-extensions.md`. Final split decided in Structure phase (see OQ2).
- **New file (recommended)** `evals/gemini-cli-evals.json` — mirrors the `graphite-evals.json` shape (`skill_name`, `evals[]` with `command_check`/`flag_check`/`safety_check`) to validate command/flag/safety guidance (ref: Q5, Q11). Scoring will not run until harness stubs are implemented (ref: Q10).
- **No agent file** in `.claude/agents/` — this is a content skill, not a wrapper→agent phase (see Decision 1).
- **Possible doc fix (out of scope, note only):** `.claude/CLAUDE.md` misstates the agents path as `.qrspi/agents/` (ref: Inconsistencies).

## Pattern Decisions

### Decision 1: Skill shape — self-contained content vs. wrapper→agent

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Self-contained SKILL.md + `references/` (like the global `using-graphite-cli`) | Matches a CLI-usage skill's purpose; content is directly discoverable; no agent indirection | Diverges from the in-repo `qrspi-*` wrapper→agent norm |
| B | Thin wrapper SKILL.md delegating to `.claude/agents/using-gemini-cli.md` | Matches the dominant in-repo pattern (ref: Q2, Q6) | Wrapper→agent exists for artifact-generating phases, not reference content; adds indirection with no caller/arguments |

**Recommendation:** Option A
**Rationale:** The wrapper→agent pattern serves QRSPI phase skills that spawn a subagent to write an artifact (ref: Q2). This skill provides usage guidance with no ticket argument or artifact output, matching the content-skill model. `qrspi-ticket` already shows in-repo precedent for embedding content directly rather than delegating (ref: Q6).
**NEW PATTERN?** Partially — first in-repo *content/reference* skill (all current skills are `qrspi-*` wrappers, ref: Q1). The structure reuses the demonstrated `references/` split (ref: Q5); only the "non-wrapper, non-phase" role is new.

### Decision 2: Body/reference split for the 500-line budget

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Keep control-flow + quick reference in body; push sandbox/config/subagents/MCP detail to `references/` | Follows the only in-repo split precedent (ref: Q5); keeps body under budget (ref: Q6) | Requires deciding the reference file boundaries |
| B | Single large SKILL.md, everything inline | Simplest authoring | Likely exceeds the 500-line budget, repeating the `qrspi-work` overrun (ref: Q6) |

**Recommendation:** Option A
**Rationale:** `qrspi-work` factoring `review-cascade.md` is the established budget-control technique (ref: Q5, Q6); the ticket explicitly calls for `references/` when needed.
**NEW PATTERN?** No — reuses the `references/` extraction pattern (ref: Q5).

### Decision 3: Surfacing destructive operations (yolo / sandbox-off)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Named "When to use each mode" + a prominent risk/caution block, mirroring "Hard constraints" prose sections (ref: Q8) | Follows established surface-don't-bury convention (ref: Q8); readable | Prose-only, not machine-enforced |
| B | Add `safety_check` eval assertions in `evals/gemini-cli-evals.json` (ref: Q8, Q11) | Machine-gradable safety expectations like Graphite (ref: Q8) | Grader stubs mean it won't score yet (ref: Q10) |

**Recommendation:** Both A and B
**Rationale:** The repo surfaces risk as named sections *and* `safety_check` assertions (ref: Q8); using both matches precedent and prepares for when the harness is implemented (ref: Q10).
**NEW PATTERN?** No for A/B mechanics; the eval file for a *second* external CLI extends the `graphite-evals.json` precedent (ref: Q5).

### Decision 4: Encoding the deprecation/migration timeline note

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | A dated, named caveat block (e.g., "Deprecation timeline") in the body | Surfaces the June 2026 / Antigravity AC prominently | No existing in-repo format to copy (ref: Q7) |
| B | Inline footnote within the installation section | Minimal | Buries a time-sensitive caveat against the surface-don't-bury norm (ref: Q8) |

**Recommendation:** Option A
**Rationale:** No deprecation-note convention exists (ref: Q7), so one must be introduced; the named-section style aligns with how risk is surfaced elsewhere (ref: Q8).
**NEW PATTERN?** Yes — no in-repo precedent documents tool deprecation timelines (ref: Q7); justified because the AC explicitly requires the note and the surface-don't-bury norm (ref: Q8) argues for a named block over a footnote.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Skill content describes the wrong CLI: ticket says `npm install -g @anthropic-ai/gemini-cli`, but Gemini CLI is a Google product — package name likely incorrect | high | high | Verify the real package/invocation at authoring time; flag as OQ3. Do not encode an unverified install command. |
| Body exceeds the 500-line budget, repeating the `qrspi-work` overrun (ref: Q6) | med | low | Apply Decision 2 split early; the budget is unenforced (ref: Q6) so rely on review. |
| New skill cannot be validated: eval harness execution/judge/script checks are stubs (ref: Q10) | high | med | Author `gemini-cli-evals.json` assertions now (ref: Q11); accept they score zero until stubs are implemented; rely on human review for content correctness. |
| Adopting the self-contained shape (Decision 1) confuses future maintainers expecting wrapper→agent (ref: Q2) | med | low | Note the deliberate divergence in the design and PR; cite `qrspi-ticket` inline precedent (ref: Q6). |
| Deprecation note goes stale or the June 2026 date passes before merge | med | med | Use a dated, clearly-scoped block (Decision 4); revisit during review given today is 2026-05-31. |

## Open Questions

- OQ1: AC requires the skill be "built using the Anthropic skill builder skill," which is global and out of repo scope (ref: Q2). Confirm this is an authoring-process requirement (invoke `skill-creator` during creation) and not an in-repo artifact to produce.
- OQ2: Final `references/` file boundaries — one combined reference vs. the four-file split proposed in Delta. Defer to Structure phase or decide now?
- OQ3: The ticket's install command `npm install -g @anthropic-ai/gemini-cli` appears to misattribute Gemini CLI to Anthropic. Which package name / invocation is authoritative? This blocks the installation section.
- OQ4: Should `evals/gemini-cli-evals.json` be in scope for this ticket, given the harness cannot score it yet (ref: Q10), or deferred until the stubs are implemented?
- OQ5: Should this ticket also fix the `.claude/CLAUDE.md` agents-path inconsistency (ref: Inconsistencies), or is that strictly out of scope?
