# Work Tree — writing-bash-scripts agent skill

**Plan basis:** plan.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft
**Total sessions:** 1
**Critical path:** T1 → T2 → T3 → T4 → T5

## Session 1

**Load:** plan.md §Slice 1, structure.md (convention sections referenced in plan)

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Verify `.claude/skills/writing-bash-scripts/references/` directory is empty | — | §1.1 | S | pending |
| T2 | Create SKILL.md with YAML frontmatter, 12 convention sections, code examples, and Gotchas section | T1 | §1.2 | M | pending |
| T3 | Create bash-template.sh with strict mode, argument parsing, subcommand dispatcher, logging, quoting, dependency checking, temp cleanup, usage/help | T2 | M | pending |
| T4 | Verify syntax and content: `bash -n` on template, line count on SKILL.md, grep for all section headers and frontmatter keys | T3 | §1.4 | S | pending |
| T5 | **Verify Slice 1** — Confirm full acceptance criteria (frontmatter, line count, sections, gotchas, BATS-core mention, dependency pattern, template validity) | T4 | §1.5 | S | pending |
