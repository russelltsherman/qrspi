# Implementation Plan — Create a new agent skill using argo workflows cli

**Structure basis:** structure.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft
**Total steps:** 22

> **Blocking open questions (resolve before starting).** Per structure.md Unverified Assumptions:
> - **OQ1** sets the directory name / `name` / `command`. This plan assumes `using-argo-workflows-cli` (design Decision 2, Option A). If reversed, rename every path below.
> - **OQ2** sets frontmatter `allowed-tools` (read-only vs. executable). Used in Step 4.
> - **OQ5** sets the targeted argo CLI / Argo Workflows version string. Used in Steps 8, 11, 14, 17.
> - **OQ3** gates whether Slice 2 runs at all.
> - **OQ4** confirmed out of scope — no eval case is created by this plan.

## Slice 1: Author the `using-argo-workflows-cli` skill (body + references)

### Setup

1. **Build action (process step, not a committed file):** Invoke the global `skill-creator` skill to scaffold `using-argo-workflows-cli`. Treat its output as a starting scaffold to be reconciled to repo conventions in the steps below — do not accept it blindly (ref: structure Verify "skill-creator was used", design Risk Register row 2; OQ4 confirms no eval scaffolding).

2. ✨ Create directory `.claude/skills/using-argo-workflows-cli/references/` — establishes the agentskills.io layout: `SKILL.md` at the skill root plus a `references/` subtree (ref: structure Verify "Directory layout matches agentskills.io", Q1).

### Core Logic — SKILL.md body

3. ✨ Create `.claude/skills/using-argo-workflows-cli/SKILL.md` — the lean body file (frontmatter + when-to-use + decision-first overview + reference pointers). Created empty/scaffolded here; populated in Steps 4–7 (ref: structure §Slice 1 Files touched, design §Delta).

4. ⚠️ Modify `.claude/skills/using-argo-workflows-cli/SKILL.md` — write the frontmatter block.
   - **Current:** scaffolded/empty file from Step 3.
   - **After:** YAML frontmatter with exactly the 5 repo-standard fields and nothing else: `name: using-argo-workflows-cli`, `description: <when-to-use trigger sentence>`, `command: /using-argo-workflows-cli`, `argument-hint: <brief usage hint>`, `allowed-tools: <value per OQ2>`. The directory name == `name` == `command` sans leading `/` invariant MUST hold (ref: structure Contracts "directory name == frontmatter.name == frontmatter.command", Q3, Q9, Decision 3). No `version` field, no extras.

5. ⚠️ Modify `.claude/skills/using-argo-workflows-cli/SKILL.md` — add the "When to use" section describing the skill as general-purpose argo guidance (capability skill, not a QRSPI phase) (ref: design Desired End State, Decision 2).

6. ⚠️ Modify `.claude/skills/using-argo-workflows-cli/SKILL.md` — add a decision-first overview that summarizes each named convention (DAG/Steps decision, retry/backoff, debugging escalation, CronWorkflow lifecycle, resource conventions, artifact best practices) in one or two lines each (ref: structure Verify "summarized in the body", design §Delta).

7. ⚠️ Modify `.claude/skills/using-argo-workflows-cli/SKILL.md` — add a "References" section that names each of the four reference files and states explicitly when to open each one (decision-first pointers). Every reference file must be named here; no orphan files (ref: structure Contracts "SKILL.md body → references/*.md", Q6, Q8).

### Core Logic — reference files

8. ✨ Create `.claude/skills/using-argo-workflows-cli/references/cli-commands.md` — full command-group catalog covering all 15 acceptance-criteria groups: submit, get, logs, list, delete, retry, resubmit, stop, terminate, suspend, resume, watch, lint, cron, template — each with flags. State the targeted argo version (OQ5) at the top. All invocations use non-interactive/scriptable flags: explicit `--namespace`, and lint/dry-run before submit (ref: structure Verify "All 15 command groups", "non-interactive/scriptable flags", Q4, design §Desired End State).

9. ✨ Create `.claude/skills/using-argo-workflows-cli/references/templates.md` — DAG vs Steps decision criteria, template authoring, parameters/variables, and WorkflowTemplate vs ClusterWorkflowTemplate scope (ref: structure §Slice 1 Files touched, design §Delta).

10. ✨ Create `.claude/skills/using-argo-workflows-cli/references/reliability.md` — retry strategy / exponential backoff, error handling, timeouts, resource management (limits, nodeSelector, parallelism, synchronization), and artifact best practices (keys, parameterization, GC) (ref: structure §Slice 1 Files touched, design §Delta).

11. ✨ Create `.claude/skills/using-argo-workflows-cli/references/cron-and-debugging.md` — CronWorkflow lifecycle (create/list/suspend/resume/delete/lint/get) and the debugging escalation path `argo get` → `argo logs` → `kubectl describe` (ref: structure §Slice 1 Files touched, design §Desired End State).

