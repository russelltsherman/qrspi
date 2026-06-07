# Design — Create a new agent skill: using helm cli

**Ticket:** RUS-14
**Research basis:** research.md @ 2026-06-03T12:52:33Z
**Generated:** 2026-06-03T13:10:00Z
**Status:** draft

## Current State

Skills live as directories at `.claude/skills/<skill-name>/SKILL.md`, with the directory name equal to the frontmatter `name` (ref: Q2). The repo holds ten production skills, all using a stable five-field YAML frontmatter set — `name`, `description`, `command`, `argument-hint`, `allowed-tools` — delimited by `---`; there is no separate `triggers` field (ref: Q3). There are two skill archetypes: thin wrappers (~25–35 lines) that delegate all real content to a sibling `.claude/agents/<name>.md`, and self-contained skills whose full prompt lives in SKILL.md, such as qrspi-ticket (119 lines) and qrspi-work (565 lines) (ref: Q7, Discovered Patterns). A skill's `description` encodes triggering directly, structured as an action statement plus an explicit "Use when/after" clause, with literal trigger phrases enumerated for high-ambiguity skills (ref: Q4). Supporting material is loaded on demand by naming a backtick-quoted relative path in prose rather than inlining content; the only live precedent is `references/` (one occurrence, `qrspi-work/references/review-cascade.md`, 77 lines) — no `scripts/` or `assets/` subdirectory exists in any skill today (ref: Q5, Q2, Inconsistencies). Scope boundaries are expressed two ways: a dedicated negative-scope/anti-pattern section, and inline "do NOT" directives that name the excluded topic and say which other skill/phase owns it (ref: Q8). There is no in-repo precedent for version-specific or compatibility-caveat guidance inside a SKILL.md (ref: Q9). No automated validation exists for skills — no frontmatter linter, no 500-line/5000-token size checker, no structure validator anywhere in the repo (ref: Q7, Q10, Discovered Patterns). The `skill-creator` skill is globally installed; its definition lives outside REPO_ROOT and was not readable, so its inputs, eval loop, validation behavior, and trigger logging are unknown from the repo (ref: Q1, Q4, Q6, Q10, Q12). Verification is by stdlib-only unit tests for deterministic logic plus manual end-to-end runs; SKILL.md prose has no unit test and the `evals/` harness is an explicit non-functional placeholder (ref: Q11). The fail-loud convention — hard stop, print exact error, no silent fallback — is established across QRSPI skills (ref: Q10, Discovered Patterns).

## Desired End State

A new self-contained skill directory `using-helm-cli` exists under `.claude/skills/`, authored via the skill-builder workflow, mapping each acceptance criterion to concrete behavior:

- **agentskills.io structure with valid SKILL.md frontmatter** → `.claude/skills/using-helm-cli/SKILL.md` carries the five-field frontmatter set proven across the repo (ref: Q3).
- **Built using the Anthropic skill builder skill** → authoring goes through the globally-installed skill-creator as the generation/validation pass (ref: Q1, Q11), even though its internals are not repo-visible.
- **SKILL.md body under 500 lines / 5000 tokens** → the body stays well under budget by offloading detail into `references/`, mirroring qrspi-work's mitigation; size is confirmed by `wc -l` and manual review since no automated checker exists (ref: Q7).
- **`references/` covering values patterns, hook lifecycle, OCI workflow, testing strategies, Helm 4 migration** → five reference files under `using-helm-cli/references/`, each named by backtick path in SKILL.md and read on demand (ref: Q5).
- **Full release lifecycle (install, upgrade, rollback, uninstall, status)** → SKILL.md body sections cover each operation with the ticket's release-management defaults.
- **Security-first defaults (`--atomic`, `--wait`, `--verify`, explicit namespaces)** → encoded as mandatory directives in the release-management section.
- **Chart authoring conventions (naming, versioning, schema validation, library charts)** → a chart-authoring section plus deeper coverage in references.
- **Both OCI and classic repository workflows** → covered in the OCI workflow reference, opinionated toward OCI with classic-repo notes.
- **Troubleshooting decision tree for common failure modes** → a decision-tree section in SKILL.md following the ticket's diagnostic sequence.
- **Scope boundaries** → an explicit out-of-scope section deferring kubectl/kustomize, Helmfile, and GitOps reconcilers to other skills, using the repo's name-and-defer convention (ref: Q8).
- **Helm 3 vs Helm 4 version guidance** → a compatibility convention introduced here, since no precedent exists (ref: Q9).

## Delta

New files (all under `.claude/skills/using-helm-cli/`):

- `SKILL.md` — self-contained body: frontmatter (five fields), release lifecycle, security defaults, values/overrides, chart authoring, repo/registry, hooks, testing, troubleshooting decision tree, Helm 4 awareness, and an explicit out-of-scope section. Body kept under 500 lines / 5000 tokens by pushing depth into references.
- `references/values-patterns.md` — layered values hierarchy, `-f` ordering, deep-merge vs array-replace, `values.schema.json`, secrets deferral.
- `references/hook-lifecycle.md` — hook weights, delete policies, pre/post lifecycle phases, hook Job resource limits.
- `references/oci-workflow.md` — OCI push/pull, classic-repo workflow, signing/verification (cosign + provenance).
- `references/testing-strategies.md` — `helm test`, helm-unittest, lint, template-against-policy, schema validation.
- `references/helm4-migration.md` — Server-Side Apply default, readiness annotations, post-renderer plugins, Helm 3 compatibility notes.

No modified files are required: skills are additive and no central registry references them (ref: Q2). No new scripts or `assets/` directory unless a future need arises (none in repo today — ref: Q2, Inconsistencies). The skill directory name `using-helm-cli` must equal the frontmatter `name` (ref: Q2, Q3); there is no matching `.claude/agents/` file because this is a self-contained (archetype b) skill (ref: Discovered Patterns).

