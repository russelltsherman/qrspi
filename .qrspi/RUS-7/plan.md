# Implementation Plan — Create an agent skill for the Argo Workflows CLI

**Structure basis:** structure.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total steps:** 18

> Note: This feature ships Markdown content (a self-contained skill + reference
> docs + catalog updates), not executable code. There are no runtime types or
> function signatures. "Modify" steps below give Current/After document state
> (catalog entries) rather than code signatures. There is no automated validator
> or lint (ref: structure §Contracts note, design Q11); every contract check is a
> manual grep/inspection, reflected in the Verify checkpoint.

## Slice 1: Author the argo-workflows-cli skill, references, and catalog entries

### Setup

1. **Gate (BLOCKING):** Confirm the external `skill-creator` skill is available in
   this environment (Risk #1 / OQ4; structure verification bullet 1). If present,
   author this slice through `skill-creator` and run its eval loop. If absent, STOP
   and escalate as an open question — do **not** hand-author and claim skill-creator
   was used (per user global memory "Use skill-creator for skills" + design Risk #1).
   No file is written by this step; it gates every step below.

2. Resolve the open naming/scoping questions that fix downstream paths and one
   frontmatter field, recording the chosen values for use in steps 3–15:
   - OQ1 skill directory name (assumed `using-argo-workflows-cli`).
   - OQ2 reference-file split (assumed four files: submission-and-monitoring,
     debugging-and-lifecycle, authoring, cron-workflows).
   - OQ3 argo version target / whether the prereq check asserts a minimum version.
   - OQ5 `allowed-tools` scoping (`Bash(argo:*)`/`Bash(kubectl:*)` vs unscoped Bash).
   No file written; values feed steps 3–15.

3. ✨ Create `.claude/skills/using-argo-workflows-cli/` — new self-contained skill
   directory (`SkillDir`). Basename must equal the resolved skill name (satisfies
   `triple-name-invariant`).

4. ✨ Create `.claude/skills/using-argo-workflows-cli/references/` — directory holding
   the topic-scoped progressive-disclosure files (`ReferenceSet`).

### Core Logic

5. ✨ Create `.claude/skills/using-argo-workflows-cli/SKILL.md` — frontmatter only
   first: a `---`-delimited YAML block with exactly the five conventional keys
   `name`, `description`, `command`, `argument-hint`, `allowed-tools`
   (`frontmatter-schema`). Set `name` == dirname, `command` == `/` + dirname
   (`triple-name-invariant`); must NOT use the agent `claude.tools` shape. Pack
   `description` with explicit "Use when…" conditions plus concrete argo trigger
   phrases (`description-trigger-contract`).

6. ⚠️ Modify `.claude/skills/using-argo-workflows-cli/SKILL.md` — append the lean
   body: one-paragraph purpose, then the `argo`-binary availability/prerequisite
   check with a hard-stop-on-failure instruction (surface exact command + error, do
   not work around) (`hard-stop-prereq`; design Decision 4).
   - **Current:** file contains frontmatter block only.
   - **After:** frontmatter + purpose paragraph + prerequisite/hard-stop section.

7. ⚠️ Modify `.claude/skills/using-argo-workflows-cli/SKILL.md` — append a short
   decision-routing section with relative-path pointers `references/<file>.md` to each
   file in `ReferenceSet`, each placed at its decision point (`reference-link-contract`).
   Keep total body under ~500 lines / ~5000 tokens (`body-size-budget`); push all
   command-group detail into the reference files, not the body.
   - **Current:** frontmatter + purpose + prerequisite section.
   - **After:** above + routing section linking all four reference files.

8. ✨ Create `.claude/skills/using-argo-workflows-cli/references/submission-and-monitoring.md`
   — submit/lint/dry-run conventions, parameters, `--from`, monitoring
   (list/get/logs/watch), `@latest`, container selection. Covers command groups:
   submit, lint, list, get, logs, watch (`coverage-contract`).

9. ✨ Create `.claude/skills/using-argo-workflows-cli/references/debugging-and-lifecycle.md`
   — debugging escalation path (argo get → argo logs → kubectl describe), common
   failure causes, and lifecycle commands: retry, resubmit, stop, terminate, suspend,
   resume, delete (`coverage-contract`).

10. ✨ Create `.claude/skills/using-argo-workflows-cli/references/authoring.md`
    — DAG vs Steps decision criteria ("DAG by default; Steps only for purely
    sequential, no-branching"), templates (WorkflowTemplate/ClusterWorkflowTemplate,
    templateRef), parameters/variables, artifacts (key parameterization via
    `{{workflow.uid}}`, `.tgz` suffix, GC), retry strategy/backoff
    (duration/factor/maxDuration, retryPolicy, idempotency, timeouts), resource
    management (requests/limits, nodeSelector, tolerations, parallelism,
    synchronization). Covers command group: template (`coverage-contract`).

11. ✨ Create `.claude/skills/using-argo-workflows-cli/references/cron-workflows.md`
    — cron lifecycle (create/list/suspend/resume/delete/lint), concurrency policy,
    timezone. Covers command group: cron (`coverage-contract`).

### Catalog updates

12. ⚠️ Modify `README.md` — add the new skill to the skills table and the directory
    tree, name matching the directory exactly.
    - **Current:** skills table/tree lists existing skills only (no argo skill).
    - **After:** table row + tree entry for `using-argo-workflows-cli`.

13. ⚠️ Modify `.claude/CLAUDE.md` — add the new skill to the "Available skills" list,
    name matching the directory exactly.
    - **Current:** "Available skills" lists the 10 `qrspi-*` skills only.
    - **After:** list also includes `/using-argo-workflows-cli` with a one-line blurb.

### Tests

14. Run the `skill-creator` eval loop against the authored skill (per step 1 gate;
    structure verification bullet 1). There is no in-repo validator/lint to invoke
    (design Q11), so this eval loop is the only automated authoring check.
    - **Expected:** eval loop passes / reports no blocking issues.

### Verify Slice 1

15. **Checkpoint:** run the following manual contract checks from the worktree root
    (`.worktrees/RUS-7/`):
    `ls .claude/skills/using-argo-workflows-cli/SKILL.md .claude/skills/using-argo-workflows-cli/references/{submission-and-monitoring,debugging-and-lifecycle,authoring,cron-workflows}.md && wc -l .claude/skills/using-argo-workflows-cli/SKILL.md && grep -nE 'references/[a-z-]+\.md' .claude/skills/using-argo-workflows-cli/SKILL.md && grep -RniE 'submit|get|logs|list|delete|retry|resubmit|stop|terminate|suspend|resume|watch|lint|cron|template' .claude/skills/using-argo-workflows-cli/references/ && grep -n 'using-argo-workflows-cli' README.md .claude/CLAUDE.md`
    - [ ] `triple-name-invariant`: dirname == frontmatter `name` == `command` minus `/`.
    - [ ] `frontmatter-schema`: only the five conventional keys, `---`-delimited, no `claude.tools` shape.
    - [ ] `reference-link-contract`: every `references/<file>.md` link in the body resolves to an existing file.
    - [ ] `body-size-budget`: `SKILL.md` body under ~500 lines / ~5000 tokens.
    - [ ] `coverage-contract`: all 15 command groups + DAG/Steps + retry/backoff + debugging escalation + cron lifecycle + resource mgmt + artifact config appear across `references/`.
    - [ ] `hard-stop-prereq`: availability check + surface-and-stop instruction present in body.
    - [ ] `description-trigger-contract`: `description` carries "Use when…" + concrete argo trigger phrases.
    - [ ] `README.md` skills table/tree and `.claude/CLAUDE.md` "Available skills" both contain the new skill, name matching the directory exactly.

---

## Rollback Notes

- No DB migrations, config changes, or destructive ops in this slice — all steps
  create or append Markdown content under version control.
- Steps 3–4 (new directories) and steps 5–11 (new files): rollback = delete the
  `.claude/skills/using-argo-workflows-cli/` directory tree.
- Steps 12–13 (catalog edits to `README.md` / `.claude/CLAUDE.md`): rollback = revert
  the added skill row/tree entry and the "Available skills" list line; these are the
  only edits to existing files and are independently reversible.
