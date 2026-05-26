# Structure Outline — Create a new agent skill called using argo workflows cli

**Design basis:** design.md @ 2026-05-26
**Generated:** 2026-05-26
**Status:** draft

## New Types

None. This ticket produces static markdown files (a skill definition and reference documents), not executable code with types or data structures.

## Modified Types

None.

## Contracts

### Cross-file references within the skill

The SKILL.md body contains explicit `Read` instructions pointing to each reference file. These constitute the contract between the skill body and its reference material:

- `Read .claude/skills/using-argo-workflows-cli/references/template-authoring.md` — loaded when agent needs DAG vs Steps guidance, WorkflowTemplate/ClusterWorkflowTemplate patterns, or template design decisions
- `Read .claude/skills/using-argo-workflows-cli/references/debugging-and-errors.md` — loaded when agent encounters a failed workflow, needs the escalation ladder, or is configuring retry strategies
- `Read .claude/skills/using-argo-workflows-cli/references/cron-and-resources.md` — loaded when agent is working with CronWorkflows, setting resource limits, configuring parallelism/synchronization, or managing artifacts

### Frontmatter contract

```yaml
---
name: using-argo-workflows-cli
description: "<trigger description for argo-related work>"
command: /using-argo-workflows-cli
argument-hint: <argo subcommand or workflow task description>
allowed-tools: Read, Bash(argo:*), Bash(kubectl:*), Bash(which:*)
---
```

### CLAUDE.md registration contract

A new entry is added to the "Available skills" list in `.claude/CLAUDE.md`, following the existing format:

```
- `/using-argo-workflows-cli <argo subcommand or task>` — Guide agents managing Argo Workflows via the argo CLI
```

This is listed in a separate section from the QRSPI phase skills, since it is a general advisory skill (per PD-5).

## Slice 1: Argo Workflows CLI Skill

**Goal:** Deliver the complete `using-argo-workflows-cli` skill — SKILL.md with frontmatter and compact body, three topic-based reference files, and CLAUDE.md registration — as a testable, self-contained unit. Invoke `skill-creator` as the final validation step.

**Files touched:**

- ✨ `.claude/skills/using-argo-workflows-cli/SKILL.md` — Frontmatter (name, description, command, argument-hint, allowed-tools) + compact skill body (target 150-200 lines) covering: prerequisite check (PD-4), command group guidance (submit, list, get, logs, watch, delete, cron, lint, retry, resubmit, stop, terminate, suspend, resume), DAG vs Steps rule, retry/error core rules, debugging escalation ladder summary, CronWorkflow core commands, resource management rules, artifact core rules, and Read instructions pointing to each reference file
- ✨ `.claude/skills/using-argo-workflows-cli/references/template-authoring.md` — DAG vs Steps detailed guidance, WorkflowTemplates, ClusterWorkflowTemplates, template design patterns (target 60-80 lines)
- ✨ `.claude/skills/using-argo-workflows-cli/references/debugging-and-errors.md` — Full escalation ladder detail, common failure modes (OOMKilled, ImagePullBackOff, volume mount errors, pending pods), retry configuration (retryPolicy, exponential backoff, activeDeadlineSeconds, idempotency) (target 60-80 lines)
- ✨ `.claude/skills/using-argo-workflows-cli/references/cron-and-resources.md` — CronWorkflow lifecycle (create, list, suspend, resume, lint, get), concurrency policy, timezone, history limit, resource requests/limits, parallelism, synchronization, artifact configuration (default repo, .tgz suffix, workflow.uid keys, artifact vs params) (target 60-80 lines)
- ⚠️ `.claude/CLAUDE.md` — Add `using-argo-workflows-cli` to the Available skills list, in a new "Advisory skills" subsection after the QRSPI phase skills

**Verification:**

- [ ] `SKILL.md` has valid YAML frontmatter with all 5 required fields (name, description, command, argument-hint, allowed-tools)
- [ ] `SKILL.md` body is under 200 lines (`wc -l`)
- [ ] `SKILL.md` body is under 500 lines total including frontmatter
- [ ] Each reference file is under 80 lines (`wc -l`)
- [ ] `SKILL.md` body contains Read instructions for all 3 reference files
- [ ] `SKILL.md` covers all 14 command groups listed in the ticket (submit, list, get, logs, watch, delete, cron, lint, retry, resubmit, stop, terminate, suspend, resume)
- [ ] `SKILL.md` begins with prerequisite check (`which argo`, `which kubectl`)
- [ ] `.claude/CLAUDE.md` contains the new skill entry
- [ ] Invoke `skill-creator` to validate the skill files

**Context cost:** M

**Depends on:** none

---

## Unverified Assumptions

1. **Bash permission syntax for external CLIs.** The design recommends `Bash(argo:*)` and `Bash(kubectl:*)` scoping. No existing skill scopes Bash to an external CLI binary — all existing scoped permissions target standard Unix utilities. Whether Claude Code supports `Bash(argo:*)` syntax for non-standard binaries is unverified (design.md Open Question 1, Risk Register row 2). Fallback: use unrestricted `Bash` if scoped syntax is unsupported.

2. **Argo CLI version targeting.** The design does not resolve which argo version(s) to target (design.md Open Question 2). Some flags differ between v3.4, v3.5, and v3.6. The skill will include a version note (e.g., "argo v3.5+") but correctness of specific flags cannot be verified without the argo binary installed.

3. **Argo CLI command surface accuracy.** The argo binary is not installed in the development environment (research Q5). All command groups, flags, and behaviors documented in the skill must be sourced from external Argo Workflows documentation. Incorrect flags or missing subcommands cannot be caught by local testing.

4. **skill-creator validation scope.** The skill-creator is a platform built-in whose internal validation logic is not inspectable (research Q3, Q7). It is unclear whether skill-creator validates frontmatter schema, line count limits, or reference file structure. It may only scaffold new skills rather than validate existing ones.

5. **kubectl as an explicit dependency.** The debugging escalation ladder requires `kubectl` (design.md Open Question 3). The design includes `Bash(kubectl:*)` in allowed-tools, but whether this skill should defer to a separate kubectl skill (if one exists in the future) is unresolved. Current structure includes kubectl in scope.
