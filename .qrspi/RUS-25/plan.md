# Implementation Plan — Create a new agent skill: writing Architecture Decision Records

**Structure basis:** structure.md @ 2026-05-31T16:36:00Z
**Generated:** 2026-05-31T16:39:00Z
**Status:** draft
**Total steps:** 22

## Slice 1: Author the ADR-writing skill via skill-creator

### Setup

1. Invoke the `skill-creator` skill (the Anthropic skill builder) to scaffold a new skill. Provide: skill name (kebab-case, derived from ticket title — confirm against OQ1, default `writing-architecture-decision-records`), purpose ("guide agents to write and manage Architecture Decision Records"), and request the standard `references/` + `assets/` structure. Target directory: `.claude/skills/<name>/`.
   - **Reference:** structure.md §Slice 1, Decision 2. If skill-creator is unavailable or errors, STOP and report (do not hand-author).
2. ✨ Confirm scaffold created `.claude/skills/<name>/SKILL.md` with valid frontmatter keys `name` and `description`. Set `name` to the chosen kebab-case value; ensure no collision with existing skills (ref: structure.md Contracts; research Q9).

### Core Logic — SKILL.md body

3. ⚠️ Write the SKILL.md `description` field: capability summary + explicit "Use when/Trigger on" phrases (e.g., "write an ADR", "record an architecture decision", "supersede/deprecate an ADR", "maintain the ADR index") + negative scope ("not for making the decision itself; not for CI enforcement; not for retroactive generation from code").
   - **Current:** scaffold placeholder description
   - **After:** trigger-tuned description per structure.md §Contracts and research Q11
4. ✨ Body section "When to write an ADR": encode the architecturally-significant test (hard to reverse, multi-component, affects non-functional requirements, would confuse future developers); include the "when in doubt, write a lightweight one" guidance.
5. ✨ Body section "Default format: MADR 4.0": list the required ordered sections (Title; Status; Date; Context and Problem Statement; Decision Drivers; Considered Options; Decision Outcome; Consequences) and the optional sections (Deciders, Consulted, Informed, Pros/Cons per option, Confirmation, More Information). Point to `references/madr-4.0.md` for the full template.
6. ✨ Body section "Choosing a format": an option/recommendation table — MADR (default), Nygard (minimal-ceremony teams), Y-statement (rapid lightweight capture) — pointing to `references/nygard.md` and `references/y-statements.md` (ref: structure.md Contracts choose-format; design Decision 1).
7. ✨ Body section "Numbering, naming, and location": `NNNN-kebab-case-title.md`, zero-padded 4-digit, sequential, never reused; default `docs/decisions/`, accept `docs/adr/` and `architecture/decisions/`; monorepo + per-domain subdirectory caveat (numbering becomes local). State adr-tools / log4brains compatibility explicitly.
8. ✨ Body section "Status lifecycle": proposed → accepted → [deprecated | superseded]; proposed → rejected; ADRs immutable once accepted (only status/date may change).
9. ✨ Body section "Creating an ADR": instruct the agent to copy `assets/adr-template.md`, fill placeholders, compute next `NNNN` (max existing + 1), write to `docs/decisions/`, set status `proposed`, and add an index row (ref: structure.md Contracts create-adr).
10. ✨ Body section "Superseding an ADR": create new ADR with "Supersedes ADR-NNNN" back-reference; set old ADR status to `superseded by ADR-NNNN` with forward reference; update both index entries — bidirectional links mandatory (ref: structure.md Contracts supersede-adr).
11. ✨ Body section "Deprecating an ADR": set status `deprecated`, update date and index; body otherwise immutable.
12. ✨ Body section "Maintaining the index": keep `docs/decisions/README.md` listing every ADR with number, title, and status; point to `assets/index-README-template.md`.
13. ✨ Body section "Writing style & level of detail": write for a future developer 6 months out; full sentences; 1-2 pages / ~200-500 words; match weight to decision (200 words for a library choice, 500+ for event sourcing); supersede-vs-amend judgment call.
14. ⚠️ Trim/verify the body stays under 500 lines and ~5000 tokens; move any overflow detail into the appropriate `references/` file.
    - **Current:** body possibly verbose
    - **After:** body ≤ 500 lines, ≤ ~5000 tokens, detail offloaded to references

### Core Logic — references and assets

15. ✨ Create `references/madr-4.0.md` — full MADR 4.0 template with every required and optional section, each annotated with the ticket's per-section guidance (context, decision, consequences guidance).
16. ✨ Create `references/nygard.md` — Nygard original template (Title, Status, Context, Decision, Consequences) and when to prefer it.
17. ✨ Create `references/y-statements.md` — Y-statement one-line format ("In the context of <use case>, facing <concern>, we decided for <option> to achieve <quality>, accepting <downside>") and when to prefer it.
18. ✨ Create `references/examples.md` — at least two worked example ADRs (one lightweight ~200 words, one heavy ~500 words) plus a worked supersede pair (old + new) demonstrating bidirectional links.
19. ✨ Create `assets/adr-template.md` — copyable MADR 4.0 starter using angle-bracket placeholders (e.g., `# ADR-NNNN: <Short noun phrase>`) matching the repo template convention (research Q8).
20. ✨ Create `assets/index-README-template.md` — copyable `docs/decisions/README.md` index starter with a placeholder table (number, title, status, link).

### Verify Slice 1

21. Run skill-creator's validation / eval loop on the new skill (description-trigger check + structural validation). Address any findings it surfaces.
    - **Expected:** skill validates; description triggers on ADR requests and not on unrelated ones.
22. **Checkpoint:** structural verification of the deliverable.
    - [ ] `.claude/skills/<name>/SKILL.md` exists with valid `name` + `description` frontmatter; `name` is unique kebab-case
    - [ ] `wc -l SKILL.md` body < 500 lines; token estimate < ~5000
    - [ ] `references/` contains madr-4.0.md, nygard.md, y-statements.md, examples.md — all non-empty
    - [ ] `assets/adr-template.md` and `assets/index-README-template.md` exist and use angle-bracket placeholders
    - [ ] Body covers: when-to-write test, MADR default sections, format selection, numbering/naming, status lifecycle + immutability, create/supersede/deprecate, bidirectional links, index maintenance, writing style + level-of-detail
    - [ ] adr-tools / log4brains conventions stated (naming + paths)
    - [ ] skill-creator eval loop passed

---

## Rollback Notes

- Steps 1-20 are purely additive (new files under a new skill directory). Rollback = delete `.claude/skills/<name>/`. No existing files are modified, so there is no destructive change to reverse.
- Step 21 (skill-creator eval) is read/validate-only; no rollback needed.
- No DB migrations, config changes, or destructive operations are involved.
