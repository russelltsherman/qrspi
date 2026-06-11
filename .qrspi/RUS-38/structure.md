# Structure Outline — Implement LLM judge integration in grade.py

**Design basis:** design.md @ 2026-06-09T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** draft

## New Types

No new classes/dataclasses. The design preserves the existing assertion-result
dict shape; the only "types" introduced are structural conventions (dict shapes
and callable seams) captured below as Contracts.

- Judge-result dict (unchanged shape, returned by `run_llm_judge`):
  `{ check: str, type: "llm_judge", passed: bool|None, score: int|None, evidence: str, weight: number }`
- Judge-client callable seam (injected; see Contracts):
  `judge_client(prompt: str) -> { text: str, input_tokens: int, output_tokens: int }`
- Cache file shape: JSON object mapping `cache_key: str -> { score: int, passed: bool, rationale: str }`,
  persisted at `results/.cache/llm_judge.json` (ref: design §Delta, Decision 1).

## Modified Types

- Judge-result dict — `run_llm_judge` now populates `passed`/`score`/`evidence`
  with real values instead of `None`/`None` (ref: design §Desired End State, §Delta).
  Downstream consumers (`score_case`, diagnose.py) read the same keys unchanged.

## Contracts

Cross-slice interfaces. Signatures are pseudo-code (not implementations).

- `load_api_key() -> str` — return `ANTHROPIC_API_KEY` from `os.environ`; if absent,
  parse a gitignored root `.env` (`KEY=VALUE` lines, stdlib only) and return the key.
  Raises/sentinels if neither source has it (ref: Decision 5, OQ2).
- `make_judge_client(api_key: str) -> Callable[[str], dict]` — construct the real
  Anthropic-backed callable that takes a prompt and returns
  `{ text, input_tokens, output_tokens }`. Imported `anthropic` lazily, local to this
  path, so non-judge grade.py logic stays stdlib-only (ref: Risk Register, Decision 3).
- `build_judge_prompt(criteria: str, output: str) -> str` — assemble the grading
  prompt from the assertion `criteria` and the agent `output` (ref: §Desired End State).
- `parse_judge_response(text: str) -> (score: int, rationale: str)` — extract a 1-5
  score and rationale from model text. Raises a parse error if no score is found
  (ref: §Desired End State, Decision 4).
- `cache_key(output: str, criteria: str) -> str` —
  `sha256(output.encode() + b"\x00" + criteria.encode()).hexdigest()` (ref: Decision 2).
- `cache_read(key: str) -> dict|None` and `cache_write(key, entry) -> None` — read/write
  `results/.cache/llm_judge.json` (JSON, indent=2, full-file overwrite; create dir as
  needed) (ref: Decision 1).
- `call_with_retry(judge_client, prompt) -> dict` — invoke `judge_client` with up to 3
  total attempts and exponential `time.sleep` backoff on transient API errors/timeouts;
  re-raise the final error after exhaustion. Parse/range errors are NOT retried by this
  wrapper (ref: Decision 4, OQ4).
- `run_llm_judge(assertion, result, case, judge_client=<default>) -> dict` — orchestrates:
  cache lookup → (on miss) build prompt → `call_with_retry` → parse → validate score ∈ [1,5]
  → set `passed = score >= 4` → cache write → accumulate tokens. On exhausted-retry or
  non-retryable parse/range failure, map to `{ passed: False, score: None, evidence: "<reason>" }`.
  The `judge_client` parameter is the injectable seam; default constructs the real client
  via `make_judge_client(load_api_key())` (ref: Decision 3, Decision 4, §Delta).
- Cost accounting — a per-run token accumulator (module-level or threaded through) summed
  across judge calls; the grade.py main path prints a cost line
  `input_tok * $3/MTok + output_tok * $15/MTok` to stdout, compared against the $20 ceiling
  (ref: §Desired End State, OQ3, Q15). The accumulator is the contract between
  `run_llm_judge` (producer) and the main-path cost print (consumer).

## Slice 1: Judge core — prompt, client seam, parse, score validation, error mapping

**Goal:** `run_llm_judge` returns a real `(score 1-5, passed = score>=4)` from an injected
judge client, validates the score range, and maps transient-retry-exhaustion and
non-retryable parse/range failures to `{passed: False, score: None, evidence}`. Verified
end-to-end offline with a stub client — no network, no cache, no cost yet.

**Files touched:**

- ⚠️ `scripts/grade.py` — add `build_judge_prompt`, `parse_judge_response`,
  `call_with_retry`, and `make_judge_client` (lazy `anthropic` import); rewrite
  `run_llm_judge` to accept an injectable `judge_client`, call it (via retry), parse +
  validate score ∈ [1,5], set `passed`, and map errors to the failure convention. No change
  to the return-dict keys (ref: Decision 3, Decision 4, §Delta).
- ✨ `scripts/grade_test.py` — stdlib-only, assert-based, exit 0/1; cover: stubbed judge
  client returns a happy-path score→passed dict; out-of-range/unparseable score maps to
  `passed: False, score: None, evidence`; retry loop attempts up to 3 times on a
  transient-error stub then maps to failure; empty `result["output"]` is still graded
  (not short-circuited) (ref: Q13, OQ5, Decision 4).

**Verification:**

- [ ] `python3 scripts/grade_test.py` exits 0, exercising happy-path, range/parse failure,
      retry-exhaustion, and empty-output cases with an injected stub client (no network).

**Context cost:** M
**Depends on:** none

## Slice 2: Cache persistence

