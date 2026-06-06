# Work Tree — Create a new agent skill called using-graphite-cli

**Plan basis:** plan.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total sessions:** 2
**Critical path:** T1 → T4 → T5 → T6 → T7 → T10 → T11 (7 tasks)

> Single-slice ticket: all work lands under `.claude/skills/using-graphite-cli/`.
> Split into two sessions at a clean artifact boundary — SKILL.md body authored
> and structurally validated first, then the two content-heavy `references/`
> files (which need Graphite command/conflict detail) plus the final slice
> verification. Both sessions stay well under the 40% context budget.

## Session 1

**Load:** structure.md §New Types, structure.md §Contracts, structure.md §Files touched,
        plan.md §Slice 1 (steps 1-7, 10), design.md §Desired End State
**Estimated context:** ~25% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create `SKILL.md` with five-key YAML frontmatter (`SkillFrontmatter` order; identity-triple holds) | — | §1.1 | S | pending |
| T2 | Create `references/command-reference.md` placeholder header (lazy pointer target) | — | §1.2 | S | pending |
| T3 | Create `references/conflict-resolution.md` placeholder header (lazy pointer target) | — | §1.3 | S | pending |
| T4 | Add Create→Submit→Modify→Sync workflow section to SKILL.md (agent submit defaults inline) | T1 | §1.4 | M | pending |
| T5 | Add stack navigation + directionality section (`gt bu`/`gt bd`, `gt stack top`, `gt log short`) | T4 | §1.5 | S | pending |
| T6 | Add clustered hard-rules/prohibitions section (`hard-rule-format`: single-commit, no raw `git rebase`/`amend`, `gt continue`) | T5 | §1.6 | S | pending |
| T7 | Add lazy pointers + "QRSPI orchestration differs" note; enforce `size-budget` (≤500 lines / 5000 tokens) | T6, T2, T3 | §1.7 | M | pending |
| T10 | Structural check on SKILL.md frontmatter (five keys in order; `name` == `using-graphite-cli`; identity triple) | T7 | §1.10 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** SKILL.md body complete and structurally validated. Fresh context to author the two content-heavy `references/` files (full `gt` command catalog + conflict-resolution flow, verified against Graphite docs) and run the final slice verification — keeps the body-authoring context out of the reference work.

## Session 2

**Load:** structure.md §Files touched, structure.md §Contracts, plan.md §Slice 1 (steps 8-9, 11),
        design.md §Risk Register, design.md §Desired End State (acceptance criteria),
        SKILL.md §lazy pointers (the resolved pointer list only)
**Estimated context:** ~20% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T8 | Populate `references/command-reference.md` — full `gt` command catalog with flags | T2 | §1.8 | M | pending |
| T9 | Populate `references/conflict-resolution.md` — `gt continue` flow, edge cases, stack-repair recipes | T3 | §1.9 | M | pending |
| T11 | **Verify Slice 1** — checkpoint: identity triple, pointers resolve, size budget, all acceptance criteria present; invoke skill-creator eval if available | T8, T9, T10 | §1.11 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete and verified. No further sessions — this is the only slice; control returns to the orchestrator for PR submission.
