---
name: atmos
description: Operate Cloud Posse's atmos to manage Terraform/OpenTofu components across stacks. Use whenever the user works with atmos, an atmos.yaml, stack YAML under stacks/, catalog imports, vendoring components, multi-account/multi-region Terraform via Cloud Posse, name_pattern stacks, abstract/inherited components, or runs atmos terraform plan/apply/deploy, atmos vendor pull, atmos describe, or atmos workflow.
command: /atmos
argument-hint: <task, e.g. "plan the vpc component in plat-ue1-prod">
allowed-tools: Read, Edit, Write, Bash, Glob, Grep
---

# atmos

`atmos` (Cloud Posse) orchestrates Terraform/OpenTofu by separating reusable
**components** (the Terraform root modules) from **stacks** (the YAML that
configures a component for one place: an account + region + tier). One component
is deployed many times — once per stack — with different variables. Your job is
to help the user move a component through its lifecycle: target a stack →
vendor/create the component → configure it in stack YAML → plan → apply safely →
share its outputs with other components → debug when it breaks.

The hardest part of atmos for newcomers is that almost nothing lives where you
run the command. Variables come from a chain of imported YAML files, the backend
is generated, and the "stack" you name on the CLI is a *derived* identifier, not
a file path. Internalize the targeting model first; the rest follows.

## Orient before acting

Before changing anything, learn the shape of the repo. Read `atmos.yaml` (or
`.atmos/atmos.yaml`) at the repo root — it declares where components and stacks
live (`components.terraform.base_path`, `stacks.base_path`,
`stacks.included_paths`, `stacks.excluded_paths`) and, critically, the
`stacks.name_pattern` (or `stacks.name_template`) that defines how a stack is
named. Then run `atmos list stacks` and `atmos list components` to see what
actually exists rather than guessing from file names. Never assume the default
layout; every repo configures these paths.

## 1. Target a stack (the addressing model)

A **stack** is the deployable unit you name on every command. Its identifier is
*assembled* from hierarchy variables, most commonly:

- `namespace` — the org (e.g. `acme`)
- `tenant` — a grouping of accounts / business unit (e.g. `plat`, `core`)
- `environment` — usually a region abbreviation (e.g. `ue1` for us-east-1)
- `stage` — the account/tier (e.g. `dev`, `prod`)

`stacks.name_pattern` (e.g. `{tenant}-{environment}-{stage}`) determines the
string you pass as `-s`/`--stack`. So `-s plat-ue1-prod` means tenant=plat,
environment=ue1, stage=prod. If a repo omits `tenant` from its pattern, do not
include it. When a command fails with "stack not found", the cause is almost
always a mismatch between the identifier you typed and the `name_pattern` — run
`atmos list stacks` and copy an exact name.

These hierarchy variables are set in imported YAML (org → tenant → account →
region files), not redundantly on the CLI. The CLI only names the assembled
result. This is why the same component config can target dozens of stacks: you
change which files get imported, not the component.

For the full targeting model — how `name_pattern`/`name_template` tokens map to
vars, the org/tenant/account/region import hierarchy, and region mixins — read
`references/stack-yaml-schema.md`.

## 2. Vendor or create the component

A component is a Terraform root module under the components base path. Two ways
to get one:

- **Vendor** an existing community/shared module. `atmos vendor pull` copies
  remote source into your repo per a `vendor.yaml` (repo-wide manifest) or a
  per-component `component.yaml`. Pin a version so pulls are reproducible; a
  floating ref makes "it worked yesterday" bugs. Decide deliberately between
  committing vendored code (auditable, the common choice) and just-in-time
  pulling in CI (less repo noise, needs network at deploy time).
- **Create** a component by writing a normal Terraform module in its own
  directory under the components base path. It becomes addressable as soon as a
  stack references it by that directory name.

To customize a vendored component without forking it, prefer Terraform
**Overrides** (an `_override.tf` / `*.override.tf` file that Terraform merges
over the upstream `.tf`) so the next `vendor pull` doesn't clobber your edits.

For `vendor.yaml`/`component.yaml` syntax, mixins, version pinning with
`{{.Version}}`, override-vs-fork tradeoffs, and JIT-vs-commit vendoring, read
`references/vendoring.md`.

## 3. Configure the component in stack YAML

You make a component "real" in a place by declaring it under `components:` in a
stack file. Almost never write the whole config in one file — atmos's power is
**deep merge** across imports. The standard pattern:

- A **catalog** entry (e.g. `stacks/catalog/vpc.yaml`) holds the default,
  place-independent config for a component, often as an **abstract** base
  (`metadata.type: abstract` — defines settings but is never deployed itself).
- Concrete stacks `import:` the catalog entry and a chain of hierarchy files,
  then override only what differs (CIDR, instance size, flags) for that place.
- A concrete component can inherit from an abstract one via
  `metadata.inherits: [<base>]`, layering defaults then specifics.

Imports deep-merge in order — later imports and inline `vars` win over earlier
ones, map keys merge, and (by default) lists replace. So config is the *sum* of
the import chain, not any single file. When a variable's value surprises you,
the answer is the merge order, which `atmos describe component` will show you
resolved.

