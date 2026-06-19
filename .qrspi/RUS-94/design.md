# Design — Self-verifying design & plan producers: codebase-grounded claim checks + pre-persist verification gate

**Ticket:** RUS-94
**Research basis:** research.md @ 2026-06-19
**Generated:** 2026-06-19T00:00:00Z
**Status:** draft

## Current State

The `qrspi-design` and `qrspi-plan` producer agents declare a minimal `Read, Write` toolset and explicitly forbid codebase exploration ("Your only reads are the input files ... no codebase exploration") (ref: Q5). They synthesize their artifact from the lossy ticket→questions→research chain and cannot verify any claim against source. The RUS-82 read-only-scoped posture (`tools: Read, Grep` + a `CODEBASE_PATH` input that the agent "Read and Grep real source here to verify the artifact's claims") already exists, but only in the `*-review` critic lenses — not in the producers (ref: Q5).

`runPhase` runs three deterministic steps in order: a resume short-circuit, the producer `agent()` spawn (a `null` return is phase failure), then `persistArtifact()`, which shells `python3 scripts/qrspi_persist.py --ticket <id> --artifact <name>`. The producer writes only to the token-free staging path `stg(id, name)` = `/tmp/phase-stage/<id>/<name>.md`; persist owns the canonical `.qrspi`-laden destination and `shutil.move`s the staged file there. The one natural gate insertion point is between the producer returning non-null and `persistArtifact` — the staged file exists and has not yet been moved (ref: Q1).

Producer spawn inputs are passed as absolute file PATHS, never inline. The design spawn splices `TICKET_ID`, `TICKET_CONTENT_PATH`, `QUESTIONS_PATH`, `RESEARCH_PATH`, `OUTPUT_PATH`, `TEMPLATE_PATH`. The plan spawn splices only `TICKET_ID`, `STRUCTURE_PATH`, `DESIGN_PATH`, `OUTPUT_PATH`, `TEMPLATE_PATH` — it receives neither the ticket nor REPO_ROOT; the design spawn also receives no REPO_ROOT (ref: Q2). Only the research spawn passes `REPO_ROOT = wd` (ref: Q2). ACs reach the design producer only as raw ticket markdown (`## Acceptance Criteria`, `- [ ] AC1: ...`) and reach the plan producer not at all; no machine-readable AC extraction, count, or coverage check exists anywhere, so a zero/malformed AC section degrades silently (ref: Q8).

`qrspi_persist.py` follows the strict helper convention: self-locating engine root via `qrspi_paths.resolve_repo_root`, argparse long flags, a pure functional core (`persist(src, dest) -> (bytes, error)`) wrapped by a thin `main()`, a single JSON envelope on stdout (`{ ok, repoRoot, src, dest, bytes, error? }`, `indent=2` + bare `print()`), and exit code mirroring `ok` (ref: Q3, Q4). It already fails loud on a missing/empty staged file with verbatim error strings (ref: Q9). `ok` means only "the move succeeded," not content validity (ref: Q9).

There is no connection today between a `runPhase` failure and the revise pass — they are separate mechanisms. A `runPhase` failure returns `false` → `failTicket(t)` (`action: 'failed'`, ticket left untouched, recomputed on re-run); this is pre-commit. `doRevise` is a different, post-commit, PR-gated action driven by the resolver `revise` decision, operating on a committed branch via `gt`/`gh` (ref: Q6). The only bounded-retry precedent is the CI-revise cap (`CI-Revise-Attempt: N` head-commit trailer, `ciReviseCap` default 3, cap-then-park with a visible `ciGaveUp`), but it lives on a committed PR head and is unusable pre-commit, so a producer-side gate needs its own bound (ref: Q10). The producer pipeline runs exactly once with no retry counter (ref: Q10).

`## Open Questions` is the design template's sixth required section: bulleted `OQN:` items, "things only a human can answer," prose-only (ref: Q7). It is **design-only** today — the plan template (`.qrspi/templates/plan.md`: `## Slice N` + `## Rollback Notes`) and plan agent (`.claude/agents/qrspi-plan.md`) have no Open-Questions section, so the AC2/AC5 fail-closed sink does not yet exist for the plan producer; this ticket adds it (see Delta). The verdict invariant `pass:false ⟺ findings non-empty` is the canonical shape in the RUS-82 lenses, with an optional non-blocking advisory channel (ref: Q9, Discovered Patterns). Tested helpers conform to a zero-registration `scripts/*_test.py` convention (standalone, stdlib-only, assert-based, subprocess-isolated by `run_tests.py`) (ref: Q11), and the JS↔Python seam is covered by committed contract/golden fixtures asserted from producer (Python) and consumer (`node:vm` over `qrspi-batch.js`) sides (ref: Q12). Phase outcomes surface via `log()` lines, recorded result objects (`{ ticketId, action, summary, ... }`) with optional ride-along flags like `ciGaveUp`, and the run-summary envelope (ref: Q13).

