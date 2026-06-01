# Design — Create a new agent skill called using-graphite-cli

**Ticket:** RUS-6
**Research basis:** research.md @ 2026-06-01T00:00:00Z
**Generated:** 2026-06-01T00:00:00Z
**Status:** draft

## Current State

This repo expects skills to live at `.claude/skills/<skill-name>/SKILL.md`, one directory per skill, documented in the README structure block and confirmed by the actual layout of 10 skill directories (ref: Q1). A skill's identity is conventional: the directory name, the `name` frontmatter value, and the `command` stem are all identical, lowercase, and hyphen-separated (ref: Q6). Frontmatter consistently carries five fields across existing skills — `name`, `description`, `command`, `argument-hint`, and `allowed-tools` — with no in-repo schema file enforcing them; the contract is convention-only (ref: Q3). The `description` field doubles as the auto-invocation trigger text, while `command` drives explicit slash invocation; no wrapper file beyond `SKILL.md` is required for a knowledge-only skill that spawns no sub-agent (ref: Q4).

Exactly one existing skill, `qrspi-work`, uses a `references/` sub-resource; it loads the reference by a skill-relative path (`references/review-cascade.md`) via an explicit on-demand `Read` instruction rather than inlining it, which keeps `SKILL.md` small. No skill in the repo uses `scripts/` or `assets/` subdirectories (ref: Q2). The repo does NOT already contain a `using-graphite-cli` skill or any git-delegation skill — `.claude/skills/` holds only the 10 QRSPI skills, so there is nothing to conflict with or replace (ref: Q6).

Graphite command conventions already exist in-repo but only as embedded fragments, not as a dedicated reference. The orchestrator `qrspi-work/SKILL.md` and `evals/graphite-evals.json` establish that every `gt` command carries `--no-interactive`, commits use `gt create`/`gt modify` (never raw `git commit`), and after mutations the agent runs `gt log short --no-interactive` to verify and surface stack state (ref: Q12). Planning uses a single amended commit — `gt modify -c` to create, `gt modify` (no `-c`) to amend — establishing the `gt modify` amend semantics but NOT a detect/recover procedure for a branch that accidentally accumulates multiple commits (ref: Q7). The repo contains one concrete metadata-drift recovery (rename-detach + force-submit for a branch pinned to a closed/merged PR in `.git/.graphite_pr_info`) and the general rule "never run raw git when a gt equivalent exists," but no general git/Graphite mixing recovery and no `gt continue` vs `git rebase --continue` conflict sequence (ref: Q8, ref: Q9). Repo-level Graphite state lives in `.git/` (`.graphite_pr_info`, `gt track --parent`), while global user config lives in the bind-mounted `~/.config/graphite/`; the prescriptive "verify trunk before operating" guidance does not exist in-repo (ref: Q5).

The eval harness under `scripts/` (driven by `run_loop.sh`) hard-requires suite JSON with top-level `name` + `cases`, each case needing `id` + `prompt` + `assertions`. A pre-existing suite `evals/graphite-evals.json` (`"skill_name": "graphite"`, 5 cases) already targets a Graphite skill, but its `{text, type}` assertion shape (`command_check`, `flag_check`, etc.) is NOT in `grade.py`'s `CHECKS` registry, so it cannot be scored by the current harness without new code; additionally `run_eval.py`'s executor is a stub that produces zero scores (ref: Q10). No lint/validation step enforces SKILL.md-specific acceptance criteria (line/token limits, frontmatter validity, `references/` presence); the only directly reusable check is `line_count`, and unknown checks named in a suite are silently skipped rather than failed (ref: Q11).

## Desired End State

A new knowledge-only skill exists at `.claude/skills/using-graphite-cli/` with a valid `SKILL.md` and a `references/` directory. It maps to the ticket's acceptance criteria as follows:

