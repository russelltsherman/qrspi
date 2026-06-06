# PR: RUS-24 Add using-omlx-cli skill for local LLM inference

**Ticket:** RUS-24
**Design:** design.md @ 2026-06-04T13:00:00Z
**Structure:** structure.md @ 2026-06-06T00:00:00Z

## Summary

Adds a new self-contained agent skill, `using-omlx-cli`, that documents operating
the omlx CLI for local LLM inference on Apple Silicon — full server lifecycle, memory-tier
model sizing, two-tier KV cache tuning, OpenAI-compatible API usage, MCP/agent-launch
patterns, troubleshooting, and an opinionated oMLX-vs-Ollama-vs-LM-Studio comparison. The
skill is a thin `SKILL.md` (116 lines, under budget) backed by three topic-split `references/`
companions; unlike the ten existing `qrspi-*` skills it intentionally does **not** delegate to a
`.claude/agents/` body because it is reference knowledge, not a phase orchestrator (Decision 1).
Reviewers should focus on (a) factual accuracy of the omlx CLI specifics, which come solely from
the ticket — omlx has zero in-repo footprint and no confirmed upstream source (OQ2), and (b)
the new `using-…-cli` name breaking the uniform `qrspi-*` namespace (OQ4, Decision 2).

## Acceptance Criteria Mapping

Acceptance behaviors are the design §Desired End State criteria. "Tests" are structural
verification commands (this ticket ships a knowledge skill, not runtime code — no unit tests exist).

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: agentskills.io dir structure + valid frontmatter | `.claude/skills/using-omlx-cli/SKILL.md` (frontmatter) | `sed -n '/^---$/,/^---$/p' SKILL.md` → field order `name→description→command→argument-hint→allowed-tools` (C2) |
| AC2: Built with the Anthropic skill builder | authored via external `skill-creator` (T1) | impl-log Session 1 deviation note (C7; eval-loop not runnable here — see Open Items) |
| AC3: SKILL.md body < 500 lines / 5000 tokens | `.claude/skills/using-omlx-cli/SKILL.md` | `wc -l SKILL.md` → 116 lines (C3) |
| AC4: Reference material in `references/` | `references/{serve-flags,memory-tiers,troubleshooting}.md` | `grep -oE 'references/...' SKILL.md` + existence check → 3 links resolve, no dead links (C4) |
| AC5: Full server lifecycle (install/serve/configure/monitor/stop) | `SKILL.md` + `references/serve-flags.md` | T17 checkpoint — all 4 files exist (C5) |
| AC6: Memory-tier model-size recommendations | `references/memory-tiers.md` (16/24/32/64 GB tiers) | T17 checkpoint — companion exists + linked (C4/C5) |
| AC7: Two-tier KV cache config & tuning | `references/memory-tiers.md` + `references/serve-flags.md` | T17 checkpoint — companion exists + linked (C4/C5) |
| AC8: OpenAI-compatible API endpoint usage | `references/serve-flags.md` (`/v1/chat/completions`, `/v1/embeddings`, `/v1/messages`) | T17 checkpoint — companion exists + linked (C4/C5) |
| AC9: MCP integration + agent launch patterns | `references/serve-flags.md` (`--mcp-config`, `omlx launch`) | T17 checkpoint — companion exists + linked (C4/C5) |
| AC10: Common failure modes / troubleshooting | `references/troubleshooting.md` | T17 checkpoint — companion exists + linked (C4/C5) |
| AC11: Opinion on oMLX vs Ollama vs LM Studio | `.claude/skills/using-omlx-cli/SKILL.md` (decision section) | T17 checkpoint — SKILL.md exists (C5) |
| (identity) folder == name == /command, no collision | `.claude/skills/using-omlx-cli/` | T17 checkpoint — three-way identity `using-omlx-cli`, no collision (C1) |
| (self-contained) no agent body | (absence of) `.claude/agents/using-omlx-cli.md` | T17 checkpoint — file absent (C6) |

## Changes by Slice

### Slice 1: Author the using-omlx-cli skill (SKILL.md + references)

| File | Change | Lines |
|------|--------|-------|
| `.claude/skills/using-omlx-cli/SKILL.md` | ✨ new | +116 |
| `.claude/skills/using-omlx-cli/references/serve-flags.md` | ✨ new | +143 |
| `.claude/skills/using-omlx-cli/references/memory-tiers.md` | ✨ new | +82 |
| `.claude/skills/using-omlx-cli/references/troubleshooting.md` | ✨ new | +82 |

### Slice 2: Register skill in the human-facing catalog

| File | Change | Lines |
|------|--------|-------|
| `.claude/CLAUDE.md` | ⚠️ modified | +1, -0 |

