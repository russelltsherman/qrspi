# Design — Create a new agent skill called using-graphite-cli

**Ticket:** RUS-6
**Research basis:** research.md @ 2026-05-31T10:30:00Z
**Generated:** 2026-05-31T10:35:00Z
**Status:** draft

## Current State

The repository has ten skills under `.claude/skills/<name>/`, each with a YAML-frontmatter `SKILL.md`. Most are thin wrappers (~25-35 lines) that delegate to a paired sub-agent at `.claude/agents/<name>.md`; the largest skill (`qrspi-work`) is 730 lines and is the only one that uses a `references/` subdirectory (ref: Q1, Q13). No skill currently teaches an agent how to use the Graphite CLI (`gt`) directly. All Graphite knowledge is embedded inline inside `qrspi-work/SKILL.md` as part of the QRSPI workflow orchestration, not extracted as a reusable agent skill (ref: Q3).

The repo assumes `gt` is pre-installed, pre-authenticated, and that the trunk branch is already configured. No skill documents `brew install graphite`, `gt auth login`, or `gt repo init` (ref: Q5, Q6). Onboarding is implicit. The strongest convention is that every `gt` invocation passes `--no-interactive`, and the orchestrator is the only place where git/graphite mutations happen — sub-agents never commit (ref: Q3, Q12).

Single-commit-per-branch is doctrinal but enforced by skill instruction only: there is no pre-commit hook, no CI workflow, and no lint check (ref: Q8). Planning uses one commit amended with `gt modify`; each implementation slice is a fresh branch via `gt create` then amended with `gt modify`. The repo also forbids the `-a` and `-u` staging flags during normal flow to prevent capturing untracked files (ref: Q3, "NEVER use `-a` flag" — `.claude/skills/qrspi-work/SKILL.md:642`).

For error handling, the orchestrator devotes a full section to a HARD STOP rule for infrastructure errors: never use raw `git` to bypass a broken `gt`, never `chmod`/`chown`/`sudo`, never reroute config (ref: Q7). The one documented exception is `git worktree` operations, which `gt` does not wrap. For semantic gt failures (conflicts), the convention `gt continue` (never `git rebase --continue`) appears only in the RUS-6 ticket body — it is not documented in any existing skill (ref: Q7).

Evaluation infrastructure exists. `evals/graphite-evals.json` already contains 5 cases targeting commit, submit, log, move, and sync intents, but its schema diverges from `evals/suite.json` (top-level `evals` vs `cases`; assertion types `command_check`/`flag_check`/`safety_check`/`workflow_check`/`content_check` are not implemented in `scripts/grade.py`) (ref: Q10, Inconsistency 4). The graphite eval will not run through the existing pipeline without an adapter or a schema update. Two factual inconsistencies in the existing eval also need addressing: case 1 expects `-a` or `-u` staging flags that contradict the orchestrator's "NEVER `-a`" rule (ref: Q3, Inconsistency 5).

Skill naming follows kebab-case with a `qrspi-` prefix for workflow phases. The proposed name `using-graphite-cli` matches the kebab-case pattern and correctly omits the `qrspi-` prefix because the skill is not a QRSPI phase (ref: Q14).

## Desired End State

After this ticket ships, the repo contains a new skill at `.claude/skills/using-graphite-cli/` that any agent (QRSPI orchestrator or otherwise) can consult before issuing Graphite commands. The skill embodies the conventions surfaced in the ticket and aligns with existing repo practice. The skill must satisfy every acceptance criterion in the ticket:

- AC: agentskills.io directory structure with valid SKILL.md frontmatter → SKILL.md exists with `name`, `description`, `command`, `argument-hint`, `allowed-tools` fields matching the repo's observed convention.
- AC: built using the Anthropic skill-builder skill → invocation of the global skill-creator skill is mandated as part of slice 1 validation (the structure phase already names skill-creator as a validation step — `.claude/agents/qrspi-structure.md:41`).
- AC: SKILL.md body under 500 lines / 5000 tokens → SKILL.md kept under 500 lines; long-form material lives in `references/` siblings.
- AC: detailed reference material in `references/` covering full command reference and edge cases → at least two reference files: `command-reference.md` (full command list and flags) and `edge-cases.md` (conflict resolution, stale worktree recovery, multi-commit detection).
- AC: encodes single-commit-per-branch as a hard rule → SKILL.md states the rule in its conventions section with explicit "do this / not that" examples.
- AC: covers Create → Submit → Modify → Sync loop → dedicated workflow section in SKILL.md walks through each step in order.
- AC: documents conflict resolution flow with `gt continue` (never `git rebase --continue`) → explicit do/don't pair in the edge-cases reference.
- AC: includes stack navigation commands and directionality conventions → SKILL.md or a navigation reference defines `gt bu` / `gt bd` / `gt stack top` / `gt log short` and the downstack/upstack vocabulary.
- AC: provides submit flag defaults (`--no-edit --publish`) for automated agent use → SKILL.md states the agent defaults in a "Submitting" subsection.
- AC: warns against mixing raw git branch/rebase with Graphite-tracked branches → SKILL.md "When NOT to use raw git" section, with the one documented exception (`git worktree`).

