# Work Tree — Create a new agent skill called writing Product Requirements Documents

**Plan basis:** plan.md @ 2026-05-31
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft
**Total sessions:** 2
**Critical path:** T1 → T2 → T3 → T4 → T5 → T6 → T7 (Verify Slice 1) → T8 → T9 → T10 → T11 (Verify Slice 2)

## Session 1 — Author the writing-prds skill

**Load:** structure.md §New Types, structure.md §Contracts, structure.md §Slice 1, plan.md §Slice 1
**Estimated context:** ~25% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create skill dir + `references/`; scaffold via skill-creator or author directly to repo layout | — | §1.1–1.2 | S | pending |
| T2 | Write `SKILL.md` frontmatter (name/description/command/argument-hint/allowed-tools) | T1 | §1.3 | S | pending |
| T3 | Write `SKILL.md` body: evidence gate + problem-first ordering + default-vs-expanded + template pointer + finalize checklist | T2 | §1.4–1.8 | M | pending |
| T4 | Create `references/prd-template.md` (6 sections + SMART table + mandatory non-goals + user-story format + changelog) | T1 | §1.9 | M | pending |
| T5 | Create `references/expanded-format.md` (expansion triggers + additional sections) | T1 | §1.10 | S | pending |
| T6 | Frontmatter + content sanity checks (grep section headers, SMART table, story markers) | T3, T4, T5 | §1.11–1.12 | S | pending |
| T7 | **Verify Slice 1** — files exist, SKILL.md ≤ 500 lines, all required content present | T6 | §1.13 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete (skill authored). Fresh context for the eval-harness wiring, which needs different load (suite.json schema, grade.py checks) rather than the authoring context.

## Session 2 — Wire and run the eval gate

**Load:** structure.md §Contracts, structure.md §Slice 2, structure.md §Unverified Assumptions, plan.md §Slice 2, impl-log.md §Slice 1 (notes only)
**Estimated context:** ~25% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T8 | Read `evals/suite.json` schema; add fixture `prd_request_lean.md` if none suits | T7 | §2.14–2.15 | S | pending |
| T9 | Append `writing-prds` eval case with assertions (output_file_exists, has_section x3, line_count SKILL.md 500) | T8 | §2.16–2.17 | M | pending |
| T10 | Add `problem_before_solution` check to `grade.py` ONLY if not expressible with existing checks | T9 | §2.18 | S | pending |
| T11 | Run `run_eval.py` + `grade.py`; record results / harness limits in impl-log; **Verify Slice 2** (or report blocker per §2.22) | T10 | §2.19–2.23 | M | pending |

--- SESSION BOUNDARY ---
**Reason:** Final session. After Verify Slice 2, the PR phase generates the summary.

## Notes

- Slices are cohesive units (structure rule 8): Slice 1's SKILL.md and its two references are mutually dependent and verified together; Slice 2's eval wiring is a single testability boundary verified by one green run. They are split because Slice 2 can only be verified after Slice 1 exists, and it loads a distinct context (harness internals vs. authoring).
- Watch the blocker in §2.22 / structure §Unverified Assumptions: if `run_eval.py` assumes a QRSPI `phase`, T11 may degrade to a defined-but-not-run eval case with documented manual verification. Surface the exact harness error rather than working around it.
- Each session stays well under the 40% context ceiling; no `/compact` expected mid-session.
