# Design — Create a new agent skill using glab cli

**Ticket:** RUS-13
**Research basis:** research.md @ 2026-06-03T00:00:00Z
**Generated:** 2026-06-03T00:00:00Z
**Status:** draft

## Current State

This repo separates skills (slash-command wrappers) from agents (the prompt bodies they spawn); the convention is documented in `.claude/CLAUDE.md` (ref: Q1). Every skill lives at `.claude/skills/<skill-name>/SKILL.md`, with a mandatory `SKILL.md` per directory; the directory name equals the `name:` frontmatter and the `command:` value minus the leading slash (ref: Q1, ref: Q2). All 10 existing skills carry the `qrspi-` prefix because they are workflow-phase skills, but that prefix is project-area-specific — only the kebab-case dir==name==command identity is universal (ref: Q2).

Skill frontmatter uses five fields in practice: `name`, `description`, `command`, `argument-hint`, `allowed-tools` (ref: Q3). `description` is the trigger-matching string and is quoted when it contains YAML-significant punctuation or embedded examples (ref: Q3). The authoritative required-vs-optional frontmatter rules live in the global `skill-creator` skill, which is outside `REPO_ROOT` and therefore not citable from project scope (ref: Q3, Inconsistencies).

There is exactly one reference-heavy skill in the repo — `qrspi-work` — whose ~370-line `SKILL.md` holds the runnable procedure and safety rules inline while factoring one cohesive conceptual topic into `references/review-cascade.md` and linking to it from the body (ref: Q4). `references/` is used sparingly: that is the only `references/` directory that exists (ref: Q1, ref: Q4).

The repo has zero `glab`/GitLab footprint — no `glab-cli`, `GITLAB_TOKEN`, `~/.config/glab-cli/config.yml`, or `--hostname` content anywhere outside the input artifacts (ref: Q4, ref: Q5, ref: Q8, ref: Q9). The only CLI-skill precedents are GitHub `gh` (inside `qrspi-work` and `qrspi_pr_state.py`) and Graphite `gt` (an external skill whose coverage is captured as eval assertions in `evals/graphite-evals.json`) (ref: Q4, Inconsistencies). A glab skill is greenfield relative to this codebase.

For scripted/non-interactive CLI use the repo has a strong pattern: every CLI invocation appends a non-interactive flag, JSON output is parsed with `--jq`/`jq`, and multi-step flows are folded into a single self-locating script emitting one `{"ok": ...}` JSON envelope the caller parses (ref: Q7). Error handling is uniform: a copy-pasted HARD STOP block on permissions/auth/config/tooling errors (stop, print the exact failing command and output, no workarounds), verbatim error propagation, and a sharp distinction between recoverable "recognized states" (which get deterministic handlers) and infrastructure HARD STOPs (ref: Q5, ref: Q9, ref: Q12). Judgment-call branches (e.g. stale/closed PR) are encoded as named states with explicit recovery sequences, not as errors (ref: Q9).

The "500 lines / 5000 tokens" SKILL.md threshold is NOT a repo-documented rule — the only "500" convention is 500 words for a ticket body, a different artifact (ref: Q10, ref: Q11, Inconsistencies). No token counter exists; the only line-count code is `grade.py:line_count`, which operates on eval output and takes `max_lines` as a parameter (no 500 default) (ref: Q10, ref: Q11). The `evals/` + `run_eval.py` harness is a non-functional placeholder: `execute_single` returns empty output, so eval scores are not a real gate (ref: Q6, ref: Q10). Real verification = valid frontmatter + (for logic) green stdlib unit tests + manual end-to-end runs (ref: Q10). The `skill-creator` skill itself is outside `REPO_ROOT` and cannot be cited (ref: Q6, ref: Q12, Inconsistencies).

## Desired End State

A new standalone skill `glab-cli` ships at `.claude/skills/glab-cli/SKILL.md` plus a `references/` directory. It is not a QRSPI phase, so it carries no `qrspi-` prefix and has no agent file (it is reference/guidance content, not an agent-spawning wrapper). Acceptance criteria map to behavior as follows:

