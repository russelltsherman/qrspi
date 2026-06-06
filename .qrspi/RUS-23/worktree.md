# Work Tree — Create a new agent skill using the Crossplane CLI

**Plan basis:** plan.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total sessions:** 4
**Critical path:** T1 → T4 → T5 → T6 → T7 → T13 → T14 (7 tasks)

> Single-slice, skill-authoring ticket. Steps 1–3 resolve the blocking Open
> Questions that every templated `<name>` path depends on, so they front-load
> Session 1. Sessions are split to keep each load manifest narrow (under 40%):
> resolution+scaffold, SKILL.md authoring, reference files, then verification.
> "Tests" (T12–T14) are reviewer-gate checks, not executable unit tests.

## Session 1

**Load:** plan.md §Slice 1 Setup (steps 1–4), structure.md §Contracts (Frontmatter field set), design.md §OQ1–OQ4, MEMORY §skill-creator directive
**Estimated context:** ~20% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Resolve OQ1 — choose skill `<name>` (lowercase kebab-case, non-`qrspi-`; dirname == frontmatter `name` == `command` slug; default `using-crossplane-cli`) | — | §1 | S | pending |
| T2 | Resolve OQ3 — decide whether SKILL.md carries `argument-hint` (omit per qrspi-ticket exception unless author overrides) | — | §2 | S | pending |
| T3 | Resolve OQ2/OQ4 — confirm `skill-creator` invocation path; record exact invocation | — | §3 | S | pending |
| T4 | Invoke `skill-creator` to scaffold `.claude/skills/<name>/` + initial SKILL.md | T1, T2, T3 | §4 | M | pending |

--- SESSION BOUNDARY ---
**Reason:** Open Questions resolved and directory scaffolded. Fresh context to author the SKILL.md body without carrying the resolution reasoning.

## Session 2

**Load:** plan.md §Slice 1 Core Logic (steps 5–7), structure.md §Contracts, structure.md §New Types (`SkillFrontmatter`), design.md §Decision 3, impl-log.md §Session 1 (resolved `<name>` + decisions only)
**Estimated context:** ~28% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T5 | Create SKILL.md — frontmatter (exact field set per T2) + lean body covering provider lifecycle, composition, XRD/claims, managed resources, packaging, troubleshooting, kubectl/GitOps, env config; each section ends in backticked reference pointer | T4 | §5 | L | pending |
| T6 | Edit SKILL.md — add v1/v2 version-branching prose (`if v1 … otherwise v2 …`, default v2) | T5 | §6 | M | pending |
| T7 | Edit SKILL.md — add inline `trace → describe → events → logs` troubleshooting escalation sequence | T6 | §7 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** SKILL.md entry point complete. Fresh context to author the four reference files, which only need the scaffolded directory and structure §Slice 1.

## Session 3

**Load:** plan.md §Slice 1 Core Logic (steps 8–11), structure.md §Slice 1 (files 2–5), impl-log.md §Session 2 (reference-pointer paths only)
**Estimated context:** ~30% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T8 | Create references/cli-reference.md — `xpkg build/push/login/validate`, `render`, `trace`; defer flags to official Crossplane docs | T4 | §8 | M | pending |
| T9 | Create references/composition-patterns.md — Pipeline-mode, `function-patch-and-transform`, EnvironmentConfig, `crossplane render` validation | T4 | §9 | M | pending |
| T10 | Create references/xrd-schemas.md — XRD templates, v1 cluster-scoped+Claims vs v2 `scope: Namespaced`, connectionSecretKeys, versioning/conversion | T4 | §10 | M | pending |
| T11 | Create references/troubleshooting.md — trace→describe→events→logs tree, condition checks, `xpkg validate` | T4 | §11 | M | pending |

--- SESSION BOUNDARY ---
**Reason:** All authoring complete. Fresh context for reviewer-gate verification so the verification reads files cleanly rather than from in-memory drafts.

## Session 4

**Load:** plan.md §Tests (steps 12–13), plan.md §Verify Slice 1 (step 14), structure.md §New Types (`SkillDirectory`, `SkillFrontmatter`), impl-log.md §Sessions 1–3 (decisions + recorded skill-creator invocation)
**Estimated context:** ~18% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T12 | Run `ls` over all five files — confirm existence, no dangling reference pointer | T5, T8, T9, T10, T11 | §12 | S | pending |
| T13 | Run frontmatter check (`head -n1` + `grep` field set) — first line `---`, field set matches T2 decision, diffs clean vs known-good skill | T5, T6, T7 | §13 | S | pending |
| T14 | **Verify Slice 1** — checkpoint: name/frontmatter/argument-hint/body-size/reference-links/v1-v2/escalation/description-pattern/canonical-source/skill-creator-eval | T12, T13 | §14 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Single-slice feature complete and verified. No further sessions — proceed to PR phase.
