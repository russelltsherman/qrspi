# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** draft

## Q1: How does the `project` value reach the Query phase's `list_issues` call today, and what is the exact code path from `input?.project` to the `PROJECT` constant to the call site?

**Answer:** The path is three hops, all in `.claude/workflows/qrspi-batch.js`:
1. `args` (the workflow invocation argument) is parsed into `input` — either a JSON-parsed string or the object itself (lines 60–62).
2. `PROJECT` is bound directly to `input?.project` at line 67. Its documented contract: `undefined ⇒ all projects`.
3. At the Query phase, `PROJECT` is interpolated into the per-status `list_issues` agent prompt at line 922, where a truthy `PROJECT` adds a `- project: "<value>"` line and a falsy one substitutes a "do not pass a project argument" instruction.

There is no config-file involvement anywhere in this path today — `PROJECT` derives solely from the runtime `input`.

**Evidence:**

```
const input = typeof args === 'string'
  ? (() => { try { return JSON.parse(args) } catch { return undefined } })()
  : args
const STATUSES = input?.statuses ?? ['Selected', 'Design Review', 'Plan Review', 'Code Review']
const PROJECT = input?.project // undefined ⇒ all projects
```

— `.claude/workflows/qrspi-batch.js:60-67`

```
- limit: 250${PROJECT ? `\n- project: "${PROJECT}"` : '\n(do not pass a project argument — include every project)'}
```

— `.claude/workflows/qrspi-batch.js:922`

**Dependencies:** Upstream: the workflow runner's `args`. Downstream: the Query phase `list_issues` agent prompt only (see Q7). No script/helper feeds it.
**Implicit contracts:** `undefined`/falsy `PROJECT` means "all projects" — the absence of the value is overloaded as a sentinel. Any config-derived default would change that sentinel's meaning (see Q7/Q11).

## Q2: How does `/qrspi-ticket` currently obtain the `linearProject` value from `.qrspi/config.json`, and what mechanism does it use to read the file given the workflow sandbox constraints?

**Answer:** `/qrspi-ticket` is a prose SKILL (not the JS workflow), so it is not under the workflow JS sandbox — it runs as a normal Claude Code session with file-read tools. Step 3 ("Create Linear issue on approval") instructs the agent to read `.qrspi/config.json` (noting "it may not exist") and use its `linearProject` field, **defaulting to `"QRSPI"` when unset**. The read is performed by the agent following the prose, not by a deterministic helper. The resolved project is then passed to `mcp__linear__save_issue` as the `project` argument.

**Evidence:**

```
1. Resolve the Linear destination — never hard-code a team. Read `.qrspi/config.json`
   (it may not exist):
   - `team`: use its `linearTeam` field. ...
   - `project`: use its `linearProject` field, defaulting to `"QRSPI"` when unset.

2. Call `mcp__linear__save_issue` with:
   ...
   - `project`: the project resolved in step 1
```

— `.claude/skills/qrspi-ticket/SKILL.md:106-117`

**Dependencies:** Upstream: `.qrspi/config.json` (`linearProject` key). Downstream: `mcp__linear__save_issue`'s `project` argument.
**Implicit contracts:** The `"QRSPI"` literal is the documented default when the file is missing or the key is absent — this is the only place in the repo that fixes a default project value (the workflow uses `undefined`, see Q7). The read is agent-prose, so no programmatic JSON parsing/validation exists here.

## Q3: What is the established pattern for a self-locating, stdlib-only helper that reads from the repo root, and what command-line interface and output format do those helpers expose?

