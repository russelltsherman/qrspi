# Design — Create a new agent skill: writing GitLab pipelines

**Ticket:** RUS-28
**Research basis:** research.md @ 2026-06-04T00:00:00Z
**Generated:** 2026-06-04T00:00:00Z
**Status:** draft

## Current State

Agent skills in this repo live at `.claude/skills/<skill-name>/SKILL.md`; there are 10 skill directories, each with exactly one `SKILL.md`, and only `qrspi-work/` carries a subdirectory (`references/review-cascade.md`) (ref: Q1). No skill in the repo has a `scripts/` or `assets/` subdirectory (ref: Q1, Q9). A skill is, by convention, a directory whose name equals its frontmatter `name`, containing a `SKILL.md`; subdirectories are optional and referenced by relative path from the body (ref: Q1).

There is no skill-loading or skill-registration module inside the repo — discovery and loading are performed by the host Claude Code harness, not by repo code (ref: Q1, Q2). Descriptions are authored in trigger-oriented language ("Use when… / Trigger on…"); the harness reads the `description` to decide triggering and loads the body on invocation (ref: Q2).

The observed (de-facto, unvalidated) SKILL.md frontmatter fields are `name`, `description`, `command`, `argument-hint`, and `allowed-tools`; `name` and `description` are universal across all 10 skills (ref: Q3). Skill frontmatter uses a flat `allowed-tools`, whereas the separate agent definitions under `.claude/agents/` use a nested `claude: { tools: … }` block — a known footgun if mixed (ref: Q3, Inconsistencies).

The QRSPI workflow phases use a two-file split (thin `SKILL.md` wrapper that spawns `subagent_type: <name>` plus a heavyweight `.claude/agents/<name>.md`), but a self-contained, non-delegating skill is equally valid — `qrspi-ticket/SKILL.md` (119 lines) holds its full prompt inline with no agent companion (ref: Q5). A purely instructional skill needs only a `SKILL.md` (ref: Q5).

Skill directory naming is kebab-case, prefixed `qrspi-`, with directory name equal to frontmatter `name` — convention only, with no registry or validator enforcing it (ref: Q6). There is no tooling that enforces SKILL.md size limits; the convention is already violated in-repo (`qrspi-work/SKILL.md` is 565 lines, over the 500-line guideline) (ref: Q7). The only `references/` precedent is `qrspi-work/references/review-cascade.md`: a standalone H1 Markdown doc referenced by relative path `references/<file>.md` from the body (ref: Q8).

The Anthropic "skill builder" / `skill-creator` skill named in the ticket is NOT checked into the repo — it exists only as an environment-provided skill, so its inputs and invocation cannot be observed from repo files (ref: Q4). The `scripts/run_eval.py` + `evals/` harness is a non-functional placeholder (stubbed execution) and targets workflow-phase artifacts, not skill-definition authoring — so this skill cannot be eval-tested by repo tooling (ref: Q10, Q11). There is no in-repo logging or hook for skill-invocation observability; any such signal is host-side (ref: Q12).

## Desired End State

A new self-contained skill at `.claude/skills/writing-gitlab-pipelines/` that guides agents authoring `.gitlab-ci.yml` pipelines, mapping each acceptance criterion to concrete behavior:

- **agentskills.io directory structure + valid frontmatter** → directory `writing-gitlab-pipelines/` (kebab-case, matching observed convention, ref: Q6) containing `SKILL.md` with frontmatter `name: writing-gitlab-pipelines` and a trigger-oriented `description` (ref: Q3, Q2). Because this skill is instructional and does not fan out to a sub-agent, it mirrors the self-contained `qrspi-ticket` shape and needs no `.claude/agents/` companion (ref: Q5).
- **Built using the Anthropic skill builder skill** → the human author invokes the environment-provided `skill-creator` skill to scaffold/validate (ref: Q4); this Design phase cannot itself run it (out of repo scope) — captured as an Open Question and a process step, not an artifact this phase produces.
- **SKILL.md body under 500 lines / 5000 tokens** → the body stays a concise navigational index; depth lives in `references/`. The limit is convention-only here and already exceeded by one skill, so the design treats it as a firm target backed by structure, not tooling (ref: Q7).
- **Detailed reference material in `references/`** → one Markdown file per concern (rules, includes/extends, caching/artifacts, environments/review-apps, security scanning, pipeline architecture), each a standalone H1 doc referenced by relative path `references/<file>.md`, mirroring the lone `qrspi-work/references/` precedent (ref: Q8).
- **Covers all major pipeline concerns** → every concern from the ticket (structure, rules, DRY, artifacts/cache, services, environments, review apps, multi-project, security, variables/secrets) maps to either a body section or a `references/` file.
- **Encodes opinionated best practices** → body states the rules-over-only/except, pinned-images, explicit-`expire_in` defaults as imperatives.
- **Performance targets + optimization** → a body section on the sub-10-minute target, DAG/`needs`, `interruptible`, `resource_group`, `retry`, `timeout`.
- **Anti-patterns with alternatives** → a dedicated body section pairing each anti-pattern with its preferred alternative.

