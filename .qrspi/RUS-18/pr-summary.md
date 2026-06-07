# PR: RUS-18 Add using-terraform-cli skill (lifecycle, state, CI/CD)

**Ticket:** RUS-18
**Design:** design.md @ 2026-06-06T00:00:00Z
**Structure:** structure.md @ 2026-06-06T00:00:00Z

## Summary

Adds a new self-contained agent skill, `using-terraform-cli`, that captures how to
operate Terraform/OpenTofu safely from the CLI: the full lifecycle (init → validate →
plan → apply → destroy), remote state with locking/encryption, provider and CLI version
pinning, `import`/`moved`/`removed` refactors, CI/CD with OIDC, secrets handling,
workspace-vs-environment separation, and module authoring + testing. The skill follows
the repo's self-contained shape (no `.claude/agents/` counterpart) with progressive
disclosure: a lean 209-line `SKILL.md` body summarizes each topic and cites three
`references/` files for deep detail. Reviewer focus: (1) the frontmatter description /
triggering — it anchors on Terraform/IaC vocabulary and must not collide with future
infra skills; (2) the body/reference split and that every reference is cited from the
body; (3) the two unresolved open questions below (a fourth security reference file, and
whether the `.claude/CLAUDE.md` skill-list edit should stay). Discovery is automatic via
the harness `.claude/skills/*/SKILL.md` scan — no manifest edit was needed.

## Acceptance Criteria Mapping

Verification is by structural self-check plus manual e2e (the in-repo standard; the
`evals/` harness is a non-functional stub). "Test" below names the verification command
from the impl log / structure contract.

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: agentskills.io structure + valid five-field frontmatter | `.claude/skills/using-terraform-cli/SKILL.md` (frontmatter block) | Frontmatter check: all five fields, `name: using-terraform-cli` (impl log §Tests) |
| AC2: built using the Anthropic skill builder | process criterion — `skill-creator` invoked during authoring | Documented in impl-log.md §Deviations from plan (T1) |
| AC3: body under 500 lines / 5000 tokens | `SKILL.md` (209 lines) | `wc -l SKILL.md` → 209 (< 500, pass) |
| AC4: reference material in `references/` (backend, CI/CD, migration) | `references/backend-setup.md`, `references/cicd-pipelines.md`, `references/migration-blocks.md` | `ls references/` → all three exist (pass); `grep references/*.md` → all cited (pass) |
| AC5: complete lifecycle init→validate→plan→apply→destroy | `SKILL.md` core-workflow section | Body-coverage check (impl log §Tests / structure verification) |
| AC6: state management, locking, encryption | `SKILL.md` state section + `references/backend-setup.md` | Body-coverage check; reference-exists check |
| AC7: provider + CLI version pinning | `SKILL.md` version-pinning section | Body-coverage check |
| AC8: import/moved/removed blocks | `SKILL.md` migration summary + `references/migration-blocks.md` | Reference-cited check (pass) |
| AC9: CI/CD with OIDC | `SKILL.md` CI/CD summary + `references/cicd-pipelines.md` | Reference-cited check (pass) |
| AC10: secrets management + security hardening | `SKILL.md` security section | Body-coverage check |
| AC11: workspace vs. environment separation | `SKILL.md` workspaces section | Body-coverage check |
| AC12: module authoring + testing patterns | `SKILL.md` module section | Body-coverage check |
| AC13: `/using-terraform-cli` invocable + in available-skills list | directory/name/command identity (discovery contract) | Manual e2e — pending reviewer (impl log §Notes) |

## Changes by Slice

### Slice 1: Author the using-terraform-cli skill (SKILL.md + references)

| File | Change | Lines |
|------|--------|-------|
| `.claude/skills/using-terraform-cli/SKILL.md` | ✨ new | +209 |
| `.claude/skills/using-terraform-cli/references/backend-setup.md` | ✨ new | +188 |
| `.claude/skills/using-terraform-cli/references/cicd-pipelines.md` | ✨ new | +140 |
| `.claude/skills/using-terraform-cli/references/migration-blocks.md` | ✨ new | +125 |
| `.claude/CLAUDE.md` | ⚠️ modified | +1, -0 |

### Phase artifacts (not part of the deliverable; QRSPI workflow record)

