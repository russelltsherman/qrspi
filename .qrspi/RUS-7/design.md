# Design — Create a new agent skill called using argo workflows cli
**Ticket:** RUS-7
**Generated:** 2026-05-26
**Status:** draft

## Current State

All skills in this codebase live under `.claude/skills/<skill-name>/` and are discovered by directory convention -- Claude Code scans for `SKILL.md` files at session start (ref: Q1, Q8). There are 10 existing skills, all focused on document generation and QRSPI workflow orchestration; none wraps an external CLI binary (ref: Q6, Q14). Only one skill (`qrspi-work`) uses a `references/` subdirectory; no skill uses `scripts/` or `assets/` (ref: Q1). Every `SKILL.md` uses identical YAML frontmatter fields: `name`, `description`, `command`, `argument-hint`, `allowed-tools` (ref: Q2). Per-phase skills average 47 lines; only the orchestrator reaches 500 lines (ref: Q6). The `argo` CLI is not installed in this environment and no file in the codebase references Argo Workflows (ref: Q5). No existing skill performs upfront prerequisite checks for CLI binaries -- error handling follows a reactive HARD STOP pattern: attempt, fail, stop, report (ref: Q10, Q11). The `skill-creator` is a Claude Code platform built-in whose internal logic is not inspectable from this codebase (ref: Q3, Q7). Skills that need Bash access use fine-grained permissions like `Bash(wc:*)` and `Bash(find:*)`; only two skills have unrestricted `Bash` access (ref: Q10). The eval harness exists in `evals/` and `scripts/` but agent execution and LLM judge scoring are stubs (ref: Q12, Q13). No skill includes observability guidance for wrapped CLI tools (ref: Q14). Progress output follows the pattern `Print: "<phase> complete. Moving to <next>..."` -- there is no real-time status stream convention (ref: Q15).

## Desired End State

Each acceptance criterion maps to a concrete system behavior:

**AC: Skill follows agentskills.io directory structure with valid SKILL.md frontmatter.** A new directory `.claude/skills/using-argo-workflows-cli/` exists containing a `SKILL.md` with frontmatter fields `name`, `description`, `command`, `argument-hint`, and `allowed-tools`. A `references/` subdirectory holds supplementary material.

**AC: Built using the Anthropic skill builder skill.** The `skill-creator` skill is invoked during implementation to generate and validate the skill files.

**AC: SKILL.md body under 500 lines / 5000 tokens.** The main `SKILL.md` body stays compact (target under 200 lines). Detailed reference material is offloaded to `references/` files, following the `qrspi-work/references/review-cascade.md` precedent.

**AC: Detailed reference material in references/ directory if needed.** Reference files cover areas that would bloat the skill body: debugging flowcharts, template authoring patterns, CronWorkflow lifecycle, artifact configuration. The skill body contains explicit `Read` instructions pointing to each reference file.

**AC: Covers all major argo CLI command groups.** The skill body organizes guidance by command group: `submit`, `list`, `get`, `logs`, `watch`, `delete`, `cron`, `lint`, `retry`, `resubmit`, `stop`, `terminate`, `suspend`, `resume`. Additional groups not in the ticket (e.g., `archive`, `cluster-template`, `auth`) are noted in reference material if relevant.

**AC: Includes DAG vs Steps guidance.** The skill body encodes the rule: DAG by default for complex workflows, Steps only for simple sequential. Template authoring details live in a reference file.

**AC: Encodes retry strategy and error handling.** The skill body provides the core retry rules (exponential backoff, `retryPolicy`, idempotency requirement, `activeDeadlineSeconds`). Detailed retry configuration lives in a reference file.

**AC: Provides debugging workflow.** The skill body contains the escalation ladder: `argo get` then `argo logs` then `kubectl describe pod` then `kubectl get events`. A reference file covers common failure modes and their resolutions.

**AC: Covers CronWorkflow lifecycle.** The skill body covers `argo cron create/list/suspend/resume/lint/get`. Concurrency policy, timezone, and history limit details live in a reference file.

