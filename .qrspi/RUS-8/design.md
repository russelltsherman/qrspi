# Design — Create a new agent skill using argocd CLI

**Ticket:** RUS-8
**Research basis:** research.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## Current State

This repository is the QRSPI workflow itself; "agent skills" here are Claude Code `SKILL.md` prompt files, not Kubernetes automation (ref: scope note). Skills live under `.claude/skills/<skill-name>/`, one directory per skill, each containing a `SKILL.md`; all 10 existing skills are `qrspi-*` prefixed (ref: Q1). Only `qrspi-work` uses a `references/` subdirectory; no skill uses `scripts/` or `assets/` (ref: Q1). There is no argocd, kubectl, Helm, or any CLI-wrapper skill in the repo today (ref: Q10).

Skill frontmatter uses the fields `name`, `description`, `command`, `argument-hint`, and `allowed-tools`; "required" is established by convention only — there is no schema file or validator (ref: Q3). The directory name equals the `name` field equals the slash command minus its leading slash, all lowercase kebab-case (ref: Q4). No existing skill is non-`qrspi-`-prefixed, so any new prefix is a new precedent (ref: Q4). Effective `description` fields state purpose, give a concrete user phrase, and for high-traffic skills enumerate trigger variants — this is the trigger surface the harness matches against user intent (ref: Q7).

The single established progressive-disclosure pattern is in `qrspi-work`: a one-line imperative pointer ("Read `references/review-cascade.md` for cascade logic") defers a self-contained decision procedure to a reference file loaded only when that path executes (ref: Q5, Q9). The repo encodes guidance in three formats: markdown decision tables, numbered do/don't and anti-pattern lists, and bold "HARD STOP" escalation blocks listing explicitly forbidden actions (ref: Q11). It also enforces CLI discipline — "never run raw `git` when a `gt` equivalent exists" — and prefers narrowly scoped shell access like `Bash(pwd:*)` (ref: Q3, Q10).

The `skill-creator` skill named in the ticket process is NOT present in this repository; it is a global/plugin skill outside project scope and could not be read (ref: Q2, scope note). No in-repo tooling enforces or measures the "under 500 lines / 5000 tokens" body budget — it is honor-system guidance in `docs/qrspi_claude_code_guide.md:592`, and there is no token counter (ref: Q8). There is no SKILL.md frontmatter linter or directory-structure validator anywhere in `scripts/` (ref: Q13). Skills become discoverable purely by existing at `.claude/skills/<name>/SKILL.md` — there is no registry to register into (ref: Q6). The eval harness (`evals/` + `scripts/`) is a prompt-quality suite driven by hand-curated cases in `evals/suite.json`, but its execution layer is a stub that returns empty output, so end-to-end eval scores cannot currently be produced (ref: Q6, Q12). There is no `.claude/settings.json` or in-repo hooks directory to log skill invocation (ref: Q14).

## Desired End State

A new skill exists at `.claude/skills/<name>/SKILL.md` plus a `references/` directory, guiding agents to manage Argo CD deployments via the `argocd` CLI. Each acceptance criterion maps as follows:

- **agentskills.io directory structure with valid frontmatter** → a `SKILL.md` carrying `name`, `description`, `command`, `argument-hint`, `allowed-tools` matching the in-repo skill shape (ref: Q3), with directory name == `name` == command-without-slash (ref: Q4).
- **Built using the Anthropic skill builder skill** → authored via the global `skill-creator` skill (external; see Open Questions and Risk) (ref: Q2).
- **SKILL.md body under 500 lines / 5000 tokens** → main body holds flow + pointers only; verbose catalogs live in `references/` (ref: Q5, Q8, Q9). No in-repo tool can verify the 5000-token figure; line count is checkable manually (ref: Q8).
- **Detailed reference material in `references/`** → separate topic files for authentication patterns, sync strategies, rollback procedures, ApplicationSet generators, RBAC configuration, and troubleshooting flowcharts (ref: Q5, Q9).
- **Full lifecycle: create, sync, monitor, rollback, delete** → SKILL.md body sections covering each stage with the ticket's opinionated commands.
- **Encodes opinionated defaults** → manual sync for prod, Git revert over imperative rollback, token auth over password — expressed as decision tables and do/don't lists (ref: Q11).
- **Both interactive developer and CI/CD automation contexts** → distinct guidance blocks (interactive `argocd login`/`context` vs token-based `ARGOCD_AUTH_TOKEN`/`--core` automation).
- **Clear escalation path simple → multi-cluster/ApplicationSet** → decision tables routing app-of-apps vs ApplicationSets (>20 apps or >3 clusters) and a HARD STOP block for auth/cluster-access and sync failures (ref: Q11).

