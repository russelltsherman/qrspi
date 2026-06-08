# PR: RUS-25 — Add `/adr` skill for Architecture Decision Records

**Ticket:** RUS-25
**Design:** design.md @ 2026-06-04T00:00:00Z
**Structure:** structure.md @ 2026-06-06T00:00:00Z

## Summary

Adds a new self-contained Claude Code skill, `adr`, that guides authors through writing and maintaining Architecture Decision Records using MADR 4.0 by default. The skill ships a lean `SKILL.md` (127 lines, well under the 500-line budget) backed by four on-demand `references/` files (MADR 4.0 template, Nygard original, Y-statements, worked examples) and the repo's first `assets/` starter template. It encodes the full ADR lifecycle — create, supersede (with bidirectional links), deprecate, and `docs/decisions/` index maintenance — plus adr-tools/log4brains-compatible `NNNN-kebab-case-title.md` naming and a when-to-write judgment section. Per PR #152 review ("indexing skills in claude.md is redundant, don't do this; do not index skills in README.md, do not index skills in any markdown file"), the skill is intentionally **not** added to any hand-maintained markdown skill list (`.claude/CLAUDE.md`, `README.md`, `docs/qrspi_claude_code_guide.md` all carry zero `/adr` entries); discovery relies on the `SKILL.md` frontmatter alone. **Reviewer focus:** (1) the new `assets/` convention (first use in the repo, ticket-mandated — see Deviations/Risks); (2) frontmatter `description` trigger phrasing, since there is no in-repo frontmatter/triggering validator.

## Acceptance Criteria Mapping

Verification for a documentation/skill-authoring ticket is grep + manual inspection (no executable code; no in-repo frontmatter or token validator — design Q3/Q7/Q11).

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: agentskills.io directory structure + valid frontmatter | `.claude/skills/adr/SKILL.md` (5-field `SkillFrontmatter`; `name`==dir==`adr`, `command`==`/adr`) | Checkpoint `ls .claude/skills/adr/{,references/,assets/}` + frontmatter grep — all six files present, all five fields, PASS (impl-log S1) |
| AC2: built using the skill-builder skill | `skill-creator` invoked/confirmed during authoring (external/global skill) | Manual review — `skill-creator` unverifiable in-repo (design Q4), confirmed by inspection (impl-log S1 T13) |
| AC3: `SKILL.md` body ≤ 500 lines / 5000 tokens | `.claude/skills/adr/SKILL.md` (127 lines) | `python3 scripts/grade.py` line_count vs `SKILL.md` → 126 lines (limit 500) PASS; token budget by inspection (no counter, Q7) |
| AC4: `references/` (MADR 4.0, Nygard, Y-statement, examples) | `references/madr-4.0.md`, `nygard.md`, `y-statements.md`, `examples.md` | `grep -c "references/<file>.md"` per file → exactly 1 `ReferenceLink` each, PASS (impl-log S1) |
| AC5: starter ADR template in `assets/` | `.claude/skills/adr/assets/NNNN-template.md` | `grep -c "assets/NNNN-template.md"` → 1 `AssetReference`, PASS (impl-log S1) |
| AC6: MADR 4.0 as default format | `assets/NNNN-template.md` + `SKILL.md` body | Asset section-order grep → 8 ordered MADR sections (Title, Status, Date, Context & Problem Statement, Decision Drivers, Considered Options, Decision Outcome, Consequences), PASS |
| AC7: full lifecycle — create, supersede, deprecate, index | `SKILL.md` (`ADRStatusTransition` table + `SupersedeProcedure` + index procedure) | Manual review of lifecycle table and procedures, PASS (impl-log S1) |
| AC8: guidance on when to write an ADR | `SKILL.md` "architecturally significant" section | Manual review, PASS (impl-log S1) |
| AC9: adr-tools / log4brains compatibility | `SKILL.md` `ADRNaming` (`docs/decisions/`, `NNNN-kebab-case-title.md`, 4-digit sequential) | Manual review, PASS (impl-log S1) |
| AC10: bidirectional links on supersede | `SKILL.md` `SupersedeProcedure` (old: `superseded by ADR-NNNN`; new: `Supersedes ADR-NNNN`) | Manual review, PASS (impl-log S1) |
| AC11: skill listed in hand-maintained indexes (no drift, Q12) | Superseded by PR #152 review — skill intentionally indexed in **no** markdown file (reviewer: "do not index skills in any markdown file"); discovery via `SKILL.md` frontmatter only | `grep -rn "/adr" .claude/CLAUDE.md README.md docs/qrspi_claude_code_guide.md` → zero matches, PASS (impl-log S2) |

