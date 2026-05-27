# Research — Create a new agent skill called using graphite cli

**Ticket:** RUS-6
**Generated:** 2026-05-27T12:45:00Z
**Status:** complete

---

## Data Flow

### Q1: How does the existing `skill-creator` skill validate that a generated `SKILL.md` conforms to the agentskills.io frontmatter specification?

The validation is implemented in `/home/vscode/.claude/skills/skill-creator/scripts/quick_validate.py`. It performs the following checks on the YAML frontmatter:

- Must start with `---` delimiters (lines 23-29)
- Allowed properties: `name`, `description`, `license`, `allowed-tools`, `metadata`, `compatibility` (line 42)
- Name must be a string, lowercase kebab-case (`^[a-z0-9-]+$`), cannot start/end with hyphen or contain consecutive hyphens (lines 64-68)
- Name max 64 characters (lines 69-71)
- Description must be a string, no angle brackets (`<` or `>`) (lines 79-81)
- Description max 1024 characters (lines 82-84)
- Compatibility (if present) max 500 characters (lines 86-92)

Evidence from validation script at `/home/vscode/.claude/skills/skill-creator/scripts/quick_validate.py`:

```python
ALLOWED_PROPERTIES = {'name', 'description', 'license', 'allowed-tools', 'metadata', 'compatibility'}
unexpected_keys = set(frontmatter.keys()) - ALLOWED_PROPERTIES
if unexpected_keys:
    return False, f"Unexpected key(s) in SKILL.md frontmatter: {', '.join(sorted(unexpected_keys))}"
```

### Q2: Where does the `skill-creator` skill write its output, and how does it reference the `references/`, `scripts/`, and `assets/` subdirectories?

Skill-creator writes output into a workspace directory pattern: `<skill-name>-workspace/` containing iteration subdirectories (`iteration-1/`, `iteration-2/`, etc.), each with eval subdirectories (`eval-0/`, `eval-1/`, etc.) containing `with_skill/` and `without_skill/` subdirectories for comparative testing.

The skill structure spec from `/home/vscode/.claude/skills/skill-creator/SKILL.md` defines:

```
skill-name/
  SKILL.md          # Required - agent prompt
  scripts/          # Optional - shell/Python scripts
  references/       # Optional - reference documents
  assets/           # Optional - other resources
```

The skill-creator skill itself uses this pattern. Its own directory at `/home/vscode/.claude/skills/skill-creator/` contains:
- `SKILL.md` (486 lines)
- `scripts/quick_validate.py` (validation script)
- `references/schemas.md` (JSON schema definitions)
- `eval-viewer/` (review tools: `generate_review.py`, `viewer.html`)

### Q3: What is the existing `using-graphite-cli` skill's current `SKILL.md` content, and how does it structure reference material?

The existing skill is at `/home/vscode/.claude/skills/using-graphite-cli/SKILL.md` (387 lines). It is a single self-contained file with no bundled resource subdirectories (no `references/`, `scripts/`, or `assets/`).

Frontmatter:
```yaml
---
name: using-graphite-cli
description: "Use for ANY request involving version control, commits, branches, diffs, or pull requests..."
---
```

Body sections: Non-interactive execution, Co-authorship, Core workflows (determine state, create branch, modify branch, submit PRs, sync, restack, navigate), Branch management (delete, rename, track/untrack, fold, squash, split, pop), Stack reorganization, Collaboration, Conflict resolution, Recovery, Merging, Viewing PR info, Aliases table, Terminology.

All 387 lines are in one file with no hierarchical progressive disclosure via bundled resources.

### Q4: How does the `qrspi-worktree` skill encode its DAG and session state, and could the graphite skill use a similar pattern for tracking stack state?

The `qrspi-worktree` skill at `/workspaces/qrspi/.worktrees/RUS-6/.claude/skills/qrspi-worktree/SKILL.md` is minimal (24 lines) with no DAG encoding:

```yaml
---
name: qrspi-worktree
description: "Manage worktree-based parallel development for QRSPI tickets."
command: /qrspi-worktree
argument-hint: <ticket-id>
allowed-tools: Read
---
```

It does NOT encode a DAG or session state. It is simply a frontmatter directive that maps the `/qrspi-worktree` slash command to the skill file.

**Relevance to graphite skill:** The graphite skill could potentially benefit from a similar lightweight approach for its stack state tracking, but Graphite has its own state system (event logs and snapshots). The skill's role would be instructional (telling the agent how to use `gt` commands) rather than state-tracking. A DAG pattern is not needed for the graphite skill since Graphite CLI handles stack ordering internally.

---

## API Surface

