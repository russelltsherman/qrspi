# Work Tree — qrspi critics 4/5 — Stage 3 (Implementation): per-slice code critics + whole-stack coherence pass

**Plan basis:** plan.md @ 2026-06-13T21:55:00Z
**Generated:** 2026-06-13T22:10:00Z
**Status:** draft
**Total sessions:** 5
**Critical path:** T1 → T2 → T4 → T5 → T6 → T7 → T8 → T9 → T10 → T11 → T13 → T14 → T15 → T16 → T18 → T19 → T20 → T21 → T22 → T23 → T24 → T25 → T26 → T27 (24 tasks)

## Session 1 — Slice 1: Diff-scope/skip reducer (`qrspi_slice_critic.py`)

**Load:** structure.md §Types, structure.md §Contracts, structure.md §Verification, plan.md §Slice 1
**Estimated context:** ~15% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create `scripts/qrspi_slice_critic.py` — stdlib-only pure module exposing `decide(setup, slice_index)` | — | §1.1 | S | pending |
| T2 | Implement `decide(setup, slice_index)` per contract: skip branches (`alreadyCommitted`, `single-slice`), run branch (diffBase/diffHead), precedence | T1 | §1.2 | M | pending |
| T3 | Add `__main__` guard only if needed for CLI parity with sibling pure modules; else import-only | T1 | §1.3 | S | pending |
| T4 | Create `scripts/qrspi_slice_critic_test.py` — cover all branches (two diff bases, two skip reasons, run case, no-skip-reason assert) | T2 | §1.4 | M | pending |
| T5 | **Verify Slice 1** — `python3 scripts/qrspi_slice_critic_test.py`, exit 0, all branches pass | T4 | §1.5 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete and verified (new pure module + tests). Fresh context for Slice 2, a separate additive module change with no shared in-memory state.

## Session 2 — Slice 2: Extend `qrspi_critic_body.py` with the `slice` branch

**Load:** structure.md §Contracts (critic_body slice branch), structure.md §Verification, plan.md §Slice 2, impl-log.md §Slice 1 (notes only)
**Estimated context:** ~18% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T6 | Read existing `_PHASE_BRANCH` map + `--phase` parsing in `scripts/qrspi_critic_body.py` (confirm current shape) | T5 | §2.6 | S | pending |
| T7 | Add `slice` branch-resolution path: `--phase slice --slice N` → `f"{id}/slice-{N}"`; design/plan unchanged | T6 | §2.7 | M | pending |
| T8 | Extend argparse to accept `--slice` (int), required only when `--phase slice` | T7 | §2.8 | S | pending |
| T9 | Modify `scripts/qrspi_critic_body_test.py` — add slice-1/slice-N cases + design/plan regression guard + unchanged rendering | T8 | §2.9 | M | pending |
| T10 | **Verify Slice 2** — `python3 scripts/qrspi_critic_body_test.py`, slice + design/plan pass, exit 0 | T9 | §2.10 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 2 complete and verified. Slice 3 is the large orchestrator wiring in `qrspi-batch.js` that consumes both prior modules; it needs a fresh context with the full design/structure/plan loaded for the seam. Split into Sessions 3–5 to stay under 40%.

## Session 3 — Slice 3a: Anchors + config reader + coherence pass

