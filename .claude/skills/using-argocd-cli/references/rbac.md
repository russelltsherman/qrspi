# Argo CD RBAC & Permissions

Self-contained reference for AppProjects and access control. Loaded from the "RBAC &
permissions" section of `SKILL.md`.

## Deny-all default

Argo CD's RBAC default policy is **deny-all** (`policy.default: role:''` or `role:readonly`
depending on install). A subject can do nothing until a policy grants it. So a "permission
denied" almost always means a missing grant, not a bug. Check RBAC first.

## AppProjects

An `AppProject` is the unit of multi-tenancy. It constrains which repos, destination
clusters/namespaces, and resource kinds its member Applications may use, and it carries
project-scoped roles.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata: { name: my-proj, namespace: argocd }
spec:
  sourceRepos: ['https://github.com/org/*']
  destinations:
    - { server: https://kubernetes.default.svc, namespace: 'my-*' }
  roles:
    - name: ci-deployer
      policies:
        - p, proj:my-proj:ci-deployer, applications, sync, my-proj/*, allow
```

An Application that violates its project's `sourceRepos`/`destinations` is rejected.

## RBAC policy format

Casbin-style lines in the `argocd-rbac-cm` ConfigMap (global) or in an AppProject role
(project-scoped):

```
p, <subject>, <resource>, <action>, <object>, allow|deny
g, <subject>, <role>          # group/role assignment
```

Example: `p, role:dev, applications, get, */*, allow`.

## JWT role tokens

Project role tokens are JWTs minted per role (see `authentication.md`):

```bash
argocd proj role create-token my-proj ci-deployer --expires-in 720h
```

The token's permissions are exactly the role's policies — least privilege by
construction.

## Validating permissions

```bash
argocd admin settings rbac validate --policy-file argocd-rbac-cm.yaml   # lint policy syntax
argocd admin settings rbac can role:dev sync 'my-proj/my-app'           # does subject X have action Y?
```

Use `rbac can` to confirm a grant before assuming a failure is non-RBAC.

## SSO mapping

SSO/OIDC group claims map to Argo CD roles via `g` lines:

```
g, my-org:platform-team, role:admin
```

The group string must match the IdP's claim exactly. A mismatched group name is a common
cause of "logged in but denied" — verify the claim against the `g` mapping.
