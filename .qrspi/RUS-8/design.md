# Design — Create a new agent skill for the argocd CLI

**Ticket:** RUS-8
**Research basis:** research.md @ 2026-06-03T00:00:00Z
**Generated:** 2026-06-03T00:00:00Z
**Status:** draft

## Current State

This repo holds 10 skills, each a self-contained directory at `.claude/skills/<name>/SKILL.md`; discovery is purely directory-convention with no manifest, index, or registry file, so adding a skill edits no other file (ref: Q5). There is no `argocd` skill today, and no Kubernetes/GitOps tooling of any kind in the skill set (ref: Q4). The triggerable surface is the wrapper `SKILL.md`; a separate `.claude/agents/qrspi-<phase>.md` agent definition is only required when a skill delegates to a fresh-context sub-agent — `qrspi-ticket` and `qrspi-work` ship as a single SKILL.md with no agent, which is the minimal discoverable deliverable (ref: Q4).

Frontmatter is a convention, not code-enforced: all 10 files consistently use the five keys `name`, `description`, `command`, `argument-hint`, `allowed-tools` in that order, with `name` == directory == `command` minus the slash, and `allowed-tools` minimized per skill (ref: Q3). `description` is left unquoted in 9 of 10 files and quoted only when it contains YAML-special characters such as colons (ref: Q3). Two body templates exist: a thin wrapper (`# /<command>` + a single `## Steps` list) and a rich self-contained skill (descriptive H1 + topical `##` sections + bash-fenced examples) (ref: Q10).

Only one skill — `qrspi-work` — demonstrates the `references/` split: always-needed procedure stays in the body, while deep, conditionally-needed material moves to `references/<topic>.md`, cited skill-root-relative (no leading `./`) and loaded on demand at the decision point (ref: Q1, Q7). There are no multi-reference (2+) skills in the repo to copy, and no `assets/` directory exists anywhere (ref: Q7, Q1). No skill contains its own `scripts/` subdirectory; shared executable logic lives in the repo-level `scripts/` and is invoked `python3 scripts/<name>.py` repo-root-relative (ref: Q1, Q8). There is no per-skill `scripts/`/`assets/` precedent (ref: Q8).

There is no SKILL.md frontmatter validator and no line/token budget mechanism in the repo; the 500-line/5000-token figure is enforced nowhere, and `qrspi-work/SKILL.md` itself is 565 lines, confirming non-enforcement (ref: Q3, Q6). Verification is by stdlib unit tests for Python logic and manual end-to-end runs; the `evals/` harness is a documented but non-functional placeholder, and there is no automated SKILL.md validity or trigger test (ref: Q9). No runtime skill-selection logging exists; a `description`'s correctness is judged only by its explicit "Use when…/Trigger on…" trigger clause and externally by the skill-creator eval loop (ref: Q11). The `skill-creator` skill referenced by the ticket is external to `REPO_ROOT` and cannot be inspected or vendored here (ref: Q2).

## Desired End State

A new self-contained skill exists at `.claude/skills/using-argocd-cli/SKILL.md`, auto-discovered with no other file edited, satisfying each acceptance criterion:

