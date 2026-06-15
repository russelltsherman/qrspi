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
