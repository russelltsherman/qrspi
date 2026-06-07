# PR: RUS-20 Add aws-cli documentation skill

**Ticket:** RUS-20
**Design:** design.md @ 2026-06-04T00:00:00Z
**Structure:** structure.md @ 2026-06-06T00:00:00Z

## Summary

Adds a new documentation-only Claude Code skill, `aws-cli`, that provides operational guidance for the AWS v2 CLI: authentication and named profiles, output shaping (`--query`/`--output`), pagination, waiters, per-service operations (S3, EC2, ECS, Lambda, IAM, CloudFormation), error handling/scripting, and security imperatives. The skill follows the established in-repo layout — a directory under `.claude/skills/<name>/` with a five-field-frontmatter `SKILL.md` whose body stays lean by delegating deep detail to three single-topic `references/` files. No existing files are modified and no loader registration is needed; skills are discovered by directory. Reviewers should focus on (1) frontmatter correctness and `name == directory == command` consistency, (2) content hygiene — placeholder tokens only, no real account IDs/regions/ARNs, and (3) whether establishing the repo's first multi-file `references/` directory is acceptable. The skill-creator skill was invoked as the in-slice validation step (no issues); the live `/aws-cli` auto-trigger confirmation remains a manual operator step after merge.

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| agentskills.io directory structure with valid five-field frontmatter | `.claude/skills/aws-cli/SKILL.md` (frontmatter block) | impl-log S2: Frontmatter five-field check (awk) → exactly 5 fields; name==command==dir==`aws-cli` |
| Built using the Anthropic skill builder skill | authoring-time `skill-creator` invocation (no committed artifact) | impl-log S3 T10: skill-creator invoked as validation step → no issues |
| Body under 500 lines / 5000 tokens | `.claude/skills/aws-cli/SKILL.md` (188 lines) + delegation to `references/` | impl-log S3 T14: Budget contract → 188 lines / ~1569 tokens (< 500 / < 5000) → OK |
| Detailed reference material: JMESPath, waiters, service cheat sheets | `references/jmespath.md`, `references/waiters.md`, `references/services.md` | impl-log S1: file-existence checkpoint → 3 created, 0 missing; S2: 3/3 reference links resolve |
| Covers authentication (SSO, profiles, assume-role, env vars) | `SKILL.md` §Authentication & Profiles | impl-log S2: Body-coverage check → section present |
| Covers core services S3, EC2, ECS, Lambda, IAM, CloudFormation | `SKILL.md` §Per-Service Operations + `references/services.md` | impl-log S2/S3: all six services present |
| Output formatting (`--query`, `--output`, `AWS_PAGER`) | `SKILL.md` §Output Formatting & Filtering + `references/jmespath.md` | impl-log S2: Body-coverage check → section present |
| Error handling and scripting (exit codes, retries, idempotency) | `SKILL.md` §Error Handling & Scripting | impl-log S2: Body-coverage check → section present |
| Security best practices (least privilege, no long-lived keys, hygiene) | `SKILL.md` §Security (`Do NOT/Never` imperatives) | impl-log S2/S3: §Security present; content-hygiene grep → 0 violations |
| Waiter usage for async operations | `SKILL.md` §Waiters + `references/waiters.md` | impl-log S3: waiters.md exit-code-255 note; Body-coverage → section present |
| Scope boundaries; no embedded account IDs/resources/regions | `SKILL.md` §Scope | impl-log S3 T14: content-hygiene grep (12-digit IDs / real regions / real ARNs) → 0 violations, placeholders only |

## Changes by Slice

### Slice 1: Author the `aws-cli` skill (SKILL.md + references)

| File | Change | Lines |
|------|--------|-------|
| `.claude/skills/aws-cli/SKILL.md` | ✨ new | +188 |
| `.claude/skills/aws-cli/references/jmespath.md` | ✨ new | +130 |
| `.claude/skills/aws-cli/references/services.md` | ✨ new | +139 |
| `.claude/skills/aws-cli/references/waiters.md` | ✨ new | +81 |

### Workflow artifacts (not part of the feature payload)

These files are QRSPI phase artifacts under `.qrspi/RUS-20/`, committed across the design/plan/implement phases. They are not skill code but appear in the diff against `main`.

