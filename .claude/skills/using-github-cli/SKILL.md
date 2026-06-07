---
name: using-github-cli
description: "Opinionated, non-interactive guidance for the GitHub CLI (`gh`) — read/metadata queries, scripting with `--json`/`--jq`, GraphQL, automation/CI, and extensions. Use whenever the user wants to inspect GitHub state (PRs, issues, runs, releases, repo metadata), script `gh` in a pipeline or CI job, query the REST or GraphQL API, or asks how to do something with `gh`. Trigger even when the user only describes the goal (\"what checks failed on that PR\", \"list open issues assigned to me\", \"pull the run logs\") without naming `gh`. This skill covers READS only — defer commits, branches, PR creation/merging, and any history mutation to the orchestration layer / the `using-graphite-cli` skill."
command: /using-github-cli
argument-hint: "[topic]"
allowed-tools: Read, Glob, Grep, Bash(gh auth status:*), Bash(gh api:*), Bash(gh repo view:*), Bash(gh repo list:*), Bash(gh pr view:*), Bash(gh pr list:*), Bash(gh pr checks:*), Bash(gh pr diff:*), Bash(gh issue view:*), Bash(gh issue list:*), Bash(gh run view:*), Bash(gh run list:*), Bash(gh release view:*), Bash(gh release list:*), Bash(gh search:*), Bash(gh label list:*), Bash(gh cache list:*)
---

# Using the GitHub CLI (`gh`)

`gh` is the fastest way for an agent to read GitHub state and feed it into a
pipeline. The trap is that `gh`'s defaults are tuned for a human at a terminal:
it paginates through a pager, prompts interactively, and prints decorated,
unstable text. Inside an agent or a CI job those defaults hang or produce output
you can't parse. This skill makes `gh` behave deterministically and stay inside
a read-only capability boundary.

## Capability boundary — reads here, mutations elsewhere

This skill is scoped to **reads and metadata**: viewing and listing PRs, issues,
runs, releases, repos, labels; querying the REST/GraphQL API with safe verbs;
checking auth. That scoping lives in `allowed-tools` above, which enumerates
read/metadata subcommands rather than granting blanket `Bash(gh:*)` — a blanket
grant would silently also permit `gh pr merge`, `gh pr create`, `gh repo delete`,
and other irreversible operations.

**Do not perform mutating git or PR operations from this skill.** That includes
committing, pushing, branching, creating/editing/merging PRs or issues, and any
history rewrite. Those belong to the orchestration layer. In this repo the
single sanctioned path for version-control and PR mutations is the
**`using-graphite-cli`** skill (`gt`) — see the project's git-delegation rule.
Routing every mutation through one layer keeps the stack consistent and prevents
two tools from fighting over branch state.

If a task seems to need a write (e.g. "merge this PR"), stop and hand it to the
orchestrator / `using-graphite-cli` rather than reaching for `gh pr merge` here.

## Non-interactive defaults (always apply in agent/CI contexts)

A human can dismiss a pager or answer a prompt; an agent cannot. Apply these so
`gh` never blocks and never emits decoration you have to strip:

- **Kill the pager.** `gh` pipes long output through `less` by default, which
  hangs a non-interactive shell waiting for `q`. Use `--no-pager` per command,
  or set `GH_PAGER=""` (equivalently `PAGER=cat`) for the whole session.
- **Disable prompts.** Set `GH_PROMPT_DISABLED=1` so `gh` errors out fast
  instead of waiting on stdin for a confirmation that will never come.
- **Ask for structured output.** Add `--json <fields>` and shape it with
  `--jq` so you parse stable JSON, not human-formatted text whose layout can
  change between `gh` versions. List the exact fields you need; `--json` with no
  fields prints the available field names.
- **Drop color/ANSI.** `NO_COLOR=1` (or `CLICOLOR=0`) keeps escape codes out of
  captured output.

A reusable preamble for a scripted session:

```bash
export GH_PAGER="" GH_PROMPT_DISABLED=1 NO_COLOR=1
```

### Read structured data, then branch on it

Prefer `--json`/`--jq` over grepping decorated text. Example — get the failing
check names for a PR and act on the count:

```bash
failed=$(gh pr checks 123 --json name,state \
  --jq '[.[] | select(.state=="FAILURE") | .name] | join(", ")')
if [ -n "$failed" ]; then
  echo "Failing checks: $failed"
fi
```

### Use exit codes, don't parse prose

`gh` returns non-zero on failure (no such resource, auth error, API error), and
some subcommands encode meaning in the exit code — e.g. `gh pr checks` exits
non-zero while checks are pending/failing and `0` when all pass. Drive control
flow off `$?`, not off matching strings in the human output:

```bash
if gh pr checks 123 --no-pager >/dev/null 2>&1; then
  echo "all checks green"
else
  echo "checks not green (pending or failing)"
fi
```

## Authentication

Verify before you query so failures are explicit rather than mysterious empty
output:

```bash
gh auth status        # confirms you are logged in and shows the active account/scopes
```

For an interactive human setup, `gh auth login` walks through browser/device
auth. That is a setup step, not something an agent runs mid-task.

### `GH_TOKEN` in CI / external contexts — legitimate

In CI and other non-interactive external contexts, authenticate by exporting a
token: `gh` reads **`GH_TOKEN`** (or `GITHUB_TOKEN`) from the environment. On
GitHub Actions the workflow's built-in `GITHUB_TOKEN` is the standard mechanism:

```yaml
env:
  GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

This is the supported, documented way `gh` authenticates outside an interactive
login — use it freely in CI.

> Note the distinction: passing a token to `gh` for authentication in an
> external context is normal and expected. That is **not** the same as routing
> this harness's own configuration or behavior through ad-hoc environment
> variables to bypass settings — that workaround pattern is forbidden in this
> repo. `GH_TOKEN` here is solely `gh`'s auth credential, nothing more.

## Opinionated defaults for repository hygiene

When you *do* surface a recommendation to a human (this skill won't execute the
mutation — see the capability boundary), recommend these defaults, which keep
history readable:

- **Squash merge.** Collapse a PR's work-in-progress commits into one coherent
  commit on the base branch, so history reads as one logical change per PR.
- **Delete the branch after merge.** Removing the merged head branch keeps the
  branch list to active work only.
- **Author bodies with a HEREDOC.** When a body string is needed (PR/issue/
  release notes), build it with a quoted heredoc so multi-line Markdown survives
  intact instead of being mangled by shell quoting:

  ```bash
  body=$(cat <<'EOF'
  ## Summary
  - first point
  - second point
  EOF
  )
  ```

  In this repo, remember the actual PR/issue creation is performed by the
  orchestration layer / `using-graphite-cli`, not by `gh` from this skill.

## Going deeper — reference files

This SKILL.md stays lean on purpose. Load the matching reference file (paths are
relative to this skill directory) when a task needs that depth:

- **`references/gh-api.md`** — advanced `gh api` REST patterns: pagination
  (`--paginate`), `--jq` shaping, `-X`/`-f`/`-F` request fields, `--cache`,
  custom `--header`, and read-vs-mutation guidance.
- **`references/graphql.md`** — `gh api graphql` query examples, including
  multi-resource joins the REST endpoints can't express in one call, variables,
  and cursor pagination.
- **`references/automation.md`** — non-interactive and CI recipes: the env-var
  preamble, `GH_TOKEN`/`GITHUB_TOKEN` auth, scripting patterns, and exit-code
  driven control flow.
- **`references/extensions.md`** — useful `gh` extensions and alias
  recommendations (`gh extension`, `gh alias set`).
