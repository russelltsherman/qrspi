# Implementation Plan — Self-verifying design & plan producers: codebase-grounded claim checks + pre-persist verification gate

**Structure basis:** structure.md @ 2026-06-19
**Generated:** 2026-06-19T00:00:00Z
**Status:** draft
**Total steps:** 38

## Slice 1: Verification core + tests + seam fixtures

### Setup

1. ✨ Create `scripts/qrspi_verify_artifact.py` — new pure verification-core module. Start with the strict helper-convention scaffold: module docstring, `from __future__` not needed (stdlib `argparse`, `json`, `re`, `sys`, `pathlib` only), self-locating engine root via `qrspi_paths.resolve_repo_root` (mirroring `qrspi_persist.py`). No logic yet — placeholder `main()` returning exit 0 so the file imports.

### Core Logic

2. ⚠️ Modify `scripts/qrspi_verify_artifact.py` — add `extract_acs(ticket_text: str) -> list[dict]`. Parse the `## Acceptance Criteria` section's AC bullets into `ACCoverageEntry` dicts `{ id, text, mapped: False }`. **Match every AC bullet form real QRSPI tickets use**, not only the template's checkbox style — at minimum: (a) the ticket-TEMPLATE checkbox form `- [ ] ACn: ...`, and (b) the **bold/em-dash bullet form the actual RUS-94 (and similar prose) tickets use** — `* **ACn — ...** ...` and `- **ACn — ...** ...` (asterisk-or-dash bullet, bold `**ACn`, em-dash or hyphen separator). A single tolerant `re` pattern keyed on the `ACn` token (case-insensitive `AC` + digits) anchored to a leading list bullet covers both, extracting `id` (`AC1`…) and the remaining `text`. A zero/missing/malformed section returns `[]` (no crash; caller treats as "no AC signal"). Per structure.md Contracts (ref: design §AC3, Risk row 6).

3. ⚠️ Modify `scripts/qrspi_verify_artifact.py` — add `build_coverage_map(acs: list[dict], artifact_text: str) -> list[dict]`. For each AC entry, set `mapped=True` iff its `id` (e.g. `AC3`) is referenced in `artifact_text`; return the updated entry list. Per structure.md Contracts (ref: design §AC3).

4. ⚠️ Modify `scripts/qrspi_verify_artifact.py` — add `scan_dangling_refs(artifact_text: str, valid_sinks: list[str]) -> list[dict]`. Detect internal section pointers / cross-refs whose target heading is absent; a pointer into a name present in `valid_sinks` (which MUST include the `## Open Questions` heading literal, shared by design and plan) is NOT dangling. Return a list of `Finding {kind:"dangling_ref", detail, ref}`. Per structure.md Contracts (ref: design §AC4, §Delta plan.md note).

5. ⚠️ Modify `scripts/qrspi_verify_artifact.py` — add module-level constant for the Open Questions section heading literal used as the canonical valid sink (e.g. `OPEN_QUESTIONS_HEADING = "## Open Questions"`), so step 4's `valid_sinks` default and Slice 2's template cross-check reference one source of truth.

6. ⚠️ Modify `scripts/qrspi_verify_artifact.py` — add `decide(acs, coverage, dangling, has_signal: bool) -> tuple[str, bool, list[dict]]`. Tri-state: no signal → `("none", True, [])`; signal + empty findings → `("pass", True, [])`; signal + findings → `("fail", False, findings)`. Findings = unmapped-AC findings (`kind:"unmapped_ac"`) from `coverage` + `dangling`. Enforce invariant `pass:false ⟺ findings non-empty`. Per structure.md Contracts (ref: design §Decision 1, §AC6).

7. ⚠️ Modify `scripts/qrspi_verify_artifact.py` — replace the placeholder `main()` with the real one: argparse long flags `--ticket --artifact --stage-root --repo-root`; read the staged artifact at `<stage-root>/<ticket>/<artifact>.md` and the ticket text; derive `has_signal` (any ACs extracted OR artifact has verifiable refs); call the core functions; print one `VerifyEnvelope { ok, signal, verified, findings, error? }` JSON (`indent=2`, bare `print()`); exit code mirrors `ok`. On read error, emit `ok:false` with `error` and a non-zero exit. Per structure.md Contracts (ref: design §Delta, helper convention Q3/Q4).

### Tests

