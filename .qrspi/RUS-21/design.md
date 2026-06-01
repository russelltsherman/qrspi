# Design — Create a new agent skill for using the Codex CLI

**Ticket:** RUS-21
**Research basis:** research.md @ 2026-06-01T00:00:00Z
**Generated:** 2026-06-01T00:00:00Z
**Status:** draft

## Current State

Skills in this repo live under `.claude/skills/<skill-name>/SKILL.md`, one directory per skill, with an optional `references/` subdirectory for on-demand detail (ref: Q1). No skill currently uses a `scripts/` or `assets/` subdirectory; the only multi-file example is `qrspi-work`, which factors one cohesive topic into `references/review-cascade.md` (ref: Q1, ref: Q8). Repo-level automation lives in the top-level `scripts/` directory, not inside skill folders (ref: Q1, ref: Q8).

There is no formal frontmatter schema in-repo; the schema is observable only by convention across the ten existing `SKILL.md` files (ref: Q3). Two frontmatter shapes exist: skill wrappers use `name`, `description`, `command`, `argument-hint`, and `allowed-tools`; agent files use `name`, `description`, `model`, and a nested `claude.tools` block (ref: Q3). Registration is purely by file placement plus valid frontmatter — there is no manifest, index, or registry file (ref: Q4). The `command` field defines the slash invocation; the `description` field is the trigger surface that drives auto-invocation matching (ref: Q4, ref: Q6).

The QRSPI phase skills follow a wrapper/agent split: a thin `SKILL.md` wrapper spawns a same-named agent from `.claude/agents/<name>.md`, where the substantive prompt lives (ref: Q1). Two skills, `qrspi-ticket` and `qrspi-work`, are exceptions — they carry full logic in their `SKILL.md` with no paired agent file (ref: Q1).

The `description` convention is two-part — what the skill does plus when to use it — often with literal trigger phrases and, for agents, negative scoping such as "Not for general codebase exploration" (ref: Q6). References sit under `<skill-dir>/references/` and are addressed by relative path, loaded on demand as progressive disclosure (ref: Q5).

There is NO in-repo tooling that measures or enforces SKILL.md body size; the eval suite's `line_count` and `code_snippets_under_limit` checks apply only to generated QRSPI artifacts (design.md, research.md), not to skill source files, so any size budget is manual and editorial (ref: Q7). There is also no in-repo validation of skill frontmatter — correctness is enforced by the external Claude Code harness; the only in-repo schema gate validates eval suite JSON (ref: Q9).

The `skill-creator` skill named in the ticket is NOT present in this repo; it is an external/global skill listed in the session's available-skills list, so its file read/write behavior cannot be observed from the codebase (ref: Q2). A five-stage Python eval pipeline (`run_eval.py` → `grade.py` → `report.py` → `diagnose.py` → `revise.py`, orchestrated by `run_loop.sh`) drives skill evaluation, but it is largely stubbed: no real agent execution, judge/script checks return None, and only 4 of 21 fixtures exist (ref: Q10, ref: Q11). A new non-QRSPI skill would need its own suite shape, as shown by `evals/graphite-evals.json` (ref: Q10). There is no in-repo measurement of description triggering accuracy (ref: Q11), and no logging of trigger matches or skill invocations (ref: Q12).

## Desired End State

A new skill named `using-codex-cli` exists at `.claude/skills/using-codex-cli/SKILL.md`, discoverable and invocable through the standard file-placement + frontmatter convention. Mapping each acceptance criterion to concrete behavior:

- **agentskills.io directory structure with valid SKILL.md frontmatter** — the skill is a directory `using-codex-cli/` with a `SKILL.md` at its root and a `references/` subdirectory; frontmatter matches the in-repo wrapper convention (`name`, `description`, `command`, `argument-hint`, `allowed-tools`) (ref: Q1, ref: Q3, ref: Q4).
- **Built using the Anthropic skill builder skill** — authored via the external `skill-creator` skill, invoked at design/structure time (ref: Q2). This is an external dependency, not in-repo code.
- **SKILL.md body under 500 lines / 5000 tokens** — enforced editorially during authoring; no automated gate exists in-repo (ref: Q7). Overflow detail moves to `references/`.
- **Detailed reference material in references/ if needed** — deep tables (config.toml keys, sandbox enforcement, exec flags) live in `references/*.md`, loaded on demand, following the `qrspi-work` precedent (ref: Q5, ref: Q8).
- **Covers all three approval modes** with selection guidance — body section.
- **Documents sandbox modes and platform-specific enforcement** (macOS Seatbelt, Linux Bubblewrap + Landlock) — reference file.
- **Includes codex exec patterns for CI/automation**, **AGENTS.md hierarchy authoring**, **MCP server exposure and multi-agent orchestration**, **config.toml reference with profiles**, **known limitations and workarounds**, **Unix pipe composition examples** — distributed across body summary + reference files.

