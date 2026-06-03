# Design — Create a kubectl CLI agent skill

**Ticket:** RUS-15
**Research basis:** research.md @ 2026-06-03T00:00:00Z
**Generated:** 2026-06-03T00:00:00Z
**Status:** draft

## Current State

The repo's `.claude/skills/` holds only the 10 QRSPI slash-command wrapper skills; no general CLI-tool skill exists, and the external authoring skills (`skill-creator`, `using-graphite-cli`, `writing-bash-scripts`) are global, not vendored in-repo (ref: research scope note). A skill is registered purely by directory convention: placing `<name>/SKILL.md` under `.claude/skills/` — there is no manifest, no central registry, and no discovery script (ref: Q4, Q11). The `description` frontmatter field is what surfaces a skill for auto-invocation; `command` declares its slash form (ref: Q4).

Frontmatter has no validator; the schema is conventional, inferred from 10 consistent files using five fields (`name`, `description`, `command`, `argument-hint`, `allowed-tools`) in `---`-delimited YAML (ref: Q3). A triple-identity invariant holds across every skill: directory name == frontmatter `name` == `command` minus the leading `/` (ref: Q11). Only `qrspi-work` quotes its `description` because it contains commas/colons; the other nine leave it bare, a trip-hazard for hand-authored punctuated descriptions (ref: Q3, inconsistencies).

The repo splits skills two ways: thin wrappers (25–35 lines) that spawn an agent in `.claude/agents/<name>.md` via the `Agent` tool, versus `qrspi-work`, the monolith exception that carries its full 565-line prompt inline and is the only skill with a `references/` subdirectory (ref: Q4, Q6, discovered patterns). That `references/review-cascade.md` is linked from the body with a **bare relative path** (no `./`, no `.claude/...` prefix), relative to the skill directory, cited as on-demand prose ("see `references/...`") rather than an eager include (ref: Q1). No in-repo skill uses a `scripts/` or `assets/` subdir — only a `references/` precedent exists (ref: Q1, inconsistencies).

There is **no body-size budget check** anywhere; `qrspi-work` is already 565 lines (over the 500 cited) and nothing flags it (ref: Q7). Safety guardrails follow an established formatting convention: a dedicated `###`/`##` heading naming the hazard, ALL-CAPS imperative emphasis, bolded absolute language, an enumerated stop-procedure, and an "Explicitly forbidden" list — e.g. the "HARD STOP" section (ref: Q8). Scope boundaries use enumerated DO/DON'T "firewall" blocks with a pre-action validation gate and a report-and-stop fallback; there is no single named "judgment call" heading (ref: Q9).

Skill source files are **not** routed through `qrspi_persist.py` — that script's `ARTIFACTS` list is closed to the six phase artifacts and always moves into `.qrspi/<ticket>/`; a kubectl skill is ordinary source under `.claude/skills/`, created in the worktree and committed like any code file (ref: Q5). There is no automated skill test: `run_eval.py` is a stubbed placeholder, so the accepted verification path is manual end-to-end runs (plus stdlib `unittest` for any pure-logic helper) (ref: Q10). No in-repo mechanism logs skill triggering; confirmation of a `description` trigger is manual observation (ref: Q12).

## Desired End State

A new skill directory `.claude/skills/using-kubectl-cli/` exists, discoverable by convention, with `SKILL.md` plus a `references/` subdir. Mapping each acceptance criterion to concrete behavior:

- **agentskills.io structure + valid frontmatter:** `SKILL.md` carries the five-field frontmatter with `name: using-kubectl-cli`, `command: /using-kubectl-cli`, a quoted `description`, an `argument-hint`, and an `allowed-tools` allowlist — satisfying the triple-identity invariant (ref: Q3, Q11).
- **Built using the Anthropic skill-builder skill:** the implement agent invokes the global `skill-creator` skill as the authoring tool; this is a process step folded into the producing slice, not an in-repo artifact (ref: Q2). Captured as Open Question OQ1 since `skill-creator` is out of repo scope.
- **SKILL.md under 500 lines / 5000 tokens:** the body is authored terse; unenforced by tooling, so the constraint is honored by construction and checked manually (ref: Q7).
- **`references/` covers JSONPath examples, krew catalog, RBAC decision tree, common errors+resolutions:** four reference files under `references/`, linked from the body by bare relative path (ref: Q1).
- **Covers all convention subsections with copy-pasteable patterns:** the body has a section per ticket subsection (context/namespace, inspection, rollouts, debugging, apply strategies, output formatting, plugins/krew, RBAC, safety), using fenced command blocks with `<angle-bracket>` placeholders and inline `#` comments (ref: Q6).
- **Safety guardrails prominently placed:** a top-of-body guardrail block in the HARD-STOP convention covering context verification, dry-run-before-delete, and explicit namespace flags (ref: Q8).
- **Debugging escalation path events → logs → describe → exec/debug:** an ordered escalation section in the body, with the RBAC decision tree and error catalog in `references/` (ref: Q8, Q9).

## Delta