**Answer:** Both `scripts/qrspi_resolve.py` and `scripts/qrspi_persist.py` follow an identical pattern:
- **Self-location:** the repo root is derived from `__file__` (two levels up: `<repo>/scripts/<helper>.py`), never from `cwd` and never from an argument. The stated rationale: the weak local worker model corrupts the literal `qrspi` token in hand-typed paths, so all qrspi-laden paths are computed inside the script.
- **Stdlib-only:** `argparse`, `json`, `os`, `sys` (plus `shutil`/`subprocess` as needed). No third-party imports.
- **CLI:** short, token-free flags the worker can reproduce (`--ticket`, `--artifact`, `--linear-status`, etc.).
- **Output:** a single JSON envelope printed to **stdout** with an `ok` boolean and, on failure, a verbatim `error` string. Exit code 0 on success, non-zero on error. Failures are reported ONCE, never retried.

`qrspi_resolve.py` additionally demonstrates the config-read pattern relevant to this ticket: `_read_reviewer_config()` opens `<REPO_ROOT>/.qrspi/config.json`, `json.load`s it, returns `{}` on any `OSError`/`ValueError`, and never raises (best-effort).

**Evidence:**

```
# The script lives at <repo-root>/scripts/qrspi_persist.py, so the repo root is
# two levels up. Deriving it from __file__ (not cwd, not an argument) is the whole
# point: it removes the path the worker model keeps corrupting.
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(_SCRIPT_DIR)
```

— `scripts/qrspi_persist.py:37-41` (identical idiom at `scripts/qrspi_resolve.py:40-41`)

```
def _read_reviewer_config():
    path = os.path.join(REPO_ROOT, ".qrspi", *REVIEWER_CONFIG)  # config.json
    try:
        with open(path) as fh:
            cfg = json.load(fh)
        return cfg if isinstance(cfg, dict) else {}
    except (OSError, ValueError):
        return {}
```

— `scripts/qrspi_resolve.py:254-264` (`REVIEWER_CONFIG = ["config.json"]` at line 54)

```
env = {"ok": error is None, "repoRoot": REPO_ROOT, "src": src, "dest": dest, "bytes": bytes_written}
if error is not None: env["error"] = error
json.dump(env, sys.stdout, indent=2); print()
return 0 if error is None else 1
```

— `scripts/qrspi_persist.py:102-114`

**Dependencies:** These helpers are invoked by one-line worker agents spawned from `qrspi-batch.js` (see Q8). They read only `<REPO_ROOT>/.qrspi/...` and the worktree filesystem; no network in the pure parts.
**Implicit contracts:** (a) caller types only short tokens; (b) all `qrspi`-laden paths computed internally from `__file__`; (c) stdout is exactly one JSON envelope, parseable verbatim; (d) config reads are best-effort and return `{}` (never raise) when the file is missing/invalid.

## Q4: What arguments does the workflow's Query phase `list_issues` call accept, and how is the `project:` argument conditionally included versus omitted to mean "every project"?

**Answer:** The Query phase does not call `list_issues` from JS — it builds a **prompt** for an agent that calls `mcp__linear__list_issues`. The prompt lists these arguments: `state` (the per-status value), `assignee: "me"`, `limit: 250`, and **conditionally** `project`. The conditional is a JS ternary on the `PROJECT` constant: if `PROJECT` is truthy it appends a newline + `- project: "${PROJECT}"`; otherwise it appends `\n(do not pass a project argument — include every project)`. The agent returns each ticket as `{ id, title, status }` validated against `TICKETS_SCHEMA`.

**Evidence:**

```
agent(
  `Use mcp__linear__list_issues with:
- state: "${status}"
- assignee: "me"
- limit: 250${PROJECT ? `\n- project: "${PROJECT}"` : '\n(do not pass a project argument — include every project)'}

Return every ticket as { id, title, status } with id like "RUS-8" and status "${status}". Nothing else.`,
  { label: `list:${status.toLowerCase().replace(/\s+/g, '-')}`, phase: 'Query', schema: TICKETS_SCHEMA }
)
```

— `.claude/workflows/qrspi-batch.js:918-925`

