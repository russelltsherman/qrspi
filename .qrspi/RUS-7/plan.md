# Implementation Plan — Create a new agent skill called using argo workflows cli

**Structure basis:** structure.md @ 2026-05-27T00:00:00Z
**Generated:** 2026-05-27T00:00:00Z
**Status:** draft
**Total steps:** 12

## Slice 1: Skill scaffold and frontmatter

**Structure reference:** Slice 1 — `.claude/skills/using-argo-workflows-cli/SKILL.md` with YAML frontmatter (name, description, command, argument-hint, allowed-tools) plus core body covering invocation and lifecycle commands. Body under 500 lines.

### Create

1. ✨ Create `.claude/skills/using-argo-workflows-cli/SKILL.md` — Skill frontmatter and core body per contracts in structure.md. The frontmatter must include: `name: "Using Argo Workflows CLI"`, `description` specific enough for semantic matching (not generic "Argo Workflows help"), `command: "/using-argo-workflows-cli"`, `argument-hint: "<command> [flags]"`, `allowed-tools: [Bash, Read]`. Body starts with `command -v argo` prerequisite check. Covers command groups: submit, get, logs, list, delete, retry, resubmit, stop, terminate, suspend, resume, watch. Keep body under 500 lines total (including frontmatter).

### Verify Slice 1

2. **Checkpoint:** `wc -l .claude/skills/using-argo-workflows-cli/SKILL.md && head -10 .claude/skills/using-argo-workflows-cli/SKILL.md`
   - [ ] `command -v argo` check is present at the top of SKILL.md
   - [ ] Frontmatter parses as valid YAML with all 5 required fields (name, description, command, argument-hint, allowed-tools)
   - [ ] Body line count (excluding frontmatter) is under 500 lines
   - [ ] Description is specific enough to trigger via semantic matching
   - [ ] `allowed-tools` is scoped to `[Bash, Read]`

---

## Slice 2: Reference material — templates, DAG vs Steps, WorkflowTemplates

**Structure reference:** Slice 2 — `references/templates.md` with DAG vs Steps decision table, inline YAML vs `--from wf/` vs `--from cwt/` guidance, WorkflowTemplate/ClusterWorkflowTemplate usage patterns.

### Create

3. ✨ Create `.claude/skills/using-argo-workflows-cli/references/templates.md` — Decision table mapping workflow complexity (linear steps, branching DAG, parallel stages) to template type. Covers `--from` flag syntax with explicit `--namespace` encoding. Documents namespace resolution caveats (auto-resolution unreliable across multi-namespace clusters). Notes ClusterWorkflowTemplate requires cluster-admin prerequisite.

### Verify Slice 2

4. **Checkpoint:** `cat .claude/skills/using-argo-workflows-cli/references/templates.md`
   - [ ] Decision table maps workflow complexity to template type
   - [ ] Covers `--from` flag syntax with explicit `--namespace` encoding
   - [ ] Namespace resolution caveats are documented
   - [ ] ClusterWorkflowTemplate cluster-admin prerequisite is noted

---

## Slice 3: Reference material — debugging escalation path

**Structure reference:** Slice 3 — `references/debugging.md` with escalation decision matrix, common failure causes and remedies, argo-to-kubectl transition rules, notes on empty `argo logs` output.

### Create

5. ✨ Create `.claude/skills/using-argo-workflows-cli/references/debugging.md` — Escalation decision matrix: `argo get` -> `argo logs` -> `argo template` -> `kubectl describe pod` -> `kubectl get events`. Decision matrix maps workflow status conditions (Pending, Running, Error, CrashLoopBackOff) to specific commands. Documents that `argo logs` can return empty and explains why. All kubectl commands presented as Bash invocations.

### Verify Slice 3

6. **Checkpoint:** `cat .claude/skills/using-argo-workflows-cli/references/debugging.md`
   - [ ] Escalation path: `argo get` -> `argo logs` -> `argo template` -> `kubectl describe pod` -> `kubectl get events`
   - [ ] Decision matrix maps workflow status conditions to specific commands
   - [ ] Documents `argo logs` can return empty and explains why
   - [ ] kubectl commands are presented as Bash invocations

---

## Slice 4: Reference material — CronWorkflow lifecycle

