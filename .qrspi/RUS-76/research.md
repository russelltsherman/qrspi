# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-14T00:00:00Z
**Generated:** 2026-06-14T00:00:00Z
**Status:** draft

## Q1: For each named consumer helper (`extractJsonObject`, `extractJsonArray`, `parseResolveEnvelope`, `parseOrderedTickets`, `parseSyncTrunkEnvelope`, `parseLandVerdict`, `parseConfigEnvelope`, `parseCriticsEnvelope`), which Python script produces the envelope it consumes?

**Answer:** Producer/consumer pairs (all parsers live in `.claude/workflows/qrspi-batch.js`):

| Consumer helper | Producer script | Producer entry | Stdout shape |
|---|---|---|---|
| `parseResolveEnvelope` | `scripts/qrspi_resolve.py` | `main` → `json.dump(env, …, indent=2)` then `print()` | one indented JSON object + trailing newline |
| `parseOrderedTickets` (via `extractJsonArray`) | `scripts/qrspi_order_tickets.py` | `main` → `json.dump(sort_tickets(...), sys.stdout)` | a JSON **array** (the sorted tickets), not an object |
| `parseSyncTrunkEnvelope` | `scripts/qrspi_sync_trunk.py` | `_run` → `print(json.dumps(envelope))` | single-line JSON object |
| `parseLandVerdict` | `scripts/qrspi_land_verify.py` | `main` → `print(json.dumps(verdict))` | single-line JSON object |
| `parseConfigEnvelope` | `scripts/qrspi_config.py` | `main` → `print(json.dumps({...}))` | single-line JSON object |
| `parseCriticsEnvelope` | `scripts/qrspi_critics_config.py` | `main` → `print(json.dumps({"ok":…,"phases":…,"warnings":…}))` | single-line JSON object |
| `extractJsonObject` / `extractJsonArray` | (low-level scanners) | n/a — used internally by the parsers above and by inline call sites | substring of free text |

`extractJsonObject` is also used directly (not just inside a named parser) at one inline call site for an LLM `{ "exists": … }` reply (qrspi-batch.js:2461), and `parseRestackEnvelope`/`parseCleanupEnvelope` (not named in the question) consume `scripts/qrspi_restack.py` and `scripts/qrspi_cleanup.py` respectively.

**Evidence:**

```
json.dump(env, sys.stdout, indent=2)
print()
return 0 if env["ok"] else 1
```

— `scripts/qrspi_resolve.py:413-415`

```
json.dump(sort_tickets(tickets, statuses), sys.stdout)
```

— `scripts/qrspi_order_tickets.py:116`

```
print(json.dumps({"ok": True, "key": key, "value": value}))
...
print(json.dumps({"ok": False, "key": key, "value": None, "error": str(exc)}))
```

— `scripts/qrspi_config.py:71-74`