## Delta

New directory `.claude/skills/writing-gitlab-pipelines/` containing:

- `SKILL.md` — frontmatter (`name`, `description`; optionally `command`/`argument-hint` if a slash invocation is desired — see Decision 2; `allowed-tools` scoped narrowly per Decision 3). Body sections: Purpose & when-to-use; Pipeline structure & stages; Rules (over only/except); DRY (includes/extends/CI-CD Catalog); Artifacts & caching; Services; Environments, deployments & review apps; Multi-project/parent-child; Security scanning; Variables & secrets; Docker & images; Performance & optimization; Anti-patterns → alternatives; and a "See references/" index linking each deep-dive file.
- `references/rules.md` — `rules:` syntax, `workflow:rules`, `rules:changes`, `$CI_PIPELINE_SOURCE`/`$CI_COMMIT_BRANCH`, explicit terminal `when`.
- `references/includes-extends.md` — `include` (local/file/remote/component), `extends` deep-merge vs YAML anchors, multi-level extends, `!reference`, CI/CD Catalog (GA 17.0).
- `references/cache-artifacts.md` — cache keys/`files`/`policy`/`$CI_COMMIT_REF_SLUG`; artifacts `expire_in`, `reports`, `when: on_failure`.
- `references/environments.md` — static/dynamic environments, `on_stop`, `auto_stop_in`, review-app per-MR pattern, scoped variables, deployment gates.
- `references/security.md` — SAST/dependency/container/secret-detection templates, DAST against review apps, `artifacts:reports:*`, scan execution policies.
- `references/architecture.md` — worked pipeline-architecture examples: minimal `build/test/deploy`, mature `lint/build/test/security/deploy/cleanup`, parent-child and multi-project trigger patterns.

No code changes, no Python, no eval-suite changes (the harness does not target skill authoring, ref: Q10). No `.claude/agents/` file (self-contained skill, ref: Q5).

## Pattern Decisions

### Decision 1: Self-contained skill vs. two-file wrapper+agent split

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Self-contained `SKILL.md` only (mirror `qrspi-ticket`) | Matches purely-instructional intent; no orchestration; one fewer file shape to keep consistent (ref: Q5) | Larger body pressure (mitigated by `references/`) |
| B | Thin wrapper `SKILL.md` + `.claude/agents/writing-gitlab-pipelines.md` | Matches the dominant QRSPI phase pattern (ref: Q5) | The agent split exists for sub-agent fan-out this skill never needs; adds a second frontmatter shape (`claude.tools`) to get right (ref: Q3) |

**Recommendation:** Option A
**Rationale:** Research is explicit that the agent split is a QRSPI orchestration convention, not a requirement, and that a purely instructional skill needs only a `SKILL.md` — `qrspi-ticket` is the in-repo precedent for exactly this shape (ref: Q5).
**NEW PATTERN?** No — directly mirrors `qrspi-ticket` (ref: Q5).

### Decision 2: Slash command vs. auto-trigger-only invocation

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Auto-trigger only — `name` + trigger-oriented `description`, no `command`/`argument-hint` | This skill is contextual guidance, not an argument-taking action; matches the "description as trigger" pattern (ref: Q2) | Diverges from the 10 in-repo skills, which all carry `command` (ref: Q3) |
| B | Add `command: /writing-gitlab-pipelines` (+ no meaningful args) | Consistent with every existing skill carrying a `command` (ref: Q3) | Implies an explicit slash invocation for what is really passive guidance; `argument-hint` would be empty/forced |

