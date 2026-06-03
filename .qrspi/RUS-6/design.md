# Design — Create a new agent skill called using-graphite-cli

**Ticket:** RUS-6
**Research basis:** research.md @ 2026-06-03T13:44:56Z
**Generated:** 2026-06-03T14:10:00Z
**Status:** draft

## Current State

Skills in this repo live under `.claude/skills/<skill-name>/`, one directory per skill, each containing an uppercase `SKILL.md` body file (ref: Q1). There are 10 skill directories today, all named `qrspi-*`; only `qrspi-work` uses an optional subdirectory (`references/review-cascade.md`), and no skill uses `scripts/` or `assets/` (ref: Q1). The identity triple is rigid: directory name == frontmatter `name` == `command` slug, all lowercase kebab-case with no spaces (ref: Q5). Every `SKILL.md` opens with `---`-delimited YAML frontmatter carrying five keys in order — `name`, `description`, `command`, `argument-hint`, `allowed-tools` — where `description` is a purpose sentence plus a "Use when…" trigger clause, and multi-clause descriptions are double-quoted to stay valid YAML (ref: Q3).

There is NO graphite skill in-repo yet; the global `using-graphite-cli` referenced by memory lives outside REPO_ROOT and is out of scope (ref: Q6). However the repo is heavily graphite-coupled and carries a strong in-repo convention the new skill must align with: `evals/graphite-evals.json` is a 5-case suite named `"graphite"` covering commit/submit/log/move/sync that acts as a de facto behavioral spec, and `qrspi-work/SKILL.md` (lines 480-521) plus `qrspi-batch.js` encode extensive `gt` rules — always `--no-interactive`, single-commit-per-branch, `gt create`/`gt modify`, `--publish` on submit, `gt sync` only at land, and HARD STOP on infra errors (ref: Q6, Q10). Notably, `gt continue` is NOT referenced anywhere in the repo's vocabulary today (ref: Q10).

Existing skills encode hard rules with bold lead-ins, ALL-CAPS imperatives (NEVER, Do NOT, HARD STOP, forbidden), dedicated named sections, and a one-sentence rationale paired immediately after each rule (ref: Q8, Q9). Prohibitions cluster in named sections near the end of a rules block ("Anti-patterns", "HARD STOP", "Staging — NEVER use `-a`") (ref: Q9). The SKILL.md size limit (under 500 lines / 5000 tokens) is purely convention — nothing in-repo enforces it, and `qrspi-work/SKILL.md` already exceeds it at 565 lines (ref: Q7). Skill discovery is by directory convention with no manifest: dropping `<name>/SKILL.md` into `.claude/skills/` makes it discoverable; the actual loader is the external Claude Code harness, out of scope (ref: Q2, Q13). The eval harness (`run_eval.py` and friends) is a non-functional placeholder; the only working in-repo validation is the stdlib unit tests for resolver/persist logic, which do not cover skills (ref: Q11). The `skill-creator` skill the ticket mandates is external/global and undefined in-repo, referenced only as a slice-final validation step in `qrspi-structure.md` (ref: Q12).

## Desired End State

A new self-contained skill `using-graphite-cli` exists at `.claude/skills/using-graphite-cli/SKILL.md` with a `references/` subdirectory, discoverable by directory convention with no manifest edits (ref: Q5, Q13). Each acceptance criterion maps to concrete behavior:

- **Valid agentskills.io structure + frontmatter** → directory `using-graphite-cli/`, `SKILL.md` with the five-key frontmatter contract (`name: using-graphite-cli`, `description`, `command: /using-graphite-cli`, `argument-hint`, `allowed-tools`) (ref: Q3, Q5).
- **Built using skill-creator** → an Open Question (skill-creator is out of scope / undefined in-repo, see OQ1) (ref: Q12).
- **SKILL.md under 500 lines / 5000 tokens** → body self-policed to that budget; detailed material pushed to `references/` (ref: Q7).
- **Detailed reference material in `references/`** → at minimum a full command reference and an edge-cases/conflict-resolution file, pointed to lazily from the body ("see `references/<file>`") (ref: Q1, Q2).
- **Single-commit-per-branch as a hard rule** → bold + CAPS dedicated rule with rationale, mirroring `qrspi-work` phrasing (ref: Q8).
- **Complete Create → Submit → Modify → Sync loop** → a workflow section enumerating `gt create --all -m`, `gt submit`/`gt ss`, `gt modify --all`, `gt sync` (ref: Q10).
- **Conflict resolution via `gt continue` (never `git rebase --continue`)** → documented in body and `references/`, despite `gt continue` being new to the repo vocabulary (ref: Q10).
- **Stack navigation + directionality** → `gt bu`/`gt bd`, `gt stack top`, `gt log short`, downstack=toward-trunk / upstack=away-from-trunk (ref: ticket; no in-repo precedent — Q10).
- **Submit flag defaults (`--no-edit --publish`) for agents** → stated as the agent default, consistent with the orchestrator's non-interactive submits (ref: Q10).
- **Warn against mixing raw git branch/rebase with tracked branches** → a prohibition section (CAPS + bold + rationale), extending the existing indirect coverage into an explicit "NEVER run `git rebase`/`git commit --amend` on a tracked branch" line (ref: Q8, Q9).

## Delta

**New files:**
- `.claude/skills/using-graphite-cli/SKILL.md` — the skill body (target ~150-300 lines, hard cap 500).
- `.claude/skills/using-graphite-cli/references/command-reference.md` — full `gt` command catalog with flags.
- `.claude/skills/using-graphite-cli/references/conflict-resolution.md` — `gt continue` flow, edge cases, stack-repair recipes.

