# PR: RUS-11 Add devcontainer-cli guidance skill

**Ticket:** RUS-11
**Design:** design.md @ 2026-06-03T00:00:00Z
**Structure:** structure.md @ 2026-06-06T00:00:00Z

## Summary

Adds a new self-contained guidance skill, `devcontainer-cli`, under
`.claude/skills/devcontainer-cli/`. It pairs a concise `SKILL.md` body (install +
primary workflow, opinionated defaults, lifecycle/Compose summaries,
troubleshooting) with four progressive-disclosure references covering the
`devcontainer` CLI, the `devcontainer.json` schema, the six lifecycle hooks, and
CI/CD integration via `devcontainers/ci`. Per design Decision 2 this is a content
skill, not a thin wrapper, so no `.claude/agents/` file was added. Reviewers
should focus on: (1) the frontmatter five-key conformance and `name`==directory
invariant, (2) that all four references are cited from the body (no orphans), and
(3) the "this repo is a deliberate exception" caveat that reconciles the general
opinionated defaults with this repo's own hardened build-based devcontainer.

## Acceptance Criteria Mapping

No runtime code exists for this content-authoring feature; "Test" columns are the
inspection checks the impl-log recorded (file existence + `grep` + `wc -l`), since
the repo has no SKILL.md validator and the eval harness is a non-functional
placeholder (design OQ4).

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: agentskills.io directory structure with valid frontmatter | `.claude/skills/devcontainer-cli/SKILL.md` (5-key YAML, `name: devcontainer-cli`) | impl-log Slice 2: stdlib YAML parse — 5 keys in order, `name`==dir |
| AC2: Built using the Anthropic skill builder skill | authored via global `skill-creator` (task T7) | impl-log Slice 2: skill-creator invoked at authoring; OQ1 reconciliation recorded |
| AC3: Body under 500 lines / 5000 tokens | `SKILL.md` (143 lines) | impl-log Slice 2: `wc -l` = 143, within token budget |
| AC4: `references/` covering CLI, schema, lifecycle, CI/CD | `references/{cli-commands,devcontainer-json-schema,lifecycle-decision-tree,cicd-workflows}.md` | impl-log Slice 1: 4 files exist, non-empty, content-grep pass |
| AC5: All six lifecycle hooks with when-to-use guidance | `references/lifecycle-decision-tree.md` | impl-log Slice 1: grep all 6 hook names + skip-on-failure rule |
| AC6: Opinionated defaults (non-root user, lockfile committed, named volumes) | `SKILL.md` §Opinionated defaults | impl-log Slice 2: grep defaults + exception caveat |
| AC7: Docker Compose multi-container patterns | `SKILL.md` §Docker Compose + `references/devcontainer-json-schema.md` Compose table | impl-log Slice 1/2: grep `dockerComposeFile`/`service`/`workspaceFolder`/`shutdownAction` |
| AC8: CI/CD GitHub Actions integration | `references/cicd-workflows.md` | impl-log Slice 1: grep `devcontainers/ci`, `cacheFrom`/`--cache-from`, pre-build |
| AC9: Troubleshooting top issues | `SKILL.md` §Troubleshooting | impl-log Slice 2: grep permissions, cache invalidation, volume ownership, lifecycle failures, slow builds |

## Changes by Slice

### Slice 1: Reference files (CLI, schema, lifecycle, CI/CD)

| File | Change | Lines |
|------|--------|-------|
| `.claude/skills/devcontainer-cli/references/cli-commands.md` | new | +113 |
| `.claude/skills/devcontainer-cli/references/devcontainer-json-schema.md` | new | +151 |
| `.claude/skills/devcontainer-cli/references/lifecycle-decision-tree.md` | new | +115 |
| `.claude/skills/devcontainer-cli/references/cicd-workflows.md` | new | +111 |

### Slice 2: SKILL.md body, frontmatter, and citations

| File | Change | Lines |
|------|--------|-------|
| `.claude/skills/devcontainer-cli/SKILL.md` | new | +143 |

### Workflow artifacts (not feature code)

These QRSPI artifacts are part of the stack but are documentation, not deliverable
skill content.

