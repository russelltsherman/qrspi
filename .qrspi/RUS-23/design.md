# Design — Create a new agent skill using the Crossplane CLI

**Ticket:** RUS-23
**Research basis:** research.md @ 2026-06-04T00:00:00Z
**Generated:** 2026-06-04T00:00:00Z
**Status:** draft

## Current State

Skill source lives under `.claude/skills/<skill-name>/`, one directory per skill, each with a `SKILL.md` entry point; 9 of 10 existing skills contain only a `SKILL.md` and the single multi-file example (`qrspi-work/`) adds one `references/` file, while no skill ships a `scripts/` or `assets/` directory (ref: Q1). This repo has a wrapper-vs-agent split unique to it: phase skills are thin slash-command wrappers and the substantive prompt logic lives in sibling `.claude/agents/<name>.md` files, but only `qrspi-ticket` and `qrspi-work` carry full inline logic in their SKILL.md (ref: Q1, Discovered Patterns).

The `skill-creator` skill that the ticket names as the build tool is NOT defined anywhere under the repo; it is a global harness skill whose contract (inputs, output paths, collision behavior, eval sub-capability, progress/validation output) cannot be observed from this repo and is answered "outside project scope" (ref: Q2, Q5, Q9, Q12). The repo references it only as a process step in `qrspi-structure.md` without specifying its interface (ref: Q2).

Frontmatter has no schema or validator in-repo; "required" is observed empirically. All 10 skills carry `name`, `description`, `command`, `allowed-tools`; 9 also carry `argument-hint`, and frontmatter is YAML delimited by `---` as the first content in the file (ref: Q3). Descriptions are single-line strings ranging 74–489 chars following a "<what it does>. Use when/after <condition>." pattern, with `qrspi-work` the richest, embedding explicit "Trigger on any variant of:" phrasing and quoting because it contains a colon (ref: Q4). Naming is lowercase kebab-case where dirname == frontmatter `name` == `command` minus the leading slash, uniqueness enforced only by the one-dir-per-skill filesystem layout (ref: Q9).

Reference documents are linked by a relative-path prose pointer in backticks (e.g., "see `references/review-cascade.md`"), loaded on demand — there is no include directive (ref: Q6). No automated mechanism enforces the 500-line / 5000-token SKILL.md limit; sizes are managed by convention, and the repo's own `qrspi-work/SKILL.md` is 565 lines, exceeding the guideline (ref: Q7, Inconsistencies). No skill currently encodes software version (v1/v2) branching; the established conditional-guidance idiom is "resolve from config; if unset, fall back to a default; else discover/ask," written as numbered imperative prose with explicit `if … otherwise …` clauses (ref: Q8). The in-repo eval harness (`scripts/run_eval.py` + `evals/suite.json`) is a non-functional placeholder targeting QRSPI phase prompts, not skill triggering, and has no skill-creator or trigger-accuracy cases (ref: Q5, Q10, Q11).

## Desired End State

A new skill directory `.claude/skills/<name>/` ships a valid `SKILL.md` plus a `references/` directory, matching the established repo location and the agentskills.io structure.

| Acceptance criterion | System behavior after ship |
|---|---|
| agentskills.io directory structure with valid SKILL.md frontmatter | `.claude/skills/<name>/SKILL.md` exists with first-line `---` YAML carrying `name`, `description`, `command`, `argument-hint`, `allowed-tools`, matching the empirical field set (ref: Q3) |
| Built using the Anthropic skill-builder skill | The `skill-creator` global skill is invoked to generate the skill; because its contract is out-of-repo (ref: Q2), this is recorded as an Open Question for exact invocation |
| SKILL.md body under 500 lines / 5000 tokens | Body kept lean via references/ offload; no tooling enforces this (ref: Q7), so size is a manual reviewer gate |
| references/ covering full CLI reference, composition patterns, XRD templates, troubleshooting decision tree | Four reference files under `references/`, each linked from SKILL.md by backticked relative path (ref: Q6) |
| Covers v1 (Claims) and v2 (namespaced XRs) with version guidance | Version branching written as explicit `if v1 … otherwise v2 …` prose following the "default to X unless environment indicates Y" idiom (ref: Q8) |
| Troubleshooting escalation path trace → describe → events → logs | Encoded as an ordered sequence in SKILL.md, detailed in the troubleshooting reference file |
| References official Crossplane docs as canonical source | SKILL.md and references point to official docs for CLI flags / API specs rather than inlining volatile detail |

## Delta

New files (single skill directory):
- `.claude/skills/<name>/SKILL.md` — entry point with frontmatter and lean body (provider lifecycle, composition, XRD/claims, managed resources, packaging, troubleshooting escalation, kubectl/GitOps, env config), each section pointing to a reference file.
- `.claude/skills/<name>/references/cli-reference.md` — full `crossplane xpkg build/push/login/validate`, `render`, `trace` command/flag reference, deferring to official docs as canonical.
- `.claude/skills/<name>/references/composition-patterns.md` — Pipeline-mode compositions, `function-patch-and-transform`, EnvironmentConfig usage, `crossplane render` validation.
- `.claude/skills/<name>/references/xrd-schemas.md` — XRD schema templates, v1 cluster-scoped + Claims vs v2 `scope: Namespaced` XRs, connectionSecretKeys, versioning/conversion.
- `.claude/skills/<name>/references/troubleshooting.md` — trace → describe → events → logs decision tree, condition checks (ReconcileError, Ready, Synced, Responsive), `xpkg validate`.

