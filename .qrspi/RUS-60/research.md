# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-10T00:00:00Z
**Generated:** 2026-06-10T00:00:00Z
**Status:** draft

## Q1: How does `scripts/qrspi_resolve.py` currently compute the repo root from `__file__` (the "two levels up" derivation at line 40), and what other paths in the envelope it builds depend on that derived root?

**Answer:** `qrspi_resolve.py` derives `REPO_ROOT` purely from its own file location: `_SCRIPT_DIR` = the absolute dir of `__file__` (i.e. `<root>/scripts`), and `REPO_ROOT` = its parent (one `dirname` up = "two levels up" from the file). It then `sys.path.insert(0, _SCRIPT_DIR)` to import its sibling pure modules. It NEVER consults cwd, an argument, or `git --git-common-dir` (unlike `qrspi_pr_body.py`/`qrspi_comment_reply.py`/`qrspi_revise_amend.py`, which prefer git-common-dir). Everything path-related hangs off this single derived `REPO_ROOT`:

- The emitted envelope field `repoRoot` (`build_envelope`, line 215) is always the module-level `REPO_ROOT`.
- The worktree dir: `worktrees_dir = os.path.join(REPO_ROOT, ".worktrees")` and `worktree = .../<ticket>` (`setup_worktree`, lines 298-299), surfaced as `worktreeDir`.
- The reviewer config path: `os.path.join(REPO_ROOT, ".qrspi", "config.json")` (`_read_reviewer_config`, line 258).
- All `gh`/`git`/`gt` subprocesses run with `cwd=REPO_ROOT` (lines 239, 249, 279, 307, 318) — except `gt track` which runs with `cwd=worktree` (line 321).
- Artifact detection: `detect_existing(os.path.join(worktree, ".qrspi", args.ticket))` (line 363) — derived from `worktree`, which is derived from `REPO_ROOT`.

**Evidence:**

```python
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(_SCRIPT_DIR)
sys.path.insert(0, _SCRIPT_DIR)
```

— `scripts/qrspi_resolve.py:40-42`

```python
worktrees_dir = os.path.join(REPO_ROOT, ".worktrees")
worktree = os.path.join(worktrees_dir, ticket)
```

— `scripts/qrspi_resolve.py:298-299`

**Dependencies:** Imports sibling pure modules `qrspi_pr_state` (`build_state`, `branch_set`, `slice_numbers`) and `qrspi_resolve_state` (`resolve`) via the `sys.path.insert`. Downstream consumer is `qrspi-batch.js` `resolveTicket()`/`parseResolveEnvelope()`.
**Implicit contracts:** The script MUST physically live at `<repo-root>/scripts/qrspi_resolve.py` for the "two levels up" derivation to land on the real repo root. The caller is told (in the workflow prompt) "Your cwd is the main repo root," but cwd is irrelevant to path derivation here — only `__file__` location matters. If the script file is relocated (e.g. under a plugin root), `REPO_ROOT` resolves to the plugin's parent, not the host repo.

## Q2: Which `qrspi_*.py` scripts beyond `qrspi_resolve.py` perform their own self-location or path derivation relative to `__file__`, and what directories do each of them resolve to?

**Answer:** Every persisted/self-locating script uses the identical `_SCRIPT_DIR = dirname(abspath(__file__))`, `REPO_ROOT = dirname(_SCRIPT_DIR)` pattern (= parent of `scripts/`). There are TWO variants:

- **`__file__`-only (no git fallback):** `qrspi_resolve.py:40-41`, `qrspi_persist.py:40-41`, `qrspi_cleanup.py:42-43`, `qrspi_restack.py:53-54`, `qrspi_clear_stale_pr.py:47-48`. These treat the `__file__`-derived `REPO_ROOT` as authoritative.
- **git-common-dir preferred, `__file__` as FALLBACK:** `qrspi_pr_body.py:48-49` + `resolve_repo_root()` (lines 154-165), `qrspi_comment_reply.py:40-41` + git-common-dir (lines 161-166), `qrspi_revise_amend.py:48-49` + git-common-dir (lines 170-176). These run `git rev-parse --path-format=absolute --git-common-dir` and use its parent as the MAIN repo root, falling back to the `__file__`-derived `REPO_ROOT` only when git can't answer. The stated reason: to be correct whether invoked from the main checkout OR from inside a linked worktree (where `__file__` would point at the worktree's own copy and mis-resolve `<worktree>/.worktrees/<ticket>`).

All variants resolve to the directory two levels up from the script file (the repo root that contains `scripts/`). `qrspi_resolve.py`, `qrspi_cleanup.py`, `qrspi_restack.py` also `sys.path.insert(0, _SCRIPT_DIR)` to import siblings.

