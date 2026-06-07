# Implementation Plan — Create a new agent skill: writing GitLab pipelines

**Structure basis:** structure.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total steps:** 22

> Skill-authoring (Markdown) deliverable — no executable code. Verification commands
> are shell checks over the Markdown files (existence, YAML frontmatter parse, link
> resolution, line/token budget). The flat `allowed-tools` shape is copied verbatim
> from `.claude/skills/qrspi-ticket/SKILL.md` (structure.md Contracts; design Risk
> "Wrong frontmatter shape"). Author-facing Open Questions (OQ1 command field, OQ3
> allowed-tools set, OQ4 GitLab target version) are noted at decision points.

## Slice 1: SKILL.md skeleton — frontmatter, body index, opinionated body sections

### Setup

1. ✨ Create `.claude/skills/writing-gitlab-pipelines/references/rules.md` — stub: H1 `# GitLab Pipeline Rules` + one-line scope sentence (placeholder for Slice 2 depth). Satisfies the Reference-link contract so the body link resolves before content is written.
2. ✨ Create `.claude/skills/writing-gitlab-pipelines/references/includes-extends.md` — stub: H1 `# Includes & Extends (DRY)` + one-line scope sentence.
3. ✨ Create `.claude/skills/writing-gitlab-pipelines/references/cache-artifacts.md` — stub: H1 `# Caching & Artifacts` + one-line scope sentence.
4. ✨ Create `.claude/skills/writing-gitlab-pipelines/references/environments.md` — stub: H1 `# Environments, Deployments & Review Apps` + one-line scope sentence.
5. ✨ Create `.claude/skills/writing-gitlab-pipelines/references/security.md` — stub: H1 `# Security Scanning` + one-line scope sentence.
6. ✨ Create `.claude/skills/writing-gitlab-pipelines/references/architecture.md` — stub: H1 `# Pipeline Architecture (Worked Examples)` + one-line scope sentence.

### Core Logic

7. ✨ Create `.claude/skills/writing-gitlab-pipelines/SKILL.md` — write YAML frontmatter only, conforming to `SkillFrontmatter { name, description, allowed-tools (flat, comma-separated), command?, argument-hint? }`. Copy the `qrspi-ticket/SKILL.md` frontmatter shape verbatim. Set `name: writing-gitlab-pipelines` (MUST equal directory name). Set a trigger-oriented `description` ("Use when authoring/editing `.gitlab-ci.yml`… / Trigger on…"). Set `allowed-tools: Read, Write, Edit, Bash` (OQ3 default — narrow set; flag for author). Omit `command`/`argument-hint` per Decision 2 default auto-trigger (OQ1 — flag for author).
8. ⚠️ Modify `.claude/skills/writing-gitlab-pipelines/SKILL.md` — append body Purpose & when-to-use section.
   - **Current:** frontmatter only
   - **After:** frontmatter + `## Purpose & when to use` section (what the skill covers, when an agent should follow it)
9. ⚠️ Modify `.claude/skills/writing-gitlab-pipelines/SKILL.md` — append the inline opinionated-imperatives section.
   - **Current:** frontmatter + Purpose
   - **After:** + `## Opinionated defaults` section stating imperatives: prefer `rules:` over `only/except`; pin image tags/digests (no `:latest`); always set explicit `expire_in` on artifacts (design §Desired End State).
10. ⚠️ Modify `.claude/skills/writing-gitlab-pipelines/SKILL.md` — append the Performance & optimization section.
    - **Current:** + Opinionated defaults
    - **After:** + `## Performance & optimization` section: sub-10-minute target, DAG/`needs`, `interruptible`, `resource_group`, `retry`, `timeout` (design §Desired End State).
11. ⚠️ Modify `.claude/skills/writing-gitlab-pipelines/SKILL.md` — append the Anti-patterns → alternatives section.
    - **Current:** + Performance & optimization
    - **After:** + `## Anti-patterns → alternatives` section pairing each anti-pattern with its preferred alternative (design §Desired End State).
12. ⚠️ Modify `.claude/skills/writing-gitlab-pipelines/SKILL.md` — append the "See references/" index linking all six deep-dive files by relative path `references/<file>.md` (Reference-link contract). Links: rules.md, includes-extends.md, cache-artifacts.md, environments.md, security.md, architecture.md.
    - **Current:** + Anti-patterns
    - **After:** + `## See references/` index with six resolving relative links

### Verify Slice 1

