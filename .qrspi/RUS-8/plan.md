# Implementation Plan — Create a new agent skill using-argocd-cli

**Structure basis:** structure.md @ 2026-05-27T00:00:00Z
**Generated:** 2026-05-27T13:00:00Z
**Status:** draft
**Total steps:** 8

## Slice 1: Create the using-argocd-cli skill

### Setup

1. ✨ Create `.claude/skills/using-argocd-cli/` directory — top-level skill directory following the agentskills.io pattern and the existing `qrspi-work/references/` structure from `structure.md` Contract types.

### SKILL.md body via skill-creator

2. ✨ Create `.claude/skills/using-argocd-cli/SKILL.md` — Use the `skill-creator` skill to generate the SKILL.md body. The skill-creator skill handles the eval loop and line-count/token gate. Provide it with these inputs:
   - Frontmatter: `name: using-argocd-cli`, `description` encoding full lifecycle coverage, `command: argocd`, `argument-hint: <app-name or subcommand>`, `allowed-tools: Read, Write, Edit, Bash, Glob, Grep` (from `structure.md` Contract type `SkillFrontmatter`)
   - Body sections to cover: Activation (any bare `argocd` CLI reference), Role (Argo CD operations assistant), Workflow (diagnose -> select -> run -> verify), Quick Reference (common commands), Application Lifecycle (create, sync, monitor, rollback, delete), Auth (two-mode: CI/CD tokenless via `ARGOCD_AUTH_TOKEN` + interactive via `argocd login`), Opinionated Defaults (manual sync for prod, declarative manifests, git-revert-over-rollback, ApplicationSets-at-scale, deny-all-RBAC), Safety (RED WARNING for `--force`, dry-run-first policy)
   - Constraint: SKILL.md body must stay under 500 lines total (including frontmatter). The design's Risk Register flags this as medium-likelihood, high-impact — use skill-creator's eval loop to verify.

### Reference files

3. ✨ Create `.claude/skills/using-argocd-cli/references/cli-output.md` — Maps each major subcommand group (`app`, `repo`, `cluster`, `account`, `project`, `secret`, `context`) to its supported output flags (`--json`, `--yaml`, `--wide`, `--tree`) and describes how `PrintResource()` renders them. Consumed by the Quick Reference section of SKILL.md.

4. ✨ Create `.claude/skills/using-argocd-cli/references/sync-model.md` — Documents sync waves, resource hooks, sync phases, and sync strategies (manual vs auto, self-heal, prune) with version caveats. Consumed by the sync section of SKILL.md for agent-aware sync behavior.

5. ✨ Create `.claude/skills/using-argocd-cli/references/auth-rbac.md` — Covers authentication flows (`ARGOCD_AUTH_TOKEN` env var vs `ARGOCD_OPTS` vs `argocd login`), context management (`argocd context`), project-scoped role tokens, and RBAC escalation path (flags -> opts -> context -> project config). Consumed by the auth section of SKILL.md.

6. ✨ Create `.claude/skills/using-argocd-cli/references/troubleshooting.md` — Provides diagnostic commands (`argocd version`, `argocd app get`, `argocd app diff`), error patterns (optimistic lock failures, TLS/self-signed cert issues, SSO redirect behavior), and retry guidance (10-attempt optimistic locking). Consumed by the safety section of SKILL.md.

### Register the skill

7. ⚠️ Modify `.claude/CLAUDE.md` — Add `using-argocd-cli` to the available skills list, after the existing QRSPI skills.
   - **Current:** Available skills list ends with `/qrspi-pr`
   - **After:** Available skills list has a new entry appended after the QRSPI skills: `- using-argocd-cli — Argo CD CLI operations assistant. Covers the full lifecycle: create, sync, monitor, rollback, delete. Activates on any reference to the argocd CLI. Supports CI/CD tokenless and interactive login modes.`

### Verification

8. **Run verification checks:**
   - `wc -l .claude/skills/using-argocd-cli/SKILL.md` — body line count must be under 500
   - `head -7 .claude/skills/using-argocd-cli/SKILL.md` — frontmatter must parse as valid YAML with all 5 required fields (name, description, command, argument-hint, allowed-tools)
   - `ls .claude/skills/using-argocd-cli/references/` — must list all 4 reference files (cli-output.md, sync-model.md, auth-rbac.md, troubleshooting.md), each non-empty
   - `grep -c "using-argocd-cli" .claude/CLAUDE.md` — must appear in the available skills list
   - `grep -c "argocd" .claude/skills/using-argocd-cli/SKILL.md` — must contain Argo CD content (not empty)

### Verify Slice 1

9. **Checkpoint:** Run the verification commands above from the worktree root.
   - [ ] SKILL.md frontmatter is valid YAML with all 5 required fields
   - [ ] SKILL.md body is under 500 lines (count non-frontmatter, non-blank lines)
   - [ ] `references/` directory contains all 4 reference files, each non-empty
   - [ ] `.claude/CLAUDE.md` lists `using-argocd-cli` in the available skills section
   - [ ] All file paths resolve from worktree root (no relative references in frontmatter)

---

## Rollback Notes

- Step 1: Delete the `.claude/skills/using-argocd-cli/` directory entirely: `rm -rf .claude/skills/using-argocd-cli/`
- Step 2: Remove `SKILL.md`: `rm .claude/skills/using-argocd-cli/SKILL.md`
- Steps 3-6: Remove reference files: `rm .claude/skills/using-argocd-cli/references/cli-output.md .claude/skills/using-argocd-cli/references/sync-model.md .claude/skills/using-argocd-cli/references/auth-rbac.md .claude/skills/using-argocd-cli/references/troubleshooting.md` then `rmdir .claude/skills/using-argocd-cli/references/ 2>/dev/null`
- Step 7: Revert `.claude/CLAUDE.md` by removing the `using-argocd-cli` line added to the available skills list. If the file was only changed in this step, `git checkout .claude/CLAUDE.md` restores it; otherwise manually remove the inserted line.
