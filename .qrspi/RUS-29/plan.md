# Implementation Plan — Create a new agent skill called writing-dockerfiles

**Structure basis:** structure.md @ 2026-05-31T16:11:00Z
**Generated:** 2026-05-31T16:14:00Z
**Status:** draft
**Total steps:** 34

## Slice 1: Skill scaffold, SKILL.md body, and convention references

### Setup

1. ✨ Create directory `.claude/skills/writing-dockerfiles/` and `.claude/skills/writing-dockerfiles/references/` (mkdir -p).
2. ✨ Create `.claude/skills/writing-dockerfiles/SKILL.md` with frontmatter only first: `name: writing-dockerfiles`, a trigger-bearing `description` (per `SkillFrontmatter` contract; design Decision 2 Option A — no `command`/`argument-hint`). Description must say what the skill does and "Use when… / Do NOT use for… (Compose, orchestration, CI/CD, runtime config)".

### Core Logic

3. ⚠️ Modify `SKILL.md` — add body section "Base image selection" (concise checklist) ending with a pointer: "See `references/base-images.md`."
4. ⚠️ Modify `SKILL.md` — add body section "Multi-stage builds & layer caching" pointing to `references/multi-stage-and-caching.md`.
5. ⚠️ Modify `SKILL.md` — add body section ".dockerignore" pointing to `references/dockerignore.md`.
6. ⚠️ Modify `SKILL.md` — add body section "Security" (non-root, runtime secrets, scanning) pointing to `references/security.md`.
7. ⚠️ Modify `SKILL.md` — add body section "Build args & env" and "Production readiness" pointing to `references/production-readiness.md`.
8. ⚠️ Modify `SKILL.md` — add body section "Healthchecks & signal handling" (warn against shell form, recommend exec form + tini/dumb-init) pointing to `references/signals-and-healthchecks.md`.
9. ⚠️ Modify `SKILL.md` — add a "Language patterns" placeholder section noting per-language examples live in `references/` (links populated in Slice 2). Keep the body a checklist + pointers only; depth lives in references (body-size contract).
10. ✨ Create `references/base-images.md` — minimal bases; scratch for static (Go/Rust), distroless for interpreted/JIT (Python/Node/Java); pin tags then digests; official/verified publishers (ref structure Contracts).
11. ✨ Create `references/multi-stage-and-caching.md` — multi-stage with named `AS` stages; copy only final artifacts; least→most-frequently-changed ordering; manifests before source; combine RUN with `&&`; `--mount=type=cache`; cache-bust ARGs last.
12. ✨ Create `references/dockerignore.md` — always include `.dockerignore`; exclude `.git/`, `node_modules/`, `__pycache__/`, build artifacts, IDE configs; exclude secrets (`.env`, keys, `.aws/`); sparing documented `!` exceptions.
13. ✨ Create `references/security.md` — create dedicated non-root user (`addgroup`/`adduser`) + `USER`; never embed secrets via ARG/ENV/COPY, inject at runtime; `--mount=type=secret` for build secrets; remove package caches in same RUN layer; explicit fs permissions; avoid unnecessary packages; pin `apt-get install` versions; scan with Trivy/Grype/Snyk in CI.
14. ✨ Create `references/signals-and-healthchecks.md` — exec form (JSON array) for ENTRYPOINT/CMD; never shell form (wraps in `/bin/sh -c`, swallows signals); tini/dumb-init for zombie reaping; `STOPSIGNAL`; ENTRYPOINT binary + CMD args; HEALTHCHECK interval 10-30s / timeout 2-5s / retries 3 / `--start-period`; note k8s probes override Docker HEALTHCHECK.
15. ✨ Create `references/production-readiness.md` — OCI `LABEL org.opencontainers.image.*`; `EXPOSE` (doc only); `WORKDIR` not `cd`; `COPY` over `ADD`; ARG (build-time) vs ENV (runtime) with documented ARGs; never secrets as ARG.

### Tests

16. ✨ Create `scripts/validate_dockerfile_skill.py` — static validator. Functions per validation contract: parse YAML frontmatter (fail if unparseable or `name != "writing-dockerfiles"` or name != dir); body line count ≤ 500 and token estimate ≤ ~5000; collect `references/*.md` on disk and reference paths cited in body; assert bidirectional integrity (no orphan file, no dangling link). Language-coverage + example-lint checks are present but gated behind a flag default-off until Slice 2 enables them. Degrade gracefully: if hadolint/`docker` absent, skip lint with a printed note. Exit non-zero on any failure.
17. Run: `python scripts/validate_dockerfile_skill.py`
   - **Expected:** exits 0; prints body line/token counts within budget and "reference integrity OK".
18. ✨ Add a negative-test invocation: temporarily introduce a dangling reference link in a scratch copy (or a `--selftest` mode in the validator) and confirm the validator exits non-zero, proving the dangling-link check works. Revert any scratch edit.

### Verify Slice 1

