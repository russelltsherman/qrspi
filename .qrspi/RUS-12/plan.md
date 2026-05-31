# Implementation Plan — Create a new agent skill called using github cli

**Structure basis:** structure.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft
**Total steps:** 18

## Slice 1: Author the SKILL.md and references

### Setup

1. ✨ Create directory `.claude/skills/using-github-cli/` (mkdir -p).
2. ✨ Create directory `.claude/skills/using-github-cli/references/` (mkdir -p).

### Core Logic

3. ✨ Create `.claude/skills/using-github-cli/SKILL.md` with frontmatter (ref: structure.md §Contracts):
   - `name: using-github-cli`
   - `description:` high-recall string enumerating gh verbs and literal trigger phrases like "create a PR", "open an issue", "list runs", "merge with squash". Must mention `gh` and "GitHub CLI" explicitly to disambiguate from non-CLI tasks.
   - `command: /using-github-cli`
   - `argument-hint: <gh subcommand or task description>`
   - `allowed-tools: Read, Write, Edit, Bash, Glob, Grep`
   - Body sections (level-2 headings, in order): Role statement, Authentication, Defaults, PR Workflows, Code Review, Issue Management, Releases & Versioning, GitHub Actions, API Queries (`gh api`), Repository Management, Scripting & Automation, Boundary with git/graphite, Hard Stop on Auth Errors, References.

4. ✨ In `SKILL.md` Authentication section, document:
   - First-command preflight: `gh auth status` (HARD STOP on failure — print verbatim error, exit; ref: research Q8).
   - CI/automation: `GH_TOKEN` env var.
   - Workstation: `gh auth login`, `gh auth switch`.
   - Out-of-checkout: `GH_REPO` env var or `-R owner/repo` flag.

5. ✨ In `SKILL.md` Defaults section, encode opinionated defaults (ref: ticket acceptance criteria):
   - Default merge: `gh pr merge --squash --delete-branch`.
   - Default body formatting: HEREDOC with single-quoted delimiter (`$(cat <<'EOF' ... EOF)`).
   - Default parsing: `--json <fields> --jq '<filter>'`.
   - Non-interactive: `GH_PAGER=""`, `--no-pager`, `GH_PROMPT_DISABLED=1`.

6. ✨ In `SKILL.md` PR Workflows section, encode the rules from the ticket: `gh pr create --title --body` (both required), title ≤ 70 chars, `--draft` + `gh pr ready`, `gh pr checks` before merge, `gh pr edit --add-label/--add-reviewer/--add-assignee`.

7. ✨ In `SKILL.md` Code Review section, encode the rules from the ticket: `gh pr list --search "review-requested:@me"`, `gh pr review --approve/--request-changes/--comment`, `gh pr diff`, inline comments via `gh api`, `gh pr checkout <number>`.

8. ✨ In `SKILL.md` Issue Management, Releases, GitHub Actions, API Queries, Repository Management sections, encode the ticket's bullet rules verbatim where they are commands, paraphrased where they are guidance. Keep each section to ~10 lines or fewer. Point depth to `references/`.

9. ✨ In `SKILL.md` Scripting & Automation section, summarize the non-interactive patterns and link to `references/automation.md`. Keep summary under 20 lines.

10. ✨ In `SKILL.md` Boundary with git/graphite section, write the deferral rule: branch/commit operations belong to the using-graphite-cli skill; `gh` handles GitHub-side state (PRs, issues, releases, runs).

11. ✨ Create `.claude/skills/using-github-cli/references/gh-api.md` with:
    - REST verbs (`-X PATCH/PUT/DELETE`).
    - `--paginate` for list endpoints.
    - `--cache <duration>` for repeated reads.
    - Custom headers via `--header`.
    - Batch mutations via `gh api --paginate | gh api`.
    - Worked examples for: setting labels, adding reviewers, listing run logs.

12. ✨ Create `.claude/skills/using-github-cli/references/graphql.md` with:
    - Basic `gh api graphql -f query='...'` shape.
    - 2–3 worked examples: PR with reviews+checks+commits in one query; cross-repo issue search; user activity.
    - Pagination cursor pattern.

