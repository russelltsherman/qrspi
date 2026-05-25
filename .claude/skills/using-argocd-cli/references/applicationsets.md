# ApplicationSets Reference

Purpose: Guide to managing ApplicationSets — generator types, CLI commands, production safety settings, and migration from the app-of-apps pattern.

## When to Use ApplicationSets

ApplicationSets dynamically generate ArgoCD Application resources from templates and generators. Use them when:

- You manage more than ~20 applications with similar configuration
- You deploy the same application across 3+ clusters
- You want to auto-discover and onboard applications from Git directory structure
- The app-of-apps pattern has become too verbose or hard to maintain

If you have fewer than 20 applications on a single cluster, the app-of-apps pattern or individual `argocd app create` commands are simpler and more appropriate.

## Generator Types

### Git Generator

Creates applications based on Git repository structure — one app per directory or per file matching a pattern.

#### Directory generator

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

Adding a new directory under `apps/` automatically creates a new ArgoCD Application.

#### File generator

```yaml
generators:
- git:
    repoURL: https://github.com/org/gitops-repo.git
    revision: HEAD
    files:
    - path: "config/**/config.json"
```

Each matching JSON file provides template parameters. Useful when application configuration varies and cannot be derived from directory structure alone.

### Cluster Generator

Creates one application per registered ArgoCD cluster. Useful for deploying shared infrastructure (monitoring, ingress, cert-manager) to all clusters.

```yaml
generators:
- clusters:
    selector:
      matchLabels:
        environment: production
```

This generates one application for each cluster labeled `environment: production`. Adding a new cluster with that label automatically creates the application.

#### Cluster parameters

Available template parameters from cluster generator:

| Parameter | Value |
|-----------|-------|
| `{{name}}` | Cluster name in ArgoCD |
| `{{server}}` | Cluster API server URL |
| `{{metadata.labels.<key>}}` | Cluster labels |

### List Generator

Explicitly lists target environments. No auto-discovery — you control exactly which applications are created.

```yaml
generators:
- list:
    elements:
    - cluster: prod-us-east
      url: https://prod-us-east.example.com
      namespace: my-app
    - cluster: prod-eu-west
      url: https://prod-eu-west.example.com
      namespace: my-app
```

Use this when you need precise control over which clusters/environments get an application, without relying on labels or Git structure.

### Matrix Generator

Combines two generators to produce the Cartesian product. Creates applications for every combination of parameters from both generators.

```yaml
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
            environment: production
```

This creates one application per directory per production cluster. If you have 5 app directories and 3 production clusters, you get 15 applications.

**Warning:** Matrix generators can produce a large number of applications. Calculate the expected count before applying: `count = generator_A_results * generator_B_results`.

### Merge Generator

Combines parameters from multiple generators, merging on a key field. Unlike Matrix (which produces a Cartesian product), Merge combines matching entries.

```yaml
generators:
- merge:
    mergeKeys:
    - name
    generators:
    - list:
        elements:
        - name: app-a
          replicas: 3
        - name: app-b
          replicas: 1
    - git:
        repoURL: https://github.com/org/config.git
        revision: HEAD
        files:
        - path: "apps/*/config.json"
```

## CLI Commands

### List ApplicationSets

```bash
# List all ApplicationSets
argocd appset list

# Get details of a specific ApplicationSet
argocd appset get <appset-name>
```

### Create an ApplicationSet

```bash
# ApplicationSets are typically created from YAML manifests
kubectl apply -f applicationset.yaml -n argocd

# Or via argocd CLI
argocd appset create applicationset.yaml
```

### Delete an ApplicationSet

```bash
# Delete the ApplicationSet and its generated applications
argocd appset delete <appset-name>

# Delete only the ApplicationSet, keep generated applications
argocd appset delete <appset-name> --cascade=false
```

### View generated applications

```bash
# List applications and filter by the ApplicationSet label
argocd app list -l app.kubernetes.io/instance=<appset-name>
```

## Production Safety: preserveResourcesOnDeletion

By default, deleting an ApplicationSet deletes its generated Applications, which cascade-deletes the Kubernetes resources. For production, set `preserveResourcesOnDeletion` to prevent accidental resource deletion:

```yaml
spec:
  syncPolicy:
    preserveResourcesOnDeletion: true
```

With this enabled:
- Deleting the ApplicationSet removes Application CRDs but leaves Kubernetes workloads running
- Removing a directory from Git (with Git generator) removes the Application but leaves workloads running
- You must manually delete Kubernetes resources if you actually want them gone

**Recommendation:** Always enable `preserveResourcesOnDeletion` for production ApplicationSets. The cost of accidentally deleting production workloads far exceeds the cost of manual cleanup.

## Migrating from App-of-Apps

### When to migrate

The app-of-apps pattern becomes unwieldy when:
- You have more than ~20 child applications
- Adding a new application requires editing a central manifest
- You deploy to 3+ clusters and must duplicate Application CRDs per cluster
- Application configuration follows a predictable pattern that a generator could derive

### Migration steps

1. **Audit existing applications:** List all child applications and identify common patterns (same repo, similar paths, same destination structure).

2. **Choose a generator:** If apps are organized as directories in Git, use the Git directory generator. If deploying across clusters, use the Cluster generator. If both, use Matrix.

3. **Create the ApplicationSet:** Write the ApplicationSet manifest with the template matching your current Application specs.

4. **Test in a non-production environment first:**
   ```bash
   # Apply the ApplicationSet in staging
   argocd appset create applicationset.yaml
   # Verify generated applications match expected set
   argocd app list -l app.kubernetes.io/instance=<appset-name>
   ```

5. **Enable `preserveResourcesOnDeletion`** on the ApplicationSet before migrating production.

6. **Transition production:**
   - Apply the ApplicationSet
   - Verify generated applications are created and healthy
   - Delete the old parent app-of-apps application (the children are now managed by the ApplicationSet)

### Handling exceptions

Not every application fits the generator pattern. For exceptions:
- Use the `exclude` field in the Git generator to skip non-conforming directories
- Create separate ApplicationSets for different patterns
- Keep individual `argocd app create` commands for true one-offs

```yaml
generators:
- git:
    directories:
    - path: apps/*
    - path: apps/legacy-app
      exclude: true
```

## Template Overrides

Override template values for specific generated applications:

```yaml
spec:
  generators:
  - list:
      elements:
      - name: app-a
        namespace: app-a-ns
      - name: app-b
        namespace: app-b-custom
  template:
    metadata:
      name: '{{name}}'
    spec:
      destination:
        namespace: '{{namespace}}'
```

For complex overrides that vary per application, consider the file generator with per-app JSON configuration files instead of inline list elements.
