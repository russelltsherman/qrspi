# Structure Outline — Self-verifying design & plan producers: codebase-grounded claim checks + pre-persist verification gate

**Design basis:** design.md @ 2026-06-19
**Generated:** 2026-06-19T00:00:00Z
**Status:** draft

## New Types

These are JSON-shape contracts (no static type system; Python dicts + JS objects across the seam).

- `VerifyEnvelope { ok: bool, signal: "none" | "pass" | "fail", verified: bool, findings: [Finding], error?: string }` — the single JSON object `qrspi_verify_artifact.py` prints to stdout; the JS gate parses it. `pass:false ⟺ findings non-empty` (RUS-82 lens invariant); `signal:"none"` means no verifiable content present → pass-through (AC6 backward-compat).
- `Finding { kind: "unmapped_ac" | "dangling_ref" | "unconfirmed_claim" | "malformed_ac", detail: string, ref?: string }` — one verification failure; serialized inside `VerifyEnvelope.findings`.
- `ACCoverageEntry { id: string, text: string, mapped: bool }` — internal-to-core record produced by the AC-coverage map (ticket AC ↔ artifact mention); an entry with `mapped:false` becomes an `unmapped_ac` finding.

## Modified Types

- `result object` (qrspi-batch.js, `{ ticketId, action, summary, ... }`) — add ride-along flag `verifyFailed: bool` (mirrors existing `ciGaveUp`); set true when the producer-side verification bound is exhausted (ref: design.md §AC6, §Decision 3).
- plan artifact shape (`.qrspi/templates/plan.md`) — add a `## Open Questions` section (bulleted `OQN:` items, prose-only) as the AC2/AC5 fail-closed sink (ref: design.md §AC2, §Delta).

## Contracts

Python core (`scripts/qrspi_verify_artifact.py`) — pure functions, stdlib-only:

- `extract_acs(ticket_text: str) -> [ACCoverageEntry]` — parse `## Acceptance Criteria` AC bullets into entries, matching **every AC bullet form real QRSPI tickets use**, not only the template checkbox style: the checkbox form `- [ ] ACn: ...` AND the bold/em-dash bullet form the actual RUS-94 (and similar prose) tickets use — `* **ACn — ...** ...` / `- **ACn — ...** ...` (asterisk-or-dash bullet, bold `**ACn`, em-dash or hyphen). A single tolerant `re` pattern keyed on the `ACn` token covers both. Zero/malformed section → empty list (caller treats as "no AC signal", not a crash) (ref: design.md §AC3, Risk row 6).
- `build_coverage_map(acs: [ACCoverageEntry], artifact_text: str) -> [ACCoverageEntry]` — mark each AC `mapped` iff referenced in the artifact; unmapped → finding (ref: §AC3).
- `scan_dangling_refs(artifact_text: str, valid_sinks: [str]) -> [Finding]` — detect internal cross-refs / section pointers with no target; the plan's `## Open Questions` section must be a recognized valid sink, same as the design's (ref: §AC4, §Delta plan.md note).
- `decide(acs, coverage, dangling, has_signal: bool) -> (signal: str, verified: bool, findings: [Finding])` — tri-state gate: no signal → `("none", True, [])`; signal + empty findings → `("pass", True, [])`; signal + findings → `("fail", False, findings)` (ref: §Decision 1, §AC6).
- `main()` — argparse `--ticket --artifact --stage-root --repo-root`; reads staged artifact + ticket; prints one `VerifyEnvelope` JSON (`indent=2`, bare `print()`); exit code mirrors `ok` (ref: §Delta, helper convention Q3/Q4).

JS gate (`qrspi-batch.js`, inside `runPhase`):

- `runVerifyGate(id, name, repoRoot): VerifyEnvelope` — thin shell-out to `python3 scripts/qrspi_verify_artifact.py ...` between producer-return and `persistArtifact`; parses stdout (ref: §AC6, §Decision 2).
- bounded producer loop — `produce → verify`; on `signal:"fail"` re-produce up to a hardcoded bound of `2`; on exhaustion `runPhase` returns `false` → `failTicket(t)` with `verifyFailed` set; on `"pass"`/`"none"` fall through to `persistArtifact` (ref: §Decision 3, §AC6).

