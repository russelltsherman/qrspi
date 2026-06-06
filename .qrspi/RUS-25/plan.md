# Implementation Plan — Create a new agent skill for writing Architecture Decision Records

**Structure basis:** structure.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total steps:** 23

> Parameterization: `<name>` is the unresolved skill slug (structure OQ1 — BLOCKING:
> `adr` / `writing-adr` / `architecture-decision-records`). Every path below is templated
> on it; `name` == directory == `command` stem (design Q3). `<name>` and the `allowed-tools`
> allowlist (OQ2) must be fixed by a human before Step 1. The numbering/naming convention is
> `ADRNaming { path: "docs/decisions/", filename: "NNNN-kebab-case-title.md", numbering: sequential-4-digit }`.

## Slice 1: Author the `adr` skill (SKILL.md + references/ + assets/)

### Setup

1. ✨ Create `.claude/skills/<name>/references/madr-4.0.md` — full MADR 4.0 template plus per-section guidance for all eight required ordered sections of `MADR4Document { Title, Status, Date, Context-and-Problem-Statement, Decision-Drivers, Considered-Options, Decision-Outcome, Consequences }`, including the documented optional sections (ref: structure New Types §MADR4Document; design §Desired End State).
2. ✨ Create `.claude/skills/<name>/references/nygard.md` — Nygard original ADR template (ref: structure Slice 1 Files touched; design §Delta).
3. ✨ Create `.claude/skills/<name>/references/y-statements.md` — Y-statement format reference (ref: structure Slice 1 Files touched; design §Delta).
4. ✨ Create `.claude/skills/<name>/references/examples.md` — worked example ADRs (ref: structure Slice 1 Files touched; design §Delta).
5. ✨ Create `.claude/skills/<name>/assets/NNNN-template.md` — copyable MADR 4.0 starter ADR materializing the eight ordered `MADR4Document` sections; first `assets/` use in the repo (ref: structure Contracts §AssetReference; design Decision 2).

### Core Logic

6. ✨ Create `.claude/skills/<name>/SKILL.md` — write the YAML `SkillFrontmatter { name, description, command, argument-hint, allowed-tools }` block delimited by `---`, with `name` == `<name>`, `command` == `/<name>`, `description` in imperative "Use when… / Trigger on…" form, and `allowed-tools` set to the human-confirmed OQ2 allowlist (ref: structure New Types §SkillFrontmatter; design Q3).
7. ⚠️ Modify `.claude/skills/<name>/SKILL.md` — add the lean body section documenting MADR 4.0 as the default format and its eight ordered required sections, noting optional sections live in the reference file.
   - **Current:** file holds frontmatter only (after Step 6).
   - **After:** frontmatter + "Default format (MADR 4.0)" body section.
8. ⚠️ Modify `.claude/skills/<name>/SKILL.md` — add the `ADRStatusTransition { from, to, action }` prose markdown table encoding `proposed → accepted → deprecated|superseded` plus `rejected` (ref: structure New Types §ADRStatusTransition; design Decision 4).
   - **Current:** frontmatter + default-format section.
   - **After:** above + lifecycle transition table.
9. ⚠️ Modify `.claude/skills/<name>/SKILL.md` — add the `ADRNaming` rules section: `docs/decisions/` path, `NNNN-kebab-case-title.md` filename, sequential 4-digit numbering (adr-tools / log4brains compatible) (ref: structure New Types §ADRNaming; design §Desired End State).
   - **Current:** above through lifecycle table.
   - **After:** above + numbering/naming section.
10. ⚠️ Modify `.claude/skills/<name>/SKILL.md` — add the "When to write an ADR" judgment-call section defining "architecturally significant" (ref: structure Slice 1; design §Desired End State).
    - **Current:** above through naming section.
    - **After:** above + when-to-write section.
11. ⚠️ Modify `.claude/skills/<name>/SKILL.md` — add the `SupersedeProcedure(oldADR, newADR)` section documenting the bidirectional-link invariant (old ADR gets `superseded by ADR-NNNN`, new ADR gets `Supersedes ADR-NNNN`) and the deprecate / index-maintenance procedures (ref: structure Contracts §SupersedeProcedure; design §Desired End State).
    - **Current:** above through when-to-write section.
    - **After:** above + supersede/deprecate/index section.
12. ⚠️ Modify `.claude/skills/<name>/SKILL.md` — add one bare-relative-backtick `ReferenceLink` (`see \`references/<file>.md\``) for each of the four `references/*.md` files and one `AssetReference` (`\`assets/NNNN-template.md\``) for the starter, each file pointed to exactly once (ref: structure Contracts §ReferenceLink, §AssetReference; design Decision 3).
    - **Current:** body complete except cross-file pointers.
    - **After:** body includes exactly five on-demand pointers (4 references + 1 asset).

### Tests