**Dependencies:** Upstream: `STATUSES` (line 66, mapped via `parallel`), `PROJECT` (line 67). Downstream: `mcp__linear__list_issues`; result feeds the dedup loop at lines 930–939.
**Implicit contracts:** The Linear `project` argument is omitted entirely (not passed empty) to mean "all projects"; the agent is explicitly told NOT to pass the argument in that branch. The id format contract is `"RUS-8"`.

## Q5: How are `args`/`input` values passed into the workflow at invocation, and what fields besides `project` does the workflow currently read from `input`?

**Answer:** The workflow runner supplies `args` (a global). The workflow normalizes it: if `args` is a string it `JSON.parse`s it (returning `undefined` on parse failure), otherwise it uses the object as-is, binding the result to `input` (lines 60–62). The documented shape (comment at lines 58–59) is `{ statuses?: string[], project?: string, reconcile?: boolean, reconcileDryRun?: boolean }`. The workflow reads four fields from `input`:
- `input?.statuses` → `STATUSES` (default `['Selected', 'Design Review', 'Plan Review', 'Code Review']`) — line 66
- `input?.project` → `PROJECT` (default `undefined`) — line 67
- `input?.reconcile === true` → `RECONCILE` (default off) — line 74
- `input?.reconcileDryRun !== false` → `RECONCILE_DRY_RUN` (default true) — line 75

**Evidence:**

```
// Optional overrides: { statuses?: string[], project?: string,
//                       reconcile?: boolean, reconcileDryRun?: boolean }
const input = typeof args === 'string'
  ? (() => { try { return JSON.parse(args) } catch { return undefined } })()
  : args
const STATUSES = input?.statuses ?? ['Selected', 'Design Review', 'Plan Review', 'Code Review']
const PROJECT = input?.project // undefined ⇒ all projects
...
const RECONCILE = input?.reconcile === true
const RECONCILE_DRY_RUN = input?.reconcileDryRun !== false // default true
```

— `.claude/workflows/qrspi-batch.js:58-75`

**Dependencies:** Upstream: workflow runner `args`. Downstream: each constant gates a distinct branch (Query, reconciliation).
**Implicit contracts:** All `input` fields are optional with `?.` access, so the workflow runs with no args at all (`input` may be `undefined`). A malformed JSON string silently degrades to `undefined` (defaults apply) — no error surfaced.

## Q6: What is the current shape and field list of `.qrspi/config.example.json`, and how is the `linearProject` field documented there?

**Answer:** `.qrspi/config.example.json` is a single JSON object with a leading `$comment` field plus four data fields: `reviewers`, `teamReviewers`, `linearTeam`, `linearProject`. The `$comment` documents all of them. `linearProject` is described as "the Linear project, defaulting to 'QRSPI'", and in the example it is set to `"QRSPI"`. The file is the template; the real `.qrspi/config.json` is gitignored.

**Evidence:**

```
{
  "$comment": "Optional QRSPI local config. Copy to .qrspi/config.json (gitignored) to use it. REVIEWERS: ... LINEAR: 'linearTeam' is the Linear team /qrspi-ticket files new issues under (if unset, the skill discovers/asks); 'linearProject' is the Linear project, defaulting to 'QRSPI'.",
  "reviewers": ["@me"],
  "teamReviewers": [],
  "linearTeam": "Your Linear Team",
  "linearProject": "QRSPI"
}
```

— `.qrspi/config.example.json:1-7`

**Dependencies:** Consumed (today) only by `/qrspi-ticket` prose (Q2, `linearProject`/`linearTeam`) and `qrspi_resolve.py` (`reviewers`/`teamReviewers`, Q3). `qrspi-batch.js` does NOT read this file today.
**Implicit contracts:** The example documents `linearProject` default as `"QRSPI"`, but that default is enforced only in `/qrspi-ticket` prose (Q2) — there is no programmatic default in any script. The file is optional/gitignored; consumers must tolerate its absence.

## Q7: Where is the `PROJECT` constant consumed throughout the workflow beyond the Query phase, and would changing its default from `undefined` to a config-derived value affect any other branch?

