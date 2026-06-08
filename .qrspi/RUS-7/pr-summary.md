# PR: RUS-7 — Add using-argo-workflows-cli agent skill

**Ticket:** RUS-7
**Design:** design.md @ 2026-06-03T00:00:00Z
**Structure:** structure.md @ 2026-06-06T00:00:00Z

## Summary

This PR adds a new self-contained agent skill, `using-argo-workflows-cli`, that
gives the harness reusable guidance for operating Argo Workflows from the `argo`
CLI. It follows the established self-contained skill pattern (`qrspi-ticket` /
`qrspi-work`): a lean 104-line `SKILL.md` body carries the frontmatter, an
`argo`-binary prerequisite check with hard-stop-on-failure behavior, and routing
pointers into four topic-scoped `references/*.md` files (submission/monitoring,
debugging/lifecycle, authoring, cron). The skill is **not** indexed in any
catalog — neither the `README.md` directory tree nor the `.claude/CLAUDE.md`
"Available skills" list is updated, per reviewer feedback that re-indexing skills
in those files is redundant since the harness auto-discovers them. Reviewer focus:
the `triple-name-invariant` (dirname ==
frontmatter `name` == `command` minus `/`), reference-link resolution, and that
all 15 argo command groups are covered across the reference files. Note: this
ships Markdown content only — no executable code, no runtime types, and there is
no in-repo validator/lint, so all contract checks are manual greps (design Q11).

## Acceptance Criteria Mapping

This feature ships docs/content, not code; "Test" is the manual contract
verification (T15 greps in the impl log) since no automated validator exists.

| Criterion | Implementation | Test |
|-----------|---------------|------|
| agentskills.io structure + valid SKILL.md frontmatter | `.claude/skills/using-argo-workflows-cli/SKILL.md` (frontmatter block) | `frontmatter-schema` + `triple-name-invariant` greps (impl-log T15) |
| Built using the skill-creator skill | authored via loaded `skill-creator` skill | T1 BLOCKING gate (impl-log "Notes") |
| SKILL.md body under 500 lines / 5000 tokens | `SKILL.md` (104 lines) | `body-size-budget` (`wc -l` = 104) |
| Detailed reference material in references/ | `references/{submission-and-monitoring,debugging-and-lifecycle,authoring,cron-workflows}.md` | `reference-link-contract` grep (all links resolve) |
| Covers all 15 argo command groups | `references/*.md` (all four files) | `coverage-contract` grep — all 15 groups, each ≥7 hits (impl-log) |
| DAG vs Steps selection criteria | `references/authoring.md` | coverage grep (DAG/Steps present) |
| Retry strategy + exponential backoff | `references/authoring.md` | coverage grep (exponential backoff present) |
| Debugging escalation (get → logs → kubectl describe) | `references/debugging-and-lifecycle.md` | coverage grep (`kubectl describe` escalation present) |
| CronWorkflow lifecycle | `references/cron-workflows.md` | coverage grep (cron concurrency/timezone present) |
| Resource management (limits, nodeSelector, parallelism) | `references/authoring.md` | coverage grep (nodeSelector/parallelism present) |
| Artifact config (key parameterization, GC) | `references/authoring.md` | coverage grep (artifactGC present) |
| Catalogs updated (not stale) | n/a — neither `README.md` nor `.claude/CLAUDE.md` is indexed (redundant per reviewer; the harness auto-discovers skills) | manual: no skill-index entry added in either catalog |
| hard-stop prerequisite check | `SKILL.md` body | `hard-stop-prereq` (availability check + surface-and-stop) |

## Changes by Slice

### Slice 1: Author the argo-workflows-cli skill and references

| File | Change | Lines |
|------|--------|-------|
| `.claude/skills/using-argo-workflows-cli/SKILL.md` | ✨ new | +104 |
| `.claude/skills/using-argo-workflows-cli/references/authoring.md` | ✨ new | +214 |
| `.claude/skills/using-argo-workflows-cli/references/submission-and-monitoring.md` | ✨ new | +168 |
| `.claude/skills/using-argo-workflows-cli/references/debugging-and-lifecycle.md` | ✨ new | +157 |
| `.claude/skills/using-argo-workflows-cli/references/cron-workflows.md` | ✨ new | +129 |

