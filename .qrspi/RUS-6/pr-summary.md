# PR: Add using-graphite-cli skill (gt workflow + references)

**Ticket:** RUS-6
**Design:** design.md @ 2026-06-03T14:10:00Z
**Structure:** structure.md @ 2026-06-06T00:00:00Z

## Summary

Adds a new self-contained agent skill, `using-graphite-cli`, that documents
general-purpose Graphite CLI (`gt`) usage: the Create → Submit → Modify → Sync
loop, stack navigation and directionality, conflict resolution via `gt continue`,
agent submit defaults (`--no-edit --publish`), and a clustered set of hard rules
prohibiting raw-git history operations on tracked branches. The skill body
(`SKILL.md`) stays within the 500-line / 5000-token budget by offloading the full
command catalog and stack-repair recipes to two `references/` files, pointed to
lazily. This is a documentation-only ticket — three new files under
`.claude/skills/using-graphite-cli/`, no existing code or files modified
(discovery is by directory convention). Reviewer focus: (1) the
identity-triple / frontmatter contract is intact and YAML-valid, (2) the gt
command vocabulary and `gt continue` guidance are accurate for the installed
Graphite version (asserted from the ticket, see Risks), and (3) the
"QRSPI orchestration differs" note correctly reconciles general defaults with the
repo's stricter orchestrator conventions.

## Acceptance Criteria Mapping

The criteria below are the ticket's acceptance criteria as enumerated in
design.md §Desired End State. This is a documentation skill, so "implementation"
is a section/anchor in the artifact files and "test" is the structural /
textual-presence check recorded in impl-log.md (the only working in-repo
validation per CLAUDE.md; the eval harness is a placeholder).

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: Valid agentskills.io structure + five-key frontmatter | `SKILL.md` frontmatter block (lines 1-6) | Structural check — five keys present in order `name, description, command, argument-hint, allowed-tools`; YAML-valid (stdlib regex parse, PyYAML absent) |
| AC2: Identity triple (dir == name == command slug) | `using-graphite-cli/` + `name: using-graphite-cli` + `command: /using-graphite-cli` | Structural check — `name == using-graphite-cli`, `command == /using-graphite-cli`, dir matches |
| AC3: Built using skill-creator | `SKILL.md` (built manually to agentskills.io spec) | OQ1 — skill-creator is external/undefined in-repo; manual construction + structural check accepted (see Deviations / Open Items) |
| AC4: SKILL.md under 500 lines / 5000 tokens | `SKILL.md` — 133 lines, ~853 words | Checkpoint — `wc -l` = 133 (≤ 500); ~853 words (well under 5000 tokens) |
| AC5: Detailed reference material in `references/` | `references/command-reference.md`, `references/conflict-resolution.md` | Checkpoint — both files exist; both lazy pointers in `SKILL.md` resolve on disk |
| AC6: Single-commit-per-branch as a hard rule | `SKILL.md` §Hard rules "One commit per branch — ALWAYS" | Textual-presence check (design §Desired End State) — PASS |
| AC7: Complete Create → Submit → Modify → Sync loop | `SKILL.md` §The core loop (`gt create --all -m`, `gt submit --no-edit --publish`, `gt modify --all`, `gt sync`) | Textual-presence check — full loop present |
| AC8: Conflict resolution via `gt continue` (never `git rebase --continue`) | `SKILL.md` §Conflict resolution + §Hard rules; `references/conflict-resolution.md` | Textual-presence check — `gt continue` documented, raw `git rebase --continue` prohibited |
| AC9: Stack navigation + directionality | `SKILL.md` §Stack navigation & directionality (`gt bu`/`gt bd`, `gt stack top`, `gt log short`; downstack=toward-trunk) | Textual-presence check — navigation + directionality present |
| AC10: Submit flag defaults (`--no-edit --publish`) for agents | `SKILL.md` §The core loop step 2 | Textual-presence check — stated as agent default |
| AC11: Warn against mixing raw git branch/rebase with tracked branches | `SKILL.md` §Hard rules (NEVER `git rebase` / `git commit --amend`; Do NOT mix raw `git push`/`git branch`) | Textual-presence check — prohibition section present |

## Changes by Slice

### Slice 1: The using-graphite-cli skill (body + references)

Single-slice feature — the three files are mutually dependent (body's lazy
pointers are dead until the reference files exist), so they form one unit of work
with a single verification boundary (structure.md §Slice 1).

| File | Change | Lines |
|------|--------|-------|
| `.claude/skills/using-graphite-cli/SKILL.md` | ✨ new | +133 |
| `.claude/skills/using-graphite-cli/references/command-reference.md` | ✨ new | +108 |
| `.claude/skills/using-graphite-cli/references/conflict-resolution.md` | ✨ new | +65 |

### Workflow artifacts (not part of the deliverable)

The remaining files in the diff are QRSPI phase artifacts written under
`.qrspi/RUS-6/` by upstream phases; they are not part of the feature deliverable
but are accounted for here for completeness.