**Answer:** `PROJECT` is **consumed in exactly one place**: the Query phase `list_issues` prompt at line 922. A full grep of `qrspi-batch.js` for `PROJECT` returns only its definition (line 67) and that single call site (line 922). No other branch (Resolve, Restack, Design, Plan, Implementation, Finalize, Reconcile) references it. Therefore changing its default from `undefined` to a config-derived value would affect **only** which tickets the Query phase enumerates — it would not alter any downstream phase logic directly. The behavioral consequence: a non-`undefined` default flips the line-922 ternary from the "all projects" branch to the "scope to project" branch by default (see Q11), so the default scope changes from all-projects to the configured project.

**Evidence:**

```
const PROJECT = input?.project // undefined ⇒ all projects
```

— `.claude/workflows/qrspi-batch.js:67` (only definition)

```
- limit: 250${PROJECT ? `\n- project: "${PROJECT}"` : '\n(do not pass a project argument — include every project)'}
```

— `.claude/workflows/qrspi-batch.js:922` (only consumer)

Grep result for `PROJECT` (token, excluding "Project" in prose): definition at line 67 and consumer at line 922 — no others.

**Dependencies:** Downstream of `PROJECT` is solely the Query ticket enumeration; all later phases operate on the resulting `tickets` array regardless of how it was scoped.
**Implicit contracts:** The `undefined ⇒ all projects` sentinel is load-bearing. A config-derived default must preserve a way to express "all projects" (today: omit the argument) or it silently narrows the batch sweep.

## Q8: How does the workflow invoke one-line agents that run shell helpers at phase boundaries, and what is the mechanism for capturing a helper's stdout back into a workflow variable?

**Answer:** The workflow uses the `agent(prompt, opts)` primitive (awaited). The pattern for capturing a helper's stdout: spawn an agent told to run EXACTLY one verbatim `python3 scripts/<helper>.py ...` command and return the JSON stdout. Two variants:
- **Schema variant** (`persistArtifact`, lines 286–299): pass `{ schema: PERSIST_SCHEMA }`; the agent's parsed structured result is returned by `agent(...)` directly. `runPhase` reads `p.ok`/`p.bytes`/`p.error` off it (lines 317–322).
- **Plain-text variant** (`resolveTicket`, lines 337–390): NO schema — the agent returns the script's JSON stdout as plain text (the comment at lines 334–336 explains the StructuredOutput tool stalled the weak local worker, so "Option A" returns text), and the JS parses it via `parseResolveEnvelope(out, t.id)` at line 390.

So stdout is captured either via a StructuredOutput schema or by returning raw text and JS-parsing it. The agent always runs from "the main repo root" cwd, and the helper self-locates the rest.

**Evidence:**

```
async function persistArtifact(id, name, phaseLabel) {
  return await agent(
    `You are the PERSIST worker for ${id} artifact "${name}". Your cwd is the main repo root.
Run EXACTLY this one command verbatim ...:
  python3 scripts/qrspi_persist.py --ticket ${id} --artifact ${name}
... Parse that JSON and return it verbatim. ...`,
    { label: `persist:${id}:${name}`, phase: phaseLabel, schema: PERSIST_SCHEMA }
  )
}
```

— `.claude/workflows/qrspi-batch.js:286-299`

```
// NO schema: the worker returns the script's JSON stdout as plain text; we parse it
// with parseResolveEnvelope() ...
const out = await agent(`You are the RESOLVE worker ... python3 scripts/qrspi_resolve.py ...`,
    { label: `resolve:${t.id}`, phase: 'Resolve' })
return parseResolveEnvelope(out, t.id)
```

— `.claude/workflows/qrspi-batch.js:334-390`

