# Design — qrspi critics 1/5: edge-critic loop primitive wired into runPhase

**Ticket:** RUS-55
**Research basis:** research.md @ /workspaces/qrspi/.worktrees/RUS-55/.qrspi/RUS-55/research.md
**Generated:** 2026-06-12T00:00:00Z
**Status:** draft

## Current State

`runPhase(name, agentType, prompt, existing, id, phaseLabel)` is the single per-artifact pipeline for design/plan phases, with exactly four steps: resume short-circuit, produce via `agent()`, persist gate via `persistArtifact`, then log+return a bare boolean (ref: Q1, Q9). No artifact is passed in memory between phases — a phase agent writes to a token-free staging path `stg(id,name)` (`/tmp/phase-stage/<id>/<name>.md`) and `persistArtifact` deterministically moves it to the canonical `art(wd,id,name)` path under `.worktrees/<id>/.qrspi/<id>/` (ref: Q1, Q2). Downstream phases read upstream artifacts back from the canonical `art(...)` path because the upstream persist gate already ran (ref: Q2).

The persist gate runs AFTER the produce `agent()` call and verifies the staged file exists and is non-empty before `shutil.move` removes it from staging (ref: Q3). So between produce and persist, the just-written artifact still lives at `stg(id,name)` and has not yet been moved (ref: Q2, Q3).

`agent(prompt, options)` is a runner-injected primitive; options carry `label`, `phase`, optional `agentType` (resolves to a `.claude/agents/<type>.md` file by its `name:` frontmatter), and optional `schema` (a JS-object JSON-Schema; present ⇒ parsed object return, absent ⇒ plain-string return) (ref: Q4, Q5). `parallel()` runs thunks concurrently; `pipeline()` is referenced in vocabulary but never called in this file (ref: Q4). Typed agents are Markdown files in `.claude/agents/` registered purely by file presence plus their `name:` field — there is no central manifest, and the `.md` files declare no StructuredOutput schema themselves (ref: Q5).

There is no declarative per-phase config table — the phase→agent→template→artifact mapping is imperative and inlined as positional `runPhase(...)` calls inside `doDesign`/`doPlan`; `meta.phases` is descriptive UX metadata only (ref: Q7). Implementation slices bypass `runPhase` entirely, spawning `agent({agentType:'qrspi-implement'})` directly (ref: Q7, Pattern 8).

For design/plan the PR body equals the branch commit message (Graphite seeds it at creation; `gt submit` has no body flag), composed as a bare commit subject with no multi-line body; only the implementation phase builds a rich body via `scripts/qrspi_pr_body.py` (ref: Q8).

All existing loops are bounded by a finite collection — there is no `while(true)` or round-cap counter anywhere; multi-pass agentic work is made loop-safe ACROSS runs by a state flip, not by an in-process counter (ref: Q10, Pattern 6). Malformed agent output is handled two ways: schema'd calls return falsy/`null` and callers guard `if (!x || !x.ok)`; plain-text calls run `extractJsonObject` + a bespoke `parse*Envelope` that NEVER throws and fails closed to `{ok:false}`/`incomplete`/`wait` (ref: Q6, Q11, Pattern 5). The weak local model has a documented failure of stalling against StructuredOutput by emitting empty `{}`, which is why several workers were migrated to the plain-text path (ref: Q6, Q11, Inconsistency 3).

The JS in `qrspi-batch.js` is NOT unit-tested anywhere — no `package.json`, no JS test runner; orchestration is verified by manual e2e only (ref: Q12). The established testability strategy is to push pure logic into a `scripts/qrspi_*.py` module with a stdlib-only assert-based `_test.py` sibling (22 exist) fed hand-built fixture dicts; there is no precedent for stubbing `agent()` (ref: Q12, Q13, Pattern 7). `runPhase` reports via `log(...)` lines and a bare boolean; richer per-step signal is folded into `log` and the ticket-level `res.summary` (ref: Q14).

## Desired End State

Each acceptance criterion maps to concrete behavior:

