# PR: RUS-21 Add using-codex-cli agent skill

**Ticket:** RUS-21
**Design:** design.md @ 2026-06-02T00:00:00Z
**Structure:** structure.md @ 2026-06-06T00:00:00Z

## Summary

Adds a new standalone knowledge skill at `.claude/skills/using-codex-cli/` that
teaches agents how to operate the Codex CLI: approval modes, sandbox modes and
platform enforcement, `codex exec` automation, AGENTS.md hierarchy, MCP server
mode, `config.toml` reference, and known limitations. The skill follows the
agentskills.io layout — a `SKILL.md` body (191 lines, ~2267 tokens, under the
500-line / 5000-token limit) plus four focused `references/` deep-dives that the
body cross-links. Implemented as a single vertical slice; greenfield, no existing
files modified. **Reviewer focus:** (1) factual accuracy of the Codex CLI claims
(UA-9) — they were encoded from the ticket without live Codex docs and carry
explicit hedging; (2) confirmation that the deterministic contract checks
(frontmatter, length, links, coverage) are sufficient given the skill-creator
*eval loop* could not run non-interactively.

## Acceptance Criteria Mapping

These 11 criteria come from design.md §Desired End State item 2. This is a
documentation/skill-authoring ticket, so "Test" refers to the deterministic
contract checkpoints recorded in impl-log.md (T17/T18) rather than code tests.

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: Valid agentskills.io frontmatter | `SKILL.md` frontmatter (`name: using-codex-cli`, `description`) | frontmatter-contract checkpoint (T17) → PASS |
| AC2: Built via Anthropic skill builder | authored to `skill-creator` conventions | skill-creator-validation-contract — partial (see Open Items) |
| AC3: Body < 500 lines / 5000 tokens | `SKILL.md` body (191 lines, ~2267 tokens) | body-length-contract checkpoint (T17) → PASS |
| AC4: All three approval modes with guidance | `SKILL.md` approval-modes section (decision matrix) | acceptance-coverage-contract checkpoint (T18) → PASS |
| AC5: Sandbox modes + platform enforcement | `SKILL.md` sandbox-modes section (Seatbelt / Landlock+bubblewrap) | acceptance-coverage-contract (T18) → PASS |
| AC6: `codex exec` automation patterns | `references/codex-exec-patterns.md` | acceptance-coverage-contract (T18) → PASS |
| AC7: AGENTS.md hierarchy + custom instructions | `SKILL.md` AGENTS.md section (override-first cascade, 32 KiB) | acceptance-coverage-contract (T18) → PASS |
| AC8: MCP server exposure + multi-agent orchestration | `references/mcp-server-mode.md` (`codex()`/`codex-reply()`) | acceptance-coverage-contract (T18) → PASS |
| AC9: config.toml reference | `references/config-reference.md` | acceptance-coverage-contract (T18) → PASS |
| AC10: Limitations and workarounds | `references/limitations-and-workarounds.md` | acceptance-coverage-contract (T18) → PASS |
| AC11: Unix pipe composition examples | `references/codex-exec-patterns.md` (pipe + CI patterns) | acceptance-coverage-contract (T18) → PASS |

## Changes by Slice

### Slice 1: Author and validate the `using-codex-cli` skill

| File | Change | Lines |
|------|--------|-------|
| `.claude/skills/using-codex-cli/SKILL.md` | ✨ new | +191 |
| `.claude/skills/using-codex-cli/references/codex-exec-patterns.md` | ✨ new | +107 |
| `.claude/skills/using-codex-cli/references/config-reference.md` | ✨ new | +121 |
| `.claude/skills/using-codex-cli/references/limitations-and-workarounds.md` | ✨ new | +82 |
| `.claude/skills/using-codex-cli/references/mcp-server-mode.md` | ✨ new | +106 |

### Workflow artifacts (not part of the shipped skill)

The diff against `main` also carries the QRSPI phase artifacts committed in the
design and plan PRs. They are metadata, not product code, but are listed here so
every file in `git diff main...HEAD` is accounted for.

| File | Change | Lines |
|------|--------|-------|
| `.qrspi/RUS-21/questions.md` | ✨ new | +62 |
| `.qrspi/RUS-21/research.md` | ✨ new | +266 |
| `.qrspi/RUS-21/design.md` | ✨ new | +146 |
| `.qrspi/RUS-21/structure.md` | ✨ new | +153 |
| `.qrspi/RUS-21/plan.md` | ✨ new | +151 |
| `.qrspi/RUS-21/worktree.md` | ✨ new | +83 |
| `.qrspi/RUS-21/impl-log.md` | ✨ new | +29 |

