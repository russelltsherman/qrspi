# Implementation Log — Critic effectiveness: instrumentation, cost reduction, teeth eval

## Session 1 — Slice 1

**Timestamp:** 2026-06-15T02:28:37Z
**Tasks completed:** T1, T2, T3, T4, T5, T6, T7
**Tasks failed:** none
**Tests:**

- `python3 scripts/run_tests.py metrics` → 2 test files passed (`qrspi_critic_metrics_test.py`, `qrspi_metrics_append_test.py`), 0 failed
- Manual: ran `qrspi_metrics_append.main` twice against a temp-pinned root — first call creates a 1-line ledger, second appends to 2 lines (no overwrite), each line is the envelope-wrapped `CriticMetricsLedgerLine` (`{...CriticStepMetrics, ticketId, timestamp}`), and NO `.worktrees/<id>/.worktrees/<id>/…` double-nesting was created.

**Deviations from structure.md:**

- none

**Deviations from plan.md:**

- none

**Notes for next session:**

- Slice 2 wires these into `qrspi-batch.js`. The Slice-1 contracts are: reducer `qrspi_critic_metrics.build_record(verdicts, terminalAction, usage=None, phase=None) -> dict`; appender CLI `python3 scripts/qrspi_metrics_append.py --ticket <id> --record '<json>'`.
- `build_record`'s `verdicts` arg expects per-lens dicts each with `lens`, `pass`, `findings` (list). It maps to `{lens, pass: bool, findingsCount: len(findings)}` per round. JS must pass `findings` as a list (count is derived here, not in JS).
- `terminalAction` is validated against EXACTLY `{converged, cap_reached, exhausted, aborted}` (frozenset `qrspi_critic_metrics.VALID_TERMINAL_ACTIONS`). `revise` raises `ValueError` — JS must only call the reducer once the loop has actually TERMINATED, mapping the four `runCriticLoop`/`runCriticPanelLoop` return sites to these four values. Do NOT pass `revise`.
- Token fields are OMITTED unless `usage` supplies them; per OQ2 the live JS path supplies no usage, so `tokensIn`/`tokensOut` stay absent (cost dimension ships unmeasured — acknowledged at design level).
- The appender is the single envelope authority: it injects `ticketId` (from `--ticket`) and `timestamp` (UTC ISO-8601, generated at write time). JS should pass the BARE `CriticStepMetrics` record as `--record` and let the appender add the envelope; any `ticketId`/`timestamp` already in the record is overwritten by the appender.
- The appender resolves the host root via `qrspi_paths.resolve_repo_root(cwd=os.getcwd(), validate=False)` (git-common-dir first). It must be invoked with cwd inside the worktree so the resolver finds the MAIN checkout; the ledger lands at `<main>/.worktrees/<id>/.qrspi/<id>/critic-metrics.jsonl`.
- Appender fails closed (exit 1, writes nothing) on invalid/non-object `--record` JSON. Slice 2 should treat a non-zero exit as a step-instrumentation failure.
- Slice 2 still needs to gitignore `.qrspi/<id>/critic-metrics.jsonl` (structure.md Slice 2 verification item) — NOT done in Slice 1.

---

## Session 2 — Slice 2

**Timestamp:** 2026-06-15T02:36:00Z
**Tasks completed:** T8, T9, T10, T11, T12, T13 (T13 to the extent runnable in the implement-agent sandbox — see Tests)
**Tasks failed:** none

**Tests:**

- `python3 scripts/run_tests.py metrics` → 2 test files passed (`qrspi_critic_metrics_test.py`, `qrspi_metrics_append_test.py`), 0 failed — confirms the Slice-1 reducer is unbroken after adding its CLI shim
- `python3 scripts/run_tests.py` → 33 passed, 0 failed (full regression suite green)
- `node --check .claude/workflows/qrspi-batch.js` → JS-SYNTAX-OK (no parse errors after the wiring edits)
- Integration smoke test (the EXACT chained worker command, run from a temp main-checkout): reducer emits the bare `CriticStepMetrics` (Python-derived `findingsCount`), appender wraps it as the `CriticMetricsLedgerLine` envelope (`ticketId` + `timestamp`) and appends; a second call appends (no overwrite) → 2 lines; each ledger line is the envelope-wrapped record, NOT the bare record
- `git check-ignore -v .worktrees/RUS-77/.qrspi/RUS-77/critic-metrics.jsonl` → matches `.gitignore:3:.worktrees/` (ledger already gitignored; no `.gitignore` edit needed — see deviations)
- NOT runnable in this sandbox: the live critics-ENABLED vs critics-DISABLED end-to-end design run (T13 checkpoint) — it requires live agents/Linear. Verified instead by code inspection (disabled path: `criticConfig` falsy ⇒ loops un-dispatched in `runPhase` ⇒ no `recordCriticMetrics` call ⇒ no ledger write; `doDesign` surfaces zero records ⇒ `criticMetrics` key OMITTED ⇒ byte-for-byte-unchanged result object) + the integration smoke test of the enabled-path shell-out.

