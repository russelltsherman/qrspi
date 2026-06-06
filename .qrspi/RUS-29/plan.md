# Implementation Plan — Create a new agent skill called writing-dockerfiles

**Structure basis:** structure.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total steps:** 17

> Note: This is a documentation-only skill. There are no executable types,
> signatures, or unit tests (ref: structure.md "New Types: None"; design.md §Delta
> "docs-only artifact has no logic to bind to"). "Tests" are therefore structural
> verification: frontmatter parses, body budget, and the reference-cue path
> contract (SKILL.md cites paths that the reference files create verbatim).

## Slice 1: Skill scaffold, frontmatter, body, and topic references

### Setup

1. ✨ Create `.claude/skills/writing-dockerfiles/SKILL.md` (frontmatter only) — author
   YAML frontmatter per the de-facto schema (ref: structure.md Contracts; design.md
   Decision 4): `name: writing-dockerfiles`, `command: /writing-dockerfiles`,
   capability-first `description` with "Use when..." + enumerated triggers ("write a
   Dockerfile", "optimize this image", "harden my container build"), `argument-hint`,
   `allowed-tools`. Double-quote any YAML value containing `:` or `"` (ref: Q4).
   Directory name must equal the `name` field verbatim (ref: Q5).

### Core Logic

2. ⚠️ Modify `.claude/skills/writing-dockerfiles/SKILL.md` — append the body section for
   **base image selection** with an imperative cue: "read `references/base-images.md`
   before choosing a base image" (ref: structure.md Contracts; design.md §Desired End State).
3. ⚠️ Modify `.claude/skills/writing-dockerfiles/SKILL.md` — append the body sections for
   **multi-stage builds**, **layer caching**, and **.dockerignore**, each with an
   imperative cue to `references/multistage-and-caching.md` (ref: structure.md Contracts).
4. ⚠️ Modify `.claude/skills/writing-dockerfiles/SKILL.md` — append the body sections for
   **security** (non-root/`USER`, secrets, scanning) and **build args**, with an imperative
   cue to `references/security.md` (ref: design.md §Desired End State; Risk Register).
5. ⚠️ Modify `.claude/skills/writing-dockerfiles/SKILL.md` — append the body sections for
   **healthchecks** and **signal handling** (mandate exec-form `ENTRYPOINT`/`CMD`, warn
   against shell form, recommend `tini`/`dumb-init`), with an imperative cue to
   `references/runtime.md` (ref: design.md §Desired End State).
6. ⚠️ Modify `.claude/skills/writing-dockerfiles/SKILL.md` — append a **per-language examples**
   pointer section with explicit imperative cues to
   `references/languages/{go,node,python,java,rust}.md` (cue style per structure.md Contracts;
   files created in Slice 2).
7. ✨ Create `.claude/skills/writing-dockerfiles/references/base-images.md` — base image
   selection, tag-vs-digest pinning, distroless/scratch/Alpine decision guidance
   (ref: structure.md Slice 1; design.md §Delta).
8. ✨ Create `.claude/skills/writing-dockerfiles/references/multistage-and-caching.md` —
   multi-stage patterns, named stages, layer ordering, cache mounts, `.dockerignore`
   template (ref: structure.md Slice 1; design.md §Delta).
9. ✨ Create `.claude/skills/writing-dockerfiles/references/security.md` — non-root user
   /`USER`, runtime/build-time secret injection (never `ARG`/`ENV`/`COPY`), package
   hygiene, scanning (Trivy/Grype/Snyk), build args (ref: structure.md Slice 1; design.md §Delta).
10. ✨ Create `.claude/skills/writing-dockerfiles/references/runtime.md` — healthchecks,
    exec-form signal handling, `tini`/`dumb-init`, labels/EXPOSE/WORKDIR
    (ref: structure.md Slice 1; design.md §Delta).
11. ⚠️ Modify `.claude/CLAUDE.md` — add a `/writing-dockerfiles` entry to the "Available
    skills" list (lines 43-53) for documentation hygiene (ref: structure.md Slice 1; Q6).
    - **Current:** list ends with `/qrspi-pr <ticket-id>` entry.
    - **After:** an added bullet `- /writing-dockerfiles — author/optimize/harden Dockerfiles`.
    - **Note:** OQ2 questions whether this human-facing list should stay `qrspi-*`-only;
      drop this step if the reviewer rules it out of scope.

### Tests

12. ✨ Validate via the `skill-creator` skill — author/validate the skill through skill-creator
    (the acceptance-criterion process step, ref: structure.md Slice 1 verification; Q1, Q10).
    This is a process step, not an in-repo test (ref: Unverified Assumptions).

### Verify Slice 1

13. **Checkpoint:** `python3 -c "import yaml,sys; yaml.safe_load(open('.claude/skills/writing-dockerfiles/SKILL.md').read().split('---')[1])"`
    and `wc -l .claude/skills/writing-dockerfiles/SKILL.md`
    - [ ] Frontmatter parses; has `name`, `description`, `command`, `argument-hint`,
      `allowed-tools`; directory name == `name` field (`writing-dockerfiles`).
    - [ ] SKILL.md body under the advisory 500-line / 5000-token budget (manual count, Q7).
    - [ ] Each of the eight convention areas (base image, multi-stage, layer caching,
      .dockerignore, security, build args, healthchecks, signal handling) has a body
      section with an imperative cue to the correct topic reference path.
    - [ ] All four `references/*.md` topic files exist and resolve from SKILL.md cues.

---

## Slice 2: Per-language example Dockerfiles

### Core Logic

14. ✨ Create `.claude/skills/writing-dockerfiles/references/languages/go.md` — one complete
    multi-stage Go example Dockerfile applying the skill's conventions (multi-stage, non-root
    `USER`, pinned base, exec-form `ENTRYPOINT`/`CMD`) (ref: structure.md Slice 2).
