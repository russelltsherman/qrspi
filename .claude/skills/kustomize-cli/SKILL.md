---
name: kustomize-cli
description: "Author and operate Kustomize overlays (the kustomize CLI / kubectl -k) for Kubernetes and GitOps repos. Use when working with kustomization.yaml, base/overlay/component layouts, strategic-merge or JSON-6902 patches, configMapGenerator/secretGenerator, transformers (labels, namespace, images, replacements), or kustomize build / kubectl apply -k pipelines. Trigger on any variant of: 'add an overlay', 'write a kustomization', 'patch this resource per environment', 'generate a configmap from a file', 'set the image tag for staging', 'wire kustomize into Argo CD / Flux', 'validate my overlays in CI', or any request to structure, render, or troubleshoot Kustomize output — even if the user never says the word 'kustomize' but is clearly editing kustomization.yaml or running kubectl -k."
command: /kustomize-cli
argument-hint: <what you want to do with kustomize>
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Kustomize CLI

Kustomize composes Kubernetes manifests declaratively: you keep a **base** of plain,
environment-agnostic YAML and layer **overlays** on top that patch, generate, and
transform it per environment. No templating language, no string interpolation — every
input and output is valid Kubernetes YAML. That property is the whole point: a reviewer
can read the base, read the overlay, and predict the result without running a renderer.

Use this skill whenever you are creating or editing a `kustomization.yaml`, deciding how
to express a per-environment difference, or wiring `kustomize build` into a CI or GitOps
pipeline.

## Scope and mental model

- **Prefer composition over duplication.** If two environments differ, express the
  difference as a patch or transformer in the overlay — do not fork the base.
- **The base must build on its own.** A base is a deployable, valid set of manifests with
  sensible defaults. Overlays only adjust; they never supply mandatory missing pieces.
- **Keep the rendered output predictable.** Avoid constructs that change a resource's
  identity (name, namespace, labels used as selectors) unless you understand the blast
  radius — see the `commonLabels` caution in `references/transformers.md`.
- **One concern per overlay.** Environment overlays (`dev`, `staging`, `prod`) and
  cross-cutting feature overlays should not be tangled together; lift shared cross-cutting
  pieces into a **component** instead.

## Directory layout

A typical base/overlay/component repo renders to this shape. Overlays reference the base
(or other overlays) via `resources:`; components are opted into via `components:`.

```
k8s/
├── base/
│   ├── kustomization.yaml        # resources: deployment.yaml, service.yaml
│   ├── deployment.yaml
│   └── service.yaml
├── components/
│   └── monitoring/
│       ├── kustomization.yaml    # apiVersion: .../v1alpha1, kind: Component
│       └── servicemonitor.yaml
└── overlays/
    ├── staging/
    │   ├── kustomization.yaml    # resources: ../../base; components: ../../components/monitoring
    │   └── replica-patch.yaml
    └── prod/
        ├── kustomization.yaml    # resources: ../../base
        └── replica-patch.yaml
```

You render a specific environment by pointing the CLI at its overlay directory:

```sh
kustomize build k8s/overlays/prod
# or, equivalently, via kubectl's built-in kustomize:
kubectl kustomize k8s/overlays/prod
```

## Resource types — pick the right tool

Each construct below has a short orientation here and a deeper reference file. Read the
reference when you need the decision framework, full field list, or deprecation details.

### Patches

Patches modify resources pulled in from a base. There are two flavors — **strategic-merge**
(YAML that looks like the resource, merged field-by-field) and **JSON 6902** (an explicit
list of `op`/`path` operations). Choosing the wrong one is the most common Kustomize
mistake, especially for list/array edits.

→ Decision framework and the `patchesStrategicMerge` / `patchesJson6902` → `patches:`
deprecation: see `references/patch-selection.md`.

```yaml
# overlays/prod/kustomization.yaml
patches:
  - path: replica-patch.yaml          # strategic-merge by file
  - target: { kind: Deployment, name: web }
    patch: |                          # inline JSON-6902
      - op: replace
        path: /spec/replicas
        value: 5
```

### Generators

`configMapGenerator` and `secretGenerator` build ConfigMaps/Secrets from literals, files,
or `.env` files, and append a content hash to the name so rollouts trigger on change. Use
`behavior:` to merge or replace a generator inherited from the base.

