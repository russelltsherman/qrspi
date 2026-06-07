# OIDC Setup Patterns

Use GitHub's OIDC provider to obtain **short-lived cloud credentials** at runtime
instead of storing long-lived static cloud secrets (access keys, service-account
JSON) in repository/organization secrets. The workflow presents a signed OIDC
token; the cloud provider exchanges it for temporary credentials scoped by a trust
policy you control.

## Prerequisite — grant the token `id-token` scope

OIDC requires the job to request an ID token:

```yaml
permissions:
  id-token: write    # REQUIRED to mint the OIDC token
  contents: read
```

Without `id-token: write` the auth step fails. Keep it on the **deploy job only**.

## AWS — assume an IAM role (no static keys)

1. Create an IAM OIDC identity provider for `token.actions.githubusercontent.com`.
2. Create an IAM role with a trust policy conditioned on
   `token.actions.githubusercontent.com:sub` (e.g. `repo:OWNER/REPO:ref:refs/heads/main`
   or `repo:OWNER/REPO:environment:production`).

```yaml
- uses: aws-actions/configure-aws-credentials@e3dd6a429d7300a6a4c196c26e071d42e0343502 # v4.0.2
  with:
    role-to-assume: arn:aws:iam::123456789012:role/github-deploy
    aws-region: us-east-1
    # no aws-access-key-id / aws-secret-access-key
```

## GCP — Workload Identity Federation

1. Create a Workload Identity Pool + provider mapping
   `attribute.repository` / `google.subject` to the GitHub claim.
2. Allow the GitHub principal to impersonate a service account (or use direct
   resource access).

```yaml
- uses: google-github-actions/auth@71f986410dfbc7added4569d411d040a91dc6935 # v2.1.8
  with:
    workload_identity_provider: projects/123/locations/global/workloadIdentityPools/gh/providers/gh
    service_account: deployer@my-project.iam.gserviceaccount.com
```

## Azure — federated credentials

1. On an App Registration / user-assigned managed identity, add a **federated
   credential** with subject `repo:OWNER/REPO:environment:production`.
2. Grant that identity the needed Azure RBAC roles.

```yaml
- uses: azure/login@a457da9ea143d694b1b9c7c869ebb04ebe844ef5 # v2.3.0
  with:
    client-id: ${{ vars.AZURE_CLIENT_ID }}
    tenant-id: ${{ vars.AZURE_TENANT_ID }}
    subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}
    # no client-secret
```

## GitHub Environments + OIDC (recommended for deploys)

Bind the cloud trust policy to a GitHub **Environment** (`environment: production`)
rather than a branch. Environments add:

- **Required reviewers** — a human approves before credentials are mintable.
- **Deployment branch rules** — only protected branches can target the env.
- **Environment-scoped variables/secrets** — narrowest blast radius.

```yaml
jobs:
  deploy:
    environment: production        # gates the job + scopes the OIDC trust
    permissions:
      id-token: write
      contents: read
```

The `:sub` claim then reads `repo:OWNER/REPO:environment:production`, so leaked
workflow code on a feature branch cannot assume the production role.

## Why OIDC over static secrets

- No long-lived credentials to rotate, leak, or exfiltrate.
- Credentials expire in minutes; trust is scoped to repo + ref/environment.
- Auditable: cloud logs show the exact GitHub subject that assumed the role.

All action SHAs above are illustrative — re-pin to the current release SHA and
keep the `# vX.Y.Z` comment (see `security-hardening-checklist.md` §1).
