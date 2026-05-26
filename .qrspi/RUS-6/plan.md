# Plan — Create a new agent skill called using graphite cli

**Ticket:** RUS-6
**Structure basis:** structure.md @ 2026-05-26
**Generated:** 2026-05-26
**Status:** draft

## Slice 1: Author complete skill (SKILL.md + all references)

### Step 1 — Create references directory

- **File:** `~/.agents/skills/using-graphite-cli/references/` (new directory)
- **Action:** `mkdir -p ~/.agents/skills/using-graphite-cli/references`
- **Purpose:** Establish the references subdirectory required by AC4 and the two-file reference architecture (Decision 4).

### Step 2 — Create references/command-reference.md

- **File:** `~/.agents/skills/using-graphite-cli/references/command-reference.md` (new)
- **Action:** Create file with content extracted from the existing SKILL.md body.
- **Purpose:** Hold detailed command documentation, flag tables, aliases, and examples — everything the model needs when executing a specific `gt` command but does not need at trigger time.
- **Content outline (from structure.md):**

```
# Command Reference

## Non-interactive flag table
  Table: command | required flags | notes
  Covers: create, modify, submit, sync, undo, abort, track, untrack, delete, absorb, squash, split
  List of commands that cannot be used non-interactively

## Core commands
  ### gt create — detailed flags (-a, -u, -o, -i, auto-name), heredoc example
  ### gt modify — amend (default) vs new commit (-c), heredoc example
  ### gt submit — all flags (--draft, --publish, --reviewers, --merge-when-ready, --dry-run, --confirm, --update-only, --stack)
  ### gt sync — --force --delete-all, --no-restack, -a; pre-sync git status check
  ### gt restack — scoped variants (--downstack, --upstack, --only, --branch)

## Branch management
  ### gt delete — --force, --upstack, --downstack, --close; restacking behavior
  ### gt rename — PR association warning
  ### gt track / gt untrack — parent specification, child untracking
  ### gt fold — --keep, --stack, --close
  ### gt squash — heredoc example
  ### gt split — --by-file only; multi-pattern; unusable modes
  ### gt pop — behavior description

## Stack reorganization
  ### gt move — --onto, --source, --only
  ### gt absorb — --force, --dry-run, -a

## Collaboration
  ### gt get — --force, --downstack, --remote-upstack
  ### gt freeze / gt unfreeze — purpose and usage

## Viewing info
  ### gt info — current branch, specific branch
  ### gt log — short, long, full; flags (--stack, --steps, --reverse, --show-untracked)
  ### gt parent / gt children

## Merging
  ### gt merge — --confirm, --dry-run

## Recovery
  ### gt undo — --force; mention after destructive ops
  ### gt continue — -a flag
  ### gt abort — --force

## Aliases table
  Full alias-to-command mapping table (gt c, gt m, gt s, gt ss, etc.)
  Note: always use full command form for clarity

## Terminology glossary
  stack, trunk, downstack, upstack, restack, frozen
```

### Step 3 — Create references/safety-rules.md

- **File:** `~/.agents/skills/using-graphite-cli/references/safety-rules.md` (new)
- **Action:** Create file with safety content extracted from the existing SKILL.md body plus AC10 raw-git warning.
- **Purpose:** Consolidate all safety-critical information: dangerous operations, confirmation requirements, recovery, and the raw-git prohibition.
- **Content outline (from structure.md):**

```
# Safety Rules

## Dangerous operations table
  Table: operation | why dangerous | confirmation required?
  Covers: gt submit, gt merge, gt delete --force, gt delete --close, gt sync --force

## Confirmation requirements
  - Always confirm with user before executing dangerous operations
  - After any mutation, run gt log short --no-interactive to show updated state
  - After destructive operations, mention gt undo availability

## Recovery via gt undo
  gt undo --force --no-interactive
  Scope: undoes most recent Graphite mutation only
  Limitation: cannot undo gt merge or gt submit side effects on remote

## Raw git commands warning (AC10)
  NEVER use these commands when Graphite manages the repository:
  - git commit (use gt create or gt modify)
  - git rebase (use gt restack)
  - git merge (use gt merge)
  - git push (use gt submit)

  SAFE raw git commands alongside Graphite:
  - git status
  - git diff / git diff --staged
  - git add <files>
  - git log (read-only; prefer gt log for stack-aware view)

  Why: raw git mutations corrupt Graphite's metadata, causing phantom branches,
  lost stack relationships, and broken restacks.

## Pre-sync checklist
  1. Run git status to check for uncommitted changes
  2. Commit or stash changes before syncing
  3. Only then run gt sync --force --delete-all --no-interactive
```

