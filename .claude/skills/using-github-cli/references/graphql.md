# `gh api graphql` — GraphQL queries

GraphQL's advantage over REST is fetching exactly the fields you want across
several related resources in **one** request. Where REST would force N+1 calls
(list PRs, then per-PR fetch reviews, then per-PR fetch checks), a single
GraphQL query joins them. Reach for it when you need a multi-resource view or
fields the REST endpoints don't expose.

Run queries through `gh api graphql`, which authenticates and targets the
GraphQL endpoint automatically. Apply the non-interactive defaults from
`SKILL.md` in scripted contexts. Everything here is a **read** (`query`); GraphQL
`mutation` operations are writes and are out of scope — defer them per the
capability boundary in `SKILL.md`.

## Table of contents

- Basic query with variables
- Multi-resource join in one call
- Cursor pagination
- Shaping with `--jq`

## Basic query with variables

Pass variables with `-F` (typed) or `-f` (string). Reference the implicit
`$owner`/`$repo` by declaring them:

```bash
gh api graphql -F owner='{owner}' -F repo='{repo}' -f query='
  query($owner: String!, $repo: String!) {
    repository(owner: $owner, name: $repo) {
      name
      defaultBranchRef { name }
      stargazerCount
    }
  }'
```

`{owner}`/`{repo}` are filled from the current repo context, same as `gh api`.

## Multi-resource join in one call

Fetch open PRs together with their latest commit's check rollup and requested
reviewers — data that would take several REST calls:

```bash
gh api graphql -F owner='{owner}' -F repo='{repo}' -f query='
  query($owner: String!, $repo: String!) {
    repository(owner: $owner, name: $repo) {
      pullRequests(states: OPEN, first: 20) {
        nodes {
          number
          title
          reviewDecision
          commits(last: 1) {
            nodes {
              commit {
                statusCheckRollup { state }
              }
            }
          }
        }
      }
    }
  }'
```

`reviewDecision` and `statusCheckRollup.state` in particular are convenient
rollups that REST exposes only piecemeal.

## Cursor pagination

GraphQL paginates with cursors. `gh` can auto-follow them with `--paginate` when
the query exposes a `pageInfo { hasNextPage endCursor }` and accepts an
`$endCursor` variable:

```bash
gh api graphql --paginate -F owner='{owner}' -F repo='{repo}' -f query='
  query($owner: String!, $repo: String!, $endCursor: String) {
    repository(owner: $owner, name: $repo) {
      issues(first: 100, after: $endCursor, states: OPEN) {
        nodes { number title }
        pageInfo { hasNextPage endCursor }
      }
    }
  }'
```

`gh` feeds `$endCursor` automatically across pages.

## Shaping with `--jq`

The GraphQL response nests under `data`; `--jq` drills in:

```bash
gh api graphql -F owner='{owner}' -F repo='{repo}' -f query='
  query($owner: String!, $repo: String!) {
    repository(owner: $owner, name: $repo) {
      pullRequests(states: OPEN, first: 50) { nodes { number reviewDecision } }
    }
  }' --jq '.data.repository.pullRequests.nodes[]
            | select(.reviewDecision=="APPROVED") | .number'
```
