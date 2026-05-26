# Work Tree — Create a new agent skill called using graphite cli

**Plan basis:** plan.md @ 2026-05-26
**Generated:** 2026-05-26
**Status:** draft
**Total sessions:** 1
**Critical path:** T1 → T2 → T4 → T5 → T10

## Session 1

**Load:** structure.md §Types and Signatures, structure.md §Contracts, plan.md §Slice 1 (all steps)
**Estimated context:** ~25%

Context budget breakdown:
- structure.md §Types and Signatures + §Contracts: ~150 lines (~3%)
- plan.md §Slice 1 (Steps 1-14 + Verify checkpoint): ~300 lines (~6%)
- Existing SKILL.md (read for extraction): ~386 lines (~7%)
- Three output files (write): ~500 + ~300 + ~150 lines (~5%)
- Verification commands and eval output: ~100 lines (~2%)
- Overhead (tool calls, reasoning): ~2%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create `references/` directory under `~/.agents/skills/using-graphite-cli/` | — | §1.1 | S | pending |
| T2 | Create `references/command-reference.md` — extract detailed command docs, flag tables, aliases, examples from existing SKILL.md | T1 | §1.2 | L | pending |
| T3 | Create `references/safety-rules.md` — dangerous ops table, confirmation rules, recovery, raw-git warning, pre-sync checklist | T1 | §1.3 | M | pending |
| T4 | Rewrite SKILL.md body — restructure around Hard Rules, Workflow Loop, Conflict Resolution, Stack Navigation, Submit Defaults, Safety summary, Co-authorship, Reference Pointers; keep body under 500 lines | T2, T3 | §1.4 | L | pending |
| T5 | Verify AC1 (frontmatter validation) — run `quick_validate.py` or manual check | T4 | §1.5 | S | pending |
| T6 | Verify AC3 (body under 500 lines) — `tail -n +4 SKILL.md \| wc -l` | T4 | §1.6 | S | pending |
| T7 | Verify AC4 (reference files exist and non-empty) — `test -s` both files | T4 | §1.7 | S | pending |
| T8 | Verify AC5-AC10 (grep checks for single-commit-per-branch, workflow loop, conflict resolution, stack navigation, submit defaults, raw git warning) | T4 | §1.8-1.13 | S | pending |
| T9 | Verify checkpoint — run consolidated verification script from plan | T5, T6, T7, T8 | §1.Verify | S | pending |
| T10 | Run eval suite — `python3 scripts/run_eval.py --eval-set evals/graphite-evals.json --skill-path ~/.agents/skills/using-graphite-cli`; fix and re-run if any of 5 cases fail | T4 | §1.14 | M | pending |

### Task grouping notes

- T2 and T3 are independent of each other (both depend only on T1) and can be authored in parallel.
- T5, T6, T7, T8, T10 are all independent verification tasks that depend only on T4. They can run in any order or in parallel.
- T9 is a consolidated re-run of T5-T8 as a single script to confirm all pass together.
- T10 (eval suite) may require iteration if cases fail — the plan calls for adjusting description or body content and re-running. Budget for one iteration within this session.

### Why one session is sufficient

This is a single-slice feature with 4 implementation tasks and 6 verification tasks. All files are under 500 lines. The existing SKILL.md (386 lines) is read once for extraction, then the three output files are written. Verification is lightweight bash commands. Total estimated context stays well under 40%.
