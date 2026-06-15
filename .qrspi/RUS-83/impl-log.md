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
