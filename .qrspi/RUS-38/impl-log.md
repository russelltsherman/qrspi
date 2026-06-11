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

## Session 2 — Slice 2

**Timestamp:** 2026-06-11T13:40:00Z
**Tasks completed:** T12, T13, T14, T15, T16, T17, T18
**Tasks failed:** none
**Tests:**

- `python3 scripts/grade_test.py` → 46 passed, 0 failed (5 new cache tests added to `LlmJudgeTest`; 41 pre-existing), exit 0, no network, ~0.005s. Includes the required miss-then-hit test: two identical `run_llm_judge` calls invoke the counting stub exactly once (`stub.calls == 1`), the second served from cache.

**Deviations from structure.md:**

- none. `cache_key(output, criteria) = sha256(output + 0x00 + criteria).hexdigest()`, `cache_read(key) -> dict|None`, and `cache_write(key, entry)` over `results/.cache/llm_judge.json` (JSON, `indent=2`, full-file overwrite, dir auto-create) all match the specified contracts. `run_llm_judge` checks cache before calling the client and writes `{score, passed, rationale}` on a miss.

**Deviations from plan.md:**

- none on behavior. Cache-path isolation (Step 16) is implemented as a module-level constant `grade.JUDGE_CACHE_PATH = "results/.cache/llm_judge.json"` that the test class redirects to a temp dir in `setUp`/`tearDown` (verified: no `results/.cache/` is created in the worktree). The plan said "monkeypatch the cache path constant" — done exactly that.

**Notes for next session:**

