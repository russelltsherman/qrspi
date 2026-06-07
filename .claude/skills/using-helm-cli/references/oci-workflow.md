# OCI and classic-repo workflow

Depth content for the SKILL.md "Repositories and registries" section.

## OCI workflow (preferred in Helm 4)

Charts are stored as OCI artifacts alongside container images.

```bash
# Authenticate
helm registry login registry.example.com -u "$USER" --password-stdin <<<"$TOKEN"

# Package and push
helm package ./chart                      # -> app-1.4.2.tgz
helm push app-1.4.2.tgz oci://registry.example.com/charts

# Pull / inspect
helm pull oci://registry.example.com/charts/app --version 1.4.2 --verify
helm show chart oci://registry.example.com/charts/app --version 1.4.2

# Install directly from OCI
helm upgrade --install app oci://registry.example.com/charts/app \
  --version 1.4.2 -n prod --create-namespace \
  --atomic --wait --timeout 5m --verify

# Logout when done
helm registry logout registry.example.com
```

Reference charts by **immutable version**, never a floating tag, in any
non-interactive path.

`Helm 3:` early releases gated OCI behind `HELM_EXPERIMENTAL_OCI=1`. Helm 4 makes
it the default distribution channel.

## Classic HTTP repo workflow

```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
helm search repo bitnami/nginx --versions
helm pull bitnami/nginx --version 18.0.0 --verify
```

`helm repo update` refreshes the cached `index.yaml`; always update before search
or install to avoid stale version resolution.

## Signing and verification

Two complementary mechanisms — use both for supply-chain assurance:

### Provenance (`.prov`, Helm-native)

```bash
helm package --sign --key 'release@example.com' \
  --keyring ~/.gnupg/secring.gpg ./chart      # produces app-1.4.2.tgz + .prov

helm verify app-1.4.2.tgz --keyring ~/.gnupg/pubring.gpg
helm install ... --verify --keyring ~/.gnupg/pubring.gpg
```

`--verify` checks the `.prov` signature and the chart's SHA-256 digest before
deploying.

### cosign (OCI artifact signing)

```bash
cosign sign      registry.example.com/charts/app:1.4.2
cosign verify --key cosign.pub registry.example.com/charts/app:1.4.2
```

cosign signs the OCI artifact itself (keyless or key-based) and integrates with
admission policy (e.g. Kyverno/Connaisseur) to block unsigned charts at deploy
time. Provenance proves *Helm packaged it*; cosign proves *who published the
artifact* — keep both.