For the stack file keys (`import`, `vars`, `components`, `settings`, `env`,
`metadata`, `backend`), deep-merge and import-ordering rules, the catalog
pattern, and abstract/concrete inheritance, read
`references/stack-yaml-schema.md`.

## 4. Plan and apply — the two-stage safety pattern

atmos wraps Terraform but resolves all that merged config first, then generates
the varfile and backend before invoking Terraform. The commands you'll use most:

```bash
atmos terraform plan  <component> -s <stack>            # preview
atmos terraform apply <component> -s <stack>            # plan + prompt + apply
```

For anything that matters, **separate plan from apply** so the thing you review
is exactly the thing that runs:

```bash
atmos terraform plan  <component> -s <stack> --out=tfplan
atmos terraform apply <component> -s <stack> --from-plan   # applies the saved plan
```

This two-stage flow is the safe default in CI and for production changes — it
removes the gap where state or config drifts between an unreviewed plan and the
apply.

Be careful with `atmos terraform deploy`: it is plan **and** apply in one shot
and is commonly configured to auto-approve. It's convenient for low-stakes or
fully-gated pipelines, but for a human at a terminal touching prod, prefer the
explicit two-stage flow so nothing applies without a reviewed plan. Treat any
auto-approve path as a deliberate choice, not a default.

For the full command surface — `plan`/`apply`/`deploy`, `--from-plan`,
generating varfiles and backends, the auto-generated backend, `describe
component`/`describe stacks`, `validate`, and `providers` — read
`references/cli-reference.md`.

## 5. Share data between components (remote state)

Components rarely stand alone: the EKS component needs the VPC's subnet IDs. In
atmos you wire this with YAML functions inside a component's `vars`, so one
component reads another component's published values **for a specific stack**:

- `!terraform.output <component> <stack> <output>` — calls Terraform to read a
  live output value. Flexible (any output), but invokes Terraform at resolution
  time, so it's slower and needs the upstream applied.
- `!terraform.state <component> <stack> <output>` — reads the value straight
  from the upstream's state backend. Faster and avoids a Terraform invocation,
  but reads what's in state.

Under the hood this is the Cloud Posse `remote-state` module reading the
upstream component's backend. The choice is a tradeoff: `!terraform.output` for
correctness/flexibility, `!terraform.state` for speed in tight loops. Either way
you're explicitly naming the producing component **and its stack**, which keeps
cross-environment wiring honest (prod reads prod, not dev).

For the `remote-state` module, backend config that makes outputs readable, and
the precise semantics of the two functions, read
`references/stack-yaml-schema.md` and `references/cli-reference.md`.

## 6. Debug and troubleshoot

When something is wrong, **stop guessing and ask atmos what it resolved**. The
single most useful command is:

```bash
atmos describe component <component> -s <stack>
```

It prints the fully merged, post-import view of a component in a stack — final
`vars`, `settings`, `env`, `backend`, and the deps. Most "wrong value" or
"missing var" bugs are visible immediately here because you see the result of
the whole merge chain in one place. `atmos describe stacks` does the same across
all stacks.

Other go-tos:

- Set `ATMOS_LOGS_LEVEL=Debug` (or `Trace`) to see imports, merges, and the
  generated Terraform invocation.
- `atmos validate stacks` catches schema/config errors across the repo before
  you ever run Terraform; `atmos terraform validate` checks the Terraform itself.
- The classic failures: a `name_pattern` mismatch (the stack name you typed
  isn't what the pattern assembles — `list stacks` to confirm), an omitted
  `tenant` (or extra one) versus the pattern, and a vendored-component version
  mismatch (pin it).

For the debugging playbook — `describe component` as the primary tool,
`ATMOS_LOGS_LEVEL`, the common error catalog, and `validate stacks` vs
`terraform validate` — read `references/troubleshooting.md`.

## Automating multi-step sequences

When a task is a repeatable sequence (e.g. plan+apply a set of components in
order, or a bootstrap), atmos **workflows** capture it as YAML under a
`workflows/` directory: named workflows of ordered steps (each step an `atmos`
command or a `shell` command), optionally with a workflow-level default stack so
steps don't each repeat `-s`. Run one with:

```bash
atmos workflow <name> -f <file> [--dry-run] [--from-step <step>]
```

Reach for a workflow when you catch yourself documenting "run these five
commands in this order." Use `--dry-run` to preview and `--from-step` to resume
after a failure.

For workflow file structure, step types, the default-stack setting, and the run
flags, read `references/workflows.md`.

## Working method

1. Read `atmos.yaml` and run `atmos list stacks` / `list components` to orient.
2. Confirm the exact stack identifier against `name_pattern` before any command.
3. Inspect resolved config with `atmos describe component` before changing it.
4. For risky changes, plan to a file and apply `--from-plan`; avoid blind `deploy`.
5. When stuck, raise `ATMOS_LOGS_LEVEL` and re-read the merged view — don't guess.
