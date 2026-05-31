# Structure Outline — Create a new agent skill for using the Claude CLI

**Design basis:** design.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## New Types

This ticket produces Markdown documentation artifacts, not code. The only
structured "type" is the SKILL.md YAML frontmatter, whose schema is the repo's
de facto skill dialect (ref: design.md §Decision 2, Q3):

- `SkillFrontmatter { name: string, description: string, command: string, argument-hint: string, allowed-tools: string }`
  - Invariant: `directory name` == `name` == `command` minus leading `/` (ref: design.md §Current State, Q3).
  - `name`/`command`: `using-claude-cli` / `/using-claude-cli`.
  - `allowed-tools`: minimal, likely `Read` only, using verified tool-rule syntax `Bash(<cmd>:*)` / `mcp__<server>__<tool>` where applicable (ref: design.md §Decision 2, Q13).

## Modified Types

None. No existing skill, agent, or type is modified (ref: design.md §Delta).

## Contracts

No runtime function contracts — the deliverable is documentation. The
cross-slice contracts are structural/content interfaces between artifacts:

- `SKILL.md frontmatter dialect` — the YAML schema above; every file in this skill
  references it; the naming triple must be satisfied. (Stable across all slices.)
- `references/ link contract` — SKILL.md body links/refers to each `references/*.md`
  topic file; reference filenames and topics defined in Slice 1 must match what
  the body points to. Topics: `cli-flags`, `subagents-and-teams`, `hooks`,
  `permissions-and-mcp`, `cicd-patterns` (ref: design.md §Delta).
- `Verified-CLI-facts contract` — the set of CLI flags/modes/behaviors confirmed
  against the authoritative source chosen in OQ3 (Decision 3, Option B). Both the
  SKILL.md body and every reference file may only encode facts in this set; no
  aspirational/unverified flags (ref: design.md §Decision 3, Risk Register row 1).
- `Budget contract` — SKILL.md body stays under 500 lines / 5000 tokens; anything
  exceeding the budget is pushed into `references/` (ref: design.md §Desired End State, Risk Register row 3).
- `skill-creator contract` (build-time, gated) — the skill is produced through the
  global `skill-creator` builder if reachable (OQ1); if unreachable, escalate rather
  than silently hand-author (ref: design.md §Decision section, Risk Register row 2).

## Pre-slice gate (blocking — resolve before Slice 1)

Per the design, the following Open Questions are blocking and have no code mapping
(see Unverified Assumptions). Slices below assume their resolution:

- OQ3 (authoritative CLI source) must be fixed before any CLI fact is encoded.
- OQ1 (`skill-creator` reachability) must be confirmed before authoring path is chosen.
- OQ4 (no-agent content-skill shape accepted) gates whether this structure is valid at all.

## Slice 1: Verified SKILL.md (frontmatter + body) — the complete, self-sufficient skill

**Goal:** Ship a loadable, valid `using-claude-cli` skill whose SKILL.md carries
correct frontmatter (naming triple satisfied, minimal `allowed-tools`) and a body
covering the four common patterns (headless/bare mode, subagent spawning, session
management, permission best practices) plus short orchestration examples — with
every encoded CLI fact verified against the OQ3 source and the body within budget.
This is end-to-end testable on its own: the skill loads, passes frontmatter
conventions, and stays under the line/token budget. References are stubbed as
empty-but-present files so body links resolve.
**Files touched:**

- ✨ `.claude/skills/using-claude-cli/SKILL.md` — frontmatter (skill dialect) + body: four common patterns + short orchestration examples; links to the five reference topics.
- ✨ `.claude/skills/using-claude-cli/references/cli-flags.md` — placeholder/stub (heading + scope note) so body links resolve.
- ✨ `.claude/skills/using-claude-cli/references/subagents-and-teams.md` — placeholder/stub.
- ✨ `.claude/skills/using-claude-cli/references/hooks.md` — placeholder/stub.
- ✨ `.claude/skills/using-claude-cli/references/permissions-and-mcp.md` — placeholder/stub.
- ✨ `.claude/skills/using-claude-cli/references/cicd-patterns.md` — placeholder/stub.

**Verification:**