The skill is discoverable by skill name and triggers on any task that requires git/branch/PR operations in this repo. The eval harness at `evals/graphite-evals.json` is reconciled with the rest of the pipeline so the skill can be regression-tested.

## Delta

New files (created in `.worktrees/RUS-6/`):

1. `.claude/skills/using-graphite-cli/SKILL.md` — main skill body, target ~250 lines, hard max 500.
2. `.claude/skills/using-graphite-cli/references/command-reference.md` — comprehensive `gt` command list grouped by lifecycle phase.
3. `.claude/skills/using-graphite-cli/references/edge-cases.md` — conflict recovery, stale worktrees, multi-commit detection, infrastructure-error stop rule.
4. `.claude/skills/using-graphite-cli/references/onboarding.md` — install, auth, and `gt repo init` walkthrough (fills the gap from ref: Q6).

Modified files:

1. `evals/graphite-evals.json` — reconcile the staging-flag assertion conflict (Inconsistency 5) and add a discriminator key so the grader can route this suite separately, or migrate it onto the assertion vocabulary used by `evals/suite.json`. Exact reconciliation is a Pattern Decision (below).
2. `.claude/CLAUDE.md` — add a one-line pointer under "Available skills" advertising the new skill so agents discover it without having to grep.
3. `README.md` — optional one-line addition under usage; may be deferred to a follow-up.

No deletions. No changes to `qrspi-work/SKILL.md` — the existing inline Graphite knowledge there is the orchestrator's own runbook and stays in place; the new skill is a reference companion, not a replacement.

## Pattern Decisions

### Decision 1: Thin SKILL.md + references/ vs single fat SKILL.md

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Thin SKILL.md (~150-250 lines) with detailed material offloaded to `references/command-reference.md`, `references/edge-cases.md`, `references/onboarding.md`. | Matches the dominant repo pattern (ref: Q1, Q13); keeps the SKILL.md inside the 500-line budget; lets agents load just the relevant reference when needed. | Slightly more files to maintain; agents must know to read the references when situations arise. |
| B | Single SKILL.md ~400-500 lines, no references/ subdirectory. | Single-file simplicity; fewer indirections. | Pushes against the 500-line budget on every future addition; diverges from the qrspi-work pattern that already uses references/; long files are harder for agents to load selectively. |

**Recommendation:** Option A
**Rationale:** The repo's only example of `references/` already demonstrates the pattern (`qrspi-work/references/review-cascade.md`, ref: Q1). Splitting by topic ("how do I run a command" vs "what do I do when it fails" vs "how do I bootstrap") matches how an agent encounters problems at use time. The 500-line budget in the ticket is realistic only if long material is offloaded.
**NEW PATTERN?** No — `qrspi-work/references/` is the precedent.

### Decision 2: Staging convention — adopt orchestrator's "NEVER -a" rule or the existing eval's "-a/-u" expectation

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Adopt the orchestrator's "NEVER `-a`" rule as the skill's default; update `evals/graphite-evals.json` case 1 to expect explicit `git add <files>` followed by `gt create -m "…"` or `gt modify -m "…"`. | Internally consistent with `qrspi-work/SKILL.md:642` (ref: Q3); avoids capturing untracked files and avoids `gt undo` destroying untracked work; the new skill's guidance matches the orchestrator. | Existing eval case 1 must be modified — a one-time fix. |
| B | Adopt the eval's `-a`/`-u` expectation as the convention; keep the eval unchanged; document the orchestrator's "NEVER -a" rule as a QRSPI-only override. | No eval edits. | Two contradictory rules co-exist in the repo, requiring agents to know which "mode" they're in; the safety concern (`gt undo` destroys untracked) applies universally, not just to QRSPI. |

**Recommendation:** Option A
**Rationale:** The "NEVER -a" rule is a safety rule (ref: Q3, `.claude/skills/qrspi-work/SKILL.md:642-654`) that applies regardless of QRSPI context. The existing eval predates the orchestrator's hardening and is inconsistent with current practice (Inconsistency 5). Fixing the eval costs one file; fixing the inconsistency in the agent's mental model costs much more later.
**NEW PATTERN?** No — adopting the existing orchestrator rule.

### Decision 3: Eval schema — adapter, schema migration, or keep separate

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Keep `evals/graphite-evals.json` as a standalone suite outside the run_eval.py pipeline; the new skill documents that the existing case file is reference-only and not regression-tested until a future ticket migrates it. | No scope creep into the eval harness. | The eval harness remains inconsistent; the skill is technically untested by the harness. |
| B | Migrate `evals/graphite-evals.json` to the `evals/suite.json` schema (`cases` array, `programmatic`/`llm_judge`/`script` assertion types) so it can run through `run_eval.py`. | Single eval pipeline; the new skill is regression-tested from day one. | Requires careful translation of `command_check`/`flag_check`/`safety_check`/`workflow_check`/`content_check` into the existing assertion vocabulary; implementer must add new programmatic checks to `grade.py` for `command_check`-style assertions. |
| C | Leave the existing graphite-evals.json untouched and add a fresh eval file `evals/using-graphite-cli.json` matching `evals/suite.json` schema, focused on the new skill. | Cleanest separation; no edits to existing files; new skill ships with first-class evals. | Duplicates intent with the existing graphite-evals.json; future maintainers must reconcile. |

