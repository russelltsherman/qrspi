# PR: RUS-16 Add kustomize-cli agent skill (SKILL.md + references)

**Ticket:** RUS-16
**Design:** design.md @ 2026-06-04T00:00:00Z
**Structure:** structure.md @ 2026-06-06T00:00:00Z

## Summary

This PR adds a new self-contained agent skill, `kustomize-cli`, under
`.claude/skills/kustomize-cli/`. It ships a lean 202-line `SKILL.md` with the
repo's standard five-field frontmatter plus a `references/` directory of four
deep-dive files (patch selection, generators, transformers, CI validation). The
skill teaches base/overlay/component layout, all five resource types (patches,
generators, transformers, components, replacements), the strategic-merge vs
JSON-6902 decision framework, deprecation awareness, and `kubectl apply -k` /
Argo CD / Flux GitOps integration. It is documentation-only — no executable code,
no eval-suite entry, no `.claude/agents/` companion. Reviewer focus: factual
correctness of the net-new kustomize content (deprecated-field semantics, patch
rules) since there was zero in-repo source to verify against, and that the
`description` triggers reliably without over-firing.

## Acceptance Criteria Mapping

This skill is documentation, not executable code, so "Test" is the manual
conformance check from plan §9–14 (recorded in impl-log Checkpoints 12–14)
rather than an automated test (no skill-grading harness exists in-repo, ref: Q12).

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: agentskills.io directory structure + valid frontmatter | `.claude/skills/kustomize-cli/SKILL.md:1-8` (five-field block) + `references/` dir | Checkpoint 12: `sed -n '1,12p' SKILL.md` + `ls references/` → 5 fields, `name==dir`, `command:/kustomize-cli`, 4 ref files → PASS |
| AC2: Built using the Anthropic skill builder | Authored via `skill-creator` invocation (impl-log Slice 1, T1) | Process note in impl-log; eval loop intentionally skipped (out of scope, ref: Q12) |
| AC3: SKILL.md body under 500 lines / 5000 tokens | `.claude/skills/kustomize-cli/SKILL.md` | Checkpoint 13: `wc -l` → 202 (<500); `wc -w` → 1183 (≈ under 5000 tokens) → PASS |
| AC4: Reference material in `references/` | `references/{patch-selection,generators,transformers,ci-validation}.md` | Checkpoint 14: 4/4 ref pointers resolve, no MISSING → PASS |
| AC5: Example base/overlay/component directory tree | inline tree in `SKILL.md` | Checkpoint 14: inline base/overlay/component tree present → PASS |
| AC6: Covers all resource types (patches, generators, transformers, components, replacements) | `SKILL.md:71,92,110,129,145` (one section each) | Checkpoint 14: all five sections present, each linking a reference → PASS |
| AC7: Strategic-merge vs JSON-patch decision framework | `references/patch-selection.md`; `SKILL.md:71-79` | Checkpoint 14: decision framework present + linked → PASS |
| AC8: `kubectl apply -k` AND GitOps integration | `SKILL.md:173-187` (apply -k, build \| kubectl apply, Argo CD, Flux) | Checkpoint 14: apply -k / Argo CD / Flux / build pipeline all present → PASS |
| AC9: Deprecation awareness (vars→replacements, patchesStrategicMerge→patches) | `SKILL.md:154-162` table; `references/patch-selection.md`, `references/transformers.md` | Checkpoint 14: deprecation table present → PASS |

## Changes by Slice

### Slice 1: Author the kustomize-cli skill (SKILL.md + references)

| File | Change | Lines |
|------|--------|-------|
| `.claude/skills/kustomize-cli/SKILL.md` | ✨ new | +202 |
| `.claude/skills/kustomize-cli/references/patch-selection.md` | ✨ new | +125 |
| `.claude/skills/kustomize-cli/references/transformers.md` | ✨ new | +117 |
| `.claude/skills/kustomize-cli/references/generators.md` | ✨ new | +114 |
| `.claude/skills/kustomize-cli/references/ci-validation.md` | ✨ new | +94 |