**Evidence:**

```python
def resolve_repo_root():
    rc, out, _ = _run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"])
    common = (out or "").strip()
    if rc == 0 and common:
        return os.path.dirname(common)
    return REPO_ROOT
```

— `scripts/qrspi_pr_body.py:154-165`

**Dependencies:** The git-common-dir variant depends on `git` being runnable from cwd inside the repo. The `__file__`-only variant depends only on file location.
**Implicit contracts:** All scripts assume `scripts/` sits directly under the repo root. The two-variant split is significant for plugin packaging: `qrspi_resolve.py`/`qrspi_persist.py` (the path-critical worktree+artifact ones) would resolve `REPO_ROOT` to the ENGINE/plugin location, while `qrspi_pr_body.py`/`qrspi_comment_reply.py`/`qrspi_revise_amend.py` would self-correct to the host repo via git-common-dir whenever invoked from inside the host checkout.

## Q3: How does the persistence path flow from the staging location (`/tmp/phase-stage/<id>/<artifact>.md`) into the canonical `.worktrees/<id>/.qrspi/<id>/` destination inside `qrspi_persist.py`, and which of those path segments are derived from the script's own location versus passed in as arguments?

**Answer:** `qrspi_persist.py` is `__file__`-only self-locating (`REPO_ROOT` = parent of `scripts/`, line 41). Flow:
- `src` (staging) = `staging_path(stage_root, ticket, artifact)` = `<stage_root>/<ticket>/<artifact>.md`. `stage_root` defaults to `STAGE_ROOT = "/tmp/phase-stage"` (line 48) and is overridable via `--stage-root`. `ticket`/`artifact` come from `--ticket`/`--artifact` args.
- `dest` (canonical) = `dest_path(REPO_ROOT, ticket, artifact)` = `<REPO_ROOT>/.worktrees/<ticket>/.qrspi/<ticket>/<artifact>.md` (lines 58-62). The `REPO_ROOT` segment is script-derived; `ticket`/`artifact` are args.
- `persist(src, dest)` (lines 65-83) verifies `src` is non-empty, `os.makedirs` the dest parent, `shutil.move`s, and re-verifies dest non-empty.

So the ONLY path segment that is script-self-located is the `REPO_ROOT` prefix of `dest`. Staging root and ticket/artifact tokens are caller-supplied. The whole `.worktrees/<id>/.qrspi/<id>/` suffix is hard-coded structure built in `dest_path`.

**Evidence:**

```python
def dest_path(repo_root, ticket, artifact):
    return os.path.join(repo_root, ".worktrees", ticket, ".qrspi", ticket,
                        "%s.md" % artifact)
```

— `scripts/qrspi_persist.py:58-62`

```python
src = staging_path(args.stage_root, args.ticket, args.artifact)
dest = dest_path(REPO_ROOT, args.ticket, args.artifact)
```

— `scripts/qrspi_persist.py:98-99`

**Dependencies:** Caller is `qrspi-batch.js` `persistArtifact()` (line 286), which invokes `python3 scripts/qrspi_persist.py --ticket <id> --artifact <name>` (relative path, cwd = "main repo root"). `STAGE_ROOT` is kept in sync with the JS `stg()` helper.
**Implicit contracts:** The dest `REPO_ROOT` is derived from `__file__`, NOT from cwd or git-common-dir. The persist worker prompt asserts cwd = main repo root but that only affects the relative `scripts/qrspi_persist.py` resolution, not the dest path. If the script lived under a plugin root, `dest` would write into `<plugin-root>/.worktrees/...` rather than the host repo's worktree.

## Q4: What command-line arguments and environment variables does `qrspi_resolve.py` accept today, and which of them carry a repo root, worktree path, or OWNER/REPO that an installed plugin would need to receive from the host's cwd instead?

**Answer:** `qrspi_resolve.py` accepts these CLI args (lines 330-344): `--ticket` (required), `--assigned` (flag), `--linear-status` (default ""), `--ticket-content-file` (default ""), `--trunk` (default "main"), `--blocked-open` (flag), `--blocked-by` (append/repeatable). It reads NO environment variables for path resolution. Critically, there is **no `--repo-root`, no `--worktree`, no `--owner`/`--repo` argument**:
- The repo root is derived from `__file__` (line 41), not passed in.
- OWNER/REPO is discovered at runtime via `gh repo view --json nameWithOwner` run with `cwd=REPO_ROOT` (`_gh_name_with_owner`, lines 237-242), then split by `parse_name_with_owner`.
- The worktree path is computed from `REPO_ROOT` (line 298), not passed in.