## Desired End State

- **AC1 — Code-grounded producers.** Both `qrspi-design.md` and `qrspi-plan.md` gain `Read, Grep, Glob` and a `REPO_ROOT` (codebase path) input, scoped to the worktree, reusing the RUS-82 lens posture (ref: Q5). The agent prose reframes research as the primary map and code reads as targeted verification, not a research redo. The design spawn adds `REPO_ROOT = wd`; the plan spawn adds both `REPO_ROOT = wd` and `TICKET_CONTENT_PATH = r.ticketContentPath` so the plan producer can check ACs against the ticket directly (ref: Q2, Q8 — closing the plan input asymmetry).
- **AC2 — Code-claim verification.** Before finalizing, each producer verifies every code claim (each `Current:` line, signature, file path, symbol) against actual source; any claim it cannot confirm is converted to an Open Question in that artifact's `## Open Questions` section rather than asserted (ref: Q5 fail-closed posture, Q7). **Sink asymmetry (must be closed by this ticket):** the `## Open Questions` section is a required section of the design template/agent today but does **not** exist in the plan template/agent (`.qrspi/templates/plan.md` defines only `## Slice N` + `## Rollback Notes`; `.claude/agents/qrspi-plan.md` has no Open-Questions concept — verified). Because AC2/AC5 require the same fail-closed sink for **both** producers, this ticket's Delta **adds** a `## Open Questions` section to the plan template and plan agent (see Modified files) so the plan producer has a real sink. Without that addition AC2/AC5 are unimplementable for the plan producer (the design must not rest on a plan-side section that does not exist).
- **AC3 — Completeness self-check.** Every ticket AC is explicitly mapped in the artifact. The verification core extracts ACs from ticket text and emits a coverage map; an unmapped AC is a finding (ref: Q8). For **both** producers the coverage map is computed **directly against the ticket text** — the design producer against its existing `TICKET_CONTENT_PATH`, the plan producer against the newly-plumbed `TICKET_CONTENT_PATH` (per OQ3, resolved: direct over transitive-via-`design.md`, so an AC the design dropped still surfaces as an unmapped-AC finding in the plan).
- **AC4 — Internal-consistency self-check.** The finalized artifact has no dangling cross-references or internal contradictions; the core scans for dangling references and the producer self-reviews for contradictions before finalize (ref: Q7).
- **AC5 — Premise reconciliation.** Ticket premises are reconciled against research/code; a premise the codebase contradicts surfaces as an explicit `## Open Questions` bullet in that artifact, not a silent workaround (ref: Q5, Q7). For the plan producer this relies on the same newly-added plan-side `## Open Questions` section described under AC2 (the plan template/agent gains the section in this ticket's Delta).
- **AC6 — Pre-persist gate.** A new gate sits in `runPhase` between the producer returning non-null and `persistArtifact` (ref: Q1). It shells a new tested Python verification-core helper over the staged artifact + upstream inputs; unresolved verification failures block persist and enter a bounded producer-side revise pass, and **on bound-exhaustion the phase hard-blocks** (per OQ1, resolved): `runPhase` returns `false` → `failTicket(t)` (terminal-for-run, ticket left untouched, recomputed next run) with the pinned `verifyFailed` result flag set — an artifact that cannot be verified is **never** persisted (fail-closed; no flagged-advance). The gate's decision logic is a pure stdlib Python core with a `_test.py` sibling, and the JS gate is a thin call (ref: Q4, Q11). The core emits a tri-state ("no signal present" → pass through unchanged; "pass" → persist; "fail" → re-produce) so a producer/runPhase with no verification signal behaves exactly as today (ref: Q9).
- **AC7 — Documentation.** `.claude/CLAUDE.md` describes the producer self-verification gate (ref: codebase conventions section).

## Delta

**New files**
- `scripts/qrspi_verify_artifact.py` — the tested verification core. Pure functions: AC extraction from ticket markdown, AC-coverage map vs artifact, dangling-reference scan, gate decision (tri-state). Thin `main()` with `--ticket`/`--artifact`/`--stage-root`/`--repo-root`, single JSON envelope `{ ok, signal: "none"|"pass"|"fail", verified, findings: [...], error? }` on stdout, exit code mirroring `ok` (ref: Q4, Q9).
- `scripts/qrspi_verify_artifact_test.py` — stdlib-only assert-based sibling: AC-extraction cases, coverage-map pass/fail, dangling-ref detection, tri-state gate decision, zero/malformed-AC behavior (ref: Q11).
- `scripts/fixtures/contract_seam/verify-artifact/` — `wellformed.json` + malformed/edge variants for the JS↔Python seam (ref: Q12).

**Modified files**
- `.claude/agents/qrspi-design.md` — `tools: Read, Grep, Glob`; add `REPO_ROOT` input; reframe research-as-map; author the AC2/AC3/AC4/AC5 self-verification pass. **The stale FRAMING/N-select prose is left untouched** (per OQ4, resolved: out of scope). The prose is confirmed stale, but it is unrelated to this ticket's ACs and the Risk Register flags active restack-conflict pressure on this shared file (concurrent RUS-88/RUS-90 edits), so the change surface is minimized and the cleanup is deferred to a separate follow-up ticket.
- `.claude/agents/qrspi-plan.md` — same tool/input changes plus `TICKET_CONTENT_PATH`; author the self-verification pass against ticket + structure + design (ref: Q5, Q8); **add a `## Open Questions` step/section** to the agent's authoring instructions so the plan producer has a fail-closed sink for AC2/AC5 (mirroring `qrspi-design.md:38`'s "Open Questions — things only a human can answer"), since the plan agent has no such concept today (verified).
- `.qrspi/templates/plan.md` — **add a `## Open Questions` section** (bulleted `OQN:` items, prose-only, "things only a human can answer", mirroring `.qrspi/templates/design.md:43`) so the plan artifact has the section AC2/AC5 route unconfirmable claims into; today the plan template defines only `## Slice N` + `## Rollback Notes` (verified). Note the verification core's section-presence/dangling-ref logic must treat the plan's Open Questions section as a valid sink the same way it does the design's.
- `.claude/workflows/qrspi-batch.js` — add `REPO_ROOT` (and plan's `TICKET_CONTENT_PATH`) to the spawn prompts; insert the pre-persist gate call + bounded producer-side retry in `runPhase`; add a distinct log line + the result flag **`verifyFailed`** (the pinned name, mirroring the existing `ciGaveUp` ride-along flag; used consistently in AC6 and Risk Register row 5) (ref: Q1, Q2, Q6, Q10, Q13). If the gate envelope is consumed beyond a `*_SCHEMA` check, add a `parseVerify*` parser to the consumer test seam (ref: Q12).
- `.claude/CLAUDE.md` — document the gate (AC7).

## Pattern Decisions

### Decision 1: Verdict / signal envelope shape

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Extend persist's `ok` to also mean content-valid | Minimal new fields | Overloads `ok` (means only "move succeeded"); cannot express "no signal vs failed" (ref: Q9) |
| B | New helper with explicit tri-state `signal: none\|pass\|fail` + `findings[]`, mirroring `pass:false ⟺ findings non-empty` | Cleanly separates "no signal → behave as today" (AC: additive) from "ran and failed"; reuses the established lens invariant | One more envelope field to validate |

**Recommendation:** Option B
**Rationale:** The codebase already overloads `ok` to mean only "the move succeeded" and the research flags reusing/extending it as wrong (ref: Q9 Implicit contracts). The `pass:false ⟺ findings non-empty` invariant with an optional non-blocking channel is the established RUS-82 verdict shape (ref: Q9, Discovered Patterns), and the tri-state directly satisfies AC6's "no verification signal → behave exactly as today."
**NEW PATTERN?** No — it composes the existing single-JSON-envelope helper convention with the existing lens verdict invariant.

### Decision 2: Where the gate's logic lives (JS vs Python)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Implement AC-extraction / coverage / dangling-ref / decision inline in `qrspi-batch.js` | No new file | Violates the enforced Functional-Core/Imperative-Shell rule; `qrspi-batch.js` is not unit-testable (ref: Discovered Patterns, Q12) |
| B | Pure Python `qrspi_verify_artifact.py` + `_test.py`; JS gate is a thin shell-out + envelope parse | Matches every existing helper; unit-tested; satisfies AC6's "tested pure-Python helper, thin JS gate" | New script + fixture wiring |

**Recommendation:** Option B
**Rationale:** "All deterministic logic lives in unit-tested `scripts/*.py`; `qrspi-batch.js` is a logic-starved shell" is the documented, enforced architecture (ref: Discovered Patterns, Q12), and AC6 mandates exactly this split.
**NEW PATTERN?** No.

### Decision 3: Producer-side retry bound on verification failure

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Reuse the `CI-Revise-Attempt` trailer | Existing counter | Lives on a committed PR head; verification is pre-commit, so it is structurally unusable (ref: Q10) |
| B | Single-shot: a verification fail → `failTicket` immediately (no retry) | Simplest; reuses the existing `runPhase` failure contract | Loses the "enter a revise pass" intent of AC6; a fixable miss fails the whole ticket |
| C | Small in-`runPhase` bounded loop (produce → verify → re-produce up to N), then `failTicket` with a visible give-up flag | Honors AC6's revise intent; mirrors the cap-then-park precedent (`ciGaveUp`) | New in-memory attempt counter (no durable trailer needed pre-commit) |

**Recommendation:** Option C
**Rationale:** The producer pipeline is single-shot with no counter, and the only bounded-retry precedent is unusable pre-commit (ref: Q10). The cap-then-park-with-visible-give-up shape (`ciGaveUp`) is the documented model for a bounded loop; an in-memory bound suffices because verification runs before any commit (ref: Q10). The bound honors AC6's "enter a revise pass" intent; **on exhaustion the loop falls into the hard-block terminal path** (per OQ1, resolved): `failTicket` with `verifyFailed`, never a flagged advance — so Option C is Option B's `failTicket` contract wrapped in a small bounded retry, not a new terminal mechanism.
**Bound source (per OQ2, resolved):** a **hardcoded small default of `2`**, not a new config key. Verification is pre-commit, in-memory, and fast, so there is no demonstrated need to tune it per-project; YAGNI over mirroring `ciReviseCap` (which earns its config key only because it lives on a committed PR head across runs). Trivially promotable to a `.qrspi/config.json` key later if a real need appears.
**NEW PATTERN?** Yes — an in-loop producer-side bounded re-produce within `runPhase`. Justified because no pre-commit retry mechanism exists (ref: Q6, Q10); the durable-trailer pattern cannot apply before a commit exists.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Fidelity-only drift: the self-check rubber-stamps upstream traceability instead of validity (the RUS-77 failure mode the ticket forbids) | med | high | Author the agent prose to verify against real source (Read/Grep over REPO_ROOT) and self-consistency, NOT upstream-fidelity; fail closed ("a claim you cannot confirm → Open Question") per the RUS-82 lens (ref: Q5) |
| Shared-file restack conflict: `qrspi-batch.js` is concurrently edited by RUS-88/RUS-90 (different functions) | med | med | Sequence per the ticket constraint; confine edits to the `runPhase`/spawn-prompt seam; lands before RUS-90 which adopts this OQ format (ref: ticket Out of Scope) |
| Plan producer lacked ticket access; adding `TICKET_CONTENT_PATH` is a new spawn input that could be misread | low | med | Plumb the same resolver-staged `r.ticketContentPath` the design spawn already uses; cover the new spawn shape in a manual e2e run (ref: Q2, Q8) |
| "No signal present" misclassified as failure, breaking the additive/backward-compatible AC | low | high | Encode the distinction as an explicit `signal` envelope field (Decision 1), unit-test the tri-state including empty-findings/no-verifiable-signal → pass-through (ref: Q9) |
| Producer-side retry loops or stalls the batch | low | med | Small bounded loop with cap-then-`failTicket` + the visible `verifyFailed` flag (Decision 3); never advances on failure (ref: Q10, Q13) |
| Zero/malformed `## Acceptance Criteria` degrades silently or hard-fails | med | med | The core defines explicit zero/malformed behavior (treat as "no AC signal" → pass-through, surfaced as a finding/Open Question, not a crash) and unit-tests it (ref: Q8) |

## Open Questions

All four open questions were resolved by human review (2026-06-19) and folded into the ACs / Decision 3 / Delta above. None remain blocking; recorded here with their resolutions for traceability.

- OQ1 — **RESOLVED: hard block.** On verification failure after the retry bound is exhausted, `runPhase` returns `false` → `failTicket` (terminal-for-run, recompute next run) with the `verifyFailed` flag — **not** persist-with-findings-as-Open-Questions. AC6 ("does not persist; enters a revise pass") and the ticket's no-fabrication posture both demand fail-closed; a flagged advance would let an unverified artifact through. (Folded into AC6 + Decision 3.)
- OQ2 — **RESOLVED: hardcoded default of `2`, no new config key.** Verification is pre-commit, in-memory, and fast, so there is no demonstrated need to tune it per-project (YAGNI over mirroring `ciReviseCap`, which earns its key only by living on a committed PR head). Trivially promotable to a config key later. (Folded into Decision 3.) (ref: Q10)
- OQ3 — **RESOLVED: check directly against the plumbed ticket text.** The plan producer computes AC coverage against the newly-plumbed `TICKET_CONTENT_PATH`, not transitively via `design.md`. The input is already being plumbed; direct is strictly stronger (an AC the design dropped still surfaces as an unmapped-AC finding). (Folded into AC3.) (ref: Q8)
- OQ4 — **RESOLVED: out of scope; leave the stale prose.** Removing the stale FRAMING/N-select prose from `qrspi-design.md` is deferred to a separate follow-up ticket. It is unrelated to this ticket's ACs and the Risk Register flags active restack-conflict pressure on this shared file (concurrent RUS-88/RUS-90 edits), so the change surface is minimized. (Folded into Delta — `.claude/agents/qrspi-design.md`.)
