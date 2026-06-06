# Implementation Plan — Create a new agent skill for the atmos CLI

**Structure basis:** structure.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total steps:** 22

> **Conditional scope (OQ3):** Slice 1 exists only if OQ3 resolves to Decision 3
> Option A (build the checker). If the human chooses Option B, skip steps 1–7 and
> use steps 19–20 (manual `wc -l` + five-doc presence check) as Slice 2's
> verification gate in place of the checker. OQ1 (frontmatter schema) and OQ2
> (skill dir name `atmos`) must be confirmed before Slice 2 authoring; both slices
> assume `name: atmos` == dir == all paths below.

## Slice 1: Acceptance checker (TDD)

### Setup

1. ✨ Create `scripts/atmos_skill_check.py` — new stdlib-only checker entrypoint. Add shebang `#!/usr/bin/env python3`, module docstring naming the three checkable acceptance criteria (frontmatter shape, body line/token budget, five-reference presence), and stdlib imports (`sys`, `pathlib.Path`, `re`). No logic yet.

### Core Logic

2. ⚠️ Modify `scripts/atmos_skill_check.py` — add `parse_frontmatter(text: str) -> Frontmatter | None` per Contracts, where `Frontmatter = dict[str, str]`.
   - **Current:** file has docstring + imports only.
   - **After:** function extracts the leading `---`-fenced YAML-ish block; returns a `dict[str, str]` of key/value pairs, or `None` if no valid leading fenced block is present.
3. ⚠️ Modify `scripts/atmos_skill_check.py` — add `check_skill(skill_dir: Path) -> list[Violation]` per Contracts, where `Violation = str`. Accumulate into a `list[Violation]`; empty list == pass.
   - **Current:** has `parse_frontmatter` only.
   - **After:** runs all four checks — (a) frontmatter present with the five-field schema `name, description, command, argument-hint, allowed-tools`, `name`/`description` non-empty; (b) frontmatter `name` == `skill_dir.name`; (c) `SKILL.md` body (content after frontmatter) < 500 lines exact and within ~5000-token approximate guard; (d) the five `references/*.md` (`stack-yaml-schema.md, vendoring.md, workflows.md, cli-reference.md, troubleshooting.md`) exist and are non-empty.
4. ⚠️ Modify `scripts/atmos_skill_check.py` — add CLI entrypoint under `if __name__ == "__main__":`.
   - **Current:** has `parse_frontmatter` + `check_skill`.
   - **After:** reads `sys.argv[1]` as `skill_dir`, calls `check_skill`, prints each violation to stdout, exits `0` when no violations else `1` (`python3 scripts/atmos_skill_check.py <skill_dir>`).
5. Set exec bit: `chmod +x scripts/atmos_skill_check.py` (repo convention for script entrypoints).

### Tests

6. ✨ Create `scripts/atmos_skill_check_test.py` — stdlib-only `_test.py` sibling using `tempfile` temp-dir fixtures. Cover: a well-formed skill dir (pass / empty violations) and each failure mode independently — missing frontmatter field, `name` != dir, over-budget body (>500 lines), missing reference file, empty reference file. Assert `parse_frontmatter` returns `None` for a body with no leading fence.

### Verify Slice 1

7. **Checkpoint:** `python3 scripts/atmos_skill_check_test.py`
   - [ ] All tests pass (every `check_skill` branch and the `parse_frontmatter` `None` path covered).
   - [ ] CLI against a deliberately malformed temp fixture dir exits `1` and prints the violation; against a well-formed fixture exits `0`.

---

## Slice 2: The atmos skill (SKILL.md + five references)

> Author this slice through the `skill-creator` skill and its eval/triggering loop
> (process criterion, ref: Q7/Q12). Verify atmos CLI factual claims against atmos
> docs while authoring (ref: Q10, Risk row 5).

### Setup

8. ✨ Create `.claude/skills/atmos/SKILL.md` — add frontmatter only first: the in-repo five-field schema `name: atmos` (== dir), `description` (quoted, with atmos/Cloud-Posse trigger phrases per the `qrspi-work` pattern, Risk row 3), `command`, `argument-hint`, `allowed-tools`. `name`/`description` non-empty (agentskills.io core). Body added in steps 9–14.

### Core Logic

9. ⚠️ Modify `.claude/skills/atmos/SKILL.md` — add the stack-targeting model section: namespace/tenant/environment/stage and `stacks.name_pattern`. End with a prose pointer (backticked relative path) to `references/stack-yaml-schema.md`.
   - **Current:** frontmatter only.
   - **After:** frontmatter + stack-targeting section with reference pointer.
10. ⚠️ Modify `.claude/skills/atmos/SKILL.md` — add the vendor/create section. End with a prose pointer to `references/vendoring.md`.
    - **Current:** through stack-targeting section.
    - **After:** + vendor/create section.
