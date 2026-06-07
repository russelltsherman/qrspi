# Structure Outline — Create a new agent skill using aws cli

**Design basis:** design.md @ 2026-06-04T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft

## New Types

This is a documentation-only skill (ref: design §Delta). There is no executable
code, so the "types" are the structural shapes the files must conform to.

- `SkillFrontmatter { name: string, description: string, command: string, argument-hint: string, allowed-tools: string }`
  — the five-field YAML block delimited by `---` lines required by all in-repo skills (ref: design §Current State, Q2). For `aws-cli`: `name: aws-cli`, `command: /aws-cli`; `description` follows the capability-clause + "Use when…" trigger-clause pattern; `argument-hint` and `allowed-tools` are open design choices (see Unverified Assumptions / OQ1, OQ2).
- `ReferenceFile { topic: single-cohesive-concern, linked-from: SKILL.md via relative path }`
  — one file per topic, mirroring `qrspi-work/references/review-cascade.md` (ref: design Decision 1, Q6).

## Modified Types

None. No existing file is modified; skills are discovered by directory and no
loader registration exists (ref: design §Delta, Q1).

## Contracts

These are the cross-file interfaces the slice must honor (no function signatures
exist for a documentation skill).

- **Frontmatter contract:** `aws-cli/SKILL.md` opens with a `---`-delimited block carrying exactly the five fields `name`, `description`, `command`, `argument-hint`, `allowed-tools`, with `name == directory name == command (minus leading /)` (ref: design §Desired End State, Q1/Q2).
- **Reference-link contract:** `SKILL.md` references each reference file by relative path of the form `references/<topic>.md`, and every such link resolves to an existing sibling file (ref: design Decision 3, Q5; Risk: relative-path links).
- **Topic-partition contract:** three reference files map 1:1 to the three required deep-detail topics — `references/jmespath.md` (`--query`/JMESPath patterns), `references/waiters.md` (built-in waiters + exit-code-255 note), `references/services.md` (per-service S3/EC2/ECS/Lambda/IAM/CloudFormation cheat sheets) (ref: design §Delta, Decision 1).
- **SKILL.md body-coverage contract:** the body contains sections for Authentication & Profiles, Environment & Config, Output Formatting & Filtering, Pagination, Waiters, per-service operations (S3/EC2/ECS/Lambda/IAM/CloudFormation), Error Handling & Scripting, Security, and Scope — each acceptance criterion mapped to a section (ref: design §Desired End State, §Delta).
- **Budget contract:** SKILL.md body stays under 500 lines / 5000 tokens; per-service and topic detail is delegated to `references/` (ref: design Decision 3, Q5).
- **Content-hygiene contract:** no embedded account IDs, resource names, or regions; placeholder tokens only (e.g. `<name>`, `i-xxx`) (ref: design §Desired End State, Q8).
- **Security-as-imperatives contract:** security best practices are encoded inline as `Do NOT/Never` imperatives plus a lightweight `## Scope` subsection (Terraform/CDK/Pulumi excluded), not as imported `## In Scope`/`## Out of Scope` headings (ref: design Decision 2, Q9).

## Slice 1: Author the `aws-cli` skill (SKILL.md + references)

**Goal:** A complete, live-triggerable `aws-cli` documentation skill — SKILL.md
with valid five-field frontmatter and all required body sections, plus the three
single-topic reference files it links to — discoverable and invocable end-to-end
in a Claude Code session. This is the full feature; the four files are mutually
dependent (SKILL.md links the references; the references have no standalone
verification path) and form one unit of work with a single acceptance gate (ref:
design §Delta, §Desired End State).

**Files touched:**

