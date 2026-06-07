# Design — Create a new agent skill using aws cli

**Ticket:** RUS-20
**Research basis:** research.md @ 2026-06-04T00:00:00Z
**Generated:** 2026-06-04T00:00:00Z
**Status:** draft

## Current State

There is no `aws` / `aws-cli` skill anywhere in this repo; `.claude/skills/` contains only the ten `qrspi-*` skills (ref: Q1). Every skill is a directory under `.claude/skills/<skill-name>/` containing a single `SKILL.md`; the directory name equals the frontmatter `name` field and the `/command` (ref: Q1). Of the ten skills, only `qrspi-work` uses a `references/` subdirectory (`references/review-cascade.md`), and no skill ships a `scripts/` or `assets/` subdirectory — those parts of the agentskills layout are unexercised here (ref: Q1, Q6).

No agentskills.io standard documentation exists under the repo root, and no validator or schema enforces `SKILL.md` frontmatter (ref: Q1, Q2). The de facto required frontmatter fields, present in all ten files, are `name`, `description`, `command`, `argument-hint`, and `allowed-tools`, delimited by `---` lines (ref: Q2). The `skill-creator` (Anthropic skill builder) skill referenced by the ticket is a harness-level global skill, not present in-repo; its full input/output contract cannot be mapped from repo content, and the only in-repo mention treats invoking it as the final in-slice validation step (ref: Q3).

The `description` field is the sole trigger signal the harness surfaces for auto-invocation; the repo-wide phrasing pattern is a capability clause followed by a "Use when/after…" trigger clause, with explicit example trigger phrases for high-fire skills (ref: Q4). No in-repo mechanism enforces the 500-line / 5000-token body budget; the only precedent for staying lean is offloading procedural detail to `references/<topic>.md` referenced by relative path, as `qrspi-work` does — and `qrspi-work/SKILL.md` is itself 565 lines, already over that budget (ref: Q5). The only `references/` precedent is a single single-topic file, which favors one-file-per-topic but provides no multi-file example (ref: Q6).

The minimal valid documentation-only skill — a directory with just `SKILL.md` (five-field frontmatter plus body), no `scripts/` or `assets/` — is the normal case here (eight of ten skills) (ref: Q7). No check scans skill content for embedded environment-specific values; the only scope check (`scripts/check_scope.py`) compares touched file *paths*, not content (ref: Q8). No `SKILL.md` uses a dedicated "In scope / Out of scope" heading; scope is expressed inline as `Do NOT/Never` imperatives in skill bodies, or via `## Out of Scope` / `## Constraints` headings in the ticket template only (ref: Q9). The eval harness (`scripts/run_eval.py`) is an explicit non-functional placeholder with no skill-authoring case, and `evals/golden/` is empty; the documented verification path for a documentation skill is manual end-to-end invocation (ref: Q10, Q11). A new skill is surfaced through the standard QRSPI PR-gated lifecycle as an ordinary tracked file change; there is no skill-specific status field or skill-creator provenance record, and acceptance is established by PR approval (ref: Q12).

## Desired End State

A new documentation-only skill exists at `.claude/skills/aws-cli/SKILL.md` plus an `.claude/skills/aws-cli/references/` directory, mapped to the acceptance criteria as follows:

