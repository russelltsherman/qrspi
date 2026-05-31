# Design — Create a new agent skill called using-graphite-cli

**Ticket:** RUS-6
**Research basis:** research.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## Current State

There is no `using-graphite-cli` skill anywhere in the repo; a recursive search for the name returned nothing, so every file must be created from scratch (ref: Q1). The skills directory is `.claude/skills/` and currently holds exactly 10 skills, all prefixed `qrspi-` (ref: Q1). Only `qrspi-work` has a `references/` subdirectory; no skill uses a `scripts/` or `assets/` subdirectory (ref: Q1, Q4).

The canonical layout is `.claude/skills/<skill-name>/SKILL.md` with an optional `references/` subdirectory of supplementary `.md` files, and the directory name conventionally matches the frontmatter `name` field (ref: Q1, Q4). There is no formal frontmatter schema or validator in the repo; the de-facto standard is inferred from existing files, where every SKILL.md uses `name`, `description`, `command`, `argument-hint`, and `allowed-tools` between `---` fences (ref: Q3). Trigger matching is performed by Claude Code's loader outside the repo; the in-repo source of truth is the `description` field, which front-loads concrete trigger phrases and "Use when…" phrasing (ref: Q5). `references/` files are referenced by bare backtick-wrapped relative path in prose and loaded on demand (progressive disclosure), not inlined (ref: Q6).

Existing thin-wrapper SKILL.md files measure 25–35 lines; the two outliers are `qrspi-ticket` (119 lines, self-contained) and `qrspi-work` (730 lines / ~8k token-equivalent bytes, the only file exceeding a 500-line / 5000-token budget) (ref: Q7). The convention for the SKILL-vs-references boundary is editorial, not enforced: always-needed control flow stays inline; large situational reference material is externalized (ref: Q8). No frontmatter or directory validator exists; the eval harness validates only suite JSON (ref: Q9). The `skill-creator` skill named in the ticket is NOT present in-repo — it lives in the global Claude environment, so its ingestion mechanism cannot be verified from repo files (ref: Q2). A Graphite eval suite already exists at `evals/graphite-evals.json` with 5 cases, but it uses top-level keys `skill_name`/`evals` and `{text, type}` assertion objects, which do NOT conform to `scripts/run_eval.py`'s required `name`/`cases` schema and would raise `ValueError` if run as-is (ref: Q9, Q10). No in-repo tooling measures trigger accuracy (ref: Q10, Q11).

## Desired End State

The new skill ships at `.claude/skills/using-graphite-cli/` with a valid `SKILL.md` (frontmatter `name`, `description`, `command`, `argument-hint`, `allowed-tools`) plus a `references/` directory holding the full command reference and edge cases. This satisfies the acceptance criteria as follows:

- **agentskills.io directory structure + valid frontmatter** — `.claude/skills/using-graphite-cli/SKILL.md` with the five frontmatter fields matching the in-repo convention (ref: Q3, Q4); directory name equals `name` (ref: Q1).
- **Built using the Anthropic skill builder skill** — see Open Questions; skill-creator is out of repo scope (ref: Q2).
- **SKILL.md under 500 lines / 5000 tokens** — target the 25–120 line band of existing single-file skills; offload bulk to references (ref: Q7, Q8).
- **Detailed reference material in `references/`** — full command catalog + edge cases in `references/*.md`, loaded on demand per the progressive-disclosure pattern (ref: Q6, Q8).
- **Single-commit-per-branch encoded as a hard rule** — stated as a non-negotiable in SKILL.md body.
- **Complete Create → Submit → Modify → Sync loop** — the core workflow occupies the always-needed inline section of SKILL.md (ref: Q8).
- **Conflict resolution via `gt continue` (never `git rebase --continue`)** — covered inline with the prohibition called out explicitly.
- **Stack navigation + directionality (downstack=toward trunk, upstack=away)** — inline navigation section.
- **Submit flag defaults (`--no-edit --publish`)** — stated as the agent default.
- **Warns against mixing raw git branch/rebase with Graphite-tracked branches** — explicit prohibition inline.

Behaviorally, an agent that loads this skill follows `gt sync` at session start, creates branches with `gt create`, amends with `gt modify`, resolves conflicts with `gt continue`, submits with `gt ss -np`, merges bottom-up, and never runs raw `git branch`/`git commit --amend`/`git rebase` on tracked branches.

## Delta

New files:
- `.claude/skills/using-graphite-cli/SKILL.md` — frontmatter + always-needed content: hard rules (single-commit-per-branch, no raw git), the Create→Submit→Modify→Sync loop, navigation/directionality, conflict-resolution flow, submit-flag defaults, and pointers into references.
- `.claude/skills/using-graphite-cli/references/command-reference.md` — full `gt` command catalog (init/config, create, submit and flags, modify, sync, navigation, downstack/upstack, restack, branch split, merge order).
- `.claude/skills/using-graphite-cli/references/edge-cases.md` — conflict resolution detail, metadata-drift recovery, trunk misdetection, deep-stack guidance, GitHub/CODEOWNERS integration.

No modifications to existing skill files. No new code or queries. The existing `evals/graphite-evals.json` is the behavioral test surface for this skill; whether to reconcile its schema with `run_eval.py` is a scope decision (ref: Q9, Q10) — see Open Questions and Risk Register.