For an installed plugin, the three host-specific facts NOT currently received as inputs — repo root, the resulting worktree path, and OWNER/REPO — would all need to come from the host's cwd/checkout rather than from the script's own location. Today they implicitly assume the script lives in the host repo.

**Evidence:**

```python
parser.add_argument("--ticket", required=True, help="Ticket id, e.g. RUS-21")
parser.add_argument("--assigned", action="store_true", ...)
parser.add_argument("--linear-status", default="", ...)
parser.add_argument("--ticket-content-file", default="", ...)
parser.add_argument("--trunk", default="main", ...)
parser.add_argument("--blocked-open", action="store_true", ...)
parser.add_argument("--blocked-by", action="append", default=[], ...)
```

— `scripts/qrspi_resolve.py:330-344`

**Dependencies:** `gh` CLI (repo view, api user), `git` (branch list, worktree add), `gt` (track). Linear facts (`--assigned`, `--linear-status`, `--blocked-*`) are supplied by the caller (the resolve worker fetches them via `mcp__linear__get_issue`).
**Implicit contracts:** OWNER/REPO is resolved by running `gh repo view` in `REPO_ROOT`; this assumes `REPO_ROOT` is the host's git checkout with a GitHub remote. There is no override path. A plugin install would break this because `REPO_ROOT` would point at the plugin, whose `gh repo view` would name the wrong repo (or fail).

## Q5: How do the `qrspi-*` agent definitions in `.claude/agents/` and their skill wrappers in `.claude/skills/` reference the `qrspi_*.py` scripts and the `qrspi-batch.js` workflow — by relative path, absolute path, or some resolved variable?

**Answer:** The **phase agent definitions** in `.claude/agents/qrspi-*.md` do NOT reference the python scripts or the workflow at all by path. They receive `REPO_ROOT` / `OUTPUT_PATH` / `QUESTIONS_PATH` etc. as spawn-prompt inputs and operate relative to those (e.g. `qrspi-research.md:16,20` "`cd "$REPO_ROOT"`"; `qrspi-pr.md:18,22`). They are pure phase workers; the script invocations are injected by the orchestrator at spawn time.

The **`qrspi-work` SKILL** (`.claude/skills/qrspi-work/SKILL.md`) — the canonical procedure the worker agents follow — references scripts with a MIX of styles:
- Relative `scripts/qrspi_*.py` (assumes cwd = repo root): `scripts/qrspi_resolve.py` (line 70), `scripts/qrspi_pr_body.py` (lines 267, 293), `scripts/qrspi_revise_amend.py` (line 332), `scripts/qrspi_comment_reply.py` (line 343), `scripts/qrspi_cleanup.py` (line 459).
- Explicit `<repo-root>/scripts/...` placeholder: `qrspi_clear_stale_pr.py` (lines 194, 589, 616).

The **`qrspi-batch.js` workflow** invokes scripts in worker prompts with BOTH styles: relative `python3 scripts/qrspi_persist.py` (line 291), `scripts/qrspi_resolve.py` (line 370), `scripts/qrspi_restack.py` (line 418), `scripts/qrspi_cleanup.py` (line 787); and absolute via the resolver envelope `python3 ${r.repoRoot}/scripts/qrspi_pr_body.py` (line 596), `${r.repoRoot}/scripts/qrspi_revise_amend.py` (lines 669, 742), `${r.repoRoot}/scripts/qrspi_comment_reply.py` (line 748). `r.repoRoot` is the `__file__`-derived root from `qrspi_resolve.py`'s envelope. The workflow refers to itself/SKILL via the constant `SKILL = '.claude/skills/qrspi-work/SKILL.md'` (line 55), a repo-relative path.

**Evidence:**

```
const SKILL = '.claude/skills/qrspi-work/SKILL.md'
```

— `.claude/workflows/qrspi-batch.js:55`

```
  python3 scripts/qrspi_persist.py --ticket ${id} --artifact ${name}
```

— `.claude/workflows/qrspi-batch.js:291`

```
     python3 ${r.repoRoot}/scripts/qrspi_pr_body.py --ticket ${t.id} --slice 1
```

— `.claude/workflows/qrspi-batch.js:596`

**Dependencies:** Worker agents execute these python commands; phase agents do not. `r.repoRoot` flows from `qrspi_resolve.py` → envelope → JS.
**Implicit contracts:** Relative `scripts/...` invocations require the worker's cwd to be the repo root (asserted in each worker prompt as "Your cwd is the main repo root"). Absolute `${r.repoRoot}/scripts/...` invocations require `r.repoRoot` to be the host repo — which it only is because the script self-located there. The `SKILL` constant is a repo-relative path with no plugin-root indirection.

## Q6: Where is the `linear` MCP binding declared (`.mcp.json`), what endpoint and fields does it contain, and does anything in that file assume it lives at the repo root rather than under a plugin root?

