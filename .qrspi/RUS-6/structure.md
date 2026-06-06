# Structure Outline — Create a new agent skill called using-graphite-cli

**Design basis:** design.md @ 2026-06-03T14:10:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft

> This ticket delivers documentation artifacts (a skill + reference files), not
> executable code. "Types" and "Contracts" below are therefore the structural
> schemas and cross-file interfaces that bind the three files together, not
> runtime types or function signatures.

## New Types

- `SkillFrontmatter { name: string, description: string, command: string, argument-hint: string, allowed-tools: string }`
  — the five-key YAML block, in this exact order, opening `SKILL.md`. `description`
  is a single double-quoted sentence ending in a "Use when…" trigger clause
  (ref: design §Delta "Frontmatter values to set", §Current State Q3).
  Values: `name: using-graphite-cli`, `command: /using-graphite-cli`,
  `argument-hint:` empty/optional, `allowed-tools: Bash`.
- `SkillDir { SKILL.md, references/ }` — directory layout at
  `.claude/skills/using-graphite-cli/`, discoverable by convention with no
  manifest edit (ref: design §Desired End State, Q13).

## Modified Types

- none. The design requires no edits to existing files for discovery
  (auto-discovery by directory) (ref: design §Delta "Modified files: none").

## Contracts

- `identity-triple` — directory name `using-graphite-cli` == frontmatter `name`
  == `command` slug `/using-graphite-cli`, all lowercase kebab-case (ref: Q5).
  Implementation MUST hold this invariant or the skill is undiscoverable.
- `lazy-reference-pointer(file): "see references/<file>"` — the body links to
  `references/command-reference.md` and `references/conflict-resolution.md`
  lazily rather than inlining their content (ref: design Decision 2, Q1/Q2).
  Every pointer in the body MUST resolve to a file that exists in this slice.
- `size-budget` — `SKILL.md` body ≤ 500 lines / 5000 tokens (self-policed;
  no in-repo enforcement exists, ref: Q7). Detail overflow routes to `references/`.
- `gt-workflow-vocabulary` — the body documents the full loop
  `gt create --all -m` → `gt submit`/`gt ss` (agent default `--no-edit --publish`)
  → `gt modify --all` → `gt sync`; conflicts resolved with `gt continue`
  (NEVER `git rebase --continue`); navigation via `gt bu`/`gt bd`,
  `gt stack top`, `gt log short` with downstack=toward-trunk /
  upstack=away-from-trunk (ref: design §Desired End State, Decision 3).
- `hard-rule-format` — each prohibition/rule uses bold lead-in + ALL-CAPS
  imperative (NEVER/Do NOT/HARD STOP) + one-sentence rationale, prohibitions
  clustered in a dedicated near-end section, mirroring `qrspi-work` phrasing
  (ref: Q8, Q9).

## Slice 1: The using-graphite-cli skill (body + references)

**Goal:** A complete, discoverable `using-graphite-cli` skill exists and reads
end-to-end: the `SKILL.md` body carries the frontmatter, the Create→Submit→Modify→Sync
workflow, the single-commit-per-branch and raw-git prohibition hard rules, and
stack navigation; both `references/` files exist and every lazy pointer in the
body resolves. This is the entire feature — the three files are mutually
dependent (the body's "see references/…" pointers are dead until the reference
files exist; the reference files carry no value without the body that links
them), so they form one unit of work with a single verification boundary
(ref: design §Delta; rule 8 — cohesive work is not over-sliced).

**Files touched:**

- ✨ `.claude/skills/using-graphite-cli/SKILL.md` — skill body: five-key
  frontmatter (`SkillFrontmatter`), Create→Submit→Modify→Sync workflow section,
  single-commit-per-branch hard rule, "NEVER run `git rebase`/`git commit --amend`
  on a tracked branch" prohibition section, stack navigation + directionality,
  agent submit defaults (`--no-edit --publish`), lazy pointers into `references/`.
  Target ~150-300 lines, hard cap 500 (ref: design §Delta).
- ✨ `.claude/skills/using-graphite-cli/references/command-reference.md` — full
  `gt` command catalog with flags (create/submit/modify/sync/log/move/navigation)
  (ref: design §Delta).
- ✨ `.claude/skills/using-graphite-cli/references/conflict-resolution.md` —
  `gt continue` flow, edge cases, stack-repair recipes; marks `gt continue` as the
  canonical conflict step per ticket (ref: design §Delta, Risk Register).

**Verification:**

- [ ] Structural check (per CLAUDE.md, the only working validation): directory
  name == frontmatter `name` == `command` slug; all five frontmatter keys present
  in order and YAML-valid; both `references/` files exist.
- [ ] Every `see references/<file>` pointer in `SKILL.md` resolves to a file on disk.
- [ ] `SKILL.md` is ≤ 500 lines / 5000 tokens (manual line/token count).
- [ ] All acceptance criteria from design §Desired End State are textually present
  (single-commit hard rule, full gt loop, `gt continue`, navigation + directionality,
  submit defaults, raw-git prohibition).
- [ ] Final step: invoke `skill-creator` (and its eval loop) for validation if
  available in the running environment, per memory directive and `qrspi-structure`
  slice-final convention — see OQ1 / Unverified Assumption 1 if it is not available.

**Context cost:** M
**Depends on:** none

---

## Unverified Assumptions

1. **skill-creator is invokable in the running environment.** The ticket mandates
   building via `skill-creator`, but the design (OQ1, Q12, Risk Register) records it
   as external/global and undefined in-repo. If it is unavailable, the slice falls
   back to manual construction against the agentskills.io structure plus the
   structural check. Whether that satisfies the "built using skill-creator"
   acceptance criterion is unresolved (OQ1) — needs human decision before planning.
2. **Ticket-verbatim gt flags vs. QRSPI-orchestration flags.** Design Decision 3 /
   OQ2 chose the ticket's general-purpose conventions (`gt create --all`,
   `gt submit --no-edit --publish`, `gt continue`, `gt modify --all`), which diverge
   from `qrspi-work`/`graphite-evals.json` (`--no-interactive` everywhere, "NEVER
   `-a`", `gt sync --delete-all`, submit confirmation, no `gt continue`). The
   implementer must encode the ticket flags and add a short "QRSPI orchestration
   differs" note. The exact divergence wording is not mappable to concrete text yet.
3. **`gt continue` is correct for the installed Graphite version.** It appears
   nowhere in the repo today (NEW PATTERN per Decision 3); design Risk Register says
   to verify against Graphite docs at implementation time. Treated as canonical per
   ticket but unverified against the actual CLI.
4. **Stack-navigation directionality semantics** (`gt bu`/`gt bd`, downstack=
   toward-trunk / upstack=away-from-trunk) have no in-repo precedent (Q10) and are
   asserted from the ticket only — unverified against the CLI.
5. **Co-authorship trailer (OQ3) and docs-list updates (OQ4) are out of scope.** The
   design flags both as follow-ups, not deltas. No slice covers updating the README /
   `.claude/CLAUDE.md` skills list or the stale "Opus 4.7" trailer. Confirm these
   stay out of scope before planning.