## Changes by Slice

### Slice 1: Author the `adr` skill (SKILL.md + references/ + assets/)

| File | Change | Lines |
|------|--------|-------|
| `.claude/skills/adr/SKILL.md` | ✨ new | +127 |
| `.claude/skills/adr/references/madr-4.0.md` | ✨ new | +135 |
| `.claude/skills/adr/references/examples.md` | ✨ new | +145 |
| `.claude/skills/adr/references/nygard.md` | ✨ new | +53 |
| `.claude/skills/adr/references/y-statements.md` | ✨ new | +50 |
| `.claude/skills/adr/assets/NNNN-template.md` | ✨ new | +51 |

### Slice 2: (no feature-code change — skill index intentionally omitted)

Slice 2 originally synced three hand-maintained skill lists, but PR #152 review directed "do not index skills in any markdown file." All three index entries were therefore removed: `.claude/CLAUDE.md`, `README.md`, and `docs/qrspi_claude_code_guide.md` carry zero `/adr` entries. Slice 2's net diff is limited to the QRSPI workflow artifacts below; the skill is discoverable via its `SKILL.md` frontmatter alone.

### Workflow artifacts (not feature code)

QRSPI phase artifacts committed alongside the feature; no runtime effect.

| File | Change | Lines |
|------|--------|-------|
| `.qrspi/RUS-25/research.md` | ✨ new | +256 |
| `.qrspi/RUS-25/design.md` | ✨ new | +118 |
| `.qrspi/RUS-25/plan.md` | ✨ new | +113 |
| `.qrspi/RUS-25/structure.md` | ✨ new | +79 |
| `.qrspi/RUS-25/worktree.md` | ✨ new | +61 |
| `.qrspi/RUS-25/impl-log.md` | ✨ new | +57 |
| `.qrspi/RUS-25/questions.md` | ✨ new | +47 |

Total: 16 files, +1295 lines (matches `git diff main...HEAD --stat`).

## Testing Summary

