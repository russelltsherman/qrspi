# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-09T00:00:00Z
**Generated:** 2026-06-09T00:00:00Z
**Status:** draft

Scope note: All facts below are from `scripts/run_eval.py` (241 lines), `evals/suite.json`,
`.claude/agents/qrspi-questions.md`, and `scripts/check_scope.py`, all under
`/workspaces/qrspi/.worktrees/RUS-34`. `run_eval.py` is the **entire** eval-execution module —
there is no companion runtime, scoring, or judge module in `scripts/`.

## Q1: What inputs does `execute_single` currently receive (parameters and types), and how are the agent prompt and case prompt assembled into messages before the stubbed return?

**Answer:** `execute_single` receives four positional inputs: `skill_text: str` (the full agent prompt file contents), `case: dict` (one entry from `suite["cases"]`), `trial_id: int`, and `timeout_ms: int`. It constructs an `ExecutionResult` seeded with `case_id` and `trial_id`, then inside a `try` block calls `build_messages(case)` and assigns the *stubbed* zero values (`output=""`, `files=[]`, `tokens={"input":0,"output":0}`, `tool_calls=[]`, `transcript=messages`). `skill_text` is **never used** inside `execute_single` (it is passed but only referenced in the commented-out placeholder block). `build_messages(case)` assembles messages by: extending with `case["context"]["conversation_history"]`, reading each existing file in `case["context"]["files"]` and appending `--- {path} ---\n{content}` blocks, then appending one `{"role":"user","content":<prompt + file context>}` message. Note `build_messages` reads `context["files"]` paths **as-is** relative to CWD (`os.path.exists(file_path)`), but suite.json stores them as `fixtures/...` (relative to `evals/`).

**Evidence:**

```python
def execute_single(skill_text, case, trial_id, timeout_ms) -> ExecutionResult:
    start = time.time()
    result = ExecutionResult(case_id=case["id"], trial_id=trial_id)
    try:
        # ── Placeholder for agent execution ──
        messages = build_messages(case)
        result.output = ""
        result.files = []
        result.tokens = {"input": 0, "output": 0}
        result.tool_calls = []
        result.transcript = messages
    except Exception as e:
        result.error = str(e)
    result.duration_ms = (time.time() - start) * 1000
    return result
```

— `scripts/run_eval.py:93-143`

```python
user_content = case["prompt"]
if file_context_parts:
    user_content += "\n\n" + "\n\n".join(file_context_parts)
messages.append({"role": "user", "content": user_content})
```

— `scripts/run_eval.py:85-90`

**Dependencies:** Upstream caller `run_suite` (`run_eval.py:170-177`) via `executor.submit`. Calls `build_messages` (`run_eval.py:67-90`). Constructs `ExecutionResult` (`run_eval.py:19-29`).
**Implicit contracts:** `case` must contain `id`, `prompt` (enforced by `load_suite`), and optionally `context.{conversation_history,files}`. `build_messages` silently skips fixture files that don't exist at CWD-relative path — no error is raised for a missing fixture.

## Q2: How is the `--skill` flag value read, parsed, and propagated from argument parsing down to `execute_single`, and what other call sites or functions reference that flag value?

**Answer:** `--skill` is declared `required=True` in `main()` and read as `args.skill` (a path string). It is passed to `EvalConfig(skill_path=args.skill, ...)`. `run_suite` loads its contents once via `skill_text = load_skill(config.skill_path)` and (a) computes `skill_hash = sha256(skill_text)[:12]`, (b) records `config.skill_path` in the output envelope, and (c) passes `skill_text` into every `execute_single` call. So the flag's *path* reaches the output JSON and the hash; its *contents* reach `execute_single` as `skill_text` but are then unused (see Q1). `load_skill` just does `open(path).read()` with no frontmatter parsing.

**Evidence:**

```python
parser.add_argument("--skill", required=True, help="Path to skill/agent prompt file")
...
config = EvalConfig(skill_path=args.skill, suite_path=args.suite, output_dir=args.output, ...)
```

— `scripts/run_eval.py:219, 227-234`

```python
def load_skill(skill_path: str) -> str:
    with open(skill_path) as f:
        return f.read()
```

— `scripts/run_eval.py:61-64`

