# PR: RUS-58 critics 4/5 — per-slice critic + coherence pass

**Ticket:** RUS-58
**Design:** design.md @ 2026-06-13T21:10:00Z
**Structure:** structure.md @ 2026-06-13T21:35:00Z

## Summary

Adds Stage 3 of the QRSPI critic subsystem to the implementation phase: a
whole-stack **coherence pass** that runs once at the planning→implementation
seam (judging ticket + questions + research + design + structure + plan for
intent drift), and a **per-slice edge critic** that runs inside the slice loop
against each slice's Graphite diff using the slice's planned steps as the rubric.
Both are wired into `doImplementation` in `qrspi-batch.js` behind a new
`critics.implementation` config block that is **OFF by default**, so the
no-critic path is byte-for-byte unchanged. The genuinely-new pure logic is
isolated to one tested reducer (`qrspi_slice_critic.py`, diff-scope + skip
decisions); convergence reuses the existing `qrspi_critic_loop.py::next_action`
verbatim, and residual findings surface through a one-line `slice` extension to
`qrspi_critic_body.py`. **Reviewer focus:** the JS orchestration in slice 3
(`doImplementation`) — the fail-closed coherence-input guard, the `ok:false`
spawn-failure → `skip(...)` handling, and the deferred coherence-findings amend
into the slice-1 PR body — since that change is verified only by manual e2e, not
an automated JS test.

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: Each slice runs its edge critic after tests, before submit, with planned steps as rubric (single-slice skipped per Decision 7) | `.claude/workflows/qrspi-batch.js::doImplementation` (per-slice loop) + `scripts/qrspi_slice_critic.py::decide` (diff scope/skip) + `qrspi_critic_loop.py::next_action` (reused, converge/cap) | `scripts/qrspi_slice_critic_test.py` (run/skip + diff-base branches); manual e2e (structure.md §Slice 3) |
| AC2: Coherence pass runs once at the seam; findings surfaced into the slice-1 PR body | `.claude/workflows/qrspi-batch.js::doImplementation` (seam coherence pass, in-memory carry, deferred slice-1 amend) + `.claude/agents/qrspi-coherence-critic.md` + `scripts/qrspi_critic_body.py` (`--phase slice --slice 1`) | `scripts/qrspi_critic_body_test.py` (`phase_branch slice N=1`); manual e2e |
| AC3: Per-slice critic does NOT run a panel (single-critic path, omit `lenses`) | `.claude/workflows/qrspi-batch.js::doImplementation` (slice `criticConfig` omits `lenses`) | manual e2e (no panel route); enforced by config shape |
| AC4: Implementation-phase eval reported before/after (eval harness is a placeholder → manual e2e + result-summary line per OQ2) | `.claude/workflows/qrspi-batch.js` per-ticket result-summary line | Documented manual e2e on a multi-slice ticket (structure.md §Slice 3 Verification) |

## Changes by Slice

### Slice 1: Diff-scope/skip reducer (`qrspi_slice_critic.py`)

| File | Change | Lines |
|------|--------|-------|
| `scripts/qrspi_slice_critic.py` | ✨ new | +129 |
| `scripts/qrspi_slice_critic_test.py` | ✨ new | +93 |

### Slice 2: Extend `qrspi_critic_body.py` with the `slice` branch

| File | Change | Lines |
|------|--------|-------|
| `scripts/qrspi_critic_body.py` | ⚠️ modified | +32, -7 |
| `scripts/qrspi_critic_body_test.py` | ⚠️ modified | +23, -0 |

### Slice 3: Wire coherence pass + per-slice critic into `doImplementation`

| File | Change | Lines |
|------|--------|-------|
| `.claude/workflows/qrspi-batch.js` | ⚠️ modified | +245, -1 |
| `.claude/agents/qrspi-coherence-critic.md` | ✨ new | +61 |
| `.qrspi/config.example.json` | ⚠️ modified | +9, -1 |

### Phase artifacts (Questions/Research/Design/Structure/Plan/WorkTree/Impl-log)

| File | Change | Lines |
|------|--------|-------|
| `.qrspi/RUS-58/questions.md` | ✨ new | +51 |
| `.qrspi/RUS-58/research.md` | ✨ new | +332 |
| `.qrspi/RUS-58/design.md` | ✨ new | +143 |
| `.qrspi/RUS-58/structure.md` | ✨ new | +76 |
| `.qrspi/RUS-58/plan.md` | ✨ new | +163 |
| `.qrspi/RUS-58/worktree.md` | ✨ new | +83 |
| `.qrspi/RUS-58/impl-log.md` | ✨ new | +150 |

## Testing Summary