- **AC1 — configured critic runs produce→critique→revise ≤ maxRounds; no critic ⇒ byte-for-byte unchanged.** `runPhase` gains an OPTIONAL trailing `criticConfig` parameter. Between the produce success and the persist gate, `if (criticConfig)` guards a new `runCriticLoop` call. With `criticConfig` absent (all current call sites), JS supplies `undefined`, the guard is false, and the four current statements execute verbatim (ref: Q9).
- **AC2 — maxRounds enforced; non-converging critic terminates and surfaces findings into the PR.** `runCriticLoop` uses a counter-driven `for (let round = 0; round < maxRounds; round++)` that breaks on all-pass; `maxRounds` is read **per phase** from `criticConfig.maxRounds ?? 2` (per-phase configurable, default 2 when omitted — see OQ4). On cap-reached the loop returns the residual findings, the loop still returns success so the phase proceeds to finalize, and the findings are threaded to the design/plan finalize commit body (ref: Q8, Q10, Q14).
- **AC3 — critic receives upstream artifact(s) + produced artifact; findings schema-validated.** The critic agent is handed the upstream anchor read from `art(wd,id,'<upstream>.md')` and the produced artifact read from the staging path `stg(id,name)` (the only place the just-produced artifact lives pre-persist). Its `{pass, findings}` reply is validated by a pure parser that fails closed (ref: Q2, Q6, Q11).
- **AC4 — all-pass on round 1 ⇒ single critic call, no revise.** The loop critiques first; if `pass` is true it breaks before any revise call, so exactly one critic agent runs and zero revise agents (ref: Q10).

The critic contract is edge-oriented: it evaluates the produced artifact as a faithful derivation of its upstream input, with the upstream artifact as the rubric anchor (ticket "review the EDGE not the node").

## Delta

**New files:**

- `scripts/qrspi_critic_loop.py` — pure decision module. Exposes a function (e.g. `next_action(verdicts, round, max_rounds)`) returning `{action: 'converged'|'revise'|'cap_reached', residual_findings: [...]}`, and a `parse_critic_verdict(text)` that fails closed to `{pass:false}` on malformation. No agent/IO coupling (ref: Q12, Q13, Pattern 7).
- `scripts/qrspi_critic_loop_test.py` — stdlib-only assert-based sibling covering: pass-first-round (no revise), fail→revise→pass, fail→cap→surface, and malformed-verdict-fails-closed (ref: ticket Tests, Q12, Q13).
- `.claude/agents/qrspi-critic.md` — new typed agent, `name: qrspi-critic`, `tools: Read` (plus `Write` only if it stages a verdict file). Body is the edge-critic system prompt consuming `UPSTREAM_PATH`, `ARTIFACT_PATH`, `RUBRIC`/phase inputs (ref: Q5).
- `.claude/skills/qrspi-critic/` — slash-command wrapper per the convention (ref: Q5).

**Modified files:**

- `.claude/workflows/qrspi-batch.js`:
  - Add `CRITIC_VERDICT_SCHEMA` in the schemas section (the ticket-specified StructuredOutput contract; see Decision 2) (ref: Q6).
  - Add a `runCriticLoop(...)` JS function: the agent-spawn glue that reads upstream + produced paths, spawns critic(s) and reviser, and delegates the converge/continue/cap decision to the python module's parsed output (ref: Q4, Pattern 1).
  - Add OPTIONAL trailing `criticConfig` param to `runPhase`; insert the guarded loop between produce-success and persist (ref: Q1, Q7, Q9).
  - In `doDesign`/`doPlan`, pass a `criticConfig` for the design and plan artifacts — each carrying its own `maxRounds` (per-phase configurable, default 2 when omitted; see OQ4) — and thread residual findings into the finalize commit body (ref: Q7, Q8).
  - Surface critic rounds / per-round pass-fail / cap-reached via `log(...)` and fold a summary into `res.summary` (ref: Q14).

**No DB/middleware changes** — this is orchestration-only.

## Pattern Decisions

### Decision 1: Where the critic loop is inserted

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Inside `runPhase`, between produce and persist, guarded by `if (criticConfig)` | Per-artifact, uniform; reuses the staging-path-is-still-present window; zero-change for no-critic phases via undefined trailing arg | Critic sees one artifact at a time, not the full phase set |
| B | Inside each `doX` after all `runPhase` calls, before finalize | Sees the full produced artifact set at once | Must re-locate each staged file; not uniform; touches every action body |