| File | Change | Lines |
|------|--------|-------|
| `.qrspi/RUS-18/questions.md` | ✨ new | +47 |
| `.qrspi/RUS-18/research.md` | ✨ new | +316 |
| `.qrspi/RUS-18/design.md` | ✨ new | +109 |
| `.qrspi/RUS-18/structure.md` | ✨ new | +115 |
| `.qrspi/RUS-18/plan.md` | ✨ new | +84 |
| `.qrspi/RUS-18/worktree.md` | ✨ new | +32 |
| `.qrspi/RUS-18/impl-log.md` | ✨ new | +29 |

## Testing Summary

- [x] Slice 1: body budget — `wc -l SKILL.md` — 209 lines (< 500 budget, pass)
- [x] Slice 1: reference citation — `grep -o 'references/[a-z-]*\.md' SKILL.md | sort -u` — all three references cited (pass)
- [x] Slice 1: references exist — `ls .claude/skills/using-terraform-cli/references/` — backend-setup, cicd-pipelines, migration-blocks all present (pass)
- [x] Slice 1: reference structure — each reference has exactly one Markdown H1, no back-link to SKILL.md (citation contract, pass; extra `# ` grep hits are HCL/YAML code-block comments, not headings)
- [x] Slice 1: frontmatter — five fields present, `name: using-terraform-cli`, positive description with no SKIP clause (discovery contract, pass)
- [ ] Manual verification (pending reviewer): confirm `/using-terraform-cli` appears in the available-skills list and is invocable in a fresh session (auto-discovery; no manifest edit needed)

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| `SkillFrontmatter` | five-field frontmatter, `name: using-terraform-cli`, positive description | matches exactly | none |
| Discovery contract | directory == name == command | holds | none |
| Citation contract | each reference cited from body, one H1, no back-link | holds | none |
| Body budget contract | < 500 lines | 209 lines | none |
| `skill-creator` eval loop | author via skill-creator | skill-creator authoring guidance applied; iterative eval/benchmark loop NOT run | Out of scope for an implement-phase slice; conflicts with in-repo manual-e2e standard; requires external tooling the agent is constrained from using (impl log §Deviations from plan) |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| Body exceeds 500-line / 5000-token target (no tooling gate; qrspi-work already at 565) | mitigated — body is 209 lines via aggressive offload to references | n/a |
| `skill-creator` "built using" criterion unverifiable from repo scope | accepted — treated as a process criterion; authoring guidance applied and documented; eval loop intentionally skipped | n/a |
| Scope creep into provider-specific resource config / HCL depth | mitigated — body has an explicit scope-exclusion note (CLI workflow + conventions only) | n/a |
| Description triggers too broadly / collides with future infra skills | mitigated — triggers anchored on Terraform/OpenTofu/IaC vocabulary; no `qrspi-` prefix | revert SKILL.md frontmatter description |
| Reference files drift from the single existing convention | mitigated — references follow the `review-cascade.md` shape (one H1, numbered H2, body citation) | n/a |
| Rollback (whole skill) | new directory + one-line doc edit only; no code, scripts, DB, or registration touched | delete `.claude/skills/using-terraform-cli/` and revert the `.claude/CLAUDE.md` line |

## Open Items

- **OQ4 — fourth security reference file:** security currently lives inline in the SKILL.md body. Design flags the topic as "reference-sized." Decide whether to add `references/security-hardening.md` or keep it inline. (unresolved; the three named references are the committed minimum)
- **OQ2 — `.claude/CLAUDE.md` skill-list edit:** the one-line addition is documentation only and not required for discovery (default = keep for completeness). Drop it if the reviewer prefers CLAUDE.md untouched.
- **OQ1 — `scripts/` helper:** none added; no runnable helper is required by the ticket and no skill ships `scripts/` today. If one is later justified it must carry a `_test.py` sibling per repo convention.
- **OQ3 — skill-creator eval acceptance bar:** the concrete pass threshold beyond "valid frontmatter + manual e2e" is undefined for a global skill outside repo scope; needs human direction if a stricter bar is wanted.
- **Manual e2e:** the `/using-terraform-cli` invocability + available-skills-list check is the one remaining verification and should be run by the reviewer in a fresh session.