- [x] Slice 1: unit tests — `python3 scripts/qrspi_slice_critic_test.py` — 8 passed, 0 failed (exit 0)
- [x] Slice 2: unit tests — `python3 scripts/qrspi_critic_body_test.py` — 41 passed, 0 failed (exit 0; 28 pre-existing design/plan regression checks + 13 new `slice`-branch checks)
- [x] Slice 3: JS syntax — `node --check .claude/workflows/qrspi-batch.js` — SYNTAX_OK (exit 0; orchestrator has no automated JS test by convention — verified by manual e2e per plan §3.24)
- [x] No regression: both Python suites re-run clean after the slice-3 wiring landed
- [ ] Manual verification (pending reviewer/operator): multi-slice e2e — coherence pass runs once at the seam; per-slice critic runs per non-first/non-committed slice and skips on `alreadyCommitted`; single-slice ticket skips the per-slice critic; residual findings appear in slice-1 (coherence) and each slice's own PR body; a forced `ok:false` spawn failure yields `skip(...)`; `critics.implementation` absent → byte-for-byte-unchanged no-critic path

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| `qrspi_slice_critic.py` exposure (structure §Contracts: `decide(setup, slice_index)` import) | Pure `decide(...)` function | `decide(...)` **plus** a thin `--slice-index N` stdin→stdout CLI shim | Matches the sibling `qrspi_critic_loop.py` precedent (JS caller shells out to read JSON, structure §Contracts line 22). The CLI is additive; the pure function is unchanged. Path §1.3 anticipated this; impl-log Session 1 records it as not a deviation. |
| `phase_branch` signature | add `slice` to `_PHASE_BRANCH` | Registered `"slice"` in `_PHASE_BRANCH` (keeps argparse `choices` table-driven) **and** added parametric `slice-{N}` computation in `phase_branch(ticket, phase, slice_index=None)` | Plan §2.7 left "add to `_PHASE_BRANCH` **or** its resolver" open; doing both keeps design/plan table-driven while computing the indexed suffix. `slice_index` is required (ValueError) only when `phase == "slice"`, so existing two-arg calls remain valid. |
| Fail-closed coherence-input guard (design Risk row 3: "stat the six paths") | Filesystem presence check | Uses the RESOLVE envelope's `r.existing.{questions,research,design,structure,plan}` booleans + truthiness of `r.ticketContentPath` | The JS workflow has no `require('fs')` / filesystem access; it uses the same authoritative presence source the design phase already trusts. Same contract (missing/empty input → `skip(...)`, no spawn); mechanism choice only. impl-log Session 3 T14. |
| Conditional `qrspi-implement` wrapper/doc touch (structure §Slice 3, marked "only if needed") | Possible doc edit | Not touched | No wrapper/doc reference to the new seam was required; the file was correctly dropped from the slice (an Unverified Assumption resolved as "no edit"). |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| N×M cost blowup if a panel leaks into the per-slice path | mitigated — slice `criticConfig` omits `lenses`, routing to single-critic path (AC3) | Set `critics.implementation.enabled=false` (default OFF) |
| Slice/coherence critic `ok:false` (spawn failure) silently ships | mitigated — explicit `ok:false` → `skip(...)` for both the seam coherence pass and the in-loop slice critic, mirroring implement/commit failure paths | Disable the block; the no-critic path is byte-for-byte unchanged |
| Coherence pass reads stale/missing artifacts | mitigated — fail-closed guard on the six inputs via `r.existing.*` presence booleans + `r.ticketContentPath` before spawn (mechanism deviation noted above) | Disable the block |
| Coherence findings have no commit to attach to at the seam (AC2 timing) | mitigated — findings carried in memory, amended into slice-1 commit only after slice 1 is committed via `qrspi_critic_body.py --phase slice --slice 1` | Disable the block |
| `critics.implementation` read via wrong dot-path silently disables critic | mitigated — `readImplementationCriticConfig` round-trips the whole `critics` object via `--key critics` and digs `value.implementation` (never a dot-path); honors the single-top-level-key reader limit | n/a — read-path correctness |
| Re-implementing `next_action` drifts from design/plan cap semantics | mitigated — `next_action` reused verbatim; `qrspi_slice_critic.py` scoped to only the diff-scope/skip reducer | n/a |
| Resumed run over/under-runs the critic | mitigated — `alreadyCommitted` skip guard in the reducer (precedence over single-slice), unit-tested | n/a |
| Single-slice ticket runs a redundant per-slice critic | mitigated — `single-slice` skip guard (`len(slices)==1`) in the reducer; coherence pass covers the lone slice (Decision 7) | n/a |
| `_PHASE_BRANCH` hard-wired to `{design,plan}` blocks slice/coherence findings | mitigated — one `slice` entry added (`--slice N`) serving both surfacing targets; design/plan paths regression-guarded | n/a |
| (newly discovered) Whole feature is config-gated and default-OFF — no automated JS test exercises `doImplementation` | accepted — verified by `node --check` + manual e2e per the documented placeholder-eval convention (AC4 / OQ2) | Default OFF means zero behavior change until an operator opts in |

## Open Items

- **Manual multi-slice e2e is still pending** (AC4 / structure §Slice 3 Verification): coherence-at-seam, per-slice run/skip, single-slice skip, both surfacing targets, `ok:false`→skip, and the absent-config no-op path must be exercised on a real multi-slice ticket before this is trusted in batch. The eval harness is a documented non-functional placeholder, so no numeric eval delta artifact exists (OQ2 RESOLVED).
- **Auto-triggered upstream revise from a coherence finding is deferred** (Decision 3 / OQ1 RESOLVED): the coherence pass is surface-only (PR body + summary); it has no automatic upstream reset/revise power this stage. Building a producer→resolver channel is a high-blast-radius follow-up, out of scope here.
- **`critics.implementation` field names** were confirmed against the existing design/plan critic blocks during planning (structure Unverified Assumption); the example block ships OFF. Real opt-in config lives in the gitignored `.qrspi/config.json`, not in this PR.
- This is **Stage 3 of the 4/5 critics arc** — it completes the implementation-phase critic seam; remaining critic-subsystem stages (if any) are tracked outside this ticket.
