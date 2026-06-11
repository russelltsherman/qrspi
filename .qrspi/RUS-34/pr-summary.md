# PR: Wire up agent execution runtime in run_eval.py (RUS-34)

**Ticket:** RUS-34
**Design:** design.md @ 2026-06-09T00:00:00Z
**Structure:** structure.md @ 2026-06-11T00:00:00Z

## Summary

`scripts/run_eval.py`'s `execute_single` was a stub that returned hard-coded zeros
(`output=""`, `tokens={input:0,output:0}`, `transcript=messages`), so a run produced a
`results.json` indistinguishable from "nothing happened." This PR makes the runtime real:
`execute_single` now invokes the Anthropic Messages API through a single mockable seam
(`call_model`), populating `output`, `tokens` (normalized to `{input,output}`), and
`transcript` (input messages + the assistant turn), enforcing `timeout_ms` at the request
boundary, and setting a new `executed: bool` sentinel so an empty-but-real run is
distinguishable from the old stub. Model id and `max_tokens` are sourced from `suite.json`
`defaults` (a missing key is a hard error, not a silent fallback); `--agent` is added as an
alias for `--skill`. **Reviewer focus:** (1) the `call_model` seam keeps `anthropic` out of
module-import/test-collection (local import) so the stdlib-only test convention holds; (2)
the hard-error-on-missing-`defaults.model`/`max_tokens` decision; (3) **Slice 2 (the live
AC4 acceptance run) is BLOCKED, not done** — see Open Items and Testing Summary.

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: `execute_single` invokes the agent at the `--skill` path (alias `--agent`) | `scripts/run_eval.py:execute_single` (calls `call_model(system=skill_text, ...)`); `--agent` alias in `main()` | `scripts/run_eval_test.py:ExecuteSingleTest.test_success_populates_fields_and_executed_true` |
| AC2: capture output, files, token usage, full transcript | `scripts/run_eval.py:execute_single` populates `output`/`tokens`/`transcript`/`executed`; `call_model` concatenates text blocks + normalizes `usage`→`{input,output}` | `scripts/run_eval_test.py:test_success_populates_fields_and_executed_true`, `:test_tokens_normalized_to_input_output_keys`, `:ModuleContractTest.test_executed_field_present` |
| AC3: honor `timeout_ms` | `scripts/run_eval.py:call_model` (`anthropic.Anthropic(timeout=timeout_s)`); `execute_single` converts raise→`result.error` | `scripts/run_eval_test.py:test_timeout_maps_to_error_and_executed_false`, `:test_seam_raises_populates_error_and_executed_false` |
| AC4: a real run produces non-empty `results.json` with real model output for the questions cases | `scripts/run_eval.py` runtime (Slice 1); no new code — live verification only | **NOT VERIFIED — Slice 2 BLOCKED** (no `ANTHROPIC_API_KEY`, `anthropic` not installed, `evals/suite.json` `defaults` has no `model`). See Open Items. |

## Changes by Slice

### Slice 1: Real model execution behind a stubbable seam (+ unit tests + deps)

| File | Change | Lines |
|------|--------|-------|
| `scripts/run_eval.py` | modified | +113, -27 |
| `scripts/run_eval_test.py` | new | +140 |
| `scripts/requirements.txt` | new | +1 |

Adds `executed: bool` to `ExecutionResult`; adds the module-level `call_model(...)` seam
(local `anthropic` import); rewrites `execute_single` to call the seam, populate fields,
normalize tokens, set `executed`, and convert any exception (incl. timeout) into
`result.error`; reads `defaults.model`/`defaults.max_tokens` in `run_suite` (hard error if
absent) and threads them through (`execute_single` gained `model`/`max_tokens` params);
adds `--agent` as a mutually-exclusive alias for `--skill` (exactly one required). Pins
`anthropic==0.49.0`.

### Slice 2: Live end-to-end acceptance run (AC4)

| File | Change | Lines |
|------|--------|-------|
| (none) | — | — |

No code change. Live verification of Slice 1's runtime against the real API. **Blocked** —
see Testing Summary and Open Items.

### Phase artifacts (not product code)

| File | Change | Lines |
|------|--------|-------|
| `.qrspi/RUS-34/design.md` | new | +108 |
| `.qrspi/RUS-34/impl-log.md` | new | +66 |
| `.qrspi/RUS-34/plan.md` | new | +90 |
| `.qrspi/RUS-34/questions.md` | new | +53 |
| `.qrspi/RUS-34/research.md` | new | +395 |
| `.qrspi/RUS-34/structure.md` | new | +66 |
| `.qrspi/RUS-34/worktree.md` | new | +47 |

## Testing Summary

