# Structure Outline — Create a new agent skill: writing GitLab pipelines

**Design basis:** design.md @ 2026-06-04T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft

> This is a skill-authoring (Markdown) deliverable — no executable code, types, or
> function signatures. "Types" and "Contracts" below are expressed as the structural
> schemas these Markdown artifacts must satisfy (frontmatter shape, link convention),
> which are the real cross-file interfaces a reviewer can verify.

## New Types

- `SkillFrontmatter { name: string, description: string, allowed-tools: string (flat, comma-separated), command?: string, argument-hint?: string }`
  — YAML frontmatter at the top of `SKILL.md`. Flat `allowed-tools` (NOT the nested
  `claude: { tools: … }` agent shape). `name` MUST equal the directory name. Copy
  `qrspi-ticket/SKILL.md`'s frontmatter as the verbatim template (ref: design Decision 1, Risk "Wrong frontmatter shape").
- `ReferenceDoc { H1 heading, standalone Markdown body }` — one self-contained
  deep-dive file per concern under `references/`, addressable by the body's link contract (ref: design Decision 4, Q8).

## Modified Types

- none — this is a net-new directory; no existing file or type is modified (ref: design §Delta, "No code changes").

## Contracts

- **Directory/name contract:** directory `writing-gitlab-pipelines/` (kebab-case) ⇔ frontmatter `name: writing-gitlab-pipelines` (ref: Q6).
- **Reference-link contract:** `SKILL.md` body links each deep-dive via relative path `references/<file>.md`; every link MUST resolve to an existing file in the slice that ships it (ref: Q8).
- **Body-budget contract:** `SKILL.md` body ≤ 500 lines / ≤ ~5000 tokens; depth is delegated to `references/`, never inlined (ref: Q7, Decision 4).
- **Triggering contract:** `description` is trigger-oriented ("Use when… / Trigger on…") because the host triggers on `description`, not `command` (ref: Q2, Decision 2).
- **Concern-coverage contract:** every ticket concern (structure, rules, DRY, artifacts/cache, services, environments, review apps, multi-project, security, variables/secrets, performance, anti-patterns) maps to exactly one body section and/or one `references/` file (ref: design §Desired End State).

## Slice 1: SKILL.md skeleton — frontmatter, body index, opinionated body sections

**Goal:** A loadable, triggerable skill: the directory exists with a valid `SKILL.md`
(correct frontmatter shape, name = dir, trigger description) whose body holds all the
inline-content sections (Purpose/when-to-use, opinionated best-practice imperatives,
performance & optimization, anti-patterns → alternatives) and a "See references/" index
that links all six deep-dive files. Reference files are shipped as stubs (H1 + one-line
scope) so every body link resolves and the budget/structure can be verified before
content depth is invested. This is the end-to-end "skill triggers and loads with valid
structure" path.
**Files touched:**

- ✨ `.claude/skills/writing-gitlab-pipelines/SKILL.md` — frontmatter + full body (index + inline opinionated/performance/anti-pattern sections)
- ✨ `.claude/skills/writing-gitlab-pipelines/references/rules.md` — stub (H1 + scope line)
- ✨ `.claude/skills/writing-gitlab-pipelines/references/includes-extends.md` — stub
- ✨ `.claude/skills/writing-gitlab-pipelines/references/cache-artifacts.md` — stub
- ✨ `.claude/skills/writing-gitlab-pipelines/references/environments.md` — stub
- ✨ `.claude/skills/writing-gitlab-pipelines/references/security.md` — stub
- ✨ `.claude/skills/writing-gitlab-pipelines/references/architecture.md` — stub

**Verification:**
- [ ] Frontmatter parses as YAML; `name: writing-gitlab-pipelines` equals the directory name; `allowed-tools` is flat (no nested `claude.tools`); matches the `qrspi-ticket` frontmatter shape.
- [ ] `description` is trigger-oriented ("Use when…/Trigger on…").
- [ ] `wc -l SKILL.md` body ≤ 500 lines and estimated ≤ ~5000 tokens.
- [ ] Every `references/<file>.md` link in the body resolves to a file that exists in this slice (no broken links).
- [ ] Body contains the inline sections that do not live in references: Purpose & when-to-use, opinionated imperatives (rules-over-only/except, pinned images, explicit `expire_in`), Performance & optimization, Anti-patterns → alternatives.

