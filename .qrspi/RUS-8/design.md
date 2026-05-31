# Design — Create a new agent skill called using argocd cli

**Ticket:** RUS-8
**Research basis:** research.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## Current State

The repository hosts ten skills, all of which are QRSPI-internal phase skills under `.claude/skills/<skill-name>/` and a paired agent prompt at `.claude/agents/<agent-name>.md` (ref: Q1). Skill directories follow the `qrspi-` kebab-case namespace and the SKILL.md frontmatter uses exactly five fields: `name`, `description`, `command`, `argument-hint`, `allowed-tools` (ref: Q2, Q4). Only the orchestrator `qrspi-work` ships a `references/` subdirectory containing a single Markdown file consulted on demand (ref: Q3, Q9). No skill in the repo currently ships a `scripts/` or `assets/` subdirectory (ref: Q3).

The repo does not contain a local skill-creator or skill-builder skill; only one agent prompt references invoking it as a validation step (ref: Q5). The repo's eval harness (`evals/suite.json`, `scripts/run_eval.py`, etc.) is currently scoped to QRSPI phase agents — there is no precedent for evaluating a CLI-wrapper skill (ref: Q11, Q12). Failure-handling conventions are unambiguous: a HARD STOP block forbidding workarounds for permission, auth, config, or tooling errors is duplicated across both the orchestrator and agent prompts (ref: Q8). Status output is plain stdout — short `Print:` lines emitted by the orchestrator and a one-line summary returned by agents (ref: Q13). No existing skill in the repo wraps an external CLI tool, so RUS-8 is establishing the first such pattern in this codebase (ref: Q3, Q8, Discovered Patterns).

## Desired End State

After RUS-8 ships, a new skill named `using-argocd-cli` exists under `.claude/skills/using-argocd-cli/` that guides Claude Code agents in operating Argo CD deployments via the `argocd` CLI. Acceptance criteria map as follows:

- **Valid agentskills.io directory + frontmatter.** `SKILL.md` at the skill root has frontmatter matching the repo's five-field shape plus any required agentskills.io fields. `references/` directory holds the supplementary docs called out in the ticket (authentication patterns, sync strategies, rollback procedures, ApplicationSet generators, RBAC configuration, troubleshooting flowcharts).
- **Built using skill-creator.** The skill is generated via the global skill-creator skill (invoked manually during implementation) so its structure and description follow Anthropic's authoring guidelines.
- **Body ≤ 500 lines / ≤ 5000 tokens.** The main SKILL.md stays under the limit by pushing long-form material into `references/` files, mirroring the `qrspi-work` pattern.
- **Reference material covers the six topics.** Six reference files (one per topic) live in `references/`, each loaded on demand by the skill body.
- **Covers the full application lifecycle.** SKILL.md and its references walk the agent through create, sync, monitor, rollback, and delete operations.
- **Opinionated defaults encoded.** Manual sync for production, Git revert preferred over imperative rollback, token-based auth over username/password, declarative manifests over `argocd app create`.
- **Interactive + CI/CD guidance.** Both contexts are explicitly addressed in the body (Core mode, `--grpc-web`, project-scoped role tokens for CI; `argocd login` and `argocd context` for interactive).
- **Escalation path from simple to complex.** The body guides the agent from single-app management up through app-of-apps, ApplicationSets, and multi-cluster patterns, with the >20-application or >3-cluster threshold for switching to ApplicationSets explicitly documented.

## Delta

New files (all under `.claude/skills/using-argocd-cli/`):

