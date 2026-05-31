# Work Tree — Create a new agent skill called using github cli

**Plan basis:** plan.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft
**Total sessions:** 2
**Critical path:** T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8 → T9 → T10 → T11 → T12 → T13 → T14 → T15

## Session 1

**Load:** structure.md §Contracts, plan.md §Slice 1, design.md §Delta, design.md §Pattern Decisions
**Estimated context:** ~25% of window (one SKILL.md + 4 reference files, all new and authored from scratch; no existing-code reading required beyond research artifacts).

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create `.claude/skills/using-github-cli/` and `references/` directories | — | §1.1–1.2 | S | pending |
| T2 | Author `SKILL.md` frontmatter (name, description, command, argument-hint, allowed-tools) | T1 | §1.3 | S | pending |
| T3 | Author `SKILL.md` Authentication section (gh auth status preflight, GH_TOKEN, gh auth login/switch, GH_REPO) | T2 | §1.4 | S | pending |
| T4 | Author `SKILL.md` Defaults section (squash+delete-branch, HEREDOC, --json/--jq, non-interactive flags) | T3 | §1.5 | S | pending |
| T5 | Author `SKILL.md` PR Workflows + Code Review sections | T4 | §1.6–1.7 | M | pending |
| T6 | Author `SKILL.md` Issue Management, Releases, Actions, API Queries, Repo Management sections | T5 | §1.8 | M | pending |
| T7 | Author `SKILL.md` Scripting & Automation + Boundary with git/graphite + Hard Stop sections + References cross-links | T6 | §1.9–1.10 | M | pending |
| T8 | Create `references/gh-api.md` (REST verbs, --paginate, --cache, headers, batch mutations, worked examples) | T7 | §1.11 | M | pending |
| T9 | Create `references/graphql.md` (graphql shape, 2–3 worked queries, pagination cursors) | T8 | §1.12 | M | pending |
| T10 | Create `references/automation.md` (CI auth, gh status, aliases, exit-code patterns, --fill in CI) | T9 | §1.13 | M | pending |
| T11 | Create `references/extensions.md` (prefer built-in rule, curated list, install cookbook, consent note) | T10 | §1.14 | S | pending |
| T12 | **Verify Slice 1** — run checkpoint greps and line/section counts | T11 | §1.15 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 ships the entire authored skill as one self-contained deliverable. Slice 2 needs a fresh context because it consults the existing eval harness format (`evals/suite.json`, `evals/graphite-evals.json`, `scripts/grade.py`) which was not loaded in session 1. The author of slice 2 should approach the eval file with a fresh eye to avoid encoding slice-1 prose into the assertions.

## Session 2

**Load:** structure.md §Contracts, plan.md §Slice 2, `evals/graphite-evals.json` (for shape), `evals/suite.json` §assertions (for grammar), impl-log.md §Slice 1 notes (for skill path/section names only — not for assertion content).
**Estimated context:** ~15% of window (small JSON authoring task; only the eval-format files need full reads).

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T13 | Read `evals/graphite-evals.json` and `evals/suite.json` to confirm assertion grammar | T12 | §2.16 | S | pending |
| T14 | Create `evals/gh-evals.json` with case_001 covering: SKILL.md existence, line count, section count, reference-file presence, required keyword presence (gh auth status, GH_TOKEN, HARD STOP, --squash, --jq) | T13 | §2.17 | M | pending |
| T15 | **Verify Slice 2** — JSON validity, ≥1 case, ≥1 assertion per case, file references the new skill path | T14 | §2.18 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** No further sessions — slice 2 verification closes the implementation. The orchestrator will then call the PR phase.
