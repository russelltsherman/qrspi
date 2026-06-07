# PR: RUS-8 Add using-argocd-cli skill for Argo CD GitOps workflows

**Ticket:** RUS-8
**Design:** design.md @ 2026-06-03T00:00:00Z
**Structure:** structure.md @ 2026-06-06T00:00:00Z

## Summary

Adds a new self-contained agent skill, `using-argocd-cli`, that gives Claude
operational knowledge of the Argo CD `argocd` CLI across the full GitOps app
lifecycle (create → sync → monitor → rollback → delete). The skill follows the
repo's existing self-contained pattern (`qrspi-ticket`/`qrspi-work`): a `SKILL.md`
body holding procedure plus bash-fenced examples, with deep per-topic material
offloaded to six on-demand `references/` files cited skill-root-relative. No
existing file is modified — skill discovery is directory-convention only, so this
is a pure additive change. Reviewer focus: (1) correctness of the opinionated
Argo CD operational guidance in the references (sync waves, generator transitions,
RBAC defaults, rollback semantics — domain knowledge not verifiable against the
codebase), and (2) the `description` trigger clause and the manual-only length budget.

## Acceptance Criteria Mapping

ACs are enumerated in design.md §Desired End State. This is a knowledge-skill
deliverable: "tests" are the structure.md contract checks and the impl-log
verification checkpoint, not code unit tests (no runtime code was added).

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: agentskills.io directory structure + valid 5-key frontmatter | `.claude/skills/using-argocd-cli/SKILL.md` (frontmatter: name/description/command/argument-hint/allowed-tools in order; `name`==dir==`command` minus slash; `allowed-tools: Bash`) | impl-log §1.9 `FrontmatterContract` check — PASS |
| AC2: Built using the Anthropic skill-builder (skill-creator) skill | Authored to repo conventions; `skill-creator` run as a validation pass | impl-log T8 `skill-creator` validation — no findings (see Deviations & Open Items: non-interactive pass, not full eval loop) |
| AC3: SKILL.md body under 500 lines / 5000 tokens | `SKILL.md` = 216 lines (body well under target) | impl-log §1.9 manual length check — body = 209 lines, PASS |
| AC4: `references/` covering auth, sync, rollback, ApplicationSet generators, RBAC, troubleshooting | `references/authentication.md`, `sync-strategies.md`, `rollback-procedures.md`, `applicationset-generators.md`, `rbac-configuration.md`, `troubleshooting.md` | impl-log §1.9 `ReferenceTitleContract` + pointer-resolution check — PASS |
| AC5: Full lifecycle (create, sync, monitor, rollback, delete) | `SKILL.md` §Application Lifecycle, §Sync Strategies, §Health Monitoring, §Rollbacks | impl-log §1.9 lifecycle-keywords check — PASS |
| AC6: Opinionated defaults (manual sync for prod, Git revert over rollback, token auth over password) | `SKILL.md` + relevant references as `**bold**` rules | impl-log §1.9 `OpinionatedDefaultsContract` (three bold defaults) — PASS |
| AC7: Both interactive developer and CI/CD automation contexts | `SKILL.md` §Authentication & Context + `references/authentication.md` (interactive `login`/`context` vs token + env-var + `--core`/`--grpc-web`) | impl-log §1.9 auth-context check — PASS |
| AC8: Clear escalation path simple → multi-cluster/ApplicationSet | `SKILL.md` `##` sections ordered Auth → Lifecycle → Sync → Health → Rollbacks → App-of-Apps → ApplicationSets → RBAC → Multi-Cluster → Troubleshooting | impl-log §1.9 `EscalationOrderContract` check — PASS |

## Changes by Slice

### Slice 1: Author the `using-argocd-cli` skill (SKILL.md + six references)

One cohesive slice: SKILL.md plus the six references it cites are a single
mutually-dependent unit with no testability boundary between them.

| File | Change | Lines |
|------|--------|-------|
| `.claude/skills/using-argocd-cli/SKILL.md` | ✨ new | +216 |
| `.claude/skills/using-argocd-cli/references/authentication.md` | ✨ new | +83 |
| `.claude/skills/using-argocd-cli/references/sync-strategies.md` | ✨ new | +97 |
| `.claude/skills/using-argocd-cli/references/rollback-procedures.md` | ✨ new | +60 |
| `.claude/skills/using-argocd-cli/references/applicationset-generators.md` | ✨ new | +56 |
| `.claude/skills/using-argocd-cli/references/rbac-configuration.md` | ✨ new | +73 |
| `.claude/skills/using-argocd-cli/references/troubleshooting.md` | ✨ new | +84 |

### Workflow artifacts (not part of the feature deliverable)

These are QRSPI phase metadata committed alongside the slice; they are not
shipped skill code.