Implementation total: 5 files, +772 lines (skill body + four references only — no
catalog index entry, per reviewer). (The full `main...HEAD` diff also
includes 7 design-phase artifacts under `.qrspi/RUS-7/` — questions, research,
design, structure, plan, worktree, impl-log — carried by the upstream stacked
design/plan commits, not this implementation slice.)

## Testing Summary

No runtime code ships, so verification is the plan's contract greps (impl-log
Session 1, T15) — there is no in-repo validator/lint (design Q11).

- [x] Plan verification command (ls + wc + grep contract checks) — all 8 contracts pass, 0 fail
- [x] `body-size-budget` — `wc -l SKILL.md` = 104 (under 500)
- [x] `coverage-contract` grep across `references/` — all 15 command groups present (each ≥7 hits); DAG/Steps, exponential backoff, nodeSelector/parallelism, artifactGC, `kubectl describe` escalation, cron concurrency/timezone all covered
- [x] `triple-name-invariant` / `frontmatter-schema` — dirname == name == command-minus-`/`, five conventional keys only
- [x] `reference-link-contract` — every `references/<file>.md` link in body resolves
- [x] Catalog presence — intentionally NOT indexed in any catalog (neither `README.md` nor `.claude/CLAUDE.md`); the harness auto-discovers skills, so re-indexing is redundant per reviewer

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| (none) | | | impl-log records "Deviations from structure.md: none" |

One deviation from **plan.md** (not structure.md): plan T12 said add the skill to
the README "skills table and the directory tree", but on reviewer feedback no
catalog index entry is added at all — neither in `README.md` nor in
`.claude/CLAUDE.md` — because the harness auto-discovers skills and re-indexing
them in those files is redundant. The skill therefore ships as the SKILL.md body
plus its four references only. This does not change any structure contract.

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| `skill-creator` not installed, blocking prescribed authoring path | mitigated — skill was loaded and used (T1 BLOCKING gate satisfied); its progressive-disclosure structure + frontmatter validation applied | n/a |
| No validator/lint, so malformed frontmatter / broken links ship undetected | accepted — mitigated by manual T15 contract greps; all links resolve, schema matches | revert the slice commit |
| SKILL.md body exceeds 500-line / 5000-token budget across 15 groups | mitigated — body is 104 lines; all command detail pushed to `references/` | n/a |
| `description` too generic, harness fails to auto-invoke | accepted — explicit "Use when…" + argo trigger phrases packed into `description`; no in-repo firing log exists to confirm | edit `SKILL.md` description |
| README catalog drift | not applicable — no catalog index entry is added (neither `README.md` nor `.claude/CLAUDE.md`); the harness auto-discovers skills, so there is nothing to drift | n/a |
| Argo CLI conventions outdated vs installed `argo` version | accepted — reference content is version-aware prose; OQ3 resolved to assert reachability (`argo version`), not a minimum version | update `references/*.md` |

Rollback for the whole feature: revert the single implementation slice commit —
it is purely additive (5 new files, no deletions).

## Open Items

- **OQ3 (resolved in impl):** prerequisite check asserts `argo` reachability via
  `argo version`, not a minimum version; revisit if a version floor becomes needed.
- **OQ5 (resolved in impl):** `allowed-tools: Bash, Read` left unscoped because the
  documented debugging escalation shells out to `kubectl describe`, which a
  `Bash(argo:*)` scope would block. Revisit if tighter scoping is desired.
- No quantitative skill-creator eval-loop benchmark was run — there is no runtime
  behavior to benchmark for a pure-docs skill; verification is structural greps only.
- No automated validator/lint exists for skill frontmatter or reference links; a
  follow-up ticket could add one to replace the manual contract greps.
