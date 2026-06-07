# PR: Add glab-cli skill for GitLab CLI agent guidance

**Ticket:** RUS-13
**Design:** design.md @ 2026-06-03T00:00:00Z
**Structure:** structure.md @ 2026-06-06T00:00:00Z

## Summary

Adds a new standalone `glab-cli` skill that gives agents opinionated, scripted
guidance for driving the GitLab CLI (`glab`). The skill ships a concise
`SKILL.md` body (155 lines) plus four `references/` files covering the full
command reference, authentication flows, CI/CD scripting patterns, and error
handling. It is greenfield — the repo previously had zero glab/GitLab footprint
— and is purely additive: no existing files are modified. Reviewer focus areas:
(1) accuracy of glab command/flag content, which is greenfield and could not be
machine-verified here because `glab` is not installed; (2) the
`description` trigger string, to confirm it does not collide with existing skill
auto-invocation; (3) the verbatim HARD STOP block kept byte-identical to the
repo source.

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: agentskills.io directory structure + valid frontmatter | `.claude/skills/glab-cli/SKILL.md` (frontmatter) | Checkpoint 16 — dir/`name`/`command` all `glab-cli`, `description` quoted, `argument-hint`+`allowed-tools` present → PASS |
| AC2: built using the skill-creator skill | authored via `skill-creator` (impl-log Session 1) | Manual — skill-creator invoked for authoring; full quantitative eval loop not run (placeholder harness, no human-in-loop) — see Deviations |
| AC3: SKILL.md body under 500 lines / 5000 tokens | `.claude/skills/glab-cli/SKILL.md` | Checkpoint 17 — `wc -l` = 155 lines, under ~500 soft budget → PASS |
| AC4: references/ covers full command ref, auth flows, CI/CD scripting, error handling | `references/{commands,authentication,ci-scripting,error-handling}.md` | Checkpoint 17 — all four files exist and body links each → PASS |
| AC5: covers auth, mr, issue, ci/pipeline, release, changelog, repo, api | `.claude/skills/glab-cli/references/commands.md` | Checkpoint 18 — all eight subcommand groups present → PASS |
| AC6: opinionated patterns (merge-after-green, stacked MRs, fork-based) | `SKILL.md` Workflow Patterns; `references/ci-scripting.md` | Checkpoint 18 (body sections present); human spot-check (open) |
| AC7: gitlab.com and self-hosted instances | `references/authentication.md` (`--hostname`, multi-host `config.yml`) | Manual review; OQ4 host-inference flagged inline |
| AC8: agent-specific scripted guidance (error handling, exit codes, JSON parsing) | `references/{ci-scripting,error-handling}.md`; `SKILL.md` HARD STOP + RecognizedState | Checkpoint 18 — verbatim HARD STOP block + distinct RecognizedState section → PASS |

## Changes by Slice

### Slice 1: Author the glab-cli skill (body + four references) via skill-creator

| File | Change | Lines |
|------|--------|-------|
| `.claude/skills/glab-cli/SKILL.md` | ✨ new | +155 |
| `.claude/skills/glab-cli/references/commands.md` | ✨ new | +166 |
| `.claude/skills/glab-cli/references/ci-scripting.md` | ✨ new | +90 |
| `.claude/skills/glab-cli/references/authentication.md` | ✨ new | +79 |
| `.claude/skills/glab-cli/references/error-handling.md` | ✨ new | +70 |

### Workflow artifacts (not feature code)

| File | Change | Lines |
|------|--------|-------|
| `.qrspi/RUS-13/questions.md` | ✨ new | +53 |
| `.qrspi/RUS-13/research.md` | ✨ new | +316 |
| `.qrspi/RUS-13/design.md` | ✨ new | +107 |
| `.qrspi/RUS-13/structure.md` | ✨ new | +66 |
| `.qrspi/RUS-13/plan.md` | ✨ new | +83 |
| `.qrspi/RUS-13/worktree.md` | ✨ new | +66 |
| `.qrspi/RUS-13/impl-log.md` | ✨ new | +30 |

## Testing Summary