- **agentskills.io directory structure + valid frontmatter** → directory `using-graphite-cli/` with `name: using-graphite-cli`, `command: /using-graphite-cli`, a single-line `description`, `argument-hint`, and `allowed-tools` matching the dir==name==command convention (ref: Q6, ref: Q3).
- **Built using the Anthropic skill builder** → authored via the skill-creator skill; the skill-creator itself is out of project scope (global), so this is a process step, not an in-repo artifact (ref: Q1).
- **SKILL.md under 500 lines / 5000 tokens** → body stays a concise rules-and-workflow summary; full command reference and edge cases are pushed to `references/` and lazy-loaded, following the `qrspi-work` pattern (ref: Q2).
- **Detailed reference material in `references/`** → at minimum a full command reference plus an edge-cases/recovery file, loaded on demand via skill-relative `Read` instructions (ref: Q2).
- **Single-commit-per-branch as a hard rule** → SKILL.md states `gt create` for new branches and `gt modify --all` to amend (never `git branch` / `git commit --amend`), with detect-and-recover guidance authored fresh since none exists in-repo (ref: Q7).
- **Complete Create → Submit → Modify → Sync loop** → documented in SKILL.md body, consistent with the in-repo `gt modify` amend semantics and `gt submit`/`gt sync` usage (ref: Q12, ref: Q7).
- **Conflict resolution via `gt continue` (never `git rebase --continue`)** → authored fresh in the recovery reference, with post-resolution verification via `gt log short --no-interactive` (ref: Q8).
- **Stack navigation + directionality** → `gt bu`/`gt bd`/`gt stack top`/`gt log short` and downstack=toward-trunk/upstack=away-from-trunk, in SKILL.md (ref: Q12).
- **Submit flag defaults `--no-edit --publish` for agents** → encoded as the agent default, consistent with the in-repo `--no-interactive` convention (ref: Q12).
- **Warn against mixing raw git with Graphite-tracked branches** → SKILL.md hard rule plus drift-recovery in the reference, extending the in-repo closed-PR recovery and "never raw git" rule (ref: Q9).

## Delta

New files:
- `.claude/skills/using-graphite-cli/SKILL.md` — frontmatter + concise body covering: install/auth/trunk-verify, the Create→Submit→Modify→Sync loop, single-commit hard rule, stack navigation + directionality, submit flag defaults, the raw-git warning, and explicit `Read references/...` pointers.
- `.claude/skills/using-graphite-cli/references/command-reference.md` — full `gt` command/flag catalog (create, submit/ss, modify, sync, bu/bd/stack top/log short, ds/us, downstack edit, branch split, repo trunk/remote/init).
- `.claude/skills/using-graphite-cli/references/edge-cases.md` — single-commit detect/recover, restack conflict `gt continue` sequence + verification, raw-git/Graphite drift recovery, bottom-up merge ordering.

Optional / decision-dependent:
- `evals/graphite-evals.json` — reconcile `"skill_name": "graphite"` → `using-graphite-cli` and/or its assertion shape (see Decision 3). Adding matching `CHECKS` entries to `scripts/grade.py` would be required to actually score it (ref: Q11).

No project code performs skill registration — discovery is implicit on file placement, so no loader/wrapper changes are needed (ref: Q4). No `.claude/agents/` companion is required because this skill provides knowledge and spawns no sub-agent (ref: Q4).

## Pattern Decisions

### Decision 1: SKILL.md body vs references split

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Single self-contained SKILL.md, everything inline | One file; nothing to lazy-load | Risks blowing the 500-line/5000-token limit; contradicts the in-repo lazy-load pattern |
| B | Concise SKILL.md + `references/` loaded on demand | Mirrors `qrspi-work`; keeps body small; satisfies the "references/ present" criterion | Two-plus files; agent must follow Read pointers |

**Recommendation:** Option B
**Rationale:** `qrspi-work` is the one in-repo precedent and it lazy-loads `references/review-cascade.md` via a skill-relative Read, explicitly to keep SKILL.md small (ref: Q2). The ticket independently requires both a sub-500-line body and a populated `references/` dir, so B satisfies both at once.
**NEW PATTERN?** No — directly reuses the `qrspi-work` references pattern.

