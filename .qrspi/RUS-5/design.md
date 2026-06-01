# Design — Create a new agent skill called writing bash scripts

**Ticket:** RUS-5
**Research basis:** research.md @ 2026-06-01T00:00:00Z
**Generated:** 2026-06-01T00:00:00Z
**Status:** draft

## Current State

The repo holds 10 skills, each at `.claude/skills/<name>/SKILL.md`, where the directory name equals the frontmatter `name` and the `command` suffix (ref: Q1). Only one skill (`qrspi-work`) uses a subdirectory — a `references/` folder holding `review-cascade.md`; no skill in the repo uses `scripts/` or `assets/` (ref: Q1). Reference inclusion is not automatic: the SKILL.md body carries a literal "Read references/<file>.md" instruction and the agent performs an on-demand read with a path relative to the skill directory (ref: Q2). Subdirectories exist only when they hold a file — there are no empty `references/`/`scripts/`/`assets/` dirs and no `.gitkeep` placeholders inside skills (ref: Q9).

Every in-repo SKILL.md uses frontmatter keys in fixed order: `name`, `description`, `command`, `argument-hint`, `allowed-tools`; `description` is quoted only when it embeds a colon or apostrophe (ref: Q3). There is no in-repo validator for frontmatter, naming collisions, versioning, or the ≤500-line / ≤5000-token body limit — registration is by file presence and the limit is an external convention (ref: Q3, Q4, Q6, Q7). The `skill-creator`/skill-builder skill named by the ticket is an external/global skill and is NOT present in this repo (ref: Q1, Q3, Q12).

ShellCheck is NOT installed in this environment and is not in the devcontainer Dockerfile; BATS is also absent and no `*.bats` files or bash test runner exist (ref: Q8, Q11). The repo's own bash scripts are hand-written ShellCheck-clean using `#!/usr/bin/env bash` (or `#!/bin/bash`), `set -euo pipefail`, and `${1:?usage}` arg guards; the only ShellCheck reference is one surgical `# shellcheck disable=SC2053` directive (ref: Q8, Q11). No repo script uses a `BASH_SOURCE`-guarded `main` pattern (ref: Q11). The repo does have a Python eval harness (`run_loop.sh` → `run_eval.py` → `grade.py` → `report.py`/`diagnose.py`/`revise.py`) whose cases live in `evals/suite.json` and require `id`, `prompt`, `assertions` with types `programmatic`|`llm_judge`|`script`; `grade.py` exposes a `line_count(...)` check (ref: Q5, Q7, Q10). The harness's `execute_single` is currently a stub that invokes no agent and returns empty output (ref: Q5, Q10).

## Desired End State

A new skill exists at `.claude/skills/writing-bash-scripts/SKILL.md` plus a `references/` directory, encoding the bash conventions in the ticket.

- **AC: agentskills.io directory structure with valid SKILL.md frontmatter** — The skill is a directory `writing-bash-scripts/` containing `SKILL.md` whose frontmatter matches the in-repo five-key schema in fixed order, with `name: writing-bash-scripts` equal to the directory name (ref: Q1, Q3).
- **AC: built using the Anthropic skill builder skill** — Authoring is performed by invoking the external `skill-creator` skill (available in the harness list, not in-repo) to scaffold and refine the skill; the process step is satisfied by using that skill rather than hand-rolling (ref: Q1).
- **AC: SKILL.md body under 500 lines / 5000 tokens** — The body stays lean and defers detail to `references/`; since no in-repo gate enforces this (ref: Q7), it is satisfied by construction and checked by hand against a line count.
- **AC: detailed reference material in references/ if needed** — Deep material (subcommand dispatcher, full templates, gotchas, portability matrix, testing) lives in `references/*.md`, pulled in via explicit "Read references/<file>.md" instructions in the body (ref: Q2).
- **AC: produces ShellCheck-clean output when an agent follows the guidance** — The guidance encodes the exact conventions the repo's hand-clean scripts already use (strict mode, full quoting, dependency checks). Because ShellCheck is not installed (ref: Q8), the criterion is convention-enforced; the design flags installing ShellCheck as the only way to mechanically verify it (Open Question OQ1).

The skill content encodes all ticket-specified conventions: strict-mode header, error handling and traps, argument parsing (getopts / while-case, never GNU getopt), the subcommand dispatcher pattern for 2+ operations, logging helpers with TTY-gated color, quoting rules, dependency checks, heredoc usage, mktemp temp files, code organization order, `main "$@"` sourcing guard, ShellCheck/BATS testing guidance, portability notes, and a gotchas section.

## Delta