The skill is content-bearing (a "how to use a tool" knowledge skill), not a wrapper that spawns an agent — so it follows the full-logic-in-SKILL.md model of `qrspi-ticket`/`qrspi-work`, not the wrapper/agent split (ref: Q1).

## Delta

New files:

- `.claude/skills/using-codex-cli/SKILL.md` — frontmatter plus a body that introduces Codex CLI, states the key judgment defaults (workspace-write + auto-edit; escalate to full-auto only in containers; prefer MCP server mode for multi-agent; always set explicit `--sandbox`/`--approval-policy` in automation), and points to references for depth. Target well under 500 lines.
- `.claude/skills/using-codex-cli/references/approval-and-sandbox.md` — three approval modes, three sandbox modes, platform enforcement, network-off default, mode-selection decision guidance.
- `.claude/skills/using-codex-cli/references/automation-and-exec.md` — `codex exec` input patterns, stdout/stderr composition, `--json`/`--quiet`/`--ephemeral`/`--ignore-user-config`/`--ignore-rules`, Unix pipe examples, `CODEX_API_KEY`.
- `.claude/skills/using-codex-cli/references/config-and-agents.md` — config.toml sections and profiles, `model_instructions_file`, feature flags, project-root detection, AGENTS.md / AGENTS.override.md hierarchy and precedence.
- `.claude/skills/using-codex-cli/references/multi-agent.md` — MCP server mode (`codex()`/`codex-reply()`), Agents SDK integration, subagents, git-worktree parallelism, custom agent definitions.
- `.claude/skills/using-codex-cli/references/limitations.md` — pitfalls and workarounds (non-determinism guarded by tests, macOS network silent-ignore, sandbox-mode config bug, context pressure).

Optional (pending Open Questions):

- `evals/using-codex-cli-evals.json` — a per-skill suite modeled on `evals/graphite-evals.json` if the skill is to be benchmarked (ref: Q10). May be deferred given the stubbed harness.

No existing files are modified. No new queries, middleware, or registrations beyond file placement (registration is convention-only, ref: Q4).

## Pattern Decisions

### Decision 1: Skill structure — wrapper/agent split vs. full-logic SKILL.md

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Wrapper SKILL.md spawning a paired `.claude/agents/using-codex-cli.md` | Matches the dominant QRSPI phase pattern (ref: Q1) | The split exists to inject prompts into fresh-context phase agents; this is a static knowledge skill with no phase pipeline — the agent file would be dead weight |
| B | Full-logic content in SKILL.md + references/ (the `qrspi-ticket`/`qrspi-work` model) | Fits a knowledge/reference skill; references give progressive disclosure (ref: Q5, ref: Q8) | None material; this is the established model for non-phase skills |

**Recommendation:** Option B
**Rationale:** The wrapper/agent split is specific to QRSPI phase orchestration (ref: Q1). A "how to use Codex CLI" skill is reference content with no agent to spawn; `qrspi-ticket` and `qrspi-work` already establish the full-logic-in-SKILL.md precedent for non-phase skills (ref: Q1).
**NEW PATTERN?** No.

### Decision 2: Overflow handling — single body vs. multiple reference files

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Keep all detail inline in SKILL.md | One file | Ticket mandates < 500 lines / 5000 tokens, and the content (3 approval modes, 3 sandbox modes, platform enforcement, exec, config, multi-agent, limitations) clearly exceeds that (ref: Q7) |
| B | Slim body + topic-per-file under references/ | Honors the size budget editorially; matches the `qrspi-work` factoring precedent (ref: Q5, ref: Q8) | Authors must keep body/reference boundaries coherent |

