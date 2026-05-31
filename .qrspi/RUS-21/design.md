# Design — Create a new agent skill: using-codex-cli

**Ticket:** RUS-21
**Research basis:** research.md @ 2026-05-31T17:05:00Z
**Generated:** 2026-05-31T17:08:00Z
**Status:** draft

## Current State

- The repo holds 10 skills under `.claude/skills/<name>/SKILL.md`, all QRSPI workflow skills (ref: Q1). There is no `using-codex-cli` skill today.
- The minimal skill layout is `<name>/SKILL.md`; only `qrspi-work` uses a `references/` subdirectory, and no skill uses `scripts/` or `assets/` (ref: Q1).
- SKILL.md frontmatter is YAML with `name`, `description`, `command`, `argument-hint`, `allowed-tools` (ref: Q3). Directory name equals the `name` field, kebab-case (ref: Q5).
- Descriptions are written as "what it does + when to use it," often enumerating trigger phrases for auto-invocation (ref: Q6).
- Conditional/deep material is pushed into `references/<topic>.md` and linked by relative path from the body; the body holds the common path (ref: Q2, Q8).
- There is **no** in-repo Anthropic skill-builder/skill-creator skill, and **no** captured agentskills.io standard document (ref: Q4, Q9). The de-facto standard is the existing SKILL.md shape.
- There is **no** automated linter for SKILL.md size or frontmatter validity; the `evals/` harness only tests QRSPI workflow phase agents (ref: Q7, Q10). Verification for a content skill is structural/manual (ref: Q11).
- Skills are auto-discovered from `.claude/skills/`; there is no manifest/registry to edit. README and `.claude/CLAUDE.md` skill lists are documentation, not load-bearing (ref: Q12).
- The repo separates skills (slash-command entry points) from agents (`.claude/agents/`, spawned workers); a standalone content skill needs no paired agent (ref: Discovered Patterns).

## Desired End State

A new skill `using-codex-cli` exists at `.claude/skills/using-codex-cli/SKILL.md`, auto-discoverable by the harness, that guides an agent in using the OpenAI Codex CLI. Mapping each acceptance criterion to concrete behavior:

- **agentskills.io directory structure + valid frontmatter** → `.claude/skills/using-codex-cli/SKILL.md` with YAML frontmatter matching the in-repo shape (ref: Q3) plus `references/` for depth.
- **Built using the skill builder skill** → Authored to the SKILL.md contract (ref: Q9). The in-repo builder is absent; if a harness-provided skill-creator is available it is used, otherwise the deliverable conforms to the same output contract. (Recorded as Open Question OQ1.)
- **Body under 500 lines / 5000 tokens** → SKILL.md body kept lean; overflow tables (sandbox matrix, config reference, CI patterns) live in `references/` (ref: Q2, Q7, Q8).
- **Reference material in references/** → `references/` directory with topic files for sandbox/approval detail, config.toml, automation, and multi-agent patterns.
- **All three approval modes with when-to-use guidance** → a body section "Approval Modes" with a decision rule and a deeper reference.
- **Sandbox modes + platform enforcement** → a body section "Sandbox Modes" stating the default-restrictive rule; macOS Seatbelt / Linux Bubblewrap+Landlock detail in a reference (ref: Q8).
- **codex exec patterns for non-interactive/CI** → a body section + `references/automation.md`.
- **AGENTS.md hierarchy + custom instructions authoring** → a body section + reference covering discovery order, precedence, size cap, override file.
- **MCP server exposure + multi-agent orchestration** → a body section + `references/multi-agent.md`.
- **config.toml reference with profiles** → `references/config.md`.
- **Known limitations + workarounds** → a body "Limitations & Pitfalls" section.
- **Unix pipe composition examples with codex exec** → inline examples in the automation section.
- **Tests** (user directive) → a structural verification script `references/` or `scripts/`-style checklist asserting frontmatter validity, body size, and presence of required sections.

## Delta

New files (all under `.claude/skills/using-codex-cli/`):

- ✨ `SKILL.md` — frontmatter (`name: using-codex-cli`, `description` with trigger phrases per Q6, `command: /using-codex-cli`, `argument-hint`, `allowed-tools`) + lean body with sections: Overview, Approval Modes, Sandbox Modes, AGENTS.md, Configuration, Session Management, Non-Interactive Automation (codex exec), Multi-Agent Integration, Limitations & Pitfalls, Quick Decision Rules. Body links to references for depth.
- ✨ `references/sandbox-and-approvals.md` — full approval×sandbox matrix, macOS Seatbelt vs Linux Bubblewrap+Landlock enforcement detail, network-access gotchas.
- ✨ `references/config.md` — config.toml sections, profiles, `model_instructions_file`, feature flags, project-root detection, user vs project config precedence.
- ✨ `references/agents-md.md` — AGENTS.md / AGENTS.override.md discovery order, concatenation/precedence, 32 KiB cap, fallback filenames, nested rules.
- ✨ `references/automation.md` — `codex exec` input patterns, `--json`/`--quiet`, hermetic-CI flags, Unix pipe composition, `CODEX_API_KEY`.
- ✨ `references/multi-agent.md` — MCP server mode (`codex()`/`codex-reply()` tools), Agents SDK pipelines, subagents, git-worktree parallelism, custom agent definitions.
- ✨ a verification check (script or documented checklist) asserting: frontmatter parses, required keys present, body ≤ 500 lines, each required section header present, referenced files exist.

Documentation touch (optional, non-load-bearing):

- ⚠️ `.claude/CLAUDE.md` and/or `README.md` skill list — add a one-line entry for discoverability (ref: Q12). Not required for registration.

No code modules, types, or eval-suite changes are required (ref: Q7, Q10).

## Pattern Decisions

### Decision 1: Body-vs-references split

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Put everything (all modes, full matrices, config, CI) inline in SKILL.md | Single file; nothing to cross-link | Body blows past the 500-line/5000-token budget; violates AC (ref: Q7) |
| B | Lean body with decision rules + per-topic `references/` files linked by relative path | Meets size budget; follows the one in-repo precedent (qrspi-work → references) (ref: Q2, Q8); references load on demand | More files; body must correctly name each reference path |

**Recommendation:** Option B
**Rationale:** The only in-repo precedent for conditional/deep material is `qrspi-work/SKILL.md:273` linking `references/review-cascade.md` (ref: Q2, Q8). The ticket's own acceptance criteria pair a ≤500-line body with "detailed reference material in references/." Option B is the only one that satisfies both.
**NEW PATTERN?** No — it reuses the existing references mechanism.

### Decision 2: Skill name and command

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | `name: using-codex-cli`, dir `using-codex-cli`, `command: /using-codex-cli` | Matches dir==name kebab-case convention (ref: Q5); `using-` prefix matches sibling external skills like `using-graphite-cli` | none material |
| B | `name: codex-cli` | shorter | Breaks the ticket's stated name and the `using-` convention for tool-usage skills |

**Recommendation:** Option A
**Rationale:** Directory name must equal frontmatter `name`, kebab-case (ref: Q5); the ticket titles the skill "using codex cli."
**NEW PATTERN?** No.

### Decision 3: How to satisfy "built using the skill builder skill"

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Author directly to the in-repo SKILL.md contract (ref: Q3, Q9) | Works regardless of builder availability; deterministic | Does not literally invoke an external tool |
| B | Hard-require invoking an external skill-builder skill | Literal AC compliance | The builder skill is not in the repo (ref: Q9); availability is environment-dependent and unverifiable from the repo |

**Recommendation:** Option A, and invoke a harness-provided skill-creator if (and only if) it is available at implementation time.
**Rationale:** Q9 establishes the builder is absent from the repo. The binding contract is a valid in-repo SKILL.md. The implementer should use the skill-creator skill when present (it is listed among environment skills) but must not block on it. Flagged as OQ1.
**NEW PATTERN?** No.

### Decision 4: Verification approach

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | A small validation script (e.g. python under the skill's own dir or repo `scripts/`) that parses frontmatter, counts body lines, and asserts required section headers + reference-link existence | Automatable; satisfies the user's "tests required" directive; mirrors the repo's python eval tooling style (ref: Q7, Q10, Q11) | One more file to maintain |
| B | A manual checklist in the artifact only | Zero code | No executable test; weaker against the TDD directive |

**Recommendation:** Option A
**Rationale:** No linter exists (ref: Q7); verification is structural (ref: Q11); the user requires tests. A focused validation script is the smallest executable guardrail and matches the repo's python tooling idiom.
**NEW PATTERN?** Yes — minor: a per-skill structural validator. Justified because no existing tool validates arbitrary SKILL.md (ref: Q7), and the TDD directive requires an executable check.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Body exceeds 500 lines / 5000 tokens | med | med | Enforce Option B split; validation script counts body lines and fails over budget |
| Codex CLI facts drift from upstream (flags/modes change) | med | med | Source all behavioral claims from the ticket's documented conventions; mark version-sensitive items; keep them in references for easy update |
| "Skill builder skill" AC unmet because tool absent (ref: Q9) | high | low | Author to SKILL.md contract; invoke skill-creator if present; record decision in OQ1 |
| macOS `network_access=true` silently ignored (ticket-noted pitfall) | low | med | Document the pitfall and the `--sandbox` CLI override in references; recommend verifying with the flag |
| Reviewer expects README/CLAUDE.md registry update | low | low | Add an optional one-line doc entry (ref: Q12); note it is not load-bearing |
| Re-running Codex reintroduces bugs (ticket-noted) | n/a (guidance content) | low | Encode "use unit tests as guardrails" guidance in the Limitations section |

## Open Questions

- OQ1: Is a harness-provided Anthropic skill-creator/skill-builder skill available at implementation time, and is using it a hard gate for this ticket, or is conformance to the in-repo SKILL.md contract sufficient? (Repo has no such skill — ref: Q9. Default: author to contract, use skill-creator if present.)
- OQ2: Should the skill's discoverability entry be added to `README.md` and `.claude/CLAUDE.md` skill lists, or left to harness auto-discovery only? (Auto-discovery is sufficient for registration — ref: Q12. Default: add a short doc entry for human discoverability.)
- OQ3: Is `scripts/` (per agentskills.io) acceptable inside the skill dir for the validation script, given no in-repo skill currently uses a `scripts/` subdirectory (ref: Q1)? Default: place the validator where it is runnable and reference it from verification, preferring the skill's own dir to keep the skill self-contained.
