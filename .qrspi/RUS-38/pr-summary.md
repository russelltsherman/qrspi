# PR: RUS-38 — Integrate real LLM judge into grade.py

**Ticket:** RUS-38
**Design:** design.md @ 2026-06-09T00:00:00Z
**Structure:** structure.md @ 2026-06-11T00:00:00Z

## Summary

This change replaces the `run_llm_judge` stub in `scripts/grade.py` — which always
returned `passed: None, score: None` and silently depressed scores on the ~34% of suite
weight carried by `llm_judge` assertions — with a real Anthropic-backed judge. The judge
builds a grading prompt from each assertion's `criteria` plus the agent output, calls
`claude-sonnet-4-6` through an injectable client seam, parses a 1-5 score and rationale,
validates the range, sets `passed = score >= 4`, and degrades to the established
`{passed: False, score: None, evidence}` failure convention on retry-exhaustion or
malformed responses. It adds a persistent cache (`results/.cache/llm_judge.json`) so a
second run over identical `(output, criteria)` pairs skips the model, per-run token/cost
accounting printed against a $20 ceiling, and `ANTHROPIC_API_KEY` sourcing (env first, then
a gitignored root `.env`). Reviewer focus areas: the error-mapping / range-validation logic
in `run_llm_judge`, the cache miss-then-hit semantics, and the credential-resolution
precedence (env over `.env`, raise-on-missing). The return-dict contract is unchanged, so
`score_case`, `score_suite`, and diagnose.py are untouched.

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: `run_llm_judge` returns a real 1-5 `score` and `passed = score >= 4` from the judge model | `scripts/grade.py:run_llm_judge`, `build_judge_prompt`, `parse_judge_response`, `make_judge_client` | `scripts/grade_test.py:LlmJudgeTest` (happy-path score→passed) |
| AC2: Out-of-range / unparseable scores degrade to the `{passed: False, score: None, evidence}` convention (not retried) | `scripts/grade.py:run_llm_judge` (range check + `parse_judge_response` ValueError mapping) | `scripts/grade_test.py:LlmJudgeTest` (range-failure, unparseable cases) |
| AC3: Transient API errors are retried with bounded exponential backoff (max 3 attempts) before degrading | `scripts/grade.py:call_with_retry` | `scripts/grade_test.py:LlmJudgeTest` (retry-exhaustion via transient-error stub, `time.sleep` patched) |
| AC4: Empty agent output is graded, not short-circuited | `scripts/grade.py:run_llm_judge` (sends `result.get("output", "")` unconditionally) | `scripts/grade_test.py:LlmJudgeTest` (empty-output case) |
| AC5: Caching — running the same suite twice serves identical `(output, criteria)` from a persistent cache | `scripts/grade.py:cache_key`, `cache_read`, `cache_write`; `run_llm_judge` cache check/write | `scripts/grade_test.py:LlmJudgeTest` (miss-then-hit: counting stub called exactly once) |
| AC6: Per-run cost logged to stdout at $3/$15 per MTok vs a $20 ceiling | `scripts/grade.py:JUDGE_TOKENS`, `reset_judge_tokens`, `judge_cost`, cost print in `grade_results` | `scripts/grade_test.py:LlmJudgeTest` (token-accumulation + cost-formula, cache-hit/failed-call add zero) |
| AC7: `ANTHROPIC_API_KEY` sourced from env, falling back to a gitignored root `.env` | `scripts/grade.py:load_api_key`, `parse_dotenv` | `scripts/grade_test.py:LoadApiKeyTest` (env precedence, `.env` fallback, missing-in-both, quote-stripping) |
| AC8: `anthropic` declared in a manifest; `.env` gitignored | `requirements.txt` (new), `.gitignore` (`.env` line) | `scripts/grade_test.py` presence check — `test -f requirements.txt && grep -q anthropic requirements.txt && grep -q '^\.env$' .gitignore` |

## Changes by Slice

### Slice 1: Judge core — prompt, client seam, parse, score validation, error mapping

| File | Change | Lines |
|------|--------|-------|
| `scripts/grade.py` | ⚠️ modified | +150, -12 |
| `scripts/grade_test.py` | ⚠️ modified (added `LlmJudgeTest`) | +147 |

### Slice 2: Cache persistence

| File | Change | Lines |
|------|--------|-------|
| `scripts/grade.py` | ⚠️ modified (`cache_key`/`cache_read`/`cache_write` + wiring) | +83, -1 |
| `scripts/grade_test.py` | ⚠️ modified (cache hit/miss tests) | +73, -1 |

### Slice 3: Cost accounting and stdout cost summary

| File | Change | Lines |
|------|--------|-------|
| `scripts/grade.py` | ⚠️ modified (`JUDGE_TOKENS`, `reset_judge_tokens`, `judge_cost`, cost print) | +40 |
| `scripts/grade_test.py` | ⚠️ modified (token/cost tests) | +64 |

### Slice 4: Credential sourcing, dependency manifest, and .gitignore

| File | Change | Lines |
|------|--------|-------|
| `scripts/grade.py` | ⚠️ modified (`load_api_key`, `parse_dotenv`, default-client wiring) | +61, -2 |
| `scripts/grade_test.py` | ⚠️ modified (`LoadApiKeyTest`) | +61 |
| `requirements.txt` | ✨ new (declares `anthropic`) | +4 |
| `.gitignore` | ⚠️ modified (`.env` line) | +2 |

### Workflow artifacts (non-source; QRSPI phase outputs)

