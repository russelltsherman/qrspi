# Structure Outline — Create an agent skill for the Argo Workflows CLI

**Design basis:** design.md @ 2026-06-03T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft

> Note: This feature ships Markdown content (a self-contained skill + reference
> docs + catalog updates), not executable code. There are no runtime types or
> function signatures. The "New Types" and "Contracts" sections below therefore
> describe the structural artifacts and the invariants they must satisfy — these
> are the load-bearing interfaces the plan and implementation must honor.

## New Types

- `SkillDir = .claude/skills/<skill-name>/` — new self-contained skill directory.
  Working name `using-argo-workflows-cli` (OQ1 — see Unverified Assumptions).
- `SkillFrontmatter { name: string, description: string, command: string, argument-hint: string, allowed-tools: string }`
  — YAML block delimited by `---` at top of `SKILL.md`, mirroring the repo's
  conventional schema (ref: design §Current State, Q3).
- `ReferenceSet = SkillDir/references/{ submission-and-monitoring.md, debugging-and-lifecycle.md, authoring.md, cron-workflows.md }`
  — topic-scoped progressive-disclosure files (ref: design §Delta, Decision 3).
  Exact file boundaries are a design choice (OQ2).

## Modified Types

- `README.md` — add the new skill to the skills table and the directory tree
  (ref: design §Delta, Q6). Documentation convention, not functional.
- `.claude/CLAUDE.md` — add the new skill to the "Available skills" list
  (ref: design §Delta, Q6). Documentation convention, not functional.

## Contracts

These are the structural invariants every artifact in this feature must satisfy;
the implementation slice verifies each one.

- `triple-name-invariant`: `SkillDir` basename == `frontmatter.name` == `frontmatter.command` minus its leading `/` (ref: design §Current State, Q5).
- `frontmatter-schema`: `SKILL.md` frontmatter contains exactly the conventional keys (`name`, `description`, `command`, `argument-hint`, `allowed-tools`) delimited by `---` lines; must NOT use the agent frontmatter shape (`claude.tools`) (ref: Q3).
- `reference-link-contract`: the `SKILL.md` body points to each file in `ReferenceSet` by a relative path (`references/<file>.md`) at the relevant decision point; every such link must resolve to an existing file (ref: design §Current State, Q1/Q8; Decision 2).
- `body-size-budget`: `SKILL.md` body stays under ~500 lines / ~5000 tokens; all command-group detail lives in `ReferenceSet`, not the body (ref: design Decision 2, Q7/Q8).
- `description-trigger-contract`: `frontmatter.description` packs explicit "Use when…" conditions plus concrete argo trigger phrases so the harness matcher auto-invokes the skill (ref: design Risk register, Q12).
- `hard-stop-prereq`: `SKILL.md` body encodes an `argo`-binary availability check and a hard-stop-on-failure instruction (surface exact command + error, do not work around) (ref: design Decision 4, Q9).
- `coverage-contract`: `ReferenceSet` collectively documents all 15 command groups (submit, get, logs, list, delete, retry, resubmit, stop, terminate, suspend, resume, watch, lint, cron, template) plus DAG-vs-Steps, retry/backoff, debugging escalation, cron lifecycle, resource management, artifact config (ref: design §Desired End State).

## Slice 1: Author the argo-workflows-cli skill, references, and catalog entries

**Goal:** A discoverable, valid self-contained skill exists end-to-end — an agent
asked an argo CLI question can have the skill auto-invoke, read the lean body, be
routed to the correct `references/*.md`, and find the relevant command-group
guidance; the skill is registered in both human-facing catalogs. This is one
cohesive content-authoring unit: the body's routing pointers, the reference files
they point to, and the catalog entries all depend on the final skill name and the
reference-file boundaries, so they are authored in one sitting.

**Files touched:**

