# Design — Create `using-gemini-cli` Agent Skill

**Ticket:** RUS-22
**Research basis:** research.md @ 2026-06-03T00:00:00Z
**Generated:** 2026-06-03T00:00:00Z
**Status:** draft

## Current State

The repo has no Gemini CLI integration of any kind — no Gemini/Antigravity code, config, env var, or reference exists anywhere under the repo root (ref: scope note; ref: Q5). This ticket adds a pure-documentation skill, so the constraints are entirely about how the repo's skill infrastructure works.

Skills live as one directory per skill under `.claude/skills/<name>/`, each containing a `SKILL.md` with YAML frontmatter; heavyweight phase-agent prompt bodies live as flat files `.claude/agents/<name>.md` (ref: Q1). The two-layer split — a thin slash-command wrapper that spawns a same-named agent — is a project convention for QRSPI *lifecycle* phases (ref: Q1, ref: Q3). Not every skill follows it: `qrspi-ticket` and `qrspi-work` carry full logic inline in their `SKILL.md` with no spawned agent, and this self-contained form is the closest precedent for a "how to use tool X" skill like this one (ref: Q3, Discovered Patterns).

`SKILL.md` frontmatter fields observed in-repo are `name`, `description`, `command`, `argument-hint`, and `allowed-tools` (ref: Q1). Supplementary material is exposed by placing files in a `references/` subdirectory and referencing them by relative path from the `SKILL.md` prose — there is no declarative manifest; the model is simply told to read them (ref: Q1). The only in-repo example is `.claude/skills/qrspi-work/references/review-cascade.md`; no skill directory contains a `scripts/` or `assets/` subdir (ref: Q1, ref: Q3).

Skills are discovered by convention: there is no manifest, glob config, `.claude/settings.json`, or registry anywhere in the repo. The Claude Code harness keys each skill by its frontmatter `name`/`command` and each agent by its `name`; adding a skill requires no registration edit (ref: Q4). All existing skills are `qrspi-*` namespaced, but the un-namespaced `using-*` style (matching the global `using-graphite-cli` skill) is the appropriate convention for a non-phase utility skill (ref: Q4, Inconsistencies).

Tools are declared in `allowed-tools` frontmatter and then invoked by exact tool name in the prose; a tool not listed cannot be used, and names are case-sensitive (ref: Q6). The canonical tool vocabulary is `Read, Write, Edit, Glob, Grep, Bash, Agent` — note the editing tool is `Edit`, not "replace" (ref: Q6). External CLIs are always run through `Bash`; there is no dedicated shell/subprocess tool (ref: Q6, Discovered Patterns).

The repo's relevant content conventions: stateless handoff via explicit inputs plus on-disk artifacts rather than session state (ref: Q7); a HARD-STOP-on-error contract — surface the exact error verbatim, never retry or improvise on infra/tooling failures (ref: Q10); and pinning time-bound caveats to verified tool versions/dates in prose (ref: Q9). `CLAUDE.md`/`AGENTS.md` layered context via `@import` is the in-repo analog for a layered context-file hierarchy (ref: Q8).

The `evals/` + `scripts/run_eval.py` harness is a non-functional placeholder that returns empty output (ref: Q12). There are no integration tests for any skill or agent; only Python orchestration modules carry stdlib `_test.py` unit tests, and skills are verified by manual end-to-end runs (ref: Q12, ref: Q13). There is no application-level observability layer for skill/CLI invocation (ref: Q14).

## Desired End State

A new skill at `.claude/skills/using-gemini-cli/` that guides agents using the Google Gemini CLI. Acceptance criteria map to behavior as follows:

- **agentskills.io structure + valid `SKILL.md` frontmatter** → a `SKILL.md` with valid YAML frontmatter (`name`, `description`, and, since it is invocable, `allowed-tools`) plus optional `references/` (ref: Q1, ref: Q3).
- **Built using the Anthropic skill builder skill** → authored via the `skill-creator` skill and its eval loop (process requirement; satisfied during implementation).
- **Body under 500 lines / 5000 tokens** → `SKILL.md` body stays terse; overflow detail moves into `references/` (ref: Q1).
- **Detailed reference material in `references/`** → deep-dive content (permission model, sandbox profiles, MCP/extensions, subagents, orchestration) lives in `references/*.md`, referenced by relative path from prose (ref: Q1).
- **Installation / authentication / invocation (interactive, non-interactive, piped)** → a dedicated `SKILL.md` section covering `npm`/`npx` install, Google-account vs. API-key auth, and the interactive / `-p` / stdin-pipe modes.
- **Full permission/approval model (default, auto_edit, yolo) with when-to-use guidance** → a permission-model section with the HARD-STOP-on-error framing applied to approval prompts (ref: Q10).
- **Sandbox mode configuration and when to enable it** → a sandbox section covering `--sandbox`/`-s`, profiles, and `SANDBOX_MOUNTS`, recommending sandbox for autonomous/subagent use (ref: Q11).
- **GEMINI.md context-file hierarchy and best practices** → a section mirroring the layered context-file convention (ref: Q8).
- **MCP server config and extension installation** → a section on `mcpServers` config and `gemini extensions install`, focused on Gemini specifics only.
- **Subagent definition, routing, tool grants** → a subagents section covering `.gemini/agents/*.md`, routing/`@agent-name`, and wildcard tool grants.
- **Multi-agent orchestration patterns for calling Gemini from external agents** → an orchestration section: non-interactive `-p`, stdin context, stdout capture, filesystem coordination, `--sandbox` — encoded via `Bash` as the invocation mechanism (ref: Q6).
- **June 2026 deprecation / Antigravity transition note** → a limitations section, caveat pinned to the date and the pre-migration tool state (ref: Q9).
- **Actionable examples for common workflows** → worked examples for code review, test generation, and codebase exploration.

