# Implementation Plan — Create a new agent skill called writing gitlab pipelines

**Structure basis:** structure.md @ 2026-05-31
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft
**Total steps:** 28

> Deliverable is a documentation skill (no executable code). "Tests" are structural
> validation commands: frontmatter parse, body line/token budget, reference-link
> integrity, and concern/criteria coverage.

## Slice 1: SKILL.md — frontmatter + concise dispatcher body

### Setup

1. ✨ Create directory `.claude/skills/writing-gitlab-pipelines/` — the skill root (Contract: dir basename == frontmatter `name`).
2. ✨ Create `.claude/skills/writing-gitlab-pipelines/SKILL.md` with YAML frontmatter only first: `name: writing-gitlab-pipelines`, `description:` (see step 3), `command: /writing-gitlab-pipelines`, `argument-hint: <path-to-.gitlab-ci.yml or pipeline goal>`, `allowed-tools: Read, Write, Edit, Glob, Grep` (Type: `Frontmatter`; structure.md Unverified Assumption on allowed-tools — flag for review).
3. ⚠️ Set the `description` value in SKILL.md frontmatter to a trigger blurb with explicit phrases.
   - **Current:** placeholder description
   - **After:** "Author, review, and refactor GitLab CI/CD pipelines (`.gitlab-ci.yml`). Use when writing or editing a `.gitlab-ci.yml`, designing pipeline stages/jobs, setting up rules, includes/extends, caching, artifacts, environments, review apps, multi-project pipelines, or security scanning. Trigger on: 'write a GitLab pipeline', 'edit .gitlab-ci.yml', 'GitLab CI', 'CI/CD pipeline for GitLab'." (Contract: `description` trigger phrases.)

### Core Logic (body sections)

4. ✨ Add body section "When to use / scope" — authoring `.gitlab-ci.yml`, not GitLab server/runner admin; SaaS and self-managed both (ticket Scope Guidance).
5. ✨ Add body section "Pipeline structure" — explicit stages in logical order; DAG `needs` (incl. `needs: []`); many small focused jobs; <10min target. Point to `references/architecture.md`.
6. ✨ Add body section "Rules over only/except" using the opinionated format (bold imperative + forbidden-list + why): always `rules:`, never `only/except`, terminal `when`, `workflow:rules`, `rules:changes`. Point to `references/rules.md` (Contract: opinionated-rule format).
7. ✨ Add body section "DRY: includes & extends" — `include` (local/file/remote/component), `extends` deep-merge over anchors, `!reference`, CI/CD Catalog (GA 17.0+). Point to `references/includes-extends.md`.
8. ✨ Add body section "Artifacts & cache" — artifacts for build outputs with explicit `expire_in`; `artifacts:reports`; cache for deps with `cache:key:files`; never rely on cache for correctness. Point to `references/caching.md` and `references/architecture.md`.
9. ✨ Add body section "Services" — pinned versions (never `:latest`), `alias`, warm-up. Point to `references/architecture.md`.
10. ✨ Add body section "Environments & review apps" — `environment:`, static vs dynamic, review apps, `on_stop`/`auto_stop_in`, deployment gates, `resource_group`. Point to `references/environments.md`.
11. ✨ Add body section "Multi-project & parent-child pipelines" — `trigger:include` vs `trigger:project`, `trigger:strategy: depend`, passing variables. Point to `references/architecture.md`.
12. ✨ Add body section "Security scanning" — SAST baseline template, dependency/container/secret/DAST, `artifacts:reports:*`, never skip on MR pipelines. Point to `references/security-scanning.md`.
13. ✨ Add body section "Variables & secrets" — never hardcode; masked+protected; external secret managers via `secrets:`; file-type vars. Point to `references/security-scanning.md` / `references/environments.md`.
14. ✨ Add body section "Performance & optimization" — <10min MR target; `interruptible`, `resource_group`, `retry` (max 2) with `when:`, `timeout:`; DAG/parallelization. Point to `references/architecture.md`.
15. ✨ Add body section "Common anti-patterns" — concise do/don't table (only/except, `:latest`, missing `expire_in`, hardcoded secrets, monolithic jobs, cache-for-correctness) each with the alternative (ticket: anti-patterns with alternatives).
16. ✨ Add body section "Reference material" — index listing each `references/<concern>.md` with one line on when to load it (Contract: body→reference link, no orphans).

### Tests (structural validation)

17. Run: `head -12 .claude/skills/writing-gitlab-pipelines/SKILL.md`
    - **Expected:** valid `---`-delimited YAML; `name: writing-gitlab-pipelines`; `description` present with trigger phrases.
