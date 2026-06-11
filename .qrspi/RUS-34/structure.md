# Structure Outline — Wire up agent execution runtime in run_eval.py

**Design basis:** design.md @ 2026-06-09T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** draft

## New Types

- No brand-new types. The change is one new field on an existing dataclass (see Modified Types) plus one new module-level function (see Contracts).

## Modified Types

- `ExecutionResult` — add field `executed: bool` (default `False`); status sentinel set `True` once a real model call returns, `False` for the stub/zeroed path. JSON-serializable, flows through `dataclasses.asdict` unchanged (ref: design.md §Delta, AC2, OQ2).

## Contracts

- `call_model(system: str, messages: list[dict], model: str, max_tokens: int, timeout_s: float) -> ModelReply` — single mockable seam wrapping the Anthropic Messages API. `ModelReply` is the loose return shape `{output: str, tokens: {"input": int, "output": int}, raw_transcript_turn: dict}`. Imports `anthropic` locally (inside the function body), reads the API key from the SDK's standard environment variable, applies `timeout_s` as the request-level timeout. Tests stub this function so no network/import happens at collection time (ref: design.md Decision 2, Risk: tests-hit-live-API).
- `execute_single(skill_text: str, case: dict, trial_id: str, timeout_ms: int) -> ExecutionResult` — rewritten body: builds messages via existing `build_messages(case)`, calls `call_model(system=skill_text, messages=..., model=defaults.model, max_tokens=defaults.max_tokens, timeout_s=timeout_ms/1000)`, populates `output`, `tokens` (normalized to `{input,output}` keys), `transcript` (input messages + assistant turn), sets `executed=True`; on exception (incl. timeout) writes `result.error` and leaves `executed=False`. `files`/`tool_calls` stay empty (SDK seam for option b). Signature unchanged (ref: design.md §Delta, AC1–AC3).
- `--agent` argparse alias for `--skill` — `--skill` stays the primary/required name; `--agent` resolves to the same `dest` so `args.skill` is unchanged downstream (ref: design.md Decision 4, OQ1).
- Model id + `max_tokens` source: `suite.json` `defaults.model` / `defaults.max_tokens`, read in `run_suite` (where the loaded suite is in scope) and threaded into `execute_single`/`call_model` (ref: design.md §Delta, OQ3). NOTE — `execute_single`'s current public signature carries no `model`/`max_tokens` params; threading these in is an implementation detail flagged in Unverified Assumptions.

## Slice 1: Real model execution behind a stubbable seam (+ unit tests + deps)

**Goal:** `execute_single` performs a real Anthropic Messages call through the `call_model` seam, populating `output`/`tokens`/`transcript`/`executed`/`error` and honoring `timeout_ms`, all verifiable offline via stdlib-only tests that stub `call_model` (no network, no API key). This is one cohesive unit — the seam, the dataclass field, the model/max_tokens threading, the `--agent` alias, the requirements file, and the test sibling are mutually dependent and share a single offline verification signal.

**Files touched:**

- ⚠️ `scripts/run_eval.py` — add `executed: bool` to `ExecutionResult`; add module-level `call_model(...)` seam (local `anthropic` import); rewrite `execute_single` to call the seam, populate fields, normalize `tokens` to `{input,output}`, set `executed`, enforce `timeout_ms` at the call boundary and convert exceeded/raised into `result.error`; read `defaults.model`/`defaults.max_tokens` in `run_suite` and thread them through; add `--agent` as an argparse alias for `--skill`. Keep `load_skill`, `load_suite`, `build_messages`, the envelope, and the `run_suite` fan-out shape unchanged.
- ✨ `scripts/run_eval_test.py` — stdlib-only `_test.py` sibling; stubs `call_model` (monkeypatch the module attribute, never import `anthropic`); asserts populated `output`/`tokens`/`transcript` and `executed=True` on success; asserts a raised seam → populated `result.error` + `executed=False`; asserts timeout maps to `result.error`; asserts `tokens` is normalized to `{input,output}` keys.
- ✨ `scripts/requirements.txt` (or repo-root equivalent) — minimal pinned `anthropic` dependency; none exists today.

**Verification:**

- [ ] `python3 scripts/run_eval_test.py` passes (success-path fields, error capture, timeout-to-error, token normalization) with no network access and no API key set.
- [ ] Module imports and test collection do not import `anthropic` (the import is local to `call_model`); confirm by running the test with `anthropic` absent from the environment.
- [ ] `python3 -c "import scripts.run_eval"` (or equivalent) succeeds with the new field and alias present.

**Context cost:** M
**Depends on:** none

## Slice 2: Live end-to-end acceptance run (AC4)

**Goal:** The documented command produces a non-empty `results.json` whose `results[*].output`/`tokens`/`transcript` reflect real model responses for the questions cases and carry `executed=True`, distinguishable from the zeroed stub. This is a separate slice solely because its verification signal is distinct from Slice 1 — it requires a real API key and incurs the ~$20 acceptance cost, so it cannot run in the offline unit-test gate.

**Files touched:**

- (none — no new code; this slice is the live verification of Slice 1's runtime against the real API)

**Verification:**

- [ ] Run the documented `--skill` invocation against the questions suite with a valid API key; confirm `results.json` is non-empty, `results[*].executed == True`, and `output`/`tokens`/`transcript` are real (non-zero, non-stub) for the questions cases.
- [ ] Confirm the run stays within the ~$20 cost ceiling across the 15 questions cases.
- [ ] Confirm `--agent` alias invokes identically to `--skill`.

**Context cost:** S
**Depends on:** Slice 1

---

## Unverified Assumptions

- **`execute_single` signature must change to receive `model`/`max_tokens`.** The design pins `execute_single(skill_text, case, trial_id, timeout_ms)` as unchanged in shape, yet also requires model id and `max_tokens` to come from `suite.json` `defaults`. Those values live in the loaded suite, not in the current parameter list, so they must be threaded in (extra params, a closure, or a passed config). The design does not specify the mechanism — the plan phase must choose how the defaults reach the call without breaking the `(case × trial)` fan-out.
- **`ModelReply` return shape and `tokens` normalization are inferred, not specified.** The design states tokens must normalize to the existing `{input,output}` keys at the seam boundary but gives no concrete SDK `usage` field mapping. The exact `anthropic` `usage` attribute names (`input_tokens`/`output_tokens`) are assumed and should be confirmed against the installed SDK version during implementation.
- **Dependency file location/format is unspecified.** Design says "a minimal `requirements.txt` (or equivalent)" — no path or pin is fixed. Placement (`scripts/requirements.txt` vs repo root) and the pinned `anthropic` version are left to the plan.
- **`max_tokens`/`model` may be absent from a given `suite.json`.** The design assumes `defaults.model`/`defaults.max_tokens` exist; the questions suite is not shown to declare them. Behavior when `defaults` (or either key) is missing — error vs. fallback — is undefined and needs a decision before AC4 can run.
- **Timeout semantics are per-request, not whole-trial.** AC3 is satisfied at the SDK call boundary only; the `ThreadPoolExecutor`/`as_completed` wait remains without a `timeout=`. A trial that hangs outside the `call_model` call (it should not, given the rewrite) is not covered — accepted per Decision 3 but worth confirming no other blocking call exists in `execute_single`.
