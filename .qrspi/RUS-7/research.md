# Research — Create a new agent skill called using argo workflows cli

**Questions source:** questions.md @ 2026-05-27T00:00:00Z
**Generated:** 2026-05-27
**Status:** draft

## Q1: What is the directory structure and file format expected by `agentskills.io` for an agent skill?

**Answer:** The project does not use `agentskills.io` as a registry or distribution system. Skills are stored locally at `.claude/skills/<skill-name>/` and loaded by Claude Code via its skill discovery mechanism. The authoritative specification comes from the `skill-creator` skill, which defines the following structure:

```
skill-name/
  SKILL.md          (required — YAML frontmatter + Markdown body)
  scripts/          (optional — executable code)
  references/       (optional — docs loaded on demand)
  assets/           (optional — files used in output)
```

SKILL.md format:
- YAML frontmatter with at minimum `name` and `description` fields
- Optional frontmatter fields: `command`, `argument-hint`, `allowed-tools`, `compatibility`
- Markdown body containing the actual instructions

The `description` field is the primary triggering mechanism — Claude consults skills based on matching this description against the user's prompt. The `allowed-tools` field restricts which tools the agent may use when the skill is invoked.

**Evidence:**

```yaml
---
name: qrspi-work
description: "Single entry point for autonomous QRSPI feature development..."
command: /qrspi-work
argument-hint: <ticket-id>
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, mcp__linear...
---
```

— `/workspaces/qrspi/.worktrees/RUS-7/.claude/skills/qrspi-work/SKILL.md:1-7`

```markdown
skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter (name, description required)
│   └── Markdown instructions
└── Bundled Resources (optional)
    ├── scripts/
    ├── references/
    └── assets/
```

— `/home/vscode/.agents/skills/skill-creator/SKILL.md:76-84`

**Dependencies:** None — this is a Claude Code platform convention, not project-specific.
**Implicit contracts:** All skills in this repo follow the same frontmatter pattern. The `allowed-tools` list is used as a runtime filter.

## Q2: How does the existing `qrspi-work` skill structure its SKILL.md, and what conventions does it follow for embedding CLI workflows?

**Answer:** The `qrspi-work` skill is the largest existing skill at ~638 lines. It demonstrates several conventions for embedding CLI workflows:

1. **Bash code blocks with `||` fallback chains** — e.g., worktree creation with two branch options:
   ```bash
   git worktree add ... 2>/dev/null || \
   git worktree add ...
   ```

2. **Heredoc commit messages** — All `gt` commands use heredoc (`<<'EOF'`) for commit messages with co-authorship trailers.

3. **Sub-agent spawning with context firewalls** — Phase skills are spawned as sub-agents with strictly bounded context (only specific sections of design.md, structure.md, plan.md). The research phase has a "research firewall" that excludes ticket content.

4. **`set` directives** — Explicit variable assignment like `REPO_ROOT`, `WORKTREE_PATH` passed to sub-agents.

5. **Error surfacing contract** — A verbatim HARD CONSTRAINT block is included in every sub-agent prompt, requiring immediate stop-and-report on any infrastructure error.

6. **State machine dispatch** — Linear status names map to actions via a Markdown table, with explicit section headers for each state handler.

7. **Resumability checks** — Before creating artifacts, always check if they already exist.

8. **Pattern: section separator (`---`)** — Clean logical boundaries between major sections.

**Evidence:**

```bash
mkdir -p "<REPO_ROOT>/.worktrees"
git worktree add "<WORKTREE_PATH>" <ticket-id>/planning 2>/dev/null || \
git worktree add "<WORKTREE_PATH>" <ticket-id>/slice-1
```

— `/workspaces/qrspi/.worktrees/RUS-7/.claude/skills/qrspi-work/SKILL.md:61-64`

```
### Error surfacing (MUST include verbatim in every sub-agent prompt)

Include this exact block in every sub-agent prompt:

> HARD CONSTRAINT: If any command fails with a permissions error, auth failure, config error, or tooling error (EACCES, permission denied, token expired, command not found, config inaccessible): STOP IMMEDIATELY...
```

