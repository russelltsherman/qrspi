# Design — Create a new agent skill called using argocd cli

**Ticket:** RUS-8
**Research basis:** research.md @ 2026-05-25T22:45:00Z
**Generated:** 2026-05-25T23:00:00Z
**Status:** draft

## Current State

Skills in this project are stored under `/workspaces/qrspi/.claude/skills/`, each as a subdirectory containing a required `SKILL.md` file (ref: Q2). Ten skills currently exist, all following this minimal structure — only `qrspi-work` uses a `references/` subdirectory; none use `scripts/`, `assets/`, or `examples/` (ref: Q2).

The skill-creator validates SKILL.md frontmatter via `scripts/quick_validate.py`, enforcing required fields `name` (kebab-case, max 64 chars) and `description` (max 1024 chars, no angle brackets), with optional fields `license`, `allowed-tools`, `metadata`, and `compatibility` (ref: Q1). Notably, the project's existing skills use `command` and `argument-hint` frontmatter fields that are NOT in the validator's allowed set — running the validator on any existing project skill would fail (ref: Q1, Inconsistencies section).

The SKILL.md body has a soft 500-line budget stated in the skill-creator's own SKILL.md, but no programmatic enforcement exists (ref: Q5). The skill-creator's guidance says to move overflow content to `references/` files with explicit pointers from the main SKILL.md (ref: Q3, Q10).

No existing skill in the project references environment variables like `ARGOCD_AUTH_TOKEN` or `ARGOCD_SERVER` (ref: Q6). The `compatibility` frontmatter field exists for documenting tool dependencies but is documented as "rarely needed" and unused by any project skill (ref: Q6).

Trigger descriptions follow inconsistent conventions — the skill-creator recommends "pushy" imperative descriptions, the plugin-dev recommends third-person with quoted phrases, and existing project skills mostly use short functional descriptions (ref: Q4). There is no cross-skill collision detection mechanism (ref: Q4).

For multi-context skills (interactive vs CI/CD), the skill-creator uses separate top-level sections at the end of SKILL.md that describe deltas from the default workflow (ref: Q8). No other project skill differentiates between contexts (ref: Q8).

For progressive disclosure, the convention is a three-level loading system: metadata (always in context), SKILL.md body (loaded on trigger), and bundled resources in `references/` (loaded on demand) (ref: Q9). Within SKILL.md, escalation uses sequential sections with explicit "Advanced" labels (ref: Q9).

No existing skill encodes environment-conditional defaults like "manual sync for prod, auto for dev" (ref: Q11). The skill-creator philosophy favors explaining reasoning behind recommendations over rigid environment-specific rules (ref: Q11).

The skill quality measurement system includes quantitative evals via grader subagent, benchmark aggregation, qualitative HTML review, optional blind A/B comparison, and post-hoc analysis (ref: Q7). Trigger accuracy is tested by running `claude -p` with queries and checking for skill invocation (ref: Q13). No post-deployment observability exists (ref: Q14).

## Desired End State

**AC1 — agentskills.io directory structure with valid frontmatter:** A new directory `using-argocd-cli/` exists under `.claude/skills/` containing `SKILL.md` with valid YAML frontmatter (fields: `name`, `description`, at minimum) and a `references/` subdirectory. The frontmatter passes the schema constraints documented in `quick_validate.py`.

**AC2 — Built using the Anthropic skill builder skill:** The skill-creator skill is invoked to generate the skill. Its eval loop is used to validate trigger accuracy and skill quality before finalizing.

**AC3 — SKILL.md body under 500 lines / 5000 tokens:** The main SKILL.md body stays within budget. Detailed reference material is offloaded to `references/` files.

**AC4 — Reference material in references/ directory:** Separate reference documents cover: authentication patterns, sync strategies, rollback procedures, ApplicationSet generators, RBAC configuration, and troubleshooting flowcharts. Each is explicitly pointed to from SKILL.md with guidance on when to read it.

**AC5 — Full application lifecycle coverage:** SKILL.md covers create, sync, monitor, rollback, and delete operations as a coherent workflow, not isolated command lists.

**AC6 — Opinionated defaults encoded:** The skill embeds clear defaults: manual sync for production, Git revert over `argocd app rollback`, token-based auth over password, `--dry-run` before sync, declarative manifests for production. Reasoning is provided alongside each default so the agent can apply judgment.

**AC7 — Interactive and CI/CD guidance:** Separate sections handle interactive developer use (login-based auth, exploratory commands) and CI/CD automation (token auth, project-scoped roles, core mode, wait commands with timeouts). The default path is interactive; CI/CD is described as a delta.

**AC8 — Escalation path from simple to complex:** Progressive disclosure moves from single-app management through app-of-apps to ApplicationSets and multi-cluster. Advanced topics are deferred to reference files.

## Delta

**New files:**

