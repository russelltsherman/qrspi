# CI validation for Kustomize overlays

Because Kustomize output is deterministic, the highest-value CI gate is simply: **render
every overlay and schema-check the result before it merges**. A broken patch path, a
missing resource, or a typo'd field surfaces at `kustomize build` time — long before it
reaches a cluster.

## 1. Build every overlay

The first gate is that each overlay renders at all. Walk every directory that contains a
`kustomization.yaml` under your overlays root and build it:

```sh
set -euo pipefail
for overlay in k8s/overlays/*/; do
  echo "== building $overlay =="
  kustomize build "$overlay" >/dev/null
done
```

A non-zero exit from `kustomize build` means a structural error (bad patch target, missing
file, invalid field). That alone catches the majority of overlay regressions.

## 2. Schema-validate the rendered manifests (kubeconform)

`kustomize build` checks that the *kustomization* is valid; it does **not** check that the
resulting Kubernetes objects are schema-valid. Pipe the output into `kubeconform` (the
maintained successor to `kubeval`) to validate against the Kubernetes OpenAPI schemas:

```sh
for overlay in k8s/overlays/*/; do
  kustomize build "$overlay" \
    | kubeconform -strict -summary -ignore-missing-schemas
done
```

- `-strict` rejects unknown fields (catches typos like `replcias`).
- `-ignore-missing-schemas` skips CRDs that have no published schema (otherwise supply
  `-schema-location` pointing at your CRD schemas).

## 3. Policy checks (conftest / OPA)

For organizational rules beyond schema validity — "every Deployment must set resource
limits", "no `:latest` image tags", "must carry an owner label" — run the rendered output
through `conftest` (which uses Open Policy Agent's Rego) or OPA directly:

```sh
for overlay in k8s/overlays/*/; do
  kustomize build "$overlay" | conftest test -p policy/ -
done
```

Keep policies in a `policy/` directory of `.rego` files. Render-then-check is the right
order: you validate exactly what will be applied, including all transformer/generator
output, not the pre-rendered base.

## 4. Failure reporting — print the exact command and full stderr, then stop

Follow the repo's error-surfacing doctrine. When any step fails, the CI job must surface
the **exact failing command** and its **complete stderr verbatim**, then stop — do not
swallow the error, summarize it, retry blindly, or attempt a workaround. A developer
reading the CI log should be able to copy the failing command and reproduce it locally.

```sh
set -euo pipefail   # fail fast; a failed build/validate aborts the job immediately

run() {
  echo "+ $*"                      # echo the exact command
  if ! "$@"; then
    echo "FAILED: $*" >&2          # name the command that failed
    exit 1                         # stop — no fallback, no retry
  fi
}

for overlay in k8s/overlays/*/; do
  run sh -c "kustomize build '$overlay' | kubeconform -strict -summary -ignore-missing-schemas"
done
```

`set -euo pipefail` plus `pipefail` is important: without it, a failing `kustomize build`
on the left of a pipe is masked by a succeeding `kubeconform` on the right, and the job
goes green on broken input. With `pipefail`, any stage's failure fails the pipeline.

## Putting it together

A minimal but complete CI stage, in order of cheapness:

1. `kustomize build` every overlay (structural validity) — fast, catches most errors.
2. `kubeconform -strict` the rendered output (schema validity) — catches field typos.
3. `conftest`/OPA the rendered output (policy) — enforces org conventions.
4. On any failure: print the exact command + full stderr and exit non-zero.

Pin tool versions (`kustomize`, `kubeconform`, `conftest`) in CI so a render that passes
locally passes in the pipeline.
