# Argo CD ApplicationSets & App-of-Apps

Self-contained reference for multi-app / multi-cluster management. Loaded from the
"Escalation: simple → multi-cluster" section of `SKILL.md`.

## App-of-apps

A parent Application whose source is a directory of *child* Application manifests. Syncing
the parent creates/updates the children. Good for a fixed, hand-curated set of apps in one
place; the children are still individual manifests you maintain.

```yaml
# parent app points at a path containing child Application CRs
spec:
  source:
    path: apps/        # directory of Application manifests
```

When the children become numerous or templated, move to an ApplicationSet.

## ApplicationSet

A controller that **templates** Applications from a **generator**. One `ApplicationSet`
CR fans out to N Applications without hand-writing each.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
spec:
  generators:
    - <generator>
  template:
    metadata:
      name: '{{name}}-{{cluster}}'
    spec:
      project: default
      source: { repoURL: ..., targetRevision: HEAD, path: '{{path}}' }
      destination: { server: '{{server}}', namespace: '{{name}}' }
```

## Generators

| Generator | Produces one Application per... | Typical use |
|-----------|---------------------------------|-------------|
| **Git (directory)** | subdirectory in a repo path | monorepo of apps |
| **Git (file)** | entry in config files matched by glob | declarative app catalog |
| **Cluster** | registered cluster (by label selector) | same app to many clusters |
| **List** | hand-listed element | small static fan-out |
| **Matrix** | cartesian product of two child generators | apps × clusters |

`Matrix` (e.g. Git × Cluster) is the standard pattern for "every app to every cluster."

## `preserveResourcesOnDeletion`

By default, deleting an `ApplicationSet` deletes its generated Applications (and, via
cascade, their live resources). Set:

```yaml
spec:
  syncPolicy:
    preserveResourcesOnDeletion: true
```

to keep generated Applications/resources alive when the ApplicationSet itself is removed.
Use this to avoid mass-deleting workloads when refactoring the generator. Deleting
generated apps is a destructive action — confirm before removing an ApplicationSet that
does not set this flag.
