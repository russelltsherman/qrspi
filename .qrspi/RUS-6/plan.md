# Implementation Plan — Create a new agent skill called using-graphite-cli

**Structure basis:** structure.md @ 2026-05-31T10:40:00Z
**Generated:** 2026-05-31T10:45:00Z
**Status:** draft
**Total steps:** 24

## Slice 1: Author the using-graphite-cli skill

### Setup

1. ✨ Create directory `.claude/skills/using-graphite-cli/references/` — via `mkdir -p .claude/skills/using-graphite-cli/references/`. Verify with `ls -d .claude/skills/using-graphite-cli/references/`.

### Core Logic

2. ✨ Create `.claude/skills/using-graphite-cli/SKILL.md` — write the main skill body. Frontmatter must contain `name: using-graphite-cli`, `description: <one-paragraph trigger description>`, `command: /using-graphite-cli`, `argument-hint: <task description>`, `allowed-tools: Read, Bash` (ref: structure.md New Types `SkillFrontmatter`, design.md Decision 4). Body must include sections: Preconditions (gt installed, authenticated, trunk configured), Core Workflow (Create → Submit → Modify → Sync subsections in that order), Single-commit-per-branch rule (one explicit "do this / not that" example pair), Stack navigation (`gt bu`, `gt bd`, `gt stack top`, `gt log short`, with downstack/upstack directionality definition), Submit defaults (`--no-edit --publish` for automation; `--draft` for WIP), When NOT to use raw git (with the one `git worktree` exception), Edge cases pointer (links to references/edge-cases.md), Onboarding pointer (links to references/onboarding.md), Command reference pointer (links to references/command-reference.md). Hard ceiling: 500 lines.

3. ✨ Create `.claude/skills/using-graphite-cli/references/command-reference.md` — comprehensive `gt` command list grouped by lifecycle: Init/Auth (`gt auth login`, `gt repo init --trunk main`, `gt repo trunk`, `gt repo remote`), Create (`gt create`, `gt track --parent <p>`), Submit (`gt submit`, `gt submit --stack`, `gt ss`, `gt submit --draft`, `gt submit --reviewers`, `gt submit --merge-when-ready`, `gt ds submit`), Modify (`gt modify`, `gt modify -c`), Sync (`gt sync`, `gt sync --force --delete-all`, `gt get`), Navigate (`gt bu`, `gt bd`, `gt stack top`, `gt log short`, `gt info`), Stack ops (`gt move --onto <branch>`, `gt restack`, `gt us restack`, `gt downstack edit`, `gt branch split`, `gt delete --force`), Conflict (`gt continue`, `gt restack` after resolution), Merge (`gt merge --confirm`). Each entry: one-line purpose + flag list + one example.

