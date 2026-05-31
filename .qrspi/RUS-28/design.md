# Design — Create a new agent skill called writing gitlab pipelines

**Ticket:** RUS-28
**Research basis:** research.md @ 2026-05-31
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## Current State

The repository hosts ten project-local skills, all under `.claude/skills/<skill-name>/SKILL.md`, and all belonging to the `qrspi-*` workflow family (ref: Q2). Two body archetypes exist: thin wrappers that delegate to a companion agent in `.claude/agents/`, and a self-contained procedural skill (`qrspi-work`) whose long body defers discrete sub-topics to `references/` files (ref: Q1). The only `references/` directory in the repo is `qrspi-work/references/`, containing a single concern-scoped file `review-cascade.md`; no skill uses `scripts/` or `assets/` (ref: Q2, Q7). SKILL.md frontmatter consistently carries `name` (equal to the directory name), `description` (a "what + when to use" trigger blurb, sometimes with literal trigger phrases), `command`, `argument-hint`, and `allowed-tools` (ref: Q3, Q5). Reference files are loaded lazily: the body names each one by relative path at its point of need, with no central manifest (ref: Q7, Q10).

No automated gate enforces SKILL.md body length, frontmatter parseability, or description-triggering accuracy; the eval harness in `evals/` + `scripts/` evaluates only the `qrspi-*` phase agents against fixture tickets and asserts on generated artifacts, not on arbitrary new skills (ref: Q6, Q11, Q12, Q13). The "Anthropic skill builder" (skill-creator) referenced by the ticket is a global skill not present in this repo, so its inputs, output structure, and eval loop are unobservable from within scope (ref: Q4). The repo's only precedent for opinionated "prefer X / forbid Y" guidance is the bold-imperative + forbidden-list + short-rationale style in `qrspi-work` (e.g., the staging and hard-stop sections); there is no in-repo precedent for version-gated or SaaS-vs-self-managed conditional notes (ref: Q8, Q9).

## Desired End State

A new standalone guidance skill exists at `.claude/skills/writing-gitlab-pipelines/` that an agent auto-invokes when authoring or reviewing `.gitlab-ci.yml` files, mapping each acceptance criterion to concrete behavior:

- **agentskills.io structure + valid SKILL.md frontmatter** → directory `writing-gitlab-pipelines/` with `SKILL.md` carrying `name`, `description`, plus the in-repo frontmatter fields, following the standard layout (ref: Q2, Q3).
- **Built using the skill builder** → the skill is authored following the skill-creator pattern where available; because that skill is out of project scope (ref: Q4), the deliverable conforms to the observable `.claude/skills/<name>/` standard rather than depending on the global builder at runtime.
- **Body under 500 lines / 5000 tokens** → the SKILL.md body stays a concise dispatcher of principles, deferring depth to `references/` (ref: Q1, Q10); this is an author-enforced target since nothing validates it in-repo (ref: Q6).
- **Detailed `references/` covering rules syntax, includes/extends, caching, environments, security scanning, pipeline architecture** → one concern-scoped reference file per topic, named after its concern and named in the body at point of use (ref: Q7, Q10).
- **Covers all major pipeline concerns** (structure, rules, DRY, artifacts/cache, services, environments, review apps, multi-project, security, variables/secrets) → each concern gets a short body section pointing to its reference file.
- **Encodes opinionated best practices** (rules over only/except, pinned images, explicit `expire_in`) → expressed in the in-repo bold-imperative + forbidden-list + rationale format (ref: Q8).
- **Pipeline performance targets + optimization** → a dedicated body section and reference coverage (interruptible, resource_group, retry, timeout, DAG/needs).
- **Anti-patterns with clear alternatives** → a do/don't presentation per concern, following the forbidden-list precedent (ref: Q8).

## Delta

New files (all under `.claude/skills/writing-gitlab-pipelines/`):

- `SKILL.md` — frontmatter + concise body: trigger guidance, the opinionated principles, a concern→reference map, and a performance/anti-pattern summary. Under 500 lines.
- `references/rules.md` — `rules:` syntax, `workflow:rules`, `rules:changes`, predefined variables, and why `only/except` is deprecated.
- `references/includes-extends.md` — `include` (local/file/remote/component), `extends` deep-merge, multi-level extends, `!reference`, CI/CD Catalog components.
- `references/caching.md` — cache vs artifacts, `cache:key:files`, pull/push policies, key scoping, single-populator rule.
- `references/environments.md` — environments, static vs dynamic, review apps, `on_stop`/`auto_stop_in`, deployment gates, environment-scoped variables.
- `references/security-scanning.md` — SAST/DAST/dependency/container/secret-detection templates, `artifacts:reports:*`, scan execution policies, MR-pipeline scanning.
- `references/architecture.md` — stages/DAG `needs`, artifacts passing, services, parent-child and multi-project pipelines, variables/secrets, Docker/image pinning, performance worked examples.

No modifications to existing skills, agents, eval harness, or docs are required; the new skill is additive and not wired into the qrspi eval suite (ref: Q11). `.claude/agents/` gets no companion agent — this is a self-contained guidance skill (archetype 2), not a workflow wrapper (ref: Q1).

