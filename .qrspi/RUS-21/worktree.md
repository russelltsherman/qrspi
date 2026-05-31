# Work Tree — Create a new agent skill: using-codex-cli

**Plan basis:** plan.md @ 2026-05-31T17:14:00Z
**Generated:** 2026-05-31T17:16:00Z
**Status:** draft
**Total sessions:** 2
**Critical path:** T1 → T2 → T3 → T4 → T5 → T6 (Verify S1) → T7 → T8 → T9 → T10 (Verify S2)

## Session 1

**Load:** structure.md §Contracts, structure.md §Slice 1, plan.md §Slice 1
**Estimated context:** ~25% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create skill dir + `references/` + `scripts/`; write SKILL.md frontmatter + stub H2 sections; add `references/` stub so links resolve | — | §1.1, §1.2, §1.4 | M | pending |
| T2 | Implement `scripts/validate_skill.py` (frontmatter keys, name==dir, body ≤500 lines, required sections present, reference links resolve) | T1 | §1.3 | M | pending |
| T3 | Write `scripts/test_validate_skill.py` (accept well-formed; reject missing-section, oversize, broken-link, name-mismatch) | T2 | §1.5 | M | pending |
| T4 | Run validator tests; fix until green | T3 | §1.6 | S | pending |
| T5 | Run validator against the stub skill; confirm pass | T4 | §1.7 | S | pending |
| T6 | **Verify Slice 1** (tests pass; validator exits 0; dir==name) | T5 | §1.7 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete (validated skeleton + green test guardrail). Fresh context for content authoring; Slice 2 is content-heavy (L) and benefits from a clean window.

## Session 2

**Load:** structure.md §Slice 2, plan.md §Slice 2, impl-log.md §Slice 1 (notes only — validator path, REQUIRED_SECTIONS list, body-size headroom)
**Estimated context:** ~45% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T7 | Create the five `references/*.md` files (sandbox-and-approvals, config, agents-md, automation, multi-agent) with full detail | T6 | §2.8 | L | pending |
| T8 | Replace SKILL.md stubs with real concise guidance for all required sections; keep body ≤500 lines; link every reference file | T7 | §2.9, §2.10 | L | pending |
| T9 | Run validator + tests; trim body into references if over budget; fix broken links | T8 | §2.11, §2.12 | M | pending |
| T10 | Optional: add one-line skill entry to README.md and `.claude/CLAUDE.md`; **Verify Slice 2** (validator pass + acceptance checklist) | T9 | §2.13, §2.14 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** End of implementation. Next step is the PR phase (handled by the orchestrator after Plan Approved).