4. ✨ Create `.claude/skills/using-graphite-cli/references/edge-cases.md` — sections: Conflict resolution flow (resolve files, `git add`, then `gt continue` — explicit "NEVER `git rebase --continue`"); Stale worktree recovery (the three-step recovery from `qrspi-work/SKILL.md:691-697`: `git worktree remove --force`, `git worktree prune`, retry `git worktree add`); Multi-commit detection (how to spot it via `gt log short`, how to recover by squashing with `gt modify -c` or `gt squash`); HARD STOP: Infrastructure Errors (mirror the orchestrator's rule from `qrspi-work/SKILL.md:709-730` — STOP, print error verbatim, exit; no `chmod`/`chown`/`sudo`/raw git workaround); `gt sync` safety (forbidden during ticket planning because it deletes merged-PR branches; safe at session start and during cleanup). Each section ends with a "do this / not that" pair.

5. ✨ Create `.claude/skills/using-graphite-cli/references/onboarding.md` — sections: Install (`brew install graphite` on macOS/Linux, `npm i -g @withgraphite/graphite-cli` cross-platform), Authenticate (`gt auth login` with API token from app.graphite.dev), Initialize repo (`gt repo init --trunk main`), Verify (`gt repo trunk` should print the trunk branch), Override remote (`gt repo remote` if origin isn't the default). Each step has the exact command and the expected output shape.

6. ⚠️ Modify `.claude/CLAUDE.md` — add a single line under the "Available skills" list pointing to the new skill.
   - **Current:** the "Available skills" list ends at `/qrspi-pr <ticket-id>`.
   - **After:** append a new line `- \`/using-graphite-cli <task>\` — Reference skill for Graphite CLI (gt) usage, conventions, and conflict recovery`.

### Tests

7. Run: `wc -l .claude/skills/using-graphite-cli/SKILL.md`
   - **Expected:** integer < 500.

8. Run: `head -10 .claude/skills/using-graphite-cli/SKILL.md`
   - **Expected:** YAML frontmatter block opens at line 1 with `---`, contains the five fields `name`, `description`, `command`, `argument-hint`, `allowed-tools`, and closes with `---`.

9. Run: `grep -c 'gt continue' .claude/skills/using-graphite-cli/references/edge-cases.md`
   - **Expected:** integer ≥ 1.

10. Run: `grep -E -c 'single.commit|one commit' .claude/skills/using-graphite-cli/SKILL.md`
    - **Expected:** integer ≥ 1.

11. Run: `grep -E -c 'Create.*->.*Submit|Create.*Submit.*Modify.*Sync' .claude/skills/using-graphite-cli/SKILL.md`
    - **Expected:** integer ≥ 1 (workflow loop documented).

12. Run: `grep -E -c 'gt bu|gt bd|gt stack top|gt log short' .claude/skills/using-graphite-cli/SKILL.md`
    - **Expected:** integer ≥ 1 (navigation commands).

13. Run: `grep -E -c '\-\-no-edit|\-\-publish' .claude/skills/using-graphite-cli/SKILL.md`
    - **Expected:** integer ≥ 1 (submit defaults).

14. Run: `grep -E -c 'never .*git rebase|do NOT.*git rebase|raw git' .claude/skills/using-graphite-cli/SKILL.md`
    - **Expected:** integer ≥ 1.

15. Invoke the global skill-creator skill against `.claude/skills/using-graphite-cli/` to apply structural review. If skill-creator is not available in the agent's environment, note the deviation in `impl-log.md` and continue.

### Verify Slice 1

16. **Checkpoint:** `ls .claude/skills/using-graphite-cli/ .claude/skills/using-graphite-cli/references/ && wc -l .claude/skills/using-graphite-cli/SKILL.md .claude/skills/using-graphite-cli/references/*.md`
    - [ ] Four files exist: `SKILL.md`, `references/command-reference.md`, `references/edge-cases.md`, `references/onboarding.md`.
    - [ ] SKILL.md is under 500 lines.
    - [ ] Each reference is under 250 lines.
    - [ ] All 8 grep tests above pass.
    - [ ] `.claude/CLAUDE.md` has the new "Available skills" entry.

---

## Slice 2: Reconcile evals/graphite-evals.json with the suite pipeline

### Setup

17. Run: `python -c "import json; print(json.load(open('evals/suite.json'))['cases'][0].keys())"`
    - **Expected:** prints a `dict_keys([...])` that includes `id`, `name`, `phase`, `prompt`, `context`, `assertions`, `tags`, `difficulty`, `split`. Confirms the target schema.

18. Run: `python -c "import json; print(json.load(open('evals/graphite-evals.json')).keys())"`
    - **Expected:** prints `dict_keys(['skill_name', 'evals'])`. Confirms the source schema needs migration.

19. ⚠️ Inspect `scripts/grade.py` — read in full to inventory existing programmatic check names. Look for the registry/dispatch (e.g., `CHECKS = {...}` or `if check.startswith(...)`). Note which assertion functions already exist that the migrated cases can use (likely candidates: `output_file_exists`, `has_section`, regex-based checks). Decide whether new check names need to be added.

### Core Logic

20. ⚠️ Modify `evals/graphite-evals.json` — migrate to suite.json shape.
    - **Current:**
      ```
      {
        "skill_name": "graphite",
        "evals": [
          { "id": 1, "prompt": "...", "expected_output": "...", "files": [], "assertions": [{"text": "...", "type": "command_check"}] }
        ]
      }
      ```
    - **After:**
      ```
      {
        "name": "using-graphite-cli-evals",
        "version": "0.1.0",
        "description": "Eval suite for the using-graphite-cli skill",
        "defaults": { "trials_per_case": 3, "timeout_ms": 120000, "max_tokens": 128000 },
        "cases": [
          { "id": "case_g001", "name": "commit_intent", "phase": "skill", "prompt": "...", "context": { "files": [], "conversation_history": [], "user_preferences": {} }, "assertions": [ ... programmatic + llm_judge entries ... ], "tags": ["graphite", "commit"], "difficulty": "medium", "split": "train" }
        ]
      }
      ```
    - Case 1's staging assertion is rewritten: from "Includes -a or -u flag to stage changes" to "Stages files explicitly with `git add <files>` before invoking `gt create`/`gt modify` (no `-a`/`-u`)" (ref: design.md Decision 2). Preserve all 5 case IDs and intents — only the schema and the one staging assertion change.

21. ⚠️ Modify `scripts/grade.py` — only if step 19's inventory shows the existing checks are insufficient. If new checks are needed, add them with the same return-bool contract as existing checks. Likely additions: `command_used(transcript, expected_cmd)` and `flag_present(transcript, expected_flag)`. If step 19 finds an existing regex check that can express the same intent, prefer reusing it and skip this step.
    - **Current (only if modifying):** existing check registry without `command_used`/`flag_present`.
    - **After:** registry includes the new helpers, each documented with a one-line docstring.

### Tests

22. Run: `python -c "import json; json.load(open('evals/graphite-evals.json'))"`
    - **Expected:** exits 0 (file is valid JSON).

23. Run: `python -c "import json; data=json.load(open('evals/graphite-evals.json')); print(len(data['cases'])); types=set(); [types.add(a['type']) for c in data['cases'] for a in c['assertions']]; print(sorted(types))"`
    - **Expected:** prints `5` (case count preserved) on line 1 and a list containing only `'llm_judge'`, `'programmatic'`, and/or `'script'` on line 2 (no legacy assertion types).

24. If `scripts/grade.py` was modified in step 21:
    - Run: `python -m py_compile scripts/grade.py`
    - **Expected:** exit code 0 (no syntax errors).

### Verify Slice 2

25. **Checkpoint:** Run a single migrated case end-to-end through the pipeline. Exact command depends on `scripts/run_eval.py`'s CLI (inspected at step 19); a likely form is `python scripts/run_eval.py --suite evals/graphite-evals.json --case case_g001 --trials 1`.
    - [ ] Run completes without schema or runtime errors.
    - [ ] Output includes a score for the case (pass/fail does not matter — only that grading executed).
    - [ ] If the runner does not accept the schema, slice 2 will have surfaced the discrepancy in step 17/18 and the actual target schema is matched instead — note the discovery in `impl-log.md`.

---

## Rollback Notes

- Step 1: `rm -rf .claude/skills/using-graphite-cli/` — removes the new directory cleanly.
- Step 6: revert the single-line `.claude/CLAUDE.md` change with `git checkout .claude/CLAUDE.md` (slice 1 commit not yet finalized) or a one-line follow-up edit (after commit).
- Step 20: keep a copy of the original `evals/graphite-evals.json` content from the pre-edit state. If migration causes regressions, revert with `git checkout HEAD~1 -- evals/graphite-evals.json` (the prior commit on the slice's parent branch).
- Step 21: if `grade.py` changes break existing eval runs, revert that file with `git checkout HEAD~1 -- scripts/grade.py` and re-scope the migration to use only existing checks.
- Whole-ticket rollback: each slice is its own branch (`RUS-6/slice-1`, `RUS-6/slice-2`). To undo the entire feature without touching other branches, the human can drop both slice branches with `gt delete RUS-6/slice-1 --force` and `gt delete RUS-6/slice-2 --force`. The planning branch (`RUS-6/planning`) holds only artifacts under `.qrspi/RUS-6/` and does not modify production code.
