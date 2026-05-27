# Questions — Create a new agent skill called using argocd cli

**Ticket:** RUS-8
**Generated:** 2026-05-27T00:00:00Z
**Status:** draft

## Data Flow

- Q1: What command-line output formats does the `argocd` CLI produce (JSON, YAML, table), and which formats are used by which subcommands such as `argocd app get`, `argocd app diff`, and `argocd app list`?
  **Target:** the `argocd` CLI source or its help output (`argocd --help`)

- Q2: How does the `ARGOCD_OPTS` environment variable work, and can it be set once at skill initialization to eliminate repetitive flags across all `argocd` subcommands?
  **Target:** the `argocd` CLI documentation or source for environment variable handling

- Q3: What is the structure of an Argo CD Application manifest file, and what fields are required versus optional for `argocd app create` and for declarative manifests committed to Git?
  **Target:** the Argo CD API types definition or the Application CRD schema

- Q4: How do sync waves, resource hooks (PreSync, Sync, PostSync, SyncFail), and resource tracking work together to control ordering and state in Argo CD?
  **Target:** the Argo CD sync controller or resource tracking documentation

## API Surface

- Q5: Which `argocd` subcommands require interactive prompts versus accepting all input via flags, and how does this affect their suitability for agent-driven automation?
  **Target:** the `argocd` CLI source for each subcommand's flag definitions and prompt handling

- Q6: How does the `argocd context` subcommand work for switching between multiple Argo CD server instances, and what state does it persist (config file location, format)?
  **Target:** the `argocd` CLI config file format and context management source

- Q7: What is the format and lifecycle of an `ARGOCD_AUTH_TOKEN`, and how do project-scoped role tokens differ from admin tokens in terms of permissions and longevity?
  **Target:** the Argo CD auth server or project role binding source

## State Management

- Q8: What state does the `argocd` CLI client cache locally (e.g., server certificates, auth tokens, application state), and where is this cache stored?
  **Target:** the `argocd` CLI client config directory (typically `~/.config/argocd/`)

- Q9: How does `argocd app diff` compute the diff between Git state and cluster state, and what inputs does it need (local repo path, revision, remote connection)?
  **Target:** the `argocd app diff` command source code

## Edge Cases

- Q10: What happens when the `argocd` CLI runs against a server behind an ingress controller with TLS termination, and when is the `--grpc-web` flag required versus sufficient?
  **Target:** the Argo CD ingress configuration and gRPC-web proxy source

- Q11: How does `argocd app sync --force` interact with in-progress sync operations, live overrides, and `--self-heal`, and what state inconsistencies can it introduce?
  **Target:** the Argo CD sync executor and self-heal controller source

- Q12: When multiple agents invoke `argocd app create` or `argocd app sync` concurrently for the same application, how does Argo CD handle the conflict, and what error responses does the CLI surface?
  **Target:** the Argo CD application controller's sync conflict handling

## Testing

- Q13: What testing infrastructure exists in this codebase for validating agent skills, and what fixtures or mocking patterns are used for simulating CLI command output?
  **Target:** the `evals/` directory or any skill test harness in `scripts/`

## Observability

- Q14: Which `argocd` CLI subcommands or Argo CD API endpoints provide health status, sync status, and operation state for monitoring purposes, and what information is included in their output that an agent skill can surface?
  **Target:** the `argocd app get --verbose`, `argocd app history`, and health check source
