# Design — Create a new agent skill using argo workflows cli

**Ticket:** RUS-7
**Research basis:** research.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## Current State

Skills in this repo live under `.claude/skills/<skill-name>/`, each holding a single `SKILL.md`; only `qrspi-work` adds a `references/` subdirectory, and no skill uses `scripts/` or `assets/` (ref: Q1). The repo contains 10 skills, all prefixed `qrspi-` (ref: Q1, Q9). There is no `skill-creator` skill and no `argo` CLI material anywhere in the repo — both subjects named by the ticket are external to `REPO_ROOT` (ref: Q2, Q4). The global `skill-creator` referenced by the ticket lives outside this repo and is invoked via the harness, not from in-repo files (ref: Q2).

SKILL.md frontmatter is uniform across all 10 skills: `name`, `description`, `command`, `argument-hint`, `allowed-tools` — and nothing else; there is no `version` field and no schema or validator enforcing frontmatter (ref: Q3, Q5, Q11). The directory name equals the `name` value equals `command` without the leading slash; uniqueness is convention, not enforced (ref: Q9). Skill versioning is recorded only at the eval-iteration level as a sha256 content-hash prefix, never in frontmatter or a changelog (ref: Q5).

Two content-offloading strategies exist: thin-wrapper skills (~25 lines) that delegate the full prompt to a peer `.claude/agents/<name>.md` file, and the `qrspi-work` body-plus-`references/` pattern that reads a reference file on demand by relative path via the `Read` tool (ref: Q6, Q8). The `references/` mechanism is plain natural-language progressive disclosure — no include or templating system exists (ref: Q6). Nothing enforces the 500-line / 5000-token body budget; the only `line_count` check targets eval output, not SKILL.md files, and `qrspi-work/SKILL.md` already violates the budget at 730 lines undetected (ref: Q7, and Inconsistencies). The eval harness (`run_loop.sh` → `run_eval.py` → `grade.py` → `report.py`) is content-agnostic but stub-backed, producing zero scores today; no eval case validates skill creation or agentskills.io conformance (ref: Q10, Q11, Q12). CLI calls inside skills append non-interactive flags (e.g. `gt ... --no-interactive`) because the harness blocks interactive prompts (ref: Q4).

## Desired End State

A new skill `using-argo-workflows-cli` ships under `.claude/skills/using-argo-workflows-cli/` with a valid `SKILL.md` and a `references/` directory holding the bulk of the conventions. Each acceptance criterion maps to behavior as follows:

- agentskills.io directory structure + valid frontmatter: directory `using-argo-workflows-cli/` with `SKILL.md` carrying the repo-standard five frontmatter fields (ref: Q1, Q3).
- Built using the Anthropic skill builder skill: the structure/plan/implement phases invoke the global `skill-creator` skill to scaffold and refine the skill (ref: Q2 — external tool, used at build time, not committed to repo).
- SKILL.md body under 500 lines / 5000 tokens: body stays lean by pushing detail into `references/`, following the progressive-disclosure precedent (ref: Q6, Q8).
- Detailed reference material in `references/`: command-group, template, retry, cron, resource, and artifact conventions live in reference files loaded on demand (ref: Q6).
- Covers all major command groups (submit, get, logs, list, delete, retry, resubmit, stop, terminate, suspend, resume, watch, lint, cron, template): documented in a CLI reference file.
- DAG vs Steps selection with decision criteria; retry/backoff conventions; debugging escalation (`argo get` → `argo logs` → `kubectl describe`); CronWorkflow lifecycle; resource conventions; artifact best practices: each becomes a dedicated reference section, summarized in the SKILL.md body so the agent knows when to open each file.
- All CLI invocations in the skill prefer non-interactive, scriptable flags (explicit `--namespace`, lint/dry-run before submit) consistent with the repo's non-interactive CLI discipline (ref: Q4).

## Delta

New files:

- `.claude/skills/using-argo-workflows-cli/SKILL.md` — lean body: frontmatter, when-to-use, a short decision-first overview, and pointers to each reference file. Target well under 500 lines.
- `.claude/skills/using-argo-workflows-cli/references/cli-commands.md` — full command-group catalog (submit/get/logs/list/delete/retry/resubmit/stop/terminate/suspend/resume/watch/lint/template) with flags and the submission conventions from the ticket.
- `.claude/skills/using-argo-workflows-cli/references/templates.md` — DAG vs Steps decision criteria, template authoring, parameters/variables, WorkflowTemplate vs ClusterWorkflowTemplate scope.
- `.claude/skills/using-argo-workflows-cli/references/reliability.md` — retry strategy / exponential backoff, error handling, timeouts, resource management (limits, nodeSelector, parallelism, synchronization), artifacts (keys, parameterization, GC).
- `.claude/skills/using-argo-workflows-cli/references/cron-and-debugging.md` — CronWorkflow lifecycle (create/list/suspend/resume/delete/lint/get) and the debugging escalation path.

Modified files:

- None required for the skill to function (skills are auto-discovered, ref: Q1, Q9). Optionally add `using-argo-workflows-cli` to the project `.claude/CLAUDE.md` skills list, but that file currently lists only `qrspi-*` workflow skills and is an Open Question.

No new DB queries, middleware, or eval cases are required to satisfy the acceptance criteria. Adding an eval case for SKILL.md conformance is possible but out of scope (ref: Q11) unless raised as an Open Question.

## Pattern Decisions