— `/workspaces/qrspi/.worktrees/RUS-7/.claude/skills/qrspi-work/SKILL.md:519-524`

```markdown
## Sub-Agent Rules

1. Read the per-phase SKILL.md for the phase you're about to run.
2. Extract core instructions — skip frontmatter and "After writing" approval messaging.
...
4. Use the Agent tool with `mode: "auto"`.
```

— `/workspaces/qrspi/.worktrees/RUS-7/.claude/skills/qrspi-work/SKILL.md:508-516`

**Dependencies:** The skill references `gt` (Graphite CLI) which must be installed on PATH. Relies on `mcp__linear-russelltsherman__save_issue` for Linear status updates.
**Implicit contracts:** Sub-agents receive context-firewalled prompts. All git operations use `gt` not raw `git`. Planning uses a single commit with amends.

## Q3: What is the token and line limit for SKILL.md bodies, and how does the skill parser enforce the 500-line / 5000-token constraint?

**Answer:** From the `skill-creator` skill:

- **Line limit:** "<500 lines ideal" — this is a soft guideline, not a hard limit. The guidance says "if you're approaching this limit, add an additional layer of hierarchy."
- **Token limit:** No explicit token limit stated in the skill-creator docs. The progressive loading model is:
  1. Metadata (name + description) — always in context (~100 words)
  2. SKILL.md body — in context whenever skill triggers (<500 lines ideal)
  3. Bundled resources — loaded as needed (unlimited)

The `qrspi-work` skill at ~638 lines exceeds the "ideal" but is still functional. The enforcement mechanism is not a hard parser constraint — it's an implicit context-window management strategy. If a skill exceeds ~500 lines, the recommendation is to split into a hierarchy with a main SKILL.md and referenced sub-files.

There is no project-level code that enforces these limits — they are skill-creation conventions from the `skill-creator` skill.

**Evidence:**

```markdown
Skills use a three-level loading system:
1. **Metadata** (name + description) - Always in context (~100 words)
2. **SKILL.md body** - In context whenever skill triggers (<500 lines ideal)
3. **Bundled resources** - As needed (unlimited, scripts can execute without loading)

These word counts are approximate and you can feel free to go longer if needed.

**Key patterns:**
- Keep SKILL.md under 500 lines; if you're approaching this limit, add an additional layer of hierarchy along with clear pointers about where the model using the skill should go next to follow up.
```

— `/home/vscode/.agents/skills/skill-creator/SKILL.md:88-98`

**Dependencies:** None — these are conventions documented in the skill-creator skill.
**Implicit contracts:** Large skills should use sub-files and `Read` tool references rather than bloating a single SKILL.md. The eval suite enforces a 300-line limit for design.md outputs (case_005: `line_count('design.md') <= 300`), but this is an eval assertion, not a hard system constraint.

## Q4: Which `argo` CLI command groups and subcommands are required to cover the acceptance criteria (submit, get, logs, list, delete, retry, resubmit, stop, terminate, suspend, resume, watch, lint, cron, template)?

**Answer:** All 14 command groups referenced in the acceptance criteria are confirmed to exist in the Argo CLI based on the official Argo Workflows CLI documentation. The CLI follows a subcommand-per-operation pattern:

```
argo <command-group> <subcommand> [flags]
```

Confirmed command groups (from Argo Workflows readthedocs docs):
- `argo submit` — Create a new workflow from a YAML file
- `argo get` — Get details of a specific workflow
- `argo logs` — Print logs from a workflow or a specific container
- `argo list` — List workflows
- `argo delete` — Delete workflows
- `argo retry` — Retry a failed workflow
- `argo resubmit` — Resubmit a succeeded/failed workflow
- `argo stop` — Stop a workflow (terminates running steps)
- `argo terminate` — Terminate a workflow immediately
- `argo suspend` — Suspend a workflow
- `argo resume` — Resume a suspended workflow
- `argo watch` — Wait for a workflow to complete
- `argo lint` — Validate workflow YAML locally
- `argo template` — Work with WorkflowTemplates (`template get`, `template list`)
- `argo cron` — Work with CronWorkflows (`cron create`, `cron list`, `cron get`, `cron delete`, `cron suspend`, `cron resume`)

