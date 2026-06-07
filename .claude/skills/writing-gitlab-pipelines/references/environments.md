# Environments, Deployments & Review Apps

Deep dive on `environment:` — how GitLab tracks *where* code is deployed, gates
deployments, spins up per-MR review apps, and tears them down with `on_stop`.

## Static environments

An `environment:` keyword turns a job into a tracked deployment. GitLab records the
deployed ref, shows it on the Environments page, and links it from MRs.

```yaml
deploy-production:
  stage: deploy
  script: ./deploy.sh production
  environment:
    name: production
    url: https://app.example.com
  rules:
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
      when: manual            # gate prod behind a human click
```

- `name:` — the environment's identity (e.g. `staging`, `production`).
- `url:` — surfaced as a clickable link in the GitLab UI.
- Use `when: manual` (optionally `allow_failure: false`) to require a human to trigger
  production deploys.

## Dynamic environments (review apps)

A dynamic environment uses variables in `name`/`url` so every branch or MR gets its own
ephemeral environment — the **review app** pattern. The deploy job creates it; a paired
`stop` job tears it down via `on_stop`.

```yaml
deploy-review:
  stage: deploy
  script: ./deploy-review.sh
  environment:
    name: review/$CI_COMMIT_REF_SLUG       # one env per branch
    url: https://$CI_COMMIT_REF_SLUG.review.example.com
    on_stop: stop-review                   # the job that tears it down
    auto_stop_in: 1 week                   # auto-teardown after inactivity
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'

stop-review:
  stage: deploy
  script: ./teardown-review.sh
  environment:
    name: review/$CI_COMMIT_REF_SLUG
    action: stop                           # marks this as a teardown job
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
      when: manual
  variables:
    GIT_STRATEGY: none                     # repo may be gone when stopping
```

Key points:

- **`on_stop:`** names the job GitLab runs to stop the environment. That job must set
  `environment: action: stop` and target the **same** `name`.
- **`auto_stop_in:`** schedules automatic teardown after a period of inactivity (e.g.
  `auto_stop_in: 2 days`) so stale review apps don't accumulate. GitLab also stops the
  environment automatically when the MR is merged or closed if an `on_stop` job exists.
- `$CI_COMMIT_REF_SLUG` keeps the env/URL DNS- and path-safe.
- Set `GIT_STRATEGY: none` on stop jobs — the branch may already be deleted.

## Environment tiers

`environment: deployment_tier:` (`production`, `staging`, `testing`, `development`,
`other`) lets GitLab classify environments consistently for dashboards and DORA metrics
even when names vary:

```yaml
environment:
  name: prod-eu
  deployment_tier: production
```

## Scoped (per-environment) variables

CI/CD variables can be **scoped to an environment** in the project/group settings
(Settings → CI/CD → Variables, "Environment scope"). A variable like `API_KEY` can hold a
different value for `production` than for `review/*`. The pipeline references the same
`$API_KEY`; GitLab injects the value matching the job's `environment:name`. Scope secrets
to `production` (and mark them **protected**) so review apps never receive prod
credentials.

## Deployment gates: approvals, protected environments, resource groups

- **Protected environments** (Settings → CI/CD → Protected environments) restrict who can
  deploy to an environment and can require **deployment approvals** (a configurable number
  of approvers) before a job to that environment runs — an out-of-pipeline gate layered on
  top of `when: manual`.
- **`resource_group:`** serializes jobs that must not deploy concurrently to the same
  target, preventing two pipelines from racing a single environment:

  ```yaml
  deploy-production:
    environment: { name: production }
    resource_group: production
    script: ./deploy.sh production
  ```

- Combine `when: manual` (human trigger) + protected environment (who may trigger) +
  `resource_group` (no concurrent deploys) for a safe production gate.

## Review-app lifecycle summary

1. MR opened → `deploy-review` creates `review/<branch>` with a unique URL.
2. Reviewers click the URL from the MR widget to test the change live.
3. `auto_stop_in` (or MR merge/close) triggers the `on_stop` job.
4. `stop-review` tears down infrastructure and marks the environment stopped.
