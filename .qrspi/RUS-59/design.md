# Design — Generation-side N-select for Design: N candidate designs → judge → synthesize

**Ticket:** RUS-59
**Research basis:** research.md @ 2026-06-13T00:00:00Z
**Generated:** 2026-06-13T00:00:00Z
**Status:** draft

## Current State

The Design phase runs exactly one design agent. `doDesign(t, r)` calls `runPhase('design', 'qrspi-design', prompt, …, designCritic)`, which spawns a single `qrspi-design` agent that writes one `design.md` to the token-free staging path `stg(id, 'design')` = `/tmp/phase-stage/<id>/design.md` (ref: Q1, Q2). The design prompt is built inline in `doDesign` and passes inputs as `KEY = value` lines; the agent must write exactly to the `OUTPUT_PATH` it receives (ref: Q2).

After the single produce call and before persist, `runPhase` runs the critic dispatch in the "pre-persist staging window": when `criticConfig` is present it calls `runCriticPanelLoop` (if `criticConfig.lenses?.length`) or `runCriticLoop` (ref: Q1). The panel reads the artifact from that same `stg(id, 'design')` path, revises it in place, and returns `{ ok, residualFindings, summary? }`; `runPhase` aborts the ticket on `!ok` (ref: Q3, Q4). Finally `persistArtifact` invokes `qrspi_persist.py`, which verifies the staged file is non-empty and moves it to the canonical worktree path — persist is the real per-phase success gate (ref: Q1, Q3).

There is no per-candidate framing mechanism and no N-candidate generation today (ref: Q2). The closest parallel-fan-out-with-per-run-variation pattern is the critic panel: `parallel(lenses.map(lens => async () => agent(...)))` collects an array of tagged `{ lens, verdict }` results, checks for any null (hard abort), and reduces via `synthesizeVerdicts` (ref: Q2, Q7). All critic/lens output is the binary `{pass, findings}` schema (`CRITIC_VERDICT_SCHEMA`); there is no numeric or comparative score anywhere (ref: Q5). The pure reduction logic lives in stdlib-only `scripts/qrspi_*.py` modules (`synthesize`, `next_action`) invoked from JS via worker agents because the JS sandbox cannot run python; the JS never re-derives the reduction (ref: Q8, Q11). These modules are unit-tested by `_test.py` siblings exercising stubbed inputs, fail-closed on empty/malformed (ref: Q11).

The design panel is gated by the optional top-level `critics` config key, read via `qrspi_config.py --key critics` (single-top-level-key only) and parsed by `parseCriticConfig`/`resolveDesignCritic` with config>default precedence; an absent or garbled block silently falls back to JS defaults and never gates the run (ref: Q6). The opt-in seam pattern is `if (criticConfig)` guard plus default-OFF parsing: an absent config means the existing path runs byte-for-byte unchanged with zero extra spend (ref: Q10). Quality-bearing fan-out is fail-closed — any null result aborts the ticket; only the non-gating Query sweep skips nulls (ref: Q9). The eval harness is a non-functional placeholder: it records raw outputs and per-trial token counts but never scores assertions and has no config-comparison/A-B mechanism; the orchestrator itself logs per-round panel activity via `log(...)` but has no token accounting at all (ref: Q12, Q13).

## Desired End State

**AC1 — Design phase can run N-candidate generation → judge → synthesize, producing one `design.md` that then enters the critic panel.** A new N-select stage splices into `runPhase` (or a design-specific helper called from `doDesign`) between the single produce `agent()` call and the `if (criticConfig)` critic block (ref: Q1). When enabled with N>1, it fans out N design-agent runs with distinct framing prompts to N distinct staging paths, a judge agent scores the candidates on a rubric AND identifies, per non-winning candidate, the specific strong ideas worth grafting into the winner, and a **two-step synthesis** lands the final design at exactly `stg(id, 'design')`: (1) a deterministic pure selector picks the highest-scoring candidate as the winning base and emits the judge-identified graft directives, then (2) a graft agent rewrites the winning base IN PLACE, merging in the named runner-up ideas — so the produced `design.md` is a *synthesized* artifact (winner + grafted runner-up ideas), not the verbatim winning candidate. The unchanged `runCriticPanelLoop` and `persistArtifact` then consume that single file as today (ref: Q3, Q4).