### Step 4 — Rewrite SKILL.md body

- **File:** `~/.agents/skills/using-graphite-cli/SKILL.md` (modify)
- **Action:** Rewrite the entire file. Preserve frontmatter `name` and `description` fields (may refine description text). Restructure body to match the organization defined in structure.md. Body must be under 500 lines.
- **Purpose:** Satisfy AC1 (valid frontmatter), AC3 (under 500 lines), AC5 (explicit single-commit-per-branch), AC6 (Create-Submit-Modify-Sync loop), AC7 (conflict resolution), AC8 (stack navigation with directionality), AC9 (submit defaults), AC10 (raw-git warning summary), and reference pointers (AC4).

- **Current frontmatter:**
```yaml
---
name: using-graphite-cli
description: "Use for ANY request involving version control, commits, branches, diffs, or pull requests — this is the mandatory, exclusive way to perform all such operations. Trigger whenever the user wants to: see what changed or review a diff, commit or amend their work, push code or submit/update PRs (including drafts), pull or sync from remote, squash or fold commits or branches together, create/delete/rename/navigate branches, restack or reorganize a stack, clean up merged branches, resolve merge conflicts, or anything else related to git history, branches, or code submission. This skill wraps the Graphite CLI for stacked PRs. Even simple read-only checks like viewing a diff or status must go through this skill. Never run raw git or gt commands outside it."
---
```

- **After frontmatter:** Same `name` and `description` (description may be refined during eval loop but starts unchanged).

- **After body structure:**

```
# Graphite CLI Skill

## Hard Rules
  1. Single-commit-per-branch (AC5)
     - Each Graphite branch carries exactly one logical commit
     - gt modify amends by default; use this, not gt modify -c, unless explicitly asked
     - Never create multiple commits on a single branch without user instruction
  2. No raw git mutations (AC10 summary)
     - git commit, git rebase, git merge, git push are forbidden
     - git status, git diff, git add are safe
     - Pointer: Read references/safety-rules.md for full detail
  3. Non-interactive execution
     - Every gt command must include --no-interactive
     - Never use commands that require interactive input with no override
  4. Co-authorship trailer required on every commit

## Primary Workflow Loop (AC6)
  Create → Submit → Modify → Sync
  ### Create (new work)
    gt create <branch> -a --no-interactive -m "message"
    When: starting new work or stacking on existing work
  ### Submit (push to remote)
    gt submit --no-edit --no-interactive
    When: work is ready for review; requires user confirmation
  ### Modify (update existing branch)
    gt modify -a --no-interactive -m "message"
    When: addressing review feedback or making changes to current branch
  ### Sync (pull from remote)
    git status first, then gt sync --force --delete-all --no-interactive
    When: pulling latest changes, cleaning up merged branches

## Conflict Resolution (AC7)
  1. Detect: gt restack or gt sync reports conflicts
  2. Resolve: edit conflicted files
  3. Stage: git add <resolved-files>
  4. Continue: gt continue -a --no-interactive
  Escape hatch: gt abort --force --no-interactive

## Stack Navigation (AC8)
  gt checkout <branch> --no-interactive — switch to named branch
  gt up --no-interactive — move to child (away from trunk / upstack)
  gt down --no-interactive — move to parent (toward trunk / downstack)
  gt top --no-interactive — move to stack tip (furthest from trunk)
  gt bottom --no-interactive — move to branch nearest trunk
  Directionality: upstack = away from trunk (children); downstack = toward trunk (ancestors)
  Step count: gt up 2, gt down 3

## Submit Defaults (AC9)
  Baseline: --no-edit --no-interactive
  Situational flags:
  - --draft / --publish
  - --reviewers <users>
  - --merge-when-ready
  - --stack (submit entire stack)
  - --dry-run (preview)
  - --update-only (skip creating new PRs)

## Safety Rules (summary)
  Dangerous operations: submit, merge, delete --force, delete --close, sync --force
  Always confirm with user before executing
  After mutations: run gt log short --no-interactive
  After destructive ops: mention gt undo --force --no-interactive
  Pointer: Read references/safety-rules.md for full detail

## Co-authorship
  Trailer: Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
  Heredoc pattern for message formatting (example)

## Reference Pointers
  - Read references/command-reference.md before executing any gt command you have not used in this session
  - Read references/safety-rules.md before any destructive operation
```

