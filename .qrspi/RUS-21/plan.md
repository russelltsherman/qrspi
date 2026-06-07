# Implementation Plan — Create a new agent skill `using-codex-cli`

**Structure basis:** structure.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total steps:** 18

> NOTE: This is a documentation / skill-authoring ticket — one vertical slice, no
> runtime code. Steps create markdown artifacts and validate them. Several design
> claims are [UNVERIFIED] (research was skipped); see the structure's Unverified
> Assumptions (UA-1..UA-9). Step 1 resolves the blocking ones before authoring.

## Slice 1: Author and validate the `using-codex-cli` skill

### Setup

1. ⚠️ Resolve blocking unverified assumptions before authoring (no file written).
   - **Current:** UA-1 (frontmatter schema), UA-3 (`references/` precedent),
     UA-6 (skill-builder = `skill-creator`?), UA-7 (slash-command wrapper needed?)
     are open per structure §Unverified Assumptions.
   - **After:** Confirm against the live codebase: inspect an existing
     `.claude/skills/<name>/SKILL.md` for the exact frontmatter fields in use
     (resolves UA-1/UA-5), confirm whether any `references/` dir already exists
     (UA-3), confirm the skill-builder skill name is `skill-creator` (UA-6), and
     decide wrapper vs directory-only discovery (UA-7). Record decisions inline;
     if any cannot be resolved, surface to the human and stop.

2. ✨ Create `.claude/skills/using-codex-cli/SKILL.md` — write the YAML
   frontmatter block only (`frontmatter-contract`): opening `---`, `name:
   using-codex-cli`, a non-empty `description`, plus exactly the additional fields
   confirmed required in step 1, closing `---`. Body filled by later steps.

### Core Logic — SKILL.md body sections (in-body per design Decision 1)

3. ⚠️ Modify `.claude/skills/using-codex-cli/SKILL.md` — add the **approval modes**
   section (suggest / auto-edit / full-auto) with the decision matrix: local dev →
   suggest; trusted iterative → auto-edit; CI/containers → full-auto.
   - **Current:** frontmatter only, empty body.
   - **After:** body contains an "Approval Modes" section (acceptance row 4).

4. ⚠️ Modify `.claude/skills/using-codex-cli/SKILL.md` — add the **sandbox modes**
   section: read-only / workspace-write / danger-full-access; macOS Seatbelt and
   Linux bubblewrap/Landlock enforcement; network-off-by-default guidance.
   - **Current:** body has Approval Modes.
   - **After:** body adds "Sandbox Modes" section (acceptance row 5).

5. ⚠️ Modify `.claude/skills/using-codex-cli/SKILL.md` — add the **session
   management** section (fresh sessions for discrete tasks; context-window pressure).
   - **Current:** body has Approval + Sandbox Modes.
   - **After:** body adds "Session Management" section.

6. ⚠️ Modify `.claude/skills/using-codex-cli/SKILL.md` — add the **AGENTS.md
   hierarchy** section: `AGENTS.override.md`-first cascade, concatenation with deeper
   precedence, 32 KiB size limit, nested directory rules.
   - **Current:** body has Approval/Sandbox/Session sections.
   - **After:** body adds "AGENTS.md Hierarchy" section (acceptance row 7).

7. ⚠️ Modify `.claude/skills/using-codex-cli/SKILL.md` — add a condensed
   **config.toml quick-start** table plus a relative TOC link to
   `references/config-reference.md` (design Decision 3 Option B).
   - **Current:** body has the four sections above.
   - **After:** body adds a quick-start config table + reference link.

8. ⚠️ Modify `.claude/skills/using-codex-cli/SKILL.md` — add a **MCP server mode**
   summary (~40 lines, 2 worked examples: orchestrator→`codex()`, nested
   `codex-reply()`) plus a TOC link to `references/mcp-server-mode.md`
   (design Decision 4 Option B, acceptance row 8).
   - **Current:** body has config quick-start.
   - **After:** body adds "MCP Server Mode" section + reference link.

9. ⚠️ Modify `.claude/skills/using-codex-cli/SKILL.md` — add a **re-run
   non-determinism** flowchart (re-run → diff → run tests → accept/rollback) plus
   a TOC link to `references/limitations-and-workarounds.md` (design Decision 5
   Option B, acceptance row 10).
   - **Current:** body has MCP section.
   - **After:** body adds "Re-run Non-Determinism / Limitations" section + link.

