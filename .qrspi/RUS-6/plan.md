# Implementation Plan — Create a new agent skill called using-graphite-cli

**Structure basis:** structure.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft
**Total steps:** 18

## Slice 1: Author the using-graphite-cli skill (SKILL.md + references)

**Goal:** A complete, valid, budget-compliant `using-graphite-cli` skill at `.claude/skills/using-graphite-cli/` — SKILL.md plus both reference files — satisfying every acceptance criterion in design §Desired End State.

> **Authoring note (OQ1):** If skill-creator is available in the build environment, perform the file-authoring steps below *through* skill-creator and its eval loop rather than writing the files directly; the file targets and content sets are identical either way. If unavailable, author directly and document the deferral in the PR (ref: structure Unverified Assumptions OQ1).

### Setup

1. ✨ Create directory `.claude/skills/using-graphite-cli/references/` — establishes the skill directory and the references subdirectory in one `mkdir -p`; directory name `using-graphite-cli` MUST equal the frontmatter `name` (ref: structure Contracts `SKILL.md frontmatter`).

### Core Logic

2. ✨ Create `.claude/skills/using-graphite-cli/SKILL.md` — write the five-field YAML frontmatter only, fenced by `---`: `name: using-graphite-cli`, `description`, `command`, `argument-hint`, `allowed-tools`. Copy field shape verbatim from an existing SKILL.md. Quote `description` if its value contains `:`/`'`/comma (ref: structure Contracts `SKILL.md frontmatter`, `description field`).
   - `description`: front-load concrete trigger phrases + "Use when…" phrasing (commit, branch, diff, PR, stack, restack, sync) (ref: structure Contracts `description field`).
   - `allowed-tools`: `Bash(gt:*)` plus `Read` (ref: structure Contracts `allowed-tools value`). **UNVERIFIED pending OQ3** — if OQ3 resolves to "advise only," narrow per resolution.
3. ⚠️ Modify `.claude/skills/using-graphite-cli/SKILL.md` — append the "Hard rules" inline section: single-commit-per-branch as a non-negotiable, and the no-raw-git prohibition (ref: structure Contracts `Required inline content set`).
4. ⚠️ Modify `.claude/skills/using-graphite-cli/SKILL.md` — append the core workflow section: the full Create → Submit → Modify → Sync loop (ref: structure Contracts `Required inline content set`).
5. ⚠️ Modify `.claude/skills/using-graphite-cli/SKILL.md` — append the stack navigation section: navigation commands + directionality definitions (downstack = toward trunk, upstack = away from trunk) (ref: structure Contracts `Required inline content set`).
6. ⚠️ Modify `.claude/skills/using-graphite-cli/SKILL.md` — append the conflict-resolution flow: resolve via `gt continue`, with an explicit prohibition on `git rebase --continue` (ref: structure Contracts `Required inline content set`).
7. ⚠️ Modify `.claude/skills/using-graphite-cli/SKILL.md` — append submit-flag defaults: `--no-edit --publish` (`gt ss -np`) as the agent default, and an explicit warning against mixing raw `git branch`/`git rebase` with Graphite-tracked branches (ref: structure Contracts `Required inline content set`).
8. ⚠️ Modify `.claude/skills/using-graphite-cli/SKILL.md` — append pointers to references: bare backtick-wrapped relative paths to `references/command-reference.md` and `references/edge-cases.md`; do NOT inline their content (progressive disclosure) (ref: structure Contracts `SKILL.md → references link`).
9. ✨ Create `.claude/skills/using-graphite-cli/references/command-reference.md` — full `gt` catalog: init/config, create, submit + flags, modify, sync, navigation, downstack/upstack, restack, branch split, merge order (ref: structure Contracts `references/command-reference.md content set`).
10. ✨ Create `.claude/skills/using-graphite-cli/references/edge-cases.md` — conflict-resolution detail, metadata-drift recovery, trunk misdetection, deep-stack guidance, GitHub/CODEOWNERS integration (ref: structure Contracts `references/edge-cases.md content set`).

### Tests