- `.claude/skills/using-argocd-cli/SKILL.md` — Main skill definition. Frontmatter with `name: using-argocd-cli` and a trigger-oriented description. Body covers: prerequisites and authentication, core application lifecycle (create, get, diff, sync, monitor, rollback, delete), opinionated defaults with reasoning, context-specific sections for interactive vs CI/CD use, and explicit pointers to reference files. Target: 350-450 lines.

- `.claude/skills/using-argocd-cli/references/authentication.md` — Token-based auth, login flow, context management, core mode, grpc-web, project-scoped role tokens, initial admin password change.

- `.claude/skills/using-argocd-cli/references/sync-strategies.md` — Manual vs automated sync, self-heal, auto-prune, dry-run, sync waves, resource hooks (PreSync/Sync/PostSync/SyncFail), force and prune safety rules, apply-out-of-sync-only.

- `.claude/skills/using-argocd-cli/references/rollback-procedures.md` — Git revert as primary path, emergency rollback with `argocd app rollback`, post-rollback Git reconciliation, deployment history inspection.

- `.claude/skills/using-argocd-cli/references/applicationsets.md` — Generator types (Git, Cluster, Matrix, List), preserveResourcesOnDeletion for production, transition criteria from app-of-apps pattern (>20 apps or >3 clusters).

- `.claude/skills/using-argocd-cli/references/rbac-configuration.md` — AppProject isolation, project-scoped roles with JWT, deny-all defaults, production sync permission restrictions.

- `.claude/skills/using-argocd-cli/references/troubleshooting.md` — Diagnostic flowchart starting with `argocd app get`, branching to dry-run, terminate-op, resources, logs, manifests, hard-refresh based on symptom.

**New eval file:**

- `evals/argocd-evals.json` — Trigger accuracy eval set in skill-creator format. Should-trigger queries (e.g., "sync my argocd app", "check argocd deployment health") and should-not-trigger queries (e.g., "deploy with kubectl", "install argocd server", "write a Kubernetes deployment manifest").

**No modified files.** This is a net-new skill with no impact on existing skills or infrastructure.

## Pattern Decisions

### Decision 1: Skill location

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Place under `.claude/skills/using-argocd-cli/` alongside existing qrspi skills | Consistent with all 10 existing skills in the project (ref: Q2). Auto-discovered by Claude Code's skill scanner. | Mixes workflow-specific (qrspi-*) skills with general-purpose CLI skills in the same directory. |
| B | Place under a separate top-level directory (e.g., `skills/` or `agent-skills/`) | Clean separation between project-workflow skills and reusable CLI skills. | Requires verifying Claude Code's skill discovery scans this path. Breaks from established project convention. |

**Recommendation:** Option A
**Rationale:** All existing skills live under `.claude/skills/` and are auto-discovered from that path (ref: Q2). Introducing a second skill root adds discovery risk for no functional benefit.
**NEW PATTERN?** No — follows existing convention exactly.

### Decision 2: Reference file granularity

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Six reference files (authentication, sync, rollback, applicationsets, rbac, troubleshooting) | Maps directly to the six topic areas in the acceptance criteria (AC4). Claude loads only the relevant file per query. Keeps each file focused and under 300 lines. | More files to maintain. Requires precise pointers from SKILL.md. |
| B | Two reference files (operations.md for lifecycle topics, architecture.md for patterns) | Fewer files. Simpler SKILL.md pointers. | Larger individual files. Claude loads unrelated content alongside relevant content. Doesn't match the AC4 enumeration cleanly. |
| C | Single reference file (reference.md with table of contents) | Simplest structure. Matches the project's minimal reference usage (only qrspi-work uses references/) (ref: Q2). | Defeats progressive disclosure — Claude loads everything on any reference read. Will likely exceed 300 lines, violating the skill-creator's guidance for large reference files (ref: Q3). |

**Recommendation:** Option A
**Rationale:** The acceptance criteria explicitly list six topic areas. The skill-creator instructs reference files to include a table of contents if over 300 lines (ref: Q3), and a single file combining all six topics would certainly exceed that. Six files also align with the domain-organization pattern from the skill-creator (aws.md/gcp.md/azure.md example) (ref: Q9).
**NEW PATTERN?** Yes — This project currently has only one skill with a single reference file. Six reference files is a significant increase in reference directory usage. Justified because the ArgoCD CLI surface area is large and the acceptance criteria explicitly require six distinct topic areas. The pattern is documented and supported by the skill-creator; it is simply unused in this project until now.

### Decision 3: Frontmatter field set

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Use only `quick_validate.py`-compliant fields: `name`, `description`, optionally `compatibility` | Passes automated validation. Aligns with the skill-creator's schema (ref: Q1). | Breaks from the convention of all 10 existing project skills, which use `command` and `argument-hint` (ref: Q1, Inconsistencies). |
| B | Use `name`, `description`, `command`, `argument-hint` like existing project skills | Consistent with existing project skills. Enables slash-command invocation (ref: Q4). | Fails `quick_validate.py` validation — same as every other project skill currently does (ref: Q1, Inconsistencies). |

