# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-12T00:00:00Z
**Generated:** 2026-06-12T00:00:00Z
**Status:** draft

> Scope note: all paths below are under `REPO_ROOT = /workspaces/qrspi/.worktrees/RUS-63`.
> Cited with repo-relative paths for brevity.

## Q1: What inputs does `qrspi-batch.js` read at startup (project scope, config, env vars) and where do those values originate today?

**Answer:** The workflow reads exactly three classes of input at startup:

1. **`args` (the workflow invocation payload)** — parsed at module top. Supported keys: `statuses[]`, `project`, `allProjects`, `reconcile`, `reconcileDryRun`. It accepts either a JSON string or an object.
2. **One environment variable: `CLAUDE_PLUGIN_ROOT`** — read as the *first* precedence for `ENGINE_ROOT` (see Q5/Q9). No other env vars are read.
3. **`.qrspi/config.json` via `scripts/qrspi_config.py --key linearProject`** — read at Query start to resolve project scope (precedence `input.allProjects` > `input.project` > config `linearProject` > built-in `"QRSPI"`). The config read happens inside a worker agent (the JS sandbox cannot run python), invoked through `engineCmd('scripts/qrspi_config.py')`.

Project scope resolution lives at lines 97–110 (arg parsing) and the config fallback at ~1137.

**Evidence:**

```js
const input = typeof args === 'string'
  ? (() => { try { return JSON.parse(args) } catch { return undefined } })()
  : args
const STATUSES = input?.statuses ?? ['Selected', 'Design Review', 'Plan Review', 'Code Review']
const ALL_PROJECTS = input?.allProjects === true
const PROJECT_ARG = (typeof input?.project === 'string' && input.project.trim() !== '')
  ? input.project.trim() : undefined
const RECONCILE = input?.reconcile === true
const RECONCILE_DRY_RUN = input?.reconcileDryRun !== false // default true
```

— `.claude/workflows/qrspi-batch.js:97-118`

```js
const ENGINE_ROOT =
  (typeof process !== 'undefined' && process.env && process.env.CLAUDE_PLUGIN_ROOT) ||
  (typeof process !== 'undefined' && process.cwd && process.cwd()) ||
  '.'
```

— `.claude/workflows/qrspi-batch.js:68-71`

`.qrspi/config.json` is gitignored; the committed template is `.qrspi/config.example.json` (keys: `reviewers`, `teamReviewers`, `linearTeam`, `linearProject` defaulting to `"QRSPI"`).

**Dependencies:** Upstream of `scripts/qrspi_config.py` (reads `.qrspi/config.json`). Downstream: the Query phase (`STATUSES`, `PROJECT`), all script invocations (`ENGINE_ROOT`).
**Implicit contracts:** A concrete resolved project scope that matches no Linear project aborts the Query phase (fail loud); an absent project no longer means "all projects" (`allProjects:true` is the explicit opt-in). `config.json` is optional — a fresh clone needs none.

## Q2: How does the batch workflow currently locate and invoke the `scripts/qrspi_*.py` engine scripts, and what path assumptions does each invocation make?

**Answer:** Every script reference is routed through a single indirection: `const engineCmd = (rel) => \`${ENGINE_ROOT}/${rel}\`` (line 76). The JS sandbox cannot run python, so the workflow never spawns the scripts itself — it **embeds the exact command string in a worker-agent prompt** and instructs the worker to run it verbatim. There are 10 distinct `engineCmd('scripts/...')` call sites:

- `qrspi_persist.py` (line 416, persist worker)
- `qrspi_resolve.py` (line 498, resolve worker)
- `qrspi_restack.py` (line 546, restack worker)
- `qrspi_pr_body.py` (lines 722, 739)
- `qrspi_revise_amend.py` (lines 833, 897)
- `qrspi_comment_reply.py` (line 903)
- `qrspi_cleanup.py` (line 938)
- `qrspi_land_verify.py` (line 960)
- `qrspi_config.py` (line 1137)
- `qrspi_order_tickets.py` (line 1232)

`ENGINE_ROOT` precedence today is `process.env.CLAUDE_PLUGIN_ROOT` → `process.cwd()` → `'.'`. The comment (lines 57–67) labels this the **INTERIM derived-engine-constant indirection**: today the engine *is* the main checkout the batch runs from, so it derives from the runner's cwd and resolves to the same paths the old bare-relative strings did (behavior-preserving). The `CLAUDE_PLUGIN_ROOT` carriage that would let the engine live in an installed plugin dir is explicitly deferred (it is "sub-ticket 3" of the RUS-60 series), pre-wired as first precedence so flipping is a one-line change.

Each worker prompt sets `Your cwd is the main repo root.` and the resolve/restack/persist scripts are themselves **self-locating** (they derive paths from `__file__`), so the only cwd assumption that matters is that the host checkout is reachable from the worker's cwd (Q7/Q11).