New files:
- `.claude/skills/writing-bash-scripts/SKILL.md` — frontmatter (five keys, fixed order) plus a lean body: when-to-use, the non-negotiable defaults (strict mode, quoting, stderr/stdout discipline, exit codes), the decision rule for the subcommand pattern (2+ operations), and explicit "Read references/<file>.md" pointers for depth.
- `.claude/skills/writing-bash-scripts/references/patterns.md` — full templates: strict-mode header, trap-based cleanup/ERR, logging helpers, getopts vs while-case parsing, subcommand dispatcher (`cmd_*` + `declare -f`), `usage()` heredoc, `mktemp` + EXIT trap, dependency checks, and the canonical code-organization order with the `BASH_SOURCE` main guard.
- `.claude/skills/writing-bash-scripts/references/gotchas.md` — common pitfalls (unquoted vars, missing `--`, `cd` without `||` guard, masked `local` exit codes) and the portability matrix (bash 4+ vs macOS 3.2, BSD vs GNU `sed`/`date`/`grep`).

Optional (see Decision 3):
- `evals/suite.json` cases for `writing-bash-scripts`, following the existing case schema (`id`, `prompt`, `assertions`) (ref: Q10).

Modified files: none required for the skill to register (registration is file-presence based, ref: Q4). The `description` frontmatter value must embed concrete trigger phrases, since `description` is the trigger-match corpus (ref: Q4).

No new queries, middleware, or DB changes — this feature is documentation/skill content only.

## Pattern Decisions

### Decision 1: Body/reference split

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Everything inline in one SKILL.md | Single file; no read step | Risks blowing the ≤500-line budget; the ticket's full templates are long |
| B | Lean SKILL.md + `references/patterns.md` + `references/gotchas.md`, pulled via explicit Read instructions | Matches the only in-repo multi-file skill (`qrspi-work`); keeps body well under budget; defers depth | Two extra files; agent must follow the read pointer |

**Recommendation:** Option B
**Rationale:** Mirrors the sole in-repo reference pattern (`qrspi-work` body says "Read references/review-cascade.md") and keeps the body lean against the ≤500-line AC (ref: Q2, Q7).
**NEW PATTERN?** No — directly reuses the `qrspi-work` references pattern.

### Decision 2: Authoring mechanism

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Invoke external `skill-creator` skill to scaffold/refine | Satisfies the "built using skill builder" AC; gets description-optimization | Skill is external/global, not in-repo; output still must be reconciled to in-repo five-key schema |
| B | Hand-author following the in-repo SKILL.md convention | Full control over schema/order match | Fails the explicit process AC requiring the builder |

**Recommendation:** Option A, then normalize output to the in-repo frontmatter schema
**Rationale:** The ticket process step and an AC both mandate the skill builder; the in-repo frontmatter convention (five keys, fixed order, name=dir) is the reconciliation target (ref: Q1, Q3).
**NEW PATTERN?** No — uses an existing external skill; output conforms to existing in-repo convention.

### Decision 3: Eval coverage for the skill

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Add `evals/suite.json` cases for the skill | Fits existing harness schema; future regression coverage | `execute_single` is a stub (no real agent run yet), so cases would not actually execute (ref: Q5, Q10) |
| B | Ship skill only; no eval cases now | Avoids dead cases against a stubbed runner | No automated coverage; AC verification stays manual |

**Recommendation:** Option B for this ticket; revisit when the harness runner is wired
**Rationale:** The eval runner is a stub today (ref: Q5, Q10), so eval cases would not execute; adding them now yields no signal. The ShellCheck AC is better verified by installing ShellCheck (OQ1) than by stubbed eval cases.
**NEW PATTERN?** No.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| ShellCheck-clean AC cannot be mechanically verified — ShellCheck not installed (ref: Q8) | high | med | Resolve OQ1: add `shellcheck` to the devcontainer Dockerfile, or manually lint a representative generated script; otherwise mark the AC convention-enforced |
| External skill-builder output diverges from in-repo five-key frontmatter schema (ref: Q3) | med | low | Normalize frontmatter to the fixed-order five keys; set `name` = `writing-bash-scripts` = directory name |
| SKILL.md body exceeds the ≤500-line / ≤5000-token AC with no in-repo gate to catch it (ref: Q7) | med | med | Enforce the body/reference split (Decision 1); hand-check line count before approval |
| `description` lacks concrete trigger phrases, so the skill never auto-invokes (ref: Q4) | med | med | Embed explicit trigger phrases in `description` following the `qrspi-work` example |
| BATS/`BASH_SOURCE` guidance the skill teaches is unvalidated by any repo tooling (ref: Q11) | low | low | Present as recommendation; do not claim repo-enforced; keep examples self-contained |

## Open Questions

- OQ1: Should this ticket also add `shellcheck` (and optionally `bats`) to the devcontainer Dockerfile so the "ShellCheck-clean output" AC can be mechanically verified, or is convention-only enforcement acceptable for now? (ref: Q8, Q11)
- OQ2: What exact trigger phrases should the `description` carry for auto-invocation (e.g., "write a bash script", "shell script", ".sh file"), given `description` is the sole trigger corpus? (ref: Q4)
- OQ3: Is the ~200-line ceiling the skill recommends ("suggest a different language beyond ~200 lines") intended as hard guidance the skill enforces, or advisory?
