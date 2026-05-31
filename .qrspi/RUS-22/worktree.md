# Work Tree — Create a new agent skill for using the Gemini CLI

**Plan basis:** plan.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft
**Total sessions:** 3
**Critical path:** T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8 → T9 → T10 → T12 → T15 → T16 → T17 → T18 → T19 → T20 → T21 → T22 → T23 → T24 (21 tasks)

> Slice 1 (plan steps 1–18) is doc-heavy: it authors a full SKILL.md body plus four
> reference files, all sourced from authoritative Gemini CLI docs at authoring time
> (OQ3 + external content facts are unverified from the codebase). It is split across
> Sessions 1–2 so neither exceeds the 40% context ceiling. Slice 2 (steps 19–24) is
> Session 3. The chain is almost fully sequential because every body section appends to
> the same SKILL.md and every later artifact references content authored earlier.

## Session 1

**Load:** structure.md §New Types, structure.md §Contracts (Frontmatter, Risk-surfacing),
        plan.md §Slice 1 (Setup + Core Logic, steps 1–10), design Decisions 1A–4A,
        authoritative Gemini CLI docs (external — package name/OQ3, modes, deprecation)
**Estimated context:** ~35% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Scaffold `.claude/skills/using-gemini-cli/` via global `skill-creator` (resolves OQ1) | — | §1 | M | pending |
| T2 | Write SKILL.md frontmatter — all five fields; `name` matches dir | T1 | §2 | S | pending |
| T3 | Add **Installation & auth** — verify OQ3 package name from official docs (NOT `@anthropic-ai/gemini-cli`) | T2 | §3 | M | pending |
| T4 | Add **Invocation** section (interactive, `-p`, piped/stdin) | T3 | §4 | S | pending |
| T5 | Add **Permission / approval model** + named yolo/sandbox-off risk block | T4 | §5 | S | pending |
| T6 | Add **Sandbox** summary (tables deferred to references) | T5 | §6 | S | pending |
| T7 | Add **Multi-agent orchestration** section | T6 | §7 | S | pending |
| T8 | Add **Workflow examples** (prose-only) | T7 | §8 | S | pending |
| T9 | Add dated **Deprecation / Antigravity** caveat block | T8 | §9 | S | pending |
| T10 | Add **References** links section (links all four reference files) | T9 | §10 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** SKILL.md body fully drafted. The next session fetches and authors the four
reference files (separate doc-sourcing pass) plus the budget/audit/eval work — a fresh
context avoids carrying the body-authoring doc dump into reference authoring.

## Session 2

**Load:** structure.md §Contracts (Body→reference link, Budget), plan.md §Slice 1
        (References + Budget & link audit + Tests + Verify, steps 11–18),
        impl-log.md §Slice 1 (notes only — section names authored in Session 1),
        authoritative Gemini CLI docs (external — sandbox profiles, GEMINI.md precedence,
        subagent routing, MCP/extension config)
**Estimated context:** ~32% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T11 | Create `references/sandbox.md` (profiles + when to enable) | T10 | §11 | M | pending |
| T12 | Create `references/configuration.md` (GEMINI.md hierarchy + settings precedence) | T10 | §12 | M | pending |
| T13 | Create `references/subagents.md` (definition, routing, tool grants) | T10 | §13 | M | pending |
| T14 | Create `references/mcp-and-extensions.md` (MCP config + extension install) | T10 | §14 | M | pending |
| T15 | Trim/relocate body to Budget (≤ 500 lines / 5000 tokens) | T11, T12, T13, T14 | §15 | S | pending |
| T16 | Audit Body→reference link parity (bidirectional) | T15 | §16 | S | pending |
| T17 | Run `skill-creator` eval loop against the skill (resolves OQ1) | T16 | §17 | M | pending |
| T18 | **Verify Slice 1** checkpoint | T17 | §18 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete and verified. Slice 2 is scope-gated by OQ4 — if the eval
file is deferred until harness stubs exist, drop Session 3 entirely. Fresh context for
the eval-fixture work, which loads a different schema slice.

## Session 3

**Load:** structure.md §New Types (`EvalFile`, `EvalCase`), structure.md §Contracts
        (Eval-file schema), plan.md §Slice 2 (steps 19–24),
        impl-log.md §Slice 1 (documented commands/flags/safety modes referenced by assertions)
**Estimated context:** ~22% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T19 | Create `evals/gemini-cli-evals.json` — `skill_name` + empty `evals: []` (mirror graphite-evals.json) | T18 | §19 | S | pending |
| T20 | Add ≥1 `command_check` case (references a Slice 1 command) | T19 | §20 | S | pending |
| T21 | Add ≥1 `flag_check` case (e.g. `-p`, `--sandbox`) | T20 | §21 | S | pending |
| T22 | Add ≥1 `safety_check` case (yolo / sandbox-off) | T21 | §22 | S | pending |
| T23 | Validate JSON parses (`json.load`) | T22 | §23 | S | pending |
| T24 | **Verify Slice 2** checkpoint | T23 | §24 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** All slices complete. Proceed to the PR phase (`/qrspi-pr RUS-22`).
