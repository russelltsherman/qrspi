# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-14T00:00:00Z
**Generated:** 2026-06-14T00:00:00Z
**Status:** draft

> Scope note: all paths below are under the RUS-74 worktree root
> `/workspaces/qrspi/.worktrees/RUS-74`. Line numbers are from that checkout.

## Q1: In the Resolve phase, where does the base ref that a new worktree is cut from get determined, and does any step fetch or move local `main` before that cut?

**Answer:** The base ref is the LOCAL trunk branch, defaulting to `"main"`, threaded as the
`--trunk` arg (default `"main"`) into `qrspi_resolve.py`'s `setup_worktree(ticket, trunk="main", ...)`.
A brand-new ticket's design branch is cut with `git worktree add -b <ticket>/design <worktree> trunk`
and tracked with `gt track --parent trunk`. **No step fetches or advances local `main` first.** There is
no `git fetch`, no `gt sync`, and no `origin/main` reference anywhere in the resolve path — the cut uses
whatever commit local `main` currently points at. (Confirmed by a repo-wide grep: `git fetch` appears in
NO script, in NO workflow, and only in prose in `docs/`.)

**Evidence:**

```python
def setup_worktree(ticket, trunk="main", create_design=False, repo_root=REPO_ROOT):
    ...
    # run_design on a brand-new ticket: create the design branch off trunk and track it.
    os.makedirs(worktrees_dir, exist_ok=True)
    rc, _, err = _run(["git", "worktree", "add", "-b", "%s/design" % ticket, worktree, trunk],
                      cwd=repo_root)
    ...
    rc, _, err = _run(["gt", "track", "--parent", trunk, "--no-interactive"], cwd=worktree)
```

— `scripts/qrspi_resolve.py:302-343` (cut at `:336`; `--trunk` default `"main"` at `:359`)

The orchestration call site that runs resolve (lines 1364-1430 `resolveTicket`) supplies no trunk
override; the worker runs `python3 scripts/qrspi_resolve.py --ticket <id> ...` and the default `main` holds.

**Dependencies:** `qrspi_resolve.py` imports `qrspi_pr_state.build_state` (read-only PR/git gather),
`qrspi_resolve_state.resolve` (decision), and `qrspi_paths.resolve_repo_root` (host-root). The worktree cut
is impure git/gt mechanics in `setup_worktree`. Upstream caller: `resolveTicket()` in `qrspi-batch.js`.
**Implicit contracts:** The cut assumes local `main` is the intended trunk tip. Nothing in the resolve path
guarantees local `main` == `origin/main`; a stale or divergent local `main` silently becomes the base of a
new stack. `trunk` is a parameter but is never passed as anything but `main`.

## Q2: How does the Restack phase select its restack base, and at what point does it read local `main` relative to the start-of-run sequence?

**Answer:** Restack selects the **LOCAL trunk only**. `qrspi_restack.py` runs
`gt restack --downstack` from the stack tip (rebasing `tip -> ... -> design` onto the current local trunk
tip) and, for a partial-land re-parent, `gt move --onto main --source <branch>`. The module docstring is
explicit: "It restacks onto the LOCAL trunk only — it NEVER `gt sync`s ... and never rewrites trunk."
There is no fetch/sync before the restack, so it reads local `main` as it stands at the moment the ticket
is processed in the per-ticket loop — there is no separate start-of-run trunk read. `gt restack` is
idempotent (no-op when already aligned).

**Evidence:**

```python
rc, out, err = _run(["gt", "restack", "--downstack", "--no-interactive"], cwd=worktree)
...
def reparent_lowest_open(branch, worktree):
    return _run(["gt", "move", "--onto", "main", "--source", branch, "--no-interactive"],
                cwd=worktree)
```

— `scripts/qrspi_restack.py:381` (restack) and `:293-309` (re-parent onto `main`)

Orchestration: `ensureRestacked(t, phaseLabel)` (`qrspi-batch.js:1450-1473`) spawns a worker that runs
`python3 scripts/qrspi_restack.py --ticket <id>`; called per-ticket inside the main loop at `:2466-2467`.

**Dependencies:** imports `qrspi_pr_state` (merge-state classifiers), `qrspi_resolve.pick_tip`/`_gh_name_with_owner`,
`qrspi_paths`. Hard-codes `--onto main` in `reparent_lowest_open`. **Implicit contracts:** restack base ==
local `main`; if local `main` is stale/divergent, the stack is realigned onto the WRONG trunk and the
`gt submit --force` push (`:312-322`) propagates that to the remote PRs. The "drift gate" comment (`:1432-1448`)
frames restack as surfacing trunk-divergence early — but only divergence between the held stack and *local*
trunk, never local vs `origin`.

