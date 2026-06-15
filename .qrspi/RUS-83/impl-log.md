# Implementation Log — CI-revise loop cap must count failed revise attempts (close AC6 hole from RUS-81)

## Session 1 — Slice 1

**Timestamp:** 2026-06-15T22:10:00Z
**Tasks completed:** T1, T2, T3, T4, T5, T6, T7
**Tasks failed:** none
**Tests:**

- `python3 scripts/qrspi_ci_revise_bump_test.py` → 16 passed, 0 failed
- `python3 scripts/run_tests.py bump` → 1 file passed, 0 failed (runner discovers the new test)
- Manual fail-closed check: `qrspi_ci_revise_bump.py --ticket NOPE-999 --branch NOPE-999/design` → exit 1 + `ok:false` JSON with `error: "worktree not found: ..."`

**Deviations from structure.md:**

- none

**Deviations from plan.md:**

- none. T7's live throwaway-branch `gt modify`/`gt submit --publish` round-trip (0→1→2 on a real branch) was NOT executed: it mutates a live PR head and is outside Slice 1's safe-to-run scope. The imperative `gt` shell follows the SAME verified-by-design + manual-e2e trust model as `qrspi_revise_amend.py` (its `gt` mechanics are likewise not unit-tested); the pure rewrite core and the fail-closed path ARE verified here. The live publish round-trip is exercised in Slice 3's end-to-end checkpoints.

**Notes for next session:**

- **Trailer-parse contract (shared serialization):** The trailer regex is `^CI-Revise-Attempt:\s*(\d+)\s*$` with `re.MULTILINE`, last-occurrence-wins, absent/malformed/None ⇒ `0`. This is byte-identical to the gather's `qrspi_pr_state.ci_revise_attempt` (verified against `scripts/qrspi_pr_state.py:112`). Slice 2's resolver reads the gathered count; it must NOT re-parse the trailer — keep using `ciReviseAttempt` from the gather.
- **Helper CLI contract (for Slice 3 `doRevise` wiring):** `python3 scripts/qrspi_ci_revise_bump.py --ticket <id> --branch <branch> [--stack]`. `--stack` is a boolean flag (present ⇒ `gt submit --publish --stack --no-edit --no-interactive` for implementation; absent ⇒ no `--stack` for design/plan). Prints JSON `{ ok, branch, prior, new, error? }` to stdout and exits **non-zero** on any failure (fail-closed). It is self-locating (resolves repo root via `qrspi_paths.resolve_repo_root`), so Slice 3 must invoke it via `engineCmdFor(r, 'scripts/qrspi_ci_revise_bump.py')` / `r.repoRoot`, NOT `engineCmd`'s `.` (per MEMORY: batch-worker-cwd-engine-path).
- **Pure increment core:** `bump_ci_revise_trailer(message) -> (new_message, prior, new_value)`. It strips ALL existing `CI-Revise-Attempt:` lines and appends exactly one `CI-Revise-Attempt: <prior+1>` as the last line, trimming trailing blank lines first; subject + every other trailer preserved byte-for-byte; result ends with a single `\n`. This is the sole increment authority — Slice 3 deletes the worker's hand-rolled step-6 trailer write and calls this helper unconditionally per still-red branch instead.
- **Publish form confirmed:** `gt modify --no-interactive -m <message>` (message-only amend, no staging) then `gt submit --publish --no-edit --no-interactive` (+`--stack` for implementation). Matches the canonical forms in `qrspi-batch.js` (revise re-publish at line ~2343/2406) — no flag deviation.

---

## Session 2 — Slice 2

**Timestamp:** 2026-06-15T23:05:00Z
**Tasks completed:** T8, T9, T10, T11, T12, T13, T14
**Tasks failed:** none
**Tests:**

- `python3 scripts/qrspi_resolve_state_test.py` → 68 passed, 0 failed (was 60; +8 new `ciGaveUp` cases)
- `python3 scripts/run_tests.py resolve` → 2 files passed, 0 failed
- `python3 scripts/run_tests.py` → 40 files passed, 0 failed (full suite green)

