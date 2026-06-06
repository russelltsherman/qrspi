# Runtime: healthchecks, signal handling, and metadata

The Dockerfile defines how the container behaves as a supervised process. These
settings determine whether orchestrators can tell the container is healthy and
whether it shuts down cleanly on deploy.

## Healthchecks

A `HEALTHCHECK` lets Docker/Compose mark a container healthy/unhealthy. Probe
*real readiness* (an app endpoint), not just process existence.

```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -fsS http://localhost:8080/healthz || exit 1
```

- `--start-period` gives slow-starting apps grace before failures count.
- Keep the probe cheap and dependency-light; a heavy probe can itself cause
  load or false unhealthy states.
- On distroless/`scratch` there's no `curl`/`sh`. Either ship a tiny static
  healthcheck binary and use exec form, or rely on the orchestrator's own probes
  (Kubernetes liveness/readiness) and omit `HEALTHCHECK`. Don't assume a shell
  exists.

Note: Kubernetes ignores the image `HEALTHCHECK` and uses its own probes — set
both intentionally depending on where the image runs.

## Signal handling — exec form is mandatory

Always use **exec form** for `ENTRYPOINT` and `CMD`:

```dockerfile
ENTRYPOINT ["/app"]          # exec form — /app is PID 1, receives SIGTERM
CMD ["--serve", "--port", "8080"]
```

Never use shell form:

```dockerfile
ENTRYPOINT /app --serve      # shell form — runs as `/bin/sh -c "/app --serve"`
```

Shell form wraps the command in `/bin/sh -c`, so the **shell** becomes PID 1.
Most shells don't forward `SIGTERM` to children, so on `docker stop` /
orchestrator shutdown your app never gets the signal — it's `SIGKILL`ed after
the grace period (typically 10s), breaking graceful shutdown and slowing every
deploy.

Exec form has no shell, so there's no variable expansion or `&&`. If you need
those, call the shell explicitly (`ENTRYPOINT ["/bin/sh", "-c", "..."]`) — but
then handle signals yourself (e.g. `exec` the real process so it takes over PID 1).

## Init process (zombie reaping + signal forwarding)

If your app spawns child processes or doesn't reap zombies / forward signals,
run a tiny init as PID 1:

```dockerfile
# tini (often available as a package or via Docker's --init flag)
ENTRYPOINT ["/usr/bin/tini", "--", "/app"]

# dumb-init
ENTRYPOINT ["dumb-init", "--", "/app"]
```

`tini`/`dumb-init` correctly reap zombies and forward signals to your process.
`docker run --init` injects tini without changing the Dockerfile, but baking it
in makes the image correct everywhere. Single-process apps that already handle
`SIGTERM` and don't fork may not need an init.

## Make the image self-describing

```dockerfile
WORKDIR /app                              # absolute working dir; avoid relative paths
EXPOSE 8080                               # documents the listening port (informational)
LABEL org.opencontainers.image.source="https://github.com/org/repo" \
      org.opencontainers.image.description="My service" \
      org.opencontainers.image.licenses="Apache-2.0"
```

- `WORKDIR` creates the dir and sets it; prefer it over `cd` in `RUN`.
- `EXPOSE` is documentation/metadata — it does not publish ports.
- Use OCI `org.opencontainers.image.*` labels so registries and tooling can link
  the image back to its source, revision, and license.
