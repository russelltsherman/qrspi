# Design — Create a new agent skill called writing bash scripts

**Ticket:** RUS-5
**Research basis:** research.md @ 2026-06-03T00:00:00Z
**Generated:** 2026-06-03T00:00:00Z
**Status:** draft

## Current State

This repo has no bash-scripting guidance skill. Skills live one-directory-per-skill under `.claude/skills/<name>/SKILL.md`; discovery is purely filesystem-based with no index, registry, or manifest to update (ref: Q2, Q6). Ten skills exist today, all carrying the same five frontmatter keys — `name`, `description`, `command`, `argument-hint`, `allowed-tools` (ref: Q3). Triggering is governed entirely by the `description` text; there is no separate triggers field (ref: Q1, Q9).

Two structural archetypes exist. Eight phase skills are *thin wrappers*: the SKILL.md parses arguments, resolves `REPO_ROOT`, and spawns a same-named agent at `.claude/agents/<name>.md` that holds the real logic (ref: Q1, Q5). Two skills — `qrspi-ticket` and `qrspi-work` — are *self-contained*: they carry full logic in the SKILL.md with no agent file, and are interactive/orchestrator skills rather than spawned phase agents (ref: Q5).

Only one skill uses a subdirectory: `qrspi-work/references/review-cascade.md`, linked by relative path from the SKILL body and consulted on demand — the repo's sole overflow precedent (ref: Q2, Q7). No skill in this repo bundles a `scripts/` or `assets/` subdirectory; executable helpers live at repo-root `scripts/` instead (ref: Q2, Q8). There is no enforced SKILL.md size limit, and the largest existing skill (`qrspi-work`, 565 lines) already exceeds the ticket's cited ~500-line guideline (ref: Q7).

The skill-builder/skill-creator tool the ticket mandates is not present in-repo; it is a global/external skill referenced by convention but not committed here (ref: Q4). ShellCheck is not installed in this container and is not provisioned by the Dockerfile or post-create, though repo authors do write ShellCheck-aware bash with disable directives (ref: Q11). The eval harness is a non-functional placeholder; real verification is via stdlib unit tests and manual e2e (ref: Q10). Human-facing skill lists in `README.md` and `.claude/CLAUDE.md` mirror the skill set manually and can drift (ref: Q6, Q12).

## Desired End State

A new knowledge skill `writing-bash-scripts` exists and is discoverable, encoding the ticket's bash conventions so an agent following it produces ShellCheck-clean scripts. Mapping each acceptance criterion to behavior:

- **AC: agentskills.io directory structure with valid SKILL.md frontmatter** → a directory `.claude/skills/writing-bash-scripts/` containing a `SKILL.md` whose YAML frontmatter parses and carries the in-repo five-key schema (`name`, `description`, `command`, `argument-hint`, `allowed-tools`) (ref: Q3). The repo's convention is the verifiable standard; the external agentskills.io standard cannot be fetched and is treated as compatible (ref: Q3, OQ1).
- **AC: built using the Anthropic skill builder skill** → the implementation phase invokes the external skill-creator skill to author/validate the skill, per repo convention; this is a process step, not a committed artifact (ref: Q4).
- **AC: SKILL.md body under 500 lines / 5000 tokens** → the SKILL.md body stays under the limit by holding opinionated defaults and gotchas inline and pushing exhaustive convention detail into `references/` (ref: Q7).
- **AC: detailed reference material in references/ if needed** → a `references/` subdirectory (mirroring the `qrspi-work` precedent) holds the long-form convention catalog (strict mode, traps, getopts, subcommand dispatch, logging, quoting, portability tables), linked by relative path from SKILL.md (ref: Q2, Q7).
- **AC: produces ShellCheck-clean output when an agent follows the guidance** → guidance is concrete enough that generated scripts pass ShellCheck with zero warnings; verification requires provisioning ShellCheck since it is absent here (ref: Q11, OQ2).

The skill auto-triggers on bash-script authoring requests via a specificity-engineered `description` with enumerated positive triggers and an explicit scope/skip boundary (ref: Q9).

## Delta

New files:

- `.claude/skills/writing-bash-scripts/SKILL.md` — the skill body: frontmatter (five-key schema), opinionated defaults, a structured "code organization" ordering, a gotchas section, and inline links to references. Self-contained archetype (no agent file), since this is a knowledge skill, not a spawned phase agent (ref: Q5).
- `.claude/skills/writing-bash-scripts/references/*.md` — one or more reference files carrying the overflow convention detail (strict mode, error handling/traps, argument parsing, subcommand dispatcher, logging, quoting, dependency checks, usage heredoc, temp files, testing/linting, portability) so the SKILL body stays under the size limit (ref: Q7).

Modified files (documentation mirrors, for consistency — not load-bearing for discovery) (ref: Q6, Q12):

- `README.md` — add the skill to the skill table and the Project Structure tree.
- `.claude/CLAUDE.md` — add the skill to the "Available skills" list.

No new agent file (`.claude/agents/writing-bash-scripts.md` is NOT created — self-contained archetype) (ref: Q5). No registry/manifest edit is required for discovery (ref: Q6).

## Pattern Decisions