No modifications to existing skills, agents, scripts, templates, or config are required. No new queries, middleware, or DB changes. The skill name must be decided (Open Question) and applied consistently as dirname == `name` == `command` slug (ref: Q9).

## Pattern Decisions

### Decision 1: Single-file vs wrapper-vs-agent layout

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Self-contained skill: all logic in SKILL.md + references/ (the agentskills.io standard) | Matches the ticket's stated standard; portable; references/ offload keeps body small | Diverges from this repo's dominant phase-skill wrapper convention (ref: Q1) |
| B | Wrapper SKILL.md + `.claude/agents/<name>.md` logic file | Mirrors the repo's QRSPI phase split | That split exists to serve the spawned-agent phase lifecycle; this is a standalone reference skill, not a phase agent — the split adds an empty indirection |

**Recommendation:** Option A
**Rationale:** The wrapper-vs-agent split is specific to QRSPI phase orchestration; `qrspi-ticket` and `qrspi-work` already carry full inline logic in SKILL.md, so a self-contained skill is an existing, sanctioned shape (ref: Q1, Discovered Patterns). The ticket explicitly targets the agentskills.io standard.
**NEW PATTERN?** No — self-contained SKILL.md is precedented by `qrspi-ticket`/`qrspi-work`; the only genuinely new element is a non-QRSPI-prefixed skill name.

### Decision 2: Reference loading mechanism

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Backticked relative-path prose pointers (e.g., "see `references/cli-reference.md`") | Exactly the one in-repo precedent (ref: Q6); on-demand load keeps body lean | No tooling verifies the link resolves |
| B | Inline all reference content in SKILL.md | One file | Blows past the 500-line guideline (ref: Q7); defeats the references/ acceptance criterion |

**Recommendation:** Option A
**Rationale:** Q6 documents the only existing references/ link style; it satisfies both the body-size and references/ criteria simultaneously.
**NEW PATTERN?** No.

### Decision 3: v1/v2 version-branching expression

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Imperative prose with explicit `if v1 … otherwise v2 …`, defaulting to v2 unless installed version indicates v1 | Matches the repo's documented conditional idiom (ref: Q8); honors the ticket's "default to v2" judgment call | Prose can grow if branches are deep — mitigated by pushing detail to references/ |
| B | Side-by-side comparison table of v1 vs v2 in the body | Scannable | No repo precedent for data-table branching; risks duplicating reference content in the body |

**Recommendation:** Option A
**Rationale:** Q8 shows the established "resolve/default/branch" pattern is imperative prose with `if … otherwise …`, not tables; the ticket already prescribes "default to v2 unless the installed version indicates v1."
**NEW PATTERN?** No for the branching idiom; the v1/v2 software-version axis itself is new content (no existing skill branches on software version, ref: Q8), but it reuses the existing expression pattern.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `skill-creator` contract (inputs, output paths, invocation, collision behavior) is unknown — out of repo scope (ref: Q2, Q9, Q12) | high | med | Treat skill-creator as a black box; verify only its output (directory + frontmatter) against the empirical conventions in Q1/Q3; raise as Open Question |
| Body exceeds 500 lines / 5000 tokens with no tooling to catch it (ref: Q7) | med | med | Aggressively offload to the four references/ files; make body-size a manual reviewer checklist item; the repo's own `qrspi-work` already violates this, so reviewer vigilance is the only gate |
| No frontmatter validator exists; an invalid field set ships silently (ref: Q3, Q12) | med | med | Copy the exact field set from an existing SKILL.md (`name`, `description`, `command`, `argument-hint`, `allowed-tools`); reviewer diff against a known-good skill |
| Crossplane CLI flags / API specs drift from whatever is inlined, going stale | med | med | Per acceptance criterion, point to official Crossplane docs as canonical; keep inlined flags minimal in references/ |
| No eval harness can measure trigger accuracy of the new description (ref: Q10, Q11) | med | low | Hand-craft the description on the Q4 "<what it does>. Use when…" pattern; rely on human review since the placeholder harness cannot score it |

## Open Questions

- OQ1: What is the skill's `name` / directory slug? It must be lowercase kebab-case and is not `qrspi-`-prefixed (the first non-QRSPI skill here); pick before authoring since dirname == `name` == `command` (ref: Q9). Suggested: `using-crossplane-cli`.
- OQ2: How exactly is the `skill-creator` global skill invoked, and what inputs/output paths does it expect? Its definition is outside the repo (ref: Q2) — does the author drive it interactively, or is there a non-interactive entry point?
- OQ3: Should this skill define `argument-hint` at all? It is a reference/guidance skill, not an argument-taking phase command; 9/10 skills carry it but `qrspi-ticket` omits it (ref: Q3) — decide whether to include or follow the `qrspi-ticket` exception.
- OQ4: Acceptance asks the skill be "built using the Anthropic skill builder skill," but no such artifact or its eval loop exists in-repo to validate against (ref: Q5, Q10). Is invoking the global skill-creator sufficient, or is a recorded eval result expected?
