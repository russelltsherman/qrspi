# Implementation Plan — Create new agent skill: writing-github-actions

**Structure basis:** structure.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total steps:** 13

> Content-only / prose skill (structure §Note, Decision 1 Option A). No runtime
> code, no scripts, no programmatic types. "Contracts" are document contracts:
> the `SKILLFrontmatter` shape and the SKILL.md → `references/` pointer interface.
> All steps create new prose files under `.claude/skills/writing-github-actions/`.
> No existing files are modified (structure §Modified Types: None).

## Slice 1: Author writing-github-actions skill (SKILL.md + four references)

### Setup

1. ✨ Create `.claude/skills/writing-github-actions/references/` directory — establishes the only precedented extra-dir pattern (Decision 2; structure §Contracts). Atomic: `mkdir -p .claude/skills/writing-github-actions/references`.

### Core Logic

2. ✨ Create `.claude/skills/writing-github-actions/references/security-hardening-checklist.md` — reference topic `security-hardening` per `ReferenceFile`. Body: SHA-pinning as a hard rule, least-privilege `permissions: {}`, expression-injection avoidance, `pull_request_target` PR-head-checkout rules, CODEOWNERS, zizmor check mapping (structure file list; design §Delta). Satisfies the `references/security-hardening-checklist.md restates→ SHA-pinning` half of the cross-reference contract (Decision 4: echo/link, not full duplicate of the SKILL.md canonical statement).

3. ✨ Create `.claude/skills/writing-github-actions/references/oidc-setup-patterns.md` — reference topic `oidc-setup` per `ReferenceFile`. Body: provider-agnostic OIDC auth (AWS/GCP/Azure) replacing static cloud secrets, GitHub Environments (structure file list; design §Delta).

4. ✨ Create `.claude/skills/writing-github-actions/references/common-workflow-templates.md` — reference topic `common-workflow-templates` per `ReferenceFile`. Body: single-job CI through multi-job deploy pipelines; reusable-workflow (`workflow_call`) and composite-action skeletons (structure file list; design §Delta).

5. ✨ Create `.claude/skills/writing-github-actions/references/matrix-strategy-examples.md` — reference topic `matrix-strategy` per `ReferenceFile`. Body: `strategy.matrix`, `fail-fast: false`, `include`/`exclude`, cache-key isolation (structure file list; design §Delta).

6. ✨ Create `.claude/skills/writing-github-actions/SKILL.md` — frontmatter conforming to `SKILLFrontmatter { name: "writing-github-actions" (== dir name == command slug), description: "what it does + when to use it" with GHA-YAML-authoring trigger phrases + negative scope }`; `command`/`argument-hint` per in-repo baseline; `allowed-tools` per OQ4 decision (content-only skill, reconcile at authoring). Body: lifecycle-organized guidance (triggers → jobs → steps → caching → artifacts → secrets → deployments), reusable-workflow-vs-composite-action decision section, concurrency/performance section, SHA-pinning canonical hard-rule statement, and exactly four backticked relative `references/` pointers (`ReferencePointer`: no leading `./`, no absolute) — one per ReferenceFile from steps 2–5. Honors `SKILL.md.frontmatter conforms to SKILLFrontmatter`, `SKILL.md.body links→ references/*.md`, `SKILL.md.body states→ SHA-pinning`, and `skill ⟂ zizmor-rules` contracts (structure §Contracts).

### Tests

7. No automated tests — prose-only skill; repo policy verifies prompt/skill behavior by manual e2e, reserving unit tests for Python logic (design §Current State Q12; structure §Note). Tests are the manual checkpoints below.

### Verify Slice 1

8. **Checkpoint:** `test "$(grep -m1 '^name:' .claude/skills/writing-github-actions/SKILL.md | awk '{print $2}')" = writing-github-actions`
   - [ ] `name` in frontmatter equals the directory name and command slug (structure §Verification; Q5).

9. **Checkpoint:** `ls .claude/skills/writing-github-actions/references/security-hardening-checklist.md .claude/skills/writing-github-actions/references/oidc-setup-patterns.md .claude/skills/writing-github-actions/references/common-workflow-templates.md .claude/skills/writing-github-actions/references/matrix-strategy-examples.md`
   - [ ] All four `references/` files exist (steps 2–5).
   - [ ] Every backticked pointer in SKILL.md is a relative path (no leading `./`, no absolute) and resolves to one of these files (manual cross-check).

10. **Checkpoint:** `awk 'END{print NR}' .claude/skills/writing-github-actions/SKILL.md`
    - [ ] SKILL.md body under 500 lines AND under 5000 tokens (manual line/token count — no automated gate, Q7; structure §Verification).

11. **Checkpoint:** manual content review of SKILL.md
    - [ ] Every AC topic present: lifecycle coverage (triggers→deployments), reusable-vs-composite decision section, concurrency/performance section, SHA-pinning hard rule in body AND restated in security reference (structure §Verification; Decision 4).

12. **Checkpoint:** manual e2e — hand-author a sample workflow under the skill's rules and a GHA-YAML-authoring prompt
    - [ ] Sample workflow satisfies zizmor's checks: SHA-pinning, least-privilege `permissions`, no expression injection, no `pull_request_target` with PR-head checkout (Q12, Decision 3 — rule-conformance, not an in-repo gate).
    - [ ] A GHA-YAML-authoring prompt auto-triggers the skill (description triggers correctly; no in-repo dispatch logger, Q13).

13. **Checkpoint (closing step):** invoke the `skill-creator` skill / its eval loop on the authored skill per the user's standing skill-creation directive; reconcile its scaffold + frontmatter expectations against the in-repo shape (OQ1/OQ2; structure §Verification final step).
    - [ ] skill-creator eval run completed; frontmatter reconciled against in-repo baseline; any agentskills.io field conflicts resolved.

---

## Rollback Notes

- No DB migrations, config changes, or destructive ops — the slice is purely additive (structure §Modified Types: None; design §Delta "No modified files").
- Steps 1–6: to roll back, `rm -rf .claude/skills/writing-github-actions/` removes the entire new skill directory; no other files are touched.
- Step 13 (skill-creator): if reconciliation surfaces an agentskills.io frontmatter conflict (OQ2) or escalates the optional `references/zizmor-audit.md` (structure §Unverified Assumptions), treat as a scope amendment and revisit structure before adding a fifth reference file.
