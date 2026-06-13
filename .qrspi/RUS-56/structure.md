# Structure Outline — qrspi critics 2/5: Stage 1 (Design) multi-lens critic panel + design edge critic

**Design basis:** design.md @ 2026-06-13T00:00:00Z
**Generated:** 2026-06-13T00:00:00Z
**Status:** draft

## New Types

- `LensVerdict { pass: bool, findings: list[str|{text, lens}] }` — one lens agent's reply, validated by the landed `parse_critic_verdict` (fail-closed: garbage ⇒ `{pass:false, findings:[]}`).
- `SynthesizedVerdict { pass: bool, findings: list }` — the single authoritative verdict for a round, produced by reducing M `LensVerdict`s: `pass` only if every lens passed; `findings` is the exact-string-deduped union, each finding optionally lens-tagged.
- `CriticConfig { lenses: list[str], maxRounds: int, upstream: str }` — JS object passed into `runPhase`'s optional trailing parameter; `lenses` defaults to the four-lens set, `maxRounds` defaults to 2, `upstream` is `'research'` for design. Built by `doDesign` from the `critics.design` config block (config value > JS default).

## Modified Types

- `runPhase(name, id, ...ctx)` — add optional trailing `criticConfig` parameter; guarded by `if (criticConfig)` so an absent value reproduces today's produce→persist behavior byte-for-byte (ref: design.md §Delta item c, §Desired End State).
- `.qrspi/config.json` schema — add optional `critics.design` block `{maxRounds: int, lenses: list[str]}` (ref: design.md §Delta, OQ3). Documented in `.qrspi/config.example.json`.

## Contracts

- `synthesize(verdicts: list[LensVerdict]) -> SynthesizedVerdict` (Python, `scripts/qrspi_critic_synthesize.py`) — all-pass-required-for-pass plus exact-string finding-union with optional lens-tag; no lens privileged (ref: OQ2). Empty/malformed lens entries are coerced via the existing fail-closed parser before reduction.
- `next_action(verdicts, round, max_rounds)` (Python, `scripts/qrspi_critic_loop.py`, ALREADY LANDED — unchanged) — consumes the per-round authoritative verdict list (last element wins), returns `converged` / `revise` / `cap_reached`. The panel loop appends each round's `synthesize(...)` output as the latest element.
- `parse_critic_verdict(raw) -> {pass, findings}` (Python, `scripts/qrspi_critic_loop.py`, ALREADY LANDED — unchanged) — per-lens fail-closed coercion, reused inside `synthesize` and at lens-reply ingestion.
- `compose_message(existing, body) -> str` (Python, `scripts/qrspi_pr_body.py`, ALREADY LANDED — unchanged) — splices a body between commit subject and trailers; reused by the new design/plan body helper.
- `qrspi_critic_body.py` CLI — reads a staged residual-findings file + the finalize commit message, calls `compose_message`, emits the spliced message for the design finalize commit (ref: Q9 Path A, Decision 4).
- `runCriticPanelLoop(name, id, criticConfig, ...ctx)` (JS, `qrspi-batch.js`) — per round: `parallel()`-fan-out the `criticConfig.lenses` lens `agent()` thunks against the staged `stg(id,'design')` + persisted upstream `art(...)` paths; ingest each reply through `parse_critic_verdict`; call `synthesize`; append to the verdict list; call `next_action`; on `revise` re-spawn the design agent with the synthesized findings (rewriting `stg(id,'design')` in place, never emptying it); break on `converged`; on `cap_reached` stage residual findings and return success. Runs entirely inside the produce→persist window before the single `persistArtifact`.
- `CRITIC_VERDICT_SCHEMA` (JS constant, `qrspi-batch.js`) — the `{pass, findings}` shape handed to lens agents as their required output contract.

## Slice 1: Pure synthesis + body helpers (Python firewall)

**Goal:** The two new pure Python helpers exist and pass their stdlib tests in isolation — `synthesize` reduces M lens verdicts to one authoritative verdict, and `qrspi_critic_body.py` splices residual findings into a commit message. These are independently testable with literal dict/string fixtures before any JS glue exists.
**Files touched:**

- ✨ `scripts/qrspi_critic_synthesize.py` — `synthesize(verdicts) -> {pass, findings}`: all-pass-for-pass, exact-string-deduped finding-union, optional lens-tag; coerces each entry through `parse_critic_verdict` first (ref: §Delta, OQ2).
- ✨ `scripts/qrspi_critic_synthesize_test.py` — `check()`-style sibling: all-pass, one-fail, duplicate-across-lenses, empty/malformed-lens fixtures (ref: §Delta, Q12).
- ✨ `scripts/qrspi_critic_body.py` — CLI splicing a staged residual-findings file into a finalize commit message via `compose_message` (ref: Decision 4, Q9 Path A).
- ✨ `scripts/qrspi_critic_body_test.py` — `check()`-style sibling: empty findings, single finding, multi-line findings, idempotent re-splice.
**Verification:**
- [ ] `python3 scripts/qrspi_critic_synthesize_test.py` exits 0 (all fixtures pass).
- [ ] `python3 scripts/qrspi_critic_body_test.py` exits 0.
- [ ] A one-fail fixture yields `pass:false` and the deduped union of findings; an all-pass fixture yields `pass:true`.
**Context cost:** S
**Depends on:** none

## Slice 2: Lens agent prompts + verdict schema

**Goal:** The four design lens prompts and the JS verdict-schema constant exist and emit a `parse_critic_verdict`-valid `{pass, findings}` reply against a design rubric. Verifiable by spawning a single lens against a sample design and confirming the reply parses.
**Files touched:**

