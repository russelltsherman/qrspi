# Implementation Plan — Create a new agent skill called using-graphite-cli

**Structure basis:** structure.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total steps:** 11

> This ticket delivers documentation artifacts (a skill + two reference files),
> not executable code. Steps below create/populate Markdown files; "signatures"
> are the structural schemas (frontmatter keys, lazy pointers, identity triple)
> defined in structure.md. The three files form a single mutually-dependent slice
> with one verification boundary.

## Slice 1: The using-graphite-cli skill (body + references)

### Setup

1. ✨ Create `.claude/skills/using-graphite-cli/SKILL.md` — write the five-key
   YAML frontmatter block per the `SkillFrontmatter` type (structure §New Types),
   in this exact order and YAML-valid:
   - `name: using-graphite-cli`
   - `description:` single double-quoted sentence ending in a "Use when…" trigger clause
   - `command: /using-graphite-cli`
   - `argument-hint:` empty/optional (reference guidance, not parameterized)
   - `allowed-tools: Bash`
   Hold the `identity-triple` contract: directory name == `name` == `command` slug,
   all lowercase kebab-case (structure §Contracts).

2. ✨ Create `.claude/skills/using-graphite-cli/references/command-reference.md`
   — create the file (empty placeholder header) so the body's lazy pointer
   resolves; full content added in step 8 (structure §Files touched, Contract
   `lazy-reference-pointer`).

3. ✨ Create `.claude/skills/using-graphite-cli/references/conflict-resolution.md`
   — create the file (empty placeholder header) so the body's lazy pointer
   resolves; full content added in step 9 (structure §Files touched).

### Core Logic

4. ⚠️ Modify `.claude/skills/using-graphite-cli/SKILL.md` — add the
   Create→Submit→Modify→Sync workflow section per the `gt-workflow-vocabulary`
   contract: `gt create --all -m` → `gt submit`/`gt ss` (agent default
   `--no-edit --publish`) → `gt modify --all` → `gt sync` (structure §Contracts;
   design §Desired End State, Decision 3).
   - **Current:** frontmatter only (from step 1)
   - **After:** frontmatter + workflow section enumerating the full loop with agent
     submit defaults stated inline

5. ⚠️ Modify `.claude/skills/using-graphite-cli/SKILL.md` — add the stack
   navigation + directionality section: `gt bu`/`gt bd`, `gt stack top`,
   `gt log short`, downstack=toward-trunk / upstack=away-from-trunk
   (structure §Contracts; design §Desired End State).
   - **Current:** frontmatter + workflow section
   - **After:** adds navigation/directionality section

6. ⚠️ Modify `.claude/skills/using-graphite-cli/SKILL.md` — add the clustered
   hard-rules/prohibitions section near the end per the `hard-rule-format`
   contract (bold lead-in + ALL-CAPS imperative + one-sentence rationale,
   mirroring qrspi-work phrasing): single-commit-per-branch rule, and "NEVER run
   `git rebase` / `git commit --amend` on a tracked branch"; reference
   `gt continue` (NEVER `git rebase --continue`) for conflicts
   (structure §Contracts; design §Desired End State).
   - **Current:** frontmatter + workflow + navigation sections
   - **After:** adds dedicated prohibitions/hard-rules section near end

7. ⚠️ Modify `.claude/skills/using-graphite-cli/SKILL.md` — add lazy pointers
   ("see `references/command-reference.md`", "see `references/conflict-resolution.md`")
   and a short "QRSPI orchestration differs" note (per design Decision 3 / Unverified
   Assumption 2). Enforce `lazy-reference-pointer` contract: every pointer resolves
   to a file created in steps 2-3. Keep body ≤ 500 lines / 5000 tokens (`size-budget`).
   - **Current:** frontmatter + workflow + navigation + hard-rules sections
   - **After:** complete body with resolving lazy pointers and divergence note

8. ⚠️ Modify `.claude/skills/using-graphite-cli/references/command-reference.md`
   — populate the full `gt` command catalog with flags
   (create/submit/modify/sync/log/move/navigation) per structure §Files touched.
   - **Current:** placeholder header (from step 2)
   - **After:** complete command catalog

9. ⚠️ Modify `.claude/skills/using-graphite-cli/references/conflict-resolution.md`
   — populate `gt continue` flow, edge cases, stack-repair recipes; mark
   `gt continue` as the canonical conflict step per ticket (structure §Files
   touched; design Risk Register — verify against Graphite docs at this point).
   - **Current:** placeholder header (from step 3)
   - **After:** complete conflict-resolution reference

### Tests

10. Run structural check (per CLAUDE.md, the only working validation):
    `python3 -c "import yaml,sys; d=yaml.safe_load(open('.claude/skills/using-graphite-cli/SKILL.md').read().split('---')[1]); assert list(d.keys())==['name','description','command','argument-hint','allowed-tools']; assert d['name']=='using-graphite-cli'"`
    (or equivalent manual YAML inspection if PyYAML is absent).
    - **Expected:** all five frontmatter keys present in order; `name` ==
      `using-graphite-cli`; identity triple holds.

### Verify Slice 1

11. **Checkpoint:**
    `ls .claude/skills/using-graphite-cli/SKILL.md .claude/skills/using-graphite-cli/references/command-reference.md .claude/skills/using-graphite-cli/references/conflict-resolution.md && grep -o 'see `references/[^`]*`' .claude/skills/using-graphite-cli/SKILL.md && wc -l .claude/skills/using-graphite-cli/SKILL.md`
    - [ ] Directory name == frontmatter `name` == `command` slug; all five
      frontmatter keys present in order and YAML-valid (step 10 passed).
    - [ ] Both `references/` files exist; every `see references/<file>` pointer in
      `SKILL.md` resolves to a file on disk.
    - [ ] `SKILL.md` ≤ 500 lines / 5000 tokens (`wc -l` ≤ 500; manual token check).
    - [ ] All design §Desired End State acceptance criteria textually present:
      single-commit hard rule, full Create→Submit→Modify→Sync loop, `gt continue`,
      navigation + directionality, submit defaults (`--no-edit --publish`),
      raw-git (`git rebase`/`amend`) prohibition.
    - [ ] Final step: invoke `skill-creator` (and its eval loop) for validation if
      available in the running environment, per memory directive and the
      qrspi-structure slice-final convention. If unavailable, fall back to the
      structural check above and record it against OQ1 / Unverified Assumption 1.

---

## Rollback Notes

- Steps 1-9: all changes are new files under
  `.claude/skills/using-graphite-cli/`. To roll back, delete the directory:
  `rm -rf .claude/skills/using-graphite-cli/`. No existing files are modified
  (structure §Modified Types: none), so removal is fully non-destructive and
  reversible — discovery is by directory convention with no manifest to revert.
- No DB migrations, config changes, or destructive operations are involved.