**Evidence:**

```js
const engineCmd = (rel) => `${ENGINE_ROOT}/${rel}`
const SKILL = engineCmd('.claude/skills/qrspi-work/SKILL.md')
```

— `.claude/workflows/qrspi-batch.js:76-78`

```js
  python3 ${engineCmd('scripts/qrspi_resolve.py')} --ticket ${t.id} --linear-status "<status>" --ticket-content-file ${ticketFile}
```

— `.claude/workflows/qrspi-batch.js:498` (embedded in the resolve-worker prompt)

`scripts/qrspi_resolve.py` self-locates: `ENGINE_ROOT = os.path.dirname(os.path.abspath(__file__))` then `sys.path.insert(0, ENGINE_ROOT)`, and resolves the host root via `qrspi_paths.resolve_repo_root(cwd=os.getcwd(), validate=False)` (`scripts/qrspi_resolve.py:48-58`).

**Dependencies:** `ENGINE_ROOT` → all script invocations. The scripts depend on `qrspi_paths.py` for host-root resolution.
**Implicit contracts:** Worker agents must run the embedded command **verbatim** (the prompts repeat "no path edits, no exploration, no alternatives"). This rigidity exists because a weak local worker model mangles the literal `qrspi` token (documented at length in `qrspi_resolve.py:6-15`).

## Q3: How is the target repository discovered today versus the decoupled discovery mechanism introduced by RUS-61, and which of the two does the workflow currently consume?

**Answer:** There is no module bearing the name "RUS-61" in the codebase. Searching the repo, `RUS-61` appears only as (a) a fixture ticket id in `scripts/qrspi_order_tickets_test.py:110` and (b) in this ticket's own `questions.md`. **NOT FOUND — no RUS-61-labeled discovery mechanism exists.** The decoupled engine-location-vs-host-checkout discovery that the question describes is, in this codebase, attributed to the **RUS-60** series and lives in `scripts/qrspi_paths.py` (the `resolve_repo_root()` / `engine_root()` split). I treat the question as referring to that mechanism.

Two roots are explicitly separated:
- **Engine root** — `engine_root()` returns `os.path.dirname(os.path.abspath(__file__))` (the dir holding `scripts/`), used only for `sys.path.insert` sibling imports.
- **Host checkout root** — `resolve_repo_root()` decides it with precedence `--repo-root` (validated) → git-common-dir auto-detect (validated) → `__file__` parent (unvalidated last resort).

**Which does the workflow consume today?** The Python scripts (resolve/persist/restack/etc.) consume `qrspi_paths.resolve_repo_root()` for every host path. The **`qrspi-batch.js` workflow itself does not call this Python discovery** — it only locates the *engine* via the JS `ENGINE_ROOT` constant (`process.env.CLAUDE_PLUGIN_ROOT` → `process.cwd()` → `'.'`). Host-repo discovery is delegated entirely to the self-locating scripts, which run with the worker's cwd at "the main repo root" and use git-common-dir to find the host root (correct even from a linked worktree). So the workflow consumes the new mechanism *indirectly* — only the scripts it dispatches do the host discovery.

**Evidence:**

```python
def resolve_repo_root(repo_root=None, cwd=None, validate=True):
    if repo_root:
        root = os.path.abspath(repo_root)
        if validate: _validate_root(root)
        return root
    common = _git_common_dir(cwd=cwd)
    if common:
        if validate: _validate_root(common)
        return common
    # Last resort: the engine's own parent dir. Unvalidated by design.
    return os.path.dirname(engine_root())
```

— `scripts/qrspi_paths.py:111-143`

```python
common = (res.stdout or "").strip()  # git rev-parse --path-format=absolute --git-common-dir
if res.returncode == 0 and common:
    return os.path.dirname(common)
```

— `scripts/qrspi_paths.py:57-78`

**Dependencies:** Scripts → `qrspi_paths.resolve_repo_root` → `git rev-parse --git-common-dir` + `gh repo view` (validation gate). `qrspi-batch.js` → JS `ENGINE_ROOT` only.
**Implicit contracts:** git-common-dir returns the MAIN checkout even from a worktree (so host root is `<main>`, never `<worktree>`). Validation calls `gh repo view`; a stale `--repo-root` or wrong cwd raises `HostRootError` (fail loud).

## Q4: What does the Claude Code plugin manifest support as component types, and which directory/manifest fields declare skills, commands, agents, hooks, and supporting files?

**Answer:** **NOT FOUND — no plugin manifest exists in this repo.** I searched for `.claude-plugin/`, `plugin.json`, and any `*marketplace*` file across the whole tree (excluding node_modules): zero results. The `.claude/` directory contains only `CLAUDE.md`, `agents/`, `skills/`, and `workflows/` — no packaging manifest. The repo is currently a plain project-local `.claude/` layout, not a packaged plugin. Component definitions are discovered by convention from their directories:

