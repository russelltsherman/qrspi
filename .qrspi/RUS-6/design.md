# Design — Create a new agent skill called using graphite cli

**Ticket:** RUS-6
**Research basis:** research.md @ 2026-05-26T00:45:00Z
**Generated:** 2026-05-26
**Status:** draft

## Current State

A `using-graphite-cli` skill already exists at `~/.agents/skills/using-graphite-cli/SKILL.md` and is 386 lines long (ref: Q1, Q2). It is a flat SKILL.md file with no `references/` directory and no subdirectories (ref: Q3). The skill is auto-discovered by the Claude Code harness via its location under `~/.agents/skills/` -- no registration in settings.json is required (ref: Q2).

The existing skill's frontmatter uses only `name` and `description` fields (ref: Q4). It does not use `command`, `argument-hint`, `license`, `metadata`, or `compatibility`. The `description` field is an aggressive, "pushy" single string designed to win trigger priority over any generic git skill (ref: Q9). The description is 700+ characters, within the 1024-character limit (ref: Q1).

The skill body covers: non-interactive execution flags, co-authorship trailers, safety rules for destructive operations, core workflows (create, modify, submit, sync, restack, navigate), branch management (delete, rename, track/untrack, fold, squash, split, pop), stack reorganization (move, absorb), collaboration (get, freeze/unfreeze), conflict resolution, recovery (undo), merging, PR info viewing, aliases, and terminology (ref: Q1). It encodes the single-commit-per-branch convention implicitly via `gt modify` defaulting to amend mode, but does not state it as an explicit hard rule.

The skill-creator's `quick_validate.py` enforces a strict frontmatter schema: only `name`, `description`, `license`, `allowed-tools`, `metadata`, and `compatibility` are allowed as keys (ref: Q1, Q4). Project-level skills in `.claude/skills/` use additional keys (`command`, `argument-hint`) that would fail this validation (ref: Q4). This means user-level skills destined for `~/.agents/skills/` and project skills in `.claude/skills/` operate under different effective schemas.

The skill-creator skill provides a structured workflow: capture intent, interview, write SKILL.md, author evals, run eval loop, optimize description (ref: Q6, Q13). Eval infrastructure exists in two formats: the skill-creator's trigger eval (`run_eval.py` / `run_loop.py`) for description optimization, and a qualitative eval system using subagent pairs and a grader (ref: Q6). An `evals/graphite-evals.json` file with 5 test cases already exists in this project for the graphite skill (ref: Q12).

Body size limits are soft guidance only -- 500 lines or 5000 words recommended, no programmatic enforcement (ref: Q5, Q10). Reference files in a `references/` directory are loaded on demand via explicit `Read` tool calls when the SKILL.md body instructs the model to do so (ref: Q3). The SKILL.md must mention reference files explicitly or they will never be read (ref: Q3).

There is no pre-invocation check for CLI tool availability; if `gt` is missing, the Bash tool call fails at runtime (ref: Q8). There is no harness-side logging of skill selection or execution (ref: Q14). Skill trigger priority is determined entirely by the model's inference based on description text quality (ref: Q7, Q9).

## Desired End State

After this feature ships, the `using-graphite-cli` skill will:

**AC1 — agentskills.io directory structure with valid SKILL.md frontmatter:** The skill directory at `~/.agents/skills/using-graphite-cli/` contains a `SKILL.md` with frontmatter that passes the skill-creator's `quick_validate.py` validation (keys limited to `name`, `description`, `license`, `allowed-tools`, `metadata`, `compatibility`; `name` in kebab-case; `description` under 1024 chars). A `references/` subdirectory holds detailed reference material.

**AC2 — Built using the skill-creator skill:** The skill is authored through the skill-creator's structured workflow (intent capture, interview, drafting, eval authoring, eval loop, description optimization), not ad-hoc.

**AC3 — SKILL.md body under 500 lines / 5000 tokens:** The SKILL.md body (after the closing `---`) is under 500 lines. Detailed command reference, aliases, and examples are moved to `references/` files, keeping the body focused on decision logic and workflow patterns.

**AC4 — Detailed reference material in references/ directory:** A `references/` subdirectory contains files covering command details, flag tables, aliases, and examples that the body explicitly points the model to read on demand.