**Context cost:** M
**Depends on:** none

## Slice 2: Reference content — fill the six deep-dive docs

**Goal:** Replace the six reference stubs with full, standalone deep-dive content so every
ticket concern has reviewable depth behind the SKILL.md index. The skill is now complete:
a reviewer can trace each concern from the body index into a substantive reference doc.
**Files touched:**

- ⚠️ `.claude/skills/writing-gitlab-pipelines/references/rules.md` — `rules:` syntax, `workflow:rules`, `rules:changes`, `$CI_PIPELINE_SOURCE`/`$CI_COMMIT_BRANCH`, explicit terminal `when`
- ⚠️ `.claude/skills/writing-gitlab-pipelines/references/includes-extends.md` — `include` (local/file/remote/component), `extends` deep-merge vs anchors, multi-level extends, `!reference`, CI/CD Catalog (GA 17.0)
- ⚠️ `.claude/skills/writing-gitlab-pipelines/references/cache-artifacts.md` — cache keys/`files`/`policy`/`$CI_COMMIT_REF_SLUG`; artifacts `expire_in`, `reports`, `when: on_failure`
- ⚠️ `.claude/skills/writing-gitlab-pipelines/references/environments.md` — static/dynamic environments, `on_stop`, `auto_stop_in`, review-app per-MR, scoped variables, deployment gates
- ⚠️ `.claude/skills/writing-gitlab-pipelines/references/security.md` — SAST/dependency/container/secret-detection templates, DAST vs review apps, `artifacts:reports:*`, scan execution policies
- ⚠️ `.claude/skills/writing-gitlab-pipelines/references/architecture.md` — worked examples: minimal build/test/deploy, mature lint/build/test/security/deploy/cleanup, parent-child + multi-project triggers

**Verification:**
- [ ] Each reference is a standalone H1 Markdown doc (no shared/relative state beyond the link target).
- [ ] Every ticket concern from design §Desired End State maps to a body section and/or a reference file with non-stub content.
- [ ] Version-gated features (e.g. CI/CD Catalog / components GA 17.0+) carry an inline version note (Risk "GitLab feature drift").
- [ ] Cross-check against acceptance criteria manually (no eval/validation harness applies to skill authoring — ref: Q10/Q11).

**Context cost:** M
**Depends on:** Slice 1

---

## Unverified Assumptions

- **OQ1 / Decision 2 (`command` field):** Whether `SKILL.md` should carry an explicit
  `command: /writing-gitlab-pipelines` (uniformity with the 10 in-repo skills) or remain
  auto-trigger-only. Unresolved design decision — Slice 1 frontmatter cannot be finalized
  until the author chooses. Default assumed: auto-trigger-only (design recommendation).
- **OQ3 / Decision 3 (`allowed-tools` set):** The exact tool list (read/edit-only vs.
  including `Bash` for local `.gitlab-ci.yml` lint) is author's choice. Slice 1 assumes
  the narrow `Read, Write, Edit, Bash` set pending confirmation.
- **OQ2 (skill-creator provenance):** The ticket's "built using the Anthropic skill builder"
  criterion cannot be satisfied or verified from repo files — `skill-creator` is
  environment-only (ref: Q4). Treated as a human/process step outside these slices; the
  structure conforms regardless of which tool scaffolds it. Cannot be mapped to a file.
- **OQ4 (GitLab target version):** Which SaaS/self-managed version(s) the reference
  material should assume for version-gated features. Affects Slice 2 content scoping; no
  concrete value available — assumed "note version gates inline, keep guidance
  principle-based" per the Risk Register mitigation.
- **Frontmatter field set is de-facto/unvalidated** (ref: Q3): `name`/`description`/
  `command`/`argument-hint`/`allowed-tools` are observed conventions with no
  registry/validator enforcing them; the contract above relies on copying an existing
  skill verbatim rather than a specified schema.
