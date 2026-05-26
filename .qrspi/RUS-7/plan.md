# Implementation Plan — Create a new agent skill called using argo workflows cli

**Structure basis:** structure.md @ 2026-05-26
**Generated:** 2026-05-26
**Status:** draft

---

## Slice 1: Argo Workflows CLI Skill

**Goal:** Deliver the complete `using-argo-workflows-cli` skill — SKILL.md with frontmatter and compact body, three topic-based reference files, and CLAUDE.md registration.

**Depends on:** none

---

### Step 1.1 — Create skill directory structure

**Action:** Create directory `.claude/skills/using-argo-workflows-cli/references/`

**File:** `.claude/skills/using-argo-workflows-cli/references/` (directory)

**Purpose:** Establish the skill directory and references subdirectory in one operation. The parent `.claude/skills/using-argo-workflows-cli/` is created implicitly.

**Command:**
```bash
mkdir -p .claude/skills/using-argo-workflows-cli/references/
```

---

### Step 1.2 — Create template-authoring.md reference file

**Action:** Create new file

**File:** `.claude/skills/using-argo-workflows-cli/references/template-authoring.md`

**Purpose:** DAG vs Steps detailed guidance, WorkflowTemplates, ClusterWorkflowTemplates, and template design patterns. Target 60-80 lines.

**Content requirements (from structure.md and design.md):**
- DAG vs Steps rule: DAG by default for complex workflows, Steps only for simple sequential
- WorkflowTemplate patterns: when to use, how to reference
- ClusterWorkflowTemplate patterns: cluster-scoped reuse
- Template design patterns: parameterization, input/output artifacts, template composition

---

### Step 1.3 — Create debugging-and-errors.md reference file

**Action:** Create new file

**File:** `.claude/skills/using-argo-workflows-cli/references/debugging-and-errors.md`

**Purpose:** Full escalation ladder, common failure modes, and retry configuration. Target 60-80 lines.

**Content requirements (from structure.md and design.md):**
- Escalation ladder detail: `argo get` -> `argo logs` -> `kubectl describe pod` -> `kubectl get events`
- Common failure modes: OOMKilled, ImagePullBackOff, volume mount errors, pending pods
- Retry configuration: `retryPolicy`, exponential backoff, `activeDeadlineSeconds`, idempotency requirement

---

### Step 1.4 — Create cron-and-resources.md reference file

**Action:** Create new file

**File:** `.claude/skills/using-argo-workflows-cli/references/cron-and-resources.md`

**Purpose:** CronWorkflow lifecycle, resource management, artifact configuration. Target 60-80 lines.

**Content requirements (from structure.md and design.md):**
- CronWorkflow lifecycle: create, list, suspend, resume, lint, get
- Concurrency policy, timezone, history limit
- Resource requests/limits conventions
- Parallelism and synchronization configuration
- Artifact configuration: default artifact repo, `.tgz` suffix, `workflow.uid` in keys, artifact vs params for large data

---

### Step 1.5 — Create SKILL.md

**Action:** Create new file

**File:** `.claude/skills/using-argo-workflows-cli/SKILL.md`

**Purpose:** Skill frontmatter and compact body. Target 150-200 lines for body, under 500 lines total.

**Frontmatter contract (from structure.md):**
```yaml
---
name: using-argo-workflows-cli
description: "<trigger description for argo-related work>"
command: /using-argo-workflows-cli
argument-hint: <argo subcommand or workflow task description>
allowed-tools: Read, Bash(argo:*), Bash(kubectl:*), Bash(which:*)
---
```

**Body content requirements (from structure.md and design.md):**
- Prerequisite check (PD-4): Run `which argo` and `which kubectl`; if either missing, STOP with install instructions
- Command group guidance covering all 14 groups: submit, list, get, logs, watch, delete, cron, lint, retry, resubmit, stop, terminate, suspend, resume
- DAG vs Steps rule (summary; detail in reference file)
- Retry/error core rules (summary; detail in reference file)
- Debugging escalation ladder summary
- CronWorkflow core commands (summary; detail in reference file)
- Resource management rules
- Artifact core rules (summary; detail in reference file)
- Read instructions pointing to each of the 3 reference files:
  - `Read .claude/skills/using-argo-workflows-cli/references/template-authoring.md`
  - `Read .claude/skills/using-argo-workflows-cli/references/debugging-and-errors.md`
  - `Read .claude/skills/using-argo-workflows-cli/references/cron-and-resources.md`

---

### Step 1.6 — Register skill in .claude/CLAUDE.md

**Action:** Modify existing file

**File:** `.claude/CLAUDE.md`

**Current (lines 21-22):**
```markdown
- `/qrspi-pr <ticket-id>` — Prepare pull request summary

### Workflow rules
```

