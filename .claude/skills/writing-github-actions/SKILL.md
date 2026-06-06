---
name: writing-github-actions
description: Guide for authoring secure, efficient GitHub Actions workflows and actions. Use whenever creating or editing a workflow YAML file under .github/workflows/, writing a reusable workflow or composite/JavaScript action, configuring CI/CD, build, test, release, or deploy pipelines on GitHub, setting up matrix builds, caching, artifacts, OIDC cloud auth, or workflow permissions/secrets. Trigger on any request to write, fix, review, or harden a GitHub Actions YAML file, even a single job or step. Do NOT use for GitLab CI, CircleCI, Jenkins, Azure Pipelines, or other non-GitHub CI systems.
---

# Writing GitHub Actions

Author GitHub Actions workflows that are **secure by default** and **efficient by
default**. This skill organizes guidance along the workflow lifecycle and links to
four on-demand reference files for depth. Read a reference only when the task
touches that topic.

## Non-negotiable hard rule: pin actions to a full commit SHA

**Every `uses:` MUST reference a 40-character commit SHA, never a tag or branch.**
Tags (`@v4`) and branches (`@main`) are mutable; a compromised action repo can
re-point them at malicious code. A SHA is immutable.

```yaml
# WRONG
- uses: actions/checkout@v4
# RIGHT — SHA pinned, version in a trailing comment for humans + Dependabot
- uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2
```

Keep the `# vX.Y.Z` comment so Dependabot/Renovate can still propose upgrades.
This rule is restated, with the rest of the hardening checklist, in
`references/security-hardening-checklist.md`.

## Workflow lifecycle

### Triggers (`on:`)

- Choose the narrowest trigger: `push` (branch filters), `pull_request`,
  `workflow_dispatch` (manual), `schedule` (cron), `workflow_call` (reusable).
- Filter with `branches:`, `paths:`, `tags:` to avoid wasted runs.
- **Security:** prefer `pull_request` (read-only token, no secrets) for anything
  that builds untrusted PR code. `pull_request_target` carries secrets + write
  token — never check out / execute PR-head code under it. See
  `references/security-hardening-checklist.md` §4.

### Permissions (least privilege)

Set a default-deny at the top, then grant the minimum per job:

```yaml
permissions: {}            # whole-workflow default-deny
jobs:
  build:
    permissions:
      contents: read       # only what this job needs
```

Never rely on default token scopes. Details: security reference §2.

### Jobs

- Jobs run on **separate fresh runners** in parallel by default.
- Order with `needs:` to form a DAG (`deploy` needs `build`).
- Gate sensitive jobs with `environment:` (required reviewers, scoped secrets).
- Pick explicit runner images (`ubuntu-24.04`, not `ubuntu-latest`) for
  reproducibility.

### Steps

- A step is either `uses:` (an action, SHA-pinned) or `run:` (a shell command).
- **Never interpolate untrusted `${{ github.event.* }}` text directly into a
  `run:` block** — that is shell injection. Pass it through `env:` and quote it.
  See security reference §3.
- Set `shell: bash` explicitly inside composite actions.

### Caching

- Use `actions/cache` (or built-in `cache:` on setup actions) to reuse
  dependencies across runs.
- Anchor the cache `key` with a lockfile hash; add `restore-keys` for partial
  hits. In matrix jobs, include every cache-affecting axis in the key — see
  `references/matrix-strategy-examples.md`.

### Artifacts

- Jobs share **no filesystem**. Pass build outputs between jobs with
  `actions/upload-artifact` → `actions/download-artifact`.
- Set a `retention-days:` appropriate to the artifact; scope names per matrix leg.

### Secrets & cloud auth

- Store secrets in repo/org/**environment** scope; reference via `secrets.*`.
  Environment scope (with required reviewers) is narrowest for deploys.
- **Prefer OIDC over static cloud keys.** Mint short-lived credentials at runtime
  instead of long-lived secrets. Requires `permissions: id-token: write`. Full
  AWS/GCP/Azure patterns: `references/oidc-setup-patterns.md`.

### Deployments

- Use `environment:` for approval gates and deployment branch rules.
- Disable `cancel-in-progress` for production deploys (don't kill an in-flight
  release). See concurrency below.

## Decision: reusable workflow vs composite action

Both promote reuse — they differ in granularity:

| Use a **reusable workflow** (`workflow_call`) | Use a **composite action** (`runs.using: composite`) |
|----------------------------------------------|------------------------------------------------------|
| Sharing **whole jobs**                        | Sharing a **sequence of steps** inside a job          |
| Needs its own runner(s), matrix, or secrets   | Runs inline on the **caller's** runner                |
| Cross-repo CI pipelines                        | Cross-repo / cross-job step bundles (e.g. setup)      |
| Typed `inputs:` + explicit `secrets:`          | Typed `inputs:`; inherits caller env                  |

Rule of thumb: reach for a **composite action** for "set up the toolchain"-style
step bundles; reach for a **reusable workflow** when you want to call an entire
job pipeline. Skeletons for both: `references/common-workflow-templates.md`.

## Concurrency & performance

- **`concurrency:`** — collapse redundant runs. For CI, cancel superseded runs;
  for deploys, never cancel mid-flight:

  ```yaml
  concurrency:
    group: ci-${{ github.ref }}
    cancel-in-progress: true      # false for production deploy groups
  ```

- **Matrix** — fan one job into parallel variants (`strategy.matrix`); use
  `fail-fast: false` on test grids to see every failing combination. Details and
  `include`/`exclude`/cache-key isolation: `references/matrix-strategy-examples.md`.
- **Speed:** cache dependencies, shard tests across the matrix, scope `paths:`
  filters, and avoid `ubuntu-latest` drift.

## References

Read on demand — each covers one topic in depth:

- `references/security-hardening-checklist.md` — SHA-pinning, least-privilege
  `permissions: {}`, expression-injection avoidance, `pull_request_target` rules,
  CODEOWNERS, and the zizmor check map.
- `references/oidc-setup-patterns.md` — provider-agnostic OIDC auth (AWS / GCP /
  Azure) replacing static cloud secrets, plus GitHub Environments.
- `references/common-workflow-templates.md` — single-job CI through multi-job
  deploy pipelines; reusable-workflow (`workflow_call`) and composite-action
  skeletons.
- `references/matrix-strategy-examples.md` — `strategy.matrix`, `fail-fast`,
  `include`/`exclude`, and per-leg cache-key isolation.
