# Troubleshooting atmos

Most atmos confusion is "the merged configuration isn't what I thought." The fix is almost
always to **inspect the merge**, not to guess. Read this when a stack won't resolve, a value is
wrong, a remote-state lookup is empty, or a plan fails in a way Terraform's error doesn't
explain.

## Contents

- [First move: `describe component`](#first-move-describe-component)
- [`ATMOS_LOGS_LEVEL`](#atmos_logs_level)
- [`validate stacks` and `terraform validate`](#validate-stacks-and-terraform-validate)
- [Common errors and their causes](#common-errors-and-their-causes)

## First move: `describe component`

Before anything else, look at what the component actually resolves to:

```sh
atmos describe component <component> -s <stack>
atmos describe component <component> -s <stack> --format json
```

This prints the fully-merged `vars`, `settings`, `env`, `metadata`, and the generated backend —
i.e. exactly what Terraform will receive after every import and inheritance layer. If the value
you see here is wrong, the problem is in the stack YAML / merge, not in Terraform. If the value
here is *right* but the apply still misbehaves, the problem is downstream in the component's HCL
or the cloud — switch to `terraform validate` / the provider error.

## `ATMOS_LOGS_LEVEL`

Turn up logging to see how atmos resolves imports, generates files, and shells out:

```sh
ATMOS_LOGS_LEVEL=Trace atmos terraform plan vpc -s core-uw2-prod
```

Levels, increasing verbosity: `Off` → `Error` → `Warning` → `Info` (default) → `Debug` →
`Trace`. `Trace` shows the import resolution order, the generated varfile/backend paths, and the
exact Terraform invocation — invaluable when a value's origin is unclear or a stack name won't
resolve. Set it as an env var (above) or via `logs.level` in `atmos.yaml`.

## `validate stacks` and `terraform validate`

These check different layers — run both, in this order:

```sh
atmos validate stacks                       # 1. atmos layer: YAML schema, imports, name_pattern, inheritance
atmos terraform validate vpc -s core-uw2-prod   # 2. Terraform layer: HCL correctness for the resolved config
```

1. **`atmos validate stacks`** catches structural problems in the stack graph — malformed YAML,
   a broken `import`, an unresolvable `name_pattern`, a bad `metadata.inherits`. Run it first and
   in CI; it's fast and catches the atmos-specific failures Terraform can't see.
2. **`terraform validate`** (via atmos) checks the component's HCL is internally consistent for
   the merged inputs. It runs against the generated varfile, so it only makes sense *after* the
   stack resolves.

If `validate stacks` fails, fix the YAML before touching Terraform — a HCL error on top of a
broken merge is a red herring.

## Common errors and their causes

| Symptom | Most likely cause | Fix |
|---------|-------------------|-----|
| `stack name ... not found` / stack won't resolve | A context var referenced by `name_pattern` is unset (commonly `tenant`), **or** the `-s` value doesn't match `name_pattern`'s output. | `atmos list stacks` to see real names; set the missing context var or correct `-s`. See `stack-yaml-schema.md`. |
| `missing name_pattern` / no stacks resolve at all | `stacks.name_pattern` (or `name_template`) is absent or malformed in `atmos.yaml`. | Define `name_pattern` with the tokens your stacks actually set. |
| A `var` has a value you never set | Inherited from a catalog default or an abstract base, or overridden by import order. | `atmos describe component` to see the source; adjust the catalog/import or override the key in the concrete stack. |
| `atmos terraform plan` on a component errors that it can't be deployed | The component is `metadata.type: abstract` — abstract components are never applied directly. | Plan/apply a **concrete** component that `inherits` it instead. |
| `!terraform.output` returns null / lookup fails | The source component isn't applied yet, its outputs aren't available, or the wrong source stack was given. | Apply the source first (or use `!terraform.state` for a stable value); pass the explicit source `<stack>`. See `stack-yaml-schema.md`. |
| Remote-state lookup can't find the backend | Source and consumer don't share the backend config, so `remote-state` can't derive the source's state key. | Ensure both components' merged stacks carry the same backend config (usually via a shared catalog import). |
| Vendored code changed unexpectedly / version mismatch | Unpinned or drifted `version` in `vendor.yaml`/`component.yaml`. | Pin `version` explicitly, re-`atmos vendor pull`, review the diff, commit. See `vendoring.md`. |
| Local edits to a vendored component vanished | `atmos vendor pull` overwrites vendored files. | Don't edit vendored files — use a Terraform Override (`*_override.tf`). See `vendoring.md`. |
| A workflow stops partway and re-running redoes everything | You re-ran the whole workflow instead of resuming. | Fix the cause, re-run with `--from-step <name>`. See `workflows.md`. |

When the merge-level inspection clears the component but the apply still fails, the issue is in
the component's Terraform or the cloud provider — at that point it's an ordinary Terraform
problem, and the command surface for re-running plan/apply is in `cli-reference.md`.
