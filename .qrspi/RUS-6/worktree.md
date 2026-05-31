# Work Tree — Create a new agent skill called using-graphite-cli

**Plan basis:** plan.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft
**Total sessions:** 2 (Session 2 conditional on OQ2)
**Critical path:** T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8 → T9 → T10 → T13 → (T14 → T15 → T16 → T17 → T18)

## Session 1 — Author the using-graphite-cli skill (Slice 1)

**Load:** structure.md §Contracts (`SKILL.md frontmatter`, `description field`, `allowed-tools value`, `Required inline content set`, `SKILL.md → references link`, `SKILL.md budget`, `command-reference.md content set`, `edge-cases.md content set`), structure.md §Unverified Assumptions (OQ1, OQ3), plan.md §Slice 1
**Estimated context:** ~30% of window
**Authoring note:** If skill-creator is available, author through it and its eval loop (OQ1); otherwise author directly and document deferral in the PR.

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create skill + references directory (`mkdir -p .claude/skills/using-graphite-cli/references/`); dir name must equal frontmatter `name` | — | §1 | S | pending |
| T2 | Create SKILL.md with five-field YAML frontmatter (`name`, `description`, `command`, `argument-hint`, `allowed-tools`); `description` front-loads triggers; `allowed-tools: Bash(gt:*)` + `Read` (UNVERIFIED pending OQ3) | T1 | §2 | M | pending |
| T3 | Append "Hard rules" inline section: single-commit-per-branch + no-raw-git prohibition | T2 | §3 | S | pending |
| T4 | Append core workflow section: full Create → Submit → Modify → Sync loop | T3 | §4 | M | pending |
| T5 | Append stack navigation section: nav commands + downstack/upstack directionality | T4 | §5 | S | pending |
| T6 | Append conflict-resolution flow: `gt continue` with explicit `git rebase --continue` prohibition | T5 | §6 | S | pending |
| T7 | Append submit-flag defaults (`gt ss -np` = `--no-edit --publish`) + raw-git mixing warning | T6 | §7 | S | pending |
| T8 | Append backtick-relative-path pointers to both reference files (no inlining; progressive disclosure) | T7 | §8 | S | pending |
| T9 | Create references/command-reference.md — full `gt` catalog | T2 | §9 | L | pending |
| T10 | Create references/edge-cases.md — conflict/metadata-drift/trunk-misdetect/deep-stack/GitHub integration | T2 | §10 | L | pending |
| T11 | Test: `wc -l`/`wc -c` SKILL.md — lines < 500 AND bytes/4 < 5000; offload prose if exceeded | T3,T4,T5,T6,T7,T8 | §11 | S | pending |
| T12 | Test: grep backtick `references/` paths and confirm each resolves on disk; no dangling links, no inlined content | T8,T9,T10 | §12 | S | pending |
| T13 | **Verify Slice 1** (checkpoint: budget, frontmatter five-fields + name==dir, references resolve, inline content set present, reference content sets complete, OQ1 disposition) | T11,T12 | §13 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete. Session 2 is conditional and operates on a different artifact (`evals/graphite-evals.json` + `scripts/run_eval.py`) with a distinct load manifest; fresh context avoids carrying skill-authoring detail into the eval-schema reconciliation.

## Session 2 (CONDITIONAL) — Reconcile graphite-evals.json with run_eval.py (Slice 2)

**INCLUDE ONLY IF** OQ2 resolves to "Definition of Done includes running the eval suite." Otherwise OMIT and document the deferral in the PR.

**Load:** plan.md §Slice 2, structure.md §Contracts (eval schema: `name`/`cases` + assertion shape), `evals/suite.json` (assertion shape reference), `scripts/run_eval.py` (required schema), impl-log.md §Slice 1 (notes only)
**Estimated context:** ~20% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T14 | Rename top-level key `skill_name` → `name` in graphite-evals.json | T13 | §14 | S | pending |
| T15 | Rename top-level key `evals` → `cases` | T14 | §15 | S | pending |
| T16 | Convert all 5 cases' `{text, type}` assertions to the shape required by run_eval.py (mirror suite.json) | T15 | §16 | M | pending |
| T17 | Test: run `python scripts/run_eval.py` against graphite-evals.json — no `ValueError`; all 5 cases parse/execute | T16 | §17 | S | pending |
| T18 | **Verify Slice 2** (checkpoint: harness runs without `ValueError`; 5 converted cases parse + execute; results recorded) | T17 | §18 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Final session. On completion, proceed to the PR phase (`/qrspi-pr RUS-6`); no further implementation sessions.