**Dependencies:** `agent()`, `parallel()`, `phase()`, `log()` are workflow runner built-ins (no inline definition in the file). Helpers are the self-locating scripts of Q3.
**Implicit contracts:** (a) the agent must run the command verbatim with no path edits; (b) it returns exactly the JSON (verbatim, no fences/prose) so JS can parse it; (c) HARD STOP on `ok:false` — no retries/improvisation; (d) a parse failure or null agent result is treated as a skip/failure for that ticket.

## Q9: How does the existing config-reading path behave when `.qrspi/config.json` is absent or when the `linearProject` key is missing, and what fallback is applied?

**Answer:** Two distinct readers exist, with different fallback handling:
- **`/qrspi-ticket` prose** (the `linearProject` reader): explicitly tolerates a missing file ("it may not exist") and falls back to `"QRSPI"` when `linearProject` is unset (`.claude/skills/qrspi-ticket/SKILL.md:112`). For `linearTeam` (different key) it discovers/asks; for `linearProject` the documented default is the literal `"QRSPI"`.
- **`qrspi_resolve.py`** (the only programmatic config reader, currently for reviewers, not project): `_read_reviewer_config()` returns `{}` on any `OSError`/`ValueError` (file missing OR malformed JSON), never raising; per-key resolution then applies each field's own default via `select_source(config, key, default)` — `config[key]` when present, else the supplied default. This is the established programmatic pattern a new project-config reader would follow.

There is **no** programmatic reader for `linearProject` today.

**Evidence:**

```
   - `project`: use its `linearProject` field, defaulting to `"QRSPI"` when unset.
```

— `.claude/skills/qrspi-ticket/SKILL.md:112`

```
def _read_reviewer_config():
    ...
    try:
        with open(path) as fh:
            cfg = json.load(fh)
        return cfg if isinstance(cfg, dict) else {}
    except (OSError, ValueError):
        return {}
```

— `scripts/qrspi_resolve.py:254-264`

```
def select_source(config, key, default):
    if isinstance(config, dict) and key in config:
        return _as_token_list(config[key])
    return list(default)
```

— `scripts/qrspi_resolve.py:84-90`

**Dependencies:** Both readers depend on `<REPO_ROOT>/.qrspi/config.json` being optional/gitignored.
**Implicit contracts:** Missing-or-invalid config must degrade gracefully to a documented default, never raise. The prose path's `"QRSPI"` default and the script path's per-key `default` argument are two different mechanisms for the same intent.

## Q10: How does the Query phase currently behave when `PROJECT` resolves to an empty string or a project name that matches no Linear project, and is there any validation of the resolved value?

**Answer:** There is **no validation** of `PROJECT` anywhere in the workflow.
- **Empty string `""`:** `PROJECT` is falsy, so the line-922 ternary takes the "do not pass a project argument — include every project" branch. An empty string therefore behaves identically to `undefined` — the batch sweeps all projects (the empty string is NOT passed to Linear).
- **Non-matching project name:** a truthy non-matching name takes the "scope to project" branch and is passed verbatim to `mcp__linear__list_issues`. The workflow does not check the result against the requested project; it simply receives whatever tickets the MCP call returns (presumably zero). The downstream code logs `Found 0 ticket(s)` and returns early with `note: "No tickets in ..."` (lines 941–946) — it does NOT distinguish "no tickets in a real project" from "project name typo'd / matched nothing." No error is raised.

**Evidence:**

```
- limit: 250${PROJECT ? `\n- project: "${PROJECT}"` : '\n(do not pass a project argument — include every project)'}
```

— `.claude/workflows/qrspi-batch.js:922`

```
log(`Found ${tickets.length} ticket(s): ${tickets.map(...).join(', ') || '(none)'}`)
if (tickets.length === 0) {
  const reconciliation = RECONCILE ? await runReconciliation(new Set()) : undefined
  return { ticketsProcessed: 0, note: `No tickets in ${STATUSES.join(' / ')}`, reconciliation }
}
```

— `.claude/workflows/qrspi-batch.js:941-946`

