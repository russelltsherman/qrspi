---
name: glab-cli
description: "Drive GitLab from the command line with the official glab CLI — authenticate, manage merge requests, issues, CI/CD pipelines, releases, changelogs, repositories, and raw API calls non-interactively. Use this skill whenever a task involves GitLab, glab, a GitLab merge request (MR), a GitLab pipeline or job, a GitLab release, gitlab.com or a self-hosted GitLab instance, or any time you need to script GitLab operations from an agent or CI job — even if the user does not say the word 'glab'. Do NOT use this for GitHub (use the GitHub CLI gh) or for local git history/branch operations (use git or the Graphite CLI)."
command: /glab-cli
argument-hint: <gitlab-task, e.g. 'open an MR and merge it after the pipeline passes'>
allowed-tools: Bash(glab:*), Bash(jq:*), Read
---

# glab-cli — GitLab from the command line, for agents

`glab` is GitLab's official command-line client. It mirrors what you can do in the
GitLab web UI (merge requests, issues, pipelines, releases) plus a raw `glab api`
escape hatch, and it works against both `gitlab.com` and self-hosted instances.

This skill is written for **agents and scripts**, not humans clicking through prompts.
The single most important consequence of that: every command here runs
**non-interactively** and, wherever possible, emits **machine-readable JSON** you can
parse. An agent that lets `glab` drop into an interactive prompt is stuck forever — so
the rules below exist to make sure that never happens.

## Overview

- **Targets:** `gitlab.com` by default; any self-hosted GitLab via `--hostname` or
  `GITLAB_HOST`. Host selection is explicit, never guessed — see
  [references/authentication.md](references/authentication.md).
- **Auth:** OAuth device flow for humans, a Personal Access Token (PAT) or the
  `GITLAB_TOKEN` environment variable for agents and CI. Details in
  [references/authentication.md](references/authentication.md).
- **Shape of every call:** non-interactive flag + JSON output + parsed result. Multi-step
  flows collapse into a single `{"ok": ...}` envelope so a caller can branch on one value.

## The eight command groups

`glab` is organized into subcommand groups. Below is the one-line orientation for each;
the **full flag-by-flag reference is in [references/commands.md](references/commands.md)** —
read it before composing any command whose flags you are not certain of.

| Group | What it does | Most-used commands |
|-------|--------------|--------------------|
| `auth` | Log in / check credentials / pick a host | `glab auth login`, `glab auth status` |
| `mr` | Merge requests: create, review, merge | `glab mr create`, `glab mr merge`, `glab mr list` |
| `issue` | Issues: file, triage, close | `glab issue create`, `glab issue list`, `glab issue close` |
| `ci` / `pipeline` | CI/CD pipelines and jobs | `glab ci status`, `glab ci run`, `glab ci trace` |
| `release` | Tagged releases and their assets | `glab release create`, `glab release list` |
| `changelog` | Generate changelog entries from commits | `glab changelog generate` |
| `repo` | Projects: clone, fork, view, create | `glab repo clone`, `glab repo fork`, `glab repo view` |
| `api` | Raw authenticated GitLab REST/GraphQL calls | `glab api projects/:id`, `glab api --paginate` |

## Authentication (summary)

For agents and CI, prefer a token over interactive login. Set `GITLAB_TOKEN` (and
`GITLAB_HOST` for self-hosted) in the environment; `glab` picks them up with no prompt:

```bash
export GITLAB_TOKEN="glpat-xxxxxxxxxxxxxxxxxxxx"
export GITLAB_HOST="gitlab.example.com"   # omit for gitlab.com
glab auth status                          # verify before doing real work
```

For interactive/human setup, multi-host config, and how to treat credential conflicts as
named recoverable states, see [references/authentication.md](references/authentication.md).

## Workflow patterns

These are the high-value flows agents actually need. The scripting mechanics (JSON
parsing, exit codes, the single-envelope pattern) live in
[references/ci-scripting.md](references/ci-scripting.md).

### Merge-after-green (the canonical CI flow)

Never merge an MR before its pipeline is green. There are two non-interactive ways to do
it, and which you pick depends on whether you want to block:

```bash
# Option A — fire-and-forget: GitLab merges automatically once the pipeline succeeds.
glab mr merge 42 --when-pipeline-succeeds --squash --remove-source-branch --yes

# Option B — block until the pipeline finishes, then decide yourself.
glab ci status --wait        # blocks until the running pipeline reaches a terminal state
glab mr merge 42 --squash --remove-source-branch --yes
```

> Spot-check: confirm `--when-pipeline-succeeds` (older builds) vs `--auto-merge` (newer
> builds) and the exact `glab ci status` wait flag against your installed `glab version` —
> the flag names have drifted across releases. See the note in
> [references/commands.md](references/commands.md).

### Stacked / dependent MRs

Create an MR whose target is another feature branch rather than the default branch, so a
chain of changes can be reviewed in order:

```bash
glab mr create --source-branch feat-step-2 --target-branch feat-step-1 \
  --title "Step 2: ..." --description "Depends on Step 1." --yes
```

### Fork-based contributions

Fork, push to the fork, then open the MR back at the upstream project:

```bash
glab repo fork --clone --remote
glab mr create --fill --yes   # --fill derives title/body from commits; no prompt
```

## Recognized states (judgment calls)

Some `glab` outcomes are **not** failures — they are expected branches with a deterministic
recovery. Handle these in-band; do **not** trigger the HARD STOP below for them. They are
textually and categorically distinct from infrastructure failures: a recognized state has a
known cause and a scripted next step, whereas a HARD STOP is an unknown-environment failure
you must not paper over. The full catalogue with detection snippets is in
[references/error-handling.md](references/error-handling.md).

- **MR already exists on this branch.** `glab mr create` reports an existing MR for the
  source branch. Recovery: switch to `glab mr view` / `glab mr update` instead of creating.
- **Release tag does not exist yet.** `glab release create` needs a tag. Recovery: pass
  `--ref <branch-or-sha>` so glab creates the tag, or create the tag first.
- **Pipeline not green at merge time.** A merge is refused because CI is pending/failed.
  Recovery: this is the merge-after-green flow — wait (`glab ci status --wait`) or use
  `--when-pipeline-succeeds`, do not force the merge.

## Rules for agent / scripted use

These exist because an agent has no human to recover from a prompt or eyeball a table.

1. **Every invocation is non-interactive.** Append the confirmation/auto flag the
   subcommand expects (`--yes`/`-y`, `--fill` for `mr create`). If a command would still
   prompt, it is the wrong command — find the non-interactive form in
   [references/commands.md](references/commands.md).
2. **Parse JSON, never scrape tables.** Use `-F json` (alias `--output json`) on commands
   that support it, or `glab api` (always JSON), and pipe through `jq`. Human-formatted
   tables are not a stable contract.
3. **Fold multi-step flows into one `{"ok": ...}` envelope.** A caller should branch on a
   single boolean/value, not re-parse intermediate output. Pattern and helpers in
   [references/ci-scripting.md](references/ci-scripting.md).
4. **Check exit codes.** `glab` returns non-zero on failure; a recognized state is decided
   by inspecting the message/JSON, not by ignoring the exit code. See
   [references/error-handling.md](references/error-handling.md).

## HARD STOP: Infrastructure Errors

If ANY command fails with a permissions error, auth failure, config error, or tooling error (EACCES, permission denied, token expired, command not found, config inaccessible): STOP IMMEDIATELY. Print the exact failing command and exact error output. Do not execute another command. Do not investigate. Do not attempt workarounds. Do not use alternate tools. Do not modify configuration. Exit and report the error. "Let me just try one thing" is the exact failure mode this rule prevents.

## Reference files

- [references/commands.md](references/commands.md) — full subcommand/flag reference for all
  eight groups (`auth`, `mr`, `issue`, `ci`/`pipeline`, `release`, `changelog`, `repo`, `api`).
- [references/authentication.md](references/authentication.md) — login methods, `GITLAB_TOKEN`
  in CI, self-hosted `--hostname`, multi-host `config.yml`, credential conflicts as named states.
- [references/ci-scripting.md](references/ci-scripting.md) — merge-after-green, `glab ci status
  --wait`, `jq` parsing, exit-code handling, the single-`{"ok": ...}`-envelope pattern.
- [references/error-handling.md](references/error-handling.md) — exit codes, recognized-state vs
  HARD-STOP distinction, verbatim error propagation.