18. Run: `basename "$(dirname .claude/skills/writing-gitlab-pipelines/SKILL.md)"` and compare to the `name` field.
    - **Expected:** both equal `writing-gitlab-pipelines`.
19. Run: `awk '/^---$/{c++; next} c>=2' .claude/skills/writing-gitlab-pipelines/SKILL.md | wc -l` (body line count).
    - **Expected:** < 500 lines; spot-check token budget < ~5000.

### Verify Slice 1

20. **Checkpoint:** `grep -c 'references/' .claude/skills/writing-gitlab-pipelines/SKILL.md`
    - [ ] Frontmatter parses; `name` == directory basename.
    - [ ] `description` contains explicit `.gitlab-ci.yml` / GitLab pipeline trigger phrases.
    - [ ] Body < 500 lines.
    - [ ] All ten concerns present (structure, rules, DRY, artifacts/cache, services, environments, review apps, multi-project, security, variables/secrets).
    - [ ] Body names all six `references/<concern>.md` files.
    - [ ] At least one opinionated rule uses bold-imperative + forbidden-list + rationale (rules over only/except; pinned images; explicit `expire_in`).

---

## Slice 2: references/ — six concern-scoped depth files

### Setup

21. ✨ Create `.claude/skills/writing-gitlab-pipelines/references/rules.md` — `rules:` syntax, `workflow:rules`, terminal `when: never`/`on_success`, `rules:changes`, `$CI_PIPELINE_SOURCE`/`$CI_COMMIT_BRANCH`; deprecation of `only/except` + migration; anti-pattern→alternative (Type: `ReferenceFile` concern=rules).
22. ✨ Create `.claude/skills/writing-gitlab-pipelines/references/includes-extends.md` — `include` local/file/remote/component; `extends` deep-merge vs YAML anchors; multi-level extends; `!reference`; CI/CD Catalog components (annotate GA 17.0+); anti-pattern→alternative.
23. ✨ Create `.claude/skills/writing-gitlab-pipelines/references/caching.md` — cache vs artifacts; `cache:key:files` with lock files; `cache:policy` pull/push; `$CI_COMMIT_REF_SLUG` scoping; single-populator rule; "never rely on cache for correctness"; anti-pattern→alternative.
24. ✨ Create `.claude/skills/writing-gitlab-pipelines/references/environments.md` — `environment:`; static vs dynamic; review apps `review/$CI_COMMIT_REF_SLUG`; `on_stop`/`auto_stop_in`; deployment gates (`when: manual`, `allow_failure: false`); `resource_group`; environment-scoped/protected variables; anti-pattern→alternative.
25. ✨ Create `.claude/skills/writing-gitlab-pipelines/references/security-scanning.md` — SAST/DAST/dependency/container/secret-detection templates; `artifacts:reports:*`; scan execution policies; DAST against review apps; never skip on MR pipelines; anti-pattern→alternative.
26. ✨ Create `.claude/skills/writing-gitlab-pipelines/references/architecture.md` — stages & DAG `needs`/`needs: []`; artifacts passing + `expire_in` + reports; services (pinned, `alias`); parent-child (`trigger:include`) & multi-project (`trigger:project`, `trigger:strategy: depend`); variables/secrets (Vault/masked+protected/file-type/`secrets:`); Docker/image pinning + multi-stage; performance (`interruptible`, `retry` max 2, `timeout`, <10min) with worked examples; SaaS vs self-managed notes; anti-pattern→alternative.

### Tests (structural validation)

27. Run: link-integrity + orphan check —
    `for f in $(grep -oE 'references/[a-z-]+\.md' .claude/skills/writing-gitlab-pipelines/SKILL.md | sort -u); do test -f ".claude/skills/writing-gitlab-pipelines/$f" && echo "OK $f" || echo "MISSING $f"; done` and `ls .claude/skills/writing-gitlab-pipelines/references/`.
    - **Expected:** every body-referenced file exists (no MISSING); every file on disk is referenced (no orphan).

### Verify Slice 2

28. **Checkpoint:** review each reference file against the topic checklist in structure.md Slice 2.
    - [ ] All six reference files exist at the exact paths the body names (no broken links, no orphans).
    - [ ] Each file covers its mandated topics with at least one anti-pattern→alternative.
    - [ ] Version-gated features annotated (CI/CD Catalog GA 17.0; SaaS vs self-managed where relevant).
    - [ ] Body + references cover all ten concerns and every acceptance criterion in the ticket.

---

## Rollback Notes

- Steps 1–2: purely additive new directory/files; rollback = delete `.claude/skills/writing-gitlab-pipelines/`. No existing files modified, so no destructive operations and no migrations.
- No config changes, no DB migrations, no edits to existing skills/agents/evals — the entire deliverable is new files under one new directory.