**Deviations from structure.md:**

- none

**Deviations from plan.md:**

- none functional. The plan (steps 8–14) listed only `qrspi_resolve_state.py` + `qrspi_resolve_state_test.py` as touched. Adding the additive `ciGaveUp` field to the resolver decision dict tripped one byte-pinned golden — `scripts/fixtures/contract_seam/resolve/wellformed.json` (consumed by `qrspi_contract_fixtures_producer_test.py::test_resolve`, which byte-matches the producer's serialized envelope). This is the expected consequence of step 13's "confirm the additive defaulted field regresses no consumer" gate catching the one consumer that pins exact serialization. The golden was **regenerated mechanically from the producer itself** (re-ran `qrspi_resolve.build_envelope(qrspi_resolve_state.resolve(...))` and rewrote the file with the same `json.dumps(env, indent=2) + "\n"` form `main()` uses) — NOT hand-edited — so it stays a faithful pin. Net effect: `ciGaveUp: false` is now inserted in the embedded decision dict between `ciFailing` and `reason`, matching the resolver's key order. No logic, no other consumer changed.

**Notes for next session:**

- **`ciGaveUp` decision-field contract (for Slice 3 JS surfacing, T18):** Every decision dict now carries `ciGaveUp: bool`, defaulting `False` on every path (added to the `decision(...)` builder in `qrspi_resolve_state.py`, mirroring `ciFailing`). It is set `True` **only** on the cap-reached red→`wait` branch (`fci == "red"` and `attempt >= ci_revise_cap`). The give-up `wait` decision also carries `ciFailing: True`. Slice 3 reads `d.ciGaveUp` (or the envelope's re-emitted copy if step 21 re-emits it like `ciFailing`) — it must NOT re-derive give-up from `attempt`/`cap`; the resolver is the sole authority.
- **Distinct give-up reason string:** the cap-reached `wait` reason now reads `"<phase> frontier PR still has failing CI after <a>/<cap> consecutive auto-revise attempt(s); CI-revise cap reached — gave up auto-revising, parked for manual diagnosis."` (contains the substrings `"cap reached"` and `"gave up"`, asserted by the new test). Any JS log line that wants a human-readable park reason can use `d.reason` directly.
- **Additive field, byte-pinned golden caveat:** any FUTURE additive field on the resolver decision dict will likewise trip `qrspi_contract_fixtures_producer_test.py::test_resolve` — regenerate `scripts/fixtures/contract_seam/resolve/wellformed.json` from the producer (do NOT hand-edit) the same way this slice did. The `prose_wrapped` / `unknown_action` / `no_json` resolve variants are consumer-side parser-tolerance fixtures (not byte-pinned producer output) and did NOT need the new field.
- **No write-side coupling:** Slice 2 only READS the gathered `ciReviseAttempt` (via `ci_revise_attempt_of`) to compute `ciGaveUp`; it does not write the trailer. The trailer increment authority remains Slice 1's `qrspi_ci_revise_bump.py`. Slice 3 wires the two together.

---

## Session 3 — Slice 3

**Timestamp:** 2026-06-15T23:55:00Z
**Tasks completed:** T15, T16, T17, T18, T19, T20, T21 (plan steps 15–21)
**Tasks failed:** none
**Tests:**

- `python3 scripts/qrspi_resolve_test.py` → 133 passed, 0 failed (+18 new `red_branches_of` / `ciRedBranches` cases)
- `python3 scripts/run_tests.py resolve` → 2 files passed, 0 failed
- `python3 scripts/run_tests.py` → 40 files passed, 0 failed (full suite green)
- `node --check .claude/workflows/qrspi-batch.js` → SYNTAX OK
- Deterministic e2e sanity (in-process): `build_envelope` emits `ciRedBranches == ["RUS-9/slice-1","RUS-9/slice-3"]` for an impl `[red,green,red]` stack, `["RUS-9/design"]` for a red design frontier, `[]` for a non-CI decision

**Deviations from structure.md:**

- none

**Deviations from plan.md:**

- **Byte-pinned golden regenerated (same caveat Slice 2 hit, now for a top-level field):** adding `ciRedBranches` to the envelope tripped `scripts/fixtures/contract_seam/resolve/wellformed.json` (consumed by `qrspi_contract_fixtures_producer_test.py::test_resolve`, which byte-matches the producer's serialized envelope). Plan step 15 listed only `qrspi_resolve.py` + `qrspi_resolve_test.py`; this golden + the producer test's shape-key list are the two additional touch points the additive top-level field forces. The golden was **regenerated mechanically from the producer** (re-ran `build_envelope(resolve(...))` with the same `json.dumps(env, indent=2) + "\n"` form `main()` uses), NOT hand-edited — `ciRedBranches: []` is inserted between `ciFailingChecks` and `reviewers`, matching dict key order. Net: additive, no logic/consumer change.
- **Live-PR e2e checkpoints (plan steps 23–27) NOT executed:** the unfixable-red / multi-slice-selectivity / non-CI-reset / cap / green-reset checkpoints require a live PR with red CI and mutate live PR heads via `gt submit` (the helper publishes). Per the QRSPI hard constraint (this agent runs no git/gt mutations — the orchestrator owns commits/publishes) and the Slice 1 precedent (its live `gt` round-trip was likewise deferred), those are deferred to a real batch run. The deterministic core (`ciRedBranches` aggregation, envelope re-emit, resolver passthrough, JS wiring shape + Node syntax) and the full Python suite ARE verified here.

**Notes for next session:**

- Slice 3 is the final slice. Feature is ready for `/qrspi-pr`.
- **Single-writer-per-path invariant (now orchestrator-owned, three-way matched set):** the worker step-6 `CI-Revise-Attempt` block was DELETED (worker never touches the counter). In `doRevise`, AFTER the step-2b content worker returns: (1) CI path (`ciFailing`) → `bumpCiReviseTrailers(t, r, d)` fires UNCONDITIONALLY (regardless of worker `ok`, regardless of `changeRequested`), iterating `r.ciRedBranches` lowest-first, each via a thin worker running `qrspi_ci_revise_bump.py --ticket --branch [--stack]` (engineCmdFor/r.repoRoot). (2) Non-CI path (`changeRequested && !ciFailing`) → `resetCiReviseTrailer(t, r, d, answered)` fires UNCONDITIONALLY (idempotent). Step-2a's gated reset (`answered.some(a => a.applied)`) is UNCHANGED.
- **`ciRedBranches` is the deterministic red-branch list** (new top-level envelope field via pure `red_branches_of(decision, phases, ticket)` in `qrspi_resolve.py`): impl → each red slice as `"<t>/slice-<n>"` ascending; red design/plan frontier → `["<t>/<phase>"]`; non-CI/None → `[]`. doRevise iterates it directly — it never re-derives per-slice CI nor delegates "which slices are red" to an LLM worker.
- **`ciGaveUp` surfacing:** `skip()` now carries `ciGaveUp` onto the wait/skip record from `decision.ciGaveUp`; the wait-case log and the final per-ticket log line both annotate "CI-revise cap reached — auto-revise gave up, manual diagnosis needed". A revise result also passes `ciGaveUp` through verbatim (always False on a revise, since give-up resolves to `wait`).
- **Helper non-zero exit = hard failure (OQ1):** `bumpCiReviseTrailers` returns `{ ok, bumped, failures }`; a non-zero/`ok:false` helper exit sets `out.ciReviseBumpFailed = true` and appends "CI-Revise-Attempt counter FAILED to advance on: <branches>" to the revise summary, and the final per-ticket log line flags it — a count that could not advance is never silent.
- **`CI_REVISE_BUMP_SCHEMA`** (new) pins the thin bump worker's parsed output to `{ ok, branch, prior?, new?, error? }` read off the script STDOUT (not exit code alone).

---
