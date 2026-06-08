# Extensions & aliases

`gh` is extensible two ways: **aliases** (shorthand for command + flag
combinations you repeat) and **extensions** (installable subcommands). Both cut
down the typing and standardize how a team drives `gh`.

## Table of contents

- Aliases
- Managing extensions
- Useful extensions
- A note on scope

## Aliases

`gh alias set` saves a named shortcut. Great for baking in the non-interactive
flags and `--json`/`--jq` shapes you use constantly:

```bash
# open PRs assigned to me, as a clean table-ish list
gh alias set mine 'pr list --author @me --state open --json number,title --jq ".[] | \"\(.number)\t\(.title)\""'

# expand a shell pipeline alias with --shell / -s
gh alias set failing -s 'gh pr checks "$1" --json name,state --jq ".[] | select(.state==\"FAILURE\") | .name"'
```

Invoke with `gh mine` / `gh failing 123`. List and remove with
`gh alias list` and `gh alias delete <name>`.

## Managing extensions

```bash
gh extension list                       # what's installed
gh extension install owner/gh-foo       # add one
gh extension upgrade --all              # keep them current
gh extension remove gh-foo              # uninstall
```

Treat third-party extensions like any dependency: install only ones you trust,
since they run with your `gh` credentials.

## Useful extensions

- **`dlvhdr/gh-dash`** — a configurable TUI dashboard of PRs and issues across
  repos; handy for a human triaging review queues (interactive, so not for
  scripts).
- **`github/gh-copilot`** — `gh copilot suggest`/`explain` for command help.
- **`actions/gh-actions-cache`** — list and manage Actions caches beyond the
  built-in `gh cache` commands.
- **`gh-poi`** (`seachicken/gh-poi`) — prunes local branches whose PRs have
  merged; useful for hygiene, but note any branch deletion is a mutation —
  surface it to the human / orchestration layer rather than running it from this
  read-scoped skill.

## A note on scope

Extensions can do anything `gh` can, including writes. This skill stays
read-only (see the capability boundary in `SKILL.md`); recommend extensions
freely for inspection and human convenience, but keep mutating actions in the
orchestration layer / `using-graphite-cli`.
