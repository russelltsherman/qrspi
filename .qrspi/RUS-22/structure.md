# Structure Outline — Create `using-gemini-cli` Agent Skill

**Design basis:** design.md @ 2026-06-03T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft

> This ticket produces a pure-markdown skill (no code, no executable types, no
> automated tests — ref: design.md §Delta). The "types" and "contracts" below are
> therefore the documentation/manifest shapes the skill must conform to, not
> runtime data structures.

## New Types

- `SKILLFrontmatter { name: string, description: string, allowed-tools: string, argument-hint?: string, command?: string }`
  — YAML frontmatter block at the top of `SKILL.md`. Observed in-repo fields are
  `name, description, command, argument-hint, allowed-tools` (ref: design.md §Current State, Q1).
  For this invocable, self-contained skill the required set is `name`, `description`,
  `allowed-tools` (ref: design.md §Desired End State).
- `ReferenceDoc { path: ".claude/skills/using-gemini-cli/references/<topic>.md", linkedFrom: SKILL.md prose }`
  — a deep-dive markdown file surfaced only by relative-path mention in `SKILL.md` prose;
  there is no declarative manifest (ref: design.md §Current State, Q1).

## Modified Types

- None. Discovery is by convention; no registry, `.claude/settings.json`, glob config, or
  README edit is required for the harness to find the skill (ref: design.md §Delta, Q4).

## Contracts

- `frontmatter.name == "using-gemini-cli"` — keys the skill for harness discovery; un-namespaced
  `using-*` style matching `using-graphite-cli` (ref: design.md §Current State, Q4). Subject to OQ2.
- `frontmatter.allowed-tools ⊇ { Bash }` — every external-CLI (`gemini …`) invocation in prose is
  encoded through the `Bash` tool, the repo's only external-CLI mechanism; tool names are
  case-sensitive and a tool not listed cannot be used (ref: design.md §Decision 3, Q6).
- `SKILL.md body ≤ 500 lines AND ≤ 5000 tokens` — hard size cap; overflow detail moves to
  `references/*.md` (ref: design.md §Desired End State, §Decision 2).
- `references resolved by relative path` — each `references/<topic>.md` is reachable only via an
  explicit relative-path mention from `SKILL.md` prose (the `qrspi-work/references/review-cascade.md`
  precedent), not via any manifest (ref: design.md §Current State, Q1).
- `orchestration guidance == { non-interactive -p, stdin context, stdout capture, filesystem
  coordination, --sandbox } + stateless-handoff + HARD-STOP-on-error` — cross-call continuity uses
  explicit inputs + on-disk artifacts (Gemini non-interactive has no session persistence), and
  failed/blocked invocations surface the exact error verbatim with no retry (ref: design.md
  §Decision 3, Q7, Q10).

## Slice 1: Author the `using-gemini-cli` skill (SKILL.md + references)

**Goal:** A complete, self-contained `using-gemini-cli` skill that an agent can invoke and follow
end-to-end — frontmatter discoverable by the harness, a concise in-cap `SKILL.md` overview covering
every in-scope section, and `references/*.md` deep dives reachable by relative path. This is a single
cohesive unit: the `SKILL.md` prose links the reference files, so neither half is verifiable in
isolation, and the `skill-creator` eval loop validates the whole skill at once.

**Files touched:**

- ✨ `.claude/skills/using-gemini-cli/SKILL.md` — frontmatter (`name`, `description`, `allowed-tools`
  incl. `Bash`) + concise body with sections: install/auth/invocation (interactive, `-p`,
  stdin-pipe); permission/approval model (default, auto_edit, yolo) with when-to-use + HARD-STOP
  framing; sandbox (`--sandbox`/`-s`, profiles, `SANDBOX_MOUNTS`); `GEMINI.md` context-file
  hierarchy; MCP (`mcpServers`) + extensions (`gemini extensions install`); subagents
  (`.gemini/agents/*.md`, routing/`@agent-name`, tool grants); multi-agent orchestration; June 2026
  Antigravity-deprecation note; worked examples (code review, test generation, codebase exploration).
  All Gemini-specific facts pinned to a verified version/date in prose (ref: Q9).
- ✨ `.claude/skills/using-gemini-cli/references/permissions-and-sandbox.md` — deep dive on the
  permission/approval model and sandbox profiles/mounts (ref: design.md §Delta).
- ✨ `.claude/skills/using-gemini-cli/references/orchestration.md` — deep dive on calling Gemini from
  external agents: `-p`, stdin context, stdout capture, filesystem coordination, stateless handoff,
  HARD-STOP-on-error (ref: design.md §Decision 3).
- ✨ `.claude/skills/using-gemini-cli/references/subagents-mcp-extensions.md` — deep dive on
  `.gemini/agents/*.md` subagents, `mcpServers` config, and `gemini extensions install`.

**Verification:**

- [ ] Authored via the `skill-creator` skill and run through its eval loop (process requirement;
      ref: design.md §Desired End State).
- [ ] `SKILL.md` body ≤ 500 lines and ≤ 5000 tokens (checked during the eval loop).
- [ ] Frontmatter parses as valid YAML and contains `name: using-gemini-cli`, `description`, and
      `allowed-tools` including `Bash`.
- [ ] Every `references/*.md` path mentioned in `SKILL.md` prose resolves to an existing file
      (no broken relative links); no orphan reference files.
- [ ] All twelve acceptance-criterion sections from §Desired End State are present in `SKILL.md`
      (overview) and/or `references/`.
- [ ] Every Gemini-specific fact (flags, env vars, sandbox profile names, deprecation date) is
      pinned to a verified version/date, with any unconfirmable fact explicitly flagged (ref: Q9, Risk 1).
- [ ] No cross-reference to the in-repo `yolo()` bash wrapper or JS workflow "sandbox" — all such
      terms scoped to Gemini CLI (ref: Risk 3).
- [ ] Manual end-to-end read-through confirms an agent can install, authenticate, and invoke Gemini
      from the document alone (no automated test exists under repo conventions — ref: Q12, Q13).

**Context cost:** M
**Depends on:** none

---

## Unverified Assumptions

- **All Gemini-CLI-specific facts are unverifiable in-repo** and cannot be mapped to any concrete
  file or symbol in this codebase: exact flag names (`-p`, `-s`/`--sandbox`), env vars
  (`SANDBOX_MOUNTS`), sandbox profile names, `mcpServers` config schema, `.gemini/agents/*.md`
  subagent format, `gemini extensions install` syntax, and the June 18 2026 deprecation date. The
  ticket body is the sole authoritative source; these must be pinned to a verified Gemini CLI
  version/date during implementation and any unconfirmable item flagged (ref: design.md Risk 1, OQ3).
- **OQ1 — README skill-list update:** unresolved whether the README skill list should mention
  `using-gemini-cli`. Auto-discovery does not require it (ref: Q4); treated as out of the Delta
  (human-discretionary). No file is touched for this unless a human directs otherwise.
- **OQ2 — final skill name:** `using-gemini-cli` is assumed final (drives `frontmatter.name` and the
  directory path). If renamed, the contract above and all four file paths change.
- **OQ4 — Antigravity migration depth:** the amount of Antigravity-CLI migration content (brief
  forward-pointer vs. fuller treatment) is unresolved; the limitations section's scope depends on it.
- **Skill description triggering quality** cannot be verified without the `skill-creator` eval loop;
  effectiveness is assumed to be tuned there, mirroring the `using-graphite-cli` description style
  (ref: design.md Risk 4).