- Judge cache lives in `scripts/grade.py`: constant `JUDGE_CACHE_PATH = "results/.cache/llm_judge.json"` (relative to cwd); `cache_key(output, criteria)` NUL-separates the two fields before sha256; `cache_read`/`cache_write` are read-modify-write over a single JSON dict keyed by cache key, entries shaped `{"score": int, "passed": bool, "rationale": str}`.
- Only SUCCESSFUL grades are cached. Failures (call-exhaustion, unparseable, out-of-range score) return without writing — re-running them re-invokes the judge. A cache hit returns `{passed, score, evidence=rationale, weight}` and never builds/calls the client (so a cached path needs no `anthropic` and no API key).
- `cache_read`/`cache_write` read `JUDGE_CACHE_PATH` at call time (not import time), so monkeypatching the constant redirects them. `LlmJudgeTest.setUp`/`tearDown` already isolate every judge test to a temp cache dir — extend that class for further judge tests rather than touching the real cache.
- `weight` is NOT part of the cached entry; it is taken from the live `assertion` on every call (a hit re-applies the current assertion's weight to the cached score/passed/rationale).

---

## Session 3 — Slice 3

**Timestamp:** 2026-06-11T13:11:09Z
**Tasks completed:** T19, T20, T21, T22, T23, T24
**Tasks failed:** none
**Tests:**

- `python3 scripts/grade_test.py` → 49 passed, 0 failed (3 new in `LlmJudgeTest`: token-accumulation+cost-formula, failed-call-zero-tokens, cache-hit-zero-tokens; 46 pre-existing), exit 0, no network, ~0.004s. Confirmed no `results/.cache/` created in the worktree.

**Deviations from structure.md:**

- none. A module-level accumulator `grade.JUDGE_TOKENS = {"input": 0, "output": 0}` is the producer/consumer contract between `run_llm_judge` (increments) and the main-path cost print (consumes). The cost print uses `input_tok*$3/MTok + output_tok*$15/MTok` vs the `$20` ceiling exactly.

**Deviations from plan.md:**

- none on behavior. The plan's "main path" cost print (Step 21) lives in `grade_results` (the function `main()` calls) — printed alongside the existing Train/Test/gap score lines, which is where those lines already are. `reset_judge_tokens()` (Step 19) is called at the top of `grade_results`, not inside `main()`, so the accumulator is reset for both CLI and any direct `grade_results` caller.
- Accumulation (Step 20) is placed immediately after a SUCCESSFUL `call_with_retry` return (cache misses only reach this code; cache hits return earlier and add zero). A call-exhaustion failure returns before accumulation and carries no usage, so it also adds zero — asserted by `test_failed_call_does_not_accumulate_tokens` (an extra test beyond the two the plan named).

**Notes for next session:**

- Per-run token accounting lives in `scripts/grade.py`: module constant `JUDGE_TOKENS = {"input": 0, "output": 0}`; `reset_judge_tokens()` zeroes it (called at the start of `grade_results`); `judge_cost(input_tokens, output_tokens)` returns USD at `JUDGE_INPUT_COST_PER_MTOK=3.0` / `JUDGE_OUTPUT_COST_PER_MTOK=15.0` per million tokens. `JUDGE_COST_CEILING=20.0` is the noted per-run ceiling.
- `run_llm_judge` increments `JUDGE_TOKENS` only after a successful `call_with_retry` (cache miss + non-exhausted call). Cache hits return before that line; failures return before it too — both add zero.
- `LlmJudgeTest.setUp`/`tearDown` now also call `grade.reset_judge_tokens()` to isolate the global accumulator per test. Extend that class (do not touch the global directly) for any further token/cost tests.
- The main-path cost line is printed in `grade_results` between the train-test-gap line and the "Grades written to" line; format: `Judge cost: $<cost> (<in> in @ $3/MTok + <out> out @ $15/MTok) vs $20/run ceiling`.


---

## Session 4 — Slice 4

**Timestamp:** 2026-06-11T13:14:26Z
**Tasks completed:** T25, T26, T27, T28, T29, T30, T31
**Tasks failed:** none
**Tests:**

- `python3 scripts/grade_test.py` → 54 passed, 0 failed (5 new in `LoadApiKeyTest`; 49 pre-existing), exit 0, no network, ~0.006s
- `test -f requirements.txt && grep -q anthropic requirements.txt && grep -q '^\.env$' .gitignore` → all pass

**Deviations from structure.md:**

- none

**Deviations from plan.md:**

- none — added one extra defensive test (`test_dotenv_value_strips_surrounding_quotes`) beyond the plan's required env-precedence + .env-fallback + missing-in-both cases; covers the quote-stripping branch of `parse_dotenv`.

**Notes for next session:**

- API-key resolution lives in `scripts/grade.py`: `load_api_key() -> str` reads `os.environ["ANTHROPIC_API_KEY"]` first (env wins; `.env` is not read when set), else parses the gitignored root `.env` via `parse_dotenv(DOTENV_PATH)`, else raises `RuntimeError`. There is NO sentinel return — the missing-in-both contract is a raise.
- `parse_dotenv(path) -> dict` is a stdlib `KEY=VALUE` parser: skips blanks/`#` comments/`=`-less lines, strips an optional `export ` prefix, trims one layer of matching surrounding quotes. Absent/unreadable file → `{}`.
- Module constants: `ANTHROPIC_API_KEY_ENV = "ANTHROPIC_API_KEY"`; `DOTENV_PATH` = repo-root `.env` (parent of `scripts/`). `DOTENV_PATH` is module-level so tests monkeypatch it to a temp path.
- `run_llm_judge`'s default-client branch now calls `make_judge_client(load_api_key())` (was `make_judge_client()`). Injected stub clients still bypass this entirely, so the test suite needs no key.
- `LoadApiKeyTest` isolates by redirecting `grade.DOTENV_PATH` to a temp file (setUp/tearDown) and patching `os.environ` with `mock.patch.dict(..., clear=True)` so a host-shell key cannot leak in. Extend that class for further key/dotenv tests.
- New files: `requirements.txt` (declares `anthropic`, the first third-party runtime dep; imported lazily so tests run without it). `.gitignore` now has a bare `.env` line.
