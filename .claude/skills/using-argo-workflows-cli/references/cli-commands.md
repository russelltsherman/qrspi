# Argo CLI command catalog

**Targeted version:** Argo Workflows / `argo` CLI **v3.5.x**. Flags below are stable across the 3.x
line; always confirm against the cluster with `argo <command> --help`.

## Global conventions (apply to every command)

- **Always pass `--namespace <ns>` (`-n`)** explicitly. Do not rely on the kube-context default —
  scripts must be deterministic about which namespace they touch.
- **Scriptable output:** `-o json`, `-o yaml`, `-o name`, or `-o wide` when a script consumes output.
- **No prompts:** avoid interactive selection; pass names/files explicitly. Confirmation-style
  commands (delete/terminate) take explicit targets or selectors, never interactive pickers.
- **Validate before mutate:** `argo lint` and `argo submit --dry-run` come before `argo submit`.
- Common global flags: `--namespace/-n`, `--output/-o`, `--kubeconfig`, `--context`,
  `--instanceid`, `--gloglevel`.

---

## 1. submit — create and run a workflow

```bash
# Validate first, then submit non-interactively.
argo lint -n ci workflow.yaml
argo submit -n ci --dry-run -o yaml workflow.yaml          # client-side render, no apply
argo submit -n ci --server-dry-run -o yaml workflow.yaml   # server validates, no persist
argo submit -n ci workflow.yaml \
  --parameter message=hello --parameter-file params.yaml \
  --generate-name my-wf- --labels owner=ci --serviceaccount argo-runner
```

Submit from a template instead of an inline spec:

```bash
argo submit -n ci --from workflowtemplate/build-and-test --parameter ref=main
argo submit -n ci --from clusterworkflowtemplate/shared-lint
```

Key flags: `--from <kind>/<name>`, `--parameter/-p k=v`, `--parameter-file/-f`, `--generate-name`,
`--name`, `--labels/-l`, `--serviceaccount`, `--dry-run`, `--server-dry-run`, `--wait`,
`--watch/-w`, `--log`, `--priority`.

## 2. get — inspect a workflow's status

```bash
argo get -n ci @latest                  # most recent workflow in the namespace
argo get -n ci my-wf-abcde -o json      # machine-readable status for scripting
argo get -n ci my-wf-abcde --node-field-selector phase=Failed
```

Key flags: `-o json|yaml|wide`, `--node-field-selector`, `--status`, `--no-color`.

## 3. logs — read step/pod logs

```bash
argo logs -n ci @latest --follow                 # stream the whole workflow
argo logs -n ci my-wf-abcde --container main      # one container
argo logs -n ci my-wf-abcde --since 10m --no-color --timestamps
argo logs -n ci my-wf-abcde --grep ERROR
```

Key flags: `--follow/-f`, `--since`, `--since-time`, `--tail`, `--container/-c`, `--grep`,
`--previous/-p`, `--timestamps`, `--no-color`.

## 4. list — enumerate workflows

```bash
argo list -n ci -o name                                  # names only, script-friendly
argo list -n ci --status Running,Pending
argo list -n ci --selector owner=ci --since 24h --running
argo list --all-namespaces -o json
```

Key flags: `--status`, `--selector/-l`, `--all-namespaces/-A`, `--since`, `--running`, `--completed`,
`--prefix`, `--chunk-size`, `-o name|json|wide`.

## 5. delete — remove workflow objects

```bash
argo delete -n ci my-wf-abcde
argo delete -n ci --completed --older 7d        # GC old finished runs
argo delete -n ci --selector owner=ci
argo delete -n ci --all-namespaces --status Failed   # explicit selectors, never interactive
```

Key flags: `--all`, `--completed`, `--older`, `--status`, `--selector/-l`, `--prefix`, `--force`,
`--dry-run`.

## 6. retry — re-run failed nodes of a finished workflow

```bash
argo retry -n ci my-wf-abcde                     # retries failed/errored nodes, keeps successes
argo retry -n ci my-wf-abcde --restart-successful --node-field-selector templateName=build
```

Key flags: `--restart-successful`, `--node-field-selector`, `--parameter/-p`, `--wait`, `--watch/-w`.

## 7. resubmit — start a fresh run from an existing workflow's spec

```bash
argo resubmit -n ci my-wf-abcde                  # new workflow from the same spec
argo resubmit -n ci my-wf-abcde --memoized       # reuse memoized step outputs
```

Key flags: `--memoized`, `--parameter/-p`, `--priority`, `--wait`, `--watch/-w`. (Difference from
`retry`: `resubmit` creates a new workflow object; `retry` resumes the existing one.)

## 8. stop — gracefully stop a running workflow

```bash
argo stop -n ci my-wf-abcde                                  # runs exit handlers / onExit
argo stop -n ci --selector owner=ci --node-field-selector phase=Running
```

`stop` shuts the workflow down but **still runs `onExit`/exit handlers** (graceful). Key flags:
`--selector/-l`, `--node-field-selector`, `--message`.

## 9. terminate — immediately kill a running workflow

```bash
argo terminate -n ci my-wf-abcde                  # hard stop, skips exit handlers
argo terminate -n ci --selector owner=ci
```

`terminate` is the hard counterpart to `stop`: it does **not** run exit handlers. Key flags:
`--selector/-l`, `--all`.

## 10. suspend — pause a running workflow

```bash
argo suspend -n ci my-wf-abcde                    # pauses scheduling of new nodes
```

(Distinct from a `suspend` *template*, which pauses for manual/automatic approval inside a spec.)

## 11. resume — continue a suspended workflow

```bash
argo resume -n ci my-wf-abcde
argo resume -n ci my-wf-abcde --node-field-selector displayName=approval
```

Key flags: `--node-field-selector` (resume a specific suspended node).

## 12. watch — live-watch a workflow to completion

```bash
argo watch -n ci @latest
argo watch -n ci my-wf-abcde --node-field-selector phase=Running --status Running
```

Streams status transitions until the workflow finishes; pair with `--status`/`--node-field-selector`.

## 13. lint — validate manifests offline

```bash
argo lint -n ci workflow.yaml templates/*.yaml
argo lint -n ci --strict --output simple ./manifests/
```

Run in CI as a gate before submit. Key flags: `--strict`, `--output pretty|simple`,
`--kinds workflows,workflowtemplates,cronworkflows,clusterworkflowtemplates`.

## 14. cron — manage CronWorkflows

```bash
argo cron lint -n ci cron.yaml
argo cron create -n ci cron.yaml
argo cron list -n ci -o wide
argo cron get -n ci nightly-build
argo cron suspend -n ci nightly-build
argo cron resume  -n ci nightly-build
argo cron delete  -n ci nightly-build
```

Full lifecycle and scheduling semantics: see `cron-and-debugging.md`. Sub-commands: `create`,
`list`, `get`, `suspend`, `resume`, `delete`, `lint`.

## 15. template — manage WorkflowTemplates

```bash
argo template lint -n ci template.yaml
argo template create -n ci template.yaml
argo template list -n ci -o name
argo template get -n ci build-and-test -o yaml
argo template delete -n ci build-and-test
```

Sub-commands: `create`, `list`, `get`, `update`, `delete`, `lint`. Use
`argo cluster-template ...` for the cluster-scoped (`ClusterWorkflowTemplate`) equivalents. Authoring
and scope details: see `templates.md`.