12. ⚠️ Modify reference files (`templates.md`, `reliability.md`, `cron-and-debugging.md`) — add the targeted argo version note (OQ5) and confirm guidance is principle-based rather than version-specific flag minutiae (ref: design Risk Register row 5, OQ5).

### Tests / Conformance checks (no automated suite exists — manual)

13. Run: `test -f .claude/skills/using-argo-workflows-cli/SKILL.md && ls .claude/skills/using-argo-workflows-cli/references/`
    - **Expected:** `SKILL.md` exists and the four reference files (`cli-commands.md`, `templates.md`, `reliability.md`, `cron-and-debugging.md`) are listed.

14. Run: `wc -l .claude/skills/using-argo-workflows-cli/SKILL.md`
    - **Expected:** body ≤ 500 lines. Also confirm ≤ 5000 tokens by manual estimate (no automated token check exists — ref: structure Verify, Q7, design Risk Register row 1).

15. Run: `grep -c -E 'cli-commands|templates|reliability|cron-and-debugging' .claude/skills/using-argo-workflows-cli/SKILL.md`
    - **Expected:** ≥ 4 — every reference filename is named in the body, with surrounding when-to-open guidance verified by reading (no orphan references — ref: structure Contracts).

16. Run: `grep -E -o 'submit|get|logs|list|delete|retry|resubmit|stop|terminate|suspend|resume|watch|lint|cron|template' .claude/skills/using-argo-workflows-cli/references/cli-commands.md | sort -u | wc -l`
    - **Expected:** all 15 command groups present in `cli-commands.md` (ref: structure Verify).

### Verify Slice 1

17. **Checkpoint:** `ls -R .claude/skills/using-argo-workflows-cli/ && wc -l .claude/skills/using-argo-workflows-cli/SKILL.md`
    - [ ] Directory layout matches agentskills.io: `SKILL.md` at root + `references/` with four files (Q1).
    - [ ] Frontmatter has exactly the 5 repo-standard fields; directory == `name` == `command` sans `/` (Q3, Q9).
    - [ ] SKILL.md body ≤ 500 lines and ≤ 5000 tokens, manually counted (Q7).
    - [ ] Every reference file is named in the body with explicit when-to-open guidance; no orphans (Contracts).
    - [ ] All 15 command groups appear in `cli-commands.md` (Verify).
    - [ ] Each named convention (DAG/Steps, retry/backoff, debugging escalation, CronWorkflow lifecycle, resource conventions, artifact best practices) is present in its assigned reference file and summarized in the body.
    - [ ] All CLI invocations use non-interactive/scriptable flags (explicit `--namespace`, lint/dry-run before submit) (Q4).
    - [ ] `skill-creator` was used to scaffold/refine and its output was reconciled to repo's 5-field frontmatter + layout (Q2, Risk Register).
    - [ ] OQ2 and OQ5 resolutions are reflected in frontmatter and reference content.

---

## Slice 2 (conditional): Register skill in project `.claude/CLAUDE.md`

> **Skip this entire slice unless OQ3 is resolved "yes."** The skill functions without it (skills are auto-discovered — ref: structure §Slice 2 Conditional, Q1, Q9).

### Setup

18. **Gate:** Confirm OQ3 resolved "yes." If not resolved or "no," stop — do not modify `.claude/CLAUDE.md` (ref: structure §Slice 2 Verify "OQ3 has been resolved 'yes'").

### Core Logic

19. ⚠️ Modify `.claude/CLAUDE.md` — add `using-argo-workflows-cli` to the "Available skills" list with a one-line description consistent with the existing entries.
    - **Current:** "Available skills" list enumerates only `qrspi-*` workflow skills (ref: structure §Slice 2, project CLAUDE.md).
    - **After:** list additionally includes `- `/using-argo-workflows-cli`` — <one-line description matching SKILL.md `description`>`.

### Tests

20. Run: `grep -F 'using-argo-workflows-cli' .claude/CLAUDE.md`
    - **Expected:** one matching line in the "Available skills" section.

### Verify Slice 2

21. **Checkpoint:** `grep -n -F 'using-argo-workflows-cli' .claude/CLAUDE.md`
    - [ ] OQ3 was resolved "yes" before this slice ran.
    - [ ] `.claude/CLAUDE.md` lists `using-argo-workflows-cli` with a description consistent with the other entries.

---

## Rollback Notes

- **Step 19 (config / `.claude/CLAUDE.md` edit):** to reverse, delete the added `using-argo-workflows-cli` line from the "Available skills" list, restoring the `qrspi-*`-only list. No functional impact — registration is documentation-only; the skill remains auto-discovered either way.
- **Steps 2–11 (new files/dir):** to reverse, `rm -rf .claude/skills/using-argo-workflows-cli/`. These are net-new, untracked-until-committed paths; removal has no effect on existing skills.
- No DB migrations or destructive operations are involved in this plan.