## Q3: What is the ordering of phases at run start (Query → Resolve → Restack → … → land), and what is the earliest orchestration point that executes in the main checkout before any worktree is cut?

**Answer:** The top-level script body runs **Query once**, then iterates tickets **sequentially**, and per
ticket runs Resolve → Restack → dispatch(action). The declared phase list is Query, Resolve, Restack,
Design, Plan, Implementation, Finalize, Reconcile (`meta.phases`, `:5-14`). At run start the script body
executes (in the main checkout): `phase('Query')` (`:2301`), project-scope resolution via a config worker +
a Linear validation worker (`:2311-2372`), the parallel `list_issues` sweep (`:2374-2386`), dedup
(`:2388-2397`), an optional order worker (`:2408-2429`), then the per-ticket `for` loop (`:2443`). Inside the
loop: `resolveTicket(t)` (`:2452`) → `phase('Restack'); ensureRestacked(t, ...)` (`:2466-2467`) →
`switch(action)` dispatch (`:2477-2493`). **The earliest orchestration point that runs in the main checkout
is the Query phase** (project-scope config read + Linear sweep). The first git mutation in the main checkout
is the worktree cut inside `resolveTicket` → `qrspi_resolve.py setup_worktree`. There is no run-start step
that touches trunk before the first worktree is cut.

**Evidence:**

```javascript
for (let i = 0; i < tickets.length; i++) {
  const t = tickets[i]
  ...
  const r = await resolveTicket(t)          // cuts/reuses the worktree
  ...
  phase('Restack')
  const rs = await ensureRestacked(t, 'Restack')
  ...
  switch (a) {
    case 'run_design': res = await doDesign(t, r); break
    ...
    case 'land': res = await doLand(t, r); break
```

— `.claude/workflows/qrspi-batch.js:2443-2493`

**Dependencies:** Query depends on `mcp__linear__list_issues`, `qrspi_config.py`, `qrspi_order_tickets.py`.
The loop is strictly sequential ("tickets share one .git index, so worktree/Graphite ops must not race",
`:2439`). **Implicit contracts:** Each ticket's worktree cut happens lazily at its turn in the loop, NOT at
run start — so a trunk sync inserted at run start (before the loop) would precede every worktree cut. The
main-checkout context is the runner's cwd / `process.cwd()` (the `ENGINE_ROOT` derivation, `:68-71`).

## Q4: What is the established JSON-envelope convention and self-locating repo-root pattern used by sibling helpers, so a new `scripts/qrspi_sync_trunk.py` matches it?

**Answer:** The established pattern (shared by `qrspi_persist.py`, `qrspi_resolve.py`, `qrspi_restack.py`,
`qrspi_cleanup.py`, `qrspi_land_verify.py`):
1. **Self-location:** `ENGINE_ROOT = os.path.dirname(os.path.abspath(__file__))`, then
   `sys.path.insert(0, ENGINE_ROOT)` for sibling imports; the HOST checkout root is resolved via
   `REPO_ROOT = qrspi_paths.resolve_repo_root(cwd=os.getcwd(), validate=False)` at module level (and
   re-resolved with `validate=True` inside `main()` honoring a `--repo-root` override).
2. **Envelope:** a single JSON object on stdout via `json.dump(env, sys.stdout, indent=2); print()`, always
   carrying `{"ok": bool, "repoRoot": ..., ...payload..., "error"?: str}`. `error` key present only on failure.
3. **Exit code:** `return 0 if env["ok"] else 1`.
4. **Pure/impure split:** pure helpers (path builders, classifiers) are unit-tested; subprocess mechanics
   (`_run(cmd, cwd=None) -> (rc, stdout, stderr)`) are not.
5. **Fail-once:** any infra error caught and reported ONCE as `ok:false` with a verbatim message, never retried.

**Evidence:**

```python
ENGINE_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ENGINE_ROOT)
import qrspi_paths  # noqa: E402
REPO_ROOT = qrspi_paths.resolve_repo_root(cwd=os.getcwd(), validate=False)
...
env = { "ok": error is None, "repoRoot": repo_root, "src": src, "dest": dest, "bytes": bytes_written }
if error is not None: env["error"] = error
json.dump(env, sys.stdout, indent=2); print()
return 0 if error is None else 1
```

