# Implementation Plan — Create a new agent skill using obsidian cli

**Structure basis:** structure.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total steps:** 18

> Note: This ticket produces a prose/documentation skill, not executable code. "Tests"
> below are mechanical validation steps (YAML frontmatter parse, reference-link
> resolution, command/property coverage counts) plus the human-review gate — there is no
> functional eval (structure.md, design.md §Risk Register, ref Q10). Per AC #2 the skill
> is authored via the global skill-creator skill (Step 1); the steps below enumerate the
> concrete files and contracts that authoring must satisfy.

## Slice 1: Author the `obsidian` skill (body + references + list update)

### Setup

1. ✨ Invoke the global `skill-creator` skill to scaffold the `obsidian` skill (AC #2, OQ3, design.md §Risk Register). Build-time action; produces the directory skeleton `.claude/skills/obsidian/` that the following steps populate. Compliance is not verifiable from repo artifacts — record that the skill was created via skill-creator.

2. ✨ Create `.claude/skills/obsidian/SKILL.md` with the five-key YAML frontmatter only (body added in later steps) — `SkillFrontmatter { name: obsidian, description, command: /obsidian, argument-hint, allowed-tools }`, keys in fixed order `name`, `description`, `command`, `argument-hint`, `allowed-tools` (structure.md `SkillFrontmatter`, frontmatter-name-invariant). `name: obsidian` == directory basename == `command` minus the leading `/`. `description` is a capability statement + explicit "Use when…" trigger clause naming Obsidian/vault/note nouns (design.md ref Q11).

### Core Logic

3. ⚠️ Modify `.claude/skills/obsidian/SKILL.md` — add capability/trigger description and vault-structure conventions section to the body.
   - **Current:** frontmatter only (from Step 2).
   - **After:** frontmatter + opening capability paragraph + `## Vault structure` conventions section.

4. ⚠️ Modify `.claude/skills/obsidian/SKILL.md` — add a `## Note CRUD` overview section citing the CLI reference by relative path `(see references/cli-reference.md)` (reference-link-contract). Overview only; per-command detail lives in the reference file.
   - **Current:** body has description + vault structure.
   - **After:** adds note-CRUD overview section with relative-path pointer.

5. ⚠️ Modify `.claude/skills/obsidian/SKILL.md` — add a `## Frontmatter / properties` section documenting all seven supported types (Text, Number, Checkbox, Date, Date & Time, List, Links) with one example each (property-coverage-contract, design.md §Desired End State).
   - **Current:** body through note-CRUD overview.
   - **After:** adds properties section covering all 7 types.

6. ⚠️ Modify `.claude/skills/obsidian/SKILL.md` — add a `## Linking` section: `[[wikilink]]`, `[[Note#Heading]]`, `[[Note#^block-id]]`, pipe-display, and when to use standard markdown links (design.md §Desired End State).
   - **Current:** body through properties.
   - **After:** adds linking-best-practices section.

7. ⚠️ Modify `.claude/skills/obsidian/SKILL.md` — add a `## Tags` section documenting tag conventions.
   - **Current:** body through linking.
   - **After:** adds tags section.

8. ⚠️ Modify `.claude/skills/obsidian/SKILL.md` — add the `## CLI vs URI vs filesystem` section: a decision table plus imperative "prefer X / do NOT Y because <consequence>" prose, each with a stated reason (tool-preference-contract, Decision 4 Option A, ref Q8). Cite `(see references/uri-protocol.md)`.
   - **Current:** body through tags.
   - **After:** adds tool-preference decision table + prefer/forbid prose.

9. ⚠️ Modify `.claude/skills/obsidian/SKILL.md` — add an `## Idempotency` guidance section.
   - **Current:** body through tool-preference.
   - **After:** adds idempotency guidance.

10. ⚠️ Modify `.claude/skills/obsidian/SKILL.md` — add a `## Plugin conventions` section documenting Dataview/Templater/Tasks data formats (no installation), citing `(see references/dataview.md)` for DQL detail (design.md §Desired End State, reference-link-contract).
    - **Current:** body through idempotency.
    - **After:** adds plugin-conventions section with relative-path pointer.

11. ⚠️ Modify `.claude/skills/obsidian/SKILL.md` — add the `## Error handling` section in the `qrspi-work` `condition → STOP/action` style covering Obsidian-not-running, malformed YAML, and link collisions (error-handling-contract, ref Q7).
    - **Current:** body through plugin conventions.
    - **After:** adds error-handling section; body content complete.

12. ✨ Create `.claude/skills/obsidian/references/cli-reference.md` — prose+tables, no frontmatter (`ReferenceFile`); enumerate all 13 commands (create, read, append, prepend, move, delete, search, daily, properties, tags, links, files, templates) each with parameters and quoting/encoding notes; mark examples as CLI v1.12.4 (cli-coverage-contract, design.md §Desired End State, OQ4).

13. ✨ Create `.claude/skills/obsidian/references/uri-protocol.md` — prose+tables, no frontmatter (`ReferenceFile`); `obsidian://` actions and URI encoding.

14. ✨ Create `.claude/skills/obsidian/references/dataview.md` — prose+tables, no frontmatter (`ReferenceFile`); DQL + inline-field syntax.

15. ⚠️ Modify `.claude/CLAUDE.md` — add one bullet to the "Available skills" prose list for the new `obsidian` skill (`AvailableSkillsList`, design.md §Delta, ref Q5; non-load-bearing).
    - **Current:** "Available skills" list ends with `/qrspi-pr <ticket-id> — Prepare pull request summary`.
    - **After:** same list plus a bullet `obsidian — <capability> Use when working with an Obsidian vault via the obsidian CLI`.

### Tests

16. Run: `python3 -c "import yaml,sys; d=yaml.safe_load(open('.claude/skills/obsidian/SKILL.md').read().split('---')[1]); assert list(d)==['name','description','command','argument-hint','allowed-tools']; assert d['name']=='obsidian' and d['command']=='/obsidian'"`
    - **Expected:** exits 0 — frontmatter parses, exactly the five keys in order, name/command invariant holds (frontmatter-name-invariant). (If PyYAML is unavailable, parse the frontmatter block manually and assert the same.)

17. Run: `for f in $(grep -oE 'references/[a-z-]+\.md' .claude/skills/obsidian/SKILL.md | sort -u); do test -f ".claude/skills/obsidian/$f" || echo "MISSING $f"; done`
    - **Expected:** no `MISSING` lines — every `(see references/<file>.md)` link resolves (reference-link-contract).

### Verify Slice 1

18. **Checkpoint:** `bash -c 'grep -c . .claude/skills/obsidian/SKILL.md; for c in create read append prepend move delete search daily properties tags links files templates; do grep -qiw "$c" .claude/skills/obsidian/references/cli-reference.md || echo "CLI MISSING $c"; done'`
    - [ ] SKILL.md frontmatter is valid YAML with exactly the five keys in order; `name: obsidian`, `command: /obsidian`, directory basename == `obsidian` (Step 16).
    - [ ] Every `(see references/<file>.md)` link in the body resolves (Step 17).
    - [ ] CLI reference contains all 13 named commands (no `CLI MISSING` lines); properties section covers all 7 types (cli/property coverage contracts).
    - [ ] Body line count checked against the < 500 line / < 5000 token budget; overflow detail confirmed to live in `references/` (body-budget-contract; manual count, unenforced).
    - [ ] Skill was built via the global skill-creator skill (Step 1; AC #2 / OQ3 — not provable from artifacts).
    - [ ] Human review of `SKILL.md` prose — the in-repo gate (ref Q10); no functional eval exists.

---

## Rollback Notes

- No DB migrations, config changes, or destructive operations. All changes are additive new files plus one additive bullet in `.claude/CLAUDE.md`.
- Step 15: to reverse, remove the single `obsidian` bullet from the "Available skills" list in `.claude/CLAUDE.md`.
- Steps 2–14: to reverse, delete the `.claude/skills/obsidian/` directory (auto-discovery means removing the directory fully removes the skill; no manifest/registry edit needed, design.md ref Q5).

## Open items carried from structure.md (resolve before/during implementation)

- **OQ1 / frontmatter shape:** plan assumes the in-repo five-key contract (Decision 3 Option A). If the human mandates the agentskills.io two-key standard, Step 2 and the Step 16 assertion change.
- **OQ2 / skill name:** plan assumes bare `obsidian`. A `qrspi-` prefix would rewrite every path and the `command`/name-invariant assertions.
- **Reference granularity:** Steps 12–14 assume three reference files; they may collapse to one `references/*.md` if the body budget allows, without changing the linking contract (Step 17 still passes).