**Modified files:** none required for discovery (auto-discovery by directory) (ref: Q13). Optional: the README skills list and `.claude/CLAUDE.md` "Available skills" block could gain an entry, but neither is a discovery requirement and both are out of scope for acceptance — flag as a follow-up, not a delta.

**Frontmatter values to set:** `name: using-graphite-cli`; `command: /using-graphite-cli`; `argument-hint:` (likely empty/optional — this is reference guidance, not a parameterized command); `allowed-tools: Bash` at minimum since the skill drives `gt`; `description` a single quoted sentence with a "Use when…" trigger.

## Pattern Decisions

### Decision 1: Self-contained skill vs. wrapper+agent split

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Self-contained SKILL.md (logic in body + `references/`), like `qrspi-ticket`/`qrspi-work` | Matches reference-guidance skills; no agent spawn; everything discoverable in one dir | Body must stay under size budget by offloading to `references/` |
| B | Thin wrapper SKILL.md spawning a `.claude/agents/using-graphite-cli.md` agent | Mirrors the QRSPI phase pattern | Agent split exists to run multi-step phase work; this skill is static guidance, not a phase — no agent fits |

**Recommendation:** Option A.
**Rationale:** The wrapper/agent split is specifically the QRSPI *phase* pattern; self-contained skills (`qrspi-ticket`, `qrspi-work`) are the precedent for non-phase, content-heavy skills, and `qrspi-work` already proves the `references/` offload pattern (ref: Q1, Q4, Discovered Patterns).
**NEW PATTERN?** No.

### Decision 2: Where reference detail lives

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Body holds workflow + hard rules; `references/` holds full command catalog + edge cases, pointed to lazily | Keeps body under budget; matches lazy-load convention | Two-file maintenance |
| B | Everything inline in SKILL.md | Single file | Breaks the 500-line/5000-token criterion; ignores lazy-load convention |

**Recommendation:** Option A.
**Rationale:** `qrspi-work` references `references/review-cascade.md` lazily rather than inlining it; the size criterion plus the lazy-load convention make offloading mandatory (ref: Q1, Q2, Q7).
**NEW PATTERN?** No.

### Decision 3: Reconciling the ticket's flags against in-repo gt conventions

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Follow the ticket verbatim (`gt create --all`, `gt submit --no-edit --publish`, `gt continue`, `gt modify --all`) | Satisfies acceptance criteria exactly; this is a *general* graphite skill, not the QRSPI orchestrator | Diverges from qrspi-work specifics (`--no-interactive` everywhere; "NEVER `-a`"; `gt continue` absent) |
| B | Force the skill to match `qrspi-work`/`graphite-evals.json` exactly | Internal consistency with orchestrator | The orchestrator's rules are QRSPI-specific (held stacks, no mid-feature sync) and would distort a general-purpose skill; the eval file itself contradicts qrspi-work on `-a` and confirmation |

**Recommendation:** Option A, with explicit notes where the ticket and orchestrator diverge.
**Rationale:** The ticket defines a general-purpose graphite skill; the in-repo conventions are QRSPI-orchestration-specific and mutually inconsistent (the `-a`/`-u` staging contradiction, the `gt sync` flag mismatch, the submit-confirmation divergence) — see Inconsistencies (ref: Q6, Q10, Inconsistencies). The skill should encode the ticket's conventions while noting that `--no-interactive` is advisable for autonomous agents.
**NEW PATTERN?** Yes — `gt continue` and explicit stack-navigation directionality are NOT present in the repo today (ref: Q9, Q10). Justified: the ticket explicitly requires them and no existing pattern covers conflict-resolution flow or navigation.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| skill-creator mandate is unsatisfiable in-repo (external/undefined) | high | med | Treat as OQ1; build the skill to agentskills.io structure manually, invoke skill-creator at validation if available in the running environment |
| Skill flags contradict qrspi-work / graphite-evals (`-a` staging, `gt sync --delete-all`, submit confirmation) | high | med | Adopt ticket conventions for the general skill; add a short "QRSPI orchestration differs" note so readers aren't misled (ref: Inconsistencies) |
| Body exceeds 500-line / 5000-token budget while covering all criteria | med | med | Offload command catalog + edge cases to `references/`; self-check line/token count before finishing (no enforcement exists, ref: Q7) |
| `gt continue` documented but never used in-repo — may be wrong for this graphite version | low | med | Verify against Graphite docs during implementation; mark in `references/conflict-resolution.md` as the canonical conflict step per ticket |
| No automated validation for skills (harness is a placeholder) | high | low | Rely on manual review + structural check (frontmatter present, dir==name==command, files exist) per CLAUDE.md (ref: Q11) |

## Open Questions

- OQ1: The ticket mandates building via the `skill-creator` skill, but skill-creator is external/global and undefined in-repo (ref: Q12). Should the implementation invoke the global skill-creator (relying on the running environment), or is manual construction to the agentskills.io spec acceptable for satisfying that criterion?
- OQ2: Should `using-graphite-cli` encode the ticket's general-purpose flags verbatim, or be tailored to this repo's QRSPI orchestration rules where they diverge (`-a` staging, `gt sync --delete-all`, submit confirmation, `--no-interactive`)? (ref: Inconsistencies)
- OQ3: The stale co-authorship trailer ("Claude Opus 4.7" vs. running 4.8) appears in qrspi-work and qrspi-batch.js (ref: Inconsistencies) — should the new skill document the correct/current trailer, and is fixing the existing references in scope?
- OQ4: Should the README and `.claude/CLAUDE.md` skill lists be updated to mention this skill, or is auto-discovery sufficient and the docs left to a follow-up?
