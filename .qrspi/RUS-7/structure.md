# Structure Outline — Create a new agent skill called using argo workflows cli

**Design basis:** design.md @ 2026-05-27T00:00:00Z
**Generated:** 2026-05-27T00:00:00Z
**Status:** draft

## New Types

None. This is a purely instructional skill — no types, functions, or runtime behavior.

## Modified Types

None. No existing files are modified.

## Contracts

- `SKILL.md frontmatter` — `name`, `description`, `command`, `argument-hint`, `allowed-tools` fields must be present and valid per skill-creator conventions.
- `references/` directory — contains markdown files referenced by the SKILL.md body via inline `Read` tool instructions. Each file is independently readable.
- `argo` CLI — the skill assumes the `argo` binary is installed and reachable via `$PATH`. The SKILL.md instructs agents to verify with `command -v argo` before use.

## Slice 1: Skill scaffold and frontmatter

**Goal:** A valid, triggerable skill file at the correct path with complete frontmatter and a lean body covering the primary argo CLI command groups (submit, get, logs, list, delete, retry, resubmit, stop, terminate, suspend, resume, watch).

**Files touched:**

- ✨ `.claude/skills/using-argo-workflows-cli/SKILL.md` — Skill frontmatter (name, description, command, argument-hint, allowed-tools) plus core body covering invocation and lifecycle commands. Body kept under 500 lines.
**Verification:**
- [ ] `command -v argo` check is present at the top of SKILL.md
- [ ] Frontmatter parses as valid YAML with all 5 required fields
- [ ] Body line count is under 500 lines (excluding frontmatter)
- [ ] Description is specific enough to trigger via semantic matching (not generic "Argo Workflows help")
- [ ] `allowed-tools` is scoped to the minimal necessary set (Bash for running argo, Read for referencing skill docs)
**Context cost:** S
**Depends on:** none

## Slice 2: Reference material — templates, DAG vs Steps, WorkflowTemplates

**Goal:** Templates and selection guidance in a separate references file so the SKILL.md body stays lean.

**Files touched:**

- ✨ `.claude/skills/using-argo-workflows-cli/references/templates.md` — DAG vs Steps decision table, inline YAML vs `--from wf/` vs `--from cwt/` guidance, WorkflowTemplate/ClusterWorkflowTemplate usage patterns.
**Verification:**
- [ ] Decision table maps workflow complexity (linear steps, branching DAG, parallel stages) to template type
- [ ] Covers `--from` flag syntax with explicit `--namespace` encoding
- [ ] Namespace resolution caveats are documented (auto-resolution unreliable across multi-namespace clusters)
- [ ] ClusterWorkflowTemplate requires cluster-admin prerequisite is noted
**Context cost:** S
**Depends on:** none

## Slice 3: Reference material — debugging escalation path

**Goal:** A step-by-step debugging workflow that escalates from argo commands to kubectl when needed.

**Files touched:**

- ✨ `.claude/skills/using-argo-workflows-cli/references/debugging.md` — Escalation decision matrix (status symptom -> action), common failure causes and remedies, argo -> kubectl transition rules, notes on empty `argo logs` output.
**Verification:**
- [ ] Escalation path: `argo get` -> `argo logs` -> `argo template` -> `kubectl describe pod` -> `kubectl get events`
- [ ] Decision matrix maps workflow status conditions (Pending, Running, Error, CrashLoopBackOff) to specific commands
- [ ] Documents `argo logs` can return empty and explains why
- [ ] kubectl commands are presented as Bash invocations (no new allowed-tools needed — argo and kubectl both use Bash)
**Context cost:** S
**Depends on:** none

## Slice 4: Reference material — CronWorkflow lifecycle

**Goal:** CronWorkflow creation, management, and troubleshooting guidance.

**Files touched:**

