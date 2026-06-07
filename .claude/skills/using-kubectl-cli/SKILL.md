---
name: using-kubectl-cli
description: "Use for ANY task that inspects, queries, debugs, or changes a Kubernetes cluster with kubectl — the mandatory way to drive clusters. Trigger whenever the user wants to: list/get/describe pods, deployments, services, nodes, or any resource; read or follow logs; exec into a container; debug a CrashLoopBackOff, ImagePullBackOff, Pending, or Forbidden error; roll out, restart, scale, or roll back a workload; apply, diff, patch, or delete manifests; switch context or namespace; extract fields with jsonpath/custom-columns/jq; troubleshoot RBAC or 'cannot <verb>' denials; or run krew plugins. Even read-only 'kubectl get' or 'what is running in namespace X' belongs here. Covers context/namespace safety, inspection, rollouts, debugging escalation, apply strategies, output formatting, krew plugins, and RBAC."
command: /using-kubectl-cli
argument-hint: <what you want to do with kubectl>
allowed-tools: Bash, Read, Grep, Glob
---

# Using the kubectl CLI

You drive Kubernetes clusters with `kubectl`. This skill gives you the safe command
patterns, an ordered debugging procedure, and a scope firewall. Command blocks use
`<angle-bracket>` placeholders — substitute real values; never run a placeholder verbatim.

## ⛔ HARD STOP — read before any mutating command

**You are operating on a live cluster. A wrong context or a missing namespace flag can
destroy the wrong workload. These rules are absolute.**

1. **ALWAYS verify the active context and namespace before any write.** A mutating
   command with the wrong context targets the wrong cluster.
   ```sh
   kubectl config current-context        # which cluster am I on?
   kubectl config view --minify -o jsonpath='{..namespace}'   # default namespace
   ```
2. **ALWAYS dry-run before deleting or applying.** Never delete or apply blind.
   ```sh
   kubectl delete <kind> <name> -n <namespace> --dry-run=client
   kubectl apply -f <file> -n <namespace> --dry-run=server
   ```
3. **ALWAYS pass an explicit `-n <namespace>` (or `-A`) on mutating commands.** Never
   rely on the default namespace for a write — make the target explicit and visible.

**Stop procedure** — if you cannot satisfy ALL three of the above (context unknown,
namespace ambiguous, or dry-run shows an unexpected target): **STOP. Do not run the
mutating command. Report the exact context, namespace, and intended target to the user
and ask for confirmation.**

**Explicitly forbidden — never do these:**
- `kubectl delete` with no namespace flag on a write you have not dry-run.
- Any mutation against a context you have not just confirmed with `current-context`.
- `--all`, `--force`, `--grace-period=0`, or `delete ... --all-namespaces` without an
  explicit, user-confirmed reason.
- Editing live objects with `kubectl edit` on production resources without a captured
  backup (`kubectl get <kind> <name> -n <namespace> -o yaml > <backup>.yaml`).

## Context and namespace

```sh
kubectl config get-contexts                       # list contexts; * marks active
kubectl config current-context                    # active context
kubectl config use-context <context>              # switch cluster
kubectl config set-context --current --namespace=<namespace>   # set default ns
kubectl get ns                                    # list namespaces
```

Prefer the `ctx` / `ns` krew plugins for fast switching (see `references/krew-plugins.md`).
After any switch, re-confirm with `current-context` before mutating.

## Inspection

```sh
kubectl get <kind> -n <namespace>                 # list (add -o wide for more cols)
kubectl get <kind> <name> -n <namespace> -o yaml  # full object
kubectl get <kind> -A                             # across all namespaces
kubectl describe <kind> <name> -n <namespace>     # events + status, human-readable
kubectl get <kind> -n <namespace> --show-labels   # see labels
kubectl get <kind> -n <namespace> -l <key>=<value> # filter by label selector
kubectl get events -n <namespace> --sort-by=.lastTimestamp   # recent events
```

For pulling specific fields, see `references/jsonpath.md` (jsonpath / custom-columns / jq).

## Rollouts

```sh
kubectl rollout status deployment/<name> -n <namespace>      # watch a rollout
kubectl rollout restart deployment/<name> -n <namespace>     # re-roll (no spec change)
kubectl rollout history deployment/<name> -n <namespace>     # revisions
kubectl rollout undo deployment/<name> -n <namespace>        # roll back one revision
kubectl rollout undo deployment/<name> -n <namespace> --to-revision=<n>
kubectl scale deployment/<name> -n <namespace> --replicas=<n>
```

## Debugging