— `scripts/qrspi_persist.py:45-50, 121-133` (and identically `qrspi_resolve.py:49-56, 413-415`,
`qrspi_restack.py:56-72, 426-428`)

The `_run` helper is verbatim-identical across helpers:
`def _run(cmd, cwd=None): res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True); return res.returncode, res.stdout, res.stderr`
— `scripts/qrspi_resolve.py:250-253`, `qrspi_restack.py:243-246`, `qrspi_cleanup.py:98-101`.

**Dependencies:** `qrspi_paths.resolve_repo_root` is the single source of truth for host-root resolution
(`scripts/qrspi_paths.py:118-159`); precedence `--repo-root` (validated) → git-common-dir (validated) →
`__file__` parent. **Implicit contracts:** the `repoRoot` field is the resolved HOST checkout root (the MAIN
checkout even when invoked from a worktree, via `git rev-parse --git-common-dir`). A new sync helper should
default `repo_root` from `resolve_repo_root` and key all git ops to `cwd=repo_root`.

## Q5: How does the workflow shell out to these Python helpers and parse their JSON output, including how a non-`ok` envelope is surfaced as a hard stop?

**Answer:** The JS sandbox cannot run python, so each helper is invoked by spawning a **worker agent**
prompted to run EXACTLY one verbatim command (built with `engineCmd('scripts/qrspi_*.py')` or
`engineCmdFor(r, ...)`), output the stdout JSON verbatim, and NOT call any structured-output tool. The
script's path is prefixed by `ENGINE_ROOT` via `engineCmd(rel) => ${ENGINE_ROOT}/${rel}` (`:76`) — or
`engineCmdFor(r, rel)` which derives the host root from `r.worktreeDir` for worker-cwd prompts (`:95-105`).
The worker's text return is parsed by a dedicated `parse*Envelope(text, ...)` function that uses
`extractJsonObject` (a brace-depth, string-aware scanner, `:190-206`) to pull the outermost `{...}`,
`JSON.parse`s it, and validates required fields. A non-`ok` envelope is passed through verbatim
(`if (!env.ok) return env`); the CALLER decides — e.g. restack's `if (!rs.ok)` logs and skips the ticket;
the Query config read THROWS (`:2335`) to hard-fail the whole run.

**Evidence:**

```javascript
const SKILL = engineCmd('.claude/skills/qrspi-work/SKILL.md')
const engineCmd = (rel) => `${ENGINE_ROOT}/${rel}`
...
async function persistArtifact(id, name, phaseLabel) {
  return await agent(
    `... Run EXACTLY this one command verbatim ...
  python3 ${engineCmd('scripts/qrspi_persist.py')} --ticket ${id} --artifact ${name}
... If it reports ok:false, return that as-is — HARD STOP, do NOT retry ...`,
    { label: `persist:${id}:${name}`, phase: phaseLabel, schema: PERSIST_SCHEMA })
}
```

— `.claude/workflows/qrspi-batch.js:700-713` (persist); parse+validate `parseResolveEnvelope` `:212-226`,
`parseRestackEnvelope` `:269-276`, `parseConfigEnvelope` `:316-326`; `extractJsonObject` `:190-206`.

Hard-stop variants: restack failure is non-fatal per-ticket — `if (!rs.ok) log(... skipping ...)`
(`:1466-1468`) then the loop records `restack_conflict` and `continue`s (`:2468-2472`); a config-scope
non-ok THROWS `new Error(...)` aborting the run (`:2331-2336`).

**Dependencies:** every helper invocation rides the `agent()` runner + a `parse*Envelope` validator. The
land/cleanup workers additionally use `WORKER_SCHEMA` StructuredOutput (`:467-477`). **Implicit contracts:**
worker output must contain a parseable top-level JSON object; `ok` must be a boolean; a garbled echo
deterministically becomes `{ ok:false, error:'... no JSON envelope ...' }` so a corrupt decision never acts.

## Q6: What fields does the land worker's output schema currently expose, and where does `finResult` read from it (`fin.error` vs `fin.summary`)?