## Delta

**New files:**
- `.claude/skills/<name>/SKILL.md` — main skill body: frontmatter, lifecycle sections (auth, create, diff/sync, monitor, rollback, delete), opinionated-defaults decision tables, scope-deferral do/don't list, one-line pointers into `references/`, and a HARD STOP block.
- `.claude/skills/<name>/references/authentication.md` — token vs password, env vars, `--core`, `--grpc-web`, context management, project-scoped role tokens.
- `.claude/skills/<name>/references/sync-strategies.md` — manual vs automated, self-heal/auto-prune, sync waves, hooks, retry policies, `--force`/`--prune` cautions.
- `.claude/skills/<name>/references/rollback.md` — Git revert vs `argocd app rollback`, history inspection, automated-rollback-on-degraded.
- `.claude/skills/<name>/references/applicationsets.md` — generators (Git, Cluster, Matrix, List), app-of-apps, `preserveResourcesOnDeletion`.
- `.claude/skills/<name>/references/rbac.md` — AppProjects, JWT role tokens, `rbac validate`/`can`, SSO mapping, deny-all default.
- `.claude/skills/<name>/references/troubleshooting.md` — debugging flowchart, `terminate-op`, hard refresh, manifests live-vs-git, repo connectivity.

**Modified files (optional, see Open Questions):**
- `evals/suite.json` — add ≥1 case to make the skill eval-testable (ref: Q12). Requires a fixture and possibly a new check in `grade.py`'s `CHECKS` registry. Currently moot because eval execution is stubbed (ref: Q12).

**No registry edit required** — discoverability is filesystem-driven (ref: Q6).

## Pattern Decisions

### Decision 1: Skill naming / prefix

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | `using-argocd-cli` | Mirrors the global `using-graphite-cli` naming idiom the repo already defers to (ref: Q10); reads as a how-to skill | Introduces first non-`qrspi-` skill (new precedent) (ref: Q4) |
| B | `argocd` | Shortest; matches the binary name | Bare noun is a weak trigger surface; still non-`qrspi-` (ref: Q4, Q7) |
| C | `qrspi-argocd` | Keeps the universal repo prefix (ref: Q4) | Misleading — this is not a QRSPI workflow phase; ticket title says "using argocd cli" |

**Recommendation:** Option A (`using-argocd-cli`)
**Rationale:** The repo's only CLI-wrapping precedent is the global `using-graphite-cli` skill it mandates for git (ref: Q10); matching that `using-<tool>-cli` form is the closest existing convention. The `qrspi-` prefix denotes workflow phases (ref: Q4), which this is not. Either way this is a new naming precedent (ref: Q4).
**NEW PATTERN?** Yes — first non-`qrspi-`-prefixed skill in the repo; no direct in-repo template exists (ref: Q4, Q10). Justified because the universal prefix is semantically a workflow-phase marker and this skill is a general-purpose CLI wrapper.

### Decision 2: SKILL.md vs references/ split point

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Single fat SKILL.md, all commands inline | Simplest; one file | Will blow the 500-line budget (the ticket has 8 large topic areas); ignores the documented split pattern (ref: Q8, Q9) |
| B | Thin SKILL.md + 6 topic references, loaded lazily via one-line pointers | Mirrors the one established split pattern in `qrspi-work`; keeps body small (ref: Q5, Q9); matches the ticket's required `references/` topics | More files to maintain |

