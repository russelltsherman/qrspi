# Implementation Plan — Create a new agent skill for using the Claude CLI

**Structure basis:** structure.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft
**Total steps:** 26

> **Pre-slice gate (blocking — resolve before Slice 1).** Per structure.md and
> design.md Open Questions, the following must be resolved before any step below
> executes. They have no file mapping; they constrain content authored in every step.
>
> - **OQ3** — authoritative CLI source of truth (installed `claude --help` vs. a
>   specific published docs version). Fixes which flags/modes/behaviors are "real."
>   No CLI fact may be encoded until fixed.
> - **OQ1** — `skill-creator` reachability in the implementation session. If reachable,
>   the skill must be produced/validated through it; if unreachable, escalate rather
>   than silently hand-author.
> - **OQ4** — acceptance of the no-agent content-skill shape (no `.claude/agents/` file).
>   If rejected, the entire structure is invalid and this plan must be reworked.
> - **OQ5** — correct vs. echo unverified ticket specifics (10MB stdin cap, exact
>   permission-mode list). Depends on OQ3; constrains body and reference content.

## Slice 1: Verified SKILL.md (frontmatter + body) — the complete, self-sufficient skill

### Setup

1. ✨ Create `.claude/skills/using-claude-cli/SKILL.md` — file with only the YAML frontmatter block per the skill dialect `SkillFrontmatter { name, description, command, argument-hint, allowed-tools }` (ref: structure.md New Types).
   - `name: using-claude-cli`
   - `command: /using-claude-cli` (naming triple: directory == `name` == `command` minus `/`)
   - `description:` one-line trigger description for a Claude CLI reference skill
   - `argument-hint:` no-op placeholder or topic selector (ref: design.md Decision 2)
   - `allowed-tools: Read` (minimal; verified syntax `Bash(<cmd>:*)` / `mcp__<server>__<tool>` only if needed) (ref: structure.md, Q13)
2. ✨ Create `.claude/skills/using-claude-cli/references/cli-flags.md` — stub: H1 heading + one-line scope note ("advanced flags, output formats, cost/resource control"). Present so Slice 1 body links resolve.
3. ✨ Create `.claude/skills/using-claude-cli/references/subagents-and-teams.md` — stub: H1 heading + scope note ("built-in subagent types, custom agents, --agents JSON, agent teams, worktrees").
4. ✨ Create `.claude/skills/using-claude-cli/references/hooks.md` — stub: H1 heading + scope note ("hook events, matcher syntax, exit codes, examples").
5. ✨ Create `.claude/skills/using-claude-cli/references/permissions-and-mcp.md` — stub: H1 heading + scope note ("permission modes, deny→ask→allow order, settings hierarchy, rule syntax, MCP config").
6. ✨ Create `.claude/skills/using-claude-cli/references/cicd-patterns.md` — stub: H1 heading + scope note ("GitHub Actions / GitLab CI examples").

### Core Logic

7. ⚠️ Modify `.claude/skills/using-claude-cli/SKILL.md` — append body section: CLI modes (headless/bare mode and the three modes) — only OQ3-verified facts; no unverified flags.
8. ⚠️ Modify `.claude/skills/using-claude-cli/SKILL.md` — append body section: subagent spawning (common pattern only; defer detail to references/subagents-and-teams.md link).
9. ⚠️ Modify `.claude/skills/using-claude-cli/SKILL.md` — append body section: session management (resume/continue/persistence) — OQ3-verified facts only.
10. ⚠️ Modify `.claude/skills/using-claude-cli/SKILL.md` — append body section: permission best practices (defer modes/order detail to references/permissions-and-mcp.md link).
11. ⚠️ Modify `.claude/skills/using-claude-cli/SKILL.md` — append body section: short orchestration examples (cost control + composition; defer advanced flags to references/cli-flags.md link).
12. ⚠️ Modify `.claude/skills/using-claude-cli/SKILL.md` — append a "References" section that links to all five `references/*.md` files (satisfies references/ link contract; topic names must match Slice 1 stubs and Slice 2 content).

### Tests

13. Run: `python3 -c "import sys,yaml; t=open('.claude/skills/using-claude-cli/SKILL.md').read(); fm=t.split('---')[1]; d=yaml.safe_load(fm); req={'name','description','command','argument-hint','allowed-tools'}; assert req<=set(d), 'missing: '+str(req-set(d)); assert d['name']=='using-claude-cli' and d['command']=='/using-claude-cli', 'naming triple'; print('OK')"`
    - **Expected:** prints `OK` — frontmatter parses as valid YAML, carries all five keys, naming triple holds.
14. Run: `awk 'f{print} /^---$/{c++} c==2{f=1}' .claude/skills/using-claude-cli/SKILL.md | wc -l` and `wc -w` on the same body slice.
    - **Expected:** body < 500 lines and < ~5000 tokens (word count as proxy; confirm under budget).
15. Run: `grep -oE 'references/[a-z-]+\.md' .claude/skills/using-claude-cli/SKILL.md | sort -u | while read f; do test -f ".claude/skills/using-claude-cli/$f" || echo "MISSING $f"; done`
    - **Expected:** no `MISSING` output — every referenced file exists (link contract).