8. ✨ Create `scripts/qrspi_verify_artifact_test.py` — stdlib-only, assert-based, zero-registration sibling. Add `extract_acs` cases covering **both** real AC bullet forms: (a) checkbox `- [ ] AC1: ...`/`- [ ] AC2: ...` → entries; (b) **the actual RUS-94 bold/em-dash form** `* **AC1 — ...** ...` / `- **AC2 — ...** ...` → entries with `id` `AC1`/`AC2` (this case MUST fail against a checkbox-only matcher — it is the regression guard for the silently-narrowed-AC3 finding); a section mixing both forms → all entries; missing section → `[]`; malformed/no-`ACn` lines → `[]`/skip (no crash). (ref: design §Delta, Risk row 6).

9. ⚠️ Modify `scripts/qrspi_verify_artifact_test.py` — add `build_coverage_map` cases: an artifact mentioning AC1/AC2 but not AC3 → AC3 `mapped:False`; all mentioned → all `mapped:True`.

10. ⚠️ Modify `scripts/qrspi_verify_artifact_test.py` — add `scan_dangling_refs` cases: a pointer to a missing heading → one `dangling_ref` finding; a pointer to `## Open Questions` when that is in `valid_sinks` → no finding.

11. ⚠️ Modify `scripts/qrspi_verify_artifact_test.py` — add `decide` tri-state cases: no signal → `("none",True,[])`; signal + clean → `("pass",True,[])`; signal + findings → `("fail",False,findings)`; assert `pass:false ⟺ findings non-empty` holds in each.

### Seam Fixtures

12. ✨ Create `scripts/fixtures/contract_seam/verify-artifact/wellformed.json` — canonical `VerifyEnvelope` golden for the JS↔Python seam: `{ "ok": true, "signal": "pass", "verified": true, "findings": [] }`.

13. ✨ Create `scripts/fixtures/contract_seam/verify-artifact/fail.json` — `signal:"fail"` variant with a non-empty `findings` array (one `unmapped_ac`, one `dangling_ref`) and `ok:false, verified:false`.

14. ✨ Create `scripts/fixtures/contract_seam/verify-artifact/none.json` — `signal:"none"` pass-through variant: `{ "ok": true, "signal": "none", "verified": true, "findings": [] }`.

15. ✨ Create `scripts/fixtures/contract_seam/verify-artifact/malformed.json` — a deliberately malformed envelope (missing required field / wrong type) for the consumer-side rejection test.

### Verify Slice 1

16. **Checkpoint:** `python3 scripts/run_tests.py verify_artifact && python3 scripts/qrspi_verify_artifact.py --ticket RUS-94 --artifact design --stage-root /tmp/phase-stage --repo-root "$(pwd)"`
    - [ ] `run_tests.py verify_artifact` passes (all assert cases green)
    - [ ] the `main()` invocation prints a well-formed `VerifyEnvelope` JSON and exits with a code mirroring `ok`
    - [ ] tri-state covered: no-signal → `"none"`+pass-through; signal+clean → `"pass"`; signal+findings → `"fail"`

---

## Slice 2: Plan-side Open Questions sink (template + agent)

### Core Logic

17. ⚠️ Modify `.qrspi/templates/plan.md` — add a `## Open Questions` section after `## Rollback Notes`. Bulleted `OQN:` items, prose-only, "things only a human can answer," mirroring `.qrspi/templates/design.md`'s Open Questions section.
    - **Current:** template ends with `## Rollback Notes` (sections: `## Slice N` + `## Rollback Notes` only).
    - **After:** template additionally contains a `## Open Questions` section with `OQN:` bullet guidance.

18. ⚠️ Modify `.claude/agents/qrspi-plan.md` — add an Open-Questions authoring step instructing the plan producer to route any unconfirmable claim into the `## Open Questions` section (the fail-closed sink), mirroring the design agent's "Open Questions — things only a human can answer" step.
    - **Current:** plan agent has no Open-Questions concept.
    - **After:** plan agent prose instructs writing the `## Open Questions` section as the sink for unconfirmable claims.

### Verify Slice 2

19. **Checkpoint:** `grep -n "## Open Questions" .qrspi/templates/plan.md && grep -n "Open Questions" .claude/agents/qrspi-plan.md && grep -n "## Open Questions" scripts/qrspi_verify_artifact.py`
    - [ ] `.qrspi/templates/plan.md` contains a `## Open Questions` section with `OQN:` bullet guidance
    - [ ] `qrspi-plan.md` instructs writing the Open Questions section as the sink for unconfirmable claims
    - [ ] Slice 1's `OPEN_QUESTIONS_HEADING` constant string matches the literal heading added to `plan.md` (sink recognized by `scan_dangling_refs`)