### Q5: Which Graphite CLI commands need to be represented in the skill versus left as references, given the agentskills.io convention of embedding core workflow directly in `SKILL.md`?

Based on analysis of the existing skill at `/home/vscode/.claude/skills/using-graphite-cli/SKILL.md`, the core commands embedded in the skill body are:

| Command | Used in skill body | Non-interactive flags |
|---------|-------------------|----------------------|
| `gt create` | Yes | `-a` or `-u`, `-m "message"` |
| `gt modify` | Yes | `-c`, `-a` or `-u`, `-m "message"` |
| `gt submit` | Yes | `--no-edit` |
| `gt sync` | Yes | `--force`, `--delete-all` |
| `gt undo` | Yes | `--force` |
| `gt abort` | Yes | `--force` |
| `gt track` | Yes | `--parent <branch>` |
| `gt untrack` | Yes | `--force` |
| `gt delete` | Yes | `--force` (after confirmation) |
| `gt absorb` | Yes | `--force` |
| `gt squash` | Yes | `-m "message"`, `--no-edit` |
| `gt split` | Yes | `--by-file <pathspec>` only |
| `gt move` | Yes (in workflow section) | `--onto <branch>` |
| `gt log` / `gt log short` | Yes | Standard |
| `gt up` / `gt down` | Yes | Standard |
| `gt restack` | Yes | Standard |
| `gt checkout` | Prohibited (requires branch arg) | N/A |
| `gt reorder` | Prohibited (interactive only) | N/A |
| `gt split --by-commit` | Prohibited (interactive only) | N/A |
| `gt split --by-hunk` | Prohibited (interactive only) | N/A |

Commands left as references (aliases): `gt aliases` file defines `ls -> log short`, `ll -> log long`, `ss -> submit --stack`. The skill includes these in an aliases table but instructs agents to use the full command names.

**Prohibited commands** from the existing skill (body lines 34-36):
```
gt reorder, gt split --by-commit, gt split --by-hunk, gt config, gt demo,
gt checkout without a branch name argument.
```

### Q6: How does the skill distinguish between commands an agent should invoke directly (e.g., `gt create`) and commands that are prohibitions (e.g., `git rebase` on tracked branches)?

The existing skill uses two distinct mechanisms:

1. **Explicit prohibition listing** in the Non-interactive execution section (lines 34-36):
   ```
   **Commands that cannot be used** (they require interactive input with no override):
   `gt reorder`, `gt split --by-commit`, `gt split --by-hunk`, `gt config`, `gt demo`,
   `gt checkout` without a branch name argument.
   ```

2. **Category heading** separating core workflows from prohibitions. The skill also prohibits raw `git` commands entirely in its opening paragraph (lines 8-11):
   ```
   All version control in this environment uses the Graphite CLI (`gt`), which manages
   stacked pull requests on top of Git. Every git or gt operation — including read-only
   ones like status, diff, and log — must go through the patterns in this skill. Never
   run raw git or gt commands ad-hoc.
   ```

The skill also encodes prohibitions in workflow sections by only showing the approved command pattern. For example, the "modify branch" section shows `gt modify` and never mentions `git commit --amend` as an alternative.

---

## State Management

### Q7: Where does Graphite store its repo-level config (trunk branch, remote) inside `.git/`, and what file names are used?

Graphite stores state in the following locations within the `.git/` directory:

**Repo-level (shared across all worktrees):**
- `.git/.gt/` — Contains `event_log` (history of mutations) and `snapshots/` (directory with 125 snapshot files)
- `.git/rr-cache/<snapshot-id>/` — Rebase-restore cache used by Graphite for branch tracking. Contains `preimage`, `thisimage`, `postimage` files. Example snapshot ID: `81bd9237e727fba5eb454b7a2a338df8b513bc66`

**Per-worktree:**
- `.git/worktrees/<name>/.gt/` — Contains `event_log` (worktree-specific mutations only)
- `.git/worktrees/<name>/.gtlocalprinfo` — Local PR info file, format: `{"localPrInfo": []}`

The repo-level `event_log` at `/workspaces/qrspi/.git/.gt/event_log` stores all mutation events. The worktree-level `event_log` at `/workspaces/qrspi/.git/worktrees/RUS-6/.gt/event_log` stores only events for that worktree.

Example event structure from event_log:
```json
{
  "id": "a83dc19d-c07d-4f80-a5a2-dbe62997f587",
  "canonicalName": "modify",
  "userCommand": "modify -c --no-interactive -m \"...\"",
  "startingSnapshot": { "sha": "c4ea6f9c475633a4156d6a66b3350eee025d35a5" },
  "endingSnapshot": { "sha": "41a0c3c19ee1694c82a6790632d2d7b4375af953" },
  "mutatedBranches": ["RUS-6/planning", "main"]
}
```

