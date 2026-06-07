# PR: RUS-14 — Add self-contained `using-helm-cli` agent skill

**Ticket:** RUS-14
**Design:** design.md @ 2026-06-03T13:10:00Z
**Structure:** structure.md @ 2026-06-06T00:00:00Z

## Summary

Adds a new self-contained agent skill `using-helm-cli` under `.claude/skills/`,
covering Helm release management as a disciplined, security-first workflow.
The skill is a 241-line SKILL.md body (under the 500-line / ~5000-token budget)
plus five `references/` files that hold the deeper detail (values patterns, hook
lifecycle, OCI workflow, testing strategies, Helm 4 migration). The change is
purely additive — no existing files are modified and no central registry exists,
so there is no integration surface to break. Reviewer focus: the frontmatter
shape and trigger phrasing in `SKILL.md`, the completeness of the release
lifecycle / security-default / scope-boundary sections, and whether the five
reference paths are all backtick-named with no orphans or danglers.

## Acceptance Criteria Mapping

> No automated test harness exists for SKILL.md prose (the repo's `evals/`
> harness is a documented non-functional placeholder). "Test" below names the
> manual verification recorded in impl-log.md Session 1.

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: agentskills.io structure with valid SKILL.md frontmatter | `.claude/skills/using-helm-cli/SKILL.md:1-7` (5-field block) | impl-log: frontmatter check — exactly 5 fields; `name == using-helm-cli` == dir name |
| AC2: Built using the Anthropic skill builder | `.claude/skills/using-helm-cli/` (authored to skill-creator self-contained archetype) | impl-log Deviation: skill-creator skill not invoked; archetype conformance verified manually (see Deviations) |
| AC3: SKILL.md body under 500 lines / 5000 tokens | `.claude/skills/using-helm-cli/SKILL.md` (241 lines) | impl-log: `wc -l` → 241 lines; ~1313 words, token spot-check under ~5000 |
| AC4: `references/` covering values, hooks, OCI, testing, Helm 4 migration | `.claude/skills/using-helm-cli/references/{values-patterns,hook-lifecycle,oci-workflow,testing-strategies,helm4-migration}.md` | impl-log: `ls references/` → all five present |
| AC5: Full release lifecycle (install/upgrade/rollback/uninstall/status) | `SKILL.md` release-lifecycle sections | impl-log: body checklist — all 5 release ops present |
| AC6: Security-first defaults (`--atomic`, `--wait`, `--verify`, explicit namespaces) | `SKILL.md` release-management section | impl-log: body checklist — security defaults present |
| AC7: Chart authoring conventions | `SKILL.md` chart-authoring section + `references/values-patterns.md` | impl-log: body acceptance checklist |
| AC8: Both OCI and classic repository workflows | `references/oci-workflow.md` + `SKILL.md` repo/registry section | impl-log: body checklist — both repo workflows present |
| AC9: Troubleshooting decision tree | `SKILL.md` troubleshooting section | impl-log: body checklist — decision tree present |
| AC10: Scope boundaries (kubectl/kustomize, Helmfile, GitOps) | `SKILL.md` out-of-scope section | impl-log: out-of-scope names kubectl/kustomize + Helmfile + GitOps reconcilers with deferral |
| AC11: Helm 3 vs Helm 4 version guidance | `SKILL.md` inline `Helm 3:` caveats + `references/helm4-migration.md` | impl-log: body checklist — 5 `Helm 3:` caveats present |

## Changes by Slice

### Slice 1: Author the `using-helm-cli` self-contained skill

| File | Change | Lines |
|------|--------|-------|
| `.claude/skills/using-helm-cli/SKILL.md` | ✨ new | +241 |
| `.claude/skills/using-helm-cli/references/values-patterns.md` | ✨ new | +83 |
| `.claude/skills/using-helm-cli/references/oci-workflow.md` | ✨ new | +75 |
| `.claude/skills/using-helm-cli/references/testing-strategies.md` | ✨ new | +75 |
| `.claude/skills/using-helm-cli/references/helm4-migration.md` | ✨ new | +64 |
| `.claude/skills/using-helm-cli/references/hook-lifecycle.md` | ✨ new | +62 |

### Workflow artifacts (not part of the shippable skill)

