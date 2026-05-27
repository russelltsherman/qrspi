# Design — Create a new agent skill called using argo workflows cli

**Ticket:** RUS-7
**Research basis:** research.md @ 2026-05-27
**Generated:** 2026-05-27T00:00:00Z
**Status:** draft

## Current State

1. The project has no Argo Workflows skill or any Argo-related tooling. No Argo workflow YAML files exist in the codebase (ref: Q13).

2. Agent skills in this project follow a consistent convention: YAML frontmatter (name, description, command, argument-hint, allowed-tools) plus a Markdown body, stored at `.claude/skills/<skill-name>/SKILL.md` (ref: Q1, Q2). The project CLAUDE.md documents skill location as `.qrspi/agents/` but the actual path is `.claude/skills/` — a known documentation bug (ref: Q2).

3. The `argo` CLI binary is not installed in the devcontainer. Confirmed via `which argo` returning nothing (ref: Q6). The devcontainer is egress-restricted via squid proxy + iptables, and sudoers only allows specific security scripts (ref: Q6, Q10).

4. The skill-creator skill defines the canonical skill structure: a `SKILL.md` with frontmatter and body, plus optional `scripts/`, `references/`, and `assets/` subdirectories (ref: Q1, Q3). The recommended SKILL.md body is under 500 lines, though the existing `qrspi-work` skill at ~638 lines demonstrates this is a soft guideline (ref: Q3).

5. Authentication for `argo` relies on kubeconfig (default mode), Argo server gRPC, or Argo server HTTP — the CLI has no built-in credential manager (ref: Q5). In this environment, no `ARGO_SERVER` or `ARGO_TOKEN` environment variables are set (ref: Q5).

6. The eval harness at `evals/` is infrastructure-complete but execution-stubbed: `scripts/run_eval.py` has a placeholder `execute_single` that returns empty results, so end-to-end evals cannot currently run (ref: Q12).

7. `argo lint` performs only client-side validation; server-side validation requires reaching the Argo server via `submit --server-dry-run` (ref: Q9). The two stages produce different failure modes (ref: Q9).

8. WorkflowTemplates are namespace-scoped; ClusterWorkflowTemplates are cluster-scoped. Namespace resolution for `--from` falls back through kubeconfig context, env vars, and default — but auto-resolution is unreliable across multi-namespace clusters (ref: Q11).

## Desired End State

The `using-argo-workflows-cli` skill will be a functional agent skill that guides agents through all major Argo Workflow operations. After this feature ships:

- **AC1: Skill follows agentskills.io directory structure with valid SKILL.md frontmatter.** The skill lives at `.claude/skills/using-argo-workflows-cli/SKILL.md` with YAML frontmatter containing `name`, `description`, `command`, `argument-hint`, and `allowed-tools`. Directory structure: `SKILL.md` + `references/` subdirectory. (ref: Q1, Q2)

- **AC2: Built using the skill-creator skill.** The skill is produced following the `skill-creator` guidance on frontmatter schema, body structure, and progressive disclosure. (ref: Q1, Q3)

- **AC3: SKILL.md body under 500 lines / 5000 tokens.** The core guidance fits within the hard body limit, with supplementary material deferred to `references/` files. (ref: Q3)

- **AC4: Detailed reference material in `references/` directory.** Shared templates, parameter conventions, and troubleshooting matrices live in `references/` to keep the main SKILL.md lean. (ref: Q1)

- **AC5: Covers all major argo CLI command groups.** The SKILL.md encodes usage for: submit, get, logs, list, delete, retry, resubmit, stop, terminate, suspend, resume, watch, lint, cron, template. (ref: Q4)

- **AC6: Includes DAG vs Steps template selection guidance with clear decision criteria.** A decision table maps workflow complexity to the appropriate template type. (ref: ticket description)

- **AC7: Encodes retry strategy and error handling conventions with exponential backoff patterns.** Covers `retryStrategy` fields, `backoff.duration/factor/maxDuration`, `retryPolicy` selection, and idempotency requirements. (ref: ticket description)

- **AC8: Provides debugging workflow covering argo get -> argo logs -> kubectl describe escalation path.** A decision matrix maps workflow status symptoms to the appropriate debugging stage. (ref: Q14)

- **AC9: Covers CronWorkflow lifecycle management.** Encodes create, list, get, delete, suspend, resume, and lint commands with concurrency policy guidance. (ref: ticket description, Q4)

