# CronWorkflows and Resource Management

## CronWorkflow Commands

```bash
argo cron create <file.yaml> -n ns          # Create
argo cron lint <file.yaml> -n ns            # Validate
argo cron list -n ns                        # List all
argo cron get <name> -n ns                  # Get details
argo cron suspend <name> -n ns              # Pause
argo cron resume <name> -n ns               # Unpause
argo cron delete <name> -n ns               # Remove
```

## CronWorkflow Configuration

- **Schedule**: standard cron syntax. Example: `0 2 * * *` (daily 2 AM in workflow timezone).
- **Concurrency policy**: `Allow` (default), `Forbid` (skip if running), `Replace` (cancel previous).
- **Timezone**: `spec.timezone` overrides server default (e.g., `America/New_York`).
- **History limits**: `successfulHistoryLimit` and `failedHistoryLimit` (default 3 each) — older runs garbage collected.

## Resource Management

- **Container resources**: always set both `requests` and `limits` for cpu and memory.
- **Workflow parallelism**: `spec.parallelism` caps total concurrent template execution.
- **Synchronization**: mutex-based (via `spec.synchronization.workflowSet` or `workflowTemplate`) prevents concurrent conflicts on shared resources.

## Artifact Configuration

- Pass data between templates: `inputs.artifacts` / `outputs.artifacts` with `from: "{{tasks.X.outputs.artifacts.name}}"`.
- **Storage**: emptyDir (same-node, volatile), S3/GCS (persistent, cross-node).
- **GC strategy**: `OnWorkflowCompletion` (default), `OnWorkflowDeletion`, `Never`.
