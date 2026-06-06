# Troubleshooting Crossplane

A decision tree for diagnosing stuck or unhealthy Crossplane resources. Work the
escalation order top to bottom and **stop as soon as a condition message explains
the failure** — going deeper than necessary just adds noise.

## Contents

- [Escalation order](#escalation-order)
- [Condition checks](#condition-checks)
- [Common patterns](#common-patterns)
- [Package-level faults: xpkg validate](#package-level-faults-xpkg-validate)

## Escalation order

**`trace → describe → events → logs`**

1. **`crossplane trace <kind> <name> [-n <ns>]`** — the whole composite tree with
   each node's `READY`/`SYNCED`/`STATUS`. Identifies *which* resource is broken.
2. **`kubectl describe <kind> <name>`** — read that resource's `status.conditions`
   and their human-readable messages. Most root causes show up here.
3. **`kubectl get events --sort-by=.lastTimestamp`** (or describe's Events
   section) — recent reconcile errors, often with the provider's exact rejection
   reason (bad ARN, missing permission, quota).
4. **provider/controller logs** — `kubectl logs -n crossplane-system
   deploy/<provider-deployment>`. The deepest, noisiest signal; only reach here
   when steps 1–3 don't explain the failure.

## Condition checks

Inspect `status.conditions` on the resource:

- **`Synced`** — did the controller reconcile the spec with the external API?
  `Synced=False` means a config/credential/permission problem **before** the
  external call succeeded. Read the message; it usually names the field or auth
  issue. This is the first condition to check.
- **`Ready`** — did the external resource reach its desired state?
  `Ready=False` with `Synced=True` means the request was accepted but the external
  resource is still provisioning or the API rejected it downstream.
- **`ReconcileError`** — surfaced in conditions/events when the controller hit an
  error reconciling; the message carries the provider error string.
- **`Responsive`** (providers/packages) — whether the package's controller is
  reachable/healthy. `Responsive=False` points at an unhealthy provider
  deployment, not your resource — check `kubectl get providers`.

## Common patterns

- **Stuck at `Synced=False`, no events:** usually a missing or wrong
  `ProviderConfig`/`Secret`. Verify the secret exists in the referenced namespace.
- **`Ready=False` forever, `Synced=True`:** external dependency or quota; read the
  describe message and events for the provider's reason.
- **XR exists but no managed resources:** composition selection or
  `compositeTypeRef` mismatch — validate offline with `crossplane render` (see
  `composition-patterns.md`).
- **Claim/XR rejected by API server:** v1/v2 scope mismatch — recheck the XRD
  scope against the installed version (see `xrd-schemas.md`).

## Package-level faults: xpkg validate

When the problem is a Configuration/Function package itself (won't install, schema
errors), validate the package before debugging cluster state:

```bash
crossplane xpkg validate <package>
```

Pair this with `kubectl get providerrevision` /
`kubectl describe configuration <name>` to see install-time conditions. See
`cli-reference.md` for the full `xpkg` family.
