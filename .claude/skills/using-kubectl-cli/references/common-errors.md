# Common kubectl Errors and Resolutions

Each entry: the message you see, the usual cause, and the concrete next command.

## Connection / context

**`The connection to the server <host>:<port> was refused - did you specify the right host or port?`**
- Cause: wrong/empty current context, stopped cluster, or stale kubeconfig endpoint.
- Fix: `kubectl config current-context`; `kubectl config get-contexts`; switch with
  `kubectl config use-context <context>`. Confirm the cluster is up.

**`error: You must be logged in to the server (Unauthorized)`**
- Cause: expired credentials/token or an exec auth plugin that failed to refresh.
- Fix: re-authenticate (cloud CLI `get-credentials`, SSO login). Inspect
  `kubectl config view --minify` for the `users:` exec block.

**`error: current-context is not set`**
- Cause: kubeconfig has no active context.
- Fix: `kubectl config use-context <context>`.

## Not found / namespace

**`Error from server (NotFound): <kind> "<name>" not found`**
- Cause: usually the wrong namespace, not a missing object.
- Fix: add `-n <namespace>` or `-A`; verify with `kubectl get <kind> -A | grep <name>`.

**`error: the server doesn't have a resource type "<kind>"`**
- Cause: CRD not installed, wrong API group, or typo'd kind.
- Fix: `kubectl api-resources | grep -i <kind>`; check the CRD is installed.

## Authorization

**`Error from server (Forbidden): <user> cannot <verb> resource "<resource>" in API group "<group>" ...`**
- Cause: RBAC denial.
- Fix: walk `rbac-debugging.md` starting at `kubectl auth can-i <verb> <resource>`.

## Apply / validation

**`error: error validating data: ... unknown field "<field>"`**
- Cause: typo or wrong apiVersion in the manifest.
- Fix: `kubectl explain <kind>.<path>`; preview with
  `kubectl apply -f <file> --dry-run=server`.

**`Error from server (Conflict): Operation cannot be fulfilled on <kind> "<name>": the object has been modified`**
- Cause: optimistic-concurrency clash — your copy is stale.
- Fix: re-`get` the object and re-apply; prefer `kubectl apply` (server-side merge)
  over `replace`.

**`metadata.resourceVersion: Invalid value: 0x0: must be specified for an update`**
- Cause: `replace` without a current `resourceVersion`.
- Fix: `kubectl apply` instead, or `get -o yaml` then `replace` with the fresh object.

## Pods / scheduling

**`0/<n> nodes are available: <reason>` (Pending pod)**
- Cause: insufficient resources, taints, or unsatisfiable affinity/selectors.
- Fix: `kubectl describe pod <pod> -n <namespace>` and read the `Events:` section.

**`CrashLoopBackOff` / `ImagePullBackOff`**
- Cause: container exits repeatedly / image cannot be pulled.
- Fix: `kubectl logs <pod> -n <namespace> --previous`;
  `kubectl describe pod <pod> -n <namespace>` for pull/auth detail. See the
  debugging-escalation section in `SKILL.md`.

**`error: unable to upgrade connection: container not found ("<container>")`**
- Cause: `exec`/`logs` against a multi-container pod without `-c`, or a not-yet-running container.
- Fix: `kubectl exec -it <pod> -n <namespace> -c <container> -- <command>`.
