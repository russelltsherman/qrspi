# Base images

The base image determines image size, attack surface, available tooling, libc
flavor, and how often you inherit upstream CVEs. Choose it deliberately for the
**runtime** stage; the build stage can afford to be larger.

## Pinning: tag vs. digest

- **Never use `latest`.** It is a moving target — a rebuild months later can pull
  a different OS, different libc, or a breaking runtime version with no diff in
  your Dockerfile.
- **Pin a specific tag** for readability: `python:3.12-slim`, `golang:1.22`.
- **Pin a digest** for reproducibility and supply-chain integrity. A tag can be
  re-pushed; a digest cannot.

```dockerfile
# Readable + reproducible: tag for humans, digest for the builder.
FROM python:3.12-slim@sha256:<digest>
```

Find a digest with `docker buildx imagetools inspect python:3.12-slim` or
`docker pull <image> && docker inspect --format='{{index .RepoDigests 0}}' <image>`.
Use a tool like Renovate/Dependabot to bump digests so pinning doesn't mean
never patching.

## Choosing how minimal to go

Smaller base = smaller attack surface, faster pulls, fewer CVEs — but less
debuggability and stricter linking requirements. Trade-offs:

| Base | Size | Shell/pkg mgr | Notes |
|------|------|---------------|-------|
| `scratch` | ~0 | none | Only for fully static binaries (e.g. CGO-disabled Go, static Rust). No shell, no certs — add `ca-certificates` and a user via `COPY`. |
| Distroless (`gcr.io/distroless/*`) | very small | none | Has libc, certs, tzdata, non-root `nonroot` user. No shell — exec-form only, debug via `:debug` variants. |
| Alpine (`*-alpine`) | small | `apk`, `sh` | musl libc, not glibc. Can break glibc-linked binaries, native modules, and some wheels. Great when your stack is musl-clean. |
| Slim distro (`*-slim`, `debian:*-slim`) | medium | `apt`, `bash` | glibc, easy to extend, good default when distroless/Alpine cause friction. |
| Full distro | large | full | Avoid for runtime; fine as a build stage. |

### Decision guidance

- Static binary (Go with `CGO_ENABLED=0`, static Rust)? → `scratch` or
  distroless `static`.
- Dynamically linked, glibc, want minimal? → distroless matching the language
  (`distroless/java`, `distroless/python3`, `distroless/nodejs`).
- Need a shell, native deps, or fast iteration? → a `-slim` distro.
- Reach for Alpine only when you've confirmed your binaries/wheels are
  musl-compatible — debugging musl vs. glibc breakage costs more than the size
  savings for most teams.

## Keep the runtime base patched

Even a pinned base accumulates CVEs over time. Rebuild on a cadence so you pick
up upstream security fixes, and scan the result (see `security.md`).