13. **Checkpoint:** `cd .claude/skills/writing-gitlab-pipelines && python3 -c "import yaml,sys; t=open('SKILL.md').read(); fm=t.split('---')[1]; d=yaml.safe_load(fm); assert d['name']=='writing-gitlab-pipelines'; assert 'claude' not in d; print('OK', list(d))" && for f in $(grep -oE 'references/[a-z-]+\.md' SKILL.md | sort -u); do test -f "$f" && echo "resolves: $f" || { echo "BROKEN: $f"; exit 1; }; done && wc -l SKILL.md`
    - [ ] Frontmatter parses as YAML; `name` equals directory name `writing-gitlab-pipelines`; `allowed-tools` is flat (no nested `claude.tools` key).
    - [ ] `description` is trigger-oriented ("Use when…/Trigger on…").
    - [ ] Every `references/<file>.md` link in the body resolves to an existing file.
    - [ ] `wc -l SKILL.md` body ≤ 500 lines and estimated ≤ ~5000 tokens.
    - [ ] Body contains the four inline sections: Purpose & when-to-use, Opinionated defaults, Performance & optimization, Anti-patterns → alternatives.

---

## Slice 2: Reference content — fill the six deep-dive docs

### Core Logic

14. ⚠️ Modify `.claude/skills/writing-gitlab-pipelines/references/rules.md` — replace stub with full content: `rules:` syntax, `workflow:rules`, `rules:changes`, `$CI_PIPELINE_SOURCE`/`$CI_COMMIT_BRANCH`, explicit terminal `when`. Keep standalone H1.
15. ⚠️ Modify `.claude/skills/writing-gitlab-pipelines/references/includes-extends.md` — replace stub with full content: `include` (local/file/remote/component), `extends` deep-merge vs YAML anchors, multi-level extends, `!reference`, CI/CD Catalog (note GA 17.0 version gate — design Risk "GitLab feature drift").
16. ⚠️ Modify `.claude/skills/writing-gitlab-pipelines/references/cache-artifacts.md` — replace stub with full content: cache keys/`files`/`policy`/`$CI_COMMIT_REF_SLUG`; artifacts `expire_in`, `reports`, `when: on_failure`.
17. ⚠️ Modify `.claude/skills/writing-gitlab-pipelines/references/environments.md` — replace stub with full content: static/dynamic environments, `on_stop`, `auto_stop_in`, review-app per-MR pattern, scoped variables, deployment gates.
18. ⚠️ Modify `.claude/skills/writing-gitlab-pipelines/references/security.md` — replace stub with full content: SAST/dependency/container/secret-detection templates, DAST vs review apps, `artifacts:reports:*`, scan execution policies.
19. ⚠️ Modify `.claude/skills/writing-gitlab-pipelines/references/architecture.md` — replace stub with full content: worked examples — minimal build/test/deploy, mature lint/build/test/security/deploy/cleanup, parent-child + multi-project triggers.

### Verify Slice 2

20. **Checkpoint:** `cd .claude/skills/writing-gitlab-pipelines/references && for f in rules.md includes-extends.md cache-artifacts.md environments.md security.md architecture.md; do head -1 "$f" | grep -q '^# ' && test "$(wc -l < "$f")" -gt 5 && echo "OK (non-stub): $f" || { echo "STUB/NO-H1: $f"; exit 1; }; done`
    - [ ] Each reference is a standalone H1 Markdown doc.
    - [ ] No file remains a stub (each substantially exceeds the H1+scope-line stub).
    - [ ] Every ticket concern from design §Desired End State maps to a body section and/or a reference file with non-stub content (manual cross-check).
    - [ ] Version-gated features (CI/CD Catalog / components GA 17.0+) carry an inline version note.
21. **Checkpoint (manual):** Re-run the Slice 1 link + budget check after content fill to confirm no links broke and SKILL.md body still ≤ 500 lines: `cd .claude/skills/writing-gitlab-pipelines && for f in $(grep -oE 'references/[a-z-]+\.md' SKILL.md | sort -u); do test -f "$f" || { echo "BROKEN: $f"; exit 1; }; done && wc -l SKILL.md`
    - [ ] All body links still resolve.
    - [ ] SKILL.md body still within budget.
22. **Checkpoint (manual):** Cross-check the whole skill against the ticket acceptance criteria — no eval/validation harness applies to skill authoring (structure.md Verification; design Risk "No eval/validation harness"). Confirm OQ1 (`command` field), OQ3 (`allowed-tools` set), OQ4 (GitLab target version) were resolved by the author or are explicitly accepted as defaults.
    - [ ] All acceptance criteria covered by a body section or reference file.
    - [ ] Open Questions OQ1/OQ3/OQ4 resolved or accepted.

---

## Rollback Notes

- Steps 1–12 (Slice 1): net-new directory `.claude/skills/writing-gitlab-pipelines/`. No existing file is modified (structure.md Modified Types: none). Rollback = delete the entire directory `rm -rf .claude/skills/writing-gitlab-pipelines/`; nothing else in the repo references it.
- Steps 14–19 (Slice 2): edits replace stub content within the same new files. Rollback = `git checkout` the reference files (reverts to Slice 1 stubs) or delete the directory as above.
- No DB migrations, config changes, or destructive operations on existing code.
