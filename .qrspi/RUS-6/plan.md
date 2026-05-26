# Plan -- Create a new agent skill called using graphite cli

**Ticket:** RUS-6
**Structure basis:** structure.md @ 2026-05-26
**Generated:** 2026-05-26
**Status:** draft

---

## Slice 1: Skill definition, reference files, and eval alignment

**Goal:** Deliver the complete `using-graphite-cli` skill (SKILL.md + two reference files) and fix the contradictory eval assertions in `graphite-evals.json`, then validate via skill-creator.

**Depends on:** none

---

### Step 1.1 — Create command reference file

- **Action:** Create new file
- **File:** `.claude/skills/using-graphite-cli/references/command-reference.md`
- **Purpose:** Complete gt command reference covering all subcommands, flags, examples, and directionality conventions. This file is loaded by the SKILL.md via an explicit `Read` instruction.
- **Content outline:**
  - Section: Directionality conventions (downstack = toward trunk, upstack = away from trunk)
  - Section: Branch lifecycle commands (`gt create`, `gt modify`, `gt submit`)
  - Section: Stack navigation commands (`gt bu`, `gt bd`, `gt stack top`, `gt checkout`)
  - Section: Stack management commands (`gt log`, `gt log short`, `gt move`, `gt restack`, `gt delete`)
  - Section: Sync commands (`gt sync`)
  - Section: `gt continue` (conflict resolution only -- detail deferred to conflict-resolution.md)
  - Each command entry includes: syntax, required/optional flags, examples, and notes on `--no-interactive` behavior
- **Target size:** 200-400 lines

### Step 1.2 — Create conflict resolution reference file

- **Action:** Create new file
- **File:** `.claude/skills/using-graphite-cli/references/conflict-resolution.md`
- **Purpose:** Conflict resolution procedures using `gt continue`, restack flows, and recovery from common errors. Loaded by SKILL.md via explicit `Read` instruction.
- **Content outline:**
  - Section: Golden rule -- always `gt continue`, never `git rebase --continue`
  - Section: Conflict resolution during `gt restack`
  - Section: Conflict resolution during `gt sync`
  - Section: Conflict resolution during `gt move`
  - Section: Recovery from common errors (detached HEAD, dirty worktree, failed restack)
  - Section: When to abort vs. continue
- **Target size:** 50-100 lines

### Step 1.3 — Create SKILL.md

- **Action:** Create new file
- **File:** `.claude/skills/using-graphite-cli/SKILL.md`
- **Purpose:** Main skill definition with frontmatter conforming to the 5-field contract, core workflow rules, and Read instructions pointing to both reference files.
- **Frontmatter (exact):**
  ```yaml
  ---
  name: using-graphite-cli
  description: "Use for ANY request involving version control, commits, branches, diffs, or pull requests — this is the mandatory, exclusive way to perform all such operations. Trigger whenever the user wants to: see what changed or review a diff, commit or amend their work, push code or submit/update PRs (including drafts), pull or sync from remote, squash or fold commits or branches together, create/delete/rename/navigate branches, restack or reorganize a stack, clean up merged branches, resolve merge conflicts, or anything else related to git history, branches, or code submission. This skill wraps the Graphite CLI for stacked PRs. Even simple read-only checks like viewing a diff or status must go through this skill. Never run raw git or gt commands outside it."
  command: /using-graphite-cli
  argument-hint: "<subcommand>"
  allowed-tools: Bash
  ---
  ```
- **Body content outline (must stay under 500 lines):**
  - Load reference files:
    - `Read .claude/skills/using-graphite-cli/references/command-reference.md`
    - `Read .claude/skills/using-graphite-cli/references/conflict-resolution.md`
  - Section: Core Principles
    - Single-commit-per-branch rule (HARD DIRECTIVE): each Graphite branch has exactly one commit; `gt create` for new branches, `gt modify` for amendments
    - All `gt` commands include `--no-interactive`
    - Never use raw `git branch`, `git rebase`, `git commit --amend` on Graphite-tracked branches
    - Permitted raw git commands: `git add`, `git status`, `git diff`
  - Section: Staging Rule
    - NEVER use `-a` flag on `gt create` or `gt modify`
    - Always use explicit `git add <files>` before `gt create`/`gt modify`
    - Run `git status --short` after staging to verify only intended files are staged
  - Section: Workflow Loop (Create -> Submit -> Modify -> Sync)
    - Create: `gt create <branch-name> --no-interactive -m "<message>"`
    - Submit: `gt submit --no-edit --publish --no-interactive`
    - Modify: `gt modify -c --no-interactive -m "<message>"` (amend existing branch)
    - Sync: `gt sync --force --no-interactive`
  - Section: Safety Rules
    - Always check `git status` before destructive operations
    - Always run `gt log short --no-interactive` after mutations to verify stack state
    - Ask user for confirmation before `gt submit`
  - Section: Conflict Resolution (summary, defer to reference file for details)
    - Always `gt continue`, never `git rebase --continue`
  - Section: Co-authorship Trailer
    - All commit messages must include the co-authorship trailer via heredoc format
