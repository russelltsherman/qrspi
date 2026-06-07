# Generators: configMapGenerator and secretGenerator

Generators build ConfigMaps and Secrets from literals, files, or `.env` files instead of
hand-writing them. Their defining behavior: Kustomize appends a **content hash suffix** to
the generated name (e.g. `app-config-7t9f2k8c4d`) and rewrites every reference to it. When
the content changes, the name changes, so dependent Deployments roll automatically — you
get config-driven rollouts for free. Disable the suffix only when something external
references the name by a fixed value (see `generatorOptions` below).

## configMapGenerator

```yaml
configMapGenerator:
  - name: app-config
    literals:                 # inline key=value pairs
      - LOG_LEVEL=info
      - FEATURE_X=true
  - name: app-files
    files:                    # whole files become keys (filename → key)
      - nginx.conf
      - app.properties=config/app.properties   # rename key
  - name: app-env
    envs:                     # parse a dotenv file into individual keys
      - config.env
```

## secretGenerator

Same shapes as `configMapGenerator`, but produces a `Secret`. Values are base64-encoded by
Kustomize; they are **not** encrypted — base64 is encoding, not security.

```yaml
secretGenerator:
  - name: app-secrets
    envs:
      - .env                  # see secret handling below
  - name: tls
    files:
      - tls.crt
      - tls.key
    type: kubernetes.io/tls
```

## behavior: merge / replace / create

When an overlay declares a generator with the **same name** as one inherited from the base,
`behavior:` decides what happens. Default is `create`, which errors on a name clash — so be
explicit in overlays.

| `behavior:` | Effect                                                      |
| ----------- | ---------------------------------------------------------- |
| `create`    | Make a new generator (default; errors if name already exists) |
| `merge`     | Add/override keys on the base's generator of the same name |
| `replace`   | Discard the base's generator entirely, use this one        |

```yaml
# overlays/prod/kustomization.yaml — add prod-only keys onto the base config
configMapGenerator:
  - name: app-config
    behavior: merge
    literals:
      - LOG_LEVEL=warn        # overrides the base value
      - PROD_ONLY=1           # adds a new key
```

## generatorOptions

Controls applied to all generators in the file (or per-generator under `options:`).

```yaml
generatorOptions:
  disableNameSuffixHash: true   # keep a stable name (needed when something refs it externally)
  labels:
    generated-by: kustomize
  annotations:
    note: do-not-edit-by-hand
```

Reach for `disableNameSuffixHash: true` sparingly — it forfeits the automatic-rollout
benefit. The usual reason is an external resource (an Ingress, a cross-namespace ref, a
controller config) that points at a fixed ConfigMap/Secret name.

## Secret handling: gitignored `.env` + committed `.env.example`

Never commit real secret values. Mirror the repo's existing precedent
(`.qrspi/config.json` is gitignored while `.qrspi/config.example.json` is committed):

- Source the `secretGenerator` from a **gitignored `.env`** that each developer/CI supplies.
- Commit a **`.env.example`** sibling with the same keys and placeholder/empty values, so a
  newcomer knows exactly which variables to provide.

```
overlays/prod/
├── kustomization.yaml     # secretGenerator: envs: [.env]
├── .env                   # gitignored — real values, never committed
└── .env.example           # committed — same keys, placeholder values
```

```gitignore
# .gitignore
overlays/*/.env
!overlays/*/.env.example
```

```dotenv
# .env.example (committed) — documents required keys, no real values
DATABASE_URL=
API_TOKEN=
```

This keeps the *contract* (which secrets exist) in version control while keeping the
*values* out of it. In real clusters, prefer a proper secrets manager (Sealed Secrets,
External Secrets, SOPS, Vault) over a plain `.env` for anything beyond local/dev use — the
`.env` + `.env.example` pattern documents the interface, not a production secret store.