**Dependencies:** Outcome depends entirely on what `mcp__linear__list_issues` returns for the given project string.
**Implicit contracts:** Falsy `PROJECT` (`undefined`, `""`, `0`, `null`) all mean "all projects". A typo'd project name silently yields an empty sweep indistinguishable from a legitimately empty queue — no validation, no warning specific to the project scope.

## Q11: What value of `input.project` currently triggers the "include every project" branch, and how is that branch distinguished from a normal project name at the call site?

**Answer:** The "include every project" branch is triggered by any **falsy** value of `PROJECT` (`input.project`): `undefined` (the default when the field is absent), `null`, `""`, `0`, or `false`. The distinction at the call site (line 922) is a plain JS truthiness ternary `PROJECT ? ... : ...`: a truthy value (any non-empty string project name) emits `- project: "${PROJECT}"`; a falsy value emits `(do not pass a project argument — include every project)`. There is no explicit sentinel like `"all"` or `"*"` — "all projects" is encoded as the absence/falsiness of the value, exactly as the line-67 comment states (`undefined ⇒ all projects`).

**Evidence:**

```
const PROJECT = input?.project // undefined ⇒ all projects
...
- limit: 250${PROJECT ? `\n- project: "${PROJECT}"` : '\n(do not pass a project argument — include every project)'}
```

— `.claude/workflows/qrspi-batch.js:67,922`

**Dependencies:** Upstream `input.project` (Q5); downstream the Linear `project` argument inclusion.
**Implicit contracts:** "All projects" and "no project specified" are the same state — there is no way today to *explicitly* request all-projects while a config default is set, because the only signal is falsiness. This is the central tension a config-derived default introduces (see Q7 / Inconsistencies).

## Q12: What is the structure of an existing stdlib-only `_test.py` sibling — test runner, assertions, and how it stubs or fixtures the repo-root file reads?

**Answer:** Two distinct stdlib-only test styles coexist:
- **`unittest` style** (`scripts/qrspi_persist_test.py`): `import unittest`, `TestCase` subclasses, `setUp`/`tearDown` using `tempfile.TemporaryDirectory()`, `self.assert*` methods, `unittest.main()` entrypoint. It imports the module under test directly (`import qrspi_persist as qp`) and exercises **pure** functions (`staging_path`, `dest_path`, `persist`) against temp dirs — it never touches the real repo root; the repo-root path is supplied as a function argument (e.g. `qp.dest_path("/repo", ...)`), which is why the helpers keep path computation in pure, argument-driven functions.
- **`check()`/assert style** (`scripts/qrspi_resolve_test.py`): a hand-rolled `check(name, got, want)` and `check_raises(name, fn)` harness with module-level `failures`/`total` counters; tests run at import time, top-to-bottom. It imports pure helpers from `qrspi_resolve` and feeds them in-memory dicts for config (`select_source({"reviewers": [...]}, ...)`) and `tempfile` dirs for filesystem reads — it explicitly does NOT test subprocess-backed parts (gh/git/gt/build_state), deferring those to manual e2e (docstring lines 6–8).

In both, "stubbing the repo-root read" is achieved by **dependency-injecting the path/config as a function argument** rather than mocking — the pure functions accept `repo_root`/`config`/`path` so tests pass temp dirs or literal dicts.

**Evidence:**

```
import qrspi_persist as qp
class DestPathTest(unittest.TestCase):
    def test_canonical_worktree_layout(self):
        d = qp.dest_path("/repo", "RUS-21", "plan")
        self.assertEqual(d, "/repo/.worktrees/RUS-21/.qrspi/RUS-21/plan.md")
```

— `scripts/qrspi_persist_test.py:8,23-26`

```
def check(name, got, want):
    global failures, total
    total += 1
    if got != want:
        print("FAIL: %s ..."); failures += 1
    else:
        print("ok: %s" % name)
```

— `scripts/qrspi_resolve_test.py:33-40`

