# Work Tree — Create a new agent skill for the kustomize CLI

**Plan basis:** plan.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total sessions:** 1
**Critical path:** T1 → T2 → T3 → T4 → T5 → T11 → T14 (7 tasks)

> Single-slice plan (one `skill-creator` authoring pass). All file creation,
> conformance checks, and verify checkpoints fit in one session well under the
> 40% context budget — no session boundary is required. The four reference files
> (T5–T8) are independent of each other and may be authored in any order once the
> SKILL.md body (T4) is in place.

## Session 1 — Author the kustomize-cli skill

**Load:** plan.md §Slice 1, structure.md §New Types, structure.md §Contracts,
        structure.md §Verification
**Estimated context:** ~20% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1  | Invoke `skill-creator` to scaffold/author the `kustomize-cli` skill (wraps all file creation; note invocation in PR) | — | §1 | S | pending |
| T2  | Create `.claude/skills/kustomize-cli/references/` directory | T1 | §2 | S | pending |
| T3  | Author `SKILL.md` five-field frontmatter (`name`==dir, `command: /kustomize-cli`, auto-invoke `description`, `argument-hint`, `allowed-tools`) | T2 | §3 | S | pending |
| T4  | Add `SKILL.md` body: scope, base/overlay/component tree, per-resource sections w/ reference pointers, deprecation table, `kubectl apply -k`/GitOps section (keep < 500 lines) | T3 | §4 | M | pending |
| T5  | Create `references/patch-selection.md` (strategic-merge vs JSON-6902 framework + `patches:` deprecation) | T4 | §5 | M | pending |
| T6  | Create `references/generators.md` (`configMapGenerator`/`secretGenerator`, `behavior:`, `.env`/`.env.example` handling) | T4 | §6 | M | pending |
| T7  | Create `references/transformers.md` (labels/annotations/namespace/images/namePrefix/replacements matrix, `commonLabels` caution, `vars`→`replacements`) | T4 | §7 | M | pending |
| T8  | Create `references/ci-validation.md` (`kustomize build` per overlay, kubeconform/conftest/OPA, verbatim failure reporting) | T4 | §8 | M | pending |
| T9  | Confirm frontmatter completeness (all five fields; `name`/`command` correct) | T3 | §9 | S | pending |
| T10 | Confirm size budget (`wc -l` < 500, token check < 5000) | T4 | §10 | S | pending |
| T11 | Confirm reference-link resolution (every `references/…` pointer names an existing sibling) | T5, T6, T7, T8 | §11 | S | pending |
| T12 | **Checkpoint:** frontmatter + structure (sed frontmatter, `ls references/`, four files present) | T8, T9 | §12 | S | pending |
| T13 | **Checkpoint:** size budget (`wc -l SKILL.md`) | T10 | §13 | S | pending |
| T14 | **Verify Slice 1:** link resolution + content coverage (no MISSING pointers; all five resource types, patch framework, deprecation table, GitOps, inline tree present) | T11, T12, T13 | §14 | S | pending |
