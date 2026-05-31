# Work Tree — Create a new agent skill called writing-dockerfiles

**Plan basis:** plan.md @ 2026-05-31T16:14:00Z
**Generated:** 2026-05-31T16:16:00Z
**Status:** draft
**Total sessions:** 2
**Critical path:** T1 → T2 → T10 → T11 → T12 → T13 → T14 → T15 → T16 → T17 → T18 (Verify Slice 1) → T19 → T24 → T25 → T26 → T27 (Verify Slice 2)

## Session 1 — Slice 1: Skill scaffold, body, and convention references

**Load:** structure.md §Contracts, structure.md §Slice 1, plan.md §Slice 1, design.md §Pattern Decisions (Decisions 1–3)
**Estimated context:** ~30%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create skill dir + `references/` dir | — | §1.1 | S | pending |
| T2 | Create `SKILL.md` with frontmatter (name + trigger description, scope exclusions) | T1 | §1.2 | S | pending |
| T3 | Body: base image selection + pointer | T2 | §1.3 | S | pending |
| T4 | Body: multi-stage & layer caching + pointer | T3 | §1.4 | S | pending |
| T5 | Body: .dockerignore + pointer | T4 | §1.5 | S | pending |
| T6 | Body: security (non-root, secrets, scanning) + pointer | T5 | §1.6 | S | pending |
| T7 | Body: build args & env + production readiness + pointer | T6 | §1.7 | S | pending |
| T8 | Body: healthchecks & signal handling (shell-form warning, exec form, init) + pointer | T7 | §1.8 | S | pending |
| T9 | Body: language-patterns placeholder section | T8 | §1.9 | S | pending |
| T10 | Create `references/base-images.md` | T2 | §1.10 | S | pending |
| T11 | Create `references/multi-stage-and-caching.md` | T2 | §1.11 | M | pending |
| T12 | Create `references/dockerignore.md` | T2 | §1.12 | S | pending |
| T13 | Create `references/security.md` | T2 | §1.13 | M | pending |
| T14 | Create `references/signals-and-healthchecks.md` | T2 | §1.14 | M | pending |
| T15 | Create `references/production-readiness.md` | T2 | §1.15 | S | pending |
| T16 | Create `scripts/validate_dockerfile_skill.py` (frontmatter, body size, bidirectional reference integrity; lang checks gated off) | T9–T15 | §1.16 | L | pending |
| T17 | Run validator; expect exit 0 | T16 | §1.17 | S | pending |
| T18 | Negative test: dangling-link detection fires | T16 | §1.18 | S | pending |
| T19 | **Verify Slice 1** (validator exit 0, body ≤500, eight areas, security+signals, reference integrity, negative test) | T17, T18 | §1.19 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 delivers an independently-validatable skill scaffold. Fresh context for Slice 2 keeps language-example work below the 40% context budget and matches the "fresh session between slices" project rule.

## Session 2 — Slice 2: Per-language example Dockerfiles

**Load:** structure.md §Contracts, structure.md §Slice 2, plan.md §Slice 2, impl-log.md §Slice 1 (notes only)
**Estimated context:** ~32%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T20 | Create `references/languages-go.md` (scratch, CGO_ENABLED=0, -ldflags=-s -w) + example | T19 | §2.20 | M | pending |
| T21 | Create `references/languages-node.md` (`npm ci --omit=dev`, distroless/Alpine) + example | T19 | §2.21 | M | pending |
| T22 | Create `references/languages-python.md` (pip/uv builder, venv to slim/distroless) + example | T19 | §2.22 | M | pending |
| T23 | Create `references/languages-java.md` (jlink/Temurin, GraalVM note) + example | T19 | §2.23 | M | pending |
| T24 | Create `references/languages-rust.md` (`--release` to scratch) + example | T19 | §2.24 | M | pending |
| T25 | Modify `SKILL.md` language section to link all five language references | T20–T24 | §2.25 | S | pending |
| T26 | Confirm/trim `SKILL.md` ≤ 500 lines after language section | T25 | §2.26 | S | pending |
| T27 | Extend validator: enable language-coverage assertion | T25 | §2.27 | M | pending |
| T28 | Extend validator: enable per-example lint/parse (hadolint/docker/structural) | T27 | §2.28 | M | pending |
| T29 | Run validator with language checks enabled; expect exit 0 | T28 | §2.29 | S | pending |
| T30 | **Verify Slice 2** (five examples linked, each lints/parses, patterns correct, body ≤500) | T26, T29 | §2.30 | S | pending |
| T31 | Acceptance sweep against all ticket criteria | T30 | §2.31 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** End of implementation. Next step is PR-summary generation by the orchestrator, then Code Review.
