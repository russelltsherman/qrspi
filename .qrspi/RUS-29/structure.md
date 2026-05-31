# Structure Outline — Create a new agent skill called writing-dockerfiles

**Design basis:** design.md @ 2026-05-31T16:08:00Z
**Generated:** 2026-05-31T16:11:00Z
**Status:** draft

## New Types

This is a content/documentation skill, not executable software. There are no programmatic types. The "types" here are the file artifacts and their required shapes (contracts below).

- `SkillFrontmatter { name: kebab-string (== dir name), description: trigger-bearing string }` — YAML frontmatter block of `SKILL.md`. `allowed-tools` optional (design Decision 2, Option A).
- `ReferenceFile { topic: single coherent subject, linked-from: SKILL.md body via relative path }` — each file under `references/`.

## Modified Types

None. No existing skill, eval, manifest, or settings file is modified (ref: design.md §Delta — discovery is directory-based, no registry edit).

## Contracts

- `SKILL.md` body references each `references/<file>.md` by bare relative path in prose (e.g., "See `references/security.md`"), mirroring `qrspi-work`'s style (ref: design.md §Delta, Decision 1).
- Reference integrity is **bidirectional**: every file in `references/` is linked from the body, and every reference path the body names exists on disk (ref: design.md Risk "Dangling reference links").
- Body size contract: ≤ 500 lines and ≤ ~5000 tokens (acceptance criterion; ref: design.md Decision 1/Risk-1).
- Coverage contract: the body addresses all eight convention areas — base image selection, multi-stage builds, layer caching, `.dockerignore`, security, build args, healthchecks, signal handling.
- Example contract: `references/` contains ≥ 1 complete, structurally valid example Dockerfile for each of Go, Node.js, Python, Java, Rust.
- Security contract: guidance explicitly covers non-root execution, secrets management (runtime + `--mount=type=secret`), and image scanning (Trivy/Grype/Snyk).
- Signal-handling contract: explicitly warns against shell form and recommends exec form (JSON array) plus an init process (tini/dumb-init).
- Validation contract (`validate.py` or equivalent): exits non-zero on frontmatter parse failure, oversize body, dangling reference link (either direction), or a missing required language example; runs hadolint/`docker build --check` on examples when available, else structural parse (ref: design.md Decision 3).

## Slice 1: Skill scaffold, SKILL.md body, and convention references

**Goal:** A discoverable, structurally complete `writing-dockerfiles` skill whose SKILL.md body covers all eight convention areas within the size budget, with the convention reference files it points to present — and a validator proving frontmatter parses, the body is within budget, and reference links are not dangling. This is independently verifiable end-to-end before any language example exists.

**Files touched:**

- ✨ `.claude/skills/writing-dockerfiles/SKILL.md` — frontmatter (`name: writing-dockerfiles`, trigger-bearing `description`) + concise body: the eight convention areas as an opinionated checklist, each pointing to its reference; scope exclusions (no Compose/orchestration/CI-CD/runtime config).
- ✨ `.claude/skills/writing-dockerfiles/references/base-images.md` — minimal bases, scratch/distroless guidance, tag→digest pinning, official/verified publishers.
- ✨ `.claude/skills/writing-dockerfiles/references/multi-stage-and-caching.md` — multi-stage, named `AS` stages, layer ordering, manifest-before-source, `--mount=type=cache`, cache-bust ARG placement.
- ✨ `.claude/skills/writing-dockerfiles/references/security.md` — non-root user creation + `USER`, runtime secrets + `--mount=type=secret`, cache/temp cleanup in-layer, version pinning, image scanning (Trivy/Grype/Snyk).
- ✨ `.claude/skills/writing-dockerfiles/references/signals-and-healthchecks.md` — exec vs shell form, tini/dumb-init, `STOPSIGNAL`, ENTRYPOINT+CMD split, HEALTHCHECK interval/timeout/retries/start-period, k8s-probe override note.
- ✨ `.claude/skills/writing-dockerfiles/references/dockerignore.md` — required excludes, sensitive-file excludes, sparing documented `!` exceptions.
- ✨ `.claude/skills/writing-dockerfiles/references/production-readiness.md` — OCI labels, `EXPOSE`, `WORKDIR`, `COPY` over `ADD`, build-arg vs env discipline.
- ✨ `scripts/validate_dockerfile_skill.py` (or `.claude/skills/writing-dockerfiles/scripts/validate.py`) — static validator implementing the validation contract; degrades gracefully when hadolint/docker absent. (Final location to be set in Plan; keep within repo.)