- ✨ `.claude/skills/aws-cli/SKILL.md` — five-field frontmatter (`name: aws-cli`, `command: /aws-cli`, trigger-phrased `description`, `argument-hint`, `allowed-tools`) + body sections: Authentication & Profiles (SSO over IAM keys, `sts get-caller-identity`, named profiles, `role_arn`/`source_profile`/`external_id`, CI/CD roles), Environment & Config, Output Formatting & Filtering (`--query`, `--output`, `AWS_PAGER`), Pagination, Waiters, per-service operations (S3/EC2/ECS/Lambda/IAM/CloudFormation), Error Handling & Scripting (exit codes, retries, idempotency), Security (`Do NOT/Never` imperatives), Scope.
- ✨ `.claude/skills/aws-cli/references/jmespath.md` — `--query` JMESPath patterns: field selection, filters, date ranges, text-output column ordering.
- ✨ `.claude/skills/aws-cli/references/waiters.md` — common built-in waiter commands per service + exit-code-255 handling note.
- ✨ `.claude/skills/aws-cli/references/services.md` — per-service cheat sheets: S3 high-level vs `s3api`, EC2 filters/tags/launch templates, ECS deploy/exec, Lambda deploy/invoke/log decode, IAM simulate/least-privilege, CloudFormation `deploy`/change-set/drift.

**Verification:**

- [ ] Frontmatter contract holds: SKILL.md has exactly the five fields, and `name == directory name (aws-cli) == command (aws-cli)`.
- [ ] All `references/<topic>.md` links in SKILL.md resolve to existing sibling files (no broken relative paths).
- [ ] All three reference topics present and single-topic (jmespath, waiters, services).
- [ ] All acceptance-criterion sections present in SKILL.md body (auth, env/config, formatting, pagination, waiters, six services, error/scripting, security, scope).
- [ ] Budget check: `wc -l .claude/skills/aws-cli/SKILL.md` body under 500 lines and a token estimate under 5000.
- [ ] Content-hygiene check: grep for account-ID / region / resource-name patterns; only placeholder tokens present.
- [ ] skill-creator (Anthropic skill builder) invoked as the in-slice validation step; its use recorded in the PR description (ref: design Risk register, Q3/Q12). If skill-creator is unavailable in the environment, see Unverified Assumption A3.
- [ ] Live trigger: in a Claude Code session, confirm the `description` fires `/aws-cli` auto-invocation (manual end-to-end, the documented path; ref: Q11).

**Context cost:** M
**Depends on:** none

---

## Unverified Assumptions

- **A1 (OQ1 — `allowed-tools`):** The design does not fix the `allowed-tools` value for a pure reference skill (existing skills are sub-agent wrappers scoping `Agent`/`Bash(...)`/MCP tools). A reference skill may need only `Bash` / `Bash(aws:*)` or none. The frontmatter contract requires the field but its value is unresolved — needs a human decision before/at planning (ref: design OQ1, Q2).
- **A2 (OQ2 — `argument-hint`):** The five-field convention requires `argument-hint`, but this skill takes no positional argument, so the appropriate value is undetermined (ref: design OQ2, Q2).
- **A3 (OQ3 — skill-creator gate):** "Built using the Anthropic skill builder" cannot be verified from committed files because skill-creator is a harness-level/global skill absent from the repo. Whether its invocation is a hard gate — and whether hand-authoring to the same standard is acceptable when it is unavailable in the implementing environment — is unresolved (ref: design OQ3, Q3; Risk register). This affects one verification checkbox in Slice 1.
- **A4 (OQ4 — first multi-file `references/` dir):** Establishing the repo's first multi-file `references/` directory has no exact in-repo precedent (only a single single-topic file exists). The design recommends it (Decision 1, Option A) but flags that combining into one file to stay literally within precedent is an open call — needs sign-off (ref: design OQ4, Decision 1, Q6).
- **A5 (budget enforcement):** Nothing in the repo enforces the 500-line / 5000-token budget; honoring it relies on authoring discipline and a manual check. The precedent lean skill (`qrspi-work`) already overruns at 565 lines, so the budget is an aspiration, not a guaranteed-met contract (ref: design Decision 3, Risk register, Q5).
