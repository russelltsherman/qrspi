# Cron workflows

Scheduling recurring workflows with `CronWorkflow`. Read this when creating,
inspecting, pausing, or removing a schedule, or when tuning how overlapping runs
and timezones are handled.

## Contents

- [Creating a CronWorkflow](#creating-a-cronworkflow)
- [Listing and inspecting](#listing-and-inspecting)
- [Suspend and resume](#suspend-and-resume)
- [Deleting](#deleting)
- [Linting](#linting)
- [Concurrency policy](#concurrency-policy)
- [Timezone](#timezone)
- [Triggering an off-schedule run](#triggering-an-off-schedule-run)

A `CronWorkflow` wraps a normal `workflowSpec` with a schedule. The Argo controller
creates a Workflow from that spec on each tick. Everything in authoring.md (DAG vs
Steps, parameters, retry, resources) applies unchanged inside `spec.workflowSpec`.

## Creating a CronWorkflow

```bash
argo cron create cron-workflow.yaml
```

A minimal spec:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: CronWorkflow
metadata:
  name: nightly-report
spec:
  schedule: "0 2 * * *"            # 02:00 daily, cron syntax
  timezone: "America/New_York"
  concurrencyPolicy: Forbid
  startingDeadlineSeconds: 300
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 3
  workflowSpec:
    entrypoint: main
    templates: [...]
```

`startingDeadlineSeconds` bounds how late a missed tick may still start (e.g. after
a controller restart); past it, that occurrence is skipped rather than firing late.
The two `historyLimit` fields cap how many finished runs are retained so the
namespace does not accumulate old workflows.

## Listing and inspecting

```bash
argo cron list                    # all CronWorkflows in the namespace
argo cron list -A                 # across all namespaces
argo cron get nightly-report      # schedule, last/next run time, suspended state
```

`argo cron get` shows the next scheduled time and the last run's outcome — the
fastest way to confirm a schedule is active and firing when expected.

## Suspend and resume

Pause a schedule without deleting it — no new runs are created while suspended;
in-flight runs are unaffected:

```bash
argo cron suspend nightly-report
argo cron resume nightly-report
```

Prefer suspend over delete when you are pausing for maintenance or an incident and
intend to turn the schedule back on — it preserves the definition and history.

## Deleting

```bash
argo cron delete nightly-report
```

Deleting removes the schedule (and stops future runs). Workflows it already created
persist independently — clean those up separately with `argo delete` (see
debugging-and-lifecycle.md).

## Linting

```bash
argo cron lint cron-workflow.yaml
```

Validates both the cron envelope (schedule syntax, concurrency policy, timezone)
and the embedded `workflowSpec`. Lint before `create` so a bad schedule string or
template fails client-side instead of silently never firing.

## Concurrency policy

`concurrencyPolicy` decides what happens when a tick arrives while the previous
run is still going — the single most important field to get right, because the
wrong choice causes either pile-ups or silent data races.

| Policy | Behavior | Use when |
|---|---|---|
| `Allow` (default) | Start the new run regardless; overlapping runs coexist | Runs are independent and idempotent |
| `Forbid` | Skip the new run if the previous is still active | A run must not overlap itself (e.g. a report that reads+writes shared state) |
| `Replace` | Cancel the in-flight run and start the new one | Only the latest result matters; stale in-flight work is worthless |

Default `Allow` is rarely what you want for stateful jobs. Choose `Forbid` for
"never two at once" and `Replace` for "always run the newest, drop the old."

## Timezone

Set `spec.timezone` to an IANA name (e.g. `America/New_York`, `Europe/London`,
`UTC`). Without it the schedule is interpreted in the controller's local timezone,
which is environment-dependent and a classic source of "it ran an hour off"
surprises — especially across daylight-saving transitions. Always set `timezone`
explicitly so the schedule means the same thing regardless of where the controller
runs.

## Triggering an off-schedule run

To run a CronWorkflow's spec immediately without waiting for the next tick:

```bash
argo submit --from cronworkflow/nightly-report
```

This creates a one-off Workflow from the cron's `workflowSpec` — handy for testing
a schedule's logic or backfilling a missed run.