- ✨ `.claude/agents/qrspi-design-critic.md` (or four per-lens prompt files) — completeness, internal consistency, ticket/research alignment (edge), simplicity; each receives `TICKET_CONTENT_PATH`, `RESEARCH_PATH`, `QUESTIONS_PATH` (persisted `art(...)`) plus staged `stg(id,'design')` as rubric, emits `{pass, findings}` (ref: §Delta, AC2, OQ1).
- ⚠️ `.claude/workflows/qrspi-batch.js` — add `CRITIC_VERDICT_SCHEMA` constant (the `{pass, findings}` lens output contract) only; no loop wiring yet (ref: §Delta item a).
**Verification:**
- [ ] A single lens agent spawned against a sample `design.md` returns text that `parse_critic_verdict` accepts (pass through `python3 -c` ingest check).
- [ ] Each of the four lenses references the correct upstream inputs (ticket/research/questions + design) in its prompt.
**Context cost:** M
**Depends on:** Slice 1 (verdict shape that `synthesize` consumes)

## Slice 3: Panel loop + doDesign wiring + config + PR-body splice

**Goal:** `doDesign` runs the M-lens panel → synthesize → revise ≤ maxRounds inside the design produce→persist window, breaking on round-1 pass, surfacing cap-reached residuals into the design PR body, with the lens set / maxRounds config-overridable and absent-config preserving today's behavior. This is the end-to-end path: a design run now exercises the panel.
**Files touched:**

- ⚠️ `.claude/workflows/qrspi-batch.js` — (b) add `runCriticPanelLoop` (parallel lens fan-out → `parse_critic_verdict` ingest → `synthesize` → `next_action` → re-spawn design agent on `revise`, in-place staged rewrite); (c) extend `runPhase` with optional trailing `criticConfig` guarded by `if (criticConfig)`; (d) `doDesign` reads the `critics.design` config block and passes `criticConfig {lenses, maxRounds:2, upstream:'research'}` (config > JS default; unknown lenses dropped with `log` warning; empty set falls back to default four per OQ3); (e) splice cap-reached residuals into the design finalize commit via `qrspi_critic_body.py`; (f) `log(...)` per-round pass/fail/cap + `res.summary` fold (ref: §Delta items b–f, AC1/3/4, Q14).
- ⚠️ `.qrspi/config.example.json` — add optional `critics.design` block documenting the override surface (ref: §Delta, OQ3).
**Verification:**
- [ ] End-to-end design run with a deliberately-flawed design triggers ≥1 revise round, then converges or caps; `res.summary` shows per-round pass/fail (manual e2e — JS glue is not unit-tested per Q12).
- [ ] A design that passes all four lenses on round 0 produces zero revise spawns (AC3).
- [ ] A capped run writes residual findings into the design PR body (inspect the submitted PR / staged commit message) (AC4).
- [ ] `doDesign` with no `critics.design` config key reproduces today's single-persist design behavior (opt-in seam; AC §Desired End State).
- [ ] A `critics.design` block in `.qrspi/config.json` overrides `maxRounds` / `lenses` for the run (OQ3).
**Context cost:** L
**Depends on:** Slice 1 (synthesize/body helpers), Slice 2 (lens prompts + `CRITIC_VERDICT_SCHEMA`)

---

## Unverified Assumptions

- **`parallel()` and `agent()` runner primitives are available to `runCriticPanelLoop` in `qrspi-batch.js`.** The design asserts `parallel()` is "already in the runner vocabulary" (ref: Q10, Decision 2) but the structure phase cannot read the codebase to confirm the exact signature/import. Plan phase must verify the call shape before wiring the fan-out.
- **~~The existing config-loading path in `doDesign` exposes arbitrary nested blocks like `critics.design`.~~ RESOLVED — no such path exists; the plan reads it explicitly.** Verified during plan review: `scripts/qrspi_config.py --key <KEY>` resolves a **single top-level** key only (`select_value` returns `config.get(key)`, no dot-path — `--key critics.design` → `None`), and the JS consumer `parseConfigEnvelope` (qrspi-batch.js:324) **hard-rejects any non-string value**, so nothing currently surfaces a nested block. The plan's Step 21 therefore uses Option A (no `qrspi_config.py` change): read the **top-level** `critics` key — which already round-trips as `{"ok":true,"value":{"design":{…}}}` — and parse `.design` with a new **lenient** `parseCriticConfig` in qrspi-batch.js (separate from the string-only `parseConfigEnvelope`). Config > JS default precedence; absent block ⇒ `criticConfig` undefined ⇒ today's behavior.
- **The RUS-55 foundation modules (`scripts/qrspi_critic_loop.py` with `next_action` + `parse_critic_verdict`, and `scripts/qrspi_pr_body.py` with `compose_message`) are present in this worktree as described.** The design states the Python module and `compose_message` are landed while the JS glue is NOT (ref: Q1/Q3/Q4, Risk Register row 1). Slices 1 and 3 depend on these signatures being exactly as documented; the plan must confirm before building.
- **Acceptance criterion 5 (eval before/after score) is a documentation deliverable, not executable scope.** Per OQ4 the eval harness is a ~0 non-functional placeholder, so no slice produces a measured score; the repeatable procedure is documented instead (likely folded into the PR summary / a doc). No code slice covers it — flagged so planning does not allocate an implementation slice to an unrunnable measurement.
- **Lens prompt packaging (one `qrspi-design-critic.md` parameterized by lens vs. four separate prompt files).** The design writes "`.claude/agents/qrspi-design-critic.md` (or M lens prompts)" — the exact file layout is left open and must be decided in plan/implementation.