**Deviations from structure.md:**

- **Added a thin stdin→stdout CLI shim to the Slice-1 file `scripts/qrspi_critic_metrics.py`** (a `main()`/`__main__` over the pure `build_record`, mirroring `qrspi_critic_synthesize.py`). Structure.md/plan.md step 9 say "Build the record via the reducer (`qrspi_critic_metrics.py`)", and the impl-log Slice-1 note mandates `findingsCount` be derived in Python (not JS) — but Slice 1 shipped `build_record` with NO callable CLI, so the JS worker had no way to invoke the reducer. The shim is a PURE ADDITION (it does not touch `build_record`); it reads the verdicts JSON array on stdin and takes `--terminal-action`/`--phase`, emitting the bare `CriticStepMetrics`. This is the only faithful way to satisfy both "reduce via the reducer" and "count derived in Python". No type/signature of `build_record` changed.
- **`tokensIn`/`tokensOut` ship unmeasured** (OQ2, already acknowledged at design/structure level): the live JS path supplies no `usage`, so the CLI shim does NOT expose a usage flag and the cost fields stay absent. No behavioral deviation — matches the design.

**Deviations from plan.md:**

- **T8 (gitignore): NO `.gitignore` edit made**, per plan §8's own review finding (the worktree.md T8 row still says "add `**/.qrspi/*/critic-metrics.jsonl`", but plan §8 supersedes it as redundant). The ledger lands under `.worktrees/<id>/…`, already ignored by `.gitignore:3:.worktrees/` — verified via `git check-ignore`. Adding a `**/.qrspi/*/critic-metrics.jsonl` rule would be dead, so it was deliberately NOT added. The plan is the authority here over the stale worktree.md row.
- **Disabled-path result shape:** plan §12 explicitly requires the `criticMetrics` key be OMITTED on the fully-disabled path ("doDesign adds no `criticMetrics` key … byte-for-byte-unchanged result object"). Structure.md Modified Types lists `criticMetrics` as an added field, which could read as always-present. I followed plan §12 (the more specific authority for the disabled-path guarantee): `doDesign` adds the key ONLY when ≥1 record was surfaced; the disabled path returns the unchanged object.

**Notes for next session:**

- Slice 2 is the LAST instrumentation slice; Slice 3 (Session 3) is an independent tested Python config core + JS mirror — no Slice 2 internals are needed.
- Wiring summary for anyone touching the critic loops later: each loop (`runCriticLoop`, `runCriticPanelLoop`) now keeps a `metricRounds[]` accumulator of raw `{lens, pass, findings}` verdicts (single critic ⇒ `lens:null`; panel ⇒ one entry per lens per round) and, at EVERY return site (converged / cap_reached / exhausted / aborted — including all `ok:false` aborts), calls `recordCriticMetrics(id, name, metricRounds, terminalAction)` and returns the produced record on the envelope as `{ …, metrics }`. NEVER pass `revise` (mid-loop; the reducer rejects it).
- `recordCriticMetrics(id, phase, verdicts, terminalAction)` is the new JS helper (defined right after `synthesizeVerdicts`). It runs ONE chained worker command at main-repo-root cwd via `engineCmd('scripts/…')` (same convention as `synthesizeVerdicts`/`criticDecision`, because `r`/`repoRoot` is NOT in scope in the loops): pipe verdicts → `qrspi_critic_metrics.py --terminal-action <a> --phase <p>` → tee to a temp file → `qrspi_metrics_append.py --ticket <id> --record "$(cat tmp)"` → re-`cat` the record. The reducer record is the return value (for the result fold); the appender is the side-effecting durability gate (non-zero exit fails the chain ⇒ null ⇒ logged step-instrumentation failure). It is guarded by `CRITIC_METRICS_SCHEMA`.
- `runPhase` surfaces the record onto `criticConfig.criticMetrics` (same back-channel pattern as `criticConfig.residualFindings`/`criticSummary`), so it stays inside the existing `if (criticConfig)` guard and keeps its boolean return contract. `doDesign` collects `questionsCritic/researchCritic/designCritic .criticMetrics` (filter Boolean) into the result's `criticMetrics` array.
- The reducer CLI shim added here means `qrspi_critic_metrics.py` is now BOTH an importable pure module AND a CLI — if a later slice needs to extend the record, change `build_record` (pure, unit-tested) and the shim just re-exposes it.

