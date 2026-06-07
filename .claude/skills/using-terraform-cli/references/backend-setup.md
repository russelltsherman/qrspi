# Terraform Remote Backend Setup

Remote state is the foundation of safe, collaborative Terraform: it gives you
locking (no concurrent-apply corruption), encryption, versioning (rollback), and a
shared source of truth. This file shows the canonical AWS setup plus equivalents for
the other major backends, partial configuration for keeping secrets out of code, and
the encryption / versioning / IAM hardening that makes state durable and private.

## 1. Canonical AWS backend (S3 + locking)

The reference setup for AWS. Modern Terraform (1.10+) can lock with an S3 object
directly via `use_lockfile`, removing the separate DynamoDB table; the DynamoDB form
is still common and shown after.

```hcl
terraform {
  backend "s3" {
    bucket       = "acme-tfstate-prod"
    key          = "network/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true            # SSE; pair with kms_key_id for CMK
    kms_key_id   = "arn:aws:kms:us-east-1:111122223333:key/abcd-1234"
    use_lockfile = true            # S3-native state locking (Terraform >= 1.10)
  }
}
```

DynamoDB-based locking (works on all versions):

```hcl
terraform {
  backend "s3" {
    bucket         = "acme-tfstate-prod"
    key            = "network/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    kms_key_id     = "arn:aws:kms:us-east-1:111122223333:key/abcd-1234"
    dynamodb_table = "acme-tfstate-locks"   # PK: LockID (String)
  }
}
```

The `key` is the path of this state within the bucket; give each root module a
distinct key so states never collide.

## 2. Bootstrapping the backend resources

The bucket, KMS key, and lock table must exist before the backend can use them —
classic chicken-and-egg. Create them with a small, *separately stated* bootstrap
configuration (often with local state, applied once), then have every other config
point at the bucket.

```hcl
resource "aws_s3_bucket" "tfstate" {
  bucket = "acme-tfstate-prod"
}

resource "aws_s3_bucket_versioning" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.tfstate.arn
    }
  }
}

resource "aws_s3_bucket_public_access_block" "tfstate" {
  bucket                  = aws_s3_bucket.tfstate.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_dynamodb_table" "tfstate_locks" {
  name         = "acme-tfstate-locks"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"
  attribute {
    name = "LockID"
    type = "S"
  }
}
```

## 3. Partial configuration (keep specifics out of code)

Leave environment-specific or sensitive values out of the committed backend block
and supply them at init time. This keeps one configuration reusable across
environments and avoids hardcoding account-specific values.

```hcl
# backend.tf — committed, no environment specifics
terraform {
  backend "s3" {}
}
```

```hcl
# prod.s3.tfbackend — per-environment, supplied at init
bucket       = "acme-tfstate-prod"
key          = "network/terraform.tfstate"
region       = "us-east-1"
encrypt      = true
use_lockfile = true
```

```bash
terraform init -backend-config=prod.s3.tfbackend
```

You can also pass discrete `-backend-config="key=value"` flags. Never commit a
`.tfbackend` file containing secrets; reference a KMS key by ARN rather than
embedding credentials.

## 4. GCS backend (Google Cloud) equivalent

GCS provides locking natively — no separate lock resource needed.

```hcl
terraform {
  backend "gcs" {
    bucket = "acme-tfstate-prod"
    prefix = "network"               # path within the bucket
    # encryption via bucket CMEK / Google-managed keys configured on the bucket
  }
}
```

Enable object versioning and a customer-managed encryption key on the bucket, and
restrict access with IAM (`roles/storage.objectAdmin` scoped to the bucket).

## 5. Azure backend (azurerm) equivalent

Azure Blob Storage provides leasing-based locking automatically.

```hcl
terraform {
  backend "azurerm" {
    resource_group_name  = "acme-tfstate-rg"
    storage_account_name = "acmetfstateprod"
    container_name       = "tfstate"
    key                  = "network.terraform.tfstate"
    use_oidc             = true       # auth via workload identity
  }
}
```

Enable blob versioning and soft delete on the storage account, encryption with a
Key Vault CMK, and scope access with Azure RBAC.

## 6. HCP Terraform / Terraform Enterprise equivalent

HCP Terraform manages state, locking, encryption, and versioning for you, and can
also run plans/applies remotely.

```hcl
terraform {
  cloud {
    organization = "acme"
    workspaces {
      name = "network-prod"
    }
  }
}
```

## 7. Encryption, versioning, and IAM checklist

Apply these regardless of backend — they are what make state safe to rely on:

- **Encryption at rest:** SSE-KMS (S3), CMEK (GCS), Key Vault CMK (Azure). Prefer a
  customer-managed key so you control rotation and access.
- **Versioning:** enable object/blob versioning so a corrupt or accidental write can
  be rolled back to a prior state version.
- **Least-privilege IAM:** grant read/write on the state bucket and lock table only
  to the Terraform execution role(s) and the humans who break-glass. Deny public
  access explicitly. The state bucket is a top-tier secret store — treat it like one.
- **Audit logging:** enable access logging / CloudTrail (or cloud equivalent) on the
  state store so every read and write is attributable.
- **Lifecycle:** add an expiration/transition policy for old state versions so the
  version history doesn't grow unbounded, but keep enough history to recover.
