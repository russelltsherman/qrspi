# RBAC & Projects

Deep reference for scoping who can do what in Argo CD via AppProjects and RBAC. Loaded
on demand from the skill body's RBAC & Projects section.

## AppProjects: the scoping boundary

An **AppProject** is the unit of multi-tenancy. It constrains the Applications assigned
to it along three axes:

- **Source repos** — which Git repositories apps in this project may deploy from.
- **Destinations** — which `(cluster, namespace)` pairs apps may deploy to.
- **Allowed resource kinds** — cluster-scoped and namespaced kinds apps may manage
  (whitelist/blacklist).

Putting a team's apps in their own project means a misconfigured Application physically
cannot deploy from an unapproved repo or into another team's namespace.

```bash
argocd proj list
argocd proj get payments
argocd proj create payments \
  --dest https://kubernetes.default.svc,payments-* \
  --src https://github.com/acme/payments-manifests.git
```

## Project-scoped roles and tokens

Define roles **inside** a project and mint tokens bound to them, so CI/automation gets
only the permissions of that role within that one project (ties back to
`references/authentication.md`).

```bash
argocd proj role create payments ci
argocd proj role add-policy payments ci \
  --action sync --permission allow --object 'payments/*'
argocd proj role create-token payments ci --expires-in 720h
```

## SSO group mapping

Map identity-provider groups to Argo CD roles in `argocd-rbac-cm`. Reference the SSO
group by its claim value; the built-in roles are `role:admin` and `role:readonly`, or
your own custom roles.

```
# argocd-rbac-cm (policy.csv)
g, acme:platform-admins, role:admin
g, acme:payments-devs,   role:payments-deployer
p, role:payments-deployer, applications, sync, payments/*, allow
```

## Deny-all default

**Argo CD's RBAC default is deny-all.** Anything not explicitly granted by a `p` (policy)
or `g` (group) line is denied. The fallback is controlled by `policy.default` in
`argocd-rbac-cm`; leave it empty (or `role:''`) so unmatched requests are denied rather
than silently allowed. Grant least privilege explicitly; never set a permissive default.

## Validate before trusting

```bash
# Lint the RBAC policy for syntax/structure errors
argocd admin settings rbac validate --policy-file policy.csv

# Simulate: can this subject perform this action on this object?
argocd admin settings rbac can role:payments-deployer sync 'payments/web' \
  --policy-file policy.csv
```

`rbac validate` catches malformed policy lines before they ship; `rbac can` answers
concrete authorization questions ("can the deployer role sync this app?") so you verify
grants instead of guessing.
