# Vendoring components

Reference for pulling external components into the repo: `atmos vendor pull`, the
`vendor.yaml` and per-component `component.yaml` manifests, mixins, the
commit-vs-just-in-time decision, customizing with Terraform Overrides instead of
forking, and version pinning.

## Why vendor

A component is a Terraform root module under the components base path. Rather than
copy-paste shared modules (e.g. Cloud Posse's `terraform-aws-components`), you
**vendor** them: declare the remote source and let atmos pull it into your repo
reproducibly. This keeps upstream code current via a controlled pull instead of
manual edits.

## `atmos vendor pull`

```bash
atmos vendor pull                       # pull everything in vendor.yaml
atmos vendor pull --component vpc        # pull one component (component.yaml)
atmos vendor pull -c vpc --dry-run       # show what would change
atmos vendor pull --tags networking      # pull only sources matching a tag
```

`atmos vendor pull` reads a manifest, fetches each source (git, OCI, http, local,
etc. via go-getter-style URIs), and writes files to the target paths. Run it
whenever you bump a pinned version or add a new component.

## `vendor.yaml` — repo-wide manifest

A single `vendor.yaml` (atmos manifest kind) lists many sources:

```yaml
apiVersion: atmos/v1
kind: AtmosVendorConfig
metadata:
  name: vendor-config
spec:
  sources:
    - component: "vpc"
      source: "github.com/cloudposse/terraform-aws-components.git//modules/vpc?ref={{.Version}}"
      version: "1.398.0"
      targets:
        - "components/terraform/vpc"
      included_paths:
        - "**/*.tf"
      excluded_paths:
        - "**/*.md"
      tags:
        - networking
```

- `source` is a go-getter URI; `{{.Version}}` is templated from `version` so one
  field controls the pinned ref.
- `targets` is where files land under the repo.
- `included_paths`/`excluded_paths` filter what gets copied (glob).
- `tags` let `--tags` pull a subset.

## `component.yaml` — per-component manifest

A component directory can carry its own `component.yaml`, pulled with
`atmos vendor pull -c <name>`:

```yaml
apiVersion: atmos/v1
kind: ComponentVendorConfig
metadata:
  name: vpc
spec:
  source:
    uri: "github.com/cloudposse/terraform-aws-components.git//modules/vpc?ref={{.Version}}"
    version: "1.398.0"
  mixins:
    - uri: "https://raw.githubusercontent.com/.../context.tf"
      filename: "context.tf"
```

Use `component.yaml` when a component owns its vendoring locally; use `vendor.yaml`
to manage many components centrally. Repos commonly pick one convention.

## Mixins

A vendoring **mixin** is an extra file merged into the component on pull (e.g. a
shared `context.tf` or `provider.tf`), listed under `spec.mixins`. It lets every
vendored component share boilerplate without that file living upstream. (Distinct
from *stack* mixins, which are reusable YAML imports — see `stack-yaml-schema.md`.)

## Commit vs just-in-time (JIT) vendoring

Two operating models:

- **Commit vendored code** (most common): run `vendor pull`, commit the result.
  The exact deployed code is auditable in git, diffs show upstream changes, and
  CI needs no network to fetch components. Cost: more files in the repo and
  pull/commit churn on version bumps.
- **JIT pull in CI**: don't commit vendored code; run `vendor pull` as a pipeline
  step before plan/apply. Keeps the repo lean but requires network at deploy time
  and means the deployed code isn't directly visible in git history.

Default to committing unless the repo has a deliberate JIT pipeline — auditability
usually wins for infrastructure.

## Customize without forking: Terraform Overrides

To change a vendored component's behavior without editing (and later losing) its
files, use Terraform's native **override** mechanism: add an `_override.tf` or
`*.override.tf` file in the component directory. Terraform merges override files
over the base `.tf`, so you can replace a resource argument, provider block, or
default. Because override files aren't part of the upstream source, the next
`vendor pull` won't clobber them.

Prefer overrides over forking the upstream module: forking strands you from
upstream fixes, while an override file is a small, reviewable delta layered on top
of a still-current vendored module. Fork only when the change is too deep for an
override.

## Version pinning

Always pin. The `version` field feeds `{{.Version}}` in the source URI, so the
pulled ref is deterministic:

```yaml
version: "1.398.0"   # -> ?ref=1.398.0 in the source URI
```

A floating ref (`main`, `latest`) makes pulls non-reproducible and produces
"worked yesterday, broken today" failures that are hard to trace. Bump the pinned
version intentionally, re-run `vendor pull`, review the diff, and commit. A
version mismatch between what's pinned and what's deployed is a common source of
plan surprises — see `troubleshooting.md`.
