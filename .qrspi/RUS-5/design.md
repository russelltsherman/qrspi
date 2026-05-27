# Design — Create a new agent skill called writing bash scripts

**Ticket:** RUS-5
**Generated:** 2026-05-27
**Status:** draft

---

## Current State

The `writing-bash-scripts` skill already exists in the global skills directory (`/home/vscode/.claude/skills/writing-bash-scripts/`) as a SKILL.md body (274 lines, 7432 bytes) plus a `references/` directory with four files (patterns.md, gotchas.md, conventions.md, template.sh) (ref: Q1). The frontmatter uses `name: writing-bash-scripts`, a description field with trigger phrases, and `command: writing-bash-scripts` (without a leading slash) (ref: Q2). The skill body covers script structure, strict mode, quoting rules, error handling, argument parsing, function conventions, testing (BATS), and ShellCheck (ref: Q2). The `references/patterns.md` file covers the subcommand dispatcher, getopts, long-option parsing, logging helpers, and function organization (ref: Q4). The `references/gotchas.md` file covers BSD vs GNU coreutils differences, bash 3.2 vs 4+ feature gaps, common ShellCheck warnings, word splitting pitfalls, globbing hazards, and subshell variable scope (ref: Q4). The `references/conventions.md` file covers quoting, variable naming, declaration-separation, dependency checking, temp files, exit codes, and signal trapping (ref: Q4). The `references/template.sh` is a 105-line canonical script demonstrating all conventions together (ref: Q4). The skill was built using the skill-creator tool, which produced the eval infrastructure alongside the skill (ref: Q3). No `agentskills.io` specification was found in the codebase; the format appears to be a project-local standard derived from skill-creator (ref: Q4). The skill-creator output includes eval harness artifacts (evals.json, timing.json, grading.json, benchmark.json) that do not apply to a general-purpose guidance skill (ref: Q3).

---

## Desired End State

| # | Acceptance Criterion | Target Behavior |
|---|----------------------|-----------------|
| 1 | Follows agentskills.io directory structure (proxied via skill-creator pattern: SKILL.md + optional references/, scripts/, assets/) | Skill directory at `/home/vscode/.claude/skills/writing-bash-scripts/` contains SKILL.md with YAML frontmatter plus `references/` directory with referenced files (currently satisfied) |
| 2 | Built using the Anthropic skill-creator skill | SKILL.md frontmatter has required fields: `name` (matches directory), `description` (trigger phrases included), `command` (invocation form) (currently satisfied) |
| 3 | SKILL.md body under 500 lines / 5000 tokens | SKILL.md body is 274 lines (limit: 500) (currently satisfied) |
| 4 | Detailed reference material in `references/` directory | Four reference files cover: dispatcher patterns (patterns.md), portability gotchas (gotchas.md), conventions for quoting/temp-files/exit-codes (conventions.md), and a full structural template (template.sh) (currently satisfied) |
| 5 | Produces ShellCheck-clean output when followed | SKILL.md section on ShellCheck + `references/gotchas.md` detailed rules + `references/conventions.md` variable separation rules + template.sh as passing example (currently satisfied) |

Additional requirements from ticket body:
- Encoding of all listed conventions: shebang, strict mode, trap patterns, stderr diagnostics, exit codes, getopts, subcommand dispatcher with `cmd_` prefix and dynamic lookup, logging helpers with color detection, quoting rules, dependency checking, heredoc usage/help, mktemp with EXIT trap, seven-section code organization, BATS testing recommendation (ref: Q9, Q10)

---

## Delta

**Files to modify:**

1. **`/home/vscode/.claude/skills/writing-bash-scripts/SKILL.md`** — Add/expand:
   - `command` field: change `writing-bash-scripts` to `/writing-bash-scripts` (add leading slash) to match other global skill patterns
   - "Script Structure" section: add explicit seven-section ordered list matching ticket convention
   - "Function Conventions" section: add `declare -f` dynamic lookup pattern for subcommand dispatch (ticket: "Lookup via `declare -f \"cmd_${1}\"`")
   - Add dedicated "Usage/Help" section describing heredoc `usage()` pattern with `${0##*/}` basename and column alignment (ref: Q9, Q10)
   - Add "Logging" section with `[[ -t 2 ]]` color detection pattern (currently only in references/patterns.md, not in SKILL.md body)
   - Add `trap 'echo "Error on line $LINENO"'` debugging pattern (ticket convention, not currently in any file)
   - Add line-count guidance: "Never exceed ~200 lines without strong justification; at that point suggest a different language" (ticket requirement, currently absent)
   - Add "Gotchas" section referencing `references/gotchas.md` with key callouts (aligns with progressive disclosure pattern used by `qrspi-*` skills)

2. **`/home/vscode/.claude/skills/writing-bash-scripts/references/template.sh`** — Minor additions:
   - Add `trap 'echo "Error on line $LINENO"'` debugging trap
   - Add `usage()` function body demonstrating heredoc with column alignment (currently present but could add `${0##*/}` comment)
   - Consider adding `[[ -t 2 ]]` color block to demonstrate color detection pattern

3. **Files NOT created:** No `scripts/` or `assets/` subdirectory needed. The skill is pure guidance with reference documentation. No eval harness needed for a general-purpose skill (the skill-creator created one, but it can be discarded).

---

## Pattern Decisions

