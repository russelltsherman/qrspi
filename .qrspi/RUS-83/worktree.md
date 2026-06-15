# Work Tree — CI-revise loop cap must count failed revise attempts (close AC6 hole from RUS-81)

**Plan basis:** plan.md @ 2026-06-15T00:00:00Z
**Generated:** 2026-06-15T00:00:00Z
**Status:** draft
**Total sessions:** 3
**Critical path:** T1 → T2 → T3 → T4 → T7 → T8 → T9 → T10 → T14 → T15 → T16 → T19 → T21

## Session 1

**Load:** structure.md §Contracts, structure.md §Slice 1 (Files touched), plan.md §Slice 1, design.md §Delta bullet 1
**Estimated context:** ~18% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create `scripts/qrspi_ci_revise_bump.py` skeleton — self-locating preamble, `--ticket`/`--branch`/`--stack` argparse | — | §1.1 | S | pending |
| T2 | Add pure `bump_ci_revise_trailer(message)->str` — last-occurrence-wins parse, single rewritten `CI-Revise-Attempt: prior+1` trailer, byte-preserve subject + other trailers | T1 | §1.2 | M | pending |
| T3 | Add imperative shell — checkout, read head msg, apply bump, `gt modify -m`, `gt submit` publish (+`--stack`), verify single trailer, JSON output, non-zero on failure (confirm publish flags vs `qrspi_revise_amend.py`) | T2 | §1.3 | M | pending |
| T4 | Create `scripts/qrspi_ci_revise_bump_test.py` — stdlib-only pure-core cases (absent⇒1, 2⇒3, single trailer, subject preserved, other trailers preserved, last-occurrence-wins) | T2 | §1.4 | M | pending |
| T5 | Run `python3 scripts/qrspi_ci_revise_bump_test.py` (expect all pass, exit 0) | T4 | §1.5 | S | pending |
| T6 | Run `python3 scripts/run_tests.py bump` (expect runner discovers + green) | T4 | §1.6 | S | pending |
| T7 | **Verify Slice 1** — pure-core standalone green, runner-discovered green, manual throwaway-branch increment (0→1→2, single trailer, subject intact) + simulated `gt` failure → non-zero + `ok:false` | T3, T5, T6 | §1.7 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete (new helper script + tests shipped). Fresh context for Slice 2 — a disjoint file set (resolver, not the helper); only the trailer-parse semantics carry forward as a note.

## Session 2

**Load:** structure.md §Modified Types, structure.md §Slice 2 (Files touched), plan.md §Slice 2, design.md Decision 2 / Decision 3, impl-log.md §Slice 1 (trailer-parse semantics note only)
**Estimated context:** ~16% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T8 | Modify `scripts/qrspi_resolve_state.py` — add `ciGaveUp: bool` to decision builder, default `False` on every path (mirror `ciFailing`) | T7 | §2.8 | M | pending |
| T9 | Modify `scripts/qrspi_resolve_state.py` — on cap-reached red→`wait` branch set `ciGaveUp=True` + distinct reason; do NOT change the `attempt < cap` comparison | T8 | §2.9 | S | pending |
| T10 | Modify `scripts/qrspi_resolve_state_test.py` — cap-reached red→`wait`+`ciGaveUp==True`+reason; under-cap red→`revise`+`ciGaveUp==False`; non-CI `wait`→`ciGaveUp==False` | T9 | §2.10 | M | pending |
| T11 | Run `python3 scripts/qrspi_resolve_state_test.py` (expect new + existing pass) | T10 | §2.11 | S | pending |
| T12 | Run `python3 scripts/run_tests.py resolve` (expect green) | T10 | §2.12 | S | pending |
| T13 | Run `python3 scripts/run_tests.py` (full suite — confirm additive defaulted field regresses no consumer) | T10 | §2.13 | S | pending |
| T14 | **Verify Slice 2** — resolver test green (new+existing), `run_tests.py resolve` green, full suite green | T11, T12, T13 | §2.14 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 2 complete (resolver `ciGaveUp` field + tests). Fresh context for Slice 3 — the JS wiring slice depends on both the helper (Slice 1) and the `ciGaveUp` field (Slice 2) existing, and is verified by manual e2e rather than unit tests; load only the contracts of those two prior outputs, not their full diffs.

## Session 3

**Load:** structure.md §Slice 3 (Files touched), plan.md §Slice 3, design.md §Delta JS bullets / OQ1 / Risk Register row 4, impl-log.md §Slice 1 (helper CLI contract) + §Slice 2 (`ciGaveUp` field), MEMORY: batch-worker-cwd-engine-path
**Estimated context:** ~22% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T15 | Modify `.claude/workflows/qrspi-batch.js` (`doRevise` worker prompt) — DELETE the step-6 worker instruction to write `CI-Revise-Attempt: prior+1`; worker no longer touches the counter | T14 | §3.15 | M | pending |
| T16 | Modify `.claude/workflows/qrspi-batch.js` (`doRevise`) — after content worker returns on red, run `qrspi_ci_revise_bump.py` **unconditionally** once per still-red branch (impl: lowest-first); invoke via thin worker using `engineCmdFor`/`r.repoRoot` (NOT `engineCmd`'s `.`) | T15 | §3.16 | L | pending |
| T17 | Modify `.claude/workflows/qrspi-batch.js` (`doRevise`) — confirm non-CI `resetCiReviseTrailer` reset-to-0 path UNCHANGED (verify-only, no edit) | T16 | §3.17 | S | pending |
| T18 | Modify `.claude/workflows/qrspi-batch.js` (`wait`-branch result/skip record + per-ticket log) — surface `ciGaveUp` into recorded result object + log line | T16 | §3.18 | S | pending |
| T19 | Modify `.claude/workflows/qrspi-batch.js` (`doRevise` result record) — record a non-zero helper exit as a hard failure so a non-advancing count is never silent | T16 | §3.19 | M | pending |
| T20 | Note: `qrspi-batch.js` is harness-coupled, not unit-testable — Slice 3 verified by manual e2e + full Python suite (no new JS unit tests) | T15 | §3.20 | S | pending |
| T21 | **Verify Slice 3** — e2e on unfixable red PR: helper advances trailer +1/pass; repeat to cap⇒`wait`+`ciGaveUp==True` surfaced in JS record/log; green pass⇒gather read-side reset to 0; `python3 scripts/run_tests.py` full suite green | T16, T17, T18, T19, T20 | §3.21–3.24 | M | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 3 complete — all three slices implemented and verified. Feature is ready for PR preparation (`/qrspi-pr`); no further implementation session needed.