**Note:** Graphite does not appear to store trunk branch or remote configuration in `.git/` files accessible via filesystem. This configuration is likely managed through `gt config` (interactive) or remote Git configuration (`.git/config`). The `gt config --help` command exists but has no non-interactive subcommands visible in CLI help, suggesting it is purely interactive.

### Q8: What files exist in `~/.config/graphite/` and what is the schema of the user-level config?

Directory listing of `/home/vscode/.config/graphite/`:
```
aliases          (441 bytes)
user_config      (112 bytes)
```

**`user_config` contents:**
```json
{
  "updateAutomatically": true,
  "authToken": "6snIQQbZIkpVvTWVTTEWTlW6yTqqrSkGDVR49Bf4HexqulYBjV4bIQoBnLUZ"
}
```

Schema: Two fields — `updateAutomatically` (boolean) and `authToken` (string). The token is used for authenticating with Graphite's remote service.

**`aliases` contents** (this file was previously read):
```
ls log short
ll log long
ss submit --stack
```

Format: Simple `alias target command` lines. No header or section markers.

---

## Edge Cases

### Q9: When an agent runs `gt modify --all` and multiple descendants have uncommitted changes, what does Graphite do and what does the skill need to warn the agent about?

From `gt modify` help output: "Modify the current branch by amending its commit or creating a new commit. Automatically restacks descendants."

The `--all` flag (`-a`) stages all changes before committing. When descendants exist, Graphite will automatically rebase them on top of the modified current branch.

**What the skill needs to warn about:** If descendants have uncommitted local changes, the rebase during restack will encounter conflicts. The skill should warn that the agent should commit or stash descendant changes before modifying a branch with descendants. The `gt modify` command does NOT have a `--no-interactive` bypass for rebase conflicts — conflicts would require manual resolution or `gt sync --force` to resolve.

No explicit documentation on this edge case was found in the existing skill. This is an area where the new skill should add guidance.

### Q10: What happens when `gt sync` encounters a branch that was merged remotely but the local Graphite metadata does not reflect that merge?

From `gt sync` help output: "Sync all branches with remote, prompting to delete any branches for PRs that have been merged or closed. Restacks all branches in your repository that can be restacked without conflicts. If trunk cannot be fast-forwarded to match remote, overwrites trunk with the remote version."

With `--force --delete-all --no-interactive`, `gt sync` will:
1. Force-overwrite trunk with remote (no prompt)
2. Delete all merged/closed branches (no prompt)
3. Restack branches that can be restacked without conflicts

**Implicit contract:** Branches that cannot be restacked without conflicts are left in their current state but not deleted. The agent needs to check `gt log` after sync to identify which branches were affected.

---

## Testing

### Q11: Does the project have an eval harness or test script for validating generated skills, and what assertions does it make on `SKILL.md`?

Yes. Two eval suites exist:

**1. Project-level eval suite** at `/workspaces/qrspi/.worktrees/RUS-6/evals/suite.json` (780 lines, 15 test cases). Tests all QRSPI phases including code review, research, design, structure, plan, worktree, implement, and PR phases. Key assertions relevant to skills:
- Code snippets must be under 20 lines
- NOT FOUND handling when questions cannot be answered
- Citation compliance (file paths must be cited)

**2. Graphite-specific eval suite** at `/workspaces/qrspi/.worktrees/RUS-6/evals/graphite-evals.json` (68 lines, 5 evals). Each eval has:
- `id`: Integer
- `prompt`: User prompt to test
- `expected_output`: Description of expected agent behavior
- `files`: Optional input files
- `assertions`: Array of `{text, type}` objects

Assertion types: `command_check`, `flag_check`, `content_check`, `workflow_check`, `safety_check`.

Evidence from `graphite-evals.json`:
```json
{"text": "Uses gt create or gt modify (not raw git commit)", "type": "command_check"},
{"text": "Includes --no-interactive flag", "type": "flag_check"},
{"text": "Includes Co-Authored-By trailer in the commit message", "type": "content_check"},
```

**3. Skill-creator validation script** at `/home/vscode/.claude/skills/skill-creator/scripts/quick_validate.py` validates SKILL.md frontmatter conformance (see Q1).

### Q12: How should the generated skill's correctness be verified — by running the `skill-creator` eval, by manual review, or through some other mechanism?

Three verification mechanisms are available:

1. **`quick_validate.py`** — Run `python3 quick_validate.py <skill-directory>` to validate frontmatter conformance (required fields, allowed properties, naming conventions, length limits). This is a programmatic check.