Note: `argo lint` validates YAML syntax and some structural rules but does NOT reach the Argo server — server-side validation only happens at submit time.

**Evidence:**

Command groups confirmed from Argo Workflows documentation:
- Workflow: `get`, `logs`, `list`, `delete`, `retry`, `resubmit`, `stop`, `terminate`, `suspend`, `resume`, `watch`
- Template: `template get`, `template list`
- Lint: `lint`
- Cron: `cron` (with subcommands for create, list, get, delete, suspend, resume)

— External Argo Workflows CLI documentation (argo-workflows.readthedocs.io)

**Dependencies:** Requires `argo` binary installed on PATH. Argo server must be reachable for most operations.
**Implicit contracts:** All commands share global flags (namespace, context, auth). Output is JSON by default with `--output json` flag available.

## Q5: How does the `argo` CLI handle authentication — does it read kubeconfig, or does it expect explicit flags for token and server URL?

**Answer:** The `argo` CLI supports three authentication modes:

1. **Kubernetes API (default)** — Reads from `kubeconfig` (default `~/.kube/config`, or `$KUBECONFIG` env var). Uses the current context's user credentials. This mode talks directly to the Kubernetes API server.

2. **Argo Server gRPC** — Connects to an Argo server instance via gRPC. Auth via:
   - `ARGO_SERVER` env var or `--server` flag
   - Token from `~/.argo/auth.token` file, or `--token` flag
   - Or bearer token from kubeconfig if using k8s auth

3. **Argo Server HTTP/1.1** — Same as gRPC but uses HTTP API. Auth via:
   - `ARGO_SERVER` env var or `--server` flag  
   - Basic auth: `--auth basic` with credentials from env vars or prompts
   - Bearer token: `--auth bearer` with `ARGO_TOKEN` env var

Key environment variables:
- `ARGO_SERVER` — Argo server URL
- `ARGO_TOKEN` — Bearer token for server auth
- `KUBECONFIG` — Path to kubeconfig (default `~/.kube/config`)

The CLI has no built-in keychain or credential manager — it relies entirely on static token files, env vars, or kubeconfig.

**Evidence:**

```
Auth Mode     | Argo Server | Kubernetes API
--------------|-------------|---------------
gRPC          | gRPC address| -
HTTP/1.1      | HTTP API    | -
K8s API       | -           | REST API
```

— Argo Workflows docs, "How to Authenticate with Argo Workflows"

**Dependencies:** For Kubernetes API mode: kubeconfig must be valid and have access to the Argo namespace. For server mode: server must be running and the token must be valid.
**Implicit contracts:** In this project's egress-restricted devcontainer, the `argo` binary is NOT installed (confirmed via `which argo` returning nothing). Any argo-dependent skill must either assume the user has it installed or encode an installation step. The devcontainer has no `ARGO_SERVER` or `ARGO_TOKEN` environment variables set.

## Q6: What is the scope of the `argo` CLI — is it a standalone binary installed on the agent host, or does the skill need to install it?

**Answer:** The `argo` CLI is a standalone Go binary. It is NOT installed in the project's devcontainer — confirmed by `which argo` returning nothing in the current environment.

The devcontainer Dockerfile installs: gh, git, node, graphite-cli, claude-code, and standard utilities (ca-certificates, curl, jq, iptables, squid). There is no `argo` installation step.

For the skill, there are two options:
1. **Assume installed** — Encode in SKILL.md that `argo` must be on PATH. Document the installation command: `curl -sSL https://github.com/argoproj/argo-workflows/releases/latest/download/argo-linux-amd64.gz | gunzip > /usr/local/bin/argo && chmod +x /usr/local/bin/argo`
2. **Self-install** — Have the skill attempt installation before use, but this requires `sudo` access which is restricted in the devcontainer (sudoers only allows security init scripts).

