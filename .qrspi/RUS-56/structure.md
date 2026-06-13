# Structure Outline — qrspi critics 2/5: Stage 1 (Design) multi-lens critic panel + design edge critic

**Design basis:** design.md @ 2026-06-13T00:00:00Z
**Generated:** 2026-06-13 (rebuilt against current `main`)
**Status:** draft

## Reconciliation with RUS-55 (landed on `main`) — READ FIRST

The design.md was authored in a worktree where RUS-55 Slice 3's JS glue was **unlanded**, so it
specifies "build the orchestration seam itself." That premise is now **false**: RUS-55 landed the
full single-critic seam on `main` (commit `8028105`). This structure is therefore re-derived
against current `main`, preserving the design's **intent** (a configurable multi-lens design-phase
panel that surfaces residual findings into the design PR body) while **reusing** everything RUS-55
already shipped instead of rebuilding (and colliding with) it.

**Already landed on `main` — REUSED unchanged, NOT recreated:**

| Symbol / file | Where | Reused as |
|---|---|---|
| `CRITIC_VERDICT_SCHEMA` | `qrspi-batch.js:416` | the `{pass, findings}` lens output contract — **not re-added** |
| `runPhase(..., criticConfig)` | `qrspi-batch.js:611` | optional 7th param already present — **not re-added** |
| `runCriticLoop(name,id,criticConfig)` | `qrspi-batch.js:501` | the **single-critic** sibling kept for the plan phase; the panel is a new peer function |
| `next_action(verdicts, round, max_rounds)` | `scripts/qrspi_critic_loop.py` | loop decision — unchanged |
| `parse_critic_verdict(raw)` | `scripts/qrspi_critic_loop.py` | per-lens fail-closed coercion — unchanged |
| `compose_message(existing, body)` | `scripts/qrspi_pr_body.py` | body splice — unchanged |
| `qrspi_critic_body.py` + `criticBodyStep` | `scripts/`, `qrspi-batch.js:594` | residual-findings → PR body — **reused; RUS-56 creates NO new body splicer** (this removes the RUS-55 collision) |
| `doDesign` design-phase critic | `qrspi-batch.js:~782` | already runs a single edge-critic anchored on `research.md` and splices residuals via `criticBodyStep` — RUS-56 **swaps the single critic for the panel**, leaving the residual/PR-body flow intact |

**Net new scope (the genuine delta this ticket adds):** a pure `synthesize` reducer, four design
lens prompts, a parallel `runCriticPanelLoop` peer to `runCriticLoop`, and a config-overridable
`critics.design` block read by `doDesign`. Nothing else.

## New Types

- `LensVerdict { pass: bool, findings: list[str|{text, lens}] }` — one lens agent's reply, validated by the landed `parse_critic_verdict` (fail-closed: garbage ⇒ `{pass:false, findings:[]}`).
- `SynthesizedVerdict { pass: bool, findings: list }` — the single authoritative verdict for a round, produced by reducing M `LensVerdict`s: `pass` only if every lens passed; `findings` is the exact-string-deduped union, each finding optionally lens-tagged.
- `CriticConfig` (extended) — the JS object passed as `runPhase`'s existing optional trailing param. RUS-55 uses `{ upstreamPath, maxRounds }` (single critic). RUS-56 adds an optional `lenses: list[str]` field; **its presence is the panel switch**: `lenses?.length` ⇒ panel, absent/empty ⇒ today's single critic. Built by `doDesign` from the `critics.design` config block (config value > JS default).

## Modified Types

- `runPhase(name, agentType, prompt, existing, id, phaseLabel, criticConfig)` — **signature unchanged** (the `criticConfig` 7th param already exists, `qrspi-batch.js:611`). Only its internal `if (criticConfig)` branch changes: dispatch to `runCriticPanelLoop` when `criticConfig.lenses?.length`, else the existing `runCriticLoop`. Absent `criticConfig` ⇒ byte-for-byte today's behavior (every non-design caller).
- `.qrspi/config.json` schema — add optional top-level `critics` key with a `design` block `{maxRounds: int, lenses: list[str]}` (ref: design.md §Delta, OQ3). Documented in `.qrspi/config.example.json`.

## Contracts

