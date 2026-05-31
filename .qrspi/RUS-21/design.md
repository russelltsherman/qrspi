# Design — Create a new agent skill using Codex CLI

**Ticket:** RUS-21
**Research basis:** research.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## Current State

This repo's skills live under `.claude/skills/<skill-name>/`, one directory per skill, each containing a `SKILL.md`; there are 10 skills, all `qrspi-*` workflow phases (ref: Q1). Only one skill (`qrspi-work`) uses a `references/` subdirectory, and no skill uses `scripts/` or `assets/` — those agentskills.io directory conventions are not present in-repo (ref: Q1). The skill directory name equals its `name:` frontmatter value equals its `/command` (a three-way identity), and all names are lowercase hyphen-separated slugs (ref: Q4).

The observed `SKILL.md` frontmatter contract across all 10 skills is five fields: `name`, `description`, `command`, `argument-hint`, `allowed-tools`; no agentskills.io standard is referenced anywhere in-repo (`grep "agentskills"` returns zero hits) (ref: Q3). `description` may be a bare scalar or a quoted string when it contains commas/colons/parens, and `allowed-tools` is a comma-separated list that may be parameter-scoped (ref: Q3).

There is **no `skill-creator` skill, no agentskills.io schema, and no skill-authoring or skill-eval tooling inside the repo** — the `skill-creator` referenced in project context is a global Claude Code skill living outside `REPO_ROOT`, which the research firewall forbids reading (ref: Q2, Q5). The in-repo eval harness (`evals/`, `scripts/`) grades **QRSPI phase artifacts**, not generated skills, and its `execute_single` runner plus `llm_judge`/`script` graders are stubs not wired to a real runtime (ref: Q10).

The 500-line / 5000-token `SKILL.md` size guidance exists only as advisory prose in `docs/qrspi_claude_code_guide.md:592` and is unenforced — `qrspi-work/SKILL.md` is 791 lines, violating it (ref: Q6). Content offloading to `references/` is an observed practice in exactly one skill: `qrspi-work` keeps its state machine in the body and offloads one self-contained decision topic (review-cascade rules, 64 lines) to a reference loaded on-demand via an explicit `Read references/<file>.md` instruction tied to a narrow execution path (ref: Q7).

No in-repo skill documents an external CLI as its subject, but `qrspi-work` heavily encodes Graphite (`gt`) and GitHub (`gh`) CLI conventions: tool knowledge is grouped into dedicated trailing sections with fenced `bash` blocks, imperative rule lists, "never do X" hazard callouts, named recovery procedures, and mandatory non-interactive flags — the closest in-repo precedent for a CLI-wrapping skill (ref: Q8). No skill, agent, template, or doc documents macOS-vs-Linux or any OS-conditional behavior, and no authoring guideline for it exists in-repo (ref: Q9). The repo is implicitly Linux-oriented (devcontainer, bash + `python3` tooling) (ref: Q9).

## Desired End State

A new self-contained skill ships under `.claude/skills/`, documenting OpenAI Codex CLI usage. Each acceptance criterion maps to concrete behavior:

- **agentskills.io directory structure + valid `SKILL.md` frontmatter** → a new directory `.claude/skills/<name>/SKILL.md` whose frontmatter follows the in-repo five-field contract (`name`, `description`, `command`, `argument-hint`, `allowed-tools`), with `name` matching the directory (ref: Q3, Q4). The agentskills.io standard is not in-repo, so we conform to the *observed* Claude Code frontmatter shape, which is the only verifiable standard here.
- **Built using the Anthropic skill builder skill** → the global `skill-creator` skill (out of repo, ref: Q2) is invoked during implementation; this is an Open Question because it cannot be exercised or verified from within the research firewall.
- **SKILL.md body under 500 lines / 5000 tokens** → body kept within the advisory ceiling (ref: Q6); since no tooling enforces this, it is a hand-checked constraint via `wc -l` and token estimate.
- **Detailed reference material in `references/`** → a sibling `references/` directory holding the long-form material (sandbox/platform enforcement, config.toml schema, multi-agent patterns), loaded on-demand per the `qrspi-work` precedent (ref: Q7).
- **All three approval modes with selection guidance** → a body section covering suggest / auto-edit / full-auto with a context-to-mode decision table (ref: Q8 structuring precedent).
- **Sandbox modes + platform-specific enforcement** → a reference file covering read-only / workspace-write / danger-full-access plus macOS Seatbelt and Linux Bubblewrap+Landlock; this introduces OS-conditional documentation, which has no in-repo precedent (ref: Q9 — NEW PATTERN).
- **`codex exec` non-interactive/CI patterns** → a section with the three input patterns (positional, stdin `-`, prompt-plus-stdin), `--json`/`--quiet` flags, and hermetic-run flags, modeled on `qrspi-work`'s fenced `bash` command blocks (ref: Q8).
- **AGENTS.md hierarchy + authoring** → a section on `AGENTS.override.md`/`AGENTS.md` discovery, concatenation precedence, size cap, and nested-directory rules.
- **MCP server exposure + multi-agent orchestration** → a reference file on MCP server mode, Agents SDK pipelines, subagents, and worktree parallelism.
- **config.toml reference with profiles** → a reference file documenting `~/.codex/config.toml` vs `.codex/config.toml`, key sections, `[profiles.<name>]`, and `model_instructions_file`.
- **Known limitations + workarounds** → a body section on re-run nondeterminism, the macOS `network_access` Seatbelt bug, context-window pressure, and the `--sandbox` override verification.
- **Unix pipe composition examples** → fenced `bash` examples (`command | codex exec "prompt"`, chaining via stdout), per the `qrspi-work` example-block convention (ref: Q8).

## Delta

**New directory:** `.claude/skills/<name>/` (name decided in Open Questions; candidate `codex-cli`).

**New files:**
- `.claude/skills/<name>/SKILL.md` — frontmatter (5 fields) + body: overview, approval-mode selection table, `codex exec` patterns, AGENTS.md authoring, limitations/workarounds, pipe examples; with explicit on-demand `Read references/<file>.md` pointers (ref: Q7). Target under 500 lines (ref: Q6).
- `.claude/skills/<name>/references/sandbox-and-platform.md` — sandbox modes + macOS/Linux enforcement.
- `.claude/skills/<name>/references/config-toml.md` — config schema, profiles, feature flags, project-root detection.
- `.claude/skills/<name>/references/multi-agent.md` — MCP server mode, Agents SDK, subagents, worktree parallelism.

**Not in scope (no change):** the eval harness (`evals/`, `scripts/`) is not modified — it grades QRSPI artifacts and is stubbed; wiring a skill-eval suite for this skill is deferred (ref: Q5, Q6, Q10). No new fixtures or golden outputs (ref: Q11).

## Pattern Decisions

### Decision 1: Skill structure — self-contained vs. thin-wrapper+agent

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Self-contained `SKILL.md` body + `references/` | Matches a documentation skill (no agent to spawn); follows `qrspi-ticket` (119 lines, no agent) and `qrspi-work` reference split | Body must stay disciplined under 500 lines |
| B | Thin wrapper + `.claude/agents/<name>.md` prompt body | Matches the dominant 9-of-10 QRSPI pattern | The wrapper/agent split exists to spawn a phase agent for *work*; this skill is reference guidance, not an orchestrated task — agent indirection adds no value |

**Recommendation:** Option A
**Rationale:** The QRSPI thin-wrapper pattern spawns an agent to *perform* a phase (ref: Discovered Patterns). This skill encodes operational knowledge for an agent to consult, matching the `qrspi-work` CLI-convention sections (ref: Q8) and the `qrspi-ticket` self-contained precedent (ref: Q1, Discovered Patterns). The `references/` split for long-form topics directly follows `qrspi-work` (ref: Q7).
**NEW PATTERN?** No — composes two existing in-repo patterns (self-contained skill + on-demand references).

