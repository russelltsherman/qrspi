# Automation & CI recipes

This file collects the patterns that make `gh` reliable inside scripts, cron
jobs, and CI — environments with no human to dismiss a pager or answer a prompt.
It expands on the non-interactive defaults summarized in `SKILL.md`.

## Table of contents

- The session preamble
- Authentication in CI (`GH_TOKEN` / `GITHUB_TOKEN`)
- Structured output for parsing
- Exit-code driven control flow
- GitHub Actions example
- Rate limits

## The session preamble

Export these once so every subsequent `gh` call is non-interactive:

```bash
export GH_PAGER=""          # no pager — avoids hanging on `less`
export GH_PROMPT_DISABLED=1 # fail fast instead of waiting on stdin
export NO_COLOR=1           # no ANSI escapes in captured output
```

Per-command equivalents (when you can't set env): `--no-pager` and avoiding any
subcommand that would prompt.

## Authentication in CI

Outside an interactive `gh auth login`, `gh` authenticates from the environment:
it reads **`GH_TOKEN`**, falling back to **`GITHUB_TOKEN`**. This is the
supported mechanism for automation.

```bash
export GH_TOKEN="$MY_PAT"
gh auth status   # verify before doing real work
```

On GitHub Actions, wire the built-in token through `env`:

```yaml
env:
  GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

This is a legitimate, documented auth pattern for an external execution context.
It is distinct from — and must not be conflated with — routing this harness's own
configuration through ad-hoc env vars to dodge its settings, which is forbidden
in this repo. Here `GH_TOKEN` is purely `gh`'s credential.

## Structured output for parsing

Never scrape human-formatted output in a script; request JSON and filter it:

```bash
# numbers of open PRs authored by @me
gh pr list --state open --author '@me' --json number --jq '.[].number'

# latest run conclusion for a workflow
gh run list --workflow ci.yml --limit 1 --json conclusion --jq '.[0].conclusion'
```

Run `gh <command> --json` with no field list to discover available fields.

## Exit-code driven control flow

`gh` returns non-zero on failure; some commands encode status in the exit code.
Branch on `$?`, not on string matches:

```bash
if gh pr checks "$PR" --no-pager >/dev/null 2>&1; then
  echo "checks green"; deploy
else
  echo "checks not green"; exit 1
fi
```

`gh pr checks` exits non-zero while checks are pending or failing and `0` when
all required checks pass — ideal as a CI gate.

## GitHub Actions example

A job step that fails the build unless a PR is approved and green:

```yaml
- name: Gate on review + checks
  env:
    GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    GH_PAGER: ""
    GH_PROMPT_DISABLED: "1"
  run: |
    decision=$(gh pr view "$PR" --json reviewDecision --jq '.reviewDecision')
    [ "$decision" = "APPROVED" ] || { echo "not approved"; exit 1; }
    gh pr checks "$PR" || { echo "checks not green"; exit 1; }
```

## Rate limits

Check remaining quota and cache reads to stay under it:

```bash
gh api rate_limit --jq '.resources.core'
gh api repos/{owner}/{repo} --cache 10m --jq '.default_branch'
```

Remember: everything in this file is read/metadata. Mutating operations (merge,
create, push) are out of scope — route them through the orchestration layer /
`using-graphite-cli` as described in `SKILL.md`.
