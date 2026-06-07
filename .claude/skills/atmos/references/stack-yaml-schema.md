# Stack YAML schema, merge model, and targeting

Reference for the structure of stack files, how atmos merges them, the catalog
pattern, abstract/concrete inheritance, the namespace/tenant/environment/stage
targeting model, `name_pattern`, region mixins, and remote-state wiring.

## Contents

- [Top-level keys](#top-level-keys)
- [Deep merge and import ordering](#deep-merge-and-import-ordering)
- [The catalog pattern](#the-catalog-pattern)
- [Abstract and concrete components](#abstract-and-concrete-components)
- [Targeting: namespace / tenant / environment / stage](#targeting)
- [name_pattern and name_template](#name_pattern-and-name_template)
- [Region and mixin imports](#region-and-mixin-imports)
- [Remote state: YAML functions and the module](#remote-state)

## Top-level keys

A stack file is YAML with these top-level keys (all optional; you use what you
need):

| Key | Purpose |
|-----|---------|
| `import` | List of other stack/catalog files to pull in (deep-merged in order). |
| `vars` | Global variables merged into every component in this stack. |
| `components` | Map of component instances; `components.terraform.<name>` holds per-component `vars`, `settings`, `env`, `backend`, `metadata`. |
| `settings` | Non-Terraform config consumed by atmos/integrations (e.g. `settings.spacelift`, validation). |
| `env` | Environment variables exported into the Terraform process (e.g. `AWS_PROFILE`, `TF_VAR_*`). |
| `metadata` | Component-level controls: `type` (`abstract`/`real`), `component` (path override), `inherits`, `enabled`. |
| `backend` / `backend_type` | Backend configuration; usually inherited from a base import so it's defined once. |

Example concrete component entry:

```yaml
import:
  - catalog/vpc                       # defaults for the vpc component
  - mixins/region/us-east-1           # region-specific values

vars:
  namespace: acme
  tenant: plat
  environment: ue1
  stage: prod

components:
  terraform:
    vpc:
      vars:
        cidr_block: 10.20.0.0/16
        availability_zones: ["us-east-1a", "us-east-1b", "us-east-1c"]
```

## Deep merge and import ordering

Imports are resolved and **deep-merged in list order**, then inline content in
the current file is merged on top. Rules:

- **Later wins.** A value in a later import overrides the same key from an
  earlier one; inline `vars` in the file override all imports.
- **Maps merge recursively.** Nested keys combine; you can set one nested field
  without restating siblings.
- **Lists replace by default.** A later list value replaces the earlier one
  rather than concatenating. (Some merge strategies are configurable in
  `atmos.yaml`'s `settings.list_merge_strategy`, but assume replace unless the
  repo says otherwise.)

The effective config for a component is the *sum* of its import chain plus inline
overrides. This is why `atmos describe component <c> -s <stack>` is the source of
truth — it shows the merged result so you never have to mentally replay the
chain.

## The catalog pattern

Keep component defaults in one reusable place and import them everywhere:

```
stacks/
  catalog/
    vpc.yaml          # default vpc config (often abstract)
    eks/
      cluster.yaml
  orgs/acme/plat/ue1/prod.yaml   # concrete: imports catalog + sets place vars
```

`catalog/vpc.yaml` holds place-independent defaults; each concrete stack imports
it and overrides only the deltas for that account/region. Changing a default in
the catalog propagates to every stack that imports it — the central reason atmos
scales to many environments without copy-paste.

## Abstract and concrete components

`metadata.type` controls whether a component is deployable:

```yaml
# catalog/vpc.yaml — a base that is never deployed directly
components:
  terraform:
    vpc/defaults:
      metadata:
        type: abstract
      vars:
        ipv6_enabled: true
        nat_gateway_enabled: true
```

```yaml
# concrete stack — inherits the abstract base, then specializes
components:
  terraform:
    vpc:
      metadata:
        component: vpc            # the Terraform dir to run
        inherits:
          - vpc/defaults          # layer abstract defaults first
      vars:
        cidr_block: 10.20.0.0/16
```

- `type: abstract` → defines config but atmos refuses to plan/apply it directly.
  Use it for shared baselines you never deploy on their own.
- `metadata.inherits: [...]` → layers the listed components' config in order
  (earlier first, later/inline last), giving multi-level inheritance.
- `metadata.component` → points a named instance at a specific Terraform
  directory, so you can deploy the same module under different instance names.

## Targeting

A stack identity is built from hierarchy variables. The common four:

| Var | Meaning | Example |
|-----|---------|---------|
| `namespace` | Organization / top-level prefix | `acme` |
| `tenant` | Business unit / account grouping (Cloud Posse "tenant") | `plat`, `core` |
| `environment` | Region (abbreviated) | `ue1` (us-east-1), `uw2` (us-west-2) |
| `stage` | Account / tier | `dev`, `staging`, `prod` |

These are ordinary `vars`, set along the import hierarchy:

```
orgs/<namespace>.yaml                 # namespace
orgs/<namespace>/<tenant>.yaml        # tenant
orgs/<namespace>/<tenant>/<stage>.yaml# stage / account
mixins/region/<region>.yaml           # environment + region settings
```

Some repos use a subset (no `tenant`) or extra dimensions; always match the
repo's actual `name_pattern`.

## name_pattern and name_template

`atmos.yaml` defines how the stack identifier (the `-s` value) is assembled:

```yaml
stacks:
  name_pattern: "{tenant}-{environment}-{stage}"
```

With this pattern, `-s plat-ue1-prod` resolves to tenant=plat, environment=ue1,
stage=prod. The tokens correspond exactly to the hierarchy `vars`. Rules of
thumb:

- The `-s` string must be what the pattern produces from the vars — not a file
  path. `atmos list stacks` prints the valid identifiers; copy from there.
- If the pattern omits `tenant`, do **not** put it in the identifier (and vice
  versa). A token/identifier mismatch is the #1 "stack not found" cause.
- `name_template` is the Go-template alternative to `name_pattern` for complex
  cases (e.g. `{{.vars.tenant}}-{{.vars.environment}}-{{.vars.stage}}`); only one
  is used per repo.

## Region and mixin imports

A **mixin** is a small reusable import — most often per-region settings shared
across stacks in that region:

```yaml
# mixins/region/us-east-1.yaml
vars:
  environment: ue1
  region: us-east-1
  availability_zones: ["us-east-1a", "us-east-1b", "us-east-1c"]
```

Concrete stacks import the region mixin plus the account file, so region facts
live in one place. Mixins are just stack files used purely for import — there's
no special key; the convention is the `mixins/` directory.

## Remote state

Cross-component data sharing is expressed as YAML functions in a consumer
component's `vars`, naming the producer component **and its stack**:

```yaml
components:
  terraform:
    eks:
      vars:
        # read the live output (invokes Terraform on the upstream)
        vpc_id: !terraform.output vpc {{ .stack }} vpc_id
        # or read straight from the upstream's state backend (faster)
        private_subnet_ids: !terraform.state vpc {{ .stack }} private_subnet_ids
```

- `!terraform.output <component> <stack> <output>` — runs Terraform against the
  upstream to fetch the named output. Always current, slower, requires the
  upstream applied.
- `!terraform.state <component> <stack> <output>` — reads the value from the
  upstream's state file via the backend. Faster, no Terraform call, reflects
  what's in state.

Both are implemented by the Cloud Posse `remote-state` Terraform module, which
configures a `terraform_remote_state` data source from the upstream component's
backend. For this to work the upstream's backend must be discoverable (usually
because both components inherit the same backend config from a base import). Name
the producer's stack explicitly so wiring stays within an environment (prod reads
prod). See `cli-reference.md` for the backend/varfile generation that makes these
reads resolve.
