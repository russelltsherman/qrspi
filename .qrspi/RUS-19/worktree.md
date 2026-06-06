# Work Tree — Create a new agent skill for the atmos CLI

**Plan basis:** plan.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total sessions:** 2
**Critical path:** T1 → T2 → T3 → T4 → T6 → T7 → T8 → T9 → T10 → T11 → T12 → T13 → T14 → T20 → T21 → T22 (16 tasks)

> **Conditional scope (OQ3):** Session 1 (Slice 1, the acceptance checker) exists
> only if OQ3 = Decision 3 Option A. If Option B is chosen, skip Session 1 entirely
> (tasks T1–T7); Session 2's acceptance gate (T20/T21) falls back to manual `wc -l`
> body check + five-reference presence check. OQ1 (frontmatter schema) and OQ2 (skill
> dir name `atmos`) must be confirmed before Session 2.

## Session 1 — Slice 1: Acceptance checker (TDD)

**Load:** structure.md §Contracts (parse_frontmatter / check_skill / Violation /
        Frontmatter signatures), plan.md §Slice 1 (steps 1–7)
**Estimated context:** ~15% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create `scripts/atmos_skill_check.py` — shebang, docstring, stdlib imports (`sys`, `pathlib.Path`, `re`); no logic | — | §1 | S | pending |
| T2 | Add `parse_frontmatter(text) -> Frontmatter \| None` (leading `---`-fenced block → `dict[str,str]`, else `None`) | T1 | §2 | S | pending |
| T3 | Add `check_skill(skill_dir) -> list[Violation]` — four checks: 5-field frontmatter schema, `name`==dir, body <500 lines / ~5000-token guard, five non-empty `references/*.md` | T2 | §3 | M | pending |
| T4 | Add `__main__` CLI entrypoint — read `argv[1]`, print violations, exit 0/1 | T3 | §4 | S | pending |
| T5 | `chmod +x scripts/atmos_skill_check.py` (script-entrypoint convention) | T4 | §5 | S | pending |
| T6 | Create `scripts/atmos_skill_check_test.py` — stdlib `tempfile` fixtures: pass case + each failure mode + `parse_frontmatter` `None` path | T4 | §6 | M | pending |
| T7 | **Verify Slice 1** — `python3 scripts/atmos_skill_check_test.py` all pass; CLI exits 1 on malformed fixture, 0 on well-formed | T5, T6 | §7 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete and gated. Fresh context for Slice 2; the checker is now a callable acceptance gate, so only its CLI invocation (not its source) needs to carry forward.

## Session 2 — Slice 2: The atmos skill (SKILL.md + five references)

**Load:** structure.md §Contracts (skill frontmatter schema), plan.md §Slice 2
        (steps 8–22), impl-log.md §Slice 1 (checker CLI invocation only),
        design.md §Desired End State (acceptance-criteria mapping). Author via the
        `skill-creator` skill + its eval/triggering loop; verify atmos facts against
        atmos docs while writing (Q7/Q10/Q12, Risk rows 3 & 5).
**Estimated context:** ~30% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T8 | Create `.claude/skills/atmos/SKILL.md` — frontmatter only: 5-field schema `name: atmos`(==dir), trigger-phrase `description`, `command`, `argument-hint`, `allowed-tools` | T7 | §8 | S | pending |
| T9 | Add stack-targeting section (namespace/tenant/environment/stage, `name_pattern`) → pointer to `references/stack-yaml-schema.md` | T8 | §9 | M | pending |
| T10 | Add vendor/create section → pointer to `references/vendoring.md` | T9 | §10 | S | pending |
| T11 | Add configure-in-stack section (catalog + abstract/concrete inheritance) → pointer to `references/stack-yaml-schema.md` | T10 | §11 | M | pending |
| T12 | Add two-stage plan/apply + safety section (`plan --out` / `apply --from-plan`, `deploy` caution) → pointer to `references/cli-reference.md` | T11 | §12 | M | pending |
| T13 | Add remote-state / cross-component section (`!terraform.state` vs `!terraform.output`, `remote-state`) → pointers to schema + cli-reference | T12 | §13 | M | pending |
| T14 | Add debugging/troubleshooting section (`describe component`, `validate stacks`, `ATMOS_LOGS_LEVEL`) → pointer to `references/troubleshooting.md`; confirm body <500 lines / ~5000 tokens | T13 | §14 | M | pending |
| T15 | Create `references/stack-yaml-schema.md` (import/vars/components/settings/env/metadata/backend, deep-merge, catalog, inheritance, targeting, remote-state) — non-empty | T8 | §15 | M | pending |
| T16 | Create `references/vendoring.md` (`vendor pull`, `vendor.yaml`/`component.yaml`, mixins, JIT vs commit, overrides, version pinning) — non-empty | T8 | §16 | M | pending |
| T17 | Create `references/workflows.md` (`workflows/` YAML, step types, default stack, `workflow -f`, `--dry-run`/`--from-step`) — non-empty | T8 | §17 | S | pending |
| T18 | Create `references/cli-reference.md` (plan/apply/deploy, `--from-plan`, varfile/backend gen, describe, validate, providers, helmfile) — non-empty | T8 | §18 | M | pending |
| T19 | Create `references/troubleshooting.md` (`describe component`, `ATMOS_LOGS_LEVEL`, common errors, `validate stacks`) — non-empty | T8 | §19 | S | pending |
| T20 | Acceptance gate: `python3 scripts/atmos_skill_check.py .claude/skills/atmos` exits 0 (OQ3=B fallback: manual `wc -l` + five-ref presence) | T14, T15, T16, T17, T18, T19 | §20 | S | pending |
| T21 | **Verify Slice 2** — checker exits 0; manual review every body section ends in a pointer + each design acceptance criterion maps to a section/ref; authored via `skill-creator` eval loop | T20 | §21 | S | pending |
| T22 | **Checkpoint** — `python3 scripts/atmos_skill_check_test.py` still passes (no checker regression) | T21 | §22 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Final session. Feature complete after T22; no further sessions required.
