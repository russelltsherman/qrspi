# RBAC Debugging Decision Tree

When an action is denied (`Error from server (Forbidden): ... cannot <verb> resource
"<resource>" in API group "<group>"`), walk this ordered tree. Stop at the first step
that explains the denial.

## 1. Confirm what is denied and for whom

Always start from the authoritative check, not from reading Role YAML by eye:

```sh
# Can the CURRENT identity do it?
kubectl auth can-i <verb> <resource> -n <namespace>

# Can a SPECIFIC subject do it? (impersonation; requires impersonate privilege)
kubectl auth can-i <verb> <resource> -n <namespace> --as <user>
kubectl auth can-i <verb> <resource> -n <namespace> --as=system:serviceaccount:<namespace>:<serviceaccount>

# What CAN this subject do? (full list)
kubectl auth can-i --list -n <namespace> --as=system:serviceaccount:<namespace>:<serviceaccount>
```

Identify the current identity itself with `kubectl whoami` (krew; see
`krew-plugins.md`) — many "Forbidden" surprises are a wrong context/identity.

## 2. Find the bindings that grant (or fail to grant) access

```sh
# Namespaced grants
kubectl get rolebindings,clusterrolebindings -A -o wide \
  | grep <subject-or-role>

# Inspect the (Cluster)Role's actual rules
kubectl describe clusterrole <role>
kubectl describe role <role> -n <namespace>
```

A binding must connect three things correctly: a **subject**, a **roleRef**, and (for
RoleBindings) a **namespace**. A ClusterRole referenced by a RoleBinding grants its
verbs only within that RoleBinding's namespace.

## 3. Validate the subject form

The single most common silent failure is a malformed subject. Verify exactly:

- ServiceAccount subject `name` is the bare SA name; the `namespace` field is required.
- The implicit username for a ServiceAccount is
  `system:serviceaccount:<namespace>:<serviceaccount>`.
- `kind` is one of `User`, `Group`, `ServiceAccount` (case-sensitive).
- User/Group names come from the authenticator and are **not** Kubernetes objects —
  a typo'd `User` name binds to nobody and fails silently (no error, no access).

## 4. If RBAC permits but traffic/requests still fail — look past RBAC

RBAC governs API-server authorization only. If `auth can-i` returns `yes` but the
workload still cannot act:

- **NetworkPolicy** — pod-to-pod or pod-to-apiserver traffic may be blocked.
  Inspect `kubectl get networkpolicy -A` and the pod's labels/namespace selectors.
- **Admission / validating webhook** — a `ValidatingWebhookConfiguration` or
  `MutatingWebhookConfiguration` may reject the request after authorization.
  List with `kubectl get validatingwebhookconfigurations,mutatingwebhookconfigurations`
  and check the webhook's failure policy and matching rules.

## Quick matrix view

For a whole-subject overview instead of one-verb probes, use the `access-matrix`
krew plugin (see `krew-plugins.md`):

```sh
kubectl access-matrix --sa <namespace>:<serviceaccount> -n <namespace>
```