- `synthesize(verdicts: list[LensVerdict]) -> SynthesizedVerdict` (Python, **NEW** `scripts/qrspi_critic_synthesize.py`) — all-pass-required-for-pass plus exact-string finding-union with optional lens-tag; no lens privileged (ref: OQ2). Each entry coerced via the landed `parse_critic_verdict` before reduction.
- `next_action(verdicts, round, max_rounds)` (Python, `scripts/qrspi_critic_loop.py`, **LANDED — unchanged**) — consumes the per-round authoritative verdict list (last element wins), returns `converged` / `revise` / `cap_reached`. The panel appends each round's `synthesize(...)` output as the latest element.
- `parse_critic_verdict(raw) -> {pass, findings}` (Python, `scripts/qrspi_critic_loop.py`, **LANDED — unchanged**) — per-lens fail-closed coercion, reused inside `synthesize` and at lens-reply ingestion.
- `qrspi_critic_body.py` + `criticBodyStep(id, phase, findings, wd)` (`scripts/` + `qrspi-batch.js:594`, **LANDED — unchanged, REUSED**) — already splices residual findings into the design finalize commit body. The panel writes its synthesized residuals onto `criticConfig.residualFindings` exactly as the single critic does, so this flow needs **no change**. RUS-56 creates no new body splicer.
- `runCriticPanelLoop(name, id, criticConfig)` (JS, **NEW** in `qrspi-batch.js`) — a parallel peer to the landed `runCriticLoop`. Per round: `parallel()`-fan-out the `criticConfig.lenses` lens `agent()` thunks against the staged `stg(id,'design')` + persisted upstream `art(...)` paths; ingest each reply through `parse_critic_verdict`; call `synthesize`; append to the verdict list; call `next_action`; on `revise` re-spawn the design agent with the synthesized findings (rewriting `stg(id,'design')` in place, never emptying it); break on `converged`; on `cap_reached` set `residualFindings` and return success. Returns the same `{ residualFindings }` shape as `runCriticLoop` so `runPhase`'s existing write-back is unchanged. Runs entirely inside the produce→persist window before the single `persistArtifact`.
- `parseCriticConfig(text) -> {design?: object}` (JS, **NEW** lenient parser in `qrspi-batch.js`) — separate from the string-only `parseConfigEnvelope`. Extracts the `qrspi_config.py --key critics` envelope, accepts an **object** value, returns `value.design` (object or `undefined`); a missing/garbled/`ok:false` envelope ⇒ `undefined` (opt-in seam stays off).

## Slice 1: Pure synthesis helper (Python firewall)

**Goal:** The new pure `synthesize` reducer exists and passes its stdlib test in isolation — reduces M lens verdicts to one authoritative verdict, independently testable with literal dict/string fixtures before any JS glue exists. (RUS-55's `qrspi_critic_body.py` is **already landed and reused** — this slice no longer creates it.)
**Files touched:**

- ✨ `scripts/qrspi_critic_synthesize.py` — `synthesize(verdicts) -> {pass, findings}`: all-pass-for-pass, exact-string-deduped finding-union (first-seen order), optional lens-tag; coerces each entry through the landed `parse_critic_verdict` first (ref: §Delta, OQ2).
- ✨ `scripts/qrspi_critic_synthesize_test.py` — `check()`-style sibling: all-pass, one-fail, duplicate-across-lenses, empty/malformed-lens fixtures (ref: §Delta, Q12).
**Verification:**
- [ ] `python3 scripts/qrspi_critic_synthesize_test.py` exits 0 (all fixtures pass).
- [ ] A one-fail fixture yields `pass:false` and the deduped union of findings; an all-pass fixture yields `pass:true`.
- [ ] `synthesize` imports and reuses the landed `parse_critic_verdict` (no re-implemented coercion).
**Context cost:** S
**Depends on:** none (reuses landed `parse_critic_verdict`)

## Slice 2: Lens agent prompts

**Goal:** The four design lens prompts exist and emit a `parse_critic_verdict`-valid `{pass, findings}` reply against a design rubric. Verifiable by spawning a single lens against a sample design and confirming the reply parses. (`CRITIC_VERDICT_SCHEMA` is **already landed** at `qrspi-batch.js:416` and reused — this slice adds **no** JS constant.)
**Files touched:**

- ✨ Four per-lens prompt files under `.claude/agents/` (completeness, internal consistency, ticket/research alignment (edge), simplicity); each receives `TICKET_CONTENT_PATH`, `RESEARCH_PATH`, `QUESTIONS_PATH` (persisted `art(...)`) plus staged `stg(id,'design')` as rubric, emits `{pass, findings}` conforming to the landed `CRITIC_VERDICT_SCHEMA` (ref: §Delta, AC2, OQ1).
**Verification:**
- [ ] A single lens agent spawned against a sample `design.md` returns text that the landed `parse_critic_verdict` accepts (`python3 -c` ingest probe).
- [ ] Each of the four lenses references the correct upstream inputs (ticket/research/questions + staged design) in its prompt.
- [ ] No new `CRITIC_VERDICT_SCHEMA` was added — the landed constant is referenced.
**Context cost:** M
**Depends on:** Slice 1 (verdict shape that `synthesize` consumes)

## Slice 3: Panel loop + doDesign rewiring + config

**Goal:** `doDesign`'s design phase runs the M-lens panel → synthesize → revise ≤ maxRounds (replacing today's single edge-critic) inside the produce→persist window, breaking on round-1 pass, surfacing cap-reached residuals into the design PR body **via the landed `criticBodyStep`**, with the lens set / maxRounds config-overridable and absent-config preserving today's single-critic behavior.
**Files touched:**

