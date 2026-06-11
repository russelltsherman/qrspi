# Implementation Log — Integrate real LLM judge into grade.py

## Session 1 — Slice 1

**Timestamp:** 2026-06-11T13:02:00Z
**Tasks completed:** T1, T2, T3, T4, T5, T6, T7, T8, T9, T10, T11
**Tasks failed:** none
**Tests:**

- `python3 scripts/grade_test.py` → 41 passed, 0 failed (14 new in `LlmJudgeTest`; 27 pre-existing RUS-37 checks), exit 0, no network, ~0.003s

**Deviations from structure.md:**

- none on the source contracts. `build_judge_prompt`, `parse_judge_response`, `make_judge_client`, `call_with_retry`, and `run_llm_judge(assertion, result, case, judge_client=<default>)` all match the specified signatures. `judge_client` default is `None` and the lazy Anthropic-backed client is built inside `run_llm_judge`/`make_judge_client` (the `<default>` in the contract).

**Deviations from plan.md:**

- Step 1 said "create scripts/grade_test.py stdlib test harness (check/_failures/main exit 0/1)". A `scripts/grade_test.py` already existed (committed by RUS-37, a stdlib-only `unittest` module that already satisfies the same gate: imports `grade`, no anthropic, exits 0/1 via `unittest.main()`). Rather than overwrite RUS-37's 27 check tests, I ADDED a new `LlmJudgeTest(unittest.TestCase)` class (plus a `StubJudge` helper and `_judge_response`) to the existing file. The verification command `python3 scripts/grade_test.py exits 0` is unchanged and satisfied. This is the only deviation; it preserves prior-slice work and keeps a single test entrypoint.
- Retry tests patch `grade.time.sleep` (save/restore in try/finally) so the exhaustion path is deterministic and instant rather than sleeping the real 1.0+2.0s backoff. The backoff values (`[1.0, 2.0]`) are asserted via the patch, so coverage of the exponential-backoff behavior is retained without wall-clock cost.

**Notes for next session:**

- LLM-judge plumbing lives in `scripts/grade.py` between the programmatic-check registry and `run_script_check`: constants `JUDGE_MODEL="claude-sonnet-4-6"`, `JUDGE_MAX_TOKENS=1024`, `JUDGE_MAX_ATTEMPTS=3`, `JUDGE_BACKOFF_BASE=1.0`.
- `run_llm_judge` failure mapping returns `passed=False, score=None` with a descriptive `evidence` string for three cases: call-exhaustion, unparseable response (no `SCORE:` marker), and out-of-range score. Success returns `passed = (score >= 4)` with the integer score and the rationale as evidence. `score_case` (unchanged) normalizes 1-5 to 0-1 only when `score is not None`, so `None`-score failures contribute 0 — already compatible.
- `make_judge_client` lazy-imports `anthropic` (no module-level import), so `grade` imports and the test suite run with zero network/SDK dependency. `make_judge_client` itself is NOT exercised by any test (would require the SDK); it is covered only by the lazy-import assertion. A future slice wiring a real end-to-end judge call must supply `ANTHROPIC_API_KEY` and the `anthropic` package.
- The judge_client contract is `(prompt: str) -> {"text": str, "input_tokens": int, "output_tokens": int}`. `call_with_retry` retries only on the client raising; parse/range failures are handled in `run_llm_judge` and never retried.
- `grade_results` already dispatches `llm_judge` assertions through `run_llm_judge(assertion, trial_result, case)` (positional, no judge_client) — that call site is unchanged and now invokes the real (default-client) path.

---
