# Design — Create a new agent skill: using-gemini-cli

**Ticket:** RUS-22
**Research basis:** research.md @ 2026-06-01T01:40:00Z
**Generated:** 2026-06-01T02:10:00Z
**Status:** draft

## Current State

Skills live under `.claude/skills/<skill-name>/`, each a directory whose canonical entry point is a single `SKILL.md`; the directory tree itself is the storage and there is no skill-storage module (ref: Q1). Nine of ten existing skills contain only `SKILL.md`; only `qrspi-work` uses a `references/` subdirectory, holding one offloaded doc (`review-cascade.md`), and no skill uses `scripts/` or `assets/` (ref: Q1, Q8). The repo-root `scripts/` directory is the eval harness, unrelated to skill packaging (ref: Q1).

There is no `skill-creator` skill in this repo — `grep` finds only one passing prose mention and no SKILL.md, agent, or script for it (ref: Q2). The nearest authoring analogue is the QRSPI phase pattern: a thin wrapper skill parses `$ARGUMENTS`, resolves `REPO_ROOT` from `pwd`, then spawns a same-named subagent via the `Agent` tool with a structured input contract, and the subagent writes a markdown artifact (ref: Q2, Q4).

Skill frontmatter uses five conventionally-present fields: `name`, `description`, `command` (the `/slash` form), `argument-hint`, and `allowed-tools`; agent files use a different shape (`name`, `description`, `model`, nested `claude.tools`) (ref: Q3). The `description` is a single-line "what it does + when to use" string and is the auto-invocation trigger surface, with no enforced length limit (ref: Q3). Skills are invoked three ways: explicit slash command, auto-invocation from `description` text, or programmatic spawn from the batch workflow (ref: Q4). For every skill, four identifiers are identical — directory name, frontmatter `name`, `command` slug, and `/slash-command` — all kebab-case; this is convention, not enforced (ref: Q5).

No size limit is enforced or measured by any code in this repo; the "500 lines / ~40 instructions" figure appears only as prose guidance in `docs/qrspi_claude_code_guide.md:582`, and no "5000-token" threshold appears anywhere (ref: Q7). The `qrspi-work/SKILL.md` outlier is 791 lines yet nothing flags it (ref: Q7). Content offload into `references/` is an ad-hoc authoring decision with no coded trigger; the body must explicitly point to the reference doc by relative path to load it on demand (ref: Q8). No skill contains a deprecation or version-transition notice, and there is no in-repo template for phrasing one (ref: Q9).

There is no frontmatter validation and no CI in this repo; correctness is trust-based and any validator would be net-new (ref: Q11). The eval harness does not assess description-triggering accuracy and only scores phase *output artifacts*, not SKILL.md bodies; furthermore its runtime is a stub that returns empty output, so all scores are zeros today (ref: Q10, Q12). Post-run inspection is effectively `results.json` + `grades.json` + `report.py` output, and `diagnose.py`/`revise.py` produce nothing useful until the stub is replaced (ref: Q12).

## Desired End State

A new skill `using-gemini-cli` exists at `.claude/skills/using-gemini-cli/SKILL.md` with valid frontmatter, plus a `references/` directory for detailed material. It guides agents using the Google Gemini CLI for coding and multi-agent orchestration. Mapping each acceptance criterion to concrete behavior:

- **agentskills.io directory structure with valid frontmatter** → `.claude/skills/using-gemini-cli/SKILL.md` follows the existing five-field skill frontmatter shape (ref: Q3) and the four-way name identity (ref: Q5).
- **Built using the Anthropic skill builder skill** → satisfied at implementation time by invoking the available `skill-creator` skill in the harness (it is not in-repo; ref: Q2). See OQ1.
- **SKILL.md body under 500 lines / 5000 tokens** → the body stays within the doc-stated 500-line guidance; this is unenforced (ref: Q7), so discipline is manual and verified by the author. Overflow goes to `references/`.
- **Detailed reference material in `references/`** → topic reference docs (e.g., orchestration, sandbox, subagents) live under `references/`, loaded on demand by explicit body pointers, mirroring the `qrspi-work` precedent (ref: Q8).
- **Installation, authentication, invocation patterns (interactive, non-interactive, piped)** → covered in SKILL.md body. NOTE the ticket's stated `npm install -g @anthropic-ai/gemini-cli` package name is almost certainly wrong (Gemini CLI is a Google tool); see OQ2.
- **Permission/approval model (default, auto_edit, yolo)** → covered with when-to-use guidance, body or reference.
- **Sandbox mode configuration and when to enable** → covered, including profiles and `SANDBOX_MOUNTS`; recommended whenever Gemini CLI runs as an autonomous subagent.
- **GEMINI.md context-file hierarchy and best practices** → covered (analogous to CLAUDE.md).
- **MCP server configuration and extension installation** → covered with Gemini-CLI-specific patterns, not generic MCP protocol docs.
- **Subagent definition, routing, tool grants** → covered, including `.gemini/agents/*.md` and wildcard tool grants.
- **Multi-agent orchestration patterns for calling Gemini CLI from external agents** → covered as a priority section: non-interactive `-p`, stdin piping, stdout capture, filesystem coordination, `--approval-mode=yolo --sandbox`.
- **June 2026 deprecation / Antigravity transition note** → included; this is greenfield as no skill models deprecation phrasing (ref: Q9).
- **Actionable examples (code review, test generation, codebase exploration)** → included as concrete invocation examples.

