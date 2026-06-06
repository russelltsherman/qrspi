# Structure Outline — Create a new agent skill using glab cli

**Design basis:** design.md @ 2026-06-03T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft

> Note: This ticket produces Markdown skill content, not executable code. There
> are no runtime types or function signatures. The "types" below are the YAML
> frontmatter schema and reference-file shapes; the "contracts" are the
> structural invariants every skill in this repo must satisfy (dir==name==command,
> the references split rule, the HARD STOP block). They are the load-bearing
> interfaces the implementation must honor.

## New Types

- `SkillFrontmatter { name: string (kebab-case), description: string (quoted), command: string (/<name>), argument-hint: string, allowed-tools: string }` — the five-field frontmatter dialect used by in-repo skills (ref: design §Desired End State, Q3).
- `ReferenceFile { topic: one-cohesive-concept, path: references/<topic>.md }` — one cohesive topic per file, linked from the SKILL.md body (ref: design §Decision 2, Q4).
- `RecognizedState { name: string, trigger: condition, recovery: deterministic-steps }` — named judgment-call branch, distinct from a HARD STOP (ref: design §Decision 3, Q9).
- `HardStopBlock` — the repo's copy-pasted verbatim error block: stop, print exact failing command + output, no workarounds (ref: design §Desired End State, Q5/Q12).

## Modified Types

- None. The design's Delta states no existing files are modified; a new skill is purely additive (ref: design §Delta).

## Contracts

- `dir == name == command-minus-slash` — the directory `glab-cli/`, frontmatter `name: glab-cli`, and `command: /glab-cli` must be identical kebab-case (ref: design §Desired End State, Q1/Q2). The only universal structural contract.
- `body links every references/*.md` — the SKILL.md body must summarize and link each of the four reference files (qrspi-work split rule) (ref: design §Decision 2, Q4).
- `command coverage = {auth, mr, issue, ci/pipeline, release, changelog, repo, api}` — all eight subcommand groups enumerated in references/commands.md and summarized in the body (ref: design §Desired End State, Q4).
- `every CLI invocation is non-interactive + JSON-parsed` — each documented command appends a non-interactive flag; JSON output parsed via `glab ... -F`/`jq`; multi-step flows fold into a single `{"ok": ...}` envelope (ref: design §Desired End State, Q5/Q7/Q12).
- `judgment calls = RecognizedState, infra failures = HardStopBlock` — the two error categories must remain textually distinct (ref: design §Decision 3, Q9/Q12).

## Slice 1: Author the glab-cli skill (body + four references) via skill-creator

**Goal:** A complete, self-contained `glab-cli` skill that validates as a well-formed skill — correct frontmatter, body under the size budget, and four populated reference files covering the eight subcommand groups — authored and eval-checked through the skill-creator skill. This is the whole feature; it is one cohesive authoring act performed in a single sitting and cannot be meaningfully verified piecemeal (the skill-creator eval loop evaluates the skill as a unit, and the body's links require the references to exist).

**Files touched:**

- ✨ `.claude/skills/glab-cli/SKILL.md` — frontmatter (name/command/quoted description/argument-hint/allowed-tools), overview, authentication summary, eight subcommand groups condensed, opinionated Workflow Patterns (merge-after-green via `--when-pipeline-succeeds` / `glab ci status --wait`, stacked MRs, fork-based contributions), RecognizedState section, agent/scripted-use rules, HARD STOP block, links into `references/`.
- ✨ `.claude/skills/glab-cli/references/commands.md` — full subcommand/flag reference for auth, mr, issue, ci/pipeline, release, changelog, repo, api.
- ✨ `.claude/skills/glab-cli/references/authentication.md` — `glab auth login` (OAuth vs PAT), `GITLAB_TOKEN` for CI, `--hostname` self-hosted, multi-host `config.yml`, conflict handling as named states.
- ✨ `.claude/skills/glab-cli/references/ci-scripting.md` — merge-after-green, `glab ci status --wait`, JSON parsing via `jq`, exit-code handling, single-envelope scripting pattern.
- ✨ `.claude/skills/glab-cli/references/error-handling.md` — exit codes, recognized-state vs HARD-STOP distinction, verbatim error propagation.

**Verification:**

- [ ] `name`/`command`/dir all equal `glab-cli`; `description` is quoted; `argument-hint` and `allowed-tools` present (frontmatter contract).
- [ ] `wc -l .claude/skills/glab-cli/SKILL.md` body is within the ~500-line soft budget; deep detail lives in `references/` (ref: design Risk Register, OQ1).
- [ ] All four reference files exist and each covers exactly one cohesive topic; the body links every one of them.
- [ ] commands.md enumerates all eight subcommand groups (auth, mr, issue, ci/pipeline, release, changelog, repo, api).
- [ ] Body contains the verbatim HARD STOP block and a distinct RecognizedState section (auth/config/tooling → HARD STOP; existing MR / missing tag → recovery).
- [ ] Skill authored through the skill-creator skill and passed its eval loop; auto-invocation `description` does not collide with existing skill triggers.
- [ ] Human spot-check of glab command/flag accuracy (content is greenfield — no in-repo glab facts to verify against; ref: design Risk Register).

**Context cost:** L
**Depends on:** none

---

## Unverified Assumptions

- **skill-creator availability and rule reconciliation (OQ3, Decision 4):** The design mandates authoring via the global `skill-creator` skill, but research confirms it is outside `REPO_ROOT` and its frontmatter rules / 500-line-5000-token thresholds cannot be cited or verified from project scope. Whether skill-creator can run and be verified in this environment, and how to reconcile any conflict between its rules and the in-repo five-field dialect, is unresolved. Cannot be mapped to a concrete file contract.
- **Size budget enforcement (OQ1, Risk Register):** The 500-line/5000-token limit is not a repo rule and no token counter exists. The verification falls back to `wc -l` as a soft check only; the 5000-token figure has no concrete tool behind it.
- **glab command/flag content (Risk Register, high impact):** All glab subcommand and flag content is greenfield — there are zero in-repo glab facts to verify against. The actual command syntax must be sourced from official glab docs at implementation time and human spot-checked; it cannot be validated by this structure.
- **Self-hosted/multi-host default behavior (OQ4, Q8):** No in-repo precedent exists for whether to require explicit `--hostname` or infer the host from the repo remote. The authentication.md content depends on this decision, which is unmade.
- **Optional eval entry (OQ2):** Whether to add `evals/glab-evals.json` modeled on `graphite-evals.json` is undecided. The eval harness is a non-functional placeholder and not a gate, so this is excluded from Slice 1; flagged here pending a human call.