**Answer:** The binding is in `.mcp.json` at the repo root. It declares a single server named `linear`, type `http`, url `https://mcp.linear.app/mcp`. There are no secrets, no auth fields, no path/cwd references, and no repo-root assumptions in the file itself — it is purely a server URL binding. Claude Code's convention is that a project-scoped `.mcp.json` lives at the project root; nothing inside the JSON encodes that location. `.claude/CLAUDE.md` documents that this binding is referenced "by the fixed name `linear` (tools `mcp__linear__*`)" and is "committed in the project-scoped `.mcp.json`."

**Evidence:**

```json
{
  "mcpServers": {
    "linear": {
      "type": "http",
      "url": "https://mcp.linear.app/mcp"
    }
  }
}
```

— `.mcp.json:1-8`

**Dependencies:** The resolve/ticket workers call `mcp__linear__get_issue` etc., which require this server to be registered and OAuth-authenticated.
**Implicit contracts:** The server name `linear` (and thus the `mcp__linear__*` tool prefix) is hard-coded throughout the agents/workflow. The file's effective scope (project vs plugin) is determined by WHERE the file sits, which Claude Code resolves — the JSON has no internal anchor. A plugin would need its own mechanism to register this same `linear` server name, or the host's `.mcp.json` must still provide it.

## Q7: How is the QRSPI guidance block currently embedded in `.claude/CLAUDE.md`, and what configuration values (`.qrspi/config.json`, `linearTeam`, `linearProject`, reviewers) does that block and the scripts read from the target repo at runtime?

**Answer:** The QRSPI guidance is the entire body of `.claude/CLAUDE.md` (the project-scoped CLAUDE.md, which is itself `@~/.agents/AGENTS.md`-prefixed at the repo-root `CLAUDE.md`). It is plain markdown prose embedded directly in the file (sections: QRSPI Workflow, Setup—Linear MCP, Lifecycle—PR-gated, Available skills, Workflow rules, Worktrees, Codebase conventions) — there is no include/transclusion of a separate guidance file; the content is inline.

Config values it documents and the scripts read at runtime:
- `.qrspi/config.json` — gitignored per-user override (`.gitignore:5`); template at `.qrspi/config.example.json`. `qrspi_resolve.py` reads it from `<REPO_ROOT>/.qrspi/config.json` (`_read_reviewer_config`, line 258) for `reviewers` / `teamReviewers`. Missing/invalid → `{}` and the `@me` default applies.
- `reviewers` — defaults to `["@me"]`; `@me` expands to the gh-authenticated login via `gh api user` (`_gh_authenticated_login`, line 249). Resolved by `resolve_reviewers`/`select_source` (lines 84-118). Emitted as CSV in the envelope, spliced via `reviewerFlags()` (`qrspi-batch.js:274-279`).
- `teamReviewers` — defaults to `[]`; Graphite team slugs.
- `linearTeam` / `linearProject` — documented as read by `/qrspi-ticket` from `.qrspi/config.json` (default project "QRSPI"); these are NOT read by any python script in `scripts/` — they are consumed by the ticket-creation skill conversation, not the resolver. (No grep hit for `linearTeam`/`linearProject` in `scripts/`.)

**Evidence:**

```python
REVIEWER_CONFIG = ["config.json"]  # relative to <repo>/.qrspi/
...
def _read_reviewer_config():
    path = os.path.join(REPO_ROOT, ".qrspi", *REVIEWER_CONFIG)
    try:
        with open(path) as fh:
            cfg = json.load(fh)
        return cfg if isinstance(cfg, dict) else {}
    except (OSError, ValueError):
        return {}
```

— `scripts/qrspi_resolve.py:54, 254-264`

**Dependencies:** `qrspi_resolve.py` (reviewer config) and the `/qrspi-ticket` skill (linearTeam/linearProject). `gh api user` for `@me` expansion.
**Implicit contracts:** Config is read from `<REPO_ROOT>/.qrspi/config.json`, where `REPO_ROOT` is `__file__`-derived. A plugin install would read config from the plugin's `.qrspi/`, not the host's. The guidance block is inline prose in the host repo's CLAUDE.md — there is no plugin-distributable form of it today.

## Q8: When `qrspi-batch.js` and the phase agents construct the staging path and canonical destination, what happens if the target repo's cwd differs from the directory the engine code lives in — which call sites would resolve to the engine location instead of the target repo?

**Answer:** The staging path (`stg(id, name) => /tmp/phase-stage/${id}/${name}.md`, `qrspi-batch.js:264`) is an absolute `/tmp` path independent of both cwd and engine location — it is always correct. The canonical destination, however, is built INSIDE `qrspi_persist.py` from its `__file__`-derived `REPO_ROOT` (Q3). The decisive factor is therefore where the python script files physically live, NOT the worker's cwd:

- If the engine code (`scripts/*.py`, `qrspi-batch.js`) lives in a DIFFERENT directory than the target repo, the `__file__`-only scripts (`qrspi_persist.py`, `qrspi_resolve.py`, `qrspi_cleanup.py`, `qrspi_restack.py`, `qrspi_clear_stale_pr.py`) resolve `REPO_ROOT` to the ENGINE location and would write `.worktrees/<id>/.qrspi/...` under the engine, not the target repo.
- The git-common-dir variants (`qrspi_pr_body.py`, `qrspi_comment_reply.py`, `qrspi_revise_amend.py`) would self-CORRECT to the host repo, BUT only when invoked from a cwd inside the host's git checkout (so `git rev-parse --git-common-dir` answers); otherwise they fall back to the engine `REPO_ROOT`.
- The relative `scripts/qrspi_*.py` invocations in worker prompts (lines 291, 370, 418, 787) depend on cwd = repo root to even FIND the script; if cwd is the host repo but the scripts live under the engine, these relative invocations would fail to locate the file entirely.

So the engine-vs-target split would mis-resolve at: every `__file__`-only `REPO_ROOT` (persist dest, resolve worktree/config/owner), and every relative `scripts/...` invocation. The `${r.repoRoot}/scripts/...` invocations inherit whatever (possibly wrong) root the resolver derived.

**Evidence:**

```javascript
const stg = (id, name) => `/tmp/phase-stage/${id}/${name}.md`
```

— `.claude/workflows/qrspi-batch.js:264`

```python
src = staging_path(args.stage_root, args.ticket, args.artifact)
dest = dest_path(REPO_ROOT, args.ticket, args.artifact)
```

— `scripts/qrspi_persist.py:98-99`

**Dependencies:** `persistArtifact()` → `qrspi_persist.py`; `resolveTicket()` → `qrspi_resolve.py`.
**Implicit contracts:** The entire Fix-A persistence + resolve mechanism assumes the python scripts are co-located with (two levels above) the host repo's worktree tree. Today that holds because everything is one checkout. Separating engine from target violates this assumption for the `__file__`-only scripts.

## Q9: How does the worktree setup logic in `qrspi_resolve.py` create or locate `.worktrees/<id>/`, and would that succeed if the engine were installed read-only under `${CLAUDE_PLUGIN_ROOT}` while the host repo is a separate git checkout?

**Answer:** `setup_worktree(ticket, trunk, create_design)` (lines 283-324) computes `worktrees_dir = os.path.join(REPO_ROOT, ".worktrees")` and `worktree = .../<ticket>` from the `__file__`-derived `REPO_ROOT`. It is idempotent:
- Existing `worktree` dir → reuse.
- No dir but a phase branch exists (via `pick_tip` over `_existing_branches`, which runs `git branch --list <ticket>/*` with `cwd=REPO_ROOT`) → `git worktree add <worktree> <tip>` with `cwd=REPO_ROOT`.
- No branch + `create_design=True` → `git worktree add -b <ticket>/design <worktree> <trunk>` then `gt track --parent <trunk>` (cwd=worktree).
- No branch + `create_design=False` → returns the path, creates nothing (keeps resolve read-only).