- **agentskills.io directory structure + valid frontmatter** → a kebab-named directory with `SKILL.md` carrying the repo's five-key frontmatter in order; `name` == directory, `command` == `/using-argocd-cli`, `description` quoted (it will contain colons), `allowed-tools` minimized to `Bash` (ref: Q3, Q5, Q10).
- **Built using the Anthropic skill-builder skill** → the skill is authored through the external `skill-creator` skill as the final authoring/validation step (ref: Q2); this is the only criterion the design cannot fully wire in-repo and is tracked as a process step, not a code deliverable.
- **SKILL.md body under 500 lines / 5000 tokens** → enforced by author discipline only, since no checker exists; body holds procedure + when-to-consult pointers, deep material is offloaded to `references/` (ref: Q6, Q7).
- **`references/` covering auth, sync strategies, rollback, ApplicationSet generators, RBAC, troubleshooting flowcharts** → six topic files, each a self-titled H1 cited skill-root-relative from the relevant body section (ref: Q1, Q7).
- **Full lifecycle: create, sync, monitor, rollback, delete** → body sections walk each stage with bash-fenced `argocd` examples (ref: Q10).
- **Opinionated defaults (manual sync for prod, Git revert over rollback, token auth over password)** → encoded as explicit rules in body and references, matching the convention of `**bold**` key rules (ref: Q10).
- **Both interactive developer and CI/CD automation contexts** → auth/context section and references contrast interactive `argocd login`/`context` with token + env-var + `--core`/`--grpc-web` automation.
- **Clear escalation path simple → multi-cluster/ApplicationSet** → body orders content from single-app operations to app-of-apps to ApplicationSets to multi-cluster, mirroring the on-demand reference pattern (ref: Q7).

## Delta

New directory `.claude/skills/using-argocd-cli/` containing:

- `SKILL.md` — five-key frontmatter; descriptive H1 `# Using the Argo CD CLI`; topical `##` sections in escalation order: Authentication & Context, Application Lifecycle (create/get/diff/sync/wait/delete), Sync Strategies, Health Monitoring, Rollbacks, App-of-Apps, ApplicationSets, RBAC & Projects, Multi-Cluster, Troubleshooting. Each deep section ends with a skill-root-relative pointer into `references/`. Bash-fenced command examples throughout. Target ~250–350 lines (discipline only, no enforcement).
- `references/authentication.md` — token vs password, `ARGOCD_SERVER`/`ARGOCD_AUTH_TOKEN`/`ARGOCD_OPTS`, `--grpc-web`, `--core`, project-scoped role tokens, interactive `login`/`context`.
- `references/sync-strategies.md` — manual vs automated, `--self-heal`/`--auto-prune`, `--dry-run`, sync waves, hooks, `--force`/`--prune` cautions, retry policies, `--apply-out-of-sync-only`.
- `references/rollback-procedures.md` — Git revert preference, `argocd app rollback` emergency use + auto-disable of automated sync, `app history`, follow-up revert.
- `references/applicationset-generators.md` — Git/Cluster/Matrix/List generators, app-of-apps→ApplicationSet transition thresholds, `preserveResourcesOnDeletion`.
- `references/rbac-configuration.md` — AppProjects, project-scoped role tokens, `admin settings rbac validate`/`can`, SSO group mapping, deny-all default.
- `references/troubleshooting.md` — flowchart prose: `app get` → `app resources` → events/logs → `terminate-op`, manifest live-vs-git compare, hard refresh, repo connectivity.

No existing file is modified. No repo-level `scripts/` entry and no `assets/` directory are added (none are needed; the skill is prose + command examples). No agent definition is created (the skill is self-contained).

## Pattern Decisions

### Decision 1: Skill type — self-contained vs. wrapper+agent

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Self-contained SKILL.md (like `qrspi-ticket`/`qrspi-work`), no agent | Minimal discoverable deliverable (ref: Q4); fits a CLI knowledge skill; one fewer dialect to maintain | Body must stay disciplined to meet length goal |
| B | Wrapper SKILL.md + `.claude/agents/` agent definition | Matches the QRSPI phase pattern | Agent layer is for fresh-context delegation, not static CLI guidance (ref: Q4); adds the agent frontmatter dialect (ref: Q3) for no benefit |

**Recommendation:** Option A
**Rationale:** The skill conveys static CLI conventions, not a delegated multi-step phase; research confirms self-contained skills are valid and minimal, and the agent layer exists only for sub-agent delegation (ref: Q4).
**NEW PATTERN?** No.

