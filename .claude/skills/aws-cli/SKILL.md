---
name: aws-cli
description: "Operational guidance for the AWS Command Line Interface (`aws` v2): authentication and named profiles, output shaping with `--query`/`--output`, pagination, waiters, per-service operations (S3, EC2, ECS, Lambda, IAM, CloudFormation), error handling, scripting, and security. Use when running, writing, scripting, or debugging `aws` CLI commands — authenticating with SSO or assumed roles, filtering or formatting CLI output, waiting on resource state, deploying/inspecting AWS resources from the shell, or troubleshooting CLI exit codes and credentials. Trigger on tasks like 'run an aws command', 'query/filter aws CLI output', 'set up an aws profile', 'assume a role with the CLI', 'wait for the stack/service', or 'script against AWS from bash'."
command: /aws-cli
argument-hint: "[topic e.g. s3 | ec2 | profiles | query]"
allowed-tools: Read, Bash
---

# AWS CLI (`aws` v2)

Operational guidance for driving AWS from the shell with the v2 `aws` CLI. This
file is the concise index of imperatives; deep per-topic detail lives in
`references/`:

- `references/jmespath.md` — `--query`/JMESPath patterns and `--output` shaping.
- `references/waiters.md` — built-in waiters per service + exit-code-255 timeouts.
- `references/services.md` — per-service cheat sheets (S3/EC2/ECS/Lambda/IAM/CFN).

Read the matching reference file before composing anything non-trivial in that
area. All examples use placeholder tokens (`<name>`, `i-xxx`, `<arn>`) — never
embed real account IDs, regions, or resource names.

## Scope

In scope: the raw `aws` CLI (v2) and its `s3api`/service subcommands for
authentication, querying, and resource operations from the shell.

Out of scope: infrastructure-as-code tooling — **Terraform, AWS CDK, and
Pulumi** are not covered here. For repeatable infrastructure prefer those tools;
this skill is for direct CLI operations, inspection, and scripting.

## Authentication & Profiles

- **Prefer IAM Identity Center (SSO) over long-lived IAM access keys.** Configure
  with `aws configure sso`, then sign in with `aws sso login --profile <name>`.
- **Verify who you are before acting**, especially in scripts that mutate state:

  ```bash
  aws sts get-caller-identity --query 'Arn' --output text
  ```

- **Named profiles** select an identity/config set. Pass `--profile <name>` or
  set `AWS_PROFILE=<name>`. Profiles live in `~/.aws/config` and (for static
  keys) `~/.aws/credentials`.
- **Assume a role** by configuring a profile that chains from a source:

  ```ini
  # ~/.aws/config
  [profile <name>]
  role_arn       = <role-arn>
  source_profile = <base-profile>     # or: sso_session = <session>
  external_id    = <external-id>      # only if the trust policy requires it
  ```

  The CLI assumes the role automatically when the profile is used.
- **CI/CD** should assume a role via OIDC/instance/web-identity credentials, not
  baked-in keys. On EC2/ECS/Lambda the CLI picks up the task/instance role from
  the metadata endpoint with no profile needed.
- Credential resolution order (first match wins): explicit `--profile`/env vars →
  env credentials → shared config/credentials files → SSO cache → container/EC2
  role. `Do NOT` mix conflicting sources expecting a specific one to win.

## Environment & Config

- Common env vars: `AWS_PROFILE`, `AWS_REGION` / `AWS_DEFAULT_REGION`,
  `AWS_PAGER`, `AWS_MAX_ATTEMPTS`, `AWS_RETRY_MODE`, `AWS_ENDPOINT_URL`.
- Region is required for most calls — set it per command (`--region <region>`),
  per profile, or via `AWS_REGION`. Use a placeholder `<region>`, never a
  hard-coded real region, in shared scripts.
- Inspect effective config with `aws configure list` and
  `aws configure get <key> --profile <name>`.
- `--debug` prints the full wire/credential resolution trace when diagnosing.

## Output Formatting & Filtering

- `--output {json|text|table|yaml}` chooses the rendering;
  **`--query '<JMESPath>'`** filters/reshapes it **client-side**.
- Disable the interactive pager for non-interactive/script use:

  ```bash
  export AWS_PAGER=""          # or pass --no-cli-pager per command
  ```

- Quick shapes (full patterns in `references/jmespath.md`):

  ```bash
  aws ec2 describe-instances \
    --query 'Reservations[].Instances[].InstanceId' --output text
  aws s3api list-buckets \
    --query 'Buckets[].{Name:Name,Created:CreationDate}' --output table
  ```

