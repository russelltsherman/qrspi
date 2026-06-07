---
name: using-helm-cli
description: "Operate Helm safely for Kubernetes release management — install, upgrade, rollback, uninstall, and status of charts, plus chart authoring, values/overrides, OCI and classic repositories, hooks, and testing. Use when the user wants to: 'deploy with helm', 'helm install', 'helm upgrade', 'rollback a release', 'helm uninstall', 'check helm status / helm list', author or lint a Helm chart, manage chart values or overrides, push/pull charts from an OCI registry or classic repo, run helm test / helm-unittest, debug a stuck or failed release, or migrate between Helm 3 and Helm 4. Trigger on any mention of helm, charts, releases, Chart.yaml/values.yaml, or 'helm upgrade --install'."
command: /using-helm-cli
argument-hint: <release-or-chart-or-question>
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Using the Helm CLI

Operate Helm as a disciplined release tool, not a one-shot `kubectl apply`. Helm
manages **releases** (a named, versioned instance of a chart in a namespace) and
keeps revision history so every change is reversible. This skill is opinionated
toward **Helm 4** defaults; where behavior differs from the older line, an inline
caveat is prefixed `Helm 3:`. Deep migration detail lives in
`references/helm4-migration.md`.

Default posture: **safe, atomic, observable, namespaced**. Never run a mutating
release command without `--atomic --wait` and an explicit `--namespace`. When the
chart or its dependencies are signed, add `--verify`.

## Mandatory security-first defaults

Apply these on every mutating operation unless the user explicitly opts out:

- `--namespace <ns>` (and `--create-namespace` only on first install) — never rely
  on the ambient kube-context namespace; be explicit so the release lands where
  intended.
- `--atomic` — roll the release back automatically if it fails, leaving no
  half-applied state.
- `--wait` — block until all resources are Ready (or the timeout fires) instead of
  returning the moment the API server accepts the manifests.
- `--timeout <dur>` — bound the wait (e.g. `--timeout 5m`); `--atomic` needs a
  finite timeout to trigger rollback.
- `--verify` — verify the chart's provenance signature when a `.prov` file /
  signing is in use (see `references/oci-workflow.md`).

> `--atomic` implies `--wait`. Listing both is harmless and self-documenting.

## Release lifecycle

The five core operations. Treat `helm upgrade --install` as the idempotent default
for both first deploy and subsequent deploys in automation.

### install

```bash
helm install my-release ./chart \
  --namespace prod --create-namespace \
  --atomic --wait --timeout 5m \
  --values values.prod.yaml
```

Idempotent form for pipelines:

```bash
helm upgrade --install my-release oci://registry.example.com/charts/app \
  --version 1.4.2 \
  --namespace prod --create-namespace \
  --atomic --wait --timeout 5m --verify \
  -f values.prod.yaml
```

### upgrade

```bash
helm upgrade my-release ./chart \
  --namespace prod \
  --atomic --wait --timeout 5m \
  -f values.prod.yaml
```

- `--install` makes it create-or-update.
- `--reuse-values` carries forward prior overrides; `--reset-values` discards them.
  Be explicit — silent value drift is a top cause of surprise diffs.
- Preview first with `helm diff upgrade` (helm-diff plugin) or
  `helm upgrade --dry-run=server`.
- `Helm 3:` `--dry-run` had no server/client distinction; in Helm 4 prefer
  `--dry-run=server` for an accurate, admission-aware render.

### rollback

```bash
helm rollback my-release <REVISION> \
  --namespace prod --atomic --wait --timeout 5m
```

- `helm history my-release -n prod` lists revisions; omit `<REVISION>` to roll back
  one step.
- Rollback creates a *new* forward revision — history is append-only.

### uninstall

```bash
helm uninstall my-release --namespace prod --wait
```

- `--keep-history` retains revision records (allows later rollback of an uninstall).
- Uninstall does **not** remove PVCs created by StatefulSets, CRDs, or
  out-of-band resources — verify cleanup explicitly.

### status

```bash
helm status my-release -n prod
helm list -n prod                 # or --all-namespaces
helm get values my-release -n prod
helm get manifest my-release -n prod
```

Use `helm status` and `helm get values/manifest/hooks` as the first stop when
diagnosing — they show what Helm believes is deployed.

## Values and overrides

Configuration precedence (lowest → highest): chart `values.yaml` → each `-f` file
in left-to-right order → each `--set`/`--set-string`/`--set-file`. Later wins.

- Prefer layered `-f` files (`values.yaml` → `values.staging.yaml` →
  `values.prod.yaml`) over sprawling `--set`; files are reviewable and diffable.
- Ship a `values.schema.json` so bad inputs fail at render time, not at runtime.
- Understand deep-merge (maps merge) vs array replacement (lists are replaced
  wholesale, not concatenated).
- Never commit secrets to values files; defer secret material to a secrets
  manager / SOPS / external-secrets.

Depth and worked examples: `references/values-patterns.md`.

