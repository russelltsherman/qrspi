# Design — Create an agent skill for the Argo Workflows CLI

**Ticket:** RUS-7
**Research basis:** research.md @ 2026-06-03T00:00:00Z
**Generated:** 2026-06-03T00:00:00Z
**Status:** draft

## Current State

The repo's `.claude/skills/` contains exactly 10 skills, all named `qrspi-*`; there is no general-purpose CLI-wrapping skill (ref: research scope note, Q6). Skills live at `.claude/skills/<skill-name>/SKILL.md` relative to the worktree root, and discovery is performed by the external Claude Code harness — no in-repo loader, registry, manifest, or index governs availability; adding a skill means creating the directory (ref: Q5, Q6). Across all 10 skills an invariant holds: directory name equals frontmatter `name` equals `command` minus the leading slash (ref: Q5). The SKILL.md frontmatter schema actually used is `name`, `description`, `command`, `argument-hint`, `allowed-tools`, delimited by `---` lines; this is convention only — no validator, JSON schema, or lint enforces it (ref: Q3, Q11). Agent files in `.claude/agents/` use a different frontmatter shape (`name`, `description`, nested `claude.tools`) and must not be conflated with the skill schema (ref: Q3).

Two skill patterns exist: 8 phase skills are thin wrappers that delegate to a same-named `.claude/agents/<n>.md` via the `Agent` tool, while `qrspi-ticket` and `qrspi-work` are self-contained skills with no agent counterpart — all logic in the SKILL.md body (ref: Q4). No in-repo skill wraps an external binary, so there is no direct precedent for `argo`-style CLI wrapping; the closest precedent is the agents' and orchestrator's hard-stop error culture — surface the exact command and error and stop on tooling/infra failure rather than working around it (ref: Q9). There is no enforced SKILL.md body-size limit; the 500-line/5000-token guidance originates from the external `skill-creator` (out of repo). Most skills are 25–35 lines; the only oversize skill, `qrspi-work` (565 lines), offloads detail to `references/review-cascade.md` linked by relative-path prose (ref: Q7, Q8). The `references/` subdir is the one progressive-disclosure mechanism actually exercised; `scripts/` and `assets/` are conventionally available but unused anywhere in the repo (ref: Q1, Q8). The `skill-creator` skill the ticket mandates is a global/plugin skill not present in this repo, so its input/output contract is not knowable from the codebase (ref: Q2). Verification is by stdlib unit tests plus manual e2e runs; the `evals/` harness is an explicit non-functional stub (ref: Q10). Triggering is driven by the `description` field, which packs explicit "Use when…" conditions and example phrases for the harness matcher; there is no in-repo logging of whether a skill fired (ref: Q12).

## Desired End State

A new self-contained skill directory `.claude/skills/using-argo-workflows-cli/` (or equivalently named) exists with a valid `SKILL.md` and a `references/` directory holding the detailed conventions.

| Acceptance criterion | System behavior after ship |
|---|---|
| agentskills.io directory structure with valid SKILL.md frontmatter | `SKILL.md` carries the repo's conventional frontmatter (name/description/command/argument-hint/allowed-tools), dirname==name==command-minus-slash (ref: Q3, Q5) |
| Built using the Anthropic skill-builder skill | Skill is authored via the external `skill-creator` skill; its eval loop is run where available (ref: Q2; user global memory "Use skill-creator for skills") |
| SKILL.md body under 500 lines / 5000 tokens | Body kept lean; detail pushed to `references/` per the `qrspi-work` precedent (ref: Q7, Q8) |
| Detailed reference material in references/ if needed | `references/*.md` files carry the per-topic conventions, linked by relative-path prose from the body (ref: Q1, Q8) |
| Covers all major argo CLI command groups (submit, get, logs, list, delete, retry, resubmit, stop, terminate, suspend, resume, watch, lint, cron, template) | Reference content documents each command group with the ticket's conventions |
| DAG vs Steps selection with decision criteria | Reference section states "DAG by default; Steps only for purely sequential, no-branching" |
| Retry strategy and error handling with exponential backoff | Reference section encodes retryStrategy, backoff duration/factor/maxDuration, retryPolicy, idempotency, timeouts |
| Debugging workflow: argo get → argo logs → kubectl describe escalation | Reference section documents the escalation path and common failure causes |
| CronWorkflow lifecycle (create, list, suspend, resume, delete, lint) | Reference section covers cron create/list/suspend/resume/delete/lint and concurrency/timezone settings |
| Resource management conventions (limits, nodeSelector, parallelism) | Reference section covers requests/limits, nodeSelector, tolerations, parallelism, synchronization |
| Artifact configuration best practices (key parameterization, GC) | Reference section covers repo config, `{{workflow.uid}}` key parameterization, `.tgz` suffixing, artifact GC |