- For pipelines use `--output text` (tab-separated, stable column order from a
  multi-select **list** `[a,b]`); for humans use `--output table` with a
  multi-select **hash** `{X:a}`. See `references/jmespath.md` for filters, tag
  matching, and date-range queries.

## Pagination

- The CLI **auto-paginates** by default (with the pager off it prints all pages).
- Control it explicitly in scripts:

  ```bash
  aws s3api list-objects-v2 --bucket <bucket> \
    --page-size 100 --max-items 500 \
    --query 'Contents[].Key' --output text
  ```

  - `--page-size` = items per API call (tuning, not a result cap).
  - `--max-items` = total items the CLI returns; it then emits a `NextToken`.
  - Resume with `--starting-token <token>`.
- `--no-paginate` returns only the first page (plus the raw `NextToken`) — use
  when you want to drive paging yourself.
- Prefer server-side `--filters`/`--prefix` to shrink results before `--query`.

## Waiters

- A waiter blocks until a resource reaches a state, then exits `0`; on the
  attempt-budget timeout it exits **`255`**. Form:
  `aws <service> wait <condition> --<selector> ...`.

  ```bash
  aws cloudformation wait stack-create-complete --stack-name <stack>
  aws ecs wait services-stable --cluster <cluster> --services <service>
  ```

- **Always branch on the exit code** — a `255` means "did not reach state in the
  attempt budget", not success. See `references/waiters.md` for the per-service
  waiter list and the timeout-handling pattern. List with
  `aws <service> wait help`.

## Per-Service Operations

Concise directives below; full cheat sheets in `references/services.md`.

- **S3** — use high-level `aws s3` (`cp`/`sync`, `--dryrun`) for transfers; drop
  to `aws s3api` for object metadata, versioning, policies, and lifecycle.
- **EC2** — reduce results **server-side** with `--filters Name=...,Values=...`
  then shape with `--query`; tag via `create-tags`; launch from launch templates.
- **ECS** — `update-service --force-new-deployment` to roll out; follow with
  `wait services-stable`; `execute-command` to shell into a task (must be enabled).
- **Lambda** — `update-function-code` then `wait function-updated-v2`; invoke with
  `--cli-binary-format raw-in-base64-out`; decode `--log-type Tail` `LogResult`
  from base64.
- **IAM** — `simulate-principal-policy` to test access **before** changing it;
  scope resource ARNs and conditions toward least privilege.
- **CloudFormation** — `deploy` for idempotent create/update; explicit change
  sets when the diff must be reviewed; `detect-stack-drift` (async) for drift.

## Error Handling & Scripting

- **Check exit codes.** `0` = success; `255` = command/CLI failure (incl. waiter
  timeout and most service errors); `2` = CLI usage/parse error;
  `130` = interrupted. `Do NOT` assume success without checking `$?`.
- In scripts, fail fast and surface the real error:

  ```bash
  set -euo pipefail
  export AWS_PAGER=""
  if ! out=$(aws s3api head-object --bucket <bucket> --key <key> 2>&1); then
    echo "head-object failed: $out" >&2; exit 1
  fi
  ```

- **Retries:** the CLI retries throttling/5xx using `AWS_RETRY_MODE`
  (`standard`/`adaptive`) and `AWS_MAX_ATTEMPTS`. Tune rather than hand-rolling
  retry loops for throttling.
- **Idempotency:** prefer idempotent operations — `s3 sync`, `cloudformation
  deploy`, and client-request-token / `--client-token` parameters — so re-running
  a failed script is safe. `Do NOT` write scripts that double-apply on retry.
- Parse output with `--query` (client-side) or pipe JSON to `jq`; guard empty
  `--output text` results (`[ -n "$out" ]`) before looping.

## Security

- `Do NOT` commit, log, or echo credentials, access keys, or session tokens.
- **Never** hard-code long-lived IAM access keys in scripts, env files, or CI
  config — use SSO or assumed roles.
- `Do NOT` embed real account IDs, ARNs, or resource names in shared
  scripts/docs — use placeholders (`<arn>`, `i-xxx`).
- **Never** widen IAM to `Resource: "*"` / `Action: "*"` for convenience; scope
  to the minimum and verify with `simulate-principal-policy`.
- `Do NOT` disable TLS verification (`--no-verify-ssl`) outside isolated local
  testing.
- **Never** pass secrets on the command line where they land in shell history or
  the process list — read from a file (`fileb://`/`file://`) or stdin, and rotate
  anything that leaks.
- Sign out of shared/CI hosts when done: `aws sso logout`.