**Dependencies:** Consumers (qrspi-batch.js) depend on producers (scripts/*.py) — a one-way data dependency through a worker agent's verbatim-stdout echo (the JS sandbox cannot run python, so a worker runs the script and returns its stdout as the agent's final message; qrspi-batch.js:30-34). No producer imports a consumer.

**Implicit contracts:** Each producer emits its JSON to stdout; the worker prompt instructs the agent to echo that stdout "exactly and verbatim, NO surrounding prose, NO code fences" (qrspi-batch.js:2424-2426, 2520-2523). The consumer must therefore tolerate prose/whitespace around the JSON (extractJsonObject/Array exist precisely because the echo is not guaranteed clean).

---

## Q2: What is the exact text/format the producers emit around their JSON, and how do `extractJsonObject`/`extractJsonArray` locate the JSON within that output?

**Answer:** Producers emit **raw JSON** to stdout (object via `json.dumps`/`json.dump`, array via `json.dump`), no fences, no wrapping prose. `qrspi_resolve.py` uses `indent=2` (pretty, multi-line) plus a trailing `print()` newline; the others emit single-line compact JSON. The *worker agent* echoes that stdout as its final message, so in practice the text the parser receives may carry leading/trailing prose despite the "verbatim" instruction — which is why extraction is by structural scan, not by parsing the whole string.

`extractJsonObject` finds the first `{`, then does a string-aware brace-depth scan (tracking `inStr`/`esc` so braces inside JSON string values do not fool it) and returns the substring from that `{` to the matching `}` where depth returns to 0; returns `null` if no `{` or never balances. `extractJsonArray` is the identical algorithm for `[`/`]` — added because `qrspi_order_tickets.py` emits a top-level **array**, to which `extractJsonObject` does not apply (qrspi-batch.js:240-242).

**Evidence:**

```
function extractJsonObject(text) {
  const s = String(text == null ? '' : text)
  const start = s.indexOf('{')
  if (start < 0) return null
  let depth = 0, inStr = false, esc = false
  for (let i = start; i < s.length; i++) {
    const c = s[i]
    if (inStr) {
      if (esc) esc = false
      else if (c === '\\') esc = true
      else if (c === '"') inStr = false
    } else if (c === '"') inStr = true
    else if (c === '{') depth++
    else if (c === '}') { depth--; if (depth === 0) return s.slice(start, i + 1) }
  }
  return null
}
```

— `.claude/workflows/qrspi-batch.js:202-218` (extractJsonArray is the bracket-twin at :243-259)

**Dependencies:** Both scanners are pure (only depend on the input string). All object-consuming parsers call `extractJsonObject`; only `parseOrderedTickets` calls `extractJsonArray`.

**Implicit contracts:** The scan returns the **outermost/first** balanced structure — it assumes the producer's JSON is the first `{`/`[` in the echo. A producer that prefixed JSON-shaped prose containing `{` before the real envelope would mis-extract. The string-awareness contract: any `{`/`}`/`[`/`]` inside a double-quoted JSON string is ignored.

---

## Q3: What is the required-field/shape contract each Python producer guarantees in its output envelope?

**Answer:**

- **resolve** (`qrspi_resolve.py` `build_envelope`, :222-237): `{ ok, repoRoot, worktreeDir, existing{questions,research,design,structure,plan,worktree:bool}, decision, commentTargets[], reviewers, teamReviewers, ticketContentPath, tip, slices[] }`, plus optional `error`. `decision` (from `qrspi_resolve_state.py` `resolve`, :149-156) is `{ action, phase, nextPhase, resetToPhase, discardPhases[], commentTargets[], changeRequested, reason }`; `action ∈ {entry_blocked, run_design, advance, submit, wait, revise, reset, land}` (the set is enumerated in JS as `RESOLVE_ACTIONS`, qrspi-batch.js:196-198).
- **ordered tickets** (`qrspi_order_tickets.py`): a JSON **array** — a permutation of the input `tickets` (each element is the original ticket object; sort is stable group-then-createdAt). No envelope wrapper.
- **sync-trunk** (`qrspi_sync_trunk.py`, :83-119): `{ ok, repoRoot, updated, from, to }` on ok paths; fail paths carry `{ ok:false, repoRoot, updated:false, …, error }`.
- **land verdict** (`qrspi_land_verify.py`, :63-68): `{ status: "landed"|"incomplete", openBranches: list[str] }`.
- **config** (`qrspi_config.py`, :17-18, 71-74): `{ ok:true, key, value }` (value str|null) on success; `{ ok:false, key, value:null, error }` on failure.
- **critics config** (`qrspi_critics_config.py`, :34-35, 209-212): `{ ok:true, phases:{<six phases>}, warnings:[…] }`; failure emits `{ ok:false, phases:<all defaults>, warnings:[], error }`. The six phases are questions/research/structure/plan (`{enabled,maxRounds}`), design (`{enabled,maxRounds,lenses,candidates}`), implementation (`{enabled,maxRounds,coherence:{enabled,maxRounds}}`).

**Evidence:**

```
env = {
    "ok": ok,
    "repoRoot": REPO_ROOT if repo_root is None else repo_root,
    "worktreeDir": worktree_dir,
    "existing": existing,
    "decision": decision,
    "commentTargets": comment_targets_of(decision),
    "reviewers": reviewers,
    "teamReviewers": team_reviewers,
    "ticketContentPath": ticket_content_path,
    "tip": tip,
    "slices": slices if slices is not None else [],
}
```

— `scripts/qrspi_resolve.py:222-234`

```
print(json.dumps({"ok": True, "phases": phases, "warnings": warnings}))
...
print(json.dumps({"ok": False, "phases": default_phases(), "warnings": [], "error": str(exc)}))
```

— `scripts/qrspi_critics_config.py:209-212`

**Dependencies:** `qrspi_resolve.py` embeds `qrspi_resolve_state.py`'s `decision` verbatim. The JS `DEFAULT_CRITIC_PHASES` (qrspi-batch.js:612-619) is hand-kept "in lockstep" with `qrspi_critics_config.py`'s defaults (comment at :610-611) — a contract verified only on the Python side by `qrspi_critics_config_test.py`, never cross-checked in JS today.

**Implicit contracts:** resolve guarantees `worktreeDir` ends with `/.worktrees/<ticketId>` (the parser hard-requires it, qrspi-batch.js:233). critics `enabled` defaults are uniformly **false/OFF** across all phases (opt-in); `maxRounds` default is 2.

---

## Q4: What is the input/return signature of each parser helper in `qrspi-batch.js`?

**Answer:** All are top-level declarations in `.claude/workflows/qrspi-batch.js`:

- `extractJsonObject(text) → string|null` (:202)
- `extractJsonArray(text) → string|null` (:243)
- `parseResolveEnvelope(text, ticketId) → envelope object` — on success the validated full envelope; on any failure `{ ok:false, error }` (:224)
- `parseOrderedTickets(text, original) → Array|null` — sorted array (a permutation of `original`) or `null` (:266)
- `parseSyncTrunkEnvelope(text) → {ok, …}` — validated envelope or `{ok:false, error}` (:296)
- `parseLandVerdict(text) → {status, openBranches[], error?}` (:330)
- `parseConfigEnvelope(text, key) → {ok, …}` — validated envelope or `{ok:false, error}` (:346)
- `parseCriticsEnvelope(text) → phases object` — always returns a full phases object (DEFAULT_CRITIC_PHASES or `{...defaults, ...phases}`); never throws (:369)

`text` is coerced via `String(text == null ? '' : text)` inside the extractors, so the parsers tolerate non-string/`null`/`undefined` input. `parseResolveEnvelope`/`parseConfigEnvelope` take a second validation argument (`ticketId`/`key`); `parseOrderedTickets` takes the original array for permutation validation.

**Evidence:**

```
function parseLandVerdict(text) {
  const raw = extractJsonObject(text)
  if (!raw) return { status: 'incomplete', openBranches: [], error: 'land-verify: no JSON verdict in worker output' }
  let v
  try { v = JSON.parse(raw) } catch (e) { return { status: 'incomplete', openBranches: [], error: `land-verify: unparseable verdict (${e.message})` } }
  if (v.status !== 'landed' && v.status !== 'incomplete') {
    return { status: 'incomplete', openBranches: [], error: 'land-verify: verdict missing/unknown status' }
  }
  return { status: v.status, openBranches: Array.isArray(v.openBranches) ? v.openBranches : [] }
}
```

— `.claude/workflows/qrspi-batch.js:330-339`

**Dependencies:** Each object parser depends on `extractJsonObject`; `parseOrderedTickets` on `extractJsonArray`; `parseResolveEnvelope` on the module-level `RESOLVE_ACTIONS` Set (:196); `parseCriticsEnvelope` on `DEFAULT_CRITIC_PHASES` (:612) and the injected `log` global (:376).

**Implicit contracts:** None are attached to any object/exports — see Q10. To call them from a `node:vm` test, an appended export shim must reference them by name (they are reachable by name within the compiled function body).

---

## Q5: How does `scripts/check_workflows_test.py` invoke `node` as a subprocess and detect/skip when `node` is absent?

**Answer:** It resolves the node binary once at module load via `shutil.which("node")` into `NODE`. A module-level `@unittest.skipIf(NODE is None, "node not installed")` decorator on the test class skips the whole class when node is unavailable (CI runners have node preinstalled, so it runs there). The `_run(*args)` helper invokes `subprocess.run([NODE, GATE, *args], capture_output=True, text=True)` where `GATE` is the absolute path to `check_workflows.js`, and tests assert on `proc.returncode` (0 pass / 1 fail) plus substring checks on `proc.stdout + proc.stderr`.

**Evidence:**

```
NODE = shutil.which("node")
...
def _run(*args):
    return subprocess.run([NODE, GATE, *args], capture_output=True, text=True)

@unittest.skipIf(NODE is None, "node not installed")
class CheckWorkflowsGate(unittest.TestCase):
    def test_real_workflow_passes(self):
        proc = _run(REAL_WORKFLOW)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
```

— `scripts/check_workflows_test.py:22,42-51`

**Dependencies:** Paths derive self-locatingly: `SCRIPT_DIR = dirname(abspath(__file__))`, `REPO_ROOT = dirname(SCRIPT_DIR)`, `GATE`/`REAL_WORKFLOW` built from those (:18-21).

**Implicit contracts:** The gate's exit-code contract is the asserted surface — 0 = all files compile, 1 = any fail (or no files given). Skipping (not failing) on a node-less machine keeps the Python suite green there.

---

## Q6: What harness globals does `qrspi-batch.js` reference at load time that a `node:vm` sandbox must stub?

**Answer:** The Workflow harness injects these globals (enumerated authoritatively in `check_workflows.js`): `agent, parallel, pipeline, phase, log, args, budget, workflow`. The file also references `process` but guards every use with `typeof process !== 'undefined'` (ENGINE_ROOT at :68-71, engineRootFor at :102), so `process` need not be stubbed for *loading*. Critically, the file is loaded by **compiling, not running** — `check_workflows.js` strips the lone `export` keyword and wraps the body in `return (async () => { … })()`, then calls `vm.compileFunction(wrapped, INJECTED, …)`, passing the injected names as **parameters** so the references resolve at compile time without ever executing. The two load-blocking features are: `export const meta` (ESM-only) and top-level `return` + top-level `await` (legal only inside the harness's async wrapper).

**Evidence:**

```
const INJECTED = ['agent', 'parallel', 'pipeline', 'phase', 'log', 'args', 'budget', 'workflow']
...
  const body = src.replace(/^export\s+const\s+meta\b/m, 'const meta')
  const wrapped = `return (async () => {\n${body}\n})()`
  vm.compileFunction(wrapped, INJECTED, { filename: file })
```

— `scripts/check_workflows.js:25,30-34`

```
const ENGINE_ROOT =
  (typeof process !== 'undefined' && process.env && process.env.CLAUDE_PLUGIN_ROOT) ||
  (typeof process !== 'undefined' && process.cwd && process.cwd()) ||
  '.'
```

— `.claude/workflows/qrspi-batch.js:68-71`

**Dependencies:** A `node:vm` test that wants to *load and call the parsers* (not just compile) must replicate this exact strip-export + async-wrap + INJECTED-params recipe. The top-level `return` at the file's end (qrspi-batch.js:2625) and top-level `await` (e.g. `await parallel(...)` at :2473) mean the body is only legal inside an async function. `log` is the only injected global the parsers actually invoke at runtime (`parseCriticsEnvelope` → `log(...)`, :376); a vm sandbox calling that parser must provide a `log` stub.

**Implicit contracts:** No `module.exports` exists anywhere (`grep` confirms only `export const meta`); the file is NOT a Node module. `Workflow` (capital W) is NOT an injected global — it appears only in CLAUDE.md prose; the injected workflow-control global is lowercase `workflow`.

---

## Q7: How does `scripts/run_tests.py` discover and aggregate `scripts/*_test.py` files?

**Answer:** `discover_tests(scripts_dir=SCRIPT_DIR, pattern=None)` lists `os.listdir(scripts_dir)`, keeps names ending in `_test.py`, sorts them, optionally filters by case-sensitive substring `pattern`, and returns absolute paths. `run_one(path, …)` runs each as its own subprocess `subprocess.run([python, path], capture_output=True, text=True, timeout=180)` (default `sys.executable`), treating exit 0 as pass and a `TimeoutExpired` as fail. `run_suite` iterates, prints `PASS`/`FAIL` per file, and `main` returns `1 if failures else 0` (exit-code propagation for CI). `SCRIPT_DIR` is self-located via `dirname(abspath(__file__))`.

**Evidence:**

```
names = sorted(
    n for n in os.listdir(scripts_dir)
    if n.endswith("_test.py")
)
if pattern:
    names = [n for n in names if pattern in n]
return [os.path.join(scripts_dir, n) for n in names]
```

— `scripts/run_tests.py:42-48`

```
proc = subprocess.run([python, path], capture_output=True, text=True, timeout=timeout)
ok = proc.returncode == 0
```

— `scripts/run_tests.py:61-67`

**Dependencies:** Picks up ANY new `scripts/<name>_test.py` automatically — a new producer/consumer test named e.g. `scripts/qrspi_contract_fixtures_test.py` is discovered with zero registration. It is the CI regression gate (`.github/workflows/tests.yml`).

**Implicit contracts:** A test file must (a) live in `scripts/`, (b) end in `_test.py`, (c) be runnable standalone as `python3 scripts/<name>_test.py`, and (d) exit 0 on success / non-zero on failure. `run_tests.py` itself is excluded (it is not a `*_test.py`); `run_tests_test.py` is a normal member that imports this module's functions guarded by `__main__` (:30-32). Per-file timeout is 180s.

---

## Q8: For each parser helper, what is the documented "fail-closed" behavior on malformed input?

**Answer:** All fail-closed by **returning a sentinel**, never throwing (every `JSON.parse` is wrapped in try/catch):

- `extractJsonObject` / `extractJsonArray`: return `null` when no opening bracket or never balances.
- `parseResolveEnvelope`: returns `{ ok:false, error:<reason> }` for no-JSON / unparseable / missing-ok / bad-worktreeDir / unknown-action; passes a clean producer `ok:false` through verbatim.
- `parseOrderedTickets`: returns `null` on no-array / unparseable / length-mismatch / id-multiset-mismatch (caller then keeps the unsorted queue — sort is "a nicety, never a gate", :262-265).
- `parseSyncTrunkEnvelope`: returns `{ ok:false, error }` for no-JSON / unparseable / missing-ok / (ok-but-missing updated/from/to).
- `parseLandVerdict`: returns `{ status:'incomplete', openBranches:[], error }` for no-JSON / unparseable / missing-or-unknown status — fails CLOSED to "not landed" so Done is never projected on ambiguity (:328-329).
- `parseConfigEnvelope`: returns `{ ok:false, error }` for no-JSON / unparseable / missing-ok / key-mismatch / non-string-value; passes clean producer `ok:false` through.
- `parseCriticsEnvelope`: returns `DEFAULT_CRITIC_PHASES` for no-JSON / unparseable / missing-or-non-object `phases` — fails OPEN to defaults so a garbled critic config never gates the run (:363-367). This is the one "fail-open-to-default" parser, distinct from the others' fail-closed-to-error.

**Evidence:**

```
function parseConfigEnvelope(text, key) {
  const raw = extractJsonObject(text)
  if (!raw) return { ok: false, error: 'config: no JSON envelope in worker output' }
  let env
  try { env = JSON.parse(raw) } catch (e) { return { ok: false, error: `config: unparseable envelope (${e.message})` } }
  if (typeof env.ok !== 'boolean') return { ok: false, error: 'config: envelope missing ok flag' }
  if (!env.ok) return env  // helper reported a clean ok:false — pass it through verbatim
  if (env.key !== key) return { ok: false, error: `config: envelope key mismatch (want ${key}, got ${env.key})` }
  if (typeof env.value !== 'string') return { ok: false, error: `config: envelope value not a string (got ${env.value})` }
  return env
}
```

— `.claude/workflows/qrspi-batch.js:346-356`

**Dependencies:** Caller behaviors differ on the sentinel: `parseConfigEnvelope` non-ok → `throw new Error(...)` aborting the run (qrspi-batch.js:2430-2434, a hard gate); `parseOrderedTickets` null → silently keep unsorted (:2526-2527); `parseSyncTrunkEnvelope` non-ok → hard gate; `parseLandVerdict` incomplete → block Done; `parseCriticsEnvelope` default → run continues with critics OFF.

**Implicit contracts:** No parser throws on malformed input — the sentinel IS the failure channel. Malformed-input fixtures should assert the exact sentinel **shape** (e.g. `{ok:false}` with a non-empty `error`, or `null`, or `DEFAULT_CRITIC_PHASES`), not an exception.

---

## Q9: How do the consumer helpers handle missing required fields vs wrong field types vs prose-wrapped-but-invalid JSON — distinct code paths?

**Answer:** Yes, three distinct paths with distinct outcomes (illustrated by `parseResolveEnvelope`/`parseConfigEnvelope`/`parseCriticsEnvelope`):

1. **Prose-wrapped-but-invalid JSON** is split into two sub-cases by extraction: (a) no balanced `{` at all → `extractJsonObject` returns `null` → "no JSON envelope" error (qrspi-batch.js:226, 348; criticsEnvelope → defaults at :371); (b) a balanced `{...}` extracted but not valid JSON → `JSON.parse` throws → caught → "unparseable envelope (<msg>)" error embedding the parse message (:228, 350; critics → defaults at :373).
2. **Missing required field**: checked field-by-field after parse. `typeof env.ok !== 'boolean'` → "missing ok flag" (:229, 351). `parseResolveEnvelope` further checks `env.decision` presence and `env.worktreeDir` shape (:233-236); `parseConfigEnvelope` checks `env.key !== key` (:353).
3. **Wrong field type**: also field-by-field — `parseConfigEnvelope` `typeof env.value !== 'string'` → "value not a string (got <v>)" (:354); `parseResolveEnvelope` `typeof env.worktreeDir !== 'string'` and the `.endsWith` suffix check (:233); `parseCriticsEnvelope` `typeof phases !== 'object' || Array.isArray(phases)` → defaults (:375).

So missing-field and wrong-type are merged into one validation block per field (the `typeof`/equality checks), distinct from the two extraction/parse paths above. Each emits a different `error` string, making them distinguishable.

**Evidence:**

```
function parseCriticsEnvelope(text) {
  const raw = extractJsonObject(text)
  if (!raw) return DEFAULT_CRITIC_PHASES
  let env
  try { env = JSON.parse(raw) } catch { return DEFAULT_CRITIC_PHASES }
  const phases = env && typeof env === 'object' ? env.phases : undefined
  if (!phases || typeof phases !== 'object' || Array.isArray(phases)) return DEFAULT_CRITIC_PHASES
  if (Array.isArray(env.warnings)) for (const w of env.warnings) log(`  config: ${w}`)
  return { ...DEFAULT_CRITIC_PHASES, ...phases }
}
```

— `.claude/workflows/qrspi-batch.js:369-378`

**Dependencies:** `parseResolveEnvelope` depends on `RESOLVE_ACTIONS` for the action-enum check (:235); a wrong `decision.action` is its own path (`unknown decision.action`). `parseCriticsEnvelope` collapses ALL three failure classes to the same outcome (DEFAULT_CRITIC_PHASES) — distinct error strings are NOT produced for it (fail-open), unlike resolve/config which produce distinct error strings.

**Implicit contracts:** A partial-but-valid critics envelope is **shallow-merged** over defaults (`{...DEFAULT_CRITIC_PHASES, ...phases}`, :377) — a present-but-partial `phases` does not drop unmentioned phase keys, but a nested partial (e.g. `design:{enabled:true}` without `lenses`) WOULD overwrite the whole `design` block (shallow merge, not deep) — a fixture-worthy edge.

---

## Q10: Are the top-level parser helpers attached to anything reachable from outside, or does loading under `node:vm` require an appended export shim referencing them by name?

**Answer:** They are NOT attached to anything. They are bare top-level `function` declarations (`extractJsonObject`, `parseResolveEnvelope`, …) and `const` arrow-bindings (`engineCmd`, `stg`, …). `grep -E "module.exports|exports\.|globalThis\."` over the file returns nothing; the only `export` is `export const meta` at line 1. So nothing is reachable from an importer/sandbox by default.

To call them from a `node:vm` test, an **appended export shim must reference each by name** — and that referencing works: the `check_workflows.js` load recipe compiles the whole body (including any appended trailing lines) as one async function, so a trailing assignment like `globalThis.__qrspiParsers = { parseResolveEnvelope, parseConfigEnvelope, … }` (or returning them) sits in the same lexical scope as the `function`/`const` declarations. `function` declarations are hoisted (referenceable anywhere in the body); `const` arrow helpers are NOT hoisted (referenceable only after their declaration line) — so a shim must be appended AFTER the declarations (i.e. at the end of the body, which is where the existing top-level `return` already is, line 2625). Note the file already ends in a top-level `return` (its run-time result), so a naive shim appended after that `return` would be dead code at runtime; a vm harness that wants the parsers either appends the shim BEFORE that return, replaces/wraps the return, or compiles a modified copy.

**Evidence:**

```
$ grep -nE "module.exports|exports\.|globalThis\.|^export " .claude/workflows/qrspi-batch.js
1:export const meta = {
```

(only `export const meta`; no other exports — verified this turn)

```
const engineCmd = (rel) => `${ENGINE_ROOT}/${rel}`
...
function extractJsonObject(text) {   // hoisted (function declaration)
```

— `.claude/workflows/qrspi-batch.js:76, 202`

**Dependencies:** A consumer-side test depends on (a) the exact `check_workflows.js` strip+wrap+INJECTED recipe to make the file loadable, and (b) a name-referencing shim. The `function`-vs-`const` hoisting distinction matters: all eight named parsers in Q4 are `function` declarations EXCEPT none — re-checked: `extractJsonObject`, `extractJsonArray`, `parseResolveEnvelope`, `parseOrderedTickets`, `parseRestackEnvelope`, `parseSyncTrunkEnvelope`, `parseCleanupEnvelope`, `parseLandVerdict`, `parseConfigEnvelope`, `parseCriticsEnvelope` are ALL `function` declarations (hoisted), so a shim placed anywhere in the body can name them. `DEFAULT_CRITIC_PHASES`/`RESOLVE_ACTIONS` they close over are `const` (must be initialized before the parser runs, which they are, at module top).

**Implicit contracts:** Because the file is loaded by COMPILE (not run) for the existing syntax gate, a test that needs to actually invoke the parsers must take the extra step of RUNNING the wrapped function (e.g. via `vm.runInNewContext` / `new Function`) with `log`/etc. stubbed — the existing gate never runs it.

---

## Q11: Where do existing committed fixtures live, and what directory layout/naming does the repo use that a new per-seam fixtures directory should match?

**Answer:** The ONLY committed file-fixtures directory is `evals/fixtures/` — but it belongs to the eval harness, which CLAUDE.md and the repo memory both flag as a **non-functional placeholder**. Its naming is `<phase>_<scenario>.md` / `.txt` (e.g. `research_rest_endpoint.md`, `git_diff_rest_endpoint.txt`, `ticket_websocket.md`), i.e. full QRSPI-phase artifacts, NOT JSON envelopes for the JS↔Python seam.

The Python *unit* tests (the relevant, functional convention) do NOT use a committed fixtures directory at all — they embed fixtures as **inline string/dict constants** in the test module and write transient files via `tempfile.TemporaryDirectory()` when a file on disk is needed. `scripts/check_workflows_test.py` exemplifies this: `VALID_WORKFLOW`/`BROKEN_WORKFLOW` are inline string constants written to a temp dir per test. So there is **no existing per-seam JSON fixtures directory** to match — a new one would be a new pattern. The closest committed-fixtures precedent is `evals/fixtures/` (placeholder).

**Evidence:**

```
$ ls evals/fixtures
README.md  design_billing_migration.md  ...  research_rest_endpoint.md
ticket_rest_endpoint.md  worktree_session1.md  ...

VALID_WORKFLOW = (
    "export const meta = { name: 'x', description: 'y' }\n"
    "log('hi')\n"
    "const data = await agent('do a thing')\n"
    "return { ok: true, data }\n"
)
```

— `evals/fixtures/` listing; `scripts/check_workflows_test.py:27-32`

**Dependencies:** `evals/` is driven by `scripts/run_eval.py` (also a placeholder). It is NOT discovered by `run_tests.py` (that runner only sweeps `scripts/*_test.py`).

**Implicit contracts:** The functional-test convention is inline-constant + temp-dir, scoped under `scripts/`. A new committed fixtures dir would diverge from that convention; if introduced, `evals/fixtures/`'s `<category>_<scenario>.<ext>` flat-file naming is the only committed precedent.

---

## Q12: What is the existing convention for a Python test that drives a `node` subprocess and feeds it fixtures?

**Answer:** Exactly ONE such test exists: `scripts/check_workflows_test.py`. Its convention:
1. Resolve `NODE = shutil.which("node")` at module load; gate the class with `@unittest.skipIf(NODE is None, …)`.
2. Self-locate paths from `__file__` (`SCRIPT_DIR`, `REPO_ROOT`, `GATE`, `REAL_WORKFLOW`).
3. Wrap the call in `_run(*args) → subprocess.run([NODE, GATE, *args], capture_output=True, text=True)`.
4. Feed fixtures by writing an inline-constant string into a `tempfile.TemporaryDirectory()` file, then passing its path as an argv arg (`_run(p)`) — fixtures go in as **files via argv**, not stdin, in this test.
5. Assert on `proc.returncode` for the pass/fail contract and `assertIn("FAIL", proc.stdout + proc.stderr)` for the message contract.

For feeding fixtures over **stdin** (which the seam producers like `qrspi_order_tickets.py` use), the precedent is in the *Python-to-Python* tests, not node tests — e.g. a producer test pipes a JSON envelope to the script's stdin. A consumer-side node test would combine #1-#5 above with stdin-piping (`subprocess.run([...], input=fixture_json, …)`).

**Evidence:**

```
with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, "ok.js")
    with open(p, "w") as fh:
        fh.write(VALID_WORKFLOW)
    proc = _run(p)
    self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
```

— `scripts/check_workflows_test.py:54-59`

**Dependencies:** `unittest` + stdlib only (`os`, `shutil`, `subprocess`, `tempfile`) — no pytest, matching the repo-wide stdlib-only rule (CLAUDE.md "stdlib-only unit tests").

**Implicit contracts:** Output is captured (`capture_output=True, text=True`) and asserted only on returncode + stdout/stderr substrings — never on side-effect files. Tests must skip (not fail) when `node` is absent so the suite stays green node-less.

---

## Q13: When a parser fail-closes on malformed input, what diagnostic does it emit, and is it surfaced to the workflow run output?

**Answer:** Two diagnostic mechanisms, depending on the parser:

1. **Embedded `error` string in the returned sentinel** (resolve/config/sync-trunk/land/restack/cleanup): the parser packs a human-readable, source-tagged message into `error` (e.g. `'config: unparseable envelope (<JSON.parse msg>)'`, `'resolve: worktreeDir not <repo>/.worktrees/<id> (got <v>)'`). Each is prefixed by the seam name (`config:`, `resolve:`, `sync-trunk:`, `land-verify:`). This `error` is surfaced only when the **caller** acts on it: e.g. `parseConfigEnvelope` non-ok is re-thrown into the run as `throw new Error('qrspi-batch: could not resolve project scope from config — ${cfg.error}')` (qrspi-batch.js:2434), which the per-ticket try/catch logs. `parseLandVerdict`'s `error` rides inside the verdict but the Done gate keys off `status`, not `error` — the error text is informational.
2. **`log()` calls** (criticsEnvelope only): on a VALID envelope it logs each `env.warnings` entry as `  config: <w>` (:376); on the fail-open default path it logs **nothing** (silent fallback). So a garbled critics config produces NO diagnostic at all — it silently degrades to critics-OFF.

`parseOrderedTickets` emits NO diagnostic — it returns `null` silently and the caller keeps the unsorted queue with no log (a deliberate "nicety, never a gate" design, :262-265). So drift in the order seam would be **invisible** at runtime.

**Evidence:**

```
if (!cfg.ok) {
  throw new Error(`qrspi-batch: could not resolve project scope from config — ${cfg.error ?? 'unknown error'}`)
}
```

— `.claude/workflows/qrspi-batch.js:2430-2434`

```
if (Array.isArray(env.warnings)) for (const w of env.warnings) log(`  config: ${w}`)
return { ...DEFAULT_CRITIC_PHASES, ...phases }
```

— `.claude/workflows/qrspi-batch.js:376-377` (no log on the earlier `return DEFAULT_CRITIC_PHASES` fail paths)

**Dependencies:** `log` is the injected harness global; its output is the workflow run log (surfaced to the run output). Re-thrown `Error`s are caught by the per-ticket loop's try/catch and logged as `${t.id}: ERRORED — ${summary}` (qrspi-batch.js near :2615).

**Implicit contracts:** Debuggability is **uneven** across seams: config/resolve/sync surface a tagged error on the act path; critics and order fail SILENTLY (default / null). A regression test asserting "drift is debuggable" can only assert the embedded `error` text for the loud seams; for critics/order the only assertable signal is the returned-value difference (defaults vs custom; unsorted vs sorted), not a log line.

---

## Discovered Patterns

- **Worker-echo seam (no StructuredOutput):** Every Python producer's JSON is returned to JS not by a structured-output tool but by a worker agent echoing the script's stdout verbatim as its final message; the JS side re-extracts + re-validates. This was a deliberate choice — the weak local worker model emitted empty `{}` against StructuredOutput schemas and stalled the batch (qrspi-batch.js:183-187). Extraction-by-brace-scan exists precisely to tolerate an imperfect echo.
- **Self-locating scripts:** Producers and runners derive their root from `__file__` / their own path (`SCRIPT_DIR = dirname(abspath(__file__))`), so they run from any cwd (run_tests.py:28, check_workflows_test.py:18-21, and the resolve/persist/pr_body scripts per CLAUDE.md).
- **Two fail-modes by design:** Most parsers fail-CLOSED to an error sentinel that the caller turns into a hard stop (config/sync = gates); two fail differently — `parseOrderedTickets` returns `null`→keep-unsorted (nicety) and `parseCriticsEnvelope` fails-OPEN to defaults (never gates). `parseLandVerdict` fails-closed to `incomplete` so Done is never falsely projected.
- **Stdlib-only, subprocess-per-file testing:** All tests are `unittest`, no pytest; `run_tests.py` runs each `*_test.py` as its own subprocess and gates CI on exit codes. Fixtures are inline constants + `tempfile`, not committed files.
- **Compile-not-run loading of the workflow:** `check_workflows.js` proves the canonical way to load `qrspi-batch.js` outside the harness — strip the one `export`, async-wrap, `vm.compileFunction` with INJECTED params. A consumer test that must *invoke* parsers needs to additionally RUN that wrapped function with `log` stubbed.

## Inconsistencies

- **`Workflow` (capital) vs `workflow` (lowercase):** The questions and CLAUDE.md prose reference `Workflow` as a global/entrypoint (e.g. `Workflow({ name: "qrspi-batch", … })`), but the actual injected global per `check_workflows.js` is lowercase `workflow` (check_workflows.js:25). `Workflow` is the user-facing tool name, not a script-scope global.
- **`DEFAULT_CRITIC_PHASES` lockstep is asserted only in Python:** The JS defaults (qrspi-batch.js:612-619) are documented as kept "in lockstep with the Python resolver's defaults (verified there by qrspi_critics_config_test.py)" — but there is NO test that cross-checks the JS copy against the Python producer. The two can silently drift; this is exactly the seam the ticket-shaped contract-fixture work would cover.
- **Silent seams undercut debuggability (Q13):** `parseOrderedTickets` (null) and `parseCriticsEnvelope` (default) emit NO diagnostic on malformed input, while resolve/config/sync emit tagged errors. A drift in the order or critics seam would degrade silently — inconsistent with the "fail loud" discipline the config/sync seams follow.
- **`evals/fixtures/` is committed but its harness is a placeholder:** The only committed fixtures directory is driven by a non-functional eval harness (CLAUDE.md + memory both flag `evals/` + `run_eval.py` as a placeholder). It is NOT swept by `run_tests.py`, so its fixtures are not exercised by the functional CI gate — a committed-but-inert asset.
- **resolve emits pretty (indented) JSON, others emit single-line:** `qrspi_resolve.py` uses `json.dump(..., indent=2)` + trailing `print()` while config/sync/land/critics use single-line `json.dumps`. The brace-scan extractor handles both, but a fixture set must reflect this per-producer formatting difference (multi-line vs single-line) to be faithful.
