# Security Scanning

Deep dive on GitLab's built-in security scanners, how to enable them via templates, where
their results surface, and how to enforce them with policies.

> **Version & tier note:** The scanning *templates* below run on any GitLab tier and
> populate JSON artifacts. The **MR security widget**, **Security Dashboard**, and **scan
> execution / result policies** require **Ultimate**. On Free/Premium you still get the
> reports as artifacts but not the merged dashboard view. Verify keyword availability
> against your instance version.

## Enabling scanners via templates

Each scanner ships as a GitLab-maintained template you `include`. They add hidden jobs and
wire up the right `artifacts:reports:*`.

```yaml
include:
  - template: 'Jobs/SAST.gitlab-ci.yml'
  - template: 'Jobs/Dependency-Scanning.gitlab-ci.yml'
  - template: 'Jobs/Container-Scanning.gitlab-ci.yml'
  - template: 'Jobs/Secret-Detection.gitlab-ci.yml'
  - template: 'Security/DAST.gitlab-ci.yml'

stages:
  - test
  - deploy
  - dast
```

Configure scanners with documented CI variables rather than editing the template jobs,
e.g. `SAST_EXCLUDED_PATHS`, `DS_EXCLUDED_PATHS`, `CS_IMAGE` for the container image to
scan, `SECRET_DETECTION_HISTORIC_SCAN` to scan full Git history.

## The scanners

- **SAST (Static Application Security Testing)** — analyzes *source code* for
  vulnerabilities. Auto-selects language analyzers. Report: `artifacts:reports:sast`.
- **Dependency Scanning** — finds known-vulnerable (CVE) dependencies from lockfiles.
  Report: `artifacts:reports:dependency_scanning`. Pair with a license check where needed.
- **Container Scanning** — scans a **built image** for OS/package CVEs. Run it *after* the
  image is built and pushed; point `CS_IMAGE` at it. Report:
  `artifacts:reports:container_scanning`.
- **Secret Detection** — scans the repo (and optionally full history) for committed
  credentials/tokens. Report: `artifacts:reports:secret_detection`. Treat any hit as a
  rotate-the-secret incident, not just a code fix.
- **DAST (Dynamic Application Security Testing)** — probes a **running** application over
  HTTP for runtime vulnerabilities. Report: `artifacts:reports:dast`.

## DAST vs review apps

DAST needs a live target. The standard pattern is to **deploy a review app first, then
point DAST at its URL**, so each MR is scanned against its own running instance:

```yaml
dast:
  stage: dast
  needs: ['deploy-review']
  variables:
    DAST_WEBSITE: https://$CI_COMMIT_REF_SLUG.review.example.com
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
```

SAST/dependency/secret scanning are *static* and run without a deployment; DAST and
container scanning depend on something being built/running first — order them with
`needs:` accordingly. See `environments.md` for the review-app deploy.

## `artifacts:reports:*` — how results surface

Scanners emit their findings as `artifacts:reports:<type>` JSON. GitLab ingests these to:

- Show **new vs existing** findings in the MR security widget (diff against the target
  branch).
- Populate the **Security Dashboard** and vulnerability report (Ultimate).
- Feed **policies** that can block a merge.

You normally don't write these report keys by hand — the templates do — but knowing the
report type matters when customizing a scanner or building a custom one.

## Scan execution & merge-request approval policies

On Ultimate, enforce scanning centrally instead of trusting every project's
`.gitlab-ci.yml`:

- **Scan execution policies** — *require* specified scans (e.g. SAST + secret detection on
  every MR to protected branches) across a group, even if a project omits the template.
  This closes the "someone deleted the scan job" gap.
- **Merge request approval policies (scan result policies)** — *block merges* (require
  approval) when a scan introduces findings above a severity threshold (e.g. any new
  `critical` dependency vulnerability requires security-team approval).

Define these in **Security & Compliance → Policies**; they live outside the pipeline YAML
and cannot be bypassed by editing `.gitlab-ci.yml`.

## Secrets handling (defense in depth)

- Never echo secrets or put them in plain `variables:` in the YAML. Use **masked** and
  **protected** CI/CD variables, or an external secrets manager via `secrets:` (e.g.
  HashiCorp Vault).
- Scope production secrets to the `production` environment (see `environments.md`) so
  review apps never receive them.
- Run **Secret Detection** so an accidentally committed credential is caught in CI — then
  rotate it.
