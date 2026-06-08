# Node.js example Dockerfile

A complete, copy-ready multi-stage build for a Node.js service. It applies every
convention in this skill: multi-stage build, pinned base, dependency-first layer
ordering, a non-root user, exec-form `CMD`, and a real `HEALTHCHECK`.

```dockerfile
# syntax=docker/dockerfile:1

# ---- dependencies stage ----
FROM node:20-bookworm-slim AS deps
WORKDIR /app
# Manifests first so editing source doesn't re-run npm ci.
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci --omit=dev

# ---- build stage (transpile/bundle if needed) ----
FROM node:20-bookworm-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci
COPY . .
RUN npm run build

# ---- runtime stage ----
# distroless/nodejs ships node + a nonroot user, no shell or package manager.
FROM gcr.io/distroless/nodejs20-debian12:nonroot AS runtime
WORKDIR /app
ENV NODE_ENV=production
COPY --from=deps  --chown=nonroot:nonroot /app/node_modules ./node_modules
COPY --from=build --chown=nonroot:nonroot /app/dist        ./dist
COPY --chown=nonroot:nonroot package.json ./

USER nonroot
EXPOSE 8080
LABEL org.opencontainers.image.source="https://github.com/org/repo" \
      org.opencontainers.image.description="Node.js service" \
      org.opencontainers.image.licenses="Apache-2.0"

# distroless has no shell/curl; probe from inside node, or use orchestrator probes.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD ["node", "-e", "fetch('http://localhost:8080/healthz').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"]

# Image entrypoint is `node`; CMD supplies the script (exec form).
CMD ["dist/server.js"]
```

## Notes

- **Base:** `gcr.io/distroless/nodejs20` for a minimal runtime with a `nonroot`
  user and no shell; use `node:20-bookworm-slim` instead if you need a shell or
  native build tooling at runtime. Avoid Alpine unless your native modules are
  confirmed musl-clean (`references/base-images.md`). Pin a digest for repro.
- **Dev deps stay out of runtime:** `npm ci --omit=dev` in the `deps` stage; the
  fat `build` stage (with dev deps) never ships (`references/multistage-and-caching.md`).
- **Non-root + ownership:** `--chown=nonroot:nonroot` so the app can read its
  files as uid 65532 (`references/security.md`).
- **Signals/zombies:** Node doesn't reap child processes; if your app forks,
  add `tini`/`dumb-init` as PID 1 or run with `--init` (`references/runtime.md`).

## .dockerignore

```gitignore
.git
.github
node_modules
dist
build
npm-debug.log
.env
.env.*
*.pem
*.key
Dockerfile*
.dockerignore
*.md
```

See `references/multistage-and-caching.md` for the full starter template.