- `SKILL.md` — the main skill body. Frontmatter declares `name: using-argocd-cli`, a description that triggers on Argo CD / argocd CLI / GitOps / sync / rollback work, a `command` if one is needed, and a tightly-scoped `allowed-tools` list (Bash for argocd invocations, plus Read for reading manifests; no MCP tools required).
- `references/authentication.md` — token vs. username/password, `ARGOCD_*` environment variables, `--grpc-web` flag, Core mode (`--core`), project-scoped role tokens.
- `references/sync-strategies.md` — manual vs. automated sync, `--self-heal`/`--auto-prune` pairing, sync waves, resource hooks, retry policies, `--apply-out-of-sync-only`.
- `references/rollback-procedures.md` — Git revert preferred; emergency `argocd app rollback`; automated-sync disabling; `argocd app history`; PostSync-driven automated rollback.
- `references/applicationset-generators.md` — Git, Cluster, Matrix, List generators; when to use each; templating DRYness; `preserveResourcesOnDeletion` for production.
- `references/rbac-configuration.md` — AppProjects, project-scoped role tokens, `argocd admin settings rbac validate`/`can`, SSO group mapping, deny-by-default posture.
- `references/troubleshooting.md` — start-with-`argocd app get` flowchart; stuck syncs; resource-level debugging; manifest diff (`--source live` vs `--source git`); hard refresh; repo connectivity.

No modifications to existing files are required. `.qrspi/templates/`, `.claude/agents/`, and the eval harness are out of scope. The skill is self-contained.

The skill-creator skill is invoked once during implementation to scaffold and validate; it is not added to the repo, only used.

## Pattern Decisions

### Decision 1: Skill-only vs. skill + paired agent prompt

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Skill-only — all content lives in `SKILL.md` and `references/`; no `.claude/agents/using-argocd-cli.md` | Matches agentskills.io shape; simpler; no agent dispatch overhead; mirrors `qrspi-ticket` which is also skill-only | Diverges from the QRSPI phase-skill convention of wrapper + agent |
| B | Wrapper skill that spawns a paired sub-agent (mirrors `qrspi-questions` et al.) | Consistent with QRSPI phase-skills; allows per-agent tool restrictions | Sub-agent dispatch adds latency and complexity; not justified for a reference-only skill; agentskills.io standard does not require it |

**Recommendation:** Option A
**Rationale:** The skill is a reference document, not an orchestration step. There is no Linear fetch, no artifact-producing pipeline, no need to firewall a sub-context. The agentskills.io standard targets self-contained skills with `SKILL.md + references/` (ref: Q1, Q3). The QRSPI phase-skill wrapper pattern exists because phase agents need different tool scopes from the user-facing skill (ref: Q6); that constraint does not apply here. `qrspi-ticket` is the closest in-repo analogue and is also skill-only.
**NEW PATTERN?** No — Option A mirrors `qrspi-ticket` and the agentskills.io standard.

### Decision 2: Where to put long-form Argo CD guidance

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | All guidance inline in `SKILL.md` | One file to read; no cross-references | Likely breaks the 500-line / 5000-token budget; fails ticket criterion |
| B | Topic-per-file `references/` with `SKILL.md` linking on demand | Mirrors `qrspi-work` overflow pattern (ref: Q9); keeps body scannable; matches ticket's reference-directory criterion | Six new files to maintain; cross-reference rot risk |

**Recommendation:** Option B
**Rationale:** The ticket explicitly requires the body under 500 lines / 5000 tokens AND reference material in `references/` covering six named topics. Option B satisfies both. The repo precedent for the overflow pattern is `qrspi-work`, which keeps `review-cascade.md` in `references/` and reads it on demand (ref: Q3, Q9).
**NEW PATTERN?** No — extends the `qrspi-work` overflow pattern by adding more reference files.

### Decision 3: `allowed-tools` scope for the new skill

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | `allowed-tools: Bash, Read` (broad Bash) | Lets the agent invoke any `argocd` subcommand without enumeration | Permits arbitrary shell beyond `argocd` |
| B | `allowed-tools: Bash(argocd:*), Read` (path-restricted Bash) | Aligns with the `Bash(pwd:*)` pattern used by most QRSPI phase skills (ref: Q6); narrows the blast radius | The agent may also need `kubectl` for cross-tool debugging documented in the ticket; restricting too tightly forces escape hatches |
| C | `allowed-tools: Bash, Read, Edit` | Lets the agent edit manifests in the working tree alongside CLI calls | Edit is rarely needed when the user owns Git-side authoring; out of scope per ticket (Kubernetes resource authoring is deferred) |

