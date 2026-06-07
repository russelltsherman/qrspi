---
name: using-crossplane-cli
description: Guidance for the Crossplane CLI and control-plane resources — provider lifecycle, Pipeline-mode Compositions, XRDs/claims, managed resources, xpkg packaging, and render/trace. Use whenever the user works with Crossplane: installing providers, authoring Compositions or XRDs, building or validating packages with `crossplane xpkg`, running `crossplane render`, or debugging stuck or non-Ready managed resources — even if they don't name the CLI.
command: /using-crossplane-cli
allowed-tools: Bash, Read, Edit, Write, Grep, Glob
---

# Using the Crossplane CLI

Crossplane turns a Kubernetes cluster into a control plane: you declare
infrastructure as Kubernetes resources and Crossplane reconciles it against real
cloud APIs. This skill orients you across the everyday surface — installing
providers, composing APIs, packaging them, and debugging when reconciliation
stalls. The body stays lean on purpose; each section ends with a pointer to a
`references/` file that carries the full command syntax and templates. Read a
reference file only when you actually need that depth.

## Version awareness (do this first)

Crossplane's authoring model changed between major lines, so **establish the
installed version before writing or editing any XRD, Composition, or claim** —
the right shape depends on it. Check with `crossplane version` (or
`kubectl get deployment crossplane -n crossplane-system -o jsonpath='{.spec.template.spec.containers[0].image}'`).

Apply this branching rule throughout:

- **if v1** (Crossplane 1.x): XRDs are cluster-scoped by default and you typically
  pair each composite (XR) with a namespaced **Claim** (`claimNames` in the XRD).
  Composition `mode: Pipeline` is available in later 1.x but legacy
  `resources`-array compositions still exist in older clusters.
- **otherwise v2** (Crossplane 2.x): namespaced XRs are first-class
  (`scope: Namespaced` on the XRD), Claims are de-emphasized in favor of
  namespaced composites, and `mode: Pipeline` with composition functions is the
  standard authoring path.

**Default to v2 idioms unless the installed version indicates v1.** When you can't
determine the version, say so and ask rather than guessing — a v1/v2 mismatch
produces resources the API server silently rejects or the controller ignores.

## Provider lifecycle

Providers are packages that teach Crossplane about an external API (AWS, GCP,
Azure, etc.). Install one as a `Provider` object, wait for it to become
`Installed` and `Healthy`, then supply credentials through a `ProviderConfig`
that references a Kubernetes `Secret`. Upgrades are a change to the package tag;
Crossplane runs a new revision and cuts over once healthy. Watch
`provider.pkg.crossplane.io` and `providerrevision` objects to see rollout state.

→ Provider install/upgrade commands, `ProviderConfig` wiring, and credential
patterns: `references/cli-reference.md`.

## Compositions

A `Composition` maps one composite resource (XR) to the set of managed resources
that realize it. Prefer **Pipeline mode** (`mode: Pipeline`): an ordered list of
function steps, most commonly `function-patch-and-transform`, that build and patch
the managed resources. `EnvironmentConfig` lets a pipeline pull shared values
(region, tags, account IDs) into the composition without hardcoding them per XR.

→ Pipeline-mode structure, `function-patch-and-transform` patch syntax,
`EnvironmentConfig` usage, and offline `crossplane render` validation:
`references/composition-patterns.md`.

## XRDs, composites, and claims

A `CompositeResourceDefinition` (XRD) defines the schema and API surface your
users consume — it generates the XR (and, under v1, the Claim) CRDs. Decide
scope per the version rule above, declare `connectionSecretKeys` for any
credentials the composite should expose, and version the XRD's schema with a
conversion strategy when the API evolves.

→ XRD schema templates, v1 cluster-scoped + Claim vs v2 `scope: Namespaced`
shapes, `connectionSecretKeys`, and versioning/conversion:
`references/xrd-schemas.md`.

## Managed resources

A managed resource is the controller's representation of one external object. Its
`status.conditions` are the source of truth for health — chiefly `Synced` (the
spec reconciled cleanly with the provider) and `Ready` (the external resource
reached its desired state). `Synced=False` points at config or credential
problems; `Ready=False` with `Synced=True` usually means the external API is
still working or rejected the request downstream.

→ Condition semantics and inspection commands: `references/troubleshooting.md`.

## Packaging with xpkg

Bundle Configurations and Functions into OCI images with the `crossplane xpkg`
family: `build` a package from your manifests, `login` to a registry, `push` the
image, and `validate` it before shipping. Treat published package tags as
immutable releases so cluster upgrades are a deliberate tag bump.

→ Full `crossplane xpkg build/push/login/validate` command and flag reference:
`references/cli-reference.md`.

## Troubleshooting escalation

When something is stuck, escalate in a fixed order so you move from the widest
view to the narrowest detail and stop as soon as the cause is clear:

**`trace → describe → events → logs`**

1. **`crossplane trace`** — the whole composite tree and each resource's
   condition at a glance; find which resource is unhealthy.
2. **`kubectl describe`** the offending resource — read its `conditions` and the
   human-readable status messages.
3. **`kubectl get events`** (or `describe`'s Events section) — recent reconcile
   errors, often with the provider's exact rejection reason.
4. **provider/controller `logs`** — only when the first three don't explain it;
   the deepest and noisiest signal.

→ The full decision tree, condition checks (`ReconcileError`, `Ready`, `Synced`,
`Responsive`), and `crossplane xpkg validate` for package-level faults:
`references/troubleshooting.md`.

## kubectl and GitOps

Everything Crossplane manages is a Kubernetes object, so the normal `kubectl`
verbs apply — `apply`, `get`, `describe`, `delete` — and the whole control plane
fits a GitOps model: commit XRDs, Compositions, claims, and `ProviderConfig`s and
let Argo CD or Flux apply them. Keep credentials out of Git; deliver `Secret`s
through your secret manager and reference them from `ProviderConfig`.

→ kubectl inspection idioms and `crossplane render` for pre-merge validation:
`references/composition-patterns.md`.

## Environment configuration

The CLI reads connection and auth settings from your environment: `KUBECONFIG`
selects the target cluster/context, and registry auth for `xpkg push/pull` comes
from `crossplane xpkg login` (or a Docker credential store). Confirm you are
pointed at the intended cluster before applying anything.

→ Environment variables, registry auth, and context selection:
`references/cli-reference.md`.

## Canonical sources

CLI flags and API field specifications change between releases. This skill
captures stable idioms and escalation order; for exact, current flag names and
field schemas defer to the **official Crossplane documentation**
(<https://docs.crossplane.io>) rather than trusting inlined detail that can drift.
