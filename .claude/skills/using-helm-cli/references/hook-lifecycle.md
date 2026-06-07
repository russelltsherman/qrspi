# Hook lifecycle

Depth content for the SKILL.md "Hooks" section.

## Hook annotations

A normal chart resource becomes a hook by adding the `helm.sh/hook` annotation:

```yaml
metadata:
  annotations:
    "helm.sh/hook": pre-upgrade,pre-install
    "helm.sh/hook-weight": "-5"
    "helm.sh/hook-delete-policy": before-hook-creation,hook-succeeded
```

## Lifecycle phases

Hooks fire at these points (in execution order around the main release apply):

- `pre-install` → (resources applied) → `post-install`
- `pre-upgrade` → (resources applied) → `post-upgrade`
- `pre-rollback` → (resources applied) → `post-rollback`
- `pre-delete` → (resources deleted) → `post-delete`
- `test` — only on `helm test`

A common pattern: `pre-upgrade` DB migration Job (weight `-5`), then app rollout,
then `post-upgrade` smoke/seed Job (weight `0`+).

## Hook weights

`helm.sh/hook-weight` is a **string-encoded integer**. Within a single phase,
hooks run in ascending weight order (lower/negative first); ties run in
alphabetical resource-name order. Use negative weights for "must happen before
everything else in this phase."

## Delete policies

`helm.sh/hook-delete-policy` controls cleanup of the hook resource:

- `before-hook-creation` (default-ish best practice) — delete a previous instance
  of this hook before creating the new one; prevents "already exists" failures on
  re-run.
- `hook-succeeded` — delete after the hook completes successfully (keeps the
  cluster clean).
- `hook-failed` — delete after failure (set carefully: deleting a failed Job
  discards its logs; often you want to *keep* failed hooks for diagnosis).

Typical safe combo: `before-hook-creation,hook-succeeded`.

## Hook Job resourcing

Because `--wait` blocks on hook completion, a misbehaving hook can hang the whole
release:

- Set `resources.requests`/`limits` so the hook pod schedules predictably.
- Set `backoffLimit` (e.g. `1`–`3`) and `activeDeadlineSeconds` so a wedged hook
  fails fast instead of retrying forever.
- Set `restartPolicy: Never` (or `OnFailure` with a bounded `backoffLimit`).
- Ensure the hook's `--timeout` headroom is less than the release `--timeout`.

Diagnose with `helm get hooks <release> -n <ns>` and the hook pod's logs.