**Recommendation:** Option B
**Rationale:** The acceptance criteria explicitly demand a `references/` directory covering six named topics, and the only in-repo precedent (`qrspi-work`) extracts self-contained decision procedures behind one-line pointers loaded on demand (ref: Q5, Q9). This directly satisfies the body-budget criterion (ref: Q8).
**NEW PATTERN?** No — extends the existing `qrspi-work` progressive-disclosure pattern (ref: Q5, Q9).

### Decision 3: `allowed-tools` scope

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | `Bash(argocd:*)` (+ `Read`, possibly `Bash(kubectl:*)`) | Matches repo's narrowly-scoped shell precedent (`Bash(pwd:*)`); least privilege (ref: Q3) | Troubleshooting uses `kubectl describe`/logs — may need a second scoped entry |
| B | Unscoped `Bash` | Covers every command the ticket lists | Violates the repo's least-privilege shell convention (ref: Q3) |

**Recommendation:** Option A, with `Bash(argocd:*)` plus a scoped `Bash(kubectl:*)` for the troubleshooting follow-ups the ticket calls out.
**Rationale:** The repo demonstrates scoped Bash allowlists (`Bash(pwd:*)`) and CLI-wrapping discipline (ref: Q3, Q10). The ticket's troubleshooting flow explicitly chains to `kubectl describe`, so a second scoped grant is warranted.
**NEW PATTERN?** No — scoped `Bash(<cmd>:*)` is established (ref: Q3).

### Decision 4: How to encode opinionated defaults and escalation

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Decision tables + do/don't lists + HARD STOP block | Uses all three established in-repo guidance formats (ref: Q11) | Verbose; pushes some content to references |
| B | Free prose only | Less structure to author | No precedent; harder for an agent to follow under pressure (ref: Q11) |

**Recommendation:** Option A
**Rationale:** The repo's three guidance formats map cleanly onto the ticket: decision tables for judgment calls (app-of-apps vs ApplicationSets, manual vs auto sync), do/don't lists for defaults, and a HARD STOP block for the ticket's "don't jump to `--force`/`--prune`" and auth-failure escalation rules (ref: Q11).
**NEW PATTERN?** No — reuses the decision-table / do-don't / HARD STOP formats (ref: Q11).

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `skill-creator` is external and unavailable, but the ticket mandates building "using the Anthropic skill builder skill" | med | med | Confirm the global `skill-creator` skill is invocable in this session before authoring; if absent, hand-author to the in-repo conventions (Q3–Q5, Q9, Q11) and flag the criterion as partially met (ref: Q2) |
| No in-repo validator/linter or token counter — frontmatter, structure, and the 5000-token budget cannot be auto-checked (ref: Q8, Q13) | high | med | Verify frontmatter by matching the existing skill shape (ref: Q3); keep the body well under 500 lines by aggressive reference splitting; treat "5000 tokens" as approximate |
| First non-`qrspi-` skill sets a new naming precedent that may surprise maintainers (ref: Q4) | med | low | Surface the prefix choice as an Open Question; document rationale in the design |
| Eval coverage cannot be produced end-to-end — execution layer is stubbed (ref: Q12) | high | low | Optionally add a `evals/suite.json` case + fixture for future use, but do not block delivery on a non-functional harness |
| `description` field, the sole trigger surface, may over-trigger or under-trigger without any in-repo logging to verify (ref: Q7, Q14) | med | med | Write a purpose + concrete-phrase + trigger-variants description per the `qrspi-work`/`qrspi-questions` pattern (ref: Q7); include explicit out-of-scope language |

## Open Questions

- OQ1: Skill name/prefix — adopt `using-argocd-cli` (recommended), or keep the universal `qrspi-` prefix despite this not being a workflow phase? Human decision on the new precedent (ref: Q4).
- OQ2: Is the global `skill-creator` skill available and required to be used in this session, or is hand-authoring to in-repo conventions acceptable to satisfy the "built using the skill builder" criterion (ref: Q2)?
- OQ3: Should this skill ship with an `evals/suite.json` case now, given the eval execution layer is currently a stub and would require a new `grade.py` check (ref: Q6, Q12)?
- OQ4: Should `allowed-tools` include scoped `Bash(kubectl:*)` for troubleshooting, or keep the skill strictly `argocd`-only and defer all kubectl steps to a separate skill (ref: Q3, Q10)?
