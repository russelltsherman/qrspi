# Multi-stage builds, layer caching, and .dockerignore

Multi-stage builds and good layer ordering are what make images both small and
fast to rebuild. The goal: ship only the runtime artifact, and structure layers
so the expensive steps (dependency installs) are cached across code changes.

## Multi-stage pattern

Use a fat build stage with the full toolchain, then copy only the artifact into
a minimal runtime stage. Build-time tools (compilers, headers, package caches)
never reach production this way.

```dockerfile
# ---- build stage ----
FROM golang:1.22 AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o /out/app ./cmd/app

# ---- runtime stage ----
FROM gcr.io/distroless/static AS runtime
COPY --from=build /out/app /app
ENTRYPOINT ["/app"]
```

- Name every stage (`AS build`, `AS runtime`) and reference with
  `COPY --from=<stage>`.
- You can have multiple build stages (e.g. one for deps, one for assets) and
  copy from each.
- The last stage is what gets shipped — keep it minimal.

## Layer ordering for cache hits

Docker caches each layer and invalidates a layer (and all below it) when its
inputs change. Order from **least- to most-frequently-changing**:

1. Base image
2. System packages
3. Dependency manifests + dependency install
4. Application source
5. Build/compile

The key move: **copy dependency manifests and install dependencies before
copying source**, so editing a source file doesn't re-run the dependency
install.

```dockerfile
# Good: deps cached until manifests change.
COPY package.json package-lock.json ./
RUN npm ci
COPY . .

# Bad: any source edit busts the npm ci layer.
COPY . .
RUN npm ci
```

## BuildKit cache mounts

Cache mounts persist a package manager's cache *across builds* without baking it
into a layer — faster rebuilds, smaller images. Requires BuildKit (default in
modern Docker).

```dockerfile
# npm
RUN --mount=type=cache,target=/root/.npm npm ci

# pip
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt

# apt (also disable the clean-on-exit so the cache survives)
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends curl
```

Use `--mount=type=cache` for caches and bind mounts (`--mount=type=bind`) for
read-only access to source instead of copying when appropriate.

## .dockerignore

A `.dockerignore` shrinks the build context (faster sends, better cache
stability) and stops secrets, VCS metadata, and local build artifacts from
leaking into the image. Always add one next to the Dockerfile.

Starter template — trim/extend per language:

```gitignore
# VCS and CI
.git
.gitignore
.github

# Local env and secrets — never ship these
.env
.env.*
*.pem
*.key
secrets/

# Dependencies / build output (rebuilt inside the image)
node_modules
dist
build
target
__pycache__
*.pyc
.venv

# Docker and docs
Dockerfile*
.dockerignore
docker-compose*.yml
*.md

# Editor / OS cruft
.idea
.vscode
.DS_Store
```

Note: `Dockerfile` is in the build context even when ignored from `COPY .`;
ignoring it just keeps `COPY . .` from baking it into the image.
