# Implementation Plan — Wire up agent execution runtime in run_eval.py

**Structure basis:** structure.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** draft
**Total steps:** 18

## Slice 1: Real model execution behind a stubbable seam (+ unit tests + deps)

### Setup

1. ✨ Create `scripts/requirements.txt` — minimal pinned third-party dependency surface; add a single pinned line `anthropic==0.49.0` (confirm/adjust the exact pin against the installed SDK during implementation). Purpose: declare the first third-party import for this module; none exists today (ref: design.md §Delta "New dependency surface", structure.md Slice 1 Files; Unverified Assumptions "Dependency file location/format is unspecified").

2. ⚠️ Modify `scripts/run_eval.py` — add the `executed` status sentinel to the `ExecutionResult` dataclass.
   - **Current:** `ExecutionResult` dataclass has its nine fields (`output`, `files`, `tokens`, `tool_calls`, `transcript`, `duration_ms`, `error`, etc.) with no execution sentinel.
   - **After:** add field `executed: bool = False` to `ExecutionResult` so `dataclasses.asdict` serializes it unchanged; `False` for the stub/zeroed path, set `True` once a real model call returns (ref: structure.md Modified Types; design.md §Delta "results.json gains one field", AC2).

### Core Logic

3. ⚠️ Modify `scripts/run_eval.py` — add the module-level `call_model` seam.
   - **Current:** no model-invocation function exists; `execute_single` assigns hard-coded zeros.
   - **After:** add `def call_model(system: str, messages: list[dict], model: str, max_tokens: int, timeout_s: float) -> ModelReply` that imports `anthropic` *locally inside the function body*, reads the API key from the SDK's standard environment variable, applies `timeout_s` as the request-level timeout, and returns the loose shape `{output: str, tokens: {"input": int, "output": int}, raw_transcript_turn: dict}`. Normalize SDK `usage` (`input_tokens`/`output_tokens`) into the `{input,output}` keys here at the seam boundary (ref: structure.md Contracts `call_model`; design.md Decision 1, Decision 2, Risk: tokens shape).

4. ⚠️ Modify `scripts/run_eval.py` — thread `model`/`max_tokens` from `suite.json` `defaults` through `run_suite`.
   - **Current:** `run_suite` loads the suite but does not read `defaults.model`/`defaults.max_tokens`; `execute_single(skill_text, case, trial_id, timeout_ms)` carries no model params.
   - **After:** in `run_suite` (where the loaded suite is in scope) read `defaults.model` and `defaults.max_tokens`, decide and implement the missing-key behavior (error-with-clear-message vs. fallback — pick one and document it inline; Unverified Assumptions "max_tokens/model may be absent"), and thread the two values into the `execute_single` call. Threading mechanism (extra params) per Unverified Assumptions "execute_single signature must change"; keep the `(case × trial)` fan-out shape unchanged (ref: structure.md Contracts "Model id + max_tokens source"; design.md §Delta).

5. ⚠️ Modify `scripts/run_eval.py` — rewrite the `execute_single` body to call the seam and populate fields.
   - **Current:** `execute_single(skill_text, case, trial_id, timeout_ms) -> ExecutionResult` builds messages via `build_messages(case)` then assigns hard-coded zeros (`output=""`, `tokens={"input":0,"output":0}`, `transcript=messages`); `skill_text`/`timeout_ms` unused.
   - **After:** build messages via `build_messages(case)`, call `call_model(system=skill_text, messages=..., model=..., max_tokens=..., timeout_s=timeout_ms/1000)`, populate `output`, `tokens` (normalized `{input,output}`), `transcript` (input messages + assistant turn), and set `executed=True`; on exception (including timeout) write `result.error` and leave `executed=False`. Keep `files`/`tool_calls` empty (SDK seam for option b). Signature gains the `model`/`max_tokens` params from step 4 but is otherwise unchanged (ref: structure.md Contracts `execute_single`; design.md AC1–AC3, Decision 3).

6. ⚠️ Modify `scripts/run_eval.py` — add `--agent` as an argparse alias for `--skill`.
   - **Current:** `argparse` defines `--skill` as `required=True`, flowing `args.skill → EvalConfig.skill_path → run_suite`.
   - **After:** `--skill` stays the primary/required name; add `--agent` resolving to the same `dest` so `args.skill` is unchanged downstream. Keep `load_skill`, `load_suite`, `build_messages`, the envelope, and the `run_suite` fan-out unchanged (ref: structure.md Contracts "--agent argparse alias"; design.md Decision 4, OQ1).

