# Work Tree — Create a new agent skill called writing-dockerfiles

**Plan basis:** plan.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total sessions:** 4
**Critical path:** T1 → T2 → T3 → T4 → T5 → T6 → T12 → T13 → T14 → T17 (10 tasks)

> Note: This is a documentation-only skill — no executable types, signatures, or unit
> tests (ref: plan.md header; structure.md "New Types: None"). "Verify" tasks are
> structural checks (frontmatter parse, body budget, cue-path contract) plus a
> skill-creator eval pass, not code tests.

## Session 1

**Load:** structure.md §Contracts, design.md §Decision 4, design.md §Desired End State, plan.md §Slice 1 (steps 1-6)
**Estimated context:** ~25% of window

Author SKILL.md: frontmatter plus all eight convention body sections with imperative reference cues. Single artifact, sequential append — kept in one session so the body budget can be tracked as it grows.

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create SKILL.md frontmatter (name/command/description+triggers/argument-hint/allowed-tools; dir name == name) | — | §1.1 | S | pending |
| T2 | Append **base image selection** body section + cue to references/base-images.md | T1 | §1.2 | S | pending |
| T3 | Append **multi-stage / layer caching / .dockerignore** body sections + cue to references/multistage-and-caching.md | T2 | §1.3 | M | pending |
| T4 | Append **security + build args** body sections + cue to references/security.md | T3 | §1.4 | M | pending |
| T5 | Append **healthchecks + signal handling** body sections + cue to references/runtime.md | T4 | §1.5 | S | pending |
| T6 | Append **per-language examples** pointer section + cues to references/languages/{go,node,python,java,rust}.md | T5 | §1.6 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** SKILL.md body complete. Authoring four reference files is content-heavy; fresh context keeps the reference-file session under budget and isolates it from the SKILL.md draft.

## Session 2

**Load:** structure.md §Slice 1, design.md §Delta, design.md §Risk Register, plan.md §Slice 1 (steps 7-11)
**Estimated context:** ~30% of window

Create the four topic reference files (cue targets from Session 1) and the CLAUDE.md skills-list edit. Each reference file is substantial prose.

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T7 | Create references/base-images.md (tag-vs-digest pinning, distroless/scratch/Alpine guidance) | T2 | §1.7 | M | pending |
| T8 | Create references/multistage-and-caching.md (named stages, layer ordering, cache mounts, .dockerignore template) | T3 | §1.8 | M | pending |
| T9 | Create references/security.md (non-root USER, secret injection, package hygiene, scanning, build args) | T4 | §1.9 | M | pending |
| T10 | Create references/runtime.md (healthchecks, exec-form signals, tini/dumb-init, labels/EXPOSE/WORKDIR) | T5 | §1.10 | M | pending |
| T11 | Modify .claude/CLAUDE.md — add /writing-dockerfiles to Available skills list (drop if reviewer rules OQ2 out of scope) | — | §1.11 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** All Slice 1 files authored. Validation/verification needs a clean read of the complete skill; isolating it avoids carrying authoring context into the skill-creator eval.

## Session 3

**Load:** plan.md §Slice 1 (steps 12-13), structure.md §Slice 1 verification, SKILL.md + references/*.md (the authored skill, read by skill-creator)
**Estimated context:** ~20% of window

Validate the assembled Slice 1 skill via skill-creator and run the structural checkpoint.

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T12 | Validate skill via the skill-creator skill (process step, not in-repo test) | T6, T10, T11 | §1.12 | S | pending |
| T13 | **Verify Slice 1** — frontmatter parses; body under budget; 8 areas cite correct cues; 4 reference files resolve | T12 | §1.13 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete and verified. Fresh context for Slice 2 (per-language example Dockerfiles).

## Session 4

**Load:** structure.md §Slice 2, plan.md §Slice 2 (steps 14-17), impl-log.md §Slice 1 (notes only — confirms cue paths SKILL.md expects)
**Estimated context:** ~25% of window

Author the five per-language example Dockerfiles that close the cue-path contract from Slice 1.

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T14 | Create references/languages/go.md — complete multi-stage Go Dockerfile (multi-stage, non-root USER, pinned base, exec-form CMD) | T13 | §2.14 | M | pending |
| T15 | Create references/languages/node.md — complete multi-stage Node.js Dockerfile (same conventions) | T13 | §2.15 | M | pending |
| T16 | Create references/languages/{python,java,rust}.md — one complete multi-stage Dockerfile each (same conventions; OQ3 flatten option) | T13 | §2.16 | M | pending |
| T17 | **Verify Slice 2** — all five lang files exist + apply conventions; cue-path contract closed; final skill-creator eval pass | T14, T15, T16 | §2.17 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Final session — all slices implemented and verified; no further sessions.
