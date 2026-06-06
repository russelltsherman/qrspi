# PR: Add writing-dockerfiles skill — guidance + 5 language examples

**Ticket:** RUS-29
**Design:** design.md @ 2026-06-04T12:10:00Z
**Structure:** structure.md @ 2026-06-06T00:00:00Z

## Summary

Adds a new self-contained documentation skill at
`.claude/skills/writing-dockerfiles/` that gives the agent opinionated,
production-grade Dockerfile authoring guidance. The skill is a `SKILL.md` body
covering the eight convention areas (base image selection, multi-stage builds,
layer caching, `.dockerignore`, security, build args, healthchecks, signal
handling) plus a `references/` tree split into four topic files and a nested
`languages/` folder holding one complete example Dockerfile per language (Go,
Node.js, Python, Java, Rust). It diverges from the dominant `qrspi-*`
wrapper/agent shape on purpose — a docs-only capability is self-contained prose
plus references (design Decision 1). Reviewer focus: (1) the reference-cue path
contract — every `references/...` path cited in SKILL.md must resolve to a real
file in both directions; (2) the nested `references/languages/` depth (OQ3);
(3) correctness of the five example Dockerfiles, since no hadolint/skill-creator
gate runs in this environment. Per reviewer direction, the skill is NOT indexed
in `.claude/CLAUDE.md` (or any markdown file) — that file is untouched (OQ2 dropped).

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: Valid agentskills.io structure + frontmatter (`name`, `description`, `command`, `argument-hint`, `allowed-tools`) | `.claude/skills/writing-dockerfiles/SKILL.md` (frontmatter) | impl-log S1: stdlib frontmatter parse — all 5 required keys present, description double-quoted (Q4); dir name == `name` field |
| AC2: Built using the Anthropic skill builder (skill-creator) | `.claude/skills/writing-dockerfiles/SKILL.md` (authored per skill-creator conventions) | impl-log S1/S2: process step — author attestation + manual structural review (unverifiable in-repo, OQ1; interactive eval loop out of scope for automated slice) |
| AC3: SKILL.md under 500 lines / 5000 tokens | `.claude/skills/writing-dockerfiles/SKILL.md` | impl-log S1: `wc -l` → 134 lines (≤500); `wc -w` → 1019 words ≈ 1360 tokens (≤5000) |
| AC4: Detailed reference material in `references/` | `references/base-images.md`, `multistage-and-caching.md`, `security.md`, `runtime.md`, `languages/*.md` | impl-log S1/S2: cue resolution — all topic + language references cued from SKILL.md and exist on disk |
| AC5: Covers all major conventions (base image, multi-stage, caching, .dockerignore, security, build args, healthchecks, signals) | `.claude/skills/writing-dockerfiles/SKILL.md` body + 4 topic references | impl-log S1: each of the eight areas has a body section with an imperative cue to the correct topic reference |
| AC6: One complete example Dockerfile per language (Go, Node, Python, Java, Rust) | `references/languages/{go,node,python,java,rust}.md` | impl-log S2: `ls references/languages/` → 5/5 present; convention check — multi-stage `FROM ... AS`, one `USER`, one exec-form `ENTRYPOINT`/`CMD`, zero `:latest` per file |
| AC7: Security guidance — non-root, secrets, scanning | `references/security.md` (+ SKILL.md security section) | impl-log S2: convention check — exactly one non-root `USER` line per example; security.md covers secret mounts (never `ARG`/`ENV`/`COPY`) + Trivy/Grype/Snyk |
| AC8: Signal handling warns against shell form | `references/runtime.md` (+ SKILL.md signal-handling section) | impl-log S2: convention check — one exec-form `ENTRYPOINT`/`CMD` per example; runtime.md mandates exec form, warns shell form swallows signals, recommends `tini`/`dumb-init` |

## Changes by Slice

### Slice 1: Skill scaffold, frontmatter, body, and topic references

| File | Change | Lines |
|------|--------|-------|
| `.claude/skills/writing-dockerfiles/SKILL.md` | ✨ new | +134 |
| `.claude/skills/writing-dockerfiles/references/base-images.md` | ✨ new | +53 |
| `.claude/skills/writing-dockerfiles/references/multistage-and-caching.md` | ✨ new | +124 |
| `.claude/skills/writing-dockerfiles/references/security.md` | ✨ new | +81 |
| `.claude/skills/writing-dockerfiles/references/runtime.md` | ✨ new | +84 |

### Slice 2: Per-language example Dockerfiles

| File | Change | Lines |
|------|--------|-------|
| `.claude/skills/writing-dockerfiles/references/languages/go.md` | ✨ new | +73 |
| `.claude/skills/writing-dockerfiles/references/languages/node.md` | ✨ new | +79 |
| `.claude/skills/writing-dockerfiles/references/languages/python.md` | ✨ new | +85 |
| `.claude/skills/writing-dockerfiles/references/languages/java.md` | ✨ new | +73 |
| `.claude/skills/writing-dockerfiles/references/languages/rust.md` | ✨ new | +81 |

