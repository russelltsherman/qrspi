# Template Authoring Guide

## DAG vs Steps

**Default to DAG.** Use Steps only for explicit sequential flows with branching.

- **DAG**: templates run in parallel unless `dependencies` declared. Use when parallelism is desirable.
- **Steps**: each step group runs sequentially; groups run in parallel. Use only for sequential order with entry-point branching.
- **Conditional branching**: prefer DAG with `when:` clauses over Steps.

> Decision: parallelizable = DAG. Explicit sequential order = consider Steps. Conditional branching = DAG with `when:`.

## WorkflowTemplate

Reusable, namespaced template collection referenced via `workflowTemplateRef`.

- Templates scoped to the WorkflowTemplate's namespace.
- Use when multiple workflows share common template logic.

## ClusterWorkflowTemplate

Cluster-scoped, namespace-agnostic templates. Same `workflowTemplateRef` reference pattern. Requires ClusterWorkflowTemplate CRD and RBAC.

## Template Design Patterns

- **Parameter passing**: `inputs.parameters` (string), `{{tasks.X.outputs.result}}` for task-to-task data.
- **Parameter injection**: `argo submit -p key=val` for ad-hoc overrides.
- **Template defaults**: `inputs.default` for optional parameters.
- **Nesting**: DAG can call other templates inline or via `templateRef`. Keep depth shallow.
- **Error handling**: always set `retryStrategy` on external-service templates. Use `onExit` for cleanup.
- **Timeouts**: set `activeDeadlineSeconds` on templates; default is 30 days — override in production.