> **Ticket fidelity note (graft-synthesis).** The ticket's Desired behavior and Approach both require that "the winner is synthesized (grafting the best ideas from runners-up)" — i.e. the produced `design.md` merges strong ideas from the non-winning candidates, not merely the verbatim winner. An earlier draft of this design reduced that to pure single-candidate selection (the selector returned only `{winner, scores, synthesisNotes}` with `synthesisNotes` as metadata, never a content-merge). That narrowing is **rejected here**: this design restores an explicit content-merge graft step (the graft agent in AC1) as a distinct, mechanized phase, so the ticket-required graft-synthesis capability is preserved end to end. The pure selector still owns the deterministic *which-base-wins* decision; the graft *content-merge* is an LLM rewrite step (it cannot be a pure-python operation — merging prose ideas is generative, not deterministic), gated identically to the rest of N-select and only run when N>1.

**AC2 — Eval score reported to justify the N× spend vs. the panel alone (token cost OUT OF SCOPE this round, OQ1-resolved).** Per-candidate judge scores are logged via the existing `log(...)` + `summaryRounds` + returned-`summary` pattern and folded into the `doDesign` result summary (ref: Q13). The **token-cost** half of the ticket's AC2 is explicitly **descoped** here: `agent()` returns no token counts and no token accounting is added to `qrspi-batch.js`; the N×-spend justification rests solely on manual e2e comparison (panel-only vs. N-select+panel) and the eval-harness per-trial capture (ref: Q13, Q12). See OQ1 (resolved).

**AC3 — OFF by default; a single flag enables it.** A single enabling flag (e.g. `critics.design.candidates`) is read off the same `value.design` object that `resolveDesignCritic` already parses; absent/non-positive ⇒ N=1 (ref: Q6, Q10). When N=1 the design phase spawns the single produce agent exactly as today — zero extra agents, no judge worker, no selector, no graft agent, no synthesis — then falls through to the unchanged panel, mirroring how an absent `criticConfig` spawns zero critic agents (ref: Q10).

**Tests.** Pure judge-base-selection logic gets a `scripts/qrspi_design_select.py` module with a `_test.py` sibling covering all-pass, ties, single-winner, and empty/malformed fail-closed cases, mirroring `qrspi_critic_synthesize_test.py` (ref: Q11). The selector also emits the graft directives it was handed (passthrough/normalization), unit-tested for the degenerate cases (no runners-up ⇒ empty graft set ⇒ graft step is a no-op rewrite). The graft *content-merge* itself is an LLM rewrite, so it is verified by manual e2e (like the panel revise step), not by the pure unit tests. Eval comparison (panel-only vs N-select+panel) is done by unit tests plus manual e2e, since the harness has no A/B mechanism (ref: Q12).

## Delta

