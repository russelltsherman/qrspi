# Implementation Plan — Implement LLM judge integration in grade.py

**Structure basis:** structure.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** draft
**Total steps:** 31

## Slice 1: Judge core — prompt, client seam, parse, score validation, error mapping

### Setup

1. ✨ Create `scripts/grade_test.py` — stdlib-only, assert-based test harness with `exit(0/1)` driver; add a module-level `_failures` list / `check(cond, msg)` helper and a `main()` that runs all test functions and exits 1 on any failure. Import `run_llm_judge` (and helpers added below) from `grade`. No `anthropic` import.

### Core Logic

2. ⚠️ Modify `scripts/grade.py` — add `build_judge_prompt(criteria: str, output: str) -> str` that assembles the grading prompt from the assertion `criteria` and the agent `output`, mandating a parseable score format (e.g. a `SCORE: N` line plus rationale). New function; no existing signature.
3. ⚠️ Modify `scripts/grade.py` — add `parse_judge_response(text: str) -> (int, str)` that extracts a 1-5 score and rationale from model text per the format `build_judge_prompt` mandates; raise a `ValueError`-class parse error if no score is found. New function.
4. ⚠️ Modify `scripts/grade.py` — add `make_judge_client(api_key: str) -> Callable[[str], dict]` that lazily imports `anthropic` (import local to the function body), constructs `anthropic.Anthropic(api_key=api_key)`, calls `claude-sonnet-4-6` via `messages.create`, and returns `{ text, input_tokens, output_tokens }` from the response. New function; lazy import keeps non-judge logic stdlib-only.
5. ⚠️ Modify `scripts/grade.py` — add `call_with_retry(judge_client, prompt) -> dict` that invokes `judge_client(prompt)` with up to 3 total attempts and exponential `time.sleep` backoff on transient API errors/timeouts, re-raising the final error after exhaustion. Parse/range errors are NOT caught/retried here. New function.
6. ⚠️ Modify `scripts/grade.py` — rewrite `run_llm_judge` to accept an injectable `judge_client` seam and return real values.
   - **Current:** `run_llm_judge(assertion, result, case)` is a stub returning `{ check, type: "llm_judge", passed: None, score: None, evidence, weight }`, ignoring `result` and `case`.
   - **After:** `run_llm_judge(assertion, result, case, judge_client=<default>)` builds the prompt from `assertion["criteria"]` + `result["output"]`, calls `call_with_retry(judge_client, prompt)`, parses via `parse_judge_response`, validates `score ∈ [1,5]`, sets `passed = score >= 4`, and returns the same dict keys with real `passed`/`score`/`evidence`. On exhausted-retry or non-retryable parse/range failure, returns `{ passed: False, score: None, evidence: "<reason>", ... }`. Default `judge_client` constructs the real client (wired fully in Slice 4); empty `result["output"]` is graded, not short-circuited.

### Tests

7. ✨ Add to `scripts/grade_test.py` — happy-path test: an injected stub `judge_client` returns text yielding score 5; assert `run_llm_judge` returns `passed: True, score: 5` with non-empty evidence.
8. ✨ Add to `scripts/grade_test.py` — range/parse-failure test: stub returns out-of-range (e.g. 7) and unparseable text; assert each maps to `passed: False, score: None` with an `evidence` string and that the stub is invoked only once (no retry on deterministic failure).
9. ✨ Add to `scripts/grade_test.py` — retry-exhaustion test: a stub raising a transient error every call; assert it is invoked 3 times then maps to `passed: False, score: None, evidence`.
10. ✨ Add to `scripts/grade_test.py` — empty-output test: `result["output"] == ""` with a stub returning a low score; assert the stub IS called (not short-circuited) and the low score flows through.

### Verify Slice 1

11. **Checkpoint:** `python3 scripts/grade_test.py`
    - [ ] Exits 0.
    - [ ] Exercises happy-path, range/parse failure, retry-exhaustion, and empty-output cases with an injected stub (no network).

---

## Slice 2: Cache persistence

### Core Logic

12. ⚠️ Modify `scripts/grade.py` — add `cache_key(output: str, criteria: str) -> str` returning `sha256(output.encode() + b"\x00" + criteria.encode()).hexdigest()`. New function.
13. ⚠️ Modify `scripts/grade.py` — add `cache_read(key: str) -> dict|None` that reads `results/.cache/llm_judge.json` (JSON), returning the entry for `key` or `None` (also `None` if the file is absent). New function.
14. ⚠️ Modify `scripts/grade.py` — add `cache_write(key, entry) -> None` that read-modify-writes `results/.cache/llm_judge.json` (JSON, `indent=2`, full-file overwrite, creating `results/.cache/` as needed) storing `{ score, passed, rationale }` under `key`. New function.
15. ⚠️ Modify `scripts/grade.py` — wire `run_llm_judge` to check the cache before calling the client and write on a miss.
    - **Current:** `run_llm_judge` always calls `call_with_retry` for a score.
    - **After:** compute `cache_key(result["output"], assertion["criteria"])`, return a `cache_read` hit (mapping cached `score/passed/rationale` into the result dict) without invoking the client; on miss, proceed as Slice 1 then `cache_write` the `(score, passed, rationale)`.

