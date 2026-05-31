# Work Tree — Create a new agent skill called using-graphite-cli

**Plan basis:** plan.md @ 2026-05-31T10:45:00Z
**Generated:** 2026-05-31T10:50:00Z
**Status:** draft
**Total sessions:** 2
**Critical path:** T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8 → T9 → T10 → T11 → T12

## Session 1

**Load:** structure.md §New Types (`SkillFrontmatter`), structure.md §Contracts (link conventions), plan.md §Slice 1 (steps 1-16), design.md §Decision 1, design.md §Decision 4, design.md §Risk Register entries about scope creep and SKILL.md drift.
**Estimated context:** ~30%
**Goal:** Slice 1 — Author the using-graphite-cli skill end-to-end.

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create skill directory `.claude/skills/using-graphite-cli/references/` via `mkdir -p`. Verify with `ls -d`. | — | §1.1 | S | pending |
| T2 | Create `SKILL.md` with valid frontmatter (`name`, `description`, `command`, `argument-hint`, `allowed-tools: Read, Bash`) and full body (preconditions, Create→Submit→Modify→Sync workflow, single-commit rule, stack navigation, submit defaults, "no raw git" rule with worktree exception, links to references). Hard ceiling 500 lines. | T1 | §1.2 | M | pending |
| T3 | Create `references/command-reference.md` covering every `gt` command grouped by lifecycle phase. Each command: purpose, flags, one example. | T1 | §1.3 | M | pending |
| T4 | Create `references/edge-cases.md`: conflict via `gt continue` (NEVER `git rebase --continue`), stale worktree recovery, multi-commit detection, HARD STOP rule for infrastructure errors, `gt sync` safety. Each section ends with a do/don't pair. | T1 | §1.4 | S | pending |
| T5 | Create `references/onboarding.md`: install (brew, npm), `gt auth login`, `gt repo init --trunk main`, verify with `gt repo trunk`, override remote. | T1 | §1.5 | S | pending |
| T6 | Modify `.claude/CLAUDE.md`: append one-line entry for the new skill under "Available skills". | — | §1.6 | S | pending |
| T7 | Run the 8 grep/wc verification commands from plan steps 7-14. Capture any failures and revise files until all pass. | T2, T3, T4, T5 | §§1.7-1.14 | S | pending |
| T8 | Invoke the global skill-creator skill on the new skill directory; apply structural feedback if any. If skill-creator unavailable, note deviation in `impl-log.md`. | T2, T3, T4, T5 | §1.15 | S | pending |
| T9 | **Verify Slice 1** — run the checkpoint command from plan step 16 and confirm all checkboxes. | T7, T8 | §1.16 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete and verified. Fresh context for Slice 2 to focus exclusively on the eval pipeline schema migration. The skill content from Session 1 is not needed beyond the "Notes for next session" entries (which assertion intents were encoded so Slice 2 can author matching assertions).

## Session 2

**Load:** structure.md §Modified Types (`evals/graphite-evals.json` schema target), structure.md §Contracts (`programmatic_check`), plan.md §Slice 2 (steps 17-25), design.md §Decision 2 (staging convention), design.md §Decision 3 (eval schema), `impl-log.md` §Slice 1 notes for next session (assertion intents).
**Estimated context:** ~25%
**Goal:** Slice 2 — Reconcile `evals/graphite-evals.json` with the suite pipeline.

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T10 | Confirm target schema by reading `evals/suite.json` case shape (plan step 17) and source schema by reading `evals/graphite-evals.json` (plan step 18). Inspect `scripts/grade.py` and `scripts/run_eval.py` to inventory existing programmatic checks and learn the runner's CLI. | T9 | §§2.17-2.19 | M | pending |
| T11 | Migrate `evals/graphite-evals.json` to the suite.json schema: top-level `name`, `version`, `description`, `defaults`, `cases`; per-case `id`, `name`, `phase`, `prompt`, `context`, `assertions`, `tags`, `difficulty`, `split`. Translate the 5 original assertion intents into `programmatic`/`llm_judge` entries that reuse existing checks where possible. Reverse the staging assertion in case 1 (no `-a`/`-u`). | T10 | §2.20 | M | pending |
| T12 | If T10 revealed missing programmatic checks needed by T11, extend `scripts/grade.py` with new helpers (`command_used`, `flag_present`) — same return-bool contract as existing checks. Skip this task if existing checks cover all needs. | T10, T11 | §2.21 | S | pending |
| T13 | Run JSON validity and schema invariant checks (plan steps 22-23): `python -c "import json; json.load(...)"`, case count == 5, only `programmatic`/`llm_judge`/`script` assertion types. | T11, T12 | §§2.22-2.23 | S | pending |
| T14 | If `grade.py` was modified, run `python -m py_compile scripts/grade.py`. | T12 | §2.24 | S | pending |
| T15 | **Verify Slice 2** — execute one migrated case end-to-end through `scripts/run_eval.py` (exact CLI per T10's findings). Confirm grading runs without schema/runtime errors and produces a score. | T13, T14 | §2.25 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 2 complete and verified. Next phase is the PR phase (`qrspi-pr`), which runs in its own context with `impl-log.md`, `design.md`, and `structure.md` only.
