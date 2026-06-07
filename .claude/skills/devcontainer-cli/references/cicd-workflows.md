# devcontainers in CI/CD — GitHub Actions reference

Running the **same** dev container in CI that developers use locally eliminates
"works on my machine" drift: tests run in the identical environment. The
`devcontainers/ci` GitHub Action wraps the `@devcontainers/cli` for this.

---

## `devcontainers/ci` action — basic usage

Build the dev container and run a command inside it:

```yaml
name: CI
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build dev container and run tests
        uses: devcontainers/ci@v0.3
        with:
          runCmd: npm test
```

`runCmd` executes inside the freshly built dev container (equivalent to
`devcontainer up` followed by `devcontainer exec`). The action reads
`.devcontainer/devcontainer.json` from the checked-out repo.

---

## Pre-build and push

Build the image **once** in CI and push it to a registry so subsequent runs —
and developers' local `up` — pull a ready image instead of rebuilding:

```yaml
      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Pre-build and push dev container image
        uses: devcontainers/ci@v0.3
        with:
          imageName: ghcr.io/${{ github.repository }}-dev
          imageTag: latest
          push: always
```

`push: always` publishes the built image. `push: filter` (the default for some
setups) pushes only on the default branch; `push: never` builds without
pushing.

---

## Registry cache (`--cache-from`)

To make builds fast, seed the layer cache from a previously pushed image. The
action exposes this as `cacheFrom`, which maps to the CLI's `--cache-from`
(and the `build.cacheFrom` key in `devcontainer.json`):

```yaml
      - uses: devcontainers/ci@v0.3
        with:
          imageName: ghcr.io/${{ github.repository }}-dev
          cacheFrom: ghcr.io/${{ github.repository }}-dev:latest
          push: always
          runCmd: npm test
```

The build pulls cached layers from the registry image referenced by
`cacheFrom`; unchanged layers are reused, so only changed layers rebuild. This
is the same `--cache-from` mechanism available to `devcontainer build` directly
(see `cli-commands.md`).

---

## Reusing the CI image as the local `image`

Once CI pre-builds and pushes the image, point local development at that same
published image so developers skip the Dockerfile build entirely. Swap the
`build` block in `devcontainer.json` for an `image` reference:

```jsonc
{
  // was: "build": { "dockerfile": "Dockerfile" }
  "image": "ghcr.io/org/repo-dev:latest"
}
```

Now `devcontainer up` (local) and the CI `runCmd` resolve to the identical,
already-built image — a single source of truth for the environment. See
`devcontainer-json-schema.md` for the `image` vs `build` tradeoff.

---

## Putting it together

A typical pipeline:

1. On the default branch: `devcontainers/ci` pre-builds, tags, and **pushes**
   the dev image to GHCR, using `cacheFrom` the prior tag for speed.
2. On PRs: `devcontainers/ci` runs `runCmd: npm test` with `cacheFrom` the
   pushed image, so CI reuses cached layers.
3. Locally: `devcontainer.json` sets `image:` to the pushed tag, so developers
   pull the same artifact CI validated.