**Recommendation:** Option B with a documented Bash exception list
**Rationale:** The path-restricted form (`Bash(argocd:*)`) is the project's documented convention for skills that wrap a specific tool (ref: Q6). Where the troubleshooting flow calls for `kubectl describe`, the skill should instruct the agent to defer to a kubectl-specific skill rather than expanding its own tool surface, which matches the ticket's "Out of scope" guidance. Read is required for inspecting Application manifests and `argocd app manifests` output saved to files.
**NEW PATTERN?** No — `Bash(<cmd>:*)` is already used by QRSPI phase skills.

### Decision 4: Whether to add an eval case

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Add an eval case to `evals/suite.json` for the new skill | Establishes a precedent for evaluating non-QRSPI skills | The harness is built around QRSPI phase artifacts (ref: Q11); a CLI-wrapper skill produces no `.md` artifact, so existing programmatic checks (`output_file_exists`, `question_count`) do not apply |
| B | Skip evals; rely on skill-creator validation + manual smoke test | Matches the de-facto practice in the repo (ref: Q12); avoids forcing a new eval framework into the current suite | No automated regression check |

**Recommendation:** Option B
**Rationale:** The ticket's acceptance criteria do not mandate evals. The current eval harness's programmatic assertions are written against artifact files produced by QRSPI phases (ref: Q11), and the new skill produces guidance rather than artifacts. Establishing a new eval pattern is itself a separate concern and would expand scope. Skill-creator's own validation, plus a manual smoke test on a representative argocd task, is the established acceptance bar (ref: Q12).
**NEW PATTERN?** No — codifies the existing default.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| The SKILL.md body exceeds the 500-line / 5000-token limit because each Argo CD topic naturally expands | high | medium | Hard cap the body at scaffolding + topic-links + opinionated-defaults summary; push every example, flag-by-flag table, and procedure into `references/` |
| The skill duplicates content that the agentskills.io community already publishes (drift between local and upstream) | medium | low | Cite the upstream conventions in the SKILL.md description; keep wording opinionated to this org's defaults so divergence is intentional |
| The `allowed-tools` declaration leaks beyond `argocd` and the skill turns into a general-purpose kubectl runner | medium | medium | Lock `Bash` to `Bash(argocd:*)` and explicitly defer kubectl/Helm/CI work to other skills, as the ticket scope guidance dictates |
| skill-creator's recommended structure conflicts with the repo's existing five-field frontmatter shape (ref: Q4) | low | medium | Resolve the conflict during implementation by extending the frontmatter only if skill-creator requires it; document the resolution in the impl-log |
| The `.claude/CLAUDE.md` inconsistency (`.qrspi/agents/` vs actual `.claude/agents/`) misleads the agent during creation (ref: Inconsistencies) | low | low | The new skill does not require an agent prompt at all (Decision 1), so the inconsistency does not affect this ticket; flag separately in the impl-log if encountered |
| The skill's opinionated defaults (e.g., "manual sync for production") conflict with a team that has chosen automated sync, leading to incorrect agent guidance in some shops | low | medium | Phrase defaults as opinionated recommendations with rationale, not absolutes; document the trade-offs so an agent can adapt to local policy |

## Open Questions

- OQ1: Does Russell want the skill to declare a `command:` (e.g., `/argocd`) so it can be slash-invoked, or should it remain auto-triggered only (matching `using-graphite-cli` which has no slash command in the visible skill listing)? The QRSPI skills all declare a `command`; some global skills do not. The ticket does not specify.
- OQ2: Should `references/` use the `.md` extension only, or include a small JSON/YAML cheat sheet of common `argocd` invocations for fast lookup? Adding such a file would be a new pattern in this repo.
- OQ3: Is invoking the global skill-creator during this ticket's implementation acceptable inside a worktree, given that skill-creator may want to write to global skill directories? The ticket says to use skill-creator; the project scope firewall says implementations must stay in the worktree. The expected resolution is that skill-creator only writes inside the worktree path passed to it, but this requires verification before implementation.
