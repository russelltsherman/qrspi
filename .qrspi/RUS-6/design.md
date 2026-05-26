# Design -- Create a new agent skill called using graphite cli

**Ticket:** RUS-6
**Generated:** 2026-05-26
**Status:** draft

## Current State

Skills in this project live under `.claude/skills/<skill-name>/SKILL.md`, with each skill getting its own directory named after the skill (ref: Q2). There are currently 10 skills, all following the QRSPI workflow naming convention. Only one skill (`qrspi-work`) has a `references/` subdirectory (ref: Q2).

Every SKILL.md uses identical YAML frontmatter with exactly five fields: `name`, `description`, `command`, `argument-hint`, and `allowed-tools`. No skill uses additional fields such as `triggers` or `version` (ref: Q4). The `description` field doubles as the trigger-matching text for the Claude Code skill dispatcher (ref: Q4). The `allowed-tools` field creates a least-privilege boundary -- read-only tools for research phases, full Bash access for implementation phases (ref: Q4).

Reference files are loaded explicitly by `Read` instructions within the SKILL.md body, not auto-loaded (ref: Q5, Q8). There is no manifest, indexing convention, or load-order mechanism (ref: Q8).

The skill-creator skill is external to this project, provided by the Claude Code harness (ref: Q1). Its validation logic and frontmatter schema enforcement are not inspectable from within this codebase (ref: Q1). No local enforcement mechanism validates the 500-line or 5000-token constraint on SKILL.md bodies (ref: Q6, Q10).

The project has a complete eval loop (`run_loop.sh` orchestrating `run_eval.py`, `grade.py`, `diagnose.py`, `revise.py`, `report.py`) that persists state to disk between iterations (ref: Q3, Q7). Two eval suite formats coexist: `suite.json` uses `{type, check, weight}` assertions with function references, while `graphite-evals.json` uses `{text, type}` assertions with descriptive labels (ref: Q12). The `grade.py` script can only process `suite.json` format assertions; there is no grading implementation for the `graphite-evals.json` format (ref: Q12, Q13).

A `graphite-evals.json` file already exists with 5 eval cases targeting a skill named `"graphite"`, but no corresponding `.claude/skills/graphite/` directory exists (ref: Q13). The evals test commit, push, log, move, and sync operations and use assertion types (`command_check`, `flag_check`, `content_check`, `workflow_check`, `safety_check`) that have no corresponding grading implementation (ref: Q13).

Skill loading does not verify that external CLIs are installed; failure is deferred to invocation time (ref: Q11). The existing `qrspi-work` skill treats "command not found" as an infrastructure error that triggers a hard stop (ref: Q11). The `qrspi-work` skill already mandates `gt` commands with `--no-interactive` flags and forbids raw `git` except for `git add` and `git status --short` (ref: Q11, research Discovered Patterns 8).

The existing `graphite-evals.json` asserts that `-a` or `-u` flags should be used for staging, but `qrspi-work/SKILL.md` explicitly forbids the `-a` flag (ref: research Inconsistency 4). This contradiction must be resolved during implementation.

No structured telemetry or logging is emitted upon skill invocation; this is handled externally by the Claude Code harness (ref: Q14).

## Desired End State

Each acceptance criterion mapped to a concrete system behavior:

**AC: Skill follows agentskills.io directory structure with valid SKILL.md frontmatter.** A new directory `.claude/skills/using-graphite-cli/` contains a `SKILL.md` with the five standard frontmatter fields (`name`, `description`, `command`, `argument-hint`, `allowed-tools`), consistent with all 10 existing skills.

**AC: Built using the Anthropic skill builder skill.** The skill-creator skill is invoked to generate and refine the SKILL.md through its eval loop. The final artifact is the output of that process, not a hand-authored file.

**AC: SKILL.md body under 500 lines / 5000 tokens.** The SKILL.md body (excluding frontmatter) stays under 500 lines. Detailed reference material is offloaded to `references/` files to keep the body concise.

**AC: Detailed reference material in references/ directory covering full command reference and edge cases.** A `references/` directory contains one or more markdown files with the complete `gt` command reference, flag details, edge cases, and conflict resolution procedures. These files are loaded explicitly by `Read` instructions in the SKILL.md body.