**Answer:** The land worker uses `WORKER_SCHEMA` = `{ ok, error?, prUrl?, newStatus?, summary }` (required:
`ok`, `summary`). `doLand` prompts it to return `ok, prUrl, newStatus, summary` (`:2160`). `finResult(t, fin, action)`
reads: on failure (`!fin || !fin.ok`) it builds the summary from **`fin?.error`** (`... finalize failed: ${fin?.error ?? 'unknown'}`)
and does NOT read `fin.summary`; on success it returns `newStatus: fin.newStatus, summary: fin.summary, prUrl: fin.prUrl`.
So `fin.error` feeds the failure path's surfaced reason, and `fin.summary` only the success path.

**Evidence:**

```javascript
function finResult(t, fin, action) {
  if (!fin || !fin.ok) {
    log(`  ${t.id}: ${action} finalize failed — ${fin?.error ?? 'no result'} (nothing advanced)`)
    return { ticketId: t.id, action, summary: `${action} finalize failed: ${fin?.error ?? 'unknown'}` }
  }
  return { ticketId: t.id, action, newStatus: fin.newStatus, summary: fin.summary, prUrl: fin.prUrl }
}
```

— `.claude/workflows/qrspi-batch.js:2210-2216`; `WORKER_SCHEMA` `:467-477`; land call site `:2154-2163`.

**Dependencies:** `doLand` → `finResult` → main-loop `results.push(res)` → final run-result object.
After `finResult`, `doLand` augments `res` with `landed`, `openBranches`, `cleanup`, `reconcileRetry` fields
(`:2168-2203`) and on an incomplete land OVERWRITES `res.summary` with a verbatim
`land incomplete: slice(s) [...] still OPEN ...` (`:2181`). **Implicit contracts:** the failure summary is
`<action> finalize failed: <fin.error>` — the canonical place a verbatim land/merge error reason is assembled
for surfacing. A land worker that returns `ok:false` must put its verbatim reason in `error`, not `summary`,
for `finResult` to surface it.

## Q7: Which checkout (main repo vs `.worktrees/<id>/`) does each orchestration site run in, and how is "the main checkout" identified for a sync that must not run inside a worktree?

**Answer:** Two cwd contexts:
- **Main repo root** workers: persist, node-check, config, order, restack, land-verify, cleanup, reconcile-enumerate —
  their prompts state "Your cwd is the main repo root" / "the MAIN repo root". They run self-locating scripts that
  re-derive the host root from `__file__`/git-common-dir, so cwd is advisory.
- **Worktree** workers: design/plan/implementation/submit/reset/revise/land/peer-reviewer — prompts say
  "in ${r.worktreeDir}" (= `<root>/.worktrees/<id>`).

The MAIN checkout is identified in JS two ways: (1) `ENGINE_ROOT` = `process.env.CLAUDE_PLUGIN_ROOT || process.cwd() || '.'`
(`:68-71`) — the runner's cwd is the main checkout; (2) `hostRootFromWorktree(r)` strips the
`/.worktrees/<id>` suffix off `r.worktreeDir` to deterministically recover the main root (`:95-100`). In Python,
`qrspi_paths.resolve_repo_root` uses `git rev-parse --git-common-dir` whose parent is the MAIN checkout even
when cwd is a linked worktree (`scripts/qrspi_paths.py:60-83`).

**Evidence:**

```javascript
const hostRootFromWorktree = (r) => {
  const wd = r && r.worktreeDir
  if (typeof wd !== 'string') return null
  const m = wd.match(/^(.*)\/\.worktrees\/[^/]+$/)
  return m ? m[1] : null
}
```

— `.claude/workflows/qrspi-batch.js:95-100`; cleanup worker's explicit main-checkout requirement
`:2115-2123` ("Your cwd is the MAIN repo root (NOT a worktree — the script self-locates REPO_ROOT ... and must
see the real .worktrees/${ticketId})").

**Dependencies:** `qrspi_paths.resolve_repo_root` / `_git_common_dir`. **Implicit contracts:** a sync that must
run on the main checkout (not a worktree) should either run from the runner cwd (main-checkout workers) or
key `cwd` to `resolve_repo_root(...)` so git-common-dir yields the main root from anywhere. The cleanup worker
is the precedent for a script that MUST operate on the main checkout and self-locates to enforce it.

## Q8: How is the post-land call site distinguished from the land worker's own worktree context, so AC3's hygiene sync runs in the orchestrator/main-checkout context only?

