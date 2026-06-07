# Design — Create a new agent skill: using terraform cli

**Ticket:** RUS-18
**Research basis:** research.md @ 2026-06-04T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft

## Current State

This repo holds 10 skills, each a directory under `.claude/skills/<skill-name>/` whose entry point is a single `SKILL.md`; the directory name equals the `name:` frontmatter field equals the slash command (ref: Q1). Discovery is automatic — Claude Code scans `.claude/skills/*/SKILL.md` and surfaces each skill's `name` + `description` into the available-skills list, with no registration file, manifest, or index to update (ref: Q12). Every `SKILL.md` opens with a five-field YAML frontmatter block — `name`, `description`, `command`, `argument-hint`, `allowed-tools` — present on all 10 skills (ref: Q3).

All 10 existing skills are QRSPI-workflow phase skills; none are infrastructure, IaC, or CLI-tool skills, so a Terraform skill faces no in-repo description/triggering collision, and the only CLI-adjacent capability (`using-graphite-cli`) is a global harness skill about git/PR operations, not provisioning (ref: Q9). The repo distinguishes thin phase skills (25–35-line shells that spawn `subagent_type: <name>` against a sibling `.claude/agents/<name>.md`) from self-contained skills like `qrspi-work` and `qrspi-ticket` that inline all logic with no agent counterpart; the agent/skill split is a QRSPI-specific convention, not an agentskills.io requirement (ref: Q1).

Exactly one skill uses a subdirectory today: `qrspi-work` with `references/review-cascade.md`. There are NO `scripts/` or `assets/` subdirectories in any skill (ref: Q2, Q8). The reference convention, set by that single file: kebab-case `.md` filename, a single H1, numbered/descriptive H2 sections with tables and fenced ASCII diagrams, cited from the body via an inline parenthetical `(see ` + "`references/<file>.md`" + `)`, with the reference file self-contained and not back-linking (ref: Q2, Q11). Descriptions follow a "what it does + when to use it" shape, sometimes embedding literal trigger phrases; no in-repo skill uses negative/anti-trigger SKIP clauses — that convention appears only in global harness skills (ref: Q5).

There is NO enforced size limit and NO tooling that measures `SKILL.md` line or token count; brevity is convention, not a gate. Most skills are 25–35 lines, but the flagship `qrspi-work` is 565 lines — itself exceeding the ticket's "under 500 lines" target (ref: Q7). The `skill-creator` (Anthropic skill builder) skill is a global harness skill outside `REPO_ROOT`; it is not a repo asset and cannot be inspected from project scope, though the user's global instructions mandate routing skill creation through it (ref: Q4). Verification in-repo is by stdlib-only unit tests for any logic scripts plus manual end-to-end runs; the `evals/`/`run_eval.py` pipeline is a non-functional stub and is not a real pass gate (ref: Q10). Skills are tracked source on `main`; new work flows through the QRSPI PR-gated lifecycle in a worktree at `.worktrees/<id>/` as a Graphite stack (ref: Q6). Repo-level scripts are Python 3, stdlib-only, `#!/usr/bin/env python3`, executable bit on CLIs, with a mandatory `_test.py` sibling per logic module (ref: Q8).

## Desired End State

A new self-contained skill directory `.claude/skills/using-terraform-cli/` exists with a valid `SKILL.md` (five-field frontmatter) plus a `references/` directory, auto-discovered by the harness with no manifest edit. Mapping each acceptance criterion to behavior:

- **agentskills.io structure + valid frontmatter** → directory `using-terraform-cli/` with `name: using-terraform-cli`, a triggering `description`, and the repo's standard `command`/`argument-hint`/`allowed-tools` fields (ref: Q1, Q3, Q12).
- **Built using the Anthropic skill builder skill** → the `skill-creator` global skill drives authoring; this is a process criterion satisfied during implementation, not a file (ref: Q4).
- **SKILL.md body under 500 lines / 5000 tokens** → body kept lean via progressive disclosure, detail pushed to `references/`; self-checked with `wc -l` since no gate exists (ref: Q7, Q2).
- **Detailed reference material in `references/`** covering backend setup, CI/CD, and migration → at minimum `references/backend-setup.md`, `references/cicd-pipelines.md`, `references/migration-blocks.md`, each kebab-case with one H1 and numbered H2s, cited from the body (ref: Q11).
- **Complete lifecycle init → validate → plan → apply → destroy** → encoded as the SKILL.md core-workflow section.
- **State management, locking, encryption** → SKILL.md state section (remote backend, locking, SSE-KMS, versioning, IAM, gitignore, treat-as-secret).
- **Provider and CLI version pinning** → SKILL.md section on `required_providers`, `required_version`, committing `.terraform.lock.hcl`, `tfenv`/`asdf`.
- **import/moved/removed blocks** → covered concisely in body, with deep detail in `references/migration-blocks.md`.
- **CI/CD with OIDC** → body summary + `references/cicd-pipelines.md` (stage order, OIDC, plan-on-PR, manual approval, security scanning).
- **Secrets management + security hardening** → SKILL.md security section (secrets manager + data sources, ephemeral values 1.10+, OIDC, least-privilege, audit logging).
- **Workspace vs. environment separation** → SKILL.md workspaces section (CLI workspaces for lightweight separation only; separate root dirs per env).
- **Module authoring + testing patterns** → SKILL.md module section (file layout, naming, validation, `sensitive`, `.tftest.hcl`).

Confirmation: directory + `SKILL.md` with valid frontmatter exists, `/using-terraform-cli` becomes invocable, and the skill appears in the available-skills list (ref: Q12).

## Delta

New files (all inside `.worktrees/RUS-18/`, delivered as implementation-slice PRs on the Graphite stack):

- `.claude/skills/using-terraform-cli/SKILL.md` — new skill body, self-contained model, five-field frontmatter, all in-body sections above, each reference cited via `(see ` + "`references/<file>.md`" + `)`.
- `.claude/skills/using-terraform-cli/references/backend-setup.md` — S3+DynamoDB canonical example with GCS/Azure/HCP equivalents; partial config; encryption/versioning/IAM.
- `.claude/skills/using-terraform-cli/references/cicd-pipelines.md` — pipeline stages, OIDC auth, plan-on-PR, manual approval gates, security scanning, plan-artifact passing.
- `.claude/skills/using-terraform-cli/references/migration-blocks.md` — `import`/`moved`/`removed` block patterns, refactor-in-small-batches, plan-before-apply discipline.

Modified files: optionally the human-facing skill list in `.claude/CLAUDE.md` (documentation only — not required for discovery, ref: Q12). No new scripts, no DB queries, no registration code. A `scripts/` subdirectory inside the skill is NOT planned unless a runnable helper proves necessary (none identified); if added it would carry a `_test.py` sibling per repo convention (ref: Q8).

## Pattern Decisions

### Decision 1: Skill shape (self-contained vs. thin-wrapper + agent)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Self-contained `SKILL.md` (inline logic, no `.claude/agents/` counterpart) | Matches non-phase skills `qrspi-work`/`qrspi-ticket`; no spawn indirection; standard agentskills.io shape | Body must stay lean to meet 500-line target |
| B | Thin wrapper + `.claude/agents/using-terraform-cli.md` | Mirrors phase-skill split | The agent/skill split is QRSPI-phase-specific; pointless for a non-phase reference skill; adds an unused file |

**Recommendation:** Option A
**Rationale:** Research is explicit that the wrapper+agent split is a QRSPI-phase convention and a non-phase skill follows the self-contained model (ref: Q1, Discovered Patterns).
**NEW PATTERN?** No.

### Decision 2: Body vs. references split (progressive disclosure)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Lean body with always-needed conventions; push backend/CI-CD/migration detail to `references/` | Matches `qrspi-work` lever; meets <500-line target; satisfies the references AC directly | Multi-file authoring; agent must read references on demand |
| B | Single large `SKILL.md`, no references | Simpler single file | Violates the references AC; risks exceeding 500 lines like `qrspi-work` (565) |

