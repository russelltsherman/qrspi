# Implementation Plan — Create a new agent skill using Codex CLI

**Structure basis:** structure.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft
**Total steps:** 16

> **BLOCKING PRECONDITION (structure §Unverified Assumptions, OQ1):** the final skill
> `<name>` is undecided (candidate: `codex-cli`). Every path below uses `<name>` literally.
> Resolve the name before Step 1; substitute it identically across the directory name,
> frontmatter `name`, and frontmatter `command` (three-way identity, structure Contracts / Q4).
> If the agentskills.io frontmatter field list (OQ4) or the skill-creator attestation
> expectation (OQ2) is later supplied, revisit Slice 2 frontmatter and verification.

> **AUTHORING NOTE:** Codex CLI factual content (sandbox modes, macOS Seatbelt /
> `network_access` bug, Linux Bubblewrap+Landlock, `config.toml` schema, `codex exec`
> flags, MCP/Agents-SDK behavior, AGENTS.md hierarchy) is external and unverified in-repo
> (structure §Unverified Assumptions). Source accurate, current Codex CLI facts at authoring
> time. Per MEMORY (skill-creator directive), invoke the global skill-creator skill during
> authoring and record the invocation (OQ2 attestation).

## Slice 1: Reference material (`references/`)

### Setup

1. ✨ Create `.claude/skills/<name>/references/` directory (and parent
   `.claude/skills/<name>/`) — the `SKILL_DIR` container from structure Contracts. Established
   implicitly by creating the first file in Step 2.

### Core Logic

2. ✨ Create `.claude/skills/<name>/references/sandbox-and-platform.md` — long-form reference
   covering all three sandbox modes (read-only / workspace-write / danger-full-access) AND
   both OS enforcement branches: macOS Seatbelt and Linux Bubblewrap+Landlock, including the
   macOS `network_access` Seatbelt bug. Structure as rule-lists + fenced `bash` blocks +
   hazard callouts (structure Slice 1, Decision 3; design §Desired End State, Risk Register).

3. ✨ Create `.claude/skills/<name>/references/config-toml.md` — reference documenting
   `~/.codex/config.toml` vs `.codex/config.toml`, key sections, `[profiles.<name>]`,
   `model_instructions_file`, and project-root detection (structure Contracts / Slice 1).

4. ✨ Create `.claude/skills/<name>/references/multi-agent.md` — reference covering MCP server
   mode, Agents SDK pipelines, subagents, and worktree parallelism (structure Contracts /
   Slice 1).

### Tests

5. Run: `ls .claude/skills/<name>/references/`
   - **Expected:** exactly `sandbox-and-platform.md`, `config-toml.md`, `multi-agent.md`
     present, filenames verbatim per structure Contracts.

6. Run: `grep -il "seatbelt" .claude/skills/<name>/references/sandbox-and-platform.md &&
   grep -il "bubblewrap" .claude/skills/<name>/references/sandbox-and-platform.md &&
   grep -il "network_access" .claude/skills/<name>/references/sandbox-and-platform.md`
   - **Expected:** all three terms present (both OS branches + the macOS bug covered).

### Verify Slice 1

7. **Checkpoint:** `ls .claude/skills/<name>/references/ && wc -l .claude/skills/<name>/references/*.md`
   - [ ] All three files exist with exact filenames from structure Contracts.
   - [ ] `sandbox-and-platform.md` covers all three sandbox modes AND both OS branches
         (macOS Seatbelt, Linux Bubblewrap+Landlock) including the macOS `network_access` bug.
   - [ ] `config-toml.md` documents both config locations, `[profiles.<name>]`, and
         `model_instructions_file`.
   - [ ] `multi-agent.md` covers MCP server mode, Agents SDK, subagents, worktree parallelism.
   - [ ] Markdown lints clean — fenced `bash` blocks and headings consistent with repo
         `SKILL.md` style.

---

## Slice 2: `SKILL.md` body + integration + validation

### Setup

8. ✨ Create `.claude/skills/<name>/SKILL.md` with frontmatter only — exactly the 5-field
   `SkillFrontmatter` shape: `name`, `description`, `command`, `argument-hint`, `allowed-tools`
   (structure New Types / Decision 2, Q3). `name` MUST equal the directory `<name>` and the
   `command` slug (three-way identity, Q4). `description` quoted if it contains commas/colons/
   parens; `allowed-tools` a comma-separated list.

