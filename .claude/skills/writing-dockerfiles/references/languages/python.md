# Python example Dockerfile

A complete, copy-ready multi-stage build for a Python service. It applies every
convention in this skill: multi-stage build, pinned base, dependency-first layer
ordering, a non-root user, exec-form `ENTRYPOINT`, and a real `HEALTHCHECK`.
The pattern builds a virtualenv in the build stage and copies it into a slim
runtime so build tooling never ships.

```dockerfile
# syntax=docker/dockerfile:1

# ---- build stage ----
FROM python:3.12-bookworm AS build
WORKDIR /app
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=0

# Build the venv from manifests first so source edits don't re-install deps.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt ./
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt

# ---- runtime stage ----
FROM python:3.12-slim-bookworm AS runtime
WORKDIR /app
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# curl is only for the HEALTHCHECK; clean apt lists in the same layer.
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root user (slim is Debian-based → groupadd/useradd).
RUN groupadd --system app && useradd --system --gid app --no-create-home app

COPY --from=build /opt/venv /opt/venv
COPY --chown=app:app . .

USER app
EXPOSE 8080
LABEL org.opencontainers.image.source="https://github.com/org/repo" \
      org.opencontainers.image.description="Python service" \
      org.opencontainers.image.licenses="Apache-2.0"

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -fsS http://localhost:8080/healthz || exit 1

ENTRYPOINT ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
```

## Notes

- **Base:** `-slim` (Debian glibc) is the safe default and supports a shell +
  `curl` healthcheck. For the smallest surface use `gcr.io/distroless/python3`
  and drop the `apt` line (then probe via the orchestrator or a Python one-liner).
  Avoid Alpine unless your wheels are confirmed musl-compatible — many ship
  glibc-only manylinux wheels (`references/base-images.md`). Pin a digest.
- **Venv copy:** building the venv in a fat stage and copying `/opt/venv` keeps
  compilers/headers out of runtime (`references/multistage-and-caching.md`).
- **Non-root + ownership:** `USER app` after the installs; `--chown=app:app` so
  the app owns its code (`references/security.md`).
- **Signals:** run a single process under an exec-form entrypoint; if a worker
  manager forks children that orphan, add `tini`/`dumb-init` (`references/runtime.md`).

## .dockerignore

```gitignore
.git
.github
__pycache__
*.pyc
.venv
.pytest_cache
.mypy_cache
.env
.env.*
*.pem
*.key
Dockerfile*
.dockerignore
*.md
```

See `references/multistage-and-caching.md` for the full starter template.
