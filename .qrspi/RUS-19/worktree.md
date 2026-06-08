# Work Tree — Create a new agent skill for the atmos CLI

**Plan basis:** plan.md @ 2026-06-08T00:00:00Z
**Generated:** 2026-06-08T00:00:00Z
**Status:** draft
**Total sessions:** 3
**Critical path:** T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8 → T9 → T14 → T15 → T16 (12 tasks)

> Single-slice plan (16 steps, all under "Slice 1"). The slice is markdown-only and is
> authored via the `skill-creator` skill (mandatory authoring path — see plan §Authoring
> directive). Sessions are split to keep each load manifest under the 40% context budget and
> to place a fresh-context boundary between (a) the SKILL.md body authoring and (b) the five
> reference files, which are the bulk of the prose. Pre-authoring blockers OQ1/OQ2 (frontmatter
> schema + directory name `atmos`) must be resolved before T2, per plan §Pre-authoring blockers.

## Session 1 — Scaffold + SKILL.md (frontmatter + six-section body)

**Load:** structure.md §Contracts (Frontmatter shape, Description triggering, Prose-pointer
        disclosure), structure.md §Files touched, plan.md §Slice 1 (Setup + Core Logic steps 1–8),
        design.md §Desired End State
**Estimated context:** ~25%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Invoke `skill-creator` to scaffold the skill at `.claude/skills/atmos/` (mandatory authoring path) | — | §1 | S | pending |
| T2 | Create `SKILL.md` frontmatter (`name, description, command, argument-hint, allowed-tools`; `name: atmos`) — resolve OQ1/OQ2 first | T1 | §2 | S | pending |
| T3 | Append body section **Stack-targeting model** ending in `references/stack-yaml-schema.md` pointer | T2 | §3 | S | pending |
| T4 | Append body section **Vendor / create** ending in `references/vendoring.md` pointer | T3 | §4 | S | pending |
| T5 | Append body section **Configure-in-stack** ending in `references/stack-yaml-schema.md` pointer | T4 | §5 | S | pending |
| T6 | Append body section **Two-stage plan/apply** ending in `references/cli-reference.md` pointer | T5 | §6 | S | pending |
| T7 | Append body section **Cross-component data sharing** ending in stack-yaml-schema + cli-reference pointers | T6 | §7 | S | pending |
| T8 | Append body section **Debugging** ending in `references/troubleshooting.md` pointer (completes six-section body) | T7 | §8 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** SKILL.md body complete. The five reference files are the prose bulk; a fresh context
keeps the reference-authoring session clean and well under the 40% budget. Only the completed
SKILL.md pointer set carries forward as input.

## Session 2 — Five reference files

**Load:** structure.md §Files touched (references list), plan.md §Slice 1 (Core Logic steps 9–13),
        SKILL.md pointer set (the six body pointers from Session 1, for closure — notes only)
**Estimated context:** ~30%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T9 | Create `references/stack-yaml-schema.md` (import/vars/components/settings/env/metadata/backend; deep-merge; catalog; inheritance; name_pattern; region mixins; remote-state) | T8 | §9 | L | pending |
| T10 | Create `references/vendoring.md` (`atmos vendor pull`; vendor.yaml + component.yaml; mixins; commit-vs-JIT; Overrides; version pinning) | T8 | §10 | M | pending |
| T11 | Create `references/workflows.md` (`workflows/` YAML; step types; default stack; `atmos workflow`; `--dry-run`, `--from-step`) | T8 | §11 | M | pending |
| T12 | Create `references/cli-reference.md` (terraform plan/apply/deploy; `--from-plan`; varfile/backend gen; describe; validate; providers; helmfile) | T8 | §12 | M | pending |
| T13 | Create `references/troubleshooting.md` (`describe component`; `ATMOS_LOGS_LEVEL`; common errors; `validate stacks`, `terraform validate`) | T8 | §13 | M | pending |

--- SESSION BOUNDARY ---
**Reason:** All authored files exist. Verification (skill-creator eval + mechanical checks +
manual e2e triggering) is a distinct activity needing a fresh context and a different load
manifest (verification commands, not authoring content).

## Session 3 — Eval + verification

**Load:** plan.md §Slice 1 (Tests step 14, Verify steps 15–16), structure.md §Verification,
        the authored `.claude/skills/atmos/` tree
**Estimated context:** ~20%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T14 | Run the `skill-creator` eval loop against `.claude/skills/atmos/` (frontmatter validity, triggering, budget) | T9, T10, T11, T12, T13 | §14 | M | pending |
| T15 | **Checkpoint — mechanical**: frontmatter parse + field order + `name: atmos`; body < 500 lines; all five references exist; no dangling/orphan pointers; six sections each end in a pointer | T14 | §15 | S | pending |
| T16 | **Checkpoint — manual e2e triggering**: fresh session, atmos infra intent triggers skill and a cited reference loads on demand | T15 | §16 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete and verified. End of work tree (single-slice ticket).