- **New file** `scripts/qrspi_design_select.py` — pure, stdlib-only stdin-JSON→stdout-JSON selector: takes the judge output (a list of `{candidate, score, rationale}` plus, per candidate, optional `graft_ideas`), returns `{winner, scores, graftDirectives}` where `winner` is the highest-scoring candidate's id and `graftDirectives` is the deduped list of runner-up ideas (drawn from the judge's per-candidate `graft_ideas`, excluding the winner) that the graft step must merge in. Deterministic tie-break for the base (highest score, ties broken by candidate index). Fail-closed on empty/malformed (ref: Q5, Q8, Q11).
- **New file** `scripts/qrspi_design_select_test.py` — `_test.py` sibling with stubbed-candidate coverage, including the no-runners-up case (empty `graftDirectives` ⇒ graft is a no-op) (ref: Q11).
- **New schema** `DESIGN_JUDGE_SCHEMA` in `qrspi-batch.js` — the judge agent's comparative rubric output: `{ scores: [{candidate, score, rationale, graft_ideas: string[]}], winner }`. `graft_ideas` per candidate names the specific strong ideas in that candidate worth grafting into the winner (empty for the winner / for candidates with nothing distinctive). Cannot reuse `CRITIC_VERDICT_SCHEMA` (binary, no ranking, no graft dimension) (ref: Q5).
- **New agent prompt(s)** under `.claude/agents/`:
  - a `qrspi-design-judge` prompt — scores N candidates on a rubric AND, per non-winning candidate, names the strong ideas worth grafting (emits `DESIGN_JUDGE_SCHEMA`);
  - a `qrspi-design-graft` prompt — given the winning base design path and the selector's `graftDirectives`, rewrites the winning design IN PLACE at `stg(id, 'design')`, merging in the named runner-up ideas while preserving the winner's structure (mirrors the panel reviser's in-place-rewrite contract, ref: Q3);
  - the framing mechanism for candidate generation: either a per-framing instruction spliced into the existing `qrspi-design` prompt (preferred) or new per-framing agent files mirroring the lens files (ref: Q2).
- **New framing-id list** `DEFAULT_DESIGN_FRAMINGS = ['mvp-first', 'risk-first', 'extensibility-first']` in `qrspi-batch.js`, analogous to `DEFAULT_DESIGN_LENSES` — three orthogonal axes (minimal ↔ robust ↔ extensible), per OQ2-resolved (ref: Q2).
- **New JS helper** `runDesignSelectLoop(name, id, config)` in `qrspi-batch.js` — maps N framings to N design-agent thunks via `parallel`, each writing to a distinct staging path `stg(id, 'design-cand-K')`; collects, judges via the `qrspi-design-judge` agent, calls the pure selector via a worker (like `synthesizeVerdicts`/`criticDecision`) to get `{winner, scores, graftDirectives}`, copies the winning candidate's content to `stg(id, 'design')` as the base, then — when `graftDirectives` is non-empty — runs the `qrspi-design-graft` agent to merge runner-up ideas in place at `stg(id, 'design')`; logs per-candidate scores and the graft summary (ref: Q3, Q7, Q8, Q13).
- **Modified** `runPhase` / `doDesign` — splice the N-select call between produce and the critic block, guarded by an N>1 check defaulting to N=1 (ref: Q1, Q10).
- **Modified** `resolveDesignCritic` / `parseCriticConfig` — parse the numeric `candidates` (N) flag off `value.design` and **clamp it to `[1, len(DEFAULT_DESIGN_FRAMINGS)]` (= `[1, 3]`)**: absent/`≤1` ⇒ N=1 (OFF, unchanged single-produce path), `≥2` ⇒ `min(candidates, 3)` running the first N framings; **log when clamping** (mirroring the unknown-lens log-and-drop idiom). Default OFF (ref: Q6, Q10) — per OQ3-resolved. **Testability note:** these are JS functions in `qrspi-batch.js`, which has no JS unit-test harness (no `package.json`); like the existing lens-parsing in the same function, the clamp is verified by **manual e2e** (`candidates` absent/`0`/`-5` ⇒ N=1 and zero extra spawns; `2` ⇒ 2; `99` ⇒ clamped-to-3 with a log line). If unit coverage is wanted, the count-resolution can be factored into a pure `scripts/`-side helper with a `_test.py` sibling — recorded as an option for the Structure phase, not mandated here.
- **Modified** `.qrspi/config.example.json` — document `critics.design.candidates` (the numeric N flag, clamped `[1,3]`, default OFF) (ref: Q6).

## Pattern Decisions

### Decision 1: Where N-select splices into the phase flow

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | New `runDesignSelectLoop` called from inside `runPhase`, between produce and the critic block, guarded by N>1 | Single chokepoint; panel + persist untouched; matches the documented splice point | Adds design-specific logic into the generic `runPhase` |
| B | A design-specific wrapper in `doDesign` that runs N-select, then calls `runPhase` with the winner already staged | Keeps `runPhase` generic | Two produce paths; risks the produce agent in `runPhase` double-running; harder to keep byte-for-byte-when-off |

**Recommendation:** Option A
**Rationale:** Research identifies the exact splice point as "between the single produce `agent()` call and the `if (criticConfig)` critic block" inside `runPhase` (ref: Q1), and the N=1 guarantee is cleanest when the single produce call is the N=1 case rather than an additional path (ref: Q10). The critic block and persist remain byte-for-byte unchanged.
**NEW PATTERN?** No — reuses the existing in-`runPhase` opt-in-seam guard pattern (ref: Q10).

### Decision 2: How framing variants are materialized

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Reuse the single `qrspi-design` agentType; splice a per-framing instruction line into the otherwise-identical prompt | No new agent files; framings live as data (a list like `DEFAULT_DESIGN_LENSES`); one prompt to maintain | Framing guidance is terser (one line) |
| B | New per-framing agent prompt files mirroring the lens files | Rich per-framing guidance | N new files to maintain; duplicates the design prompt N times |

**Recommendation:** Option A
**Rationale:** The panel varies parallel runs by interpolating per-run identity into an otherwise-identical dispatch (ref: Q2, Q7); reusing one agentType with a framing line keeps framings as a small editable data list and avoids N divergent prompt copies. Distinct per-candidate output paths (`stg(id,'design-cand-K')`) prevent the single-slot collision research flags (ref: Q2, Q3).
**NEW PATTERN?** No — extends the panel's per-run-variation fan-out pattern (ref: Q7).

### Decision 3: Judge/selection schema, graft-synthesis, and pure-core split

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | New `DESIGN_JUDGE_SCHEMA` (comparative scores + per-candidate `graft_ideas`) + pure `qrspi_design_select.py` selector (deterministic base + graft directives) + a `qrspi-design-graft` LLM rewrite that merges runner-up ideas in place | Matches the repo's pure-core/JS-glue split; deterministic, unit-testable, fail-closed base selection; **delivers the ticket's graft-synthesis (winner + grafted runner-up ideas), not bare selection** | New schema + new pure module + one extra agent prompt and one extra agent run when grafts exist |
| B | Reuse `CRITIC_VERDICT_SCHEMA` `{pass, findings}` and pick the first all-pass candidate verbatim | No new schema | Cannot rank/score; ties undefined; **drops the ticket-required graft-synthesis entirely** (verbatim winner, no merge); contradicts "judge on a rubric" (ref: Q5) |
| C | New `DESIGN_JUDGE_SCHEMA` + pure selector, but return only `{winner, scores, synthesisNotes}` with `synthesisNotes` as metadata and NO content-merge | Slightly simpler (no graft agent) | **Silently narrows the ticket** — "synthesized (grafting the best ideas from runners-up)" becomes pure verbatim selection; metadata notes are not a content merge; rejected as a scope drop |

**Recommendation:** Option A
**Rationale:** The ticket explicitly requires a *synthesized* winner that grafts the best ideas from runners-up (Desired behavior, Approach) — pure selection (Option C) drops that capability, so it is rejected. Verdicts are binary today with no comparative dimension, so ranking N candidates genuinely needs a new score schema, and the graft directive is a further new dimension (ref: Q5). The *which-base-wins* decision and the *graft-directive normalization* must be deterministic and isolated-testable, which the pure-core/JS-glue split provides (`synthesize`/`next_action` precedent) (ref: Q8, Q11). The graft *content-merge* itself is necessarily generative (merging prose ideas), so it lives in an LLM rewrite agent that mirrors the panel reviser's in-place-rewrite contract on `stg(id, 'design')` (ref: Q3) — it is verified by manual e2e, like the panel revise step. When no runner-up carries a distinctive idea (judge emits empty `graft_ideas`), `graftDirectives` is empty and the graft agent is skipped — the winning base is the final design, a clean no-op degenerate case.
**NEW PATTERN?** Partially — the SCHEMA (numeric/comparative scoring + graft directives) is a genuinely new dimension flagged explicitly (ref: Q5); the pure-module + worker invocation MECHANISM and the in-place LLM-rewrite MECHANISM (graft = panel-reviser shape) are existing patterns (ref: Q3, Q8).

### Decision 4: Partial-failure policy for the candidate fan-out

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Fail-closed: any null/empty candidate aborts the ticket | Matches the panel precedent exactly; "a missing run is never a winner"; zero new threshold arithmetic, no survivor-validity check, no extra Risk Register row (ref: Q9) | Loses work if one of N flakes; N× exposure to transient failure |
| B | Proceed with survivors above a minimum threshold (≥ ceil(N/2), and ≥1) | Resilient to a single flaky run | Departs from the panel's all-or-nothing precedent; needs a novel threshold mechanism, a survivor-validity check, and a dedicated degenerate-survivor mitigation — complexity the ticket does not demand |

**Recommendation:** Option A (fail-closed)
**Rationale:** The codebase's quality-bearing fan-out precedent (the critic panel) is fail-closed: any null lens verdict aborts the ticket, "a missing run is never a winner" (ref: Q9). Reusing that exact behavior for the candidate fan-out requires **zero new mechanism** — no `ceil(N/2)`/`≥1` threshold arithmetic, no survivor-validity check, and no dedicated Risk Register row. This feature is explicitly **deferred** and gated on eval payoff (ticket: "Deferred follow-up — pursue only if 2/5's eval gains plateau"), so introducing a novel survivor-threshold pattern in round one is complexity the ticket does not demand. A null produce candidate is caught the same way the panel catches a null lens (the `parallel` results' `=== null` check), and empty/unparseable produced files are caught downstream by the non-empty staging check before the candidate enters judging. The survivors-with-threshold refinement (Option B) is recorded below as a **deferred enhancement** to revisit only if e2e runs show single-candidate flakiness materially wastes N× spend.
**NEW PATTERN?** No — reuses the panel's established abort-on-any-null fail-closed fan-out (ref: Q9). (Option B's survivor-threshold would be a new pattern; it is deferred, not built.)

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| N-select accidentally runs when the flag is absent/garbled, incurring N× spend on every design | med | high | Default-OFF best-effort parsing (absent/non-positive ⇒ N=1, clamped `[1,3]`); reuse `parseCriticConfig` garble-to-default behavior; verify (manual e2e — JS config path, no JS unit harness) that absent config ⇒ N=1 and zero extra spawns (ref: Q6, Q10) |
| Candidate staging paths collide and clobber the canonical `design` slot before synthesis | med | high | Distinct per-candidate names `stg(id,'design-cand-K')`; the winning base is copied to `stg(id,'design')` only after selection, and the graft agent rewrites that same path in place; persist gate verifies non-empty (ref: Q2, Q3) |
| Graft step drops the winner's content or produces an empty file (in-place rewrite hazard) | med | high | Graft agent mirrors the panel reviser's in-place-rewrite-then-non-empty contract; `runDesignSelectLoop` re-checks `stg(id,'design')` is non-empty after the graft (and after the no-graft copy) before handing to the panel; persist gate is the final backstop (ref: Q3, Q9) |
| A candidate run flakes (null/empty), wasting the other N−1 runs | med | med | Fail-closed (Decision 4 Option A): any null/empty candidate aborts the ticket, matching the panel's abort posture — no partial-winner risk to mitigate. Survivor-tolerance is a deferred enhancement, not built (ref: Q9) |
| AC2 token-cost reporting is unsatisfiable — `agent()` returns no token counts to the script | high | med | **Accepted, not mitigated (OQ1-resolved: token cost OUT OF SCOPE).** Judge scores reported via existing `log`/`summary` surface; no token accounting added; N× justification rests on eval-harness per-trial capture + manual e2e (ref: Q12, Q13) |
| Judge produces a tie or no clear winner | med | med | Deterministic tie-break in the pure selector (highest score, ties by candidate index); explicit unit-test coverage for ties (ref: Q8, Q11) |

