# Structure Outline — Create a new agent skill for using the Gemini CLI

**Design basis:** design.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

> Note: This ticket produces a **content skill** (Markdown + JSON artifacts), not application code.
> There are no runtime types or function signatures. The sections below adapt "Types" and
> "Contracts" to the artifact schemas that govern this work: the SKILL.md frontmatter shape,
> the body→reference link contract, and the eval-file schema. These are the binding interfaces
> a planner/implementer must honor.

## New Types

- `SkillFrontmatter { name: string, description: string, command: string, argument-hint: string, allowed-tools: string }`
  — the five-field YAML frontmatter convention every in-repo `SKILL.md` uses (ref: design §Current State / Q3).
  For this skill: `name: using-gemini-cli`, `description:` capability+trigger shape, `command: /using-gemini-cli`,
  plus `argument-hint` and `allowed-tools`.
- `ReferenceFileSet = { "sandbox.md", "configuration.md", "subagents.md", "mcp-and-extensions.md" }`
  — the four-file split under `references/`, resolving OQ2 to the four-file option from the design Delta.
- `EvalFile { skill_name: string, evals: EvalCase[] }` and
  `EvalCase { assertion_type: "command_check" | "flag_check" | "safety_check" | "content_check" | "workflow_check", ... }`
  — mirrors the `graphite-evals.json` shape (ref: design §Delta / Q5, Q11).

## Modified Types

- None. No existing types or schemas are modified. (`.claude/CLAUDE.md` agents-path inconsistency is noted out-of-scope per OQ5; ref: design §Delta.)

## Contracts

- **Frontmatter contract** — `SKILL.md` MUST carry all five `SkillFrontmatter` fields with `name` matching the directory name `using-gemini-cli` (ref: design §Current State / Q1, Q3).
- **Body→reference link contract** — every `references/<file>.md` named in the body MUST exist, and every reference file MUST be linked from the body. Body holds control-flow + quick reference; deep tables live in `references/` (Decision 2; ref: Q5, Q6).
- **Budget contract** — `SKILL.md` body ≤ 500 lines / 5000 tokens; overflow material moves to `references/` (Decision 2; ref: Q6).
- **Risk-surfacing contract** — destructive modes (yolo, sandbox-off) and the deprecation timeline appear as named, prominent blocks in the body, not buried footnotes (Decisions 3A, 4A; ref: Q8).
- **Eval-file schema contract** — `evals/gemini-cli-evals.json` MUST be valid JSON conforming to the `graphite-evals.json` shape and include `command_check`, `flag_check`, and `safety_check` assertions (Decision 3B; ref: Q5, Q11). Scoring will not run until harness stubs exist (ref: Q10).

## Slice 1: Author the `using-gemini-cli` skill (body + references)

**Goal:** A complete, self-contained skill exists at `.claude/skills/using-gemini-cli/` — body plus all four reference files — authored via the global `skill-creator` skill and passing its eval loop. This is one cohesive unit: the body links into the references and cannot be meaningfully verified without them (Decision 1A, Decision 2A).
**Files touched:**

- ✨ `.claude/skills/using-gemini-cli/SKILL.md` — frontmatter (five fields) + body: installation/auth/invocation (interactive/non-interactive/piped), permission/approval model (default/auto_edit/yolo) with named risk block, sandbox summary, multi-agent orchestration patterns (non-interactive `-p`, stdin piping, filesystem coordination, `--sandbox`), prose-only workflow examples (code review, test gen, codebase exploration), dated deprecation/Antigravity caveat block, and links into `references/`.
- ✨ `.claude/skills/using-gemini-cli/references/sandbox.md` — sandbox profiles + when to enable.
- ✨ `.claude/skills/using-gemini-cli/references/configuration.md` — GEMINI.md context hierarchy + settings precedence + best practices.
- ✨ `.claude/skills/using-gemini-cli/references/subagents.md` — subagent definition, routing, tool grants.
- ✨ `.claude/skills/using-gemini-cli/references/mcp-and-extensions.md` — MCP server config + extension installation.