```
check("config used (list)", select_source({"reviewers": ["alice"]}, "reviewers", ["@me"]), ["alice"])
check("default when key absent from config", select_source({}, "reviewers", ["@me"]), ["@me"])
```

— `scripts/qrspi_resolve_test.py:157-165` (config fed as in-memory dict; no file/mocking)

**Dependencies:** Tests import the helper modules by name (run from `scripts/`); stdlib only (`unittest`, `tempfile`, `os`, `sys`).
**Implicit contracts:** Helpers must keep path/config resolution in **pure, argument-driven** functions (taking `repo_root`/`config`/`path`) so tests can exercise them without touching the real `<REPO_ROOT>/.qrspi/config.json`. Subprocess/network parts are left to manual e2e by convention.

## Q13: How are the workflow's project-scoping behaviors verified today, and is there any automated coverage of the `qrspi-batch.js` Query phase versus manual end-to-end runs only?

**Answer:** There is **no automated coverage of `qrspi-batch.js`** at all — it is a JavaScript workflow and the entire test suite is Python (`scripts/*_test.py`). A grep across `scripts/*_test.py` for `qrspi-batch`, `list_issues`, and `PROJECT` returns nothing. The project-scoping logic (lines 67, 922) is pure JS string interpolation with no Python helper behind it, so no `_test.py` can reach it. A grep for the string `project` across all of `scripts/` and the evals JSON files returns no project-scoping references. Per CLAUDE.md and project memory, the `evals/` + `scripts/run_eval.py` harness is a **non-functional placeholder**; pure logic is verified with the `_test.py` unit tests and orchestration changes are verified by **manual end-to-end runs**. So today: project-scoping is verified by manual e2e only — there is zero automated coverage of the Query phase.

**Evidence:**

- Grep `qrspi-batch|list_issues|PROJECT` over `scripts/*_test.py` → `(none)`.
- Grep `project` over `scripts/` and `evals/*.json` → no project-scoping match.
- `scripts/qrspi_resolve_test.py:6-8`: "The subprocess-backed parts ... are intentionally NOT tested here ... and are verified by a manual end-to-end run against a real ticket."
- CLAUDE.md (`.claude/CLAUDE.md`): "The `evals/` + `scripts/run_eval.py` harness is a **non-functional placeholder** — verify pure logic with the unit tests and orchestration changes with manual end-to-end runs."

**Dependencies:** N/A — the gap is structural (JS workflow vs Python test suite).
**Implicit contracts:** To gain automated coverage of project-scoping, the testable logic must be extracted into a pure Python helper with a `_test.py` sibling (the Q3/Q12 pattern); JS interpolation alone is untestable in this repo's harness.

## Q14: What does the workflow log or emit at the start of the Query phase about which project scope it resolved, and where would a reader confirm the effective project during a batch run?

**Answer:** The workflow logs **nothing about the project scope**. The Query phase begins with `phase('Query')` (line 914) and immediately fans out the `list_issues` agents. The first `log(...)` is **after** enumeration: `Found N ticket(s): ...` (line 941), which lists ticket ids+statuses but never echoes `PROJECT` or whether the run was project-scoped vs all-projects. The early-return note when zero tickets are found mentions only `STATUSES`, not the project: `note: "No tickets in ${STATUSES.join(' / ')}"` (line 946). The only place the effective project surfaces is **inside each agent's prompt** (line 922) — i.e. in the spawned agent's transcript, not in the workflow's own log stream. There is no validation/echo of the resolved scope before the call.

**Evidence:**

```
phase('Query')
const batches = await parallel(STATUSES.map(status => () => agent(...)))
...
log(`Found ${tickets.length} ticket(s): ${tickets.map(t => `${t.id} (${t.status})`).join(', ') || '(none)'}`)
```

— `.claude/workflows/qrspi-batch.js:914-941`

```
return { ticketsProcessed: 0, note: `No tickets in ${STATUSES.join(' / ')}`, reconciliation }
```

