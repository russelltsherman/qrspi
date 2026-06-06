# Work Tree — Create new agent skill: writing-github-actions

**Plan basis:** plan.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total sessions:** 2
**Critical path:** T1 → T2 → T6 → T12 → T13 (5 tasks)

> Single-slice, content-only prose skill (plan §Note). One authoring+verification
> session, then a separate session for the skill-creator eval loop (heavy external
> skill — warrants fresh context). The four `references/*.md` files (T2–T5) are
> independent of one another and all gate the SKILL.md authoring (T6).

## Session 1 — Author skill + manual verification

**Load:** structure.md §Contracts, structure.md §Verification, plan.md §Slice 1, design.md §Delta
**Estimated context:** ~25% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create `references/` directory (`mkdir -p`) | — | §1 | S | pending |
| T2 | Author `references/security-hardening-checklist.md` (SHA-pinning, least-privilege, injection, `pull_request_target`, CODEOWNERS, zizmor map) | T1 | §2 | S | pending |
| T3 | Author `references/oidc-setup-patterns.md` (provider-agnostic OIDC, GitHub Environments) | T1 | §3 | S | pending |
| T4 | Author `references/common-workflow-templates.md` (CI→deploy, `workflow_call`, composite skeletons) | T1 | §4 | S | pending |
| T5 | Author `references/matrix-strategy-examples.md` (`strategy.matrix`, `fail-fast`, include/exclude, cache keys) | T1 | §5 | S | pending |
| T6 | Author `SKILL.md` (frontmatter per `SKILLFrontmatter`, lifecycle body, reusable-vs-composite + concurrency sections, SHA-pinning canonical rule, four relative `references/` pointers) | T2, T3, T4, T5 | §6 | M | pending |
| T7 | Confirm no automated tests — manual checkpoints only (prose-only policy) | T6 | §7 | S | pending |
| T8 | **Verify:** `name` frontmatter == dir name == command slug | T6 | §8 | S | pending |
| T9 | **Verify:** all four `references/*.md` exist; every SKILL.md pointer is relative and resolves | T6, T2, T3, T4, T5 | §9 | S | pending |
| T10 | **Verify:** SKILL.md body < 500 lines AND < 5000 tokens | T6 | §10 | S | pending |
| T11 | **Verify:** all AC topics present (lifecycle, reusable-vs-composite, concurrency, SHA-pinning in body + restated in security ref) | T6 | §11 | S | pending |
| T12 | **Verify Slice 1:** manual e2e — author sample workflow passing zizmor checks; confirm GHA-authoring prompt auto-triggers skill | T6, T8, T9, T10, T11 | §12 | M | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 authored and self-verified. The skill-creator eval loop (T13)
loads a separate, heavy skill and its scaffold/frontmatter expectations; a fresh
context isolates that reconciliation work and keeps each session under 40%.

## Session 2 — skill-creator eval loop + frontmatter reconciliation

**Load:** plan.md §Slice 1 (step 13 only), structure.md §Verification (final step), impl-log.md §Slice 1 (notes only), skill-creator skill
**Estimated context:** ~20% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T13 | Invoke `skill-creator` skill / eval loop on authored skill; reconcile scaffold + frontmatter against in-repo baseline; resolve any agentskills.io field conflicts (OQ1/OQ2) | T12 | §13 | L | pending |

--- SESSION BOUNDARY ---
**Reason:** End of work tree — all tasks complete; hand off to PR phase.