**AC: Includes resource management conventions.** The skill body encodes: always set `resources.requests` and `resources.limits`, use `parallelism` for pod limits, use `synchronization` for shared resources.

**AC: Addresses artifact configuration best practices.** The skill body provides the core rules (default artifact repo, `.tgz` suffix, `workflow.uid` in keys, artifact over params for large data). Detailed configuration lives in a reference file.

## Delta

### New Files

| File | Purpose | Size target |
|------|---------|-------------|
| `.claude/skills/using-argo-workflows-cli/SKILL.md` | Frontmatter + compact skill body with numbered rules | 150-200 lines |
| `.claude/skills/using-argo-workflows-cli/references/template-authoring.md` | DAG vs Steps, WorkflowTemplates, ClusterWorkflowTemplates, template design | 60-80 lines |
| `.claude/skills/using-argo-workflows-cli/references/debugging-and-errors.md` | Escalation ladder, common failures (OOMKilled, image pull, volumes), retry configuration | 60-80 lines |
| `.claude/skills/using-argo-workflows-cli/references/cron-and-resources.md` | CronWorkflow lifecycle, resource management, artifact configuration | 60-80 lines |

### Modified Files

| File | Change |
|------|--------|
| `.claude/CLAUDE.md` | Add the new skill to the "Available skills" list |

### No Changes Needed

No existing skill files, eval suite, or scripts require modification. The new skill is additive. Eval coverage for this skill is out of scope for this ticket (the eval harness is not yet operational per Q12/Q13).

## Pattern Decisions

### PD-1: Skill body structure -- monolithic vs split with references

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A: Monolithic SKILL.md | All guidance in a single file, no references/ | Simpler discovery; no Read instructions needed | Will exceed 500-line limit given the breadth of argo CLI surface |
| **B: Split body + references/ (recommended)** | Compact skill body with explicit `Read` instructions pointing to reference files | Stays within 500-line / 5000-token budget; matches `qrspi-work` precedent | Agent must perform extra Read calls; slightly more complex |

**Recommendation:** Option B. The ticket's CLI surface spans 10+ command groups with detailed conventions for each. The only existing skill approaching this breadth (`qrspi-work`) uses the split pattern. This is an EXISTING PATTERN (ref: Q4).

### PD-2: Bash permission scope in allowed-tools

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A: Unrestricted `Bash` | Full Bash access | Simple; lets agent run any argo/kubectl command | Overly permissive; breaks codebase convention where most skills use scoped Bash |
| B: Scoped `Bash(argo:*)`, `Bash(kubectl:*)` | Fine-grained scoping to argo and kubectl binaries | Follows existing convention of scoped Bash; limits blast radius | Agent cannot run other diagnostic commands (e.g., `curl`, `jq`) |
| **C: Scoped `Bash(argo:*)`, `Bash(kubectl:*)`, `Bash(which:*)` (recommended)** | Scoped to argo, kubectl, and prerequisite checks | Follows convention; enables the debugging escalation ladder; allows prereq check | Slightly more verbose frontmatter |

**Recommendation:** Option C. The skill needs both `argo` and `kubectl` (for the debugging escalation ladder). Adding `which` enables a prerequisite check pattern. This is a NEW PATTERN -- no existing skill scopes Bash to an external CLI binary. All existing scoped Bash permissions target standard Unix utilities (`wc`, `find`, `head`, `tail`, `git diff`).

### PD-3: Reference file organization

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A: Single reference file | One `references/argo-reference.md` with all detail | Fewer files; single Read call | Could grow unwieldy (200+ lines); less targeted loading |
| **B: Topic-based reference files (recommended)** | 3 reference files split by topic: template authoring, debugging/errors, cron/resources | Agent loads only what it needs for the current task; each file stays under 80 lines | More files to maintain; skill body needs multiple Read instructions |
| C: Command-group reference files | One file per argo command group | Maximally targeted | Too many small files (10+); excessive fragmentation |

**Recommendation:** Option B. Three topic files balance granularity against file count. The agent typically needs one topic area at a time (e.g., debugging a failure vs authoring a template vs managing cron schedules).