- [x] Slice 1: unit tests — `python3 scripts/run_eval_test.py` (run with `env -u ANTHROPIC_API_KEY`, `anthropic` not installed) — 6 passed, 0 failed
- [x] Slice 1: collection isolation — `anthropic` absent from `sys.modules` after importing `run_eval`; `executed` field present on `ExecutionResult` — OK (`ModuleContractTest`)
- [x] Slice 1: CLI parser — `python3 scripts/run_eval.py --help` — parser builds; `--skill`/`--agent` shown as a mutually-exclusive required pair
- [ ] Slice 2: live AC4 run — `python3 scripts/run_eval.py --skill <agent> --suite evals/suite.json --output <dir>` — **NOT RUN (BLOCKED):** `ANTHROPIC_API_KEY` not set; `anthropic==0.49.0` not installed (pin unconfirmed against an installed version); `evals/suite.json` `defaults` has no `model` key (`run_suite` hard-errors by design until added)
- [ ] Slice 2: `--agent` alias invokes identically to `--skill` — NOT RUN (blocked on the same prerequisites)

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| `execute_single` signature | "Signature unchanged" (structure Contracts), but flagged in Unverified Assumptions as needing model/max_tokens threading | Gained `model: str`, `max_tokens: int` params | Explicitly anticipated in structure.md Unverified Assumptions ("must change to receive model/max_tokens") and authorized by plan §1.4/§1.5; `(case × trial)` fan-out shape unchanged |
| Missing-key behavior for `defaults` | Undefined (structure Unverified Assumptions: "error vs. fallback undefined") | Hard `ValueError` in `run_suite` for missing `defaults.model` or `defaults.max_tokens` | Left to plan to decide (§1.4); a real call cannot proceed without a model id — surfacing it is correct |
| `anthropic` pin | "minimal pinned `anthropic`" | `anthropic==0.49.0` in `scripts/requirements.txt` | SDK not installed in this env, so the pin is unconfirmed against an installed version; Slice 2 / live run will exercise it |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| Tests hit the live API / require a key, breaking the stdlib-only `python3` convention | mitigated — all model calls route through `call_model`, stubbed in tests; `anthropic` imported locally, absent from `sys.modules` at collection (verified by `ModuleContractTest`) | n/a |
| Empty real run byte-identical to the old stub in `results.json` | mitigated — `executed: bool` sentinel added (`True` only after a real call returns) | Revert the `executed` field + seam in `scripts/run_eval.py` |
| Fixtures silently dropped when runner not invoked from `evals/` | accepted / out of scope — deferred to a separate ticket (OQ4) | n/a (untouched) |
| New `anthropic` dependency with no requirements file present | mitigated — `scripts/requirements.txt` pins `anthropic==0.49.0`; import kept local to the seam | Delete `scripts/requirements.txt` + the local import |
| `tokens` dict shape may not match SDK `usage` keys | mitigated in code — `call_model` normalizes `usage.input_tokens`/`output_tokens`→`{input,output}` at the seam; **discovered-new:** the exact SDK `usage` attr names are assumed (`anthropic` not installed) and remain unconfirmed until the live run | Adjust the `getattr(usage, ...)` mapping in `call_model` once confirmed |
| **Discovered (new):** `evals/suite.json` `defaults` declares `max_tokens` but no `model` | discovered-new — Slice 1's hard error means the documented AC4 command fails fast until a `model` is added to that suite's `defaults` | Add `"model": "<valid model id>"` to `evals/suite.json` `defaults` |

## Open Items

- **Slice 2 (live AC4 acceptance run) is BLOCKED and incomplete.** Three operator-level prerequisites must be resolved by a human (none performable by an isolated implement-phase slice agent):
  1. `ANTHROPIC_API_KEY` present in the environment.
  2. `anthropic==0.49.0` installed (`pip install -r scripts/requirements.txt`) — also confirms the pin and the assumed `usage` attribute names (`input_tokens`/`output_tokens`).
  3. A valid `"model"` added to `evals/suite.json` `defaults` (it currently has `trials_per_case`, `timeout_ms`, `max_tokens=128000` but no `model`), or `run_suite` hard-errors by design.
  Network egress to `api.anthropic.com:443` is reachable from the sandbox; once the three are resolved the documented `--skill`/`--agent` invocations can produce a real `results.json` (~$20 cost ceiling across the 15 questions cases).
- **Deferred (separate ticket, OQ4):** `fixtures/...` CWD-relative path rooting — fixtures are silently dropped when the runner is not invoked from `evals/`.
- **Tech-debt seam (option b):** `files` and `tool_calls` stay empty under the direct-SDK path; real agent-loop / tool-lockdown capture is the explicitly tracked follow-up (design Decision 1).
