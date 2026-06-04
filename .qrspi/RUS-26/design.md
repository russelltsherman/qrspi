# Design — Create a new agent skill for writing Product Requirements Documents

**Ticket:** RUS-26
**Research basis:** research.md @ 2026-06-04T00:00:00Z
**Generated:** 2026-06-04T00:00:00Z
**Status:** draft

## Current State

There is no PRD-authoring skill anywhere in the repo; the only skills present are the ten `qrspi-*` skills under `.claude/skills/`, and no in-repo code generates skills — they are authored by hand (ref: Q1). The referenced `skill-creator`/`agentskills.io` standard is a global Claude Code asset installed outside `REPO_ROOT` and is NOT FOUND in-repo (ref: Q1, ref: Q3).

The established on-disk shape is a directory `.claude/skills/<skill-name>/` whose only required file is `SKILL.md`; overflow content goes in a `references/` subdirectory, and the directory name must equal the `name` frontmatter field (ref: Q2). Only `qrspi-work` currently uses a `references/` subdir; no skill uses `scripts/` or `assets/` (ref: Q2, ref: Q7). Frontmatter is YAML delimited by `---` with fields `name`, `description`, and (for command skills) `command`, `argument-hint`, and `allowed-tools`; `name`/`description` appear in every skill (ref: Q3). Descriptions follow a two-part convention — what the skill does plus an explicit "Use when…" trigger clause, with the richest example (`qrspi-work`) listing concrete trigger phrasings inline (ref: Q4).

Two structural conventions coexist: most phase skills are thin SKILL.md wrappers (`Agent`-only `allowed-tools`, ~25-35 lines) that spawn a sibling prompt body in `.claude/agents/qrspi-<phase>.md`, while `qrspi-ticket` (119 lines) and `qrspi-work` (565 lines) inline their full logic in SKILL.md with no separate agent file — so a self-contained author skill needs no separate wrapper (ref: Q5). `qrspi-ticket` is the direct precedent for an interactive, problem-first author: it throttles clarifying questions (≤2 at a time), redirects premature solution detail back to the problem, encodes an outcome-vs-output contrast with a contrastive example, treats a mandatory "Out of Scope" section as a required field via an always-present template block with a "None" fallback, and gates output behind a solution-blind self-review (ref: Q8, ref: Q9, ref: Q10). Templates under `.qrspi/templates/` are the layout source-of-truth: skills read them at draft time and reproduce the skeleton inline; templates are reference-only and not written to disk by the skill (ref: Q6, ref: Q9).

The 500-line / 5000-token body cap is a prose convention only — there is no in-repo validator for line count, token count, or frontmatter, and the cap is already violated by `qrspi-work` at 565 lines (ref: Q7, ref: Q12). Verification in this repo is stdlib unit tests plus manual end-to-end runs; `scripts/run_eval.py` and the `evals/` harness are a non-functional placeholder (ref: Q11). Every artifact template opens with a metadata header (source line, ISO-8601 timestamp, `**Status:**` enumeration), but status vocabularies diverge per artifact and no template carries a `version` field or changelog (ref: Q13).

## Desired End State

A new self-contained skill at `.claude/skills/writing-prds/` (directory name == `name`) that, when invoked, guides an agent to author a PRD. Acceptance-criteria mapping:

- **agentskills.io directory structure + valid frontmatter** → `SKILL.md` with YAML frontmatter (`name`, `description`, and `allowed-tools` declaring the concrete tools the inline author uses), matching the repo convention (ref: Q2, ref: Q3, ref: Q5).
- **Built using the Anthropic skill builder skill** → satisfied at authoring time by invoking the global `skill-creator` skill; out-of-repo and unverifiable in-repo (ref: Q1, ref: Q11). See OQ1.
- **Body under 500 lines / 5000 tokens** → primary procedure in the body; bulky template/format detail factored into `references/` (ref: Q7). Unenforced by tooling — author self-checks (ref: Q12).
- **Detailed reference material in `references/`** → the full default template, the expanded-format sections, and the user-story/metrics format examples live under `references/` (ref: Q7).
- **Enforces problem-first structure** → the skill refuses to specify solution detail before the problem is evidenced, mirroring `qrspi-ticket`'s redirect rule (ref: Q8).
- **Default template with all six core sections** → an inline/`references/` skeleton covering Title & Metadata, Problem Statement, Goals & Non-Goals, Solution Overview, Success Metrics, and Scope/Milestones/Open Questions (ref: Q6).
- **SMART success metrics with baseline/target/timeframe** → a metrics table format encoded as a reference example (ref: Q6, ref: Q13).
- **Mandatory non-goals in every PRD** → the Goals & Non-Goals section is always emitted with a "None" fallback and a required-field checklist, mirroring "Out of Scope" enforcement (ref: Q9).
- **User stories "As a / I want / So that" + Given/When/Then** → encoded as a reference format block with testable-criteria guidance (ref: Q10).
- **Asks clarifying questions when evidence is missing** → throttled (≤2 at a time) clarifying-question behavior gating progress (ref: Q8).
- **Supports lean one-pager and expanded formats + guidance on when to expand** → prose selection rules plus two skeletons (lean default, expanded), the format choice being a model decision not a code branch (ref: Q6).

The PRD output itself carries a metadata header with a Status marker, timestamp, and reference line, following the artifact-header convention (ref: Q13).

## Delta

**New files:**

- `.claude/skills/writing-prds/SKILL.md` — self-contained inline author (no `.claude/agents/` sibling). Frontmatter `name: writing-prds`, a two-part `description` with explicit trigger phrasings ("write a PRD", "product requirements document for…"), and `allowed-tools` listing the concrete tools used (e.g. `Read, Write`), following the inline `qrspi-ticket`/`qrspi-work` style rather than the `Agent`-only wrapper style (ref: Q5). Body holds: the problem-first conversation discipline, the format-selection rules, the required-section checklist, and the self-review gate.
- `.claude/skills/writing-prds/references/prd-template.md` — the default lean six-section skeleton plus the expanded sections (Personas, Technical Considerations, Dependencies, Launch Plan), the SMART metrics table format, the user-story/Given-When-Then block, and the metadata-header convention. Pulled in by path from the body (ref: Q7).

**Modified files:** none required for the skill to function. The global skill router discovers `.claude/skills/*/SKILL.md` automatically (ref: Q3).

**No new templates under `.qrspi/templates/`** — that directory is for QRSPI phase artifacts; the PRD layout is a skill-owned asset and lives under the skill's `references/` (ref: Q6, ref: Q2).

## Pattern Decisions

### Decision 1: Skill structure — inline vs. wrapper+agent

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Self-contained inline SKILL.md, no `.claude/agents/` file (like `qrspi-ticket`) | Matches the interactive-author precedent; single file to author/maintain; no spawning indirection | Risks pushing body toward the 500-line cap |
| B | Thin wrapper SKILL.md + `.claude/agents/writing-prds.md` (like phase skills) | Keeps body tiny; separates trigger from logic | Wrapper/agent split exists to support the QRSPI batch-spawn machinery, which a standalone author does not use; adds an unneeded file |

**Recommendation:** Option A
**Rationale:** A PRD author is a single interactive, guided-conversation skill with no batch-orchestration role — exactly the shape of `qrspi-ticket`, which is inline and SKILL.md-only (ref: Q5). The wrapper split's purpose (spawning a typed sub-agent for the batch workflow) does not apply here.
**NEW PATTERN?** No — it reuses the existing inline-author pattern (`qrspi-ticket`, `qrspi-work`).