→ Patterns, `behavior:`/`generatorOptions`, and `.env` + committed `.env.example` secret
handling (no committed secret values): see `references/generators.md`.

```yaml
configMapGenerator:
  - name: app-config
    envs: [config.env]
secretGenerator:
  - name: app-secrets
    envs: [.env]          # .env is gitignored; commit .env.example as the template
```

### Transformers

Transformers apply cross-cutting changes to every selected resource: `namespace`,
`namePrefix`/`nameSuffix`, `labels`, `annotations`, `images`, and `replacements`.

→ Usage matrix, the `commonLabels`-breaks-selectors caution, and the `vars` →
`replacements` deprecation: see `references/transformers.md`.

```yaml
namespace: prod
namePrefix: prod-
images:
  - name: myorg/web
    newTag: v1.4.2
labels:
  - pairs: { team: platform }
    includeSelectors: false   # safe: does not touch selectors
```

### Components

A **component** (`kind: Component`, `apiVersion: kustomize.config.k8s.io/v1alpha1`) is a
reusable, opt-in bundle of resources/patches/generators that multiple overlays can pull in
via `components:`. Use it when the same cross-cutting capability (monitoring, a sidecar, an
ingress class) is shared by several environments — it avoids duplicating the same patch in
every overlay.

```yaml
# overlays/staging/kustomization.yaml
resources:
  - ../../base
components:
  - ../../components/monitoring
```

### Replacements

`replacements` copy a value from one resource's field into another's — the supported,
schema-aware successor to the removed `vars`. Use them to keep a value defined once (e.g. a
hostname in a ConfigMap) and propagate it into a Deployment env var or an Ingress host.

→ Full source/target syntax and the `vars` → `replacements` migration: see
`references/transformers.md`.

## Deprecations — prefer current, recognize legacy

You will encounter older repos. Recognize the legacy form, but write the current one. Do
not rewrite a working legacy repo wholesale just to modernize syntax unless asked — the
goal is not to break legacy repos, only to stop emitting deprecated constructs in new work.

| Legacy construct                              | Current construct        | Why it changed                                              |
| --------------------------------------------- | ------------------------ | ---------------------------------------------------------- |
| `vars`                                        | `replacements`           | `vars` was unschema'd and removed; `replacements` is typed |
| `patchesStrategicMerge`                       | `patches:` (with `path`) | Single unified patch list; auto-detects merge vs 6902      |
| `patchesJson6902`                             | `patches:` (with `target`) | Same unified list; target selects the resource           |
| `commonLabels` (mutates selectors by default) | `labels:` with `includeSelectors:` | Default selector mutation silently broke rollouts |
| `bases:`                                       | `resources:`             | Bases and resources merged into one list                   |

## Building, applying, and GitOps integration

Render and apply directly with kubectl's embedded kustomize:

```sh
kubectl apply -k k8s/overlays/prod        # build + apply in one step
```

For GitOps, **render then pipe** so the rendered YAML is the reviewable artifact, and let
the GitOps controller own the cluster state:

```sh
kustomize build k8s/overlays/prod | kubectl apply -f -
```

- **Argo CD** recognizes a directory containing `kustomization.yaml` as a Kustomize
  Application automatically; point the Application `source.path` at the overlay directory.
  Per-environment image tags and the like belong in the overlay, not in Argo parameters,
  so the Git state stays the single source of truth.
- **Flux** uses a `Kustomization` (kustomize-controller) resource whose `path` points at
  the overlay directory; it runs the equivalent of `kustomize build` and applies the
  result on its sync interval.

Validate every overlay in CI before it merges — render each overlay and schema-check the
output. → `kustomize build` per overlay, `kubeconform`/`conftest`/OPA, and the
verbatim-error-on-failure reporting norm: see `references/ci-validation.md`.

## Quick checklist when authoring an overlay

1. Does the **base build cleanly** on its own (`kustomize build base`)?
2. Is each per-environment difference the **smallest possible patch/transformer**, not a copy?
3. For list edits, did you pick **strategic-merge vs JSON-6902** deliberately (see reference)?
4. Are generated Secrets sourced from a **gitignored `.env`** with a committed `.env.example`?
5. Did you avoid **selector-mutating** label transforms unless intended?
6. Does the overlay **render and validate** in CI?