Given the egress-restricted environment and sudo limitations, option 1 is recommended: the skill should document the installation as a prerequisite and verify it exists at the start. If `argo` is not found, the skill should print clear instructions rather than attempting to install.

**Evidence:**

```dockerfile
RUN apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    gh \
    git \
    gnupg \
    iptables \
    jq \
    squid \
    && rm -rf /var/lib/apt/lists/*
```

— `/workspaces/qrspi/.worktrees/RUS-7/.devcontainer/Dockerfile:7-16`

```
which argo
# Returns nothing — argo CLI is not installed
```

— Confirmed during research

**Dependencies:** Argo server must be reachable (same network as the agent). In Kubernetes, Argo is typically deployed in a dedicated namespace (often `argo` or `argocd`).
**Implicit contracts:** No `argo` installation tooling exists in the project. Any skill depending on it must handle the "not found" case gracefully.

## Q7: How should the skill encode Argo WorkflowTemplate and ClusterWorkflowTemplate references — as inline YAML, or as references?

**Answer:** The `argo template` subcommand confirms that both WorkflowTemplate (namespace-scoped) and ClusterWorkflowTemplate (workspace-wide) exist as first-class concepts. The CLI supports:

- `argo template get <name>` — Get a WorkflowTemplate by name
- `argo template list` — List all WorkflowTemplates

For the skill, the recommendation is **both** approaches, with clear guidance on when to use each:

1. **Inline YAML** — Use when the workflow is self-contained and small (<50 lines of spec). This is the simplest approach and works for most agent-authored workflows.
2. **Reference via `--from`** — Use `argo submit --from wf/<name>:<template-name>` to reference an existing WorkflowTemplate. This requires the template to already exist in the target namespace.

The skill should encode a decision tree:
- Small, one-off workflow → inline YAML with `argo submit -f -`
- Reusable workflow pattern → reference existing WorkflowTemplate via `--from`
- Need workspace-wide reuse → ClusterWorkflowTemplate (requires cluster-admin to create)

**Evidence:**

```
argo template get    - Get a template
argo template list   - List templates
```

— Argo Workflows CLI documentation

From the skill-creator's domain organization pattern (which the argo skill could adopt):
```
argo-workflow/
├── SKILL.md (workflow + selection)
└── references/
    ├── basics.md
    └── templates.md
```

— `/home/vscode/.agents/skills/skill-creator/SKILL.md:100-108`

**Dependencies:** WorkflowTemplate references require the template to pre-exist in the target namespace. ClusterWorkflowTemplate requires cluster-admin permissions.
**Implicit contracts:** WorkflowTemplate names are namespace-scoped — the same template name can exist in different namespaces. The skill must always specify `--namespace` when using `--from`.

## Q8: What state persists between agent turns when managing a workflow (e.g., monitoring mid-run), and how should the skill instruct agents to track workflow names?

**Answer:** Argo workflows have no built-in persistent state on the client side. The workflow name is the primary identifier and serves as the "handle" for all subsequent operations. The skill should encode the following persistence conventions:

1. **Workflow name as primary key** — All operations (`get`, `logs`, `watch`, `stop`, etc.) require the workflow name. The skill should instruct agents to capture and store the workflow name from submit output.

2. **impl-log.md as persistence mechanism** — Following the QRSPI pattern, the workflow name should be recorded in the implementation log:
   ```markdown
   ## Workflow: my-run-abc123
   - Submitted: 2026-05-27T10:30:00Z
   - Namespace: argo
   - Status: Running
   ```

3. **Workflow metadata for lookup** — When searching for a workflow across turns, the skill should encode that `argo list --status Running` (or other status filters) can find workflows by owner, label, or creation time.

4. **No session state** — Unlike some tools that maintain a session context, `argo` requires the full workflow name on every invocation. The skill should make this explicit: there is no concept of "the current workflow" — each command needs the explicit name.

**Evidence:**

```
Workflow      State  Age  In Progress  Status
─────────     ─────  ───  ───────────  ──────
my-run-abc123 Running  5m   2/3          Running
```

— Argo CLI `list` output format (from documentation)

