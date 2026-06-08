# Work Tree — Create an agent skill for the Argo Workflows CLI

**Plan basis:** plan.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total sessions:** 3
**Critical path:** T1 → T2 → T3 → T5 → T6 → T7 → T14 → T15 (8 tasks)

> Single-slice feature (plan Slice 1 only). Tasks are split across three sessions
> to isolate the bulk reference-file authoring (heaviest output) into its own
> context. T1 is a hard BLOCKING gate: if `skill-creator` is unavailable, STOP and
> escalate — every downstream task is invalid without it.

## Session 1 — Skill scaffold + SKILL.md

**Load:** plan.md §Slice 1 (Setup + Core Logic steps 1–7), structure.md §Contracts
        (frontmatter-schema, triple-name-invariant, hard-stop-prereq,
        description-trigger-contract, reference-link-contract, body-size-budget),
        design §Risk #1 / OQ1–5
**Estimated context:** ~20%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | **Gate (BLOCKING):** confirm `skill-creator` available; author via it + run its eval loop, else STOP and escalate | — | §1.1 | S | pending |
| T2 | Resolve naming/scoping decisions (OQ1 dirname, OQ2 ref split, OQ3 argo version, OQ5 allowed-tools) | T1 | §1.2 | S | pending |
| T3 | Create SkillDir `.claude/skills/using-argo-workflows-cli/` (basename == resolved name) | T2 | §1.3 | S | pending |
| T4 | Create `references/` subdirectory (ReferenceSet holder) | T3 | §1.4 | S | pending |
| T5 | Create `SKILL.md` — frontmatter only (5 keys; name==dirname, command==/dirname; no claude.tools shape) | T3 | §1.5 | S | pending |
| T6 | Append SKILL.md body — purpose paragraph + argo prereq availability check w/ hard-stop-on-failure | T5 | §1.6 | S | pending |
| T7 | Append SKILL.md routing — relative `references/<file>.md` pointers at decision points; keep body <~500 lines/~5000 tokens | T6 | §1.7 | M | pending |

--- SESSION BOUNDARY ---
**Reason:** Skill scaffold and SKILL.md body complete. The four reference files are
the bulk of authored content (one is L); start them with fresh context so the body
work doesn't crowd the window.

## Session 2 — Reference files (bulk authoring)

**Load:** plan.md §Slice 1 (Core Logic steps 8–11), structure.md §Contracts
        (coverage-contract), impl-log.md §Slice 1 (scaffold notes only — resolved
        ref-file names + command-group split)
**Estimated context:** ~30%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T8 | Author `references/submission-and-monitoring.md` (submit/lint/dry-run, params, --from, list/get/logs/watch, @latest, container selection) | T4 | §1.8 | M | pending |
| T9 | Author `references/debugging-and-lifecycle.md` (debug escalation argo get→logs→kubectl describe; retry/resubmit/stop/terminate/suspend/resume/delete) | T4 | §1.9 | M | pending |
| T10 | Author `references/authoring.md` (DAG-vs-Steps, templates/templateRef, params, artifacts/GC, retry/backoff/timeouts, resource mgmt/parallelism/synchronization) | T4 | §1.10 | L | pending |
| T11 | Author `references/cron-workflows.md` (cron lifecycle, concurrency policy, timezone) | T4 | §1.11 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** All reference files authored. Catalog edits + eval loop + the manual
contract verification are a distinct validation concern; fresh context keeps the
authored prose out of the way during cross-file checks.

## Session 3 — Catalog updates, eval, verify

**Load:** plan.md §Slice 1 (Catalog/Tests/Verify steps 12–15), structure.md §Contracts,
        impl-log.md §Slice 1 (resolved skill name + file list)
**Estimated context:** ~25%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T12 | Modify `README.md` — add skill to skills table + directory tree (name == dirname) | T7 | §1.12 | S | pending |
| T13 | Modify `.claude/CLAUDE.md` — add `/using-argo-workflows-cli` to Available skills (name == dirname) | T7 | §1.13 | S | pending |
| T14 | Run `skill-creator` eval loop against authored skill (only automated authoring check) | T7, T8, T9, T10, T11 | §1.14 | M | pending |
| T15 | **Verify Slice 1** — run manual contract checks (triple-name, frontmatter-schema, reference-link, body-size, coverage, hard-stop-prereq, description-trigger, catalog presence) | T12, T13, T14 | §1.15 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Final slice — no successor session. Boundary marks end of work tree.
