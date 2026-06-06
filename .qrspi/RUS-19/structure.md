# Structure Outline — Create a new agent skill for the atmos CLI

**Design basis:** design.md @ 2026-06-04T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft

## New Types

This ticket is primarily content authoring (a skill + reference docs), so there are
no runtime/data types. The only code artifact is the acceptance checker (Decision 3,
Option A), whose internal shapes are:

- `Violation = str` — a single human-readable failure message (e.g. `"frontmatter: missing field 'description'"`). The checker accumulates a `list[Violation]`; empty list == pass.
- `Frontmatter = dict[str, str]` — parsed YAML-ish key/value block between the leading `---` fences of `SKILL.md`.

## Modified Types

- None. The skill is self-contained; no existing type, schema, or data structure changes (ref: design.md §Delta — "Modified files: none required").

## Contracts

Cross-slice interface produced by Slice 1 and consumed (as the verification gate) by Slice 2:

- `parse_frontmatter(text: str) -> Frontmatter | None` — extract the `---`-fenced frontmatter block from `SKILL.md` body; returns `None` if no valid fenced block is present.
- `check_skill(skill_dir: Path) -> list[Violation]` — run all acceptance checks against a skill directory and return violations. Checks: (a) frontmatter present and contains the in-repo five-field schema `name, description, command, argument-hint, allowed-tools` with the agentskills.io core `name`/`description` non-empty; (b) frontmatter `name` == `skill_dir.name`; (c) `SKILL.md` body (content after frontmatter) is < 500 lines and within the ~5000-token budget (line count is exact; token budget is an approximate guard — see Unverified Assumptions); (d) all five `references/*.md` files exist and are non-empty: `stack-yaml-schema.md, vendoring.md, workflows.md, cli-reference.md, troubleshooting.md`.
- CLI entrypoint: `python3 scripts/atmos_skill_check.py <skill_dir>` — exits `0` when `check_skill` returns no violations, `1` otherwise, printing each violation. Shebang `#!/usr/bin/env python3`, exec bit set, stdlib-only (ref: design.md §Decision 3, Q8 conventions).

## Slice 1: Acceptance checker (TDD)

**Goal:** A stdlib-only Python checker that mechanically verifies the three checkable acceptance criteria (frontmatter shape, body line/token budget, five-reference presence), proven correct against fixtures before any skill content exists. Delivers an independently runnable, unit-tested verification gate.
**Files touched:**

- ✨ `scripts/atmos_skill_check.py` — implements `parse_frontmatter`, `check_skill`, and the CLI entrypoint per Contracts.
- ✨ `scripts/atmos_skill_check_test.py` — stdlib-only `_test.py` sibling exercising pass and each failure mode (missing field, name mismatch, over-budget body, missing/empty reference) using temp-dir fixtures.
**Verification:**
- [ ] `python3 scripts/atmos_skill_check_test.py` passes (all check branches covered).
- [ ] Running the CLI against a deliberately malformed fixture dir exits `1` and prints the violation; against a well-formed fixture exits `0`.
**Context cost:** S
**Depends on:** none
**Conditional:** This slice exists only if OQ3 resolves to Decision 3 Option A (build the checker). If the human chooses Option B (manual + out-of-scope skill-creator verification only), drop this slice and replace Slice 2's checker-based verification with a manual line count + five-doc presence check.

## Slice 2: The atmos skill (SKILL.md + five references)

**Goal:** The complete self-contained `atmos` skill exists and passes every acceptance criterion: valid frontmatter, body under budget with full-lifecycle guidance, and five reference docs cited by prose pointers. Authored via the `skill-creator` skill (process criterion, ref: design.md Q7). This is a single cohesive authoring unit — the body and its five references are mutually dependent (the under-budget body offloads depth into the references via backticked prose pointers), so they cannot be meaningfully verified apart.
**Files touched:**

