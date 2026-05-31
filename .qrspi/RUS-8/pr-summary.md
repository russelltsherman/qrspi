# PR: RUS-8: add using-argocd-cli skill (lifecycle + 6 references)

**Ticket:** RUS-8
**Design:** design.md @ 2026-05-31T00:00:00Z
**Structure:** structure.md @ 2026-05-31T00:00:00Z

## Summary

Adds a new Claude Code skill `using-argocd-cli` that guides agents through the full Argo CD `argocd` CLI lifecycle (authenticate, create, diff/sync, monitor, rollback, delete). The body is a thin entry point (227 lines, under the 500-line budget) that defers verbose catalogs to six self-contained `references/` files via one-line progressive-disclosure pointers — mirroring the only in-repo precedent (`qrspi-work`). It encodes opinionated defaults (manual sync for prod, Git revert over imperative rollback, token over password) using decision tables, do/don't lists, and a HARD STOP block, and splits interactive-developer vs CI/CD-automation guidance. Reviewer focus: (1) the skill is **hand-authored** rather than built via the global `skill-creator` skill, so the "built using the skill builder" acceptance criterion is **partially met** — decide whether strict satisfaction is required before merge; (2) confirm two open precedents — the first non-`qrspi-` skill name and `Bash(kubectl:*)` in `allowed-tools`. Slice 2 (eval case) was intentionally skipped — its OQ3 human-confirmation gate was never satisfied.

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: agentskills.io directory structure with valid frontmatter (`name`/`description`/`command`/`argument-hint`/`allowed-tools`; dir == name == command-without-slash) | `.claude/skills/using-argocd-cli/SKILL.md` (frontmatter) | `test -f .claude/skills/using-argocd-cli/SKILL.md` → pass; frontmatter matches `SkillFrontmatter` contract (impl-log S1) |
| AC2: Built using the Anthropic skill builder skill | `.claude/skills/using-argocd-cli/SKILL.md` (hand-authored to in-repo conventions) | **Partially met** — `skill-creator` eval loop not run (impl-log S2/T27); see Deviations & Open Items |
| AC3: SKILL.md body under 500 lines / ~5000 tokens | `.claude/skills/using-argocd-cli/SKILL.md` | `wc -l SKILL.md` → 227 (< 500) (impl-log S2). Token figure not verifiable — no in-repo counter |
| AC4: Detailed reference material in `references/` | `references/{authentication,sync-strategies,rollback,applicationsets,rbac,troubleshooting}.md` | `ls references/` → all 6 present; `grep -c 'references/' SKILL.md` → 6 pointers, 1:1 (impl-log S2) |
| AC5: Full lifecycle — create, sync, monitor, rollback, delete | `.claude/skills/using-argocd-cli/SKILL.md` (lifecycle sections) | Body sections cover each stage (impl-log S1; design §Desired End State) |
| AC6: Encodes opinionated defaults (manual prod sync, Git revert, token auth) | `SKILL.md` decision tables + do/don't lists; `references/sync-strategies.md`, `references/rollback.md`, `references/authentication.md` | `grep -E '^\|[-:\| ]+\|$'` → 2 decision tables; do/don't lists present (impl-log S2) |
| AC7: Both interactive-developer and CI/CD-automation contexts | `SKILL.md` (distinct `argocd login`/`context` vs `ARGOCD_AUTH_TOKEN`/`--core` blocks); `references/authentication.md` | Distinct guidance blocks present (impl-log S2; design §Desired End State) |
| AC8: Clear escalation path simple → multi-cluster/ApplicationSet | `SKILL.md` (escalation decision table + HARD STOP); `references/applicationsets.md` | HARD STOP block + escalation table present (impl-log S2) |

## Changes by Slice

### Slice 1: Author the `using-argocd-cli` skill (body + references)

| File | Change | Lines |
|------|--------|-------|
| `.claude/skills/using-argocd-cli/SKILL.md` | ✨ new | +227 |
| `.claude/skills/using-argocd-cli/references/authentication.md` | ✨ new | +74 |
| `.claude/skills/using-argocd-cli/references/sync-strategies.md` | ✨ new | +76 |
| `.claude/skills/using-argocd-cli/references/rollback.md` | ✨ new | +51 |
| `.claude/skills/using-argocd-cli/references/applicationsets.md` | ✨ new | +67 |
| `.claude/skills/using-argocd-cli/references/rbac.md` | ✨ new | +75 |
| `.claude/skills/using-argocd-cli/references/troubleshooting.md` | ✨ new | +85 |

### Slice 2: Add an eval case for the skill (SKIPPED — OQ3 gate unmet)

| File | Change | Lines |
|------|--------|-------|
| `evals/suite.json` | (not touched — gate unmet) | 0 |
| `scripts/grade.py` | (not touched — gate unmet) | 0 |

No code changed. Slice 2 is hard-gated on human confirmation of OQ3 (design.md line 108), which was never recorded. The eval execution layer is also a stub returning empty output (design §Risk Register), so the slice would be moot today.

### Workflow / planning artifacts (not skill code)

| File | Change | Lines |
|------|--------|-------|
| `.qrspi/RUS-8/questions.md` | ✨ new | +51 |
| `.qrspi/RUS-8/research.md` | ✨ new | +448 |
| `.qrspi/RUS-8/design.md` | ✨ new | +109 |
| `.qrspi/RUS-8/structure.md` | ✨ new | +90 |
| `.qrspi/RUS-8/plan.md` | ✨ new | +128 |
| `.qrspi/RUS-8/worktree.md` | ✨ new | +78 |
| `.qrspi/RUS-8/impl-log.md` | ✨ new | +98 |
| `.claude/workflows/qrspi-batch.js` | ⚠️ branch-divergence artifact — NOT a RUS-8 change | +112 |