13. Validate the skill via the `skill-creator` skill (external/global dependency, assumed present — structure Unverified Assumptions; design Q4); confirm success by manual review (no in-repo validator).
14. Run: `python3 scripts/grade.py` line_count helper against `.claude/skills/<name>/SKILL.md` as a one-off.
    - **Expected:** body ≤ 500 lines; token budget (≤5000) confirmed by inspection (no token counter exists — design Q7).
15. Run: `grep -rn "references/" .claude/skills/<name>/SKILL.md` and `grep -rn "assets/NNNN-template.md" .claude/skills/<name>/SKILL.md`.
    - **Expected:** each of the four `references/*.md` files appears exactly once and the asset exactly once, each as a bare-relative path in backticks.

### Verify Slice 1

16. **Checkpoint:** `ls .claude/skills/<name>/ .claude/skills/<name>/references/ .claude/skills/<name>/assets/ && grep -nE "^(name|description|command|argument-hint|allowed-tools):" .claude/skills/<name>/SKILL.md`
    - [ ] All six files exist (SKILL.md, four references, one asset).
    - [ ] Frontmatter has all five `SkillFrontmatter` fields; `name` == dir name and `command` == `/`+name.
    - [ ] Every `references/*.md` reachable by exactly one `ReferenceLink`; `assets/NNNN-template.md` by one `AssetReference` (grep, Step 15).
    - [ ] `SKILL.md` body ≤ 500 lines (Step 14); token budget verified by inspection.
    - [ ] `assets/NNNN-template.md` contains the eight ordered MADR sections.
    - [ ] Lifecycle transition table and supersede bidirectional-link procedure present.
    - [ ] Skill appears in the runtime's available-skills list (drop-in discoverability — design Q12).

---

## Slice 2: Sync the three hand-maintained skill lists

> Depends on Slice 1: the final `name` / `command` / `description` in `SKILL.md` frontmatter
> must be fixed before authoring these entries (structure Slice 2 Depends on; contract §SkillListEntry).

### Core Logic

17. ⚠️ Modify `.claude/CLAUDE.md` — add a `SkillListEntry` (`- \`/<name> <args>\` — <one-line desc>`) for the new skill to the available-skills list, matching the surrounding bullet style and the Slice 1 `description` (ref: structure Contracts §SkillListEntry; design §Delta).
    - **Current:** available-skills list ends at `/qrspi-pr`.
    - **After:** list includes the new `<name>` entry.
18. ⚠️ Modify `README.md` — add the same `SkillListEntry` for the skill, matching that file's existing bullet style (ref: structure Slice 2 Files touched; design §Delta).
    - **Current:** skill list without `<name>`.
    - **After:** skill list includes `<name>` with matching style.
19. ⚠️ Modify `docs/qrspi_claude_code_guide.md` — add the same `SkillListEntry` for the skill, matching that file's existing bullet style (ref: structure Slice 2 Files touched; design §Delta).
    - **Current:** skill list without `<name>`.
    - **After:** skill list includes `<name>` with matching style.

### Tests

20. Run: `grep -rl "<name>" .claude/CLAUDE.md README.md docs/qrspi_claude_code_guide.md`.
    - **Expected:** all three files returned.
21. Confirm by inspection that the `name` / `command` / `description` in each of the three entries matches Slice 1's final `SKILL.md` frontmatter (no drift).

### Verify Slice 2

22. **Checkpoint:** `grep -rn "<name>" .claude/CLAUDE.md README.md docs/qrspi_claude_code_guide.md`
    - [ ] `grep -rl "<name>"` returns all three files (Step 20).
    - [ ] Each entry uses that file's existing bullet style.
    - [ ] `name`/`command`/`description` in each entry matches Slice 1's final frontmatter (Step 21).

---

## Rollback Notes

- Steps 1-12 (Slice 1, new files): rollback = delete the `.claude/skills/<name>/` directory in full; no other code depends on it, and the skill simply stops appearing in the runtime's skill list.
- Step 5 (first-ever `assets/` convention): if the new convention is rejected in review, remove `assets/NNNN-template.md` and its `AssetReference` pointer from `SKILL.md` (Step 12) together; do not leave a dangling pointer.
- Steps 17-19 (Slice 2, doc edits): rollback = remove the added `SkillListEntry` bullet from each of the three files; these are additive single-line edits with no functional dependency.
- No DB migrations, config changes, or destructive operations in this plan.

---

## Blocking notes (carried from structure)

- **OQ1 — final skill slug (BLOCKING):** `<name>` must be chosen by a human before Step 1; it fixes the directory, every path above, the `command` stem, and all three Slice 2 entries.
- **OQ2 — `allowed-tools` allowlist:** must be confirmed before Step 6 writes the frontmatter (likely Read/Write/Edit + Glob, minimized per the firewall idiom).
- **OQ3 — scaffold `docs/decisions/` + index vs. document only:** this plan treats it as documentation-only (covered in Step 11). If scaffolding is in scope, an additional step/slice creating `docs/decisions/README.md` is required.
- **OQ4 — ≤500-line / ≤5000-token budget as gate vs. guideline:** treated here as a manual guideline (Step 14, inspection). A real gate would require a new check and an extra step.
