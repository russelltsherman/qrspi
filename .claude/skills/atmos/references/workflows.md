# Workflows

Reference for atmos workflows: the `workflows/` YAML files, step types
(`atmos` vs `shell`), the workflow-level default stack, and running them with
`atmos workflow <name> -f <file>` plus `--dry-run` and `--from-step`.

## What a workflow is

A workflow is a named, ordered sequence of steps stored as YAML. Reach for one
whenever a task is "run these commands in this order" — bootstrapping an account,
planning then applying a set of components, or a teardown sequence. Capturing it
as a workflow makes the sequence repeatable, reviewable, and resumable instead of
living in a runbook or someone's shell history.

## File structure

Workflow files live under the `workflows` base path (configured in `atmos.yaml`
as `workflows.base_path`, commonly `stacks/workflows/` or `workflows/`). One file
can define multiple named workflows:

```yaml
# workflows/network.yaml
workflows:
  deploy-network:
    description: "Plan and apply core networking for a stack"
    stack: plat-ue1-prod          # workflow-level default stack
    steps:
      - command: terraform plan vpc
        name: plan-vpc
      - command: terraform apply vpc --from-plan
        name: apply-vpc
      - command: terraform apply dns
      - type: shell
        command: echo "network deployed"
        name: notify
```

Key fields:

| Field | Purpose |
|-------|---------|
| `workflows.<name>` | The workflow's name (what you pass on the CLI). |
| `description` | Human summary. |
| `stack` | Workflow-level default stack, so steps don't each repeat `-s`. |
| `steps` | Ordered list of steps, run top to bottom. |
| `steps[].command` | The command to run (an atmos subcommand, or a shell line). |
| `steps[].type` | `atmos` (default) or `shell`. |
| `steps[].name` | Optional label, used by `--from-step`. |
| `steps[].stack` | Per-step stack override of the workflow default. |

## Step types

- **`atmos` steps** (the default `type`): the `command` is an atmos subcommand
  *without* the leading `atmos` — e.g. `terraform plan vpc`. atmos runs it with
  the resolved stack. These are the backbone of most workflows.
- **`shell` steps** (`type: shell`): the `command` runs as an arbitrary shell
  command. Use for glue — notifications, fetching a token, calling another tool —
  that isn't an atmos subcommand.

## The default stack

Setting `stack:` at the workflow level lets every `atmos` step inherit it, so you
write `terraform plan vpc` instead of `terraform plan vpc -s plat-ue1-prod` on
each line. A step can still override with its own `stack:` when one step targets a
different place. This keeps multi-component, single-stack sequences clean.

## Running a workflow

```bash
atmos workflow <name> -f <file>                 # run all steps in order
atmos workflow deploy-network -f network        # -f resolves under workflows base_path
atmos workflow deploy-network -f network --dry-run
atmos workflow deploy-network -f network --from-step apply-vpc
atmos workflow deploy-network -f network -s plat-uw2-prod   # override default stack
```

- `-f <file>` selects the workflow file (by name under the workflows base path,
  or a path). Required because names are scoped per file.
- `--dry-run` prints what each step would do without executing — always preview a
  destructive workflow this way first.
- `--from-step <name>` resumes at a named step, skipping earlier ones. Essential
  after a mid-workflow failure: fix the cause, then resume rather than re-running
  already-applied steps.
- `-s <stack>` overrides the workflow's default stack for the whole run.

## When to use a workflow vs a slice of commands

Use a workflow when the sequence is stable and rerun often, or when ordering and
resumability matter (apply A before B). For a one-off exploratory set of
commands, just run them directly — don't prematurely encode throwaway steps. The
signal to create a workflow is catching yourself documenting an ordered command
list for others to repeat.