This would NOT work for a read-only-plugin + separate-host-repo layout. The git operations are all run with `cwd=REPO_ROOT` and the worktree is created UNDER `REPO_ROOT/.worktrees`. If `REPO_ROOT` were `${CLAUDE_PLUGIN_ROOT}` (read-only, and likely not even a git repo with the host's branches), then: `git branch --list`/`git worktree add` would target the wrong repo (or fail — the plugin root may not be a git checkout), AND writing `.worktrees/<id>/` under a read-only plugin root would fail. The host repo's branches and trunk live in the SEPARATE checkout, which this code never references. There is no mechanism today to point worktree creation at a host checkout distinct from the script's own location.

**Evidence:**

```python
worktrees_dir = os.path.join(REPO_ROOT, ".worktrees")
worktree = os.path.join(worktrees_dir, ticket)
if os.path.isdir(worktree):
    return worktree  # reuse
tip = pick_tip(_existing_branches(ticket), ticket)
if tip:
    os.makedirs(worktrees_dir, exist_ok=True)
    rc, _, err = _run(["git", "worktree", "add", worktree, tip], cwd=REPO_ROOT)
```

— `scripts/qrspi_resolve.py:298-307`

**Dependencies:** `git worktree`, `gt track`. `_existing_branches` (line 278) and all git calls use `cwd=REPO_ROOT`.
**Implicit contracts:** `REPO_ROOT` must be the writable host git checkout. Note `qrspi_resolve.py` uses `__file__`-only derivation (no git-common-dir fallback), so it cannot self-correct to a host repo when run from a plugin location. `${CLAUDE_PLUGIN_ROOT}` is NOT referenced anywhere in the codebase (no grep hits in scripts/, workflow, or agents).

## Q10: What does `qrspi-batch.js` depend on (Node runtime, file layout, sibling scripts) that has no documented plugin component slot, and where exactly does it expect to find the `qrspi_*.py` scripts it invokes?

**Answer:** `qrspi-batch.js` is a Claude Code Workflow script (ES-module `export const meta = {...}`, top of file). It has NO `require`/`import` statements (no grep hits) — it relies entirely on the Workflow runtime's injected globals (`agent`, `parallel`, `phase`, `log`, `args`). The git/gh/Linear/python mechanics the JS sandbox cannot run are delegated to worker agents (documented lines 17-26). It expects the python scripts at the repo-relative path `scripts/<name>.py`:
- Relative invocations assuming cwd = repo root: `scripts/qrspi_persist.py` (291), `scripts/qrspi_resolve.py` (370), `scripts/qrspi_restack.py` (418), `scripts/qrspi_cleanup.py` (787).
- Absolute via envelope: `${r.repoRoot}/scripts/qrspi_pr_body.py` (596), `${r.repoRoot}/scripts/qrspi_revise_amend.py` (669, 742), `${r.repoRoot}/scripts/qrspi_comment_reply.py` (748).
- The SKILL it references: `.claude/skills/qrspi-work/SKILL.md` (constant, line 55).

There is NO documented plugin component slot for any of this: the file lives at `.claude/workflows/qrspi-batch.js`, refers to scripts at `scripts/` (a sibling of `.claude/`, i.e. repo root), and there is no `.claude-plugin/` manifest, no `plugin.json`, no marketplace file, and no `${CLAUDE_PLUGIN_ROOT}` usage anywhere in the repo (verified: `.claude/` contains only `CLAUDE.md`, `agents/`, `skills/`, `workflows/`).

**Evidence:**

```javascript
export const meta = {
  name: 'qrspi-batch',
  ...
}
```

— `.claude/workflows/qrspi-batch.js:1-15`

```javascript
  python3 scripts/qrspi_persist.py --ticket ${id} --artifact ${name}
```

— `.claude/workflows/qrspi-batch.js:291`

**Dependencies:** Workflow runtime globals (`agent`, `phase`, `parallel`, `log`); `python3`, `git`, `gh`, `gt` in the worker environment; the `scripts/` dir as a repo-root sibling of `.claude/`.
**Implicit contracts:** The workflow assumes a flat single-checkout layout: `.claude/workflows/qrspi-batch.js` and `scripts/*.py` both under one repo root, with cwd = that root for the relative invocations. No plugin packaging or component manifest exists to relocate these.

## Q11: How do the existing `scripts/qrspi_*_test.py` siblings set up paths and fixtures for the self-locating scripts, and do any of them hard-code a repo-root assumption that would break once code lives under a plugin root?

**Answer:** The tests are stdlib-only and import the module under test directly (`import qrspi_persist as qp`; `from qrspi_resolve import ...`). They rely on the test file living in `scripts/` so Python's automatic `sys.path[0]` (the script's own dir) makes the sibling importable; `qrspi_pr_body_test.py` makes this explicit with `_HERE = dirname(abspath(__file__)); sys.path.insert(0, _HERE)` (lines 15-16). Documented run convention: `python3 scripts/qrspi_*_test.py` (cwd = repo root).

Path handling is designed to AVOID hard-coding the real repo root:
- The PURE functions take `repo_root` as a parameter, so tests pass synthetic roots: `qp.dest_path("/repo", "RUS-21", "plan")` → asserts `/repo/.worktrees/RUS-21/.qrspi/RUS-21/plan.md` (`qrspi_persist_test.py:25-26`), and `persist()` is exercised against `tempfile.TemporaryDirectory()` roots (lines 35-47).
- Where tests reference the module's derived `REPO_ROOT`, they assert EQUALITY TO the imported `REPO_ROOT` symbol, not to a literal path string: `check("ok envelope repoRoot is derived REPO_ROOT", ok_env["repoRoot"], REPO_ROOT)` (`qrspi_resolve_test.py:101`). `qrspi_pr_body_test.py` likewise uses the imported `REPO_ROOT` in expected envelopes (lines 112, 119).

