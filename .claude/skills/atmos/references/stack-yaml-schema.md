# Stack YAML schema, deep-merge, inheritance, and remote state

This is the deep reference for how an atmos stack's final configuration is computed. Read it
when a stack name won't resolve, a value isn't what you expect, you're designing the
environment hierarchy, or you're wiring components together with remote state.

## Contents

- [Top-level keys](#top-level-keys)
- [The four context variables and `name_pattern`](#the-four-context-variables-and-name_pattern)
- [Deep-merge and import ordering](#deep-merge-and-import-ordering)
- [The catalog pattern](#the-catalog-pattern)
- [Abstract vs concrete components (inheritance)](#abstract-vs-concrete-components-inheritance)
- [Region and account mixins](#region-and-account-mixins)
- [The `backend` block](#the-backend-block)
- [Remote-state YAML functions and the `remote-state` module](#remote-state-yaml-functions-and-the-remote-state-module)

## Top-level keys

A stack file (anything under `stacks/`) is YAML with these meaningful top-level keys. All are
optional; what matters is the *merged* result across every import.

| Key | Purpose |
|-----|---------|
| `import` | List of other stack/catalog files to merge **before** this file's own keys. |
| `vars` | Global context + variables inherited by every component in the stack (this is where `namespace`/`tenant`/`environment`/`stage` live). |
| `components` | Per-component config, keyed `components.terraform.<name>` (or `components.helmfile.<name>`). |
| `settings` | atmos-level behavior (validation, dependencies, integrations) — *not* passed to Terraform as vars. |
| `env` | Environment variables exported into the Terraform process (e.g. `AWS_PROFILE`). |
| `metadata` | Per-component component metadata: `type`, `inherits`, `component` (which source dir to use). Lives under a component, not at the top level. |
| `backend` / `backend_type` | Backend configuration merged into the generated backend (see below). |

A component block has the shape:

```yaml
components:
  terraform:
    vpc:
      metadata:
        type: real            # or "abstract"
        component: vpc        # source dir under components/terraform/ (defaults to the key)
        inherits: [vpc-defaults]
      vars:
        cidr_block: 10.0.0.0/16
      settings: {}
      env: {}
      backend: {}
```

## The four context variables and `name_pattern`

The stack's identity comes from four context vars, normally set in `vars` and inherited down:

- `namespace` — top-level org identifier (e.g. `acme`).
- `tenant` — account/OU grouping (e.g. `core`, `plat`). Optional in some layouts; **required if
  `name_pattern` references `{tenant}`**.
- `environment` — usually a region alias (`uw2` = us-west-2, `ue1` = us-east-1).
- `stage` — lifecycle slot (`dev`, `staging`, `prod`, `sandbox`).

`atmos.yaml` assembles these into a stack name with **either**:

```yaml
stacks:
  name_pattern: "{tenant}-{environment}-{stage}"   # classic token substitution
  # or, more flexible Go-template form:
  name_template: "{{.vars.tenant}}-{{.vars.environment}}-{{.vars.stage}}"
```

The produced name is what you pass to `-s`. With `name_pattern: "{tenant}-{environment}-{stage}"`
and `tenant: core, environment: uw2, stage: prod`, the stack is `core-uw2-prod`.

**Resolution failures** almost always trace to: (a) a context var referenced by the pattern but
unset in the stack (commonly `tenant`), or (b) a `-s` value that doesn't match the pattern's
output. `atmos list stacks` prints every resolvable name — diff it against what you expect.

## Deep-merge and import ordering

atmos merges maps **deeply** and resolves them in a deterministic order. Understanding this
order is the key to predicting any final value.

1. Files in `import:` are merged **in listed order** — a later import overrides an earlier one
   key-by-key.
2. The importing file's **own keys override all of its imports**.
3. Merging is recursive for maps; **lists are replaced wholesale, not concatenated** (so an
   overriding file's list for a key fully replaces the inherited list).
4. Component inheritance (`metadata.inherits`) layers on top of the above — see the next
   section.

```yaml
# stacks/catalog/vpc.yaml  (imported first)
components: { terraform: { vpc: { vars: { cidr_block: 10.0.0.0/16, nat_gateway_enabled: true } } } }

# stacks/orgs/acme/core/uw2/prod.yaml  (the concrete stack)
import:
  - catalog/vpc
components:
  terraform:
    vpc:
      vars:
        cidr_block: 10.20.0.0/16     # overrides the catalog default
        # nat_gateway_enabled: true  inherited unchanged from the catalog
```

When a value surprises you, walk the import list top-to-bottom, then apply the file's own keys
last — `atmos describe component <name> -s <stack>` shows the end result so you don't have to do
it by hand.

## The catalog pattern

The catalog is the convention that keeps concrete stacks small: put each component's shared
defaults in `stacks/catalog/<component>.yaml`, then `import` it everywhere the component is used.

```
stacks/
  catalog/
    vpc.yaml              # shared vpc defaults (abstract base, often)
    eks.yaml
  orgs/acme/core/uw2/
    dev.yaml              # import: [catalog/vpc, catalog/eks] + overrides
    prod.yaml
```

- Import paths are relative to the configured `stacks.base_path` and are written **without** the
  `.yaml` extension (`catalog/vpc`).
- A catalog file commonly defines an **abstract** component (next section) so it can never be
  applied on its own and exists purely as a base to inherit.

## Abstract vs concrete components (inheritance)

`metadata.type` controls whether a component can be deployed:

- `type: real` (default) — a normal, deployable component.
- `type: abstract` — a base that is **never deployed directly**; `atmos terraform plan/apply` on
  an abstract component errors by design. It exists only to be inherited.

Concrete components pull in a base with `metadata.inherits`:

```yaml
# catalog/vpc.yaml
components:
  terraform:
    vpc/defaults:
      metadata: { type: abstract, component: vpc }   # 'component' points at components/terraform/vpc
      vars: { nat_gateway_enabled: true, max_subnet_count: 3 }

# prod.yaml
components:
  terraform:
    vpc:
      metadata: { inherits: [vpc/defaults] }         # absorbs the abstract base's vars
      vars: { cidr_block: 10.20.0.0/16 }             # then specializes
```

- `inherits` is a list and is applied in order (later entries win), then the component's own
  `vars` override the inherited result — same precedence logic as imports.
- `metadata.component` decouples the **config name** (the YAML key, e.g. `vpc/defaults`) from the
  **source directory** (`components/terraform/vpc`), so many configs can share one root module.

## Region and account mixins

Mixins are small reusable stack fragments imported to inject a slice of context — commonly a
region or account map — instead of repeating it in every stack:

```yaml
# stacks/mixins/region/us-west-2.yaml
vars:
  environment: uw2
  region: us-west-2

# stacks/orgs/acme/core/uw2/prod.yaml
import:
  - mixins/region/us-west-2     # sets environment + region for this whole stack
  - catalog/vpc
vars:
  tenant: core
  stage: prod
```

Mixins are ordinary stack files; they obey the same import-ordering and deep-merge rules. They
keep the region/account coordinate defined once and imported everywhere it applies.

## The `backend` block

You do **not** write a Terraform `backend {}` block in the component. atmos generates the
backend at run time from the merged stack `backend`/`backend_type` config, so the same component
gets a different state key per stack automatically.

```yaml
terraform:
  backend_type: s3
  backend:
    s3:
      bucket: acme-core-uw2-tfstate
      dynamodb_table: acme-core-uw2-tflock
      region: us-west-2
      # atmos derives the state key from the component + stack coordinate
```

This is why moving a component between stacks is safe: the backend key follows the stack, not the
code. The generated backend file is what `atmos describe component` shows under the backend
section, and the CLI mechanics are in `cli-reference.md`.

## Remote-state YAML functions and the `remote-state` module

To consume another component's outputs, use the remote-state YAML functions directly in `vars`:

```yaml
components:
  terraform:
    eks:
      vars:
        vpc_id:      !terraform.output vpc vpc_id              # same stack implied
        subnet_ids:  !terraform.output vpc private_subnet_ids
        peer_cidr:   !terraform.output vpc core-uw2-net cidr   # explicit source stack
        kms_key:     !terraform.state kms-key prod arn         # read from state file instead
```

- `!terraform.output <component> [<stack>] <output>` evaluates the **live outputs** of the source
  component at plan time. Always current; requires the source to be applied and `terraform
  output` to succeed (it triggers an init/output of the source).
- `!terraform.state <component> [<stack>] <output>` reads the value **straight from the remote
  state file**. Cheaper (no init/output cycle) but only as fresh as the source's last apply. Use
  it for stable values or when the source's outputs aren't cheaply runnable.
- Omitting the `<stack>` argument means "the same stack as the consumer." Provide it explicitly
  for cross-stack references (e.g. an app stack reading a shared networking stack).

Both functions resolve through Cloud Posse's **`remote-state`** Terraform module, which derives
the source component's backend from the same stack configuration — so you never copy backend
bucket/key values by hand. If you need the source's backend to be discoverable, ensure both
components share the backend config in their merged stacks (which the catalog usually provides).

Choosing between `output` and `state`, and the lower-level read mechanics, are summarized in
`cli-reference.md`; debugging a remote-state lookup that returns nothing is in
`troubleshooting.md`.
