# Structure Outline — Create a new agent skill for the atmos CLI

**Design basis:** design.md @ 2026-06-04T00:00:00Z
**Generated:** 2026-06-08T00:00:00Z
**Status:** draft

## New Types

This ticket delivers a markdown skill (`SKILL.md` + five `references/*.md`). It adds no
code, no functions, and no programmatic types (ref: design.md §Delta "Tests/queries: none").
The only "type-like" artifact is the SKILL.md frontmatter document shape, captured below as a
contract.

- _(none — markdown content only)_

## Modified Types

- _(none — Modified files: none, per design.md §Delta)_

## Contracts

These are the cross-file interfaces the slice must honor internally — not code signatures, but
the conventions that bind the body to its references and the skill to the in-repo loader.

- **Frontmatter shape** — `SKILL.md` opens with `---`-delimited YAML in the in-repo observed
  field order: `name, description, command, argument-hint, allowed-tools` (ref: design.md
  §Current State, Q1). `name: atmos` MUST equal the directory name (`.claude/skills/atmos/`),
  the triple-identity key (ref: Q1, Q3). `name`/`description` together satisfy the
  agentskills.io minimal pair (ref: §Desired End State).
- **Description triggering** — `description` uses the `qrspi-work` quoted-description-with-trigger-phrases
  style, scoped to atmos / Cloud-Posse infra intents (ref: design.md Risk Register, Q4).
- **Prose-pointer disclosure** — every body section ends by citing its reference as a
  backticked relative path inside an instruction sentence (e.g. ``see `references/stack-yaml-schema.md` ``),
  not a markdown link, no manifest field, no marker syntax (ref: design.md Decision 2, Q6).
  Each of the five reference filenames cited by the body MUST exist; each reference MUST cover
  exactly the topic its body section promises.
- **Body budget** — `SKILL.md` body (excluding frontmatter) stays under 500 lines / ~5000
  tokens; all depth is offloaded to `references/` (ref: design.md §Desired End State, Decision 2/3).
- **Five-document set** — the `references/` directory contains exactly:
  `stack-yaml-schema.md`, `vendoring.md`, `workflows.md`, `cli-reference.md`, `troubleshooting.md`
  (ref: design.md §Delta).

## Slice 1: Author the atmos skill (SKILL.md + five references) via skill-creator

**Goal:** A complete, self-contained `atmos` skill exists and loads — `SKILL.md` with valid
in-repo frontmatter and a lifecycle-organized body whose every section ends in a prose pointer,
plus the five named `references/*.md` files each covering the topic its pointer promises. This
is the full testable end-to-end path: the skill is discoverable by the `.claude/skills/*/SKILL.md`
scan, its body stays within budget, and every cited reference resolves. The design is one cohesive
markdown deliverable with no internal testability boundary (the body's pointers are meaningless
without their targets, and the references are scoped by the body), so it is a single slice
authored in one sitting via the `skill-creator` skill.

**Files touched:**

- ✨ `.claude/skills/atmos/SKILL.md` — frontmatter (`name: atmos`, quoted trigger-phrase
  description, `command`, `argument-hint`, `allowed-tools`) + body organized by the component
  lifecycle: stack-targeting model (namespace/tenant/environment/stage + `stacks.name_pattern`),
  vendor/create, configure-in-stack (catalog pattern + `metadata.type: abstract` / `metadata.inherits`),
  two-stage plan/apply (`plan --out` → `apply --from-plan`, `deploy` auto-approval caution),
  cross-component data sharing (`!terraform.state` vs `!terraform.output`, `remote-state` module),
  debugging (`atmos describe component`, `validate stacks`, `ATMOS_LOGS_LEVEL`). Each section ends
  with a prose pointer into its matching reference.
- ✨ `.claude/skills/atmos/references/stack-yaml-schema.md` — `import`/`vars`/`components`/`settings`/
  `env`/`metadata`/`backend`; deep-merge/import-ordering; catalog pattern; abstract/concrete
  inheritance; namespace/tenant/environment/stage; `name_pattern`; region mixins; remote-state YAML
  functions and module.
- ✨ `.claude/skills/atmos/references/vendoring.md` — `atmos vendor pull`; `vendor.yaml` and
  per-component `component.yaml`; mixins; commit-vs-JIT vendoring; Terraform Overrides
  (`.override.tf`) vs forking; version pinning with `{{.Version}}`.
- ✨ `.claude/skills/atmos/references/workflows.md` — `workflows/` YAML; step types (`atmos`/`shell`);
  workflow-level default stack; `atmos workflow <name> -f <file>`; `--dry-run`, `--from-step`.
- ✨ `.claude/skills/atmos/references/cli-reference.md` — terraform plan/apply/deploy; `--from-plan`;
  generate varfile/backend; auto-generated backend; `describe component`/`describe stacks`; validate;
  providers; helmfile (secondary).
- ✨ `.claude/skills/atmos/references/troubleshooting.md` — `describe component` as primary debug
  command; `ATMOS_LOGS_LEVEL`; common errors (missing `name_pattern`, tenant omitted, version
  mismatch); `validate stacks`, `terraform validate`.

**Verification:**

- [ ] Authored via the `skill-creator` skill and run through its eval loop (process criterion,
      per global memory directive and design.md §Desired End State / Decision 3).
- [ ] `SKILL.md` frontmatter parses as YAML, carries the five in-repo fields in order, and
      `name: atmos` equals the directory name.
- [ ] `SKILL.md` body (excluding frontmatter) is under 500 lines / ~5000 tokens — checked by
      line count / token estimate at authoring time and by the skill-creator eval.
- [ ] All five reference files exist under `references/`, and every backticked
      `references/<file>.md` pointer in the body resolves to one of them (no dangling pointers,
      no orphan references).
- [ ] Each body lifecycle section (stack-targeting, vendor/create, configure-in-stack, plan/apply,
      data sharing, debugging) is present and ends with a prose pointer.
- [ ] Manual end-to-end check: the skill triggers on an atmos/Cloud-Posse infra intent and the
      agent can load a cited reference on demand (matches repo's "real validation = manual e2e").

**Context cost:** L
**Depends on:** none

---

## Unverified Assumptions

These are claims from design.md that could not be mapped to a concrete file/interface decision and
need human attention before planning. Both are the design's own Open Questions, unresolved.

- **OQ1 — frontmatter schema reconciliation (design.md §Open Questions, Risk Register).** It is
  unverified whether the agentskills.io standard mandates a frontmatter schema that conflicts with
  the in-repo five-field schema, and if so which wins (in-repo loader vs external standard). The
  Frontmatter-shape contract above assumes the in-repo five-field schema with `name`/`description`
  as the shared core; if OQ1 resolves the other way, that contract changes. agentskills.io is not
  referenced anywhere in-repo, so conformance cannot be verified from the project.
- **OQ2 — skill directory name (design.md §Open Questions).** The name `atmos` (no `qrspi-` prefix,
  since this is not a workflow phase) is proposed but unconfirmed. The only observed naming
  convention is lowercase-hyphenated, project-prefixed for phase skills. Whether a non-prefixed
  name is acceptable is unverified; the directory name and `name:` frontmatter field both depend on
  this answer (triple-identity key, Q1/Q3).
- **skill-creator / writing-bash-scripts internals (design.md Risk Register, Q7).** These global/plugin
  skills were unreadable in research, so the exact authoring rules and eval mechanics they impose are
  unknown. The slice treats their use as a live process step the implementer performs; no assumptions
  about their internals are encoded here.
