# Troubleshooting

Reference for debugging atmos: `atmos describe component` as the primary tool,
`ATMOS_LOGS_LEVEL`, the catalog of common errors and their fixes, and
`validate stacks` vs `terraform validate`.

## First move: describe the merged config

When anything is wrong, **don't replay the import chain in your head — ask atmos
what it resolved**:

```bash
atmos describe component <component> -s <stack>
```

This prints the fully merged, post-import view: final `vars`, `settings`, `env`,
`backend`, and `metadata`. The vast majority of bugs ("wrong CIDR", "missing
var", "deploying to the wrong account") are visible immediately because you see
the *result* of the whole merge in one place rather than guessing which import
won. Make this your reflex before changing any file.

`atmos describe stacks` gives the same merged view across every stack — useful
when the question is "which stacks even include this component?"

## Turn up logging

```bash
ATMOS_LOGS_LEVEL=Debug atmos terraform plan vpc -s plat-ue1-prod
ATMOS_LOGS_LEVEL=Trace atmos describe component vpc -s plat-ue1-prod
```

`ATMOS_LOGS_LEVEL` accepts `Info` (default), `Debug`, and `Trace`. `Debug` shows
which files were imported and the merge sequence; `Trace` adds the generated
Terraform invocation and the resolved varfile/backend paths. When the merged
config looks right but Terraform still misbehaves, `Trace` reveals exactly what
atmos handed to Terraform.

## Common errors and fixes

### "Stack not found" / wrong stack
The `-s` identifier you typed doesn't match what `name_pattern` assembles. This
is the single most common failure.
- Run `atmos list stacks` and copy an exact identifier.
- Check `stacks.name_pattern` in `atmos.yaml` and confirm the token order matches
  your string (e.g. `{tenant}-{environment}-{stage}` → `plat-ue1-prod`).

### `tenant` omitted (or extra)
If the pattern includes `tenant` but your identifier or vars omit it (or vice
versa), the stack won't resolve.
- Make the identifier and the hierarchy `vars` agree with the pattern exactly.
- A repo without a `tenant` dimension must not have `tenant` in the pattern or the
  `-s` string.

### "Component not found" / "abstract component cannot be provisioned"
- The component name must match a directory under the components base path (and a
  `components.terraform.<name>` entry). Run `atmos list components`.
- If it's `metadata.type: abstract`, atmos refuses to plan/apply it directly —
  deploy a concrete component that `inherits` it instead (see
  `stack-yaml-schema.md`).

### Vendored-component version mismatch
A floating or stale pinned ref produces plan diffs you didn't expect.
- Pin `version` in `vendor.yaml`/`component.yaml`, re-run `atmos vendor pull`,
  review the diff, commit (see `vendoring.md`).
- Confirm the deployed files match the pinned version (git diff after a pull).

### Surprising variable value
A value you didn't set, or set differently, is coming from the import chain.
- `atmos describe component <c> -s <stack>` shows the winning value; trace it back
  through the imports (remember: later imports and inline `vars` win, maps merge,
  lists replace).

### Remote-state read fails / empty output
A `!terraform.output`/`!terraform.state` lookup can't find the upstream.
- The upstream component must be applied (for `!terraform.output`) and its backend
  discoverable — usually both components must inherit the same backend config.
- Confirm you named the upstream's **stack** correctly (prod consumer must read
  the prod producer). See `stack-yaml-schema.md`.

## validate stacks vs terraform validate

Two different layers — run both when diagnosing:

- `atmos validate stacks` — validates the **atmos config**: YAML well-formedness,
  resolvable imports, schema correctness across the repo. Run it first and often;
  it catches config mistakes before Terraform ever starts.
- `atmos terraform validate <component> -s <stack>` — runs **Terraform's own**
  `validate` on the resolved component: checks the HCL and variable types. Use it
  when the stack config is fine but Terraform rejects the module.

A clean `validate stacks` plus a clean `terraform validate` rules out both the
atmos layer and the Terraform layer, leaving provider/state/runtime issues, which
`ATMOS_LOGS_LEVEL=Trace` and `describe component` will surface.