**Answer:** `doLand` (`:2154-2204`) is structured as: (1) the LAND worker runs "in ${r.worktreeDir}" doing
the merge; (2) `finResult`; (3) a Done-gate `runLandVerify(t.id, ...)` worker that runs on the MAIN repo root;
(4) on `landed`, `runCleanup(t.id, false, 'Finalize')` — also a MAIN-repo-root, self-locating worker. The
post-land steps (3,4) are orchestrator-driven calls in `doLand` AFTER the worktree-context land worker returns,
and they explicitly run on the main checkout (their prompts say "Your cwd is the MAIN repo root"). So the
orchestrator/main-checkout context for a post-land hygiene sync is exactly this region of `doLand`, after
`fin.ok` and the `verdict.status === 'landed'` gate — the same place `runCleanup` is invoked.

**Evidence:**

```javascript
  res.landed = true
  const cl = await runCleanup(t.id, /* dryRun */ false, 'Finalize')
  ...
async function runCleanup(ticketId, dryRun, phaseLabel) {
  ... `You are the CLEANUP worker for QRSPI ticket ${ticketId}. Your cwd is the MAIN repo root (NOT a worktree ...)`
```

— `.claude/workflows/qrspi-batch.js:2184-2185` (post-land cleanup call) and `:2115-2123` (cleanup worker
main-checkout context); the land worker's worktree context at `:2159` ("in ${r.worktreeDir}").

**Dependencies:** `runLandVerify` (`:2138-2149`, main-repo-root, self-locating), `runCleanup` (`:2115-2136`).
**Implicit contracts:** post-land orchestration steps are gated on `verdict.status === 'landed'` (`:2174-2184`)
— a hygiene trunk-sync placed alongside `runCleanup` would only run on a fully-landed stack, on the main
checkout, after the merge. The land worker is forbidden from running `gt sync --force` itself (`:2159`); reaping
and any trunk hygiene is deterministic-script territory invoked from the orchestrator.

## Q9: How is a divergent local `main` (not an ancestor of `origin/main`) currently detected anywhere in the harness, and what FF-ancestor check primitives are available to fail loud on it?

**Answer:** **NOT FOUND — no such detection exists.** A repo-wide search for `merge-base`, `--is-ancestor`,
`is_ancestor`, `origin/main`, `git fetch`, `fast-forward`, and `ff-only` across `scripts/*.py`,
`.claude/workflows/`, and `docs/` found ZERO occurrences in executable code. The harness never compares local
`main` to `origin/main` and never runs a fast-forward/ancestor check. The only available git-primitive idioms
in the codebase that a new check could be built from are:
- `git rev-parse --path-format=absolute --git-common-dir` (root resolution) — `scripts/qrspi_paths.py:70-71`
- `git rev-parse --verify --quiet refs/heads/<branch>` (branch existence) — `scripts/qrspi_cleanup.py:186`
- `git rev-parse HEAD` — `scripts/qrspi_revise_amend.py:178`
- `git ls-remote --heads origin` (read-only remote ref snapshot) — `scripts/qrspi_cleanup.py:137`
- `git branch --list <ticket>/*` — `scripts/qrspi_resolve.py:298`, `qrspi_restack.py:251`, `qrspi_cleanup.py:123`

No `git merge-base --is-ancestor` primitive is used anywhere; it would be a new addition.

**Search queries attempted:** `grep -rn "git fetch|merge-base|--is-ancestor|is_ancestor|rev-parse|origin/main|symbolic-ref|fast-forward|ff-only"` over `scripts/`, `.claude/workflows/`, `docs/` — only `rev-parse`/`ls-remote` (root/ref discovery) matched; no ancestor/divergence check.

**Evidence:**

```python
def _remote_refs(ticket):
    ... rc, out, _ = _run(["git", "ls-remote", "--heads", "origin"], cwd=REPO_ROOT)
```

— `scripts/qrspi_cleanup.py:127-148` (the only read of origin refs; it lists refs, never compares trunk tips)

**Dependencies:** none — the capability is absent. **Implicit contracts:** the harness implicitly TRUSTS that
local `main` is a valid ancestor of/equal to `origin/main`. The known failure (project MEMORY.md
"Batch land 'unknown' failures" — stale/drifted local main) is currently handled only by a manual FF recipe,
not by code. A `git merge-base --is-ancestor origin/main main` (or the reverse) check would be the natural
fail-loud primitive and is not yet present.

## Q10: How does the existing code detect a dirty working tree before mutating refs, so the sync can guard on a clean main working tree?