— `.claude/workflows/qrspi-batch.js:946`

**Dependencies:** `phase()` and `log()` are workflow runner built-ins (no inline definition).
**Implicit contracts:** A reader confirming the effective project today must inspect the spawned `list:<status>` agent's prompt/transcript (line 922 interpolation) — the workflow's own log does not report scope. Any new config-derived default would benefit from an explicit log line to make the resolved scope observable (currently absent).

---

## Discovered Patterns

- **Self-locating, stdlib-only Python helpers** (`scripts/qrspi_*.py`): repo root from `__file__` (two levels up), short token-free CLI flags, single JSON envelope on stdout with `ok` + verbatim `error`, exit 0/non-zero, failures reported ONCE and never retried. Rationale throughout: a weak local worker model corrupts the literal `qrspi` token in hand-typed paths, so all qrspi-laden paths are computed inside scripts (`scripts/qrspi_persist.py:37-41`, `scripts/qrspi_resolve.py:37-42`).
- **Pure-function + dependency injection for testability**: path/config resolution lives in pure functions that take `repo_root`/`config`/`path` as arguments (`dest_path`, `select_source`, `detect_existing`), so `_test.py` siblings exercise them with temp dirs or in-memory dicts and never touch the real config file. Subprocess/network parts are deliberately left to manual e2e.
- **Config is read in two completely separate places with two mechanisms**: `/qrspi-ticket` reads `linearProject`/`linearTeam` via agent **prose** (`.claude/skills/qrspi-ticket/SKILL.md:106-117`); `qrspi_resolve.py` reads `reviewers`/`teamReviewers` via **programmatic** `_read_reviewer_config()` (`scripts/qrspi_resolve.py:254-275`). `qrspi-batch.js` reads the config file for **nothing** today.
- **"All projects" is encoded as falsiness, not a sentinel** — the `undefined ⇒ all projects` overload (lines 67, 922) is the only mechanism; there is no explicit `"all"`/`"*"` value.
- **JS workflow has zero automated test coverage** — the entire suite is Python `_test.py`; orchestration is verified by manual e2e (CLAUDE.md, project memory).
- **Worker-agent stdout capture has two shapes**: StructuredOutput schema (`persistArtifact`) vs plain-text-return-then-JS-parse (`resolveTicket`/`parseResolveEnvelope`), the latter chosen because the weak worker stalled on StructuredOutput (lines 334-336).

## Inconsistencies

- **Default project value is inconsistent across the two consumers.** `/qrspi-ticket` defaults `linearProject` to the literal `"QRSPI"` when unset (`SKILL.md:112`), but `qrspi-batch.js` defaults `PROJECT` to `undefined` = **all projects** (line 67). So a fresh clone with no config files in: ticket creation under "QRSPI", but batch sweeps EVERY project. The two phases do not agree on what "the project" is, and the batch never reads `linearProject` at all. (This is the documented config field `linearProject` being honored by one consumer and ignored by the other.)
- **`.qrspi/config.example.json` documents `linearProject` defaulting to `"QRSPI"`, but only `/qrspi-ticket` enforces that default.** The `$comment` (`config.example.json:2`) presents `linearProject` as a general "the Linear project" setting, implying repo-wide scope, yet `qrspi-batch.js` does not consult it — a reader could reasonably expect setting `linearProject` to scope the batch sweep, and it does not today.
- **Empty string vs undefined are conflated for `PROJECT`.** `input.project: ""` behaves identically to "all projects" (falsy → branch at line 922), with no validation or warning — a user who set the field to an empty/whitespace string gets a silent all-projects sweep rather than an error.
- **No observability of resolved scope.** The Query phase logs ticket counts/ids (line 941) but never the project scope it resolved; the effective project is only visible inside a spawned agent's prompt. Code comment `undefined ⇒ all projects` (line 67) is accurate, but the runtime emits nothing confirming which branch was taken.