- **agentskills.io directory structure with valid frontmatter** → `aws-cli/SKILL.md` with the five-field frontmatter (`name: aws-cli`, `description`, `command: /aws-cli`, `argument-hint`, `allowed-tools`) plus sibling `references/`, matching the only in-repo precedent (ref: Q1, Q2).
- **Built using the Anthropic skill builder skill** → the skill-creator skill is invoked during authoring/validation; because it is a harness-level skill not in-repo, this is an authoring-time action, not a committed artifact (ref: Q3).
- **Body under 500 lines / 5000 tokens** → SKILL.md body kept lean by delegating detail to `references/`; budget is honored by authoring discipline since nothing enforces it (ref: Q5).
- **Detailed reference material covering JMESPath, waiters, service cheat sheets** → three reference files (or a justified partition), one cohesive topic each, per the single-topic precedent (ref: Q6).
- **Covers authentication (SSO, profiles, assume-role, env vars)** → a SKILL.md section encodes the ticket's auth conventions (SSO over IAM keys, `sts get-caller-identity` verification, named profiles, `role_arn`/`source_profile`, `external_id`, CI/CD roles).
- **Covers core services S3, EC2, ECS, Lambda, IAM, CloudFormation** → per-service guidance in SKILL.md with deep command tables in the services cheat-sheet reference.
- **Output formatting guidance (`--query`, `--output`, `AWS_PAGER`)** → a formatting section in SKILL.md plus the JMESPath reference.
- **Error handling and scripting patterns (exit codes, retries, idempotency)** → a scripting-patterns section in SKILL.md.
- **Security best practices (least privilege, no long-lived keys, credential hygiene)** → a security section encoded as `Do NOT/Never` imperatives following the in-repo scope/non-goal convention (ref: Q9).
- **Waiter usage patterns for async operations** → guidance in SKILL.md plus the waiters reference.
- **Scope boundaries** → in-scope (raw `aws` CLI ops) and out-of-scope (Terraform/CDK/Pulumi) stated; no AWS account IDs, resource names, or regions embedded (ref: Q8, Q9).

## Delta

New files:

- `.claude/skills/aws-cli/SKILL.md` — five-field frontmatter; body sections for Authentication & Profiles, Environment & Config, Output Formatting & Filtering, Pagination, Waiters, per-service operations (S3/EC2/ECS/Lambda/IAM/CloudFormation), Error Handling & Scripting, Security, and Scope. Detail delegated to `references/` to stay under budget.
- `.claude/skills/aws-cli/references/jmespath.md` — `--query` JMESPath patterns (field selection, filters, date ranges, text-output column ordering).
- `.claude/skills/aws-cli/references/waiters.md` — common built-in waiter commands per service and the exit-code-255 handling note.
- `.claude/skills/aws-cli/references/services.md` — per-service command cheat sheets (S3 high-level vs `s3api`, EC2 filters/tags/launch templates, ECS deploy/exec, Lambda deploy/invoke/log decode, IAM simulate/least-privilege, CloudFormation `deploy`/change-set/drift).

Modified files: none required for the skill to function (skills are discovered by directory; no loader registration exists) (ref: Q1).

No new DB queries, middleware, or scripts. The skill is documentation-only, so no `scripts/` or `assets/` subdirectory and no Python helper or `_test.py` sibling (ref: Q7, Q11). The `argument-hint` and `allowed-tools` values are open design choices flagged in Open Questions, since this skill is reference guidance rather than a sub-agent-spawning wrapper.

## Pattern Decisions

### Decision 1: references/ partitioning

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Three files: `jmespath.md`, `waiters.md`, `services.md` | One cohesive topic per file (sole in-repo precedent, ref: Q6); maps 1:1 to the three required reference topics; smallest SKILL.md body | Establishes the first multi-file `references/` dir in the repo — no exact precedent |
| B | One combined `reference.md` | Mirrors the literal single-file precedent | Mixes three unrelated topics in one file, contradicting the "one file = one topic" contract (ref: Q6); larger, harder to navigate |

**Recommendation:** Option A
**Rationale:** The only existing reference file (`qrspi-work/references/review-cascade.md`) is scoped to a single cohesive concern (ref: Q6), so three single-topic files extend that contract rather than break it. The acceptance criteria name exactly three reference topics, giving a clean 1:1 mapping.
**NEW PATTERN?** Partially — a multi-file `references/` directory has no exact in-repo precedent (ref: Q6), but it is a direct extension of the existing single-topic-per-file convention, not a new authoring model.

