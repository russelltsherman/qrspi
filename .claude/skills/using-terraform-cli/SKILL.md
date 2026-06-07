---
name: using-terraform-cli
description: "Author, run, and operate Terraform safely from the command line. Use whenever the user is writing or running Terraform / OpenTofu (HCL, .tf files), managing infrastructure as code, configuring remote state or backends, pinning provider/Terraform versions, refactoring resources with import/moved/removed, wiring Terraform into CI/CD, handling secrets in IaC, or operating workspaces and modules. Trigger on any of: terraform init/plan/apply/destroy, 'terraform state', backend setup, .terraform.lock.hcl, tfstate, OIDC for Terraform, terraform import, terraform test, or 'is this Terraform safe to apply'."
command: /using-terraform-cli
argument-hint: <what you want to do with Terraform>
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Using the Terraform CLI

This skill captures how to operate Terraform (and the API-compatible OpenTofu) from
the command line the way a careful platform engineer does: predictable lifecycle,
state treated as production data, pinned versions, reviewable changes, and secrets
that never leak. The goal is not to teach HCL syntax — it is to make every
`terraform` invocation safe, repeatable, and auditable.

**Why this matters:** Terraform's failure modes are quiet and expensive. A
clobbered state file, an unpinned provider that changes behavior overnight, or a
plan applied without review can destroy or recreate live infrastructure. The
practices below exist to make those outcomes structurally hard.

## Scope

This skill covers the **CLI lifecycle and operational conventions** only. It
deliberately excludes:

- Provider-specific resource configuration (e.g. how to set up an `aws_eks_cluster`
  argument-by-argument) — read the provider docs for that.
- CDK for Terraform (CDKTF) and other non-HCL authoring layers.
- HCL language deep-dives (expressions, `for`/`for_each` semantics, dynamic blocks).

If a request is really about one of those, say so and point elsewhere rather than
forcing it through this skill.

## Core workflow / lifecycle

The everyday loop is `init → validate → plan → apply`, with `destroy` for teardown.
Run these from the directory holding the root module (or pass `-chdir`).

1. **`terraform init`** — downloads providers and modules, configures the backend,
   and writes/reads `.terraform.lock.hcl`. Run it after cloning, after changing
   providers/modules, or after changing the backend. Use `-upgrade` only when you
   intend to move provider versions (it rewrites the lock file). Use
   `-backend-config=...` for partial backend config (see `references/backend-setup.md`).

2. **`terraform fmt -recursive`** then **`terraform validate`** — `fmt` normalizes
   style so diffs stay reviewable; `validate` checks the config is internally
   consistent (it does **not** talk to the cloud, so it can't catch everything).

3. **`terraform plan -out=tfplan`** — computes the change set. Always write the plan
   to a file when you intend to apply it, so the apply executes *exactly* what was
   reviewed rather than re-planning against drifted state. Read the plan: pay
   attention to anything marked **destroy** or **replace** (`-/+`) — those are the
   operations that cause outages.

4. **`terraform apply tfplan`** — applies the saved plan with no further prompts
   (the plan file is the approval). For interactive use, `terraform apply` will
   plan-then-prompt; never pipe `yes` into it in automation — gate on a reviewed
   saved plan instead.

5. **`terraform destroy`** — tears everything down. Treat it as a loaded gun in any
   shared/production workspace; prefer `terraform plan -destroy -out=...` first so
   the deletion set is reviewed.

Useful adjuncts: `terraform show tfplan` (human-readable plan), `terraform output`
(read root outputs), `terraform console` (evaluate expressions), and
`terraform state list` (inspect tracked resources).

## State management

State is the single source of truth Terraform uses to map config to real
infrastructure. **Treat the state file as sensitive production data**, because it
is: it can contain secrets (DB passwords, keys) in plaintext, and corrupting or
losing it means Terraform no longer knows what it owns.

Core conventions:

- **Use a remote backend, never local state**, for anything shared or production.
  Local `terraform.tfstate` doesn't lock, doesn't version, and lives on one laptop.
- **Enable state locking** so two applies can't race and corrupt state (S3 native
  lockfile or DynamoDB for AWS; the backend handles it for GCS/Azure/HCP).
- **Encrypt at rest** (SSE-KMS on S3, CMEK on GCS, etc.) and **enable bucket
  versioning** so a bad write can be rolled back.
- **Lock down IAM** to the principals that actually run Terraform; state buckets are
  high-value targets.
- **Never commit state** — `.terraform/`, `*.tfstate`, `*.tfstate.backup`, and
  `crash.log` belong in `.gitignore`. The `.terraform.lock.hcl` file is the
  exception: commit it (see Version pinning).

Full backend examples (S3+DynamoDB canonical, plus GCS / Azure / HCP equivalents,
partial config, and the encryption/versioning/IAM setup) are in
`references/backend-setup.md`.

When you must touch state directly (`terraform state mv`, `rm`, `import`), back it
up first (`terraform state pull > backup.tfstate`) — these commands are surgical and
unforgiving.

## Version pinning