## Open Questions

### Resolved

- **OQ1 (resolved — token-cost reporting is OUT OF SCOPE).** AC2 requires token cost be
  reported, but `agent()` returns no token counts to the orchestrator and there is no token
  accounting in `qrspi-batch.js` (ref: Q13). **Decision:** the token-cost half of AC2 is dropped
  from this round. Per-candidate judge **scores** are still reported via the existing
  `log(...)`/`summary` surface; the N×-spend justification comes solely from manual e2e
  comparison (panel-only vs. N-select+panel). The Risk Register row about `agent()` exposing no
  token counts is therefore **accepted, not mitigated** — no token accounting is added.
- **OQ2 (resolved — framing set + judge rubric).**
  - **Framings** (`DEFAULT_DESIGN_FRAMINGS`): `mvp-first` (smallest thing satisfying the ACs;
    defer everything deferrable) / `risk-first` (foreground the riskiest, most-uncertain part;
    design failure modes first) / `extensibility-first` (design for the likely next requirements;
    pay structure cost now). Three **orthogonal** axes (minimal ↔ robust ↔ extensible) — chosen
    over the ticket's `MVP-first / risk-first / simplest-thing` because `simplest-thing` collapses
    onto `MVP-first`'s minimal axis, yielding only ~2 real axes of spread.
  - **Judge rubric**: the four RUS-56 panel lenses — `completeness`, `internal-consistency`,
    `edge-alignment`, `simplicity` — scored with **equal weight**. This shares one quality
    vocabulary across generate + review (the judge picks the candidate the downstream panel will
    rate highest), and equal weighting is what makes graft-synthesis coherent: each specialist
    framing deliberately underweights one lens, so the evenly-weighted judge selects the
    **best-balanced base** and grafts the standout ideas from the specialists.