## Slice 1: Verification core + tests + seam fixtures

**Goal:** A standalone, unit-tested verification core that, given a staged artifact + ticket text, returns the tri-state `VerifyEnvelope`. Runnable and fully verifiable in isolation via `python3` before any JS or agent wiring exists.
**Files touched:**

- ✨ `scripts/qrspi_verify_artifact.py` — pure core (`extract_acs`, `build_coverage_map`, `scan_dangling_refs`, `decide`) + thin `main()` emitting the JSON envelope (ref: §Delta New files)
- ✨ `scripts/qrspi_verify_artifact_test.py` — stdlib-only assert-based sibling: AC-extraction, coverage pass/fail, dangling-ref detection, tri-state decision, zero/malformed-AC → pass-through (ref: §Delta, Risk row 6)
- ✨ `scripts/fixtures/contract_seam/verify-artifact/wellformed.json` — canonical envelope fixture for the JS↔Python seam
- ✨ `scripts/fixtures/contract_seam/verify-artifact/<malformed/edge>.json` — malformed + edge variants (ref: §Delta, Q12)

**Verification:**
- [ ] `python3 scripts/qrspi_verify_artifact.py --ticket RUS-94 --artifact design --stage-root <tmp> --repo-root <root>` prints a well-formed `VerifyEnvelope` and exits with code mirroring `ok`
- [ ] `python3 scripts/run_tests.py verify_artifact` passes (all assert cases green)
- [ ] tri-state covered: no-signal → `"none"`+pass-through; signal+clean → `"pass"`; signal+findings → `"fail"`

**Context cost:** M
**Depends on:** none

## Slice 2: Plan-side Open Questions sink (template + agent)

**Goal:** The plan producer gains the fail-closed `## Open Questions` sink that AC2/AC5 require and that Slice 1's `scan_dangling_refs` already treats as valid. Independently verifiable: the template renders the section and the agent instructs authoring it.
**Files touched:**

- ⚠️ `.qrspi/templates/plan.md` — add `## Open Questions` section (bulleted `OQN:` items, prose-only, mirroring `.qrspi/templates/design.md:43`) (ref: §AC2, §Delta)
- ⚠️ `.claude/agents/qrspi-plan.md` — add an Open-Questions authoring step (mirroring `qrspi-design.md:38`) so the plan producer routes unconfirmable claims there (ref: §AC2, §AC5, §Delta)

**Verification:**
- [ ] `.qrspi/templates/plan.md` contains a `## Open Questions` section with `OQN:` bullet guidance
- [ ] `qrspi-plan.md` instructs writing the Open Questions section as the sink for unconfirmable claims
- [ ] Slice 1's `scan_dangling_refs` recognizes the plan's section name as a valid sink (cross-check the constant against the literal section heading)

**Context cost:** S
**Depends on:** Slice 1 (the valid-sinks contract `scan_dangling_refs` enforces is what this section satisfies)

## Slice 3: Code-grounded producers (design + plan agents)

**Goal:** Both producer agents are reframed to read real source for targeted verification and to fail closed (unconfirmable claim → Open Question). End-to-end verifiable by running a producer spawn and inspecting that it reads code and routes a fabricated/unconfirmable claim to Open Questions instead of asserting it.
**Files touched:**

- ⚠️ `.claude/agents/qrspi-design.md` — `tools: Read, Write, Grep, Glob` (ADDITIVE: add Grep + Glob; **retain Write**, which the producer needs to emit its artifact to `OUTPUT_PATH`); add `REPO_ROOT` input; reframe research-as-map; author AC2/AC3/AC4/AC5 self-verification pass. Stale FRAMING/N-select prose left untouched (per OQ4) (ref: §AC1, §AC2, §Delta)
- ⚠️ `.claude/agents/qrspi-plan.md` — same tool/input changes plus `TICKET_CONTENT_PATH`; author the self-verification pass against ticket + structure + design (ref: §AC1, §AC2, §AC3, §Delta)

