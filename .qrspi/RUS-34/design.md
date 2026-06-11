# Design — Wire up agent execution runtime in run_eval.py

**Ticket:** RUS-34
**Research basis:** research.md @ 2026-06-09T00:00:00Z
**Generated:** 2026-06-09T00:00:00Z
**Status:** draft

## Current State

`scripts/run_eval.py` is the entire eval-execution module; there is no companion runtime, scoring, or judge module (ref: research scope note). `execute_single(skill_text, case, trial_id, timeout_ms) -> ExecutionResult` is a stub: it builds messages via `build_messages(case)` and assigns hard-coded zeros (`output=""`, `files=[]`, `tokens={"input":0,"output":0}`, `tool_calls=[]`, `transcript=messages`), so only `duration_ms` carries a real value (ref: Q1, Q4). `skill_text` and `timeout_ms` are both passed in but never used inside the body (ref: Q1, Q9).

The `--skill` flag is `required=True`, flows `args.skill → EvalConfig.skill_path → run_suite`, where `load_skill` does a plain `open(path).read()` with no frontmatter parsing; the raw text is sha256-hashed (12-char prefix) and passed to `execute_single` (ref: Q2). Agent files carry `claude.tools` allowlist frontmatter (e.g. `Read, Write` for qrspi-questions) that the runtime currently ignores; a commented placeholder shows `tools=<tool_set>` as the intended hook (ref: Q12). `load_suite` validates top-level `{name, cases}` and per-case `{id, prompt, assertions}`, then `run_suite` fans out `(case × trial)` to a `ThreadPoolExecutor` drained by `as_completed` with no `timeout=` (ref: Q3, Q8, Q9). Fixture `context.files` are loaded lazily and CWD-relative inside `build_messages`, silently skipping misses, while suite.json stores them as `fixtures/...` relative to `evals/` (ref: Q1, Q3).

`ExecutionResult` is a dataclass with all nine target fields already present; serialization is `dataclasses.asdict` → `json.dump(..., indent=2)` into `<output_dir>/results.json` under a `skill_hash/skill_path/suite/timestamp/config/results` envelope (ref: Q4, Q7). `--output` is created with `os.makedirs(..., exist_ok=True)`; all trials aggregate into one flat in-memory list, no per-trial file, no rollup (ref: Q8). Errors: a broad `except Exception` in `execute_single` sets `result.error`; a second guard in `run_suite` around `future.result()` is unreachable today because `execute_single` never re-raises (ref: Q5, Q11). There are NO tests for `run_eval.py` and no model/network mocking — it is the lone pipeline script without a `_test.py` sibling (ref: Q13, Q14). No Anthropic SDK, no Claude CLI helper, and no `requirements.txt`/`pyproject.toml` exist; the module is stdlib-only, while every sibling orchestration script uses the `subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)` + `returncode` convention (ref: Q6, Q14). Logging is `print()`-only; `transcript` and `tokens` are the designated sinks but are never aggregated (ref: Q15).

## Desired End State

Per the ticket's approach, this ships option (a) — the **direct Anthropic SDK** path — with a follow-up tracked for option (b) tool-lockdown. Mapping each acceptance criterion to behavior:

- **AC1 — `execute_single` invokes the agent at the `--skill` path; consider renaming to `--agent`.** `execute_single` calls the Anthropic Messages API using `skill_text` as the system prompt and the `build_messages(case)` output as the conversation, so `skill_text` becomes load-bearing (ref: Q1, Q2). The `--skill` flag is retained as the primary name with `--agent` added as an alias (see Decision 4), so the documented invocation keeps working.
- **AC2 — capture output text, files produced, token usage, full transcript.** The real response populates `output` (concatenated text blocks), `tokens` (from the SDK `usage` object), `transcript` (input messages plus the assistant turn), and sets `executed=True` (the new status sentinel) so an empty-but-real run is distinguishable from the zeroed stub. `files` stays an empty list under the SDK path because direct Messages calls produce no filesystem side effects; a `tool_calls` capture remains zero-valued and is the explicit seam option (b) fills (ref: Q4, Q15). The model id and `max_tokens` passed to the call come from `suite.json` `defaults` (ref: Q3). Every populated field is a JSON-serializable dataclass attribute, so `asdict` serialization carries `executed` through unchanged (ref: Q4, Q7).
- **AC3 — honor `timeout_ms`.** `execute_single` enforces `timeout_ms` at the SDK call boundary (request-level timeout), converting an exceeded deadline into a populated `result.error` rather than an indefinite hang; the inert `as_completed` wait is addressed by the per-call timeout (ref: Q9).
- **AC4 — a real run produces non-empty `results.json` with real model output for the questions cases.** Running the documented command yields a `results.json` whose `results[*].output`/`tokens`/`transcript` reflect actual model responses, distinguishable from the zeroed stub (ref: Q7, Q10).