- ✨ `.claude/skills/using-argo-workflows-cli/SKILL.md` — lean body: frontmatter (per `frontmatter-schema`), one-paragraph purpose, `argo`-availability prerequisite check with hard-stop behavior (`hard-stop-prereq`), a short decision-routing section, and relative-path pointers into `references/` (`reference-link-contract`, `body-size-budget`).
- ✨ `.claude/skills/using-argo-workflows-cli/references/submission-and-monitoring.md` — submit/lint/dry-run, parameters, `--from`, monitoring (list/get/logs/watch), `@latest`, container selection.
- ✨ `.claude/skills/using-argo-workflows-cli/references/debugging-and-lifecycle.md` — debugging escalation path (argo get → argo logs → kubectl describe), common failure causes, retry/resubmit/stop/terminate/suspend/resume/delete lifecycle.
- ✨ `.claude/skills/using-argo-workflows-cli/references/authoring.md` — DAG vs Steps decision criteria, templates (WorkflowTemplate/ClusterWorkflowTemplate, templateRef), parameters/variables, artifacts (key parameterization, GC), retry strategy/error handling with exponential backoff, resource management (limits, nodeSelector, parallelism).
- ✨ `.claude/skills/using-argo-workflows-cli/references/cron-workflows.md` — cron lifecycle (create/list/suspend/resume/delete/lint), concurrency, timezone.
- ⚠️ `README.md` — add the new skill to the skills table and the directory tree.
- ⚠️ `.claude/CLAUDE.md` — add the new skill to the "Available skills" list.

**Verification:**

- [ ] Skill authored via the external `skill-creator` skill and its eval loop run where available (per user global memory "Use skill-creator for skills"; ref: design §Desired End State, Q2). If `skill-creator` is unavailable, STOP and escalate (Risk #1 / OQ4) — do not hand-author and claim otherwise.
- [ ] `triple-name-invariant` holds: dirname == frontmatter `name` == `command` minus `/`.
- [ ] `frontmatter-schema` holds: only the five conventional keys, `---`-delimited, no `claude.tools` shape.
- [ ] `reference-link-contract` holds: every `references/<file>.md` link in the body resolves to an existing file.
- [ ] `body-size-budget` holds: `SKILL.md` body under ~500 lines / ~5000 tokens.
- [ ] `coverage-contract` holds: all 15 command groups + DAG/Steps + retry/backoff + debugging escalation + cron lifecycle + resource mgmt + artifact config appear across `references/`.
- [ ] `hard-stop-prereq` present in body (availability check + surface-and-stop instruction).
- [ ] `README.md` skills table/tree and `.claude/CLAUDE.md` "Available skills" list both contain the new skill, name matching the directory exactly.

**Context cost:** L
**Depends on:** none

---

## Unverified Assumptions

- **skill-creator availability (Risk #1 / OQ4):** Both the ticket and user global
  memory mandate authoring via the external `skill-creator` skill, but the design
  states it is not present in this repo and its I/O contract is unknowable from the
  codebase (ref: Q2). If it is absent in this environment the slice's primary
  verification step cannot be satisfied — this must be resolved before
  implementation, not worked around.
- **Skill directory name (OQ1):** Structure assumes `using-argo-workflows-cli`
  (mirrors the `using-graphite-cli` convention). The name fixes the
  `triple-name-invariant` and the catalog entries, so a different choice changes
  the path of every new file. Confirm before planning.
- **Reference-file boundaries (OQ2):** Structure assumes the four-file split
  (submission/monitoring, debugging/lifecycle, authoring, cron) from the design's
  Delta. A different grouping changes file count and the body's routing pointers
  but not the slice shape.
- **Argo CLI version (OQ3):** No target `argo` version is fixed; reference content
  is version-aware guidance. Whether the prerequisite check should assert a minimum
  version is unresolved (ref: Risk register).
- **`allowed-tools` scoping (OQ5):** Whether to restrict the skill to
  `Bash(argo:*)` / `Bash(kubectl:*)` or leave Bash unscoped is undecided; affects
  one frontmatter field only.
- **No validator exists:** There is no lint/JSON-schema/loader enforcing the
  frontmatter schema or reference links (ref: Q11). All contract checks above are
  manual; there is no automated gate to lean on beyond the skill-creator eval loop.