Additionally, the human-facing skill catalogs (`README.md` skills table/tree and `.claude/CLAUDE.md` "Available skills" list) are updated so the catalog is not stale — a documentation convention, not a functional requirement (ref: Q6).

## Delta

New files:

- `.claude/skills/using-argo-workflows-cli/SKILL.md` — lean body: frontmatter (per Q3 schema), a one-paragraph purpose, a prerequisite/availability check for the `argo` binary with hard-stop-on-failure behavior (ref: Q9), a short decision-routing section, and relative-path pointers into `references/`.
- `.claude/skills/using-argo-workflows-cli/references/submission-and-monitoring.md` — submit/lint/dry-run conventions, parameters, `--from`, monitoring (list/get/logs/watch), `@latest`, container selection.
- `.claude/skills/using-argo-workflows-cli/references/debugging-and-lifecycle.md` — debugging escalation path, common failure causes, retry/resubmit/stop/terminate/suspend/resume/delete lifecycle commands.
- `.claude/skills/using-argo-workflows-cli/references/authoring.md` — DAG vs Steps, templates (WorkflowTemplate/ClusterWorkflowTemplate, templateRef), parameters/variables, artifacts, retry strategy/error handling, resource management.
- `.claude/skills/using-argo-workflows-cli/references/cron-workflows.md` — cron lifecycle and tuning.

(Reference file count/grouping is a design choice; see Decision 3. The split must keep the SKILL.md body under the size budget.)

Modified files:

- `README.md` — add the new skill to the skills table and directory tree (ref: Q6).
- `.claude/CLAUDE.md` — add the new skill to the "Available skills" list (ref: Q6).

No code changes: there is no loader, registry, or validator to touch (ref: Q6, Q11).

## Pattern Decisions

### Decision 1: Skill shape — self-contained vs thin-wrapper-with-agent

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Self-contained skill (SKILL.md only, no agent), like `qrspi-ticket`/`qrspi-work` | Matches a knowledge/convention skill that needs no fresh-context subagent; one fewer file pair to keep in sync | Body must stay lean to respect size budget (mitigated by `references/`) |
| B | Thin wrapper + `.claude/agents/using-argo-workflows-cli.md` | Consistent with the 8 phase skills | The phase-skill agent pattern exists to spawn fresh-context workers for multi-step orchestration; this skill is reference guidance, not orchestration — an agent adds an unused indirection |

**Recommendation:** Option A
**Rationale:** Research shows non-phase utility skills follow the self-contained `qrspi-ticket`/`qrspi-work` pattern, and the wrapper+agent split exists specifically to delegate orchestration to a subagent — which this guidance skill does not need (ref: Q4).
**NEW PATTERN?** No — directly reuses the self-contained skill precedent.

### Decision 2: Body-size management — single body vs body + references/

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Everything in SKILL.md body | One file | The ticket's content far exceeds the ~500-line budget; would blow the convention and bloat always-loaded context |
| B | Lean body + `references/*.md` (progressive disclosure) | Matches the only oversize-skill precedent (`qrspi-work` → `references/review-cascade.md`); keeps always-loaded body small | Body must explicitly point the agent to each reference at the right decision point |