10. ⚠️ Modify `.claude/skills/using-codex-cli/SKILL.md` — add a TOC link to
    `references/codex-exec-patterns.md` for `codex exec` + Unix-pipe composition
    depth (acceptance rows 6 and 11 covered in the reference file).
    - **Current:** body has limitations section + earlier links.
    - **After:** body's reference TOC links to all four reference files.

### Reference files (`references/` — body-to-references-link-contract)

11. ✨ Create `.claude/skills/using-codex-cli/references/config-reference.md` — full
    `config.toml` schema: user (`~/.codex/config.toml`) vs project
    (`.codex/config.toml`), `[profiles.<name>]`, model settings, feature flags
    (`codex features enable/disable`), `model_instructions_file`,
    `project_doc_max_bytes`, `project_doc_fallback_filenames` (acceptance row 9).

12. ✨ Create `.claude/skills/using-codex-cli/references/codex-exec-patterns.md` —
    `codex exec` positional arg, stdin `-`, prompt+stdin piping, `--json`,
    `--quiet`, `--ignore-user-config`, `--ignore-rules`; Unix pipe composition and
    CI pipeline patterns (acceptance rows 6 and 11).

13. ✨ Create `.claude/skills/using-codex-cli/references/mcp-server-mode.md` —
    `codex()` / `codex-reply()` tool schemas, 2-3 worked multi-agent orchestration
    examples, git-worktrees-for-parallel-agents, subagent-only-when-requested
    discipline (acceptance row 8; depth per UA-8 decision).

14. ✨ Create `.claude/skills/using-codex-cli/references/limitations-and-workarounds.md`
    — re-run non-determinism flow with examples, macOS network/sandbox bugs (prefer
    `--sandbox` flag over config.toml), long-chain limits, context-window pressure /
    fresh-session guidance (acceptance row 10).

### Tests / Validation

15. ⚠️ Verify factual fidelity of all Codex CLI claims (UA-9) — cross-check sandbox
    enforcement mechanisms, config.toml fields, `codex exec` flags, the macOS
    network bug, and the 32 KiB AGENTS.md limit against current Codex CLI docs
    before treating them as authoritative. Fix any divergent claims in the files
    from steps 2-14.

16. ✨ Run the `skill-creator` skill and its eval loop against
    `.claude/skills/using-codex-cli/` (`skill-creator-validation-contract`,
    global directive feedback_skill_creator). Apply any fixes it reports.
    - Run: invoke `skill-creator` on the new skill directory.
    - **Expected:** skill-creator reports the skill valid; eval loop passes.

### Verify Slice 1

17. **Checkpoint — frontmatter + length:**
    `python3 - <<'PY'` parse of `SKILL.md` (or equivalent): split on the second
    `---`, assert YAML frontmatter loads, `name == using-codex-cli`, non-empty
    `description`; count body lines and tokens.
    - [ ] Frontmatter parses as YAML; `name: using-codex-cli`; non-empty
      `description` (frontmatter-contract).
    - [ ] `SkillBody` < 500 lines AND < 5000 tokens, measured after the closing
      `---` (body-length-contract).

18. **Checkpoint — links + coverage + discovery:**
    `grep -oE '\]\(references/[^)]+\)' .claude/skills/using-codex-cli/SKILL.md`
    and confirm each target exists; list `references/*.md` and confirm each is
    linked.
    - [ ] Every `references/*.md` is linked from the body and every body link
      resolves to an existing file; no dangling links (body-to-references-link-contract).
    - [ ] All 11 acceptance-criteria rows (design §Desired End State item 2) are
      covered by body + references (acceptance-coverage-contract).
    - [ ] Skill triggers in the harness on a Codex-CLI-related prompt (discoverable).
    - [ ] `skill-creator` validation passed (from step 16).

---

## Rollback Notes

- Steps 2-14 (greenfield additions): rollback = delete the
  `.claude/skills/using-codex-cli/` directory in its entirety. No existing files
  are modified (design §Delta "Modified files: None"), so removal fully reverts the
  change with no side effects.
- No DB migrations, config changes, or destructive operations are involved.