**Recommendation:** Option A, with Option B as a low-cost addition if the author wants an explicit invocation.
**Rationale:** Triggering is driven by the `description` field (ref: Q2); a guidance skill has no argument to parse. The all-`command` uniformity (ref: Q3) is observed but unenforced (ref: Q6), so omitting it is acceptable. Defer the final choice to the author (Open Question).
**NEW PATTERN?** Yes (mild) — no existing skill omits `command`. Justified because every existing skill is an action/wrapper, whereas this is passive guidance; the host triggers on `description` regardless (ref: Q2).

### Decision 3: `allowed-tools` scope

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Narrow set (e.g. `Read, Write, Edit, Bash`) sufficient to author/edit `.gitlab-ci.yml` | Follows the firewall pattern of scoping tools to need (ref: Discovered Patterns) | Author must enumerate intended tools |
| B | Omit `allowed-tools` entirely | Less to specify | Loses the explicit-capability convention every in-repo skill follows (ref: Q3) |

**Recommendation:** Option A
**Rationale:** Every in-repo skill declares `allowed-tools`, and the repo's firewall convention scopes capability to need (ref: Q3, Discovered Patterns). A pipeline-authoring skill needs file read/write/edit and possibly shell to validate YAML.
**NEW PATTERN?** No — standard `allowed-tools` usage (ref: Q3).

### Decision 4: Body-size budget — index-in-body, depth-in-references

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Keep body a concise index; push all depth into `references/` files | Honors the <500-line / <5000-token criterion structurally; mirrors the one `references/` precedent (ref: Q8) | Readers must follow links for detail |
| B | Inline all conventions in one large body | Single-file convenience | Repeats the `qrspi-work` 565-line overrun; no tooling stops it (ref: Q7) |

**Recommendation:** Option A
**Rationale:** The size limit is convention-only and already breached once (ref: Q7); structure, not tooling, is the only thing that keeps the body small. The `references/`-splitting precedent gives a proven shape (ref: Q8).
**NEW PATTERN?** No — extends the single `qrspi-work/references/` precedent to multiple files (ref: Q8).

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Body exceeds 500 lines / 5000 tokens — no tooling enforces it (ref: Q7) | med | med | Index-in-body, depth-in-`references/` (Decision 4); author manually checks `wc -l` and token estimate before submit |
| Wrong frontmatter shape — skill `allowed-tools` (flat) confused with agent `claude.tools` (nested) (ref: Q3, Inconsistencies) | med | med | Copy an existing self-contained skill's frontmatter (`qrspi-ticket`) verbatim as the template; no agent file is created (Decision 1) |
| GitLab feature drift — version-gated features (CI/CD Catalog GA 17.0, components) become stale | med | low | Note version gates inline per the ticket's scope guidance; keep guidance principle-based, not release-pinned |
| `skill-creator` is environment-only, not in-repo — "built using skill builder" criterion can't be satisfied or verified from repo (ref: Q4) | high | low | Treat skill-creator invocation as a human/process step outside this Design phase; record as Open Question; final structure still conforms regardless of which tool scaffolds it |
| No eval/validation harness applies to skill authoring (ref: Q10, Q11) | high | low | Rely on manual review of the SKILL.md + references against acceptance criteria; do not promise automated eval coverage |

## Open Questions

- OQ1: Should this skill carry an explicit `command: /writing-gitlab-pipelines` for uniformity with the other 10 skills, or remain auto-trigger-only as passive guidance (Decision 2)?
- OQ2: Must the skill literally be scaffolded by invoking the environment `skill-creator` skill to satisfy the ticket criterion, or is a hand-authored skill that conforms to the same structure acceptable? `skill-creator` is not in-repo and cannot be exercised by this phase (ref: Q4).
- OQ3: What `allowed-tools` set does the author want — read/edit-only for safety, or include `Bash` for local `.gitlab-ci.yml` lint/validation (Decision 3)?
- OQ4: Which GitLab target version(s) should reference material assume for version-gated features (CI/CD Catalog/components GA 17.0+), given the ticket asks to cover SaaS and self-managed equally?