### Decision 1: Skill archetype (thin-wrapper+agent vs. self-contained)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Self-contained SKILL.md, no agent file (qrspi-ticket/qrspi-work precedent) | Matches knowledge-skill nature; no subagent spawn overhead; simplest | Diverges from the 8 phase wrappers (but those are phase agents, not knowledge skills) |
| B | Thin wrapper + `.claude/agents/writing-bash-scripts.md` | Consistent with the dominant phase pattern | Wrong tool: agent spawning is for phase logic with input contracts; a bash-guidance skill has no phase to run; adds a needless file |

**Recommendation:** Option A
**Rationale:** The wrapper+agent split exists to spawn fresh-context phase agents with labelled input contracts (ref: Q1, Q5). A bash-scripting knowledge skill has no ticket-scoped phase to execute; it supplies guidance the calling agent consumes directly. The self-contained precedent (`qrspi-ticket`, `qrspi-work`) is the correct fit (ref: Q5).
**NEW PATTERN?** No — reuses the self-contained-skill archetype already in-repo (ref: Q5).

### Decision 2: Overflow handling for the convention catalog

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Inline everything in SKILL.md | One file | Will approach/exceed the 500-line limit given the ticket's breadth; defeats AC on size (ref: Q7) |
| B | SKILL.md = opinionated defaults + gotchas; `references/` = long-form catalog | Honors size AC; matches qrspi-work overflow precedent; loads detail on demand | Two-plus files to keep coherent |

**Recommendation:** Option B
**Rationale:** `qrspi-work` is the in-repo overflow exemplar — a sibling `references/` dir linked by relative path, consulted on demand (ref: Q7). The ticket's convention list is large enough that inlining risks the size AC.
**NEW PATTERN?** No — reuses the `references/` overflow mechanism (ref: Q7).

### Decision 3: Description / trigger engineering

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Terse one-line "what + when" (qrspi-questions style) | Short | Too broad for "bash scripts"; high false-trigger risk on any shell mention (ref: Q9) |
| B | Enumerated positive triggers + "Use when" scope, no negatives (qrspi-work style) | Strongest in-repo precedent; precise | Still may over-trigger on incidental shell mentions |
| C | Option B plus an explicit skip/negative clause ("do NOT use for...") | Tightest control for a broad topic | No in-repo skill uses negative triggers — net-new convention (ref: Q9) |

**Recommendation:** Option C
**Rationale:** "Bash scripts" is a broad topic; the qrspi-work engineered style (enumerated phrases + scope clause) is the strongest precedent (ref: Q9), but the absence of any in-repo negative-trigger exemplar means a skip clause is the right marginal addition to suppress false triggers on incidental shell mentions.
**NEW PATTERN?** Yes — explicit negative/skip triggers in a `description` are not exemplified in this repo (ref: Q9). Justified because no existing skill addresses a topic this broad, so positive-only triggers are insufficient to bound scope.

### Decision 4: Where ShellCheck verification lives

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Skill ships verification guidance only; provisioning ShellCheck is out of scope | Keeps skill focused; smallest change | The "ShellCheck-clean output" AC has no runnable checker in this container (ref: Q11) |
| B | Also provision ShellCheck via Dockerfile/post-create so the AC is checkable | Makes AC verifiable end-to-end | Scope creep into devcontainer config; the AC is about generated-output quality, not toolchain provisioning |

**Recommendation:** Option A
**Rationale:** The AC concerns the quality of scripts an agent produces when following the guidance, not whether this container ships ShellCheck. The skill should instruct ShellCheck-clean authoring and recommend running ShellCheck where available. Whether to provision the binary is a human scope call (ref: Q11, OQ2).
**NEW PATTERN?** No.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Cannot verify against the external agentskills.io standard; in-repo schema may diverge from it | med | med | Conform to the verifiable in-repo five-key schema (ref: Q3); flag the external-standard gap as OQ1 for human confirmation |
| "ShellCheck-clean output" AC is unverifiable here — binary absent (ref: Q11) | high | med | Treat AC as guidance-quality; recommend ShellCheck in the skill; escalate provisioning decision via OQ2 |
| Broad `description` over-triggers on any shell/CLI mention (ref: Q9) | med | med | Use enumerated positive triggers + explicit skip clause (Decision 3); iterate description after observing triggers |
| SKILL.md body exceeds the 500-line limit given the convention breadth (ref: Q7) | med | low | Push long-form detail into `references/` (Decision 2); keep SKILL body to defaults + gotchas |
| Manual skill lists in README/CLAUDE.md drift if not updated (ref: Q6, Q12) | low | low | Update both doc mirrors as part of the delta; note they are non-load-bearing |
| skill-creator is external and unavailable in-repo (ref: Q4) | med | low | Invoke it from the implementation session where the global skill is available; if unavailable, author by hand following the in-repo schema and note the deviation |

## Open Questions

- OQ1: The agentskills.io frontmatter standard cannot be fetched in this environment. Should the SKILL.md target the in-repo five-key schema (`name`/`description`/`command`/`argument-hint`/`allowed-tools`), or must it additionally match specific agentskills.io fields the human can supply? (ref: Q3, Q4)
- OQ2: Should this ticket also provision ShellCheck (Dockerfile/post-create) so the "ShellCheck-clean" AC is runnably verifiable, or is verification deferred to wherever ShellCheck is available? (ref: Q11)
- OQ3: Does the skill need a `command`/`argument-hint` at all? Knowledge skills are typically auto-invoked, not called as slash commands — but the in-repo schema treats both keys as standard. Confirm whether to include a nominal `/writing-bash-scripts` command. (ref: Q3, Q9)
