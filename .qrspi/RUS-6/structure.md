# Structure — Create a new agent skill called using graphite cli

**Ticket:** RUS-6
**Design basis:** design.md @ 2026-05-26
**Generated:** 2026-05-26
**Status:** draft

## Types and Signatures

### SKILL.md frontmatter (unchanged schema, validated by quick_validate.py)

```yaml
---
name: using-graphite-cli          # kebab-case, max 64 chars
description: "<trigger text>"     # max 1024 chars, no angle brackets
---
```

### SKILL.md body structure (new organization)

```
# Graphite CLI Skill

## Hard Rules
  - single-commit-per-branch convention (AC5)
  - raw git command prohibition (AC10)
  - non-interactive execution requirement

## Primary Workflow Loop (AC6)
  - Create → Submit → Modify → Sync
  - when to enter each phase

## Conflict Resolution (AC7)
  - detect → resolve → stage → gt continue
  - abort escape hatch

## Stack Navigation (AC8)
  - up/down/top/bottom/checkout
  - upstack vs downstack directionality

## Submit Defaults (AC9)
  - --no-edit --no-interactive as baseline
  - situational flags: --publish, --draft, --reviewers, --merge-when-ready

## Safety Rules (summary)
  - dangerous operations table
  - confirmation requirements
  - pointer: Read references/safety-rules.md for full detail

## Co-authorship
  - trailer format
  - heredoc pattern

## Reference Pointers
  - pointer: Read references/command-reference.md for flags, aliases, examples
  - pointer: Read references/safety-rules.md for dangerous ops, recovery, raw-git warning
```

### references/command-reference.md structure

```
# Command Reference

## Non-interactive flag table (per command)
## Core commands (create, modify, submit, sync, restack)
## Branch management (delete, rename, track/untrack, fold, squash, split, pop)
## Stack reorganization (move, absorb)
## Collaboration (get, freeze/unfreeze)
## Viewing info (info, log, log short, log long)
## Aliases table
## Terminology glossary
```

### references/safety-rules.md structure

```
# Safety Rules

## Dangerous operations table (operation + why dangerous)
## Confirmation requirements
## Recovery via gt undo
## Raw git commands warning (AC10 detail)
## Pre-sync checklist
```

## Vertical Slices

### Slice 1: Author complete skill (SKILL.md + all references)

**Goal:** Rewrite `~/.agents/skills/using-graphite-cli/SKILL.md` to meet all acceptance criteria (AC1, AC3-AC10). Create `references/command-reference.md` and `references/safety-rules.md`. The three files are mutually dependent: the body references the files, the files contain content extracted from the body. They must be authored together.

AC2 (built using skill-creator) governs the _process_ used during implementation, not a separate deliverable. The implementer must follow the skill-creator's documented workflow structure (intent → interview → draft → eval → optimize) to satisfy AC2.

**Files touched:**

| File | Action |
|------|--------|
| `~/.agents/skills/using-graphite-cli/SKILL.md` | modify |
| `~/.agents/skills/using-graphite-cli/references/command-reference.md` | new |
| `~/.agents/skills/using-graphite-cli/references/safety-rules.md` | new |

**Verification:**

1. `python3 scripts/quick_validate.py ~/.agents/skills/using-graphite-cli` passes (AC1 frontmatter validation)
2. SKILL.md body (after closing `---`) is under 500 lines: `tail -n +4 SKILL.md | wc -l` < 500 (AC3)
3. `references/command-reference.md` exists and is non-empty (AC4)
4. `references/safety-rules.md` exists and is non-empty (AC4)
5. Body contains explicit single-commit-per-branch hard rule (AC5) — grep for "single.commit" or equivalent
6. Body documents Create → Submit → Modify → Sync loop (AC6)
7. Body documents conflict resolution with `gt continue` and `gt abort` (AC7)
8. Body documents `gt up`, `gt down`, `gt top`, `gt bottom` with directionality explanation (AC8)
9. Body specifies `--no-edit --no-interactive` as submit default (AC9)
10. Body or references/safety-rules.md contains raw git commands warning (AC10)
11. Run existing evals: `python3 scripts/run_eval.py --eval-set evals/graphite-evals.json --skill-path ~/.agents/skills/using-graphite-cli` — all 5 cases pass (validates trigger behavior is preserved)

**Context cost:** M (3 files, one rewrite + two new, all under 500 lines each; needs reference to existing SKILL.md content for extraction)

**Dependencies:** None — first and only slice.

## Contracts

### Cross-slice interfaces

Not applicable — single slice. All files are authored together.

### Internal contracts (within the slice)

1. **SKILL.md body → references/command-reference.md:** Body must contain an imperative pointer: "Read `references/command-reference.md` before executing any gt command you have not used in this session." The reference file must exist and cover all commands currently documented in the existing SKILL.md body.

2. **SKILL.md body → references/safety-rules.md:** Body must contain a pointer: "Read `references/safety-rules.md` before any destructive operation." The reference file must cover the dangerous operations table, recovery, and the raw-git prohibition.

3. **Frontmatter description → trigger behavior:** The new description must preserve trigger coverage for the 5 existing eval queries in `evals/graphite-evals.json`. Description text may change but must not regress trigger accuracy.

4. **Body line budget:** Content extraction from body to references must reduce body to under 500 lines while retaining all decision logic, hard rules, and workflow patterns in the body. Reference files hold detailed flags, aliases, examples, and exhaustive command documentation.

## Unverified Assumptions

1. **AC2 interpretation:** The design's OQ1 asks whether to invoke the skill-creator skill directly (interactive workflow) or follow its structure manually. This structure assumes the implementer follows the skill-creator's documented phases manually while producing conformant artifacts, rather than invoking the skill-creator as a sub-skill. If the ticket author intended literal invocation, this slice's process would change but its file outputs would not.

2. **Eval expansion scope:** The design's OQ2 asks whether to expand the eval set from 5 to 20 cases. This structure treats eval expansion as out of scope for this ticket — the verification step runs the existing 5 cases. If eval expansion is in scope, it would add `evals/graphite-evals.json` as a fourth file (modify) to this slice, still within the 10-file limit.

3. **`quick_validate.py` availability:** Verification step 1 assumes `python3 scripts/quick_validate.py` can be run from the project root and accepts a skill directory path as argument. If the script expects a different invocation pattern, the verification command must be adjusted.

4. **"agentskills.io standard" meaning:** The design's OQ3 notes that "agentskills.io standard pattern" does not appear in the codebase. This structure treats the skill-creator's `quick_validate.py` schema as the authoritative definition. If an external specification exists and differs, frontmatter may need revision.

5. **Existing SKILL.md content completeness:** The restructuring assumes all content worth preserving is in the current 386-line SKILL.md. If the ticket author expects new commands or patterns not in the current file (beyond the explicit ACs), they would need to be specified.
