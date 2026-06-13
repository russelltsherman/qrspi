# Design — qrspi critics 4/5 — Stage 3 (Implementation): per-slice code critics + whole-stack coherence pass

**Ticket:** RUS-58
**Research basis:** research.md @ 2026-06-13T20:50:00Z
**Generated:** 2026-06-13T21:10:00Z
**Status:** draft

## Current State

The implementation phase has no edge critic, no slice-diff gathering, and no whole-stack coherence pass today; critics exist only for design (multi-lens panel) and plan (single critic) (ref: scope note, Q1, Q2). Implementation does not run through `runPhase`; it is the bespoke `doImplementation(t, r)`, which runs `impl-setup`, loops per slice spawning `qrspi-implement` then a slice-commit worker, then runs `qrspi-pr` and a Finalize `gt submit --publish --stack` (ref: Q4). The `impl-setup` worker already parses `structure.md`/`plan.md`/`worktree.md` and returns per-slice `structureSlice`/`planSlice`/`worktreeSession` blobs that are in memory in `doImplementation` — so each slice's planned steps are available with no new file read (ref: Q1).

The reusable critic machinery is two layers: `runCriticLoop(name, id, criticConfig)` runs produce→critique→revise entirely in the pre-persist staging window against `stg(id,name)`, returning `{ ok, residualFindings }`; and the `qrspi-critic` agent returns `{ pass, findings }`, with the converge/revise/cap decision delegated to the pure `qrspi_critic_loop.py::next_action` (ref: Q3). Cardinality is dispatched purely on `criticConfig.lenses?.length` in `runPhase` — single critic is simply a config without `lenses` (ref: Q6). The central asymmetry: single-artifact phases critique a staged file before the persist gate, but the implementation phase has no staging window — each slice is committed to its own Graphite branch `${id}/slice-N`, parented on `${id}/plan` (slice 1) or `${id}/slice-(N-1)` (ref: Q4, Q11, pattern 3). No slice diff is computed anywhere; a slice's diff is by construction its single branch commit relative to its parent (ref: Q11).

`cap_reached` is ship-with-disclosure, not a blocker: the loop still finalizes the artifact and surfaces residual findings into the PR body via `criticBodyStep` + `qrspi_critic_body.py`, which amends the commit message because Graphite seeds the body at creation only; submission is blocked only on a spawn failure (`ok:false`) (ref: Q5, Q8, Q14, pattern 4). The slice-amend revise path already exists as `doRevise` → `qrspi_revise_amend.py --branch <id>/slice-<N>`, which checks out, stages, amends with `gt modify`, and verifies the amend captured changes (ref: Q7). There is no mechanism to trigger an upstream revise from the implementation seam; the only upstream-drift machinery is the reviewer-initiated `reset` in `qrspi_resolve_state.py` (ref: Q9). The slice count is `setup.slices.length` from parsing `## Slice` headings; a single-slice ticket yields one loop iteration, and `alreadyCommitted` slices are skipped on resume (ref: Q10). `qrspi_config.py` reads one top-level key, so a `critics.implementation` block must be read by round-tripping the whole `critics` object under `--key critics`, never a dot-path (ref: Q6, inconsistency 1). All decisions are unit-tested as stdlib-only pure-Python `_test.py` siblings stubbing inputs as plain dicts/strings (ref: Q12, pattern 1). `run_eval.py`/`evals/` is a non-functional placeholder with no scoring step, so there is no real implementation-phase eval score to compare against (ref: Q13).

## Desired End State

**AC1 — Each slice runs its edge critic after tests, before submit, with planned steps as rubric.** Inside `doImplementation`'s slice loop, after `qrspi-implement` returns non-null ("tests pass") and after the slice-commit worker creates `${id}/slice-N`, a single per-slice edge critic runs against the slice diff (`${parent}..${id}/slice-N`) using `s.planSlice` (and `s.structureSlice`) as the rubric. On non-pass it revises via `qrspi_revise_amend.py`; the converge/revise/cap decision is the EXISTING pure `qrspi_critic_loop.py::next_action` (NOT re-implemented — see Decision 5). The critic runs before the final Finalize `gt submit` (ref: Q1, Q3, Q4, Q7, Q11). **On a single-slice ticket the per-slice critic is SKIPPED** — see Decision 7: the lone slice diff equals the whole stack, which the coherence pass already critiques against all six artifacts, so the per-slice critic would re-judge the same diff against a strict-subset rubric. The skip is owned by the `qrspi_slice_critic.py` diff-scope/skip reducer (it already gates `alreadyCommitted`; `setup.slices.length === 1` is the same kind of skip), so the surfacing path (slice-1 PR body, Decision 4) is unaffected.

