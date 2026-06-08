# atmos CLI reference

The command surface you use day to day, with the flags that matter. Read this for the exact
plan/apply/deploy mechanics, generated varfile/backend behavior, the describe/validate
inspection commands, and the secondary helmfile path.

## Contents

- [Command shape](#command-shape)
- [`terraform plan` / `apply` / `deploy`](#terraform-plan--apply--deploy)
- [`--from-plan` and saved plans](#--from-plan-and-saved-plans)
- [Generated varfile and backend](#generated-varfile-and-backend)
- [`describe component` / `describe stacks`](#describe-component--describe-stacks)
- [`validate`](#validate)
- [Providers](#providers)
- [helmfile (secondary)](#helmfile-secondary)

## Command shape

Almost every atmos Terraform command is:

```sh
atmos terraform <subcommand> <component> -s <stack> [flags]
```

`<component>` is the component config name (the YAML key, which may differ from its source dir
via `metadata.component`); `<stack>` is the resolved stack name (see `stack-yaml-schema.md`).
Flags after the component are passed through to Terraform unless atmos owns them.

## `terraform plan` / `apply` / `deploy`

```sh
atmos terraform plan   vpc -s core-uw2-prod --out=vpc.planfile
atmos terraform apply  vpc -s core-uw2-prod --from-plan
atmos terraform deploy vpc -s core-uw2-prod                 # plan + apply + auto-approve
atmos terraform destroy vpc -s core-uw2-prod
atmos terraform output vpc -s core-uw2-prod
```

- **`plan`** generates the varfile + backend, runs `terraform init` if needed, and computes the
  change set. Write it to a file with `--out=<file>` whenever you intend to apply it.
- **`apply`** applies the change. With `--from-plan` it applies a saved plan file with no
  re-plan (the reviewed gate); without it, `apply` plans-then-applies and will prompt unless
  given `--auto-approve`.
- **`deploy`** is `plan` + `apply` with **auto-approval** in one step. Convenient for dev, but it
  skips the human review gate — avoid it where an unreviewed apply could cause an outage.
- Pass-through Terraform flags work: `--auto-approve`, `-target=...`, `-var=...`,
  `-refresh=false`, etc.

## `--from-plan` and saved plans

The two-stage pattern decouples *what was reviewed* from *what is applied*:

```sh
atmos terraform plan vpc -s core-uw2-prod --out=vpc.planfile   # review this
atmos terraform apply vpc -s core-uw2-prod --from-plan          # applies exactly that, no re-plan
```

`--from-plan` tells atmos to apply the previously generated plan file for that component+stack
rather than planning again. This guarantees the apply matches the review even if state drifted
in between — the core safety property for shared/production stacks.

## Generated varfile and backend

You do not hand-write `terraform.tfvars` or a `backend {}` block. On every run atmos:

1. Merges the stack YAML (imports + inheritance) for the target component.
2. Writes a generated varfile from the merged `vars`.
3. Writes a generated backend config from the merged `backend`/`backend_type`, deriving the
   state key from the component + stack coordinate.

```sh
atmos terraform generate varfiles vpc -s core-uw2-prod    # write the varfile without planning
atmos terraform generate backend  vpc -s core-uw2-prod    # write the backend config
```

This is why a component carries no environment-specific files and why the same component gets
isolated state per stack automatically. The backend config schema is in
`stack-yaml-schema.md`.

## `describe component` / `describe stacks`

```sh
atmos describe component vpc -s core-uw2-prod       # final merged config + generated vars/backend
atmos describe component vpc -s core-uw2-prod --format json
atmos describe stacks                                # all stacks and the components each defines
atmos describe stacks --components vpc               # filter to one component across stacks
atmos describe affected --stack core-uw2-prod        # components changed vs a git ref (CI use)
```

- `describe component` is the inspection workhorse — it shows the fully-merged `vars`,
  `settings`, `env`, `metadata`, and generated backend, so you see exactly what Terraform will
  receive *before* running it. JSON output (`--format json`, or `--query` to extract a path) is
  ideal for scripting and CI.
- `describe stacks` enumerates every stack and its components — the map of what exists.
- `describe affected` (CI) lists components changed relative to a git ref, to plan only what
  moved.

## `validate`

```sh
atmos validate stacks                                # schema, imports, name_pattern, inheritance
atmos validate component vpc -s core-uw2-prod         # validate one component's resolved config
```

`validate stacks` is the fast structural check: it catches malformed YAML, broken imports,
unresolvable `name_pattern`, and bad inheritance before you ever plan. Run it in CI and after
any stack refactor. (Terraform's own `terraform validate` checks the HCL — see
`troubleshooting.md` for combining them.)

## Providers

```sh
atmos terraform providers vpc -s core-uw2-prod        # show resolved providers for the component
```

Provider configuration is generated from the merged stack the same way vars and backend are; the
`providers` command shows what atmos resolved. Provider/version pinning still lives in the
component's Terraform (`required_providers`), vendored and pinned per `vendoring.md`.

## helmfile (secondary)

atmos can also orchestrate Helmfile-based components — a secondary path used where Kubernetes
releases are managed alongside Terraform components:

```sh
atmos helmfile diff  <component> -s <stack>
atmos helmfile apply <component> -s <stack>
```

Helmfile components are configured under `components.helmfile.<name>` in stack YAML (parallel to
`components.terraform.<name>`) and obey the same stack-targeting and merge rules. Most atmos work
is Terraform; reach for helmfile only when the component is a Helmfile release.

The repeatable sequencing of these commands is covered in `workflows.md`; when a command fails or
returns surprising config, work the playbook in `troubleshooting.md`.
