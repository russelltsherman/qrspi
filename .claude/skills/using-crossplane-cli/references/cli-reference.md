# Crossplane CLI reference

Command and flag reference for the `crossplane` CLI, provider lifecycle, and
environment configuration. **Flag names and defaults drift between releases — for
the authoritative, version-matched list run `crossplane <cmd> --help` and consult
the official docs at <https://docs.crossplane.io>.** Treat everything below as the
stable shape, not a frozen spec.

## Contents

- [Environment configuration](#environment-configuration)
- [Provider lifecycle](#provider-lifecycle)
- [Packaging: crossplane xpkg](#packaging-crossplane-xpkg)
- [render](#render)
- [trace](#trace)

## Environment configuration

- `KUBECONFIG` — path to the kubeconfig; selects the target cluster. Set the
  active context with `kubectl config use-context <name>`. Always confirm the
  target before applying: `kubectl config current-context`.
- Registry auth for `xpkg push/pull` comes from `crossplane xpkg login` or an
  existing Docker credential store (`~/.docker/config.json`).
- `crossplane version` — prints client and (if reachable) server versions. Use it
  to resolve the v1/v2 authoring branch before writing manifests.

## Provider lifecycle

Install a provider declaratively:

```yaml
apiVersion: pkg.crossplane.io/v1
kind: Provider
metadata:
  name: provider-aws-s3
spec:
  package: xpkg.upbound.io/upbound/provider-aws-s3:v1   # tag = version
```

```bash
kubectl apply -f provider.yaml
kubectl get providers                      # watch INSTALLED / HEALTHY
kubectl get providerrevision               # rollout revisions
```

Wire credentials with a `ProviderConfig` referencing a `Secret`:

```yaml
apiVersion: aws.upbound.io/v1beta1
kind: ProviderConfig
metadata:
  name: default
spec:
  credentials:
    source: Secret
    secretRef:
      namespace: crossplane-system
      name: aws-creds
      key: creds
```

- **Upgrade:** edit `spec.package` to the new tag and re-apply. Crossplane creates
  a new `ProviderRevision` and cuts over once it reports healthy. Roll back by
  reverting the tag.
- **Inspect:** `kubectl describe provider <name>` for install conditions.

## Packaging: crossplane xpkg

Bundle Configurations/Functions into OCI images. Verify exact flags with
`crossplane xpkg <sub> --help`.

- `crossplane xpkg build` — build a `.xpkg` from manifests in a directory.
  Common flags: `--package-root` (source dir), `-o/--output` (artifact path).
- `crossplane xpkg login` — authenticate to the OCI registry before push.
- `crossplane xpkg push <image:tag>` — push the built package to the registry.
- `crossplane xpkg validate` — validate package contents/schema before shipping
  (also useful for package-level troubleshooting; see `troubleshooting.md`).

Treat each pushed tag as an immutable release so cluster upgrades are deliberate.

## render

`crossplane render <xr.yaml> <composition.yaml> <functions.yaml>` renders a
composite **offline** through the composition function pipeline and prints the
managed resources that would result — no cluster or apply required. Use it to
validate Compositions before merging (see `composition-patterns.md`).

## trace

`crossplane trace <kind> <name> [-n <namespace>]` prints the composite resource
tree with each node's `READY`/`SYNCED`/`STATUS`, making it the first stop when
debugging (see `troubleshooting.md` for the full escalation order).