**AC2 — The coherence pass runs once at the seam; findings surfaced into the slice-1 PR body.** Before the slice loop (the planning→implementation seam), one coherence critic reads the six artifacts at their canonical paths (`art(wd,id,name)` for five, `r.ticketContentPath` for the ticket, resolved INLINE in `doImplementation` exactly as `doDesign` resolves its panel inputs at lines 1349-1360) and flags intent drift. Because no slice branch/commit exists at the seam, the coherence pass produces findings but does NOT surface them at the seam; the findings are carried in memory through `doImplementation` and surfaced into the **slice-1 PR body** once slice 1 is committed — the bottom of the implementation stack and the durable artifact a reviewer reads first (Decision 4). Per the codebase precedent they are surfaced-as-findings, not an auto-reset (ref: Q2, Q5, Q9, Q14).

**AC3 — Per-slice critic does NOT run a panel.** The slice `criticConfig` omits `lenses`, routing to the single-critic path, bounding the N×M cost (ref: Q6, pattern 5).

**AC4 — Implementation-phase eval score reported before/after.** Because the eval harness is a non-functional placeholder, "before/after" is satisfied by a documented manual e2e on a multi-slice ticket plus the per-ticket result summary line, not by `run_eval.py` (ref: Q13, Open Questions).

## Delta

New pure module `scripts/qrspi_slice_critic.py` + `_test.py`: the genuinely-new **diff-scope/skip reducer ONLY** — which Graphite parent to diff a slice against (`${id}/plan` for slice 1, `${id}/slice-(N-1)` otherwise) and the skip guards: the `alreadyCommitted` (resume) skip AND the **single-slice skip** (`setup.slices.length === 1` → skip the per-slice critic entirely; the coherence pass covers the lone slice — Decision 7). It does **NOT** re-implement a converge/cap decision; the converge/revise/cap decision reuses the existing tested `qrspi_critic_loop.py::next_action` verbatim (Decision 5). (ref: Q3, Q10, Q11, Q12.)

The coherence pass requires **no new module**: per research Q2, `doImplementation` resolves the six artifact paths inline (`art(wd,id,name)` × 5 + `r.ticketContentPath`) exactly as `doDesign` already resolves its panel inputs (lines 1349-1360), and the fail-closed missing/empty-path check (Risk Register row 3) is a single guard inline before the coherence-critic spawn — not a module, and with no disposition reducer, because Decision 3 fixes the disposition as surface-only (a one-outcome branch is not a decision to encode). (ref: Q2, Q9, Decision 3, Decision 6.)