## Pattern Decisions

### Decision 1: Body archetype

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Self-contained guidance body + `references/` (mirror `qrspi-work`) | Matches the only in-repo multi-reference precedent; no agent needed; loads depth lazily | Author must self-police the 500-line budget |
| B | Thin wrapper + companion `.claude/agents/` agent | Matches the `qrspi-*` majority | Wrong fit — wrappers exist to fetch a ticket and run a workflow phase; this skill is static guidance, not a phased workflow |

**Recommendation:** Option A
**Rationale:** The skill is reference guidance, not a Linear-driven workflow phase. The `qrspi-work` self-contained + `references/` shape (ref: Q1, Q10) is the precise in-repo template; wrappers (ref: Q1) exist only to delegate workflow phases to agents, which does not apply here.
**NEW PATTERN?** No — reuses the `qrspi-work` self-contained + references archetype.

### Decision 2: Reference file granularity

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | One reference file per cohesive concern (6 files) | Matches in-repo "one file per concern" precedent; agent loads only the relevant topic | More files to keep coherent |
| B | One large `references/gitlab-ci.md` | Fewer files | Defeats lazy loading; a single large file is harder to load selectively and contradicts the per-concern precedent |

**Recommendation:** Option A
**Rationale:** `qrspi-work` keeps one concern per reference file (`review-cascade.md`) named for its concern and pulled in at point of need (ref: Q7, Q10). The ticket's six reference topics map one-to-one onto this convention.
**NEW PATTERN?** No.

### Decision 3: Encoding opinionated rules and anti-patterns

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Bold-imperative directive + explicit forbidden-list + short "why" (mirror `qrspi-work` hard-rules) | Matches the only in-repo opinionated-guidance precedent (ref: Q8); unambiguous for agents | Verbose if overused |
| B | Soft prose recommendations | Compact | Weak signal; the ticket explicitly demands opinionated, anti-pattern-with-alternative guidance |

**Recommendation:** Option A
**Rationale:** The ticket requires opinionated rules (rules over only/except, pinned images, explicit `expire_in`) and anti-patterns paired with alternatives. The `qrspi-work` bold-imperative + forbidden-list + rationale format (ref: Q8) is the established in-repo way to state non-negotiable guidance.
**NEW PATTERN?** No (reuses existing rule-statement format) — but version-gating annotations (SaaS vs self-managed, "GA since 17.0") have no in-repo precedent (ref: Q9) and will be introduced as inline applicability notes; flag as a minor NEW PATTERN for that sub-aspect.

### Decision 4: Eval / validation coverage

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Ship the skill without wiring it into `evals/` | Matches reality — the harness is qrspi-phase-specific and has no generic new-skill case (ref: Q11) | No automated regression check for this skill |
| B | Extend the eval harness to cover the new skill | Adds a safety net | Out of ticket scope; the harness is not designed for non-qrspi skills and would need new case/fixture/scoring machinery |

**Recommendation:** Option A
**Rationale:** The eval harness asserts on qrspi phase-agent artifacts, not arbitrary skills (ref: Q11, Q12, Q13). Wiring this skill in is a separate effort beyond the ticket. Quality is enforced by adherence to the acceptance criteria and human review of the planning PR.
**NEW PATTERN?** No.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| SKILL.md body exceeds the 500-line/5000-token budget as concerns accumulate | med | med | Keep the body a dispatcher; push all depth into `references/`; check line count before commit (ref: Q6 — no automated gate, so manual) |
| Skill builder (skill-creator) unavailable, so "built using the skill builder" criterion is only partially satisfiable | med | low | Conform to the observable `.claude/skills/<name>/` standard layout and frontmatter schema (ref: Q3); note in PR that the builder is global/out-of-scope (ref: Q4) |
| GitLab CI guidance drifts from current product reality (version-gated features) | med | med | Mark version-gated features inline ("GA since 17.0", SaaS vs self-managed) per the ticket; keep claims to stable, documented keywords (ref: Q9) |
| `description` does not auto-trigger on `.gitlab-ci.yml` authoring prompts | med | med | Write explicit trigger phrases into `description` per the in-repo precedent (ref: Q13); cover "write/edit/review .gitlab-ci.yml", "GitLab pipeline", "CI/CD" |
| Reference files duplicate or contradict the body | low | low | Body states principles once and links out; reference files hold depth only, named at point of use (ref: Q7) |

## Open Questions

- OQ1: Does "built using the Anthropic skill builder skill" require the builder to actually run (it is a global skill, absent from this repo — ref: Q4), or is conformance to the standard skill layout sufficient for acceptance?
- OQ2: Should this skill ship with eval coverage despite the harness being qrspi-phase-specific (ref: Q11), or is human PR review the accepted quality gate for non-qrspi skills?
- OQ3: What `name`/`command` should the skill use — `writing-gitlab-pipelines` (matching the ticket title and the verb-first in-repo convention, ref: Q5) — and should it carry the `qrspi-` family prefix (it does not belong to that workflow, so likely no)?