**Verification:**
- [ ] Frontmatter contains all five fields; `name: using-gemini-cli` matches the directory name.
- [ ] Body ≤ 500 lines / 5000 tokens (Decision 2).
- [ ] Every reference file named in the body exists, and every reference file is linked from the body (link contract).
- [ ] Named risk block (yolo/sandbox-off) and dated deprecation block are present and prominent.
- [ ] Skill authored through `skill-creator`; its eval loop passes as the final validation step of this slice (resolves OQ1 as an authoring-process requirement).

**Context cost:** L
**Depends on:** none

## Slice 2: Eval fixtures for command/flag/safety guidance

**Goal:** `evals/gemini-cli-evals.json` validates the skill's command, flag, and safety guidance, mirroring the Graphite eval shape. Independently verifiable as a JSON-schema-conforming artifact — a genuine testability boundary distinct from the skill content (Decision 3B).
**Files touched:**

- ✨ `evals/gemini-cli-evals.json` — `skill_name: using-gemini-cli` + `evals[]` with `command_check` / `flag_check` / `safety_check` assertions referencing the guidance authored in Slice 1.

**Verification:**
- [ ] File is valid JSON and conforms to the `graphite-evals.json` shape (`skill_name`, `evals[]`).
- [ ] Includes at least one each of `command_check`, `flag_check`, and `safety_check`.
- [ ] Assertions reference commands/flags/safety modes actually documented in Slice 1's SKILL.md.
- [ ] (Accepted) Scoring returns zero until harness stubs are implemented (ref: Q10) — verification is schema/content correctness by review, not a passing score.

**Context cost:** S
**Depends on:** Slice 1 (assertions reference the documented commands/flags/modes). **Scope-gated by OQ4** — drop this slice if the eval file is deferred until harness stubs exist.

---

## Unverified Assumptions

- **OQ3 (blocking) — install command / package name.** The ticket's `npm install -g @anthropic-ai/gemini-cli` misattributes Gemini CLI (a Google product) to Anthropic. The authoritative package name and invocation are unverified and CANNOT be encoded until confirmed at authoring time. This blocks the installation section of Slice 1's SKILL.md. (ref: design §Risk Register, OQ3)
- **Deprecation timeline details.** The "June 2026 / Antigravity" deprecation note has no in-repo precedent format (Decision 4 introduces a new pattern) and the date/details are unverified — today is 2026-05-31, so the date may pass before merge. Content must be confirmed and dated at authoring time. (ref: Decision 4, Risk Register)
- **OQ1 — skill-creator as process vs. artifact.** Assumed: "built using the skill builder" is an authoring-process requirement (invoke `skill-creator` during creation), not an in-repo artifact to produce. The `skill-creator` skill is global/out-of-repo and NOT FOUND in-repo (ref: Q2). Slice 1 verification encodes this assumption; confirm before planning.
- **OQ2 — reference file boundaries.** Resolved here to the four-file split (`sandbox.md`, `configuration.md`, `subagents.md`, `mcp-and-extensions.md`). This is a structure-phase decision, not a verified fact; a single combined reference remains a valid alternative.
- **OQ4 — eval file scope.** Slice 2 is gated on whether `evals/gemini-cli-evals.json` is in scope given the harness cannot score it (ref: Q10). Confirm in/out before planning.
- **OQ5 — CLAUDE.md agents-path fix.** Treated as out of scope (note-only). The `.claude/CLAUDE.md` misstatement of the agents path (`.qrspi/agents/` vs `.claude/agents/`) is NOT addressed by any slice. Confirm it stays out of scope.
- **Content correctness of all reference material.** Sandbox profiles, GEMINI.md precedence, subagent routing, and MCP/extension config describe an external CLI not represented in-repo (ref: Q5 — no in-repo external-CLI skill precedent). These facts are unverifiable from the codebase and must be sourced from authoritative Gemini CLI documentation at authoring time.