**Dependencies:** `main` → `EvalConfig` → `run_suite` → {`load_skill`, `hashlib.sha256`, `execute_single`}.
**Implicit contracts:** The skill file must be a readable text file at the given path. No frontmatter/tool-allowlist parsing occurs (relevant to Q12). The 12-char sha256 prefix is the version identity stamped into `results.json`.

## Q3: How are per-case prompts and any fixture inputs loaded from the suite file (`evals/suite.json`) and routed into each execution trial?

**Answer:** `load_suite(config.suite_path)` opens and `json.load`s the suite, validates top-level required fields `{"name","cases"}` and per-case required fields `{"id","prompt","assertions"}`, and returns the dict. `run_suite` iterates `suite["cases"]` and, for each case × `range(config.trials)`, submits `execute_single(skill_text, case, trial, config.timeout_ms)`. The fixture `context.files` are NOT loaded by the suite loader; they are loaded lazily inside `build_messages` per execution (Q1). suite.json defines extra fields not validated or consumed by the runner: `version`, `description`, `split`, `defaults.{trials_per_case,timeout_ms,max_tokens}`, and per-case `name/phase/context.user_preferences/assertions/tags/difficulty/split`. Notably `defaults.trials_per_case` and `defaults.timeout_ms` in suite.json are **ignored** — the runner uses CLI/`EvalConfig` defaults instead.

**Evidence:**

```python
required = {"name", "cases"}
missing = required - set(suite.keys())
if missing:
    raise ValueError(f"Suite missing required fields: {missing}")
for case in suite["cases"]:
    case_required = {"id", "prompt", "assertions"}
    case_missing = case_required - set(case.keys())
    if case_missing:
        raise ValueError(f"Case {case.get('id', '?')} missing: {case_missing}")
```

— `scripts/run_eval.py:47-56`

```python
for case in cases:
    for trial in range(config.trials):
        future = executor.submit(execute_single, skill_text, case, trial, config.timeout_ms)
        futures[future] = (case["id"], trial)
```

— `scripts/run_eval.py:168-177`

**Dependencies:** `run_suite` → `load_suite` → `json`. `evals/suite.json` is the data contract (15 cases, `case_001`..`case_015`).
**Implicit contracts:** Each case's `assertions` are required by the loader but never executed by `run_eval.py` (no scoring stage exists; `script`-type assertions reference `scripts/check_scope.py`, run separately). Fixture paths in suite.json are `fixtures/...` (relative to `evals/`), implying the runner is expected to be invoked with CWD=`evals/` or paths to be re-rooted — currently unhandled.

## Q4: What fields does the `ExecutionResult` type define, and which of them already have a representation versus needing one?

**Answer:** `ExecutionResult` is a `@dataclass` with: `case_id: str`, `trial_id: int`, `output: str=""`, `files: list=[]`, `duration_ms: float=0.0`, `tokens: dict={}`, `tool_calls: list=[]`, `transcript: list=[]`, `error: Optional[str]=None`. Every field already exists as a dataclass attribute. Mapping to the question's categories: **output text** → `output`; **files produced** → `files`; **token usage** → `tokens`; **full transcript** → `transcript`; plus `tool_calls`, `duration_ms`, `error`. The structure is fully present; what is missing is any code that *populates* them with real values — the stub writes empty/zero defaults (Q1). `duration_ms` is the only field populated with a real (non-stub) value today (wall-clock around the stub block).

**Evidence:**

```python
@dataclass
class ExecutionResult:
    case_id: str
    trial_id: int
    output: str = ""
    files: list = field(default_factory=list)
    duration_ms: float = 0.0
    tokens: dict = field(default_factory=dict)
    tool_calls: list = field(default_factory=list)
    transcript: list = field(default_factory=list)
    error: Optional[str] = None
```

— `scripts/run_eval.py:19-29`

**Dependencies:** Constructed in `execute_single`; serialized via `dataclasses.asdict` in `run_suite` (`run_eval.py:185`).
**Implicit contracts:** `asdict(result)` requires all fields be JSON-serializable (str/int/float/list/dict/None) — they are. `tokens` is loosely typed `dict` with stub keys `{"input","output"}` (no schema enforced).

## Q5: What is the current signature and return contract of `execute_single`, and which downstream stages consume its return value?