### Step 5 — Verify frontmatter validation (AC1)

- **Action:** Run `python3 /workspaces/qrspi/scripts/quick_validate.py ~/.agents/skills/using-graphite-cli` (if script exists and accepts this invocation).
- **Fallback:** If `quick_validate.py` does not exist or has a different interface, manually verify: frontmatter contains only allowed keys (`name`, `description`, `license`, `allowed-tools`, `metadata`, `compatibility`); `name` is kebab-case, max 64 chars; `description` is under 1024 chars.
- **Expected:** Pass.

### Step 6 — Verify body line count (AC3)

- **Action:** `tail -n +4 ~/.agents/skills/using-graphite-cli/SKILL.md | wc -l`
- **Expected:** Output is less than 500.

### Step 7 — Verify reference files exist and are non-empty (AC4)

- **Action:** `test -s ~/.agents/skills/using-graphite-cli/references/command-reference.md && echo "command-reference OK" && test -s ~/.agents/skills/using-graphite-cli/references/safety-rules.md && echo "safety-rules OK"`
- **Expected:** Both files report OK.

### Step 8 — Verify AC5 (single-commit-per-branch)

- **Action:** `grep -i "single.commit\|one.*commit.*per.*branch\|one logical commit" ~/.agents/skills/using-graphite-cli/SKILL.md`
- **Expected:** At least one match.

### Step 9 — Verify AC6 (Create-Submit-Modify-Sync loop)

- **Action:** `grep -i "Create.*Submit.*Modify.*Sync\|Create → Submit → Modify → Sync" ~/.agents/skills/using-graphite-cli/SKILL.md`
- **Expected:** At least one match.

### Step 10 — Verify AC7 (conflict resolution with gt continue and gt abort)

- **Action:** `grep "gt continue" ~/.agents/skills/using-graphite-cli/SKILL.md && grep "gt abort" ~/.agents/skills/using-graphite-cli/SKILL.md`
- **Expected:** Both present.

### Step 11 — Verify AC8 (stack navigation with directionality)

- **Action:** `grep "gt up\|gt down\|gt top\|gt bottom" ~/.agents/skills/using-graphite-cli/SKILL.md | wc -l`
- **Expected:** At least 4 matches (one per command).

### Step 12 — Verify AC9 (submit defaults)

- **Action:** `grep "\-\-no-edit.*\-\-no-interactive\|\-\-no-interactive.*\-\-no-edit" ~/.agents/skills/using-graphite-cli/SKILL.md`
- **Expected:** At least one match.

### Step 13 — Verify AC10 (raw git warning)

- **Action:** `grep -i "raw git\|git commit.*forbidden\|never.*git commit\|git push.*forbidden\|never.*git push" ~/.agents/skills/using-graphite-cli/SKILL.md ~/.agents/skills/using-graphite-cli/references/safety-rules.md`
- **Expected:** At least one match in body or safety-rules.md.

### Step 14 — Run existing eval suite

- **Action:** `cd /workspaces/qrspi && python3 scripts/run_eval.py --eval-set evals/graphite-evals.json --skill-path ~/.agents/skills/using-graphite-cli`
- **Expected:** All 5 cases pass.
- **If fails:** Examine which eval failed, adjust description or body content to restore trigger coverage, re-run.

### Verify checkpoint (Slice 1)

Run all verification commands in sequence:

