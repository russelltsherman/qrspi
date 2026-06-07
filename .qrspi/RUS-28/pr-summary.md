# PR: Add writing-gitlab-pipelines agent skill

**Ticket:** RUS-28
**Design:** design.md @ 2026-06-04T00:00:00Z
**Structure:** structure.md @ 2026-06-06T00:00:00Z

## Summary

Adds a new self-contained agent skill at `.claude/skills/writing-gitlab-pipelines/`
that guides agents authoring `.gitlab-ci.yml` pipelines. The skill mirrors the
in-repo `qrspi-ticket` shape (a single `SKILL.md`, no `.claude/agents/` companion):
the body is a concise navigational index with inline opinionated/performance/
anti-pattern guidance, and depth lives in six standalone `references/*.md` deep-dive
docs (rules, includes/extends, cache/artifacts, environments, security, architecture).
No executable code, Python, or eval-suite changes are involved — this is a
Markdown-authoring deliverable. **Reviewer focus:** (1) frontmatter shape — flat
`allowed-tools`, `name` equals the directory, no nested `claude.tools`; (2) the
auto-trigger-only decision (no `command` field) and the `Read, Write, Edit, Bash`
tool set, both still at author-default pending OQ1/OQ3; (3) coverage and version-gate
notes in the reference docs.

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: agentskills.io directory structure + valid frontmatter | `.claude/skills/writing-gitlab-pipelines/SKILL.md` (frontmatter) | Slice 1: frontmatter parse + assertions (`name == writing-gitlab-pipelines`, no nested `claude`, flat `allowed-tools`, no `command`/`argument-hint`) → PASS |
| AC2: Built using the Anthropic skill builder (`skill-creator`) | n/a — `skill-creator` is environment-only, not in-repo (design Risk; OQ2) | Not file-mappable; structure conforms regardless of scaffolding tool — see Open Items |
| AC3: SKILL.md body under 500 lines / 5000 tokens | `.claude/skills/writing-gitlab-pipelines/SKILL.md` | Slice 1: `wc -l SKILL.md` → 83 lines (≤ 500); ~4950 chars ≈ 1240 tokens (≤ ~5000) → PASS |
| AC4: Detailed reference material in `references/` | `.claude/skills/writing-gitlab-pipelines/references/*.md` (6 files) | Slice 2: standalone-H1 + non-stub check (`head -1 | grep '^# '`, `wc -l > 5`) → 6/6 PASS (104–215 lines each) |
| AC5: Covers all major pipeline concerns | `SKILL.md` body index + 6 reference docs | Slice 2: cross-check every design §Desired End State concern → non-stub reference → PASS |
| AC6: Encodes opinionated best practices | `SKILL.md` `## Opinionated defaults` section | Slice 1: four inline body sections present (4/4) → PASS |
| AC7: Performance targets + optimization | `SKILL.md` `## Performance & optimization` section | Slice 1: inline-section presence check → PASS |
| AC8: Anti-patterns with alternatives | `SKILL.md` `## Anti-patterns → alternatives` section | Slice 1: inline-section presence check → PASS |

## Changes by Slice

### Slice 1: SKILL.md skeleton — frontmatter, body index, opinionated body sections

| File | Change | Lines |
|------|--------|-------|
| `.claude/skills/writing-gitlab-pipelines/SKILL.md` | ✨ new | +83 |
| `.claude/skills/writing-gitlab-pipelines/references/rules.md` | ✨ new (stub) | +3 |
| `.claude/skills/writing-gitlab-pipelines/references/includes-extends.md` | ✨ new (stub) | +3 |
| `.claude/skills/writing-gitlab-pipelines/references/cache-artifacts.md` | ✨ new (stub) | +3 |
| `.claude/skills/writing-gitlab-pipelines/references/environments.md` | ✨ new (stub) | +3 |
| `.claude/skills/writing-gitlab-pipelines/references/security.md` | ✨ new (stub) | +3 |
| `.claude/skills/writing-gitlab-pipelines/references/architecture.md` | ✨ new (stub) | +3 |

### Slice 2: Reference content — fill the six deep-dive docs

| File | Change | Lines |
|------|--------|-------|
| `.claude/skills/writing-gitlab-pipelines/references/architecture.md` | ⚠️ modified | +214, -1 |
| `.claude/skills/writing-gitlab-pipelines/references/includes-extends.md` | ⚠️ modified | +149, -1 |
| `.claude/skills/writing-gitlab-pipelines/references/cache-artifacts.md` | ⚠️ modified | +126, -1 |
| `.claude/skills/writing-gitlab-pipelines/references/environments.md` | ⚠️ modified | +113, -1 |
| `.claude/skills/writing-gitlab-pipelines/references/rules.md` | ⚠️ modified | +110, -1 |
| `.claude/skills/writing-gitlab-pipelines/references/security.md` | ⚠️ modified | +103, -1 |

