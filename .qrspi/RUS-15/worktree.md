# Work Tree — Create a kubectl CLI agent skill

**Plan basis:** plan.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total sessions:** 2
**Critical path:** T1 → T5 → T6 → T7 → T8 → T9 → T10 → T11 → T12 → T13 → T14 (11 tasks)

> Single vertical slice (Slice 1) producing Markdown skill source only — no
> executable code, no automated tests (`run_eval.py` is a stub; verification is
> manual per design Q10/Q12). The slice is split across two sessions on the file
> boundary the plan calls out: the four `references/` files must exist before
> `SKILL.md` links to them. Session 1 authors the references; Session 2 authors
> `SKILL.md` and runs the manual verification checkpoints. Per the memory
> directive + acceptance criterion, authoring should use the global
> `skill-creator` skill and its eval loop (OQ1 — record a deviation in the slice
> PR if unavailable).

## Session 1

**Load:** structure.md §Files touched, structure.md §Contracts, plan.md §Slice 1 (Setup + Core Logic steps 1–5), design.md §Delta
**Estimated context:** ~25% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create `references/jsonpath.md` as an empty placeholder to establish the `references/` subdirectory | — | §1.1 | S | pending |
| T2 | Create `references/krew-plugins.md` — krew plugin catalog (ctx, ns, neat, tree, images, whoami, access-matrix) + provenance guidance | — | §1.2 | M | pending |
| T3 | Create `references/rbac-debugging.md` — RBAC decision tree (`auth can-i` → bindings → subject form → NetworkPolicy/webhook) | — | §1.3 | M | pending |
| T4 | Create `references/common-errors.md` — common kubectl error messages with resolutions | — | §1.4 | S | pending |
| T5 | Populate `references/jsonpath.md` with JSONPath, custom-columns, and jq extraction examples | T1 | §1.5 | M | pending |

--- SESSION BOUNDARY ---
**Reason:** All four `references/` files exist. Fresh context to author `SKILL.md` so its on-demand reference citations resolve (plan ordering constraint) and the body-budget / link-resolution checks pass without the reference-authoring content crowding the window.

## Session 2

**Load:** structure.md §New Types, structure.md §Contracts, plan.md §Slice 1 (Core Logic steps 6–11 + Verify), design.md §Desired End State, references/ (filenames only, for link citations)
**Estimated context:** ~30% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T6 | Create `SKILL.md` YAML frontmatter satisfying `SkillFrontmatter` + `TripleIdentity` (five fields; quoted `description`) | T2, T3, T4, T5 | §1.6 | S | pending |
| T7 | Add top-of-body `GuardrailBlock` (hazard heading, ALL-CAPS imperative, bolded absolutes, stop-procedure, forbidden list) | T6 | §1.7 | M | pending |
| T8 | Add one section per convention subsection with fenced `<angle-bracket>`-placeholder command blocks + inline comments | T7 | §1.8 | L | pending |
| T9 | Add ordered `DebugEscalation` section: events → logs → describe → exec/debug | T8 | §1.9 | M | pending |
| T10 | Add `ScopeFirewall` DO/DON'T block with pre-action validation gate + report-and-stop fallback | T9 | §1.10 | S | pending |
| T11 | Add `ReferenceLink` citations — four bare-relative on-demand reference paths (no `./`, no `.claude/...`) | T10 | §1.11 | S | pending |
| T12 | **Verify Slice 1** — directory/files present; `using-kubectl-cli` dir name; all four references exist | T11 | §1.12 | S | pending |
| T13 | **Verify Slice 1** — `TripleIdentity` holds; `description` quoted/parses; all five frontmatter fields present | T12 | §1.13 | S | pending |
| T14 | **Verify Slice 1** — `BodyBudget` (<500, target <200); bare-relative links resolve; guardrail/scope-firewall/debug-escalation present; all convention subsections covered; manual trigger check; `skill-creator` use or OQ1 deviation recorded | T13 | §1.14 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 (the only slice) complete and verified. No further sessions — feature ends here.
