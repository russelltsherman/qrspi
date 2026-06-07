# Waiters Reference

Waiters poll an API until a resource reaches a desired state, so scripts don't
busy-loop. Form:

```bash
aws <service> wait <condition> [--<resource-selector> ...]
```

The command **blocks** until the condition is met, then exits `0`. On timeout it
exits **`255`** (see below). List the waiters a service exposes with
`aws <service> wait help`.

## Common built-in waiters by service

| Service | Waiter | Waits until |
|---|---|---|
| S3 | `bucket-exists` / `bucket-not-exists` | bucket is created / deleted |
| S3 | `object-exists` / `object-not-exists` | object key present / gone |
| EC2 | `instance-running` | instance state = `running` |
| EC2 | `instance-status-ok` | instance + system status checks pass |
| EC2 | `instance-stopped` / `instance-terminated` | instance stopped / terminated |
| ECS | `services-stable` | service reached steady state (rollout done) |
| ECS | `tasks-running` / `tasks-stopped` | task(s) running / stopped |
| Lambda | `function-active` / `function-active-v2` | function ready after create |
| Lambda | `function-updated` / `function-updated-v2` | code/config update applied |
| CloudFormation | `stack-create-complete` | stack create finished |
| CloudFormation | `stack-update-complete` | stack update finished |
| CloudFormation | `stack-delete-complete` | stack deletion finished |
| RDS | `db-instance-available` | DB instance available |

Examples (placeholders only):

```bash
# Block until a new instance passes status checks
aws ec2 wait instance-status-ok --instance-ids i-xxx

# Block until a CloudFormation stack finishes creating
aws cloudformation wait stack-create-complete --stack-name <stack>

# Block until an ECS service finishes rolling out
aws ecs wait services-stable --cluster <cluster> --services <service>

# Block until a Lambda is ready to invoke after create
aws lambda wait function-active-v2 --function-name <name>
```

## Exit-code-255 timeout handling

A waiter has a **bounded** number of attempts at a fixed interval (defaults vary
per waiter — e.g. EC2 `instance-running` is 40 attempts × 15s = ~10 min). If the
state is not reached within that budget, the waiter gives up and exits with
status **`255`** (a generic CLI failure), printing a "Waiter ... failed" /
"Max attempts exceeded" message to stderr.

Always check the exit code in scripts — a `255` means the resource did **not**
reach the desired state in time, not that the resource is broken:

```bash
if aws cloudformation wait stack-create-complete --stack-name <stack>; then
  echo "stack ready"
else
  rc=$?   # 255 == waiter timed out
  echo "waiter exited $rc — stack did not reach create-complete in the attempt budget" >&2
  # Inspect the real reason rather than assuming success:
  aws cloudformation describe-stack-events --stack-name <stack> \
    --query 'StackEvents[?ResourceStatus==`CREATE_FAILED`].[LogicalResourceId,ResourceStatusReason]' \
    --output text
  exit "$rc"
fi
```

Notes:

- The attempt budget is **fixed per waiter** and not configurable from the CLI;
  for longer operations, wrap the waiter in your own retry loop or poll
  `describe-*` directly.
- Some waiters fail fast on a terminal-failure state (e.g.
  `stack-create-complete` errors immediately on `ROLLBACK_COMPLETE`) rather than
  waiting out the full budget — still surfaced as a non-zero exit.
- Do NOT treat a non-zero waiter exit as success; branch on it explicitly.