### Decision 2: Frontmatter `allowed-tools` surface

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Omit / leave broad | Less to specify | Breaks the firewall convention; inconsistent with every existing skill (ref: Q3) |
| B | Knowledge-only minimal (e.g. `Read` + `Bash(gt:*)`) | Matches the firewall convention; lets the skill read its own references and run gt | Must enumerate the gt surface deliberately |
| C | No `allowed-tools` since it is convention-only | Simplest frontmatter | Diverges from all 10 existing skills; loses the security-boundary signal |

**Recommendation:** Option B
**Rationale:** Every existing skill treats `allowed-tools` as a deliberate security firewall, not decoration (e.g. `qrspi-research` allows only `Agent, Bash(pwd:*)`) (ref: Q3). A Graphite skill needs to read its own `references/` and run `gt` commands, so a minimal explicit allowlist fits the convention. Exact tool tokens are an open question (OQ2).
**NEW PATTERN?** No — reuses the `allowed-tools` firewall convention.

### Decision 3: What to do with the pre-existing eval suite

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Leave `graphite-evals.json` as-is | Zero churn | `skill_name: graphite` mismatches `using-graphite-cli`; assertions still ungradeable; suite is dead weight (ref: Q10, ref: Q11) |
| B | Rename `skill_name` only | One-line fix aligns naming | Still ungradeable — assertion types absent from `grade.py` CHECKS (ref: Q11) |
| C | Rename + add matching `CHECKS` to grade.py + (eventually) un-stub the executor | Makes the suite actually runnable and scores acceptance criteria | Larger scope; executor stub means scores stay zero until that is fixed too (ref: Q10) |

**Recommendation:** Option B for this ticket, with Option C flagged as a known follow-up
**Rationale:** The ticket's acceptance criteria are about the skill artifact, not a green eval run; the harness is a stub that produces zeros today (ref: Q10), so full gradeability is out of reach within this ticket. Renaming removes the naming mismatch cheaply (ref: Q6) while not pretending the suite scores. Whether to attempt C now is OQ1.
**NEW PATTERN?** No for B. C would add NEW `CHECKS` entries (e.g. frontmatter/token/references-presence) that do not exist today (ref: Q11) — flag if pursued.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Graphite command/recovery details (gt continue sequence, single-commit recovery, drift recovery) are authored from the ticket alone because the canonical reference is out of project scope (ref: Q8, Q9, Q7) | high | med | Treat the ticket's convention list as the spec; cross-check against the in-repo `gt log short --no-interactive` verification and `--no-interactive` conventions; have a human verify command accuracy at review |
| SKILL.md exceeds 500-line / 5000-token limit | med | med | Push all command tables and edge cases into `references/`; keep body to rules + the four-step loop (Decision 1) |
| Acceptance criteria assumed measurable by evals are not — harness is a stub and SKILL-size/frontmatter checks do not exist (ref: Q10, Q11) | high | med | Verify criteria by manual inspection (line count, frontmatter fields, references/ presence); do not gate the ticket on a green eval run |
| Stale CLAUDE.md / eval `skill_name: graphite` cause naming confusion (ref: Q6 inconsistencies) | med | low | Standardize on `using-graphite-cli` everywhere; optionally rename the eval suite (Decision 3) |
| Frontmatter `description` quoting — values with colons must be quoted (ref: Q3) | low | low | Single-line description; quote if it contains a colon or embedded quote, following the `qrspi-work` example |

## Open Questions

- OQ1: For the pre-existing `evals/graphite-evals.json`, do we take Decision 3 Option B (rename only) within this ticket, or expand scope to Option C (add `CHECKS` to `grade.py`)? The latter touches the shared eval harness.
- OQ2: What exact `allowed-tools` token set should the skill declare (e.g. `Read`, `Bash(gt:*)`, anything else)? The convention is established but the precise surface for a knowledge-plus-gt skill is a judgment call.
- OQ3: Should `references/` be two files (command-reference + edge-cases) or split finer (e.g. a dedicated conflict-resolution file)? The ticket says "full command reference and edge cases" without prescribing file count.
- OQ4: Does the skill need to prescribe install/auth steps (`brew install graphite`, `gt auth login`) for agents, given the devcontainer already pins and bind-mounts Graphite (ref: Q5)? Possibly redundant in this environment.
