# Reliability: retries, timeouts, resources, and artifacts

**Targeted version:** Argo Workflows **v3.5.x** (principle-based — favor the patterns below over
version-specific minutiae; confirm field availability against the cluster CRD).

## Retry strategy and exponential backoff

Attach a `retryStrategy` to any template that can fail transiently. Retry **transient** errors only;
do not blindly retry deterministic failures (they just waste time and money).

```yaml
retryStrategy:
  limit: "5"                 # max retries (string)
  retryPolicy: "OnError"     # OnFailure | OnError | OnTransientError | Always
  backoff:
    duration: "10s"          # initial delay
    factor: "2"              # exponential multiplier -> 10s, 20s, 40s, ...
    maxDuration: "10m"       # cap total backoff window
  affinity:
    nodeAntiAffinity: {}     # spread retries across nodes (avoid a bad node)
```

- **`retryPolicy`** — `OnError` (infra/system errors), `OnFailure` (non-zero exit), `OnTransientError`
  (errors matching `TRANSIENT_ERROR_PATTERN`), or `Always`. Prefer `OnTransientError`/`OnError` for
  flaky infra; reserve `OnFailure` for genuinely idempotent retryable work.
- **Exponential backoff** via `factor` prevents hammering a struggling dependency; always set
  `maxDuration` so a workflow cannot retry forever.

## Error handling

- **`exit handler` / `onExit`** — run cleanup or notifications regardless of outcome; inspect
  `{{workflow.status}}` / `{{workflow.failures}}`.
- **`continueOn`** — `continueOn: { failed: true }` on a task to let the graph proceed past a
  non-critical failure.
- **`templateDefaults`** — set workflow-wide defaults (e.g., a default `retryStrategy`, `timeout`) so
  every template inherits sane reliability settings.

## Timeouts

- **`activeDeadlineSeconds`** — at workflow `spec` level bounds the whole run; at template level bounds
  a single step. Always set a workflow-level deadline so stuck runs self-terminate.
- **`ttlStrategy`** — `secondsAfterCompletion` / `secondsAfterSuccess` / `secondsAfterFailure` to
  auto-clean finished workflow objects and free etcd.

## Resource management

- **Requests/limits:** set container `resources.requests` and `resources.limits` (cpu, memory) on
  every container template — unbounded pods get evicted or starve the namespace.
- **`parallelism`:** at `spec` level caps concurrently running nodes in one workflow; in a `withItems`
  loop caps concurrent iterations. Bound it to protect shared backends.
- **`synchronization`:** use a `semaphore` (ConfigMap-backed) or `mutex` to cap concurrency *across*
  workflows competing for a shared resource (e.g., a single deploy slot).
- **Placement:** `nodeSelector`, `tolerations`, and `affinity` to target appropriate node pools
  (e.g., GPU, spot, or high-memory nodes).

## Artifact best practices

- **Parameterize keys:** build artifact paths from run identity, e.g.
  `key: "runs/{{workflow.name}}/{{pod.name}}/output.tar.gz"`, so runs never collide.
- **Scope per run:** keep each run's artifacts under a run-scoped prefix; avoid shared mutable paths.
- **Garbage collection:** set `artifactGC` (`strategy: OnWorkflowDeletion` or `OnWorkflowCompletion`)
  plus a repository lifecycle policy so artifacts don't accumulate unbounded.
- **Compression & size:** archive (`archive: { none: {} }` to opt out, or tar/gzip by default) and
  keep artifacts lean; pass large data by reference (object-store key) rather than inlining.
- **Repositories:** prefer a configured `artifactRepositoryRef` over per-workflow inline credentials
  so storage config and secrets stay centralized.