11. ⚠️ Modify `.claude/skills/atmos/SKILL.md` — add the configure-in-stack section (catalog pattern + abstract/concrete inheritance, `metadata.type: abstract` / `metadata.inherits`). End with a prose pointer to `references/stack-yaml-schema.md`.
    - **Current:** through vendor/create section.
    - **After:** + configure-in-stack section.
12. ⚠️ Modify `.claude/skills/atmos/SKILL.md` — add the two-stage plan/apply + safety section (`plan --out` then `apply --from-plan`; caution on `deploy` auto-approval). End with a prose pointer to `references/cli-reference.md`.
    - **Current:** through configure-in-stack section.
    - **After:** + plan/apply section.
13. ⚠️ Modify `.claude/skills/atmos/SKILL.md` — add the remote-state / cross-component data-sharing section (`!terraform.state` vs `!terraform.output`, `remote-state` module). End with prose pointers to `references/stack-yaml-schema.md` and `references/cli-reference.md`.
    - **Current:** through plan/apply section.
    - **After:** + remote-state section.
14. ⚠️ Modify `.claude/skills/atmos/SKILL.md` — add the debugging/troubleshooting section (`atmos describe component`, `validate stacks`, `ATMOS_LOGS_LEVEL`). End with a prose pointer to `references/troubleshooting.md`. Confirm body stays under 500 lines / ~5000 tokens.
    - **Current:** through remote-state section.
    - **After:** complete body, all six lifecycle sections present, each ending in a reference pointer.

15. ✨ Create `.claude/skills/atmos/references/stack-yaml-schema.md` — `import`/`vars`/`components`/`settings`/`env`/`metadata`/`backend`; deep-merge & import-ordering; catalog pattern; abstract/concrete inheritance; namespace/tenant/environment/stage; `name_pattern`; region mixins; remote-state YAML functions and module. Non-empty.
16. ✨ Create `.claude/skills/atmos/references/vendoring.md` — `atmos vendor pull`; `vendor.yaml` and per-component `component.yaml`; mixins; commit-vs-JIT vendoring; Terraform Overrides (`.override.tf`) vs forking; version pinning with `{{.Version}}`. Non-empty.
17. ✨ Create `.claude/skills/atmos/references/workflows.md` — `workflows/` YAML; step types (`atmos`/`shell`); workflow-level default stack; `atmos workflow <name> -f <file>`; `--dry-run`, `--from-step`. Non-empty.
18. ✨ Create `.claude/skills/atmos/references/cli-reference.md` — terraform plan/apply/deploy; `--from-plan`; generate varfile/backend; auto-generated backend; `describe component`/`describe stacks`; validate; providers; helmfile (secondary). Non-empty.
19. ✨ Create `.claude/skills/atmos/references/troubleshooting.md` — `describe component` as primary debug command; `ATMOS_LOGS_LEVEL`; common errors (missing `name_pattern`, tenant omitted, version mismatch); `validate stacks`, `terraform validate`. Non-empty.

### Tests

20. Run the acceptance gate: `python3 scripts/atmos_skill_check.py .claude/skills/atmos`
    - **Expected:** exits `0` (no violations). If OQ3=Option B, instead run `wc -l` on the body and confirm the five reference files exist and are non-empty manually.

### Verify Slice 2

21. **Checkpoint:** `python3 scripts/atmos_skill_check.py .claude/skills/atmos`
    - [ ] Exits `0` (frontmatter schema valid + `name`==dir, body < 500 lines, five references present and non-empty). OQ3=Option B fallback: manual `wc -l` body < 500 + five non-empty references confirmed.
    - [ ] Manual review: every body lifecycle section ends with a prose pointer to its matching reference; each acceptance criterion in design.md §Desired End State maps to a present body section or reference.
    - [ ] Skill authored through the `skill-creator` skill and its eval/triggering loop (process criterion, ref: Q7/Q12) — verified by the implementer invoking it, not a repo artifact.

22. **Checkpoint:** `python3 scripts/atmos_skill_check_test.py` still passes (no regression from any checker change made while authoring).
    - [ ] All Slice 1 tests pass.

---

## Rollback Notes

- Steps 1–6 (Slice 1): no DB/config/destructive changes — additive new files only. Rollback = delete `scripts/atmos_skill_check.py` and `scripts/atmos_skill_check_test.py`.
- Steps 8–19 (Slice 2): additive new files only under `.claude/skills/atmos/`. Rollback = remove the `.claude/skills/atmos/` directory. No existing files are modified (design.md §Delta — "Modified files: none required").
- OQ4 (optional README/CLAUDE.md skill-catalog listing) is not planned here; if added later it modifies existing docs and its rollback is reverting those doc edits.
