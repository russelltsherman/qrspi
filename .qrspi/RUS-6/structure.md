# Structure Outline — Create a new agent skill called using-graphite-cli

**Design basis:** design.md @ 2026-05-31T10:35:00Z
**Generated:** 2026-05-31T10:40:00Z
**Status:** draft

## New Types

(This ticket adds no runtime types — it adds documentation and adjusts an eval config. The "types" below are file-shape contracts that downstream slices and the eval pipeline rely on.)

- `SkillFrontmatter { name: string, description: string, command: string, argument-hint: string, allowed-tools: string }` — YAML frontmatter shape every SKILL.md uses in this repo (ref: design.md Delta).
- `EvalCase { id: string, name: string, phase: string, prompt: string, context: { files: string[], conversation_history: any[], user_preferences: object }, assertions: { type: 'programmatic' | 'llm_judge' | 'script', check?: string, criteria?: string, weight: number }[], tags: string[], difficulty: 'easy' | 'medium' | 'hard', split: 'train' | 'test' }` — case shape used by `evals/suite.json`; the migrated `evals/graphite-evals.json` must match.

## Modified Types

- `evals/graphite-evals.json` top-level shape — change `{ skill_name, evals: [...] }` to `{ name, version, description, defaults, cases: [...] }` matching `evals/suite.json`. Update case shape from `{ id, prompt, expected_output, files, assertions: [{ text, type }] }` to the EvalCase shape above (ref: design.md Delta, Decision 3).

## Contracts

- `programmatic_check(check_string, output_dir) -> bool` — implemented in `scripts/grade.py`. Slice 2 may add new programmatic checks: `command_used(args, expected_cmd)`, `flag_present(args, expected_flag)`, `no_solution_language(file)` already exists per `evals/suite.json:51-56`. Exact additions are constrained by what `grade.py` already supports — slice 2 inspects `grade.py` before adding new check names.
- SKILL.md links to `references/` files — links use repo-relative paths (e.g., `references/command-reference.md`), consistent with how `qrspi-work/SKILL.md` references `references/review-cascade.md`.
- The new skill MUST be discoverable by the harness via the `name` field in its SKILL.md frontmatter being unique across `.claude/skills/`. The name `using-graphite-cli` is verified not to collide via `ls .claude/skills/`.

## Slice 1: Author the using-graphite-cli skill

**Goal:** A reviewer can read `.claude/skills/using-graphite-cli/SKILL.md`, follow its links to `references/command-reference.md`, `references/edge-cases.md`, and `references/onboarding.md`, and verify that every acceptance criterion from the ticket has corresponding skill content. Discovery works: `ls .claude/skills/using-graphite-cli/` shows the four files and `head -10 .claude/skills/using-graphite-cli/SKILL.md` shows valid frontmatter.

**Files touched:**

- ✨ `.claude/skills/using-graphite-cli/SKILL.md` — main skill, ~250 lines, hard max 500. Includes frontmatter, "When to use", Initialization preconditions, Core Workflow (Create → Submit → Modify → Sync), Single-commit-per-branch rule, Stack navigation, Submit defaults, "When NOT to use raw git", links to references.
- ✨ `.claude/skills/using-graphite-cli/references/command-reference.md` — full `gt` command list grouped by lifecycle (Init/Auth, Create, Submit, Modify, Sync, Navigate, Stack ops, Conflict). Target ~200 lines.
- ✨ `.claude/skills/using-graphite-cli/references/edge-cases.md` — conflict recovery via `gt continue`, stale worktree recovery, multi-commit detection, HARD STOP rule for infrastructure errors. Target ~150 lines.
- ✨ `.claude/skills/using-graphite-cli/references/onboarding.md` — install (brew, npm), `gt auth login`, `gt repo init --trunk main`, verifying trunk via `gt repo trunk`. Target ~80 lines.
- ⚠️ `.claude/CLAUDE.md` — add a single line under "Available skills" pointing to the new skill (one-line edit).

**Verification:**

