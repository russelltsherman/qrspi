---
name: writing-dockerfiles
description: "Author and harden production-grade Dockerfiles and container images. Use whenever the user wants to write a Dockerfile, containerize an app, optimize or shrink an image, speed up image builds, harden or secure a container build, fix a Dockerfile, or set up multi-stage builds — even if they don't say the word 'Dockerfile'. Triggers include 'write a Dockerfile for my Go/Node/Python/Java/Rust service', 'optimize this image', 'my image is huge', 'harden my container build', 'add a healthcheck', 'why won't my container stop gracefully', and 'set up a .dockerignore'."
command: /writing-dockerfiles
argument-hint: "[language | path-to-Dockerfile]"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Writing Dockerfiles

Author Dockerfiles that are small, fast to build, secure by default, and behave
correctly as a process under an orchestrator. A Dockerfile is not just a build
script — it defines the runtime contract for a container (its identity, privileges,
signal behavior, and health), so treat it with the same care as application code.

This skill gives you opinionated defaults across eight areas. The body is the
decision layer: it tells you what to do and why. Each area points to a reference
file with the concrete patterns, snippets, and edge cases — read the referenced
file before you write that part of the Dockerfile, because the details (digest
pinning syntax, cache-mount flags, secret-mount invocation) are easy to get
subtly wrong from memory.

## Workflow

1. Identify the language/runtime and how the app is built and started.
2. Choose a base image (see Base images).
3. Structure the build as multi-stage and order layers for caching; add a
   `.dockerignore` (see Multi-stage builds and layer caching).
4. Drop privileges, keep secrets out of the image, and plan scanning (see
   Security and build args).
5. Add a healthcheck and make signal handling correct (see Healthchecks and
   signal handling).
6. Pull a known-good per-language example (see Per-language examples).

Prefer building on the patterns in the reference files over inventing new ones —
they encode hard-won defaults that production images converge on anyway.

## Base images

The base image sets your image size, attack surface, available tooling, and
patch cadence — it is the single highest-leverage choice in the file.

- Pin precisely. Never use `latest`; pin to a specific tag and, for anything
  reproducible or security-sensitive, pin to a `@sha256:` digest so the build
  can't drift under you.
- Prefer the smallest base that still runs your app. Distroless and `scratch`
  give the smallest attack surface; Alpine is small but uses musl libc, which
  can break glibc-linked binaries and native modules.
- Match the base to the runtime stage, not the build stage — build can be fat,
  runtime should be lean.

Read `references/base-images.md` before choosing a base image — it covers
tag-vs-digest pinning, and when distroless vs. scratch vs. Alpine vs. a slim
distro is the right call.

## Multi-stage builds and layer caching

Multi-stage builds are the default, not an optimization. They let you compile
or install with a full toolchain in a build stage and copy only the resulting
artifact into a minimal runtime stage, so build-time tools never ship to
production.

- Use named stages (`FROM ... AS build`) and `COPY --from=build` to move only
  what's needed.
- Order layers from least- to most-frequently-changing: copy dependency
  manifests and install dependencies before copying application source, so a
  code change doesn't bust the dependency cache.
- Use cache mounts (`RUN --mount=type=cache,...`) for package-manager caches
  instead of baking them into layers.

Read `references/multistage-and-caching.md` before writing the build stages —
it has the named-stage patterns, layer-ordering rules, BuildKit cache-mount
syntax, and a `.dockerignore` template.

### .dockerignore

A `.dockerignore` keeps the build context small and prevents secrets, local
env files, `.git`, and `node_modules`/build artifacts from leaking into the
image or invalidating the cache. Always create one alongside the Dockerfile.

Read `references/multistage-and-caching.md` for a starter `.dockerignore` you
can adapt per language.

## Security and build args

Containers run with too much privilege by default. Close that gap in the
Dockerfile itself rather than relying on runtime flags everyone forgets to set.

- Run as a non-root user: create a dedicated user/group and set `USER` before
  the entrypoint. Root in a container is root on the host kernel namespace.
- Never bake secrets into the image. Do not pass secrets via `ARG` or `ENV` or
  `COPY` them in — they persist in image layers and history. Use BuildKit
  secret mounts at build time and runtime injection at run time.
- Treat build args as build-time-only, non-secret configuration; remember they
  are visible in image metadata.
- Plan for scanning (Trivy, Grype, Snyk) and keep packages minimal and patched.

Read `references/security.md` before adding `USER`, build args, or any
secret handling — it details non-root setup, the secret-mount pattern, package
hygiene, and scanner integration.

## Healthchecks and signal handling

The Dockerfile defines how your process is supervised. Getting this wrong shows
up as containers that report healthy while broken, or that take 10 seconds to
die on every deploy.

- Add a `HEALTHCHECK` that probes real readiness (an app endpoint), not just
  that the process exists.
- Use exec-form `ENTRYPOINT`/`CMD` (`["bin", "arg"]`), never shell form
  (`bin arg`). Shell form wraps your process in `/bin/sh -c`, which becomes PID 1
  and does not forward `SIGTERM`, so graceful shutdown breaks.
- If your app doesn't reap zombies or forward signals, add a tiny init
  (`tini` / `dumb-init`) as PID 1.
- Set `WORKDIR`, `EXPOSE`, and OCI `LABEL`s so the image is self-describing.

Read `references/runtime.md` before writing `HEALTHCHECK`, `ENTRYPOINT`/`CMD`,
or adding an init — it covers healthcheck tuning, exec-form pitfalls,
`tini`/`dumb-init`, and labeling.

## Per-language examples

Once the conventions above are clear, start from a complete, known-good example
for the target language rather than assembling one from scratch. Each example
applies every convention in this skill end to end.

- Go: read `references/languages/go.md` before writing a Go Dockerfile.
- Node.js: read `references/languages/node.md` before writing a Node Dockerfile.
- Python: read `references/languages/python.md` before writing a Python Dockerfile.
- Java: read `references/languages/java.md` before writing a Java Dockerfile.
- Rust: read `references/languages/rust.md` before writing a Rust Dockerfile.

(The per-language example files are added in the next slice; until then, compose
the runtime from the four topic references above.)
