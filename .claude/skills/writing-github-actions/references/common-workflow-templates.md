# Common Workflow Templates

Copy-and-adapt skeletons, from a single-job CI check through a multi-job deploy
pipeline, plus reusable-workflow (`workflow_call`) and composite-action shells.
All `uses:` are SHA-pinned per `security-hardening-checklist.md` §1 (re-pin to
current SHAs).

## 1. Single-job CI

```yaml
name: ci
on:
  push:
    branches: [main]
  pull_request:
permissions:
  contents: read
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true
jobs:
  test:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2
      - uses: actions/setup-node@39370e3970a6d050c480ffad4ff0ed4d3fdee5af # v4.1.0
        with:
          node-version: '22'
          cache: npm
      - run: npm ci
      - run: npm test
```

## 2. Multi-job pipeline with dependencies (build → deploy)

```yaml
name: deploy
on:
  push:
    branches: [main]
permissions: {}
concurrency:
  group: deploy-${{ github.ref }}
  cancel-in-progress: false   # never cancel an in-flight prod deploy
jobs:
  build:
    runs-on: ubuntu-24.04
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2
      - run: make build
      - uses: actions/upload-artifact@b4b15b8c7c6ac21ea08fcf65892d2ee8f75cf882 # v4.4.3
        with:
          name: dist
          path: dist/

  deploy:
    needs: build               # runs only after build succeeds
    runs-on: ubuntu-24.04
    environment: production     # required reviewers + scoped secrets
    permissions:
      id-token: write           # OIDC — oidc-setup-patterns.md
      contents: read
    steps:
      - uses: actions/download-artifact@fa0a91b85d4f404e444e00e005971372dc801d16 # v4.1.8
        with:
          name: dist
          path: dist/
      - run: ./deploy.sh dist/
```

Key wiring: `needs:` orders jobs; artifacts pass build outputs across the
job boundary (each job is a fresh runner with no shared filesystem).

## 3. Reusable workflow (`workflow_call`)

Centralize a pipeline once; call it from many repos/workflows. Use for **whole
jobs** that need their own runner, secrets, or matrix.

```yaml
# .github/workflows/reusable-node-ci.yml  (the callee)
name: reusable-node-ci
on:
  workflow_call:
    inputs:
      node-version:
        type: string
        default: '22'
    secrets:
      NPM_TOKEN:
        required: false
permissions:
  contents: read
jobs:
  test:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2
      - uses: actions/setup-node@39370e3970a6d050c480ffad4ff0ed4d3fdee5af # v4.1.0
        with:
          node-version: ${{ inputs.node-version }}
          cache: npm
      - run: npm ci
      - run: npm test
```

```yaml
# the caller
jobs:
  ci:
    uses: ./.github/workflows/reusable-node-ci.yml   # or OWNER/REPO/...@SHA
    with:
      node-version: '20'
    secrets:
      NPM_TOKEN: ${{ secrets.NPM_TOKEN }}
    permissions:
      contents: read
```

- Pin **cross-repo** reusable workflows to a SHA, same as actions.
- A called workflow gets its own runner(s); inputs are typed; secrets are
  explicit (or `secrets: inherit`).

## 4. Composite action (`runs.using: composite`)

Bundle a **sequence of steps** that run inline within a caller's job (same
runner). Use for shared step logic that does not need its own job/runner.

```yaml
# .github/actions/setup-toolchain/action.yml
name: setup-toolchain
description: Checkout-independent toolchain setup
inputs:
  node-version:
    description: Node version
    default: '22'
runs:
  using: composite
  steps:
    - uses: actions/setup-node@39370e3970a6d050c480ffad4ff0ed4d3fdee5af # v4.1.0
      with:
        node-version: ${{ inputs.node-version }}
        cache: npm
    - run: npm ci
      shell: bash        # REQUIRED on every composite run: step
```

```yaml
# caller
steps:
  - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2
  - uses: ./.github/actions/setup-toolchain
    with:
      node-version: '20'
```

Reusable-workflow vs composite-action: see the decision section in `SKILL.md`.