### Tests

7. ✨ Create `scripts/run_eval_test.py` — stdlib-only `_test.py` sibling; stub `call_model` by monkeypatching the module attribute (never import `anthropic`). Purpose: offline verification of the rewritten runtime (ref: structure.md Slice 1 Files; design.md §Delta "New file", Decision 2).

8. ⚠️ Modify `scripts/run_eval_test.py` — add the success-path assertion: stub `call_model` to return a populated `ModelReply`; assert `execute_single` yields populated `output`/`tokens`/`transcript` and `executed == True`.

9. ⚠️ Modify `scripts/run_eval_test.py` — add the error-capture assertion: stub `call_model` to raise; assert `result.error` is populated and `executed == False`.

10. ⚠️ Modify `scripts/run_eval_test.py` — add the timeout assertion: stub `call_model` to raise the timeout/deadline-exceeded exception; assert it maps to a populated `result.error` (and `executed == False`).

11. ⚠️ Modify `scripts/run_eval_test.py` — add the token-normalization assertion: assert `tokens` is normalized to exactly `{input, output}` keys on the success path.

12. Run: `python3 scripts/run_eval_test.py`
    - **Expected:** all assertions pass with no network access and no API key set; `anthropic` is never imported at collection time.

### Verify Slice 1

13. **Checkpoint:** `python3 scripts/run_eval_test.py && python3 -c "import importlib,sys; sys.path.insert(0,'scripts'); m=importlib.import_module('run_eval'); assert hasattr(m,'call_model'); assert 'executed' in {f.name for f in __import__('dataclasses').fields(m.ExecutionResult)}"`
    - [ ] `python3 scripts/run_eval_test.py` passes (success-path fields, error capture, timeout-to-error, token normalization) with no network and no API key.
    - [ ] Module import / test collection does not import `anthropic` (import is local to `call_model`); confirmed by the test running with `anthropic` absent from the environment.
    - [ ] `run_eval` imports successfully with the new `executed` field and the `--agent` alias present.

---

## Slice 2: Live end-to-end acceptance run (AC4)

### Core Logic

14. (no code change) Confirm a valid Anthropic API key is present in the SDK's standard environment variable before running; this slice is the live verification of Slice 1's runtime against the real API (ref: structure.md Slice 2 "Files touched: none"; design.md AC4, OQ5).

### Tests

15. Run the documented `--skill` invocation against the questions suite with a valid API key, writing to a fresh `--output` directory.
    - **Expected:** the command completes and writes `results.json`.

16. Run: inspect the produced `results.json` and assert `results` is non-empty, every `results[*].executed == True`, and `output`/`tokens`/`transcript` are real (non-zero, non-stub) for the questions cases.
    - **Expected:** real model responses distinguishable from the zeroed stub.

17. Run the same invocation substituting `--agent` for `--skill`.
    - **Expected:** identical behavior — `--agent` alias invokes the same runtime path.

### Verify Slice 2

18. **Checkpoint:** run the documented questions-suite invocation, then inspect `results.json`.
    - [ ] `results.json` is non-empty, `results[*].executed == True`, and `output`/`tokens`/`transcript` are real for the questions cases.
    - [ ] The run stays within the ~$20 cost ceiling across the 15 questions cases.
    - [ ] `--agent` alias invokes identically to `--skill`.

---

## Rollback Notes

- **Step 1 (`scripts/requirements.txt`):** this is a new file declaring the `anthropic` dependency. To reverse, delete the file. No installed packages are pinned into the repo, so removal is non-destructive; uninstalling `anthropic` from the local environment is optional and only affects local runs.
- **Steps 2–6 (`scripts/run_eval.py`):** all edits are to a single existing file with no DB or persisted-state side effects. Reverse by restoring the prior `execute_single` stub body, removing `call_model`, removing the `executed` field, removing the `--agent` alias, and reverting the `run_suite` defaults threading. No migration or data backfill is involved.
- **Slice 2 (live run):** incurs real API cost (~$20 ceiling) and is non-reversible spend; it produces only a `results.json` artifact under `--output` (deletable). There is no destructive infrastructure change — guard against re-running by checking for an existing `results.json` before invoking.
