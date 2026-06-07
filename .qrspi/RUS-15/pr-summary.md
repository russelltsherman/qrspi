# PR: RUS-15 Add using-kubectl-cli agent skill

**Ticket:** RUS-15
**Design:** design.md @ 2026-06-03T00:00:00Z
**Structure:** structure.md @ 2026-06-06T00:00:00Z

## Summary

Adds a new convention-conformant agent skill at `.claude/skills/using-kubectl-cli/`
that gives agents copy-pasteable kubectl guidance for inspecting, debugging, and
changing Kubernetes clusters. The skill is a single inline-monolith `SKILL.md`
(mirroring the in-repo `qrspi-work` precedent — Decision 1) plus four `references/`
files (JSONPath/extraction, krew catalog, RBAC decision tree, common errors) linked
by bare relative paths. It encodes a top-of-body HARD-STOP safety guardrail
(context verification, dry-run-before-delete, explicit namespace flags), an ordered
debugging-escalation section (events → logs → describe → exec/debug), and a DO/DON'T
scope firewall. This is a content-only change — no executable code, no orchestration
script, and no `.claude/agents/` file is touched. **Reviewer focus:** (1) the
`TripleIdentity` invariant and quoted `description` (no automated validator exists),
and (2) the manual end-to-end trigger check, which could not be performed inside the
non-interactive implement sub-agent (see Open Items).

## Acceptance Criteria Mapping

> The ticket's acceptance criteria are restated from design.md §Desired End State,
> which maps each criterion to concrete behavior. No automated test exists for this
> feature (`run_eval.py` is a stub — design Q10); every "Test" below is a manual
> checkpoint recorded in impl-log.md Session 2.

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: agentskills.io structure + valid five-field frontmatter | `.claude/skills/using-kubectl-cli/SKILL.md` (frontmatter L1–4) | T13 manual frontmatter parse (PyYAML absent → stdlib) — all 5 fields present, pass |
| AC2: Built using the Anthropic skill-builder skill | `SKILL.md` (authoring process) | T13/OQ1 — `skill-creator` unavailable in non-interactive sub-agent; hand-authored to same structure, deviation recorded (see Deviations) |
| AC3: SKILL.md under 500 lines / 5000 tokens | `.claude/skills/using-kubectl-cli/SKILL.md` (203 lines) | T14 `wc -l SKILL.md` → 203 (< 500 cap; 3 over the < 200 target, accepted) |
| AC4: `references/` covers JSONPath, krew catalog, RBAC tree, errors+resolutions | `references/jsonpath.md`, `references/krew-plugins.md`, `references/rbac-debugging.md`, `references/common-errors.md` | T12 `ls references/` → all 4 present, pass |
| AC5: covers all convention subsections with copy-pasteable patterns | `SKILL.md` per-convention command-block sections | T14 manual review — all subsections covered with `<angle-bracket>`-placeholder blocks, pass |
| AC6: safety guardrails prominently placed | `SKILL.md` `GuardrailBlock` (HARD STOP, near top) | T14 — `GuardrailBlock` present, pass |
| AC7: debugging escalation events → logs → describe → exec/debug | `SKILL.md` `DebugEscalation` section + `references/rbac-debugging.md` | T14 — ordered `DebugEscalation` section present, pass |
| AC8 (contract): TripleIdentity + bare-relative reference links | `SKILL.md` (`name`/`command`/dir all `using-kubectl-cli`; links L57/72/97/146/157/168) | T13/T14 — TripleIdentity holds; all 4 links bare-relative, zero `./`/`.claude/`-prefixed, pass |

## Changes by Slice

### Slice 1: Author the using-kubectl-cli skill (SKILL.md + references)

| File | Change | Lines |
|------|--------|-------|
| `.claude/skills/using-kubectl-cli/SKILL.md` | ✨ new | +203 |
| `.claude/skills/using-kubectl-cli/references/jsonpath.md` | ✨ new | +81 |
| `.claude/skills/using-kubectl-cli/references/rbac-debugging.md` | ✨ new | +72 |
| `.claude/skills/using-kubectl-cli/references/common-errors.md` | ✨ new | +67 |
| `.claude/skills/using-kubectl-cli/references/krew-plugins.md` | ✨ new | +46 |

> Slice subtotal: 5 files, +469 lines.

### Non-slice: QRSPI phase artifacts

> Committed by the design/plan phases on this stack (not part of the slice deliverable),
> accounted for here per rule 3 (every diff file is enumerated).

