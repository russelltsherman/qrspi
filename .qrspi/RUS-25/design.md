# Design — Create a new agent skill for writing Architecture Decision Records

**Ticket:** RUS-25
**Research basis:** research.md @ 2026-06-04T00:00:00Z
**Generated:** 2026-06-04T00:00:00Z
**Status:** draft

## Current State

Skills in this repo live in `.claude/skills/<skill-name>/`, each containing a `SKILL.md`; there are 10 skills, all named `qrspi-*` (ref: Q1). No skill uses `assets/` or a skill-local `scripts/` directory — the only skill with any subdirectory is `qrspi-work`, which has a single `references/` subdir holding `review-cascade.md` (ref: Q1). That is the sole precedent for the multi-file pattern; `assets/` and skill-local `scripts/` have no precedent and would be net-new conventions (ref: Q1, Q6).

Skill-local reference files are pointed to from the body using a bare relative path in backticks (e.g. "see `references/review-cascade.md`"), resolved against the skill's own directory; no `[text](path)` Markdown-link form is used for skill-local references anywhere (ref: Q2). The referenced file is loaded on-demand ("see X") rather than inlined, keeping `SKILL.md` lean — the repo's progressive-disclosure idiom (ref: Q2).

Every in-repo `SKILL.md` uses YAML frontmatter delimited by `---` with the fields `name`, `description`, `command`, `argument-hint`, and `allowed-tools`; `name` matches the directory name, `command` is `/` + name, and `description` is written in imperative "Use when…" form because it doubles as the auto-invocation trigger (ref: Q3). `allowed-tools` is a comma-separated allowlist that acts as the per-skill capability firewall (ref: Q3). There is no in-repo frontmatter validator — the schema is enforced only by convention across the 10 files (ref: Q3).

The repo uses a two-layer split: agents (`.claude/agents/qrspi-<phase>.md`) hold heavy phase logic, while skills (`.claude/skills/<name>/SKILL.md`) are thin slash-command wrappers; there are 10 skills but only 8 agents, because `qrspi-work` and `qrspi-ticket` are self-contained skills with no agent (ref: Q5). A self-contained skill needs only a `SKILL.md` with valid frontmatter to be discoverable; a phase-delegating skill additionally needs an agent file (ref: Q5).

The skill-builder skill (`skill-creator`) is referenced by name in `.claude/agents/qrspi-structure.md:40` as a validation step, but its definition does not exist anywhere under the repo root — it is an external/global skill whose invocation contract cannot be determined from the repo (ref: Q4). Output-format templates are kept project-globally in `.qrspi/templates/` as the single source of truth; there is no skill-local `assets/` starter convention (ref: Q6).

There is a generic `line_count(filename, max_lines)` check in `scripts/grade.py`, but it is wired only into the (non-functional) eval grader, targets artifact outputs (not `SKILL.md`), and counts lines only — no token-counting validator exists anywhere (ref: Q7). The eval harness (`scripts/run_eval.py` + suites) is a placeholder that returns empty output; the working verification methods are stdlib-only `_test.py` unit tests for pure logic and manual end-to-end runs (ref: Q10). There is no automated verification of skill triggering or frontmatter structure — correctness is maintained by convention and human review (ref: Q11).

The QRSPI lifecycle is encoded twice: as an ordered list/enum in code (`PHASES` in the resolver) and as a human-readable transition table in skill markdown (ref: Q8). Skill surfacing is purely convention-by-location — dropping `.claude/skills/<name>/SKILL.md` with valid frontmatter causes the Claude Code runtime to list it; there is no plugin manifest or registry (ref: Q12). The available-skills list is duplicated by hand across `.claude/CLAUDE.md`, `README.md`, and `docs/qrspi_claude_code_guide.md` with no single source of truth (ref: Q12). There is no existing `docs/decisions/`, `docs/adr/`, or `architecture/decisions/` directory and no existing ADRs — the skill defines the ADR numbering/naming convention from scratch (ref: Q9).

## Desired End State

A new self-contained skill `adr` (or `writing-adr`) at `.claude/skills/<name>/` that guides agents to author and manage ADRs. Mapping each acceptance criterion to concrete behavior:

- **agentskills.io directory structure with valid frontmatter** → skill directory contains `SKILL.md` plus `references/` and `assets/`; frontmatter carries `name`, `description`, `command`, `argument-hint`, `allowed-tools` matching the repo convention (ref: Q3).
- **Built using the skill-builder skill** → the implementing slice invokes `skill-creator` during authoring/validation, matching the existing validation-step usage (ref: Q4); because `skill-creator` is external and unverifiable from the repo, success is confirmed by manual review, not tooling.
- **SKILL.md body under 500 lines / 5000 tokens** → body stays lean via progressive disclosure, pushing full templates and examples into `references/` (ref: Q2). No automated gate exists; the `line_count` check covers only the line half and is not wired to `SKILL.md` (ref: Q7).
- **`references/` covering MADR 4.0 full template, Nygard original, Y-statement, and example ADRs** → four reference files, each pointed to from `SKILL.md` by bare-relative-path-in-backticks (ref: Q2).
- **Starter ADR template in `assets/`** → a copyable MADR 4.0 starter file in `assets/`; this introduces the first `assets/` convention in the repo (ref: Q1, Q6).
- **MADR 4.0 as default format** → `SKILL.md` encodes the eight required sections (Title, Status, Date, Context and Problem Statement, Decision Drivers, Considered Options, Decision Outcome, Consequences) in order, with optional sections documented.
- **Full lifecycle: create, supersede, deprecate, index maintenance** → `SKILL.md` carries a prose status-transition table (`proposed → accepted → deprecated|superseded`, plus `rejected`) mirroring the QRSPI markdown-table idiom (ref: Q8), plus procedures for numbering, file naming, and maintaining `docs/decisions/README.md`.
- **Guidance on when to write an ADR** → a judgment-call section defining "architecturally significant."
- **adr-tools / log4brains compatibility** → encode `docs/decisions/` default path, `NNNN-kebab-case-title.md` naming, sequential 4-digit numbering.
- **Bidirectional links on supersede** → procedure requiring both the old ADR (`superseded by ADR-NNNN`) and the new ADR (`Supersedes ADR-NNNN`) to be updated.

## Delta

New files:
- `.claude/skills/<name>/SKILL.md` — frontmatter + lean body encoding MADR default, lifecycle table, numbering/naming rules, when-to-write guidance, supersede procedure, and on-demand pointers into `references/`.
- `.claude/skills/<name>/references/madr-4.0.md` — full MADR 4.0 template and section guidance.
- `.claude/skills/<name>/references/nygard.md` — Nygard original template.
- `.claude/skills/<name>/references/y-statements.md` — Y-statement format.
- `.claude/skills/<name>/references/examples.md` — worked example ADRs.
- `.claude/skills/<name>/assets/NNNN-template.md` — copyable starter ADR (MADR 4.0).

Modified files (to keep the hand-maintained skill lists in sync — ref: Q12):
- `.claude/CLAUDE.md` — add the skill to the available-skills list.
- `README.md` — add the skill.
- `docs/qrspi_claude_code_guide.md` — add the skill.

No agent file is created — this is a self-contained skill with no phase delegation (ref: Q5). No new queries, scripts, or DB changes.

## Pattern Decisions

### Decision 1: Skill type — self-contained vs. agent-backed

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Self-contained `SKILL.md` only, no agent | Matches `qrspi-work`/`qrspi-ticket` precedent (ref: Q5); no phase-orchestration coupling; simplest discoverability | Body must hold all guidance, pressuring the 500-line limit |
| B | Skill wrapper + `.claude/agents/<name>.md` | Heavy guidance moves to the agent | No precedent for a non-QRSPI-phase agent; orchestrator never reads skill bodies, so the split buys nothing here (ref: Q5) |

**Recommendation:** Option A
**Rationale:** ADR authoring is not a QRSPI phase and is not orchestrated; the self-contained pattern (`qrspi-work`, `qrspi-ticket`) fits exactly (ref: Q5). The 500-line pressure is relieved by progressive disclosure into `references/` (ref: Q2).
**NEW PATTERN?** No.

### Decision 2: Where reference/starter material lives

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | `references/` for docs + `assets/` for the starter | Satisfies the ticket's explicit structure; clean docs-vs-copyable split | Introduces the repo's first `assets/` dir (ref: Q1, Q6) |
| B | Everything in `references/`, no `assets/` | Stays within the single existing precedent (ref: Q1) | Violates the acceptance criterion requiring a starter in `assets/`; blurs reference vs. copyable template |
| C | Put the starter in project-global `.qrspi/templates/` | Reuses the existing template-as-source-of-truth idiom (ref: Q6) | Misplaces an ADR-specific asset into the QRSPI artifact templates dir; not skill-local; fails the acceptance criterion |

