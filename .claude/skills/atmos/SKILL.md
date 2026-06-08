---
name: atmos
description: "Operate the Cloud Posse atmos CLI to manage Terraform/OpenTofu components across stacks — the multi-environment, catalog-driven, deep-merge way Cloud Posse infrastructure is run. Use whenever the user works with atmos, an `atmos.yaml`, a `stacks/` or `components/terraform/` layout, a stack name like `tenant-uw2-prod`, `stacks.name_pattern`, vendoring (`atmos vendor pull`, `vendor.yaml`, `component.yaml`), catalog imports / abstract components (`metadata.type: abstract`, `metadata.inherits`), `!terraform.output`/`!terraform.state` remote-state lookups, or runs Terraform through atmos (`atmos terraform plan/apply/deploy <component> -s <stack>`). Trigger on any of: 'plan/apply a component', 'vendor the vpc component', 'wire up remote state between components', 'why is my stack not resolving', 'set up an atmos catalog', 'atmos workflow', or any Cloud-Posse / atmos infra intent — even when the user names the component and stack but not the word 'atmos'."
command: /atmos
argument-hint: <what you want to do with atmos>
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Operating the atmos CLI

[atmos](https://atmos.tools) is Cloud Posse's orchestrator for Terraform/OpenTofu. It
separates **components** (reusable root modules under `components/terraform/<name>/`) from
**stacks** (YAML that configures a component for one place in your environment hierarchy).
You almost never run `terraform` directly under atmos — you run `atmos terraform <subcommand>
<component> -s <stack>`, and atmos generates the varfile, backend, and provider config from
the merged stack YAML before delegating to the binary.

**Why this skill exists:** atmos's power and its failure modes both come from one mechanism —
**deep-merged, imported YAML resolved per stack**. A change three imports away silently alters
what a component sees; a missing `name_pattern` field makes a stack name unresolvable; an
abstract component applied directly errors. The guidance below keeps you oriented in that
merge graph so every plan reflects what you intended, and routes the deep detail into focused
reference files you load on demand.

## Mental model: components, stacks, and the merge

- A **component** is a Terraform root module. atmos does not change how it's written; it
  decides *which* component runs *where* with *what inputs*.
- A **stack** is the fully-merged configuration for one (namespace, tenant, environment,
  stage) coordinate. You rarely write a whole stack by hand — you compose it from `import`s of
  catalog defaults plus a thin top-level file that sets the coordinate and overrides.
- The everyday command is `atmos terraform <plan|apply|deploy> <component> -s <stack>`. Inspect
  the resolved result first with `atmos describe component <component> -s <stack>` — this is the
  single most useful command in atmos and the antidote to "why did it use that value?"

The lifecycle below is the order you actually work in: target a stack → bring a component in →
configure it in the stack → plan/apply it → wire it to other components → debug when the merge
surprises you.

## 1. Stack-targeting model (the environment hierarchy)

atmos identifies a stack by a coordinate built from four context variables — `namespace`,
`tenant`, `environment`, `stage` — assembled into a stack *name* by `stacks.name_pattern` (or
the newer `name_template`) in `atmos.yaml`. A typical `name_pattern: "{tenant}-{environment}-{stage}"`
turns `tenant: core, environment: uw2, stage: prod` into the stack name `core-uw2-prod`, which
is what you pass to `-s`.

- `namespace` is usually the org; `tenant` an account group; `environment` a region alias
  (e.g. `uw2` for us-west-2); `stage` the lifecycle slot (`dev`/`staging`/`prod`).
- The `-s` value must match what `name_pattern` produces from the context vars set in the
  stack's YAML. A stack that omits `tenant` while `name_pattern` references `{tenant}` will not
  resolve — this is the most common first-run error.
- `atmos list stacks` enumerates every resolvable stack; if the one you expect is missing, the
  context vars or `name_pattern` are the place to look.

The full context-variable semantics, `name_pattern` vs `name_template`, region/account mixins,
and how the coordinate threads through imports are documented in
`references/stack-yaml-schema.md` — read it when a stack name won't resolve or you're designing
the hierarchy.

## 2. Vendor / create a component

Components are pulled into your repo (vendored) rather than referenced remotely, so every
`plan` runs against code you can review and pin. Bring a component in with:

```sh
atmos vendor pull --component vpc          # one component
atmos vendor pull                          # everything declared in vendor.yaml
```

- Repo-wide vendoring is declared in `vendor.yaml` (a list of `sources` with `source`,
  `targets`, and a pinned `version`); per-component vendoring lives in a `component.yaml`
  beside the component. Pin versions explicitly — an unpinned source re-vendors to a moving
  target and silently changes your infrastructure code.
- To author a brand-new component, create `components/terraform/<name>/` with ordinary
  Terraform (`main.tf`, `variables.tf`, `outputs.tf`); no varfile or backend block — atmos
  generates those from the stack at run time.

Vendoring detail — `vendor.yaml` vs `component.yaml` schemas, mixins, commit-vs-JIT vendoring,
adapting upstream with Terraform Overrides (`.override.tf`) instead of forking, and version
pinning with `{{.Version}}` templating — is in `references/vendoring.md`.

## 3. Configure a component in a stack (catalog + inheritance)

You configure a component by declaring it under `components.terraform.<name>.vars` in stack
YAML — but you rarely repeat that everywhere. The **catalog pattern** factors shared defaults
into `stacks/catalog/<component>.yaml` and each concrete stack `import`s it, overriding only
what differs. Deep-merge means a later import or a more specific file wins key-by-key, so the
concrete stack stays small.

- An **abstract** component (`metadata.type: abstract`) is a reusable base that is *never*
  applied directly — applying it errors by design. Concrete components set
  `metadata.inherits: [<abstract-name>]` to absorb its config and then specialize. This is how
  one "vpc-defaults" base feeds `vpc/dev`, `vpc/staging`, `vpc/prod`.
- `import:` ordering matters: imports are merged in listed order, later overriding earlier, and
  the file's own keys override all of its imports. When a value isn't what you expect, the
  cause is almost always import order or an inherited default.

The complete YAML schema (`import`, `vars`, `components`, `settings`, `env`, `metadata`,
`backend`), deep-merge and import-ordering rules, the catalog pattern, and abstract/concrete
inheritance are in `references/stack-yaml-schema.md` — the reference for everything about how a
stack's final shape is computed.

## 4. Two-stage plan / apply (and the deploy caution)

Run Terraform through atmos so the generated varfile and backend always match the stack:

```sh
atmos terraform plan vpc -s core-uw2-prod --out=vpc.planfile
atmos terraform apply vpc -s core-uw2-prod --from-plan
```

- The **two-stage** form — `plan --out=<file>` then `apply --from-plan` — applies *exactly*
  the reviewed change set rather than re-planning against state that may have drifted. Prefer it
  for anything shared or production, and read the plan for `destroy`/`replace` lines before
  applying.
- `atmos terraform deploy <component> -s <stack>` is a convenience that **plans and applies in
  one step with auto-approval**. It's fine for disposable dev stacks but skips the human review
  gate — do not use it where an unreviewed apply could cause an outage.

The full subcommand surface — `plan`/`apply`/`deploy`, `--from-plan`, varfile/backend
generation, the auto-generated backend, `describe`, `validate`, providers, and the secondary
helmfile path — is in `references/cli-reference.md`. For repeatable multi-component or
multi-stack sequences (e.g. "plan then apply vpc then eks across three stages"), atmos
**workflows** capture the steps as YAML; see `references/workflows.md`.

## 5. Cross-component data sharing (remote state)

Components consume each other's outputs through atmos's remote-state YAML functions in stack
vars, so you never hardcode an ID that another component owns:

```yaml
components:
  terraform:
    eks:
      vars:
        vpc_id: !terraform.output vpc vpc_id          # reads a live output of the vpc component
        subnet_ids: !terraform.output vpc private_subnet_ids
```

- `!terraform.output <component> [<stack>] <output>` runs the source component's outputs at
  plan time — always current, but requires that component to be applied and its outputs
  available.
- `!terraform.state <component> [<stack>] <output>` reads the value straight from the remote
  state file — cheaper and avoids an init/output cycle, but only as fresh as the last apply.
- Both resolve through Cloud Posse's `remote-state` module, which derives the source's backend
  from the same stack config, so the lookup needs no manually-copied backend keys.

When to choose `!terraform.output` vs `!terraform.state`, the `remote-state` module wiring, and
how the backend coordinate is derived are covered in `references/stack-yaml-schema.md`; the CLI
mechanics of the underlying read live in `references/cli-reference.md`.

## 6. Debugging (when the merge surprises you)

Almost every atmos confusion is "the merged config isn't what I thought." Resolve it by
inspecting the merge, not by guessing:

```sh
atmos describe component vpc -s core-uw2-prod      # the fully-merged config + generated vars/backend
atmos describe stacks                              # every stack and the components it defines
atmos validate stacks                              # catch schema / import / name_pattern errors early
ATMOS_LOGS_LEVEL=Trace atmos terraform plan vpc -s core-uw2-prod   # verbose merge/generation trace
```

- `atmos describe component` is the primary debugging tool — it shows the final `vars`,
  `settings`, `env`, and generated backend after all imports and inheritance, so you can see
  *exactly* what the component will receive.
- Common errors map to specific causes: an unresolvable stack name → missing `name_pattern`
  field or an omitted context var (often `tenant`); a value you didn't set → an inherited
  catalog default or import-order surprise; a vendoring mismatch → an unpinned or drifted
  version.

The full debugging playbook — `describe` recipes, `ATMOS_LOGS_LEVEL` levels, the catalogue of
common errors with fixes, and combining `validate stacks` with `terraform validate` — is in
`references/troubleshooting.md`.