## Pattern Decisions

### Decision 1: Skill archetype (self-contained vs wrapper)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Self-contained — full prompt in SKILL.md + references/ | Matches qrspi-ticket/qrspi-work precedent for content-heavy skills; no agent indirection; content is domain knowledge, not orchestration | SKILL.md grows; must actively manage the size budget |
| B | Thin wrapper delegating to `.claude/agents/using-helm-cli.md` | Keeps SKILL.md ~25–35 lines | Wrappers exist to spawn phase subagents; a helm knowledge skill has no subagent to dispatch, so the indirection is pointless and breaks the wrapper convention's intent (ref: Discovered Patterns) |

**Recommendation:** Option A
**Rationale:** Wrappers are specifically the QRSPI phase dispatchers; their SKILL.md only parses arguments and spawns an agent (ref: Discovered Patterns). A helm skill carries reference knowledge, not an orchestration step, so it matches the self-contained archetype (qrspi-ticket, qrspi-work) the research identifies as the correct fit (ref: Q7, Discovered Patterns).
**NEW PATTERN?** No.

### Decision 2: How to stay under the 500-line / 5000-token budget

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Lean SKILL.md body, depth pushed into five `references/` files | Directly mirrors qrspi-work's mitigation; satisfies the references/ acceptance criterion in one move (ref: Q5, Q7) | Authoring split across six files |
| B | One large SKILL.md holding everything | Single file | Would overshoot the budget exactly as qrspi-work's 565-line body does (ref: Q7, Inconsistencies); fails the references/ acceptance criterion |

**Recommendation:** Option A
**Rationale:** The in-repo precedent for staying under budget is "move detail into references/," not an automated check (ref: Q7). This also satisfies the explicit references/ acceptance criterion. Size is confirmed by `wc -l` and manual review since no checker exists (ref: Q7).
**NEW PATTERN?** No.

### Decision 3: Expressing scope boundaries

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Dedicated out-of-scope section naming each excluded topic and its owning skill | Matches qrspi-ticket's anti-pattern section + qrspi-work's name-and-defer style (ref: Q8) | Slightly more body lines |
| B | Inline "do NOT" notes scattered through sections | Lower ceremony | Harder to audit against the scope-boundary acceptance criterion; less consistent than a single block |

**Recommendation:** Option A
**Rationale:** The repo's consistent convention is "name the excluded topic explicitly and say which other skill/phase owns it" — directly applicable to deferring kubectl/kustomize, Helmfile, and GitOps reconcilers (ref: Q8).
**NEW PATTERN?** No.

### Decision 4: Helm 3 vs Helm 4 version-specific guidance

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Opinionated toward Helm 4 defaults with inline "Helm 3:" compatibility caveats, plus a dedicated `references/helm4-migration.md` | Satisfies the migration-notes criterion; keeps the body lean | Introduces a convention with no in-repo precedent (ref: Q9) |
| B | Document both versions equally throughout the body | No primary bias | Doubles body length, conflicts with the ticket's "opinionated toward Helm 4" guidance, risks budget overrun |

**Recommendation:** Option A
**Rationale:** No skill encodes version-conditional defaults today, so any approach here is net-new (ref: Q9). Option A aligns with the ticket's directive to be opinionated toward Helm 4 while noting Helm 3 compatibility, and isolates the heaviest version content in a reference file to protect the budget (ref: Q7, Q9).
**NEW PATTERN?** Yes — version-specific compatibility guidance inside a SKILL.md has no existing precedent in this repo (ref: Q9). Justified because the feature inherently requires it; the convention established is "opinionated toward the current default version, inline caveats prefixed with the older version, deep migration notes in references/."

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| skill-creator internals (inputs, validation, eval loop) are unknown from the repo, so the build step may behave differently than assumed | med | med | Treat skill-creator as the authoring pass but validate output against the ten in-repo SKILL.md examples and `wc -l`; do not depend on unobserved skill-creator behavior (ref: Q1, Q11) |
| No automated frontmatter/structure/size validator exists; a malformed SKILL.md ships undetected | med | med | Manual review against the proven five-field frontmatter and directory convention; confirm body size with `wc -l`; fail-loud if structure is wrong (ref: Q3, Q7, Q10) |
| Body exceeds the 500-line/5000-token budget as it absorbs the ticket's large convention list | med | med | Decision 2: push depth into five references/ files; verify with `wc -l` before finalizing (ref: Q5, Q7) |
| Description trigger phrasing under- or over-matches, so the helm skill mis-fires | med | low | Follow the action + explicit "Use when" pattern with literal helm trigger phrases, mirroring qrspi-work's enumerated triggers (ref: Q4); trigger confirmation otherwise relies on the external harness UI (ref: Q12) |
| Establishing the net-new version-caveat convention (Decision 4) sets an inconsistent precedent for future skills | low | low | Document the convention explicitly in this design so future skills can mirror it (ref: Q9) |

## Open Questions

- OQ1: skill-creator is globally installed and outside repo scope — should this skill's definition be vendored into the repo for review and reproducibility, or remain dependent on the global skill (ref: Q1, Inconsistencies)?
- OQ2: The ticket calls for optional `scripts/` and `assets/`, but no skill uses them today (ref: Q2, Inconsistencies). Is establishing these subdirectory conventions desired now, or should the skill ship with `references/` only until a concrete script/asset need arises?
- OQ3: Should the `description` enumerate literal trigger phrases (e.g., "deploy with helm", "helm upgrade", "rollback a release") as qrspi-work does, and if so, which phrasings best match the team's real requests (ref: Q4)?
