# Structure Outline — Create a new agent skill using-argocd-cli

**Design basis:** design.md @ 2026-05-27T00:00:00Z
**Generated:** 2026-05-27T00:00:00Z
**Status:** draft

## New Types

- `SkillFrontmatter { name: string, description: string, command: string, argument-hint: string, allowed-tools: string[] }` — YAML frontmatter block at top of SKILL.md defining skill identity and tool access
- `ReferenceFile { path: string, topic: string, audience: "quick-reference" | "deep-dive" }` — Markdown file in references/ directory providing topic-specific detail loaded on demand

## Contracts

- `SKILL.md` activates on invocation of `argocd` CLI operations; body (~200 lines) covers: activation trigger, role, workflow, quick reference, lifecycle sections (create/sync/monitor/rollback/delete), two-mode auth guidance (CI/CD token vs interactive login), opinionated defaults, and safety rules
- `references/cli-output.md` maps each major subcommand group to its supported output flags (`--json`, `--yaml`, `--wide`, `--tree`) and describes how `PrintResource()` renders them — consumed by the quick-reference section of SKILL.md
- `references/sync-model.md` documents sync waves, resource hooks, and sync phases — consumed by the sync section of SKILL.md for agent-aware sync behavior
- `references/auth-rbac.md` covers authentication flows (token env var vs `argocd login`), context management, project-scoped role tokens, and RBAC escalation path — consumed by the auth section of SKILL.md
- `references/troubleshooting.md` provides diagnostic commands and common error patterns — consumed by the safety section of SKILL.md

## Slice 1: Create the using-argocd-cli skill

**Goal:** Produce the complete `using-argocd-cli` skill directory with SKILL.md and all reference files, plus register it in `.claude/CLAUDE.md` — a testable, reviewable skill artifact that meets all acceptance criteria from the design.

**Files touched:**

- ✨ `.claude/skills/using-argocd-cli/SKILL.md` — Main skill file (~200 lines, max 500). Frontmatter: name=using-argocd-cli, description encodes full lifecycle coverage, argument-hint=<app-name or subcommand>, allowed-tools=Read, Write, Edit, Bash, Glob, Grep. Body sections: Activation, Role, Workflow, Quick Reference, Application Lifecycle (create, sync, monitor, rollback, delete), Auth (two-mode: CI/CD tokenless + interactive login), Opinionated Defaults, Safety.
- ✨ `.claude/skills/using-argocd-cli/references/cli-output.md` — Output format reference for all subcommand groups (`app`, `repo`, `cluster`, `account`, `project`, `secret`, `context`), mapping each to supported flags and noting `PrintResource()` rendering
- ✨ `.claude/skills/using-argocd-cli/references/sync-model.md` — Sync waves, resource hooks, phases, and sync strategies (manual vs auto, self-heal, prune) with version caveats
- ✨ `.claude/skills/using-argocd-cli/references/auth-rbac.md` — Authentication (ARGOCD_AUTH_TOKEN, ARGOCD_OPTS, `argocd login`, `argocd context`), project-scoped role tokens, RBAC escalation path (flags -> opts -> context -> project config)
- ✨ `.claude/skills/using-argocd-cli/references/troubleshooting.md` — Diagnostic commands (`argocd version`, `argocd app get`, `argocd app diff`), error patterns (optimistic lock failures, TLS/self-signed cert issues, SSO redirect behavior), retry guidance for 10-attempt optimistic locking
- ✨ `.claude/skills/using-argocd-cli/references/` directory — created to hold reference files
- ⚠️ `.claude/CLAUDE.md` — Add `using-argocd-cli` to the available skills list (after existing QRSPI skills)
**Verification:**
- [ ] SKILL.md frontmatter parses as valid YAML with all 5 required fields (name, description, command, argument-hint, allowed-tools)
- [ ] SKILL.md body is under 500 lines (count non-frontmatter, non-blank lines)
- [ ] `references/` directory contains all 4 reference files, each non-empty
- [ ] `.claude/CLAUDE.md` lists `using-argocd-cli` in the available skills section
- [ ] All file paths resolve from worktree root (no relative references in frontmatter)
**Context cost:** M
**Depends on:** none

## Unverified Assumptions

- The design's recommended approach (Option B for all decisions) is the final approved direction — no alternative decisions are pending that would change file boundaries or content scope.
- The `allowed-tools` list (Read, Write, Edit, Bash, Glob, Grep) does not need any MCP tools — the skill operates entirely through the `argocd` CLI via Bash.
- The skill should activate on bare `argocd` CLI references (no `/slash` command prefix), since the design's `command` field is left open and the pattern-matching criteria list "argocd" as a trigger keyword.
- The open questions (OQ1-OQ5) from design.md are resolved at implementation time — the structure assumes they will be answered during implementation of Slice 1 without requiring additional slices.
- The `~/.config/argocd/argocd.yaml` context file format is a known-good reference point for auth guidance — the skill assumes the local config path is stable across Argo CD versions.
- All 4 reference files fit within a reasonable size that does not cause SKILL.md line-count overflow when cross-referenced (not copied inline).