2. **`graphite-evals.json`** — Run the 5 evals against the generated skill. Each eval tests a specific workflow scenario (commit, push, show stack, move branch, sync). Assertions check for correct command usage, required flags (`--no-interactive`), and safety patterns. This verifies the skill produces correct agent behavior.

3. **Manual review** — Compare the generated skill against the existing `/home/vscode/.claude/skills/using-graphite-cli/SKILL.md` to ensure coverage of all workflows, edge cases, and prohibitions. Also compare against `gt --help --all` output to verify no commands are missing or incorrect.

**Recommended approach:** Run `quick_validate.py` first for frontmatter, then run the graphite evals for behavioral correctness, then perform manual review for completeness.

---

## Observability

### Q13: How does the Linear MCP server currently interact with Graphite PRs (via `list_diffs`, `get_diff`, `get_diff_threads`), and does the agent skill need to mirror or replace any of those capabilities?

The Linear MCP server (`linear-russelltsherman`) exposes Graphite-related tools:
- `list_diffs` — Lists Graphite diff pull requests visible to the authenticated user. Parameters: `owner`, `repo`, `query`, `status`, `limit`, `cursor`, `orderBy`.
- `get_diff` — Exact lookup for a Linear diff by URL, ID, slug, or PR number.
- `get_diff_threads` — Lookup diff threads with optional `resolved` filter and `threadId` for specific thread retrieval.

These tools allow Linear issues to link to Graphite-managed GitHub PRs and display review threads inline in Linear.

**Does the agent skill need to mirror this?** No. The Linear MCP tools are server-side integrations that work independently of the agent's workflow. The `using-graphite-cli` skill governs how the agent interacts with Graphite CLI (`gt`) for creating, modifying, and managing stacked branches and PRs. The Linear MCP tools are a separate integration layer for viewing PR information within Linear. The skill does not need to cover these MCP tools — they are consumed by the Linear server, not by the agent's `gt` workflow.

---

## Discovered Patterns

1. **Non-interactive flag convention**: Every `gt` command used by agents requires `--no-interactive`. Additional flags vary by command but follow a pattern of `--force` for destructive operations, `-m "message"` for commit messages, and `-a`/`-u` for staging.

2. **Co-authorship trailer**: Every commit message must include `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`. Passed via heredoc syntax.

3. **State storage hierarchy**: Graphite uses a two-level event log system (repo-level `.git/.gt/` and worktree-level `.git/worktrees/<name>/.gt/`) plus snapshot storage in `.git/rr-cache/`.

4. **Config file locations**: User config at `~/.config/graphite/user_config` (JSON), aliases at `~/.config/graphite/aliases` (plain text, one alias per line).

5. **Eval assertion taxonomy**: Five assertion types: `command_check` (correct tool), `flag_check` (required flags), `content_check` (message/format compliance), `workflow_check` (correct sequence), `safety_check` (no destructive ops without confirmation).

6. **Skill structure pattern**: Skills follow a progressive disclosure model — frontmatter (~100 words), SKILL.md body (<500 lines), bundled resources (unlimited). The existing graphite skill packs everything into a single SKILL.md with no bundled resources.

---

## Inconsistencies

1. **`gt checkout` prohibition vs. help text**: The skill lists `gt checkout` without a branch name as prohibited, but `gt checkout` IS a valid command that takes a branch name argument. The prohibition is specifically for calling it without an argument (which triggers interactive selection). The skill should clarify this rather than listing it as a blanket prohibition.

2. **`gt sync` behavior with `--force`**: The existing skill shows `gt sync --force --delete-all --no-interactive` but the command help shows `--force` only suppresses confirmation prompts — it does NOT suppress the interactive branch deletion prompt. The `--delete-all` flag handles non-interactive deletion. The `--force` flag is primarily for trunk overwrite confirmation.

3. **Stage-all vs. staging-specific rule conflict**: The skill allows `-a` (stage all) in its flag table, but the QRSPI work skill at `/workspaces/qrspi/.worktrees/RUS-6/.claude/skills/qrspi-work/SKILL.md` explicitly states "NEVER use `-a` flag, always stage specific files." This conflict should be resolved — the graphite skill should either prohibit `-a` or document when `-a` is appropriate.

4. **Missing command coverage**: The skill does not cover `gt absorb`, `gt pop`, `gt rename`, or `gt track`/`gt untrack` in its workflow sections, though these commands appear in the flag table. They are mentioned only by name, not with usage examples.

5. **`gt restack` flag table vs. help**: The flag table lists `gt restack` with no flags, but `gt restack --help` is not shown in the help output. The command exists but its non-interactive behavior is not documented.
