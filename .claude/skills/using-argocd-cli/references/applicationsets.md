# ApplicationSets Reference

Guide to managing ApplicationSets via the ArgoCD CLI. Covers generator types, production safety, and transition criteria from the app-of-apps pattern.

## When to Use ApplicationSets

**Transition criteria from app-of-apps:**
- More than 20 applications to manage (app-of-apps becomes unwieldy)
- Deploying to more than 3 clusters (each cluster needs a copy of each app)
- Applications follow a repetitive pattern (same structure, different parameters)

**Stay with app-of-apps when:**
- Fewer than 20 applications with unique configurations
- Single cluster deployment
- Applications have significantly different structures

## CLI Commands

### List ApplicationSets

```bash
# List all ApplicationSets
argocd appset list

# List ApplicationSets in a specific project
argocd appset list --project <project-name>
```

### Get ApplicationSet Details

```bash
# Show ApplicationSet details
argocd appset get <appset-name>

# Show in YAML format
argocd appset get <appset-name> -o yaml
```

### Create an ApplicationSet

ApplicationSets are typically managed declaratively (YAML in Git), but can be created via CLI:

```bash
# Create from a YAML file
argocd appset create <appset-file.yaml>
```

### Delete an ApplicationSet

```bash
# Delete the ApplicationSet AND all generated applications
argocd appset delete <appset-name>

# Delete only the ApplicationSet, keep generated applications
argocd appset delete <appset-name> --cascade=false
```

**Production safety:** Always use `--cascade=false` when removing an ApplicationSet in production unless you intentionally want to delete all generated applications.

## Generator Types

### Git Generator — Directory

Discovers applications by scanning directories in a Git repository. Each directory becomes an application.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: cluster-apps
  namespace: argocd
spec:
  generators:
  - git:
      repoURL: https://github.com/org/gitops-repo.git
      revision: HEAD
      directories:
      - path: apps/*
  template:
    metadata:
      name: '{{path.basename}}'
    spec:
      project: default
      source:
        repoURL: https://github.com/org/gitops-repo.git
        targetRevision: HEAD
        path: '{{path}}'
      destination:
        server: https://kubernetes.default.svc
        namespace: '{{path.basename}}'
```

**Use when:** Each application has its own directory in the Git repo.

### Git Generator — Files

Reads JSON/YAML parameter files from Git to generate applications.

```yaml
spec:
  generators:
  - git:
      repoURL: https://github.com/org/gitops-repo.git
      revision: HEAD
      files:
      - path: "config/**/config.json"
```

**Use when:** Applications are parameterized and configuration lives in JSON/YAML files alongside manifests.

### Cluster Generator

Generates one application per registered ArgoCD cluster. Useful for deploying the same application across multiple clusters.

```yaml
spec:
  generators:
  - clusters:
      selector:
        matchLabels:
          env: production
  template:
    metadata:
      name: 'app-{{name}}'
    spec:
      source:
        repoURL: https://github.com/org/gitops-repo.git
        targetRevision: HEAD
        path: apps/my-app
      destination:
        server: '{{server}}'
        namespace: my-app
```

**Use when:** The same application must run on every cluster (or a labeled subset).

### List Generator

Uses a hardcoded list of parameters to generate applications. The simplest generator.

```yaml
spec:
  generators:
  - list:
      elements:
      - cluster: staging
        url: https://staging-k8s.example.com
        values:
          replicas: "2"
      - cluster: production
        url: https://prod-k8s.example.com
        values:
          replicas: "5"
  template:
    metadata:
      name: 'myapp-{{cluster}}'
    spec:
      source:
        repoURL: https://github.com/org/gitops-repo.git
        path: apps/myapp
        helm:
          parameters:
          - name: replicas
            value: '{{values.replicas}}'
      destination:
        server: '{{url}}'
```

**Use when:** You have a small, fixed set of targets that don't follow a discoverable pattern.

### Matrix Generator

Combines two generators to create a cross-product of applications. For example, deploy every app to every cluster.

```yaml
spec:
  generators:
  - matrix:
      generators:
      - git:
          repoURL: https://github.com/org/gitops-repo.git
          revision: HEAD
          directories:
          - path: apps/*
      - clusters:
          selector:
            matchLabels:
              env: production
  template:
    metadata:
      name: '{{path.basename}}-{{name}}'
    spec:
      source:
        repoURL: https://github.com/org/gitops-repo.git
        path: '{{path}}'
      destination:
        server: '{{server}}'
        namespace: '{{path.basename}}'
```

**Use when:** You need the cross-product of two dimensions (e.g., every app x every cluster).

### Merge Generator

Overrides values from one generator with values from another. Useful for applying cluster-specific overrides to a base configuration.

```yaml
spec:
  generators:
  - merge:
      mergeKeys:
      - cluster
      generators:
      - clusters:
          selector:
            matchLabels:
              env: production
      - list:
          elements:
          - cluster: prod-us-east-1
            values:
              replicas: "10"
```

**Use when:** Most targets use the same configuration but a few need specific overrides.

## Production Safety

### preserveResourcesOnDeletion

**Always set this for production ApplicationSets.** When an ApplicationSet is deleted, this annotation prevents the generated applications (and their Kubernetes resources) from being deleted.

```yaml
spec:
  syncPolicy:
    preserveResourcesOnDeletion: true
```

Without this, deleting an ApplicationSet cascades to all generated applications, which cascades to all their Kubernetes resources. In production, this is catastrophic.

### Progressive Sync (Rolling Update)

Roll out changes gradually across generated applications instead of all at once:

```yaml
spec:
  strategy:
    type: RollingSync
    rollingSync:
      steps:
      - matchExpressions:
        - key: envLabel
          operator: In
          values:
          - staging
      - matchExpressions:
        - key: envLabel
          operator: In
          values:
          - production
        maxUpdate: 25%
```

### Application Pruning Policy

Control what happens when an element is removed from a generator's output:

```yaml
spec:
  syncPolicy:
    applicationsSync: create-update    # Don't delete apps when removed from generator
```

Options:
- `create-only` — Create applications but never update or delete them
- `create-update` — Create and update, but never delete
- `create-delete` — Create and delete, but don't update (rare)
- `sync` — Full lifecycle: create, update, and delete (default)

## Troubleshooting ApplicationSets

```bash
# Check ApplicationSet controller logs
kubectl -n argocd logs -l app.kubernetes.io/name=argocd-applicationset-controller

# Verify an ApplicationSet's generated applications
argocd appset get <appset-name>

# Check for errors in ApplicationSet status
argocd appset get <appset-name> -o yaml | grep -A5 status
```

Common issues:
- **No applications generated:** Check generator configuration (paths, selectors, file patterns)
- **Applications not updating:** Verify the ApplicationSet controller is running and has access to the Git repo
- **Template rendering errors:** Check parameter names match between generator output and template variables