## Delta

**New files:**
- `.claude/skills/using-gemini-cli/SKILL.md` — frontmatter + concise body covering all in-scope sections; under 500 lines / 5000 tokens.
- `.claude/skills/using-gemini-cli/references/*.md` — one or more deep-dive references (proposed: `permissions-and-sandbox.md`, `orchestration.md`, `subagents-mcp-extensions.md`), referenced by relative path from prose.

**Modified files:** None required. Discovery is by convention; no registry, `.claude/settings.json`, or README edit is needed for the harness to find the skill (ref: Q4). Adding a one-line mention to the README skill list is optional and human-discretionary (not required for function).

**No new code, queries, scripts, or tests** are mandated: this is a pure-markdown skill, which carries no automated test under current conventions (ref: Q13).

## Pattern Decisions

### Decision 1: Skill shape — self-contained vs. thin-wrapper-plus-agent

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Self-contained `SKILL.md` (+ `references/`), no spawned agent — like `qrspi-ticket`/`qrspi-work` | Matches the precedent for non-phase "how-to-use-tool" skills; nothing to register; simplest | `SKILL.md` must stay terse to meet the 500-line cap, pushing detail to references |
| B | Thin `SKILL.md` wrapper spawning a `using-gemini-cli` agent in `.claude/agents/` | Matches the QRSPI phase convention | Wrong precedent — phase agents exist to do multi-step lifecycle work; this skill is reference content, not an orchestration phase; adds an unused agent file |

**Recommendation:** Option A
**Rationale:** Research identifies the self-contained form (`qrspi-ticket`, `qrspi-work`) as the closest precedent for a tool-usage skill, distinct from the thin-wrapper phase skills (ref: Q3, Discovered Patterns). No agent body is needed because the skill imparts knowledge rather than executing a lifecycle phase.
**NEW PATTERN?** No — follows the existing self-contained SKILL.md pattern.

### Decision 2: Where detail lives — single `SKILL.md` vs. `references/` split

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Everything in one `SKILL.md` | Single file to read | Ticket mandates < 500 lines / 5000 tokens; the topic surface (permissions, sandbox, MCP, extensions, subagents, orchestration) will exceed it |
| B | Concise `SKILL.md` overview + `references/*.md` deep dives | Meets the size cap; uses the documented `references/` mechanism (ref: Q1) | Multiple files; relies on the model reading referenced files on demand |

**Recommendation:** Option B
**Rationale:** The `references/` subdir is the established overflow mechanism, with `qrspi-work/references/review-cascade.md` as the in-repo example (ref: Q1). The breadth of required coverage makes the size cap infeasible in a single file.
**NEW PATTERN?** No.

### Decision 3: How Gemini-CLI invocation is encoded for external-agent orchestration

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Document invocation via the `Bash` tool (`gemini -p ...`, stdin pipes, stdout capture), listing `Bash` in `allowed-tools` | Matches the in-repo convention — all external CLIs run through `Bash` (ref: Q6); no new tool concept | Caller must have `Bash` granted |
| B | Imply a dedicated shell/subprocess tool | — | No such tool exists in the repo; would be incorrect (ref: Q6) |

**Recommendation:** Option A
**Rationale:** `Bash` is the only external-CLI invocation mechanism in the repo (ref: Q6, Discovered Patterns). Orchestration guidance should also adopt the stateless-handoff convention (explicit inputs + on-disk files) for cross-call continuity, since Gemini non-interactive mode lacks session persistence (ref: Q7), and the HARD-STOP-on-error contract for failed/blocked invocations (ref: Q10).
**NEW PATTERN?** No.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Gemini-specific facts (flags, env vars, sandbox profiles, deprecation date) are unverifiable in-repo and may be stale or wrong | high | high | Ticket body supplies these as authoritative source; during implementation, pin each caveat to a verified Gemini CLI version/date in prose per the repo convention (ref: Q9); flag any that the author cannot confirm |
| `SKILL.md` exceeds the 500-line / 5000-token cap given the topic breadth | med | med | Adopt the references split (Decision 2); keep `SKILL.md` an overview with pointers; check size during `skill-creator` eval loop |
| "sandbox"/"yolo" terms conflated with unrelated in-repo `yolo` bash wrapper and JS workflow "sandbox" | med | low | Scope all such terms explicitly to Gemini CLI in the skill; do not cross-reference the devcontainer `yolo()` function or workflow sandbox (ref: Inconsistencies) |
| Skill description triggers poorly (mis-fires or fails to fire) | med | med | Use `skill-creator`'s description-optimization/eval loop; mirror the `using-graphite-cli` description style (ref: Q4, Inconsistencies) |
| No automated test can prove the skill works under current conventions | med | low | Accept manual end-to-end verification per repo convention (ref: Q12, ref: Q13); do not cite `run_eval.py` as a validation mechanism |

## Open Questions

- OQ1: Should the README skill list be updated to mention `using-gemini-cli`, or is auto-discovery (no README edit) acceptable? (Function does not require it — ref: Q4.)
- OQ2: Is `using-gemini-cli` the final skill name, accepting it will not visually group with the `qrspi-*` lifecycle skills (ref: Inconsistencies)?
- OQ3: What is the authoritative source-of-truth and as-of date for the Gemini-specific facts (flag names, sandbox profile names, the June 18 2026 deprecation), so caveats can be pinned to a verified version? The repo cannot supply these (ref: Q5, ref: Q9, ref: Q11).
- OQ4: How much depth on Antigravity CLI migration belongs in this skill versus a brief forward-pointer, given the tool remains current until June 2026?