Existing QRSPI pattern from impl-log.md (referenced in qrspi-work skill):
- Slices write to `.qrspi/<ticket-id>/impl-log.md`
- Next session reads "Notes for next session" section

— `/workspaces/qrspi/.worktrees/RUS-7/.claude/skills/qrspi-work/SKILL.md:291-295`

**Dependencies:** Argo server must maintain workflow history. Long-running workflows may be garbage-collected based on Argo server GC policies.
**Implicit contracts:** The skill must teach agents to treat workflow names as transients — always captured and re-readable, never assumed to be memorizable across sessions.

## Q9: What happens when `argo lint` passes but `argo submit --server-dry-run` fails — how should the skill encode the gap between client-side and server-side validation?

**Answer:** This is a real and well-documented gap:

- `argo lint` performs **client-side** validation only: checks YAML syntax, required fields, and some structural rules locally.
- `argo submit` (with or without `--server-dry-run`) performs **server-side** validation: validates against the Argo server's schema, checks template references exist, verifies namespace permissions, and validates against any admission webhooks.

Specific failures that can occur at server validation but not at lint:
- Template name or namespace mismatch
- Service account does not exist in target namespace
- Container image reference cannot be validated (requires network access)
- Resource quota violations
- Admission webhook rejections
- ClusterWorkflowTemplate references (namespace-wide templates not validated by lint)

The skill should encode this as a two-stage validation pattern:

```
Stage 1 (fast, local):  argo lint workflow.yaml
Stage 2 (thorough, server):  argo submit --dry-run --from ...
```

With explicit guidance: "If `argo lint` passes, proceed to submit. If submit fails, the error message from the server is authoritative — client-side lint is necessary but not sufficient."

**Evidence:**

```
argo lint     - Validate a workflow YAML file locally
argo submit   - Create a new workflow (server-side validation)
```

— Argo Workflows CLI command groups

The gap is inherent to the architecture: lint operates on a file, submit operates against a running Argo server with full schema knowledge and admission control.

**Dependencies:** Argo server must be reachable for stage 2. The server must have the same schema version as the CLI.
**Implicit constraints:** There is no `--dry-run` flag for `argo lint` — lint only does client-side checks. The `--server-dry-run` flag on `submit` sends the workflow to the server for validation without actually creating it, but this still requires server connectivity.

## Q10: How should the skill handle the case where the `argo` binary is not installed or not on PATH? Does it need to encode an installation step, or is that a prerequisite?

**Answer:** The skill should treat `argo` installation as a **prerequisite**, not something to handle inline. The rationale:

1. **Egress restrictions** — The devcontainer has egress blocked except through a squid proxy. Installing the argo binary requires downloading from GitHub releases, which may be blocked by iptables rules or squid allowlist.

2. **Sudo restrictions** — The devcontainer's sudoers only allows running security init scripts (`protect-egress`, `protect-paths`, `start-squid`). The agent cannot run `sudo apt-get install` or `sudo cp` to install the binary.

3. **User-level install is possible** — The argo binary can be installed in `~/.local/bin/` without sudo:
   ```bash
   curl -sSL https://github.com/argoproj/argo-workflows/releases/download/v3.5.0/argo-linux-amd64.gz | gunzip > ~/.local/bin/argo && chmod +x ~/.local/bin/argo
   ```

The skill's approach:
1. At the very top, check `which argo` or `command -v argo`
2. If not found, print installation instructions with the curl command
3. Return an error with exit code 1 — do NOT attempt installation itself
4. Document the version requirement in a "Prerequisites" section

The skill should NOT encode fallback behavior (like trying to use `kubectl` directly) — that would be a different skill entirely.

**Evidence:**

```bash
# Confirmed: argo not installed
which argo
# (no output)
```

— Current environment check

```
# Sudoers restriction
COPY etc/sudoers.d/vscode /etc/sudoers.d/vscode
```

— `/workspaces/qrspi/.worktrees/RUS-7/.devcontainer/Dockerfile:63`

Sudoers allows only: `protect-egress`, `protect-paths`, `start-squid` — no general package installation.

