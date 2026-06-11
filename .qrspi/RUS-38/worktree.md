# Work Tree — Implement LLM judge integration in grade.py

**Plan basis:** plan.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** draft
**Total sessions:** 4
**Critical path:** T1 → T2 → T3 → T4 → T5 → T6 → T11 → T12 → T15 → T18 → T19 → T20 → T21 → T24 → T25 → T26 → T31

## Session 1

**Load:** structure.md §Types, structure.md §Contracts, plan.md §Slice 1
**Estimated context:** ~22%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create `scripts/grade_test.py` stdlib test harness (`check`/`_failures`/`main` exit 0/1; imports from `grade`, no `anthropic`) | — | §1 | S | pending |
| T2 | Add `build_judge_prompt(criteria, output) -> str` to `grade.py` (mandates parseable `SCORE: N` + rationale) | — | §2 | S | pending |
| T3 | Add `parse_judge_response(text) -> (int, str)` (extract 1-5 score + rationale; ValueError on no score) | T2 | §3 | S | pending |
| T4 | Add `make_judge_client(api_key) -> Callable` (lazy `anthropic` import, `claude-sonnet-4-6`, returns text+token counts) | — | §4 | M | pending |
| T5 | Add `call_with_retry(judge_client, prompt) -> dict` (3 attempts, exponential backoff on transient errors; no parse/range retry) | T4 | §5 | M | pending |
| T6 | Rewrite `run_llm_judge` with injectable `judge_client` seam returning real `passed`/`score`/`evidence` | T2, T3, T5 | §6 | M | pending |
| T7 | Happy-path test: stub yields score 5 → `passed: True, score: 5`, non-empty evidence | T1, T6 | §7 | S | pending |
| T8 | Range/parse-failure test: out-of-range + unparseable → `passed: False, score: None`, stub called once | T1, T6 | §8 | S | pending |
| T9 | Retry-exhaustion test: transient-error stub invoked 3× → `passed: False, score: None`, evidence | T1, T6 | §9 | S | pending |
| T10 | Empty-output test: `output == ""` stub still called, low score flows through | T1, T6 | §10 | S | pending |
| T11 | **Verify Slice 1** — `python3 scripts/grade_test.py` exits 0; all four cases exercised offline | T7, T8, T9, T10 | §11 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete (judge core landed). Fresh context for Slice 2; only Slice 1 notes carry forward.

## Session 2

**Load:** structure.md §Contracts, plan.md §Slice 2, impl-log.md §Slice 1 (notes only)
**Estimated context:** ~16%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T12 | Add `cache_key(output, criteria) -> str` (sha256 of `output \x00 criteria`) | T11 | §12 | S | pending |
| T13 | Add `cache_read(key) -> dict|None` (read `results/.cache/llm_judge.json`; None if absent) | T11 | §13 | S | pending |
| T14 | Add `cache_write(key, entry) -> None` (RMW JSON full-file overwrite, create `results/.cache/`) | T11 | §14 | S | pending |
| T15 | Wire `run_llm_judge` to check cache before client and write on miss | T12, T13, T14 | §15 | M | pending |
| T16 | Add cache-path isolation to test harness (monkeypatch cache path to temp dir) | T15 | §16 | S | pending |
| T17 | Cache miss-then-hit test: counting stub called once; second identical call reads cache | T15, T16 | §17 | S | pending |
| T18 | **Verify Slice 2** — `python3 scripts/grade_test.py` exits 0; identical-input double call hits stub exactly once | T17 | §18 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 2 complete (cache persistence landed). Fresh context for cost accounting; cache contract carries forward as notes.

## Session 3

**Load:** structure.md §Contracts, plan.md §Slice 3, impl-log.md §Slice 1–2 (notes only)
**Estimated context:** ~16%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T19 | Add per-run token accumulator module-level state (`{input, output}`, reset on main path) | T18 | §19 | S | pending |
| T20 | Thread accumulation into `run_llm_judge` (add tokens on real call; cache hits add zero) | T19 | §20 | S | pending |
| T21 | In main path, compute `cost = in*3/1e6 + out*15/1e6` and print cost summary (note $20/run ceiling) | T20 | §21 | M | pending |
| T22 | Cost-accounting test: known token counts → accumulator sums; cost matches $3/$15 per MTok | T20 | §22 | S | pending |
| T23 | Cache-hit-zero-tokens test: cached call adds zero to accumulator | T20 | §23 | S | pending |
| T24 | **Verify Slice 3** — `python3 scripts/grade_test.py` exits 0; cost formula + cache-hit-zero asserted | T21, T22, T23 | §24 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 3 complete (cost accounting landed). Fresh context for credential sourcing + manifest/gitignore; prior slices carry forward as notes.

## Session 4

**Load:** structure.md §Contracts, plan.md §Slice 4, impl-log.md §Slice 1–3 (notes only)
**Estimated context:** ~16%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T25 | Add `load_api_key() -> str` (env `ANTHROPIC_API_KEY`, else parse gitignored root `.env`; raise/sentinel if neither) | T24 | §25 | M | pending |
| T26 | Wire default `judge_client` in `run_llm_judge` to `make_judge_client(load_api_key())` | T25 | §26 | S | pending |
| T27 | Create `requirements.txt` declaring `anthropic` | — | §27 | S | pending |
| T28 | Modify `.gitignore` to add `.env` entry | — | §28 | S | pending |
| T29 | `load_api_key` env-precedence test: env var set → returned, no `.env` read | T25 | §29 | S | pending |
| T30 | `load_api_key` `.env`-fallback test: env unset → temp `.env` value returned; missing-in-both handled | T25 | §30 | S | pending |
| T31 | **Verify Slice 4** — test suite exits 0 (incl. env-precedence + `.env`-fallback); `requirements.txt` lists `anthropic`; `.gitignore` contains `.env` | T26, T27, T28, T29, T30 | §31 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 4 complete — final slice. Feature done; remaining work is PR-summary phase, not implementation.