13. ✨ Create `.claude/skills/using-github-cli/references/automation.md` with:
    - CI auth recipe (`GH_TOKEN` from secret, `gh auth status` sanity check).
    - `gh status` for personal dashboard.
    - Alias setup (`gh alias set prc 'pr create --fill'`).
    - Exit-code-driven shell patterns.
    - Pre-existing `gh pr create --fill` in PR automation.

14. ✨ Create `.claude/skills/using-github-cli/references/extensions.md` with:
    - The "prefer built-in" rule.
    - Curated list: `gh-dash`, `gh-poi`, `gh-copilot` (with one-line justification each).
    - `gh extension install/list/remove` cookbook.
    - Note that extensions may mutate the user environment; document the install consent.

### Tests

(No automated tests in this slice — slice 2 adds eval coverage. Manual verification below.)

### Verify Slice 1

15. **Checkpoint:** run from the worktree root:
    - [ ] `head -10 .claude/skills/using-github-cli/SKILL.md` shows frontmatter with `name`, `description`, `command`, `argument-hint`, `allowed-tools`.
    - [ ] `wc -l .claude/skills/using-github-cli/SKILL.md` ≤ 500.
    - [ ] `grep -c '^## ' .claude/skills/using-github-cli/SKILL.md` ≥ 12.
    - [ ] All four reference files exist and are non-empty.
    - [ ] `grep -q 'gh auth status' .claude/skills/using-github-cli/SKILL.md`.
    - [ ] `grep -qi 'HARD STOP\|hard-stop' .claude/skills/using-github-cli/SKILL.md`.
    - [ ] `grep -q 'GH_TOKEN' .claude/skills/using-github-cli/SKILL.md`.
    - [ ] `grep -qi 'squash' .claude/skills/using-github-cli/SKILL.md`.
    - [ ] `grep -q '\-\-jq' .claude/skills/using-github-cli/SKILL.md`.
    - [ ] `grep -q "cat <<'EOF'\|HEREDOC" .claude/skills/using-github-cli/SKILL.md`.

---

## Slice 2: Add eval coverage

### Setup

16. ✨ Read `evals/graphite-evals.json` for shape reference (do not modify it).

### Core Logic

17. ✨ Create `evals/gh-evals.json` with at minimum:
    - `name: "gh-cli-skill-evals"`, `version: "0.1.0"`, `description`.
    - One case `case_001`: `name: "skill_structure"`, programmatic assertions checking:
      - `.claude/skills/using-github-cli/SKILL.md` exists.
      - SKILL.md line count ≤ 500.
      - SKILL.md section count (level-2 headings) ≥ 12.
      - Each reference file exists and is non-empty.
      - SKILL.md contains the strings: `gh auth status`, `GH_TOKEN`, `HARD STOP` (case-insensitive), `--squash`, `--jq`.
    - Assertion shape follows the schema in `evals/suite.json` (ref: research Q10). If the existing schema does not natively support `grep`-style content checks, model the assertions as `programmatic` with a custom `check` string and add a TODO comment noting that `scripts/grade.py` may need to be extended (out of scope to extend in this ticket — note the gap explicitly).

### Tests

(No automated tests — the eval file IS the test artifact for the skill.)

### Verify Slice 2

18. **Checkpoint:** run from the worktree root:
    - [ ] `python3 -c "import json; json.load(open('evals/gh-evals.json'))"` succeeds.
    - [ ] `python3 -c "import json; d=json.load(open('evals/gh-evals.json')); assert len(d['cases']) >= 1; assert all(len(c['assertions']) >= 1 for c in d['cases'])"` succeeds.
    - [ ] `grep -q 'using-github-cli' evals/gh-evals.json`.

---

## Rollback Notes

- Step 3: If frontmatter changes block triggering, `git checkout .claude/skills/using-github-cli/SKILL.md` reverts to the last commit. The whole skill is additive — no existing skill is touched — so a full revert of slice 1 is `git rm -r .claude/skills/using-github-cli/`.
- Step 11–14: Reference files are additive; deletion is safe. Re-author rather than partial-rollback within a file.
- Step 17: If `evals/gh-evals.json` causes the harness to break, delete the file. `evals/suite.json` and `evals/graphite-evals.json` are independent and remain functional.