| File | Change | Lines |
|------|--------|-------|
| `.qrspi/RUS-8/design.md` | ✨ new | +105 |
| `.qrspi/RUS-8/impl-log.md` | ✨ new | +24 |
| `.qrspi/RUS-8/plan.md` | ✨ new | +70 |
| `.qrspi/RUS-8/questions.md` | ✨ new | +50 |
| `.qrspi/RUS-8/research.md` | ✨ new | +286 |
| `.qrspi/RUS-8/structure.md` | ✨ new | +70 |
| `.qrspi/RUS-8/worktree.md` | ✨ new | +32 |

Total diff: 14 files, +1306 lines (7 skill files = +669; 7 artifacts = +637).

## Testing Summary

This skill ships prose + bash-fenced examples; there is no runtime code and no
automated SKILL.md validity/trigger test exists in the repo (verified in research).
Verification was the structure.md contract checklist plus the skill-creator pass.

- [x] Slice 1: `python3` §1.9 verification checkpoint — frontmatter key order/values, `name`/`command`/dir == `using-argocd-cli`, quoted description with Use-when/Trigger clause naming argocd/GitOps, `allowed-tools: Bash`, H1, escalation order of the 10 `##` sections, 6 references each with self-titled H1, all body `references/` pointers resolve + root-relative (no `./`/absolute), full-lifecycle keywords, three bold defaults, bash-fenced examples, body < 500 lines → ALL CHECKS PASS (body = 209 lines)
- [x] Slice 1: `skill-creator` validation pass (frontmatter validity, description triggering quality, progressive-disclosure structure) → no findings; skill valid and discoverable
- [ ] Manual verification: `/using-argocd-cli` discovered and triggers in a live session — recommended at review (no automated trigger test exists)
- [ ] Full `skill-creator` eval loop (test prompts, baseline comparison, benchmark viewer, description optimization) — deferred, interactive (see Open Items)

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| (structure contracts) | FrontmatterContract, ReferenceCitationContract, ReferenceTitleContract, EscalationOrderContract, OpinionatedDefaultsContract all honored | All honored | impl-log records zero deviations from structure.md |
| AC2 authoring method | Author/validate through external `skill-creator` skill incl. eval loop | Non-interactive `skill-creator` validation pass only (frontmatter + triggering + structure) | The full interactive eval/iteration loop requires user interaction and is out of scope for autonomous slice implementation; plan.md flags this as an external manual process step. Validation surfaced no findings. (Deviation from plan, not structure.) |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| SKILL.md exceeds 500-line/5000-token target unnoticed (no checker) | Mitigated — body = 209 lines, manually verified well under target | `rm -rf .claude/skills/using-argocd-cli/` |
| `skill-creator` (AC #2) is external and unverifiable in-repo | Accepted/partially mitigated — ran as a non-interactive validation pass (no findings); full interactive eval loop deferred (OQ1 open) | n/a (process step) |
| Reference path citation wrong (absolute or `./`-prefixed) breaks on-demand load | Mitigated — all pointers verified skill-root-relative, no `./`/absolute | edit body pointers in `SKILL.md` |
| First 2+-reference skill drifts from single-file precedent | Mitigated — each of six references has a self-titled H1, cited from one body section | n/a |
| No automated trigger/validity test; mis-scoped `description` fails silent | Accepted — explicit Use-when/Trigger clause embedded; needs manual live trigger check + (deferred) skill-creator eval loop | revise `description` in `SKILL.md` frontmatter |

Overall rollback: this is an additive, create-only change touching no existing
file. Full rollback is `rm -rf .claude/skills/using-argocd-cli/` (plus reverting
the `.qrspi/RUS-8/` artifacts if desired). No migration, no data, no config.

## Open Items

- **OQ1 (AC #2):** Whether the skill *must* be authored through the external
  `skill-creator` skill (and its full interactive eval loop) to be accepted, or
  whether a convention-conforming, validation-passed skill suffices. The full
  eval loop (test prompts, baseline comparison, benchmark viewer, `run_loop.py`
  description optimization) is interactive and was deferred — invoke `skill-creator`
  directly in an interactive session if the reviewer requires it.
- **OQ2 (length budget):** Confirm whether the 500-line/5000-token budget is a
  hard gate measured manually at review. Current body (209 lines) is well within
  it regardless; `qrspi-work` (565 lines) already exceeds it, so non-enforcement
  is the established repo reality.
- **OQ3 (helper scripts):** Design committed to prose + bash examples only (no
  per-skill `scripts/`/`assets/`). If reviewers expect runnable helpers, that is
  new scope and a new per-skill `scripts/` pattern, out of this PR.
- **Reference content accuracy:** The six references encode opinionated Argo CD
  operational knowledge (sync waves, generator transition thresholds, RBAC
  defaults, rollback semantics) not verifiable against the codebase — requires a
  reviewer with Argo CD expertise.
- **No automated trigger test:** Recommend a manual live check that
  `/using-argocd-cli` is discovered and triggers on argocd/GitOps prompts.