**Answer:** Signature: `execute_single(skill_text: str, case: dict, trial_id: int, timeout_ms: int) -> ExecutionResult`. It always returns an `ExecutionResult` (never raises out — exceptions are caught and stored in `result.error`). Downstream, `run_suite` retrieves it via `future.result()`, converts it with `asdict(result)` into `all_results`, derives a console `status` from `result.error`, and prints `result.duration_ms`. The single consumer of the return value is therefore `run_suite`'s completion loop; the serialized dict lands in `results.json` under `results`. There is no scoring/judging consumer in the repo.

**Evidence:**

```python
result = future.result()
all_results.append(asdict(result))
status = "ERROR" if result.error else "OK"
print(f"  [{completed}/{total_runs}] {case_id} trial={trial} {status} ({result.duration_ms:.0f}ms)")
```

— `scripts/run_eval.py:184-187`

**Dependencies:** Producer `execute_single`; sole consumer `run_suite` (`run_eval.py:180-194`). No other module imports `run_eval`.
**Implicit contracts:** Callers rely on `execute_single` never raising (it catches all exceptions). The outer `try` in `run_suite` (line 183-194) only guards against `future.result()` raising — which the current impl cannot do — so its fallback dict (`{case_id, trial_id, error}`) is effectively dead unless `execute_single` is later made to raise.

## Q6: Is there an existing client, SDK import, or subprocess helper anywhere in the repo for invoking Anthropic models or the Claude Code CLI that this runtime could call?

**Answer:** NOT FOUND — no Anthropic SDK and no Claude CLI invocation helper exists. Searched `grep -rn 'import anthropic|from anthropic|Anthropic(|claude -p|"claude"|claude_api'` across all `.py` files: zero matches. There is no `anthropic` dependency declared (no `requirements.txt`/`pyproject.toml` found at root). The repo DOES contain a `using-claude-cli` skill reference and a test `scripts/using_claude_cli_skill_test.py`, but that is documentation/skill metadata, not a callable runtime helper. `subprocess.run` is used elsewhere, exclusively for `git`/`gh`/`gt` orchestration, never for a model/agent: `qrspi_pr_state.py` (git), `qrspi_resolve.py`, `qrspi_pr_body.py`, `qrspi_clear_stale_pr.py`, `qrspi_cleanup.py`, `qrspi_revise_amend.py`, `qrspi_restack.py`. `run_eval.py` itself imports only stdlib (`argparse, json, os, time, hashlib, dataclasses, pathlib, typing, concurrent.futures`).

**Evidence:**

```
$ grep -rn 'import anthropic|from anthropic|Anthropic(' . --include=*.py   → (no matches)
$ grep -rn 'subprocess.run' scripts/*.py
scripts/qrspi_pr_state.py:229: subprocess.run(["git", "branch", "--list", ...])
scripts/qrspi_pr_body.py:150:  subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)   # gt/gh
... (all git/gh/gt, none model-related)
```

— search over `/workspaces/qrspi/.worktrees/RUS-34/scripts/*.py`; `scripts/run_eval.py:8-16` (imports)

**Dependencies:** None — `run_eval.py` has no inbound dependency on any invocation helper because none exists.
**Implicit contracts:** Existing subprocess helpers follow a pattern of `subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)` and inspect `res.returncode` (see Q11 pattern note) — a convention a new model-subprocess helper could mirror.

## Q7: Where and in what format does `run_eval.py` write `results.json`, and what schema does the serialization step expect from each `ExecutionResult`?

**Answer:** `run_suite` builds an `output` dict and writes it to `os.path.join(config.output_dir, "results.json")` via `json.dump(output, f, indent=2)`. The envelope schema is: `skill_hash` (12-char sha256), `skill_path`, `suite` (the suite `name`), `timestamp` (`%Y-%m-%dT%H:%M:%SZ` gmtime), `config: {trials, timeout_ms}`, and `results: [<list of dicts>]`. Each result dict is `dataclasses.asdict(ExecutionResult)` — i.e. exactly the 9 `ExecutionResult` fields (Q4) — EXCEPT in the `future.result()` exception fallback, which appends a *partial* dict `{case_id, trial_id, error}` only (schema divergence — see Inconsistencies).

**Evidence:**

```python
output = {
    "skill_hash": skill_hash, "skill_path": config.skill_path,
    "suite": suite["name"],
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "config": {"trials": config.trials, "timeout_ms": config.timeout_ms},
    "results": all_results,
}
output_path = os.path.join(config.output_dir, "results.json")
with open(output_path, "w") as f:
    json.dump(output, f, indent=2)
```

— `scripts/run_eval.py:197-211`