```bash
# AC1: frontmatter validation (manual check if script unavailable)
python3 /workspaces/qrspi/scripts/quick_validate.py ~/.agents/skills/using-graphite-cli 2>/dev/null || echo "MANUAL: verify frontmatter keys are name+description only"

# AC3: body under 500 lines
LINES=$(tail -n +4 ~/.agents/skills/using-graphite-cli/SKILL.md | wc -l)
echo "Body lines: $LINES"
[ "$LINES" -lt 500 ] && echo "AC3 PASS" || echo "AC3 FAIL"

# AC4: reference files exist
test -s ~/.agents/skills/using-graphite-cli/references/command-reference.md && echo "AC4a PASS" || echo "AC4a FAIL"
test -s ~/.agents/skills/using-graphite-cli/references/safety-rules.md && echo "AC4b PASS" || echo "AC4b FAIL"

# AC5: single-commit-per-branch
grep -qi "single.commit\|one.*commit.*per.*branch\|one logical commit" ~/.agents/skills/using-graphite-cli/SKILL.md && echo "AC5 PASS" || echo "AC5 FAIL"

# AC6: workflow loop
grep -qi "Create.*Submit.*Modify.*Sync" ~/.agents/skills/using-graphite-cli/SKILL.md && echo "AC6 PASS" || echo "AC6 FAIL"

# AC7: conflict resolution
grep -q "gt continue" ~/.agents/skills/using-graphite-cli/SKILL.md && grep -q "gt abort" ~/.agents/skills/using-graphite-cli/SKILL.md && echo "AC7 PASS" || echo "AC7 FAIL"

# AC8: navigation commands
NAV=$(grep -c "gt up\|gt down\|gt top\|gt bottom" ~/.agents/skills/using-graphite-cli/SKILL.md)
[ "$NAV" -ge 4 ] && echo "AC8 PASS ($NAV matches)" || echo "AC8 FAIL ($NAV matches)"

# AC9: submit defaults
grep -q "\-\-no-edit" ~/.agents/skills/using-graphite-cli/SKILL.md && grep -q "\-\-no-interactive" ~/.agents/skills/using-graphite-cli/SKILL.md && echo "AC9 PASS" || echo "AC9 FAIL"

# AC10: raw git warning
grep -rqi "raw git\|never.*git commit\|git commit.*forbidden" ~/.agents/skills/using-graphite-cli/SKILL.md ~/.agents/skills/using-graphite-cli/references/safety-rules.md && echo "AC10 PASS" || echo "AC10 FAIL"

# Eval suite
cd /workspaces/qrspi && python3 scripts/run_eval.py --eval-set evals/graphite-evals.json --skill-path ~/.agents/skills/using-graphite-cli 2>&1 || echo "EVAL: check output above for failures"
```

## Rollback Notes

- **No DB migrations or config changes.** All changes are to files in `~/.agents/skills/using-graphite-cli/`.
- **Rollback procedure:** The existing SKILL.md content is 386 lines and fully captured in git history (if committed) or can be restored from the current file before modifications begin. The implementer should back up the existing SKILL.md before starting:
  ```bash
  cp ~/.agents/skills/using-graphite-cli/SKILL.md ~/.agents/skills/using-graphite-cli/SKILL.md.bak
  ```
- **New files:** `references/command-reference.md` and `references/safety-rules.md` can be deleted to roll back to the pre-feature state.
- **No destructive operations.** No data loss risk. The skill directory is not version-controlled by this project's git repo (it lives in `~/.agents/`), so changes are local to this machine only.

## Step Count Summary

| Step | Action | File |
|------|--------|------|
| 1 | mkdir | `references/` directory |
| 2 | create | `references/command-reference.md` |
| 3 | create | `references/safety-rules.md` |
| 4 | modify | `SKILL.md` (full rewrite) |
| 5 | verify | AC1 — frontmatter validation |
| 6 | verify | AC3 — body line count |
| 7 | verify | AC4 — reference files exist |
| 8 | verify | AC5 — single-commit-per-branch |
| 9 | verify | AC6 — workflow loop |
| 10 | verify | AC7 — conflict resolution |
| 11 | verify | AC8 — stack navigation |
| 12 | verify | AC9 — submit defaults |
| 13 | verify | AC10 — raw git warning |
| 14 | verify | eval suite (5 cases) |

**Total steps: 14** (4 implementation + 10 verification)