### PD-4: Prerequisite check pattern

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A: Reactive HARD STOP only | Match existing pattern: attempt command, stop on "command not found" | Consistent with all 10 existing skills | Poor UX; agent starts work then fails partway through |
| **B: Proactive check + HARD STOP fallback (recommended)** | Skill body begins with "Run `which argo` and `which kubectl`; if either is missing, STOP with install instructions" | Better UX; fails fast with actionable guidance | NEW PATTERN -- no existing skill does proactive prereq checks |

**Recommendation:** Option B. This is the first CLI-wrapping skill in the codebase (ref: Q5, Q10). CLI-wrapping skills have fundamentally different failure modes than document-generation skills. A proactive check is appropriate. Flag: this is a NEW PATTERN that sets precedent for future CLI-wrapping skills.

### PD-5: Skill invocation model

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| **A: Advisory skill (recommended)** | Skill is auto-invoked when agent detects argo-related work; provides guidance but does not own a workflow phase | Matches the ticket intent ("guides agents when managing Argo Workflows"); no QRSPI workflow dependency | No structured input/output contract; agent decides when to apply guidance |
| B: Phase-bound skill | Skill is integrated into the QRSPI workflow as a new phase | Structured invocation; clear input/output | Argo is not a QRSPI phase; forced integration creates coupling |

**Recommendation:** Option A. The ticket describes a general-purpose advisory skill, not a QRSPI workflow phase. The `description` frontmatter field should encode trigger conditions (e.g., "Use when managing Argo Workflows via the argo CLI"). This matches how the `using-graphite-cli` skill works -- it is advisory and auto-invoked based on context.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| SKILL.md body exceeds 500-line / 5000-token limit despite split pattern | Medium | High -- skill prompt too long, degraded agent performance | Target 150-200 lines in body. Run `wc -l` and token count validation after generation. Offload aggressively to references/. |
| Scoped Bash permissions (`Bash(argo:*)`) may not match Claude Code's permission syntax for external binaries | Medium | High -- skill cannot execute any argo commands | Verify syntax against Claude Code permission model during implementation. Fallback: use unrestricted `Bash` if scoped syntax is unsupported for external binaries. |
| Argo CLI is not installed in the dev environment, preventing local testing of skill guidance accuracy | High | Medium -- cannot verify that commands and flags in the skill are correct | Cross-reference all commands against official Argo Workflows CLI documentation. Include version note in skill (e.g., "tested against argo v3.5+"). |
| New prerequisite-check pattern (PD-4 Option B) may be inconsistent with future skills if not adopted broadly | Low | Low -- mild inconsistency across skills | Document the pattern decision in this design. If adopted, propose updating the QRSPI skill template to include a prereq-check section for CLI-wrapping skills. |
| Reference files loaded via Read add latency and context consumption | Low | Low -- minor UX degradation | Keep reference files under 80 lines each. Skill body should instruct agent to load only the relevant reference file, not all three. |

## Open Questions

1. **Bash permission syntax for external CLIs:** Does Claude Code support `Bash(argo:*)` scoping for non-standard binaries? If not, the fallback is unrestricted `Bash` access. This needs verification during implementation.

2. **Argo CLI version targeting:** The ticket does not specify an Argo Workflows version. Some flags and behaviors differ between v3.4, v3.5, and v3.6. Which version(s) should the skill target?

3. **kubectl dependency:** The debugging escalation ladder requires `kubectl`. Should `kubectl` access be an explicit part of this skill's scope, or should the skill defer to a separate kubectl skill if one exists?

4. **CLAUDE.md registration:** The ticket does not specify whether the new skill should be listed in `.claude/CLAUDE.md` under "Available skills." The existing convention lists all skills there, but this skill is not a QRSPI phase skill -- it is a general advisory skill. Should it be listed alongside the QRSPI skills or in a separate section?

5. **Eval coverage:** The eval harness is scaffolded but not operational (ref: Q12). Should this ticket include adding eval cases for the new skill to `evals/suite.json`, or is that deferred to a separate ticket?