**Dependencies:** `run_suite` → `dataclasses.asdict`, `json`, `time`. Output dir from `config.output_dir` (the `--output` flag).
**Implicit contracts:** Every result must be JSON-serializable. The filename is hard-coded `results.json` (the question header says `results.json`; matches). Any consumer of `results.json` must tolerate the heterogeneous result shape (full 9-field vs 3-field error dict).

## Q8: How is the `--output` directory created, validated, and used to persist per-trial output, and how are multiple `--trials` aggregated into a single results file?

**Answer:** `--output` is `required=True`, stored as `config.output_dir`. `run_suite` creates it with `os.makedirs(config.output_dir, exist_ok=True)` — no other validation (no write-permission check, no emptiness check). There is **no per-trial file**: every trial's `ExecutionResult` is collected into a single in-memory `all_results` list and written once to one `results.json`. Aggregation across `--trials` is purely by appending each `(case × trial)` result to `all_results` in `as_completed` order (so result ordering is nondeterministic w.r.t. completion, not case/trial order). `total_runs = len(cases) * config.trials`. There is no per-case rollup, no statistics, and no variance/aggregate computation — just a flat list.

**Evidence:**

```python
os.makedirs(config.output_dir, exist_ok=True)
...
all_results = []
cases = suite["cases"]
total_runs = len(cases) * config.trials
...
for future in as_completed(futures):
    ...
    all_results.append(asdict(result))
```

— `scripts/run_eval.py:152, 157-159, 180-185`

**Dependencies:** `os.makedirs`; `ThreadPoolExecutor(max_workers=config.max_workers)` parallelism (`run_eval.py:166`). `results/` dir exists in repo with only `.gitkeep`.
**Implicit contracts:** `--output` (e.g. `results/v1`) is treated as a directory, not a file. Re-running overwrites `results.json` in place. Trial isolation is logical only — all trials share the same Python process and (per stub) do no real I/O, so the "isolated environments" docstring claim (line 4) is currently unrealized.

## Q9: How does `timeout_ms` currently flow into `execute_single`, and what behavior occurs at the call site when an execution exceeds it?

**Answer:** `timeout_ms` flows: `--timeout` (default 120000) → `args.timeout` → `EvalConfig.timeout_ms` → passed as the 4th arg to every `execute_single(... config.timeout_ms)`. Inside `execute_single` the `timeout_ms` parameter is **completely unused** — it is never read, never passed to any timer, and never enforced. `as_completed(futures)` is called with **no `timeout=` argument**, so the completion loop waits indefinitely. There is therefore NO timeout behavior at the call site today: an execution that exceeded `timeout_ms` would not be cancelled or flagged. (`EvalConfig` default is 120000 at line 39; CLI default is also 120000 at line 224.)

**Evidence:**

```python
def execute_single(skill_text, case, trial_id, timeout_ms) -> ExecutionResult:
    ...   # timeout_ms is never referenced in the body
```

— `scripts/run_eval.py:93-143`

```python
with ThreadPoolExecutor(max_workers=config.max_workers) as executor:
    ...
    for future in as_completed(futures):   # no timeout= argument
```

— `scripts/run_eval.py:166, 180`

**Dependencies:** `argparse` → `EvalConfig` → `execute_single` (param) and `run_suite` (`as_completed`).
**Implicit contracts:** A future runtime is expected to honor `timeout_ms`; the plumbing exists end-to-end but the enforcement point (inside `execute_single` and/or `as_completed(timeout=)`) is a no-op. ThreadPoolExecutor cannot forcibly kill a running thread, so enforcing this likely requires subprocess-level timeout (mirroring the `subprocess.run(..., timeout=)` convention).

## Q10: What happens when an agent invocation produces no files or empty output text — does the current serialization path distinguish that from the zeroed stub result?

**Answer:** No — there is no distinction. The stub always produces `output=""`, `files=[]`, `tokens={"input":0,"output":0}`, `error=None`. A real invocation that legitimately produced empty output / no files would serialize to the **identical** dict. The serialization path (`asdict`) has no sentinel, no "executed but empty" marker, and no flag separating "ran and produced nothing" from "stub never ran." The only signal that something went wrong is `error` being non-None (set only on exception). `duration_ms` would differ (stub ~0ms vs real >0ms) but nothing keys off that. So "empty output" and "zeroed stub" are indistinguishable in `results.json`.

