# Implementation Plan — Create a kubectl CLI agent skill

**Structure basis:** structure.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total steps:** 14

> This feature produces Markdown skill source only (no executable code). Steps
> create files and write Markdown sections; verification is manual per design
> (Q10/Q12 — `run_eval.py` is a stub, no trigger-logging exists). Steps are
> ordered so the four `references/` files exist before `SKILL.md` links to them,
> letting the link-resolution check pass.

## Slice 1: Author the using-kubectl-cli skill (SKILL.md + references)

### Setup

1. ✨ Create `.claude/skills/using-kubectl-cli/references/jsonpath.md` — empty file
   to establish the `references/` subdirectory (structure §Files touched; Decision 2).
   Purpose: JSONPath + custom-columns + jq extraction reference, populated in step 5.

### Core Logic

2. ✨ Create `.claude/skills/using-kubectl-cli/references/krew-plugins.md` — krew
   plugin catalog (ctx, ns, neat, tree, images, whoami, access-matrix) and provenance
   guidance (structure §Files touched; design §Delta).

3. ✨ Create `.claude/skills/using-kubectl-cli/references/rbac-debugging.md` — RBAC
   troubleshooting decision tree honoring the `DebugEscalation`-adjacent RBAC contract:
   `auth can-i` → bindings → subject form → NetworkPolicy/webhook (structure §Contracts).

4. ✨ Create `.claude/skills/using-kubectl-cli/references/common-errors.md` — common
   kubectl error messages with resolutions (structure §Files touched; design §Delta).

5. ⚠️ Modify `.claude/skills/using-kubectl-cli/references/jsonpath.md` — populate the
   placeholder from step 1 with JSONPath, custom-columns, and jq extraction examples.
   - **Current:** empty file (from step 1)
   - **After:** JSONPath/custom-columns/jq extraction reference content

6. ✨ Create `.claude/skills/using-kubectl-cli/SKILL.md` — write the YAML frontmatter
   satisfying `SkillFrontmatter` + `TripleIdentity` (structure §New Types, §Contracts):
   - `name: using-kubectl-cli`
   - `command: /using-kubectl-cli`
   - `description:` QUOTED scalar (Decision 3) with kubectl trigger phrasing
   - `argument-hint:` and `allowed-tools:` allowlist (five-field schema, design §Desired End State)

7. ⚠️ Modify `.claude/skills/using-kubectl-cli/SKILL.md` — add the top-of-body
   `GuardrailBlock` (structure §Contracts): `###`/`##` hazard heading, ALL-CAPS
   imperative, bolded absolutes, enumerated stop-procedure, "Explicitly forbidden"
   list; covers context verification, dry-run-before-delete, explicit namespace flags.
   - **Current:** file with frontmatter only (from step 6)
   - **After:** frontmatter + guardrail block near top

8. ⚠️ Modify `.claude/skills/using-kubectl-cli/SKILL.md` — add one section per
   convention subsection with fenced `<angle-bracket>`-placeholder command blocks and
   inline `#` comments: context/namespace, inspection, rollouts, debugging, apply
   strategies, output formatting, plugins/krew, RBAC, safety (design §Desired End State; Q6).
   - **Current:** frontmatter + guardrail block (from step 7)
   - **After:** + per-convention command-pattern sections

9. ⚠️ Modify `.claude/skills/using-kubectl-cli/SKILL.md` — add the ordered
   `DebugEscalation` section: events → logs → describe → exec/debug (structure §Contracts; Q8).
   - **Current:** body with command-pattern sections (from step 8)
   - **After:** + ordered debugging-escalation section

10. ⚠️ Modify `.claude/skills/using-kubectl-cli/SKILL.md` — add the `ScopeFirewall`
    enumerated DO/DON'T block with a pre-action validation gate and report-and-stop
    fallback (structure §Contracts; Q9).
    - **Current:** body with debug-escalation section (from step 9)
    - **After:** + scope-firewall block

11. ⚠️ Modify `.claude/skills/using-kubectl-cli/SKILL.md` — add `ReferenceLink` citations:
    bare relative paths `references/jsonpath.md`, `references/krew-plugins.md`,
    `references/rbac-debugging.md`, `references/common-errors.md` (no `./`, no `.claude/...`
    prefix), cited as on-demand prose ("see `references/...`") per structure §Contracts / Decision 2.
    - **Current:** complete body without reference links (from step 10)
    - **After:** + four bare-relative on-demand reference citations

### Tests

> No automated test exists (`run_eval.py` is a stub — design Q10). Per structure rule 9
> and the slice's verification, validation is the manual checkpoint below. Authoring
> should use the global `skill-creator` skill (and its eval loop) per memory directive +
> acceptance criterion; if `skill-creator` is unavailable (OQ1/Risk), hand-author to the
> agentskills.io structure and record the deviation in the slice PR.

### Verify Slice 1

12. **Checkpoint:** `ls .claude/skills/using-kubectl-cli/ && ls .claude/skills/using-kubectl-cli/references/`
    - [ ] `SKILL.md` and `references/` present; directory name is `using-kubectl-cli`
    - [ ] All four reference files exist: `jsonpath.md`, `krew-plugins.md`, `rbac-debugging.md`, `common-errors.md`

13. **Checkpoint:** `python3 -c "import yaml,sys; d=yaml.safe_load(open('.claude/skills/using-kubectl-cli/SKILL.md').read().split('---')[1]); print(d['name'], d['command'])"`
    (or manual frontmatter inspection if PyYAML is unavailable)
    - [ ] `TripleIdentity` holds: dir name == `name` == `command` minus `/` == `using-kubectl-cli`
    - [ ] `description` is a quoted YAML scalar and parses with no YAML break on `:`/`,`
    - [ ] Frontmatter carries all five fields (`name`, `description`, `command`, `argument-hint`, `allowed-tools`)

14. **Checkpoint:** `wc -l .claude/skills/using-kubectl-cli/SKILL.md` + manual review
    - [ ] `BodyBudget`: `SKILL.md` < 500 lines (target < 200); manual token spot-check
    - [ ] Every body reference link is bare-relative (`references/<file>.md`) and resolves from the skill directory
    - [ ] `GuardrailBlock`, `ScopeFirewall`, and ordered `DebugEscalation` sections present
    - [ ] All convention subsections covered with copy-pasteable `<angle-bracket>`-placeholder command blocks
    - [ ] Manual end-to-end: a kubectl-phrased prompt auto-invokes the skill (observed; no trigger-logging exists — Q12)
    - [ ] Authoring via `skill-creator` confirmed, or deviation recorded per OQ1

---

## Rollback Notes

- Steps 1–11 (all new files under `.claude/skills/using-kubectl-cli/`): no migration,
  config, or destructive operation. To reverse, delete the directory:
  `rm -rf .claude/skills/using-kubectl-cli/`. No orchestration script, registry, or
  `qrspi_persist.py` entry is touched (design §Delta), so removal leaves no dangling
  references.
- No DB migration, no config change, no destructive op in this plan.

## Open Questions carried from structure (resolve before/at implement)

- OQ1 — `skill-creator` availability/requirement (maps to step 12 verification, not a file).
- OQ2 — skill directory name `using-kubectl-cli` (all paths in steps 1–11 hinge on it).
- OQ3 — environment-specific cluster/namespace scope constraints for the `GuardrailBlock`/`ScopeFirewall` (steps 7, 10).