**Recommendation:** Option B
**Rationale:** The repo already invested in evaluating graphite intent (`evals/graphite-evals.json` exists, ref: Q10). The schema mismatch is a known gap (Inconsistency 4) and the orchestrator-aligned staging rule (Decision 2) already requires editing the file. While editing, also reshape it onto the existing pipeline schema rather than leaving two parallel evaluation surfaces. The cost is concentrated in one slice (translation + adding 2-3 programmatic check helpers to `grade.py`).
**NEW PATTERN?** No — `evals/suite.json` schema is the canonical pattern.

### Decision 4: Tool allowlist for the new skill

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | `allowed-tools: Read, Bash` — the skill is reference material; an agent reads the SKILL.md, then runs `gt` commands via Bash. | Minimal surface; matches the role of a reference skill. | None significant. |
| B | `allowed-tools: Read, Write, Bash` — also allow Write so an agent could (in theory) edit references during the same session. | More flexible. | Violates least-privilege; risks the skill's own files being edited mid-session. |

**Recommendation:** Option A
**Rationale:** The skill teaches `gt` usage; it does not edit files. Existing thin-wrapper skills declare only what they need (ref: Q4). The skill's purpose is consultation, not mutation, so Read + Bash is sufficient.
**NEW PATTERN?** No — least-privilege allowlist is the repo norm.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Skill content drifts from `qrspi-work/SKILL.md` over time (rules in two places). | high | medium | Adopt the orchestrator's existing rules verbatim where possible; reference `qrspi-work/SKILL.md` line numbers in a "See also" footer of the new SKILL.md so future edits cross-pollinate. Consider a follow-up ticket to extract the orchestrator's Graphite-specific guidance into the new references/. |
| The new skill expands beyond its scope and becomes a general "git/graphite tutorial," not an agent skill. | medium | medium | Bound the skill to agent-actionable rules: each section ends with a concrete `do this` / `not that` pair. No background on git internals. Hard cap SKILL.md at 500 lines and enforce in slice verification (`wc -l < 500`). |
| Eval schema migration in Decision 3 introduces flakiness in the existing eval pipeline. | medium | medium | Add programmatic checks to `grade.py` with explicit unit-style verification before wiring assertions into a case. Run the new suite via `run_eval.py` with a single trial first; expand to 3 trials only after stability. |
| Agents read SKILL.md but never load `references/` files, so edge-case guidance never reaches the use site. | medium | high | SKILL.md "When you hit a problem" subsection links to each reference by name and one-sentence summary, mirroring how `qrspi-work/SKILL.md` links to `references/review-cascade.md` only when actually navigating cascade logic. Keep references short (< 200 lines each). |
| The ticket says "use the Anthropic skill builder skill" but the skill-creator does not live in this repo (ref: Q11). | medium | medium | Slice 1 invokes the global skill-creator as a generation aid, then commits the output into the repo. The skill-creator is consulted for structure/discipline but the deliverable is committed source under this repo's git history. If skill-creator is unavailable, fall back to hand-authoring with the same structural template — flag this as a deviation in the impl-log. |
| Staging-rule change in `evals/graphite-evals.json` breaks downstream tooling that consumed the old eval. | low | low | The schema is JSON consumed by `scripts/grade.py`; grep confirms no other consumers in-repo. After edit, run `python scripts/grade.py --help` or equivalent smoke test. |

## Open Questions

- OQ1: Does Russell want the new skill to handle the global onboarding gap (install, auth, `gt repo init`) as part of `references/onboarding.md`, or is onboarding considered out of scope for an agent skill (i.e., assumed pre-condition)? The ticket lists install/auth conventions but doesn't explicitly require them in the deliverable.
- OQ2: For Decision 3 (eval schema), is the implementer authorized to extend `scripts/grade.py` with new programmatic checks (e.g., `command_used('gt')`, `flag_present('--no-interactive')`), or should the assertions be expressed only via regex matches on the captured output? The former is cleaner but expands the eval framework.
- OQ3: Should the new skill set `model: opus` in its frontmatter? No existing SKILL.md sets `model` (ref: Q2) but every agent prompt does. If skill-level `model` is not supported by the harness, this is a non-question; if it is, picking `opus` matches the agent prompts and matches the difficulty of the task.
- OQ4: The ticket mentions `gt branch split` as a way to split large branches. No existing skill or doc uses this command. Should it be documented in `references/command-reference.md` even though the repo has no precedent for invoking it?