### Decision 2: Frontmatter shape (agentskills.io vs. observed in-repo)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Use observed in-repo 5-field shape (`name`, `description`, `command`, `argument-hint`, `allowed-tools`) | Verified against all 10 skills; loads in this Claude Code install (ref: Q3) | May diverge from the agentskills.io spec the ticket cites |
| B | Use agentskills.io spec fields verbatim | Matches ticket wording literally | No in-repo evidence of those fields; risks a frontmatter the loader rejects (ref: Q3) |

**Recommendation:** Option A
**Rationale:** No agentskills.io schema exists in-repo and the firewall blocks reading external standards (ref: Q2, Q3). The only verifiable, loader-compatible contract is the observed 5-field shape. The `name` must equal the directory (ref: Q4).
**NEW PATTERN?** No — reuses the established frontmatter contract.

### Decision 3: Where platform-specific (macOS/Linux) sandbox detail lives

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | OS-conditional detail in `references/sandbox-and-platform.md`, loaded on-demand | Keeps body lean; isolates the only OS-conditional content; on-demand load matches `qrspi-work` (ref: Q7) | Introduces OS-conditional docs with no in-repo precedent (ref: Q9) |
| B | Inline macOS/Linux detail in `SKILL.md` body | Single file | Bloats body toward the 500-line ceiling; mixes always-loaded guidance with rarely-needed enforcement internals (ref: Q6, Q7) |

**Recommendation:** Option A
**Rationale:** Platform enforcement (Seatbelt vs. Bubblewrap+Landlock) is consulted only when configuring sandboxing — exactly the "self-contained sub-topic needed in a narrow path" heuristic for offloading (ref: Q7). No in-repo convention dictates how to document OS branches (ref: Q9), so this is the first such case.
**NEW PATTERN?** Yes — OS-conditional documentation within a single skill has no in-repo precedent (ref: Q9). Justified because the subject CLI genuinely behaves differently per OS; existing patterns cover *where* to put it (references/) but not *how* to express OS branches.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| "Built using skill-creator" cannot be verified — the skill is out of repo and unreadable under the firewall (ref: Q2) | high | med | Surface as Open Question; implementer invokes the global skill-creator and records that it was used; reviewer accepts process attestation, not in-repo proof |
| 500-line / 5000-token ceiling unenforced by any tooling; easy to overshoot like `qrspi-work` at 791 lines (ref: Q6) | med | med | Aggressively offload to `references/`; hand-check `wc -l` and a token estimate before completion |
| Frontmatter divergence — agentskills.io fields cited by ticket may not match the loader's accepted shape (ref: Q3) | med | high | Use the verified in-repo 5-field shape (Decision 2); confirm `name` equals directory name (ref: Q4) |
| OS-conditional sandbox docs (NEW PATTERN) have no precedent and could be structured inconsistently (ref: Q9) | med | low | Mirror `qrspi-work`'s rule-list + fenced-block + hazard-callout structure (ref: Q8); group all OS branches in one reference file |
| No skill-eval coverage — harness grades QRSPI artifacts only and is stubbed (ref: Q5, Q10) | med | low | Manual review against acceptance criteria; defer building a Codex-specific eval suite as a separate task |

## Open Questions

- OQ1: Final skill name and whether to carry a `qrspi-` prefix — all 10 existing skills are `qrspi-`-prefixed as a domain marker, but this skill is not a QRSPI phase; research could not derive the canonical name from convention (ref: Q4). Candidate: `codex-cli`.
- OQ2: How should "built using the Anthropic skill builder / skill-creator skill" be satisfied and evidenced, given that skill is out of repo and unreadable under the research firewall (ref: Q2, Q5)? Does invoking it during implementation suffice, and what attestation does the reviewer expect?
- OQ3: Should a Codex-specific eval suite (a third suite alongside `suite.json` and `graphite-evals.json`, per the two-suite precedent in Discovered Patterns) be created now, or deferred — given the harness runner and graders are currently stubs (ref: Q10)?
- OQ4: The ticket cites the agentskills.io frontmatter standard, but no such schema exists in-repo (ref: Q3). Confirm that conforming to the observed Claude Code 5-field frontmatter (Decision 2) satisfies the acceptance criterion, or supply the exact agentskills.io field list.