### Decision 2: Where the PRD template lives

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Full template in `references/prd-template.md`, summarized/linked from the body | Keeps body under the cap; matches `references/` overflow pattern | One extra on-demand read for the agent |
| B | Entire template inline in the body (like `qrspi-ticket`'s inline skeleton) | Single file; skeleton always in context | Two formats + SMART table + user-story block + metadata header would push the body well over 500 lines |

**Recommendation:** Option A
**Rationale:** Only `qrspi-work` uses `references/`, and it does so for exactly this reason — bulky conditional detail belongs out of the body (ref: Q7). A dual lean/expanded template plus format examples is too large to inline without breaching the cap (ref: Q7, ref: Q12).
**NEW PATTERN?** No — reuses the `references/` overflow pattern; note it would be the second skill to use it.

### Decision 3: How to encode lean-vs-expanded format selection

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Prose selection rules + two inline-referenced skeletons; the model chooses | Matches repo convention (format is a model decision, not code); flexible defaults with overrides | Relies on the model following prose rules; unenforced |
| B | A deterministic branch / parameter forcing lean or expanded | Predictable output | No in-repo precedent; the repo has no code path that branches skill output by format (NOT FOUND, ref: Q6) |

**Recommendation:** Option A
**Rationale:** The repo pattern for "let the agent select" is prose instructions plus an inline skeleton, not a code branch — the closest analog (`qrspi-ticket`) conveys output shape via prose rules + skeleton (ref: Q6). This is also a NEW combination since no existing skill encodes a dual output format.
**NEW PATTERN?** Yes — a dual lean/expanded output format has no in-repo precedent (ref: Q6). Justified: the ticket explicitly requires both formats with guidance on when to expand; existing single-skeleton skills do not cover this, so the prose-selection convention is extended to two skeletons.

### Decision 4: Enforcing mandatory sections (non-goals) and problem-first discipline

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Prompt-level: always-emit section with "None" fallback + required-field checklist + solution-blind self-review gate | Directly mirrors `qrspi-ticket`/"Out of Scope" enforcement; proven in-repo | Not machine-validated; depends on self-review |
| B | Add a Python validator that rejects PRDs missing non-goals | Hard guarantee | No skill-output validator exists in-repo (ref: Q12); PRD output is freeform prose not parsed by the harness; large new surface for no precedent |

**Recommendation:** Option A
**Rationale:** Enforcement in this repo is prompt-level — mandatory sections stay present by always emitting them with a "None" fallback, and quality is gated by self-review, not code (ref: Q9, ref: Q10). The outcome-vs-output contrast and clarifying-question throttle are directly reusable from `qrspi-ticket` (ref: Q8, ref: Q10).
**NEW PATTERN?** No — reuses the ticket skill's enforcement-by-template-plus-self-review pattern.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| SKILL.md body exceeds the 500-line / 5000-token cap (no validator exists; `qrspi-work` already breaches it) | med | low | Push template + format examples into `references/` (Decision 2); author self-checks line/token count before finishing (ref: Q7, ref: Q12) |
| Problem-first / non-goals enforcement is prompt-level only and a model may skip it | med | med | Reuse the proven `qrspi-ticket` mechanisms verbatim — ≤2-question throttle, solution redirect, always-emit section with "None" fallback, solution-blind self-review gate (ref: Q8, ref: Q9, ref: Q10) |
| "Built using the Anthropic skill builder" is unverifiable in-repo (global asset, NOT FOUND) | high | low | Treat as an authoring-time process step (invoke global `skill-creator`); do not depend on in-repo tooling; document the dependency (ref: Q1, ref: Q11). See OQ1 |
| Status vocabulary chosen for PRDs ("Draft/In Review/Approved") matches no existing template exactly | low | low | Adopt the ticket's stated vocabulary since it is a skill-owned artifact, not a QRSPI phase artifact; keep the header shape (source + ISO-8601 timestamp + Status) consistent with the convention (ref: Q13) |
| `description` trigger wording fails to fire the skill on natural PRD requests | low | med | Follow `qrspi-work`'s richest-description pattern: explicit trigger phrasings plus a "Use when…" clause (ref: Q4) |

## Open Questions

- OQ1: The "Built using the Anthropic skill builder skill" acceptance criterion targets a global, out-of-repo asset that cannot be verified from the repo. Confirm whether satisfying it means literally invoking `skill-creator` during authoring (a process gate), or whether the produced skill merely needs to conform to the agentskills.io structure (an output gate). This changes whether the work item is "run skill-creator" vs. "hand-author to spec."
- OQ2: Should generated PRDs include a `version` field and a changelog section? The ticket asks for both, but no in-repo template carries either (the closest is design's `revision-N`) (ref: Q13). Confirm the desired metadata vocabulary for the PRD header and whether to introduce a changelog convention that does not yet exist in the repo.
- OQ3: Should this skill be registered anywhere beyond auto-discovery (e.g. listed in `.claude/CLAUDE.md`'s "Available skills" block alongside the QRSPI skills), or is it intentionally standalone and outside the QRSPI workflow?