## Pattern Decisions

### Decision 1: SKILL.md structure — thin-wrapper-over-agent vs. self-contained

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Thin SKILL.md that spawns a `.claude/agents/using-graphite-cli.md` agent | Matches 8/10 QRSPI skills (ref: Q8) | The QRSPI wrappers exist to dispatch phase agents in a workflow; a reference/guidance skill has no agent to spawn — misfit |
| B | Self-contained SKILL.md with body content + `references/` offload | Matches `qrspi-ticket` (self-contained, ref: Q7) and the `qrspi-work`→`references/` progressive-disclosure pattern (ref: Q6, Q8); fits a guidance skill | Author must police the line/token budget by hand (no validator, ref: Q9) |

**Recommendation:** Option B
**Rationale:** The thin-wrapper split exists to spawn phase agents in the QRSPI state machine; this skill is behavioral guidance with no agent to dispatch, so the self-contained-plus-references model (`qrspi-ticket` + `qrspi-work`/`review-cascade.md`) is the right in-repo precedent (ref: Q6, Q7, Q8).
**NEW PATTERN?** No — composes the existing self-contained and `references/` patterns.

### Decision 2: SKILL.md vs. references/ content split

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Put the full command reference inline in SKILL.md | One file | Blows the 500-line/5000-token budget; the full catalog is situational, not always-needed (ref: Q7, Q8) |
| B | Keep always-needed content (hard rules, core loop, conflict flow, submit defaults, navigation) inline; move full command catalog + edge cases to `references/` | Honors the budget and the always-needed-vs-situational convention (ref: Q8); progressive disclosure (ref: Q6) | Two-to-three files to maintain |

**Recommendation:** Option B
**Rationale:** Directly mirrors `qrspi-work` keeping control flow inline while externalizing the situational cascade table (ref: Q6, Q8), and is the only way to satisfy both the "under 500 lines" and "detailed reference material in references/" criteria simultaneously (ref: Q7).
**NEW PATTERN?** No.

### Decision 3: `allowed-tools` value for a guidance skill

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Broad allowlist incl. `Bash` and `Read` (like `qrspi-ticket`) | Lets the agent actually run `gt` commands described | Wider surface; `Bash` unscoped |
| B | Minimal/scoped allowlist, e.g. Bash scoped to `gt` (`Bash(gt:*)`) plus `Read` | Matches the "allowed-tools as firewall" + `Bash(pwd:*)` command-prefix scoping pattern (ref: Q3) | A guidance skill may be expected to advise, not execute — scoping may be unnecessary or too narrow |

**Recommendation:** Option B (Bash scoped to `gt`, plus `Read` for references), pending the execute-vs-advise question below
**Rationale:** The repo treats `allowed-tools` as a structural firewall and demonstrates command-prefix scoping with `Bash(pwd:*)` (ref: Q3); scoping Bash to `gt` lets the agent run Graphite without granting arbitrary shell.
**NEW PATTERN?** No — applies the existing `Bash(<prefix>:*)` scoping pattern.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Eval suite `graphite-evals.json` won't run — uses `skill_name`/`evals`, not the `name`/`cases` schema `run_eval.py` requires (ref: Q9, Q10) | high | med | Decide in scope whether to reconcile the schema; if "build the skill" excludes running evals, document the deferral; otherwise convert the suite to the `name`/`cases` format used by `evals/suite.json` |
| `skill-creator` named in the ticket is absent in-repo (ref: Q2) | high | med | Treat skill-creator as a global tool used to author the files; do not depend on any in-repo skill-creator artifact; flag as Open Question |
| SKILL.md exceeds the 500-line/5000-token budget — no validator enforces it and `qrspi-work` already overruns (ref: Q7, Q9) | med | med | Aggressively offload to `references/` (Decision 2); measure with `wc -l`/`wc -c` (bytes/4 ≈ tokens) before finishing (ref: Q7) |
| Trigger/auto-invocation cannot be verified — no in-repo trigger-accuracy tooling (ref: Q10, Q11) | med | low | Hand-craft `description` with front-loaded trigger phrases per the `qrspi-work`/`qrspi-questions` pattern (ref: Q5); accept that firing is unverifiable in-repo |
| Frontmatter malformed — no schema validator catches it (ref: Q9) | low | med | Copy the field shape from an existing SKILL.md verbatim; quote `description` if it contains `:`/`'`/commas (ref: Q3, Q5) |

## Open Questions

- OQ1: Is "build using the Anthropic skill builder skill" a hard process requirement, given skill-creator is out of repo scope (ref: Q2)? If yes, the human must confirm skill-creator is available in the build environment.
- OQ2: Does this ticket's Definition of Done include running `evals/graphite-evals.json` through the harness? If so, the schema mismatch with `run_eval.py` must be reconciled first (ref: Q9, Q10).
- OQ3: Should the skill execute `gt` commands (needs `Bash` in `allowed-tools`) or only advise the orchestrating agent? This determines Decision 3's final value.
- OQ4: Should `references/` be split into two files (command-reference + edge-cases) or one combined file? Only `qrspi-work` precedent exists (single reference file) (ref: Q6).