**Recommendation:** Option A
**Rationale:** Matches the ticket's "wires into `runPhase` as an OPTIONAL pre-finalize step." `runPhase` is the single choke point all design/plan artifacts flow through (ref: Q1, Q7), and the produced artifact is still at `stg(id,name)` exactly in this window (ref: Q2, Q3). The `if (criticConfig)`/undefined-trailing-arg guard is an established idiom for optional behavior (ref: Q9), guaranteeing byte-for-byte unchanged no-critic phases.
**NEW PATTERN?** No — extends the existing `runPhase` choke point with the existing optional-guard idiom.

### Decision 2: Critic findings return mode (schema vs plain-text)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | `agent({schema: CRITIC_VERDICT_SCHEMA})` — runner-validated object | Declarative; matches phase/persist/comment workers | Weak local model documented to stall on StructuredOutput, emitting empty `{}` and looping (ref: Q6, Q11) |
| B | Plain-text return + `extractJsonObject` + new `parseCriticEnvelope`/python `parse_critic_verdict`, fail-closed to `{pass:false}` | Survives the weak-model stall; matches resolve/land-verify/cleanup workers; fails closed | More hand-written validation; one more bespoke parser |

**Recommendation:** Option A — `agent({schema: CRITIC_VERDICT_SCHEMA})`, per the ticket.
**Rationale:** The ticket's Approach is explicit: the critic agent-type contract is "**frontier model, StructuredOutput schema**" with output `{ pass: bool, findings: [...] }`. The weak-model StructuredOutput stall (ref: Q6, Q11) is the documented hazard for workers that *may* run on the weak local model; it does not apply to an agent the ticket pins to the frontier model. Choosing A keeps the critic verdict contract declarative and runner-validated as specified, and removes the design-vs-ticket drift of recommending the plain-text path against the ticket's stated contract. The converge/continue/cap *decision* still lives in the testable `qrspi_critic_loop.py` module (Decision 3, ref: Q12, Q13) — that testability is independent of the verdict return mode, since the loop module is fed the already-parsed `{pass, findings}` verdicts; the runner's schema validation replaces the bespoke fail-closed parser at the boundary. `parse_critic_verdict` is retained only as a defensive fail-closed backstop (treat an unreadable/empty verdict as NOT-passed; ref: Q11) for the residual weak-model-stall risk, not as the primary return path.
**NEW PATTERN?** No — uses the established schema'd-agent pattern (phase/persist/comment workers, ref: Q6).

### Decision 3: Round-cap / termination construct

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Counter-driven `for (let round = 0; round < maxRounds; round++)`, break on all-pass | Finite, deterministic, terminates by construction; `maxRounds` per-phase via `criticConfig.maxRounds ?? 2` | First in-process bounded-retry construct in the file (no precedent to copy) |
| B | Reuse the across-runs state-flip loop-safety (one step per run) | Matches existing loop-safety pattern | Wrong granularity — critic must converge WITHIN one `runPhase` call, not across batch runs (ref: Q10) |

**Recommendation:** Option A
**Rationale:** There is no in-process retry precedent; the critic must converge within a single `runPhase` invocation, so the across-runs flip (Pattern 6) does not apply (ref: Q10). A finite counter with a `pass`-break is the minimal construct that guarantees termination.
**NEW PATTERN?** Yes — the first in-process bounded-retry loop in `qrspi-batch.js`. Justified because no existing pattern converges work within a single call; existing loops bound by finite collections and the across-runs flip are both the wrong granularity (ref: Q10, Pattern 6).

### Decision 4: Surfacing residual findings into the design/plan PR body

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Write residual findings to a token-free staged file; splice into the finalize commit message (mirror `qrspi_pr_body.py`) | Avoids shell-quoting hazards; mirrors the proven implementation-body pattern | New design/plan body machinery (none exists today) |
| B | Splice findings inline into the finalize prompt's commit-subject instruction | No new file | Multi-line findings in a heredoc subject risk shell-quoting breakage (ref: Q8) |

