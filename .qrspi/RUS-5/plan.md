# Implementation Plan — Create a new agent skill called writing-bash-scripts

**Structure basis:** structure.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total steps:** 14

## Slice 1: Author the writing-bash-scripts skill (SKILL.md + references + doc mirrors)

> **Authoring method (applies to all create/modify steps below):** Where the external
> `skill-creator` skill is reachable in the implementation session, invoke it (and its
> eval loop) to author/validate the skill (ref: design Decision 1, user MEMORY). If it is
> unavailable in-repo, author by hand to the in-repo five-key frontmatter schema and record
> the deviation in the slice notes. Conform to the verifiable in-repo schema regardless
> (ref: structure Contracts; design OQ1).

### Setup

1. ✨ Create directory `.claude/skills/writing-bash-scripts/` — the skill root for the
   self-contained knowledge skill (no agent file; ref: structure §Slice 1, design Decision 1).
2. ✨ Create `.claude/skills/writing-bash-scripts/references/` — subdirectory to hold the
   overflow convention catalog so the SKILL body stays under the size limit (ref: structure
   `ReferenceCatalog`, design Decision 2).

### Core Logic — Reference catalog (overflow detail)

3. ✨ Create `.claude/skills/writing-bash-scripts/references/strict-mode.md` — long-form
   detail for shell strict mode (`set -euo pipefail`, `IFS`) and its caveats (ref:
   structure `ReferenceFile`, design §Delta convention list).
4. ✨ Create `.claude/skills/writing-bash-scripts/references/error-handling.md` — error
   handling and traps (`trap ... ERR/EXIT`, cleanup, exit codes) (ref: structure
   `ReferenceFile`).
5. ✨ Create `.claude/skills/writing-bash-scripts/references/arguments.md` — argument
   parsing with `getopts`, positional handling, and subcommand dispatch (ref: structure
   `ReferenceFile`).
6. ✨ Create `.claude/skills/writing-bash-scripts/references/quoting-and-portability.md` —
   quoting rules, logging, dependency checks, usage heredoc, temp-file handling, and
   portability tables (ref: structure `ReferenceFile`, design §Delta).
7. ✨ Create `.claude/skills/writing-bash-scripts/references/testing-and-linting.md` —
   ShellCheck-clean authoring guidance, disable directives, and testing/linting practice;
   note ShellCheck may be absent and recommend running it where available (ref: structure
   `ReferenceFile`, design Decision 4 / OQ2).

   > Note: topic-to-file partition above is illustrative (structure leaves file count/grouping
   > to the implementer). Consolidate or split as needed, but every file MUST be linked from
   > SKILL.md (no orphans) per the SKILL.md.body → references contract.

### Core Logic — SKILL.md

8. ✨ Create `.claude/skills/writing-bash-scripts/SKILL.md` — body content: opinionated
   defaults, a "code organization" ordering section, a gotchas section, and relative-path
   links to every file under `references/`. Keep body (excluding references) under 500
   lines / ~5000 tokens (ref: structure Contracts `SKILL.md.body → size limit`; design
   Decision 2).
9. ✨ Add YAML frontmatter to `.claude/skills/writing-bash-scripts/SKILL.md` — exactly the
   five in-repo keys (`name`, `description`, `command`, `argument-hint`, `allowed-tools`)
   with `name: writing-bash-scripts` (ref: structure `SkillFrontmatter`; design Q3/OQ1/OQ3).
10. ⚠️ Engineer the `description` value in `.claude/skills/writing-bash-scripts/SKILL.md`.
    - **Current:** placeholder/terse description from step 9.
    - **After:** enumerated positive bash-authoring triggers + a "Use when" scope clause +
      an explicit "do NOT use for…" skip clause (ref: structure Contracts
      `description → trigger boundary`; design Decision 3, NEW PATTERN).

### Core Logic — Doc mirrors

11. ⚠️ Modify `README.md` — add the skill for consistency (non-load-bearing for discovery).
    - **Current:** skill table and Project Structure tree without `writing-bash-scripts`.
    - **After:** a `writing-bash-scripts` row in the skill table and a
      `writing-bash-scripts/` node in the Project Structure tree (ref: structure §Modified
      Types; design §Delta, Q6/Q12).
12. ⚠️ Modify `.claude/CLAUDE.md` — add the skill for consistency.
    - **Current:** "Available skills" list without `writing-bash-scripts`.
    - **After:** `writing-bash-scripts` listed under "Available skills" (ref: structure
      §Modified Types; design §Delta, Q6/Q12).

### Tests / Validation

13. Run frontmatter + link + size validation:
    ```
    python3 - <<'PY'
    import sys, re, pathlib
    root = pathlib.Path(".claude/skills/writing-bash-scripts")
    skill = (root / "SKILL.md").read_text()
    fm = skill.split("---")[1]
    import yaml  # if unavailable, parse keys manually
    meta = yaml.safe_load(fm)
    assert set(meta) == {"name","description","command","argument-hint","allowed-tools"}, meta
    assert meta["name"] == "writing-bash-scripts"
    body = skill.split("---",2)[2]
    assert len(body.splitlines()) < 500
    links = re.findall(r"references/[\w\-/]+\.md", skill)
    refs = {p.name for p in (root/"references").glob("*.md")}
    linked = {pathlib.Path(l).name for l in links}
    assert refs <= linked, ("orphans:", refs - linked)
    for l in links: assert (root / l.split("references/")[-1].join(["references/",""])).exists() or (root/l).exists(), l
    print("OK")
    PY
    ```
    - **Expected:** prints `OK` — frontmatter has exactly the five keys with
      `name: writing-bash-scripts`, body under 500 lines, every reference file is linked,
      and no SKILL.md link dangles (ref: structure Contracts). If `yaml` is unavailable,
      validate the five keys by manual parse.

### Verify Slice 1

14. **Checkpoint:** `wc -l .claude/skills/writing-bash-scripts/SKILL.md && grep -rl "do NOT use\|do not use" .claude/skills/writing-bash-scripts/SKILL.md && grep -l "writing-bash-scripts" README.md .claude/CLAUDE.md`
    - [ ] `SKILL.md` frontmatter parses as YAML with exactly the five in-repo keys and `name: writing-bash-scripts` (step 13).
    - [ ] SKILL.md body is under 500 lines / ~5000 tokens.
    - [ ] Every `references/` file is linked from SKILL.md; no orphan and no dangling link (step 13).
    - [ ] `description` contains both enumerated positive triggers and an explicit skip/negative clause.
    - [ ] `README.md` and `.claude/CLAUDE.md` both list `writing-bash-scripts`.
    - [ ] A sample script authored by following the guidance passes ShellCheck with zero warnings WHERE ShellCheck is available; otherwise record that the check is deferred (design OQ2).
    - [ ] skill-creator validation/eval passes, OR the hand-authoring deviation is noted in the slice notes.

---

## Rollback Notes

- Steps 1–10 (skill + references): purely additive new files under
  `.claude/skills/writing-bash-scripts/`. To roll back, delete the
  `.claude/skills/writing-bash-scripts/` directory; no other artifact depends on it
  (discovery is filesystem-based, no registry/manifest — design §Current State, Q6).
- Steps 11–12 (doc mirrors): non-load-bearing edits. To roll back, remove the added
  `writing-bash-scripts` rows/lines from `README.md` and `.claude/CLAUDE.md`. No
  functional impact on skill discovery.
- No DB migrations, config changes, or destructive operations in this slice.