- **Target size:** 150-300 lines body

### Step 1.4 — Update graphite-evals.json: fix skill_name

- **Action:** Modify existing file
- **File:** `evals/graphite-evals.json`
- **Current:** `"skill_name": "graphite"`
- **After:** `"skill_name": "using-graphite-cli"`
- **Rationale:** Align eval suite with the actual skill directory name per structure contract.

### Step 1.5 — Update graphite-evals.json: fix eval case 1 staging assertion

- **Action:** Modify existing file
- **File:** `evals/graphite-evals.json`
- **Current (eval id 1, assertion index 3):**
  ```json
  {"text": "Includes -a or -u flag to stage changes", "type": "flag_check"}
  ```
- **After:**
  ```json
  {"text": "Requires explicit git add before gt create/modify (never -a flag)", "type": "workflow_check"}
  ```
- **Current (eval id 1, expected_output):**
  ```
  "Uses gt create or gt modify with -a -m flags, --no-interactive, and includes co-authorship trailer. Checks git status first to determine whether to create or modify."
  ```
- **After:**
  ```
  "Uses gt create or gt modify with -m flag, --no-interactive, and includes co-authorship trailer. Requires explicit git add staging (never -a flag). Checks git status first to determine whether to create or modify."
  ```
- **Rationale:** Resolve inconsistency between eval assertion (expects `-a` flag) and the skill's staging rule (forbids `-a` flag), per Staging Rule Contract in structure.md.

### Step 1.6 — Validate graphite-evals.json is valid JSON

- **Action:** Run validation command
- **Command:** `python3 -m json.tool evals/graphite-evals.json > /dev/null`
- **Purpose:** Ensure the edits in steps 1.4 and 1.5 did not break JSON syntax.

### Step 1.7 — Validate SKILL.md frontmatter and body constraints

- **Action:** Run validation commands
- **Commands:**
  ```bash
  # Verify exactly 5 frontmatter fields
  head -8 .claude/skills/using-graphite-cli/SKILL.md | grep -cE '^(name|description|command|argument-hint|allowed-tools):'

  # Verify name field value
  head -8 .claude/skills/using-graphite-cli/SKILL.md | grep '^name: using-graphite-cli$'

  # Verify command field value
  head -8 .claude/skills/using-graphite-cli/SKILL.md | grep '^command: /using-graphite-cli$'

  # Count body lines (after frontmatter closing ---)
  awk '/^---$/{n++; if(n==2){start=NR; next}} start{count++} END{print count " body lines"}' .claude/skills/using-graphite-cli/SKILL.md

  # Verify Read instructions for both reference files
  grep -c 'references/command-reference.md' .claude/skills/using-graphite-cli/SKILL.md
  grep -c 'references/conflict-resolution.md' .claude/skills/using-graphite-cli/SKILL.md
  ```
- **Expected:** 5 frontmatter fields, name = `using-graphite-cli`, command = `/using-graphite-cli`, body < 500 lines, both Read instructions present.

### Step 1.8 — Validate skill content against acceptance criteria