---

## Slice 3: Code-grounded producers (design + plan agents)

### Core Logic

20. ⚠️ Modify `.claude/agents/qrspi-design.md` — change the tools declaration to `tools: Read, Write, Grep, Glob` (ADDITIVE: add Grep + Glob for codebase verification; **retain Write**, which the producer needs to emit its artifact to `OUTPUT_PATH`).
    - **Current:** `tools: Read, Write` (with "no codebase exploration" prohibition).
    - **After:** `tools: Read, Write, Grep, Glob`.

21. ⚠️ Modify `.claude/agents/qrspi-design.md` — document a new `REPO_ROOT` input (codebase path scoped to the worktree) in the Inputs section, reusing the RUS-82 lens posture ("Read and Grep real source here to verify the artifact's claims") (ref: design §AC1).

22. ⚠️ Modify `.claude/agents/qrspi-design.md` — reframe the research-as-redo prose: research.md is the primary map; code reads via Read/Grep over `REPO_ROOT` are targeted verification of specific claims, not a research redo. State the fail-closed rule: any code claim (each `Current:` line, signature, file path, symbol) that cannot be confirmed against source becomes an `## Open Questions` bullet rather than an assertion (ref: design §AC2, Risk row 1). Leave the stale FRAMING/N-select prose untouched (per OQ4).

23. ⚠️ Modify `.claude/agents/qrspi-design.md` — add an explicit self-verification pass covering AC2/AC3/AC4/AC5: verify every code claim against source (AC2), map every ticket AC explicitly in the artifact (AC3), self-review for dangling refs / internal contradictions (AC4), and reconcile ticket premises against research/code with contradictions surfaced as Open Questions (AC5).

24. ⚠️ Modify `.claude/agents/qrspi-plan.md` — change the tools declaration to `tools: Read, Write, Grep, Glob` (ADDITIVE: add Grep + Glob for codebase verification; **retain Write**, which the producer needs to emit its artifact to `OUTPUT_PATH`).
    - **Current:** `tools: Read, Write` (with "no codebase exploration" prohibition).
    - **After:** `tools: Read, Write, Grep, Glob`.

25. ⚠️ Modify `.claude/agents/qrspi-plan.md` — document the new `REPO_ROOT` and `TICKET_CONTENT_PATH` inputs in the Inputs section (`TICKET_CONTENT_PATH` so the plan producer can check ACs directly against the ticket; `REPO_ROOT` for targeted source verification) (ref: design §AC1, §AC3, Risk row 3).

26. ⚠️ Modify `.claude/agents/qrspi-plan.md` — reframe research-as-map / code-as-verification (same posture as the design agent) and state the fail-closed rule routing unconfirmable claims to the `## Open Questions` sink added in Slice 2 (ref: design §AC2, Risk row 1).

27. ⚠️ Modify `.claude/agents/qrspi-plan.md` — add the self-verification pass against ticket (`TICKET_CONTENT_PATH`) + structure + design: AC coverage computed directly against the ticket text (AC3, per OQ3), code-claim verification (AC2), dangling-ref / contradiction self-review (AC4), premise reconciliation (AC5).

### Verify Slice 3

28. **Checkpoint:** `grep -n "tools:" .claude/agents/qrspi-design.md .claude/agents/qrspi-plan.md && grep -n "REPO_ROOT" .claude/agents/qrspi-design.md && grep -n "TICKET_CONTENT_PATH" .claude/agents/qrspi-plan.md`
    - [ ] both agent defs declare `tools: Read, Write, Grep, Glob` (Write retained) and document `REPO_ROOT` (plan also `TICKET_CONTENT_PATH`)
    - [ ] agent prose reframes research as the map and code reads as targeted verification (not a research redo) and states the fail-closed rule (unconfirmable claim → Open Question)
    - [ ] manual e2e: a design/plan spawn over RUS-94 inputs reads code and converts at least one unconfirmable claim to an Open Question rather than asserting it

---

## Slice 4: Pre-persist gate wiring in qrspi-batch.js (spawn inputs + bounded retry + flag)

### Core Logic

29. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — add `REPO_ROOT = wd` to the design producer spawn prompt input splice.
    - **Current:** design spawn splices `TICKET_ID, TICKET_CONTENT_PATH, QUESTIONS_PATH, RESEARCH_PATH, OUTPUT_PATH, TEMPLATE_PATH`.
    - **After:** the same plus `REPO_ROOT = wd`.

30. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — add `REPO_ROOT = wd` and `TICKET_CONTENT_PATH = r.ticketContentPath` to the plan producer spawn prompt input splice.
    - **Current:** plan spawn splices `TICKET_ID, STRUCTURE_PATH, DESIGN_PATH, OUTPUT_PATH, TEMPLATE_PATH`.
    - **After:** the same plus `REPO_ROOT = wd` and `TICKET_CONTENT_PATH = r.ticketContentPath`.

31. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — add a `runVerifyGate(id, name, repoRoot)` helper that shells `python3 scripts/qrspi_verify_artifact.py --ticket <id> --artifact <name> --stage-root <stageRoot> --repo-root <repoRoot>`, parses stdout into a `VerifyEnvelope`, and returns it. Per structure.md JS gate contract (ref: design §AC6, §Decision 2).

32. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — insert the bounded producer loop in `runPhase` between producer-return (non-null) and `persistArtifact`: `produce → runVerifyGate`; on `signal:"fail"` re-produce up to a hardcoded bound of `2` (in-memory counter, re-using the same staged path); on `"pass"`/`"none"` fall through to `persistArtifact`; on exhaustion return `false` so `failTicket(t)` fires. Per structure.md (ref: design §Decision 3, §AC6).
    - **Current:** `runPhase` runs resume short-circuit → producer `agent()` → `persistArtifact` (single-shot, no verify).
    - **After:** producer `agent()` → bounded verify loop → `persistArtifact` (or `false` on exhaustion).

33. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — on bound-exhaustion set the `verifyFailed: bool` ride-along flag on the result object (mirroring `ciGaveUp`) and emit a distinct `log()` line naming the gate, the phase, and the findings count. Per structure.md Modified Types (ref: design §AC6, Risk row 5).

34. ⚠️ Modify `.claude/CLAUDE.md` — document the producer self-verification gate under the codebase-conventions section: the tested Python core (`qrspi_verify_artifact.py`), the thin JS gate in `runPhase`, the tri-state signal (none/pass/fail), the hardcoded bound of `2`, and the `verifyFailed` fail-closed terminal path (AC7).

### Tests

35. ⚠️ Modify `scripts/fixtures/contract_seam/verify-artifact/*` — only if Slice 4's consumer needs an additional golden beyond the Slice 1 fixtures (otherwise no-op; this step is conditional per structure.md Unverified Assumptions).

36. ⚠️ Modify the consumer test seam (`node:vm` over `qrspi-batch.js`) — only if `runPhase` consumes the envelope beyond a `*_SCHEMA` presence check, add a `parseVerify*` parser and a test asserting `wellformed.json` parses and `malformed.json` is rejected. Conditional per structure.md Unverified Assumptions / design §Delta Q12.

### Verify Slice 4

37. **Checkpoint:** `python3 scripts/run_tests.py`
    - [ ] full unit-test suite passes (regression gate)
    - [ ] `node:vm` consumer test (if a `parseVerify*` parser was added) asserts the well-formed fixture parses and the malformed one is rejected

38. **Checkpoint (manual e2e):** spawn the design/plan phase over RUS-94 inputs through `runPhase`
    - [ ] design + plan spawn prompts include `REPO_ROOT` (plan also `TICKET_CONTENT_PATH`)
    - [ ] a clean artifact persists; an artifact with an unmapped AC re-produces up to bound `2`, then `runPhase` returns `false`, `failTicket` records `verifyFailed`, and nothing is persisted
    - [ ] a no-signal artifact behaves exactly as today (persists; backward-compat)

---

## Rollback Notes

- **Step 17 (`.qrspi/templates/plan.md`):** config/template change. To reverse, delete the added `## Open Questions` section; no migration or state to unwind. Must be reverted in lockstep with Slice 1's `OPEN_QUESTIONS_HEADING` constant if the heading literal changes, or `scan_dangling_refs` will no longer recognize the plan's sink.
- **Step 32 (`runPhase` bounded loop):** behavioral change to the persist path. To reverse, remove the verify loop and restore the direct `producer → persistArtifact` sequence; because the gate is fail-closed (never persists an unverified artifact), reverting only relaxes the gate — no persisted-state cleanup needed.
- **Step 34 (`.claude/CLAUDE.md`):** documentation only; reverse by removing the added gate paragraph. No functional impact.