**AC5 — Single-commit-per-branch as hard rule:** The SKILL.md body states this convention explicitly and prominently, not just implicitly through `gt modify` default behavior. The rule is framed as a constraint the agent must never violate.

**AC6 — Create, Submit, Modify, Sync workflow loop:** The body documents this as the primary workflow loop, in that order, with clear guidance on when to enter each phase.

**AC7 — Conflict resolution flow using gt continue:** The body covers the conflict resolution sequence: detect conflict, resolve files, stage, `gt continue -a --no-interactive`. Also covers `gt abort --force --no-interactive` as the escape hatch.

**AC8 — Stack navigation commands and directionality:** The body covers `gt up`, `gt down`, `gt top`, `gt bottom`, `gt checkout`, with clear explanation of upstack (away from trunk) vs. downstack (toward trunk) directionality.

**AC9 — Submit flag defaults for automated agent use:** The body specifies `--no-edit --no-interactive` as the default submit pattern, with `--publish`, `--draft`, `--reviewers`, `--merge-when-ready` as situational additions.

**AC10 — Warning against mixing raw git commands with Graphite:** The body includes an explicit, prominent warning that raw `git commit`, `git rebase`, `git merge`, and `git push` commands must never be used when Graphite is managing the repository. Only `git status`, `git diff`, `git add` are safe alongside Graphite.

## Delta

### Modified files

**`~/.agents/skills/using-graphite-cli/SKILL.md`** — Rewrite to bring body under 500 lines. Extract detailed command reference into reference files. Add explicit single-commit-per-branch hard rule. Restructure around the Create-Submit-Modify-Sync loop. Ensure frontmatter passes `quick_validate.py` (remove any non-allowed keys, keep `name` and `description`).

### New files

**`~/.agents/skills/using-graphite-cli/references/command-reference.md`** — Complete command reference with flags, examples, and non-interactive flag requirements. Content extracted from the current SKILL.md body sections: non-interactive execution, branch management, stack reorganization, collaboration, aliases table.

**`~/.agents/skills/using-graphite-cli/references/safety-rules.md`** — Dangerous operations table, confirmation requirements, recovery via `gt undo`, and the raw-git-commands warning.

### Existing files (no changes needed)

**`evals/graphite-evals.json`** — Already exists with 5 test cases. May need expansion during the eval step, but that is post-design work driven by the skill-creator workflow.

## Pattern Decisions

### Decision 1: Skill location

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Keep at `~/.agents/skills/using-graphite-cli/` (user-level) | Available across all projects; matches current location; follows convention-over-configuration discovery (ref: Q2) | Not project-specific; changes affect all repos |
| B | Move to `.claude/skills/using-graphite-cli/` (project-level) | Scoped to this project; can use `command`/`argument-hint` keys | Loses cross-project availability; this skill is general-purpose, not QRSPI-specific |

**Recommendation:** Option A
**Rationale:** The skill is a general-purpose tool wrapper, not project-specific. Every project on this machine benefits from it. The current location at `~/.agents/skills/` follows the convention documented in research (ref: Q2). Project-level skills like `qrspi-work` use additional frontmatter keys (`command`, `argument-hint`) that are specific to the project harness (ref: Q4), but this skill does not need them.
**NEW PATTERN?** No -- maintains the existing user-level skill pattern.

### Decision 2: Body size strategy (how to stay under 500 lines)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Single SKILL.md, no references | Simple; everything in one file; model sees all content at trigger time | Current file is 386 lines and needs new content (AC5, AC6, AC10); would likely exceed 500 lines |
| B | Slim SKILL.md body + `references/` directory | Body stays under 500 lines; detailed content loaded on demand (ref: Q3); matches progressive disclosure architecture (ref: Q3) | Model must issue explicit Read calls; adds latency; unreferenced files are invisible (ref: Q3) |
| C | Slim SKILL.md body + `scripts/` for executable helpers | Body is minimal; complex logic delegated to scripts | Overkill for a CLI-wrapping skill; scripts add maintenance burden |

