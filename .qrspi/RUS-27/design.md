# Design — Create new agent skill called writing github actions

**Ticket:** RUS-27
**Research basis:** research.md @ 2026-06-04T00:00:00Z
**Generated:** 2026-06-04T00:00:00Z
**Status:** draft

## Current State

Skills live under `.claude/skills/<name>/SKILL.md`; the repo holds 10 skills, all kebab-case `qrspi-` prefixed (ref: Q1). Only one skill is multi-file — `qrspi-work` ships a `references/` subdirectory — and **no** skill ships `scripts/` or `assets/`, so `references/` is the sole established extra-dir pattern; `scripts/`/`assets/` have no precedent (ref: Q1, ref: Q8). The "agentskills.io standard" is not documented anywhere in this repo (ref: Q1). Most skills use a wrapper/agent split: a thin SKILL.md under `.claude/skills/` spawns a matching `.claude/agents/<name>.md` via `subagent_type`, but `qrspi-ticket` and `qrspi-work` keep their full logic in the SKILL.md with no agent file (ref: Q1, ref: Q11).

The `skill-creator` skill ("Anthropic skill builder") named in the ticket is **not in this repo** — it is a globally-available Claude Code skill outside project scope, so its inputs, scaffold output, and eval loop cannot be inspected from here (ref: Q2, ref: Q10). The only in-repo skill-authoring precedent is the existing SKILL.md + agent pattern (ref: Q2).

Skill `SKILL.md` frontmatter fields in use are `name`, `description`, `command`, `argument-hint`, and `allowed-tools`; `name` must equal the directory name and the `command` slug (ref: Q4, ref: Q5). No schema, linter, or validator enforces these fields — they are conventions only (ref: Q4). Descriptions follow a "what it does + when to use it" shape, sometimes with explicit trigger phrases and negative scope to suppress mis-triggering; nothing enforces length or wording (ref: Q6).

Content is split between SKILL.md and `references/` only in `qrspi-work`: its 565-line body carries the main procedure and offloads detail to `references/review-cascade.md`, pulled in **lazily by a prose pointer** (the agent Reads it on demand) — there is no eager-include mechanism (ref: Q3). Reference files are addressed by a backticked path relative to the skill root, no leading `./`, no absolute path (ref: Q8). There is **no in-repo tooling** that enforces or measures the ticket's <500-line / <5000-token limit, and `qrspi-work` at 565 lines already exceeds the 500-line guideline (ref: Q7).

No skill in this repo ships a `scripts/` directory, so there is no skill-internal script precedent; the repo-wide convention (project-level `scripts/`) is Python 3, `#!/usr/bin/env python3`, stdlib-only, with a stdlib-only `_test.py` sibling (ref: Q9). The in-repo eval harness `scripts/run_eval.py` is a **non-functional placeholder** — `execute_single` is a stub returning empty output — so it cannot grade a skill end-to-end (ref: Q10). The established verification policy is: pure logic via stdlib unit tests, prompt/skill behavior via manual end-to-end runs; no skill ships automated tests (ref: Q12). There is no in-repo module that dispatches or logs skill invocation — dispatch is handled by the external Claude Code runtime, so correct triggering is confirmed only by manual observation (ref: Q13). The dominant precedent for overlapping content is cross-reference over duplication: shared knowledge lives once (a reference, an agent, or `docs/`) and is linked by path (ref: Q11).

## Desired End State

A new skill `writing-github-actions` exists at `.claude/skills/writing-github-actions/` and auto-triggers when an agent writes or manages GitHub Actions workflow YAML.

