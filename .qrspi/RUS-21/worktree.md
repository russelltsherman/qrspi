# Work Tree — Create a new agent skill `using-codex-cli`

**Plan basis:** plan.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total sessions:** 4
**Critical path:** T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8 → T9 → T10 → T11 → T12 → T13 → T14 → T15 → T16 → T17 → T18 (18 tasks — fully sequential: all body tasks edit the same SKILL.md, each reference file is linked from the body, and validation depends on the complete skill)

> NOTE: One vertical slice, no runtime code. The DAG is an almost-linear chain
> because steps 3–10 all mutate the single `SKILL.md` body in order, the four
> `references/*.md` files (T11–T14) must exist for the body links written in
> T7–T10 to resolve, and validation (T15–T18) needs the finished skill. Sessions
> are split at artifact-type boundaries (assumption resolution → body → reference
> files → validation) purely to keep per-session context under 40%.

## Session 1 — Resolve assumptions + frontmatter

**Load:** structure.md §Unverified Assumptions (UA-1, UA-3, UA-5, UA-6, UA-7),
        structure.md §Contracts (frontmatter-contract), plan.md §Slice 1 Setup
**Estimated context:** ~30% (codebase inspection of an existing SKILL.md is the heavy item)

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Resolve blocking unverified assumptions (UA-1/UA-3/UA-5/UA-6/UA-7) against the live codebase; record decisions inline; surface and stop if any cannot be resolved. No file written. | — | §1 | M | pending |
| T2 | Create `.claude/skills/using-codex-cli/SKILL.md` with YAML frontmatter only (`name: using-codex-cli`, non-empty `description`, plus fields confirmed in T1). | T1 | §2 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Assumption-resolution loads broad codebase-inspection context that is no longer needed once decisions are recorded in the frontmatter. Start fresh to author the body with only the decision record carried forward.

## Session 2 — SKILL.md body sections

**Load:** structure.md §Contracts (body-length-contract, body-to-references-link-contract),
        plan.md §Slice 1 Core Logic, design.md §Decisions (1, 3, 4, 5),
        SKILL.md frontmatter + T1 decision record (notes only)
**Estimated context:** ~35%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T3 | Add **Approval Modes** section (suggest / auto-edit / full-auto decision matrix). | T2 | §3 | S | pending |
| T4 | Add **Sandbox Modes** section (read-only / workspace-write / danger-full-access; Seatbelt + bubblewrap/Landlock; network-off-by-default). | T3 | §4 | S | pending |
| T5 | Add **Session Management** section (fresh sessions per task; context-window pressure). | T4 | §5 | S | pending |
| T6 | Add **AGENTS.md Hierarchy** section (override-first cascade, concatenation precedence, 32 KiB limit, nested rules). | T5 | §6 | S | pending |
| T7 | Add **config.toml quick-start** table + relative TOC link to `references/config-reference.md`. | T6 | §7 | S | pending |
| T8 | Add **MCP Server Mode** summary (~40 lines, 2 worked examples) + link to `references/mcp-server-mode.md`. | T7 | §8 | M | pending |
| T9 | Add **Re-run Non-Determinism / Limitations** flowchart + link to `references/limitations-and-workarounds.md`. | T8 | §9 | S | pending |
| T10 | Add TOC link to `references/codex-exec-patterns.md`; confirm body links all four reference files. | T9 | §10 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** SKILL.md body is complete. The body authoring context is large; reference-file authoring is a distinct unit needing only the contract + the link targets the body now references. Fresh context.

## Session 3 — Reference files

**Load:** structure.md §Contracts (body-to-references-link-contract),
        plan.md §Slice 1 Reference files, design.md §Decisions (3, 4, 5),
        SKILL.md §reference TOC links (notes only)
**Estimated context:** ~35%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T11 | Create `references/config-reference.md` — full `config.toml` schema (user vs project, profiles, feature flags, doc-limit fields). | T7 | §11 | M | pending |
| T12 | Create `references/codex-exec-patterns.md` — `codex exec` args/flags, stdin piping, `--json`/`--quiet`/`--ignore-*`, Unix-pipe + CI patterns. | T10 | §12 | M | pending |
| T13 | Create `references/mcp-server-mode.md` — `codex()`/`codex-reply()` schemas, 2–3 orchestration examples, git-worktrees, subagent discipline. | T8 | §13 | M | pending |
| T14 | Create `references/limitations-and-workarounds.md` — re-run non-determinism flow, macOS network/sandbox bugs, long-chain limits, fresh-session guidance. | T9 | §14 | M | pending |

--- SESSION BOUNDARY ---
**Reason:** All authored artifacts (body + four reference files) now exist. Validation requires fact-checking and running the skill-creator eval loop over the whole directory — a read/verify workload distinct from authoring. Fresh context.

## Session 4 — Validation & verify

**Load:** structure.md §Contracts (skill-creator-validation-contract, acceptance-coverage-contract,
        frontmatter-contract, body-length-contract, body-to-references-link-contract),
        design.md §Desired End State (11 acceptance rows), plan.md §Slice 1 Tests + Verify Slice 1
**Estimated context:** ~30%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T15 | Verify factual fidelity of all Codex CLI claims (UA-9) against current docs; fix divergent claims in T2–T14 outputs. | T11, T12, T13, T14 | §15 | M | pending |
| T16 | Run `skill-creator` skill + eval loop against `.claude/skills/using-codex-cli/`; apply reported fixes. | T15 | §16 | M | pending |
| T17 | Checkpoint — frontmatter parses as YAML, `name: using-codex-cli`, non-empty `description`; body < 500 lines AND < 5000 tokens. | T16 | §17 | S | pending |
| T18 | **Verify Slice 1** — every `references/*.md` linked and every body link resolves; all 11 acceptance rows covered; skill triggers in harness; skill-creator validation passed. | T17 | §18 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Final session; slice complete. No further sessions — feature is a single slice.