11. Run: `wc -l .claude/skills/using-graphite-cli/SKILL.md` and `wc -c .claude/skills/using-graphite-cli/SKILL.md`
    - **Expected:** lines < 500 AND (bytes / 4) < 5000 (ref: structure Contracts `SKILL.md budget`). If exceeded, offload more inline prose into the reference files and re-measure.
12. Run: `grep -oE '`references/[^`]+`' .claude/skills/using-graphite-cli/SKILL.md` then confirm each referenced path exists on disk
    - **Expected:** every backtick-relative-path resolves to an existing file under `references/`; no dangling links; no reference content inlined.

### Verify Slice 1

13. **Checkpoint:** `wc -l .claude/skills/using-graphite-cli/SKILL.md && wc -c .claude/skills/using-graphite-cli/SKILL.md && ls .claude/skills/using-graphite-cli/references/`
    - [ ] SKILL.md < 500 lines and bytes/4 < 5000 tokens (ref: Q7).
    - [ ] Frontmatter has exactly the five fields between `---` fences; `name` == `using-graphite-cli` == directory name (ref: Q1, Q3).
    - [ ] Every backtick-relative-path reference in SKILL.md resolves to an existing file under `references/`; no reference content inlined.
    - [ ] SKILL.md body contains each required inline element: single-commit-per-branch rule, no-raw-git prohibition, full Create→Submit→Modify→Sync loop, navigation + directionality, `gt continue` conflict flow with explicit `git rebase --continue` prohibition, `--no-edit --publish` submit defaults, mixing-raw-git warning.
    - [ ] `command-reference.md` and `edge-cases.md` each cover their full content set (see structure Contracts).
    - [ ] If skill-creator is available (OQ1), the skill was authored/validated through it and its eval loop; otherwise the deferral is documented in the PR.

---

## Slice 2 (CONDITIONAL): Reconcile evals/graphite-evals.json with run_eval.py

**INCLUDE THIS SLICE ONLY IF** OQ2 resolves to "Definition of Done includes running the eval suite." Otherwise OMIT and document the deferral in the PR (ref: structure Slice 2 gate, design Risk Register row 1, OQ2).

**Goal:** `evals/graphite-evals.json` runs cleanly through `scripts/run_eval.py` using the `name`/`cases` schema and the assertion shape `run_eval.py` requires, instead of the current `skill_name`/`evals` + `{text, type}` shape that raises `ValueError` (ref: Q9, Q10).

**Depends on:** Slice 1.

### Core Logic

14. ⚠️ Modify `evals/graphite-evals.json` — rename top-level key `skill_name` → `name`.
    - **Current:** `{ "skill_name": "...", "evals": [...] }`
    - **After:** `{ "name": "...", "cases": [...] }` (top-level shape; assertion conversion follows)
15. ⚠️ Modify `evals/graphite-evals.json` — rename top-level key `evals` → `cases` (the array renamed in step 14's target shape, applied as a discrete edit if done separately).
    - **Current:** `"evals": [ ... ]`
    - **After:** `"cases": [ ... ]`
16. ⚠️ Modify `evals/graphite-evals.json` — convert each of the 5 cases' `{text, type}` assertion objects to the assertion format used by `evals/suite.json` / required by `scripts/run_eval.py`.
    - **Current:** assertions as `{ "text": "...", "type": "..." }`
    - **After:** the assertion shape consumed by `run_eval.py` (mirror `evals/suite.json`)

### Tests

17. Run: `python scripts/run_eval.py` (or the documented invocation) targeting `graphite-evals.json`
    - **Expected:** runs without raising `ValueError`; all 5 cases parse and execute; results recorded.

### Verify Slice 2

18. **Checkpoint:** `python scripts/run_eval.py`
    - [ ] `graphite-evals.json` runs through the harness without raising `ValueError`.
    - [ ] All 5 converted cases parse and execute; results recorded.

---

## Rollback Notes

- **Slice 1 (steps 1–10):** All new files. To reverse: `rm -rf .claude/skills/using-graphite-cli/`. No existing files modified; no migrations.
- **Step 14–16 (`evals/graphite-evals.json`):** Config/data edit to an existing tracked file. Before editing, the prior content is recoverable via `git checkout -- evals/graphite-evals.json` (or `git restore`). To reverse, restore the file from git. No data loss outside this single JSON file.