### Workflow artifacts (not part of the shipped skill)

| File | Change | Lines |
|------|--------|-------|
| `.qrspi/RUS-28/questions.md` | ✨ new | +53 |
| `.qrspi/RUS-28/research.md` | ✨ new | +285 |
| `.qrspi/RUS-28/design.md` | ✨ new | +110 |
| `.qrspi/RUS-28/structure.md` | ✨ new | +108 |
| `.qrspi/RUS-28/plan.md` | ✨ new | +87 |
| `.qrspi/RUS-28/worktree.md` | ✨ new | +51 |
| `.qrspi/RUS-28/impl-log.md` | ✨ new | +59 |

## Testing Summary

- [x] Slice 1: frontmatter shape — stdlib parse + assertions (name=dir, no nested `claude`, flat `allowed-tools`, no `command`/`argument-hint`) — PASS
- [x] Slice 1: body budget — `wc -l SKILL.md` → 83 lines (≤ 500); ~1240 tokens (≤ ~5000) — PASS
- [x] Slice 1: reference-link contract — all 6 `references/<file>.md` body links resolve — 6/6 PASS
- [x] Slice 1: inline body sections present (Purpose/when-to-use, Opinionated defaults, Performance & optimization, Anti-patterns → alternatives) — 4/4 PASS
- [x] Slice 2: standalone-H1 + non-stub check across all six refs (111/150/127/114/104/215 lines) — 6/6 PASS
- [x] Slice 2: link re-run + budget unchanged (83 lines) — PASS
- [x] Slice 2: concern-coverage cross-check (every design §Desired End State concern → non-stub reference) — PASS
- [x] Slice 2: version gates present inline (CI/CD Catalog + `component:` GA 17.0 in includes-extends.md; scanner tier/version in security.md) — PASS
- [x] Manual verification: no automated eval/validation harness applies to skill authoring (PyYAML absent, eval harness is a placeholder); verification is grep/wc + manual cross-check only

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| (none) | structure.md slices/contracts | Implemented as specified | impl-log records zero deviations from structure.md for both slices |

> Note: one deviation from **plan.md** (not structure.md): plan step 13's PyYAML-based
> frontmatter verification was replaced by a stdlib-only equivalent asserting the same
> intent — PyYAML is not installed in this environment (`ModuleNotFoundError: No module
> named 'yaml'`). No artifact change; same assertions verified.

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| Body exceeds 500 lines / 5000 tokens — no tooling enforces it | mitigated — index-in-body kept SKILL.md at 83 lines / ~1240 tokens; depth pushed to references | Trim `SKILL.md` body or move content into `references/` |
| Wrong frontmatter shape — flat `allowed-tools` confused with nested `claude.tools` | mitigated — verified flat `allowed-tools`, no nested `claude`, no agent file created | Correct frontmatter in `SKILL.md` |
| GitLab feature drift — version-gated features become stale | accepted — handled via inline version notes (CI/CD Catalog/`component:` GA 17.0; scanner tiers), principle-based not release-pinned | Update inline version notes in `includes-extends.md` / `security.md` |
| `skill-creator` is environment-only — "built using skill builder" can't be verified from repo | accepted — treated as a human/process step (OQ2); structure conforms regardless of scaffolding tool | n/a — provenance is process, not artifact |
| No eval/validation harness applies to skill authoring | accepted — relied on manual review + grep/wc checks; no automated coverage promised | n/a |

Rollback for the whole change: delete `.claude/skills/writing-gitlab-pipelines/`
(net-new directory; no existing file or type is modified per design §Delta).

## Open Items

- **OQ1 / Decision 2 (`command` field):** SKILL.md is auto-trigger-only (no `command`), the design default. Flag for author if an explicit `/writing-gitlab-pipelines` slash invocation is wanted — diverges from the 10 in-repo skills that all carry `command`.
- **OQ3 / Decision 3 (`allowed-tools`):** Left at the narrow default `Read, Write, Edit, Bash` (includes `Bash` for local `.gitlab-ci.yml` lint). Author should confirm or narrow to read/edit-only.
- **OQ2 (skill-creator provenance):** The ticket's "built using the Anthropic skill builder" criterion cannot be satisfied or verified from repo files — `skill-creator` is environment-only. Recorded as a process step; AC2 is not file-mappable.
- **OQ4 (GitLab target version):** Handled, not formally answered — version-gated features carry inline notes rather than a single pinned target. If the author wants one pinned version, add it to SKILL.md.
- **Services section:** The shipped SKILL.md folds service usage into the DAG/architecture guidance rather than a dedicated section (design §Desired End State mentions a standalone "Services" treatment). Flag for author if a dedicated section is wanted.
- **No automated coverage:** Verification is grep/wc + manual cross-check only; no eval harness applies. Future tooling to lint SKILL.md frontmatter/budget would close the gap.
