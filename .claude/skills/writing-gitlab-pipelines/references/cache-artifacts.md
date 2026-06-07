# Caching & Artifacts

Deep dive on the two distinct mechanisms for moving files between jobs and runs. They are
**not interchangeable**:

- **`cache:`** — a *performance optimization*. Restores dependency/build directories
  across pipelines to save time. May be missing, stale, or shared across runners — treat
  it as best-effort and never required for correctness.
- **`artifacts:`** — *job outputs* passed forward. Reliable, versioned to a pipeline, and
  used to hand build products and reports to later jobs and to the GitLab UI.

## `cache:` — keys, paths, policy

```yaml
build:
  script: npm ci && npm run build
  cache:
    key:
      files:
        - package-lock.json     # key derived from the lockfile hash
    paths:
      - .npm/
      - node_modules/
    policy: pull-push
```

### Cache keys

- **`key:` (static string)** — a fixed cache bucket. Simplest, but shared across all
  branches.
- **`key: files: [...]`** — GitLab hashes the listed files (usually lockfiles) and uses the
  hash as the key. The cache invalidates automatically when dependencies change — the
  preferred default. Up to two files.
- **`key: prefix: ... files: [...]`** — combine a prefix (e.g. per-branch) with a file
  hash.
- **`$CI_COMMIT_REF_SLUG`** — a sanitized, URL/-path-safe form of the branch or tag name.
  Use it in a cache key to give each branch its own cache without illegal characters:
  `key: "$CI_COMMIT_REF_SLUG"`. Prefer `files:` keys when correctness depends on
  dependency versions; use `$CI_COMMIT_REF_SLUG` to isolate per-branch caches.

### Cache policy

`policy` controls whether a job reads, writes, or both:

- **`pull-push`** (default) — download at start, upload at end. Use only on the job that
  *produces* the cache (e.g. the install/build job).
- **`pull`** — download only; never upload. Use on consumer jobs (lint, test) so they
  read the warmed cache without racing to rewrite it. Faster and avoids cache churn.
- **`push`** — upload only; skip the download. Useful for a dedicated warm-up job.

Pattern: one job warms the cache with `pull-push`; all downstream jobs use `pull`.

### Cache scope & fallbacks

- Caches are scoped by key and (by configuration) can be per-branch, per-runner, or
  distributed (S3). Do not assume a cache produced on one runner exists on another.
- `cache:fallback_keys:` lets a job fall back to another key (e.g. the default branch's
  cache) on a miss — useful to warm new branches.
- `cache:when:` (`on_success`/`on_failure`/`always`) controls when the cache is saved.
- `cache:untracked: true` caches files not tracked by Git.

## `artifacts:` — outputs, expiry, reports

```yaml
build:
  script: npm run build
  artifacts:
    paths:
      - dist/
    expire_in: 1 week          # ALWAYS set this — unbounded artifacts cost storage
    when: on_success           # on_success | on_failure | always
```

### `expire_in`

Always set `expire_in` to the shortest useful window: build outputs `1 week`, reports
`30 days`, throwaway debug artifacts `1 hour`. Unbounded artifacts silently accumulate
storage cost and hide intent. `expire_in: never` should be a deliberate, commented choice
(GitLab can also keep the latest artifacts on the default branch via project settings).

### `when`

- `on_success` (default) — upload only if the job passed.
- `on_failure` — upload only if the job failed. Ideal for **debug logs, screenshots, test
  reports** you want precisely when something broke.
- `always` — upload regardless. Use for reports you need from both pass and fail runs.

### `artifacts:reports:*`

`reports` artifacts feed structured data into GitLab's UI (MR widgets, security
dashboards, coverage) rather than just being downloadable files:

```yaml
test:
  script: ./run-tests.sh
  artifacts:
    when: always
    reports:
      junit: report.xml              # test results in the MR widget
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
      dotenv: build.env              # export variables to downstream jobs
```

Common report types: `junit` (tests), `coverage_report` (cobertura), `dotenv` (pass
variables forward via `needs`), `sast`/`dependency_scanning`/`container_scanning`/`dast`/
`secret_detection` (security — see `security.md`), `codequality`, `terraform`.

## Passing artifacts to specific jobs

By default a job downloads artifacts from **all** jobs in earlier stages. Control this:

- **`dependencies: [job-a, job-b]`** — download artifacts only from the listed jobs;
  `dependencies: []` downloads none (faster).
- **`needs:`** — when you build a DAG (see `architecture.md`), `needs` jobs' artifacts are
  fetched automatically and `needs` implies the dependency. Prefer `needs` over
  `dependencies` in modern pipelines.

## cache vs artifacts — quick rule

| You want to… | Use |
|---|---|
| Speed up `npm ci`/`bundle install` across runs | `cache:` (lockfile key, `pull`/`pull-push` split) |
| Hand a built `dist/` to the deploy job | `artifacts:paths` + `needs` |
| Show test/coverage/security results in the MR | `artifacts:reports:*` |
| Keep debug logs only when a job fails | `artifacts: when: on_failure` |