- ✨ `.claude/skills/using-argo-workflows-cli/references/cron.md` — CronWorkflow lifecycle commands (create, list, get, delete, suspend, resume, lint), concurrency policy guidance and decision tree, schedule syntax conventions.
**Verification:**
- [ ] Covers all 7 CronWorkflow commands: create, list, get, delete, suspend, resume, lint
- [ ] Concurrency policy options (Allow, Forbid, Replace) are explained with when-to-use guidance
- [ ] `argo cron lint` is covered as the validation step
- [ ] Assumes agent knows cron syntax — no generator encoded
**Context cost:** S
**Depends on:** none

## Slice 5: Reference material — artifact configuration and resource management

**Goal:** Best practices for artifacts (repository, key patterns, garbage collection) and resource management (limits, node selectors, parallelism, synchronization, priorities).

**Files touched:**

- ✨ `.claude/skills/using-argo-workflows-cli/references/artifacts.md` — Default repository config, `.tgz` suffix convention, UID-parameterized keys, input vs output artifacts, artifact passing vs parameters threshold, garbage collection policies.
- ✨ `.claude/skills/using-argo-workflows-cli/references/resources.md` — Resource requests/limits, nodeSelector, tolerations, parallelism, synchronization semaphores, podPriorityClassName.
**Verification:**
- [ ] Covers `.tgz` suffix convention for artifact compression
- [ ] UID-parameterized key pattern (`{{workflow.uid}}/...`) is documented
- [ ] Input vs output artifact distinction with passing examples
- [ ] Garbage collection strategies (TTL, label-based) are explained
- [ ] Resource section covers all 6 acceptance area items from design.md
**Context cost:** S
**Depends on:** none

## Slice 6: Reference material — retry strategies and error handling

**Goal:** Retry strategy conventions and idempotency guidance.

**Files touched:**

- ✨ `.claude/skills/using-argo-workflows-cli/references/retries.md` — `retryStrategy` fields, `backoff.duration/factor/maxDuration`, `retryPolicy` selection, idempotency requirements for retries.
**Verification:**
- [ ] Documents all `retryStrategy` configuration fields
- [ ] Backoff configuration (duration, factor, maxDuration) is covered with examples
- [ ] `retryPolicy` values (Default, Always, OnError, OnFailure, ResultError) are explained
- [ ] Idempotency requirements for retry-safe workflows are explicitly stated
**Context cost:** S
**Depends on:** none

---

## Unverified Assumptions

1. **The `skill-creator` skill's progressive disclosure convention applies to argo skills.** The design assumes references/ files are loaded on demand via `Read`. I could not locate a separate `skill-creator/SKILL.md` file in this repo to verify the exact referencing convention. If the convention differs from my assumption about how agents discover references, the SKILL.md body may need to explicitly instruct `Read` calls.

2. **`allowed-tools` can be minimal (Bash + Read).** Open question OQ1 in design.md is unresolved. I assumed Bash (for running `argo` and `kubectl`) and Read (for references) are sufficient. If additional MCP tools are needed (e.g., Linear for workflow tracking), the frontmatter would need updating.

3. **The `command` field should use `/using-argo-workflows-cli` as a slash command.** Design OQ3 is unresolved. I chose a slash command based on the pattern of existing skills (e.g., `/qrspi-work`), but this should be confirmed. If the skill should trigger purely via description matching, the `command` and `argument-hint` fields should be omitted.

4. **Reference files total ~4 files of ~50-150 lines each, keeping SKILL.md body under 500 lines.** This is a planning estimate. The actual line count depends on content depth during implementation. The design's risk register flags this as Medium likelihood / High impact.

5. **kubectl is accessed via Bash, not as a dedicated allowed-tool.** The SKILL.md instructs agents to run `kubectl` commands through the same Bash tool used for `argo`. This avoids expanding the allowed-tools list but means kubectl is not a first-class tool in the skill.

6. **No eval fixtures need to be created for this slice.** Design OQ6 and risk register item about "no existing Argo workflow YAMLs as test fixtures" suggest fixture creation is a future ticket. This structure assumes manual review against acceptance criteria is sufficient for now.
