# Argo CD Sync Strategies

Self-contained reference for syncing Applications. Loaded from the "Diff & sync" section
of `SKILL.md`.

## Manual vs automated

| Mode | Behavior | Use for |
|------|----------|---------|
| Manual | A human (or pipeline) triggers `argocd app sync`. Drift is reported but not corrected. | Production; anything needing a review gate. |
| Automated | Argo CD syncs whenever Git changes. | Dev/ephemeral; low-risk targets. |

Set in the Application spec:

```yaml
spec:
  syncPolicy:
    automated:          # omit this whole block for manual sync
      selfHeal: false
      prune: false
```

## Self-heal and auto-prune

- **selfHeal** — Argo CD reverts *any* live drift back to Git, continuously. Powerful but
  it will fight manual hotfixes. Avoid on production unless drift-correction is an
  explicit requirement.
- **prune (auto)** — automated sync deletes live resources that no longer exist in Git.
  Off by default. Turning it on means a Git deletion silently deletes live resources.

## Sync waves

Order resource application with the annotation `argocd.argoproj.io/sync-wave: "<n>"`
(lower waves apply first; default `0`). Use for dependencies — e.g. CRDs in wave `-1`,
controllers in `0`, CRs in `1`.

## Hooks

Lifecycle hooks run at sync phases via `argocd.argoproj.io/hook`:

| Hook | Runs |
|------|------|
| `PreSync` | before the main sync (e.g. DB migration Job) |
| `Sync` | during the main sync |
| `PostSync` | after all resources are Healthy (e.g. smoke test) |
| `SyncFail` | when the sync fails |

Clean up hook resources with `argocd.argoproj.io/hook-delete-policy`
(`HookSucceeded` / `HookFailed` / `BeforeHookCreation`).

## Retry policy

```yaml
spec:
  syncPolicy:
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
```

Retries handle transient failures; they do not fix a genuinely broken manifest. If
retries are exhausted, treat it as a real failure (see `troubleshooting.md`).

## `--force` and `--prune` cautions (read before using)

- **`--prune`** on a manual sync deletes live resources absent from Git. Run
  `argocd app sync --prune --dry-run` first and read the planned deletions. A wrong
  `--path` or branch can prune an entire namespace.
- **`--force`** deletes and recreates resources instead of patching (replace semantics).
  This causes downtime and can drop data on stateful resources. It is a last resort, not
  a way to push past a sync error.
- Both are HARD STOP actions in the body — confirm blast radius with a human first. Never
  use them to "make it go green" after a failed sync; diagnose the failure instead.