**Evidence:**

```python
result.output = ""
result.files = []
result.tokens = {"input": 0, "output": 0}
result.tool_calls = []
result.transcript = messages
```

— `scripts/run_eval.py:133-137`

**Dependencies:** `execute_single` (producer of stub values) → `asdict` serialization.
**Implicit contracts:** Downstream scorers (which don't exist yet) would need a positive "executed" signal (e.g., non-empty `transcript`, or a new status field) to tell a successful-but-empty run from the unimplemented stub. `transcript` is the only field currently non-empty even in the stub (it holds the built messages).

## Q11: How are errors and non-zero exit conditions from an invocation surfaced today, and is there an existing error field on `ExecutionResult` or an exception path in the trial loop?

**Answer:** `ExecutionResult` HAS an `error: Optional[str]` field (line 29). Two error paths exist: (1) Inside `execute_single`, a broad `except Exception as e: result.error = str(e)` (lines 139-140) — the result is still returned with `error` set and other fields at stub defaults. (2) In `run_suite`'s completion loop, a second `try/except` around `future.result()` prints `EXCEPTION` and appends the partial 3-field dict `{case_id, trial_id, error}` (lines 188-194) — but since `execute_single` itself never re-raises, path (2) is currently unreachable. There is NO concept of a "non-zero exit code" yet because no subprocess is spawned; exit-condition handling would be new. Console surfacing: `status = "ERROR" if result.error else "OK"`.

**Evidence:**

```python
except Exception as e:
    result.error = str(e)
```

— `scripts/run_eval.py:139-140`

```python
try:
    result = future.result()
    all_results.append(asdict(result))
    status = "ERROR" if result.error else "OK"
    ...
except Exception as e:
    print(f"  [{completed}/{total_runs}] {case_id} trial={trial} EXCEPTION: {e}")
    all_results.append({"case_id": case_id, "trial_id": trial, "error": str(e)})
```

— `scripts/run_eval.py:183-194`

**Dependencies:** `execute_single` (inner try) and `run_suite` (outer try). Sibling subprocess scripts inspect `res.returncode` after `subprocess.run` (e.g., `qrspi_resolve.py:210`) — the established non-zero-exit pattern a real runtime would follow.
**Implicit contracts:** `error` is a free-form string; consumers branch only on truthiness. The dual error layers assume `execute_single` *might* raise once it does real work; today only the inner layer fires.

## Q12: How is the agent file at the `--skill` path read, and what frontmatter or tool-allowlist fields exist in that file that the runtime references?

**Answer:** The agent file is read whole by `load_skill` (`open(path).read()`, Q2) — as plain text, with **no YAML frontmatter parsing**. The runtime references **zero** frontmatter fields. The agent files DO carry frontmatter: `.claude/agents/qrspi-questions.md` (lines 1-6) has `name`, `description`, and `claude:\n  tools: Read, Write` — a tool-allowlist (`tools`) field. This `tools` allowlist is NOT read by `run_eval.py`; the stub's commented placeholder shows `tools=<tool_set>` as a TODO (line 122-123), implying a real runtime would parse this frontmatter to bound the agent's tool access. Currently the entire file (frontmatter + body) is hashed and passed as opaque `skill_text`.

**Evidence:**

```yaml
---
name: qrspi-questions
description: Internal QRSPI workflow agent — generates 8-15 technical questions ...
claude:
  tools: Read, Write
---
```

— `.claude/agents/qrspi-questions.md:1-6`

```python
def load_skill(skill_path: str) -> str:
    with open(skill_path) as f:
        return f.read()        # no frontmatter parse, returns raw text
```

— `scripts/run_eval.py:61-64`

**Dependencies:** `load_skill` consumer in `run_suite`. The 8 agent files in `.claude/agents/` (`qrspi-{questions,research,design,structure,plan,worktree,implement,pr}.md`) are the `--skill` targets; each uses the same `claude.tools` frontmatter convention.
**Implicit contracts:** Agent frontmatter encodes an intended tool allowlist (`Read, Write` for questions). A real runtime is expected (per the placeholder `tools=<tool_set>`) to extract and enforce it. No YAML parser (`pyyaml`) is currently imported anywhere in `run_eval.py` (stdlib-only).

## Q13: What existing tests cover `run_eval.py`, and do any of them assert on `execute_single` output or stub behavior that a real runtime would change?

**Answer:** NOT FOUND — there are NO tests for `run_eval.py`. `grep -rln 'run_eval|execute_single|ExecutionResult|run_suite'` across all `.py` files returns only `scripts/run_eval.py` itself. There is no `scripts/run_eval_test.py` (the conventional `_test.py` sibling pattern used by every other `scripts/qrspi_*.py`). Consequently, no test asserts on `execute_single`'s stub output, so wiring a real runtime would not break any existing test — but it also means there is zero regression safety net for the current behavior. (By contrast, the codebase convention is strong: `qrspi_resolve_test.py`, `qrspi_pr_state` tests, `qrspi_pr_body_test.py`, `qrspi_cleanup_test.py`, etc. all exist as stdlib-only `_test.py` siblings.)

**Evidence:**

```
$ grep -rln 'run_eval\|execute_single\|ExecutionResult\|run_suite' . --include='*.py'
scripts/run_eval.py        ← only the module itself; no *_test.py
$ ls scripts/ | grep -i eval
run_eval.py                ← no run_eval_test.py
```

— search over `/workspaces/qrspi/.worktrees/RUS-34`

**Dependencies:** None — no test imports `run_eval`.
**Implicit contracts:** Project convention (CLAUDE.md "Codebase conventions") is stdlib-only `_test.py` siblings run with `python3`; `run_eval.py` is the lone tested-pipeline script without one. The CLAUDE.md explicitly labels `evals/` + `run_eval.py` a "non-functional placeholder."

## Q14: How is model/network access mocked or stubbed in the current eval test setup, if at all?

**Answer:** NOT FOUND — there is no test setup at all (Q13), therefore no mocking/stubbing of model or network access. The only "stub" is in production code: `execute_single`'s commented placeholder block and hard-coded zero returns (Q1) — that is a hand-rolled no-op, not a test double. No `unittest.mock`, no `monkeypatch`, no fixtures, no fake-client, and no network calls exist to mock (the module is offline/stdlib-only). The established pattern for the rest of `scripts/` is to mock `subprocess.run` in `_test.py` siblings (e.g., the qrspi resolver tests fake `gh`/`git` calls); a real model runtime here would presumably need the same `subprocess.run` seam to be test-mockable.

**Evidence:**

```
$ grep -rln 'mock\|monkeypatch\|MagicMock' scripts/run_eval*.py   → (no run_eval test file exists)
```

— search over `/workspaces/qrspi/.worktrees/RUS-34/scripts`; stub is `scripts/run_eval.py:116-137`

**Dependencies:** None.
**Implicit contracts:** To stay consistent with the repo's stdlib-only test convention, a real runtime should isolate the model/subprocess call behind a single seam (function or `subprocess.run`) so tests can stub it without network.

## Q15: What logging, transcript capture, or token-usage accounting exists in `run_eval.py` today, and where is the "full transcript" expected to be stored or emitted?

**Answer:** Logging is `print()`-only to stdout: a header (`Running N executions...`, `Skill hash:`, `Max workers:`), one progress line per completed run (`[i/total] case_id trial=t OK/ERROR (Nms)`), and a final `Results written to <path>`. No `logging` module, no log file, no levels. **Transcript capture:** the `ExecutionResult.transcript` field is the storage location; in the stub it holds `build_messages(case)` (the input messages only — no assistant turns). The "full transcript" is expected to be emitted into `results.json` under each result's `transcript` array (serialized via `asdict`) — there is no separate per-transcript file. **Token accounting:** the `tokens` dict (stub `{"input":0,"output":0}`) is the only accounting field; it is never summed, aggregated, or reported across trials/cases. `duration_ms` is the only metric actually computed.

**Evidence:**

```python
print(f"Running {total_runs} executions ({len(cases)} cases x {config.trials} trials)")
print(f"Skill hash: {skill_hash}")
...
print(f"  [{completed}/{total_runs}] {case_id} trial={trial} {status} ({result.duration_ms:.0f}ms)")
...
print(f"\nResults written to {output_path}")
```

— `scripts/run_eval.py:161-163, 187, 213`

```python
result.transcript = messages   # built inputs only; lands in results.json via asdict
```

— `scripts/run_eval.py:137`

**Dependencies:** stdout (`print`); `results.json` (transcript/token sink via `asdict`); `time` for `duration_ms`.
**Implicit contracts:** `transcript` must be a JSON-serializable list of message dicts. A real runtime is expected to append assistant/tool turns to `transcript` and fill `tokens` from the provider's usage object (commented `result.tokens = response.usage`, line 128). No aggregate token/cost rollup mechanism exists to extend.

---

## Discovered Patterns

- **Single-module pipeline, stdlib-only.** `run_eval.py` imports only the standard library (`argparse, json, os, time, hashlib, dataclasses, pathlib, typing, concurrent.futures`) — `scripts/run_eval.py:8-16`. No third-party deps; no `requirements.txt`/`pyproject.toml` at repo root. `pathlib.Path` is imported but unused.
- **Dataclass + asdict serialization.** Results use `@dataclass` (`ExecutionResult`, `EvalConfig`) and serialize via `dataclasses.asdict` → `json.dump(..., indent=2)`. Mirrors no other script (others are git/gh JSON over subprocess), so this is the eval subsystem's own convention.
- **ThreadPoolExecutor fan-out.** `(case × trial)` work units submitted to `ThreadPoolExecutor(max_workers=config.max_workers)`, drained with `as_completed` — `run_eval.py:166-194`. Thread-based, so true process isolation (claimed in docstring line 4) is not provided.
- **subprocess convention (elsewhere, not here).** Every other orchestration script invokes external CLIs via `subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)` then checks `res.returncode` (`qrspi_resolve.py:210`, `qrspi_pr_body.py:150`, `qrspi_cleanup.py:95`, `qrspi_revise_amend.py:165`, `qrspi_restack.py:132`, `qrspi_clear_stale_pr.py:122`, `qrspi_pr_state.py:229+`). This is the house pattern a model/CLI runtime would mirror.
- **`_test.py` sibling test convention.** Every pipeline script in `scripts/` except `run_eval.py` has a stdlib-only `*_test.py` sibling (CLAUDE.md states they run with `python3`). `run_eval.py` is the sole exception.
- **Agent frontmatter carries a `claude.tools` allowlist.** All 8 `.claude/agents/qrspi-*.md` files use `---\nname/description\nclaude:\n  tools: ...\n---`. This is structured metadata the eval runtime is positioned to parse but currently ignores.
- **Suite assertion taxonomy.** `evals/suite.json` cases carry `assertions` of three `type`s: `programmatic` (named checks like `output_file_exists(...)`, `no_solution_language(...)`), `llm_judge` (free-text `criteria`), and `script` (e.g. `scripts/check_scope.py --log ... --allowed ...`). No runner in the repo executes any of these assertion types; `check_scope.py` is the only assertion implementation present and is a standalone CLI.

## Inconsistencies

- **Stub vs docstring.** The module docstring (`run_eval.py:1-6`) and `execute_single` docstring (lines 99-109) promise "isolated environments/containers," "capturing full transcripts, outputs, and metrics." The implementation does none of this — it returns hard-coded zeros (lines 133-137). CLAUDE.md openly labels the whole thing a "non-functional placeholder."
- **Unused parameters.** `execute_single` accepts `skill_text` and `timeout_ms` but uses neither (Q1, Q9). `pathlib.Path` is imported but never used (`run_eval.py:14`).
- **Ignored suite defaults.** `evals/suite.json` declares `defaults.{trials_per_case:3, timeout_ms:120000, max_tokens:128000}` (lines 10-14), but `run_eval.py` ignores these and uses `EvalConfig`/CLI defaults. `max_tokens` has no representation anywhere in the runtime.
- **Heterogeneous results schema.** Normal results are full 9-field `asdict(ExecutionResult)` dicts; the `future.result()` exception fallback appends a 3-field `{case_id, trial_id, error}` dict (lines 190-194). Any `results.json` consumer must handle both shapes — and the fallback is currently unreachable because `execute_single` never re-raises (Q5, Q11).
- **Empty-result ambiguity.** A genuinely empty real run is byte-identical to the unimplemented stub in `results.json` (Q10) — no "executed" sentinel exists.
- **Fixture path rooting.** suite.json stores `context.files` as `fixtures/...` (relative to `evals/`), but `build_messages` resolves them with CWD-relative `os.path.exists` and silently skips misses (`run_eval.py:78-83`) — fixtures will be silently dropped unless the runner is invoked from `evals/`.
- **Timeout plumbed but not enforced.** `timeout_ms` reaches `execute_single` and there is no `as_completed(timeout=)` — the value is inert (Q9).