### Decision 1: Content offloading strategy (body vs references vs agent peer)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Thin wrapper → peer agent prompt in `.claude/agents/` | Matches 8/10 repo skills (ref: Q8) | Wrong fit: this is reference knowledge, not a multi-step workflow that spawns an agent; no `.qrspi` artifact lifecycle here |
| B | Lean SKILL.md body + on-demand `references/*.md` | Matches `qrspi-work` precedent (ref: Q6, Q8); directly satisfies the <500-line criterion and agentskills.io structure | Requires discipline to keep body lean (a pitfall `qrspi-work` itself failed, ref: Inconsistencies) |
| C | Everything inline in SKILL.md | Single file | Cannot fit all command groups + conventions under 500 lines; violates the budget criterion |

**Recommendation:** Option B
**Rationale:** This skill is a knowledge/reference skill (agentskills.io standard with `references/`), not a workflow dispatcher. The `qrspi-work` body+references pattern is the only in-repo precedent for progressive disclosure and is exactly the agentskills.io shape the ticket requires (ref: Q6, Q8). The `qrspi-work` 730-line overrun (ref: Inconsistencies) is a cautionary example, not a counter-pattern — the fix is aggressive offloading, which Option B does by design.
**NEW PATTERN?** No — reuses the `qrspi-work` references mechanism (ref: Q6), applied more strictly.

### Decision 2: Skill naming / namespace

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | `using-argo-workflows-cli` | Matches agentskills.io "using-X" convention the ticket invokes; reads as a capability skill | Breaks the repo's de-facto `qrspi-` prefix (ref: Q9) |
| B | `qrspi-argo` / `qrspi-argo-workflows` | Consistent with the existing `qrspi-` namespace (ref: Q9) | Misrepresents scope — this is general argo guidance, unrelated to the QRSPI workflow |

**Recommendation:** Option A
**Rationale:** The `qrspi-` prefix is a project-workflow namespace; this skill is general-purpose argo guidance, not a QRSPI phase. agentskills.io "using-X-cli" naming communicates intent. Names are convention-only and unenforced, so a new prefix carries no technical risk as long as the directory == `name` == `command` invariant holds (ref: Q9). Confirm with human (see Open Questions).
**NEW PATTERN?** Yes — first non-`qrspi-` skill in the repo. Justified because the `qrspi-` prefix denotes workflow-phase skills and would mislabel a general capability skill; the naming invariant (Q9) is still honored.

### Decision 3: Frontmatter shape

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Repo-standard 5 fields: name, description, command, argument-hint, allowed-tools | Uniform with all 10 skills (ref: Q3) | `command`/`argument-hint` are workflow-skill idioms; less natural for a reference skill |
| B | agentskills.io minimal frontmatter (name, description only) | Closer to the external standard the ticket cites | Diverges from every existing repo skill (ref: Q3); no validator forces either way |

**Recommendation:** Option A
**Rationale:** The repo enforces no schema (ref: Q3, Q11), so consistency with the 10 existing skills is the only objective tiebreaker. Use the five standard fields; set `allowed-tools` to read-only knowledge-delivery tools (e.g. `Read`, `Bash` scoped to `argo`/`kubectl` read commands) and `argument-hint` to a brief usage hint. Final tool scope is an Open Question.
**NEW PATTERN?** No — reuses the uniform frontmatter shape (ref: Q3).

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| SKILL.md body exceeds the 500-line / 5000-token budget, repeating the `qrspi-work` overrun (ref: Q7, Inconsistencies) | med | med | Keep body to overview + reference pointers; push all command/convention detail into `references/`; manually count lines/tokens since no automated check exists (ref: Q7) |
| `skill-creator` is external and may produce structure that diverges from this repo's conventions (ref: Q2) | med | low | After generation, reconcile output to the repo's directory layout and 5-field frontmatter (ref: Q1, Q3); the build step adapts, not blindly accepts, the generated scaffold |
| Non-`qrspi-` name surprises maintainers or future tooling that assumes the prefix (ref: Q9) | low | low | Confirm naming with human (Open Questions); no in-repo registration logic depends on the prefix (ref: Q9) |
| No eval/lint validates SKILL.md conformance, so structural regressions ship undetected (ref: Q11) | med | low | Manual review against acceptance-criteria checklist; optionally add a conformance eval case as a follow-up (out of scope, ref: Q11) |
| Argo conventions in references may drift from upstream argo CLI versions over time | low | med | Note the targeted argo version in references and keep guidance principle-based (lint/dry-run before submit, idempotent retries) rather than version-specific flag minutiae |

## Open Questions

- OQ1: Skill name — confirm `using-argo-workflows-cli` (breaks the `qrspi-` prefix) versus a `qrspi-`-prefixed name (ref: Decision 2, Q9).
- OQ2: `allowed-tools` scope — should the skill be read-only guidance (`Read` + scoped read `Bash`), or may it execute `argo`/`kubectl` commands? This affects whether it can act versus only advise (ref: Q3).
- OQ3: Should `using-argo-workflows-cli` be added to the project `.claude/CLAUDE.md` skills list, which currently enumerates only `qrspi-*` workflow skills?
- OQ4: Is a SKILL.md conformance eval case in scope for this ticket, or a follow-up? The harness has the extension point but no such check exists (ref: Q11).
- OQ5: Which argo CLI / Argo Workflows version should the references target, to keep flag and feature guidance accurate?
