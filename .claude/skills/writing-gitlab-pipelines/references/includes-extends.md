# Includes & Extends (DRY)

Deep dive on the three layers of reuse in GitLab CI: `include:` (pull in external YAML),
`extends:` (merge job templates), and `!reference` / YAML anchors (splice fragments).

## `include:` — composing configuration

`include:` merges other YAML into the pipeline before it runs. Four forms:

```yaml
include:
  # 1. local — a file in THIS repo (leading slash = repo root)
  - local: '/ci/templates/build.yml'

  # 2. project (file) — a file from ANOTHER project in the same GitLab instance
  - project: 'my-group/ci-templates'
    ref: 'v1.4.0'            # pin a tag/branch/SHA — never leave unpinned
    file: '/jobs/test.yml'

  # 3. remote — a full URL (must be publicly fetchable over HTTPS)
  - remote: 'https://example.com/ci/security.yml'

  # 4. template — a GitLab-maintained template shipped with the instance
  - template: 'Jobs/SAST.gitlab-ci.yml'

  # 5. component — a versioned CI/CD Catalog component (see below)
  - component: '$CI_SERVER_FQDN/my-group/ci-components/build@1.0.0'
```

Guidance:

- **Always pin `project` includes with `ref:`** to a tag or SHA. An unpinned `ref` tracks
  the default branch and makes your pipeline non-reproducible.
- Prefer `local`/`project`/`component` over `remote` — remote URLs are an availability and
  supply-chain risk and cannot be reviewed in your MR.
- Included files are merged at the top level; job names collide and override by document
  order, so namespace template jobs (e.g. `.build-template`) to avoid surprises.

## CI/CD Components & Catalog (GA in GitLab 17.0)

> **Version note:** The CI/CD Catalog and the `component:` include keyword reached
> General Availability in **GitLab 17.0**. On older self-managed instances (16.x) they are
> Beta/experimental or unavailable — fall back to `include: project` with a pinned `ref:`.

Components are reusable, versioned, parameterized pipeline units published to the CI/CD
Catalog. Reference them with a pinned version and pass `inputs:`:

```yaml
include:
  - component: '$CI_SERVER_FQDN/my-group/components/docker-build@1.2.0'
    inputs:
      image: registry.example.com/app
      tag: $CI_COMMIT_SHORT_SHA
```

Pin to a released tag (`@1.2.0`), not `@main`, for reproducibility.

## `extends:` — job template inheritance

`extends:` merges one or more "template" jobs into a job. Templates are conventionally
prefixed with `.` so they are **hidden** (not run on their own).

```yaml
.test-base:
  image: node:20.15-alpine
  before_script:
    - npm ci
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'

unit-test:
  extends: .test-base
  script: npm run test:unit

lint:
  extends: .test-base
  script: npm run lint
```

### `extends:` deep-merge vs YAML anchors

This distinction matters and is a frequent source of bugs:

- **`extends:` performs a reverse deep merge** on hashes (maps). Child keys override
  parent keys **per key**, recursively, so you can override `variables.FOO` while keeping
  `variables.BAR` from the parent. Arrays (e.g. `script`) are **replaced, not merged**.
- **YAML anchors (`&`/`*`) and `<<:` merge keys are a pure textual/structural splice**
  evaluated by the YAML parser before GitLab sees the file. They do **not** deep-merge
  nested maps the way `extends` does, and they cannot cross `include:` file boundaries
  (an anchor is only visible within the one document that defines it).

Rule of thumb: **use `extends:` for reusable jobs** (especially across `include`d files);
reserve anchors for small, local, same-file value reuse.

### Multi-level `extends`

A job can extend a template that itself extends another (up to 11 levels). Merge order
flows from the deepest parent up to the child, with the child winning per key:

```yaml
.image-base:
  image: node:20.15-alpine

.test-base:
  extends: .image-base
  before_script: [npm ci]

unit-test:
  extends: .test-base   # gets image + before_script, then adds its own script
  script: npm run test:unit
```

### `extends:` with multiple parents

```yaml
job:
  extends: [.image-base, .test-base]
```

Later entries in the list win on key conflicts. Keep the list short and the precedence
obvious.

## `!reference` — splice a value from elsewhere

`!reference` is GitLab's own tag (distinct from YAML anchors) that pulls a specific
keyword's value from another job — and, unlike anchors, it **works across `include`d
files**.

```yaml
.setup:
  script:
    - echo "common setup"

deploy:
  script:
    - !reference [.setup, script]   # splice in .setup's script steps
    - ./deploy.sh
```

Use `!reference` when you need to reuse one keyword (a `script` fragment, a `rules` list)
rather than inherit a whole job — it composes where anchors cannot.

## Choosing between them

| Need | Use |
|---|---|
| Reuse a whole job shape across files | `extends:` |
| Reuse one keyword's value (script/rules) across files | `!reference` |
| Pull in external config files / templates / components | `include:` |
| Tiny same-file value reuse | YAML anchor (`&`/`*`/`<<`) |