**AC: Encodes the single-commit-per-branch convention as a hard rule.** The SKILL.md body contains an unambiguous directive that each Graphite branch must have exactly one commit, with `gt create` for new branches and `gt modify --all` for amendments.

**AC: Covers the complete Create -> Submit -> Modify -> Sync workflow loop.** The SKILL.md body describes the full lifecycle loop with the specific `gt` commands for each step.

**AC: Documents conflict resolution flow using gt continue (never git rebase --continue).** The conflict resolution procedure is documented with `gt continue` as the only permitted resolution command.

**AC: Includes stack navigation commands and directionality conventions.** The SKILL.md body or reference material includes `gt bu`, `gt bd`, `gt stack top`, `gt log short`, and the directionality definitions (downstack = toward trunk, upstack = away from trunk).

**AC: Provides submit flag defaults (--no-edit --publish) for automated agent use.** The SKILL.md body specifies `--no-edit --publish --no-interactive` as the default flags for `gt submit` in automated contexts.

**AC: Warns against mixing raw git branch/rebase commands with Graphite-tracked branches.** The SKILL.md body contains an explicit prohibition on `git branch`, `git rebase`, and `git commit --amend` on Graphite-tracked branches, with permitted exceptions listed (e.g., `git add`, `git status`).

## Delta

### New Files

| File | Purpose | Approximate Size |
|---|---|---|
| `.claude/skills/using-graphite-cli/SKILL.md` | Main skill definition with frontmatter, core workflow rules, and Read instructions pointing to references | 150-300 lines |
| `.claude/skills/using-graphite-cli/references/command-reference.md` | Complete gt command reference with flags, examples, and edge cases | 200-400 lines |
| `.claude/skills/using-graphite-cli/references/conflict-resolution.md` | Detailed conflict resolution procedures, restack flows, and recovery from common errors | 50-100 lines |

### Modified Files

| File | Change | Rationale |
|---|---|---|
| `evals/graphite-evals.json` | Fix the `-a` flag assertion in eval case 1 to align with the skill's staging rules; update `skill_name` to `using-graphite-cli` | Resolve inconsistency 4 from research; align eval with the actual skill name |

### No Changes Required

| File | Reason |
|---|---|
| `scripts/grade.py` | Graphite evals use a different assertion format; grading infrastructure for `command_check`/`flag_check` types is out of scope for this ticket |
| `scripts/run_loop.sh` | The eval orchestrator does not need changes to support a new skill |
| `.claude/CLAUDE.md` | The skill is auto-discovered by the harness from the directory; no manual registration required |

## Pattern Decisions

### Decision 1: Skill Directory Name

| Option | Pros | Cons | Recommendation |
|---|---|---|---|
| `using-graphite-cli` | Matches ticket title; descriptive for non-QRSPI consumers; distinguishes from QRSPI-specific skills | Breaks the `qrspi-` naming prefix convention used by all 10 existing skills | RECOMMENDED |
| `qrspi-graphite` | Consistent with existing naming convention | Implies the skill is QRSPI-specific when it is general-purpose; misleading | Not recommended |
| `graphite` | Short; matches `skill_name` in existing `graphite-evals.json` | Too generic; does not describe what the skill does | Not recommended |

This is a NEW PATTERN. All existing skills use the `qrspi-` prefix. This skill is intentionally general-purpose (not tied to the QRSPI workflow), so the different naming convention is deliberate. The `description` field in the frontmatter is what drives trigger matching, not the directory name, so there is no functional impact.

### Decision 2: Reference File Organization

| Option | Pros | Cons | Recommendation |
|---|---|---|---|
| Two files: `command-reference.md` + `conflict-resolution.md` | Separation of concerns; agents can load only what they need for a given task | Two explicit Read instructions in SKILL.md body | RECOMMENDED |
| Single file: `reference.md` | Simpler; single Read instruction; matches existing `qrspi-work` pattern (one reference file) | Large single file; agent must load conflict resolution details even for simple operations | Not recommended |
| Three+ files: one per workflow phase | Maximum granularity | Over-engineered; increases SKILL.md body size with multiple Read instructions | Not recommended |