## Delta

- **Modified `scripts/run_eval.py`:** rewrite `execute_single` to call the Anthropic SDK behind a single mockable seam (a module-level `call_model(...)` function), reading the API key from the SDK's standard environment variable (no bespoke key plumbing); populate `output`, `tokens`, `transcript`, `error`, and `executed`; pass model id and `max_tokens` from `suite.json` `defaults`; enforce `timeout_ms`. Add `--agent` as an alias for `--skill` in `argparse`. Add the `executed: bool` field to `ExecutionResult`. Keep `load_skill`, `load_suite`, `build_messages`, the envelope, and `run_suite`'s fan-out unchanged in shape.
- **New file `scripts/run_eval_test.py`:** stdlib-only `_test.py` sibling that stubs `call_model` (no network) and asserts populated fields, error capture, and timeout-to-error behavior — closing the convention gap (ref: Q13, Q14).
- **New dependency surface:** the `anthropic` SDK becomes the first third-party import in this module (ref: Q6). A minimal `requirements.txt` (or equivalent) is needed since none exists.
- **`results.json` gains one field** — an `executed: bool` status sentinel is added to `ExecutionResult` (set `True` once a real model call returns, `False` for the stub/zeroed path) so a genuinely empty real run is unambiguously distinguishable from the old stub (resolves OQ2). All other fields already exist (ref: Q4, Q7); `executed` is JSON-serializable and flows through `asdict` unchanged.
- **Model id and `max_tokens` are sourced from `suite.json` `defaults`** — the runtime reads `defaults.model` / `defaults.max_tokens` from the loaded suite and passes them into `call_model()` (resolves OQ3). This activates the already-declared-but-ignored `defaults` block (ref: Q3) rather than introducing a new flag or hard-coding values.
- **API key handling is out of scope** — the SDK reads its key from its own standard environment variable; no bespoke key plumbing is added (resolves OQ5). The acceptance run carries a ~$20 cost ceiling across the 15 questions cases (resolves OQ5).
- **Fixture path rooting is deferred** — the `fixtures/...` CWD-relative loading issue (ref: Q1, Q3) is tracked under a separate ticket, not fixed here (resolves OQ4).
- **`--skill` keeps its name with `--agent` added as an alias** — no rename (resolves OQ1; see Decision 4), so the AC4 invocation string is preserved.

## Pattern Decisions

### Decision 1: Execution backend

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Direct Anthropic SDK `messages.create` (system=agent, user=case) | Fastest, cheapest, matches ticket recommendation; easy to inspect output/tokens | No tool-use; cannot assert tool lockdown; `files`/`tool_calls` stay empty |
| B | `claude-agent-sdk` Python runtime | Real agent loop, enforces `claude.tools` frontmatter | More setup, higher cost, deferred per ticket |
| C | Claude Code CLI subprocess | Closest to production; mirrors house `subprocess.run` pattern (ref: Q6) | Slowest, hardest to inspect, heaviest |

**Recommendation:** Option A.
**Rationale:** The ticket explicitly recommends (a) for speed with (b) as a tracked follow-up; research confirms no existing SDK/CLI helper to reuse (ref: Q6), so cost of entry is comparable, and A unblocks AC4 soonest.
**NEW PATTERN?** Yes — first third-party (`anthropic`) import in a stdlib-only module (ref: Q6, Discovered Patterns). Justified because no in-repo model-invocation helper exists to mirror; the subprocess convention fits CLIs (option C), not a direct SDK.

### Decision 2: Test seam for network isolation

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Wrap the SDK call in a module-level `call_model()` function, stub it in tests | Matches repo's "single mockable seam" expectation (ref: Q14); no network in tests | One extra indirection |
| B | `unittest.mock.patch` the `anthropic` client directly | No new function | Couples tests to SDK internals; brittle |

