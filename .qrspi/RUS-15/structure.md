# Structure Outline — Create a kubectl CLI agent skill

**Design basis:** design.md @ 2026-06-03T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft

> This feature produces Markdown skill source (no executable code). "Types" below
> are the conventional YAML frontmatter schema; "Contracts" are the cross-file
> invariants (triple-identity, link form) that every file must honor together.

## New Types

- Frontmatter schema (conventional, no validator — ref: design §Current State / Q3):
  `SkillFrontmatter { name: string, description: string (QUOTED scalar), command: string, argument-hint: string, allowed-tools: string }`
  - `name: using-kubectl-cli`
  - `command: /using-kubectl-cli`
  - `description` MUST be quoted (contains commas/colons) — Decision 3.

## Modified Types

- None. No existing type, schema, or script is modified (design §Delta: "No change
  to `qrspi_persist.py`, `run_eval.py`, or any orchestration script"; no
  `.claude/agents/` file added).

## Contracts

These are file-spanning invariants, not function signatures — verify all in review.

- `TripleIdentity` — directory name == frontmatter `name` == `command` minus leading
  `/`, all equal to `using-kubectl-cli`. Breaking this makes the skill undiscoverable
  (ref: Q11, Risk Register).
- `ReferenceLink(file)` — body links each reference as a **bare relative path**
  `references/<file>.md` (no `./`, no `.claude/...` prefix), relative to the skill
  directory; cited as on-demand prose ("see `references/...`") not eager include
  (ref: Q1, Decision 2).
- `BodyBudget` — `SKILL.md` body target < 200 lines, hard cap 500 lines / 5000
  tokens; honored by construction, counted manually (no tooling — ref: Q7).
- `GuardrailBlock` — top-of-body HARD-STOP block: `###`/`##` hazard heading, ALL-CAPS
  imperative, bolded absolutes, enumerated stop-procedure, "Explicitly forbidden"
  list; covers context verification, dry-run-before-delete, explicit namespace flags
  (ref: Q8).
- `ScopeFirewall` — enumerated DO/DON'T block with a pre-action validation gate and a
  report-and-stop fallback (ref: Q9).
- `DebugEscalation` — ordered section: events → logs → describe → exec/debug (ref: Q8).

## Slice 1: Author the using-kubectl-cli skill (SKILL.md + references)

**Goal:** A discoverable, convention-conformant skill at
`.claude/skills/using-kubectl-cli/` whose `description` fires on a kubectl-phrased
prompt and whose body links resolve to the four reference files — the complete,
end-to-end deliverable.

> Single slice by design: per structure rule 8, the body file and the
> reference/support files it directly depends on belong together. The references are
> on-demand support for `SKILL.md` (linked by bare relative path); neither the body
> nor a reference file yields meaningful verification signal in isolation — the skill
> is only testable as a whole (does it trigger, do its links resolve, is the budget
> met). This is one unit a developer authors in one sitting. 5 files < 10-file cap.

**Files touched:**

- ✨ `.claude/skills/using-kubectl-cli/SKILL.md` — quoted-`description` frontmatter
  satisfying `TripleIdentity`; guardrail block near top (`GuardrailBlock`); one
  section per convention subsection (context/namespace, inspection, rollouts,
  debugging, apply strategies, output formatting, plugins/krew, RBAC, safety) with
  fenced `<angle-bracket>`-placeholder command blocks; `DebugEscalation` section;
  `ScopeFirewall` block; bare-relative links to all four references. Mirrors the
  `qrspi-work` inline-monolith pattern (Decision 1); no `.claude/agents/` file.
- ✨ `.claude/skills/using-kubectl-cli/references/jsonpath.md` — JSONPath +
  custom-columns + jq extraction examples.
- ✨ `.claude/skills/using-kubectl-cli/references/krew-plugins.md` — krew catalog
  (ctx, ns, neat, tree, images, whoami, access-matrix) + provenance guidance.
- ✨ `.claude/skills/using-kubectl-cli/references/rbac-debugging.md` — RBAC decision
  tree (`auth can-i` → bindings → subject form → NetworkPolicy/webhook).
- ✨ `.claude/skills/using-kubectl-cli/references/common-errors.md` — common kubectl
  errors with resolutions.

**Verification:**

- [ ] Authoring done via the global `skill-creator` skill (and its eval loop) per
  memory directive + acceptance criterion; if `skill-creator` is unavailable
  (OQ1/Risk), hand-author to the same agentskills.io structure and record the
  deviation. (Rule 9: this validation is the final step of this slice.)
- [ ] `TripleIdentity` holds: `ls .claude/skills/using-kubectl-cli/` dir name,
  frontmatter `name`, and `command` all equal `using-kubectl-cli`.
- [ ] `description` is a quoted YAML scalar and parses (no YAML break on `:`/`,`).
- [ ] All four `references/<file>.md` exist and every body link is bare-relative and
  resolves from the skill directory.
- [ ] `BodyBudget`: `wc -l SKILL.md` body < 500 lines (target < 200); manual token spot-check.
- [ ] `GuardrailBlock`, `ScopeFirewall`, and ordered `DebugEscalation` sections present.
- [ ] Manual end-to-end: a kubectl-phrased prompt auto-invokes the skill (observed,
  since no trigger-logging mechanism exists — ref: Q12).

**Context cost:** M
**Depends on:** none

---

## Unverified Assumptions

- **OQ1 — `skill-creator` availability/requirement:** Design cannot confirm the global
  `skill-creator` skill is invocable in the implement-phase environment, nor whether
  the "Built using the Anthropic skill builder skill" criterion demands literal
  invocation vs. structural conformance. Bounded out of repo scope (Q2). Maps to a
  process step in the slice's verification, not a concrete file. Needs human ruling
  before planning.
- **OQ2 — skill directory name:** Design assumes `using-kubectl-cli` (mirroring global
  `using-graphite-cli`), but every *in-repo* skill is `qrspi-*`-namespaced. The
  `TripleIdentity` contract and all file paths above hinge on this name; a human must
  confirm before the name is committed.
- **OQ3 — cluster/namespace scope constraints:** Design has no concrete value for any
  environment-specific production-context guardrail (analogous to the REPO_ROOT
  firewall, Q9). The `GuardrailBlock`/`ScopeFirewall` contracts are structurally
  defined, but whether they must encode specific forbidden contexts/namespaces is
  unverified and needs human input.
- **No automated test exists** (`run_eval.py` is a stub — Q10): every verification
  checkbox above is manual. Trigger correctness in particular is unautomatable in-repo
  (Q12); the "skill fires" claim cannot be mapped to an automated check.
