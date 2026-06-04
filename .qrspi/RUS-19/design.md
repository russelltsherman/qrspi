# Design — Create a new agent skill for the atmos CLI

**Ticket:** RUS-19
**Research basis:** research.md @ 2026-06-04T00:00:00Z
**Generated:** 2026-06-04T00:00:00Z
**Status:** draft

## Current State

The repo holds 10 skills, each a single `SKILL.md` at `.claude/skills/<name>/SKILL.md` with `---`-delimited YAML frontmatter in a consistent field order: `name, description, command, argument-hint, allowed-tools` (ref: Q1). The `name` is a triple-identity key — directory name == frontmatter `name` == agent `subagent_type` (ref: Q1, Q3). Skill discovery is by scanning `.claude/skills/*/SKILL.md`; the entrypoint filename is always exactly `SKILL.md` (ref: Q3).

Two archetypes coexist: 8 thin-wrapper skills that only spawn a matching `.claude/agents/<name>.md` agent via `allowed-tools: Agent` + `subagent_type`, and 2 self-contained skills (`qrspi-ticket`, `qrspi-work`) that carry all logic in the body and have **no** agent file (ref: Q9). There is no hard rule that a new skill must spawn an agent or have a separate wrapper (ref: Q9).

Only `qrspi-work` ships a `references/` subdirectory; no in-repo skill ships `scripts/` or `assets/` (ref: Q2, Q8). Progressive disclosure is done by prose pointer: the body cites a backticked relative path (`references/<file>.md`) inside an instruction sentence — not a markdown link, no manifest field, no marker syntax — and the agent loads it on demand (ref: Q6). The five named reference docs do not exist in-repo; they are to be authored (ref: Q6).

There is **no** in-repo frontmatter validator, line/token-budget checker, or reference-doc-presence checker; the schema is conventional only, observed not enforced (ref: Q1, Q5, Q11). The "agentskills.io" standard the ticket references is not mentioned anywhere in-repo, so conformance cannot be verified from the project (ref: Q1, Q5). The `skill-creator` and `writing-bash-scripts` skills and their eval loops are global/plugin skills outside `REPO_ROOT` and were unreadable in research (ref: Q2, Q5, Q7, Q8, Q12). Real in-repo validation is limited to stdlib-only `*_test.py` unit tests plus manual end-to-end runs; the `evals/` + `run_eval.py` harness is a labeled non-functional placeholder returning empty outputs (ref: Q10, Q12). Repo-level scripts are Python in `scripts/` with `#!/usr/bin/env python3`, exec bit on entrypoints, and a stdlib-only `*_test.py` sibling each; there is no in-repo bash/ShellCheck convention (ref: Q8). Descriptions follow two styles: terse-imperative for phase wrappers, and a long quoted description with explicit trigger phrases for `qrspi-work` (ref: Q4).

## Desired End State

A new self-contained skill exists at `.claude/skills/atmos/SKILL.md` (proposed name `atmos`) with a `references/` subdirectory, satisfying every acceptance criterion:

- **agentskills.io structure + valid frontmatter** — `SKILL.md` carries valid frontmatter in the in-repo observed schema (`name, description, command, argument-hint, allowed-tools`), with `name` == dir name; the agentskills.io minimal pair `name`/`description` is present (ref: Q1). Open question OQ1 covers reconciling the two schemas.
- **Built with the skill-creator skill** — the skill is authored via the out-of-scope `skill-creator` skill per global memory directive (ref: Q7); this is a process criterion, verified by the implementer invoking it, not a repo artifact.
- **Body under 500 lines / 5000 tokens** — the body holds primary guidance only; depth is offloaded to `references/`. No in-repo checker exists, so the budget is enforced manually or by skill-creator tooling (ref: Q5, Q11).
- **`references/` covering the five named docs** — `references/stack-yaml-schema.md`, `references/vendoring.md`, `references/workflows.md`, `references/cli-reference.md`, `references/troubleshooting.md`, each cited by prose pointer from the body (ref: Q6).
- **Full component lifecycle** — body sections walk vendor/create → configure in stack → plan → apply → share state, pointing into references for detail.
- **Multi-environment hierarchy** — body encodes namespace/tenant/environment/stage and the `stacks.name_pattern`; detail lives in the stack-YAML-schema reference.
- **Catalog-driven inheritance + abstract components** — body shows the catalog pattern and `metadata.type: abstract` / `metadata.inherits`; detail in the stack-YAML-schema reference.
- **Two-stage plan/apply + safety** — body documents `plan --out` then `apply --from-plan`, and cautions on `deploy` auto-approval; detail in the CLI reference.
- **Cross-component data sharing** — body covers `!terraform.state` vs `!terraform.output` and the `remote-state` module; detail in the stack-YAML-schema and CLI references.
- **Debugging + troubleshooting** — body names `atmos describe component`, `validate stacks`, `ATMOS_LOGS_LEVEL`; detail in the troubleshooting reference.