- **New directory:** `.claude/skills/using-kubectl-cli/`.
- **New file:** `.claude/skills/using-kubectl-cli/SKILL.md` — frontmatter + body (target < 200 lines, hard cap 500), guardrail block near top, one section per convention subsection, ordered debugging-escalation section, scope (in/out/judgment) firewall-style block, and bare-relative links to the four reference files.
- **New file:** `references/jsonpath.md` — JSONPath + custom-columns + jq extraction examples.
- **New file:** `references/krew-plugins.md` — krew plugin catalog (ctx, ns, neat, tree, images, whoami, access-matrix) and provenance guidance.
- **New file:** `references/rbac-debugging.md` — RBAC troubleshooting decision tree (`auth can-i` → bindings → subject form → NetworkPolicy/webhook).
- **New file:** `references/common-errors.md` — common kubectl error messages with resolutions.
- **No** agent file under `.claude/agents/` — this is a standalone authoring/guidance skill, not a wrapper that spawns a phase agent (ref: Q4 two-tier split; monolith pattern from Q6).
- **No** change to `qrspi_persist.py`, `run_eval.py`, or any orchestration script — skill files are committed as ordinary source (ref: Q5).

## Pattern Decisions

### Decision 1: Skill architecture — wrapper+agent vs. inline monolith

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Inline monolith `SKILL.md` (mirror `qrspi-work`), no `.claude/agents/` file | Matches the only in-repo command-heavy CLI skill; self-contained; references/ precedent already set | Body grows long; less terse than wrappers |
| B | Thin wrapper + `.claude/agents/using-kubectl-cli.md` | Matches the 10 phase skills' terse wrapper convention | Wrapper exists to spawn a phase *agent* via `Agent` tool; there is no agent to spawn here — misuse of the pattern |

**Recommendation:** Option A
**Rationale:** `qrspi-work` is the established in-repo template for a long, command-heavy CLI skill with a `references/` subdir (ref: Q6). The wrapper pattern's whole purpose is delegating to a phase agent (ref: Q4); a guidance skill has no such agent, so Option B would be a hollow indirection.
**NEW PATTERN?** No — directly mirrors `qrspi-work` (ref: Q6, Q8, Q9).

### Decision 2: Reference-file layout — `references/` subdir vs. inline body

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Four files in `references/`, bare-relative links from body | Keeps body under budget; matches the only subdir precedent; ticket explicitly requires `references/` | Multi-file; reader must follow links |
| B | All detail inline in `SKILL.md` | Single file | Blows the 500-line/5000-token budget; violates an explicit acceptance criterion |

**Recommendation:** Option A
**Rationale:** The ticket mandates a `references/` directory, and `qrspi-work/references/` is the established precedent; bare relative paths are the documented link convention (ref: Q1).
**NEW PATTERN?** No — `references/` precedent exists; note there is **zero** precedent for `scripts/` or `assets/` subdirs, so none are introduced (ref: Q1, inconsistencies).

### Decision 3: Description frontmatter quoting

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Quote the `description` scalar | Safe for commas/colons in trigger text; matches `qrspi-work` | Diverges from the bare-scalar majority |
| B | Leave `description` bare | Matches 9 of 10 skills | YAML-fragile if text contains `:` or `,` — a real trip-hazard |

**Recommendation:** Option A
**Rationale:** A kubectl trigger description will contain commas and colons; `qrspi-work` already quotes for exactly this reason, and the research flags bare quoting as a hazard for punctuated descriptions (ref: Q3, inconsistencies).
**NEW PATTERN?** No — `qrspi-work` precedent (ref: Q3).

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `skill-creator` is out of repo scope and cannot be invoked deterministically by the implement agent (ref: Q2) | med | med | Treat "built using skill-builder" as a process step; if unavailable, hand-author to the same structure and record the deviation. Surfaced as OQ1. |
| Body exceeds 500-line/5000-token budget with no automated check (ref: Q7) | med | low | Push all detail into the four `references/` files (Decision 2); manually count lines/tokens before commit. |
| `name`/`command`/directory triple-identity broken, making the skill undiscoverable (ref: Q11) | low | high | Set all three to `using-kubectl-cli` at authoring time; verify in review (no validator exists). |
| No automated skill test; trigger correctness only confirmable manually (ref: Q10, Q12) | high | low | Manual end-to-end run after authoring; verify the `description` fires on a kubectl-phrased prompt. |
| Reference links use wrong path form (absolute or prefixed) breaking on-demand reads (ref: Q1) | low | med | Use bare relative paths (`references/<file>.md`) exactly as the `qrspi-work` precedent. |

## Open Questions

- OQ1: Is the global `skill-creator` skill available in the implement-phase environment, and does the acceptance criterion "Built using the Anthropic skill builder skill" require its literal invocation, or is structural conformance to the agentskills.io pattern sufficient if hand-authored? (research bounded this out of repo scope — ref: Q2)
- OQ2: Should the skill directory be named `using-kubectl-cli` (mirroring the global `using-graphite-cli` naming) or `qrspi`-namespaced/other? The ticket title says "using kubectl cli" but the repo's in-repo skills are all `qrspi-*`; a human should confirm the intended `name`.
- OQ3: Are there any environment-specific cluster/namespace scope constraints (analogous to the REPO_ROOT firewall, ref: Q9) the skill should encode to prevent agents from acting against production contexts?
