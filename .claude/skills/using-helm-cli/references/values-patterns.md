# Values patterns

Depth content for the SKILL.md "Values and overrides" section.

## Layered values hierarchy

Precedence, lowest to highest (later wins):

1. The chart's own `values.yaml` (defaults shipped by the chart author).
2. Subchart defaults, scoped under the subchart's key in the parent.
3. Each `-f` / `--values` file, applied **left to right** — the rightmost file
   wins on any key it sets.
4. `--set`, `--set-string`, `--set-json`, `--set-file` — applied after all files,
   in the order given.

Recommended file layering:

```
values.yaml            # baseline defaults, committed in the chart
values.common.yaml     # org-wide conventions
values.staging.yaml    # env override
values.prod.yaml       # env override (most specific)
```

```bash
helm upgrade --install app ./chart -n prod \
  -f values.common.yaml -f values.prod.yaml \
  --atomic --wait --timeout 5m
```

## `-f` ordering

`-f a.yaml -f b.yaml` means `b.yaml` overrides `a.yaml`. Order is significant and
explicit — do not rely on alphabetical or filesystem order. Keep the most specific
(environment/release) file last.

## Deep-merge vs array-replace

- **Maps deep-merge**: nested objects combine key by key across layers.
- **Arrays replace wholesale**: a list in a later layer *replaces* the earlier
  list entirely — Helm does not concatenate or merge by index.

Consequence: to "add one item" to a list you must restate the whole list in the
override. Design charts so list-valued knobs are either fully owned by one layer
or modeled as maps when partial override is needed.

## `values.schema.json`

Ship a JSON Schema (`values.schema.json` at chart root) so Helm validates merged
values at install/upgrade/template time and rejects bad input early:

```json
{
  "$schema": "https://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["image"],
  "properties": {
    "image": {
      "type": "object",
      "required": ["repository", "tag"],
      "properties": {
        "repository": { "type": "string" },
        "tag": { "type": "string" }
      }
    },
    "replicaCount": { "type": "integer", "minimum": 1 }
  }
}
```

Validation runs automatically; `helm lint` and `helm template` also exercise it.

## Secrets deferral

Do **not** put secret material in values files (they end up in the release Secret
in plaintext-ish encoding and often in git). Defer to:

- SOPS-encrypted values (decrypted by a plugin at apply time),
- `external-secrets` / `secrets-store-csi-driver` pulling from Vault/cloud KMS,
- Sealed Secrets.

This skill consumes already-resolved non-secret values; the secrets backend owns
the material (see SKILL.md "Out of scope").