- [ ] Frontmatter parses as valid YAML and carries `name`, `description`, `command`, `argument-hint`, `allowed-tools` (ref: Q3).
- [ ] Naming triple holds: directory `using-claude-cli` == `name:` == `command:` minus `/`.
- [ ] `allowed-tools` entries use verified syntax (`Bash(<cmd>:*)` / `mcp__<server>__<tool>` / bare names) (ref: Q13).
- [ ] SKILL.md body is < 500 lines and < 5000 tokens (measure).
- [ ] Every CLI flag/mode/behavior stated in the body exists in the OQ3-verified fact set; no unverified flags.
- [ ] Every `references/*.md` link in the body resolves to a present file.
- [ ] If reachable, the skill was produced/validated via `skill-creator` (OQ1); otherwise escalation recorded.
**Context cost:** M
**Depends on:** Pre-slice gate (OQ1, OQ3, OQ4)

## Slice 2: Reference content — fill the five advanced-topic files

**Goal:** Replace each reference stub with verified, authoritative content so the
skill fully satisfies the acceptance criteria (advanced flags, output/cost control;
subagents + custom `.claude/agents/` + `--agents` JSON + agent teams flagged
experimental + worktrees; hooks events/matchers/exit codes; permission modes +
deny→ask→allow order + settings hierarchy + MCP config; CI/CD examples). Each file
is independently verifiable against the OQ3 source and the topic scope set by the
body's links in Slice 1.
**Files touched:**

- ⚠️ `.claude/skills/using-claude-cli/references/cli-flags.md` — advanced flags, output formats, cost/resource control.
- ⚠️ `.claude/skills/using-claude-cli/references/subagents-and-teams.md` — built-in subagent types, custom `.claude/agents/`, `--agents` JSON, agent teams (experimental), worktrees.
- ⚠️ `.claude/skills/using-claude-cli/references/hooks.md` — hook events, matcher syntax, exit codes, examples.
- ⚠️ `.claude/skills/using-claude-cli/references/permissions-and-mcp.md` — permission modes, deny→ask→allow order, settings hierarchy, rule syntax, MCP config.
- ⚠️ `.claude/skills/using-claude-cli/references/cicd-patterns.md` — brief GitHub Actions / GitLab CI examples.

**Verification:**

- [ ] Each reference file's topic matches the link/scope the SKILL.md body declared in Slice 1 (link contract holds).
- [ ] Every flag/event/mode/option documented exists in the OQ3-verified fact set; experimental items explicitly labeled (e.g., agent teams).
- [ ] Tool-rule and MCP examples use verified syntax (`Bash(<cmd>:*)`, `mcp__<server>__<tool>`) (ref: Q13).
- [ ] No reference file silently echoes unverified ticket specifics (e.g., 10MB stdin cap, exact permission-mode list) unless confirmed via OQ3/OQ5.
- [ ] SKILL.md body remains within budget after references are finalized (no content leaked back into the body).
- [ ] If reachable, references validated via `skill-creator` eval loop (OQ1).
**Context cost:** M
**Depends on:** Slice 1

---

## Unverified Assumptions

These are claims/decisions from design.md that cannot be mapped to concrete code or
content until a human resolves them. They block or constrain the slices above.

- **OQ1 — `skill-creator` reachability.** The "built using the skill builder" criterion
  depends on the global `skill-creator` skill being reachable in the implementation
  session; it is not under the repo root (ref: design.md §Decision section, Q2,
  Risk Register row 2). If unreachable, whether hand-authoring is acceptable is unresolved.
  Slices reference this in their verification but cannot guarantee it.
- **OQ3 — authoritative CLI source of truth.** Decision 3 (Option B) requires verifying
  every flag/mode/behavior against an authoritative source, but which source —
  installed `claude --help` in this environment vs. a specific published docs version —
  is undecided. The entire factual content of both slices depends on this; until fixed,
  no CLI fact can be honestly encoded (ref: design.md §Decision 3, Risk Register row 1).
- **OQ5 — correct vs. echo unverified ticket specifics.** Whether to correct or repeat
  ticket details research could not verify (10MB stdin cap, exact permission-mode list)
  is unresolved and depends on OQ3. This determines specific content in Slice 1's body
  and Slice 2's `permissions-and-mcp.md` / `cli-flags.md`.
- **OQ4 — no-agent content-skill shape acceptance.** Decision 1's new pattern (a
  reference skill with no paired agent file) may conflict with the reviewer's
  thin-wrapper+agent expectation (ref: design.md §Decision 1, Risk Register row 4).
  If rejected, the entire structure (no `.claude/agents/` file) must be reworked.
- **OQ2 — optional eval case.** The design marks an eval case under `evals/` as optional
  and cosmetic because the harness produces zeros (ref: Q10, design.md §Delta "Optional").
  Not included as a slice. If a human decides to include it — and whether wiring real
  agent execution into `run_eval.py` is in scope — that becomes an additional slice not
  defined here.
