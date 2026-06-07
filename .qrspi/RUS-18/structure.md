# Structure Outline — Create a new agent skill: using-terraform-cli

**Design basis:** design.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft

## New Types

This is a documentation/skill-authoring task — the only formal "type" is the
SKILL.md YAML frontmatter contract that the harness parses for discovery.

- `SkillFrontmatter { name: string, description: string, command: string, argument-hint: string, allowed-tools: string }`
  — the five-field YAML block opening every `SKILL.md`; for this skill
  `name: using-terraform-cli` (ref: design.md §Decision 4), `description` in the
  positive "what it does + when to use it" form anchored on Terraform/IaC trigger
  vocabulary, no SKIP clause (ref: design.md §Decision 3).

## Modified Types

- None. No code, scripts, DB queries, or registration types are added (ref: design.md §Delta).

## Contracts

These are the cross-file invariants the single slice must satisfy; no cross-slice
runtime interface exists because the work is one cohesive authoring unit.

- **Discovery contract:** directory name `using-terraform-cli` == frontmatter
  `name:` == slash command `/using-terraform-cli`. Harness auto-scans
  `.claude/skills/*/SKILL.md`; no manifest/index edit required (ref: design.md
  §Current State, §Desired End State, Q12).
- **Reference citation contract:** every `references/<file>.md` is cited from the
  SKILL.md body via the inline parenthetical `(see ` + "`references/<file>.md`" + `)`;
  each reference is self-contained, one H1, numbered/descriptive H2 sections, no
  back-link to the body — matching the sole existing precedent `qrspi-work/references/review-cascade.md`
  (ref: design.md §Current State, Q2, Q11).
- **Body budget contract:** `SKILL.md` body stays under 500 lines / ~5000 tokens,
  self-checked with `wc -l` since no tooling gate exists; detail is offloaded to
  `references/` via progressive disclosure (ref: design.md §Decision 2, Q7).
- **Scope contract:** body covers CLI lifecycle + conventions only; explicitly
  excludes provider-specific resource config, CDKTF, and HCL language deep-dives
  (ref: design.md §Risk Register).

## Slice 1: Author the using-terraform-cli skill (SKILL.md + references)

**Goal:** A complete, auto-discovered self-contained skill — valid five-field
frontmatter, lean body covering the full Terraform CLI lifecycle and conventions,
plus the three required reference files — such that `/using-terraform-cli` becomes
invocable and the skill surfaces in the available-skills list. This is one cohesive
authoring unit: the body summarizes and cites the references, so the references
cannot be meaningfully verified apart from the body that references them, and vice
versa (rule 8 — single sitting, ~4-5 files, well under the 10-file cap).

**Files touched:**

- ✨ `.claude/skills/using-terraform-cli/SKILL.md` — new self-contained skill body
  (Decision 1, Option A). Frontmatter per `SkillFrontmatter`. In-body sections:
  core lifecycle (init → validate → plan → apply → destroy), state management
  (remote backend, locking, SSE-KMS, versioning, IAM, gitignore, treat-as-secret),
  version pinning (`required_providers`, `required_version`, commit
  `.terraform.lock.hcl`, `tfenv`/`asdf`), import/moved/removed summary,
  CI/CD-with-OIDC summary, secrets management + security hardening (secrets manager
  + data sources, ephemeral values 1.10+, OIDC, least-privilege, audit logging),
  workspace-vs-environment separation, module authoring + testing (`.tftest.hcl`,
  `sensitive`). Each deep topic cites its reference per the citation contract.
- ✨ `.claude/skills/using-terraform-cli/references/backend-setup.md` — S3+DynamoDB
  canonical example with GCS/Azure/HCP equivalents; partial config;
  encryption/versioning/IAM (ref: design.md §Delta).
- ✨ `.claude/skills/using-terraform-cli/references/cicd-pipelines.md` — pipeline
  stage order, OIDC auth, plan-on-PR, manual approval gates, security scanning,
  plan-artifact passing (ref: design.md §Delta).
- ✨ `.claude/skills/using-terraform-cli/references/migration-blocks.md` —
  `import`/`moved`/`removed` patterns, refactor-in-small-batches, plan-before-apply
  discipline (ref: design.md §Delta).
- ⚠️ `.claude/CLAUDE.md` — optional: add the new skill to the human-facing
  "Available skills" list (documentation only, not required for discovery;
  OQ2 default = update for completeness).

**Authoring method:** route creation through the global `skill-creator` skill per
the user mandate (Decision/process criterion; ref: design.md §Desired End State, Q4)
and document that invocation in the implementation.

**Verification:**
- [ ] `wc -l .claude/skills/using-terraform-cli/SKILL.md` reports < 500 lines (body budget contract).
- [ ] Frontmatter has all five fields and `name: using-terraform-cli`; directory name == name == command (discovery contract).
- [ ] Every `references/*.md` file is cited from the body via the `(see `references/<file>.md`)` parenthetical, and each reference has exactly one H1 with numbered/descriptive H2s and no back-link (citation contract).
- [ ] All three required reference files exist (backend-setup, cicd-pipelines, migration-blocks).
- [ ] Body sections cover every Desired-End-State AC: lifecycle, state, version pinning, import/moved/removed, CI/CD+OIDC, secrets/security, workspaces, modules/testing.
- [ ] `/using-terraform-cli` is invocable and the skill appears in the available-skills list (manual e2e, the in-repo verification standard; ref: Q10, Q12).
- [ ] `skill-creator` was used to author the skill (process criterion documented in the slice).

**Context cost:** L
**Depends on:** none

---

## Unverified Assumptions

- **skill-creator eval / acceptance bar (OQ3, Risk Register):** the "built using
  the Anthropic skill builder" AC and any eval-loop pass threshold cannot be mapped
  to a concrete in-repo file or check — `skill-creator` is a global harness skill
  outside repo scope and the in-repo `evals/`/`run_eval.py` pipeline is a
  non-functional stub. Treated as a process criterion; the concrete pass bar beyond
  "valid frontmatter + manual e2e" needs human direction (ref: design.md OQ3, Q4, Q10).
- **Fourth security/secrets reference file (OQ4):** the design lists security as a
  body AC but flags the topic as reference-sized. Whether to add a fourth
  `references/security-hardening.md` or keep security inline is unresolved; the
  three named references are the committed minimum. Human decision needed before
  finalizing the body/reference split.
- **CLAUDE.md skill-list edit (OQ2):** documentation-only and not required for
  discovery; included as an optional file with default = update. Drop if the
  reviewer prefers to keep CLAUDE.md untouched.
- **`scripts/` helper (OQ1):** assumed omitted — no runnable helper is required by
  the ticket and no skill ships `scripts/` today. If one proves necessary it would
  add a `scripts/` file plus a mandatory `_test.py` sibling (a separate concern not
  scoped here) (ref: design.md OQ1, Q8).