| File | Change | Lines |
|------|--------|-------|
| `.qrspi/RUS-15/research.md` | ✨ new | +428 |
| `.qrspi/RUS-15/plan.md` | ✨ new | +122 |
| `.qrspi/RUS-15/structure.md` | ✨ new | +118 |
| `.qrspi/RUS-15/design.md` | ✨ new | +92 |
| `.qrspi/RUS-15/worktree.md` | ✨ new | +53 |
| `.qrspi/RUS-15/impl-log.md` | ✨ new | +50 |
| `.qrspi/RUS-15/questions.md` | ✨ new | +47 |

> Diff total: 12 files, +1379 lines (5 slice source + 7 phase artifacts).

## Testing Summary

> No automated test exists for this feature — it produces Markdown skill source, and
> `run_eval.py` is a documented non-functional placeholder (design Q10). Verification
> is the manual checkpoint set from structure.md / plan.md, recorded in impl-log.md.

- [x] Slice 1: file presence — `ls .claude/skills/using-kubectl-cli/ && ls .../references/` — SKILL.md + 4 reference files present, dir name `using-kubectl-cli` (T12 pass)
- [x] Slice 1: frontmatter — manual stdlib parse (PyYAML absent) — all 5 fields present; `description` is a balanced quoted scalar containing `:` and `,`; TripleIdentity holds (T13 pass)
- [x] Slice 1: body budget + structure — `wc -l SKILL.md` → 203 (< 500 cap); all 4 body links bare-relative; `GuardrailBlock`, `DebugEscalation`, `ScopeFirewall` all present (T14 pass)
- [ ] Manual end-to-end trigger: a kubectl-phrased prompt auto-invokes the skill — **NOT performed** in the implement sub-agent (no trigger-logging mechanism, Q12; agent cannot self-invoke its own new skill). Deferred to reviewer (see Open Items).

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| Authoring method (OQ1 / Risk Register row 1) | Author via global `skill-creator` skill + eval loop | Hand-authored to the agentskills.io structure, modeled on the in-repo `qrspi-work` inline-monolith pattern | `skill-creator` is an interactive guided/eval-loop skill unsuited to a non-interactive vertical-slice sub-agent; structure/plan explicitly provide this fallback ("if `skill-creator` is unavailable, hand-author to the same structure and record the deviation"). No contract (TripleIdentity, ReferenceLink, BodyBudget, GuardrailBlock, ScopeFirewall, DebugEscalation) was violated. |
| BodyBudget target | `SKILL.md` body target < 200 lines | 203 lines | 3 lines over the soft target; well under the 500-line hard cap. Accepted in impl-log T14. |
| Plan granularity (steps T6–T11) | One Edit per step building `SKILL.md` incrementally | Single `SKILL.md` Write | Same end state; the slice is only testable as a whole (structure rule 8), so incremental edits add no verification signal. |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| `skill-creator` out of repo scope, not deterministically invocable (Q2) | Materialized — handled via the planned fallback; hand-authored to same structure, deviation recorded | `rm -rf .claude/skills/using-kubectl-cli/` |
| Body exceeds 500-line/5000-token budget, no automated check (Q7) | Mitigated — detail pushed into 4 `references/` files; SKILL.md is 203 lines | n/a — within budget |
| TripleIdentity broken → skill undiscoverable (Q11) | Mitigated — dir == `name` == `command` minus `/` == `using-kubectl-cli`, verified T13 | n/a |
| No automated test; trigger correctness only confirmable manually (Q10, Q12) | Accepted / open — manual trigger check still outstanding | n/a — see Open Items |
| Reference links wrong path form, breaking on-demand reads (Q1) | Mitigated — all 4 links bare-relative, zero prefixed, verified T14 | n/a |

> Rollback is trivial and non-destructive: deleting `.claude/skills/using-kubectl-cli/`
> removes the whole feature. No migration, config, registry, or `qrspi_persist.py`
> entry is touched (design §Delta; plan §Rollback Notes).

## Open Items

- **Manual trigger verification outstanding (AC2/Q12):** a reviewer must confirm a
  kubectl-phrased prompt auto-invokes the skill. The `description` was written with
  broad explicit trigger phrasing (get/describe/logs/exec/debug/rollout/apply/RBAC/krew)
  to maximize firing; this cannot be self-verified inside the implement sub-agent.
- **OQ2 — directory name:** committed as `using-kubectl-cli` (mirroring global
  `using-graphite-cli`), whereas every other *in-repo* skill is `qrspi-*`-namespaced.
  Confirm this naming is intended before landing.
- **OQ3 — production-context guardrails:** the `GuardrailBlock`/`ScopeFirewall` are
  structurally present but encode no environment-specific forbidden cluster/namespace.
  If specific production contexts must be blocked, that needs a human-supplied value
  (follow-up).
- **AC2 acceptance ruling:** confirm that structural conformance to the agentskills.io
  pattern satisfies "Built using the Anthropic skill builder skill," given the
  hand-authoring fallback was used (OQ1).