- ⚠️ `.claude/workflows/qrspi-batch.js` —
  (a) add `runCriticPanelLoop(name, id, criticConfig)` (parallel lens fan-out → `parse_critic_verdict` ingest → `synthesize` → `next_action` → re-spawn design agent on `revise`, in-place staged rewrite; returns `{residualFindings}`);
  (b) in `runPhase`'s existing `if (criticConfig)` branch, **dispatch**: `criticConfig.lenses?.length ? runCriticPanelLoop(...) : runCriticLoop(...)` — no signature change, single-critic path unchanged;
  (c) add the lenient `parseCriticConfig`;
  (d) in `doDesign`, build the design `criticConfig` from the `critics.design` config block (config > JS default `maxRounds:2` / default four lenses; unknown lenses dropped with `log` warning; empty set falls back to the four per OQ3) **replacing** the hard-coded `const designCritic = { upstreamPath, maxRounds: 2 }` — keep `upstreamPath: art(wd,id,'research.md')`;
  (e) add `log(...)` per-round pass/fail/cap + a `res.summary` fold for the panel (ref: §Delta items b/d/f, Q14).
  **The residual→PR-body splice (designBodyStep/criticBodyStep) is UNCHANGED — reused as landed.**
- ⚠️ `.qrspi/config.example.json` — add an optional `critics.design` block documenting the override surface (ref: §Delta, OQ3).
**Verification:**
- [ ] End-to-end design run with a deliberately-flawed design triggers ≥1 revise round, then converges or caps; `res.summary` shows per-round pass/fail (manual e2e — JS glue is not unit-tested per Q12).
- [ ] A design that passes all four lenses on round 0 produces zero revise spawns (AC3).
- [ ] A capped run writes residual findings into the design PR body via the landed `criticBodyStep` (inspect the submitted PR / staged commit message) (AC4).
- [ ] `doDesign` with no `critics.design` config key falls back to a single-critic-equivalent (no `lenses`) so behavior matches today's design-phase critic (opt-in panel seam).
- [ ] A `critics.design` block in `.qrspi/config.json` overrides `maxRounds` / `lenses` for the run (OQ3).
- [ ] `python3 scripts/qrspi_critic_loop_test.py` and `python3 scripts/qrspi_pr_body_test.py` (landed RUS-55 siblings) still exit 0 — the reused contracts are intact.
**Context cost:** L
**Depends on:** Slice 1 (synthesize), Slice 2 (lens prompts)

---

## Unverified Assumptions

- **`parallel()` and `agent()` runner primitives are available to `runCriticPanelLoop`.** The landed `runCriticLoop` (`qrspi-batch.js:501`) already calls `agent(...)`; the panel additionally needs `parallel()` for the lens fan-out. Plan phase must confirm `parallel()`'s exact call shape before wiring (the design asserts it is "already in the runner vocabulary", ref: Q10/Decision 2).
- **`doDesign` currently passes `criticConfig` (RUS-55).** Verified on `main`: `doDesign` builds `const designCritic = { upstreamPath: art(wd,id,'research.md'), maxRounds: 2 }` and passes it as `runPhase`'s 7th arg, then splices `designCritic.residualFindings` via `criticBodyStep`. RUS-56 **modifies this existing object** to add `lenses` from config — it does not introduce the seam.
- **Config nested-block read mechanism (RESOLVED — single-top-level-key limitation).** `scripts/qrspi_config.py --key <KEY>` resolves a **single top-level** key only (`select_value` returns `config.get(key)`, no dot-path — `--key critics.design` → `None`), and the JS `parseConfigEnvelope` (`qrspi-batch.js:324`) **hard-rejects any non-string value**. So Slice 3 reads the **top-level** `critics` key (whose value round-trips as `{"ok":true,"value":{"design":{…}}}`) and parses `.design` with the new **lenient** `parseCriticConfig` — it does **not** modify `qrspi_config.py` and does **not** rely on `parseConfigEnvelope`.
- **Acceptance criterion 5 (eval before/after score) is a documentation deliverable, not executable scope** (per OQ4 — the eval harness is a ~0 non-functional placeholder). No slice produces a measured score; the repeatable procedure is documented in the PR summary. Flagged so planning allocates no implementation slice to an unrunnable measurement.
- **Lens prompt packaging (four separate prompt files vs. one parameterized agent).** The design writes "`.claude/agents/qrspi-design-critic.md` (or M lens prompts)" — exact file layout decided in plan/implementation; this structure assumes four separate prompt files for clarity.