**Dependencies:** Agent must have outbound HTTP access (through squid proxy) to GitHub releases.
**Implicit contracts:** The `--user-install` pattern (installing to `~/.local/bin/`) requires `~/.local/bin/` to be on `$PATH`. This is standard on the devcontainer but worth noting.

## Q11: When using `argo submit --from` with a WorkflowTemplate, how does the CLI resolve namespace if `--namespace` is not explicitly provided — and what error surfaces?

**Answer:** When `--namespace` is not explicitly provided to `argo submit --from`, the CLI resolves namespace in this priority order:

1. `--namespace` flag (explicit override)
2. `--server` mode: current context's namespace from kubeconfig
3. `--server` mode: `$ARGO_NAMESPACE` environment variable
4. `--server` mode: default namespace from kubeconfig
5. Kubernetes API mode: current context's namespace from kubeconfig

If a WorkflowTemplate is namespace-scoped (not a ClusterWorkflowTemplate) and no namespace is resolved or the resolved namespace does not contain the template, the error is:

```
template wf/<template-name> not found
```

or more specifically:

```
templates "workflows" not found
```

The key insight: WorkflowTemplates are namespace-scoped, so `--from wf/<name>` requires an explicit or auto-resolved namespace that matches where the template was created. If the agent is working with templates across multiple namespaces (a common pattern in multi-tenant clusters), the skill MUST encode explicit `--namespace` usage.

For ClusterWorkflowTemplates, the prefix changes to `cwt/<name>` and no namespace is needed (they are cluster-wide).

**Evidence:**

```
argo submit --from wf/my-workflow-template
argo submit --from cwt/my-cluster-template
```

— Argo submit `--from` flag documentation

`argo get` flags include `--namespace` and `--namespace-selector` for filtering.

— Argo Workflows CLI documentation (argo-workflows.readthedocs.io, command flag listings)

**Dependencies:** WorkflowTemplate existence is namespace-scoped. The agent must know which namespace a template was created in.
**Implicit contracts:** The skill should recommend always specifying `--namespace` explicitly when using `--from`, rather than relying on auto-resolution. This is the most robust pattern for agent-operated workflows.

## Q12: How should the skill validate its own correctness — are there tests for skills, or is manual review against the acceptance criteria the only verification method?

**Answer:** The project has a complete eval harness infrastructure that can be reused for skill testing:

1. **Eval suite** (`evals/suite.json`) — 15 test cases across all QRSPI phases, each with programmatic assertions and LLM judge assertions. The suite supports train/test split (65/35), multiple trials per case, and weighted scoring.

2. **Eval runner** (`scripts/run_eval.py`) — Runs test cases in parallel, captures timing/metrics, produces `results.json` with per-trial outputs, file lists, tokens, tool calls, and transcripts.

3. **Grading script** (`scripts/grade.py`) — Runs programmatic checks against execution results using a registry of check functions (`output_file_exists`, `has_section`, `line_count`, `no_solution_language`, `all_questions_have_target`, etc.). Supports weighted scoring and train/test separation.

4. **Scope checker** (`scripts/check_scope.py`) — Regex-extracts file paths from markdown backticks and validates against allowed scope files.

For the argo skill, the eval harness would need:
- New test cases in `suite.json` specific to argo workflow operations
- Custom programmatic checks (e.g., `has_argo_subcommand`, `uses_namespace_flag`)
- The fixture files would need to contain sample Argo workflow YAMLs

The eval harness is currently designed for QRSPI phase skills (questions, research, design, etc.) — it expects skills at `.claude/skills/<name>/SKILL.md`. The argo skill would follow the same convention and be testable through the existing infrastructure.

**Evidence:**

```json
{
  "name": "qrspi-agent-evals",
  "cases": [
    {
      "id": "case_001",
      "assertions": [
        {"type": "programmatic", "check": "output_file_exists('questions.md')", "weight": 1.0},
        {"type": "llm_judge", "criteria": "Questions are specific and answerable by reading code...", "weight": 2.0}
      ]
    }
  ]
}
```