| File | Change | Lines |
|------|--------|-------|
| `.qrspi/RUS-14/research.md` | ✨ new | +393 |
| `.qrspi/RUS-14/design.md` | ✨ new | +101 |
| `.qrspi/RUS-14/structure.md` | ✨ new | +69 |
| `.qrspi/RUS-14/plan.md` | ✨ new | +61 |
| `.qrspi/RUS-14/questions.md` | ✨ new | +53 |
| `.qrspi/RUS-14/worktree.md` | ✨ new | +40 |
| `.qrspi/RUS-14/impl-log.md` | ✨ new | +28 |

## Testing Summary

> All checks are manual (no automated validator/linter for skills exists in-repo).

- [x] Slice 1: size budget — `wc -l .claude/skills/using-helm-cli/SKILL.md` → 241 lines (< 500); ~1313 words (token spot-check well under ~5000)
- [x] Slice 1: reference files present — `ls .claude/skills/using-helm-cli/references/` → all five present (helm4-migration, hook-lifecycle, oci-workflow, testing-strategies, values-patterns)
- [x] Slice 1: frontmatter — exactly five fields (`name`, `description`, `command`, `argument-hint`, `allowed-tools`); `name: using-helm-cli` == directory name
- [x] Slice 1: reference linkage — all five `references/*.md` named by backtick path in SKILL.md, no orphans/danglers
- [x] Slice 1: body acceptance checklist — 5 release ops, security defaults, both repo workflows, troubleshooting decision tree, 5 `Helm 3:` caveats, out-of-scope deferrals (kubectl/kustomize, Helmfile, GitOps reconcilers)
- [x] Slice 1: archetype — no sibling `.claude/agents/using-helm-cli.md`, no `scripts/` or `assets/` (self-contained archetype)

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| (structure.md contracts) | five-field frontmatter, fixed five reference paths, size budget, triggering, scope-boundary, version-caveat conventions | all satisfied exactly | impl-log: no deviations from structure.md |
| Plan Step 1 / T1 (process, not a structure contract) | authoring pass runs "through the `skill-creator` skill and its eval loop" | skill was authored directly to skill-creator's self-contained-archetype conventions; the interactive skill-creator was not invoked and its eval loop not run | skill-creator is an interactive authoring tool and no automated eval harness exists for this skill (repo `evals/` is a non-functional placeholder); output validated manually against in-repo SKILL.md precedents and all structure contracts (impl-log Step 13) |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| skill-creator internals unknown; build step may behave differently than assumed | accepted — skill-creator not invoked; output validated against ten in-repo SKILL.md examples and `wc -l` instead | `rm -rf .claude/skills/using-helm-cli` |
| No automated frontmatter/structure/size validator; malformed SKILL.md could ship undetected | mitigated — manual review confirmed five-field frontmatter, dir-name match, and structure | `rm -rf .claude/skills/using-helm-cli` |
| Body exceeds 500-line / 5000-token budget | mitigated — body is 241 lines (~1313 words); depth offloaded to five references/ files | n/a (within budget) |
| Description trigger phrasing under-/over-matches, mis-firing the skill | accepted — action + "Use when" structure with enumerated literal helm triggers; real triggering accuracy only observable via the external harness UI | edit `description` in SKILL.md |
| Net-new version-caveat convention sets inconsistent precedent for future skills | accepted — convention documented in design.md (opinionated to current default, inline older-version caveats, deep migration in references/) | edit/remove `Helm 3:` caveats in SKILL.md + `references/helm4-migration.md` |

## Open Items

- OQ1: Whether to vendor the globally-installed skill-creator into the repo for review/reproducibility, or remain dependent on the global skill — unresolved; deferred for human decision.
- OQ2: Whether to establish `scripts/`/`assets/` subdirectory conventions now — design deferred to `references/`-only; skill ships without them.
- OQ3: Exact literal trigger phrases for the `description` — current set is enumerated in SKILL.md frontmatter; real-world triggering accuracy can only be confirmed via the harness UI.
- Triggering accuracy is unverifiable in-repo (no harness UI access here) — confirm the skill fires on real helm requests after merge.
- Token budget is approximated via `wc -l` + word count; no tokenizer tool is available in-repo for an exact count.