### Workflow artifacts (not implementation — QRSPI phase outputs)

| File | Change | Lines |
|------|--------|-------|
| `.qrspi/RUS-29/questions.md` | ✨ new | +53 |
| `.qrspi/RUS-29/research.md` | ✨ new | +382 |
| `.qrspi/RUS-29/design.md` | ✨ new | +108 |
| `.qrspi/RUS-29/structure.md` | ✨ new | +127 |
| `.qrspi/RUS-29/plan.md` | ✨ new | +124 |
| `.qrspi/RUS-29/worktree.md` | ✨ new | +81 |
| `.qrspi/RUS-29/impl-log.md` | ✨ new | +61 |

## Testing Summary

- [x] Slice 1: frontmatter parse — `python3` stdlib frontmatter parser — all 5 required keys present, description double-quoted (Q4); dir name == `name`
- [x] Slice 1: budget — `wc -l SKILL.md` → 134 (≤500); `wc -w` → 1019 ≈ 1360 tokens (≤5000)
- [x] Slice 1: cue resolution (forward) — all 4 topic references cued from SKILL.md exist on disk
- [x] Slice 1: `.claude/CLAUDE.md` left byte-identical to main (skill not indexed in any markdown file, per reviewer direction)
- [x] Slice 2: file presence — `ls references/languages/` → go, node, python, java, rust (5/5)
- [x] Slice 2: cue-path contract (forward + reverse) — every `references/languages/*.md` cited resolves to a file; no orphan files
- [x] Slice 2: per-file convention check — multi-stage `FROM ... AS`, exactly one `USER`, one exec-form `ENTRYPOINT`/`CMD`, zero `:latest` bases
- [ ] hadolint lint pass — SKIPPED: hadolint not installed in this environment; embedded Dockerfiles verified manually (pinned bases, `--no-install-recommends` + apt cleanup in same layer, exec-form entrypoints)
- [ ] skill-creator eval/benchmark pass — SKIPPED: interactive loop out of scope for automated slice; verified structurally (progressive-disclosure cues resolve end-to-end)

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| (none) | structure.md declares no types/signatures; only the reference-cue path contract | Cue-path contract closed in both directions; nested `references/languages/` layout kept | impl-log S1 & S2 both report "Deviations from structure.md: none". Plan-level substitutions only (see Open Items) |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| "Built using skill-creator" AC unverifiable in-repo (external skill, no validator) | accepted — process step; author attests, skill authored per skill-creator conventions; interactive eval out of scope (OQ1) | n/a (process, not code) |
| SKILL.md body exceeds advisory 500-line / 5000-token budget | mitigated — 134 lines / ≈1360 tokens, well under budget; depth pushed into `references/` | n/a |
| `.claude/CLAUDE.md` skills list drifts | n/a — skill is intentionally not indexed in `.claude/CLAUDE.md` (or any markdown file) per reviewer direction; file untouched | n/a |
| Nested `references/languages/` depth diverges from attested flat `references/` | accepted — flagged partial-new-pattern (Decision 3, OQ3); resolution is by prose-cited path so depth is functionally irrelevant | rename to `references/lang-<name>.md` and update the 5 cue lines in SKILL.md (functionally equivalent) |
| Reference prose cues not followed (no auto-load) leaving language examples unread | mitigated — imperative "read `references/<topic>.md` before writing X" cues used; cue-path contract verified both directions | n/a |
| discovered-new: rust.md `--mount=type=cache` placed after `&&` inside RUN body (invalid BuildKit syntax) | mitigated — corrected during S2 authoring; mount flag moved to lead the RUN instruction | n/a (fixed in-place) |

## Open Items

- **OQ1 — skill-creator evidence:** author attestation + manual structural review used; reviewer may require a skill-creator eval/score artifact, which the repo's inert eval harness (Q9) cannot produce. Confirm sufficiency.
- **OQ2 — CLAUDE.md skills-list scope:** RESOLVED — per reviewer direction, skills are not indexed in `.claude/CLAUDE.md` (or any markdown file). The file is left byte-identical to main; no entry added.
- **OQ3 — nested layout:** confirm `references/languages/` nesting is acceptable vs. flattening to `references/lang-<name>.md`.
- **Plan deviation (T13):** plan's PyYAML-based checkpoint replaced with a stdlib-only frontmatter parser (project is stdlib-only per CLAUDE.md); same verification intent, no artifact change.
- **Plan deviation (T17):** optional hadolint pass skipped (tool not installed) — manual Dockerfile correctness review performed instead. Consider wiring hadolint into CI if a future automated gate is desired.
- **Digest placeholders:** per-language examples carry pinned tags but leave `@sha256:<digest>` as `<digest>` placeholders (environment/arch-specific); resolve digests when adopting an example.
