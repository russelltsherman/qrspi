# Implementation Plan — Create `using-gemini-cli` Agent Skill

**Structure basis:** structure.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total steps:** 18

> This ticket produces a pure-markdown skill: no code, no executable types, no
> automated tests (ref: structure.md preamble, design.md §Delta). "Create"/"Modify"
> steps therefore act on markdown files. The whole skill is one cohesive unit authored
> via the `skill-creator` skill and validated by its eval loop, so the single Verify
> checkpoint is process- and content-based, not a test runner.

## Slice 1: Author the `using-gemini-cli` skill (SKILL.md + references)

### Setup

1. Invoke the `skill-creator` skill to scaffold a new skill named `using-gemini-cli`
   — produces the `.claude/skills/using-gemini-cli/` directory and an initial
   `SKILL.md` skeleton (ref: design.md §Desired End State "Built using the Anthropic
   skill builder skill"; process requirement). All subsequent authoring steps run
   inside the `skill-creator` workflow.

2. ✨ Create `.claude/skills/using-gemini-cli/SKILL.md` frontmatter — YAML block with
   `name: using-gemini-cli`, a `description` (mirroring the `using-graphite-cli`
   triggering style), and `allowed-tools` including `Bash`
   (ref: structure.md Contracts `frontmatter.name`, `frontmatter.allowed-tools ⊇ {Bash}`;
   `SKILLFrontmatter` required set = `name, description, allowed-tools`).

### Core Logic — SKILL.md body sections (concise overview, pointers to references)

3. ✨ Add `SKILL.md` "Install & Authenticate" section — `npm`/`npx` install plus
   Google-account vs. API-key auth; every flag/fact pinned to a verified Gemini CLI
   version/date (ref: design.md §Desired End State, Q9; structure.md verification on
   pinned facts).

4. ✨ Add `SKILL.md` "Invocation" section — interactive, non-interactive `-p`, and
   stdin-pipe modes, each invoked via the `Bash` tool (ref: design.md §Decision 3, Q6).

5. ✨ Add `SKILL.md` "Permission & Approval Model" section — default, auto_edit, yolo
   with when-to-use guidance and HARD-STOP-on-error framing; points to
   `references/permissions-and-sandbox.md` by relative path (ref: design.md §Desired
   End State, Q10; structure.md Contract on relative-path reference resolution).

6. ✨ Add `SKILL.md` "Sandbox" section — `--sandbox`/`-s`, profiles, `SANDBOX_MOUNTS`,
   recommend for autonomous/subagent use; points to
   `references/permissions-and-sandbox.md`. Scope "sandbox"/"yolo" terms strictly to
   Gemini CLI — no cross-ref to the in-repo `yolo()` wrapper or JS workflow sandbox
   (ref: design.md Risk 3; structure.md verification on no cross-reference).

7. ✨ Add `SKILL.md` "GEMINI.md Context Hierarchy" section — layered context-file
   convention mirroring the repo's `@import` analog (ref: design.md §Desired End
   State, Q8).

8. ✨ Add `SKILL.md` "MCP & Extensions" section — `mcpServers` config and
   `gemini extensions install`, Gemini-specifics only; points to
   `references/subagents-mcp-extensions.md` (ref: design.md §Desired End State).

9. ✨ Add `SKILL.md` "Subagents" section — `.gemini/agents/*.md`, routing/`@agent-name`,
   tool grants; points to `references/subagents-mcp-extensions.md` (ref: design.md
   §Desired End State).

10. ✨ Add `SKILL.md` "Multi-Agent Orchestration" section — non-interactive `-p`, stdin
    context, stdout capture, filesystem coordination, `--sandbox`, stateless handoff,
    HARD-STOP-on-error; points to `references/orchestration.md` (ref: structure.md
    Contract `orchestration guidance`; design.md §Decision 3, Q7, Q10).