| File | Change | Lines |
|------|--------|-------|
| `.qrspi/RUS-6/questions.md` | ✨ new | +49 |
| `.qrspi/RUS-6/research.md` | ✨ new | +302 |
| `.qrspi/RUS-6/design.md` | ✨ new | +92 |
| `.qrspi/RUS-6/structure.md` | ✨ new | +122 |
| `.qrspi/RUS-6/plan.md` | ✨ new | +122 |
| `.qrspi/RUS-6/worktree.md` | ✨ new | +49 |
| `.qrspi/RUS-6/impl-log.md` | ✨ new | +28 |

## Testing Summary

This is a documentation artifact; verification is structural/textual per CLAUDE.md
(the only working in-repo validation — the eval harness is a placeholder).

- [x] Slice 1: Structural check — frontmatter parsed (stdlib regex, PyYAML absent); five keys present in order; `name`/`command`/dir identity-triple holds; `allowed-tools == Bash`; description double-quoted with "Use when" trigger — PASS
- [x] Slice 1: Reference-pointer resolution — both `see references/<file>` pointers in `SKILL.md` resolve to files on disk — PASS
- [x] Slice 1: Size budget — `wc -l SKILL.md` = 133 (≤ 500); ~853 words (well under 5000 tokens) — PASS
- [x] Slice 1: Acceptance-criteria textual presence (design §Desired End State) — single-commit hard rule, full gt loop, `gt continue`, navigation + directionality, submit defaults, raw-git prohibition all present — PASS
- [ ] skill-creator eval loop — NOT run as a slice gate (OQ1: external/undefined in-repo; structural check is the accepted validation) — see Open Items

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| `gt-workflow-vocabulary` (structure §Contracts) | full gt loop + `gt continue` + navigation in body | implemented as specified | none — contract satisfied |
| `identity-triple`, `lazy-reference-pointer`, `size-budget`, `hard-rule-format` | per structure §Contracts | implemented as specified | none — all contracts satisfied |
| skill-creator slice-final validation (structure §Slice 1 verification, OQ1) | invoke skill-creator eval loop if available | not invoked | skill-creator is external/undefined in-repo; structural check is the accepted in-repo validation (CLAUDE.md). Recorded, not silently dropped. |
| plan.md steps 2-3 / 8-9 (placeholder-then-populate references) | write empty reference files, then populate | reference files written with full content in one pass | same end state, fewer write passes; impl-log.md notes this against plan.md, not structure.md |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| skill-creator mandate unsatisfiable in-repo (external/undefined) | accepted (OQ1) — built to agentskills.io spec manually; structural check passes | n/a — documentation only; delete the skill dir to revert |
| Skill flags contradict qrspi-work / graphite-evals (`-a` staging, `gt sync` flags, submit confirmation) | mitigated — ticket conventions adopted for the general skill; "QRSPI orchestration differs" note added so readers aren't misled | edit/remove the divergence note in `SKILL.md` |
| Body exceeds 500-line / 5000-token budget | mitigated — 133 lines / ~853 words; catalog + edge cases offloaded to `references/` | n/a |
| `gt continue` documented but never used in-repo — may be wrong for this Graphite version | accepted/unverified — documented as canonical per ticket; NOT verified against the installed CLI (see Open Items) | correct the conflict-resolution guidance in `SKILL.md` + `references/conflict-resolution.md` if the CLI differs |
| Stack-navigation directionality asserted from ticket, no in-repo precedent | accepted/unverified — encoded from the ticket; not verified against the CLI | correct §Stack navigation if CLI semantics differ |
| No automated validation for skills (harness is a placeholder) | accepted — relied on manual review + structural check per CLAUDE.md | n/a |

**Overall rollback:** the entire change is three new files under
`.claude/skills/using-graphite-cli/`; removing that directory fully reverts the
feature with no impact on existing code (discovery is by directory convention).

## Open Items

- **OQ1 — skill-creator validation:** the "built using skill-creator" criterion (AC3) was satisfied by manual construction to the agentskills.io spec, not by invoking skill-creator (external/undefined in-repo). If a maintainer wants the skill-creator eval run, it can be invoked separately — it does not block this slice. Needs a human decision on whether this satisfies the criterion.
- **`gt continue` and stack-navigation directionality unverified against the installed Graphite CLI** (NEW PATTERN per design Decision 3 — neither appears in the repo today). Verify against the actual `gt` version before relying on the guidance.
- **OQ3 — stale co-authorship trailer** ("Opus 4.7" vs. running 4.8) in `qrspi-work`/`qrspi-batch.js`: out of scope for this ticket; flagged as a possible follow-up.
- **OQ4 — docs-list updates:** README and `.claude/CLAUDE.md` "Available skills" lists were NOT updated — auto-discovery is sufficient and doc updates are explicitly out of acceptance scope. Possible follow-up ticket if a maintainer wants the skill listed.
