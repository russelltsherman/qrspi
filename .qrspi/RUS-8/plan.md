# Implementation Plan — Create a new agent skill called using argocd cli

**Structure basis:** structure.md @ 2026-05-25
**Generated:** 2026-05-25
**Status:** draft
**Total steps:** 23

## Slice 1: Author complete skill (SKILL.md + all references + eval file)

### Setup

1. ✨ Create directory `.claude/skills/using-argocd-cli/references/` — Skill root and reference subdirectory per structure.md file list and Contract: `references/*.md`

### Core Logic — SKILL.md

2. ✨ Create `.claude/skills/using-argocd-cli/SKILL.md` — Main skill definition per structure.md contracts
   - YAML frontmatter with `name: using-argocd-cli`, `description` (trigger string, max 1024 chars), `command: using-argocd-cli`, `argument-hint` per Contract: `SKILL.md frontmatter`
   - Body sections in order:
     - Prerequisites and authentication overview
     - Core application lifecycle (create → get → diff → sync → monitor → rollback → delete) per AC5
     - Opinionated defaults with reasoning (manual sync for prod, Git revert over rollback, token auth, dry-run before sync) per AC6 and Decision 4 hybrid style
     - Interactive workflow (default context) per AC7
     - CI/CD section as delta from interactive default per AC7 and Decision 4
     - Escalation path: single-app → app-of-apps → ApplicationSets → multi-cluster per AC8
     - Conditional Read pointers to each of the six reference files with explicit trigger conditions per Contract: `SKILL.md body → references/ pointer contract`
   - Target 350-450 lines; must stay under 500 per Contract: `SKILL.md body`

### Core Logic — Reference Files

3. ✨ Create `.claude/skills/using-argocd-cli/references/authentication.md` — per structure.md file list
   - Purpose header
   - Token-based auth, login flow, context management, core mode for headless environments, grpc-web for restricted networks, project-scoped role tokens, initial admin password change
   - Must be self-contained with purpose header per Contract: `references/*.md`; under 300 lines or include TOC

4. ✨ Create `.claude/skills/using-argocd-cli/references/sync-strategies.md` — per structure.md file list
   - Purpose header
   - Manual vs automated sync, self-heal, auto-prune, dry-run workflow, sync waves and ordering, resource hooks (PreSync/Sync/PostSync/SyncFail), force sync and prune safety, apply-out-of-sync-only optimization
   - Must be self-contained with purpose header per Contract: `references/*.md`; under 300 lines or include TOC

5. ✨ Create `.claude/skills/using-argocd-cli/references/rollback-procedures.md` — per structure.md file list
   - Purpose header
   - Git revert as primary rollback path with reasoning, emergency rollback with `argocd app rollback`, post-rollback Git reconciliation, deployment history inspection via `argocd app history`
   - Must be self-contained with purpose header per Contract: `references/*.md`; under 300 lines or include TOC

6. ✨ Create `.claude/skills/using-argocd-cli/references/applicationsets.md` — per structure.md file list
   - Purpose header
   - Generator types (Git, Cluster, Matrix, List), preserveResourcesOnDeletion for production safety, transition criteria from app-of-apps to ApplicationSets (>20 apps or >3 clusters), CLI commands for listing and managing ApplicationSets
   - Must be self-contained with purpose header per Contract: `references/*.md`; under 300 lines or include TOC

7. ✨ Create `.claude/skills/using-argocd-cli/references/rbac-configuration.md` — per structure.md file list
   - Purpose header
   - AppProject isolation, project-scoped roles with JWT tokens, deny-all default policy, production sync permission restrictions, role binding examples
   - Must be self-contained with purpose header per Contract: `references/*.md`; under 300 lines or include TOC

8. ✨ Create `.claude/skills/using-argocd-cli/references/troubleshooting.md` — per structure.md file list
   - Purpose header
   - Diagnostic flowchart starting from `argocd app get`, branching by symptom to dry-run, terminate-op, resource inspection, log streaming, manifest comparison, hard-refresh
   - Must be self-contained with purpose header per Contract: `references/*.md`; under 300 lines or include TOC

### Core Logic — Eval File

9. ✨ Create `evals/argocd-evals.json` — Trigger accuracy eval set per structure.md file list
   - Format: `{ "skill_name": "using-argocd-cli", "evals": [{ "id", "prompt", "expected_output", "files", "assertions" }] }` per Contract: `evals/argocd-evals.json`
   - At least 5 should-trigger queries covering ArgoCD-specific operations (sync, rollback, app creation, health check, diff)
   - At least 3 should-not-trigger queries covering kubectl, helm, and flux to test trigger discrimination
   - Queries must be realistic user prompts, not synthetic/contrived

### Validation

10. Run: `wc -l .claude/skills/using-argocd-cli/SKILL.md`
    - **Expected:** line count < 500

