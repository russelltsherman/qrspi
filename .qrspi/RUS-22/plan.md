# Implementation Plan — Create a new agent skill for using the Gemini CLI

**Structure basis:** structure.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft
**Total steps:** 24

> Content skill — Markdown + JSON artifacts, no runtime code. "Signatures" below are the
> SKILL.md frontmatter shape, the body→reference link contract, and the eval-file schema
> (ref: structure.md §New Types / §Contracts).
>
> **Blocking inputs carried from structure.md:** OQ3 (authoritative Gemini CLI package/install
> command — Google product, NOT `@anthropic-ai/gemini-cli`), the deprecation date/details, and
> all external-CLI content facts (sandbox profiles, GEMINI.md precedence, subagent routing,
> MCP/extension config) are UNVERIFIED from the codebase and MUST be sourced from authoritative
> Gemini CLI docs at authoring time. OQ1/OQ2/OQ4/OQ5 assumptions are encoded as planned; confirm
> before implementing.

## Slice 1: Author the `using-gemini-cli` skill (body + references)

### Setup

1. ✨ Invoke the global `skill-creator` skill to scaffold `.claude/skills/using-gemini-cli/` — satisfies the "built using the skill builder" AC as an authoring-process requirement (resolves OQ1; ref: structure.md Slice 1 verification, design Decision 1A).
2. ✨ Create `.claude/skills/using-gemini-cli/SKILL.md` — write YAML frontmatter only, all five `SkillFrontmatter` fields:
   - `name: using-gemini-cli` (MUST match directory name — Frontmatter contract)
   - `description:` capability+trigger shape ("Use when…/Trigger on…")
   - `command: /using-gemini-cli`
   - `argument-hint:` and `allowed-tools:` (per in-repo five-field convention; ref: structure.md §New Types).

### Core Logic — SKILL.md body (Decision 2A: control-flow + quick reference in body; deep tables → references)

3. ⚠️ Modify `.claude/skills/using-gemini-cli/SKILL.md` — verify the authoritative Gemini CLI package name and install/invocation (OQ3, blocking) from official docs, then add the **Installation & auth** section.
   - **Current:** frontmatter only, no install section.
   - **After:** installation + auth section using the *verified* package name (do NOT encode `@anthropic-ai/gemini-cli`).
4. ⚠️ Modify `.claude/skills/using-gemini-cli/SKILL.md` — add **Invocation** section: interactive, non-interactive (`-p`), and piped/stdin modes.
   - **Current:** install/auth section present.
   - **After:** install/auth + invocation sections.
5. ⚠️ Modify `.claude/skills/using-gemini-cli/SKILL.md` — add **Permission / approval model** section (default, auto_edit, yolo) with when-to-use, including a named, prominent risk/caution block for yolo + sandbox-off (Risk-surfacing contract; Decision 3A).
   - **Current:** through invocation section.
   - **After:** + approval-model section with named risk block.
6. ⚠️ Modify `.claude/skills/using-gemini-cli/SKILL.md` — add **Sandbox** summary section (defer profile tables to `references/sandbox.md`).
   - **Current:** through approval-model section.
   - **After:** + sandbox summary section.
7. ⚠️ Modify `.claude/skills/using-gemini-cli/SKILL.md` — add **Multi-agent orchestration** section emphasizing non-interactive `-p`, stdin piping, filesystem coordination, `--sandbox`.
   - **Current:** through sandbox summary.
   - **After:** + orchestration section.
8. ⚠️ Modify `.claude/skills/using-gemini-cli/SKILL.md` — add **Workflow examples** (code review, test generation, codebase exploration), prose-only per QRSPI artifact rules.
   - **Current:** through orchestration section.
   - **After:** + workflow-examples section.
9. ⚠️ Modify `.claude/skills/using-gemini-cli/SKILL.md` — add the dated, named **Deprecation / Antigravity** caveat block (Decision 4A); confirm date/details at authoring time (today is 2026-05-31).
   - **Current:** through workflow examples.
   - **After:** + dated deprecation block.
10. ⚠️ Modify `.claude/skills/using-gemini-cli/SKILL.md` — add the **References** links section linking all four `references/` files (Body→reference link contract).
    - **Current:** through deprecation block, no reference links.
    - **After:** body links to `sandbox.md`, `configuration.md`, `subagents.md`, `mcp-and-extensions.md`.

### References (the four-file split; resolves OQ2)