### Verify Slice 1

16. **Checkpoint:** run steps 13–15 together.
    - [ ] Frontmatter parses as valid YAML with all five required keys (step 13).
    - [ ] Naming triple holds: directory `using-claude-cli` == `name:` == `command:` minus `/` (step 13).
    - [ ] `allowed-tools` entries use verified syntax (bare names / `Bash(<cmd>:*)` / `mcp__<server>__<tool>`).
    - [ ] SKILL.md body < 500 lines and < 5000 tokens (step 14).
    - [ ] Every CLI flag/mode/behavior in the body exists in the OQ3-verified fact set; no unverified flags.
    - [ ] Every `references/*.md` link resolves to a present file (step 15).
    - [ ] If `skill-creator` reachable (OQ1), skill produced/validated via it; otherwise escalation recorded.

---

## Slice 2: Reference content — fill the five advanced-topic files

### Core Logic

17. ⚠️ Modify `.claude/skills/using-claude-cli/references/cli-flags.md` — replace stub with verified advanced flags, output formats, cost/resource control. Topic must match the body's link from Slice 1.
    - **Current:** H1 heading + one-line scope note (stub from step 2).
    - **After:** full verified content, OQ3-sourced; experimental items labeled; unverified ticket specifics handled per OQ5.
18. ⚠️ Modify `.claude/skills/using-claude-cli/references/subagents-and-teams.md` — replace stub with built-in subagent types, custom `.claude/agents/`, `--agents` JSON, agent teams (labeled experimental), worktrees.
    - **Current:** H1 heading + scope note (stub from step 3).
    - **After:** full verified content; agent teams explicitly flagged experimental.
19. ⚠️ Modify `.claude/skills/using-claude-cli/references/hooks.md` — replace stub with hook events, matcher syntax, exit codes, examples.
    - **Current:** H1 heading + scope note (stub from step 4).
    - **After:** full verified content, OQ3-sourced.
20. ⚠️ Modify `.claude/skills/using-claude-cli/references/permissions-and-mcp.md` — replace stub with permission modes, deny→ask→allow order, settings hierarchy, rule syntax, MCP config.
    - **Current:** H1 heading + scope note (stub from step 5).
    - **After:** full verified content; tool-rule/MCP examples use `Bash(<cmd>:*)` / `mcp__<server>__<tool>`; permission-mode list handled per OQ5.
21. ⚠️ Modify `.claude/skills/using-claude-cli/references/cicd-patterns.md` — replace stub with brief GitHub Actions / GitLab CI examples.
    - **Current:** H1 heading + scope note (stub from step 6).
    - **After:** verified CI/CD examples, OQ3-sourced.

### Tests

22. Run: `for f in cli-flags subagents-and-teams hooks permissions-and-mcp cicd-patterns; do lines=$(wc -l < ".claude/skills/using-claude-cli/references/$f.md"); test "$lines" -gt 2 || echo "STUB $f"; done`
    - **Expected:** no `STUB` output — every reference file has content beyond the stub heading+note.
23. Run: `grep -nE '\b--[a-z-]+' .claude/skills/using-claude-cli/references/*.md` and manually confirm each flag against the OQ3 source.
    - **Expected:** every documented flag exists in the OQ3-verified fact set; experimental items (e.g., agent teams) explicitly labeled.
24. Run: `grep -nE 'Bash\(|mcp__' .claude/skills/using-claude-cli/references/permissions-and-mcp.md`
    - **Expected:** tool-rule and MCP examples present and use verified syntax `Bash(<cmd>:*)` / `mcp__<server>__<tool>` (Q13).
25. Run: re-run step 14 budget check on SKILL.md body.
    - **Expected:** body still < 500 lines / < 5000 tokens — no reference content leaked back into the body.

### Verify Slice 2

26. **Checkpoint:** run steps 22–25 together.
    - [ ] Each reference file's topic matches the link/scope the SKILL.md body declared in Slice 1 (link contract holds).
    - [ ] Every flag/event/mode/option exists in the OQ3-verified fact set; experimental items labeled (step 23).
    - [ ] Tool-rule and MCP examples use verified syntax (step 24).
    - [ ] No reference file silently echoes unverified ticket specifics (10MB stdin cap, exact permission-mode list) unless confirmed via OQ3/OQ5.
    - [ ] SKILL.md body remains within budget after references finalized (step 25).
    - [ ] If `skill-creator` reachable, references validated via its eval loop (OQ1).

---

## Rollback Notes

- No DB migrations, config changes, or destructive ops in this plan — all steps create or edit Markdown files under `.claude/skills/using-claude-cli/`.
- Steps 1–6 (file creation): rollback = `rm -rf .claude/skills/using-claude-cli/`.
- Steps 7–12, 17–21 (edits): rollback = `git checkout -- .claude/skills/using-claude-cli/` (or revert to the stub content of steps 1–6).
- No external system, package, or settings file is touched, so no out-of-tree state to reverse.