### Tests

16. ⚠️ Modify `scripts/grade_test.py` — add cache-path isolation: point the cache at a temp dir (monkeypatch the module-level cache path constant / helper) so tests never touch the real `results/.cache/`.
17. ✨ Add to `scripts/grade_test.py` — cache miss-then-hit test: a counting stub; first `run_llm_judge` (miss) invokes the stub once and writes the entry; second call with identical `(output, criteria)` reads cache and does NOT invoke the stub; assert stub call count == 1 and both results match.

### Verify Slice 2

18. **Checkpoint:** `python3 scripts/grade_test.py`
    - [ ] Exits 0.
    - [ ] Includes a test where two `run_llm_judge` calls over identical inputs invoke the counting stub exactly once.

---

## Slice 3: Cost accounting and stdout cost summary

### Core Logic

19. ⚠️ Modify `scripts/grade.py` — add a per-run token accumulator (single module-level dict/state, e.g. `{ input: 0, output: 0 }`, with a reset/init at the start of the main path; grade.py is single-threaded). New state.
20. ⚠️ Modify `scripts/grade.py` — thread accumulation into `run_llm_judge`.
    - **Current:** `run_llm_judge` discards the `input_tokens`/`output_tokens` from the client response.
    - **After:** on a real client call (cache miss only), add the response's `input_tokens`/`output_tokens` to the accumulator; cache hits add zero.
21. ⚠️ Modify `scripts/grade.py` — in the grade.py main path, after grading, compute `cost = input_tok * 3/1e6 + output_tok * 15/1e6` and `print()` a cost summary line alongside the existing score lines; note the $20/run ceiling for comparison.

### Tests

22. ✨ Add to `scripts/grade_test.py` — cost-accounting test: feed stubs with known token counts, assert the accumulator sums correctly and `cost` matches the `$3/$15 per MTok` formula.
23. ✨ Add to `scripts/grade_test.py` — cache-hit-zero-tokens test: a cached `run_llm_judge` call adds zero to the accumulator.

### Verify Slice 3

24. **Checkpoint:** `python3 scripts/grade_test.py`
    - [ ] Exits 0.
    - [ ] Includes a cost-accounting test asserting summed-token cost matches the formula and cache hits add zero tokens.

---

## Slice 4: Credential sourcing, dependency manifest, and .gitignore

### Core Logic

25. ⚠️ Modify `scripts/grade.py` — add `load_api_key() -> str` returning `os.environ["ANTHROPIC_API_KEY"]` when set; else parse a gitignored root `.env` (simple `KEY=VALUE` lines, stdlib only) for the key; raise/sentinel per the chosen convention if neither source has it. New function.
26. ⚠️ Modify `scripts/grade.py` — wire the default `judge_client` in `run_llm_judge` to `make_judge_client(load_api_key())`.
    - **Current:** the Slice 1 default `judge_client` is a placeholder.
    - **After:** the real default constructs via `make_judge_client(load_api_key())`; tests still inject a stub so they stay offline.

### Setup

27. ✨ Create `requirements.txt` — declare `anthropic` as the first third-party runtime dependency (no manifest exists today).
28. ⚠️ Modify `.gitignore` — add a `.env` entry so the credential file is never committed.
    - **Current:** `.env` is not gitignored (root `.env` is empty and tracked-eligible).
    - **After:** `.env` is gitignored.

### Tests

29. ✨ Add to `scripts/grade_test.py` — `load_api_key` env-precedence test: with `ANTHROPIC_API_KEY` set in the environment, assert it is returned (no `.env` read).
30. ✨ Add to `scripts/grade_test.py` — `load_api_key` `.env`-fallback test: with the env var unset, parse a temp `.env` `KEY=VALUE` line and assert the value is returned; assert the missing-in-both case is handled per the chosen sentinel/raise.

### Verify Slice 4

31. **Checkpoint:** `python3 scripts/grade_test.py && test -f requirements.txt && grep -q anthropic requirements.txt && grep -q '^\.env$' .gitignore`
    - [ ] `python3 scripts/grade_test.py` exits 0, including `load_api_key` env-precedence and `.env`-fallback tests (no network).
    - [ ] `requirements.txt` lists `anthropic`; `.gitignore` contains `.env`.

---

## Rollback Notes

- Step 27 (create `requirements.txt`): if reverted, delete `requirements.txt`; no installed-package state is created by adding the manifest alone, so no uninstall is needed.
- Step 28 (modify `.gitignore` to add `.env`): config change. To roll back, remove the `.env` line from `.gitignore`. Note: any local `.env` created for credential sourcing must remain untracked — verify `.env` was never staged/committed before reverting the ignore rule.
- Step 14 (`cache_write` creating `results/.cache/llm_judge.json`): writes a new on-disk cache file/dir. To roll back, delete `results/.cache/llm_judge.json` (and the `results/.cache/` dir if empty); it is regenerated on the next run and is outside any `vN` results dir, so removing it loses only cached judge scores, not grade results.