**After:**
```markdown
- `/qrspi-pr <ticket-id>` — Prepare pull request summary

### Advisory skills

- `/using-argo-workflows-cli <argo subcommand or task>` — Guide agents managing Argo Workflows via the argo CLI

### Workflow rules
```

**Purpose:** Add the new skill to the Available skills section in a separate "Advisory skills" subsection after the QRSPI phase skills, per structure.md CLAUDE.md registration contract and design.md PD-5.

---

### Step 1.7 — Verify: line counts

**Action:** Run verification commands

**Commands:**
```bash
echo "=== SKILL.md body line count (should be under 200) ==="
# Count lines after frontmatter closing ---
tail -n +$(grep -n '^---$' .claude/skills/using-argo-workflows-cli/SKILL.md | tail -1 | cut -d: -f1) .claude/skills/using-argo-workflows-cli/SKILL.md | wc -l

echo "=== SKILL.md total line count (should be under 500) ==="
wc -l .claude/skills/using-argo-workflows-cli/SKILL.md

echo "=== Reference file line counts (each should be under 80) ==="
wc -l .claude/skills/using-argo-workflows-cli/references/*.md
```

**Expected:** SKILL.md body under 200 lines, total under 500 lines, each reference file under 80 lines.

---

### Step 1.8 — Verify: frontmatter fields

**Action:** Run verification command

**Command:**
```bash
echo "=== Checking 5 required frontmatter fields ==="
head -10 .claude/skills/using-argo-workflows-cli/SKILL.md | grep -cE '^(name|description|command|argument-hint|allowed-tools):'
```

**Expected:** Output is `5` (all 5 required frontmatter fields present).

---

### Step 1.9 — Verify: command group coverage

**Action:** Run verification command

**Command:**
```bash
echo "=== Checking all 14 command groups are mentioned ==="
for cmd in submit list get logs watch delete cron lint retry resubmit stop terminate suspend resume; do
  if grep -qi "$cmd" .claude/skills/using-argo-workflows-cli/SKILL.md; then
    echo "  OK: $cmd"
  else
    echo "  MISSING: $cmd"
  fi
done
```

**Expected:** All 14 command groups report OK.

---

### Step 1.10 — Verify: Read instructions and prerequisite check

**Action:** Run verification command

**Command:**
```bash
echo "=== Checking Read instructions for all 3 reference files ==="
grep -c 'Read .claude/skills/using-argo-workflows-cli/references/' .claude/skills/using-argo-workflows-cli/SKILL.md

echo "=== Checking prerequisite check pattern ==="
grep -c 'which argo' .claude/skills/using-argo-workflows-cli/SKILL.md
grep -c 'which kubectl' .claude/skills/using-argo-workflows-cli/SKILL.md
```

**Expected:** Read instruction count is 3. Both `which argo` and `which kubectl` are present.

---

### Step 1.11 — Verify: CLAUDE.md registration

**Action:** Run verification command

**Command:**
```bash
echo "=== Checking CLAUDE.md contains new skill entry ==="
grep -c 'using-argo-workflows-cli' .claude/CLAUDE.md
```

**Expected:** Output is at least `1`.

---

### Step 1.12 — Verify: invoke skill-creator for validation

**Action:** Invoke the `skill-creator` skill to validate the generated skill files.

**Purpose:** Per structure.md verification checklist and design.md AC, the skill-creator must be invoked as the final validation step. This validates frontmatter schema, file structure, and overall skill quality.

**Note:** The skill-creator's internal validation scope is uncertain (structure.md Unverified Assumption 4). If it only scaffolds new skills rather than validating existing ones, document the outcome and proceed. The manual verification steps (1.7-1.11) serve as the primary validation.

---

## Summary

| Slice | Steps | New files | Modified files |
|-------|-------|-----------|----------------|
| 1     | 12    | 4 (SKILL.md + 3 reference files) | 1 (.claude/CLAUDE.md) |
| **Total** | **12** | **4** | **1** |

## Rollback Notes

No database migrations, config changes, or destructive operations in this plan. All changes are additive (new files + one append to CLAUDE.md). Rollback is:
1. Delete directory `.claude/skills/using-argo-workflows-cli/`
2. Remove the "Advisory skills" subsection from `.claude/CLAUDE.md`

## Unverified Assumptions Carried Forward

These are inherited from structure.md and affect implementation but cannot be resolved during planning:

1. **Bash(argo:*) permission syntax** — May not be supported for external binaries. Fallback: unrestricted `Bash`.
2. **Argo CLI version** — Skill will target v3.5+ with a version note. Flag differences cannot be verified without the binary.
3. **Argo CLI command accuracy** — All commands sourced from documentation, not local testing.
4. **skill-creator validation scope** — May only scaffold, not validate. Manual verification steps serve as primary checks.
