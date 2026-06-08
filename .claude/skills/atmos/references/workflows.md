# atmos workflows

Workflows capture a repeatable sequence of atmos (and shell) commands as YAML so a multi-step,
multi-component, or multi-stack operation runs the same way every time. Read this when you find
yourself running the same ordered set of `atmos terraform` commands by hand.

## Contents

- [Where workflows live](#where-workflows-live)
- [Workflow file structure](#workflow-file-structure)
- [Step types: `atmos` vs `shell`](#step-types-atmos-vs-shell)
- [Workflow-level default stack](#workflow-level-default-stack)
- [Running a workflow](#running-a-workflow)
- [`--dry-run` and `--from-step`](#--dry-run-and---from-step)

## Where workflows live

Workflow files live under the `workflows/` base path configured in `atmos.yaml`
(`workflows.base_path`, commonly `stacks/workflows/` or a top-level `workflows/`). Each file can
hold multiple named workflows.

```yaml
# atmos.yaml (excerpt)
workflows:
  base_path: stacks/workflows
```

## Workflow file structure

A workflow file is keyed by `workflows.<name>`, and each workflow is an ordered list of `steps`:

```yaml
# stacks/workflows/networking.yaml
workflows:
  plan-network:
    description: Plan vpc then transit-gateway for a stack
    steps:
      - command: terraform plan vpc
      - command: terraform plan tgw
  deploy-network:
    description: Apply vpc then transit-gateway
    steps:
      - command: terraform apply vpc --auto-approve
      - command: terraform apply tgw --auto-approve
```

- `description` is shown by `atmos list workflows` / `atmos describe workflows`.
- `steps` run **in order, top to bottom**; a failing step stops the workflow.
- A step's `command` is the atmos command **without** the leading `atmos` (e.g. `terraform plan
  vpc`).
- Each step may carry an optional `name` so you can resume from it with `--from-step`.

## Step types: `atmos` vs `shell`

Each step has a `type` (default `atmos`):

```yaml
steps:
  - name: plan-vpc
    command: terraform plan vpc          # type: atmos (default) — an atmos subcommand
  - name: notify
    type: shell                          # an arbitrary shell command
    command: echo "vpc planned for ${stack}"
```

- `type: atmos` (default) runs the command as an atmos subcommand — the leading `atmos` is
  implied.
- `type: shell` runs an arbitrary shell command, useful for notifications, `git` calls, or
  invoking other tools between atmos steps.

## Workflow-level default stack

Rather than repeat `-s <stack>` on every step, set the stack once for the whole workflow with
`stack:` (or pass `--stack` at invocation). Steps then inherit it.

```yaml
workflows:
  deploy-network:
    stack: core-uw2-prod            # default stack for every step below
    steps:
      - command: terraform apply vpc --auto-approve
      - command: terraform apply tgw --auto-approve
```

Invocation `--stack` overrides the file's `stack:`; an individual step can still pass its own
`-s` to target a different stack for that step.

## Running a workflow

```sh
atmos workflow deploy-network -f networking          # run workflow 'deploy-network' from networking.yaml
atmos workflow deploy-network -f networking --stack core-uw2-prod
atmos list workflows                                  # enumerate available workflows
```

- `-f <file>` names the workflow file **without** the `.yaml` extension, resolved under
  `workflows.base_path`.
- The positional argument is the workflow **name** (a key under `workflows:` in that file).

## `--dry-run` and `--from-step`

- `--dry-run` prints the steps that *would* run, in order, without executing them — use it to
  confirm a destructive workflow does what you think before committing.
- `--from-step <name>` resumes a workflow at the named step, skipping everything before it. This
  is how you recover from a mid-workflow failure: fix the cause, then re-run with `--from-step`
  at the step that failed instead of redoing the successful earlier steps.

```sh
atmos workflow deploy-network -f networking --dry-run
atmos workflow deploy-network -f networking --from-step apply-tgw
```

The individual commands a workflow strings together (`terraform plan/apply/deploy`, `describe`,
`validate`) are documented in `cli-reference.md`; when a step fails, debug the underlying command
with the playbook in `troubleshooting.md`.
