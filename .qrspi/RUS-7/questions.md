# Questions — Create a new agent skill called using argo workflows cli
**Ticket:** RUS-7
**Generated:** 2026-05-27T00:00:00Z
**Status:** draft

## Data Flow
- Q1: What is the directory structure and file format expected by `agentskills.io` for an agent skill?
  **Target:** agentskills.io specification documentation
- Q2: How does the existing `qrspi-work` skill structure its SKILL.md, and what conventions does it follow for embedding CLI workflows?
  **Target:** `.qrspi/agents/qrspi-work` skill files
- Q3: What is the token and line limit for SKILL.md bodies, and how does the skill parser enforce the 500-line / 5000-token constraint?
  **Target:** Skill loading and parsing code in the project

## API Surface
- Q4: Which `argo` CLI command groups and subcommands are required to cover the acceptance criteria (submit, get, logs, list, delete, retry, resubmit, stop, terminate, suspend, resume, watch, lint, cron, template)?
  **Target:** `argo` CLI documentation or source
- Q5: How does the `argo` CLI handle authentication — does it read kubeconfig, or does it expect explicit flags for token and server URL?
  **Target:** `argo` CLI source or documentation
- Q6: What is the scope of the `argo` CLI — is it a standalone binary installed on the agent host, or does the skill need to install it?
  **Target:** Host environment and existing `argo` installation checks

## State Management
- Q7: How should the skill encode Argo WorkflowTemplate and ClusterWorkflowTemplate references — as inline YAML, as references, or both?
  **Target:** SKILL.md content covering template authoring section
- Q8: What state persists between agent turns when managing a workflow (e.g., monitoring mid-run), and how should the skill instruct agents to track workflow names?
  **Target:** Skill guidance on workflow monitoring conventions

## Edge Cases
- Q9: What happens when `argo lint` passes but `argo submit --server-dry-run` fails — how should the skill encode the gap between client-side and server-side validation?
  **Target:** SKILL.md validation section
- Q10: How should the skill handle the case where the `argo` binary is not installed or not on PATH? Does it need to encode an installation step, or is that a prerequisite?
  **Target:** SKILL.md preconditions or references section
- Q11: When using `argo submit --from` with a WorkflowTemplate, how does the CLI resolve namespace if `--namespace` is not explicitly provided — and what error surfaces?
  **Target:** `argo submit` behavior and namespace resolution

## Testing
- Q12: How should the skill validate its own correctness — are there tests for skills, or is manual review against the acceptance criteria the only verification method?
  **Target:** The `skill-creator` skill and any eval harness in `evals/`
- Q13: Can existing Argo Workflows in the codebase be used as test fixtures to verify the skill's guidance produces valid workflow specs?
  **Target:** Any existing workflow YAML in the repository

## Observability
- Q14: The ticket requires a debugging workflow covering `argo get` -> `argo logs` -> `kubectl describe` — how should the skill encode when to escalate from `argo` commands to raw `kubectl` (e.g., when pod events are needed vs. when `argo logs` suffices)?
  **Target:** SKILL.md debugging section