- **agentskills.io directory structure + valid frontmatter** → `.claude/skills/glab-cli/SKILL.md` with `name: glab-cli`, `command: /glab-cli`, a quoted `description`, `argument-hint`, and `allowed-tools` matching the in-repo skill dialect (ref: Q1, ref: Q2, ref: Q3).
- **Built using the skill-builder/skill-creator skill** → authored via the global `skill-creator` skill; noted as an Open Question because skill-creator is out of project scope and cannot be verified from research (Inconsistencies).
- **SKILL.md body under 500 lines / 5000 tokens** → body kept concise with deep material pushed to `references/`; verified ad-hoc with `wc -l` since no repo token/line gate exists (ref: Q10, ref: Q11). The 500/5000 figure is honored as an external skill-creator constraint, not a repo rule (Inconsistencies).
- **references/ covering full command reference, authentication flows, CI/CD scripting patterns, error handling** → four reference files under `references/`, following the qrspi-work split rule of one cohesive topic per file (ref: Q4).
- **Covers auth, mr, issue, ci/pipeline, release, changelog, repo, api** → enumerated in the command reference and summarized in the body, mirroring how `graphite-evals.json` enumerates a CLI skill's subcommands/flags (ref: Q4).
- **Opinionated patterns: merge-after-green, stacked MRs, fork-based contributions** → a Workflow Patterns section in the body using `--when-pipeline-succeeds` / `glab ci status --wait` as the merge-after-green primitive (ref: Q7, ref: Q9).
- **gitlab.com and self-hosted instances** → an authentication-flows reference documenting `--hostname` and multi-host `config.yml`, with conflict handling encoded as named states (ref: Q5, ref: Q8).
- **Agent-specific scripted guidance: error handling, exit codes, JSON parsing** → a non-interactive flag on every command, JSON parsed via `glab ... -F`/`jq`, the single-JSON-envelope pattern, and the repo HARD STOP block reused verbatim for auth/config/tooling failures (ref: Q5, ref: Q7, ref: Q12).

## Delta

New files:
- `.claude/skills/glab-cli/SKILL.md` — body: frontmatter, overview, authentication summary, the eight subcommand groups condensed, opinionated Workflow Patterns (merge-after-green, stacked MRs, fork-based), judgment-call named-states section, agent/scripted-use rules, HARD STOP block, links into `references/`.
- `.claude/skills/glab-cli/references/commands.md` — full subcommand/flag reference for auth, mr, issue, ci/pipeline, release, changelog, repo, api.
- `.claude/skills/glab-cli/references/authentication.md` — `glab auth login` (OAuth vs PAT), `GITLAB_TOKEN` for CI, `--hostname` self-hosted, multi-host `config.yml`, conflict handling.
- `.claude/skills/glab-cli/references/ci-scripting.md` — merge-after-green, `glab ci status --wait`, JSON parsing via `jq`, exit-code handling, single-envelope scripting pattern.
- `.claude/skills/glab-cli/references/error-handling.md` — exit codes, recognized-state vs HARD-STOP distinction, verbatim error propagation.

No modifications to existing files are required: a new skill is additive and the dir==name==command identity is the only structural contract (ref: Q1, ref: Q2). No new DB queries, middleware, or scripts. No eval entry is required (the harness is a placeholder and not a gate) (ref: Q6, ref: Q10), though an optional `evals/glab-evals.json` modeled on `graphite-evals.json` is noted as an open question.

## Pattern Decisions

### Decision 1: Skill packaging — agent-backed wrapper vs inline reference skill

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Thin wrapper + `.claude/agents/glab-cli.md` agent body | Matches dominant QRSPI pattern (8 of 10 skills) | Agents are for spawned workflow phases; a CLI guidance skill has no phase to run — misuse of the pattern |
| B | Standalone skill: `SKILL.md` + `references/`, no agent | Matches `qrspi-work`/`qrspi-ticket` (inline, no agent); fits guidance content | Slightly broader content lives directly in SKILL.md |

**Recommendation:** Option B
**Rationale:** `qrspi-ticket` and `qrspi-work` already establish the no-agent, inline/reference skill shape, and the skill=wrapper/agent=phase-body split means an agent file only exists when there is an agent to spawn (ref: Q1, Discovered Patterns). A glab guidance skill has no spawned phase, so no agent file.
**NEW PATTERN?** No — reuses the existing standalone-skill shape (`qrspi-work`).

### Decision 2: Body-vs-references content split

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Everything inline in SKILL.md | One file | Blows the 500-line/5000-token budget; contradicts sparse-references norm |
| B | Procedure + safety + opinionated patterns inline; deep enumeration in `references/` | Mirrors qrspi-work split; keeps body under budget | Four reference files vs the repo's current one |