```sh
kubectl logs <pod> -n <namespace>                            # current container logs
kubectl logs <pod> -n <namespace> -c <container>             # specific container
kubectl logs <pod> -n <namespace> --previous                 # last crashed instance
kubectl logs -f deployment/<name> -n <namespace>             # follow, by workload
kubectl exec -it <pod> -n <namespace> -c <container> -- <command>
kubectl debug <pod> -n <namespace> --image=<image> --target=<container>   # ephemeral
```

For the **ordered** debugging procedure, see the next section. For specific error
messages and resolutions, see `references/common-errors.md`.

## Debugging escalation (ordered)

Investigate a failing workload in this order. Stop as soon as a step explains the failure
— do not skip ahead to `exec`.

1. **Events** — what the control plane tried and why it failed:
   ```sh
   kubectl get events -n <namespace> --sort-by=.lastTimestamp
   ```
2. **Logs** — what the container itself reported (use `--previous` for a crash loop):
   ```sh
   kubectl logs <pod> -n <namespace> -c <container> --previous
   ```
3. **Describe** — scheduling, probe, image-pull, and event detail on the object:
   ```sh
   kubectl describe pod <pod> -n <namespace>
   ```
4. **Exec / debug** — last resort, interactive inspection from inside:
   ```sh
   kubectl exec -it <pod> -n <namespace> -c <container> -- sh
   kubectl debug <pod> -n <namespace> --image=<image> --target=<container>
   ```

## Apply strategies

```sh
kubectl apply -f <file> -n <namespace> --dry-run=server      # preview (server-side)
kubectl diff -f <file> -n <namespace>                        # diff vs live state
kubectl apply -f <file> -n <namespace>                       # declarative (preferred)
kubectl patch <kind> <name> -n <namespace> --type=merge -p '<json>'
kubectl apply -k <kustomize-dir>                             # kustomize
```

Prefer declarative `apply` (server-side merge) over imperative `replace`/`create` for
anything tracked in source. Always `diff` or `--dry-run=server` first.

## Output formatting

```sh
kubectl get <kind> -n <namespace> -o wide
kubectl get <kind> -n <namespace> -o yaml
kubectl get <kind> -n <namespace> -o json
kubectl get <kind> -n <namespace> -o name                    # type/name only
kubectl get <kind> -n <namespace> -o jsonpath='<template>'
kubectl get <kind> -n <namespace> -o custom-columns='<spec>'
```

See `references/jsonpath.md` for jsonpath, custom-columns, and jq extraction recipes.

## Plugins / krew

```sh
kubectl krew install <plugin>                                 # add a plugin
kubectl krew info <plugin>                                    # inspect before install
kubectl plugin list                                          # audit installed plugins
```

The useful catalog (`ctx`, `ns`, `neat`, `tree`, `images`, `whoami`, `access-matrix`)
and provenance/trust guidance live in `references/krew-plugins.md`.

## RBAC

```sh
kubectl auth can-i <verb> <resource> -n <namespace>          # current identity
kubectl auth can-i <verb> <resource> -n <namespace> --as=system:serviceaccount:<namespace>:<serviceaccount>
kubectl auth can-i --list -n <namespace>                     # full permission list
```

For a "Forbidden" / "cannot <verb>" denial, walk the ordered tree in
`references/rbac-debugging.md`: `auth can-i` → bindings → subject form →
NetworkPolicy / webhook.

## Safety

- Read before you write: `get`/`describe` the target, then dry-run, then mutate.
- Capture a backup before in-place edits: `kubectl get <kind> <name> -n <namespace> -o yaml > <backup>.yaml`.
- Make the namespace explicit on every mutating command.
- Prefer `apply` over `replace`; prefer `rollout undo` over manual surgery.

## Scope firewall

Operate strictly within the cluster, namespace, and resources the user named. Do not
widen scope on your own initiative.

**DO:**
- Operate only on the context and namespace(s) the user specified.
- Act only on the resource kinds/names in the request.
- Read freely (`get`, `describe`, `logs`, `events`) to gather evidence.
- Report findings and ask before expanding to other namespaces or clusters.

**DON'T:**
- Switch context/cluster without being asked.
- Touch resources in namespaces the user did not mention.
- Mutate cluster-scoped objects (nodes, ClusterRoles, CRDs, webhooks) as a side effect
  of a namespaced task.
- Run `-A` mutations or `--all` flags to "save a step".

**Pre-action validation gate** — before every mutating command, confirm:
1. Is the target context the one the user named? (`kubectl config current-context`)
2. Is the target namespace explicit and in scope?
3. Is the resource within the requested set?

**Report-and-stop fallback** — if any gate answer is "no" or "unknown", do not act.
Report the exact context, namespace, and resource you would have touched, and ask the
user to confirm or correct before proceeding.