So no test hard-codes an absolute repo-root STRING — they all parametrize or compare against the self-derived symbol. The tests themselves would still PASS under a plugin root (the derived `REPO_ROOT` would just point at the plugin, and the equality assertions follow it). The tests therefore do NOT guard against the engine-vs-target mis-resolution — they would stay green even if `REPO_ROOT` resolved to the wrong place at runtime, because they only verify the pure path-construction shape, never that `REPO_ROOT` equals the host repo.

**Evidence:**

```python
def test_canonical_worktree_layout(self):
    d = qp.dest_path("/repo", "RUS-21", "plan")
    self.assertEqual(d, "/repo/.worktrees/RUS-21/.qrspi/RUS-21/plan.md")
```

— `scripts/qrspi_persist_test.py:24-26`

```python
check("ok envelope repoRoot is derived REPO_ROOT", ok_env["repoRoot"], REPO_ROOT)
```

— `scripts/qrspi_resolve_test.py:101`

**Dependencies:** Tests import siblings via `scripts/` on sys.path; pure helpers (`staging_path`, `dest_path`, `persist`, `build_envelope`, `parse_name_with_owner`, etc.). Subprocess-backed parts (gh/git/gt, `build_state`, `setup_worktree`) are intentionally NOT unit-tested (verified by manual e2e — `qrspi_resolve_test.py:6-9`).
**Implicit contracts:** Test correctness depends only on the test file's location in `scripts/`, not on the host repo. The pure-vs-impure split means the path-derivation that WOULD break under a plugin root (the `__file__`→`REPO_ROOT` step and the subprocess cwd) is exactly the untested part.

## Q12: How do `qrspi_resolve.py`, `qrspi_persist.py`, and `qrspi-batch.js` surface the paths they resolve (the repo root, worktree, staging, and destination) in their output or logs, so that a wrong engine-vs-target resolution would be visible during the dogfood install?

**Answer:** All three emit the resolved paths explicitly:
- `qrspi_resolve.py` prints a single JSON envelope to stdout (indent=2) with `repoRoot` (= derived `REPO_ROOT`) and `worktreeDir` as top-level fields (`build_envelope`, lines 213-223; dumped at lines 375-376). On error it still emits `repoRoot` + `worktreeDir` (lines 369-373). So a wrong root is directly visible as the `repoRoot` value.
- `qrspi_persist.py` prints a JSON envelope with `repoRoot`, `src` (staging path), `dest` (canonical destination), and `bytes` (lines 102-113). A wrong root surfaces in both `repoRoot` and the `dest` prefix.
- `qrspi-batch.js` logs via `log(...)` at persist/phase boundaries: `log(\`  ${id}: ${name} → saved ${p.bytes ?? '?'}B ...\`)` (line 322), and failure logs include `p?.error` (line 319). It consumes `r.repoRoot`/`r.worktreeDir` from the resolve envelope and splices `r.repoRoot` into invoked commands (e.g. line 596), so a wrong root would appear in the logged/invoked command paths. The staging path is the deterministic `stg()` `/tmp/...` value (line 264), independent of root.

A wrong engine-vs-target resolution would be VISIBLE: `qrspi_resolve.py`'s `repoRoot`/`worktreeDir` and `qrspi_persist.py`'s `repoRoot`/`dest` would show the engine/plugin path instead of the host repo path in their JSON stdout, and the JS `log` lines / invoked `${r.repoRoot}/scripts/...` commands would echo it. However, nothing performs an ASSERTION that `repoRoot` matches the host checkout — detection during a dogfood install would be by human inspection of the emitted JSON/logs, not an automatic guard.

**Evidence:**

```python
env = {
    "ok": error is None,
    "repoRoot": REPO_ROOT,
    "src": src,
    "dest": dest,
    "bytes": bytes_written,
}
...
json.dump(env, sys.stdout, indent=2)
```

— `scripts/qrspi_persist.py:102-112`

```javascript
log(`  ${id}: ${name} → saved ${p.bytes ?? '?'}B (${String(res).slice(0, 60)})`)
```

— `.claude/workflows/qrspi-batch.js:322`

**Dependencies:** Resolve/persist envelopes are parsed by `qrspi-batch.js` (`parseResolveEnvelope`, `PERSIST_SCHEMA`); JS `log` is the workflow runtime logger.
**Implicit contracts:** Both scripts treat their emitted `repoRoot` as authoritative (no cross-check). Observability is descriptive, not validating — a wrong root is reported faithfully but not flagged as wrong.

---

## Discovered Patterns