**Recommendation:** Option B
**Rationale:** The qrspi-work split rule — runnable procedure plus safety rules inline, one cohesive topic per `references/*.md`, linked from the body — is the only in-repo precedent and directly satisfies the references/ acceptance criterion (ref: Q4). Four files is a deliberate departure from the current single-references norm, justified by the ticket explicitly requiring four reference topics.
**NEW PATTERN?** No — extends the existing qrspi-work references pattern; the multi-file count is ticket-mandated, not a new structural idea.

### Decision 3: Encoding judgment-call branches (existing MR, missing tag, failing pipeline)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Document as errors to surface | Simple | Conflates recoverable states with infrastructure failures; contradicts repo norm |
| B | Named recognized states with deterministic handlers, separate from HARD STOP | Matches qrspi-work stale/closed-PR handling | Requires careful wording to keep the two categories distinct |

**Recommendation:** Option B
**Rationale:** `qrspi-work` encodes "PR already exists" and "PR was closed/merged" as named recognized states with recovery sequences, explicitly excluded from the HARD STOP rule (ref: Q9, ref: Q12). The glab judgment calls (existing MR on branch, missing release tag → `--ref`, failing pipeline at merge) map onto the same structure.
**NEW PATTERN?** No — direct reuse of the recognized-state-vs-HARD-STOP pattern.

### Decision 4: Authoring tool and size verification

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Author via global `skill-creator`; verify size with `wc -l` | Satisfies the ticket's "use skill builder" criterion | skill-creator is out of repo scope; cannot be verified from research |
| B | Hand-author to in-repo conventions; skip skill-creator | Fully grounded in cited repo patterns | Violates an explicit acceptance criterion |

**Recommendation:** Option A
**Rationale:** The ticket mandates the skill-builder/skill-creator skill. Research confirms skill-creator is a global skill outside `REPO_ROOT`, so its rules cannot be cited and its 500/5000 thresholds are external, not repo-enforced (ref: Q3, ref: Q6, ref: Q10, Inconsistencies). Size is checked ad-hoc with `wc -l` since no repo tool exists (ref: Q11).
**NEW PATTERN?** Yes — first use of `skill-creator` to author a skill in this repo, and first non-`qrspi` skill. Justified because the ticket requires it and no in-repo authoring tool exists.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| 500-line/5000-token budget is unverifiable in-repo (no token counter; threshold is external) (ref: Q10, ref: Q11) | high | med | Aggressively push detail to `references/`; check body with `wc -l`; treat 5000 tokens as a soft external target and flag in Open Questions |
| skill-creator authoring rules cannot be grounded from research (skill is out of scope) (ref: Q3, ref: Q6, Inconsistencies) | high | med | Author against in-repo frontmatter examples for structure; run skill-creator for the build step; surface any rule conflict as an Open Question |
| All glab command/flag content is greenfield — no in-repo glab facts to verify against (ref: Q4, ref: Q5, ref: Q8, ref: Q9) | high | high | Source commands from official glab docs at implementation time; use `graphite-evals.json` as the structural coverage checklist; have a human spot-check flags |
| New non-`qrspi` skill could confuse auto-invocation if `description` overlaps existing triggers (ref: Q3) | low | med | Write a tightly scoped `description` enumerating glab/GitLab trigger phrases only; quote it per the YAML-punctuation rule |
| Multi-host/self-hosted conflict behavior has no in-repo precedent to model (ref: Q8) | med | med | Encode host selection as explicit `--hostname`/recognized-state guidance; defer ambiguous credential resolution to the human per the auth HARD STOP norm (ref: Q5) |

## Open Questions

- OQ1: The 500-line/5000-token limit is not a repo rule (ref: Q10, ref: Q11) — should we treat it strictly as an external skill-creator constraint, or adopt a repo-local size check? No token counter exists today.
- OQ2: Should an `evals/glab-evals.json` be added modeled on `graphite-evals.json` (ref: Q4, ref: Q6), given the eval harness is a non-functional placeholder and not a real gate (ref: Q10)?
- OQ3: skill-creator is outside project scope (Inconsistencies) — can the build be performed and its output verified in this environment, and how do we reconcile any skill-creator frontmatter rules that conflict with the in-repo dialect (ref: Q3)?
- OQ4: For self-hosted/multi-host conflicts (ref: Q8), what is the preferred default — always require explicit `--hostname`, or infer from current repo remote? No in-repo precedent exists.
