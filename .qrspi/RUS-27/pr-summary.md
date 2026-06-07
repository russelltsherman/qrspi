# PR: RUS-27: Add writing-github-actions agent skill

**Ticket:** RUS-27
**Design:** design.md @ 2026-06-04T00:00:00Z
**Structure:** structure.md @ 2026-06-06T00:00:00Z

## Summary

Adds a new content-only Claude Code skill `writing-github-actions` that auto-triggers when an agent authors or hardens GitHub Actions workflow YAML. The skill is a lean lifecycle-organized `SKILL.md` (145 lines, ~1655 tokens — under the 500-line / 5000-token AC) plus four on-demand `references/*.md` files covering security hardening, OIDC setup, common workflow templates, and matrix strategies. SHA-pinning is encoded as a single canonical non-negotiable rule in the body and echoed in the security reference. Reviewers should focus on (1) frontmatter conformance — `name` == directory == command slug, with `allowed-tools` intentionally omitted (OQ4); and (2) that the sample workflows are zizmor-conformant by construction since there is no in-repo zizmor gate (verification is rule-conformance, not a machine-proven run).

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC: agentskills.io directory structure + valid SKILL.md frontmatter | `.claude/skills/writing-github-actions/SKILL.md` (frontmatter) + `references/` dir | T8 manual: `name` == dir == slug → PASS; T13 frontmatter vs skill-creator anatomy → PASS |
| AC: built using the Anthropic skill builder | `SKILL.md` authored to in-repo precedent; reconciled to skill-creator baseline | T13 skill-creator reconciliation → PASS (full eval/benchmark loop deferred — see Open Items) |
| AC: SKILL.md body under 500 lines / 5000 tokens | `.claude/skills/writing-github-actions/SKILL.md` (145 lines) | T10 manual line/token count: 145 < 500, ~1655 < 5000 → PASS |
| AC: reference material (security hardening, OIDC, common templates, matrix) | `references/security-hardening-checklist.md`, `references/oidc-setup-patterns.md`, `references/common-workflow-templates.md`, `references/matrix-strategy-examples.md` | T9 four references exist + all pointers relative & resolve → PASS |
| AC: SHA-pinning as a non-negotiable default | `SKILL.md` body (canonical) + `references/security-hardening-checklist.md` §1 (echo) | T11 SHA-pinning hard rule in body AND security ref → PASS |
| AC: covers full workflow lifecycle (triggers→deployments) | `SKILL.md` body (lifecycle-organized) | T11 AC topics present (triggers/jobs/steps/caching/artifacts/secrets/deployments) → PASS |
| AC: reusable workflows vs composite actions guidance | `SKILL.md` decision section; `references/common-workflow-templates.md` skeletons | T11 reusable-vs-composite decision section present → PASS |
| AC: concurrency and performance optimization patterns | `SKILL.md` concurrency/performance section | T11 concurrency/performance section present → PASS |
| AC: produces workflows that pass zizmor without warnings | `references/security-hardening-checklist.md` (zizmor-mapped rules); sample templates | T12 samples zizmor-conformant by construction (SHA-pinned, default-deny perms, env indirection, no `pull_request_target` PR-head checkout) → PASS |

## Changes by Slice

### Slice 1: Author writing-github-actions skill (SKILL.md + four references)

| File | Change | Lines |
|------|--------|-------|
| `.claude/skills/writing-github-actions/SKILL.md` | ✨ new | +145 |
| `.claude/skills/writing-github-actions/references/security-hardening-checklist.md` | ✨ new | +109 |
| `.claude/skills/writing-github-actions/references/oidc-setup-patterns.md` | ✨ new | +93 |
| `.claude/skills/writing-github-actions/references/common-workflow-templates.md` | ✨ new | +158 |
| `.claude/skills/writing-github-actions/references/matrix-strategy-examples.md` | ✨ new | +99 |

### Workflow artifacts (QRSPI phase outputs, non-feature)

| File | Change | Lines |
|------|--------|-------|
| `.qrspi/RUS-27/questions.md` | ✨ new | +49 |
| `.qrspi/RUS-27/research.md` | ✨ new | +242 |
| `.qrspi/RUS-27/design.md` | ✨ new | +113 |
| `.qrspi/RUS-27/structure.md` | ✨ new | +81 |
| `.qrspi/RUS-27/plan.md` | ✨ new | +64 |
| `.qrspi/RUS-27/worktree.md` | ✨ new | +49 |
| `.qrspi/RUS-27/impl-log.md` | ✨ new | +53 |

## Testing Summary

This is a prose-only skill — no automated tests apply (repo policy: prompt/skill behavior verified by manual e2e; ref design Q12). Verification is the per-task manual checkpoints from plan §7:

- [x] Slice 1: T8 — `name` frontmatter == dir == command slug (`writing-github-actions`) — PASS
- [x] Slice 1: T9 — four `references/*.md` exist; all four SKILL.md pointers relative (no `./`, no absolute) and resolve — PASS
- [x] Slice 1: T10 — SKILL.md 145 lines (< 500) and ~1655 tokens (< 5000) — PASS
- [x] Slice 1: T11 — AC topics present (lifecycle, reusable-vs-composite, concurrency/performance, SHA-pinning in body + security ref) — PASS
- [x] Slice 1: T12 — sample templates zizmor-conformant by construction; three tag/branch `uses:` hits are intentional WRONG counter-examples — PASS
- [x] Slice 1: T13 — skill-creator baseline reconciliation (third-person description + trigger phrases + negative scope; progressive disclosure; frontmatter anatomy) — PASS
- [ ] Manual e2e: a GHA-YAML-authoring prompt auto-triggers the skill — not captured (no in-repo dispatch logger, ref Q13)

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| (none) | | | impl-log records zero deviations from structure.md |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| "Built using the Anthropic skill builder" unverifiable in-repo (OQ1) | accepted — authored to in-repo precedent + reconciled to skill-creator baseline (T13); full eval/benchmark loop deferred | Delete `.claude/skills/writing-github-actions/` |
| Frontmatter shape mismatch with agentskills.io spec (OQ2) | mitigated — used in-repo `name`+`description` baseline; reconciled against skill-creator anatomy (T13 PASS) | Edit `SKILL.md` frontmatter |
| Body exceeds <500-line AC given breadth | mitigated — body 145 lines via aggressive `references/` offload (Decision 2) | n/a |
| "Passes zizmor without warnings" not machine-provable in-repo (OQ3) | accepted — encoded zizmor-aligned hard rules; conformance verified by construction, not an in-repo gate | n/a |
| `scripts/`/`assets/` would set un-precedented structure | mitigated — only `references/` used; no `scripts/`/`assets/` added | n/a |

No code paths changed; rollback for the entire feature is deleting the additive `.claude/skills/writing-github-actions/` directory.

## Open Items

- The skill-creator **eval/benchmark loop** (run_loop/aggregate/viewer) was intentionally NOT run: it writes eval artifacts to a sibling workspace outside `.worktrees/RUS-27/`, violating the implement agent's worktree-scope constraint. worktree.md earmarks it for a separate fresh-context session. Optional standalone follow-up if full triggering-accuracy optimization is wanted (not required by any §Contract).
- Manual e2e auto-trigger confirmation is not captured (no in-repo dispatch logger, ref Q13) — observe at review.
- OQ3 unresolved: whether the team wants a captured zizmor run as acceptance evidence vs. documented rule-conformance.
- Optional `references/zizmor-audit.md` not created — security checklist absorbed zizmor guidance (Decision 3).