**Verification:**
- [ ] `python <validator>` exits 0: frontmatter parses, `name == "writing-dockerfiles"` and matches dir, body ≤ 500 lines and ≤ ~5000 tokens, every `references/*.md` linked from body and every body link resolves.
- [ ] Manual check: all eight convention areas present in the body; security covers non-root + secrets + scanning; signal section warns against shell form and recommends exec form + init process.
- [ ] `wc -l .claude/skills/writing-dockerfiles/SKILL.md` confirms ≤ 500.
- [ ] Validator intentionally fails when a body link is broken (negative test) to prove the dangling-link check works.

**Context cost:** L
**Depends on:** none

## Slice 2: Per-language example Dockerfiles in references

**Goal:** A complete, structurally valid example Dockerfile for each supported language (Go, Node.js, Python, Java, Rust) added to `references/`, linked from the SKILL.md body's language section, with the validator extended to require all five examples and to lint/parse each. Verifiable independently of Slice 1's prose by checking the examples parse/lint and the language-coverage assertion passes.

**Files touched:**

- ✨ `.claude/skills/writing-dockerfiles/references/languages-go.md` — Go: `CGO_ENABLED=0`, `-ldflags=-s -w`, multi-stage, copy binary to `scratch`; complete example.
- ✨ `.claude/skills/writing-dockerfiles/references/languages-node.md` — Node: `npm ci --omit=dev`, copy `node_modules` to Alpine/distroless; complete example.
- ✨ `.claude/skills/writing-dockerfiles/references/languages-python.md` — Python: pip/uv in builder, copy site-packages/venv to distroless/slim; complete example.
- ✨ `.claude/skills/writing-dockerfiles/references/languages-java.md` — Java: jlink minimal JRE, Eclipse Temurin base, GraalVM note; complete example.
- ✨ `.claude/skills/writing-dockerfiles/references/languages-rust.md` — Rust: `--release` builder, static binary to `scratch`; complete example.
- ⚠️ `.claude/skills/writing-dockerfiles/SKILL.md` — add the language section linking the five new language reference files.
- ⚠️ `scripts/validate_dockerfile_skill.py` — extend to assert all five language examples exist and each example lints/parses (hadolint/`docker build --check` when available, else structural parse).

**Verification:**
- [ ] `python <validator>` exits 0 with the language-coverage assertion enabled: all five `languages-*.md` exist and are linked from the body.
- [ ] Each example Dockerfile passes hadolint / `docker build --check` where available; otherwise structural parse (valid instructions, exec-form ENTRYPOINT/CMD, multi-stage present, non-root `USER`).
- [ ] Manual spot-check: each example reflects its language's documented pattern from the ticket (e.g., Go copies to `scratch`, Node uses `npm ci --omit=dev`).
- [ ] Body still ≤ 500 lines after adding the language section.

**Context cost:** L
**Depends on:** Slice 1

---

## Unverified Assumptions

- The build path via the host-level **skill-creator** (ticket process step 1, global directive) cannot be executed by the QRSPI planner because skill-creator is not in `REPO_ROOT` (ref: design.md Q5/OQ1). These slices assume the skill is authored in-repo and validated structurally; if the human requires the skill-creator's own eval/variance loop to gate completion, that is an out-of-band step run in the host, not captured as a file-touching slice here.
- **hadolint / Docker daemon availability** in the target environment is unconfirmed (ref: design.md OQ3). The validator is specified to degrade to structural parsing if absent; if neither is available, "example validation" is weaker than a true build check.
- **Final validator location** (`scripts/` vs the skill's own `scripts/`) is left to Plan; agentskills.io permits a per-skill `scripts/` dir, but the repo's `scripts/` currently holds eval tooling only. Either is in-repo and acceptable.
- **Frontmatter shape** (minimal vs command-style) is a design-flagged decision (OQ2) not yet human-confirmed; Slice 1 assumes minimal `name`+`description` per design Decision 2 Option A.