- **Action:** Run validation commands
- **Commands:**
  ```bash
  # Verify single-commit-per-branch rule exists as hard directive
  grep -i 'single.commit.per.branch\|one commit per branch\|exactly one commit' .claude/skills/using-graphite-cli/SKILL.md

  # Verify Create -> Submit -> Modify -> Sync workflow documented
  grep -c 'gt create\|gt submit\|gt modify\|gt sync' .claude/skills/using-graphite-cli/SKILL.md

  # Verify --no-edit --publish --no-interactive submit defaults documented
  grep 'no-edit.*publish.*no-interactive\|submit.*--no-edit' .claude/skills/using-graphite-cli/SKILL.md

  # Verify prohibition on raw git branch/rebase
  grep -i 'git branch\|git rebase\|git commit --amend' .claude/skills/using-graphite-cli/SKILL.md

  # Verify navigation commands in command reference
  grep -c 'gt bu\|gt bd\|gt stack top\|gt log short' .claude/skills/using-graphite-cli/references/command-reference.md

  # Verify directionality conventions in command reference
  grep -i 'downstack.*trunk\|upstack.*away' .claude/skills/using-graphite-cli/references/command-reference.md

  # Verify gt continue in conflict resolution
  grep 'gt continue' .claude/skills/using-graphite-cli/references/conflict-resolution.md

  # Verify eval case 1 no longer asserts -a flag
  python3 -c "
import json
with open('evals/graphite-evals.json') as f:
    data = json.load(f)
assert data['skill_name'] == 'using-graphite-cli', f'skill_name is {data[\"skill_name\"]}'
case1 = [e for e in data['evals'] if e['id'] == 1][0]
for a in case1['assertions']:
    assert '-a or -u' not in a['text'], f'Found old assertion: {a[\"text\"]}'
print('All eval assertions valid')
"
  ```
- **Expected:** All checks pass; each grep returns at least one match.

### Step 1.9 — Invoke skill-creator to validate and refine

- **Action:** Invoke the `skill-creator` skill to validate the SKILL.md through its eval loop.
- **Purpose:** The acceptance criterion requires the skill be "built using the Anthropic skill builder skill." This step satisfies that requirement. The skill-creator will read the existing SKILL.md and run its validation/refinement process.
- **Note:** If skill-creator suggests changes, apply them to SKILL.md while preserving the 5-field frontmatter contract, the sub-500-line body constraint, and the staging rule. Do not accept changes that contradict the structure contracts.

---

### Verify — Slice 1 Checkpoint

Run all of the following. All must pass:

```bash
# 1. SKILL.md exists with correct frontmatter
test -f .claude/skills/using-graphite-cli/SKILL.md && echo "SKILL.md exists"

# 2. Both reference files exist
test -f .claude/skills/using-graphite-cli/references/command-reference.md && echo "command-reference.md exists"
test -f .claude/skills/using-graphite-cli/references/conflict-resolution.md && echo "conflict-resolution.md exists"

# 3. Frontmatter has exactly 5 fields (between the --- delimiters)
field_count=$(awk '/^---$/{n++; next} n==1 && /^[a-z]/' .claude/skills/using-graphite-cli/SKILL.md | wc -l)
test "$field_count" -eq 5 && echo "Frontmatter: 5 fields" || echo "FAIL: $field_count fields"

# 4. Body under 500 lines
body_lines=$(awk '/^---$/{n++; if(n==2){start=NR; next}} start{count++} END{print count+0}' .claude/skills/using-graphite-cli/SKILL.md)
test "$body_lines" -lt 500 && echo "Body: $body_lines lines (under 500)" || echo "FAIL: $body_lines lines"

# 5. Eval JSON is valid and assertions are correct
python3 -c "
import json, sys
with open('evals/graphite-evals.json') as f:
    data = json.load(f)
errors = []
if data['skill_name'] != 'using-graphite-cli':
    errors.append(f'skill_name={data[\"skill_name\"]}')
case1 = [e for e in data['evals'] if e['id'] == 1][0]
for a in case1['assertions']:
    if '-a or -u' in a['text']:
        errors.append(f'Old -a assertion still present')
if errors:
    print('FAIL: ' + '; '.join(errors))
    sys.exit(1)
print('Evals: all assertions valid')
"

# 6. Key content checks
grep -q 'single.commit\|one commit\|exactly one commit' .claude/skills/using-graphite-cli/SKILL.md && echo "Has single-commit rule" || echo "FAIL: missing single-commit rule"
grep -q 'gt continue' .claude/skills/using-graphite-cli/references/conflict-resolution.md && echo "Has gt continue rule" || echo "FAIL: missing gt continue"
grep -q 'gt bu' .claude/skills/using-graphite-cli/references/command-reference.md && echo "Has navigation commands" || echo "FAIL: missing navigation"
```

**All 6 checks must print success messages. Any FAIL line means the slice is incomplete.**

---

## Rollback Notes

No database migrations, infrastructure config changes, or destructive operations in this slice. All changes are new file creation plus one eval JSON edit. Rollback is:

```bash
rm -rf .claude/skills/using-graphite-cli/
git checkout -- evals/graphite-evals.json
```

---

## Step Count Summary

| Slice | Steps | Cumulative |
|---|---|---|
| Slice 1 | 9 | 9 |

**Total: 9 steps (well under 100-step limit)**