- **AC: agentskills.io directory structure with valid SKILL.md frontmatter** → a `SKILL.md` with `name`, `description` (and, where the harness supports them, the conventional fields) following the in-repo frontmatter shape (ref: Q4), plus a `references/` subdirectory following the only precedented extra-dir pattern (ref: Q1, ref: Q8).
- **AC: built using the Anthropic skill builder skill** → see Open Questions; the builder is out of project scope (ref: Q2). Authoring follows the in-repo SKILL.md + `references/` precedent regardless.
- **AC: SKILL.md body under 500 lines / 5000 tokens** → body stays under the limit by offloading depth to `references/`, the in-repo lever for staying small (ref: Q3, ref: Q7). Not repo-enforced; verified by manual word/line count.
- **AC: detailed reference material covering security hardening checklist, OIDC setup, common workflow templates, matrix strategy examples** → four files under `references/`, each linked from SKILL.md by a backticked relative path and read on demand (ref: Q3, ref: Q8).
- **AC: SHA-pinning encoded as a non-negotiable default** → stated as a hard rule in the SKILL.md body and in the security reference.
- **AC: covers full workflow lifecycle (triggers, jobs, steps, caching, artifacts, secrets, deployments)** → the SKILL.md body organizes guidance by lifecycle stage; depth lives in references.
- **AC: reusable workflows vs composite actions guidance** → a decision section in the body distinguishing `workflow_call` from composite actions and when to choose each.
- **AC: concurrency and performance optimization patterns** → covered in the body.
- **AC: produces workflows that pass zizmor without warnings** → encoded as the acceptance bar; the skill's rules (SHA-pinning, least-privilege `permissions`, no expression injection, no `pull_request_target` with PR-head checkout) map to zizmor's checks. Verified manually (ref: Q12) — no in-repo zizmor gate exists.

## Delta

**New files (all under `.claude/skills/writing-github-actions/`):**

- `SKILL.md` — frontmatter + lifecycle-organized body, under 500 lines, with backticked relative pointers into `references/`.
- `references/security-hardening-checklist.md` — SHA-pinning, least-privilege `permissions: {}`, expression-injection avoidance, `pull_request_target` rules, CODEOWNERS, zizmor mapping.
- `references/oidc-setup-patterns.md` — provider-agnostic OIDC auth (AWS/GCP/Azure) replacing static cloud secrets, GitHub Environments.
- `references/common-workflow-templates.md` — single-job CI through multi-job deploy pipelines, reusable-workflow and composite-action skeletons.
- `references/matrix-strategy-examples.md` — `strategy.matrix`, `fail-fast: false`, `include`/`exclude`, cache-key isolation.

**Optional new file (see Decision 3):** `references/zizmor-audit.md` if zizmor guidance does not fit in the security checklist.

**No agent file:** following `qrspi-ticket`/`qrspi-work` precedent, this skill carries its content in SKILL.md + references and does **not** add a `.claude/agents/` file (ref: Q1, ref: Q11) — it is content-only, not a phase wrapper that spawns a subagent.

**No modified files.** This is additive; no existing skill, script, or workflow changes.

**No new scripts.** The skill is prose-only; absent script logic, the stdlib-only `_test.py` convention does not apply (ref: Q9, ref: Q12). If a helper script is later added it must follow the `#!/usr/bin/env python3` stdlib-only + `_test.py` convention.

## Pattern Decisions

### Decision 1: Content-only skill vs. wrapper/agent split

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Content-only SKILL.md + `references/`, no agent file (like `qrspi-ticket`/`qrspi-work`) | Matches the only precedent for non-phase skills; skill is guidance, not a subagent dispatcher; no dispatch plumbing | Breaks the uniform wrapper/agent split used by the 8 phase skills |
| B | Thin SKILL.md wrapper that spawns `.claude/agents/writing-github-actions.md` | Uniform with phase skills | The agent split exists to spawn a fresh-context subagent for a workflow phase; this skill has no phase to run — pure overhead, and the wrapper would have nothing meaningful to delegate |

**Recommendation:** Option A
**Rationale:** The wrapper/agent split is purpose-built for QRSPI phase execution (spawn a subagent with a job); `qrspi-ticket` and `qrspi-work` already establish that non-phase skills keep content in SKILL.md (ref: Q1, ref: Q11). A GitHub Actions authoring guide is reference content, not a subagent task.
**NEW PATTERN?** No — follows the `qrspi-ticket`/`qrspi-work` content-in-SKILL.md precedent (ref: Q1).

### Decision 2: Where reference depth lives (single SKILL.md vs. references offload)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Inline everything in one SKILL.md | Single file; nothing to cross-link | Would blow past the <500-line AC given the ticket's breadth; `qrspi-work` shows inlining hits 565 lines (ref: Q7) |
| B | Lean SKILL.md body + four `references/` files, linked by backticked relative paths, read on demand | Keeps body under limit; matches the one in-repo multi-file precedent; the four references map 1:1 to the AC's required reference topics | Reference content is not auto-loaded — relies on the agent following prose pointers (ref: Q3) |