- [x] Slice 1: frontmatter contract — Checkpoint 16 (`name`/`command`/dir == `glab-cli`, `description` quoted, `argument-hint`+`allowed-tools` present) → PASS
- [x] Slice 1: size + references — Checkpoint 17 (`wc -l SKILL.md` = 155, under ~500 budget; four reference files exist and are each linked from body: commands 4×, authentication 4×, ci-scripting 3×, error-handling 3×) → PASS
- [x] Slice 1: coverage + safety blocks — Checkpoint 18 (eight subcommand groups in commands.md; verbatim HARD STOP block; distinct RecognizedState section) → PASS
- [ ] Manual verification: human spot-check of glab command/flag accuracy against an installed `glab version` — NOT done; `glab` is not installed in this environment. Specific drift-prone flags to check: `glab mr merge --when-pipeline-succeeds` vs `--auto-merge`; `glab ci status --wait` vs `--live`.
- [ ] Manual verification: confirm `description` does not collide with existing skill auto-invocation triggers.

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| `SkillFrontmatter` (5 fields) | five-field dialect | five-field dialect used exactly | None — clean |
| `dir == name == command-minus-slash` | all `glab-cli` | all `glab-cli` | None — clean |
| `ReferenceFile` (4 files, linked) | four cohesive topics, body links each | four files, each linked | None — clean |
| `RecognizedState` vs `HardStopBlock` | textually distinct | kept distinct | None — clean |
| skill-creator eval loop (Slice 1 verification item) | author + pass eval loop | skill-creator authoring guidance followed; full quantitative eval loop NOT executed | Eval loop needs a human-in-loop reviewer and the repo `evals/` harness is a documented non-functional placeholder (design OQ2; plan step 15: "harness is a placeholder, not a gate"). Structural well-formedness verified via Checkpoints 16–18 instead. |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| 500-line/5000-token budget unverifiable in-repo (no token counter) | mitigated — body is 155 lines, deep detail pushed to `references/`; checked with `wc -l` | Trim body; move sections to references |
| skill-creator authoring rules cannot be grounded from research (out of scope) | accepted — authored against in-repo frontmatter dialect; skill-creator guidance applied; full eval loop deferred (OQ3) | n/a (additive content) |
| All glab command/flag content greenfield — no in-repo facts to verify against | discovered-new / open — flags could not be machine-verified (`glab` not installed); drift-prone flags flagged inline | Correct flags per official glab docs; delete skill dir if inaccurate |
| New non-`qrspi` skill could confuse auto-invocation if `description` overlaps | accepted — tightly scoped, quoted glab/GitLab-only `description`; human collision check still open | Narrow `description` trigger phrases |
| Multi-host/self-hosted conflict behavior has no in-repo precedent | mitigated — skill mandates explicit `--hostname`/`GITLAB_HOST`; host-inference choice flagged (OQ4) | Adjust authentication.md guidance |

Rollback for the whole feature is clean: the change is purely additive (one new
`.claude/skills/glab-cli/` directory, no modified files), so deleting the
directory fully reverts it.

## Open Items

- Human spot-check of glab command/flag accuracy against an installed `glab` — the one remaining verification item from the Slice 1 checklist; `glab` is not installed here. Drift-prone flags: `glab mr merge --when-pipeline-succeeds` vs `--auto-merge`, `glab ci status --wait` vs `--live`.
- OQ4: self-hosted/multi-host host inference — skill currently mandates explicit `--hostname`/`GITLAB_HOST`; flagged inline in `references/authentication.md` as an unresolved choice.
- OQ2: whether to add `evals/glab-evals.json` modeled on `graphite-evals.json` — excluded from this slice (eval harness is a non-functional placeholder); pending a human call.
- OQ1/OQ3: the 500-line/5000-token budget is an external skill-creator constraint, not a repo rule, and the full skill-creator eval loop was not run (no human-in-loop, placeholder harness). Tech debt: no repo-local size check or eval gate exists for skills.
- HARD STOP block is copied verbatim from `.claude/agents/qrspi-implement.md` — keep byte-identical if edited.