**Answer:** Two precedents, both using `git status --porcelain`:
1. **Cleanup** (`qrspi_cleanup.py`): impure `_dirty_porcelain(wt_path)` returns
   `git status --porcelain` output (or `""` when the worktree dir is absent — "a missing worktree cannot be
   dirty"); the **pure** `classify_cleanup(stack_merge_state, dirty_porcelain)` returns
   `{"decision":"blocked", ...}` when `(dirty_porcelain or "").strip()` is non-empty — dirty-tree precedence
   over merge state, so dirty work is never destroyed. This pure/impure split is the canonical, unit-tested
   dirty-tree guard.
2. **Revise-amend** (`qrspi_revise_amend.py:239`): `git status --porcelain --untracked-files=all` + a pure
   `dirty_paths(porcelain_text)` parser.

There is no existing dirty-CHECK on the MAIN checkout specifically (cleanup checks the worktree), but the
`_dirty_porcelain` + `classify_*` idiom is directly reusable against the main root by passing
`cwd=repo_root`.

**Evidence:**

```python
def classify_cleanup(stack_merge_state, dirty_porcelain):
    if (dirty_porcelain or "").strip():
        return {"decision": "blocked",
                "reason": "worktree has uncommitted changes; refusing to destroy"}
    ...
def _dirty_porcelain(wt_path):
    if not os.path.isdir(wt_path):
        return ""
    rc, out, _ = _run(["git", "status", "--porcelain"], cwd=wt_path)
    return out if rc == 0 else ""
```

— `scripts/qrspi_cleanup.py:63-93` (pure classifier) and `:151-157` (impure read)

**Dependencies:** pure classifier is unit-tested in `qrspi_cleanup_test.py` (layer 1). **Implicit contracts:**
empty/whitespace porcelain == clean; non-empty == dirty/blocked. A trunk-sync guard would mirror this:
read `git status --porcelain` on `repo_root` and refuse to move `main` (fail loud) when non-empty, never
forcing past dirty work — exactly the cleanup precedence rule.

## Q11: What happens at run start if `git fetch origin` fails or local `main` is already current, and how do other run-start helpers signal a no-op versus an abort?

**Answer:** **NOT FOUND for `git fetch` specifically** — no run-start fetch exists, so there is no current
behavior for a failed/already-current fetch. The relevant PATTERN for "no-op vs abort" at run start comes from
the existing run-start helpers:
- **No-op success:** restack's `classify_result` returns `(ok=True, restacked=False, ...)` when nothing moved
  (`scripts/qrspi_restack.py:197-204`), and `main()` emits a clean `ok:True, restacked:False` envelope when the
  ticket has no worktree/branch (`:409-421`). `gt restack` is documented as idempotent (already-aligned = no-op).
- **Abort/hard-stop:** a non-ok envelope. The Query-phase config-scope read is the strictest run-start example:
  a non-ok config envelope THROWS `new Error('qrspi-batch: could not resolve project scope ...')`, aborting the
  whole run (`:2331-2336`); likewise a non-matching project scope THROWS (`:2365-2371`). Per-ticket helpers
  instead return `ok:false` and the loop logs + `continue`s (restack `:2468-2472`).
- **Fail-once on infra error:** every helper wraps its mechanics in a `try/except` that emits ONE `ok:false`
  envelope with the verbatim error and never retries (`qrspi_resolve.py:402-411`).

So a new run-start sync would signal "already current" as `ok:true` with a `changed:false`-style flag (mirroring
`restacked:false`) and a fetch/divergence failure as `ok:false` with a verbatim error — and the orchestrator
would decide whether that's a per-run hard stop (throw, like the config scope) or a logged skip.

**Search queries attempted:** `grep -rn "git fetch|fetch origin|gt sync"` — only prose/docs and the cleanup
`gt sync --force` reap; no run-start fetch.

**Evidence:**

```javascript
const cfg = parseConfigEnvelope(cfgOut, 'linearProject')
if (!cfg.ok) {
  throw new Error(`qrspi-batch: could not resolve project scope from config — ${cfg.error ?? 'unknown error'}`)
}
```

— `.claude/workflows/qrspi-batch.js:2330-2336` (run-start hard-abort idiom)

**Dependencies:** `parseConfigEnvelope` (`:316-326`), `classify_result` (`:188-206`). **Implicit contracts:**
run-start scope failures abort the whole run via `throw`; per-ticket failures degrade to a skipped ticket. A
no-op is a positive `ok:true` envelope with a boolean "nothing changed" field, never an error.

## Q12: What stdlib-only test pattern do the existing `scripts/qrspi_*_test.py` siblings use to exercise git interactions (e.g., temp repos, fakes, or subprocess stubs) for the clean-FF / already-current / divergence / dirty-tree cases?

**Answer:** Three complementary stdlib-only patterns (no pytest; `unittest` or assert-based `check()` runners):
1. **Pure classifier over crafted inputs (no subprocess)** — the dominant pattern. `classify_cleanup`,
   `resolve`, `classify_result` are called directly with hand-built dicts/strings (e.g. a porcelain string for
   the dirty case) and asserted. Used in `qrspi_cleanup_test.py` layer 1, `qrspi_resolve_state_test.py`.
2. **subprocess.run swap (fake handler)** — `qrspi_paths_test.py` replaces `qrspi_paths.subprocess.run` with a
   `_install_fake_run(handler)` that returns `_FakeCompleted(returncode, stdout, stderr)` per command, and
   `restore()`s after. Commands are matched by predicates (`_is_git_common_dir`, `_is_gh_repo_view`). This is
   the precedent for stubbing git/gh subprocess deterministically — directly applicable to a sync helper's
   fetch / merge-base ancestor / status cases (return rc/stdout to model clean-FF, already-current, divergence).
3. **Real temp-git fixtures** — `qrspi_cleanup_test.py` layer 2 builds a real temp git repo + a local BARE repo
   as "origin" to assert against real `git ls-remote` state, skip-guarded when `git` is unavailable; an
   explicitly-flagged departure from the stdlib-pure convention reserved for impure mechanics.

For a sync helper the natural fit is: pure classifier (clean-FF / already-current / divergence / dirty as
input combinations) + the `subprocess.run` swap to drive the impure fetch/ancestor/porcelain reads.

**Evidence:**

```python
class _FakeCompleted:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode; self.stdout = stdout; self.stderr = stderr

def _install_fake_run(handler):
    real = qrspi_paths.subprocess.run
    def fake_run(cmd, **kwargs):
        result = handler(cmd, **kwargs)
        if result is None: raise OSError("fake: command not found: %r" % (cmd[0],))
        return result
    qrspi_paths.subprocess.run = fake_run
    def restore(): qrspi_paths.subprocess.run = real
    return restore
```

— `scripts/qrspi_paths_test.py:61-89`; pure-classifier dirty case asserted via `classify_cleanup(..., "M file")`
in `qrspi_cleanup_test.py` (layer 1, `:4-12`); real-git fixture layer 2 (`:6-12`, `:230-280`).

**Dependencies:** tests `import` the module and call pure functions or swap its `subprocess.run`/`_run`.
**Implicit contracts:** tests run with `python3 scripts/qrspi_*_test.py`, exit 0/1, no third-party deps. Impure
mechanics (`_run`-backed) are conventionally untested OR covered by a skip-guarded real-git fixture; pure logic
is always unit-tested. A sync helper should put its FF/divergence/dirty DECISION in a pure classifier and test
that directly, leaving the fetch/`merge-base` subprocess wiring to the fake-run swap.

## Q13: How are hard-stop failures currently propagated into the batch run result, and where would a verbatim land-conflict reason ("land finalize failed: ...") be assembled and surfaced?

**Answer:** Hard-stop failures propagate through `finResult` and the main loop into the array the workflow
returns. `finResult` assembles the verbatim failure summary `${action} finalize failed: ${fin?.error ?? 'unknown'}`
(`:2213`) — this is exactly where a verbatim land-conflict reason ("land finalize failed: ...") is built, when
the land worker returns `ok:false` with the conflict in `fin.error`. The main loop pushes that result object
(`results.push(res)`, `:2494`) and logs it (`:2501`). The script's final return value is the run-result object
containing `results`. Distinct hard-stop categories the loop records: `resolve_failed` (`:2455`),
`restack_conflict` (`:2470`), `errored` (thrown phase agent, `:2505`), and per-action `finalize failed`
summaries via `finResult`. For an INCOMPLETE land specifically, `doLand` overwrites `res.summary` with
`land incomplete: slice(s) [...] still OPEN — deferred to next pass` (`:2181`).

**Evidence:**

```javascript
  if (!fin || !fin.ok) {
    log(`  ${t.id}: ${action} finalize failed — ${fin?.error ?? 'no result'} (nothing advanced)`)
    return { ticketId: t.id, action, summary: `${action} finalize failed: ${fin?.error ?? 'unknown'}` }
  }
```

— `.claude/workflows/qrspi-batch.js:2211-2213`; loop record/log `:2494, 2501`; land-incomplete override
`:2174-2182`.

**Dependencies:** `finResult` ← `doLand`/`doSubmit`/`doPlan`/etc.; loop `results` array ← final workflow return
(the `for` loop ends at `:2507`, followed by the reconciliation pass `:2511` and the run-result assembly). The
land worker's verbatim error MUST be carried on `fin.error` (not `summary`) for `finResult` to surface it (see Q6).
**Implicit contracts:** a hard-stop surfaces as a `{ ticketId, action, summary }` result whose `summary` carries
the verbatim reason; the ticket is left untouched ("nothing advanced") and the idempotent resolver reconciles on
re-run. A new land-conflict reason fits this contract by being returned in the land worker's `error` field.

---

## Discovered Patterns

- **Self-locating deterministic helper + worker-echo invocation.** Every path-sensitive operation is a
  stdlib-only Python script that self-locates its root (`__file__` → `qrspi_paths.resolve_repo_root`), emits one
  `{ ok, repoRoot, ..., error? }` JSON envelope, exits 0/1, and is invoked by a worker agent told to run ONE
  verbatim command and echo stdout. The JS side parses with a brace-scanning `extractJsonObject` +
  `parse*Envelope` validator. A new `scripts/qrspi_sync_trunk.py` should clone this shape verbatim.
- **Pure-core / impure-shell split with `_run(cmd, cwd=None) -> (rc, stdout, stderr)`.** Decisions live in pure,
  unit-tested classifiers (`classify_cleanup`, `classify_result`, `resolve`); subprocess git/gt/gh mechanics are
  thin `_run`-backed wrappers, conventionally untested or covered by a skip-guarded real-git fixture.
- **Fail-once, never-retry on infra error.** A single `try/except` per `main()` emits one `ok:false` verbatim-error
  envelope; weak workers are told "HARD STOP, do NOT retry, do NOT improvise."
- **Trunk is always LOCAL `main`, never synced mid-feature.** Resolve cuts off local `main`; restack realigns onto
  local `main`; the held stack is deliberately never `gt sync`'d (would delete branches). The whole harness assumes
  local `main` is a faithful trunk tip — there is no fetch and no local-vs-origin comparison anywhere.
- **Two cwd contexts, both robust to cwd via self-location.** Main-checkout workers ("Your cwd is the main repo
  root") vs worktree workers ("in ${r.worktreeDir}"); `git rev-parse --git-common-dir` makes scripts find the MAIN
  checkout from anywhere, so cwd in prompts is advisory, not load-bearing.
- **Run-start aborts via `throw`; per-ticket failures via logged `continue`.** Query-phase scope resolution throws
  to kill the whole run; per-ticket resolve/restack/finalize failures degrade to a recorded skip.

## Inconsistencies

- **`gt sync` policy vs docs.** Code and the restack/land prompts forbid `gt sync` on a held stack
  (`qrspi-batch.js:1447, 2159`; `qrspi_restack.py:20`), and project MEMORY notes `gt sync --force` is reap-only.
  But `docs/qrspi-pr-gated-lifecycle-design.md:217` still lists "`gt sync`/restack on each invocation" as the
  drift mitigation, and `docs/qrspi_working_example.md:1195` describes a post-merge `gt sync --force`. The doc
  prose predates the LOCAL-trunk-only restack design; the executable harness never syncs trunk during a feature.
- **"Drift gate" framing vs what it actually checks.** The restack comment (`qrspi-batch.js:1432-1448`) and
  `qrspi_restack.py` docstring sell restack as surfacing "trunk-divergence conflicts ... early." It only surfaces
  divergence between the held stack and *local* trunk — never between local `main` and `origin/main`. A stale
  local `main` passes the drift gate cleanly while still being the wrong base (the exact gap project MEMORY's
  "Batch land 'unknown' failures — stale/drifted local main" documents, currently fixed only by a manual recipe).
- **`finResult` reads `fin.error`, schema requires `summary`.** `WORKER_SCHEMA` requires `summary` and makes
  `error` optional, but `finResult`'s failure path surfaces ONLY `fin.error` (ignoring `summary`). A land worker
  that returns `ok:false` with its reason in `summary` (the required field) but an empty `error` would surface
  `... finalize failed: unknown` — a real foot-gun for assembling a verbatim land-conflict reason.
