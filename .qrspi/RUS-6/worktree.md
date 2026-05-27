# Work Tree — using graphite cli skill

**Plan basis:** plan.md @ 2026-05-27
**Generated:** 2026-05-27T00:00:00Z
**Status:** draft
**Total sessions:** 1
**Critical path:** T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8 → T9 → T10 → T11 → T12

## Session 1

**Load:** structure.md §Types, structure.md §Contracts, plan.md §Slice 1
**Estimated context:** 10%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Write SKILL.md YAML frontmatter with all 5 required keys (name, description, command, argument-hint, allowed-tools) | — | §1.1 | S | pending |
| T2 | Write "Graphite CLI Primer" section covering trunk, stacks, upstack/downstack concepts | T1 | §1.1 | S | pending |
| T3 | Write "Initialization" section documenting `gt init` and `gt auth --token` | T2 | §1.1 | S | pending |
| T4 | Write "Core Workflow" section documenting the create-modify-submit loop with exact commands and `--no-interactive` flag | T3 | §1.1 | S | pending |
| T5 | Write "Branch Navigation" section documenting stack traversal commands (checkout, up, down, bottom, top, trunk) | T4 | §1.1 | S | pending |
| T6 | Write "Single Commit Per Branch" section encoding the planning convention (modify -c, then amends) | T5 | §1.1 | S | pending |
| T7 | Write "Restacking" section covering automatic restack via modify and explicit gt sync | T6 | §1.1 | S | pending |
| T8 | Write "Submitting PRs" section distinguishing narrow submit from --stack submit | T7 | §1.1 | S | pending |
| T9 | Write "Downstack/Upstack Operations" section covering move --onto and delete --force | T8 | §1.1 | S | pending |
| T10 | Write "Merging Stacks" section documenting gt merge --confirm and cleanup | T9 | §1.1 | S | pending |
| T11 | Write "Integration with GitHub" section and "Scope Guidance" decision table | T10 | §1.1 | S | pending |
| T12 | Verify SKILL.md: file exists, frontmatter valid, all 11 sections present, commands use `--no-interactive` | T11 | §1.1 | S | pending |
