# Structure Outline — Create new agent skill: writing-github-actions

**Design basis:** design.md @ 2026-06-04T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft

> Note: This is a **content-only / prose skill** (Decision 1, Option A). There is
> no runtime code, no programmatic types, and no executable functions (design
> §Delta: "No new scripts… The skill is prose-only"). The "types" and "contracts"
> below are therefore the **document contracts** the skill must satisfy: the
> SKILL.md frontmatter shape and the SKILL.md → `references/` pointer interface.
> These are the only cross-file interfaces in scope.

## New Types

Pseudo-schemas (Markdown/YAML document shapes, not code types):

- `SKILLFrontmatter { name: string (== dir name == command slug), description: string ("what it does + when to use it", with trigger phrases + negative scope), command?: string, argument-hint?: string, allowed-tools?: string[] }`
  — in-repo frontmatter shape is the baseline; `name` MUST equal the directory name (ref: design §Current State, Q4/Q5). `allowed-tools` is open (OQ4 — content-only skill spawns no subagent).
- `ReferencePointer { backtickedRelativePath: string }`
  — a path relative to the skill root, no leading `./`, no absolute path; read on demand via a prose pointer (ref: design §Current State, Q8; Decision 2).
- `ReferenceFile { topic: one of [security-hardening, oidc-setup, common-workflow-templates, matrix-strategy], body: markdown }`
  — one file per AC-enumerated reference topic, each linked 1:1 from SKILL.md.

## Modified Types

- None. This is purely additive — no existing skill, agent, script, template, or workflow changes (ref: design §Delta "No modified files").

## Contracts

Cross-file / cross-artifact interfaces the slice must honor:

- `SKILL.md.frontmatter` conforms to `SKILLFrontmatter` — `name: writing-github-actions` equals the directory name; `description` encodes the GHA-YAML-authoring trigger so the runtime auto-dispatches the skill (ref: design §Desired End State).
- `SKILL.md.body links→ references/*.md` via `ReferencePointer` (backticked relative path, on-demand prose pointer) — exactly four pointers, one per `ReferenceFile` topic (Decision 2; ref: Q3/Q8).
- `SKILL.md.body states→ SHA-pinning as a non-negotiable default` AND `references/security-hardening-checklist.md restates→` the same rule as a hard rule (AC: SHA-pinning; cross-reference-over-duplication, Decision 4 — one is the canonical statement, the other links/echoes, not a full duplicate).
- `SKILL.md.body size < 500 lines AND < 5000 tokens` — verified by manual line/token count; no in-repo gate (ref: Q7; Risk Register).
- `skill ⟂ zizmor-rules` — the skill's hard rules (SHA-pinning, least-privilege `permissions: {}`, no expression injection, no `pull_request_target` with PR-head checkout) map to zizmor checks; conformance is the acceptance bar, verified manually (Decision 3; AC: passes zizmor).

## Slice 1: Author writing-github-actions skill (SKILL.md + four references)

**Goal:** A complete, self-contained `writing-github-actions` skill that auto-triggers
on GitHub Actions YAML authoring, with a lean SKILL.md body (under the 500-line /
5000-token limit) lifecycle-organized and linked by four on-demand `references/`
pointers — delivering the full end-to-end skill as one cohesive, mutually-dependent
authoring unit. (SKILL.md cannot be verified without its reference targets existing,
and the references have no purpose without the body that points to them — one sitting,
one testability boundary.)

**Files touched:**

- ✨ `.claude/skills/writing-github-actions/SKILL.md` — frontmatter (`SKILLFrontmatter`) + lifecycle-organized body (triggers, jobs, steps, caching, artifacts, secrets, deployments), reusable-workflow-vs-composite-action decision section, concurrency/performance section, SHA-pinning hard rule, four backticked `references/` pointers.
- ✨ `.claude/skills/writing-github-actions/references/security-hardening-checklist.md` — SHA-pinning, least-privilege `permissions: {}`, expression-injection avoidance, `pull_request_target` rules, CODEOWNERS, zizmor check mapping.
- ✨ `.claude/skills/writing-github-actions/references/oidc-setup-patterns.md` — provider-agnostic OIDC auth (AWS/GCP/Azure) replacing static cloud secrets, GitHub Environments.
- ✨ `.claude/skills/writing-github-actions/references/common-workflow-templates.md` — single-job CI through multi-job deploy pipelines; reusable-workflow (`workflow_call`) and composite-action skeletons.
- ✨ `.claude/skills/writing-github-actions/references/matrix-strategy-examples.md` — `strategy.matrix`, `fail-fast: false`, `include`/`exclude`, cache-key isolation.

**Verification:**

- [ ] `name` in SKILL.md frontmatter equals the directory `writing-github-actions` and the command slug (ref: Q5).
- [ ] All four `references/` pointers in SKILL.md are backticked relative paths (no leading `./`, no absolute) and each resolves to an existing file.
- [ ] SKILL.md body is under 500 lines AND under 5000 tokens (manual line/token count — no automated gate, ref: Q7).
- [ ] Every AC topic is present: lifecycle coverage (triggers→deployments), reusable-vs-composite decision section, concurrency/performance section, SHA-pinning hard rule in body + security reference.
- [ ] Hand-checked sample workflows produced under the skill's rules satisfy zizmor's checks (SHA-pinning, least-privilege permissions, no expression injection, no `pull_request_target` PR-head checkout) — manual e2e (ref: Q12; Decision 3).
- [ ] Manual e2e: a GHA-YAML-authoring prompt auto-triggers the skill (description triggers correctly; no in-repo dispatch logger exists, ref: Q13).
- [ ] **Validation pass (final step of this slice):** invoke the `skill-creator` skill / its eval loop on the authored skill per the user's standing directive on skill creation; reconcile its scaffold + frontmatter expectations against the in-repo shape (OQ1/OQ2). This is the closing step of this slice, not a separate slice.

**Context cost:** M
**Depends on:** none

---

## Unverified Assumptions

Claims from design.md that cannot be mapped to a concrete in-scope type, file, or
interface and need human attention before planning:

- **"Built using the Anthropic skill builder skill" (AC) — unverifiable in-repo.** `skill-creator` is a globally-available Claude Code skill, out of project scope; its inputs, scaffold output, and eval loop cannot be inspected from here (design Risk Register; OQ1). The user's standing directive ("always invoke skill-creator when creating/modifying a skill") makes invocation the expectation, but whether it is a *hard acceptance requirement* vs. "follow the agentskills.io structure" is unresolved (OQ1).
- **agentskills.io frontmatter spec is undocumented in-repo (OQ2).** The exact required fields and whether they conflict with the repo's `command` / `argument-hint` / `allowed-tools` conventions cannot be confirmed; the `SKILLFrontmatter` pseudo-type above uses the in-repo shape as baseline and must be reconciled at authoring time.
- **`allowed-tools` necessity for a content-only skill (OQ4).** Unknown whether a skill that spawns no subagent needs an `allowed-tools` allowlist at all; left as an open frontmatter decision.
- **zizmor "passes without warnings" acceptance evidence (OQ3).** Whether the team wants a documented review-checklist conformance (Decision 3, Option A) or an actual captured zizmor run is unresolved; no in-repo zizmor tooling exists, so the verification step above asserts rule-conformance, not a machine-proven gate.
- **Optional `references/zizmor-audit.md` (design §Delta, Decision 3).** Conditional on whether zizmor guidance fits inside `security-hardening-checklist.md`; not included in Slice 1's file list as it is contingent — promote to a fifth reference file only if the security checklist cannot absorb it.