Unpinned versions are a leading cause of "it worked yesterday." Pin three things:

- **Providers** via `required_providers` with a constraint that allows patches but
  not surprises, e.g. `version = "~> 5.40"`. The exact resolved versions are then
  frozen in `.terraform.lock.hcl`.
- **Terraform/OpenTofu itself** via `required_version = ">= 1.9, < 2.0"` so the
  config refuses to run on an incompatible CLI.
- **The CLI binary per project** with a version manager — `tfenv`, `asdf`, or a
  `.terraform-version` file — so every contributor and CI runner uses the same CLI.

```hcl
terraform {
  required_version = ">= 1.9, < 2.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.40"
    }
  }
}
```

**Commit `.terraform.lock.hcl`.** It records the exact provider versions and their
checksums, so `terraform init` is reproducible and supply-chain-verified across
machines. When you intentionally upgrade, run `terraform init -upgrade`, review the
lock-file diff, and commit it as its own reviewable change. For multi-platform teams,
`terraform providers lock -platform=...` records hashes for every OS/arch so CI on
Linux and laptops on macOS validate against the same lock.

## Refactoring & migration

Terraform's address is identity: rename a resource in HCL naively and Terraform
sees a *delete + create*, which can destroy live infrastructure. Use the
declarative refactoring blocks so changes are no-ops at the infrastructure level.

- **`import`** — bring existing, unmanaged infrastructure under Terraform. Prefer the
  declarative `import {}` block (plannable, reviewable) over the imperative
  `terraform import` command.
- **`moved`** — record that a resource changed address (rename, moved into/out of a
  module, `count`→`for_each`). Terraform updates state instead of recreating.
- **`removed`** — drop a resource from Terraform's management without destroying the
  real infrastructure (`removed {}` with `lifecycle { destroy = false }`).

The discipline that keeps this safe: **refactor in small batches and always
plan-before-apply**, confirming the plan shows the moves/imports you expect and
*zero* unexpected destroys. Detailed patterns and worked examples are in
`references/migration-blocks.md`.

## CI/CD

Running Terraform in a pipeline turns infrastructure changes into reviewable,
audited pull requests. The canonical shape:

- **Auth via OIDC**, not long-lived cloud keys. The CI provider (GitHub Actions,
  GitLab, etc.) exchanges a short-lived OIDC token for a cloud role — no static
  secrets to leak or rotate.
- **Plan on pull request**, post the plan as a PR comment/artifact, and require human
  approval before apply. The apply step consumes the *saved plan artifact* from the
  plan stage so it applies exactly what was reviewed.
- **Stage order:** `fmt -check` / `validate` → security scan → `plan -out` →
  (manual approval gate) → `apply` the saved plan.
- **Security scanning** (tfsec / Trivy / Checkov) runs before plan so misconfigured
  resources are caught at review time.

Stage-by-stage pipeline structure, the OIDC trust setup, approval gates, and how to
pass the plan artifact between stages are in `references/cicd-pipelines.md`.

## Secrets management & security hardening

Secrets must never live in `.tf` files, `.tfvars` committed to git, or plan output.

- **Fetch secrets at runtime** from a secrets manager via data sources
  (`aws_secretsmanager_secret_version`, `vault_*`, etc.) rather than hardcoding them.
  Note that values read this way still land in state — which is why state is
  encrypted and access-controlled.
- **Prefer ephemeral values** (Terraform 1.10+: `ephemeral` resources and
  write-only arguments) for secrets that should *not* be persisted to state at all.
  This is the strongest control when a provider supports it.
- **Mark module/output secrets `sensitive = true`** so they're redacted from CLI and
  log output.
- **Use OIDC / workload identity** for cloud auth (see CI/CD) and apply
  **least-privilege IAM** to both the Terraform runner and the state backend.
- **Enable audit logging** (CloudTrail / equivalent) on the state backend and the
  Terraform execution role so every change is attributable.

## Workspaces vs. environments

Terraform CLI workspaces (`terraform workspace new/select`) give you multiple state
files from one configuration. They are **fine for ephemeral, low-risk variants**
(a quick dev sandbox, a feature-branch copy), but they are a poor fit for strong
prod/staging separation: they share the same backend, the same code path, and one
fat-fingered `workspace select` can apply staging changes to prod.

For durable environment separation, prefer **separate root modules / state
backends per environment** (e.g. `environments/prod`, `environments/staging`, each
with its own backend config and variables), so blast radius is bounded by
construction and IAM can differ per environment.

## Modules & testing

- **Author reusable modules** with explicit `variables.tf` / `outputs.tf`, a clear
  README, and pinned provider requirements. Mark sensitive inputs and outputs
  `sensitive = true` so they don't leak through logs.
- **Test modules** with the native test framework: write `*.tftest.hcl` files and
  run `terraform test`. Use `command = plan` assertions for fast checks that don't
  create real resources, and `command = apply` (against a disposable account) for
  end-to-end validation. This catches contract regressions before consumers do.

Keep modules focused — a module that tries to do everything is hard to test and
reuse. Compose small modules in the root configuration instead.