### Decision 2: Encoding scope and security as guidance

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Inline `Do NOT/Never` imperatives plus a `## Scope` section | Matches the dominant skill-body convention for non-goals (ref: Q9); directives are the strongest trigger for agent compliance | No standardized scope heading exists, so heading naming is a judgment call |
| B | `## In Scope` / `## Out of Scope` headings copied from the ticket template | Explicit, scannable | That heading convention exists only in the *ticket* template, not in any skill body (ref: Q9) — would import a foreign convention |

**Recommendation:** Option A
**Rationale:** Skill bodies in this repo express non-goals inline as `Do NOT/Never` imperatives (ref: Q9). Security best practices ("never embed long-lived keys", "never create IAM users for apps") map naturally onto that imperative form. A lightweight `## Scope` subsection states the Terraform/CDK/Pulumi exclusion.
**NEW PATTERN?** No — uses the established inline-imperative convention (ref: Q9).

### Decision 3: Body-budget control

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Lean SKILL.md (concise per-section guidance) + detail pushed to `references/` | Follows the only lean-skill precedent (ref: Q5); keeps body well under 500 lines despite six services | Requires disciplined splitting; relative-path links must stay correct |
| B | Comprehensive single SKILL.md | Self-contained, no cross-file links | Six services + auth + formatting + scripting + security would likely exceed 500 lines, repeating the `qrspi-work` overrun (ref: Q5) |

**Recommendation:** Option A
**Rationale:** `qrspi-work` already exceeds the budget by inlining detail (ref: Q5); the explicit acceptance criterion (<500 lines / 5000 tokens) plus the three required reference files make delegation the intended structure. Nothing enforces the budget, so discipline is the only control (ref: Q5).
**NEW PATTERN?** No — extends the `qrspi-work` SKILL.md → `references/` relative-path delegation pattern (ref: Q5).

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Body exceeds 500-line / 5000-token budget; nothing enforces it (ref: Q5) | med | low | Delegate all per-service detail to `references/`; keep SKILL.md to concise directives; do a manual `wc -l` and token check before submitting |
| Embedded environment-specific values (account IDs, resource names, regions) slip in; no automated content linter exists (ref: Q8) | med | med | Use placeholder tokens (e.g. `<name>`, `i-xxx`) only; rely on PR review since no tooling catches this (ref: Q8); add a self-review checklist line |
| skill-creator (Anthropic skill builder) is not in-repo; the "built using skill builder" criterion cannot be verified from committed files (ref: Q3) | high | low | Treat skill-creator as an authoring-time/global tool; record its use in the PR description, the only acceptance signal (ref: Q12) |
| No automated validation of frontmatter, length, or triggering; eval harness is a stub (ref: Q10, Q11) | high | med | Verify manually end-to-end: confirm directory==name==command, valid frontmatter, and live trigger in a Claude Code session (ref: Q11) |
| Multi-file `references/` dir has no exact precedent; relative-path links could be wrong | low | low | Mirror `qrspi-work`'s relative-path link form (`references/<topic>.md`) (ref: Q5); verify each link resolves |

## Open Questions

- OQ1: What `allowed-tools` value should `aws-cli` declare? Existing skills are sub-agent wrappers scoping tools like `Agent`, `Bash(pwd:*)`, and specific MCP tools (ref: Q2). A pure reference skill may need only `Bash` (or `Bash(aws:*)`) — or none. A human should decide the tool allowlist and whether the skill spawns a sub-agent.
- OQ2: What `argument-hint` is appropriate for a non-positional reference skill? The five-field convention requires the field (ref: Q2), but this skill takes no ticket-id-style argument.
- OQ3: Should the skill-creator (Anthropic skill builder) invocation be a hard gate, given it is a harness-level skill absent from the repo (ref: Q3)? If it is unavailable in the implementing environment, is hand-authoring to the same standard acceptable for the acceptance criterion?
- OQ4: Is establishing the repo's first multi-file `references/` directory acceptable (Decision 1, ref: Q6), or should the three topics be combined to stay literally within the single-file precedent?
