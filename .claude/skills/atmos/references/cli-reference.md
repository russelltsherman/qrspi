# CLI reference

Reference for the atmos command surface used across the lifecycle: terraform
plan/apply/deploy and the two-stage `--from-plan` flow, generating varfiles and
backends, the auto-generated backend, `describe component`/`describe stacks`,
`validate`, `providers`, and helmfile (secondary).

## Mental model

`atmos terraform <subcommand> <component> -s <stack>` does three things: resolve
the merged stack config for that component, **generate** the Terraform inputs
(varfile + backend) from it, then invoke Terraform with them in the component's
directory. Almost every Terraform subcommand is available this way.

## Plan, apply, deploy

```bash
atmos terraform plan   <component> -s <stack>
atmos terraform apply  <component> -s <stack>
atmos terraform deploy <component> -s <stack>
atmos terraform destroy <component> -s <stack>
atmos terraform output  <component> -s <stack>
```

- `plan` — preview changes; writes no state.
- `apply` — plans, prompts for approval, then applies. Pass-through Terraform
  flags (e.g. `-auto-approve`, `-target=...`) come after the atmos args.
- `deploy` — **plan and apply in one step**, frequently configured to
  auto-approve (via `settings.terraform.command` or `--auto-approve`). Convenient
  for gated pipelines; risky at a human terminal because nothing pauses for
  review. Prefer the two-stage flow below for production.
- `destroy` — tears the component down for that stack; treat as destructive.

## Two-stage plan/apply with `--from-plan`

The safe production pattern — review exactly what will run:

```bash
atmos terraform plan  <component> -s <stack> --out=tfplan
# review tfplan / the plan output
atmos terraform apply <component> -s <stack> --from-plan
```

`--out=<file>` saves the binary plan; `--from-plan` applies that saved plan
instead of re-planning. This closes the window where state or config could drift
between an unreviewed plan and the apply. Use it in CI and for any change to a
sensitive stack.

## Generating varfiles and backends

atmos materializes the merged config into files Terraform consumes:

```bash
atmos terraform generate varfile <component> -s <stack>   # write the tfvars json
atmos terraform generate backend <component> -s <stack>   # write backend config
atmos terraform generate planfile <component> -s <stack>
```

- `generate varfile` emits the resolved `vars` as a `.tfvars.json` — useful to
  inspect exactly what Terraform will receive, or to run Terraform directly.
- `generate backend` emits the backend block.

### Auto-generated backend

By default atmos **auto-generates the backend configuration** for each component
from the stack's `backend`/`backend_type` config at plan/apply time, so you don't
hand-write `backend.tf` per component. The backend (e.g. S3 + DynamoDB, or
`backend_type: s3`) is defined once in a base import and inherited. Because the
backend is derived from stack config, it's also what makes remote-state reads
(`!terraform.output` / `!terraform.state`) able to locate an upstream component's
state — see `stack-yaml-schema.md`.

## Describe (inspection — your primary debug tool)

```bash
atmos describe component <component> -s <stack>   # merged config for one component
atmos describe stacks                             # merged view across all stacks
atmos describe stacks --components vpc             # filter
atmos describe affected --ref main                 # components changed vs a ref
atmos describe dependents <component> -s <stack>   # what depends on this
```

`describe component` prints the fully merged `vars`, `settings`, `env`, `backend`,
and `metadata` after all imports — the single best way to answer "what value will
this actually get?" `describe affected` powers CI to plan only what changed.

## Validate

```bash
atmos validate stacks                             # schema/config validation, repo-wide
atmos validate component <component> -s <stack>    # validate one component's config
atmos terraform validate <component> -s <stack>    # Terraform's own validate
```

`validate stacks` catches malformed YAML, bad imports, and schema violations
before any Terraform runs — cheap to run early and often.

## Providers and lock

```bash
atmos terraform providers <component> -s <stack>
atmos terraform init <component> -s <stack>
```

`providers` shows the provider tree (and version constraints) Terraform resolves
for the component — useful when a provider version conflict appears.

## Helmfile (secondary)

atmos also wraps Helmfile for Kubernetes release management, mirroring the
terraform surface:

```bash
atmos helmfile diff  <component> -s <stack>
atmos helmfile apply <component> -s <stack>
atmos helmfile sync  <component> -s <stack>
```

It's the same stack-config model applied to Helmfile components. Most atmos work
is Terraform/OpenTofu; reach for helmfile only when the repo manages Helm
releases through atmos.