| File | Change | Lines |
|------|--------|-------|
| `.qrspi/RUS-11/design.md` | new | +108 |
| `.qrspi/RUS-11/impl-log.md` | new | +69 |
| `.qrspi/RUS-11/plan.md` | new | +86 |
| `.qrspi/RUS-11/questions.md` | new | +53 |
| `.qrspi/RUS-11/research.md` | new | +491 |
| `.qrspi/RUS-11/structure.md` | new | +81 |
| `.qrspi/RUS-11/worktree.md` | new | +50 |

## Testing Summary

This feature ships Markdown + YAML content, not executable code; verification is
by inspection (the repo has no SKILL.md validator and the `evals/` harness is a
non-functional placeholder — design OQ4).

- [x] Slice 1: file existence + content grep (plan §7) — all 4 references exist, non-empty, required content present
- [x] Slice 1: `lifecycle-decision-tree.md` names all 6 hooks + skip-on-failure rule — pass
- [x] Slice 1: `cli-commands.md` covers up/exec/build/read-configuration/run-user-commands + 3 named flags — pass
- [x] Slice 1: `devcontainer-json-schema.md` covers image vs build, remoteUser, Compose keys — pass
- [x] Slice 1: `cicd-workflows.md` references `devcontainers/ci`, registry cache, pre-build — pass
- [x] Slice 2: frontmatter valid YAML, 5 keys in order, `name`==dir (stdlib parser; PyYAML unavailable) — pass
- [x] Slice 2: body cites all 4 references by relative path — 4 CITED, 0 ORPHAN — pass
- [x] Slice 2: opinionated defaults + repo-exception caveat present — pass
- [x] Slice 2: Compose summary + troubleshooting (5 topics) present — pass
- [x] Slice 2: body 143 lines (`wc -l`) ≤ 500, within token budget — pass
- [ ] Manual verification: skill loads/auto-triggers in the live harness — deferred to load-time (no in-repo loader)

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| (none) | | | impl-log records zero deviations from structure.md for both slices |

One non-structural plan note: Slice 2 frontmatter validation used a stdlib-only
parser instead of `yaml.safe_load` because PyYAML is not installed in the
worktree. Same assertion, no behavior change — not a structure deviation.

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| Opinionated defaults contradict the repo's own build-based hardened devcontainer | mitigated — explicit "this repo is a deliberate exception" caveat added to `SKILL.md` §Opinionated defaults | Edit/remove the defaults section in SKILL.md |
| SKILL.md body exceeds 500-line / 5000-token budget with nothing in-repo to catch it | mitigated — body is 143 lines; all detail pushed to references | Trim body further; move sections to references/ |
| A reference file is created but never cited (dead reference) | mitigated — grep confirms 4 CITED, 0 ORPHAN | Add missing relative-path citation in SKILL.md |
| "Built using the skill builder" criterion unverifiable in-repo | accepted — skill-creator invoked at authoring (T7); OQ1 reconciliation recorded; cannot be evidenced in-repo | n/a (process attestation) |
| Frontmatter shape diverges from true agentskills.io schema | mitigated — repo 5-key convention used, `name`==dir invariant held; skill-creator emitted no extra keys to keep | Adjust frontmatter keys in SKILL.md |
| (new) Negative "do NOT use" description clause has no in-repo precedent — real-world triggering behavior unverifiable | discovered-new / accepted (design Decision 4) — clause added per ticket scope; triggering surfaces only in the live harness | Remove the negative clause from `description` |

Whole-feature rollback: delete `.claude/skills/devcontainer-cli/`. The skill is
purely additive (no existing files modified per design §Delta), so removal is
clean and affects nothing else.

## Open Items

- AC2 ("Built using the Anthropic skill builder skill") is a process attestation
  recorded in the impl-log; it is not independently verifiable from the repo
  (design OQ1/OQ4). Confirm during review if stronger evidence is required.
- The negative trigger clause (design Decision 4 NEW PATTERN) and the skill's
  auto-invocation behavior can only be validated by a live-harness trigger test;
  no in-repo eval exists to assert it.
- No slash-command wrapper / `.claude/agents/` file was created (intentional,
  design Decision 2). If a wrapper is later wanted, reuse `command: /devcontainer-cli`
  and the `argument-hint` placeholder already in the frontmatter.
- Pre-existing tech debt (not introduced here): `qrspi-work/SKILL.md` is 565 lines,
  over the 500-line guideline, with no in-repo size check (design Q6/Q7). Out of
  scope for this ticket.
