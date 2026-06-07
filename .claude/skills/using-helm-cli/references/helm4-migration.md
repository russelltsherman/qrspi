# Helm 4 migration

Depth content for the SKILL.md "Helm 4 awareness" section. Inline `Helm 3:`
caveats in SKILL.md flag the per-command differences; this file is the
consolidated migration checklist.

## Server-Side Apply (SSA) is the default

Helm 4 applies manifests with Kubernetes **Server-Side Apply** by default.

- **Field ownership**: the API server tracks which manager owns each field. A
  field set by Helm and later mutated by another controller can produce
  ownership conflicts.
- **Three-way merge moves server-side**: the merge is computed by the API server
  against live state, which is more accurate than Helm 3's client-side merge but
  can surface conflicts that were previously silent.

`Helm 3:` used client-side three-way strategic merge patch. Charts that relied on
that exact merge behavior (e.g. expecting Helm to "win" over a controller) may
need explicit field management or `force` handling on upgrade.

Action: after upgrading Helm, run `helm upgrade --dry-run=server` on each chart
in a non-prod environment and review the diff for unexpected ownership conflicts.

## Readiness annotations

Helm 4 improves `--wait` readiness detection. You can annotate resources to tune
how readiness is judged (e.g. custom readiness for CRs that lack standard status
conditions). Audit long-`--wait` charts: resources that previously "passed" by
existing may now be held until genuinely Ready.

## Post-renderer plugins

Helm 4 has first-class **post-renderer** support — a binary/plugin that
transforms rendered manifests after templating, before apply (e.g. kustomize
overlay, policy injection):

```bash
helm upgrade --install app ./chart -n prod \
  --post-renderer ./kustomize-post-render.sh \
  --atomic --wait --timeout 5m
```

Prefer this over forking charts when you need org-wide manifest mutation.

## Helm 3 compatibility notes

- **Release metadata**: Helm 4 reads Helm 3 release Secrets; existing releases
  upgrade in place. Still, test rollback paths after migration.
- **OCI**: drop `HELM_EXPERIMENTAL_OCI`; OCI is default-on (see
  `oci-workflow.md`).
- **`--dry-run`**: prefer the explicit `--dry-run=server` form for admission-aware
  renders.
- **Plugins**: re-verify third-party plugins (helm-diff, helm-unittest,
  helm-secrets) for Helm 4 compatibility before relying on them in CI.

## Migration checklist

1. Inventory charts and pinned plugins.
2. Upgrade Helm 4 in a sandbox; `helm list -A` to confirm releases are visible.
3. `helm upgrade --dry-run=server` each chart; review SSA ownership diffs.
4. Re-run lint / unittest / policy suites (`testing-strategies.md`).
5. Validate rollback on a non-critical release.
6. Roll out to staging, then prod, with `--atomic --wait`.
