# Implementation Plan — Create a new agent skill: using-codex-cli

**Structure basis:** structure.md @ 2026-05-31T17:11:00Z
**Generated:** 2026-05-31T17:14:00Z
**Status:** draft
**Total steps:** 14

## Slice 1: Skeleton skill — frontmatter, body sections, and validator (TDD)

### Setup

1. ✨ Create directory `.claude/skills/using-codex-cli/` with subdirs `references/` and `scripts/`.
2. ✨ Create `.claude/skills/using-codex-cli/SKILL.md` — YAML frontmatter (`name: using-codex-cli`, `description` leading with capability + trigger phrases per research Q6, `command: /using-codex-cli`, `argument-hint: <task description>`, `allowed-tools: Read, Bash`) followed by all required H2 section headers as brief stubs: Overview, Approval Modes, Sandbox Modes, AGENTS.md, Configuration, Session Management, Non-Interactive Automation (codex exec), Multi-Agent Integration, Limitations & Pitfalls, Quick Decision Rules. Reference structure.md §Contracts (SkillFrontmatter, SkillBody).

### Core Logic

3. ✨ Create `.claude/skills/using-codex-cli/scripts/validate_skill.py` implementing the `validate_skill(skill_dir)` contract (structure.md §Contracts):
   - Parse YAML frontmatter; assert keys `name`, `description`, `command`, `argument-hint`, `allowed-tools` present.
   - Assert frontmatter `name` == basename of skill_dir.
   - Count body lines (everything after the closing `---`); assert ≤ 500.
   - Assert each required H2 header from a REQUIRED_SECTIONS list is present.
   - Find every relative `references/...md` link in the body; assert each target file exists.
   - Exit 0 on pass, non-zero with a clear message on first failure.
4. ✨ Add a `.gitkeep` (or first stub `references/sandbox-and-approvals.md`) under `references/` so the directory is tracked and at least one body reference link resolves in Slice 1.

### Tests

5. ✨ Create `.claude/skills/using-codex-cli/scripts/test_validate_skill.py` — uses tempdirs/fixtures to assert the validator:
   - accepts a well-formed stub skill (the real one) → pass
   - rejects a skill missing a required section → fail
   - rejects a body over 500 lines → fail
   - rejects a body with a broken `references/...md` link → fail
   - rejects frontmatter whose `name` != directory name → fail
6. Run: `python .claude/skills/using-codex-cli/scripts/test_validate_skill.py`
   - **Expected:** all test cases pass (validator behaves per contract).

### Verify Slice 1

7. **Checkpoint:** `python .claude/skills/using-codex-cli/scripts/validate_skill.py .claude/skills/using-codex-cli`
   - [ ] Validator exits 0 on the stub skill
   - [ ] `test_validate_skill.py` passes
   - [ ] Directory name == frontmatter `name` (`using-codex-cli`)

---

## Slice 2: Author body content + reference files (full acceptance coverage)

### Setup

8. ✨ Create the five reference files under `references/` (replace the Slice 1 stub):
   - `sandbox-and-approvals.md` — approval×sandbox matrix; macOS Seatbelt (`sandbox-exec`) vs Linux Bubblewrap+Landlock namespace isolation; network-off-by-default and the macOS `network_access` silent-ignore pitfall + `--sandbox` override.
   - `config.md` — config.toml sections (`model`, `model_provider`, sandbox, approval, MCP), `[profiles.<name>]`, `model_instructions_file`, `codex features enable/disable`, project-root detection via `.git`, user (`~/.codex/config.toml`) vs project (`.codex/config.toml`) precedence.
   - `agents-md.md` — `AGENTS.override.md` then `AGENTS.md` discovery root→cwd, concatenation with deeper-wins precedence, 32 KiB `project_doc_max_bytes`, `project_doc_fallback_filenames`, nested per-service rules.
   - `automation.md` — `codex exec`/`codex e` input patterns (positional, stdin `-`, prompt+stdin), stderr/stdout split, `--json`, `--quiet`/`-q`, `--ignore-user-config`/`--ignore-rules`, `CODEX_API_KEY`, Unix pipe composition examples.
   - `multi-agent.md` — MCP server mode (`codex()`/`codex-reply()` tools), Agents SDK pipelines (PM/Designer/Frontend/Backend/Tester), subagents (explicit-request-only), experimental git-worktree parallelism, custom agent definitions.

### Core Logic

9. ⚠️ Modify `.claude/skills/using-codex-cli/SKILL.md` — replace each stub section with real, concise guidance:
   - **Current:** stub headers from Slice 1.
   - **After:** Approval Modes (suggest/auto-edit/full-auto + when-to-use decision rule); Sandbox Modes (read-only/workspace-write/danger-full-access + 1-line platform note linking sandbox-and-approvals.md); AGENTS.md (summary + link); Configuration (summary + link); Session Management (resume/--ephemeral/goal mode); Non-Interactive Automation (codex exec essentials + 1-2 pipe examples + link); Multi-Agent Integration (summary + link); Limitations & Pitfalls (re-run nondeterminism→use tests, macOS network pitfall, long-chain caveat, context pressure, sandbox config bug); Quick Decision Rules (default workspace-write + auto-edit; full-auto only in containers; explicit `--sandbox`/`--approval-policy` in scripts; MCP server over ad-hoc subagents). Keep body ≤ 500 lines by deferring tables to references.
10. ⚠️ Modify `SKILL.md` to ensure every reference file created in step 8 is linked by relative path from the body (so the validator's link check covers them).

### Tests

11. ✨ Extend/confirm `scripts/test_validate_skill.py` still passes against the now-full skill (no new test file needed; the validator generalizes). If body approaches the limit, the oversize test guards it.
12. Run: `python .claude/skills/using-codex-cli/scripts/validate_skill.py .claude/skills/using-codex-cli`
   - **Expected:** pass — body ≤ 500 lines, all required sections present, all five reference links resolve.

### Setup (docs, optional)

13. ⚠️ Modify `README.md` and `.claude/CLAUDE.md` — add a one-line `using-codex-cli` entry to the skill listing for human discoverability (research Q12: not load-bearing; auto-discovery already registers it).

### Verify Slice 2

14. **Checkpoint:** `python .claude/skills/using-codex-cli/scripts/validate_skill.py .claude/skills/using-codex-cli && python .claude/skills/using-codex-cli/scripts/test_validate_skill.py`
    - [ ] Validator passes on the fully-authored skill
    - [ ] All validator tests pass
    - [ ] Acceptance-criteria checklist (all 3 approval modes; sandbox modes + platform enforcement; codex exec/CI patterns; AGENTS.md hierarchy; MCP/multi-agent; config.toml + profiles; limitations; pipe examples) each satisfied in body or a linked reference

---

## Rollback Notes

- Step 1-2: `rm -rf .claude/skills/using-codex-cli` removes the entire skill cleanly (no other code depends on it).
- Step 13: revert the one-line additions to `README.md` / `.claude/CLAUDE.md`; they are isolated list entries.
- No migrations, no shared modules touched — every step is contained within the new skill directory except the optional doc entry in step 13.