- **OQ3 (resolved — N default + cap).** A single numeric flag `critics.design.candidates`,
  **clamped to `[1, len(DEFAULT_DESIGN_FRAMINGS)]` (= `[1, 3]`)**. Absent or `≤1` ⇒ **N=1** (OFF,
  the unchanged single-produce path); `≥2` ⇒ N = `min(candidates, 3)`, running the **first N**
  framings; default-when-on = 3 (use all framings). The clamp lives in
  `resolveDesignCritic`/`parseCriticConfig`, **logs when it clamps** (mirroring the unknown-lens
  log-and-drop idiom), and is unit-tested (`0`/absent/`-5` ⇒ 1, `2` ⇒ 2, `99` ⇒ 3). Rationale: a
  candidate's value is its distinct framing, so the framing-set size is the principled,
  self-documenting upper bound — asking for more candidates than framings would duplicate an angle
  (pure N× waste, and under fail-closed Decision 4, extra abort exposure) without adding diversity.

### Still open

- OQ4 (deferred enhancement): Should the partial-failure policy later move from fail-closed (Decision 4 Option A, the baseline) to proceed-with-survivors above a threshold? This is explicitly **deferred** — the design baselines on the existing fail-closed fan-out and only revisits survivor-tolerance if e2e runs show single-candidate flakiness materially wastes the N× spend. Recorded so the choice is not lost, not an unsettled blocker for round one.