**Recommendation:** Option B
**Rationale:** The three-tier progressive disclosure model (metadata, body, resources) is the documented architecture for skills (ref: Q3). The body should contain decision logic, hard rules, and workflow patterns. Detailed flag tables, aliases, and exhaustive command examples belong in references that the model reads when it needs them. The body must explicitly reference these files or they will never be loaded (ref: Q3).
**NEW PATTERN?** No -- this is the documented standard pattern, though the current skill does not use it. Adopting `references/` aligns with the architecture rather than introducing something novel.

### Decision 3: Frontmatter schema compliance

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Use only `name` and `description` (current state) | Minimal; passes validation; already works | Does not declare `allowed-tools`, which could help with tool access control |
| B | Add `allowed-tools: Bash, Read` to frontmatter | Declares tool dependencies explicitly; passes validation since `allowed-tools` is in the allowed set (ref: Q1) | No evidence the harness enforces `allowed-tools` for user-level skills; may be documentation-only |

**Recommendation:** Option A
**Rationale:** The current skill works with only `name` and `description`. Adding `allowed-tools` is not enforced at the user-level skill layer (ref: Q4), and there is no evidence it affects behavior. Keep the frontmatter minimal and passing validation.
**NEW PATTERN?** No.

### Decision 4: Reference file granularity

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Single `references/full-reference.md` | One file to read; simpler pointers in body | Large file loaded all at once; may exceed what the model needs for a specific task |
| B | Two files: `command-reference.md` + `safety-rules.md` | Model reads only what it needs; safety rules loaded separately for dangerous operations | Two Read calls instead of one; more files to maintain |
| C | Many small files (one per command category) | Maximum granularity; minimal context per read | Too many files; body becomes a table of contents; maintenance overhead |

**Recommendation:** Option B
**Rationale:** Two files provides a useful split between "how to do things" (command reference) and "what to be careful about" (safety rules). The model can load the command reference when executing workflows and the safety rules when approaching destructive operations. This matches the on-demand loading pattern documented in research (ref: Q3) without fragmenting into too many files.
**NEW PATTERN?** No -- follows the existing `references/` convention used by other skills like `qrspi-work` (ref: Q3).

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Rewriting the skill breaks existing trigger behavior — the new description triggers less reliably than the current one | Medium | High | Use the skill-creator's trigger eval loop (`run_eval.py` / `run_loop.py`) to validate the new description against the existing `evals/graphite-evals.json` test cases before finalizing (ref: Q6). Expand eval set if coverage is insufficient. |
| Reference files not loaded when needed — model skips Read calls for reference files, leading to incomplete command knowledge | Medium | Medium | SKILL.md body must contain explicit, imperative pointers: "Read `references/command-reference.md` before executing any gt command you have not used in this session." Test with qualitative evals (ref: Q6) to verify reference loading happens. |
| Frontmatter validation divergence — the skill-creator's `quick_validate.py` schema does not match what the harness actually accepts, causing false validation failures or missed errors | Low | Low | Validate the final SKILL.md with `quick_validate.py` as a smoke test. The harness is permissive (convention over configuration), so passing validation is sufficient (ref: Q1, Q2). |
| Single-commit-per-branch rule is too rigid — some workflows legitimately need multiple commits per branch | Low | Medium | Frame the rule as the default convention with an explicit escape hatch: the user can override by saying "use multiple commits on this branch." The skill should enforce the default, not make the exception impossible. |

## Open Questions

- OQ1: The ticket says "Built using the Anthropic skill builder skill" (AC2). The skill-creator workflow is interactive and conversational (ref: Q13). Should the implementation invoke the skill-creator skill directly (which would drive the process conversationally), or should implementation follow the skill-creator's documented structure manually while producing the same artifact format? The former is more faithful to AC2 but cedes control of the output to the skill-creator's workflow.

- OQ2: The existing `evals/graphite-evals.json` has 5 test cases. The skill-creator's eval loop recommends 20 queries (8-10 should-trigger, 8-10 should-not-trigger) for description optimization (ref: Q6). Should we expand the eval set as part of this ticket's scope, or treat eval expansion as a follow-up?

- OQ3: The ticket references "agentskills.io standard pattern" but this term does not appear anywhere in the codebase (ref: Q4). The skill-creator has its own validation schema. Should we treat the skill-creator's schema as the authoritative definition of the "agentskills.io standard," or is there an external specification we should consult?
