# Vendoring components with atmos

Vendoring pulls component source into your repo so every plan runs against code you can review
and pin. Read this when bringing a component in, declaring repo-wide vendoring, pinning
versions, or adapting an upstream component without forking it.

## Contents

- [`atmos vendor pull`](#atmos-vendor-pull)
- [Repo-wide vendoring: `vendor.yaml`](#repo-wide-vendoring-vendoryaml)
- [Per-component vendoring: `component.yaml`](#per-component-vendoring-componentyaml)
- [Mixins](#mixins)
- [Commit-the-vendored-code vs just-in-time vendoring](#commit-the-vendored-code-vs-just-in-time-vendoring)
- [Adapting upstream: Terraform Overrides vs forking](#adapting-upstream-terraform-overrides-vs-forking)
- [Version pinning and `{{.Version}}` templating](#version-pinning-and-version-templating)

## `atmos vendor pull`

```sh
atmos vendor pull                       # pull everything declared in vendor.yaml
atmos vendor pull --component vpc        # pull a single component
atmos vendor pull --tags networking      # pull only sources carrying a tag
atmos vendor pull --dry-run              # show what would change without writing
```

`vendor pull` fetches each declared source and writes it into the target path(s). It overwrites
the vendored files, so local edits to vendored code are lost on the next pull — adapt with
Overrides instead (below).

## Repo-wide vendoring: `vendor.yaml`

A single `vendor.yaml` at the repo root declares every component to vendor. It is the
recommended layout for a real infra repo.

```yaml
apiVersion: atmos/v1
kind: AtmosVendorConfig
metadata:
  name: vendor-config
spec:
  sources:
    - component: vpc
      source: github.com/cloudposse/terraform-aws-components.git//modules/vpc?ref={{.Version}}
      version: 1.520.0
      targets:
        - components/terraform/vpc
      included_paths: ["**/*.tf", "**/*.md"]
      excluded_paths: ["**/test/**"]
      tags: [networking]
    - component: eks/cluster
      source: github.com/cloudposse/terraform-aws-components.git//modules/eks/cluster?ref={{.Version}}
      version: 1.520.0
      targets:
        - components/terraform/eks/cluster
```

- `source` is a go-getter URL; the `//path` selects a subdirectory and `?ref=` selects the
  git ref. `{{.Version}}` is templated from the `version` field (see pinning below).
- `targets` is where the files land under `components/terraform/`.
- `included_paths`/`excluded_paths` are globs that filter what gets written.
- `tags` let you vendor subsets with `--tags`.

## Per-component vendoring: `component.yaml`

Alternatively, place a `component.yaml` *inside* a component directory to vendor just that one.
Useful for components owned/updated independently.

```yaml
# components/terraform/vpc/component.yaml
apiVersion: atmos/v1
kind: ComponentVendorConfig
metadata:
  name: vpc
spec:
  source:
    uri: github.com/cloudposse/terraform-aws-components.git//modules/vpc?ref={{.Version}}
    version: 1.520.0
  mixins:
    - uri: https://raw.githubusercontent.com/cloudposse/terraform-aws-components/{{.Version}}/modules/vpc/context.tf
      filename: context.tf
```

`atmos vendor pull --component vpc` reads this file and writes the component in place.

## Mixins

Mixins (in `component.yaml.spec.mixins`) pull individual files alongside the main source — the
canonical example is Cloud Posse's `context.tf`, the standard null-label context block shared by
every Cloud Posse component. They are fetched as named files into the component directory and
keep boilerplate identical across components without copy-paste.

## Commit-the-vendored-code vs just-in-time vendoring

Two operating models:

- **Commit the vendored code (recommended).** Run `atmos vendor pull`, then commit the resulting
  `components/terraform/**` into git. Plans are reproducible, code is reviewable in PRs, and CI
  needs no network to vendor. The cost is a larger repo and explicit re-vendor commits on
  upgrade.
- **Just-in-time (JIT) vendoring.** Run `atmos vendor pull` in CI before plan/apply and keep
  vendored code gitignored. Smaller repo, but plans depend on the source being reachable at run
  time and the exact bytes aren't captured in your history — so pin versions hard if you do this.

Pick one per repo and be consistent; mixing them makes "what code actually ran" ambiguous.

## Adapting upstream: Terraform Overrides vs forking

When an upstream component is *almost* right, do **not** edit vendored files (the next pull
overwrites them) and avoid forking (you inherit maintenance forever).

- **Terraform Overrides (`*_override.tf` / `.override.tf`).** Terraform natively merges
  `*_override.tf` files over same-named blocks in the directory. Add an override file in the
  vendored component dir (or via a mixin) to change a resource argument, provider, or default
  without touching the upstream `.tf`. Survives re-vendoring because it's a *separate* file. Use
  sparingly — overrides are invisible unless you know to look for them, so comment why.
- **Forking** is the last resort: only when the change is large or structural. You then own
  updates and lose easy upstream version bumps.

Prefer Overrides for small deltas; fork only when an Override can't express the change.

## Version pinning and `{{.Version}}` templating

Unpinned vendoring is how infrastructure code silently changes under you. Always pin:

- Set `version:` (or `spec.source.version`) to an explicit upstream tag (e.g. `1.520.0`).
- Reference it in the `source`/`uri` with the `{{.Version}}` template token — atmos substitutes
  the `version` value, so the tag is declared once and used in the URL and any mixin URIs.
- Bump deliberately: change `version`, run `atmos vendor pull`, review the diff, and commit it as
  its own reviewable change (same discipline as a provider lockfile bump).

The result of pulling vendored components is configured per stack via the schema in
`stack-yaml-schema.md`; if a pull produces unexpected bytes or a version mismatch shows up at
plan time, see `troubleshooting.md`.