11. ✨ Create `.claude/skills/using-gemini-cli/references/sandbox.md` — sandbox profiles + when to enable each (sourced from authoritative docs).
12. ✨ Create `.claude/skills/using-gemini-cli/references/configuration.md` — GEMINI.md context hierarchy + settings precedence + best practices.
13. ✨ Create `.claude/skills/using-gemini-cli/references/subagents.md` — subagent definition, routing, tool grants.
14. ✨ Create `.claude/skills/using-gemini-cli/references/mcp-and-extensions.md` — MCP server config + extension installation.

### Budget & link audit

15. ⚠️ Modify `.claude/skills/using-gemini-cli/SKILL.md` — trim/relocate body content to satisfy the Budget contract (≤ 500 lines / 5000 tokens); push overflow into the matching `references/` file.
    - **Current:** full body, possibly over budget.
    - **After:** body ≤ 500 lines / 5000 tokens.
16. Audit the Body→reference link contract: every reference file named in the body exists, and every reference file is linked from the body.
    - **Expected:** bidirectional link/file parity holds.

### Tests

17. Run the `skill-creator` eval loop against `.claude/skills/using-gemini-cli/` as the final authoring validation step (resolves OQ1 as a process requirement).
    - **Expected:** skill-creator eval loop passes.

### Verify Slice 1

18. **Checkpoint:** `test -f .claude/skills/using-gemini-cli/SKILL.md && ls .claude/skills/using-gemini-cli/references/ && wc -l .claude/skills/using-gemini-cli/SKILL.md`
    - [ ] Frontmatter contains all five fields; `name: using-gemini-cli` matches the directory name.
    - [ ] Body ≤ 500 lines / 5000 tokens (Decision 2).
    - [ ] All four reference files exist; every reference named in the body exists and every reference file is linked from the body.
    - [ ] Named risk block (yolo / sandbox-off) and dated deprecation block are present and prominent.
    - [ ] Install command uses the *verified* Gemini CLI package name, not `@anthropic-ai/gemini-cli`.
    - [ ] `skill-creator` eval loop passed.

---

## Slice 2: Eval fixtures for command/flag/safety guidance

> **Scope-gated by OQ4** — drop this slice entirely if the eval file is deferred until harness
> stubs exist. Depends on Slice 1 (assertions reference documented commands/flags/modes).

### Setup

19. ✨ Create `evals/gemini-cli-evals.json` — top-level `EvalFile` shape: `skill_name: "using-gemini-cli"` and an empty `evals: []` array, mirroring `graphite-evals.json` (Eval-file schema contract).

### Core Logic — populate assertions (each references guidance authored in Slice 1)

20. ⚠️ Modify `evals/gemini-cli-evals.json` — add ≥1 `command_check` EvalCase referencing a command documented in Slice 1's SKILL.md.
    - **Current:** `evals: []`.
    - **After:** `evals[]` contains a `command_check` case.
21. ⚠️ Modify `evals/gemini-cli-evals.json` — add ≥1 `flag_check` EvalCase referencing a flag documented in Slice 1 (e.g., `-p`, `--sandbox`).
    - **Current:** command_check only.
    - **After:** + flag_check case.
22. ⚠️ Modify `evals/gemini-cli-evals.json` — add ≥1 `safety_check` EvalCase referencing the yolo / sandbox-off destructive modes documented in Slice 1.
    - **Current:** command_check + flag_check.
    - **After:** + safety_check case.

### Tests

23. Run: `python -c "import json; json.load(open('evals/gemini-cli-evals.json'))"`
    - **Expected:** valid JSON; no parse error.

### Verify Slice 2

24. **Checkpoint:** `python -m json.tool evals/gemini-cli-evals.json >/dev/null && echo OK`
    - [ ] File is valid JSON conforming to the `graphite-evals.json` shape (`skill_name`, `evals[]`).
    - [ ] Includes at least one each of `command_check`, `flag_check`, and `safety_check`.
    - [ ] Assertions reference commands/flags/safety modes actually documented in Slice 1's SKILL.md.
    - [ ] (Accepted) Scoring returns zero until harness stubs are implemented (ref: design Q10) — verification is schema/content correctness by review, not a passing score.

---

## Rollback Notes

- **Slice 1 (steps 1–17):** the skill is additive (new directory + files only; no existing types or schemas modified per structure.md §Modified Types). To reverse: `rm -rf .claude/skills/using-gemini-cli/`. No migrations, no config edits, no destructive ops.
- **Step 9 (deprecation block):** time-sensitive — if the June 2026 date has passed at merge, re-confirm and re-date the block rather than rolling back.
- **Slice 2 (steps 19–22):** additive new file only. To reverse: `rm evals/gemini-cli-evals.json`. Removing it does not affect harness execution (it currently scores zero; ref: design Q10).
- **OQ5 note-only:** the `.claude/CLAUDE.md` agents-path inconsistency is out of scope — no step touches it, so no rollback applies.
