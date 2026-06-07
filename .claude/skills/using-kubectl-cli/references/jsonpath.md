# Extraction: JSONPath, custom-columns, and jq

Three ways to pull specific fields out of `kubectl` output. Prefer JSONPath /
custom-columns for portability (no extra binary); use `jq` for complex transforms.

## JSONPath (`-o jsonpath=`)

kubectl's JSONPath is a subset — note the quirks below.

```sh
# Single field
kubectl get pod <pod> -n <namespace> -o jsonpath='{.status.phase}'

# Iterate a list with range; \n / \t are honored inside the template
kubectl get pods -n <namespace> \
  -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.phase}{"\n"}{end}'

# Filter by a field value (note: == with single quotes around the literal)
kubectl get pods -n <namespace> \
  -o jsonpath='{.items[?(@.status.phase=="Running")].metadata.name}'

# A key containing dots must be escaped with a backslash
kubectl get nodes \
  -o jsonpath='{.items[*].metadata.labels.kubernetes\.io/hostname}'

# All container images across all pods
kubectl get pods -A \
  -o jsonpath='{range .items[*]}{range .spec.containers[*]}{.image}{"\n"}{end}{end}'
```

Quirks:
- No filtering on missing keys without a guard; absent fields render empty.
- `?()` filters support `==`, `!=`, `<`, `>` but **not** regex or `&&`/`||`.
- Wrap the whole template in single quotes so the shell does not eat `{`, `}`, `$`.

## custom-columns (`-o custom-columns=`)

Tabular output with named headers; each column is a JSONPath expression.

```sh
kubectl get pods -n <namespace> \
  -o custom-columns='NAME:.metadata.name,STATUS:.status.phase,NODE:.spec.nodeName'

# Nested / first-element selection
kubectl get pods -n <namespace> \
  -o custom-columns='NAME:.metadata.name,IMAGE:.spec.containers[0].image,RESTARTS:.status.containerStatuses[0].restartCount'

# Headerless, for piping into other tools
kubectl get pods -n <namespace> \
  -o custom-columns='NAME:.metadata.name' --no-headers
```

There is also `-o custom-columns-file=<file>` to read the column spec from a file.

## jq (`-o json | jq`)

Reach for `jq` when you need regex, boolean logic, grouping, or reshaping.

```sh
# Pods not in Running phase
kubectl get pods -n <namespace> -o json \
  | jq -r '.items[] | select(.status.phase != "Running") | .metadata.name'

# Sum container restartCounts per pod
kubectl get pods -n <namespace> -o json \
  | jq -r '.items[] | {name: .metadata.name, restarts: ([.status.containerStatuses[]?.restartCount] | add)}'

# Boolean / regex filtering jsonpath cannot express
kubectl get pods -A -o json \
  | jq -r '.items[] | select(.metadata.namespace | test("^kube-")) | "\(.metadata.namespace)/\(.metadata.name)"'

# Flatten labels into key=value lines
kubectl get pod <pod> -n <namespace> -o json \
  | jq -r '.metadata.labels | to_entries[] | "\(.key)=\(.value)"'
```

## Choosing

- One scalar / simple list → **jsonpath**.
- Human-readable table → **custom-columns**.
- Regex, conditionals, aggregation, reshaping → **jq**.
