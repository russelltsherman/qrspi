# Composition patterns

Pipeline-mode Compositions, `function-patch-and-transform`, `EnvironmentConfig`,
and offline validation with `crossplane render`. Field names track the installed
Crossplane version — confirm against <https://docs.crossplane.io> for your
release.

## Contents

- [Pipeline-mode Composition](#pipeline-mode-composition)
- [function-patch-and-transform](#function-patch-and-transform)
- [EnvironmentConfig](#environmentconfig)
- [Validating with crossplane render](#validating-with-crossplane-render)

## Pipeline-mode Composition

Prefer `mode: Pipeline` (the standard path in v2 and available in later v1). A
pipeline is an ordered list of function steps; each step receives the desired
state so far and returns an updated desired state.

```yaml
apiVersion: apiextensions.crossplane.io/v1
kind: Composition
metadata:
  name: xpostgres
spec:
  compositeTypeRef:
    apiVersion: example.org/v1alpha1
    kind: XPostgresInstance
  mode: Pipeline
  pipeline:
    - step: patch-and-transform
      functionRef:
        name: function-patch-and-transform
      input:
        apiVersion: pt.fn.crossplane.io/v1beta1
        kind: Resources
        resources:
          - name: rds
            base:
              apiVersion: rds.aws.upbound.io/v1beta1
              kind: Instance
              spec:
                forProvider:
                  engine: postgres
            patches:
              - type: FromCompositeFieldPath
                fromFieldPath: spec.parameters.storageGB
                toFieldPath: spec.forProvider.allocatedStorage
```

Order matters: later steps see earlier steps' output. Keep each step focused.

## function-patch-and-transform

The workhorse function for declaratively building managed resources and copying
values between the composite and the managed resources.

- **Patch types:** `FromCompositeFieldPath` (XR → MR), `ToCompositeFieldPath`
  (MR → XR status), `CombineFromComposite` (merge several fields), and
  `PatchSet`s for reuse across resources.
- **Transforms:** `map`, `match`, `string` (fmt/regex), `math`, and
  `convert` adjust a value in flight.
- Surface connection details back to the XR with `connectionDetails` so
  `connectionSecretKeys` on the XRD can publish them.

## EnvironmentConfig

`EnvironmentConfig` holds shared values (region, tags, account IDs) that a
pipeline merges into its environment, so compositions stay free of per-XR
hardcoding.

```yaml
apiVersion: apiextensions.crossplane.io/v1beta1
kind: EnvironmentConfig
metadata:
  name: platform-defaults
data:
  region: us-east-1
```

Select it in the pipeline (via the environment-config function or the
composition's `environment` selector, per your version) and patch from
`fromFieldPath: ` paths rooted at the merged environment.

## Validating with crossplane render

Validate a Composition **before applying** — no cluster needed:

```bash
crossplane render xr.yaml composition.yaml functions.yaml
```

It runs the real function pipeline offline and prints the managed resources that
would be created. Wire it into CI / pre-merge checks to catch broken patches and
schema drift early. See `cli-reference.md` for `render` invocation details.