## Testing Summary

This ticket produces documentation; verification is by deterministic contract
checkpoints, not a code test suite.

- [x] Slice 1: frontmatter + body-length (T17) — frontmatter parses, `name: using-codex-cli`, description 599 chars; body 191 lines / ~2267 tokens — PASS
- [x] Slice 1: links checkpoint (T18) — all 4 `references/*.md` linked from body; 0 dangling links; 0 unlinked reference files — PASS
- [x] Slice 1: acceptance coverage (T18) — all 11 acceptance rows covered by body + references (keyword presence) — PASS
- [ ] skill-creator eval loop (with-skill/baseline fan-out + live trigger test) — NOT run (requires interactive subagent fan-out + display; outside non-interactive slice). Deferred — see Open Items.
- [ ] Factual fact-check of Codex CLI claims (UA-9) against live `codex --help` / docs — NOT done (no live Codex docs fetchable in sandbox). Deferred — see Open Items.

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| `SkillFrontmatter` fields | `name` + `description`, additional fields conditional (UA-1) | `name` + `description` only | Standalone knowledge skill with no slash-command wrapper (UA-7 resolved: directory placement suffices); wrapper-only fields (command/argument-hint/allowed-tools) and unused version/author intentionally omitted. Matches structure's stated minimum. |
| Optional `references/` files | `approval-modes.md`, `sandbox-modes.md`, `agents-hierarchy.md` allowed if body breaches length | Not created | Conditional on a length breach; body is at 191/500 lines, so those topics stayed in-body per design Decision 1. Final tree = 5 files (structure's 5-core target, under the 10-file ceiling). |
| `skill-creator-validation-contract` | Skill produced/validated through skill-creator eval loop | Authored to skill-creator conventions; full eval loop not run | Eval loop needs interactive subagent fan-out + a display, unavailable in the non-interactive slice. Deterministic contract checks substituted; live eval deferred. |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| SKILL.md body exceeds 500 lines / 5000 tokens | mitigated — body 191 lines / ~2267 tokens, well under limit | n/a |
| agentskills.io frontmatter schema drift | accepted — pinned to name+description; UA-1 unresolved (no live spec) | Edit `SKILL.md` frontmatter; greenfield, no dependents |
| Existing skills may not follow agentskills.io (qrspi-local YAML convention) | accepted — this skill matches the repo's name+description convention; divergence question left open | n/a — no existing skills modified |
| Over-documentation reduces agent adoption | mitigated — body kept lean (191 lines), depth pushed to references/, tables/code blocks for scannability | Trim sections or relocate to references/ |
| Research phase skipped → design lacks codebase grounding | discovered-new — research.md present in diff but design header states it was MISSING at design time; UAs (UA-2..UA-7) about repo layout were resolved during implementation by live inspection (T1) | n/a |
| macOS Seatbelt sandbox config bug (network_access ignored) | accepted — documented as workaround (prefer `--sandbox` flag over config.toml); claim itself UNVERIFIED (UA-9) | Edit `references/limitations-and-workarounds.md` |

## Open Items

- **skill-creator eval loop + live trigger test** — run interactively (subagent fan-out + eval viewer + harness live-trigger) to fully satisfy skill-creator-validation-contract. Deterministic checks pass; live verification remains.
- **Codex CLI factual fidelity (UA-9)** — a reviewer with Codex CLI access should spot-check the behavioral claims (sandbox enforcement = macOS Seatbelt / Linux Landlock+seccomp+bubblewrap; network-off-by-default; 32 KiB AGENTS.md cap via `project_doc_max_bytes`; `codex exec` flags `--json`/`--quiet`/`--ignore-user-config`/`--ignore-rules`; `codex`/`codex-reply` MCP tools; macOS network-via-config bug) against current `codex --help` and live docs before treating them as authoritative. The text already carries hedging ("Codex changes quickly… confirm against `codex --help`").
- **agentskills.io conformance decision (UA-5)** — whether the repo's existing skills (and this one) should formally conform to agentskills.io vs the qrspi-local YAML convention is an unresolved design-level question deferred to a human.
- **Single-slice feature** — no further implementation slices follow.