**Recommendation:** Option B
**Rationale:** The repo's sole precedent for large skill content is progressive disclosure via `references/`, linked by relative-path prose (ref: Q7, Q8); the ticket explicitly calls for `references/` when needed.
**NEW PATTERN?** No — reuses the `qrspi-work` references/ precedent. Note: this will be the first skill with multiple reference files and the first to use `references/` for a non-phase skill, but the mechanism is identical.

### Decision 3: Reference-file granularity

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | One large `references/conventions.md` | Simple; single pointer from body | Defeats progressive disclosure — the agent loads all content even for a narrow task |
| B | Several topic-scoped reference files (submission, debugging, authoring, cron) | Agent opens only the relevant file; mirrors the ticket's own section structure | More files; body needs several pointers |

**Recommendation:** Option B
**Rationale:** Progressive disclosure's value is loading only what the current branch needs (ref: Q8); topic-scoped files realize that. Exact file boundaries are an open question for the human (see OQ2).
**NEW PATTERN?** No — extends the single-reference precedent to multiple files; same relative-path-prose linking mechanism.

### Decision 4: Missing-binary / command-failure behavior

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Encode a prerequisite `argo`-availability check and a hard-stop-on-failure instruction in the body | Matches the repo's strong "surface exact command + error, stop, don't work around" culture and user global memory | Slightly more body content |
| B | Stay silent on failure handling | Shorter body | Contradicts the established hard-stop convention; no reusable availability helper exists to lean on |

**Recommendation:** Option A
**Rationale:** No in-repo CLI-wrapper precedent exists, but the agents/orchestrator hard-stop culture is the governing convention and is reinforced by user memory "Error surfacing over workarounds" (ref: Q9).
**NEW PATTERN?** Partial — first skill to embed an external-binary prerequisite check, but it applies the existing hard-stop error convention rather than inventing new behavior.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `skill-creator` (mandated by ticket + user memory) is not installed in this environment, blocking the prescribed authoring path | high | med | Confirm availability before structure/plan; if absent, escalate as an open question — do not silently hand-author and claim skill-creator was used (ref: Q2) |
| No validator/lint exists, so a malformed frontmatter or broken `references/` link ships undetected | med | med | Manually mirror the exact Q3 schema and Q5 triple-name invariant; verify each `references/*.md` relative link resolves; rely on unit-test/manual-e2e verification posture (ref: Q3, Q11, Q10) |
| SKILL.md body exceeds the 500-line/5000-token budget while covering all 15 command groups | med | med | Enforce Decision 2/3 split aggressively; keep body to purpose + prerequisite check + routing pointers; push all command detail into `references/` (ref: Q7, Q8) |
| Skill `description` is too generic, so the harness fails to auto-invoke it for argo-related requests | med | med | Pack explicit "Use when…" condition and concrete trigger phrases into `description`, per the `qrspi-work`/`qrspi-questions` precedent (ref: Q12) |
| README / CLAUDE.md catalogs drift out of date because update is unenforced | low | low | Include the doc updates in the Delta and treat them as part of the slice (ref: Q6) |
| Argo CLI conventions in the ticket become outdated vs the installed `argo` version | low | med | Treat reference content as version-aware guidance; note assumed argo version as an open question (OQ3) |

## Open Questions

- OQ1: Exact skill directory name — `using-argo-workflows-cli` (mirrors the `using-graphite-cli` external convention) vs an `argo-*` form? The name fixes dirname==name==command (ref: Q5).
- OQ2: Preferred `references/` file boundaries — group by the four ticket clusters (submission/monitoring, debugging/lifecycle, authoring, cron) or a different split?
- OQ3: Which `argo` CLI version should the conventions target, and should the skill assert a minimum version in its prerequisite check?
- OQ4: Is the external `skill-creator` skill actually available in this environment? If not, how should the team proceed given the ticket and user memory both mandate it (ref: Q2)?
- OQ5: Should `allowed-tools` restrict this skill to `Bash(argo:*)` / `Bash(kubectl:*)` scopes, or leave Bash unscoped? The allowlist DSL supports scoped Bash (ref: Q3).