### Decision 2: Reference material placement

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Six topic files under skill-local `references/`, cited skill-root-relative | Matches the only existing reference precedent (`qrspi-work`) and agentskills.io standard (ref: Q1, Q7); directly satisfies the references acceptance criterion | First multi-reference (2+) skill in repo — extends, but does not violate, the one-file precedent |
| B | Inline everything in SKILL.md | One file | Violates the references criterion; blows the length goal with no checker to catch it (ref: Q6, Q7) |

**Recommendation:** Option A
**Rationale:** The references directory is an explicit acceptance criterion and the body-vs-reference split is exactly the `qrspi-work` model — body holds procedure, references hold deep per-topic knowledge cited at the decision point (ref: Q7).
**NEW PATTERN?** Partial — first 2+-reference skill in the repo. Justified: the single-reference precedent generalizes cleanly to N topic files; each follows the same self-titled-H1, skill-root-relative-citation contract (ref: Q1, Q7).

### Decision 3: Helper scripts

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | No `scripts/`; ship prose + bash-fenced examples only | Matches repo (no per-skill `scripts/` precedent) (ref: Q8); nothing to test/maintain | Examples are copy-paste, not executable |
| B | Per-skill `scripts/` with helper(s) | Reusable automation | New pattern with no precedent; would need `+x`, shebang, and a `_test.py` per repo discipline (ref: Q8) for marginal value |

**Recommendation:** Option A
**Rationale:** The ticket's scope is CLI guidance, not shipped automation; the repo has no per-skill `scripts/` precedent and shared scripts live repo-level (ref: Q8). Avoiding scripts keeps the deliverable a pure knowledge skill.
**NEW PATTERN?** No (Option A avoids the unprecedented per-skill `scripts/` dir).

### Decision 4: Skill name / command

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | `using-argocd-cli` | Mirrors the `using-graphite-cli` CLI-skill naming, the nearest conceptual model (ref: Q9, Q10); kebab-case | Slightly long |
| B | `argocd` | Short | Diverges from the `using-<tool>-cli` convention modeled by the Graphite skill |

**Recommendation:** Option A
**Rationale:** The Graphite CLI skill is the nearest precedent for a non-QRSPI CLI skill (ref: Q9, Q10); `using-argocd-cli` matches its naming and reads as a clear trigger phrase, with `name` == directory == `command` minus slash (ref: Q3).
**NEW PATTERN?** No.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| SKILL.md exceeds 500-line/5000-token target unnoticed (no checker exists) (ref: Q6) | med | low | Author discipline: keep body to procedure + pointers, push depth into the six references; manually count lines before submit |
| `skill-creator` (required by AC) is external and unverifiable in-repo (ref: Q2) | high | med | Treat skill-creator as a manual process step run during implementation; design otherwise conforms to observed in-repo conventions so the skill is valid even if skill-creator output differs |
| Reference path citation wrong (absolute or `./`-prefixed) breaks on-demand load (ref: Q1) | low | med | Follow the `qrspi-work` precedent exactly: skill-root-relative `references/<file>.md`, no leading `./` |
| First 2+-reference skill drifts from single-file precedent (ref: Q7) | low | low | Give each reference a self-titled H1 and cite from one body section, replicating the single-file contract N times |
| No automated trigger/validity test; mis-scoped `description` fails silent (ref: Q9, Q11) | med | med | Embed an explicit "Use when…/Trigger on…" clause listing argocd/GitOps phrases, and verify via manual e2e + the external skill-creator eval loop |

## Open Questions

- OQ1: Must the skill be authored *through* the external `skill-creator` skill (AC #2) to be accepted, or is a hand-authored skill that conforms to repo conventions sufficient? skill-creator lives outside `REPO_ROOT` and cannot be inspected here (ref: Q2).
- OQ2: Is the 500-line/5000-token budget a hard gate for this skill given that nothing enforces it and `qrspi-work` (565 lines) already exceeds it (ref: Q6)? Confirm whether reviewers will measure it manually.
- OQ3: Should the skill ship copy-pasteable bash examples only, or are executable helper scripts/assets desired despite there being no per-skill `scripts/`/`assets/` precedent (ref: Q8)?
