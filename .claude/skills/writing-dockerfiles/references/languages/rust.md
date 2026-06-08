# Rust example Dockerfile

A complete, copy-ready multi-stage build for a Rust service. It applies every
convention in this skill: multi-stage build, pinned base, dependency-first layer
ordering, a non-root user, and an exec-form `ENTRYPOINT`. A statically linked
binary (musl target) lets the runtime be `scratch`/distroless — see
`references/base-images.md`.

```dockerfile
# syntax=docker/dockerfile:1

# ---- build stage ----
FROM rust:1.78-bookworm AS build
WORKDIR /src

# Build a static musl binary so the runtime needs no libc.
RUN rustup target add x86_64-unknown-linux-musl \
    && apt-get update && apt-get install -y --no-install-recommends musl-tools \
    && rm -rf /var/lib/apt/lists/*

# Manifests first: prime the dependency cache before copying source.
COPY Cargo.toml Cargo.lock ./
RUN --mount=type=cache,target=/usr/local/cargo/registry \
    mkdir src && echo 'fn main() {}' > src/main.rs \
    && cargo build --release --target x86_64-unknown-linux-musl \
    && rm -rf src

COPY . .
RUN --mount=type=cache,target=/usr/local/cargo/registry \
    --mount=type=cache,target=/src/target \
    cargo build --release --target x86_64-unknown-linux-musl \
    && cp target/x86_64-unknown-linux-musl/release/app /out/app

# ---- runtime stage ----
# distroless/static ships certs, tzdata, and a nonroot user (uid 65532); no shell.
FROM gcr.io/distroless/static-debian12:nonroot AS runtime
WORKDIR /app
COPY --from=build /out/app /app/app

USER nonroot
EXPOSE 8080
LABEL org.opencontainers.image.source="https://github.com/org/repo" \
      org.opencontainers.image.description="Rust service" \
      org.opencontainers.image.licenses="Apache-2.0"

# No shell/curl on distroless — rely on orchestrator probes or a tiny static
# healthcheck binary in exec form (see references/runtime.md).
ENTRYPOINT ["/app/app"]
```

## Notes

- **Base:** a static musl binary runs on `scratch` or
  `gcr.io/distroless/static`. Use `scratch` only if you also `COPY` in
  `ca-certificates`; distroless gives certs plus the `nonroot` user. If you stay
  on the default glibc target instead, use `gcr.io/distroless/cc` (ships glibc)
  for the runtime (`references/base-images.md`). Pin a digest.
- **Dependency cache trick:** building a stub `main.rs` against the manifests
  compiles dependencies into a cached layer, so editing source rebuilds only
  your crate (`references/multistage-and-caching.md`).
- **Non-root:** distroless `nonroot` (uid 65532) needs no `useradd`
  (`references/security.md`).
- **Signals:** a single-process Rust binary as PID 1 receives `SIGTERM`
  directly; no init needed if it handles graceful shutdown (`references/runtime.md`).

## .dockerignore

```gitignore
.git
.github
target
.env
.env.*
*.pem
*.key
Dockerfile*
.dockerignore
*.md
```

See `references/multistage-and-caching.md` for the full starter template.
