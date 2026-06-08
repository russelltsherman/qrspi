# Advanced `gh api` — REST patterns

`gh api` is a thin authenticated wrapper over the GitHub REST API. It reuses
your `gh` auth, sets the right `Accept` headers, and resolves the host, so you
get an authenticated `curl` without managing tokens or base URLs by hand. Use it
when a higher-level `gh` subcommand doesn't expose the field or endpoint you
need.

Apply the non-interactive defaults from `SKILL.md` (`GH_PAGER=""`,
`GH_PROMPT_DISABLED=1`) in scripted contexts.

## Table of contents

- Basic reads
- Path parameter substitution
- Pagination
- Shaping output with `--jq`
- Request fields (`-f`, `-F`, `-X`) and the mutation boundary
- Caching reads
- Custom headers and previews

## Basic reads

```bash
gh api repos/{owner}/{repo}                 # repo metadata (current repo)
gh api repos/cli/cli/releases/latest        # explicit owner/repo
gh api user                                 # the authenticated user
```

`{owner}` and `{repo}` are auto-filled from the current repository's remote, so
the same command works across checkouts.

## Path parameter substitution

`gh api` substitutes `{...}` placeholders from the current repo context. Be
explicit when operating on another repo:

```bash
gh api repos/{owner}/{repo}/pulls/123
gh api repos/anthropics/anthropic-sdk-python/issues?state=open
```

## Pagination

The REST API caps a page at 100 items. For a complete list use `--paginate`,
which follows `Link` headers and concatenates pages:

```bash
gh api --paginate repos/{owner}/{repo}/issues --jq '.[].number'
```

`--paginate` with `--jq` streams each page through the filter. To merge all
pages into a single JSON array first, add `--slurp`:

```bash
gh api --paginate --slurp repos/{owner}/{repo}/labels --jq 'length'
```

Set page size with `--paginate -f per_page=100` to minimize round trips.

## Shaping output with `--jq`

`--jq` runs the bundled `jq` engine on the response — no external `jq` needed.
Pull exactly the fields you want into a stable shape:

```bash
# open PRs as "number<TAB>title"
gh api repos/{owner}/{repo}/pulls --jq '.[] | "\(.number)\t\(.title)"'

# map reviewers to a comma list
gh api repos/{owner}/{repo}/pulls/123/requested_reviewers \
  --jq '[.users[].login] | join(", ")'
```

`--template` (Go templates) is an alternative when you want formatted text
rather than re-parsed JSON.

## Request fields and the mutation boundary

`-f` adds string fields, `-F` adds typed/file fields (numbers, booleans, `@file`,
`-` for stdin), and `-X` sets the HTTP method:

```bash
gh api -X GET search/issues -f q='repo:cli/cli is:open label:bug'
```

`gh api` will happily issue `POST`/`PATCH`/`PUT`/`DELETE` requests — that is how
it creates and edits resources. **Those are mutations and are out of scope for
this skill.** Per the capability boundary in `SKILL.md`, route any write through
the orchestration layer / `using-graphite-cli` instead of `gh api -X POST`. Keep
your `gh api` usage here to `GET` reads (the default method).

## Caching reads

`--cache <duration>` caches a response on disk so repeated reads in a script
don't re-hit the API (helpful against rate limits):

```bash
gh api repos/{owner}/{repo} --cache 1h --jq '.default_branch'
```

## Custom headers and previews

`--header`/`-H` sets request headers — for example to request a specific media
type or a raw diff:

```bash
gh api repos/{owner}/{repo}/pulls/123 \
  -H 'Accept: application/vnd.github.v3.diff'
```

Use `--header 'Accept: application/vnd.github+json'` and
`-H 'X-GitHub-Api-Version: 2022-11-28'` to pin the API version when stability
matters.