---

## Session 3 — Slice 3

**Timestamp:** 2026-06-15T02:40:33Z
**Tasks completed:** T14, T15, T16, T17, T18
**Tasks failed:** none

**Tests:**

- `python3 scripts/run_tests.py critics_config` → 1 test file passed (`qrspi_critics_config_test.py`), 0 failed — all default-OFF/absent assertions, per-lever parse cases, and the JS-mirror parity test pass
- `python3 -m unittest scripts.qrspi_critics_config_test.JsMirrorParityTests -v` → 2 passed (confirms the parity test is non-vacuous; it actually parses `DEFAULT_CRITIC_PHASES` out of `qrspi-batch.js` and compares field-for-field — verified the parsed JS design block now carries `digest:{enabled:false}` + `gateBehindEdge:{enabled:false}` and NO `lensModel` key)
- `node --check .claude/workflows/qrspi-batch.js` → JS-SYNTAX-OK (mirror edit parses)
- `python3 -c "import json; json.load(open('.qrspi/config.example.json'))"` → VALID (example JSON still well-formed after documenting the three knobs)
- `python3 scripts/run_tests.py` → 33 passed, 0 failed (full regression suite green; no Slice-1/2 breakage)

**Deviations from structure.md:**

- **`lensModel` ships ABSENT (key omitted), not `None`.** structure.md Modified Types says `lensModel?: str` "defaulting OFF / absent". I resolved "absent" literally: when config supplies no (or an empty/whitespace/non-string) `lensModel`, the `resolve_design` result OMITS the key entirely rather than emitting `lensModel: None`. This keeps the default design block byte-identical to its pre-RUS-77 shape plus only the two nested gate blocks, and the JS `DEFAULT_CRITIC_PHASES.design` mirror likewise omits the key — so the lockstep parity test compares equal. (The `?` in `lensModel?: str` denotes optional/absent, so this matches the contract.)

**Deviations from plan.md:**

- none — steps 14–17 implemented as written; step 18 checkpoint passes.
- Note on step 15(e) parity mechanism: the plan left the parity-assertion form open ("e.g. load/compare the expected default dict literal kept in sync with step 16"). I implemented it as a `JsMirrorParityTests` class that parses the live `DEFAULT_CRITIC_PHASES` object literal out of `.claude/workflows/qrspi-batch.js` by regex (the JS file is harness-coupled / not importable, per the codebase convention note) and compares it field-for-field against `default_phases()`. This is a stronger lockstep guard than a hand-maintained dict literal because it reads the ACTUAL JS source, so a future drift in either side fails the test. The parser resolves the `DEFAULT_DESIGN_LENSES` reference, strips `//` comment lines, quotes bare keys, and drops trailing commas before `json.loads`.

**Notes for next session:**

- Slice 3 is config-only: `resolve_design(config)` now returns the extended `DesignCriticConfig` with `digest:{enabled}`, `gateBehindEdge:{enabled}` (both default `{"enabled": False}`) and an OPTIONAL `lensModel` (string, key absent unless config supplies a non-empty string). No wiring consumes these yet — Slice 4 (T19–T32) is where the levers actually do work.
- The uniform `enabled` vocabulary is reused: `digest`/`gateBehindEdge` inner `enabled` go through `resolve_enabled(cfg, False)`, so only an explicit boolean flips them; a non-dict outer value or non-bool inner value falls back to the default-OFF block.
- For Slice 4, read the gates off the resolved design config as: `criticConfig.digest.enabled`, `criticConfig.gateBehindEdge.enabled`, and `criticConfig.lensModel` (test for key presence — it may be absent). The JS `DEFAULT_CRITIC_PHASES.design` fallback guarantees `digest`/`gateBehindEdge` blocks are always present on a default-config read; `lensModel` is NOT in the fallback, so Slice 4 must treat it as optional (`criticConfig.lensModel` may be `undefined`).
- LOCKSTEP CONTRACT: any future change to `resolve_design`'s default shape MUST be mirrored in `DEFAULT_CRITIC_PHASES` in `qrspi-batch.js`, or `JsMirrorParityTests` fails. Keep the Python default and the JS mirror reverted/changed together.
- `.qrspi/config.example.json` documents the three knobs under `critics.design` via a `$comment_cost_levers` key + representative default-OFF values (`digest.enabled:false`, `gateBehindEdge.enabled:false`; `lensModel` is described in the comment but NOT shown as a key, since its default is absent).

---