**Recommendation:** Option B
**Rationale:** This is exactly the lever `qrspi-work` uses to manage size (ref: Q3, ref: Q7), and the AC explicitly enumerates four `references/` topics, so the structure is dictated by the ticket. Lazy prose-pointer loading is the established mechanism (ref: Q3, ref: Q8).
**NEW PATTERN?** No — replicates `qrspi-work`'s `references/` offload (ref: Q3).

### Decision 3: zizmor "passes without warnings" acceptance bar

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Encode zizmor-aligned rules in prose only; verify manually at review | Matches repo policy (prompt skills verified by manual e2e, ref: Q12); no new tooling; zizmor is external | "Passes zizmor without warnings" is asserted, not machine-proven in-repo |
| B | Add a script/CI step that runs zizmor against example workflows | Mechanical proof of the AC | No script-in-skill precedent (ref: Q9); zizmor is a third-party binary, violating the stdlib-only/dependency-free convention; expands scope well beyond a prose skill |

**Recommendation:** Option A
**Rationale:** The repo's stated verification policy is manual e2e for prompt-only skills and reserves automated tests for Python logic (ref: Q9, ref: Q12); there is no in-repo zizmor gate. Encoding zizmor's checks as hard rules (SHA-pinning, least-privilege permissions, no expression injection, no `pull_request_target` PR-head checkout) is the in-scope way to satisfy the AC.
**NEW PATTERN?** No — consistent with the manual-verification policy for prompt skills (ref: Q12).

### Decision 4: Handling overlap with existing GHA-adjacent guidance

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Self-contained skill; cross-reference canonical guidance by path where it already exists | Matches the cross-reference-over-duplication precedent (ref: Q11) | Requires checking for existing GHA guidance to link |
| B | Inline all guidance regardless of overlap | Simpler to author | Violates the single-source-of-truth precedent (ref: Q11) |

**Recommendation:** Option A
**Rationale:** The dominant in-repo precedent is to keep one source of truth and link by path rather than duplicate (ref: Q11). No existing skill covers GitHub Actions authoring, so overlap is minimal, but the skill should still link rather than restate any guidance it does touch.
**NEW PATTERN?** No — follows the cross-reference precedent (ref: Q11).

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| "Built using the Anthropic skill builder" is unverifiable in-repo — builder is out of scope (ref: Q2, ref: Q10) | high | med | Treat the builder as the optional authoring tool; satisfy the AC by following the in-repo SKILL.md + `references/` precedent and noting builder use is external. Flag as OQ1. |
| Frontmatter shape mismatch — agentskills.io fields may differ from this repo's `name`/`description`/`command`/`argument-hint`/`allowed-tools` (ref: Q4) | med | med | Use the in-repo frontmatter shape as the baseline (it is what the harness consumes); reconcile against the agentskills.io spec at authoring time. Flag as OQ2. |
| Body exceeds <500-line AC given ticket breadth (`qrspi-work` already at 565, ref: Q7) | med | low | Aggressively offload to the four `references/` files (Decision 2); manually count lines/tokens before acceptance — no automated gate exists (ref: Q7). |
| "Passes zizmor without warnings" cannot be machine-proven in-repo (ref: Q12) | med | med | Encode zizmor-aligned hard rules (Decision 3); verify manually against example workflows; document that the bar is met by rule-conformance, not an in-repo gate. |
| `scripts/`/`assets/` would set un-precedented structure (ref: Q1, ref: Q8) | low | low | Use only `references/` (the precedented dir); add no `scripts/`/`assets/` unless a concrete need emerges. |

## Open Questions

- OQ1: Is invoking the external `skill-creator` skill a hard requirement, or is "follow the agentskills.io structure" sufficient? The builder cannot be inspected or invoked from within this project scope (ref: Q2, ref: Q10).
- OQ2: Which frontmatter fields does the agentskills.io standard require, and do they conflict with this repo's conventional fields (`command`, `argument-hint`, `allowed-tools`)? No in-repo schema reconciles the two (ref: Q4).
- OQ3: Should zizmor "passes without warnings" be a documented review checklist item, or does the team want an actual zizmor run captured as evidence at acceptance? No in-repo zizmor tooling exists (ref: Q12).
- OQ4: Does this skill need an `allowed-tools` allowlist at all, given it is content-only and spawns no subagent (contrast with the phase wrappers that list `Agent` + Linear MCP tools) (ref: Q4)?