**Recommendation:** Option A.
**Rationale:** Research states a real runtime should isolate the model call behind a single seam so stdlib-only tests can stub it without network, mirroring how sibling tests fake `subprocess.run` (ref: Q14).
**NEW PATTERN?** No — extends the established mockable-seam + `_test.py` sibling convention (ref: Q13, Q14).

### Decision 3: Timeout enforcement point

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Pass `timeout_ms/1000` as the SDK request timeout; catch and write to `result.error` | Actually cancels the in-flight request; threads cannot be force-killed anyway (ref: Q9) | Per-request, not whole-trial wall clock |
| B | Add `as_completed(timeout=)` in `run_suite` | Centralized | Cannot kill the running thread; future stays alive (ref: Q9) |

**Recommendation:** Option A.
**Rationale:** Research notes `ThreadPoolExecutor` cannot forcibly kill a running thread, so enforcement must live at the call boundary (ref: Q9). Honors AC3 without restructuring the executor.
**NEW PATTERN?** No — the `timeout_ms` plumbing already exists end-to-end; this fills the no-op enforcement point (ref: Q9).

### Decision 4: `--skill` vs `--agent` flag

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Keep `--skill`, add `--agent` as an alias | Backward-compatible with documented command (ref: Q2); satisfies the ticket's "consider" softly | Two names for one flag |
| B | Rename `--skill` → `--agent` outright | Cleaner naming | Breaks the AC4 invocation string and any caller using `--skill` (ref: Q2) |

**Recommendation:** Option A.
**Rationale:** The ticket says "consider renaming," not "rename"; AC4 pins the literal `--skill` invocation, so an alias satisfies both without breaking the acceptance command (ref: Q2).
**NEW PATTERN?** No — standard `argparse` alias.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Tests hit the live API / require a key, breaking the stdlib-only `python3` test convention | med | high | Route all model calls through `call_model()` and stub it in `run_eval_test.py`; never import `anthropic` at test-collection time (ref: Q14) |
| Empty real run is byte-identical to the old stub in `results.json` (ref: Q10) | med | med | Real output/tokens/transcript will differ for the questions cases; treat an "executed" sentinel as an Open Question rather than silently changing schema |
| Fixtures silently dropped when runner not invoked from `evals/` (ref: Q1, Q3) | high | med | Out of scope for this ticket's ACs; flag in Open Questions so it is not assumed fixed |
| New `anthropic` dependency with no `requirements.txt`/`pyproject.toml` present (ref: Q6) | high | med | Add a minimal pinned requirements file; document install step; keep import local to the seam so collection stays cheap |
| `tokens` dict is loosely typed; SDK `usage` shape may not match stub `{input,output}` keys (ref: Q4, Q15) | med | low | Normalize SDK usage into the existing `{input,output}` keys at the seam boundary |

## Resolved Questions

These resolutions answer the change request on PR #180 ("incorporate answers"). The change
request body carried no inline answers (no review-thread comments, no PR comments, no Linear
comments), so each open question is resolved from the **ticket's stated approach and the
research findings**, not from any reviewer-supplied text — and the resolutions are folded into
the design above. Recorded here for traceability:

- OQ1 — Rename `--skill` to `--agent`, or keep an alias? **Resolved: keep the alias.** The
  ticket says "consider renaming flag to `--agent`" (a suggestion, not a directive) while AC4
  pins the literal `--skill` invocation, so `--skill` stays the primary name with `--agent`
  added as an alias (Decision 4); AC4's invocation is preserved (ref: Q2).
- OQ2 — Add an `executed`/status sentinel to `ExecutionResult`? **Resolved: yes, add `executed`.** An `executed: bool` field disambiguates a genuinely empty real run from the old stub (ref: Q10); see Delta and AC2.
- OQ3 — Source of truth for model id and `max_tokens`? **Resolved: use `suite.json` `defaults`.** The runtime reads `defaults.model` / `defaults.max_tokens` and passes them into `call_model()`, activating the already-declared-but-ignored block (ref: Q3).
- OQ4 — Fix the `fixtures/...` CWD-relative path rooting here? **Resolved: separate ticket.** Deferred; not in scope for this ticket's ACs (ref: Q1, Q3).
- OQ5 — API key sourcing and cost ceiling? **Resolved: no bespoke API-key handling** (the SDK reads its standard environment variable); the acceptance run carries a **~$20 cost ceiling** across the 15 questions cases (ref: Q3). Both points are confirmed by the reviewer on PR #180 ("no api key, $20"): no bespoke key handling, and $20 as the reviewer-supplied cost ceiling.