No eval suite, validator, or workflow wiring is added by this ticket — the harness does not score skill bodies and is stubbed (ref: Q10, Q12), so adding eval cases would yield zeros and is out of scope unless requested (see OQ3).

## Delta

**New files:**

- `.claude/skills/using-gemini-cli/SKILL.md` — the skill body. Frontmatter: `name: using-gemini-cli`, single-line `description` shaped "what it does + when to use" (the auto-invocation trigger), `command: /using-gemini-cli`, `argument-hint` (likely a short hint or none-applicable marker), `allowed-tools` (minimal — this is a guidance skill, not a spawning wrapper, so it does NOT grant `Agent`; likely `Bash` for running `gemini`, plus `Read`/`Write`/`Glob`/`Grep` as the agent needs to operate Gemini CLI). See OQ4 on the exact tool set.
- `.claude/skills/using-gemini-cli/references/` — one or more topic docs to keep the body under the 500-line guidance. Candidate split (final split decided during authoring): `orchestration.md` (calling Gemini CLI from external agents, filesystem coordination), `sandbox.md` (profiles, `SANDBOX_MOUNTS`), `subagents.md` (`.gemini/agents/*.md`, routing, tool grants), `configuration.md` (settings hierarchy, GEMINI.md, MCP, extensions, checkpointing). The body references each by relative path on demand (ref: Q8).

**Modified files:** None required for the skill to load (the loader auto-discovers `.claude/skills/*/SKILL.md`, ref: Q1). Optionally update the "Available skills" lists in `.claude/CLAUDE.md` and `README.md` to mention the new skill — but those lists are QRSPI-phase-specific and this is a non-QRSPI utility skill, so an edit there may be noise. See OQ5.

**No new queries, middleware, or schema changes** — this is a content artifact, not runtime code.

## Pattern Decisions

### Decision 1: Skill shape — guidance skill vs. wrapper+subagent

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Standalone guidance skill: a single content-bearing `SKILL.md` (plus `references/`) the agent reads and acts on directly | Matches the ticket (a "guides agents" skill); no paired agent needed; simplest | Diverges from the dominant in-repo wrapper+subagent split (ref: Q2, Q4) |
| B | Wrapper skill + paired `.claude/agents/using-gemini-cli.md` subagent | Maximally consistent with the 8 QRSPI phases | Wrong fit — there is no artifact to produce and nothing to spawn; adds an unused agent file |

**Recommendation:** Option A
**Rationale:** The wrapper+subagent pattern exists to spawn a subagent that writes a `.qrspi/<ticket-id>/` artifact (ref: Q2, Q4). This skill produces no artifact and orchestrates nothing internal to QRSPI; it is reference guidance. `qrspi-work` and `qrspi-ticket` already establish that not every skill has a paired agent (ref: Q4). A content-bearing skill is a NEW shape relative to the thin QRSPI wrappers, but it is the correct shape for a guidance skill.
**NEW PATTERN?** Yes — a content-bearing guidance skill (no paired subagent, no artifact). Justified because every existing skill is a QRSPI-phase orchestrator; none is a general how-to-use-a-tool guide. The `using-graphite-cli` skill in the harness (not in-repo) is the closest analogue and validates this shape.

### Decision 2: Content offload — inline vs. references/

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Everything inline in one SKILL.md | Single file; no on-demand load needed | Risks exceeding the 500-line guidance (ref: Q7); large always-loaded body |
| B | Lean body + topic docs in `references/`, loaded by explicit body pointers | Keeps body under guidance; loads detail only when needed; matches `qrspi-work` precedent (ref: Q8) | More files; author must remember the body must point to each doc to load it |