## Delta

**New files (all under `.claude/skills/atmos/`):**

- `SKILL.md` — frontmatter + body. Body is organized by the lifecycle: stack-targeting model, vendor/create, configure-in-stack (catalog + inheritance), plan/apply, remote state, debugging. Each section ends with a prose pointer into the matching reference.
- `references/stack-yaml-schema.md` — `import`/`vars`/`components`/`settings`/`env`/`metadata`/`backend` sections; deep-merge/import-ordering; catalog pattern; abstract/concrete inheritance; namespace/tenant/environment/stage; `name_pattern`; region mixins; remote-state YAML functions and module.
- `references/vendoring.md` — `atmos vendor pull`; `vendor.yaml` and per-component `component.yaml`; mixins; commit-vs-JIT vendoring; Terraform Overrides (`.override.tf`) vs forking; version pinning with `{{.Version}}`.
- `references/workflows.md` — `workflows/` YAML; step types (`atmos`/`shell`); workflow-level default stack; `atmos workflow <name> -f <file>`; `--dry-run`, `--from-step`.
- `references/cli-reference.md` — terraform plan/apply/deploy; `--from-plan`; generate varfile/backend; auto-generated backend; `describe component`/`describe stacks`; validate; providers; helmfile (secondary).
- `references/troubleshooting.md` — `describe component` as primary debug command; `ATMOS_LOGS_LEVEL`; common errors (missing `name_pattern`, tenant omitted, version mismatch); `validate stacks`, `terraform validate`.

**Modified files:** none required for the skill to function. The skill is self-contained and needs no `.claude/agents/` file (ref: Q9). Optional: a note in `README.md`/CLAUDE.md skill list if the human wants the atmos skill discoverable in docs (deferred to OQ).

**Tests/queries:** no new DB queries. Any mechanical acceptance check (frontmatter validity, line count, five-doc presence) has no in-repo tool today (ref: Q11); see Decision 3.

## Pattern Decisions

### Decision 1: Skill archetype — self-contained vs agent-wrapper

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Self-contained `SKILL.md` (like `qrspi-ticket`/`qrspi-work`), no `.claude/agents/` file | Matches in-repo precedent for non-spawning skills; one file to maintain; this skill advises an agent, it does not orchestrate subagents | Body must stay within budget without an agent file to absorb logic (handled by `references/`) |
| B | Thin wrapper + `.claude/agents/atmos.md` agent | Mirrors the 8 QRSPI phase skills | The agent/wrapper split exists only for subagent-spawning phases; an atmos guidance skill spawns nothing, so this adds an empty layer (ref: Q9) |

**Recommendation:** Option A
**Rationale:** The atmos skill encodes guidance an agent applies inline; it does not spawn a subagent. The repo explicitly supports self-contained skills with no agent file, and the agent/wrapper split is documented as phase-specific only (ref: Q9).
**NEW PATTERN?** No — follows the `qrspi-ticket`/`qrspi-work` self-contained precedent.

### Decision 2: Reference layout and disclosure mechanism

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Five `references/*.md` files cited by backticked relative-path prose pointers, on-demand load | Exact in-repo precedent (`qrspi-work`); keeps body under budget; matches acceptance criterion naming five docs (ref: Q2, Q6) | Five files to keep in sync with the body |
| B | Single large `SKILL.md` with all detail inline | One file | Blows the 500-line/5000-token budget; violates the five-reference-doc criterion (ref: Q5, Q6) |

