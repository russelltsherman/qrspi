# Implementation Plan — Create a new agent skill: using-terraform-cli

**Structure basis:** structure.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total steps:** 14

## Slice 1: Author the using-terraform-cli skill (SKILL.md + references)

### Setup

1. Invoke the global `skill-creator` skill to drive authoring of this skill (user-mandate process criterion; ref: structure.md "Authoring method", design.md Decision/Q4). Document this invocation in the implementation notes. All file creations below are produced through that flow.

2. ✨ Create directory `.claude/skills/using-terraform-cli/references/` — container for the progressive-disclosure reference files (ref: design.md Decision 2). No content; created implicitly by the first reference file write if the tool creates parent dirs.

### Core Logic — SKILL.md

3. ✨ Create `.claude/skills/using-terraform-cli/SKILL.md` — write the five-field YAML frontmatter per `SkillFrontmatter { name, description, command, argument-hint, allowed-tools }`. Set `name: using-terraform-cli` (== directory == slash command, discovery contract). Write `description` in positive "what it does + when to use it" form anchored on Terraform/IaC trigger vocabulary, no SKIP clause (ref: structure.md SkillFrontmatter, design.md Decision 3, Decision 4).

4. ⚠️ Modify `.claude/skills/using-terraform-cli/SKILL.md` — add the core-lifecycle body section: init → validate → plan → apply → destroy (ref: design.md Desired End State "Complete lifecycle").
   - **Current:** file contains frontmatter only (step 3)
   - **After:** frontmatter + H2 "Core workflow / lifecycle" section

5. ⚠️ Modify `.claude/skills/using-terraform-cli/SKILL.md` — add state-management section (remote backend, locking, SSE-KMS encryption, versioning, IAM, gitignore, treat-state-as-secret) and add the citation `(see `references/backend-setup.md`)` per the reference-citation contract (ref: structure.md Contracts, design.md Desired End State "State management").
   - **Current:** frontmatter + lifecycle section
   - **After:** + H2 "State management" section citing backend-setup.md

6. ⚠️ Modify `.claude/skills/using-terraform-cli/SKILL.md` — add version-pinning section (`required_providers`, `required_version`, commit `.terraform.lock.hcl`, `tfenv`/`asdf`) (ref: design.md Desired End State "version pinning").
   - **Current:** body through state-management section
   - **After:** + H2 "Version pinning" section

7. ⚠️ Modify `.claude/skills/using-terraform-cli/SKILL.md` — add import/moved/removed migration summary plus the citation `(see `references/migration-blocks.md`)` (ref: structure.md Contracts, design.md Desired End State "import/moved/removed").
   - **Current:** body through version-pinning section
   - **After:** + H2 "Refactoring & migration" section citing migration-blocks.md

8. ⚠️ Modify `.claude/skills/using-terraform-cli/SKILL.md` — add CI/CD-with-OIDC summary plus the citation `(see `references/cicd-pipelines.md`)` (ref: structure.md Contracts, design.md Desired End State "CI/CD with OIDC").
   - **Current:** body through migration section
   - **After:** + H2 "CI/CD" section citing cicd-pipelines.md

9. ⚠️ Modify `.claude/skills/using-terraform-cli/SKILL.md` — add the remaining body sections: secrets management + security hardening (secrets manager + data sources, ephemeral values 1.10+, OIDC, least-privilege, audit logging), workspace-vs-environment separation, and module authoring + testing (`.tftest.hcl`, `sensitive`). Add an explicit scope note excluding provider-specific resource config, CDKTF, and HCL deep-dives (ref: structure.md Scope contract, design.md Desired End State, Risk Register).
   - **Current:** body through CI/CD section
   - **After:** complete body covering every Desired-End-State acceptance criterion

### Core Logic — Reference files

10. ✨ Create `.claude/skills/using-terraform-cli/references/backend-setup.md` — S3+DynamoDB canonical example with GCS/Azure/HCP equivalents, partial config, encryption/versioning/IAM. One H1, numbered/descriptive H2 sections, self-contained, no back-link to the body (ref: structure.md citation contract, design.md Delta).

11. ✨ Create `.claude/skills/using-terraform-cli/references/cicd-pipelines.md` — pipeline stage order, OIDC auth, plan-on-PR, manual approval gates, security scanning, plan-artifact passing. One H1, numbered H2s, self-contained, no back-link (ref: structure.md citation contract, design.md Delta).

12. ✨ Create `.claude/skills/using-terraform-cli/references/migration-blocks.md` — `import`/`moved`/`removed` patterns, refactor-in-small-batches, plan-before-apply discipline. One H1, numbered H2s, self-contained, no back-link (ref: structure.md citation contract, design.md Delta).

### Docs

13. ⚠️ Modify `.claude/CLAUDE.md` — add `using-terraform-cli` to the human-facing "Available skills" list (documentation only; not required for discovery; OQ2 default = update). Drop this step if the reviewer prefers CLAUDE.md untouched.
    - **Current:** "Available skills" list contains the 9 `qrspi-*` skills
    - **After:** list also names `/using-terraform-cli` with a one-line description

### Verify Slice 1

14. **Checkpoint:** run the verification commands below and confirm each criterion.
    - Command: `wc -l .claude/skills/using-terraform-cli/SKILL.md`
    - [ ] `wc -l` reports < 500 lines (body budget contract)
    - [ ] Frontmatter has all five fields and `name: using-terraform-cli`; directory name == name == slash command (discovery contract)
    - Command: `grep -o 'references/[a-z-]*\.md' .claude/skills/using-terraform-cli/SKILL.md | sort -u`
    - [ ] Each of backend-setup.md, cicd-pipelines.md, migration-blocks.md is cited from the body via the `(see `references/<file>.md`)` parenthetical (citation contract)
    - Command: `ls .claude/skills/using-terraform-cli/references/`
    - [ ] All three required reference files exist
    - [ ] Each reference has exactly one H1 with numbered/descriptive H2s and no back-link to the body
    - [ ] Body sections cover every Desired-End-State AC: lifecycle, state, version pinning, import/moved/removed, CI/CD+OIDC, secrets/security, workspaces, modules/testing
    - [ ] `/using-terraform-cli` is invocable and appears in the available-skills list (manual e2e — the in-repo verification standard)
    - [ ] `skill-creator` was used to author the skill (process criterion documented in the slice)

---

## Rollback Notes

- Steps 2–12 (new skill files): `rm -rf .claude/skills/using-terraform-cli/` removes the entire skill; auto-discovery drops it from the available-skills list immediately, no manifest/index cleanup needed (discovery contract).
- Step 13 (CLAUDE.md edit): revert the single added "Available skills" line; documentation-only, no functional impact.
- No DB migrations, no config changes, no destructive operations in this slice.

## Open items carried from structure (resolve before/at review)

- OQ4: whether to add a fourth `references/security-hardening.md` or keep security inline (step 9). Plan keeps it inline as the committed minimum; add a 13th file + its citation if the reviewer wants it split.
- OQ3: `skill-creator` acceptance bar beyond "valid frontmatter + manual e2e" needs human direction (step 14 process criterion).
