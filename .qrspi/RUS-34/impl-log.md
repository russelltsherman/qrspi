# Implementation Log — Wire up agent execution runtime in run_eval.py

## Session 1 — Slice 1

**Timestamp:** 2026-06-11T03:05:09Z
**Tasks completed:** T1, T2, T3, T4, T5, T6, T7, T8, T9, T10, T11, T12, T13
**Tasks failed:** none
**Tests:**

- `python3 scripts/run_eval_test.py` (run with `env -u ANTHROPIC_API_KEY`, `anthropic` not installed) → 6 passed, 0 failed
- Checkpoint: `call_model` present, `executed` field present on `ExecutionResult`, `anthropic` not in `sys.modules` after import → OK
- `python3 scripts/run_eval.py --help` → parser builds; `--skill`/`--agent` shown as a mutually-exclusive required pair

**Deviations from structure.md:**

- `execute_single` signature gained two params (`model: str`, `max_tokens: int`) — this was explicitly flagged in structure.md "Unverified Assumptions" ("execute_single signature must change to receive model/max_tokens") and authorized by plan step §1.4/§1.5. The `(case × trial)` fan-out shape is unchanged.

**Deviations from plan.md:**

- Missing-key behavior for `defaults` (left to the plan to decide, §1.4): chose **hard error with a clear message** for a missing `defaults.model` or `defaults.max_tokens`, rather than a silent fallback. Rationale: `evals/suite.json` declares `max_tokens` but no `model`, and a real call cannot proceed without a model id — surfacing it is correct. Raised in `run_suite` before any execution.
- `anthropic` pin: used `anthropic==0.49.0` exactly as the plan suggested. The SDK is not installed in this environment, so the pin could not be confirmed against an installed version (Slice 2 / live run will exercise it). The `usage` field mapping assumes `input_tokens`/`output_tokens` per the design's inferred shape.
- `--agent` alias implemented via an argparse mutually-exclusive required group (both flags share `dest="skill"`). This satisfies "same dest, args.skill unchanged downstream" and additionally rejects passing both at once.

**Notes for next session:**

- Slice 2 is a **live** acceptance run; no code changes. It needs a valid `ANTHROPIC_API_KEY` in the environment and will install `anthropic` (pin `anthropic==0.49.0` in `scripts/requirements.txt`).
- The questions suite (`evals/suite.json`) has `defaults.max_tokens=128000` but **NO `defaults.model`** — the live run will hard-error in `run_suite` until a `model` key is added to that suite's `defaults`. Add `"model": "<a valid model id>"` to `evals/suite.json` `defaults` (or to whichever suite Slice 2 targets) before running, or the run fails fast with the clear ValueError.
- Token normalization to `{input, output}` happens inside `call_model` at the seam boundary; `execute_single` passes the reply tokens through unchanged. SDK `usage` attrs assumed to be `input_tokens`/`output_tokens` — confirm against the installed `anthropic` during the live run.
- Per-request timeout is applied at the SDK call (`Anthropic(timeout=timeout_ms/1000)`); the `ThreadPoolExecutor`/`as_completed` wait has no `timeout=` (accepted per design Decision 3). No other blocking call exists in `execute_single`.
- `files`/`tool_calls` remain empty by design (SDK seam, option b).

---

## Session 2 — Slice 2 (Live end-to-end acceptance run, AC4)

**Timestamp:** 2026-06-11T12:15:05Z
**Tasks completed:** none
**Tasks failed:** T14, T15, T16, T17, T18 — BLOCKED (prerequisites unmet; HARD STOP)
**Tests:**

- T14 (confirm API key present) → FAIL: `ANTHROPIC_API_KEY` is **not set** in the environment.
- T15/T17 (live `--skill` / `--agent` run) → NOT RUN: blocked. (a) `anthropic` SDK is **not installed** (`ModuleNotFoundError: No module named 'anthropic'`); the `anthropic==0.49.0` pin in `scripts/requirements.txt` is therefore still unconfirmed against an installed version. (b) No API key. (c) `evals/suite.json` `defaults` has `trials_per_case=3`, `timeout_ms=120000`, `max_tokens=128000` but **no `model` key** — `run_suite` hard-errors with a clear `ValueError` until a `model` is added (exactly the blocker flagged in Slice 1's notes).
- T16/T18 (inspect real `results.json`) → NOT RUN: unreachable without a completed live run.

**Deviations from structure.md:**

- none (no code changes attempted; structure declares Slice 2 "Files touched: none")

**Deviations from plan.md:**

- none — but the slice could not be executed. Slice 2 is, by design, a **live** acceptance run that "requires a real API key and incurs the ~$20 acceptance cost" (structure.md Slice 2 Goal; plan steps 14–18). Its verification signal (`results[*].executed == True`; real, non-stub `output`/`tokens`/`transcript`) cannot be satisfied by stubbing — stubbing would defeat the slice's purpose.

**Blocking prerequisites (none resolvable within this slice's scope):**

1. `ANTHROPIC_API_KEY` must be present in the environment. It is not, and supplying a key is outside this agent's scope.
2. `anthropic==0.49.0` must be installed (`pip install -r scripts/requirements.txt`). It is not installed; installing it and confirming the pin is a setup step, not a Slice 2 code task.
3. `evals/suite.json` `defaults` must gain a valid `"model": "<model id>"` key, or `run_suite` hard-errors. Adding it is a file change, which this slice (Files touched: none) forbids.

**Outcome:** STOP — reported to orchestrator. No files modified. Network egress to `api.anthropic.com:443` is reachable from the sandbox, so once a key is present, the SDK is installed, and a `model` is added to the suite defaults, the documented `--skill`/`--agent` invocations can be run to produce a real `results.json`.

**Notes for next session:**

- This was the final planned slice (Slice 2 of 2). It is **incomplete/blocked**, not done. Re-running it requires the three prerequisites above resolved by a human/operator (real API key, installed SDK, a `model` added to `evals/suite.json` defaults) — none of which an isolated implement-phase slice agent can or should perform.
- Slice 1's runtime is verified offline (Session 1: `scripts/run_eval_test.py` 6 passed). The remaining gap is purely the live AC4 confirmation.

---
