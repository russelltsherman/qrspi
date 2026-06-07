# Transformers: cross-cutting edits across all resources

Transformers apply a change to **every selected resource** at once, rather than patching a
single named resource. They are how you stamp an environment onto a base: a namespace, a
name prefix, an image tag, a set of labels.

## Usage matrix

| Transformer            | What it does                                              | Watch out for                                              |
| ---------------------- | -------------------------------------------------------- | --------------------------------------------------------- |
| `namespace`            | Sets `.metadata.namespace` on all namespaced resources   | Won't touch cluster-scoped kinds                          |
| `namePrefix` / `nameSuffix` | Prepends/appends to every resource name; rewrites refs | Long prefixes can exceed the 253-char name limit          |
| `labels`               | Adds labels; optionally also to selectors/templates      | Selector mutation is breaking — see caution below         |
| `annotations`          | Adds annotations to all resources                        | Safe; annotations are not selectors                       |
| `images`               | Overrides image name/tag/digest by image name            | Matches by original image `name`, not container name      |
| `replacements`         | Copies a field value from one resource into another      | Successor to removed `vars` — see migration below         |

## namespace, namePrefix, nameSuffix

```yaml
namespace: prod
namePrefix: prod-
nameSuffix: -v2
```

These rewrite references too: if a Deployment mounts `app-config`, `namePrefix: prod-`
updates both the ConfigMap's name and the Deployment's reference to it.

## images

The cleanest way to set per-environment image tags — no patch needed. Match by the image's
**name as it appears in the base**, then override tag and/or digest:

```yaml
images:
  - name: myorg/web          # the image reference in the base manifest
    newName: registry.internal/myorg/web   # optional: relocate the registry
    newTag: v1.4.2
  - name: myorg/worker
    digest: sha256:abc123...  # pin by digest instead of tag
```

## labels and the commonLabels caution

`labels:` adds key/value pairs to resources. The dangerous part is whether they also get
written into **selectors** and **pod template labels**.

The legacy `commonLabels` field added labels to selectors **by default**. Selectors on a
Deployment/Service are immutable in-cluster — so applying a new `commonLabels` to a running
workload makes the rendered selector differ from the live one, and the apply **fails** (or,
for a Service, silently stops routing). This has broken many rollouts.

Prefer the current `labels:` form with **explicit** selector control:

```yaml
# CURRENT — explicit, safe by default
labels:
  - pairs:
      team: platform
      env: prod
    includeSelectors: false      # add to metadata only; DO NOT touch selectors
  - pairs:
      app.kubernetes.io/part-of: storefront
    includeSelectors: true       # only when you deliberately want selector labels
                                 # — and only on first creation, never on a live workload
```

Rule of thumb: identity/selector labels are decided **once** in the base. Overlays add
descriptive labels with `includeSelectors: false`. Touch selectors only when creating a
resource for the first time.

```yaml
# LEGACY — recognize it, don't write it (mutates selectors by default)
commonLabels:
  team: platform
```

## replacements (and the vars → replacements migration)

`replacements` copy a value from a **source** resource's field into one or more **target**
fields. They are the typed, schema-aware successor to `vars`, which was removed because it
was untyped and resolved unpredictably.

```yaml
replacements:
  - source:
      kind: ConfigMap
      name: app-config
      fieldPath: data.HOSTNAME
    targets:
      - select:
          kind: Deployment
          name: web
        fieldPaths:
          - spec.template.spec.containers.[name=web].env.[name=HOST].value
      - select:
          kind: Ingress
        fieldPaths:
          - spec.rules.0.host
```

Migration mapping:

```yaml
# LEGACY — recognize it, don't write it
vars:
  - name: HOSTNAME
    objref: { kind: ConfigMap, name: app-config, apiVersion: v1 }
    fieldref: { fieldpath: data.HOSTNAME }
# referenced elsewhere as $(HOSTNAME)

# CURRENT — replacements (shown above): source.fieldPath → targets[].fieldPaths
```

Prefer `replacements` in all new work. `vars` no longer resolves in current Kustomize, so
legacy repos relying on it must be migrated to keep building — unlike the patch-field and
label deprecations, this one is a hard removal, not a soft warning.