19. **Checkpoint:** `python scripts/validate_dockerfile_skill.py && wc -l .claude/skills/writing-dockerfiles/SKILL.md`
    - [ ] Validator exits 0.
    - [ ] `SKILL.md` ≤ 500 lines and within token budget.
    - [ ] All eight convention areas present in body (base images, multi-stage, layer caching, .dockerignore, security, build args, healthchecks, signal handling).
    - [ ] Security body covers non-root + secrets + scanning; signal section warns against shell form and recommends exec form + init process.
    - [ ] Every `references/*.md` is linked from the body and every body reference link resolves (no dangling links).
    - [ ] Negative test (step 18) confirms the dangling-link check fires.

---

## Slice 2: Per-language example Dockerfiles in references

### Setup

20. ✨ Create `references/languages-go.md` — pattern prose + one complete example Dockerfile: builder `golang:<pinned>-alpine AS builder`, `CGO_ENABLED=0`, `-ldflags="-s -w"`, multi-stage copy of static binary to `scratch`, non-root via numeric `USER`, exec-form ENTRYPOINT.
21. ✨ Create `references/languages-node.md` — pattern prose + complete example: builder installs with `npm ci --omit=dev`, copy `node_modules` + app to distroless/Alpine runtime, non-root `USER`, tini/dumb-init or distroless init, exec-form CMD, HEALTHCHECK.
22. ✨ Create `references/languages-python.md` — pattern prose + complete example: builder uses pip/uv, copy site-packages or venv to `python:<pinned>-slim`/distroless, non-root `USER`, exec-form ENTRYPOINT, `.dockerignore` note.
23. ✨ Create `references/languages-java.md` — pattern prose + complete example: jlink custom minimal JRE on Eclipse Temurin builder, copy JRE + jar to minimal runtime, GraalVM native-image note for microservices, non-root `USER`, exec-form ENTRYPOINT.
24. ✨ Create `references/languages-rust.md` — pattern prose + complete example: builder `--release`, copy static binary to `scratch` (or distroless), non-root, exec-form ENTRYPOINT.

### Core Logic

25. ⚠️ Modify `SKILL.md` — populate the "Language patterns" section to link all five `references/languages-*.md` files (Go, Node.js, Python, Java, Rust).
   - **Current:** placeholder section noting examples live in references (from Slice 1 step 9).
   - **After:** section listing each language with a one-line note and a relative link to its reference file.
26. ⚠️ Modify `SKILL.md` — confirm body still ≤ 500 lines after the language section; trim prose if needed (body-size contract).

### Tests

27. ⚠️ Modify `scripts/validate_dockerfile_skill.py` — enable the language-coverage assertion: require `languages-{go,node,python,java,rust}.md` to exist and be linked from the body.
28. ⚠️ Modify `scripts/validate_dockerfile_skill.py` — enable example linting: extract the fenced Dockerfile block from each `languages-*.md`; if hadolint present run it; elif `docker` present run `docker build --check` on the extracted file; else structural parse (valid instruction keywords, ≥2 `FROM` for multi-stage, exec-form ENTRYPOINT/CMD `[`...`]`, a `USER` non-root line).
29. Run: `python scripts/validate_dockerfile_skill.py`
   - **Expected:** exits 0 with language-coverage + example checks enabled; prints per-example lint/parse result (or "linter unavailable, structural parse OK").

### Verify Slice 2

30. **Checkpoint:** `python scripts/validate_dockerfile_skill.py`
    - [ ] All five `languages-*.md` exist and are linked from the body.
    - [ ] Each example Dockerfile passes hadolint / `docker build --check` where available, else structural parse.
    - [ ] Each example reflects its language's ticket pattern (Go→scratch + CGO_ENABLED=0; Node→`npm ci --omit=dev`; Python→venv/site-packages to slim/distroless; Java→jlink/Temurin; Rust→`--release` to scratch).
    - [ ] `SKILL.md` still ≤ 500 lines.
31. **Acceptance sweep:** confirm every ticket acceptance criterion is satisfiable from the produced files (directory structure + valid frontmatter; body under budget; references present; all eight conventions; ≥1 example per language; security non-root/secrets/scanning; signal shell-form warning + exec form + init process).

---

## Build-path note (skill-creator)

32. The ticket's process step 1 ("use the Anthropic skill builder skill") and the global directive require skill creation to go through the host-level **skill-creator** skill and its eval loop. skill-creator is not in `REPO_ROOT` (design Q5/OQ1), so the QRSPI implementer cannot invoke it from inside the worktree. Resolution options for the human (OQ1): (a) treat this plan's in-repo authored skill + `validate_dockerfile_skill.py` as the deliverable, optionally re-running it through skill-creator's eval loop out-of-band in the host before merge; or (b) hand the approved design/structure to a host session that runs skill-creator to author/validate the same files. Implementation steps above assume (a). Confirm before implementing.

## Rollback Notes

- Steps 1–15, 20–26: pure new-file/edit additions under `.claude/skills/writing-dockerfiles/`. Rollback = delete the skill directory; nothing else references it (discovery is directory-based, no manifest to revert).
- Step 16 / 27–28: `scripts/validate_dockerfile_skill.py` is new and standalone. Rollback = delete the file; no existing eval tooling imports it.
- No DB migrations, no config changes, no destructive ops. No `settings.json` or manifest edits (none exist). Fully reversible by file deletion.
