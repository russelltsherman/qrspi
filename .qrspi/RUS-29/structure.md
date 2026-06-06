# Structure Outline — Create a new agent skill called writing-dockerfiles

**Design basis:** design.md @ 2026-06-04T12:10:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft

## New Types

None. This is a documentation-only skill (Markdown + YAML frontmatter). It ships
no executable logic, no `scripts/`, and no data structures (ref: design.md §Delta,
"docs-only artifact has no logic to bind to").

## Modified Types

None.

## Contracts

There are no function signatures. The only cross-artifact interface is the
**reference-cue path contract** — the mechanism the design mandates for linking
SKILL.md to its reference files (ref: design.md Decision 2, Q2). It is a hard
contract because the SKILL.md body (Slice 1) cites relative paths that the
reference files (Slices 1 and 2) must create verbatim:

- `SKILL.md frontmatter` — must be `name: writing-dockerfiles`,
  `command: /writing-dockerfiles`, plus capability-first `description`,
  `argument-hint`, `allowed-tools` (ref: Q3, Q5). YAML values double-quoted only
  when containing `:` or `"` (ref: Q4).
- `SKILL.md → references/base-images.md` — imperative "read … before …" cue
  (base image selection, pinning, distroless/scratch/Alpine).
- `SKILL.md → references/multistage-and-caching.md` — multi-stage builds, layer
  ordering, cache mounts, `.dockerignore`.
- `SKILL.md → references/security.md` — non-root, secrets, scanning, build args.
- `SKILL.md → references/runtime.md` — healthchecks, signal handling, init,
  labels/EXPOSE/WORKDIR.
- `SKILL.md → references/languages/{go,node,python,java,rust}.md` — one complete
  example Dockerfile per language; cue style is explicit imperative, not passive
  parenthetical (ref: design.md Risk "reference prose cues not followed", Q2).

Cue style for every link: explicit imperative ("read `references/<topic>.md`
before writing X"), mirroring the attested `qrspi-work/SKILL.md:282-283` pattern.

## Slice 1: Skill scaffold, frontmatter, body, and topic references

**Goal:** A discoverable, auto-invokable `writing-dockerfiles` skill with valid
agentskills structure, in-budget body covering all eight convention areas, and the
four topic reference files it cues. End-to-end testable: the skill can be invoked
and its prose drives a reader to each topic reference. Per-language examples are
stubbed by the cues (filled in Slice 2).
**Files touched:**

- ✨ `.claude/skills/writing-dockerfiles/SKILL.md` — frontmatter + opinionated
  guidance sections for the eight areas (base image, multi-stage, layer caching,
  .dockerignore, security, build args, healthchecks, signal handling) +
  production-readiness, with imperative `references/` cues (ref: §Delta, Decision 4).
- ✨ `.claude/skills/writing-dockerfiles/references/base-images.md` — base image
  selection, tag-vs-digest pinning, distroless/scratch/Alpine decision guidance.
- ✨ `.claude/skills/writing-dockerfiles/references/multistage-and-caching.md` —
  multi-stage patterns, named stages, layer ordering, cache mounts, `.dockerignore`
  template.
- ✨ `.claude/skills/writing-dockerfiles/references/security.md` — non-root user
  /`USER`, runtime/build-time secret injection (never `ARG`/`ENV`/`COPY`), package
  hygiene, scanning (Trivy/Grype/Snyk), build args.
- ✨ `.claude/skills/writing-dockerfiles/references/runtime.md` — healthchecks,
  exec-form signal handling, `tini`/`dumb-init`, labels/EXPOSE/WORKDIR.
- ⚠️ `.claude/CLAUDE.md` — add a `/writing-dockerfiles` entry to the "Available
  skills" list (lines 43-53) for documentation hygiene (ref: §Delta, Q6).
**Verification:**
- [ ] Frontmatter parses and matches the de-facto schema (`name`, `description`,
  `command`, `argument-hint`, `allowed-tools`); directory name == `name` field.
- [ ] SKILL.md body is under the advisory 500-line / 5000-token budget (manual
  line/token count, ref: Q7).
- [ ] Each of the eight convention areas has a body section with an imperative cue
  to the correct topic reference path.
- [ ] Authored/validated via the `skill-creator` skill (the acceptance-criterion
  process step, ref: Q1, Q10; see Unverified Assumptions).
**Context cost:** M
**Depends on:** none

## Slice 2: Per-language example Dockerfiles

**Goal:** Complete, copy-ready example Dockerfiles for all five required languages,
satisfying the cues authored in Slice 1. Independently verifiable: each Dockerfile
is a complete, lint-clean multi-stage build following the conventions.
**Files touched:**

- ✨ `.claude/skills/writing-dockerfiles/references/languages/go.md`
- ✨ `.claude/skills/writing-dockerfiles/references/languages/node.md`
- ✨ `.claude/skills/writing-dockerfiles/references/languages/python.md`
- ✨ `.claude/skills/writing-dockerfiles/references/languages/java.md`
- ✨ `.claude/skills/writing-dockerfiles/references/languages/rust.md`
**Verification:**
- [ ] Each file contains one complete example Dockerfile for its language.
- [ ] Each example applies the skill's own conventions (multi-stage, non-root
  `USER`, pinned base, exec-form `ENTRYPOINT`/`CMD`).
- [ ] Optional: each Dockerfile is hadolint-clean.
- [ ] Every `references/languages/*.md` path cited by SLICE 1's SKILL.md resolves
  to an existing file (cue-path contract closed).
- [ ] Final skill-creator eval pass over the now-complete skill (ref: rule —
  validation is the last step of the slice that completes the artifact).
**Context cost:** M
**Depends on:** Slice 1

---

## Unverified Assumptions

- **"Built using the Anthropic skill builder skill" cannot be verified in-repo.**
  skill-creator is external and there is no in-repo validator; this maps to a
  process step (author attestation + manual structural review), not to a concrete
  file or test (ref: design.md Risk Register row 1, OQ1). Whether a reviewer
  requires a skill-creator eval/score artifact is unresolved — the repo's own eval
  harness is inert and cannot produce one (Q9).
- **CLAUDE.md skills-list update scope (OQ2).** The design's Delta includes the
  `.claude/CLAUDE.md` edit as required hygiene, but OQ2 questions whether the
  human-facing list should stay `qrspi-*`-only. Slice 1 includes the edit per the
  Delta; if the reviewer rules it out of scope, drop that one file from Slice 1.
- **Nested `references/languages/` depth (OQ3, flagged partial-new-pattern).** The
  subfolder is one level deeper than the single attested flat `references/`
  (Decision 3). Mapped to concrete files in Slice 2, but acceptance of the nesting
  vs. flattening to `references/lang-<name>.md` is unresolved (OQ3); resolution is
  functionally path-based so either layout works — confirm preferred layout before
  Slice 2.
- **Advisory budget has no enforcement.** The "under 500 lines / 5000 tokens"
  criterion maps only to a manual count in Slice 1 verification, not to any gate
  (ref: Q7); `qrspi-work/SKILL.md` already exceeds it at 565 lines with no tooling
  objecting.