- **Agents:** `.claude/agents/qrspi-*.md` (8 files: design, implement, plan, pr, questions, research, structure, worktree).
- **Skills (slash commands):** `.claude/skills/qrspi-*/SKILL.md` (10 dirs incl. `qrspi-work`). Each SKILL.md front-matter declares `name`, `description`, `command` (e.g. `/qrspi-research`), `argument-hint`, `allowed-tools`.
- **Workflows:** `.claude/workflows/qrspi-batch.js` (a `meta` export + top-level body).
- **MCP servers:** `.mcp.json` (the `linear` http server).
- **Supporting files:** `scripts/`, `.qrspi/templates/`, `docs/`.

The authoritative plugin-manifest *schema* (the component-type fields the question asks about) is not present in `REPO_ROOT` to cite. The closest thing on disk is the skill front-matter convention shown below.

**Search queries attempted:** `find . -iname "*marketplace*" -o -iname "plugin.json"`, `find . -name ".claude-plugin"`, `grep -rn "CLAUDE_PLUGIN_ROOT"` (only the workflow constant + RUS-60 artifacts), `find .claude -maxdepth 2 -type d`.

**Evidence:**

```yaml
---
name: qrspi-research
description: Map codebase facts ...
command: /qrspi-research
argument-hint: <ticket-id>
allowed-tools: Agent, Bash(pwd:*)
---
```

— `.claude/skills/qrspi-research/SKILL.md:1-6`

The RUS-60 design artifact (a prior ticket, not the manifest) records the intended packaging: workflow + sibling `scripts/` shipped as a plugin referenced via `${CLAUDE_PLUGIN_ROOT}`, bundling the `linear` MCP server (`.qrspi/RUS-60/design.md:26,99-108`). That is design intent, not implemented manifest.

**Dependencies:** n/a (artifact absent).
**Implicit contracts:** Today components are discovered by directory convention under `.claude/`; there is no manifest indirection.

## Q5: How do existing skills reference `${CLAUDE_PLUGIN_ROOT}` (or an equivalent engine-root variable), and is that variable already resolved anywhere in the engine scripts?

**Answer:** **No skill references `${CLAUDE_PLUGIN_ROOT}`.** Grepping `.claude/skills/`, scripts are referenced as bare cwd-relative `scripts/qrspi_*.py` (e.g. `qrspi_resolve.py`, `qrspi_pr_body.py`, `qrspi_comment_reply.py`) or as `<repo-root>/scripts/...` placeholder paths — never via an engine-root env var. `${CLAUDE_PLUGIN_ROOT}` appears in exactly one place in live code: `qrspi-batch.js:69`, as the first precedence of the JS `ENGINE_ROOT` constant. All other occurrences are in prior-ticket `.qrspi/RUS-60/*` artifacts (design/plan/research) and this ticket's questions.

Is it **resolved in the engine scripts (python)?** No. The Python scripts derive `ENGINE_ROOT = os.path.dirname(os.path.abspath(__file__))` from `__file__` and never read `CLAUDE_PLUGIN_ROOT`. So the env var is consumed only by the JS workflow, not by any `scripts/qrspi_*.py`.

**Evidence:**

```
.claude/skills/qrspi-work/SKILL.md:71:   python3 scripts/qrspi_resolve.py --ticket "<ticket-id>" \
.claude/skills/qrspi-work/SKILL.md:194:python3 <repo-root>/scripts/qrspi_clear_stale_pr.py --ticket <id>
```

— `.claude/skills/qrspi-work/SKILL.md` (representative; bare/`<repo-root>` relative, no env var)

```js
const ENGINE_ROOT =
  (typeof process !== 'undefined' && process.env && process.env.CLAUDE_PLUGIN_ROOT) || ...
```

— `.claude/workflows/qrspi-batch.js:68-69` (the only live `${CLAUDE_PLUGIN_ROOT}` consumer)

```python
ENGINE_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ENGINE_ROOT)
```

— `scripts/qrspi_resolve.py:47-48` and identically `scripts/qrspi_persist.py:45-46`

**Dependencies:** Skills → bare `scripts/...` (cwd-relative). Workflow → env var. Scripts → `__file__`.
**Implicit contracts:** The skills' bare `scripts/...` references assume the worker's cwd IS the engine/host repo root — a single-checkout assumption (see Inconsistencies). The Python `engine_root()` is stable regardless of cwd because it is `__file__`-derived.

## Q6: What is the contract by which the Workflow tool loads `.claude/workflows/qrspi-batch.js` — what host-side path must the file occupy?