15. ✨ Create `.claude/skills/writing-dockerfiles/references/languages/node.md` — one complete
    multi-stage Node.js example Dockerfile applying the same conventions (ref: structure.md Slice 2).
16. ✨ Create `.claude/skills/writing-dockerfiles/references/languages/python.md`,
    `.../java.md`, and `.../rust.md` — one complete multi-stage example Dockerfile each
    (Python, Java, Rust) applying the same conventions (ref: structure.md Slice 2).
    - **Note:** OQ3 — nested `references/languages/` is one level deeper than the attested
      flat `references/`; if the reviewer prefers flattening, use `references/lang-<name>.md`
      and update the Slice 1 cues accordingly (functionally equivalent, ref: Decision 3).

### Tests

(None — docs-only artifact has no executable logic; covered by the cue-path contract
verification below, ref: design.md §Delta.)

### Verify Slice 2

17. **Checkpoint:** `ls .claude/skills/writing-dockerfiles/references/languages/` and final
    skill-creator eval pass over the now-complete skill (ref: structure.md Slice 2 verification).
    - [ ] All five files exist: `go.md`, `node.md`, `python.md`, `java.md`, `rust.md`.
    - [ ] Each contains one complete example Dockerfile applying the conventions
      (multi-stage, non-root `USER`, pinned base, exec-form `ENTRYPOINT`/`CMD`).
    - [ ] Optional: each Dockerfile is hadolint-clean.
    - [ ] Every `references/languages/*.md` path cited by Slice 1's SKILL.md resolves to an
      existing file (cue-path contract closed).
    - [ ] Final skill-creator eval pass completed on the complete skill.

---

## Rollback Notes

- Steps 1-10, 14-16 (new files): `rm -rf .claude/skills/writing-dockerfiles/` removes the
  entire skill; it is discovered by directory presence, so deletion fully reverses it.
- Step 11 (`.claude/CLAUDE.md` edit): remove the added `/writing-dockerfiles` bullet from the
  "Available skills" list. Non-functional doc edit — no behavioral impact either way.