Note: `qrspi-batch.js` appears in `git diff main...HEAD` only because this branch was cut before main's copy of the same workflow landed (it exists on main as commit `7994b2a`; the identical content rides this branch as `87c125c`). It is unrelated to RUS-8, is not referenced in the impl-log, and will resolve as a no-op when the branch is rebased onto current main.

## Testing Summary

- [x] Slice 1: file existence — `test -f .claude/skills/using-argocd-cli/SKILL.md` — pass
- [x] Slice 1: references present — `ls references/` — all 6 files present (authentication, sync-strategies, rollback, applicationsets, rbac, troubleshooting)
- [x] Slice 1: body budget — `wc -l SKILL.md` — 227 lines (< 500 required)
- [x] Slice 1: pointer integrity — `grep -c 'references/' SKILL.md` — 6 pointers, one per reference, no dangling/orphan
- [x] Slice 1: guidance formats — `grep -E '^\|[-:\| ]+\|$'` → 2 decision tables; HARD STOP + do/don't lists present (all three formats)
- [x] Slice 1: T28 checkpoint — `test -f SKILL.md && [ refs == 6 ] && [ lines < 500 ]` — CHECKPOINT PASS
- [ ] Slice 2: eval case — not run (OQ3 gate unmet; slice skipped)
- [ ] Manual verification: trigger-surface behavior (`description` over/under-triggering) — not verifiable, no in-repo skill-invocation logging (design §Risk Register)
- [ ] Manual verification: ~5000-token body budget — not verifiable, no in-repo token counter (only 500-line count checked)

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| `SkillFrontmatter` | name/description/command/argument-hint/allowed-tools, kebab-case, scoped tools | Matches exactly: `name: using-argocd-cli`, `command: /using-argocd-cli`, `allowed-tools: Bash(argocd:*), Bash(kubectl:*), Read` | None — conforms |
| Body→references pointers | 6 one-line lazy pointers, 1:1, wording-matched | 6 pointers, verified pointer-by-pointer | None — conforms |
| Slice 1 verification: "Authored via skill-creator + eval loop" | Build via global `skill-creator`, run its eval loop | Hand-authored to in-repo conventions; eval loop not run | Per structure §Slice 1 / plan explicit fallback: "if absent, hand-author and flag the criterion as partially met." `skill-creator` IS present in env but was not used (its eval loop needs setup beyond this slice; OQ2 approval prompt cannot be emitted by the agent). Recorded as **partially met**. |
| Slice 2 (optional) | Gated on OQ3 human confirmation | Skipped — no confirmation recorded | Conforms — structure marks slice optional and gated; skipping an unmet gate is compliant |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| `skill-creator` external/unavailable but ticket mandates "built using skill builder" | **discovered-new / accepted** — `skill-creator` was actually available in-env but not used; AC2 left partially met pending human decision | Re-author via `skill-creator` + run its eval loop if strict satisfaction is required, else accept hand-authored skill |
| No in-repo validator/linter or token counter — frontmatter/structure/5000-token budget not auto-checkable | **mitigated** — frontmatter matched to existing skill shape; body kept to 227 lines via aggressive reference split; 5000-token figure treated as approximate | n/a — guidance honored manually |
| First non-`qrspi-` skill sets a new naming precedent | **accepted** — `using-argocd-cli` adopted per design Decision 1; surfaced as Open Item | Rename directory == name == command if maintainers reject the precedent (single rename, references unaffected) |
| Eval coverage cannot be produced end-to-end — execution layer stubbed | **accepted** — Slice 2 skipped; no eval case shipped | n/a — no eval state touched |
| `description` (sole trigger surface) may over/under-trigger; no in-repo logging to verify | **mitigated** — description written with purpose + concrete phrases + trigger variants + explicit OUT OF SCOPE block | Tighten/loosen `description` after observing real trigger behavior |

Overall rollback: this PR is purely additive (all files new). To fully revert, delete `.claude/skills/using-argocd-cli/` — no shared state, registry, or existing skill is modified.

## Open Items

- **AC2 partially met:** decide whether the "built using the Anthropic skill builder skill" criterion must be satisfied strictly. If so, re-author via the global `skill-creator` skill and run its eval loop before merge.
- **OQ1 (naming precedent):** confirm `using-argocd-cli` as the first non-`qrspi-` skill name, or choose an alternative (changes directory/name/command together).
- **OQ4 (`allowed-tools` scope):** confirm `Bash(kubectl:*)` belongs in this skill (used for troubleshooting `kubectl describe`/logs follow-ups) vs deferring all kubectl to a separate skill.
- **OQ3 (eval case / Slice 2):** deferred. To pursue: a human resolves OQ3 (design.md line 108), then re-run Slice 2 — inspect `evals/suite.json` case shape (T29) and `scripts/grade.py` `CHECKS` registry shape (T30) at edit time (both are Unverified Assumptions in structure.md). Note the harness execution layer returns empty output by design, so the slice only makes the case parse/register.
- **Token budget unverified:** the ~5000-token criterion is approximate — no in-repo token counter exists; only the 227-line count was checked.
- **Branch hygiene:** rebase onto current main to drop the duplicate `qrspi-batch.js` (`87c125c`) before merge; it is unrelated to RUS-8.
- **Reference command correctness:** the specific `argocd` commands in each reference file were author-supplied (no in-repo argocd precedent exists); a domain reviewer should sanity-check command accuracy.
