# Work Tree — Create a new agent skill: using GitHub CLI

**Plan basis:** plan.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total sessions:** 2
**Critical path:** T1 → T10 → T9 → T15 → T16 → T17 (6 tasks)

> The plan has two slices. Slice 2 is gated on OQ4 ("yes"); if OQ4 resolves
> "no", skip Session 2 entirely. Within Slice 1, the four `references/*.md`
> creations (T10–T13) and several SKILL.md body sections (T5–T8) are mutually
> independent and may proceed in parallel once the skill is scaffolded (T1) and
> frontmatter exists (T2). T9 (reference links) is the join point — it requires
> the reference files to exist.

## Session 1 — Slice 1: Author the skill + references

**Load:** structure.md §Types (SkillFrontmatter, ReferenceSet), structure.md §Contracts
        (registration, capability-firewall, CI-auth, link contracts), plan.md §Slice 1,
        design.md §Decision 2/3/4, Risk 1/4/5, OQ1/OQ2/OQ3
**Estimated context:** ~30% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Invoke `skill-creator` (+ eval loop) to scaffold/author the skill — never hand-ship ad-hoc | — | §1.1 | S | pending |
| T2 | Create `SKILL.md` frontmatter only — five `SkillFrontmatter` fields; `name: using-github-cli` matching directory | T1 | §1.2 | S | pending |
| T3 | Set `description` field to embed "Use when…" trigger prose per Decision 2 | T2 | §1.3 | S | pending |
| T4 | Set `allowed-tools` to read tools + `Bash(gh:*)` read/metadata only (capability firewall; pending OQ3) | T2 | §1.4 | S | pending |
| T5 | Add opinionated-defaults section (squash merge, branch deletion, HEREDOC bodies) | T2 | §1.5 | M | pending |
| T6 | Add non-interactive scripting section (`--json`/`--jq`, `--no-pager`, `GH_PROMPT_DISABLED`, exit codes) | T2 | §1.6 | M | pending |
| T7 | Add auth section (`gh auth status`/`login`, `GH_TOKEN`/CI per CI-auth contract; pending OQ2) | T2 | §1.7 | M | pending |
| T8 | Add "defer mutations to orchestration layer" boundary section pointing to orchestrator / `using-graphite-cli` | T2 | §1.8 | S | pending |
| T10 | Create `references/gh-api.md` — advanced `gh api` REST patterns | T1 | §1.10 | M | pending |
| T11 | Create `references/graphql.md` — GraphQL multi-resource join examples | T1 | §1.11 | M | pending |
| T12 | Create `references/automation.md` — non-interactive/CI recipes, env vars per CI-auth contract | T1 | §1.12 | M | pending |
| T13 | Create `references/extensions.md` — extension/alias recommendations | T1 | §1.13 | S | pending |
| T9 | Add four `references/*.md` links to `SKILL.md` using skill-relative paths (link contract) | T2, T10, T11, T12, T13 | §1.9 | M | pending |
| T14 | Manual frontmatter + budget check (five fields, `name`==dir, `wc -l` & token budget) | T2, T3, T4 | §1.14 | S | pending |
| T15 | **Verify Slice 1** — checkpoint: all five files non-empty, frontmatter/budget/link/tool-scope/review gates | T3, T4, T5, T6, T7, T8, T9, T14 | §1.15 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete and verified. Slice 2 is a separate gated unit (OQ4)
touching only project docs; a fresh context avoids carrying the full skill-authoring
working set into a one-line registration edit.

## Session 2 — Slice 2: Register the skill in project docs (gated on OQ4="yes")

**Load:** structure.md §Slice 2, plan.md §Slice 2, design.md §Decision 3 / Risk 1 / OQ4,
        impl-log.md §Slice 1 (final skill `name` + path only)
**Estimated context:** ~12% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T16 | Add `using-github-cli` to available-skills list in `.claude/CLAUDE.md` (+ worktree copy) with one-line read/metadata-vs-mutation boundary note | T15 | §2.16 | S | pending |
| T17 | **Verify Slice 2** — checkpoint: OQ4=="yes", entry present, boundary note references `using-graphite-cli`/orchestrator-only mandate, human review | T16 | §2.17 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Final session. All slices complete; no further sessions. If OQ4 resolves
"no", Session 2 is skipped and the feature ends after Session 1.
