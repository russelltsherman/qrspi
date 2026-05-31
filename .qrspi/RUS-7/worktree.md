# Work Tree — Create a new agent skill using argo workflows cli

**Plan basis:** plan.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft
**Total sessions:** 2
**Critical path:** T1 → T2 → T3 → T4 → T8 → T11 → T12 → T13 → T14 → T15 → T16 (Slice 1 Verify); Slice 2 (conditional) → T17 → T18 → T19 → T20

> **Blocking open questions** (carried from plan; resolve before starting): OQ1 (naming, assumes `using-argo-workflows-cli`), OQ2 (frontmatter `allowed-tools`, used in T3), OQ5 (targeted argo version, used in T7/T10/T15), OQ3 (gates whether Session 2 runs at all), OQ4 (confirmed out of scope).

## Session 1 — Author the `using-argo-workflows-cli` skill (Slice 1)

**Load:** structure.md §Types, structure.md §Contracts, structure.md §Verify, plan.md §Slice 1
**Estimated context:** ~30% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Invoke `skill-creator` to scaffold the skill; treat output as a starting scaffold to reconcile to repo conventions | — | §1 | M | pending |
| T2 | Create `references/` subtree to establish agentskills.io layout | T1 | §2 | S | pending |
| T3 | Create SKILL.md (scaffolded/empty), populated by later tasks | T2 | §3 | S | pending |
| T4 | Write SKILL.md frontmatter: exactly the 5 repo-standard fields; enforce directory == name == command invariant (uses OQ1, OQ2) | T3 | §4 | S | pending |
| T5 | Add "When to use" section (general-purpose argo guidance, capability skill) | T4 | §5 | S | pending |
| T6 | Add decision-first overview summarizing each named convention in 1–2 lines | T5 | §6 | S | pending |
| T7 | Add "References" section naming all four reference files with when-to-open guidance (no orphans) | T6 | §7 | S | pending |
| T8 | Create `references/cli-commands.md` — all 15 command groups with flags; argo version note (OQ5); non-interactive/scriptable flags | T2 | §8 | L | pending |
| T9 | Create `references/templates.md` — DAG vs Steps, authoring, params, WorkflowTemplate vs ClusterWorkflowTemplate scope | T2 | §9 | M | pending |
| T10 | Create `references/reliability.md` — retry/backoff, error handling, timeouts, resource mgmt, artifact best practices | T2 | §10 | M | pending |
| T11 | Create `references/cron-and-debugging.md` — CronWorkflow lifecycle + debug escalation path | T2 | §11 | M | pending |
| T12 | Add argo version note (OQ5) to templates/reliability/cron-and-debugging; confirm principle-based guidance | T9, T10, T11 | §12 | S | pending |
| T13 | Conformance: SKILL.md + four reference files exist | T7, T8, T12 | §13 | S | pending |
| T14 | Conformance: SKILL.md ≤ 500 lines; manual ≤ 5000 token estimate | T13 | §14 | S | pending |
| T15 | Conformance: every reference filename named in body (≥4); no orphans | T13 | §15 | S | pending |
| T16 | Conformance: all 15 command groups present in cli-commands.md | T13 | §16 | S | pending |
| T17 | **Verify Slice 1** — full checkpoint (layout, frontmatter invariant, size, no orphans, 15 groups, conventions placed, scriptable flags, skill-creator reconciled, OQ2/OQ5 reflected) | T14, T15, T16 | §17 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete and verified. Session 2 is conditional and gated on OQ3; it touches a different file (`.claude/CLAUDE.md`) and needs none of Slice 1's authoring detail in context — only the resolved `description` string. Fresh context per QRSPI fresh-session-per-slice rule.

## Session 2 (conditional) — Register skill in project `.claude/CLAUDE.md` (Slice 2)

> **Skip this entire session unless OQ3 is resolved "yes."** The skill is auto-discovered and functions without registration.

**Load:** plan.md §Slice 2, structure.md §Slice 2 Conditional, impl-log.md §Slice 1 (final SKILL.md `description` value only)
**Estimated context:** ~10% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T18 | **Gate:** confirm OQ3 resolved "yes"; if not, stop and do not modify `.claude/CLAUDE.md` | T17 | §18 | S | pending |
| T19 | Modify `.claude/CLAUDE.md` — add `using-argo-workflows-cli` to "Available skills" with one-line description matching SKILL.md `description` | T18 | §19 | S | pending |
| T20 | Conformance: one matching line for `using-argo-workflows-cli` in Available skills | T19 | §20 | S | pending |
| T21 | **Verify Slice 2** — OQ3 was "yes"; entry present with consistent description | T20 | §21 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Final slice. End of work tree — proceed to PR phase once Session 2 (or its skip decision) is recorded.