### Workflow artifacts (not part of either slice — QRSPI phase outputs)

| File | Change | Lines |
|------|--------|-------|
| `.qrspi/RUS-24/questions.md` | ✨ new | +50 |
| `.qrspi/RUS-24/research.md` | ✨ new | +398 |
| `.qrspi/RUS-24/design.md` | ✨ new | +98 |
| `.qrspi/RUS-24/structure.md` | ✨ new | +118 |
| `.qrspi/RUS-24/plan.md` | ✨ new | +120 |
| `.qrspi/RUS-24/worktree.md` | ✨ new | +53 |
| `.qrspi/RUS-24/impl-log.md` | ✨ new | +54 |

## Testing Summary

This ticket ships a knowledge/reference skill with no runtime code, so verification is structural
rather than unit/integration tests.

- [x] Slice 1: frontmatter order — `sed -n '/^---$/,/^---$/p' SKILL.md` — order `name→description→command→argument-hint→allowed-tools` confirmed (C2)
- [x] Slice 1: body budget — `wc -l SKILL.md` — 116 lines, < 500 (C3)
- [x] Slice 1: reference links — `grep -oE 'references/...' SKILL.md` + existence check — 3 links, all resolve, no dead links (C4)
- [x] Slice 1: checkpoint T17 — all 4 files exist (C5); no `.claude/agents/using-omlx-cli.md` (C6); folder == name == /command == `using-omlx-cli`, no collision (C1); description contains "Use when…" + Apple Silicon / local LLM inference / omlx triggers
- [x] Slice 2: catalog registration — `grep -n 'using-omlx-cli' .claude/CLAUDE.md` — 1 match (line 68); `grep -c` — exactly 1 new entry; existing entries untouched
- [ ] Manual: omlx CLI facts (flags, ports, endpoints, tiers) validated against a live `omlx --help` — NOT done; omlx is external, ticket is the only source (OQ2)

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| C7 — Authoring tool | skill-creator authors the skill **and its eval/validation loop is run** | skill-creator drove the SKILL.md draft (T1); the quantitative eval/iterate loop (with-skill/baseline runs, benchmark, browser eval-viewer, description-optimizer) was **not** run | The eval loop is interactive and needs a human reviewer + display; this autonomous slice has neither. Skill was authored and verified structurally instead. Matches structure.md's C7 "see Unverified Assumptions" caveat. |

No deviations from the structural types or contracts C1–C6. No deviations recorded against plan.md for Slice 2.

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| `skill-creator` invocation contract undocumented in-repo, so "built with skill builder" can't be mechanically verified | accepted — skill-creator used as authoring path; eval loop not runnable here (see Deviation C7) | n/a (documentation gap, not a shipped artifact) |
| No in-repo validator for frontmatter / body size / name collision — invalid output ships silently | mitigated — manually verified field order (C2), 116-line budget (C3), three-way identity + no collision (C1) | Delete `.claude/skills/using-omlx-cli/` |
| omlx CLI facts come entirely from the ticket; omlx absent from repo & research | accepted (open) — facts sourced from design §Desired End State / ticket; no flags invented beyond ticket; not validated against a live `omlx --help` | Correct/remove inaccurate facts in `references/`, or revert the skill dir |
| Eval/triggering harness non-functional, triggering accuracy unmeasurable | accepted — strong "Use when…" trigger phrases encoded; manual judgment only | Edit `description` frontmatter to retune triggers |
| Frontmatter-shape footgun if an agent `.md` body were added | mitigated (avoided) — Decision 1 Option B chosen; no `.claude/agents/` body created (C6 verified) | n/a — risk designed out |

Rollback for the whole feature: revert commits `780d9e2` (Slice 1) and `fa2a299` (Slice 2),
or delete `.claude/skills/using-omlx-cli/` and the single `.claude/CLAUDE.md` catalog line.

## Open Items

- **omlx fact validation (OQ2):** every omlx flag, port (`:8000`), endpoint, KV-cache option, and
  memory-tier figure originates solely from the ticket. Reconfirm against a real `omlx --help` /
  upstream docs before relying on it. Follow-up needed if a canonical source is found.
- **skill-creator eval loop (C7 / OQ1):** the quantitative eval/iterate/benchmark loop was not run
  (interactive, needs human + display). If triggering accuracy must be measured, run it manually.
- **Skill name (OQ4):** `using-omlx-cli` breaks the uniform `qrspi-*` namespace. Recommended by
  Decision 2 but awaiting human confirmation in review.
- **Triggering accuracy:** unmeasurable in-repo (placeholder eval harness, empty golden set) — relies
  on manual judgment of the "Use when…" phrases.
