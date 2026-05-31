# PR: RUS-7 — Add using-argo-workflows-cli skill (body + references)

**Ticket:** RUS-7
**Design:** design.md @ 2026-05-31T00:00:00Z
**Structure:** structure.md @ 2026-05-31T00:00:00Z

## Summary

Adds a new agent skill `using-argo-workflows-cli` — a general-purpose, agentskills.io-conformant reference skill for the Argo Workflows `argo` CLI. It ships a lean `SKILL.md` body (79 lines, well under the 500-line / 5000-token budget) plus four `references/*.md` files holding the bulk of the conventions (command catalog, templates, reliability, cron/debugging), following the `qrspi-work` progressive-disclosure precedent. Built via the global `skill-creator` skill and reconciled to the repo's 5-field frontmatter and directory conventions. Reviewers should focus on three things: (1) that the body genuinely points into every reference file (no orphans) and stays under budget; (2) the two unresolved naming/registration questions — this is the first non-`qrspi-` prefixed skill (OQ1) and Slice 2 registration was gated off pending OQ3; (3) that `.claude/workflows/qrspi-batch.js` appears in the three-dot diff only because the branch independently re-committed a file already present on `main` (identical content) — it is **not** a RUS-7 deliverable and will disappear on rebase.

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: agentskills.io directory structure + valid frontmatter | `.claude/skills/using-argo-workflows-cli/SKILL.md` + `references/` dir | `test -f SKILL.md && ls references/` → SKILL.md + 4 refs — PASS (impl-log S1) |
| AC2: Built using the Anthropic skill builder skill | build-time `skill-creator` invocation (process step, no committed artifact) | impl-log S1 note: skill-creator conventions applied + reconciled to repo frontmatter |
| AC3: SKILL.md body under 500 lines / 5000 tokens | `SKILL.md` (79 lines) | `wc -l SKILL.md` → 79 (≤500); ~1.3k tokens (≤5000) — PASS (impl-log S1) |
| AC4: Detailed reference material in `references/` | `references/{cli-commands,templates,reliability,cron-and-debugging}.md` | `ls references/` → 4 files — PASS (impl-log S1) |
| AC5: Covers all 15 major command groups | `references/cli-commands.md` | `grep -E -o '<15 groups>' \| sort -u \| wc -l` → 15 — PASS (impl-log S1) |
| AC6: DAG vs Steps selection criteria | `references/templates.md` | impl-log S1: convention present in assigned ref + summarized in body |
| AC7: retry/backoff conventions | `references/reliability.md` | impl-log S1: convention present in assigned ref + summarized in body |
| AC8: debugging escalation (`argo get`→`argo logs`→`kubectl describe`) | `references/cron-and-debugging.md` | impl-log S1: convention present in assigned ref + summarized in body |
| AC9: CronWorkflow lifecycle | `references/cron-and-debugging.md` | impl-log S1: convention present in assigned ref + summarized in body |
| AC10: resource conventions | `references/reliability.md` | impl-log S1: convention present in assigned ref + summarized in body |
| AC11: artifact best practices | `references/reliability.md` | impl-log S1: convention present in assigned ref + summarized in body |
| AC12: all CLI invocations use non-interactive/scriptable flags | all `references/*.md` (explicit `--namespace`, lint/dry-run before submit) | structure Contracts + impl-log S1 verification |
| AC13 (contract): no orphan reference files; body points to each | `SKILL.md` body pointers | `grep -c -E 'cli-commands\|templates\|reliability\|cron-and-debugging' SKILL.md` → 10 (≥4, no orphans) — PASS (impl-log S1) |
| AC14 (contract): dir == name == command invariant; exactly 5 frontmatter fields | `SKILL.md` frontmatter | `head -7 SKILL.md` → 5 repo-standard fields; invariant holds — PASS (impl-log S1) |

## Changes by Slice

### Slice 1: Author the `using-argo-workflows-cli` skill (body + references)

| File | Change | Lines |
|------|--------|-------|
| `.claude/skills/using-argo-workflows-cli/SKILL.md` | ✨ new | +79 |
| `.claude/skills/using-argo-workflows-cli/references/cli-commands.md` | ✨ new | +190 |
| `.claude/skills/using-argo-workflows-cli/references/templates.md` | ✨ new | +95 |
| `.claude/skills/using-argo-workflows-cli/references/reliability.md` | ✨ new | +66 |
| `.claude/skills/using-argo-workflows-cli/references/cron-and-debugging.md` | ✨ new | +85 |

### Slice 2 (conditional): Register skill in project `.claude/CLAUDE.md` — SKIPPED

| File | Change | Lines |
|------|--------|-------|
| `.claude/CLAUDE.md` | (not modified — gate OQ3 not resolved "yes") | 0 |

Slice 2 was correctly skipped: its gate requires OQ3 resolved "yes," which it is not (`design.md:94`). No file was modified; commit `2937893` records the gate evaluation only.

### Workflow / process artifacts (not ticket deliverables)