## Chart authoring

- `helm create <name>` scaffolds; keep `Chart.yaml` `version` (chart SemVer) and
  `appVersion` (the app's version) distinct and bumped on every change.
- Factor shared template logic into a **library chart** (`type: library`) consumed
  via `dependencies`.
- Pin and lock dependencies: `helm dependency update` writes `Chart.lock`; commit
  it.
- Validate inputs with `values.schema.json` (see `references/values-patterns.md`).

## Repositories and registries

Helm 4 treats **OCI registries as the primary distribution channel**; classic
HTTP repos remain supported.

```bash
# OCI (preferred)
helm push app-1.4.2.tgz oci://registry.example.com/charts
helm pull oci://registry.example.com/charts/app --version 1.4.2 --verify

# Classic repo
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
helm search repo bitnami/nginx
```

`Helm 3:` OCI support was experimental/behind `HELM_EXPERIMENTAL_OCI` early on; in
Helm 4 it is the default path and `helm registry login` is first-class. Full
push/pull, login, and signing/verification (cosign + provenance) flows:
`references/oci-workflow.md`.

## Hooks

Helm hooks run Kubernetes resources at defined lifecycle points
(`pre-install`, `post-install`, `pre-upgrade`, `post-upgrade`, `pre-delete`,
`post-delete`, `pre-rollback`, `post-rollback`, `test`) via the
`helm.sh/hook` annotation. Order with `helm.sh/hook-weight`; clean up with
`helm.sh/hook-delete-policy`. Always set resource limits and a sensible
`backoffLimit` on hook Jobs so a failing hook cannot hang `--wait` indefinitely.

Weights, delete policies, lifecycle ordering, and Job resourcing:
`references/hook-lifecycle.md`.

## Testing

```bash
helm lint ./chart
helm template ./chart -f values.prod.yaml      # render & inspect
helm test my-release -n prod                    # run chart `test` hooks
```

Layer fast unit tests (helm-unittest), render-time policy checks (conftest /
kyverno against `helm template` output), schema validation, and the live
`helm test` smoke. Strategy and tooling: `references/testing-strategies.md`.

## Troubleshooting decision tree

Work top-down; stop at the first match.

1. **Command rejected immediately** (template/parse error)?
   → `helm lint` + `helm template` to localize; fix chart/values, retry.
2. **Install/upgrade times out under `--wait`**?
   → `kubectl get events -n <ns> --sort-by=.lastTimestamp` and
     `kubectl describe` the not-Ready resource. Common causes: bad image,
     failing readiness probe, unschedulable pod, missing secret/config.
   → `--atomic` will already have rolled back; inspect, fix, re-run.
3. **Release stuck in `pending-install` / `pending-upgrade`**?
   → A prior run was killed mid-flight. `helm history` to see state; either
     `helm rollback` to the last good revision or `helm uninstall` and reinstall.
     Do not force-edit the release Secret unless you understand the consequences.
4. **`another operation (install/upgrade/rollback) is in progress`**?
   → A lock from an interrupted run. Resolve as in (3); `--wait` + finite
     `--timeout` prevents creating these.
5. **Hook failing**?
   → `helm get hooks my-release -n prod`; check the hook Job's pod logs. Verify
     `hook-weight` ordering and `hook-delete-policy`
     (`references/hook-lifecycle.md`).
6. **Values not taking effect**?
   → `helm get values my-release -n prod`; check `-f`/`--set` precedence and
     `--reuse-values` vs `--reset-values` (`references/values-patterns.md`).
7. **Signature/verify failure**?
   → Confirm `.prov` presence and keyring / cosign config
     (`references/oci-workflow.md`).

## Helm 4 awareness

Helm 4 changes defaults you must account for:

- **Server-Side Apply** is the default apply strategy (better three-way merge and
  field ownership). `Helm 3:` used client-side three-way merge.
- Improved **readiness** handling under `--wait`.
- First-class **OCI** and **post-renderer** support.

Inline `Helm 3:` caveats appear throughout this skill at the relevant command.
The full migration checklist (SSA implications, readiness annotations,
post-renderer plugins, Helm 3 compatibility notes) is in
`references/helm4-migration.md`.

## Out of scope

This skill is Helm-only. The following are explicitly **not** covered here —
defer to the named owner:

- **Raw `kubectl` and `kustomize`** (imperative apply, overlays without Helm) —
  out of scope; belongs to general Kubernetes manifest work, not this skill.
- **`Helmfile`** (declarative orchestration of *many* releases across
  environments) — out of scope; use a dedicated Helmfile workflow/skill.
- **GitOps reconcilers (Argo CD, Flux)** that *render* Helm charts — out of
  scope; chart authoring here is upstream of the reconciler, which the GitOps
  platform's own skill/phase owns.
- **Secrets management backends** (SOPS, Vault, external-secrets) — referenced
  for deferral only; the secrets tooling owns the material, this skill only
  consumes the rendered values.