| Decision | Option A | Option B | Recommendation | NEW PATTERN |
|----------|----------|----------|----------------|-------------|
| **Global vs worktree-local placement** | Place in `/home/vscode/.claude/skills/` (global) | Place in `.claude/skills/` (worktree-local per-ticket) | Global — the skill is general-purpose, not ticket-specific (ref: Q7). Two-tier scoping already established in project: global for general skills, worktree-local for workflow orchestrators (ref: Q6) | No |
| **`command` field format** | `writing-bash-scripts` (no slash) | `/writing-bash-scripts` (leading slash) | `/writing-bash-scripts` — all other global skills (skill-creator, mcp-builder, using-graphite-cli, workflow-creator, graphite-workspace) and all project-local skills use the leading slash convention. The missing slash is a deviation from observed patterns (ref: Q2, Q7) | No |
| **Line-count threshold enforcement** | Add "200-line rule" to SKILL.md body referencing the ticket convention | Keep SKILL.md as-is (200-line threshold was not found in any existing file; it may be a ticket-internal convention) | Add it to SKILL.md — the ticket explicitly requires this guidance. Document it as "scripts over 200 lines should be evaluated for whether a different language is more appropriate" rather than a hard cutoff (ref: Q10). The 500-line limit applies to SKILL.md files; the 200-line limit applies to generated scripts | Yes — this is a new convention not present in any existing skill |
| **SKILL.md body vs reference file content** | Keep verbose patterns (BSD vs GNU tables, ShellCheck warnings) in reference files (current) | Move all patterns into SKILL.md body for self-containment | Keep in reference files — the project uses progressive disclosure: SKILL.md body is minimal and loads references conditionally (ref: Q4). This matches `qrspi-*` skill patterns and keeps the SKILL.md under 500 lines | No |
| **`declare -f` dynamic dispatch vs `case` dispatcher** | Use `declare -f "cmd_${1}"` lookup for dynamic dispatch (ticket) | Use `case` statement dispatch (current in SKILL.md and patterns.md) | Support both: `case` dispatch for simple scripts, `declare -f` for dynamically loaded command modules. Document both patterns (ref: Q9, Q10). The ticket explicitly states "Lookup via `declare -f \"cmd_${1}\"`" | No |
| **`allowed-tools` frontmatter** | Add `allowed-tools: Read` to frontmatter (like qrspi-work has) | Omit `allowed-tools` — the skill is guidance-only and doesn't invoke tools | Omit — `allowed-tools` is used by workflow-orchestrator skills that invoke APIs (Linear MCP) and need explicit tool permissions. This skill is passive guidance; no tools are invoked | No |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| The skill was built by skill-creator and may contain eval harness artifacts or scaffolding files that serve no purpose for a guidance-only skill | High | Low — extra files are harmless but add confusion. The eval workspace (`writing-bash-scripts-workspace/`) and eval files (evals.json, timing.json, grading.json) are artifacts of the skill-creator build process that are irrelevant to end users | During implementation, delete any eval harness files generated by skill-creator. Only keep SKILL.md and references/ |
| Adding conventions to SKILL.md body pushes it over 500 lines, degrading context efficiency | Medium | Medium — SKILL.md is loaded into every invocation context. Over 500 lines wastes tokens and may slow agent responses | Keep additions concise. Move any newly verbose content to reference files. The current body is 274 lines; room remains for ~100 more lines of targeted additions |
| Bash version assumption conflict: skill documents bash 3.2 as minimum but also documents bash 4+ features without clear version gating | High | Low — developers using macOS (bash 3.2) will find the gotchas.md reference. However, SKILL.md should explicitly call out bash 3.2 vs 4+ before presenting bash 4+ features | Add a "Portability" section in SKILL.md body that establishes the bash version default and cross-references gotchas.md. Document the version check pattern early |
| `command` field without slash prefix causes the skill to not be auto-triggered by agents | Medium | High — if Claude Code requires a slash prefix for global skill invocation, the skill is silently invisible | Add leading slash to `command` field during implementation. Test by checking that the skill appears in the slash command autocomplete or is triggered by the description |
| Pre-existing skill file state prevents clean implementation | Low | Medium — if the skill was already partially modified or built, changes may conflict with an existing commit/PR | Check git status before writing. If the skill directory already has uncommitted changes, note them and write conservatively (targeted edits, not full rewrites) |

---

## Open Questions

1. **Is the skill already committed?** The skill files have timestamps from May 25. Were they committed via git, or are they uncommitted changes from a skill-creator run? If already committed, this design may need to propose a diff rather than a fresh creation.

2. **What invocation format does Claude Code expect for global skills?** The writing-bash-scripts skill uses `command: writing-bash-scripts` (no slash), but all other global skills (skill-creator, mcp-builder, using-graphite-cli, workflow-creator) also lack a slash prefix. This may be intentional for global skills. The `command` field in global vs worktree-local skills may follow different conventions. (ref: Q7)

3. **Should the eval harness files created by skill-creator be retained?** The skill-creator produced an eval workspace (evaluation infrastructure) alongside the skill. Since this skill is a general-purpose guidance skill (not a workflow step), the eval harness has no clear purpose. Should it be discarded, or kept as an example of skill eval practices for future use?

4. **The ticket's "~200 line" threshold for generated scripts was not found in any existing skill or spec.** Is this a project-internal convention that the design should encode, or a question that may have referenced an external spec (agentskills.io) that does not exist? The design proposes encoding it as a soft guideline ("suggest a different language over 200 lines"), but this should be confirmed. (ref: Q10)

5. **Does the skill need a `scripts/` subdirectory?** The ticket describes building a skill following the standard pattern which includes optional `scripts/`. The current implementation has no scripts (only reference files). Is this sufficient, or should a utility script (e.g., a ShellCheck runner wrapper or template copier) be added to `scripts/`? (ref: Q4)