- **AC10: Includes resource management conventions.** Covers `resources.requests/limits`, `nodeSelector`, `tolerations`, `parallelism`, `synchronization` semaphores, and `podPriorityClassName`. (ref: ticket description)

- **AC11: Addresses artifact configuration best practices.** Covers default repository configuration, `.tgz` suffix convention, UID-parameterized keys, input vs output artifacts, artifact passing vs parameters threshold, and garbage collection. (ref: ticket description)

## Delta

**New files:**
- `.claude/skills/using-argo-workflows-cli/SKILL.md` — Main skill file with frontmatter and core guidance
- `.claude/skills/using-argo-workflows-cli/references/templates.md` — DAG vs Steps comparison, WorkflowTemplate/ClusterWorkflowTemplate usage patterns
- `.claude/skills/using-argo-workflows-cli/references/debugging.md` — Escalation decision matrix, common failure causes and remedies
- `.claude/skills/using-argo-workflows-cli/references/cron.md` — CronWorkflow lifecycle guide with concurrency policy decision tree
- `.claude/skills/using-argo-workflows-cli/references/artifacts.md` — Artifact configuration, parameterization patterns, garbage collection

**Modified files:**
- None. This is a new skill; no existing files are modified.

**No new queries, database changes, or middleware registrations.** This skill is purely instructional text — it does not add runtime behavior to the system.

## Pattern Decisions

### Decision 1: Skill body organization — monolithic SKILL.md vs split into indexed body

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Single SKILL.md body with all 11 acceptance areas, using clear section headers | Simple, single file to review, follows the qrspi-work precedent (even though it exceeds 500 lines) | Risk of approaching/exceeding 500-line limit; harder for agents to skip irrelevant sections |
| B | Core SKILL.md covers only invocation patterns (submit, get, logs, list) and delegates detailed guidance to `references/` files via `Read` tool calls | Keeps body well under 500 lines; follows skill-creator progressive disclosure guidance; agents load references on demand | More complex structure; agents might skip references if the SKILL.md body doesn't explicitly call `Read` |

**Recommendation:** Option B
**Rationale:** The skill-creator skill's progressive loading model is the dominant architecture in this project (ref: research pattern 6). Splitting complex reference material (debugging matrix, cron decision tree, artifact patterns) into `references/` keeps the SKILL.md body focused on action-oriented guidance. The `qrspi-work` skill at 638 lines is an exception that proves the rule — it is the largest skill and suffers from section sprawl. For a CLI skill with 11 distinct topic areas, Option B is structurally sound.
**NEW PATTERN?** No — references/ subdirectory is an existing skill-creator convention.

### Decision 2: Prerequisite encoding — inline installation vs documented-as-given

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | SKILL.md checks `which argo` at start and provides a curl install command if missing | Self-contained; agent can recover from missing binary | Requires egress access to GitHub; sudo may be needed for system install; devcontainer sudoers blocks general installs (ref: Q10) |
| B | SKILL.md documents installation as a prerequisite in a Prerequisites section, checks `command -v argo`, and fails with clear instructions if missing | Respects devcontainer constraints; no installation attempt needed; follows the pattern that install is a host-level concern | Agent must manually install before using skill; not fully self-healing |

**Recommendation:** Option B
**Rationale:** The devcontainer has egress blocked through squid and sudoers restricted to security scripts only (ref: Q6, Q10). Attempting to install `argo` inline would fail in this environment. The skill-creator skill's pattern for prerequisite tools is to document them explicitly. Option B is the only option that works in the constrained devcontainer.
**NEW PATTERN?** No — documenting prerequisites is a standard practice across existing QRSPI skills.

### Decision 3: WorkflowTemplate reference encoding — inline YAML vs --from flag

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Teach agents to write full inline YAML workflows and submit via `argo submit -f -` | Works for any workflow without pre-existing templates; simpler for one-off use | Verbose; duplicates template logic across workflows; harder to keep consistent across agents |
| B | Teach agents to reference existing WorkflowTemplates via `argo submit --from wf/<name>` with explicit `--namespace` | Reuses validated templates; single source of truth; reduces SKILL.md body size | Requires template to pre-exist; namespace resolution is fragile without explicit `--namespace` (ref: Q11) |