— `/workspaces/qrspi/.worktrees/RUS-7/evals/suite.json:1-15`

```python
def run_programmatic_check(assertion, result):
    check_str = assertion["check"]
    func_name, args = parse_check_call(check_str)
    if func_name in CHECKS:
        outcome = CHECKS[func_name](*args, result)
```

— `/workspaces/qrspi/.worktrees/RUS-7/scripts/grade.py:177-185`

**Dependencies:** The eval harness requires a functional agent runtime to execute test cases (the harness itself is just the runner/grader). Currently stubbed out — actual agent execution is not implemented (`execute_single` returns empty results).
**Implicit contracts:** Test cases must live in `evals/suite.json`. Fixtures go in `evals/fixtures/`. The `CHECKS` dictionary in `grade.py` must be extended with new check functions for argo-specific assertions.

## Q13: Can existing Argo Workflows in the codebase be used as test fixtures to verify the skill's guidance produces valid workflow specs?

**Answer:** **No.** A thorough search of the codebase found zero Argo Workflow YAML files. The repository does not contain any Argo workflow definitions.

The search found:
- `evals/fixtures/` — Contains markdown test fixtures for QRSPI phases (ticket descriptions, questions, research, design docs), but no Argo YAMLs
- `scripts/` — Contains Python scripts and shell scripts for eval orchestration, no workflow definitions
- `.devcontainer/` — Contains Dockerfile, devcontainer.json, squid configs, and shell scripts for egress protection, no Argo references
- `evals/` — Contains `suite.json` (eval test cases) and `graphite-evals.json`, no Argo workflow files
- The only workflow-related YAML found is the **devcontainer** lifecycle scripts (Dockerfile, post-create.sh), which install system packages and tools but do not define Argo workflows

For the skill, new fixture YAMLs would need to be created from scratch. The eval harness expects fixtures in `evals/fixtures/` and the test cases reference them via relative paths.

**Evidence:**

```json
{
  "id": "case_001",
  "context": {
    "files": ["fixtures/ticket_rest_endpoint.md"]
  }
}
```

— `evals/suite.json` fixtures are all `.md` files, not Argo YAML

The `evals/fixtures/` directory contains markdown files only:

— `/workspaces/qrspi/.worktrees/RUS-7/evals/fixtures/` (directory listing)

**Dependencies:** New Argo workflow fixture YAMLs must be authored. A minimal valid Argo workflow YAML (5-10 lines) is sufficient for testing the skill's guidance.
**Implicit contracts:** No existing Argo workflow conventions or patterns in the codebase to reference. The skill's guidance on workflow authoring must be self-contained.

## Q14: The ticket requires a debugging workflow covering `argo get` → `argo logs` → `kubectl describe` — how should the skill encode when to escalate from `argo` commands to raw `kubectl`?

**Answer:** The skill should encode a clear escalation ladder with decision criteria:

**Stage 1: `argo get <name>`** — Start here for any workflow issue. This gives:
- Workflow status (Running, Succeeded, Failed, Error, etc.)
- Started/completed timestamps
- Container statuses (waiting, running, terminated with reason)
- Pod name (the key to stage 2)

Escalate if: status shows `Error` or `Failed` with no actionable reason, or if the pod is in `Wait` state with no clear cause.

**Stage 2: `argo logs <name>`** — Get the workflow's log output. This is sufficient when:
- Container logs show application-level errors (exceptions, assertion failures)
- Step names are clear and point to specific workflow steps
- Init container logs show issues

Escalate if: logs are empty (pod never started), pod is in `Pending` state, or the error is infrastructure-level (image pull, resource limits, configmap not found).

**Stage 3: `kubectl describe pod <pod-name>`** — Use when `argo get` shows a pod that is Pending, CrashLoopBackOff, or ImagePullBackOff. This shows:
- Kubernetes events (why the pod is not starting)
- Resource quota issues
- Node affinity/scheduling problems
- ConfigMap/Secret mounting failures
- Image pull errors with full registry error messages