**Load:** structure.md §Contracts, structure.md §Unverified Assumptions, structure.md §Risk Register, design.md §coherence-seam, plan.md §Slice 3 (steps 11–16), impl-log.md §Slices 1–2 (notes only)
**Estimated context:** ~32% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T11 | Confirm anchors in `.claude/workflows/qrspi-batch.js` (doDesign panel region, `art()`, `r.ticketContentPath`, `critics.design`/`plan` blocks, `next_action` signature); plan to actual code if anchors differ | T10 | §3.11 | M | pending |
| T12 | Add `readImplementationCriticConfig(wd, id)` — round-trip whole `critics` via `--key critics`, dig `value.implementation`; absent → disabled defaults | T11 | §3.12 | M | pending |
| T13 | In `doImplementation`, resolve six coherence-input paths inline (5 artifacts via `art()` + `r.ticketContentPath`) ahead of slice loop | T11 | §3.13 | M | pending |
| T14 | Add fail-closed guard: any missing/empty coherence input → `skip(...)` before spawning coherence critic | T13 | §3.14 | S | pending |
| T15 | Run coherence critic once at seam (gated on `coherence.enabled`) spawning `qrspi-coherence-critic`; converge via `next_action` to `coherence.maxRounds`; carry residual findings in memory | T12, T14 | §3.15 | L | pending |
| T16 | Handle coherence-critic spawn failure (`ok:false`) → `skip(...)` | T15 | §3.16 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Coherence-pass seam wiring complete. Per-slice critic loop (inside the slice loop) is a distinct region of `doImplementation` with its own revise/cap logic; fresh context keeps the per-slice work below 40% and avoids carrying the coherence-seam detail.

## Session 4 — Slice 3b: Per-slice critic inside the loop

**Load:** structure.md §Contracts (slice critic), structure.md §Risk Register, design.md §per-slice-critic, plan.md §Slice 3 (steps 17–20), impl-log.md §Slice 3a (notes only)
**Estimated context:** ~30% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T17 | In slice loop, after slice-commit creates `${id}/slice-N`, call `qrspi_slice_critic.py` reducer (shell out, parse JSON); when `run` false, skip per-slice critic | T16 | §3.17 | M | pending |
| T18 | When `run` true, run single-critic per-slice loop: spawn existing `qrspi-critic` against `${diffBase}..${diffHead}`, rubric from `s.planSlice`/`s.structureSlice`, criticConfig OMITS `lenses`; converge via `next_action(..., max_rounds=config.maxRounds)` | T17 | §3.18 | L | pending |
| T19 | Route non-pass verdict → `qrspi_revise_amend.py --branch ${id}/slice-N`, re-critique within round budget; `cap_reached` → ship-with-disclosure | T18 | §3.19 | M | pending |
| T20 | Handle per-slice-critic spawn failure (`ok:false`) → `skip(...)` | T18 | §3.20 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Per-slice critic loop complete. Residual-findings PR-body surfacing + the new agent prompt + config-example are the remaining additive pieces; a fresh context handles them plus the slice-3 manual end-to-end verification without carrying loop-internals detail.

## Session 5 — Slice 3c: Surface findings + agent prompt + config + verify

**Load:** structure.md §Contracts (critic_body slice branch), structure.md §Unverified Assumptions, design.md §residual-findings + §coherence-critic-agent, plan.md §Slice 3 (steps 21–24), impl-log.md §Slice 3a/3b (notes only)
**Estimated context:** ~28% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T21 | Surface residual findings via `qrspi_critic_body.py --phase slice`: slice-1 body = per-slice + carried coherence findings; slice-N body = own findings | T19, T20, T10 | §3.21 | M | pending |
| T22 | Create `.claude/agents/qrspi-coherence-critic.md` — whole-stack coherence critic prompt; returns `{ pass, findings }` matching `qrspi-critic` shape | — | §3.22 | M | pending |
| T23 | Modify `.qrspi/config.example.json` — add `critics.implementation` block `{ enabled, maxRounds, coherence: { enabled, maxRounds } }`, default OFF; conditional wrapper-doc touch only if step 11 confirmed | T11 | §3.23 | S | pending |
| T24 | **Verify Slice 3** — documented manual e2e on multi-slice ticket: coherence runs once + in slice-1 body; per-slice runs per non-first/non-committed slice, skips on `alreadyCommitted` + single-slice; per-slice findings in each body; forced `ok:false` → `skip`; config absent → disabled; result-summary reports run; `qrspi_slice_critic_test.py` + `qrspi_critic_body_test.py` still pass | T21, T22, T23 | §3.24 | L | pending |
