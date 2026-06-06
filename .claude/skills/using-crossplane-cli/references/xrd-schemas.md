# XRD schemas

`CompositeResourceDefinition` (XRD) templates for both Crossplane lines, scope
selection, `connectionSecretKeys`, and schema versioning/conversion. **The
v1-vs-v2 shape is the most common source of broken XRDs — establish the installed
version first** (`crossplane version`) and pick the matching template. Confirm
exact fields against <https://docs.crossplane.io>.

## Contents

- [v1: cluster-scoped XR + Claim](#v1-cluster-scoped-xr--claim)
- [v2: namespaced XR](#v2-namespaced-xr)
- [connectionSecretKeys](#connectionsecretkeys)
- [Versioning and conversion](#versioning-and-conversion)

## v1: cluster-scoped XR + Claim

Under Crossplane 1.x the composite (XR) is cluster-scoped and you usually expose a
namespaced **Claim** to consumers via `claimNames`.

```yaml
apiVersion: apiextensions.crossplane.io/v1
kind: CompositeResourceDefinition
metadata:
  name: xpostgresinstances.example.org
spec:
  group: example.org
  names:
    kind: XPostgresInstance      # cluster-scoped composite
    plural: xpostgresinstances
  claimNames:
    kind: PostgresInstance       # namespaced claim
    plural: postgresinstances
  versions:
    - name: v1alpha1
      served: true
      referenceable: true
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              properties:
                parameters:
                  type: object
                  properties:
                    storageGB: { type: integer }
                  required: [storageGB]
```

## v2: namespaced XR

Under Crossplane 2.x prefer a namespaced XR with `scope: Namespaced` and skip the
Claim — consumers create the XR directly in their namespace.

```yaml
apiVersion: apiextensions.crossplane.io/v2
kind: CompositeResourceDefinition
metadata:
  name: xpostgresinstances.example.org
spec:
  scope: Namespaced            # v2 first-class namespaced composite
  group: example.org
  names:
    kind: XPostgresInstance
    plural: xpostgresinstances
  versions:
    - name: v1alpha1
      served: true
      referenceable: true
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              properties:
                parameters:
                  type: object
                  properties:
                    storageGB: { type: integer }
                  required: [storageGB]
```

(The `apiVersion`/scope availability depends on the cluster; verify with
`crossplane version` and the docs for your release.)

## connectionSecretKeys

Declare which connection details the composite publishes so consumers get a
`Secret` with exactly those keys:

```yaml
spec:
  connectionSecretKeys:
    - host
    - port
    - username
    - password
```

The composition must populate these via `connectionDetails`
(see `composition-patterns.md`).

## Versioning and conversion

- Add a new entry under `versions` (e.g. `v1beta1`) when the schema evolves; keep
  the prior version `served` during migration.
- Exactly one version is `referenceable: true` — the one Compositions bind to.
- For breaking field changes, define a conversion strategy (webhook conversion)
  so stored objects upgrade cleanly. Avoid silently removing required fields.