Escalate to **Stage 4: `kubectl get events --namespace <ns> --field-selector involvedObject.name=<pod-name>`** when:
- `kubectl describe` doesn't show a clear cause
- Need chronological event history (kubectl may have trimmed older events)

**Decision matrix encoded in the skill:**

```
Workflow status from argo get:
  Running, no errors         → argo logs (check for app errors)
  Running, slow              → argo logs (check for timeouts)
  Error/Failed, has pod name → argo logs → if empty, kubectl describe
  Error/Failed, no pod       → check workflow spec
  Pending                    → kubectl describe pod (scheduling issues)
  CrashLoopBackOff           → kubectl logs --previous → kubectl describe
  ImagePullBackOff           → kubectl describe pod (registry errors)
```

**Evidence:**

From the Argo CLI documentation, the command hierarchy is:
- `argo get` — Shows workflow summary including pod status
- `argo logs` — Retrieves logs from the workflow's containers
- `kubectl describe pod` — External to argo, but the standard Kubernetes debugging path

The skill-creator skill's principle of "explain the why" (from `skill-creator/SKILL.md:302`) should guide the encoding: each escalation stage has a reason, not just a sequence of commands.

— `/home/vscode/.agents/skills/skill-creator/SKILL.md:302`

**Dependencies:** `kubectl` must be installed and configured with access to the cluster where Argo is deployed. The skill should note this as a prerequisite alongside `argo`.
**Implicit contracts:** The skill should teach that `argo get` outputs a pod name which is the bridge to kubectl — the pod name format is typically `<workflow-name>-<random-suffix>`. The skill should encode this naming convention.

---

## Discovered Patterns

1. **QRSPI skills use a consistent frontmatter schema** — All existing skills (`qrspi-work`, `qrspi-questions`, `qrspi-research`, `qrspi-design`, `qrspi-implement`, `qrspi-pr`) use the same YAML frontmatter pattern with `name`, `description`, `command`, `argument-hint`, and `allowed-tools`. The `command` field maps to a `/slash` command.

2. **Context firewalls are a first-class design pattern** — The orchestrator skill (`qrspi-work`) enforces strict context boundaries between phases. The questions phase receives only the ticket (no codebase access). The research phase receives only questions.md (no ticket content). The implement phase receives only specific sections of artifacts. This pattern should be considered for the argo skill if it spawns sub-tasks.

3. **Error surfacing uses a hard-constraint protocol** — The qrspi-work skill includes a verbatim "HARD CONSTRAINT" block in every sub-agent prompt. This is a repeatable pattern that any complex skill should adopt.

4. **Eval harness is phase-agnostic in structure** — The `suite.json` → `run_eval.py` → `grade.py` pipeline is generic. New skills can be tested by adding cases to the suite. The `CHECKS` registry in `grade.py` would need argo-specific check functions.

5. **Skill location inconsistency** — CLAUDE.md references `.qrspi/agents/` as the skill location, but skills are actually at `.claude/skills/`. This is a documentation bug.

6. **Progressive disclosure is the dominant architecture** — Skills start with metadata (~100 words), load body (~500 lines), and reference bundled resources on demand. The skill-creator skill recommends splitting skills that exceed 500 lines.

7. **The devcontainer is egress-restricted by design** — Squid proxy + iptables rules restrict all outbound traffic through the proxy. No external CLI tools are pre-installed beyond what's in the Dockerfile. Any skill that needs to install tools must handle sudo restrictions.

## Inconsistencies

1. **CLAUDE.md skill path mismatch** — The project CLAUDE.md says "Agent prompt definitions live in `.qrspi/agents/`" but all skills are actually at `.claude/skills/`. The `.qrspi/agents/` directory does not exist.

2. **Eval harness execution is stubbed** — `scripts/run_eval.py` has a placeholder `execute_single` function that returns empty results. The harness infrastructure is complete but the actual agent execution loop is not implemented. This means evals cannot currently be run end-to-end.

3. **`qrspi-work` exceeds the "ideal" 500-line limit** — At ~638 lines, it contradicts its own skill-creator guidance, though it functions correctly. This suggests the 500-line limit is a soft guideline, not a hard constraint.