**Verification:**
- [ ] both agent defs declare `tools: Read, Write, Grep, Glob` (Write retained) and document `REPO_ROOT` (plan also `TICKET_CONTENT_PATH`)
- [ ] agent prose reframes research as the map and code reads as targeted verification (not a research redo) and states the fail-closed rule (unconfirmable claim → Open Question)
- [ ] manual e2e: a design/plan spawn over RUS-94 inputs reads code and converts at least one unconfirmable claim to an Open Question rather than asserting it

**Context cost:** M
**Depends on:** Slice 2 (the plan agent's fail-closed sink must exist before its self-verification pass can route into it)

## Slice 4: Pre-persist gate wiring in qrspi-batch.js (spawn inputs + bounded retry + flag)

**Goal:** `runPhase` runs the verification core between producer-return and persist, with a bounded re-produce loop and the `verifyFailed` hard-block on exhaustion; the spawn prompts plumb the new inputs. End-to-end verifiable: a clean artifact persists; an unverifiable one re-produces up to the bound then fails the ticket without persisting.
**Files touched:**

- ⚠️ `.claude/workflows/qrspi-batch.js` — add `REPO_ROOT = wd` to design + plan spawns and `TICKET_CONTENT_PATH = r.ticketContentPath` to the plan spawn; insert `runVerifyGate` + bounded (hardcoded `2`) re-produce loop in `runPhase`; add the distinct log line + `verifyFailed` result flag; if the envelope is consumed beyond a `*_SCHEMA` check, add a `parseVerify*` parser to the consumer test seam (ref: §AC6, §Decision 3, §Delta, Q12)
- ⚠️ `scripts/fixtures/contract_seam/verify-artifact/*` — only if the consumer-side parser needs an additional golden (otherwise no-op; primary fixtures land in Slice 1)
- ⚠️ `.claude/CLAUDE.md` — document the producer self-verification gate (AC7)

**Verification:**
- [ ] `node:vm`-over-`qrspi-batch.js` consumer test (if a `parseVerify*` parser is added) asserts the well-formed fixture parses and a malformed one is rejected
- [ ] design + plan spawn prompts include `REPO_ROOT` (plan also `TICKET_CONTENT_PATH`)
- [ ] manual e2e: clean artifact → persists; an artifact with an unmapped AC → re-produces up to bound `2`, then `runPhase` returns `false`, `failTicket` records `verifyFailed`, and nothing is persisted
- [ ] no-signal artifact behaves exactly as today (persists; backward-compat)
- [ ] `python3 scripts/run_tests.py` passes (full suite, regression gate)

**Context cost:** M
**Depends on:** Slice 1 (the core it shells), Slice 3 (the producers it re-invokes in the loop)

---

## Unverified Assumptions

- The exact JS↔Python seam test mechanism for this gate is conditional in the design ("**If** the gate envelope is consumed beyond a `*_SCHEMA` check, add a `parseVerify*` parser"). Whether a `parseVerify*` consumer parser is actually needed — versus a plain schema-presence check reusing the existing seam pattern — is left to the implementer's read of how `runPhase` consumes the envelope. Slice 4's consumer-test step is therefore conditional, not guaranteed.
- The design names a hardcoded retry bound of `2` but does not pin where in `runPhase` the in-memory counter lives relative to the existing resume short-circuit / `agent()` spawn ordering. The precise loop structure (counter scope, whether re-produce reuses the same staged path) is a plan-phase detail not fully determined by the design.
- `r.ticketContentPath` is asserted to be the resolver-staged ticket path the design spawn already uses, but the design does not show the resolver envelope field; that the plan spawn can read the identical field name is taken from the design's claim (ref: §AC1, Risk row 3) and is verified only at implementation against `qrspi_resolve.py`'s output.
- "Reframe research-as-map" and the fail-closed prose are agent-instruction (natural-language) changes whose effectiveness is only confirmable by a manual e2e producer run, not by any unit test — the design's Risk row 1 (fidelity-only drift) mitigation rests on prose quality, which has no deterministic gate.