Extend `scripts/qrspi_critic_body.py`: add a slice branch to `_PHASE_BRANCH` so it can target `${id}/slice-N` (today design/plan only). This one extension serves BOTH residual-findings surfacing targets — the per-slice residual findings (amended into that slice's own commit message) and the coherence findings (amended into the **slice-1** commit message, per Decision 4) — because both now address a `slice-N` branch through the same `--phase slice --slice N` path (ref: Q5, inconsistency 2).

Modify `.claude/workflows/qrspi-batch.js`: in `doImplementation`, (1) resolve the six coherence paths inline and run the coherence pass before the slice loop, carrying its findings in memory; (2) insert the per-slice critic inside the loop (post-commit), computing the slice diff against the Graphite parent (via the `qrspi_slice_critic.py` reducer) and routing the non-pass outcome to `qrspi_revise_amend.py`; (3) when slice 1 is committed, surface BOTH the slice-1 residual findings and the carried coherence findings into the slice-1 PR body via the extended `qrspi_critic_body.py`; (4) add a `readImplementationCriticConfig` reader round-tripping `--key critics`; (5) handle a slice-critic or coherence-critic spawn failure (`ok:false`) as `skip(...)` like the existing implement/commit failure paths (ref: Q2, Q4, Q5, Q6, Q7, Q8). New agent prompt for the coherence critic under `.claude/agents/` (the per-slice critic reuses `qrspi-critic`). Config: a `critics.implementation` block in `.qrspi/config.example.json` (ref: Q6).

## Pattern Decisions

### Decision 1: When does the per-slice critic run — before or after the slice commit?

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | After the slice-commit worker; diff is `${parent}..${id}/slice-N` (the branch commit) | Diff is exactly the deliverable, computed deterministically from branch topology (ref: Q11); revise reuses `qrspi_revise_amend.py` which requires the branch to exist (ref: Q7) | Revise amends an already-committed branch rather than rewriting a staged file |
| B | Before commit; diff the working tree against `${parent}` | Closer to the staged-file loop shape | No branch yet, so `qrspi_revise_amend.py` cannot be used (it checks out a branch); working-tree diff is fragile; breaks the staging-gate assumption (ref: Q3, Q11) |

**Recommendation:** Option A
**Rationale:** The implementation phase commits, it does not stage (pattern 3); the only existing slice-revise mechanism (`qrspi_revise_amend.py`) operates on an existing branch (ref: Q7), and the slice diff is well-defined only after the commit (ref: Q11). Option A reuses both established patterns directly.
**NEW PATTERN?** Yes — a critic that operates on a committed Graphite branch + amend-revise, rather than the staged-file rewrite of `runCriticLoop`. Justified: implementation has no staging window (pattern 3), so the staged-file critic loop cannot be reused as-is.

### Decision 2: What happens when a slice critic fails after max rounds?

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Ship-with-disclosure: cap_reached finalizes; residual findings amended into the slice PR body | Matches established critic semantics exactly (ref: Q8, pattern 4); the human reviewer is the PR gate | A drifted slice can be submitted (with disclosure) |
| B | Block submission on cap_reached | Stronger guarantee of plan-fidelity | Contradicts the codebase precedent; no current terminal-block path in `doImplementation`; risks a wedged stack (ref: Q8) |

**Recommendation:** Option A
**Rationale:** The entire critic subsystem treats cap_reached as best-effort-exhausted-ship-anyway, blocking only on spawn failure (ref: Q8, Q14). Diverging here would be a new failure mode in a bespoke loop with no precedent. The PR review gate remains the human backstop.
**NEW PATTERN?** No — reuses pattern 4.

### Decision 3: How does a coherence finding act on upstream drift?

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Surface-as-finding only (PR body + summary); a human decides whether to request changes upstream | No new control path; reset stays reviewer-initiated and total as today (ref: Q9) | Drift is disclosed, not auto-corrected |
| B | Auto-trigger an upstream reset/revise from the seam | Closes the loop automatically | Net-new producer→resolver channel that does not exist; reset is total discard of all downstream phases — high blast radius from an automated finding (ref: Q9) |

**Recommendation:** Option A
**Rationale:** No path exists today for an automated finding to reach `resolve`/`reset`; reset is reviewer-initiated and discards all downstream work (ref: Q9). The ticket itself says the coherence pass "surfaces findings; may trigger a targeted upstream revise" — Option A satisfies the firm requirement (surface) and leaves the optional auto-revise as an Open Question rather than building a high-blast-radius auto-discard now. **Because this fixes the disposition as a constant (surface-only, never flag/reset), no disposition reducer is built** — a one-outcome branch is not a decision to encode in code (see Decision 6).
**NEW PATTERN?** No for surfacing (reuses the PR-body/summary channels, pattern 6); auto-revise would be a new pattern, deferred.

### Decision 4: Where do slice/coherence residual findings surface in the PR body, and against which commit?

This decision has **two distinct surfacing targets** — they must be resolved separately because they differ in *which commit/PR body* receives the findings and *when*:

- **Per-slice residual findings** (produced post-commit, inside the loop, for slice N): surface into **that slice's own** PR body, by amending the `${id}/slice-N` commit message.
- **Coherence residual findings** (produced once at the seam, *before any slice commit exists*): there is no slice-N commit at the seam to amend (this is the AC2 timing constraint — the critic produces findings before any slice commit the amend mechanism requires). They are therefore carried in memory and surface into the **slice-1** PR body, by amending the `${id}/slice-1` commit message **after slice 1 is committed**. Slice 1 is the bottom of the implementation stack and the first PR a reviewer reads, making it the correct durable home for whole-stack drift findings.

Both targets are a `slice-N` branch, so a single mechanism serves both:

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Extend `qrspi_critic_body.py` `_PHASE_BRANCH` with a `slice` path taking `--slice N`, then call it twice: `--phase slice --slice N` for per-slice findings against `${id}/slice-N`, and `--phase slice --slice 1` for the carried coherence findings against `${id}/slice-1` | Reuses the existing residual-findings-into-commit-message mechanism verbatim for BOTH targets; one extension covers slice and coherence (ref: Q5) | Touches a design/plan-scoped script (inconsistency 2) |
| B | Splice findings via `qrspi_pr_body.py` (the implementation body composer) | That script already owns the slice PR body (ref: Q5) | Duplicates the findings-rendering logic that already lives in `qrspi_critic_body.py`; still needs a separate path for the slice-1 coherence target |

**Recommendation:** Option A
**Rationale:** `qrspi_critic_body.py` already renders a `## Residual critic findings` section and amends the commit message (ref: Q5); the only gap is its design/plan-only `_PHASE_BRANCH` (inconsistency 2). Adding ONE `slice` branch (parameterized by `--slice N`) gives a concrete, named target for BOTH the slice half (`slice-N`) and the coherence half (`slice-1`) of this decision's scope — closing the gap that the heading "slice/coherence" previously left for coherence. The coherence amend is gated on slice 1 being committed, satisfying the AC2 timing constraint (findings exist before the commit, but are written only after it). Extending one branch table reuses the proven mechanism rather than duplicating it.
**NEW PATTERN?** No — extends an existing script's branch table; the only new behavior is the deferred (post-slice-1-commit) write of the carried coherence findings, which still flows through the same script.

### Decision 5: Does the per-slice critic re-implement the converge/cap decision, or reuse `qrspi_critic_loop.py::next_action`?

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Reuse the existing tested `qrspi_critic_loop.py::next_action(verdicts, round, max_rounds)` for converge/revise/cap; scope the NEW `qrspi_slice_critic.py` to only the genuinely-new diff-scope/skip reducer | No duplication; the slice critic gets identical, already-tested converge/cap semantics (pattern 4); the only new pure logic is the diff-scope reducer that has no existing equivalent (ref: Q11) | The slice loop must call two small pure modules (`next_action` + the diff-scope reducer) instead of one |
| B | Re-implement a `next_action`-style decision inside `qrspi_slice_critic.py` | Single module owns the whole slice-critic decision | Duplicates an existing, tested pure module; two copies of the cap/converge rule can drift; contradicts AC1's own statement that "convergence/cap follows `next_action`" (ref: Q3) |

**Recommendation:** Option A
**Rationale:** The converge/revise/cap decision already exists as the tested `qrspi_critic_loop.py::next_action` (ref: Q3), and AC1 already commits to it. Re-implementing it would duplicate a pure module for no benefit and risk divergence between the slice and design/plan cap semantics. The genuinely-new logic the slice critic needs — which Graphite parent to diff against and the `alreadyCommitted` skip guard — has no existing equivalent, so `qrspi_slice_critic.py` is scoped to ONLY that diff-scope/skip reducer. The slice loop wires `next_action` (decision) + `qrspi_slice_critic.py` (diff scope) together, mirroring how `runPhase` already wires `next_action` alongside its own glue.
**NEW PATTERN?** No — reuses `next_action` (pattern 1) and adds one small pure reducer that follows the same pure-decision-core convention.

### Decision 6: Does the coherence pass get a dedicated module, or resolve paths inline?

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Resolve the six artifact paths INLINE in `doImplementation` (`art(wd,id,name)` × 5 + `r.ticketContentPath`), exactly as `doDesign` resolves its panel inputs (lines 1349-1360); the fail-closed missing/empty-path check is a single inline guard before the spawn | No new module for constant work; matches the precedent research Q2 explicitly cites (`doDesign` resolves panel inputs inline); the disposition is a Decision-3 constant (surface-only), so there is nothing to reduce | Path-resolution + fail-closed guard live in JS glue rather than a unit-tested Python module |
| B | New module `scripts/qrspi_coherence.py` resolving the six paths + a surface-only-vs-flag disposition reducer | A pure module is unit-testable | The disposition reducer encodes a branch Decision 3 has decided never to take (surface-only is fixed) — a decision over a constant; path resolution duplicates the inline `art(...)` pattern `doDesign` already uses (ref: Q2) |

**Recommendation:** Option A
**Rationale:** Decision 3 fixes the disposition as surface-only with no auto-flag/reset, so a "surface-only vs. flag" reducer would encode a one-outcome branch — there is no decision to make, hence no module to test for it. Per research Q2, the six paths resolve inline in `doImplementation` exactly as `doDesign` already resolves its panel inputs (`art(wd,id,name)` + `r.ticketContentPath`), so a dedicated module would only duplicate an established inline pattern. The one genuinely-defensive piece — the fail-closed check that every resolved path is present and non-empty before spawning (Risk Register row 3) — is a single inline guard, not a reducer; it does not need a module. If a future stage ever introduces a real flag-vs-surface choice, THAT is when a pure reducer (and its `_test.py`) earns its place.
**NEW PATTERN?** No — reuses the inline-path-resolution pattern from `doDesign` (ref: Q2) and the fail-closed convention (pattern 7).

### Decision 7: On a single-slice ticket, does the per-slice critic still run, or is it skipped in favor of the coherence pass?

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Skip the per-slice critic when `setup.slices.length === 1`; the coherence pass alone covers the lone slice | No redundant judging: with one slice the slice diff (`${id}/plan..${id}/slice-1`) IS the whole stack, which the coherence pass already critiques against ALL six artifacts (a superset of the slice's plan/structure rubric); saves one N×rounds critic invocation per single-slice ticket at zero coverage loss | A single-slice ticket no longer gets a finding rendered specifically against its plan-slice rubric (but the coherence pass's broader rubric strictly contains it) |
| B | Always run both, even on a single-slice ticket (the as-submitted design) | One uniform loop body; no slice-count branch | Re-judges the same diff twice — once against the plan/structure subset, once against all six artifacts; the per-slice pass adds cost with no diff the coherence pass hasn't already seen |

**Recommendation:** Option A
**Rationale:** When `setup.slices.length === 1`, the per-slice critic and the coherence pass operate on the identical diff (the one slice is the entire stack), and the coherence rubric (six artifacts) is a strict superset of the per-slice rubric (that slice's plan/structure). Running the per-slice critic therefore buys no coverage the coherence pass does not already provide, while costing an extra critic loop. Skipping it is the same *kind* of skip the reducer already owns for `alreadyCommitted` slices (Decision 5 / ref: Q10), so it adds no new control surface — just one more guard clause in `qrspi_slice_critic.py`, unit-tested alongside the resume skip. The multi-slice path is unchanged: with ≥2 slices each slice diff is a proper subset of the stack, so the per-slice critic still adds plan-fidelity judgment the coherence pass does not. Surfacing is unaffected: the coherence findings still amend the slice-1 PR body (Decision 4), which on a single-slice ticket is the only PR.
**NEW PATTERN?** No — extends the existing skip-guard responsibility of `qrspi_slice_critic.py` (the reducer already decides whether a slice runs); `setup.slices.length === 1` is a second skip predicate beside `alreadyCommitted`.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| N×M cost blowup if a panel leaks into the per-slice path | med | high | Hard-enforce single-critic: slice `criticConfig` omits `lenses`; unit-test that the slice path never routes to `runCriticPanelLoop` (ref: Q6, AC3) |
| Slice/coherence-critic `ok:false` (spawn failure) silently ships, since implementation has no `runPhase` wrapper to abort | med | high | Add explicit `ok:false` handling in `doImplementation` (both the seam coherence pass and the in-loop slice critic) returning `skip(...)`, mirroring the implement/commit failure paths (ref: Q8) |
| Coherence pass reads stale/missing artifacts (e.g., ticket path not surfaced) | low | med | Resolve all six paths inline and fail-closed if any is missing/empty before spawning the critic; ticket comes from `r.ticketContentPath` — a single inline guard, no disposition reducer (ref: Q2, Decision 6, pattern 7) |
| Coherence findings have no commit to attach to at the seam (AC2 timing) | med | med | Carry coherence findings in memory; amend them into the slice-1 commit message only AFTER slice 1 is committed, via the extended `qrspi_critic_body.py --phase slice --slice 1` (ref: Q5, Decision 4) |
| `critics.implementation` read via wrong dot-path returns empty default, silently disabling the critic | med | med | Read by round-tripping the whole `critics` object under `--key critics` and digging `value.implementation`, never `--key critics.implementation`; unit-test the parser (ref: Q6, inconsistency 1) |
| Re-implementing `next_action` in the slice critic drifts from design/plan cap semantics | low | med | Reuse `qrspi_critic_loop.py::next_action` verbatim; scope `qrspi_slice_critic.py` to only the diff-scope/skip reducer (ref: Q3, Decision 5) |
| Resumed run (`alreadyCommitted` slices) over- or under-runs the critic | low | med | Bound critic runs to non-`alreadyCommitted` slices via the `qrspi_slice_critic.py` skip guard, matching the existing skip logic (ref: Q10) |
| Single-slice ticket runs a redundant per-slice critic that re-judges the same diff the coherence pass already covers | med | low | Skip the per-slice critic when `setup.slices.length === 1` via the `qrspi_slice_critic.py` single-slice skip guard; coherence pass alone covers the lone slice (Decision 7, ref: Q10) |
| `criticBodyStep` JS helper / `_PHASE_BRANCH` hard-wired to `{design,plan}` blocks slice + coherence findings reaching the body | med | low | Extend both the JS helper and `qrspi_critic_body.py` `_PHASE_BRANCH` together to add ONE `slice` path (`--slice N`) serving both surfacing targets (ref: Q5, inconsistency 2, Decision 4) |

## Open Questions

All open questions below have been answered by the reviewer; their confirmed dispositions are now integrated into the design above and recorded here as RESOLVED.

- ~~OQ1~~ RESOLVED (reviewer confirmed: "surface-only is acceptable"): The coherence pass has **no** automatic upstream-revise power for this stage. Decision 3 fixes the disposition as surface-only (PR body + summary), with no auto-flag/reset — grounded in research Q9 (no producer→resolver channel exists today; `reset` is reviewer-initiated and a total discard of all downstream phases, a high-blast-radius path to drive from a non-deterministic critic verdict). The ticket's firm requirement ("surfaces findings") is met; the optional "may trigger a targeted upstream revise" is deferred. Because the disposition is a constant, no disposition reducer is built (Decision 6).
- ~~OQ2~~ RESOLVED (reviewer confirmed: "manual e2e on a multi-slice ticket plus the result-summary line is an acceptable substitute"): AC4's before/after implementation-phase eval requirement is satisfied by a documented manual e2e on a multi-slice ticket plus the per-ticket result-summary line, **not** by `run_eval.py` — the eval harness is a documented non-functional placeholder with no scoring step (ref: Q13). Building a real scorer is out of scope for this stage.
- ~~OQ3~~ RESOLVED (reviewer confirmed: "after-commit"): The per-slice critic runs **after** the slice commit (Decision 1, Option A: diff `${parent}..${id}/slice-N`), not before against a working-tree diff. Implementation commits rather than stages (pattern 3), and the only slice-revise mechanism (`qrspi_revise_amend.py`) operates on an existing branch (ref: Q7), so the diff is well-defined only post-commit (ref: Q11). This still satisfies the ticket's "before gt submit": each per-slice critic (and its revise-amend) runs inside `doImplementation`'s slice loop, while the final stack `gt submit` happens in Finalize after the loop (ref: AC1).
- ~~OQ4~~ RESOLVED (Decision 7, reviewer comment): For a single-slice ticket the per-slice critic is **skipped** in favor of the coherence pass alone — the lone slice diff equals the whole stack, which the coherence pass already critiques against all six artifacts (a superset of the per-slice rubric), so the per-slice run is redundant. The skip lives in the `qrspi_slice_critic.py` reducer beside the `alreadyCommitted` guard; coherence findings still surface into the slice-1 PR body (Decision 4), which is the only slice (ref: Q10).
