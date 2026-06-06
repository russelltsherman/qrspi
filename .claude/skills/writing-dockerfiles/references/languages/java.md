# Java example Dockerfile

A complete, copy-ready multi-stage build for a JVM service (Maven shown; the
Gradle variant is noted below). It applies every convention in this skill:
multi-stage build, pinned base, dependency-first layer ordering, a non-root
user, exec-form `ENTRYPOINT`, and a real `HEALTHCHECK`.

```dockerfile
# syntax=docker/dockerfile:1

# ---- build stage ----
FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /src

# Resolve dependencies from the POM first so a source edit keeps the cache.
COPY pom.xml ./
RUN --mount=type=cache,target=/root/.m2 mvn -B -q dependency:go-offline

COPY src ./src
RUN --mount=type=cache,target=/root/.m2 mvn -B -q -DskipTests package \
    && cp target/app.jar /out/app.jar

# ---- runtime stage ----
# distroless/java ships a JRE + nonroot user (uid 65532); no shell or pkg mgr.
FROM gcr.io/distroless/java21-debian12:nonroot AS runtime
WORKDIR /app
COPY --from=build --chown=nonroot:nonroot /out/app.jar ./app.jar

USER nonroot
EXPOSE 8080
LABEL org.opencontainers.image.source="https://github.com/org/repo" \
      org.opencontainers.image.description="Java service" \
      org.opencontainers.image.licenses="Apache-2.0"

# distroless has no shell/curl — use the orchestrator's probes, or (Spring Boot)
# expose /actuator/health and probe it from outside the image.
ENTRYPOINT ["java", "-XX:MaxRAMPercentage=75.0", "-jar", "/app/app.jar"]
```

## Notes

- **Base:** `gcr.io/distroless/javaNN` for a minimal JRE runtime with a `nonroot`
  user and no shell; use `eclipse-temurin:21-jre-jammy` if you need a shell or a
  `curl`-based `HEALTHCHECK`. Build with a full Temurin JDK, ship only a JRE
  (`references/base-images.md`). Pin a digest for reproducibility.
- **Gradle variant:** swap the build stage for
  `FROM gradle:8-jdk21 AS build`, cache `--mount=type=cache,target=/home/gradle/.gradle`,
  and `gradle --no-daemon bootJar`, copying `build/libs/app.jar`.
- **Heap:** `-XX:MaxRAMPercentage` lets the JVM size its heap to the container's
  cgroup memory limit instead of the host's.
- **Non-root:** distroless `nonroot` (uid 65532) needs no `useradd`; `--chown`
  keeps the jar readable (`references/security.md`).
- **Signals:** the JVM handles `SIGTERM` and is PID 1 under exec form; no init
  needed for a typical single-process service (`references/runtime.md`).

## .dockerignore

```gitignore
.git
.github
target
build
.gradle
.env
.env.*
*.pem
*.key
Dockerfile*
.dockerignore
*.md
```

See `references/multistage-and-caching.md` for the full starter template.
