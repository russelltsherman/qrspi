# PR: RUS-17 Add auto-discoverable `obsidian` agent skill

**Ticket:** RUS-17
**Design:** design.md @ 2026-06-04T00:00:00Z
**Structure:** structure.md @ 2026-06-06T00:00:00Z

## Summary

Adds a new `obsidian` agent skill that teaches the harness to operate an Obsidian vault (note CRUD, frontmatter properties, wikilinks, tags, daily notes, and Dataview/Templater/Tasks data) via the obsidian CLI, `obsidian://` URIs, or the filesystem. The skill ships as `.claude/skills/obsidian/SKILL.md` with the repo-standard five-key frontmatter and a body kept under budget by factoring detailed CLI, URI, and Dataview material into three `references/` files. It is the first non-`qrspi-`-prefixed skill in the repo (Decision 1), reflecting that it is a capability skill, not a QRSPI phase. Reviewers should focus on (a) the SKILL.md prose itself — there is no functional eval, human review is the only gate (ref Q10) — and (b) whether the in-repo five-key frontmatter (Decision 3 / OQ1) and the bare `obsidian` name (Decision 1 / OQ2) are the intended resolutions of the two open questions. Note the Obsidian CLI command semantics are documented authoritative-by-ticket (CLI v1.12.4), not validated against a running binary (OQ4).

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: agentskills.io directory structure + valid SKILL.md frontmatter | `.claude/skills/obsidian/SKILL.md` (five-key frontmatter), `references/` layout | Frontmatter parse (manual fallback) — 5 keys in fixed order, `name: obsidian`, `command: /obsidian` (Session 2 T16, PASS) |
| AC2: Built using the Anthropic skill-builder skill | Global `skill-creator` skill invoked at build time (Session 1 T1) | Build-time action, unverifiable from artifacts (OQ3) — no machine test |
| AC3: Body under 500 lines / 5000 tokens | `SKILL.md` body with detail pushed to `references/` | Checkpoint: 233 lines / 190 non-blank, ~3629 tokens (Session 2 T18, PASS) |
| AC4: Detailed reference material in references/ (CLI, URI, Dataview) | `references/cli-reference.md`, `references/uri-protocol.md`, `references/dataview.md` | Reference-link resolution `grep -oE 'references/[a-z-]+\.md'` — all 3 resolve, no MISSING (Session 2 T17, PASS) |
| AC5: Covers all official CLI commands (13 named) | `references/cli-reference.md` | Checkpoint: all 13 CLI commands present, no `CLI MISSING` (Session 2 T18, PASS) |
| AC6: Frontmatter property conventions for all seven types | `SKILL.md` properties section | Property-type grep — all 7 types present (Text, Number, Checkbox, Date, Date & Time, List, Links) (Session 1, PASS) |
| AC7: Linking best practices (wikilinks vs markdown, headings, block refs) | `SKILL.md` linking section | Human review of prose (no functional eval, ref Q10) |
| AC8: Plugin-aware patterns (Dataview, Templater, Tasks) without installation | `SKILL.md` plugin-conventions section + `references/dataview.md` | Human review of prose (no functional eval, ref Q10) |
| AC9: CLI vs URI vs filesystem guidance | `SKILL.md` decision table + prefer/forbid prose | Human review of prose (no functional eval, ref Q10) |
| AC10: Error handling (Obsidian not running, malformed YAML, link collisions) | `SKILL.md` error-handling section | Human review of prose (no functional eval, ref Q10) |

## Changes by Slice

### Slice 1: Author the `obsidian` skill (body + references)

| File | Change | Lines |
|------|--------|-------|
| `.claude/skills/obsidian/SKILL.md` | ✨ new | +233 |
| `.claude/skills/obsidian/references/cli-reference.md` | ✨ new | +228 |
| `.claude/skills/obsidian/references/dataview.md` | ✨ new | +129 |
| `.claude/skills/obsidian/references/uri-protocol.md` | ✨ new | +82 |

> The skill is auto-discoverable via its SKILL.md frontmatter; per reviewer feedback it is **not** indexed in `.claude/CLAUDE.md` (or any markdown file) — that index entry was removed as redundant.

> Workflow bookkeeping also committed on the branch (not feature code): `.qrspi/RUS-17/{design,plan,research,structure,questions,worktree,impl-log}.md` (+844). These are QRSPI phase artifacts, not part of the shipped skill.

## Testing Summary

- [x] Slice 1: frontmatter parse (manual YAML fallback) — 5 keys in fixed order, `name: obsidian`, `command: /obsidian` — PASS (T16)
- [x] Slice 1: reference-link resolution — `grep -oE 'references/[a-z-]+\.md' SKILL.md` — all 3 (cli-reference, uri-protocol, dataview) resolve, no MISSING — PASS (T17)
- [x] Slice 1: coverage checkpoint — 233 lines / 190 non-blank / ~3629 tokens (under 500-line / 5000-token budget); all 13 CLI commands present; 7 property types covered — PASS (T18)
- [ ] Manual verification: human review of SKILL.md prose (the in-repo gate, ref Q10) — pending reviewer; no functional eval exists
- [ ] Manual verification: skill-creator-build compliance (AC2 / OQ3) — build-time action, unprovable from artifacts

> PyYAML is unavailable in this environment, so the plan-sanctioned manual frontmatter-parse fallback was used in place of `import yaml` — same assertions, same result.

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| (none) | | | impl-log Sessions 1 & 2 report zero deviations from structure.md |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| agentskills.io standard conflicts with in-repo five-key frontmatter (AC1) | accepted — shipped in-repo five-key (Decision 3 Option A); OQ1 still open for reviewer | Revert SKILL.md frontmatter to two-key if reviewer mandates external standard |
| AC2 "built using skill-builder" unverifiable from artifacts | accepted — skill-creator invoked at build time; compliance unprovable (OQ3) | N/A — build-time process note only |
| Body exceeds 500 lines / 5000 tokens | mitigated — 233 lines / ~3629 tokens; detail factored into `references/` | Move additional body content into `references/` |
| Obsidian CLI behavior documented only from ticket, not a running binary | accepted — authoritative-by-ticket (CLI v1.12.4), noted in cli-reference.md (OQ4) | Correct command reference once validated against a live CLI |
| No functional eval to validate the prose skill | accepted — human review is the gate (ref Q10); frontmatter validity is mechanically checked | Reviewer rejects via CHANGES_REQUESTED; revise in place |
| First non-`qrspi-` skill name sets new convention | accepted — bare `obsidian` per Decision 1; OQ2 open for reviewer | Rename dir/`name`/`command` to `qrspi-obsidian` if prefix required |

## Open Items

- OQ1 (Decision 3): confirm in-repo five-key frontmatter is acceptable for AC1 vs the agentskills.io two-key standard — reviewer decision.
- OQ2 (Decision 1): confirm bare `obsidian` name vs a `qrspi-` prefix — reviewer decision; renaming touches every skill path.
- OQ3 (AC2): skill-creator-build compliance is a build-time action that cannot be verified from repo artifacts.
- OQ4: Obsidian CLI command semantics are authoritative-by-ticket (CLI v1.12.4), not validated against a running binary.
- No functional eval exists for prose skills; human review of SKILL.md is the only gate (ref Q10).
