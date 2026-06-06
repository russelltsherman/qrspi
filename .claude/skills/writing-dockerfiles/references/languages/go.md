# Go example Dockerfile

A complete, copy-ready multi-stage build for a Go service. It applies every
convention in this skill: multi-stage build, pinned base, layer ordering for
cache hits, non-root user, and an exec-form entrypoint. Go's static binaries
make `scratch`/distroless the natural runtime — see `references/base-images.md`.

```dockerfile
# syntax=docker/dockerfile:1

# ---- build stage ----
FROM golang:1.22-bookworm AS build
WORKDIR /src

# Dependencies first so a source edit doesn't bust the module cache.
COPY go.mod go.sum ./
RUN --mount=type=cache,target=/go/pkg/mod go mod download

# Then source, then the static build (CGO off → no libc dependency).
COPY . .
RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w" -o /out/app ./cmd/app

# ---- runtime stage ----
# distroless/static ships certs, tzdata, and a nonroot user (uid 65532); no shell.
FROM gcr.io/distroless/static-debian12:nonroot AS runtime
WORKDIR /app
COPY --from=build /out/app /app/app

USER nonroot
EXPOSE 8080
LABEL org.opencontainers.image.source="https://github.com/org/repo" \
      org.opencontainers.image.description="Go service" \
      org.opencontainers.image.licenses="Apache-2.0"

# No shell/curl on distroless — rely on the orchestrator's probes, or ship a
# tiny static healthcheck binary and use exec form (see references/runtime.md).
ENTRYPOINT ["/app/app"]
```

## Notes

- **Base:** a static (`CGO_ENABLED=0`) binary needs no libc, so `scratch` or
  `gcr.io/distroless/static` is ideal. Use `scratch` only if you `COPY` in
  `ca-certificates` and a user yourself; distroless gives you both plus the
  `nonroot` user. Pin to a `@sha256:` digest for reproducibility
  (`references/base-images.md`).
- **Caching:** the `go mod download` layer is cached until `go.mod`/`go.sum`
  change; BuildKit cache mounts persist the module and build caches across
  builds (`references/multistage-and-caching.md`).
- **Non-root:** distroless `nonroot` runs as uid 65532 — no `useradd` needed
  (`references/security.md`).
- **Signals:** a single-process Go binary as PID 1 receives `SIGTERM` directly;
  no init needed if it handles graceful shutdown (`references/runtime.md`).

## .dockerignore

```gitignore
.git
.github
.env
.env.*
*.pem
*.key
Dockerfile*
.dockerignore
*.md
bin
dist
```

See `references/multistage-and-caching.md` for the full starter template.
