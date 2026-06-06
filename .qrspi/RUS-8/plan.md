# Implementation Plan — Create a new agent skill for the argocd CLI

**Structure basis:** structure.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total steps:** 9

## Slice 1: Author the `using-argocd-cli` skill (SKILL.md + six references)

All files are new; no existing file is modified (structure.md §Modified Types: None). No
DB migration, config change, or destructive op — see Rollback Notes. Author the six
`references/*.md` first so the body's pointers resolve to files that already exist, then
author `SKILL.md`, then validate.

### Setup

1. ✨ Create `.claude/skills/using-argocd-cli/references/authentication.md` — first `references/` file; satisfies `ReferenceTitleContract` (self-titled H1 `# Authentication & Context`, no frontmatter). Body content (design §Delta): token vs password auth, `ARGOCD_SERVER` / `ARGOCD_AUTH_TOKEN` / `ARGOCD_OPTS`, `--grpc-web`, `--core`, project-scoped role tokens, interactive `argocd login` / `argocd context`; explicitly contrast interactive-developer vs CI/CD-automation auth. Encode the **token auth over password** opinionated default as a `**bold**` rule (`OpinionatedDefaultsContract`).

### Core Logic

2. ✨ Create `.claude/skills/using-argocd-cli/references/sync-strategies.md` — self-titled H1 `# Sync Strategies` (`ReferenceTitleContract`). Content: manual vs automated sync, `--self-heal` / `--auto-prune`, `--dry-run`, sync waves, hooks, `--force` / `--prune` cautions, retry policies, `--apply-out-of-sync-only`. Encode the **manual sync for prod** opinionated default as a `**bold**` rule, consistent with SKILL.md (`OpinionatedDefaultsContract`).

3. ✨ Create `.claude/skills/using-argocd-cli/references/rollback-procedures.md` — self-titled H1 `# Rollback Procedures` (`ReferenceTitleContract`). Content: `argocd app rollback` emergency use + its auto-disable of automated sync, `argocd app history`, follow-up Git revert. Encode the **Git revert over `app rollback`** opinionated default as a `**bold**` rule, consistent with SKILL.md (`OpinionatedDefaultsContract`).

4. ✨ Create `.claude/skills/using-argocd-cli/references/applicationset-generators.md` — self-titled H1 `# ApplicationSet Generators` (`ReferenceTitleContract`). Content: Git / Cluster / Matrix / List generators, app-of-apps → ApplicationSet transition thresholds, `preserveResourcesOnDeletion`.

5. ✨ Create `.claude/skills/using-argocd-cli/references/rbac-configuration.md` — self-titled H1 `# RBAC & Projects` (`ReferenceTitleContract`). Content: AppProjects, project-scoped role tokens, `argocd admin settings rbac validate` / `rbac can`, SSO group mapping, deny-all default.

6. ✨ Create `.claude/skills/using-argocd-cli/references/troubleshooting.md` — self-titled H1 `# Troubleshooting` (`ReferenceTitleContract`). Content: flowchart prose `app get` → `app resources` → events/logs → `terminate-op`, manifest live-vs-git compare, hard refresh, repo connectivity.

7. ✨ Create `.claude/skills/using-argocd-cli/SKILL.md` — the triggerable wrapper. Five-key frontmatter in exact order `name`, `description`, `command`, `argument-hint`, `allowed-tools` (`FrontmatterContract`): `name: using-argocd-cli` (== directory), `command: /using-argocd-cli`, `description` quoted (contains colons) with an explicit "Use when…/Trigger on…" clause naming argocd/GitOps phrases, `allowed-tools: Bash`. Body: H1 `# Using the Argo CD CLI`; topical `##` sections in escalation order (`EscalationOrderContract`): Authentication & Context → Application Lifecycle (create/get/diff/sync/wait/delete) → Sync Strategies → Health Monitoring → Rollbacks → App-of-Apps → ApplicationSets → RBAC & Projects → Multi-Cluster → Troubleshooting. Each deep section ends with a skill-root-relative pointer `references/<file>.md` (no leading `./`, no absolute path) at its decision point (`ReferenceCitationContract`). Bash-fenced `argocd` examples throughout; the three opinionated defaults as `**bold**` rules matching the reference files (`OpinionatedDefaultsContract`). Target ~250–350 lines, < 500 (discipline only — no checker).

### Tests

No automated test exists for SKILL.md validity or triggering (design §Current State: "no SKILL.md frontmatter validator … no automated SKILL.md validity or trigger test"). Verification is the manual checkpoint below plus the external `skill-creator` eval loop.

8. ✨ Run `skill-creator` authoring/validation pass over `.claude/skills/using-argocd-cli/` (AC #2; design OQ1). This is a manual process step through the external skill — not an in-repo command. Treat its eval loop as the closing authoring gate.
   - **Expected:** skill-creator reports the skill as valid/discoverable; address any frontmatter or description findings it surfaces.

### Verify Slice 1

9. **Checkpoint:** `python3 - <<'PY'
import os,glob,re
root=".claude/skills/using-argocd-cli"
sk=os.path.join(root,"SKILL.md")
refs=sorted(glob.glob(os.path.join(root,"references","*.md")))
body=open(sk).read()
print("SKILL.md exists:",os.path.exists(sk))
print("ref count:",len(refs))
print("body lines:",body.count(chr(10))+1)
for p in re.findall(r"references/[\w-]+\.md",body):
    print("pointer",p,"resolves:",os.path.exists(os.path.join(root,p)))
print("abs/./ pointer present:",bool(re.search(r"(\./references/|/.*/references/)",body)))
for r in refs:
    first=open(r).readline().strip()
    print(os.path.basename(r),"H1 ok:",first.startswith("# "))
PY`
   - [ ] `SKILL.md` exists with five-key frontmatter in order; `name`/`command`/directory all `using-argocd-cli`; `description` quoted with a "Use when…/Trigger on…" clause naming argocd/GitOps phrases; `allowed-tools: Bash` (visual diff against `qrspi-work` frontmatter) — `FrontmatterContract`.
   - [ ] All six `references/*.md` exist; each opens with a self-titled H1 (`ReferenceTitleContract`); every `references/` pointer in the body resolves to a real file, skill-root-relative, no `./` and no absolute path (`ReferenceCitationContract`).
   - [ ] Body covers the full lifecycle (create, sync, monitor, rollback, delete) with bash-fenced `argocd` examples and presents the three opinionated defaults (manual sync for prod, Git revert over rollback, token auth over password) as `**bold**` rules consistent with their reference files (`OpinionatedDefaultsContract`).
   - [ ] Body `##` sections appear in escalation order (`EscalationOrderContract`).
   - [ ] Manual length check: `SKILL.md` body < 500 lines (discipline gate — no checker exists).
   - [ ] `skill-creator` validation pass complete (AC #2) and manual end-to-end check that `/using-argocd-cli` is discovered and triggers.

---

## Rollback Notes

- Steps 1–7: all create-only. No existing file is modified (structure.md §Modified Types: None; design §Delta: "No existing file is modified"). To roll back, delete the new directory: `rm -rf .claude/skills/using-argocd-cli/`. No manifest/index/registry edit to revert (skill discovery is directory-convention only), no DB migration, no config change.
- Step 8: `skill-creator` is an external authoring pass; if its output diverges from repo conventions, discard its changes and retain the hand-authored convention-conforming files (design Risk row 2). No persisted state to undo.
