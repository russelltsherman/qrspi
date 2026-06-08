# Security and build args

Containers default to running as root with a broad package set. Close those gaps
in the Dockerfile so the image is secure regardless of how it's run.

## Run as non-root

Root inside a container is uid 0 against the host kernel — a container escape or
mounted volume then has root reach. Create a dedicated user and switch to it
before the entrypoint.

```dockerfile
# Debian/Ubuntu slim
RUN groupadd --system app && useradd --system --gid app --no-create-home app
USER app

# Alpine
RUN addgroup -S app && adduser -S -G app app
USER app
```

- Set `USER` after installing packages (which needs root) but before `ENTRYPOINT`.
- Use a high, fixed uid/gid if filesystem permissions on mounted volumes matter.
- Distroless images ship a `nonroot` user (uid 65532): `USER nonroot` or
  use the `:nonroot` tag.
- Ensure files the app must read/write are owned by that user
  (`COPY --chown=app:app ...`).

## Never bake secrets into the image

Image layers are immutable and inspectable — anything written into a layer is
recoverable from the pushed image, even if a later layer deletes it.

- **Do not** pass secrets via `ARG` or `ENV`: both end up in image metadata /
  `docker history`.
- **Do not** `COPY` secret files in, even temporarily.
- **Build-time secrets:** use BuildKit secret mounts — the secret is available
  during one `RUN` and never persisted.

  ```dockerfile
  # syntax=docker/dockerfile:1
  RUN --mount=type=secret,id=npmrc,target=/root/.npmrc npm ci
  # build with: docker build --secret id=npmrc,src=$HOME/.npmrc .
  ```

  For SSH/private-repo access, use `--mount=type=ssh`.
- **Runtime secrets:** inject at run time via the orchestrator (env from a
  secret manager, mounted secret files), never in the Dockerfile.

## Build args are not secrets

`ARG` is for build-time, **non-sensitive** configuration (versions, target
arch). Values are visible in build logs and image history. Scope them to the
stage that needs them, and give safe defaults.

```dockerfile
ARG APP_VERSION=0.0.0
ARG TARGETARCH        # auto-populated by BuildKit for multi-arch
```

## Package hygiene

- Install only what runtime needs; build tooling stays in the build stage.
- Use `--no-install-recommends` (apt) / `--no-cache` (apk) and clean lists:
  ```dockerfile
  RUN apt-get update && apt-get install -y --no-install-recommends curl \
      && rm -rf /var/lib/apt/lists/*
  ```
- Pin package versions where supply-chain integrity matters.

## Scanning

Scan images in CI and fail the build on fixable high/critical CVEs:

- **Trivy** — `trivy image --severity HIGH,CRITICAL --exit-code 1 <image>`
- **Grype** — `grype <image> --fail-on high`
- **Snyk** — `snyk container test <image>`

Scan the final runtime image (and ideally generate an SBOM, e.g.
`docker buildx build --sbom=true` or `syft`). Combine with the minimal-base
choice from `base-images.md` — fewer packages means fewer findings.
