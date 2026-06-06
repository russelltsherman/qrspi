---
name: writing-gitlab-pipelines
description: Write, review, and optimize GitLab CI/CD pipelines (.gitlab-ci.yml). Use when authoring or modifying GitLab CI configuration, designing stages/jobs, setting up caching/artifacts, environments/deployments, or security scanning. Trigger on requests to create, debug, refactor, or speed up a .gitlab-ci.yml.
allowed-tools: Read, Write, Edit, Bash
---

# Writing GitLab Pipelines

You are an expert GitLab CI/CD pipeline author. This skill encodes opinionated,
production-grade defaults for `.gitlab-ci.yml`. Apply the inline guidance below for
every pipeline; load a file under `references/` when a concern needs depth.

## Purpose & when to use

Use this skill whenever you author, review, refactor, or optimize a GitLab CI/CD
pipeline (`.gitlab-ci.yml` or any `include`d CI fragment). It applies to:

- Greenfield `.gitlab-ci.yml` creation.
- Adding or restructuring stages, jobs, and `needs`/DAG ordering.
- Configuring caching, artifacts, environments, deployments, and security scanning.
- Debugging slow, flaky, or misfiring pipelines (wrong `rules`, cache misses, stuck deploys).

If the task is not GitLab CI (e.g. GitHub Actions, Jenkins, raw shell), this skill does
not apply. GitLab-specific keywords — `stages`, `rules`, `needs`, `environment`,
`include`, `extends` — are the signal that it does.

## Opinionated defaults

These are non-negotiable defaults. Deviate only with an explicit, stated reason.

- **Prefer `rules:` over `only`/`except`.** `only`/`except` is legacy and cannot express
  combined conditions cleanly. Use `rules:` with `if`, `changes`, and `exists`. Never mix
  `rules` and `only`/`except` in the same job. See `references/rules.md`.
- **Pin image tags or digests; never `:latest`.** Use `image: alpine:3.20` (or a digest
  `image: alpine@sha256:...`) so builds are reproducible. `:latest` silently drifts.
- **Always set an explicit `expire_in` on artifacts.** Unbounded artifacts cost storage and
  hide intent. Set `expire_in` to the shortest useful window (e.g. `1 week` for build
  outputs, `30 days` for reports). See `references/cache-artifacts.md`.
- **One concern per job; keep `script` blocks short.** Push multi-line logic into committed,
  version-controlled scripts the job calls, not inline YAML heredocs.
- **Fail fast and visibly.** Set `set -euo pipefail` in shell jobs; do not swallow errors
  with `|| true` unless intentional and commented.

## Performance & optimization

Target a sub-10-minute pipeline for the common path. Levers, in priority order:

- **Use `needs:` to build a DAG.** Replace strict stage-by-stage execution with `needs` so
  independent jobs run as soon as their inputs are ready instead of waiting on a whole stage.
- **Set `interruptible: true`** on jobs safe to cancel, so superseded pipelines auto-cancel
  and free runners (pair with "Auto-cancel redundant pipelines").
- **Scope caching tightly.** Use a stable `cache:key` (lockfile-based) and the right
  `policy` (`pull` for consumers, `pull-push` only where the cache is produced).
- **Use `resource_group`** to serialize jobs that must not run concurrently (e.g. deploys to
  one environment) without serializing the whole pipeline.
- **Add bounded `retry:`** for known-transient failures (`runner_system_failure`,
  `stuck_or_timeout_failure`) — not as a blanket flake mask.
- **Set an explicit `timeout:`** per job so a hung job fails fast instead of burning the
  project-level maximum.

## Anti-patterns → alternatives

| Anti-pattern | Preferred alternative |
|---|---|
| `only`/`except` for conditions | `rules:` with `if`/`changes`/`exists` (`references/rules.md`) |
| `image: node:latest` (floating) | Pin a tag or digest: `image: node:20.15-alpine` |
| Artifacts with no `expire_in` | Explicit `expire_in` scoped to the shortest useful window |
| Copy-pasted job definitions | `extends:` + `include:` templates (`references/includes-extends.md`) |
| Pure stage-by-stage serial pipeline | `needs:` DAG for independent jobs |
| Long inline multi-line `script:` | Call a committed script file from `script:` |
| Deploys racing each other | `resource_group:` per environment (`references/environments.md`) |
| Secrets echoed or in plain variables | Masked/protected CI variables + secret scanning (`references/security.md`) |

## See references/

Load these for depth on a specific concern:

- `references/rules.md` — `rules:` conditions, `when`, `allow_failure`, migrating off `only`/`except`.
- `references/includes-extends.md` — `include:`, `extends:`, anchors, reusable job templates (DRY).
- `references/cache-artifacts.md` — caching vs artifacts, keys, policies, `expire_in`.
- `references/environments.md` — environments, deployments, review apps, `on_stop` teardown.
- `references/security.md` — SAST/DAST/dependency/container/secret scanning.
- `references/architecture.md` — worked examples: DAG, parent-child, multi-stage layouts.