**Recommendation:** Option B
**Rationale:** Body size is enforced only editorially in-repo (ref: Q7), and the precedent for overflow is one cohesive topic per `references/` file (ref: Q8). The content volume forces a split.
**NEW PATTERN?** No, but note: this would be the first skill with MULTIPLE reference files (qrspi-work has one). Still within the established `references/` convention (ref: Q5).

### Decision 3: Frontmatter shape and trigger description

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Wrapper-style frontmatter (`name`, `description`, `command`, `argument-hint`, `allowed-tools`) | Matches every skill-side `SKILL.md` in-repo (ref: Q3) | `argument-hint` is awkward for a no-argument knowledge skill — may omit or leave empty |
| B | Agent-style frontmatter (`model`, `claude.tools`) | — | Wrong file type; agent shape is for `.claude/agents/*.md`, not skills (ref: Q3) |

**Recommendation:** Option A, with a two-part trigger description that names Codex CLI explicitly and enumerates trigger phrases ("use codex", "codex exec", "codex CLI"), following the description convention (ref: Q6).
**Rationale:** Skills use `allowed-tools`, not `claude.tools` (ref: Q3); the description is the trigger surface and should carry literal phrases plus "Use when…" scoping (ref: Q6).
**NEW PATTERN?** No.

### Decision 4: Whether to author an eval suite now

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Ship a `evals/using-codex-cli-evals.json` suite alongside the skill | Satisfies TDD intent; per-skill suites are precedented (ref: Q10) | The harness is stubbed — no agent execution, judge returns None — so the suite would score zero today (ref: Q10, ref: Q11) |
| B | Defer the suite; rely on `skill-creator`'s own external eval loop | Avoids building against a non-functional harness | Leaves no in-repo regression guard |

**Recommendation:** Option A is preferred to honor TDD, but it is gated on the harness being functional — see OQ1. If the harness stays stubbed, Option B with an externally-run `skill-creator` eval is the fallback.
**Rationale:** The in-repo harness produces zeros until agent execution and judge integration land (ref: Q10), so a suite has no scoring value yet; `skill-creator`'s external eval loop is the realistic verification path (ref: Q2).
**NEW PATTERN?** No (a per-skill suite is precedented by `evals/graphite-evals.json`).

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `skill-creator` is external/absent in-repo, so the mandated build tool cannot be invoked or observed from this codebase (ref: Q2) | high | med | Confirm `skill-creator` is available in the implementing session's skill list (it is listed there); invoke it interactively. If unavailable, hand-author against the in-repo conventions (ref: Q1, Q3). |
| No automated size gate; the < 500-line / 5000-token criterion is unverifiable in-repo (ref: Q7) | high | low | Enforce editorially: slim body, push detail to `references/`; manually count lines/tokens before submitting. |
| Codex CLI factual content (flags, config keys, enforcement) cannot be verified against the codebase — it comes only from the ticket body | med | high | Treat ticket content as the spec of record; flag that runtime claims (e.g., macOS network silent-ignore, sandbox config bug) need source verification before publishing as guidance — see OQ2. |
| First multi-reference skill — `references/` loading is harness-driven and unobserved in-repo for the multi-file case (ref: Q5) | low | med | Follow the single-file `qrspi-work` relative-path precedent for each file; reference each file explicitly from the body. |
| Eval harness is stubbed, so any suite scores zero and gives false confidence (ref: Q10, ref: Q11) | med | med | Defer or clearly mark the suite as non-functional pending harness completion; rely on external `skill-creator` eval. |

## Open Questions

- OQ1: Should this skill ship with an in-repo eval suite (`evals/using-codex-cli-evals.json`) now, given the harness is stubbed and would score zero (ref: Q10), or defer until agent execution and judge integration land?
- OQ2: The Codex CLI behavioral claims (flag names, config keys, macOS Seatbelt network silent-ignore, sandbox-mode config bug) come only from the ticket. Should the author verify these against current Codex CLI documentation before publishing, or treat the ticket as authoritative?
- OQ3: Should `argument-hint` be omitted for this no-argument knowledge skill, or retained empty for frontmatter uniformity with the QRSPI wrappers (ref: Q3)?
- OQ4: The in-worktree `.claude/CLAUDE.md` is stale (says agents live in `.qrspi/agents/`, ref: Inconsistencies). Out of scope for this ticket, but should it be corrected alongside?
