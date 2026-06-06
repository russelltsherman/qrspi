# GitLab Pipeline Rules

Deep dive on `rules:` — the modern, composable replacement for `only`/`except`. Use
`rules:` everywhere; never mix `rules` and `only`/`except` in the same job.

## How `rules:` evaluates

`rules:` is an ordered list. GitLab evaluates each rule top to bottom and stops at the
**first match**. The matched rule's attributes (`when`, `allow_failure`, `variables`)
decide whether the job is added to the pipeline and how it behaves. If no rule matches,
the job is **not** added.

```yaml
test:
  script: ./run-tests.sh
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
      when: on_success
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
      when: on_success
    - when: never   # explicit terminal: drop the job in all other cases
```

Always end with an explicit terminal rule (`- when: never` or `- when: on_success`/
`manual`) so the fall-through behavior is intentional and readable, not implicit.

## Rule clauses

- **`if:`** — a boolean expression over CI/CD variables. Quote the whole expression.
  Operators: `==`, `!=`, `=~` / `!~` (regex), `&&`, `||`. Example:
  `if: '$CI_COMMIT_BRANCH =~ /^release\/.*/'`.
- **`changes:`** — run only when listed paths changed. Use glob patterns. On branch
  pipelines `changes` compares against the previous commit; on MR pipelines it compares
  against the MR diff (more reliable — see caveat below).
- **`exists:`** — run only when a file matching the glob exists in the repo.
- **`when:`** — `on_success` (default), `manual`, `delayed` (with `start_in:`), `always`,
  `never`.
- **`allow_failure:`** — `true` lets the job fail without failing the pipeline. Common on
  `manual` jobs to make them non-blocking.
- **`variables:`** — set/override variables when that rule matches.

## Common keying variables

- `$CI_PIPELINE_SOURCE` — what triggered the pipeline. Key values: `push`,
  `merge_request_event`, `web`, `schedule`, `api`, `trigger`, `pipeline` (multi-project /
  parent-child), `parent_pipeline`. The primary lever for "MR vs branch vs scheduled".
- `$CI_COMMIT_BRANCH` — branch name for branch pipelines. **Empty in MR pipelines** and on
  tags — guard accordingly.
- `$CI_DEFAULT_BRANCH` — the project's default branch (e.g. `main`); compare against it
  rather than hard-coding the name.
- `$CI_COMMIT_TAG` — set on tag pipelines.
- `$CI_MERGE_REQUEST_TARGET_BRANCH_NAME` — target branch of an MR.

## `workflow:rules` — gate the whole pipeline

`workflow:rules` is a top-level block that decides whether a pipeline is created **at
all**. Use it to prevent duplicate pipelines (the classic "branch pipeline + MR pipeline"
double-run) and to scope when pipelines run.

```yaml
workflow:
  rules:
    # Run for merge requests
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
    # Avoid a duplicate branch pipeline when an MR is open for that branch
    - if: '$CI_COMMIT_BRANCH && $CI_OPEN_MERGE_REQUESTS'
      when: never
    # Run on the default branch
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
    # Run on tags
    - if: '$CI_COMMIT_TAG'
    - when: never
```

GitLab also ships `workflow.rules` templates you can `include` (e.g. the
"merge-request-pipelines" pattern) instead of writing this by hand.

## `rules:changes` caveats

- On **branch** pipelines, `changes` compares to the prior commit, which is unreliable for
  the first push of a branch (it may report everything or nothing changed). Prefer
  **merge-request pipelines** where `changes` reflects the full MR diff.
- Scope `changes` with `compare_to:` (e.g. `compare_to: 'refs/heads/main'`) to make the
  comparison base explicit and deterministic.
- `changes` is a convenience, not a security control — never rely on it to gate
  privileged jobs.

```yaml
build-frontend:
  script: npm run build
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
      changes:
        compare_to: 'refs/heads/main'
        paths:
          - 'frontend/**/*'
```

## Migrating off `only`/`except`

| `only`/`except` | `rules:` equivalent |
|---|---|
| `only: [merge_requests]` | `if: '$CI_PIPELINE_SOURCE == "merge_request_event"'` |
| `only: [main]` | `if: '$CI_COMMIT_BRANCH == "main"'` (or `== $CI_DEFAULT_BRANCH`) |
| `only: { changes: [...] }` | `rules: - changes: [...]` |
| `except: [schedules]` | `if: '$CI_PIPELINE_SOURCE == "schedule"' when: never` |
| `only: [tags]` | `if: '$CI_COMMIT_TAG'` |

`rules:` is strictly more expressive: it combines conditions, sets per-rule `variables`,
and supports `manual`/`delayed`/`allow_failure` inline — none of which `only`/`except`
can do cleanly.
