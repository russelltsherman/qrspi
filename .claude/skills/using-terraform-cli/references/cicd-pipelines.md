# Terraform in CI/CD Pipelines

Running Terraform in CI turns infrastructure changes into reviewable, audited pull
requests instead of someone's laptop applying to prod. This file lays out the
canonical pipeline stage order, OIDC-based authentication (so there are no
long-lived cloud keys), plan-on-PR with manual approval gates, security scanning,
and how to pass the saved plan artifact between stages so the apply executes exactly
what was reviewed.

## 1. Pipeline stage order

The stages, in order, with the principle behind each:

1. **`terraform fmt -check -recursive`** — fail fast on unformatted code so diffs
   stay clean and reviewable.
2. **`terraform init`** — configure the backend and download pinned providers
   (validated against the committed `.terraform.lock.hcl`).
3. **`terraform validate`** — catch internal config errors before doing real work.
4. **Security scan** (tfsec / Trivy / Checkov) — surface misconfigurations at review
   time, before a plan is even produced.
5. **`terraform plan -out=tfplan`** — compute the change set and **save it to a
   file**. Post a human-readable version (`terraform show -no-color tfplan`) as a PR
   comment or build artifact.
6. **Manual approval gate** — a human reviews the plan and approves. Nothing applies
   without this on protected environments.
7. **`terraform apply tfplan`** — apply the *saved* plan artifact. Because it's the
   exact reviewed plan, there are no surprises from re-planning against drifted state.

Plan stages run on every PR; apply runs only after merge/approval to a protected
branch or environment.

## 2. Authentication via OIDC (no static keys)

Long-lived cloud credentials in CI are a leak waiting to happen. Instead, the CI
provider issues a short-lived OIDC token that the cloud exchanges for a role. There
are no secrets to store or rotate.

GitHub Actions → AWS example:

```yaml
permissions:
  id-token: write      # required for the runner to request an OIDC token
  contents: read

jobs:
  plan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::111122223333:role/terraform-ci
          aws-region: us-east-1
      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: 1.9.8     # pin the CLI to match the project
```

The trust relationship on the cloud side restricts which repo/branch/environment
may assume the role:

```json
{
  "Effect": "Allow",
  "Principal": { "Federated": "arn:aws:iam::111122223333:oidc-provider/token.actions.githubusercontent.com" },
  "Action": "sts:AssumeRoleWithWebIdentity",
  "Condition": {
    "StringEquals": { "token.actions.githubusercontent.com:aud": "sts.amazonaws.com" },
    "StringLike":   { "token.actions.githubusercontent.com:sub": "repo:acme/infra:ref:refs/heads/main" }
  }
}
```

GitLab (`id_tokens` + `assume-role-with-web-identity`), Azure DevOps (workload
identity federation), and HCP Terraform (dynamic provider credentials) follow the
same pattern: short-lived token, scoped trust, least-privilege role.

## 3. Plan on PR, apply on merge

- On a pull request: run `init → validate → scan → plan -out=tfplan`, then surface
  the plan to reviewers (PR comment via `terraform show`, or upload `tfplan` plus a
  text rendering as artifacts).
- The plan job should use **read-only or plan-scoped** cloud permissions where
  possible, so a PR can never mutate infrastructure.
- On merge to the protected branch (or a manual `workflow_dispatch`): run the apply
  job, which assumes the higher-privilege apply role and consumes the saved plan.

## 4. Manual approval gates

Protected environments must require explicit human sign-off between plan and apply.
Use the platform's native gate:

- **GitHub Actions:** an `environment:` with required reviewers — the apply job
  blocks until an approver releases it.
- **GitLab:** a `manual` job (`when: manual`) on protected environments.
- **Azure DevOps:** environment approvals and checks.

The gate is what makes "infrastructure changes are peer-reviewed" a structural
guarantee rather than a convention.

## 5. Passing the plan artifact between stages

The plan and apply often run as separate jobs (different permissions, an approval
gate between them). The apply **must** consume the exact plan that was reviewed, not
re-plan — otherwise drift or a concurrent change could make apply diverge from what
the reviewer saw.

```yaml
# plan job
- run: terraform plan -out=tfplan
- uses: actions/upload-artifact@v4
  with:
    name: tfplan
    path: tfplan
    retention-days: 5

# apply job (after approval)
- uses: actions/download-artifact@v4
  with:
    name: tfplan
- run: terraform apply -input=false tfplan
```

Caveats: the apply job must `terraform init` against the **same backend and provider
lock** before consuming the plan, and saved plans are short-lived — apply promptly,
because a stale plan can be rejected if state has moved on. Treat the plan artifact
as sensitive; it can reveal resource attributes.

## 6. Security scanning

Run a static analyzer before plan so insecure configurations are caught during
review, not after apply:

- **tfsec / Trivy** — opinionated Terraform misconfiguration checks.
- **Checkov** — policy-as-code across many frameworks.
- Optionally enforce org policy with **OPA/Conftest** or **Sentinel** (HCP) against
  the plan JSON (`terraform show -json tfplan`) to gate on custom rules.

Fail the pipeline on high-severity findings; allow documented exceptions via inline
ignores so the gate stays trustworthy rather than routinely bypassed.