**Recommendation:** Option A
**Rationale:** The ticket explicitly requires `references/` and a starter in `assets/`. The repo has no `assets/` precedent (ref: Q1, Q6), so this is a deliberate, ticket-mandated new convention rather than an accident.
**NEW PATTERN?** Yes — first use of `assets/` in any skill (ref: Q1). Justified because the acceptance criteria mandate a copyable starter distinct from on-demand reference docs, and no existing skill-local location serves that role (ref: Q6).

### Decision 3: How references are linked from SKILL.md

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Bare relative path in backticks ("see `references/madr-4.0.md`") | Matches the single in-repo precedent exactly (ref: Q2) | Not a clickable link in all renderers |
| B | Markdown links `[MADR](references/madr-4.0.md)` | Clickable | No in-repo precedent for skill-local Markdown links; diverges from the established idiom (ref: Q2) |

**Recommendation:** Option A
**Rationale:** Q2 shows the repo's sole convention is bare-relative-path-in-backticks with on-demand loading; consistency over novelty.
**NEW PATTERN?** No.

### Decision 4: How the ADR status lifecycle is encoded

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Prose status-transition table in `SKILL.md` | Mirrors the QRSPI markdown transition-table idiom (ref: Q8); no code needed for a docs skill | Not machine-enforced |
| B | A Python enum/resolver + `_test.py` (like `PHASES`) | Matches the determinism-via-tested-Python idiom (ref: Q8) | Over-engineered — nothing in this skill acts on state programmatically; the resolver pattern is QRSPI-internal (ref: Q8) |

**Recommendation:** Option A
**Rationale:** The ADR lifecycle is documentation guidance, not orchestrated state; Q8 confirms code enums are only for components that act on state. A markdown transition table is the correct half of the dual pattern.
**NEW PATTERN?** No.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `skill-creator` is external and unverifiable from the repo, so the "built using skill-builder" criterion can't be checked in-repo (ref: Q4) | high | med | Treat the criterion as a process step confirmed by manual review; document in the implementation that `skill-creator` is a global dependency assumed present (ref: Q4) |
| SKILL.md exceeds 500 lines / 5000 tokens with no automated gate (ref: Q7) | med | med | Push all templates/examples into `references/` via progressive disclosure (ref: Q2); manually run `line_count` from `grade.py` against `SKILL.md` as a one-off check; no token-counter exists, so verify token budget by inspection (ref: Q7) |
| First-ever `assets/` dir may surprise reviewers expecting the `references/`-only norm (ref: Q1, Q6) | low | low | Flag the new convention explicitly in the PR; it is ticket-mandated (Decision 2) |
| Hand-maintained skill lists in three files drift if any is missed (ref: Q12) | med | low | Update all three (`.claude/CLAUDE.md`, `README.md`, `docs/qrspi_claude_code_guide.md`) in the same slice (see Delta) |
| No frontmatter/triggering validator means a malformed `description` silently degrades auto-invocation (ref: Q11, Q12) | med | med | Model the `description` on `qrspi-work`'s explicit "Use when… / Trigger on…" trigger-phrase style (ref: Q3, Q12); human-review the frontmatter |

## Open Questions

- OQ1: Final skill `name`/`command` — `adr`, `writing-adr`, or `architecture-decision-records`? Repo convention is `name` == directory == `command` stem (ref: Q3); the ticket title suggests "writing Architecture Decision Records" but does not fix a slug.
- OQ2: What `allowed-tools` allowlist should the skill carry? It needs file Read/Write/Edit and likely Glob to find existing ADRs for numbering, but the firewall idiom favors the minimum (ref: Q3). Human should confirm the exact set.
- OQ3: Should the skill also scaffold `docs/decisions/` and its `README.md` index on first use, or only document the convention? No such directory exists today (ref: Q9), and creating project files is arguably beyond a guidance skill's remit.
- OQ4: Is the `line_count`/token target meant to be enforced (e.g., a new check) or treated as an authoring guideline? No enforcement mechanism exists for either half (ref: Q7).
