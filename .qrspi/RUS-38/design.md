# Design — Implement LLM judge integration in grade.py

**Ticket:** RUS-38
**Research basis:** research.md @ 2026-06-09T00:00:00Z
**Generated:** 2026-06-09T00:00:00Z
**Status:** revised (reviewer answers integrated, PR #173)

## Current State

`run_llm_judge(assertion, result, case)` is a stub that always returns `passed: None, score: None` and ignores `result` (the agent output) and `case` (ref: Q1). Its only caller is `grade_results`, which dispatches by `assertion["type"] == "llm_judge"` and passes the case dict and the trial result dict positionally (ref: Q1, Q2). The grading unit is an *assertion*, not a separate rubric object: for an llm_judge assertion the "rubric" is the free-text `criteria` string plus a numeric `weight`, and the text to be judged is `result["output"]` (ref: Q2). Cases and assertions originate from `evals/suite.json`; results originate from `scripts/run_eval.py` (ref: Q1, Q2).

Downstream, `score_case` adds full `weight` when `passed is True`, else `weight * (score-1)/4` when `score is not None`, else nothing — so the current stub's `None`/`None` contributes zero to actual but still adds its weight to `max_score`, capping judge-heavy cases (ref: Q4, Q9). llm_judge assertions are ~34.4% of total suite weight, so this systematically depresses scores (ref: Q8). `passed: None` is the codebase's "not evaluated" sentinel and is excluded from diagnose.py's failure list, so the depression has no diagnostic trail (ref: Q4, Q9, Discovered Patterns).

The Anthropic SDK is NOT a declared dependency, and there is no dependency manifest of any kind — all scripts are stdlib-only (ref: Q5). No credential sourcing exists anywhere; `ANTHROPIC_API_KEY` is never read, no `.env` loading exists, and the root `.env` is empty and not gitignored (ref: Q6). No external API call, retry, timeout, or response validation exists in the codebase; the established failure convention is `passed: False` plus a human-readable `evidence` string (ref: Q10). No cache, no cache-key construction, and no score range-validation exist today (ref: Q11, Q12). The only hashing precedent is `hashlib.sha256(text.encode()).hexdigest()[:12]` in run_eval.py (ref: Q11, Q12). Persistence is universally JSON with `indent=2` and full-file overwrite, no locking; grade.py is single-threaded (ref: Q7). `grade.py` has no unit tests; the test convention is stdlib-only, assert-based, `scripts/<name>_test.py`, runnable via `python3`, exit 0/1 (ref: Q13). `run_loop.sh` writes each iteration to a fresh `results/vN/` and mutates the skill between runs, so it is not a same-suite-twice fixture (ref: Q3, Q14). The sole reporting channel is `print()` to stdout; no cost or token logging exists, and `ExecutionResult.tokens` is stubbed to zeros (ref: Q15).

## Desired End State

- **`run_llm_judge` returns numeric `score` (1-5) and `passed` (score >= 4).** The function calls `claude-sonnet-4-6` via the Anthropic SDK with a grading prompt built from `criteria` + agent output, parses a 1-5 score and rationale, validates the score is in range, sets `passed = score >= 4`, and returns the existing dict shape (`check`, `type`, `passed`, `score`, `evidence`, `weight`) so `score_case` and diagnose.py consume it unchanged (ref: Q1, Q4, Q11).
- **Caching reduces duplicate grade calls, verified by running the same suite twice.** A persistent cache keyed on `(sha256(output) + criteria)` stores prior `(score, passed, rationale)`; a second run over identical `(output, criteria)` pairs reads from cache instead of calling the model. The cache lives in a fixed location *outside* the per-`vN` directory so it survives across `run_loop.sh` iterations, and avoids carrying a `grades.json` so report.py skips it (ref: Q3, Q12, Q14).
- **Cost per full suite run is logged, with a $20/run target budget.** Per-call input/output token counts are summed across all judge calls and printed to stdout (the existing channel) alongside grade.py's score lines, multiplied by `claude-sonnet-4-6` rates ($3/MTok in, $15/MTok out); the printed total is the figure compared against the $20 ceiling (ref: OQ3, Q15).
- **Transient API errors are retried with bounded backoff (max 3 attempts).** API errors and timeouts are retried up to 3 total attempts with exponential backoff; only after the retries are exhausted does the call degrade to the failure convention. Out-of-range/unparseable scores are *not* retried (they are deterministic) and map directly to the failure convention (ref: OQ4, Q10, Q11).
- **Errors and malformed responses degrade gracefully.** After retries are exhausted (or for non-retryable parse/range failures), the result maps to the established `{passed: False, score: None, evidence: "..."}` convention rather than crashing the suite (ref: Q10, Q11).
- **Empty agent output is graded, not short-circuited.** Until the Runtime ticket lands and `result["output"]` carries real text, `run_llm_judge` still sends the (possibly empty) output to the judge and grades it normally — empty output is expected to score low, which is the correct signal, rather than being skipped (ref: OQ5, Q2).
- **Cost budget: a full suite run targets a ceiling of $20** at `claude-sonnet-4-6` rates ($3/MTok in, $15/MTok out). The logged per-run cost is compared against this $20 target (ref: OQ3, Q15).

## Delta

- **New file `scripts/grade_test.py`** — stdlib-only, assert-based, exit 0/1; covers cache hit/miss, score validation/clamping, error mapping, cost accounting, and a stubbed/injected judge client (no network) (ref: Q13).
- **Modified `scripts/grade.py`** — implement `run_llm_judge`: build grading prompt, call the judge (via an injectable client seam so tests run offline), parse + validate score, set `passed`, map errors; add cache read/write helpers keyed on `sha256(output)+criteria`; add per-call token accumulation and a cost summary print in the grade.py main path (ref: Q1, Q11, Q12, Q15).
- **New dependency + manifest** — add `anthropic` as the first third-party runtime dependency; create a `requirements.txt` (no manifest exists today) (ref: Q5).
- **Credential + cache-location wiring** — source `ANTHROPIC_API_KEY` from the environment, falling back to loading a gitignored root `.env` (a tiny stdlib `KEY=VALUE` parser, no `python-dotenv` dependency); add `.env` to `.gitignore` in this change since `.env` sourcing is adopted; establish the cache path under `results/` (e.g. `results/.cache/llm_judge.json`) (ref: OQ2, Q6, Q3).
- **Bounded retry on transient errors** — wrap the judge call in a retry loop of at most 3 total attempts with exponential backoff; non-retryable parse/range failures skip the loop. No retry helper exists today, so this is added local to the judge path (ref: OQ4, Q10).
- **No change to `score_case`, `score_suite`, `run_loop.sh`, run_eval.py, or diagnose.py** — the return-dict contract is preserved so downstream math and failure extraction work unchanged (ref: Q4, Q8, Q9).

## Pattern Decisions

### Decision 1: Cache location and persistence

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Fixed `results/.cache/llm_judge.json`, JSON + `indent=2`, full-file read-modify-write | Survives across `vN` iterations (ref: Q3); matches the JSON serialization convention (ref: Q7); report.py skips a dir without `grades.json` (ref: Q3) | Read-modify-write is race-prone if ever multi-threaded — acceptable since grade.py is single-threaded (ref: Q7) |
| B | Per-`vN` cache inside `results/vN/` | Co-located with grades | Does NOT persist across iterations — defeats the acceptance criterion (ref: Q3) |

**Recommendation:** Option A
**Rationale:** Q3 establishes that only a fixed location outside `results/vN/` survives `run_loop.sh` iterations, and that report.py safely ignores a `results/.cache/` dir lacking a `grades.json`. JSON + `indent=2` full-file overwrite matches the universal serialization convention (ref: Q7).
**NEW PATTERN?** No — reuses the JSON-overwrite persistence convention; the cache *location* is new but follows the constraint Q3 documents.

### Decision 2: Cache key construction

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | `sha256(output.encode() + b"\x00" + criteria.encode()).hexdigest()` (byte-exact, no normalization) | Matches the ticket's specified key and the only hashing precedent (ref: Q11, Q12); identical judge inputs share an entry (ref: Q12) | Whitespace-only criteria variants fragment the cache (ref: Q12) |
| B | Normalize/trim criteria before hashing | Collapses whitespace variants | No existing normalization helper to reuse (ref: Q12); risks over-merging distinct criteria; diverges from the ticket spec |

**Recommendation:** Option A
**Rationale:** The ticket specifies `(sha256(output) + criteria)`, and Q12 confirms identical `(output, criteria)` inputs *should* share an entry by design (the rubric IS the criteria). A delimiter byte prevents boundary-collision between output and criteria. Whitespace fragmentation is a known, low-impact cost flagged as an open question rather than silently "fixed."
**NEW PATTERN?** No — reuses `hashlib.sha256(text.encode()).hexdigest()` from run_eval.py (ref: Q11).

### Decision 3: Judge client seam (testability)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Inject the judge-call function (default constructs the real Anthropic client; tests pass a stub) | Enables offline stdlib-only tests per the convention (ref: Q13); no DI seam exists today so one must be added (ref: Q13) | Slightly more surface than a hard-coded client |
| B | Hard-code `anthropic.Anthropic()` inside `run_llm_judge` | Simplest call site | Cannot test without network or monkeypatching; violates the assert-based offline test convention (ref: Q13) |

**Recommendation:** Option A
**Rationale:** Q13 explicitly notes "no DI seam exists today — `run_llm_judge` would need one" and that tests must run without network. An injectable callable is the minimal seam.
**NEW PATTERN?** Yes — dependency injection is new to these scripts (all current callers hard-code behavior). Justified because the existing test convention (offline, stdlib-only, no pytest) cannot mock a hard-coded SDK client without introducing a mocking framework, which would break the stdlib-only invariant (ref: Q5, Q13).

### Decision 4: Retry policy, score validation, and error mapping

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Retry transient API errors/timeouts up to 3 total attempts with exponential backoff; on final failure (or non-retryable parse/range error) return `passed: False, score: None, evidence: "<reason>"` | Survives transient blips before penalizing (ref: OQ4); matches the established failure convention (ref: Q10); guards the unclamped `weight*(score-1)/4` math (ref: Q11) | A persistent judge failure scores the assertion as a miss rather than skipping it |
| B | No retry; on first error return `passed: None, score: None` (the "not evaluated" sentinel) | Simplest | Penalizes transient blips immediately and reproduces the current silent-zero + non-diagnosable problem (ref: Q4, Q9) |

**Recommendation:** Option A
**Rationale:** OQ4 is resolved to "retry/backoff max 3": a transient API error/timeout is retried up to 3 total attempts with exponential backoff before degrading. Parse/range failures are deterministic and are NOT retried — they map straight to the failure convention. Q10 establishes `passed: False` + `evidence` as that convention, and Q4/Q9 show that `passed: None` is the exact pattern that silently depresses scores without surfacing as a diagnosable failure. Mapping exhausted/deterministic failures to `passed: False` makes them visible in diagnose.py. Score is range-checked before the unguarded `score_case` math runs (ref: Q11).
**NEW PATTERN?** Partially — the `{passed: False, evidence: "..."}` mapping reuses the `run_programmatic_check` convention (ref: Q10), but a bounded retry/backoff loop is new to these scripts (no retry exists today, ref: Q10). Justified: a single network blip should not silently depress a judge-heavy suite. The loop is local to the judge path and stdlib-only (`time.sleep`).

### Decision 5: Credential sourcing

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Read `ANTHROPIC_API_KEY` from the environment, falling back to a gitignored root `.env` parsed by a tiny stdlib `KEY=VALUE` reader; add `.env` to `.gitignore` | Works both in CI (env var) and local dev (`.env`) per the reviewer's "env vars + .env"; no new dependency (stdlib parser); closes the secret-leak risk by gitignoring `.env` (ref: OQ2, Q6) | A hand-rolled `.env` parser handles only simple `KEY=VALUE` lines (no interpolation/quoting nuance) |
| B | Environment variable only | Simplest | No local-dev ergonomics; reviewer asked for `.env` support too |
| C | Add `python-dotenv` | Full `.env` semantics | New third-party dependency on top of `anthropic`; breaks the minimal-footprint goal; stdlib parser suffices for a single key |

**Recommendation:** Option A
**Rationale:** OQ2 is resolved to "env vars + .env": support both. Environment variable takes precedence (CI path); when unset, load the gitignored root `.env` with a minimal stdlib parser sufficient for `ANTHROPIC_API_KEY`. `.env` is added to `.gitignore` in this change so the secret never gets committed (the current root `.env` is empty and un-gitignored, ref: Q6).
**NEW PATTERN?** Yes — no credential sourcing exists today (ref: Q6). Justified and minimized: stdlib parser, no new dependency beyond `anthropic`.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Introducing `anthropic` breaks the stdlib-only invariant; no manifest exists, so installs are undocumented (ref: Q5) | high | med | Add `requirements.txt`; keep the import local to the judge path so non-judge grade.py logic still runs stdlib-only; tests inject a stub and never import `anthropic` (ref: Q5, Q13) |
| Secret leak: `.env` is not gitignored and no credential convention exists (ref: Q6) | med | high | Source `ANTHROPIC_API_KEY` from the environment only; if `.env` is used, add it to `.gitignore` in this change (ref: Q6) |
| Out-of-range judge score corrupts `score_case` via unclamped `weight*(score-1)/4` (ref: Q11) | med | high | Validate score ∈ [1,5] in `run_llm_judge` before returning; map invalid to `passed: False` (Decision 4) |
| Cache placed inside `results/vN/` would not persist, silently failing the cache-hit acceptance test (ref: Q3) | med | med | Fix cache at `results/.cache/llm_judge.json` (Decision 1); add a test asserting a second run hits cache (ref: Q14) |
| Whitespace-only differences in `criteria` fragment the cache, inflating cost (ref: Q12) | med | low | Documented as Open Question; key remains byte-exact per ticket spec (Decision 2) |
| Cost overrun on a full suite run; no token logging exists to detect it (ref: Q15) | med | med | Sum per-call `usage` tokens, print cost to stdout, compare against the resolved **$20/run** ceiling (ref: OQ3, Q15) |
| Transient API error silently penalizes a judge-heavy suite (ref: Q10) | med | med | Retry transient errors up to 3 attempts with backoff before degrading to `passed: False` (Decision 4, OQ4) |
| Secret leak via committed `.env` once `.env` sourcing is adopted (ref: Q6, OQ2) | med | high | Add `.env` to `.gitignore` in this change; env var takes precedence; stdlib parser, no key logged (Decision 5) |

## Resolved Questions

All open questions were answered by the reviewer on PR #173 and are now folded into the
decisions above:

- **OQ1 (cache-key whitespace normalization) → byte-exact is acceptable.** Reviewer: *"acceptable."*
  The cache key stays byte-exact `sha256(output + criteria)` per the ticket spec; no whitespace
  normalization is applied (Decision 2). Whitespace-only fragmentation is an accepted, low-impact cost.
- **OQ2 (credential sourcing) → env vars + `.env`.** Reviewer: *"env vars + .env."* Read
  `ANTHROPIC_API_KEY` from the environment, falling back to a gitignored root `.env` via a stdlib
  `KEY=VALUE` parser; add `.env` to `.gitignore` in this change (Decision 5).
- **OQ3 (target cost budget) → $20 per full suite run.** Reviewer: *"$20."* The logged per-run cost
  is compared against a $20 ceiling at `claude-sonnet-4-6` rates (Desired End State).
- **OQ4 (transient-error policy) → retry/backoff, max 3.** Reviewer: *"retry/backoff max 3."* Transient
  API errors/timeouts are retried up to 3 total attempts with exponential backoff; only after they are
  exhausted (or for non-retryable parse/range errors) does the result map to `passed: False` + `evidence`
  (Decision 4).
- **OQ5 (empty agent output before the Runtime ticket lands) → grade it.** Reviewer: *"grade it."*
  `run_llm_judge` still sends the (possibly empty) `result["output"]` to the judge and grades it
  normally; empty output is expected to score low, which is the correct signal (Desired End State).
