# Per-Service Cheat Sheets

Concise operational patterns for the six core services. All identifiers are
placeholders (`<bucket>`, `i-xxx`, `<name>`, `<arn>`). Prefer `--query` to shape
output (see `jmespath.md`) and waiters to synchronize (see `waiters.md`).

## S3 — high-level `s3` vs low-level `s3api`

- **`aws s3`** — high-level, human-friendly: recursive copy/sync, multipart
  handled automatically.
- **`aws s3api`** — thin 1:1 mapping to the REST API: per-object metadata, ACLs,
  versioning, lifecycle, bucket policy. Use it when `s3` lacks the knob.

```bash
# High-level transfers
aws s3 cp ./dir s3://<bucket>/<prefix>/ --recursive
aws s3 sync ./build s3://<bucket>/site/ --delete --exclude '*.map'

# Low-level: precise object metadata / control
aws s3api put-object --bucket <bucket> --key <key> --body ./file \
  --content-type application/json --cache-control 'max-age=300'
aws s3api list-object-versions --bucket <bucket> --prefix <prefix>
aws s3api head-object --bucket <bucket> --key <key>   # metadata / existence check
```

- Use `--dryrun` on `cp`/`sync`/`rm` to preview.
- Server-side encryption: `--sse aws:kms --sse-kms-key-id <key-arn>`.

## EC2 — filters, tags, launch templates

- Reduce results **server-side** with `--filters` (Name/Values), then shape with
  `--query`.

```bash
# Server-side filter by tag + state
aws ec2 describe-instances \
  --filters 'Name=tag:Environment,Values=<env>' 'Name=instance-state-name,Values=running' \
  --query 'Reservations[].Instances[].{ID:InstanceId,IP:PrivateIpAddress}' --output table

# Tagging
aws ec2 create-tags --resources i-xxx --tags Key=Name,Value=<name>

# Launch template: create a version, then launch from it
aws ec2 create-launch-template-version --launch-template-name <name> \
  --source-version 1 --launch-template-data '{"InstanceType":"t3.small"}'
aws ec2 run-instances --launch-template LaunchTemplateName=<name>,Version='$Latest' \
  --count 1
```

- Filter syntax differs from `--query`: `--filters` is server-side
  `Name=...,Values=...`; `--query` is client-side JMESPath.

## ECS — deploy & `execute-command`

```bash
# Roll out a new task-definition revision (force redeploy)
aws ecs register-task-definition --cli-input-json file://taskdef.json
aws ecs update-service --cluster <cluster> --service <service> \
  --task-definition <family>:<rev> --force-new-deployment
aws ecs wait services-stable --cluster <cluster> --services <service>

# Exec into a running task (requires execute-command enabled on the service/task)
aws ecs execute-command --cluster <cluster> --task <task-id> \
  --container <name> --interactive --command "/bin/sh"
```

- `update-service --force-new-deployment` redeploys the same task def (e.g. to
  pull a moved image tag) without a new revision.

## Lambda — deploy, invoke, decode logs

```bash
# Deploy code (zip) then wait until the update is applied
aws lambda update-function-code --function-name <name> --zip-file fileb://fn.zip
aws lambda wait function-updated-v2 --function-name <name>

# Invoke synchronously and capture the response payload
aws lambda invoke --function-name <name> --payload '{"k":"v"}' \
  --cli-binary-format raw-in-base64-out /tmp/out.json
cat /tmp/out.json

# Get the tail of the execution log inline (base64-encoded in LogResult)
aws lambda invoke --function-name <name> --log-type Tail \
  --query 'LogResult' --output text /tmp/out.json | base64 --decode
```

- `--cli-binary-format raw-in-base64-out` lets you pass a raw JSON `--payload`
  (v2 CLI defaults to base64).
- `LogResult` (from `--log-type Tail`) is **base64** — decode it as shown.

## IAM — policy simulation & least privilege

```bash
# Will this principal be allowed to perform an action on a resource?
aws iam simulate-principal-policy \
  --policy-source-arn <principal-arn> \
  --action-names s3:GetObject s3:PutObject \
  --resource-arns <resource-arn> \
  --query 'EvaluationResults[].{Action:EvalActionName,Decision:EvalDecision}' \
  --output table

# Find unused permissions to trim toward least privilege
aws iam generate-service-last-accessed-details --arn <policy-or-role-arn>
```

- Simulate **before** granting/denying in production; it evaluates identity +
  resource + SCP/permission-boundary effects without making a real call.
- Prefer scoped resource ARNs and condition keys over `Resource: "*"`.

## CloudFormation — `deploy`, change sets, drift

```bash
# Idempotent deploy (creates or updates; computes its own change set)
aws cloudformation deploy --template-file template.yaml --stack-name <stack> \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides Key1=<v1> Key2=<v2>

# Explicit change set: review before executing
aws cloudformation create-change-set --stack-name <stack> \
  --change-set-name <cs> --template-body file://template.yaml \
  --capabilities CAPABILITY_IAM
aws cloudformation describe-change-set --stack-name <stack> --change-set-name <cs> \
  --query 'Changes[].ResourceChange.{Action:Action,Type:ResourceType,Id:LogicalResourceId}' \
  --output table
aws cloudformation execute-change-set --stack-name <stack> --change-set-name <cs>

# Drift detection
aws cloudformation detect-stack-drift --stack-name <stack>   # returns a StackDriftDetectionId
aws cloudformation describe-stack-resource-drifts --stack-name <stack> \
  --stack-resource-drift-status-filters MODIFIED DELETED \
  --query 'StackResourceDrifts[].{Id:LogicalResourceId,Status:StackResourceDriftStatus}' \
  --output table
```

- `deploy` is the simplest path; use explicit change sets when you must review
  the diff before applying.
- Drift detection is asynchronous — poll
  `describe-stack-drift-detection-status` with the returned id before reading
  results.