11. ✨ Add `SKILL.md` "Limitations" section — June 2026 Antigravity-deprecation note
    pinned to the date and pre-migration tool state (ref: design.md §Desired End State,
    Q9; OQ4 — keep to a forward-pointer unless a human directs deeper treatment).

12. ✨ Add `SKILL.md` "Worked Examples" section — code review, test generation, codebase
    exploration, each as a `Bash` `gemini …` invocation (ref: design.md §Desired End
    State).

### Reference deep-dives

13. ✨ Create `.claude/skills/using-gemini-cli/references/permissions-and-sandbox.md`
    — deep dive on the permission/approval model (default, auto_edit, yolo) and sandbox
    profiles/`SANDBOX_MOUNTS`; reachable by the relative-path mentions from steps 5–6
    (ref: structure.md Files touched; design.md §Delta).

14. ✨ Create `.claude/skills/using-gemini-cli/references/orchestration.md` — deep dive
    on calling Gemini from external agents: `-p`, stdin context, stdout capture,
    filesystem coordination, stateless handoff, HARD-STOP-on-error; reachable from
    step 10 (ref: structure.md Files touched; design.md §Decision 3).

15. ✨ Create `.claude/skills/using-gemini-cli/references/subagents-mcp-extensions.md`
    — deep dive on `.gemini/agents/*.md` subagents, `mcpServers` config, and
    `gemini extensions install`; reachable from steps 8–9 (ref: structure.md Files
    touched).

### Consistency pass

16. ⚠️ Modify `SKILL.md` — audit body size and trim to enforce the cap, moving any
    overflow detail into the `references/*.md` files.
    - **Current:** full-detail body after sections 3–12 added.
    - **After:** overview body ≤ 500 lines AND ≤ 5000 tokens, detail relocated to
      references (ref: structure.md Contract `SKILL.md body ≤ 500 lines AND ≤ 5000 tokens`,
      design.md §Decision 2).

17. ⚠️ Modify `SKILL.md` and references — verify every `references/*.md` path mentioned
    in prose resolves to a created file and there are no orphan reference files.
    - **Current:** relative-path mentions added piecemeal across steps 5–10.
    - **After:** every mention resolves to an existing file; every reference file is
      linked from prose (ref: structure.md verification on broken links / orphans).

### Verify Slice 1

18. **Checkpoint:** Run the `skill-creator` eval loop on `using-gemini-cli`, then
    `python3 -c "import yaml,sys; d=yaml.safe_load(open('.claude/skills/using-gemini-cli/SKILL.md').read().split('---')[1]); assert d['name']=='using-gemini-cli' and 'description' in d and 'Bash' in d['allowed-tools']; print('frontmatter OK')"`
    (run from the worktree root). Then a manual end-to-end read-through.
    - [ ] Authored via `skill-creator` and passed its eval loop.
    - [ ] Frontmatter parses as valid YAML with `name: using-gemini-cli`, `description`,
          and `allowed-tools` including `Bash`.
    - [ ] `SKILL.md` body ≤ 500 lines and ≤ 5000 tokens.
    - [ ] All twelve §Desired End State acceptance-criterion sections present across
          `SKILL.md` + `references/`.
    - [ ] Every `references/*.md` path in prose resolves; no orphan reference files.
    - [ ] Every Gemini-specific fact pinned to a verified version/date; any
          unconfirmable fact explicitly flagged.
    - [ ] No cross-reference to the in-repo `yolo()` wrapper or JS workflow "sandbox".
    - [ ] Manual read-through confirms an agent can install, authenticate, and invoke
          Gemini from the document alone.

---

## Rollback Notes

- No DB migrations, config changes, or destructive operations. All steps create or
  edit new markdown files under `.claude/skills/using-gemini-cli/`.
- Rollback for any step: delete the `.claude/skills/using-gemini-cli/` directory
  (or the specific file created). No registry, `.claude/settings.json`, or README
  edit is made, so there is nothing else to revert (ref: structure.md Modified Types
  "None"; design.md §Delta "Modified files: None").