- **Two self-location strategies coexist.** Path-critical worktree/artifact scripts (`qrspi_resolve.py`, `qrspi_persist.py`, `qrspi_cleanup.py`, `qrspi_restack.py`, `qrspi_clear_stale_pr.py`) use `__file__`-ONLY derivation (`REPO_ROOT` = two levels up, no git fallback). PR-message/comment scripts (`qrspi_pr_body.py`, `qrspi_comment_reply.py`, `qrspi_revise_amend.py`) PREFER `git rev-parse --git-common-dir` and use `__file__` only as a fallback — explicitly to stay correct when invoked from inside a linked worktree. This split is the single most plugin-relevant fact: the `__file__`-only group cannot self-correct to a host repo if relocated.
- **Fix-A staging is the universal artifact-write convention.** Phase agents write to token-free `/tmp/phase-stage/<id>/<name>.md` (the `stg()` helper / `STAGE_ROOT` constant, kept in sync between JS and python), and a self-locating script moves it to the canonical `.qrspi` path. The "qrspi" token only ever appears in script-derived paths, never in model-typed paths.
- **Single-checkout layout assumption everywhere.** Every script assumes `scripts/` is a direct child of the repo root, and `.worktrees/<id>/.qrspi/<id>/` hangs off that same root. `.claude/` (workflows, skills, agents) is a sibling of `scripts/`. There is no indirection layer between "where the engine code lives" and "where the host repo is."
- **No plugin packaging exists.** No `.claude-plugin/`, `plugin.json`, marketplace manifest, or `${CLAUDE_PLUGIN_ROOT}` reference anywhere in `scripts/`, `.claude/workflows/`, or `.claude/agents/`. The only occurrence of the word "plugin" in repo code is a generic boundary clause in `.claude/agents/qrspi-research.md:53`.
- **Worker prompts assert cwd = "main repo root."** persist (288), resolve (338), restack (414), cleanup (784), reconcile (859). Relative `scripts/...` invocations depend on this; `__file__`-derived roots do not.
- **Pure/impure test split.** Every script separates pure path/logic helpers (unit-tested against synthetic/temp roots) from subprocess-backed mechanics (gh/git/gt, untested, manual e2e). Reviewer/config resolution is fully pure-tested via parameter injection.
- **Reviewers and Linear team/project are config-driven, not hard-coded.** `.qrspi/config.json` (gitignored) overrides; `@me`/default-project fallbacks keep a fresh clone zero-config and username-free.

## Inconsistencies

- **Mixed script-path styles within the SAME workflow.** `qrspi-batch.js` invokes some scripts relatively (`scripts/qrspi_persist.py`, `scripts/qrspi_resolve.py`, lines 291/370/418/787) and others absolutely via the envelope (`${r.repoRoot}/scripts/qrspi_pr_body.py`, lines 596/669/742/748). The relative form depends on worker cwd; the absolute form depends on the resolver's `__file__`-derived root. The SKILL.md doc is similarly mixed (`scripts/...` vs `<repo-root>/scripts/...`). No single convention.
- **`qrspi_resolve.py`/`qrspi_persist.py` lack the git-common-dir fallback that their siblings have.** `qrspi_pr_body.py`/`qrspi_comment_reply.py`/`qrspi_revise_amend.py` explicitly added git-common-dir resolution to be "correct whether invoked from the main checkout OR a linked worktree" (`qrspi_pr_body.py:44-47`), yet `qrspi_resolve.py` (which CREATES worktrees) and `qrspi_persist.py` (which writes INTO worktrees) rely on `__file__` only. The comment in `qrspi_resolve.py:38-40` claims deriving from `__file__` "removes the path the model kept corrupting," but does not address the worktree-vs-engine relocation case the sibling scripts guard against.
- **Comment says "two levels up" but the code is one `dirname`.** `qrspi_resolve.py:37-41` (and the identical comment in `qrspi_persist.py:37-41`) says the repo root is "two levels up," while the code does `_SCRIPT_DIR = dirname(abspath(__file__))` then `REPO_ROOT = dirname(_SCRIPT_DIR)` — i.e. the FILE is two levels deep (`<root>/scripts/<file>`), so the root is reached by one `dirname` from the dir (two from the file). The prose is loosely worded relative to the operation count, though the result is correct.
- **Observability reports but never validates the root.** All three components faithfully print `repoRoot`/`worktreeDir`/`dest`, but none asserts the resolved root is actually the host checkout (e.g. by cross-checking against `gh repo view` cwd or git-common-dir). A wrong engine-vs-target resolution is reported as if correct; detection relies on human inspection during the dogfood install.
- **Linear `linearTeam`/`linearProject` are documented as config but read by no python script.** `.claude/CLAUDE.md` and `config.example.json` describe them; only the `/qrspi-ticket` skill conversation consumes them. The reviewer keys (`reviewers`/`teamReviewers`) ARE read by `qrspi_resolve.py`. This split means part of `config.json` is script-consumed and part is skill-prose-consumed.