**Recommendation:** Option B
**Rationale:** Every existing skill in the project uses `command` and `argument-hint`. The validator's allowed-properties set appears to lag behind actual usage. Consistency with the 10 existing project skills outweighs compliance with a validator that none of them pass. If the validator is updated later, all skills (including this one) can be batch-fixed.
**NEW PATTERN?** No — follows the existing (if technically non-compliant) project convention.

### Decision 4: Environment-conditional guidance style

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Explain reasoning behind defaults, let Claude apply judgment per situation | Follows the skill-creator's writing style guidance ("explain why, not heavy-handed MUSTs") (ref: Q11). More adaptable to unanticipated situations. | Agent may choose wrong default without clear rules. |
| B | Explicit conditional rules ("In production: manual sync. In dev/staging: automated sync is acceptable.") | Unambiguous. Agent cannot misapply the default. | Rigid. May not cover all environments. Conflicts with skill-creator philosophy (ref: Q11). |

**Recommendation:** Hybrid — state the opinionated default explicitly (e.g., "Default to manual sync for production"), then provide one sentence of reasoning. This gives the agent both a clear default and the judgment to deviate when context warrants it.
**NEW PATTERN?** Yes — No existing skill encodes environment-conditional defaults (ref: Q11). This hybrid approach is new to the project. Justified because the ArgoCD skill inherently operates across environments with different safety profiles, and the ticket explicitly requires opinionated defaults.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Trigger collision with kubectl-related skills or prompts. ArgoCD operates on Kubernetes resources, and user prompts may be ambiguous ("sync my deployment"). | Medium | Medium | Include explicit should-not-trigger queries in the eval set for kubectl/helm/flux prompts. Tune the description to emphasize "argocd" CLI specifically, not generic Kubernetes operations. Test trigger discrimination during the eval loop (ref: Q13). |
| SKILL.md body exceeds 500-line budget. The ticket's scope covers authentication, lifecycle, sync strategies, rollbacks, app-of-apps, ApplicationSets, RBAC, multi-cluster, and troubleshooting — significantly more surface area than any existing skill. | High | Low | Aggressively defer detail to reference files. SKILL.md contains workflow structure and pointers only. Monitor line count during authoring. The skill-creator's own SKILL.md is 485 lines — the budget is tight but achievable if reference files carry the detail (ref: Q5, Q10). |
| Reference files are created but never loaded by Claude because SKILL.md pointers are insufficiently directive. | Medium | High | Each pointer in SKILL.md must specify the exact filename and the condition under which to read it (e.g., "When the user asks about sync strategies or needs to choose between manual and automated sync, read references/sync-strategies.md"). Follow the skill-creator's explicit guidance on referencing (ref: Q3). |
| Eval set does not catch edge-case trigger failures. The skill-creator's trigger testing runs queries individually and cannot detect cross-skill collisions (ref: Q13). | Medium | Low | Manually review the eval set for coverage of ambiguous prompts. Include at least 3 should-not-trigger queries that are plausibly close to ArgoCD but belong to other tools. Accept that cross-skill collision testing is a known gap in the current infrastructure (ref: Q13). |

## Open Questions

- OQ1: Should this skill use the `command` and `argument-hint` frontmatter fields (matching existing project skills) even though they fail `quick_validate.py`? The research found this inconsistency (ref: Q1, Inconsistencies). If the validator should be treated as authoritative, the new skill should omit these fields — but then it diverges from all 10 existing skills. A human decision is needed on which convention to follow.

- OQ2: The ticket says "Built using the Anthropic skill builder skill" (AC2). The skill-creator's eval loop requires the `claude -p` CLI tool and subagent support (ref: Q7, Q13). Should the eval loop be run as part of this ticket's implementation, or is it acceptable to generate the skill content and defer eval-loop validation to a follow-up? The answer affects scope and time.

- OQ3: Should the `compatibility` frontmatter field be used to declare the dependency on the `argocd` CLI binary being available on PATH? No existing skill uses this field (ref: Q6), but this skill is the first in the project to depend on an external CLI tool.

- OQ4: The ticket's scope guidance says "Out of scope: ArgoCD server installation/upgrade." However, several authentication patterns (initial admin password change, `argocd login`) presuppose a running server. Should the skill include a brief "Prerequisites: verify argocd CLI is installed and server is reachable" section, or should it assume these are always satisfied?

- OQ5: Six reference files is significantly more than any existing skill in this project (ref: Q2). Is there a concern about setting a precedent that makes future skills more complex than they need to be, or is the ArgoCD CLI surface area large enough to justify this as a one-off?
