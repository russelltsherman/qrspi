# Structure Outline — Create a new agent skill called writing gitlab pipelines

**Design basis:** design.md @ 2026-05-31
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

> This is a documentation/skill-authoring deliverable. There is no executable code,
> so "types" and "contracts" describe the skill's file/frontmatter structure and the
> body↔reference loading contract rather than program types.

## New Types

- `SkillDirectory { path: ".claude/skills/writing-gitlab-pipelines/", contains: [SKILL.md, references/] }`
- `Frontmatter { name: string (== dir name), description: string (trigger blurb + literal trigger phrases), command?: string, argument-hint?: string, allowed-tools?: string }` (ref: design.md §Delta; research Q3)
- `ReferenceFile { path: "references/<concern>.md", concern: one-of [rules, includes-extends, caching, environments, security-scanning, architecture], loadedBy: "explicit Read instruction in SKILL.md body at point of need" }` (ref: research Q7, Q10)

## Modified Types

- None. The skill is additive; no existing skill, agent, eval, or doc is modified (ref: design.md §Delta).

## Contracts

- `Frontmatter.name == SkillDirectory basename` — harness keys the skill by this (ref: research Q3, Q5).
- `Frontmatter.description` MUST contain explicit trigger phrases covering: authoring/editing/reviewing `.gitlab-ci.yml`, "GitLab pipeline", "GitLab CI/CD" (ref: design.md Risk "description does not auto-trigger"; research Q13).
- `Body → ReferenceFile` link: every `references/<concern>.md` named in the body must exist; every reference file must be named somewhere in the body (no orphans) (ref: research Q7).
- `Body length` contract: SKILL.md body < 500 lines / < 5000 tokens — author-enforced, no automated gate (ref: research Q6; design.md Risk "body exceeds budget").
- `Opinionated-rule format`: bold-imperative directive + explicit forbidden-list (anti-pattern) + short "why", mirroring `qrspi-work` hard-rule sections (ref: research Q8).
- `Concern coverage` contract: the body + references together MUST cover all ten ticket concerns — structure, rules, DRY (includes/extends), artifacts/cache, services, environments, review apps, multi-project pipelines, security scanning, variables/secrets.

## Slice 1: SKILL.md — frontmatter + concise dispatcher body

**Goal:** A loadable, auto-triggering skill whose `SKILL.md` states the opinionated GitLab CI principles concisely and maps every concern to a `references/<concern>.md` file. Independently verifiable before any reference depth is written: frontmatter parses, `name` matches the directory, trigger phrases are present, body is under 500 lines, and all ten concerns appear with a pointer to their reference file.
**Files touched:**

- ✨ `.claude/skills/writing-gitlab-pipelines/SKILL.md` — frontmatter (`name: writing-gitlab-pipelines`, `description` with trigger phrases, `command`, `argument-hint`, `allowed-tools`) + body. Body sections: when-to-use; pipeline structure & DAG `needs`; rules over only/except; DRY (includes/extends/catalog); artifacts & cache; services; environments & review apps; multi-project/parent-child; security scanning; variables/secrets; performance targets & optimization; anti-patterns summary; and a "Reference material" index naming each `references/<concern>.md`.
**Verification:**
- [ ] `head` of SKILL.md shows valid `---`-delimited YAML frontmatter with `name: writing-gitlab-pipelines`.
- [ ] Directory basename equals the `name` field.
- [ ] `description` contains explicit trigger phrases for `.gitlab-ci.yml` authoring/editing/review and "GitLab pipeline".
- [ ] Body line count < 500 (`wc -l`); spot-check token budget.
- [ ] All ten concerns present; each names its `references/<concern>.md` file.
- [ ] At least one opinionated rule uses the bold-imperative + forbidden-list + rationale format (rules over only/except; pinned images; explicit `expire_in`).
**Context cost:** M
**Depends on:** none

## Slice 2: references/ — six concern-scoped depth files

**Goal:** The six reference files the body points to, each delivering acceptance-criteria depth for its concern with opinionated rules and anti-pattern→alternative guidance. Independently verifiable: each file exists at the path the body references, and each covers its mandated topics. Final step of this slice is a structural review confirming no orphan references and full concern coverage.
**Files touched:**

- ✨ `.claude/skills/writing-gitlab-pipelines/references/rules.md` — `rules:` syntax, `workflow:rules`, explicit terminal `when`, `rules:changes`, `$CI_PIPELINE_SOURCE`/`$CI_COMMIT_BRANCH`; why `only/except` is deprecated and how to migrate.
- ✨ `.claude/skills/writing-gitlab-pipelines/references/includes-extends.md` — `include` (local/file/remote/component), `extends` deep-merge vs YAML anchors, multi-level extends, `!reference`, CI/CD Catalog components (GA 17.0+).
- ✨ `.claude/skills/writing-gitlab-pipelines/references/caching.md` — cache vs artifacts, `cache:key:files` with lock files, `cache:policy` pull/push, `$CI_COMMIT_REF_SLUG` scoping, single-populator rule, "never rely on cache for correctness".
- ✨ `.claude/skills/writing-gitlab-pipelines/references/environments.md` — `environment:`, static vs dynamic, review apps (`review/$CI_COMMIT_REF_SLUG`), `on_stop`/`auto_stop_in`, deployment gates (`when: manual`, `allow_failure: false`), `resource_group`, environment-scoped variables.
- ✨ `.claude/skills/writing-gitlab-pipelines/references/security-scanning.md` — SAST/DAST/dependency/container/secret-detection templates, `artifacts:reports:*`, scan execution policies, MR-pipeline scanning, DAST against review apps.
- ✨ `.claude/skills/writing-gitlab-pipelines/references/architecture.md` — stages & DAG `needs`/`needs: []`, artifacts passing + `expire_in` + `artifacts:reports`, services (pinned, `alias`), parent-child (`trigger:include`) & multi-project (`trigger:project`, `trigger:strategy: depend`), variables/secrets (Vault, masked+protected, file-type, `secrets:`), Docker/image pinning, performance (`interruptible`, `retry` max 2, `timeout`, <10min target) with worked examples.
**Verification:**
- [ ] All six files exist at the exact paths named in the SKILL.md body (no broken links).
- [ ] No orphan reference files (every file is named in the body).
- [ ] Each file covers its mandated topics (checklist above) including at least one anti-pattern→alternative per concern.
- [ ] Version-gated features annotated (e.g., "CI/CD Catalog GA in GitLab 17.0"; SaaS vs self-managed noted where relevant).
- [ ] Combined body + references cover all ten ticket concerns and all acceptance criteria.
**Context cost:** L
**Depends on:** Slice 1

---

## Unverified Assumptions

- OQ1 (design.md): "Built using the Anthropic skill builder skill" — the skill-creator is global and absent from the repo (research Q4). Assumption: conforming to the standard `.claude/skills/<name>/` layout and frontmatter satisfies the criterion; the builder is not a runtime dependency. Needs human confirmation.
- OQ2 (design.md): Whether this skill must ship eval coverage. Assumption: no — the eval harness is qrspi-phase-specific (research Q11) and human PR review is the quality gate. Needs human confirmation.
- OQ3 (design.md): Final `name`/`command` values. Assumption: `name: writing-gitlab-pipelines`, no `qrspi-` prefix (it is not a qrspi workflow skill). Verb-first kebab-case per research Q5.
- The exact `allowed-tools` value for a static guidance skill is unverified — guidance skills primarily need Read (to load their own references) and possibly Write/Edit (to author `.gitlab-ci.yml` for the user). No in-repo guidance-skill precedent exists to copy; this is an author judgment to confirm in review.