### Workflow artifacts (not part of the deliverable; QRSPI phase outputs)

| File | Change | Lines |
|------|--------|-------|
| `.qrspi/RUS-16/research.md` | ✨ new | +306 |
| `.qrspi/RUS-16/design.md` | ✨ new | +101 |
| `.qrspi/RUS-16/structure.md` | ✨ new | +95 |
| `.qrspi/RUS-16/plan.md` | ✨ new | +73 |
| `.qrspi/RUS-16/questions.md` | ✨ new | +51 |
| `.qrspi/RUS-16/worktree.md` | ✨ new | +36 |
| `.qrspi/RUS-16/impl-log.md` | ✨ new | +25 |

## Testing Summary

This slice has no code under test; verification is the plan's manual conformance
checks, executed and recorded in impl-log Checkpoints 12–14.

- [x] Slice 1: frontmatter + structure — `sed -n '1,12p' SKILL.md` + `ls references/` — 5 fields present, `name==dir`, `command:/kustomize-cli`, 4 reference files — PASS (Checkpoint 12)
- [x] Slice 1: size budget — `wc -l SKILL.md` → 202 (<500); `wc -w SKILL.md` → 1183 (≈ under 5000 tokens) — PASS (Checkpoint 13)
- [x] Slice 1: link resolution + coverage — grep of `references/…` pointers → 4/4 resolve, no MISSING; all five resource sections present; deprecation table, GitOps, inline base/overlay/component tree present — PASS (Checkpoint 14)
- [x] Manual verification (PR-phase re-check): `wc -l/-w SKILL.md` → 202 / 1183; `ls references/` → 4 files; `grep references/ SKILL.md` → 6 pointers all resolving to existing siblings; resource sections at SKILL.md:71/92/110/129/145

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| (none) | All contracts (`frontmatter`, `referenceLink`, `deprecationGuidance`, `secretExample`, `failureReporting`, `sizeBudget`) and `SkillFrontmatter` satisfied exactly per impl-log | matches structure.md | No deviations reported. |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| kustomize reference content is entirely net-new (zero in-repo source) — factual errors on deprecated fields / patch semantics could ship | accepted — content authored with deprecation framed as "prefer current, recognize legacy"; correctness still depends on human review (OQ1 version baseline unresolved) | `git revert` the slice commit; deletes `.claude/skills/kustomize-cli/` entirely (additive-only change) |
| SKILL.md silently exceeds 500 lines — no validator exists, `qrspi-work` already overran to 565 | mitigated — body is 202 lines / 1183 words, well under budget; detail offloaded into 4 reference files | n/a (within budget) |
| "Built using the skill builder" criterion is unverifiable in-repo | mitigated — `skill-creator` invoked during authoring and noted; no eval-suite case added (no generic-skill grading support, ref: Q12) | n/a |
| `references/` progressive disclosure is convention-only with no link validator — a mistyped path silently fails | mitigated — all 6 `references/…` pointers manually confirmed to resolve to existing siblings | n/a |

## Open Items

- **OQ1 (open):** kustomize version/API baseline for deprecation guidance is unresolved — a human reviewer must confirm the version where `vars` / `patchesStrategicMerge` were deprecated, since there is no in-repo source. This is the primary review risk.
- **OQ2 (resolved-by-decision):** "Built using the skill builder" is satisfied by invoking `skill-creator` during authoring; the eval/benchmark loop was intentionally not run (no in-repo generic-skill grading path; eval harness is a documented non-functional placeholder).
- **OQ3 (resolved-by-decision):** the canonical example tree is inline `SKILL.md` prose (no `assets/` precedent in-repo). If the team later wants runnable `assets/` manifests, that is a follow-up.
- No tech debt introduced; change is purely additive documentation.