**Recommendation:** Option A
**Rationale:** Design/plan have no body mechanism today — the body is a bare commit subject (ref: Q8, Inconsistency 4). The implementation path writes findings to a FILE precisely to dodge worker command-line quoting; mirroring that (token-free staged file per Fix A, Pattern 3) is the safer extension.
**NEW PATTERN?** No (mechanism-wise) — mirrors `qrspi_pr_body.py`'s file-splice; but it is the first design/plan body, so a small new helper or prompt-fed staged body is required (ref: Inconsistency 4).

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Critic runs on the weak model and stalls against StructuredOutput (empty `{}`, loops) | low | high | Ticket pins the critic to the frontier model (Decision 2 Option A), so the stall is out-of-contract; defensive backstop: `parse_critic_verdict` fails closed (empty/unreadable verdict ⇒ NOT-passed), and a non-converging round caps out (Decision 3) rather than looping (ref: Q6, Q11) |
| Critic empties/deletes the staged artifact, converting persist into `ok:false` and stopping the ticket | low | high | Critic/reviser must rewrite `stg(id,name)` in place and never empty it; persist's non-empty check is the backstop; reviser writes a full artifact (ref: Q3) |
| New in-process loop fails to terminate (no precedent to copy) | low | high | Counter-bounded `for` with a finite per-phase `maxRounds` (`criticConfig.maxRounds ?? 2`); cap-reached returns success and surfaces findings, never loops (Decision 3; ref: Q10) |
| Malformed/garbled critic verdict silently marks artifact converged | med | med | Fail closed: an unreadable verdict is treated as NOT-passed, mirroring `parseLandVerdict`→`incomplete` (ref: Q11) |
| `runCriticLoop` JS glue is untestable (no JS test harness) | high | med | Extract converge/continue/cap decision into `qrspi_critic_loop.py` with `_test.py`; keep only agent-spawn glue in untested JS; verify e2e on one phase (ref: Q12, Q13) |
| A non-critic phase's behavior drifts from byte-for-byte unchanged | low | high | Trailing optional `criticConfig` (undefined for existing call sites) + `if (criticConfig)` guard; assert all 6 existing call sites untouched (ref: Q9) |

## Open Questions

- ~~OQ1~~ (RESOLVED): The ticket's Approach pins the critic agent-type to the **frontier model with a StructuredOutput schema**, so this is not open — Decision 2 follows it (Option A, schema'd return). `parse_critic_verdict` is kept only as a fail-closed backstop for the residual weak-model-stall risk.
- ~~OQ2~~ (RESOLVED — reviewer: "single"): This primitive ticket supports a **single critic agent per edge**. The ticket's "one or more critic agents" wording is satisfied by the single-critic case here; multi-critic fan-out (if ever needed) is deferred to the per-phase tickets (2/5..5/5), as are the phase-specific rubrics. Concretely this pins `runCriticLoop` to spawn exactly one critic agent per round (not a `parallel()` fan-out), simplifying Decision 2's verdict handling to one `{pass, findings}` reply per round with no cross-critic aggregation.
- ~~OQ3~~ (RESOLVED — reviewer: "pr body"): Cap-reached residual findings live **only in the PR body**, not Linear. This repo's lifecycle (`.claude/CLAUDE.md`, `docs/qrspi-pr-gated-lifecycle-design.md`) makes **PR review state — not Linear status — the authority for advancement**; Linear is a best-effort reporting projection only (a failed Linear write must never block work). Routing residual findings through the PR body keeps the convergence signal on the authoritative surface the reviewer gates on and avoids coupling it to a non-load-bearing write path. Decision 4 already commits to splicing residual findings into the design/plan finalize commit body (which seeds the PR description), so the PR-body-only path is the consistent choice — there is no Linear write for residual findings.
- ~~OQ4~~ (RESOLVED — reviewer: "per phase configurable"): `maxRounds` is **per-phase configurable via `criticConfig`**, not a fixed constant. Each `criticConfig` carries its own `maxRounds` (so `doDesign` and `doPlan` may set different caps), with a default of `2` applied only when a `criticConfig` omits the field. Concretely: `runCriticLoop` reads the cap from `criticConfig.maxRounds ?? 2`, and `runPhase` forwards the whole `criticConfig` (including its `maxRounds`) through to the loop — there is no module-level `maxRounds` constant.
