# Work Tree — Create a new agent skill called using argo workflows cli

**Plan basis:** plan.md @ 2026-05-27T00:00:00Z
**Generated:** 2026-05-27T00:00:00Z
**Status:** draft
**Total sessions:** 3
**Critical path:** T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8 → T9 → T10 → T11 → T12 → T13

## Session 1

**Load:** structure.md §Slice 1, structure.md §Contracts, plan.md §Slice 1
**Estimated context:** 10% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create `.claude/skills/using-argo-workflows-cli/SKILL.md` with YAML frontmatter (name, description, command, argument-hint, allowed-tools) and core body covering all 11 command groups. Keep body under 500 lines. | — | 1 | S | pending |
| T2 | Verify Slice 1: `wc -l` line count, frontmatter YAML parse, `command -v argo` check present, description semantic-match specificity, allowed-tools = [Bash, Read] | T1 | 2 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** SKILL.md complete. Reference files are independent — fresh context keeps each reference scoped and avoids cross-contamination.

## Session 2

**Load:** structure.md §Slice 2-4, plan.md §Slice 2, plan.md §Slice 3, plan.md §Slice 4
**Estimated context:** 15% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T3 | Create `references/templates.md` — DAG vs Steps decision table mapping complexity to template type, `--from` flag syntax with explicit `--namespace` encoding, WorkflowTemplate/ClusterWorkflowTemplate usage patterns, namespace resolution caveats, ClusterWorkflowTemplate cluster-admin prerequisite | T2 | 3 | S | pending |
| T4 | Verify templates.md: decision table present, `--from` syntax with namespace, namespace caveats, cluster-admin note | T3 | 4 | S | pending |
| T5 | Create `references/debugging.md` — escalation path `argo get` → `argo logs` → `argo template` → `kubectl describe pod` → `kubectl get events`, decision matrix mapping Pending/Running/Error/CrashLoopBackOff to specific commands, empty `argo logs` explanation, kubectl commands as Bash invocations | T4 | 5 | S | pending |
| T6 | Verify debugging.md: escalation path present, status→command matrix, empty logs note, kubectl via Bash | T5 | 6 | S | pending |
| T7 | Create `references/cron.md` — all 7 CronWorkflow commands (create, list, get, delete, suspend, resume, lint), concurrency policy options (Allow, Forbid, Replace) with when-to-use guidance, `argo cron lint` as validation step, assumes agent knows cron syntax | T6 | 7 | S | pending |
| T8 | Verify cron.md: all 7 commands covered, concurrency policies explained with guidance, `argo cron lint` present, cron syntax not generated | T7 | 8 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** First 3 reference files done and verified. Remaining references are independent — fresh context for clean separation.

## Session 3

**Load:** structure.md §Slice 5-6, plan.md §Slice 5, plan.md §Slice 6
**Estimated context:** 15% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T9 | Create `references/artifacts.md` — default repository config, `.tgz` suffix convention, UID-parameterized keys, input vs output artifact distinction with passing examples, garbage collection strategies (TTL, label-based). Also create `references/resources.md` — resource requests/limits, nodeSelector, tolerations, parallelism, synchronization semaphores, podPriorityClassName. | T8 | 9,10 | S | pending |
| T10 | Verify Slice 5: both files exist, `.tgz` convention documented, UID-parameterized keys documented, input vs output distinction, garbage collection strategies, resources covers all 6 acceptance areas | T9 | 11 | S | pending |
| T11 | Create `references/retries.md` — all `retryStrategy` configuration fields, backoff (duration/factor/maxDuration) with examples, `retryPolicy` values (Default/Always/OnError/OnFailure/ResultError), idempotency requirements explicitly stated | T10 | 12 | S | pending |
| T12 | Verify Slice 6: retryStrategy fields documented, backoff examples, retryPolicy values explained, idempotency requirements stated | T11 | 13 | S | pending |
| T13 | Final verification: run `find .claude/skills/using-argo-workflows-cli/ -type f | sort` and confirm all 7 files exist (SKILL.md + 6 reference files) | T12 | Final | S | pending |