**Answer:** The loading contract is a directory convention: a workflow is a `.js` file under `.claude/workflows/<name>.js` (project-local) or the equivalent global location. The filename is not the workflow name — the runtime reads the exported `meta.name` (here `'qrspi-batch'`, line 2). The file is a JS module exporting `meta` plus a top-level body the runner executes; the runner provides globals the file relies on but does not define: `args`, `agent()`, `phase()`, `log()`, and structured-output schema handling. (The authoritative workflow-loading spec lives in the global `workflow-creator` skill, which is OUTSIDE `REPO_ROOT` and therefore not citable here; the in-repo evidence is the file's shape and the docs.)

In-repo, the file's required host-side path is documented as `.claude/workflows/qrspi-batch.js` (`docs/qrspi-pr-gated-lifecycle-design.md:7`, `docs/qrspi_complete_guide.md:230`). The file uses no relative `import`/`require` — its only external coupling is the `ENGINE_ROOT`-prefixed command strings it hands to workers, so its own load location only needs to satisfy the Workflow tool's `.claude/workflows/` discovery, independent of where `scripts/` lives.

**Evidence:**

```js
export const meta = {
  name: 'qrspi-batch',
  description: 'Drive every assigned in-flight QRSPI ticket one PR-gated step forward ...',
  whenToUse: 'After assigning tickets ...',
  phases: [ ... ],
}
```

— `.claude/workflows/qrspi-batch.js:1-15`

```
.claude/workflows/qrspi-batch.js | ... Finalize workers rewritten for the stacked-branch model. ...
```

— `docs/qrspi-pr-gated-lifecycle-design.md:182` (canonical host path)

**Dependencies:** Workflow runner (host) → `.claude/workflows/*.js` discovery → `meta.name`. The body → host globals `agent/phase/log/args`.
**Implicit contracts:** The file must be syntactically loadable as an ES module exporting `meta`. The body runs to completion and `return`s a result object (`{ ticketsProcessed, results, ... }`, line 1330). The host path `.claude/workflows/` is the discovery anchor.

## Q7: Where does the engine root resolve from within `scripts/qrspi_resolve.py` and its siblings, and how does that interact with the engine living at `${CLAUDE_PLUGIN_ROOT}` after a plugin install?

**Answer:** In every self-locating script, `ENGINE_ROOT = os.path.dirname(os.path.abspath(__file__))` — i.e. the directory containing the script. This is used ONLY for `sys.path.insert(0, ENGINE_ROOT)` so sibling modules (`qrspi_pr_state`, `qrspi_resolve_state`, `qrspi_paths`) import. The HOST checkout root is resolved *separately* via `qrspi_paths.resolve_repo_root(cwd=os.getcwd(), validate=False)` (git-common-dir first). `qrspi_paths.engine_root()` formalizes the same `__file__` derivation.

**Interaction with a plugin install:** After a plugin install, the scripts would physically live under `${CLAUDE_PLUGIN_ROOT}/scripts/`, so `__file__` (hence `ENGINE_ROOT`/`engine_root()`) automatically points at the installed location — sibling imports keep working with no change, because the derivation is purely from `__file__` and never from cwd or an env var. The host root stays decoupled: `resolve_repo_root()` finds the *host* checkout from the worker's cwd via git-common-dir, NOT from the engine location. This is the explicit RUS-60 separation (`qrspi_paths.py:1-31`). The one caveat: `qrspi_paths.engine_root()` is the documented single source of truth, but `qrspi_resolve.py` and `qrspi_persist.py` still compute `ENGINE_ROOT` inline from `__file__` rather than calling `engine_root()` (they import `qrspi_paths` for `resolve_repo_root` only) — functionally identical, but not yet collapsed onto the helper.

**Evidence:**

```python
ENGINE_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ENGINE_ROOT)
from qrspi_pr_state import build_state, branch_set, slice_numbers  # noqa: E402
from qrspi_resolve_state import resolve  # noqa: E402
import qrspi_paths  # noqa: E402
REPO_ROOT = qrspi_paths.resolve_repo_root(cwd=os.getcwd(), validate=False)
```

— `scripts/qrspi_resolve.py:46-58`

```python
def engine_root():
    """Directory holding the engine ``scripts/`` — the dir of this file.
    Stable regardless of host cwd or host root, because it is derived purely from
    ``__file__``."""
    return os.path.dirname(os.path.abspath(__file__))
```

— `scripts/qrspi_paths.py:47-54`

**Dependencies:** `__file__` → `ENGINE_ROOT` → `sys.path` → sibling imports. `cwd` → `resolve_repo_root` → host paths.
**Implicit contracts:** Engine location (`__file__`) and host location (cwd/git-common-dir) are independent; a plugin install moves only the former. `setup_worktree(... repo_root=REPO_ROOT)` writes `<repo_root>/.worktrees/<id>` and runs all git/gt with `cwd=repo_root` — so `repo_root` MUST be the writable host checkout, not the (possibly read-only) engine/plugin dir (`scripts/qrspi_resolve.py:302-341`).

## Q8: What persists in the host's `.claude/workflows/` directory across the workflow's lifecycle, and is there any existing version or staleness marker the engine writes or reads?

**Answer:** **NOTHING is written to `.claude/workflows/` at runtime, and there is no version/staleness marker.** `.claude/workflows/` contains exactly one committed file (`qrspi-batch.js`, 1330 lines). The workflow writes no files there; no script writes to `.claude/workflows/`. Searching for version/staleness markers (a synced-copy hash, a manifest version, a "stale" sentinel) yields none anywhere in the engine. The only runtime-written host artifacts are:

- Phase artifacts → `.worktrees/<id>/.qrspi/<id>/<artifact>.md` (via `qrspi_persist.py:67-71`, `dest_path`).
- A token-free staging area `/tmp/phase-stage/<id>/<artifact>.md` (the `stg()` helper, `qrspi-batch.js`; `STAGE_ROOT` in `qrspi_persist.py:57`) — transient, outside the repo.
- Worktrees under `<host>/.worktrees/<id>/`.

So the workflow's lifecycle leaves `.claude/` untouched; there is no engine-managed version/staleness file to read or reconcile against. (This is the gap Q9 probes — nothing tracks engine version, so nothing detects a stale synced copy because the engine is never copied into the host today.)

**Search queries attempted:** `grep -rn "version\|stale\|sync"` over scripts + workflow for marker writes; `find` for any `.claude/workflows/` writes; none found.

**Evidence:**

```python
def dest_path(repo_root, ticket, artifact):
    """Canonical worktree artifact path. ..."""
    return os.path.join(repo_root, ".worktrees", ticket, ".qrspi", ticket, "%s.md" % artifact)
```

— `scripts/qrspi_persist.py:67-71` (the only host-side artifact write target; not `.claude/`)

```js
const stg = (id, name) => `/tmp/phase-stage/${id}/${name}.md`
```

— `.claude/workflows/qrspi-batch.js` (`stg` helper; staging is `/tmp`, not the repo)

**Dependencies:** persist → `.worktrees/<id>/.qrspi/`. None → `.claude/workflows/`.
**Implicit contracts:** `.claude/workflows/qrspi-batch.js` is a committed, read-only-at-runtime artifact; persistence is the per-phase success gate but targets the worktree, never `.claude/`.

## Q9: What happens when `${CLAUDE_PLUGIN_ROOT}` changes on a plugin update — does any current code re-resolve engine script paths, or would already-synced copies become stale?

**Answer:** Each invocation re-resolves `ENGINE_ROOT` fresh, so a changed `${CLAUDE_PLUGIN_ROOT}` is picked up automatically on the next run — there is no cached/synced copy to go stale. In JS, `ENGINE_ROOT` is computed at module evaluation each time the workflow runs (`qrspi-batch.js:68-71`), reading `process.env.CLAUDE_PLUGIN_ROOT` live. In Python, every script computes `ENGINE_ROOT` from `__file__` at import each run, so wherever the plugin install places the scripts is where they resolve. **No code copies/syncs the engine into the host and no staleness marker exists** (see Q8), so there is no already-synced copy that could drift. The risk is therefore not staleness but the INTERIM state: today `ENGINE_ROOT` falls through to `process.cwd()` because `CLAUDE_PLUGIN_ROOT` is unset in the current single-checkout setup — the comment calls the plugin carriage "sub-ticket 3," not yet exercised end-to-end. The RUS-60 design records this as deferred: "end-to-end plugin-install validation is sub-ticket 4's dogfood gate" (`.qrspi/RUS-60/pr-summary.md:105,112`).

**Evidence:**

```js
// The `${CLAUDE_PLUGIN_ROOT}` carriage that lets the engine live in an installed plugin dir is
// sub-ticket 3 — wired here as the FIRST precedence so flipping to a plugin install is a
// one-line change. The `'.'` fallback keeps the deterministic engine==cwd behavior ...
```

— `.claude/workflows/qrspi-batch.js:64-67`

**Dependencies:** Per-run resolution of `ENGINE_ROOT` (JS env) and `__file__` (python). No persistent sync layer.
**Implicit contracts:** Because resolution is per-run, a plugin update that moves the engine is transparent; nothing must be invalidated. There is no version pin or compatibility check between the workflow `meta` and the scripts.

## Q10: How does the batch workflow behave when an engine script referenced by an absolute or cwd-relative path is missing — does it fail loud or silently skip?

**Answer:** It fails loud per ticket, not silently. The workflow never runs scripts itself — it dispatches a worker agent with the verbatim command. Each worker prompt instructs: emit the script's JSON stdout verbatim; if it errors or prints nothing, output the verbatim error as a HARD STOP (no retry, no improvised alternative). The workflow then parses the worker's return through a dedicated `parse*Envelope` function that returns `{ ok:false, error }` on no-JSON / unparseable / missing-`ok` output. In the main loop, a non-ok resolve pushes `action:'resolve_failed'` and `continue`s to the next ticket; `runPhase` returns `false` and logs "phase failed or was skipped — stopping this ticket"; a thrown worker is caught per-ticket (`action:'errored'`) so one failure does not abort the batch. So a missing script surfaces as that ticket's recorded failure with the verbatim error, and remaining tickets proceed.

**Evidence:**

```js
if (!raw) return { ok: false, error: 'resolve: no JSON envelope in worker output' }
try { env = JSON.parse(raw) } catch (e) { return { ok: false, error: `resolve: unparseable envelope (${e.message})` } }
if (typeof env.ok !== 'boolean') return { ok: false, error: 'resolve: envelope missing ok flag' }
```

— `.claude/workflows/qrspi-batch.js:185-188`

```js
const r = await resolveTicket(t)
if (!r || !r.ok) {
  log(`  ${t.id}: resolve failed — ${r?.error ?? 'no result'}`)
  results.push({ ticketId: t.id, action: 'resolve_failed', summary: r?.error ?? 'unknown' })
  continue
}
```

— `.claude/workflows/qrspi-batch.js` (main loop, ~1271-1276)

**Dependencies:** worker stdout → `parse*Envelope` → per-ticket branch.
**Implicit contracts:** A missing script manifests as `python3: can't open file ...` on the worker's stdout, which yields a non-ok envelope (fail loud per ticket). The per-ticket `try/catch` (`qrspi-batch.js:~1262-1320`) guarantees one ticket's failure is isolated.

## Q11: What does the workflow do when run in a host repo that is not the engine repo (no local `scripts/qrspi_*.py`), and which paths currently break?

**Answer:** Today this is the UNVALIDATED case (the deferred sub-ticket 3/4 of RUS-60). Two path classes resolve differently:

1. **Engine scripts** — found only if `ENGINE_ROOT` points at the engine. With `CLAUDE_PLUGIN_ROOT` unset (current state), `ENGINE_ROOT` falls back to `process.cwd()`. If the worker's cwd is a *host* repo that lacks `scripts/qrspi_*.py`, then `engineCmd('scripts/qrspi_resolve.py')` resolves to `<host>/scripts/qrspi_resolve.py`, which **does not exist → the resolve worker's `python3` fails** (caught as a non-ok envelope per Q10). This is the breakage: until `CLAUDE_PLUGIN_ROOT` is actually set to the plugin dir, a non-engine host repo cannot find the scripts.

2. **Host paths inside the scripts** — already decoupled. If the scripts ARE found (engine root correct), `qrspi_paths.resolve_repo_root()` finds the host checkout via git-common-dir from the worker's cwd, so worktree/config/persist/gh/git/gt all target the host repo correctly even when the engine lives elsewhere. The skills' bare `scripts/...` references (Q5) would also break in a non-engine cwd, but the workflow does not use those — it uses `engineCmd(...)`.

So the breaking surface today is **script discovery via `ENGINE_ROOT` when `CLAUDE_PLUGIN_ROOT` is unset and the engine is not the cwd**; the host-path layer is already engine-independent.

**Evidence:**

```python
# - ENGINE_ROOT: the dir holding this engine's scripts/, derived purely from __file__.
#   Used ONLY for sys.path.insert ...; never a host path.
# - REPO_ROOT (host checkout root): the repo the engine operates ON. Resolved through
#   the shared qrspi_paths.resolve_repo_root() — git-common-dir first ...
```

— `scripts/qrspi_resolve.py:40-47`

```js
const ENGINE_ROOT =
  (typeof process !== 'undefined' && process.env && process.env.CLAUDE_PLUGIN_ROOT) ||
  (typeof process !== 'undefined' && process.cwd && process.cwd()) || '.'
```

— `.claude/workflows/qrspi-batch.js:68-71` (cwd fallback is the breaking link in a foreign host)

Prior research corroborates: "There is no mechanism today to point worktree creation at a host checkout distinct from the script's own location" was the RUS-60 *pre-fix* state; the fix (qrspi_paths) addressed host paths but `${CLAUDE_PLUGIN_ROOT}` script carriage is still interim (`.qrspi/RUS-60/research.md:256`, `.qrspi/RUS-60/pr-summary.md:111-112`).

**Dependencies:** `ENGINE_ROOT` (script discovery) vs `resolve_repo_root` (host paths) — two independent layers.
**Implicit contracts:** For a foreign host to work, `CLAUDE_PLUGIN_ROOT` must be set to the installed engine dir; the host paths then self-correct via git-common-dir.

## Q12: What test coverage exists for the batch workflow and the engine scripts' path resolution, and are any tests cwd-dependent in a way that would mask a plugin-relative path change?

**Answer:** **No test covers `qrspi-batch.js`** — there are zero `*_test.js` files and no Python test references the workflow except by embedding its command strings. The JS workflow is verified only by manual e2e (Q13). The engine scripts have stdlib-only `_test.py` siblings (run with `python3`), including dedicated path-resolution coverage:

- `scripts/qrspi_paths_test.py` (9012 bytes) — exercises `resolve_repo_root` precedence and validation with git/gh stubbed, **including the divergence case** (a synthetic engine dir distinct from a synthetic checkout), explicitly designed to close the "engine ≠ host" gap (`qrspi_paths.py:29-31`).
- `scripts/qrspi_resolve_test.py`, `qrspi_persist_test.py`, plus tests for restack, pr_body, comment_reply, revise_amend, resolve_state, pr_state, config, etc.

Because `qrspi_paths_test.py` stubs subprocess and tests a synthetic engine-≠-host divergence, it is NOT cwd-dependent in a masking way for the host-root logic. However, the gap is at the JS layer: nothing tests that `engineCmd('scripts/...')` resolves correctly when `ENGINE_ROOT` comes from `CLAUDE_PLUGIN_ROOT` rather than cwd — that path change is untested and would not be caught by the python suite.

**Evidence:**

```python
# The pure precedence/validation logic is exercised by ``qrspi_paths_test.py`` with the
# subprocess calls (git, gh) stubbed, including the divergence case (a synthetic engine
# dir distinct from a synthetic checkout) that closes the Q11 testing gap.
```

— `scripts/qrspi_paths.py:29-31`

`find . -name "*_test.js"` → none. Python `_test.py` siblings enumerated in `scripts/` (e.g. `qrspi_paths_test.py`, `qrspi_resolve_test.py`, `qrspi_persist_test.py`).

**Dependencies:** Tests → stubbed `subprocess` (git/gh). No test → JS runtime.
**Implicit contracts:** `_test.py` files are stdlib-only and run with `python3` directly. The JS workflow's path-resolution layer (`ENGINE_ROOT`/`engineCmd`) has no automated coverage.

## Q13: How are orchestration changes to `qrspi-batch.js` verified today given the `evals/` harness is a non-functional placeholder?

**Answer:** Per the project conventions and docs, orchestration changes are verified by (a) the stdlib unit tests for the pure Python logic the workflow delegates to, and (b) **manual end-to-end runs** of the workflow. The `evals/` + `scripts/run_eval.py` harness is documented as a non-functional placeholder: `docs/eval-system.md:101` marks meta-agent revision as a "Stub" pointing at `revise.py:26-44` "placeholder edits," and `scripts/run_eval.py` relies on an SDK call that "tests stub ... to run fully offline" (line ~112). The project `.claude/CLAUDE.md` states the eval harness is "a **non-functional placeholder** — verify pure logic with the unit tests and orchestration changes with manual end-to-end runs."

**Evidence:**

```
| Meta-agent revision | Stub | `revise.py:26-44` — placeholder edits |
```

— `docs/eval-system.md:101`

Project guidance (cited from `.claude/CLAUDE.md`): "The `evals/` + `scripts/run_eval.py` harness is a **non-functional placeholder** — verify pure logic with the unit tests and orchestration changes with manual end-to-end runs."

**Dependencies:** verification path → `scripts/qrspi_*_test.py` (logic) + manual e2e (orchestration).
**Implicit contracts:** No automated gate exists for `qrspi-batch.js` behavior; correctness rests on the tested resolver/persist/paths logic plus human e2e review.

## Q14: What does `qrspi-batch.js` emit that would let an operator confirm phase agents dispatched correctly, and where is that output written?

**Answer:** Two output channels:

1. **`log(...)` lines** (a host-provided global, not defined in the file) — emitted throughout: project scope (`log(\`Project scope: ...\`)`, ~1158), ticket count (~1248), per-ticket header `[i/N] <id> (<status>): <title>` (~1259), the resolver decision `decision=<action> — <reason>`, per-phase progress (`<id>: <name> → saved <bytes>B`, line 447; `reusing existing <name>.md`, line 431), restack outcome, skip/fail reasons, and a per-ticket terminal line `[i/N] <id> → <action>`. These go to the workflow runner's log stream (the host decides the sink; the file does not write a log file).

2. **The returned result object** — the workflow's final `return { ticketsProcessed, results, reconciliation }` (line 1330). `results[]` holds one entry per ticket: `{ ticketId, action, summary, newStatus?, prUrl?, reconcileRetry? }`. `action` is the dispatched decision (`run_design`/`advance`/`submit`/`revise`/`reset`/`land`/`wait`/`resolve_failed`/`restack_conflict`/`errored`), which is exactly the signal an operator uses to confirm what each ticket did. Per-phase artifact persistence is independently confirmable on disk at `.worktrees/<id>/.qrspi/<id>/<artifact>.md` (Q8).

**Evidence:**

```js
log(`  ${id}: ${name} → saved ${p.bytes ?? '?'}B (${String(res).slice(0, 60)})`)
```

— `.claude/workflows/qrspi-batch.js:447` (per-phase dispatch confirmation)

```js
return { ticketsProcessed: results.length, results, reconciliation }
```

— `.claude/workflows/qrspi-batch.js:1330` (structured per-ticket outcome)

```js
log(`  ${t.id}: decision=${a} — ${r.decision.reason}`)
```

— `.claude/workflows/qrspi-batch.js` (~1300, decision trace)

**Dependencies:** `log()` (host runner sink) + the returned object (consumed by the invoker). Artifacts on disk via persist.
**Implicit contracts:** `log` is a runtime-provided global (undeclared in the file); if the host does not provide it the body would throw. There is no operator-facing log FILE written by the workflow — observability is the runner's log stream plus the structured return value.

---

## Discovered Patterns

- **Engine-location / host-checkout separation is the central architectural move** (RUS-60). Two roots are deliberately kept distinct everywhere: the engine dir (from `__file__` in python, from `ENGINE_ROOT`/`CLAUDE_PLUGIN_ROOT`/cwd in JS) used only for code/import location, and the host checkout root (from git-common-dir) used for all writes and subprocess cwds. `scripts/qrspi_paths.py` is the single source of truth for that split.
- **The JS sandbox cannot run python/git/gh**, so `qrspi-batch.js` is purely an orchestrator: it embeds verbatim command strings in worker-agent prompts and parses the worker's stdout. All real mechanics live in self-locating `scripts/qrspi_*.py`.
- **Fail-loud, never-retry on infrastructure errors**: every worker prompt says "output the verbatim error (HARD STOP — do NOT retry or improvise)," and every script reports a single `ok:false` envelope. This is a deliberate guard against a weak local worker model thrashing on path-mangled retries (`qrspi_resolve.py:6-21`).
- **Token-free staging to defeat path mangling (Fix A)**: phase agents write to `/tmp/phase-stage/<id>/<artifact>.md` (no `qrspi` token); `qrspi_persist.py` owns the canonical `.worktrees/<id>/.qrspi/<id>/` destination and is the real per-phase success gate.
- **Per-ticket isolation**: the main loop wraps each ticket in `try/catch`; one ticket's thrown worker or failed resolve records an error and continues, never aborting the batch.
- **Reviewers/project/host-root are all resolved, never hard-coded**, so the harness is shareable from a fresh clone with no config.

## Inconsistencies

- **Q3/RUS-61 mismatch**: the question attributes the decoupled discovery mechanism to "RUS-61," but the codebase attributes it to the **RUS-60** series (`scripts/qrspi_paths.py` + `.qrspi/RUS-60/*`). `RUS-61` exists only as a test fixture id (`qrspi_order_tickets_test.py:110`). Flagged so downstream phases use the correct provenance.
- **Plugin packaging is design intent, not implemented**: `.qrspi/RUS-60/design.md` and `pr-summary.md` describe shipping the engine as a plugin via `${CLAUDE_PLUGIN_ROOT}` bundling the `linear` MCP server, but **no manifest, no `.claude-plugin/`, no `plugin.json`, no marketplace file exists** (Q4). The `${CLAUDE_PLUGIN_ROOT}` carriage in `qrspi-batch.js` is explicitly labeled INTERIM/"sub-ticket 3," and the prose comment promises "flipping to a plugin install is a one-line change" — an unverified claim, since no e2e plugin install has run (Q9, Q13).
- **`engine_root()` helper is defined but not consumed by the two scripts that document it most**: `qrspi_paths.engine_root()` is the stated single source of truth, yet `qrspi_resolve.py:47` and `qrspi_persist.py:45` recompute `ENGINE_ROOT = os.path.dirname(os.path.abspath(__file__))` inline instead of calling the helper. Functionally identical, but the abstraction is not fully adopted (Q7).
- **Skills vs. workflow disagree on how scripts are addressed**: `.claude/skills/qrspi-work/SKILL.md` references scripts as bare cwd-relative `scripts/...` (single-checkout assumption), while `qrspi-batch.js` routes everything through `engineCmd(ENGINE_ROOT + '/scripts/...')`. In a plugin install the skills' bare references would break where the workflow's would not (Q5/Q11).
- **No automated coverage at the JS path-resolution layer**: `qrspi_paths_test.py` rigorously tests the python host-root logic (incl. engine≠host divergence), but nothing tests that `engineCmd` resolves correctly when `ENGINE_ROOT` derives from `CLAUDE_PLUGIN_ROOT` — the exact change a plugin install introduces is unguarded (Q12).