### Core Logic

9. ⚠️ Modify `.claude/skills/<name>/SKILL.md` — append the body sections.
   - **Current:** frontmatter only (from Step 8).
   - **After:** frontmatter + body sections: overview; approval-mode selection table
     (suggest / auto-edit / full-auto with a context→mode decision table, Q8); `codex exec`
     non-interactive/CI patterns (positional, stdin `-`, prompt-plus-stdin; `--json`/`--quiet`;
     hermetic flags); AGENTS.md hierarchy + authoring (`AGENTS.override.md`/`AGENTS.md`
     discovery, concatenation precedence, size cap, nested-dir rules); known limitations +
     workarounds (re-run nondeterminism, macOS `network_access` Seatbelt bug, context-window
     pressure, `--sandbox` override verification); Unix pipe composition examples (structure
     Slice 2; design §Desired End State).

10. ⚠️ Modify `.claude/skills/<name>/SKILL.md` — add on-demand load pointers.
    - **Current:** body sections without reference pointers (from Step 9).
    - **After:** body emits an explicit `Read references/<file>.md` pointer for each of the
      three Slice 1 files, each tied to a narrow execution path (structure Contracts on-demand
      load convention, Q7). Paths must match verbatim: `references/sandbox-and-platform.md`,
      `references/config-toml.md`, `references/multi-agent.md` (cross-slice contract).

### Tests

11. Run: `grep -c "Read references/" .claude/skills/<name>/SKILL.md`
    - **Expected:** at least 3 — one pointer per reference file.

12. Run: `for f in sandbox-and-platform config-toml multi-agent; do test -f
    ".claude/skills/<name>/references/$f.md" && grep -q "references/$f.md"
    ".claude/skills/<name>/SKILL.md" || echo "MISSING $f"; done`
    - **Expected:** no `MISSING` output — every pointed-to file exists and is referenced
      (cross-slice contract honored).

13. Run: `awk '/^---$/{n++} n>=2 && !/^---$/{print}' .claude/skills/<name>/SKILL.md | wc -l`
    - **Expected:** body under 500 lines (Q6 advisory ceiling, hand-checked). Also hand-check
      token estimate under 5000.

### Verify Slice 2

14. **Checkpoint:** validate frontmatter shape and identity —
    `sed -n '/^---$/,/^---$/p' .claude/skills/<name>/SKILL.md`
    - [ ] Frontmatter has exactly the 5 fields (`name`, `description`, `command`,
          `argument-hint`, `allowed-tools`).
    - [ ] `name` equals the directory name AND `command` (three-way identity, Q4).

15. **Checkpoint:** validate body completeness and cross-slice binding —
    `grep -iE "approval|codex exec|AGENTS.md|limitation|pipe|Read references/" .claude/skills/<name>/SKILL.md`
    - [ ] Body contains all required sections: approval-mode table, `codex exec` patterns,
          AGENTS.md authoring, limitations/workarounds, pipe examples.
    - [ ] Body emits an explicit `Read references/<file>.md` pointer for each of the three
          reference files, and each pointed-to file exists.
    - [ ] Body under 500 lines AND token estimate under 5000 (hand-checked, Q6).
    - [ ] skill-creator skill invoked during authoring; invocation recorded as process
          attestation (OQ2 — cannot be verified in-repo).

16. **Checkpoint:** confirm the skill loads without a frontmatter-loader error (manual check —
    list/load the skill in this Claude Code install).
    - [ ] Skill loads / lists without frontmatter-loader error.

---

## Rollback Notes

- No DB migrations, config changes, or destructive operations in this plan — all steps create
  net-new files under a net-new directory `.claude/skills/<name>/`.
- Steps 1–4 (Slice 1): to reverse, delete `.claude/skills/<name>/references/` (and the parent
  `.claude/skills/<name>/` if no `SKILL.md` was yet created).
- Steps 8–10 (Slice 2): to reverse, delete `.claude/skills/<name>/SKILL.md`. Deleting it
  leaves Slice 1 references intact and independently valid.
- Full rollback: `rm -rf .claude/skills/<name>/` removes the entire new skill with no impact
  on existing skills, the eval harness, or any modified type (structure Modified Types: None).