**Recommendation:** Option A
**Rationale:** The only in-repo progressive-disclosure precedent is `qrspi-work`'s prose-pointer to `references/review-cascade.md`; replicating it satisfies both the body-budget and the five-doc criteria (ref: Q2, Q6).
**NEW PATTERN?** Partly — a skill with **five** reference files and a `references/` directory beyond `qrspi-work` is a first; the mechanism is precedented but the scale is new. Flagged: this is the repo's first multi-reference skill.

### Decision 3: Mechanical acceptance verification

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Add a stdlib-only Python checker (`scripts/atmos_skill_check.py` + `_test.py`) that validates frontmatter shape, body line count, and presence of the five reference files | Satisfies TDD directive; turns three acceptance criteria into a repeatable check; matches repo script conventions (ref: Q8, Q11) | New tooling the ticket did not request; scope expansion |
| B | Manual verification + out-of-scope skill-creator eval | No new code; matches "real validation = manual e2e" reality (ref: Q10) | Criteria stay non-mechanical; no regression guard; relies on tooling outside the repo (ref: Q11, Q12) |

**Recommendation:** Option A
**Rationale:** Three acceptance criteria (frontmatter validity, line/token budget, five-doc presence) are mechanically checkable but have no in-repo tool today (ref: Q11). The global TDD directive and the repo's "every script has a stdlib-only `_test.py` sibling" convention favor a small checker over relying solely on the unreadable, out-of-scope skill-creator (ref: Q8, Q10). The human may downgrade to Option B if scope must stay minimal — see OQ3.
**NEW PATTERN?** No — follows `scripts/check_scope.py` precedent (a Python structural checker with shebang, exec bit, and `_test.py` sibling) (ref: Q8, Q11).

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| agentskills.io frontmatter schema differs from the in-repo schema; satisfying one violates the other | med | med | In-repo loader requires the observed five-field schema (ref: Q1); keep `name`/`description` (the agentskills.io core) and add the Claude Code fields. Resolve via OQ1 before authoring. |
| Body exceeds 500-line/5000-token budget with no in-repo enforcement | med | med | Offload all depth to `references/` (Decision 2); add the line/token check in Decision 3 (Option A); manual count if Option B chosen (ref: Q5, Q11). |
| Skill auto-triggers too aggressively or not at all (no in-repo triggering metric) | med | med | Use the `qrspi-work` quoted-description-with-trigger-phrases pattern scoped to atmos/Cloud-Posse infra intents (ref: Q4); rely on skill-creator triggering eval (out-of-scope) and manual checks (ref: Q12). |
| skill-creator / writing-bash-scripts unreadable in design; authoring assumptions may diverge from their actual rules | med | low | Treat their use as a process step the implementer performs live; do not hard-code assumptions about their internals (ref: Q2, Q7, Q8). |
| Reference content factual drift (atmos CLI flags/behavior) since knowledge cutoff | low | med | Cite atmos docs during authoring; keep CLI specifics in `references/cli-reference.md` so corrections are localized; verify commands manually (ref: Q10). |

## Open Questions

- OQ1: Does the agentskills.io standard mandate a frontmatter schema that conflicts with the in-repo five-field schema (ref: Q1)? If so, which wins — the in-repo loader's expectations or the external standard?
- OQ2: Confirm the skill directory name. `atmos` is proposed (no `qrspi-` prefix, since this is not a workflow phase); the repo's only naming convention observed is lowercase-hyphenated, project-prefixed for phase skills (ref: Q4). Is a non-prefixed name acceptable?
- OQ3: Should this ticket add the mechanical acceptance checker (Decision 3, Option A), or stay minimal and rely on manual + out-of-scope skill-creator verification (Option B)? This is a scope call only a human can make.
- OQ4: Should the new skill be listed in `README.md` / `.claude/CLAUDE.md` skill catalogs for discoverability, or left undocumented since it is not a QRSPI phase?