- ✨ `.claude/skills/atmos/SKILL.md` — frontmatter (in-repo five-field schema, `name: atmos` == dir) + body organized by lifecycle: stack-targeting model (namespace/tenant/environment/stage, `stacks.name_pattern`), vendor/create, configure-in-stack (catalog + abstract/concrete inheritance), two-stage plan/apply + safety, remote state (`!terraform.state` vs `!terraform.output`), debugging. Each section ends with a prose pointer into its reference.
- ✨ `.claude/skills/atmos/references/stack-yaml-schema.md` — `import`/`vars`/`components`/`settings`/`env`/`metadata`/`backend`; deep-merge & import-ordering; catalog pattern; abstract/concrete inheritance; namespace/tenant/environment/stage; `name_pattern`; region mixins; remote-state YAML functions and module.
- ✨ `.claude/skills/atmos/references/vendoring.md` — `atmos vendor pull`; `vendor.yaml` and per-component `component.yaml`; mixins; commit-vs-JIT vendoring; Terraform Overrides (`.override.tf`) vs forking; version pinning with `{{.Version}}`.
- ✨ `.claude/skills/atmos/references/workflows.md` — `workflows/` YAML; step types (`atmos`/`shell`); workflow-level default stack; `atmos workflow <name> -f <file>`; `--dry-run`, `--from-step`.
- ✨ `.claude/skills/atmos/references/cli-reference.md` — terraform plan/apply/deploy; `--from-plan`; generate varfile/backend; auto-generated backend; `describe component`/`describe stacks`; validate; providers; helmfile (secondary).
- ✨ `.claude/skills/atmos/references/troubleshooting.md` — `describe component` as primary debug command; `ATMOS_LOGS_LEVEL`; common errors (missing `name_pattern`, tenant omitted, version mismatch); `validate stacks`, `terraform validate`.
**Verification:**
- [ ] `python3 scripts/atmos_skill_check.py .claude/skills/atmos` exits `0` (from Slice 1; if OQ3=Option B, do a manual `wc -l` on the body and confirm the five reference files exist and are non-empty instead).
- [ ] Manual review: every body lifecycle section ends with a prose pointer to its matching reference; each acceptance criterion in design.md §Desired End State maps to a present body section or reference.
- [ ] Skill authored through the `skill-creator` skill and its eval/triggering loop (process criterion, ref: Q7, Q12) — verified by the implementer invoking it, not a repo artifact.
**Context cost:** L
**Depends on:** Slice 1 (consumes the checker as its verification gate; soft dependency — if OQ3=Option B this becomes a standalone slice with manual verification)

---

## Unverified Assumptions

These are claims/decisions from design.md that could not be mapped to concrete, settled
code or structure and need human attention before planning:

- **OQ1 — agentskills.io vs in-repo frontmatter schema (blocking for Slice 2 frontmatter and Slice 1 check (a)):** Design assumes the in-repo five-field schema wins and the agentskills.io `name`/`description` core is a subset that coexists. If agentskills.io actually mandates a conflicting schema, both the SKILL.md frontmatter and the checker's field list must change. Not verifiable from the repo (ref: Q1, Q5, Risk row 1).
- **OQ2 — skill directory/name `atmos` (blocking for `name`==dir check and all paths):** Proposed name is unprefixed `atmos`. All file paths in both slices assume this. A different chosen name re-paths everything (ref: Q4).
- **OQ3 — whether to build the checker (determines existence of Slice 1):** Decision 3 recommends Option A (the checker), but design explicitly defers the scope call to a human. Slice 1 and Slice 2's primary verification depend on this answer (ref: design.md §Decision 3).
- **OQ4 — listing the skill in `README.md` / `.claude/CLAUDE.md` catalogs:** Optional discoverability edit deferred; not included as a slice. If the human wants it, it adds one or two ⚠️-modified files to Slice 2 (still under the 10-file limit) (ref: §Delta, Q9).
- **Token-budget check is approximate:** The 5000-token criterion has no in-repo tokenizer; `check_skill` check (c) can enforce the 500-line bound exactly but only approximate tokens (e.g. a char- or word-based heuristic). Exact token conformance relies on out-of-scope skill-creator tooling (ref: Q5, Q11).
- **skill-creator / writing-bash-scripts internals unreadable:** Their authoring/eval rules are assumed, not verified; treated as a live process step in Slice 2, not encoded as structure (ref: Q2, Q7, Q8, Risk row 4).
- **atmos CLI factual accuracy:** Reference content (flags, YAML functions, behaviors) is asserted from design/knowledge and may drift from the current atmos CLI; must be verified against atmos docs during Slice 2 authoring (ref: Q10, Risk row 5).