**Goal:** Identical `(output, criteria)` pairs hit a persistent cache at
`results/.cache/llm_judge.json` instead of calling the judge — the "run the same suite
twice" acceptance path. Verified offline by driving `run_llm_judge` twice with a counting
stub and asserting the second call does not invoke the client.

**Files touched:**

- ⚠️ `scripts/grade.py` — add `cache_key`, `cache_read`, `cache_write` (JSON, indent=2,
  full-file overwrite, dir auto-create); wire `run_llm_judge` to check cache before calling
  the client and to write `(score, passed, rationale)` on a miss (ref: Decision 1, Decision 2).
- ⚠️ `scripts/grade_test.py` — add cache hit/miss tests: first call (miss) invokes the stub
  and writes the entry; second call with identical inputs reads cache and does NOT invoke the
  stub; cache file is the fixed `results/.cache/` path (use a temp dir / monkeypatched path)
  (ref: Q14, Decision 1).

**Verification:**

- [ ] `python3 scripts/grade_test.py` exits 0, including a test where two `run_llm_judge`
      calls over identical inputs invoke the counting stub exactly once.

**Context cost:** S
**Depends on:** Slice 1

## Slice 3: Cost accounting and stdout cost summary

**Goal:** Per-call input/output tokens are summed across judge calls and the grade.py main
path prints a cost line at `$3/MTok in + $15/MTok out`, the figure compared against the $20
ceiling. Verified offline by accumulating tokens from stub clients and asserting the printed
cost math.

**Files touched:**

- ⚠️ `scripts/grade.py` — add a per-run token accumulator threaded through `run_llm_judge`
  (incremented only on real client calls, not cache hits); compute and `print()` the cost
  summary in the grade.py main path alongside the existing score lines (ref: §Desired End
  State, OQ3, Q15).
- ⚠️ `scripts/grade_test.py` — add a cost-accounting test: feed stub clients with known token
  counts, assert the accumulator sums correctly and the cost formula yields the expected
  dollar figure; assert cache hits do NOT increment tokens (ref: Q13, Q15).

**Verification:**

- [ ] `python3 scripts/grade_test.py` exits 0, including a cost-accounting test asserting the
      summed-token cost matches the `$3/$15 per MTok` formula and cache hits add zero tokens.

**Context cost:** S
**Depends on:** Slice 1, Slice 2

## Slice 4: Credential sourcing, dependency manifest, and .gitignore

**Goal:** The real (non-test) path can source `ANTHROPIC_API_KEY` from the environment or a
gitignored root `.env`, the new `anthropic` dependency is recorded in a manifest, and `.env`
is gitignored so the secret is never committed. Verified by a stdlib `.env`-parser unit test
(env precedence + `.env` fallback) and a manifest/gitignore presence check.

**Files touched:**

- ⚠️ `scripts/grade.py` — add `load_api_key()` (env first, then stdlib `KEY=VALUE` `.env`
  parser); make the default `judge_client` construct via `make_judge_client(load_api_key())`
  so the real path is wired while tests still inject a stub (ref: Decision 5, OQ2).
- ⚠️ `scripts/grade_test.py` — add `load_api_key` tests: env var takes precedence; on unset
  env, a temp `.env` `KEY=VALUE` line is parsed; missing-in-both is handled per the chosen
  sentinel/raise (ref: Q13, Decision 5).
- ✨ `requirements.txt` — declare `anthropic` (first third-party runtime dependency; no
  manifest exists today) (ref: §Delta, Q5).
- ⚠️ `.gitignore` — add `.env` so the credential file is never committed (ref: Decision 5,
  Risk Register).

**Verification:**

- [ ] `python3 scripts/grade_test.py` exits 0, including `load_api_key` env-precedence and
      `.env`-fallback tests (no network).
- [ ] `requirements.txt` lists `anthropic`; `.gitignore` contains `.env`.

**Context cost:** S
**Depends on:** Slice 1

---

## Unverified Assumptions

- **Anthropic SDK response surface.** The design names the model `claude-sonnet-4-6`
  (§Desired End State, §Delta) and asserts per-call `usage` carries input/output token
  counts (Q15, Risk Register), but the design did not pin the exact SDK method
  (`messages.create`) or the `usage.input_tokens` / `usage.output_tokens` attribute names.
  `make_judge_client` / `parse_judge_response` must confirm the real SDK shape during
  implementation. (The model name itself — `claude-sonnet-4-6` — should also be confirmed
  against the current Anthropic model catalog before wiring the live call.)
- **Score-parse format.** The design states the judge returns "a 1-5 score and rationale"
  (§Desired End State) but does not specify the prompt's required output format (e.g. a
  leading integer, a `SCORE: N` line, or JSON). `build_judge_prompt` and
  `parse_judge_response` must jointly fix a format; the parse contract assumes whatever
  format the prompt mandates. This is an implementation detail the design left open.
- **Cost accumulator threading mechanism.** The design says tokens are "summed across all
  judge calls" and printed in "the grade.py main path" (OQ3, Q15) but does not specify
  whether the accumulator is module-level state, a returned-and-summed value, or passed by
  reference. Slice 3 assumes a single per-run accumulator; the concrete mechanism is left to
  the plan/implementation. grade.py being single-threaded (Q7) makes any of these safe.
- **`.env` parser edge cases.** Decision 5 explicitly scopes the stdlib parser to simple
  `KEY=VALUE` lines (no interpolation/quoting), so any quoted or multiline secret value is
  out of scope by design — flagged so the reviewer confirms the deployment `.env` uses a
  bare value.