**Recommendation:** Option A
**Rationale:** `references/` progressive disclosure is the established lever for keeping `SKILL.md` small, and the ticket explicitly requires `references/` covering backend/CI-CD/migration (ref: Q2, Q7, Q11).
**NEW PATTERN?** No — though it is only the second skill to use `references/`.

### Decision 3: Description / triggering style

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | "What it does + when to use it" with embedded Terraform/IaC trigger phrases, no SKIP clause | Matches every in-repo description; strongest match to repo norm | Less explicit anti-trigger guarding against overlap |
| B | Add an explicit `SKIP:`/anti-trigger clause (as global skills do) | Reduces false triggers vs. provider-specific work | No in-repo skill uses this — introduces a convention |

**Recommendation:** Option A
**Rationale:** Every in-repo description uses the positive "what + when" form with optional literal triggers and none use SKIP clauses; matching the repo norm avoids introducing a one-off convention. Anchor triggers on Terraform/IaC vocabulary and avoid the reserved `qrspi-` prefix (ref: Q5, Q9).
**NEW PATTERN?** No (Option B would be a NEW PATTERN).

### Decision 4: Skill name and slash command

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | `using-terraform-cli` (matches ticket title; echoes global `using-graphite-cli`) | Kebab-case, distinct, no `qrspi-` collision; familiar "using-<tool>" shape | Slightly long |
| B | `terraform-cli` | Shorter | Drops the established "using-<tool>-cli" naming echo |

**Recommendation:** Option A
**Rationale:** `name` must equal the directory and slash command; kebab-case is universal; the `qrspi-` prefix is reserved for workflow phases, so a distinct infra name is required, and "using-terraform-cli" mirrors the global `using-graphite-cli` convention (ref: Q1, Q3, Q9).
**NEW PATTERN?** No.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Body exceeds 500-line / 5000-token target with no tooling to catch it (qrspi-work already breaches at 565) | med | med | Aggressively offload detail to `references/`; self-check `wc -l SKILL.md` before submit; keep body to conventions + summaries (ref: Q7) |
| `skill-creator` "built using" criterion is unverifiable from repo scope (global skill, not inspectable) | med | low | Treat as a process criterion satisfied during implementation by invoking the global skill-creator per user mandate; document invocation in the slice (ref: Q4) |
| Scope creep into provider-specific resource config or HCL language depth, violating ticket scope guidance | med | med | Keep skill to CLI workflow + conventions; explicitly exclude provider resources, CDK, and language deep-dives in the body (ticket scope guidance) |
| Description triggers too broadly and collides with future infra skills | low | low | Anchor triggers on Terraform/IaC vocabulary; avoid generic "infrastructure" phrasing; no `qrspi-` prefix (ref: Q5, Q9) |
| Reference files drift from the single existing convention (one H1, numbered H2, body citation) | low | low | Follow `review-cascade.md` shape exactly; cite each from the body via the parenthetical relative path (ref: Q11) |

## Open Questions

- OQ1: Should the skill include a `scripts/` subdirectory with a runnable helper (e.g. a plan/validate wrapper)? None is required by the ticket; research found no skill ships `scripts/` (ref: Q8). Default: omit unless a helper is justified.
- OQ2: Should `.claude/CLAUDE.md`'s human-facing "Available skills" list be updated to mention the new skill? It is documentation-only and not needed for discovery (ref: Q12). Default: update for completeness.
- OQ3: How exactly is the global `skill-creator` eval loop expected to be run and what counts as passing for this skill, given it is out of project scope (ref: Q4, Q10)? Needs human direction on the acceptance bar beyond "valid frontmatter + manual e2e".
- OQ4: Beyond the three named reference files (backend, CI/CD, migration), is a fourth on security/secrets hardening wanted, or should security stay inline in the body? Ticket lists security as a body AC but the topic is reference-sized.
