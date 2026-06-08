# Implementation Plan — Create a new agent skill for the atmos CLI

**Structure basis:** structure.md @ 2026-06-08T00:00:00Z
**Generated:** 2026-06-08T00:00:00Z
**Status:** draft
**Total steps:** 16

> Scope note: this ticket delivers a markdown skill only — no code, no functions, no
> programmatic tests (ref: design.md §Delta "Tests/queries: none"). Verification is therefore
> mechanical-on-markdown (frontmatter parse, line/token budget, pointer resolution) plus the
> out-of-scope `skill-creator` eval and a manual e2e triggering check, matching the repo's
> "real validation = manual e2e" reality (ref: design.md Decision 3).
>
> Authoring directive: the skill MUST be authored via the `skill-creator` skill and run through
> its eval loop (global memory directive; design.md §Desired End State / Decision 3). The
> file-by-file steps below describe the artifact `skill-creator` must produce; invoke
> `skill-creator` to drive the authoring rather than hand-writing the files ad-hoc.
>
> Pre-authoring blockers: resolve OQ1 (frontmatter schema reconciliation) and OQ2 (skill
> directory name `atmos`) before Step 1 — both determine the directory name and `name:` field
> (ref: structure.md §Unverified Assumptions). Steps below assume the in-repo five-field schema
> and the name `atmos`; if either resolves otherwise, adjust the directory/`name` accordingly.

## Slice 1: Author the atmos skill (SKILL.md + five references) via skill-creator

### Setup

1. ✨ Invoke the `skill-creator` skill to scaffold a new skill at `.claude/skills/atmos/` —
   this is the mandatory authoring path (ref: structure.md Verification bullet 1). All
   subsequent file steps describe content `skill-creator` produces and the implementer reviews.

2. ✨ Create `.claude/skills/atmos/SKILL.md` (frontmatter only) — open with `---`-delimited
   YAML in the in-repo observed field order: `name, description, command, argument-hint,
   allowed-tools`. Set `name: atmos` (MUST equal the directory name `atmos`, the triple-identity
   key — ref: structure.md Contracts "Frontmatter shape"). `description` uses the `qrspi-work`
   quoted-description-with-trigger-phrases style scoped to atmos / Cloud-Posse infra intents
   (ref: structure.md Contracts "Description triggering"). `name`/`description` together satisfy
   the agentskills.io minimal pair.

### Core Logic

