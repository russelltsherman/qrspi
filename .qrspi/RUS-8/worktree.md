# Work Tree — Create a new agent skill called using argocd cli

**Plan basis:** plan.md @ 2026-05-31T00:00:00Z
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft
**Total sessions:** 1
**Critical path:** T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8 → T9 → T10 → T11 → T12 → T13 → T14 → T15 → T16 → T17

## Session 1

**Load:** structure.md §Slice 1, plan.md §Slice 1, design.md §Pattern Decisions, design.md §Open Questions, the ticket conventions block (RUS-8 description from Linear), the global skill-creator skill description.
**Estimated context:** ~25% (the skill text is short Markdown; the bulk of session cost is composing the references).

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Confirm skill-creator is invocable in this session and accepts the worktree path; if it cannot be scoped, HARD STOP. | — | §1 | S | pending |
| T2 | Verify `.claude/skills/using-argocd-cli/` does not already exist; HARD STOP if it does. | T1 | §2 | S | pending |
| T3 | Create `.claude/skills/using-argocd-cli/` directory. | T2 | §3 | S | pending |
| T4 | Create `.claude/skills/using-argocd-cli/references/` directory. | T3 | §4 | S | pending |
| T5 | Invoke skill-creator to scaffold `SKILL.md`. Validate it writes only inside the worktree. | T4 | §5 | M | pending |
| T6 | Edit SKILL.md frontmatter to match the five-field repo convention with correct values (`name`, `description`, `command`, `argument-hint`, `allowed-tools`). | T5 | §6 | S | pending |
| T7 | Write SKILL.md body sections: When to use, Opinionated defaults, Lifecycle at a glance, Interactive use, CI/CD automation, Escalation, References, When to defer. | T6 | §7 | M | pending |
| T8 | Sanity-check SKILL.md length (`wc -l ≤ 500`); trim and push overflow into references if needed. | T7 | §8 | S | pending |
| T9 | Create `references/authentication.md`. | T8 | §9 | M | pending |
| T10 | Create `references/sync-strategies.md`. | T8 | §10 | M | pending |
| T11 | Create `references/rollback-procedures.md`. | T8 | §11 | M | pending |
| T12 | Create `references/applicationset-generators.md`. | T8 | §12 | M | pending |
| T13 | Create `references/rbac-configuration.md`. | T8 | §13 | M | pending |
| T14 | Create `references/troubleshooting.md`. | T8 | §14 | M | pending |
| T15 | Run skill-creator validation pass if available; document outcome in impl-log. | T9, T10, T11, T12, T13, T14 | §15 | S | pending |
| T16 | Manual smoke prompts — write the two thought-experiment walkthroughs into impl-log and fix any gaps. | T15 | §16 | S | pending |
| T17 | **Verify Slice 1** — run all six verification checkpoints (file count, length, frontmatter, reference pointers, opinionated defaults present, ApplicationSets threshold present, lifecycle phases named). | T16 | §17–23 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 is the only slice. No additional session is required.

## Notes

The plan has 23 steps and one slice. All tasks fit in a single implementation session because:

1. The slice produces only Markdown documents; per-file output is small and bounded by the 500-line / 5000-token budget on SKILL.md and a few hundred lines per reference file.
2. There are no cross-slice contracts to keep alive across sessions, and no test runs that depend on previously-written code.
3. Risk of context overflow is low — the heaviest single load is the skill-creator response plus the reference draft text, which together fit comfortably inside a 40% budget.
4. The reference-writing tasks T9–T14 are mutually independent given T8, but ordering them sequentially in a single session is simpler and the cost is negligible. They could run in parallel if Russell prefers, but the gain is minimal.

If the implementation detects skill-creator writing outside the worktree (T1, T5) or the SKILL.md body refuses to fit under 500 lines after aggressive trimming (T8), pause and report rather than continue.
