# Terraform Refactoring: import, moved, removed

In Terraform a resource's *address* is its identity. Rename it carelessly in HCL and
Terraform reads the change as "destroy the old thing, create a new thing" — which on
live infrastructure means an outage or data loss. The declarative refactoring blocks
(`import`, `moved`, `removed`) let you change configuration while telling Terraform
the underlying infrastructure is unchanged, so the plan is a safe no-op at the cloud
level. This file covers each block, the small-batch discipline that keeps them safe,
and the plan-before-apply checks that confirm you got it right.

## 1. import — adopt existing infrastructure

Use when real infrastructure already exists (created by hand, by another tool, or by
a different state) and you want Terraform to manage it without recreating it.

Prefer the **declarative `import {}` block** — it shows up in `plan`, is reviewable,
and is removed after a successful apply:

```hcl
import {
  to = aws_s3_bucket.assets
  id = "acme-assets-prod"        # the provider's import ID for this resource
}

resource "aws_s3_bucket" "assets" {
  bucket = "acme-assets-prod"
  # fill in arguments to match the live resource so the plan shows no changes
}
```

`terraform plan` then reports the import and any drift between your HCL and reality;
adjust the config until the plan shows *import + no changes* before applying.

The imperative form still exists for one-offs but isn't reviewable in a PR:

```bash
terraform import aws_s3_bucket.assets acme-assets-prod
```

To scaffold config for many resources, `terraform plan -generate-config-out=gen.tf`
will emit starter HCL for `import` blocks — review and clean it up before committing.

## 2. moved — change a resource's address safely

Use when a resource's Terraform address changes but the real resource does not:
a rename, moving a resource into or out of a module, or switching `count` to
`for_each`. The `moved {}` block tells Terraform to update *state* (re-point the
address) instead of destroying and recreating.

Rename:

```hcl
moved {
  from = aws_instance.web
  to   = aws_instance.frontend
}
```

Into a module:

```hcl
moved {
  from = aws_instance.frontend
  to   = module.web.aws_instance.this
}
```

`count` → `for_each` (indexes become keys):

```hcl
moved {
  from = aws_instance.app[0]
  to   = aws_instance.app["us-east-1a"]
}
```

Keep `moved` blocks in the config until every consumer/state has applied them; they
are harmless once the move is reflected everywhere, and removing them too early on a
not-yet-migrated state re-triggers a destroy/create.

## 3. removed — stop managing without destroying

Use when you want Terraform to forget a resource (drop it from state) but **leave the
real infrastructure running** — e.g. handing ownership to another team or another
configuration. This replaces the older `terraform state rm` for the in-config case
and is reviewable in a plan.

```hcl
removed {
  from = aws_s3_bucket.legacy

  lifecycle {
    destroy = false      # forget it; do NOT delete the real bucket
  }
}
```

Delete the corresponding `resource` block at the same time. Setting `destroy = true`
(or omitting it, depending on version) will actually delete the infrastructure —
double-check this when the intent is to keep the resource.

## 4. Refactor in small batches

Large refactors fail in confusing ways: one bad address hides in a wall of plan
output and you can't tell a safe move from an accidental destroy. Keep each change
reviewable:

- Make **one logical refactor per PR** (one rename, one module extraction, one batch
  of related imports) rather than reshuffling everything at once.
- Land the `moved`/`import`/`removed` blocks and the corresponding `resource` edits
  **together**, so the state transition and the config always agree.
- For bulk imports, do them in small groups and verify each group before the next.

## 5. Plan-before-apply discipline

This is the safety net for every refactor. Before applying any of the above:

- Run `terraform plan` and **read it fully**. The expected outcome for a pure
  refactor is: the intended moves/imports, and **zero** `destroy` or `-/+` (replace)
  operations on resources you meant to keep.
- If you see an unexpected destroy/replace, **stop** — the address mapping is wrong.
  Fix the `moved`/`import` block or the config; never "just apply and recreate it."
- Save the plan (`-out=tfplan`) and apply that exact file, so the apply can't diverge
  from what you reviewed.
- Back up state first for risky changes: `terraform state pull > backup.tfstate`.