3. ⚠️ Modify `.claude/skills/atmos/SKILL.md` — append body section **Stack-targeting model**:
   namespace/tenant/environment/stage and `stacks.name_pattern`. End the section with a prose
   pointer ``see `references/stack-yaml-schema.md` `` (backticked relative path inside an
   instruction sentence — not a markdown link — ref: structure.md Contracts "Prose-pointer
   disclosure").
   - **Current:** frontmatter only (from Step 2)
   - **After:** frontmatter + Stack-targeting section ending in a stack-yaml-schema pointer

4. ⚠️ Modify `.claude/skills/atmos/SKILL.md` — append body section **Vendor / create**:
   `atmos vendor pull`, `vendor.yaml`, per-component `component.yaml`. End with a prose pointer
   ``see `references/vendoring.md` ``.
   - **Current:** body through Stack-targeting section
   - **After:** + Vendor/create section ending in a vendoring pointer

5. ⚠️ Modify `.claude/skills/atmos/SKILL.md` — append body section **Configure-in-stack**:
   catalog pattern, `metadata.type: abstract`, `metadata.inherits`. End with a prose pointer
   ``see `references/stack-yaml-schema.md` ``.
   - **Current:** body through Vendor/create section
   - **After:** + Configure-in-stack section ending in a stack-yaml-schema pointer

6. ⚠️ Modify `.claude/skills/atmos/SKILL.md` — append body section **Two-stage plan/apply**:
   `plan --out` → `apply --from-plan`, with a caution on `deploy` auto-approval. End with a
   prose pointer ``see `references/cli-reference.md` ``.
   - **Current:** body through Configure-in-stack section
   - **After:** + plan/apply section ending in a cli-reference pointer

7. ⚠️ Modify `.claude/skills/atmos/SKILL.md` — append body section **Cross-component data
   sharing**: `!terraform.state` vs `!terraform.output` and the `remote-state` module. End with
   a prose pointer ``see `references/stack-yaml-schema.md` `` (and the cli-reference where
   `remote-state` invocation detail lives, per design.md §Desired End State).
   - **Current:** body through plan/apply section
   - **After:** + data-sharing section ending in a prose pointer

8. ⚠️ Modify `.claude/skills/atmos/SKILL.md` — append body section **Debugging**:
   `atmos describe component`, `validate stacks`, `ATMOS_LOGS_LEVEL`. End with a prose pointer
   ``see `references/troubleshooting.md` ``. This completes the six-section lifecycle body
   (ref: structure.md Verification bullet 5).
   - **Current:** body through data-sharing section
   - **After:** complete six-section body, each section ending in a prose pointer

9. ✨ Create `.claude/skills/atmos/references/stack-yaml-schema.md` — `import`/`vars`/
   `components`/`settings`/`env`/`metadata`/`backend`; deep-merge/import-ordering; catalog
   pattern; abstract/concrete inheritance; namespace/tenant/environment/stage; `name_pattern`;
   region mixins; remote-state YAML functions and module (ref: structure.md Files touched).
   Covers exactly the topics the Stack-targeting, Configure-in-stack, and data-sharing pointers
   promise.

10. ✨ Create `.claude/skills/atmos/references/vendoring.md` — `atmos vendor pull`; `vendor.yaml`
    and per-component `component.yaml`; mixins; commit-vs-JIT vendoring; Terraform Overrides
    (`.override.tf`) vs forking; version pinning with `{{.Version}}` (ref: structure.md Files
    touched). Covers exactly what the Vendor/create pointer promises.

11. ✨ Create `.claude/skills/atmos/references/workflows.md` — `workflows/` YAML; step types
    (`atmos`/`shell`); workflow-level default stack; `atmos workflow <name> -f <file>`;
    `--dry-run`, `--from-step` (ref: structure.md Files touched).

12. ✨ Create `.claude/skills/atmos/references/cli-reference.md` — terraform plan/apply/deploy;
    `--from-plan`; generate varfile/backend; auto-generated backend; `describe component`/
    `describe stacks`; validate; providers; helmfile (secondary) (ref: structure.md Files
    touched). Covers exactly what the plan/apply and data-sharing pointers promise.

13. ✨ Create `.claude/skills/atmos/references/troubleshooting.md` — `describe component` as the
    primary debug command; `ATMOS_LOGS_LEVEL`; common errors (missing `name_pattern`, tenant
    omitted, version mismatch); `validate stacks`, `terraform validate` (ref: structure.md
    Files touched). Covers exactly what the Debugging pointer promises.

### Tests

14. Run the `skill-creator` eval loop against `.claude/skills/atmos/` (process criterion — ref:
    structure.md Verification bullet 1; global memory "Use skill-creator for skills").
    - **Expected:** eval passes (frontmatter validity, triggering, budget) per skill-creator's
      own rules. This is the out-of-scope eval, not an in-repo test suite.

### Verify Slice 1

15. **Checkpoint — mechanical (frontmatter, budget, pointer/reference closure):**

    ```sh
    cd /workspaces/qrspi/.worktrees/RUS-19 && \
    python3 -c "import sys,yaml; t=open('.claude/skills/atmos/SKILL.md').read(); \
      fm=t.split('---',2)[1]; d=yaml.safe_load(fm); \
      assert list(d)[:5]==['name','description','command','argument-hint','allowed-tools'], d; \
      assert d['name']=='atmos', d['name']; print('frontmatter OK')" && \
    body_lines=$(awk 'n==2{print} /^---$/{n++}' .claude/skills/atmos/SKILL.md | wc -l) && \
    echo "body lines: $body_lines" && [ "$body_lines" -lt 500 ] && \
    for f in stack-yaml-schema vendoring workflows cli-reference troubleshooting; do \
      test -f ".claude/skills/atmos/references/$f.md" || { echo "MISSING $f"; exit 1; }; done && \
    grep -oE 'references/[a-z-]+\.md' .claude/skills/atmos/SKILL.md | sort -u | \
      while read p; do test -f ".claude/skills/atmos/$p" || { echo "DANGLING $p"; exit 1; }; done && \
    echo "all checks passed"
    ```

    - [ ] Frontmatter parses as YAML; first five fields are `name, description, command,
          argument-hint, allowed-tools` in order; `name: atmos` equals the directory name.
    - [ ] Body (frontmatter excluded) is under 500 lines / ~5000 tokens.
    - [ ] All five reference files exist under `references/`.
    - [ ] Every backticked `references/<file>.md` pointer in the body resolves to one of the
          five files (no dangling pointers, no orphan references).
    - [ ] All six lifecycle sections (stack-targeting, vendor/create, configure-in-stack,
          plan/apply, data sharing, debugging) are present and each ends with a prose pointer.

16. **Checkpoint — manual e2e triggering** (ref: structure.md Verification bullet 6): in a fresh
    Claude Code session in this repo, issue an atmos/Cloud-Posse infra intent (e.g. "vendor and
    plan the vpc component for the prod stack") and confirm the `atmos` skill triggers and the
    agent can load a cited reference (e.g. `references/cli-reference.md`) on demand.
    - [ ] Skill auto-triggers on an atmos infra intent.
    - [ ] A cited reference loads on demand when the body points to it.

---

## Rollback Notes

- Steps 2–13 (all new files): the skill is additive and self-contained — it is **not** indexed
  in `README.md` or `.claude/CLAUDE.md` (ref: design.md §Delta "Modified files: none"). To
  roll back, delete the directory `.claude/skills/atmos/` (`rm -rf
  /workspaces/qrspi/.worktrees/RUS-19/.claude/skills/atmos`). No other file references it, so
  removal leaves no dangling pointers and requires no catalog edits.
- No DB migrations, config changes, or destructive ops in this slice.