**Recommendation:** Option B
**Rationale:** The ticket spans 13 dense topic areas; inlining all of them would blow the 500-line guidance the ticket itself imposes. The only in-repo offload precedent (`qrspi-work/references/review-cascade.md`) shows the mechanism: the body explicitly says "Read `references/<doc>.md` for X" (ref: Q8). Body holds the high-frequency core (install, auth, invocation, approval modes, when-to-sandbox); references hold deep config and orchestration detail.
**NEW PATTERN?** No — reuses the existing `references/` offload convention (ref: Q8).

### Decision 3: Frontmatter `allowed-tools` scope

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Minimal: `Bash` plus `Read`/`Write`/`Glob`/`Grep` | Lets the agent actually run `gemini` and do filesystem coordination the skill teaches; follows the lockdown convention (ref: Q3, Q4) | Must confirm `Bash` is the right grant for invoking the CLI |
| B | Broad / inherit-all | Fewer surprises if the skill teaches many tools | Violates the `allowed-tools` lockdown convention (ref: Q3); over-grants |

**Recommendation:** Option A
**Rationale:** Every skill declares `allowed-tools` and read-only/guidance skills keep a minimal set (ref: Q3, Q4). This skill needs to run the `gemini` binary and do filesystem-as-state coordination, so a `Bash`-plus-filesystem grant is the natural minimum. It must NOT grant `Agent` — it is not a spawning wrapper (ref: Q4).
**NEW PATTERN?** No — reuses the `allowed-tools` lockdown convention (ref: Q3).

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Ticket states wrong install command (`npm install -g @anthropic-ai/gemini-cli` — Gemini CLI is Google's, package name implausible) | high | high | Resolve via OQ2 before authoring; verify the real package name and invocation against current Gemini CLI docs; do not transcribe the ticket's command verbatim |
| "Built using the Anthropic skill builder" criterion cannot be self-verified — no `skill-creator` exists in-repo (ref: Q2) | high | low | Invoke the harness `skill-creator` skill at implement time; treat the criterion as a process note, not an in-repo deliverable (OQ1) |
| Body exceeds the 500-line guidance given 13 topic areas | medium | medium | Apply Decision 2 (offload to `references/`); author measures line count manually since nothing enforces it (ref: Q7) |
| Skill `description` does not trigger auto-invocation well — no eval checks triggering (ref: Q10) | medium | medium | Hand-craft the "what + when" description following the `qrspi-work` multi-trigger style (ref: Q3); cannot rely on the eval harness to validate (ref: Q10) |
| Gemini CLI facts in the ticket are stale by ship date (deprecation June 18 2026; Antigravity transition; experimental subagents) | medium | medium | Date the content, include the deprecation note as the ticket directs, flag experimental features explicitly; verify volatile claims at authoring time |
| Adding eval/validation scaffolding wastes effort — harness is stubbed and scores zeros (ref: Q10, Q12) | low | low | Keep eval wiring out of scope unless explicitly requested (OQ3) |

## Open Questions

- OQ1: The "Built using the Anthropic skill builder skill" criterion — confirm we should use the harness-available `skill-creator` skill (which is not in this repo, ref: Q2) and that invoking it satisfies the criterion, versus authoring the SKILL.md by hand. Recommend using `skill-creator`.
- OQ2: The ticket lists the install command as `npm install -g @anthropic-ai/gemini-cli`. Gemini CLI is a Google product; this package name is almost certainly wrong (likely a Google-scoped package and possibly `npx https://github.com/google-gemini/gemini-cli`-style invocation). Confirm the correct install/invocation before authoring so the skill is accurate.
- OQ3: Should this ticket add an eval suite case for the new skill? Given the harness does not score skill bodies and the runtime is stubbed (zeros) (ref: Q10, Q12), recommend NO unless the eval harness is being fixed in parallel.
- OQ4: Confirm the exact `allowed-tools` set — is `Bash` the correct grant to run the `gemini` binary in this environment, and should the skill teach but not itself hold any MCP tools?
- OQ5: Should `.claude/CLAUDE.md` / `README.md` "Available skills" lists be updated? Those lists are QRSPI-phase-specific; a general-purpose guidance skill may not belong there. Recommend leaving them unless you want the skill discoverable in those indexes.
