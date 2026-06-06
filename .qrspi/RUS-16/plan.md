# Implementation Plan — Create a new agent skill for the kustomize CLI

**Structure basis:** structure.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total steps:** 14

> This ticket authors a documentation skill, not executable code. "Create" steps
> name a Markdown file and the convention/content it must satisfy (frontmatter
> schema, progressive-disclosure links, guidance shapes). There are no runtime
> modules to modify; the verify checkpoint runs shell checks (`wc -l`, frontmatter
> grep, link-resolution) rather than a test runner.

## Slice 1: Author the kustomize-cli skill (SKILL.md + references)

### Setup

1. ✨ Author by invoking the `skill-creator` skill — run `skill-creator` to scaffold/author the `kustomize-cli` skill so the "Built using the Anthropic skill builder" acceptance criterion is satisfied; note the invocation in the PR (ref: structure Verification, Q2; design Risk Register). All file-creation steps below are performed within this authoring pass.
2. ✨ Create `.claude/skills/kustomize-cli/references/` directory — the progressive-disclosure subdirectory required by the acceptance criteria, mirroring the lone `qrspi-work/references/` precedent (ref: design §Current State, Q3).

### Core Logic

3. ✨ Create `.claude/skills/kustomize-cli/SKILL.md` frontmatter — the repo's five-field YAML block delimited by `---` lines, satisfying `SkillFrontmatter` and the `frontmatter` contract: `name: kustomize-cli` (== directory name), `description` carrying `qrspi-work`-style "Use when…/Trigger on…" auto-invocation text with literal examples, `command: /kustomize-cli` (== `/<name>`), `argument-hint`, `allowed-tools` (ref: structure New Types + Contracts, Q4, Q6).
4. ✨ Add `.claude/skills/kustomize-cli/SKILL.md` body — scope guidance; base/overlay/components conventions; inline prose-rendered base/overlay/component example directory tree (Decision 2 Option A, no `assets/`); one short section per resource type (patches, generators, transformers, components, replacements), each with a "see `references/…`" pointer satisfying the `referenceLink` contract; the deprecation table (`vars`→`replacements`, `patchesStrategicMerge`/`patchesJson6902`→`patches:`); and a `kubectl apply -k` + GitOps (`kustomize build | kubectl apply -f -`, Argo CD / Flux) integration section. Keep body lean per `sizeBudget` (< 500 lines / < 5000 tokens) by offloading detail into references (ref: structure Slice 1, Q1/Q4/Q6/Q7/Q13, Decisions 1–3).
5. ✨ Create `.claude/skills/kustomize-cli/references/patch-selection.md` — strategic-merge vs JSON 6902 decision framework satisfying `deprecationGuidance`: additive→strategic; remove-field / replace-array-item-by-index→JSON-6902; plus "prefer `patches:`, recognize legacy `patchesStrategicMerge`/`patchesJson6902`" deprecation (ref: structure Slice 1, Q8, Q11).
6. ✨ Create `.claude/skills/kustomize-cli/references/generators.md` — `configMapGenerator`/`secretGenerator` patterns, `behavior:`/`generatorOptions`, and `.env` + committed `.env.example` secret handling per the `secretExample` contract (mirrors `.qrspi/config.json` ↔ `.qrspi/config.example.json`; no literal secrets) (ref: structure Slice 1, Q9, Decision 4).
7. ✨ Create `.claude/skills/kustomize-cli/references/transformers.md` — labels/annotations/namespace/images/namePrefix/replacements usage matrix, the `commonLabels`-breaks-selectors caution, and "prefer `replacements`, recognize legacy `vars`" deprecation per `deprecationGuidance` (ref: structure Slice 1, Q8, Q10).
8. ✨ Create `.claude/skills/kustomize-cli/references/ci-validation.md` — `kustomize build` per overlay, `kubeconform`/`conftest`/OPA validation, and the repo's `failureReporting` doctrine (print the exact failing command + full stderr verbatim, then stop) (ref: structure Slice 1, Q13, Q14).

### Tests

> No code under test; "tests" here are the manual conformance checks the acceptance
> criteria demand. They are exercised by the Verify checkpoint commands below.

9. Confirm frontmatter completeness — `SKILL.md` has all five fields and `name`/`command` equal `kustomize-cli` / `/kustomize-cli`.
   - **Expected:** all five keys present; `name: kustomize-cli`; `command: /kustomize-cli`.
10. Confirm size budget — body kept under the line/token budget.
    - **Expected:** `wc -l` < 500 and an approximate token check < 5000.
11. Confirm reference-link resolution — every "see `references/…`" pointer in `SKILL.md` names an existing sibling file (the `referenceLink` contract is convention-only / unvalidated at runtime, so check by hand).
    - **Expected:** each pointer resolves to a file present in `references/`.

### Verify Slice 1

12. **Checkpoint:** frontmatter + structure
    ```sh
    sed -n '1,12p' .claude/skills/kustomize-cli/SKILL.md
    ls .claude/skills/kustomize-cli/references/
    ```
    - [ ] Authored by invoking `skill-creator` (noted in PR)
    - [ ] Frontmatter has all five fields; `name` == directory name; `command` == `/kustomize-cli`
    - [ ] Four reference files present: `patch-selection.md`, `generators.md`, `transformers.md`, `ci-validation.md`
13. **Checkpoint:** size budget
    ```sh
    wc -l .claude/skills/kustomize-cli/SKILL.md
    ```
    - [ ] `SKILL.md` < 500 lines (and token check < 5000)
14. **Checkpoint:** link resolution + content coverage
    ```sh
    grep -oE 'references/[A-Za-z0-9_-]+\.md' .claude/skills/kustomize-cli/SKILL.md \
      | sort -u \
      | while read -r p; do test -f ".claude/skills/kustomize-cli/$p" \
          && echo "OK  $p" || echo "MISSING  $p"; done
    ```
    - [ ] Every `references/…` pointer resolves (no `MISSING` lines)
    - [ ] All five resource types (patches, generators, transformers, components, replacements) each have a `SKILL.md` section linking to a reference file
    - [ ] Patch decision framework, deprecation table, GitOps integration, and inline base/overlay/component tree all present

---

## Rollback Notes

- No DB migrations, config changes, or destructive operations in this slice.
- Steps 2–8 create only new files under `.claude/skills/kustomize-cli/`. To roll back, delete the directory: `rm -rf .claude/skills/kustomize-cli/`. No existing files are modified, so removal is fully non-destructive to the rest of the repo.