**Recommendation:** Option A as default, Option B for team workflows
**Rationale:** Most agent-authored workflows will be one-off exploratory runs. Inline YAML is the lower-friction path. For reusable patterns, the references/ file should cover `--from` workflow (ref: Q7). The decision tree: small/one-off -> inline; reusable -> `--from wf/`; cluster-wide -> `--from cwt/` with cluster-admin note.
**NEW PATTERN?** No — this is standard Argo practice documented in the Argo CLI docs (ref: Q4).

### Decision 4: Debugging section scope — argo-only vs argo + kubectl escalation

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Cover only `argo` commands (get, logs, watch, retry) in the SKILL.md | Keeps scope tight to argo CLI; avoids scope creep | Agent lacks path when argo commands are insufficient; leaves critical debugging gap |
| B | Include the full escalation ladder: argo get -> argo logs -> kubectl describe -> kubectl events | Complete debugging path; prevents agent dead-end when argo alone is insufficient (ref: Q14) | Introduces `kubectl` dependency; slightly broadens scope beyond pure argo |

**Recommendation:** Option B
**Rationale:** The ticket explicitly requires a debugging workflow covering argo get -> argo logs -> kubectl describe (ref: acceptance criteria). The research confirms that argo logs can be empty (ref: Q14) and kubectl is needed for pod-level diagnostics. The escalation matrix in Q14 is already designed and should be encoded directly.
**NEW PATTERN?** No — cross-tool escalation is common (git + gh, argo + kubectl).

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| SKILL.md body exceeds 500 lines despite optimization | Medium | High — violates acceptance criterion; agents may skip sections | Use Option B for body organization (core SKILL.md + references/). During implementation, count lines after each section. If approaching 450, defer content to references/. |
| Agent cannot use the skill because argo binary is missing | Medium | Medium — skill is immediately unusable in devcontainer | Document installation as prerequisite (Option B for Decision 2). SKILL.md begins with `command -v argo` check. In devcontainer, `~/.local/bin/` install is possible without sudo (ref: Q10). |
| Egress restrictions block argo binary download | Low | Medium — even user-level install to ~/.local/bin may fail through squid | Pre-download the argo binary as part of devcontainer setup in a future ticket. For now, document the curl command and note the egress constraint. Squid allowlist can be extended. |
| Agent submits workflow to wrong namespace | Medium | Low — workflow runs but is hard to find/debug | Always encode explicit `--namespace` usage in submit commands. The research confirms auto-resolution is unreliable across multi-namespace clusters (ref: Q11). |
| Client-side lint passes but server-side submit fails | High | Low — agent learns the validation gap from error message | Document the two-stage validation pattern explicitly (ref: Q9). Encourage `--server-dry-run` before real submit in scripts and CI. |
| No existing Argo workflow YAMLs as test fixtures | High | Low — eval harness has no fixtures to validate skill output against | Create minimal Argo workflow fixture YAMLs in `evals/fixtures/` for the eval harness. Even a 5-line workflow is sufficient for structural validation (ref: Q13). |

## Open Questions

- OQ1: Should this skill's `allowed-tools` include `Bash` (for running argo commands), `Read` (for referencing skill docs), and/or any MCP tools? The qrspi-work skill uses a long allowed-tools list. What is the minimal set for this skill?

- OQ2: The ticket references `agentskills.io` as a standard, but research confirms this project uses `.claude/skills/` with its own conventions (ref: Q1). Should the skill description explicitly mention agentskills.io for discoverability, or should it follow the project's existing naming and triggering patterns?

- OQ3: Should the skill include a `/using-argo` slash command in its frontmatter `command` field, or should it trigger purely through description matching like the skill-creator skill? If using a command, what argument-hint makes sense?

- OQ4: The debug escalation path references `kubectl describe` and `kubectl get events`. Should the skill also grant access to `kubectl` via allowed-tools, or should it instruct the agent to use Bash to run kubectl commands directly?

- OQ5: The cron workflow section covers `argo cron create` through `argo cron lint`. Should the skill encode actual cron schedule generation (e.g., converting "every Monday at 9am" to cron syntax), or assume the agent already knows cron syntax?

- OQ6: The eval harness execution is currently stubbed (ref: Q12, research inconsistency 2). Should skill testing for this ticket depend on the eval harness, or is manual review against acceptance criteria sufficient for this first skill?
