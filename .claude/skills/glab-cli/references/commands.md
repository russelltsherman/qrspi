# glab command reference — all eight groups

Flag-by-flag reference for the `glab` subcommand groups an agent will use. This is
greenfield content sourced from the official glab documentation; **flag names and
availability drift across `glab` releases, so spot-check anything load-bearing against your
installed `glab version`.** Where a flag is known to have changed, it is called out inline.

Conventions used throughout:
- `--yes` / `-y` suppresses confirmation prompts (required for agents).
- `-F json` (alias `--output json`) emits machine-readable JSON on commands that support it.
- `-R, --repo OWNER/NAME` selects the target project without needing a checked-out repo.
- `--hostname HOST` (or `GITLAB_HOST`) targets a self-hosted instance.

## Table of contents

1. [auth](#1-auth)
2. [mr (merge requests)](#2-mr-merge-requests)
3. [issue](#3-issue)
4. [ci / pipeline](#4-ci--pipeline)
5. [release](#5-release)
6. [changelog](#6-changelog)
7. [repo](#7-repo)
8. [api](#8-api)

---

## 1. auth

Manage credentials and host selection. Full prose in `authentication.md`.

| Command | Purpose | Key flags |
|---------|---------|-----------|
| `glab auth login` | Authenticate to a GitLab host | `--hostname`, `--token`, `--stdin` (read token from stdin) |
| `glab auth status` | Show which hosts are logged in and token validity | `--hostname` |
| `glab auth logout` | Remove stored credentials for a host | `--hostname` |

Agent/CI form — token via environment, no prompt:

```bash
export GITLAB_TOKEN="glpat-..."
glab auth status            # verify before real work
# or pipe a token explicitly:
printf '%s' "$GITLAB_TOKEN" | glab auth login --hostname gitlab.example.com --stdin
```

## 2. mr (merge requests)

| Command | Purpose | Key non-interactive flags |
|---------|---------|---------------------------|
| `glab mr create` | Open an MR | `--fill` (derive title/body from commits), `--title`, `--description`, `--source-branch`, `--target-branch`, `--draft`, `--yes` |
| `glab mr list` | List MRs | `-F json`, `--state=opened\|merged\|closed\|all`, `--author`, `--label`, `--per-page` |
| `glab mr view` | Show one MR | `<id>`, `-F json`, `--comments` |
| `glab mr merge` | Merge an MR | `--squash`, `--rebase`, `--remove-source-branch`, `--when-pipeline-succeeds`, `--yes` |
| `glab mr update` | Edit an MR | `--title`, `--description`, `--ready`/`--draft`, `--label`, `--unlabel` |
| `glab mr approve` | Approve an MR | `<id>` |
| `glab mr checkout` | Check out an MR branch locally | `<id>` |
| `glab mr close` / `glab mr reopen` | Close/reopen | `<id>` |

```bash
# Create non-interactively, capture the new MR as JSON
glab mr create --fill --yes
glab mr list --state opened -F json | jq -r '.[].iid'
```

> Spot-check: the auto-merge flag is `--when-pipeline-succeeds` on older glab and may be
> `--auto-merge` on newer builds. Verify against `glab mr merge --help`.

## 3. issue

| Command | Purpose | Key non-interactive flags |
|---------|---------|---------------------------|
| `glab issue create` | File an issue | `--title`, `--description`, `--label`, `--assignee`, `--yes` |
| `glab issue list` | List issues | `-F json`, `--state`, `--label`, `--assignee`, `--per-page` |
| `glab issue view` | Show one issue | `<id>`, `-F json`, `--comments` |
| `glab issue update` | Edit an issue | `--title`, `--description`, `--label`, `--unlabel` |
| `glab issue close` / `glab issue reopen` | Close/reopen | `<id>` |

```bash
glab issue create --title "Bug: timeout on upload" \
  --description "Repro steps..." --label bug --yes
glab issue list --state opened -F json | jq -r '.[] | "\(.iid)\t\(.title)"'
```

## 4. ci / pipeline

`glab ci` operates on CI/CD pipelines and jobs. (`glab pipeline` exists as a related/alias
surface on some builds — prefer `glab ci` and spot-check.)

| Command | Purpose | Key flags |
|---------|---------|-----------|
| `glab ci status` | Status of the pipeline for the current/branch commit | `--wait`/`--live` (block until terminal), `--branch` |
| `glab ci list` | List recent pipelines | `-F json`, `--status`, `--per-page` |
| `glab ci view` | Inspect a pipeline and its jobs | `<id>`, `--branch` |
| `glab ci run` | Trigger a new pipeline | `--branch`, `--variables key:value` |
| `glab ci trace` | Stream a job's log | `<job-id>` |
| `glab ci retry` / `glab ci cancel` | Retry/cancel a pipeline or job | `<id>` |

```bash
glab ci status --wait                      # block until the pipeline finishes
glab ci list -F json | jq -r '.[0].status' # latest pipeline status
```

> Spot-check: the blocking flag is `--wait` on some builds and `--live`/`--compact` on
> others; confirm with `glab ci status --help`.

## 5. release

| Command | Purpose | Key flags |
|---------|---------|-----------|
| `glab release create` | Create a release for a tag | `<tag>`, `--ref <branch-or-sha>` (creates the tag if absent), `--notes`, `--notes-file`, asset paths |
| `glab release list` | List releases | `-F json` |
| `glab release view` | Show a release | `<tag>`, `-F json` |
| `glab release upload` | Attach assets to a release | `<tag> <files...>` |
| `glab release delete` | Delete a release | `<tag>`, `--yes` |

```bash
# Tag does not exist yet → pass --ref so glab creates it (a recognized state, not a failure)
glab release create v1.2.0 --ref main --notes "See changelog." 
```

## 6. changelog

| Command | Purpose | Key flags |
|---------|---------|-----------|
| `glab changelog generate` | Build changelog entries from commit history | `--version`, `--from`, `--to`, `--config-file` |

```bash
glab changelog generate --version 1.2.0 > CHANGELOG_FRAGMENT.md
```

## 7. repo

| Command | Purpose | Key flags |
|---------|---------|-----------|
| `glab repo clone` | Clone a project | `OWNER/NAME`, `--` (pass-through git flags) |
| `glab repo fork` | Fork a project | `--clone`, `--remote` (add fork as a git remote) |
| `glab repo view` | Show project metadata | `-F json`, `-R OWNER/NAME` |
| `glab repo create` | Create a new project | `--name`, `--private`/`--public`, `--group` |
| `glab repo list` | List projects | `-F json` |

```bash
glab repo fork --clone --remote
glab repo view -R group/project -F json | jq -r '.web_url'
```

## 8. api

`glab api` is the raw escape hatch — authenticated GitLab REST (and GraphQL) calls that
always return JSON. Use it for anything the typed subcommands do not cover.

| Form | Purpose |
|------|---------|
| `glab api <endpoint>` | GET a REST endpoint (output is JSON) |
| `glab api -X POST <endpoint> -f key=value` | Mutating call with form fields (`-f` string, `-F` typed/file) |
| `glab api --paginate <endpoint>` | Follow pagination and concatenate results |
| `glab api graphql -f query='...'` | Run a GraphQL query |

```bash
# Current authenticated user
glab api user | jq -r '.username'
# All open MRs for a project, paginated
glab api --paginate "projects/:id/merge_requests?state=opened" | jq -r '.[].iid'
```

> Note: in `glab api`, `:id` / `:fullpath` placeholders are resolved from the current repo.
> `-f` sends string fields, `-F` sends typed values and `@file` references — mirroring `gh api`.
