# Patch selection: strategic-merge vs JSON 6902

Picking the wrong patch type is the most common Kustomize mistake. The two types behave
identically for scalar field edits but diverge sharply on **lists/arrays**, which is where
people get surprised.

## Decision framework

Start here, then read the detail below.

| You want to…                                          | Use                  | Why                                                           |
| ----------------------------------------------------- | -------------------- | ------------------------------------------------------------ |
| Add or change a **scalar field** (replicas, an image) | Strategic-merge      | Reads like the resource; obvious in review                   |
| Add a field to a **map**                              | Strategic-merge      | Maps merge key-by-key naturally                              |
| Add an element to a list (e.g. a new env var)         | Strategic-merge*     | Merges by merge-key when the list has one                    |
| **Remove** a field                                    | JSON-6902 (`remove`) | Strategic-merge can't reliably delete; 6902 has explicit op  |
| **Replace a specific array element by index**         | JSON-6902            | Strategic-merge has no index addressing                      |
| Reorder or splice a list precisely                    | JSON-6902            | Index/path operations are exact                              |
| Edit a resource whose list has **no merge key**       | JSON-6902            | Strategic-merge can't merge keyless lists deterministically  |

\* Strategic-merge merges Kubernetes lists by their **merge key** (e.g. container `name`,
env var `name`, port `containerPort`). If the merge key matches an existing element it
updates it; otherwise it appends. If the list type has no registered merge key, the patch
**replaces the whole list** — usually not what you want. When in doubt for list work,
reach for JSON-6902.

## Strategic-merge: looks like the resource

The patch is a partial copy of the target resource. Kustomize merges it field-by-field.

```yaml
# replica-patch.yaml — bumps replicas and one container's image, leaves all else intact
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
spec:
  replicas: 5
  template:
    spec:
      containers:
        - name: web          # merge key — matches existing container, updates it
          image: myorg/web:v1.4.2
```

Reference it in the unified `patches:` list by file path:

```yaml
patches:
  - path: replica-patch.yaml
```

Kustomize auto-detects this is a strategic-merge patch because the document looks like a
Kubernetes resource (it has `apiVersion`/`kind`/`metadata`).

### Deleting with strategic-merge (the `$patch: delete` directive)

You can delete a list element by re-stating it with a directive, but it is fiddly and a
frequent source of bugs. For deletions, JSON-6902 `remove` is clearer:

```yaml
# strategic-merge deletion — works, but easy to get wrong
spec:
  template:
    spec:
      containers:
        - name: sidecar
          $patch: delete
```

## JSON 6902: explicit operations

A list of `op`/`path`/`value` operations against a `target` selector. `path` is a JSON
Pointer (`/` separated; `-` means "end of array"; numeric segments are array indices).

```yaml
patches:
  - target:
      kind: Deployment
      name: web
    patch: |
      - op: replace
        path: /spec/replicas
        value: 5
      - op: add
        path: /spec/template/spec/containers/0/env/-   # append to first container's env
        value:
          name: LOG_LEVEL
          value: debug
      - op: remove
        path: /spec/template/spec/containers/1         # delete second container
```

Supported ops: `add`, `remove`, `replace`, `move`, `copy`, `test`.

**Index fragility:** `path` indices are positional. If the base reorders its containers,
an index-based patch silently targets the wrong element. Prefer targeting by a merge key
via strategic-merge when the edit is element-addition; reserve index paths for genuine
"by-position" edits, and keep base and overlay close enough that a reviewer notices a
reorder.

## Deprecation: `patchesStrategicMerge` / `patchesJson6902` → `patches:`

Older kustomizations split patches into two fields. Both are deprecated in favor of a
single unified `patches:` list, which auto-detects the type (file/document → strategic
merge; `target` + op list → JSON-6902).

```yaml
# LEGACY — recognize it, don't write it
patchesStrategicMerge:
  - replica-patch.yaml
patchesJson6902:
  - target: { kind: Deployment, name: web }
    path: json-patch.yaml

# CURRENT — one list
patches:
  - path: replica-patch.yaml
  - target: { kind: Deployment, name: web }
    path: json-patch.yaml
```

Prefer `patches:` in all new work. Leave a working legacy repo alone unless asked to
migrate it — the deprecated fields still function; the goal is not to break legacy repos,
only to stop emitting deprecated syntax.