**Structure reference:** Slice 4 — `references/cron.md` with CronWorkflow lifecycle commands (create, list, get, delete, suspend, resume, lint), concurrency policy guidance and decision tree, schedule syntax conventions.

### Create

7. ✨ Create `.claude/skills/using-argo-workflows-cli/references/cron.md` — All 7 CronWorkflow commands: create, list, get, delete, suspend, resume, lint. Concurrency policy options (Allow, Forbid, Replace) explained with when-to-use guidance. `argo cron lint` covered as the validation step. Assumes agent knows cron syntax — no generator encoded.

### Verify Slice 4

8. **Checkpoint:** `cat .claude/skills/using-argo-workflows-cli/references/cron.md`
   - [ ] Covers all 7 CronWorkflow commands
   - [ ] Concurrency policy options (Allow, Forbid, Replace) explained with when-to-use guidance
   - [ ] `argo cron lint` is covered as the validation step
   - [ ] Assumes agent knows cron syntax

---

## Slice 5: Reference material — artifacts and resource management

**Structure reference:** Slice 5 — Two files: `references/artifacts.md` (artifact configuration, parameterization patterns, garbage collection) and `references/resources.md` (resource requests/limits, node selectors, parallelism, synchronization, priorities).

### Create

9. ✨ Create `.claude/skills/using-argo-workflows-cli/references/artifacts.md` — Default repository config, `.tgz` suffix convention for compression, UID-parameterized keys (`{{workflow.uid}}/...`), input vs output artifact distinction with passing examples, artifact passing vs parameters threshold, garbage collection strategies (TTL, label-based).

10. ✨ Create `.claude/skills/using-argo-workflows-cli/references/resources.md` — Resource requests/limits, nodeSelector, tolerations, parallelism, synchronization semaphores, podPriorityClassName. Covers all 6 acceptance area items from design.md.

### Verify Slice 5

11. **Checkpoint:** `cat .claude/skills/using-argo-workflows-cli/references/artifacts.md && cat .claude/skills/using-argo-workflows-cli/references/resources.md`
   - [ ] `.tgz` suffix convention for artifact compression is documented
   - [ ] UID-parameterized key pattern is documented
   - [ ] Input vs output artifact distinction with passing examples
   - [ ] Garbage collection strategies (TTL, label-based) are explained
   - [ ] Resources section covers all 6 acceptance area items

---

## Slice 6: Reference material — retry strategies and error handling

**Structure reference:** Slice 6 — `references/retries.md` with `retryStrategy` fields, `backoff.duration/factor/maxDuration`, `retryPolicy` selection, idempotency requirements.

### Create

12. ✨ Create `.claude/skills/using-argo-workflows-cli/references/retries.md` — All `retryStrategy` configuration fields documented. Backoff configuration (duration, factor, maxDuration) covered with examples. `retryPolicy` values (Default, Always, OnError, OnFailure, ResultError) explained. Idempotency requirements for retry-safe workflows explicitly stated.

### Verify Slice 6

13. **Checkpoint:** `cat .claude/skills/using-argo-workflows-cli/references/retries.md`
   - [ ] All `retryStrategy` configuration fields documented
   - [ ] Backoff configuration covered with examples
   - [ ] `retryPolicy` values explained
   - [ ] Idempotency requirements explicitly stated

---

## Final Verification

All 7 files should exist under `.claude/skills/using-argo-workflows-cli/`:

```bash
find .claude/skills/using-argo-workflows-cli/ -type f | sort
# Expected output:
# .claude/skills/using-argo-workflows-cli/SKILL.md
# .claude/skills/using-argo-workflows-cli/references/artifacts.md
# .claude/skills/using-argo-workflows-cli/references/cron.md
# .claude/skills/using-argo-workflows-cli/references/debugging.md
# .claude/skills/using-argo-workflows-cli/references/retries.md
# .claude/skills/using-argo-workflows-cli/references/resources.md
# .claude/skills/using-argo-workflows-cli/references/templates.md
```

## Rollback Notes

- Steps 1-12: Delete the entire skill directory to rollback: `rm -rf .claude/skills/using-argo-workflows-cli/`
- No existing files are modified, no database changes, no config changes. This skill is purely instructional text.