| File | Change | Lines | Note |
|------|--------|-------|------|
| `.qrspi/RUS-7/{questions,research,design,structure,plan,worktree,impl-log}.md` | ✨ new | +727 | QRSPI phase artifacts (committed in `6958efb` planning commit) |
| `.claude/workflows/qrspi-batch.js` | ✨ new (artifact of divergent history) | +112 | **Not a RUS-7 change** — identical content already on `main` (`git diff main HEAD` → 0 lines). Branch re-committed it; resolves on rebase onto `main`. |

## Testing Summary

- [x] Slice 1: structure — `test -f SKILL.md && ls references/` — SKILL.md + 4 reference files present — PASS
- [x] Slice 1: budget — `wc -l SKILL.md` — 79 lines (≤500), ~1.3k tokens (≤5000) — PASS
- [x] Slice 1: no orphans — `grep -c -E 'cli-commands|templates|reliability|cron-and-debugging' SKILL.md` — 10 hits (≥4) — PASS
- [x] Slice 1: command coverage — `grep -E -o '<15 groups>' references/cli-commands.md | sort -u | wc -l` — 15 — PASS
- [x] Slice 1: frontmatter — `head -7 SKILL.md` — exactly 5 repo-standard fields; dir == name == command invariant holds — PASS
- [x] Slice 2: gate — grep of artifacts for OQ3 resolution — no "yes" found; slice correctly skipped — PASS (skip is conforming)
- [ ] Manual verification: no runtime/eval harness validates SKILL.md conformance (none exists — design Q11); reviewer must eyeball references for argo-version accuracy and non-interactive-flag discipline.

Note: all tests are manual `grep`/`wc`/`test` assertions recorded in `impl-log.md`. There is no automated test suite or eval case for skill conformance in this repo (design Q7, Q11) — verification is checklist-based by design.

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| (none) | Slice 1 per structure §Slice 1 | Implemented exactly as specified | impl-log records "Deviations from structure.md: none" for both sessions |
| Slice 2 execution | "Skip entirely unless OQ3 resolved to require registration" | Skipped | Conforming behavior — gate not satisfied; structure §Slice 2 mandates skip |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| SKILL.md body exceeds 500-line / 5000-token budget (repeat of `qrspi-work` overrun) | **mitigated** — body is 79 lines / ~1.3k tokens, well under budget | `git rm -r .claude/skills/using-argo-workflows-cli/` |
| `skill-creator` output diverges from repo conventions | **mitigated** — output reconciled to 5-field frontmatter + repo dir layout (impl-log S1) | Re-run skill-creator or revert the skill dir |
| Non-`qrspi-` name surprises maintainers/tooling | **accepted, unresolved** — OQ1 not confirmed by a human; first non-`qrspi-` skill ships on the recommended name | Rename dir + `name` + `command` together to a `qrspi-`-prefixed value |
| No eval/lint validates SKILL.md conformance | **accepted** — manual checklist review only; conformance eval deferred (design Q11, OQ4) | n/a — follow-up ticket to add eval case |
| Argo conventions may drift from upstream CLI versions | **mitigated** — references target argo v3.5.x (OQ5 resolution) with principle-based guidance + version note per file | Update version note + flags in `references/*.md` |
| **NEW (discovered):** branch re-commits `qrspi-batch.js` already present on `main` | **discovered** — three-dot diff shows it as new; content is identical to `main` (`git diff main HEAD` → 0 lines) | Rebase branch onto current `main` (`7994b2a`) to drop the duplicate; no content change results |

## Open Items

- **OQ1 (naming):** Confirm `using-argo-workflows-cli` vs a `qrspi-`-prefixed name. Skill ships on the recommended non-`qrspi-` name; a reversal renames the dir, `name`, and `command` together. Reviewer decision required.
- **OQ2 (allowed-tools scope):** Resolved at build time to read-only guidance (`allowed-tools: Read, Bash(argo:*), Bash(kubectl:*)`) — CLI examples are advisory, no write/submit auto-execution. Confirm this scope is intended.
- **OQ3 (registration):** Unresolved → Slice 2 skipped. `.claude/CLAUDE.md` still lists only `qrspi-*` skills. To register later: resolve OQ3 "yes," then re-run Slice 2 to add the entry.
- **OQ4 (conformance eval):** Out of scope this ticket. Follow-up: add a SKILL.md conformance eval case (harness has the extension point, no check exists today).
- **OQ5 (argo version):** Resolved to Argo Workflows / `argo` CLI v3.5.x with principle-based guidance. Revisit if the target cluster version differs.
- **Rebase before merge:** Rebase `RUS-7/slice-2` onto `main` (`7994b2a`) so the duplicated `qrspi-batch.js` drops out of the diff, leaving only the 5 skill files + the `.qrspi/RUS-7/` artifacts.
- **"Built using skill-creator" criterion** has no committed artifact (it is a process step) — reviewers must trust the impl-log build record (design/structure Unverified Assumptions).
