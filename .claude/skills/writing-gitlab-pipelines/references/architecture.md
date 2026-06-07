# Pipeline Architecture (Worked Examples)

End-to-end, copy-adaptable layouts showing how the individual keywords compose into whole
pipelines. Three worked examples, increasing in scope.

## 1. Minimal build → test → deploy

A clean starting point: pinned image, lockfile cache, a DAG via `needs`, artifacts handed
forward, and a manually gated production deploy.

```yaml
stages: [build, test, deploy]

default:
  image: node:20.15-alpine

variables:
  npm_config_cache: '.npm'

workflow:
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'

build:
  stage: build
  cache:
    key: { files: [package-lock.json] }
    paths: ['.npm/', 'node_modules/']
    policy: pull-push
  script:
    - npm ci
    - npm run build
  artifacts:
    paths: [dist/]
    expire_in: 1 week

test:
  stage: test
  needs: [build]                # starts as soon as build's artifacts are ready
  cache:
    key: { files: [package-lock.json] }
    paths: ['.npm/', 'node_modules/']
    policy: pull               # consumer: read-only cache
  script: npm test
  artifacts:
    when: always
    reports:
      junit: junit.xml

deploy-production:
  stage: deploy
  needs: [test]
  environment:
    name: production
    url: https://app.example.com
  resource_group: production    # no concurrent prod deploys
  script: ./deploy.sh production
  rules:
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
      when: manual              # human gate
```

## 2. Mature: lint · build · test · security · deploy · cleanup

A production-grade single pipeline: a `.base` template via `extends:`, DAG ordering,
included security scanners, a per-MR review app with `on_stop`, and a gated prod deploy.

```yaml
stages: [validate, build, test, security, deploy, cleanup]

include:
  - template: 'Jobs/SAST.gitlab-ci.yml'
  - template: 'Jobs/Secret-Detection.gitlab-ci.yml'
  - template: 'Jobs/Dependency-Scanning.gitlab-ci.yml'

default:
  image: node:20.15-alpine
  interruptible: true           # superseded pipelines auto-cancel

.node-base:                     # reusable template (hidden job)
  cache:
    key: { files: [package-lock.json] }
    paths: ['.npm/', 'node_modules/']
    policy: pull
  before_script: [npm ci]

lint:
  stage: validate
  extends: .node-base
  script: npm run lint

build:
  stage: build
  extends: .node-base
  cache:
    key: { files: [package-lock.json] }
    paths: ['.npm/', 'node_modules/']
    policy: pull-push           # producer warms the cache
  script: npm run build
  artifacts:
    paths: [dist/]
    expire_in: 1 week

unit-test:
  stage: test
  extends: .node-base
  needs: [build]
  script: npm run test:unit
  artifacts:
    when: always
    reports:
      junit: junit.xml
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml

# SAST / Secret-Detection / Dependency-Scanning jobs come from the includes
# and run in the `test`/`security` stages; pin them into `security` if needed.

deploy-review:
  stage: deploy
  needs: [build, unit-test]
  environment:
    name: review/$CI_COMMIT_REF_SLUG
    url: https://$CI_COMMIT_REF_SLUG.review.example.com
    on_stop: stop-review
    auto_stop_in: 3 days
  script: ./deploy-review.sh
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'

stop-review:
  stage: cleanup
  environment:
    name: review/$CI_COMMIT_REF_SLUG
    action: stop
  variables: { GIT_STRATEGY: none }
  script: ./teardown-review.sh
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
      when: manual

deploy-production:
  stage: deploy
  needs: [build, unit-test]
  environment: { name: production, url: https://app.example.com }
  resource_group: production
  script: ./deploy.sh production
  rules:
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
      when: manual
```

## 3. Parent-child and multi-project pipelines

For large monorepos or cross-repo orchestration, split work with `trigger:`.

### Parent-child (one repo, split config)

The parent triggers a **child pipeline** defined by another YAML file in the same repo.
Use it to keep per-component config local and only run the relevant child when that
component changes.

```yaml
# .gitlab-ci.yml (parent)
stages: [triggers]

frontend:
  stage: triggers
  trigger:
    include: 'frontend/.gitlab-ci.yml'
    strategy: depend            # parent reflects child's status
  rules:
    - changes: ['frontend/**/*']

backend:
  stage: triggers
  trigger:
    include: 'backend/.gitlab-ci.yml'
    strategy: depend
  rules:
    - changes: ['backend/**/*']
```

- `strategy: depend` makes the parent job succeed/fail with the child pipeline.
- In the child, `$CI_PIPELINE_SOURCE == "parent_pipeline"` identifies the context.

### Multi-project (cross-repo)

Trigger a pipeline in a **different project** — e.g. an app pipeline kicks the deploy
pipeline in an infra repo:

```yaml
deploy-infra:
  stage: deploy
  trigger:
    project: 'ops/infrastructure'
    branch: main
    strategy: depend
  rules:
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
```

Pass data downstream with `variables:` on the trigger job; the downstream pipeline sees
`$CI_PIPELINE_SOURCE == "pipeline"`.

## Choosing a shape

| Situation | Shape |
|---|---|
| Single app, < ~15 jobs | One pipeline + `needs` DAG (examples 1–2) |
| Monorepo, independent components | Parent-child with `changes:` rules (example 3) |
| Orchestrate another repo's pipeline | Multi-project `trigger:project` (example 3) |
| Reuse jobs across many repos | `include` + `extends` / CI-CD components (`includes-extends.md`) |