This follows the EXISTING PATTERN from `qrspi-work/references/`, extending it from one reference file to two. The loading mechanism (explicit `Read` instructions in the SKILL.md body) is identical.

### Decision 3: allowed-tools Scope

| Option | Pros | Cons | Recommendation |
|---|---|---|---|
| `Bash` (unrestricted) | Skill needs to run `gt`, `git add`, `git status`, and potentially other CLI commands; restricting to specific patterns is fragile since `gt` subcommands vary widely | Broader permission surface than strictly necessary | RECOMMENDED |
| `Bash(gt:*), Bash(git add:*), Bash(git status:*)` | Least-privilege; only allows known-safe commands | May break on valid `gt` invocations that do not pattern-match; `gt` commands include flags that change the pattern shape | Not recommended |

This follows the EXISTING PATTERN from `qrspi-work` and `qrspi-implement`, which both use unrestricted `Bash`.

### Decision 4: Eval Suite Alignment

| Option | Pros | Cons | Recommendation |
|---|---|---|---|
| Fix `graphite-evals.json` to match new skill name and resolve contradictions; leave assertion format as-is | Minimal change; resolves the known `-a` flag inconsistency; preserves existing evals for future grading infrastructure | Assertion format remains incompatible with `grade.py` | RECOMMENDED |
| Convert `graphite-evals.json` to `suite.json` format | Makes evals runnable through existing pipeline | Significant refactor; `run_eval.py` execution is still a stub anyway; the assertions need different grading functions | Not recommended |
| Do not touch `graphite-evals.json` | No risk of breaking existing expectations | Leaves inconsistency 4 unresolved; `skill_name` will remain mismatched | Not recommended |

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Skill-creator skill produces output that does not conform to the five-field frontmatter schema observed in all existing skills | Medium | High -- skill would not load or trigger correctly | Provide the exact frontmatter template as input to skill-creator; validate output against existing skills before accepting |
| SKILL.md body exceeds 500-line limit due to comprehensive Graphite documentation | High | Medium -- violates acceptance criterion; may degrade skill performance if the prompt is too long | Aggressively offload details to `references/` files; keep SKILL.md body focused on rules and decision logic, not command encyclopedias |
| `--no-interactive` flag not supported by all `gt` subcommands, causing runtime failures | Low | Medium -- agent would hit errors on specific operations | Document which `gt` commands support `--no-interactive` in reference material; test against actual Graphite CLI version |
| New naming convention (`using-graphite-cli` vs `qrspi-` prefix) causes confusion about skill categorization | Low | Low -- purely organizational; no functional impact on skill dispatch | Document the naming rationale in this design; the trigger description, not the directory name, controls dispatch |
| Conflict between `graphite-evals.json` `-a` flag assertion and the skill's staging rules persists if not explicitly resolved | High | Medium -- evals would fail on correct skill behavior, undermining eval loop trustworthiness | Resolve in this ticket by updating the eval assertion; document the decision |

## Open Questions

1. **Staging convention: should the skill use `--all` flag on `gt create`/`gt modify`, or require explicit `git add` before each operation?** The ticket description says `gt create --all`, but `qrspi-work/SKILL.md` explicitly forbids the `-a` flag and requires explicit staging. The existing `graphite-evals.json` asserts `-a` or `-u` is used. These three sources contradict each other. A human decision is needed on the canonical staging rule before implementation.

2. **Should the skill include a `--no-interactive` flag on every `gt` command?** The existing `qrspi-work` skill and `graphite-evals.json` both use `--no-interactive` extensively, but the ticket description does not mention this flag. Since agents cannot respond to interactive prompts, `--no-interactive` seems necessary, but confirming this as a hard rule requires human sign-off.

3. **Should the eval assertions in `graphite-evals.json` be updated to match the skill or left as a separate concern for a future ticket?** This design recommends updating them, but the ticket scope says "create a skill," not "fix existing evals." If eval updates are out of scope, the inconsistency should be tracked as a separate issue.
