# PR: RUS-5 — Add writing-bash-scripts knowledge skill

**Ticket:** RUS-5
**Design:** design.md @ 2026-06-03T00:00:00Z
**Structure:** structure.md @ 2026-06-06T00:00:00Z

## Summary

Adds a new self-contained `writing-bash-scripts` knowledge skill that encodes the
repo's bash conventions so an agent following it produces robust, ShellCheck-clean
scripts. The skill is a 145-line `SKILL.md` (139-line body) carrying opinionated
defaults, a code-organization ordering, and a gotchas section, with five `references/`
files holding the long-form catalog (strict mode, error handling/traps, argument
parsing, quoting/portability, testing/linting) linked by relative path to keep the body
under the 500-line limit. The `description` uses enumerated positive triggers plus an
explicit "Do NOT use…" skip clause (a NEW PATTERN for this repo) to bound a broad topic.
**Reviewer focus:** (1) the engineered `description` trigger boundary, since it is net-new
and governs auto-invocation; (2) the deferred ShellCheck-clean AC — the binary is absent
in this container, so that AC is guidance-quality only and not runnably verified here.

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: agentskills.io directory structure with valid SKILL.md frontmatter (five in-repo keys, `name: writing-bash-scripts`) | `.claude/skills/writing-bash-scripts/SKILL.md` (frontmatter) | plan step 13 inline `python3` frontmatter/key check (manual-parse fallback, `yaml` absent) → OK |
| AC2: Built using the Anthropic skill-builder/skill-creator skill | authoring process (no committed artifact) | Deviation — skill-creator unavailable in-repo; hand-authored to the verifiable five-key schema (impl-log §Deviations from plan.md) |
| AC3: SKILL.md body under 500 lines / ~5000 tokens | `.claude/skills/writing-bash-scripts/SKILL.md` (139-line body) | plan step 13 `len(body.splitlines()) < 500` + step 14 `wc -l` = 145 total → pass |
| AC4: Detailed reference material in `references/` | `.claude/skills/writing-bash-scripts/references/{strict-mode,error-handling,arguments,quoting-and-portability,testing-and-linting}.md` | plan step 13 link/orphan check — all 5 linked, no orphans, no dangling links → OK |
| AC5: Produces ShellCheck-clean output when an agent follows the guidance | `references/testing-and-linting.md` (ShellCheck-clean authoring + disable directives) | **Deferred** — ShellCheck binary absent in container (design OQ2); not runnably verified here |
| AC (trigger boundary): `description` has positive triggers + skip clause | `.claude/skills/writing-bash-scripts/SKILL.md` (frontmatter `description`) | plan step 13 positive-trigger + skip-clause assertion (case-insensitive) → pass; step 14 grep matches |
| AC (discoverability): skill auto-discovered from the filesystem | `.claude/skills/writing-bash-scripts/SKILL.md` (frontmatter `description`) | Discovery is filesystem-based via the SKILL.md `description`; no manual index needed. (The `README.md` *and* `.claude/CLAUDE.md` mirrors were both removed per reviewer feedback on PR #119 — indexing skills in docs is redundant with filesystem-based discovery.) |

## Changes by Slice

### Slice 1: Author the writing-bash-scripts skill (SKILL.md + references)

| File | Change | Lines |
|------|--------|-------|
| `.claude/skills/writing-bash-scripts/SKILL.md` | ✨ new | +145 |
| `.claude/skills/writing-bash-scripts/references/strict-mode.md` | ✨ new | +81 |
| `.claude/skills/writing-bash-scripts/references/error-handling.md` | ✨ new | +93 |
| `.claude/skills/writing-bash-scripts/references/arguments.md` | ✨ new | +84 |
| `.claude/skills/writing-bash-scripts/references/quoting-and-portability.md` | ✨ new | +118 |
| `.claude/skills/writing-bash-scripts/references/testing-and-linting.md` | ✨ new | +88 |

Total: 6 files, +609. (Both the `README.md` and `.claude/CLAUDE.md` doc mirrors were
removed per reviewer feedback on PR #119 — indexing skills in docs is redundant with
filesystem-based discovery. The `.qrspi/RUS-5/*.md` entries in `git diff main...HEAD --stat`
are QRSPI workflow artifacts — questions, research, design, structure, plan, worktree,
impl-log — produced by earlier phases, not part of this implementation slice.)

## Testing Summary

- [x] Slice 1: frontmatter + link + size validation — `python3 - <<'PY' …` (plan step 13) — OK (manual-parse fallback used; `yaml`/PyYAML absent in container)
- [x] Slice 1: checkpoint — `wc -l SKILL.md` = 145 total (139 body, < 500); skip-clause grep matches — pass. (Both the `README.md` and `.claude/CLAUDE.md` doc mirrors were removed per reviewer feedback on PR #119 — discovery is filesystem-based, no doc index needed.)
- [x] Manual verification: exactly the five keys present (`name`, `description`, `command`, `argument-hint`, `allowed-tools`), `name: writing-bash-scripts`; all 5 reference files linked, no orphans, no dangling links; description carries positive triggers + skip clause
- [ ] ShellCheck-clean sample script — **deferred**: `shellcheck` not found in container (design OQ2). Verify in CI or a provisioned environment.

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| (none) | `SkillFrontmatter` five-key schema; `ReferenceCatalog`/`ReferenceFile`; all Contracts | Frontmatter matches the five-key schema exactly; references realized as 5 files; all Contracts satisfied | Clean — no structural deviation (impl-log §Deviations from structure.md) |

Note: a deviation from **plan.md** (not structure) was recorded — authored by hand rather
than via the external `skill-creator` skill (unavailable in-repo), the explicitly-permitted
fallback. See Open Items.

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| Cannot verify against external agentskills.io standard; in-repo schema may diverge | accepted — conformed to verifiable in-repo five-key schema; OQ1 open for human confirmation | Edit/remove `SKILL.md` frontmatter |
| "ShellCheck-clean output" AC unverifiable — binary absent | discovered-confirmed — `shellcheck not found` in container; AC treated as guidance-quality, escalated as OQ2 | n/a (guidance only) |
| Broad `description` over-triggers on any shell/CLI mention | mitigated — enumerated positive triggers + explicit skip clause (Decision 3) | Edit `description` in `SKILL.md` |
| SKILL.md body exceeds 500-line limit | mitigated — body 139 lines; long-form detail pushed to `references/` | Delete `.claude/skills/writing-bash-scripts/` directory |
| Manual doc skill-list drift | eliminated — both the `README.md` and `.claude/CLAUDE.md` mirrors were dropped per reviewer feedback (redundant); discovery is filesystem-based | n/a (no doc index to drift) |
| skill-creator external/unavailable in-repo | accepted — confirmed unavailable; hand-authored to in-repo schema, deviation noted | n/a |

**Overall rollback:** purely additive. Delete `.claude/skills/writing-bash-scripts/`;
discovery is filesystem-based (no registry/manifest, no doc index), so nothing else
depends on it. No DB migrations, config, or destructive operations.

## Open Items

- **ShellCheck-clean AC (OQ2) deferred:** `shellcheck` is absent in this container; the
  "ShellCheck-clean output" AC was not runnably verified. Follow-up: run ShellCheck on a
  sample script in CI or a provisioned environment, or provision the binary
  (Dockerfile/post-create) — a human scope call.
- **skill-creator authoring deviation:** the skill was hand-authored to the in-repo five-key
  schema rather than via the external `skill-creator` eval loop (not committed in-repo). If
  skill-creator validation is required, re-run it from a session where the global skill is
  reachable.
- **OQ1 (agentskills.io standard):** the external frontmatter standard could not be fetched;
  the in-repo five-key schema is treated as compatible. Confirm no additional agentskills.io
  fields are required.
- **OQ3 (`command`/`argument-hint` for an auto-invoked knowledge skill):** both keys are
  included per the in-repo schema; confirm whether a nominal `/writing-bash-scripts` slash
  command should exist.
- **`yaml`/PyYAML absent:** future frontmatter validation in this container must use the
  manual-parse fallback.