| File | Change | Lines |
|------|--------|-------|
| `.qrspi/RUS-38/questions.md` | ✨ new | +53 |
| `.qrspi/RUS-38/research.md` | ✨ new | +381 |
| `.qrspi/RUS-38/design.md` | ✨ new | +125 |
| `.qrspi/RUS-38/structure.md` | ✨ new | +194 |
| `.qrspi/RUS-38/plan.md` | ✨ new | +119 |
| `.qrspi/RUS-38/worktree.md` | ✨ new | +82 |
| `.qrspi/RUS-38/impl-log.md` | ✨ new | +110 |

## Testing Summary

- [x] Slice 1: unit tests — `python3 scripts/grade_test.py` — 41 passed, 0 failed (14 new in `LlmJudgeTest`; no network)
- [x] Slice 2: unit tests — `python3 scripts/grade_test.py` — 46 passed, 0 failed (includes miss-then-hit: counting stub invoked exactly once)
- [x] Slice 3: unit tests — `python3 scripts/grade_test.py` — 49 passed, 0 failed (token-accumulation + cost-formula; cache-hit and failed-call add zero tokens)
- [x] Slice 4: unit tests — `python3 scripts/grade_test.py` — 54 passed, 0 failed (5 new in `LoadApiKeyTest`)
- [x] Slice 4: manifest/gitignore presence — `test -f requirements.txt && grep -q anthropic requirements.txt && grep -q '^\.env$' .gitignore` — all pass
- [x] Manual verification: confirmed no `results/.cache/` directory is created in the worktree (tests redirect `JUDGE_CACHE_PATH`/`DOTENV_PATH` to temp paths in setUp/tearDown); retry tests patch `grade.time.sleep` so the suite runs instantly without real backoff sleeps
- [ ] Not exercised offline: `make_judge_client` (lazy `anthropic` import) and the live end-to-end judge call — require the `anthropic` package + a real `ANTHROPIC_API_KEY`; covered only by the lazy-import assertion

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| `scripts/grade_test.py` | New file (Slice 1) | Modified — file already existed from RUS-37 | RUS-37 had already committed a stdlib `unittest` harness at this path; rather than overwrite its 27 check tests, a new `LlmJudgeTest`/`LoadApiKeyTest` class was added. The verification command (`python3 scripts/grade_test.py` exits 0) and single test entrypoint are unchanged. (impl-log Session 1) |
| `load_api_key()` missing-in-both behavior | "Raises/sentinels" (structure left it open) | Raises `RuntimeError` (no sentinel) | Structure permitted either; a loud raise prevents silently constructing an unauthenticated client. (impl-log Session 4) |

All cross-slice source contracts (`build_judge_prompt`, `parse_judge_response`, `make_judge_client`,
`call_with_retry`, `run_llm_judge`, `cache_key`/`cache_read`/`cache_write`, the `JUDGE_TOKENS`
accumulator) match the specified signatures and shapes — no source deviations reported.

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| `anthropic` breaks the stdlib-only invariant; installs undocumented | mitigated — `requirements.txt` added; `anthropic` imported lazily inside `make_judge_client`; tests inject a stub and never import the SDK | Remove `requirements.txt`; non-judge grade.py logic stays stdlib-only |
| Secret leak: `.env` not gitignored, no credential convention | mitigated — `.env` added to `.gitignore`; env var takes precedence; key never logged | Revert `.gitignore` + `load_api_key`/`parse_dotenv` |
| Out-of-range judge score corrupts `score_case` via unclamped `weight*(score-1)/4` | mitigated — score validated ∈ [1,5] in `run_llm_judge`; invalid maps to `passed: False, score: None` | Revert `run_llm_judge` to the stub |
| Cache inside `results/vN/` would not persist (fails cache-hit AC) | mitigated — cache fixed at `results/.cache/llm_judge.json`; miss-then-hit test asserts one stub call | Delete `results/.cache/`; revert cache helpers |
| Whitespace-only `criteria` differences fragment the cache, inflating cost | accepted — key stays byte-exact per ticket spec (Decision 2); documented open question | Apply normalization to `cache_key` if cost data warrants |
| Cost overrun on a full suite run; no token logging to detect it | mitigated — per-run tokens summed and printed vs the $20 ceiling | Revert the cost print + `JUDGE_TOKENS` accumulator |
| Transient API error silently penalizes a judge-heavy suite | mitigated — `call_with_retry` does up to 3 attempts with exponential backoff before degrading | Revert `call_with_retry`; call the client directly |

No new risks discovered during implementation.

## Open Items

- **Live end-to-end judge call is unverified offline.** `make_judge_client`'s real SDK
  surface (`client.messages.create`, `usage.input_tokens`/`output_tokens`) and the
  `claude-sonnet-4-6` model name should be confirmed against the current Anthropic catalog
  with a real key before relying on production grades. (structure.md Unverified Assumptions; impl-log Session 1)
- **Whitespace fragmentation of the cache key** is an accepted, byte-exact cost (Decision 2 /
  OQ1). Revisit with a normalization step only if cost telemetry shows meaningful waste.
- **`.env` parser is scoped to simple `KEY=VALUE`** (one layer of surrounding quotes, no
  interpolation/multiline). A quoted/multiline deployment secret is out of scope by design —
  confirm the deployment `.env` uses a bare value. (structure.md Unverified Assumptions)
- **Empty agent output** is graded as-is (expected to score low) pending the Runtime ticket
  that will populate `result["output"]` with real text. (design §Desired End State, OQ5)