11. Run: `head -10 .claude/skills/using-argocd-cli/SKILL.md | grep -c 'name:\|description:\|command:\|argument-hint:'`
    - **Expected:** 4 (all four frontmatter fields present)

12. Run: `grep -c 'references/' .claude/skills/using-argocd-cli/SKILL.md`
    - **Expected:** >= 6 (at least one pointer per reference file)

13. Run: `for f in .claude/skills/using-argocd-cli/references/*.md; do echo "$f: $(wc -l < "$f") lines"; done`
    - **Expected:** each file under 300 lines

14. Run: `for f in .claude/skills/using-argocd-cli/references/*.md; do head -3 "$f"; echo "---"; done`
    - **Expected:** each file starts with a purpose header (H1 or H2)

15. Run: `python3 -m json.tool evals/argocd-evals.json > /dev/null`
    - **Expected:** valid JSON, exit code 0

16. Run: `python3 -c "import json; d=json.load(open('evals/argocd-evals.json')); assert d['skill_name']=='using-argocd-cli'; assert len(d['evals'])>=8; print(f'OK: {len(d[\"evals\"])} evals')"`
    - **Expected:** OK with at least 8 evals total

17. Run: `python3 -c "import json; d=json.load(open('evals/argocd-evals.json')); fields=['id','prompt','expected_output','assertions']; missing=[e['id'] for e in d['evals'] if not all(f in e for f in fields)]; assert not missing, f'Missing fields in: {missing}'; print('All evals have required fields')"`
    - **Expected:** All evals have required fields

18. Run: `grep -c 'manual sync\|Git revert\|token.*auth\|dry.run' .claude/skills/using-argocd-cli/SKILL.md`
    - **Expected:** >= 4 (opinionated defaults are present with reasoning)

19. Run: `grep -ci 'CI/CD\|ci-cd\|pipeline\|automation' .claude/skills/using-argocd-cli/SKILL.md`
    - **Expected:** >= 1 (CI/CD section exists)

20. Run: `grep -c 'ApplicationSet\|app-of-apps\|multi-cluster' .claude/skills/using-argocd-cli/SKILL.md`
    - **Expected:** >= 1 (escalation path present)

21. Run: `ls .claude/skills/using-argocd-cli/references/ | wc -l`
    - **Expected:** 6 (exactly six reference files)

### Verify Slice 1

22. **Checkpoint:** `bash -c 'set -e; echo "=== Frontmatter ===" && head -10 .claude/skills/using-argocd-cli/SKILL.md | grep -q "name: using-argocd-cli" && echo "OK: name field" && head -10 .claude/skills/using-argocd-cli/SKILL.md | grep -q "description:" && echo "OK: description field" && head -10 .claude/skills/using-argocd-cli/SKILL.md | grep -q "command:" && echo "OK: command field" && head -10 .claude/skills/using-argocd-cli/SKILL.md | grep -q "argument-hint:" && echo "OK: argument-hint field" && echo "=== Line count ===" && lines=$(wc -l < .claude/skills/using-argocd-cli/SKILL.md) && echo "SKILL.md: $lines lines" && [ "$lines" -lt 500 ] && echo "OK: under 500 lines" && echo "=== References ===" && [ $(ls .claude/skills/using-argocd-cli/references/*.md | wc -l) -eq 6 ] && echo "OK: 6 reference files" && echo "=== Eval ===" && python3 -m json.tool evals/argocd-evals.json > /dev/null && echo "OK: valid JSON" && echo "=== ALL CHECKS PASSED ==="'`
    - [ ] SKILL.md has valid frontmatter with `name`, `description`, `command`, and `argument-hint` fields
    - [ ] SKILL.md body is under 500 lines
    - [ ] SKILL.md body contains conditional pointers to each of the six reference files with clear trigger conditions
    - [ ] Each reference file has a purpose header and stays under 300 lines
    - [ ] `evals/argocd-evals.json` is valid JSON matching the skill-creator eval schema
    - [ ] Eval set includes at least 5 should-trigger and 3 should-not-trigger queries
    - [ ] Should-not-trigger queries cover kubectl, helm, and flux to test trigger discrimination
    - [ ] Opinionated defaults are stated with reasoning (not bare rules)
    - [ ] CI/CD section describes deltas from the interactive default (not a parallel workflow)
    - [ ] Escalation path flows: single-app → app-of-apps → ApplicationSets → multi-cluster, with advanced topics deferred to references

23. **Checkpoint:** Invoke skill-creator eval loop to validate trigger accuracy and overall skill quality per structure.md verification item 11 and AC2

---

## Rollback Notes

- No database migrations, config changes, or destructive operations in this slice. All files are net-new. Rollback is: delete `.claude/skills/using-argocd-cli/` directory and `evals/argocd-evals.json`.