| File | Change | Lines |
|------|--------|-------|
| `.qrspi/RUS-20/questions.md` | ✨ new | +47 |
| `.qrspi/RUS-20/research.md` | ✨ new | +242 |
| `.qrspi/RUS-20/design.md` | ✨ new | +97 |
| `.qrspi/RUS-20/structure.md` | ✨ new | +74 |
| `.qrspi/RUS-20/plan.md` | ✨ new | +63 |
| `.qrspi/RUS-20/worktree.md` | ✨ new | +69 |
| `.qrspi/RUS-20/impl-log.md` | ✨ new | +85 |

## Testing Summary

- [x] Slice 1: file-existence checkpoint — `SKILL.md` + 3 reference files → 4 created, 0 missing
- [x] Slice 1: Frontmatter contract (awk five-field check) — exactly 5 fields; `name==command==dir==aws-cli` → OK
- [x] Slice 1: Reference-link contract (`grep -oE 'references/[a-z-]+\.md'`) — 3/3 links resolve, 0 broken
- [x] Slice 1: Body-coverage contract — 9 required sections + all 6 services present → OK
- [x] Slice 1: Budget contract — 188 lines / ~1569 tokens (< 500 / < 5000) → OK
- [x] Slice 1: Content-hygiene contract (grep 12-digit account IDs / real regions / real ARNs) — 0 violations, placeholders only → OK
- [x] Slice 1: skill-creator invoked as in-slice validation step — structure/progressive-disclosure, frontmatter, description triggering, references all pass; no issues
- [ ] Manual verification: live `/aws-cli` auto-invocation in an interactive Claude Code session — deferred to operator post-merge (cannot be exercised by the implementation agent; ref: design Q11)

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| `SkillFrontmatter.allowed-tools` (open choice / A1, OQ1) | Unresolved value | `Read, Bash` | Read for bundled reference files, Bash to run the `aws` commands the guidance describes; minimal set matching the comma-separated `allowed-tools` precedent in `qrspi-work/SKILL.md`. Resolution of a flagged Unverified Assumption, not a deviation from a settled decision. |
| `SkillFrontmatter.argument-hint` (open choice / A2, OQ2) | Unresolved value | `[topic e.g. s3 \| ec2 \| profiles \| query]` | Optional non-positional topic hint, since the skill is general guidance, not a positional-argument command. Resolution of a flagged Unverified Assumption. |
| skill-creator gate (A3, OQ3) | Unresolved whether hard gate / hand-author fallback | skill-creator available and invoked as review against its documented criteria (not the full quantitative eval loop) | Documentation-only skill with objective link/coverage-verifiable outputs; skill-creator's own guidance says the eval loop is not required here. Fallback hand-authoring did not apply. |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| Body exceeds 500-line / 5000-token budget; nothing enforces it (Q5) | mitigated — measured 188 lines / ~1569 tokens, well under budget | Delete `.claude/skills/aws-cli/` |
| Embedded environment-specific values (account IDs, resource names, regions) slip in; no content linter (Q8) | mitigated — content-hygiene grep → 0 violations, placeholder tokens only | Delete `.claude/skills/aws-cli/` |
| skill-creator (skill builder) not in-repo; "built using skill builder" unverifiable from committed files (Q3) | accepted — recorded in this PR as the acceptance signal; skill-creator invoked at authoring time, no committed artifact | n/a (provenance is documentary) |
| No automated validation of frontmatter, length, triggering; eval harness is a stub (Q10, Q11) | partially mitigated — contracts verified manually/by grep+awk; live-trigger confirmation still pending (manual operator step) | Delete `.claude/skills/aws-cli/` |
| Multi-file `references/` dir has no exact precedent; relative-path links could be wrong | mitigated — links use `references/<topic>.md` form; 3/3 resolve | Delete `.claude/skills/aws-cli/` |

Rollback for the whole feature is a clean delete of `.claude/skills/aws-cli/` (all four files are net-new; no existing file was modified and no loader registration was added).

## Open Items

- Live `/aws-cli` auto-trigger confirmation in an interactive Claude Code session — manual operator step after merge; cannot be exercised by the implementation agent (design Q11).
- A4/OQ4 (first multi-file `references/` directory) needs reviewer sign-off — the design recommends Option A (three single-topic files) but flagged combining into one file as an open call; surfaced here for the reviewer.
- A5 (budget enforcement) is authoring discipline only — no repo tooling guards the 500-line / 5000-token budget; future tickets could add a lint check if the budget should be guaranteed rather than aspirational.
