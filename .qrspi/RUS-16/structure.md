# Structure Outline — Create a new agent skill for the kustomize CLI

**Design basis:** design.md @ 2026-06-04T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft

> Note: this ticket authors a documentation skill, not executable code. The
> "types" and "contracts" below are the repo conventions each authored file must
> satisfy (frontmatter schema, progressive-disclosure linking, guidance shapes)
> rather than program types/function signatures. There are no runtime modules.

## New Types

- `SkillFrontmatter { name: string, description: string, command: string, argument-hint: string, allowed-tools: string }`
  — the repo's identical five-field YAML block delimited by `---` lines, shared
  by all 10 in-repo skills (ref: design §Current State, Q4). For this skill:
  `name: kustomize-cli`, `command: /kustomize-cli`, `description` carries
  auto-invocation triggering text in the `qrspi-work` "Use when…/Trigger on…" +
  literal-example style (ref: design §Desired End State, Q6).

- `ReferenceLink { text: string, relativePath: "references/<file>.md" }`
  — convention-only progressive-disclosure pointer: `SKILL.md` body names a
  sibling file by relative path in prose; no loader/validator parses it
  (ref: design §Current State, Q3).

## Modified Types

- None. The design specifies no modifications to existing files (no agent body,
  no eval-suite entry, no `.claude/agents/` companion) (ref: design §Delta).

## Contracts

- `frontmatter` — `name` MUST equal the directory name (`kustomize-cli`) and
  `command` MUST be `/<name>` (`/kustomize-cli`) (ref: Q4).
- `referenceLink(path)` — every "see `references/…`" pointer in `SKILL.md` MUST
  resolve to an existing sibling file; unverified at runtime, so author must
  confirm each path manually before submit (ref: Q3, Risk Register).
- `deprecationGuidance(field)` — every deprecated construct stated as
  "prefer <current>, recognize legacy <old>" so legacy repos are not broken:
  `vars` → `replacements`, `patchesStrategicMerge`/`patchesJson6902` → `patches:`
  (ref: Q8).
- `secretExample()` — `secretGenerator`/`.env` examples reference an uncommitted
  `.env` plus a committed `.env.example` sibling, mirroring
  `.qrspi/config.json` ↔ `.qrspi/config.example.json`; no literal secret values
  (ref: Q9, Decision 4).
- `failureReporting()` — CI/validation guidance follows the repo doctrine: print
  the exact failing command + full stderr verbatim, then stop (ref: Q14).
- `sizeBudget(SKILL.md)` — body MUST be < 500 lines / < 5000 tokens; no automated
  gate exists, enforced by manual `wc -l`/token check and offloading into
  `references/` (ref: Q5, Decision 3).

## Slice 1: Author the kustomize-cli skill (SKILL.md + references)

**Goal:** A complete, invocable `kustomize-cli` skill delivered end-to-end — a
lean `SKILL.md` with valid five-field frontmatter and a populated `references/`
directory of four files, satisfying every acceptance criterion in one cohesive
authoring pass via `skill-creator`.
**Files touched:**

- ✨ `.claude/skills/kustomize-cli/SKILL.md` — frontmatter (`name: kustomize-cli`, triggering `description`, `command: /kustomize-cli`, `argument-hint`, `allowed-tools`); lean body: scope guidance, base/overlay/components conventions, inline example directory tree, one short section per resource type (patches, generators, transformers, components, replacements), the deprecation table, `kubectl apply -k` + GitOps integration section, and "see `references/…`" pointers (ref: Q1, Q4, Q6, Q7, Q13, Decision 1/2)
- ✨ `.claude/skills/kustomize-cli/references/patch-selection.md` — strategic-merge vs JSON 6902 decision framework (additive→strategic; remove-field / replace-array-item-by-index→JSON-6902), plus the `patchesStrategicMerge`/`patchesJson6902` → `patches:` deprecation (ref: Q8, Q11)
- ✨ `.claude/skills/kustomize-cli/references/generators.md` — `configMapGenerator`/`secretGenerator` patterns, `behavior:`/`generatorOptions`, and `.env` + `.env.example` secret handling mirroring the gitignore precedent (ref: Q9)
- ✨ `.claude/skills/kustomize-cli/references/transformers.md` — labels/annotations/namespace/images/namePrefix/replacements usage matrix, the `commonLabels`-breaks-selectors caution, and the `vars` → `replacements` deprecation (ref: Q8, Q10)
- ✨ `.claude/skills/kustomize-cli/references/ci-validation.md` — `kustomize build` per overlay, `kubeconform`/`conftest`/OPA, and the verbatim-error-on-failure reporting norm (ref: Q13, Q14)
**Verification:**
- [ ] Authored by invoking the `skill-creator` skill (ref: Q2; note in PR)
- [ ] `SKILL.md` frontmatter has all five fields; `name` == directory name; `command` == `/kustomize-cli`
- [ ] `wc -l .claude/skills/kustomize-cli/SKILL.md` < 500 (and token check < 5000)
- [ ] Every "see `references/…`" pointer in `SKILL.md` resolves to an existing sibling file (manual check)
- [ ] All five resource types each have a `SKILL.md` section linking to a reference file
- [ ] Patch decision framework, deprecation table, GitOps integration, and inline base/overlay/component tree all present
**Context cost:** M
**Depends on:** none

---

## Unverified Assumptions

- **Kustomize version baseline (OQ1).** The deprecation guidance (`vars`,
  `patchesStrategicMerge`) needs a target kustomize version/API level. No in-repo
  source exists; a human must set this baseline before the reference content can
  be stated as fact. Cannot be mapped to any concrete repo artifact (ref: Q8, Q13).
- **"Built using the skill builder" acceptance (OQ2).** Whether invoking
  `skill-creator` during authoring satisfies the criterion, or whether a recorded
  eval artifact is expected. The eval harness is an inert placeholder with no
  generic-skill grading support, so there is no in-repo path to produce such an
  artifact; this criterion is unverifiable in-repo (ref: Q2, Q12).
- **Example tree placement (OQ3).** Design recommends an inline `SKILL.md` prose
  tree (no `assets/` precedent exists), but the team may want runnable `assets/`
  manifests. If `assets/` is chosen, Slice 1 gains an unmodeled subdirectory and
  copy-pasteable manifest files (ref: Q7, Decision 2).
- **Net-new factual correctness.** All kustomize reference content is net-new with
  zero in-repo source; factual errors on patch semantics / deprecated fields could
  ship undetected. Mitigation is author-time sourcing, not a mappable code artifact
  (ref: Q13, Risk Register).