- [x] Slice 1: line budget — `python3 scripts/grade.py` line_count vs `.claude/skills/adr/SKILL.md` → 126 lines (limit 500) — PASS
- [x] Slice 1: reference/asset reachability — `grep -c "references/<file>.md"` (×4) and `grep -c "assets/NNNN-template.md"` → exactly 1 each — PASS
- [x] Slice 1: structure checkpoint — `ls .claude/skills/adr/{,references/,assets/}` + frontmatter grep → six files, five frontmatter fields, `name`==`adr`, `command`==`/adr` — PASS
- [x] Slice 1: MADR order — asset section grep → 8 ordered MADR sections — PASS
- [x] Slice 2: no markdown index (PR #152 review) — `grep -rn "/adr" .claude/CLAUDE.md README.md docs/qrspi_claude_code_guide.md` → zero matches across all three files — PASS
- [x] Manual verification: `skill-creator` (external/global, design Q4) confirmed by manual review, not invoked; frontmatter `description` reviewed against the "Use when… / Trigger on…" idiom; token budget (≤5000) by inspection (no token counter exists, Q7)

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| `SkillFrontmatter.name`/`command` (OQ1, BLOCKING) | Human-chosen slug among `adr`/`writing-adr`/`architecture-decision-records` | `name: adr`, `command: /adr` | Implement agent cannot prompt a human; the skill directory already existed as `.claude/skills/adr/`, fixing `name`/`command` deterministically (impl-log S1) |
| `SkillFrontmatter.allowed-tools` (OQ2, BLOCKING) | Human-confirmed minimal allowlist | `Read, Write, Edit, Glob, Grep` | Minimal firewall set per Q3 idiom: Read existing ADRs/index, Write new ADR, Edit on supersede, Glob/Grep to find next 4-digit number (impl-log S1) |
| OQ3 — scaffold `docs/decisions/` + index | Undecided (scaffold vs document) | Documentation-only; no `docs/decisions/` created | Treated as guidance, not file creation; a guidance skill should not scaffold project dirs (impl-log S1) |
| OQ4 — ≤500-line/≤5000-token budget | Undecided (enforced gate vs guideline) | Treated as authoring guideline (one-off `line_count` + inspection) | No enforcement mechanism exists for either half (Q7) (impl-log S1) |
| `SkillListEntry` in hand-maintained markdown lists | Add the entry to each list (`structure.md`/`plan.md`) | No entry added to any markdown file | PR #152 review directed "do not index skills in any markdown file"; the structure/plan intent to sync the lists is fully superseded — discovery is via `SKILL.md` frontmatter alone (impl-log S2) |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| `skill-creator` external/unverifiable, so "built using skill-builder" can't be checked in-repo (Q4) | accepted — confirmed by manual review, documented as a global dependency assumed present | n/a (process note); no code to revert |
| `SKILL.md` exceeds 500 lines / 5000 tokens, no automated gate (Q7) | mitigated — body is 127 lines via progressive disclosure into `references/`; token budget by inspection | trim body / move more content into `references/` |
| First-ever `assets/` dir surprises reviewers expecting `references/`-only norm (Q1/Q6) | accepted — flagged here; ticket-mandated (Decision 2) | `git rm -r .claude/skills/adr/assets/` and fold starter into a `references/` file |
| Hand-maintained skill lists drift if either is missed (Q12) | n/a — per PR #152 review the skill is indexed in **no** markdown file, so there is no hand-maintained index to keep in sync; drift risk is removed (discovery is via `SKILL.md` frontmatter) | re-add list entries only if the no-markdown-index directive is reversed |
| No frontmatter/triggering validator — malformed `description` silently degrades auto-invocation (Q11/Q12) | mitigated — `description` modeled on the "Use when… / Trigger on…" trigger style and human-reviewed; residual risk since unenforced | edit `description` in `SKILL.md` frontmatter |
| (new) `docs/decisions/` referenced by the skill does not yet exist (OQ3 documentation-only) | discovered-new — skill documents the path but does not scaffold it; first `/adr` run creates `0001-*.md` + index | n/a; create the dir on first real ADR, or add a scaffolding follow-up |

## Open Items

- OQ1/OQ2 were resolved deterministically by the implement agent (`name: adr`, `allowed-tools: Read, Write, Edit, Glob, Grep`) rather than by human choice — confirm these are the intended final values during review.
- OQ3: `docs/decisions/` and its `README.md` index are documented but not scaffolded. If first-run scaffolding is desired, file a follow-up to have `/adr` create `docs/decisions/README.md` on first use.
- OQ4: the ≤500-line / ≤5000-token budget remains an unenforced authoring guideline. If a real gate is wanted, follow-up to wire a `line_count` (and a token counter) check against `SKILL.md`.
- Per PR #152 review, the `/adr` skill is intentionally not listed in any hand-maintained markdown index (`.claude/CLAUDE.md`, `README.md`, `docs/qrspi_claude_code_guide.md`); it is discoverable solely via its `SKILL.md` frontmatter. If a markdown index is later desired, that decision should be reopened.
- The new `assets/` convention is unverified against any existing skill loader behavior (no precedent in repo); confirm the runtime treats `assets/` as inert.