- [ ] `wc -l .claude/skills/using-graphite-cli/SKILL.md` returns < 500.
- [ ] `head -10 .claude/skills/using-graphite-cli/SKILL.md` shows valid YAML frontmatter with all five required fields (`name`, `description`, `command`, `argument-hint`, `allowed-tools`).
- [ ] `grep -c 'gt continue' .claude/skills/using-graphite-cli/references/edge-cases.md` returns ≥ 1.
- [ ] `grep -E 'single.commit|one commit' .claude/skills/using-graphite-cli/SKILL.md` returns at least one hit.
- [ ] `grep -E 'Create.*Submit.*Modify.*Sync|Create.*->.*Submit' .claude/skills/using-graphite-cli/SKILL.md` returns at least one hit (workflow loop documented).
- [ ] `grep -E 'gt bu|gt bd|gt stack top|gt log short' .claude/skills/using-graphite-cli/SKILL.md` returns at least one hit (navigation commands).
- [ ] `grep -E '\-\-no-edit|\-\-publish' .claude/skills/using-graphite-cli/SKILL.md` returns at least one hit (submit defaults).
- [ ] `grep -E 'never .*git rebase|do NOT.*git rebase|raw git' .claude/skills/using-graphite-cli/SKILL.md` returns at least one hit.
- [ ] Manual: invoke the global skill-creator skill to review the new SKILL.md and apply any structural feedback (the ticket's "built using the Anthropic skill builder skill" AC). If skill-creator is unavailable, note the deviation in impl-log.md.

**Context cost:** M
**Depends on:** none

## Slice 2: Reconcile evals/graphite-evals.json with the suite pipeline

**Goal:** A reviewer can run `python scripts/run_eval.py` (or whatever the existing pipeline expects — slice begins by inspecting `scripts/run_eval.py` to confirm) targeting the migrated `evals/graphite-evals.json` and see cases execute through `scripts/grade.py` with programmatic assertions producing real scores. The staging-flag inconsistency (orchestrator says "NEVER -a" but eval case 1 expects `-a` or `-u`) is fixed in favor of the orchestrator's rule.

**Files touched:**

- ⚠️ `evals/graphite-evals.json` — migrate to `evals/suite.json` schema (top-level `name`, `version`, `description`, `defaults`, `cases`); restructure each case to the EvalCase shape; rewrite assertions as `programmatic`/`llm_judge` entries that `grade.py` can consume; reverse the staging assertion in case 1 to expect explicit `git add <files>` followed by `gt create`/`gt modify` (no `-a`/`-u`).
- ⚠️ `scripts/grade.py` — add programmatic check helpers if needed for command/flag verification. Slice begins by reading `grade.py` to inventory existing checks; only adds new ones if the existing vocabulary cannot express the assertions.

**Verification:**

- [ ] `python -c "import json; json.load(open('evals/graphite-evals.json'))"` succeeds (valid JSON).
- [ ] `jq '.cases | length' evals/graphite-evals.json` returns 5 (case count preserved).
- [ ] `jq '.cases[].assertions[].type' evals/graphite-evals.json | sort -u` returns only `"programmatic"`, `"llm_judge"`, and/or `"script"` (no legacy types).
- [ ] `grep -E '"-a"|"-u"' evals/graphite-evals.json` returns no hits in any check that would award credit (Inconsistency 5 resolved). Manual inspection of case 1's assertions confirms the staging convention matches the orchestrator's rule.
- [ ] If `scripts/grade.py` was modified, `python -m py_compile scripts/grade.py` succeeds.
- [ ] Smoke test: pick one case from the migrated file and run it through `scripts/run_eval.py` end-to-end. The run completes with a score (not necessarily passing — just no schema/runtime errors).

**Context cost:** M
**Depends on:** Slice 1 (the migrated eval cases assert behaviors documented in the SKILL.md; verifying assertions makes more sense after the skill exists)

---

## Unverified Assumptions

1. **The global skill-creator skill is accessible during slice 1 execution.** Design risk 5 acknowledges this. If the skill-creator is not available in the implementing agent's environment, slice 1 will fall back to hand-authoring per the design's mitigation and flag the deviation in `impl-log.md`. The verification step explicitly allows this fallback.
2. **`scripts/run_eval.py` accepts a JSON file matching the `evals/suite.json` schema.** Slice 2's verification depends on this. Slice 2 begins by reading `scripts/run_eval.py` to confirm the exact CLI and JSON shape it consumes. If the runner expects a different schema than `evals/suite.json` exhibits, slice 2 will adjust the migration target to match the runner's actual contract and note the discovery in `impl-log.md`.
3. **OQ1 (onboarding in scope) resolves to "yes."** Slice 1 includes `references/onboarding.md`. If the human reviewer rejects that scope during plan review, the onboarding file is the smallest deliverable to drop — it's a sibling reference, not a dependency of SKILL.md content.
4. **OQ2 (extending `grade.py`) resolves permissively.** Slice 2 may add new programmatic checks if needed. If review prefers regex-only assertions, the slice can be re-scoped to avoid `grade.py` edits.
5. **OQ4 (`gt branch split` documentation) resolves to "yes, document briefly."** Included in `references/command-reference.md` under "Stack ops" without a worked example. Worked examples can come in a follow-up ticket if needed.
6. **`model` is not required in SKILL.md frontmatter** (ref: research Q2 — no existing SKILL.md sets it). Slice 1 omits `model` from frontmatter. If the harness emits a warning, slice 1 will add `model: opus` and note in impl-log.md.
