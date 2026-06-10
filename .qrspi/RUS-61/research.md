# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-10T00:00:00Z
**Generated:** 2026-06-10T00:00:00Z
**Status:** draft

## Q1: How does `scripts/qrspi_resolve.py` currently derive the repo root from `__file__` (the `_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))` "two levels up" computation at line ~40), and what downstream values (OWNER/REPO, worktree path, artifact paths) are computed from that derived root?

**Answer:** The repo root is a module-level constant `REPO_ROOT`, derived purely from `__file__` (never cwd, never an argument). `_SCRIPT_DIR` is the absolute dir of the script (`.../scripts`); `REPO_ROOT` is its parent ("two levels up" meaning script → scripts/ → repo). Everything path-related is computed from it:
- **OWNER/REPO**: `_gh_name_with_owner()` runs `gh repo view` with `cwd=REPO_ROOT` (line 239), then `parse_name_with_owner()` splits the result.
- **Worktree path**: `setup_worktree()` computes `os.path.join(REPO_ROOT, ".worktrees", ticket)` (lines 298-299) and runs all `git worktree`/`gt track` commands with `cwd=REPO_ROOT` or `cwd=worktree`.
- **Artifact existence**: `detect_existing(os.path.join(worktree, ".qrspi", args.ticket))` (line 363).
- **Reviewer config**: `_read_reviewer_config()` reads `os.path.join(REPO_ROOT, ".qrspi", "config.json")` (line 258).
- **Branch listing**: `_existing_branches()` runs `git branch --list` with `cwd=REPO_ROOT` (line 279).
- **Envelope**: `build_envelope()` always emits `REPO_ROOT` as the `repoRoot` field (line 215).

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

**Dependencies:** Imports `build_state`, `branch_set`, `slice_numbers` from `qrspi_pr_state` and `resolve` from `qrspi_resolve_state` (both pure, arg-driven). Calls out to `gh`, `git`, `gt` subprocesses, all anchored to `REPO_ROOT`.
**Implicit contracts:** The script MUST physically live at `<repo-root>/scripts/qrspi_resolve.py` for the "two levels up" derivation to be correct. There is NO git-discovery fallback in this script (unlike `qrspi_pr_body.py`/`qrspi_revise_amend.py`) — it trusts `__file__` exclusively. If run from a copy located elsewhere (e.g. an installed plugin dir), `REPO_ROOT` would point at the plugin install, not the target repo.

## Q2: Which `qrspi_*.py` scripts compute the repo root from their own file location versus receiving it as an input, across `qrspi_persist.py`, `qrspi_pr_body.py`, `qrspi_revise_amend.py`, `qrspi_clear_stale_pr.py`, `qrspi_cleanup.py`, and `qrspi_restack.py`?

**Answer:** ALL of them self-locate from `__file__`; NONE accepts the repo root as a CLI input. Two distinct patterns exist:

**Pattern A — pure `__file__` only (no git fallback):**
- `qrspi_persist.py:40-41` — `REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))`, used directly in `main()` (line 99).
- `qrspi_restack.py:53-54` — same, used as `worktree_path(REPO_ROOT, ...)` (line 197).
- `qrspi_cleanup.py:42-43` — same; all git/gh/gt subprocesses run `cwd=REPO_ROOT`.
- `qrspi_clear_stale_pr.py:47-48` — `REPO_ROOT` from `__file__`, but `pr_info_path()` then refines via `git rev-parse --git-common-dir` (cwd=REPO_ROOT) to find the shared `.graphite_pr_info` (lines 132-136).

**Pattern B — `__file__` as FALLBACK, git-common-dir preferred at runtime:**
- `qrspi_pr_body.py:48-49` (fallback `REPO_ROOT`) + `resolve_repo_root()` (lines 154-165) which runs `git rev-parse --path-format=absolute --git-common-dir` and uses its parent; falls back to `REPO_ROOT` only when git can't answer.
- `qrspi_revise_amend.py:48-49` + `resolve_repo_root()` (lines 169-176), identical to pr_body's.

**Evidence:**

```python
def resolve_repo_root():
    rc, out, _ = _run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"])
    common = (out or "").strip()
    if rc == 0 and common:
        return os.path.dirname(common)
    return REPO_ROOT
```

— `scripts/qrspi_pr_body.py:154-165` (and verbatim mirror at `scripts/qrspi_revise_amend.py:169-176`)

**Dependencies:** `qrspi_cleanup.py` imports `worktree_path` from `qrspi_restack`, `parse_name_with_owner` from `qrspi_resolve`, and helpers from `qrspi_pr_state` (lines 46-53) — so a change to `REPO_ROOT` derivation in those modules transitively affects cleanup.
**Implicit contracts:** Pattern-A scripts assume cwd is irrelevant and `__file__` is authoritative. Pattern-B scripts assume that when running inside a *linked worktree*, `__file__` would mis-resolve to `<worktree>/.worktrees/<ticket>`, so they prefer the git-common-dir's parent (the MAIN checkout) — meaning their `repoRoot` is the main repo, not the worktree they run in.

## Q3: How does the resolver envelope produced by `qrspi_resolve.py` carry the repo root to callers — specifically what is the `repoRoot` field, and where is `${r.repoRoot}` consumed in `.claude/workflows/qrspi-batch.js`?

**Answer:** `build_envelope()` always sets `"repoRoot": REPO_ROOT` (the `__file__`-derived constant) in the JSON envelope on stdout (line 215). The JS side parses it via `parseResolveEnvelope()` into `r`. `r.repoRoot` is consumed only to build ABSOLUTE script invocation paths in finalize prompts:
- `${r.repoRoot}/scripts/qrspi_pr_body.py` (line 596 and 613) — splice PR body.
- `${r.repoRoot}/scripts/qrspi_revise_amend.py` (lines 669, 742) — revise amend.
- `${r.repoRoot}/scripts/qrspi_comment_reply.py` (line 748) — respond-comment.

Note: `parseResolveEnvelope()` validates `worktreeDir` (must end with `/.worktrees/<id>`) but does NOT validate `repoRoot` (lines 139-149). Separately, `r.worktreeDir` — NOT `r.repoRoot` — is assigned to `wd` and feeds the template/artifact path helpers (line 438: `const wd = r.worktreeDir`).

**Evidence:**

```javascript
if (typeof env.worktreeDir !== 'string' || !env.worktreeDir.endsWith(`/.worktrees/${ticketId}`))
    return { ok: false, error: `resolve: worktreeDir not <repo>/.worktrees/${ticketId} (got ${env.worktreeDir})` }
```

— `.claude/workflows/qrspi-batch.js:148-149`

**Dependencies:** Downstream consumers in qrspi-batch.js (submit/revise/respond-comment workers) depend on `r.repoRoot` being an absolute path to a checkout containing `scripts/qrspi_*.py`.
**Implicit contracts:** `repoRoot` is the engine/script location AND the target-repo root simultaneously — the envelope conflates "where the scripts live" with "which repo to act on". The batch consumers assume `${r.repoRoot}/scripts/...` exists; this only holds when engine == target repo.

## Q4: What command-line arguments does each affected `qrspi_*.py` script currently accept, and do any already expose a `--repo-root` (or equivalent) flag that the new explicit-override mechanism could extend?

**Answer:** NONE of the affected scripts exposes `--repo-root` or any path-override flag. Every script derives the root from `__file__`/git only. Current args:
- `qrspi_resolve.py`: `--ticket` (req), `--assigned`, `--linear-status`, `--ticket-content-file`, `--trunk`, `--blocked-open`, `--blocked-by` (lines 330-344).
- `qrspi_persist.py`: `--ticket` (req), `--artifact` (req, choices), `--stage-root` (default `/tmp/phase-stage`) (lines 91-95).
- `qrspi_pr_body.py`: `--ticket` (req), `--slice` (default 1), `--body-file` (lines 202-207).
- `qrspi_revise_amend.py`: `--ticket` (req), `--branch` (req) (lines 255-256).
- `qrspi_clear_stale_pr.py`: `--ticket` (req) (line 145).
- `qrspi_cleanup.py`: `--ticket` (req), `--dry-run` (lines 245-246).
- `qrspi_restack.py`: `--ticket` (req) (line 194).

**Evidence:**

```python
parser.add_argument("--ticket", required=True, help="Ticket id, e.g. RUS-21")
parser.add_argument("--artifact", required=True, choices=ARTIFACTS, ...)
parser.add_argument("--stage-root", default=STAGE_ROOT, ...)
```

— `scripts/qrspi_persist.py:91-95`

**Dependencies:** Argparse only; no env-var or config-file path overrides for the root.
**Implicit contracts:** `--stage-root` is the ONLY existing path-related override anywhere (persist). The pattern for adding a `--repo-root` flag would be a new `parser.add_argument` plus a fallback chain (flag → git-discovery → `__file__`). No script currently has that chain; `resolve_repo_root()` (pr_body/revise_amend) is the closest existing precedent (git → `__file__`, no flag).

## Q5: How do `.claude/skills/qrspi-*` and `.claude/agents/qrspi-*` currently invoke the scripts — what literal invocation strings (`scripts/qrspi_*.py`, `${r.repoRoot}/scripts/...`) appear, and are paths relative to cwd or absolute?

**Answer:** Two distinct invocation styles, depending on the caller:

**Skills (`.claude/skills/qrspi-*/SKILL.md`)** do NOT invoke the python scripts directly for repo-root resolution — they instruct the agent to "Resolve `REPO_ROOT` from `pwd`" (relative to cwd) and then build artifact/template paths as `<REPO_ROOT>/.qrspi/...`. Examples: `qrspi-research/SKILL.md:16`, `qrspi-design/SKILL.md:17`, `qrspi-plan/SKILL.md:16`, `qrspi-implement/SKILL.md:16` (which notes `REPO_ROOT` equals the worktree path). The one script invocation in skills is `qrspi-work/SKILL.md:70`: `python3 scripts/qrspi_resolve.py ...` — a **cwd-relative** path.

**Workflow (`.claude/workflows/qrspi-batch.js`)** uses BOTH:
- cwd-relative `scripts/qrspi_*.py` for workers told "Your cwd is the main repo root" — persist (line 291), resolve (line 370), restack (line 418), cleanup (line 787).
- absolute `${r.repoRoot}/scripts/qrspi_*.py` for finalize-stage workers (pr_body line 596, revise_amend line 669/742, comment_reply line 748).

**Evidence:**

```javascript
async function persistArtifact(id, name, phaseLabel) {
  return await agent(
    `You are the PERSIST worker for ${id} artifact "${name}". Your cwd is the main repo root.
...
  python3 scripts/qrspi_persist.py --ticket ${id} --artifact ${name}
```

— `.claude/workflows/qrspi-batch.js:286-291`

**Dependencies:** cwd-relative invocations depend on the worker actually being in the main repo root; absolute invocations depend on `r.repoRoot` from the resolve envelope.
**Implicit contracts:** Skills assume `pwd` IS the repo/worktree root (no script self-location involved). The mix of relative and absolute invocation in batch.js is a latent inconsistency: relative ones break if cwd drifts; absolute ones depend on the (engine==repo) `repoRoot` value.

## Q6: Is `${CLAUDE_PLUGIN_ROOT}` referenced anywhere in the current codebase (scripts, skills, agents, or `qrspi-batch.js`), and what environment variables do the scripts already read?

**Answer:** **NOT FOUND** — `CLAUDE_PLUGIN_ROOT` is referenced nowhere. A recursive grep across `scripts/`, `.claude/`, and `docs/` returned zero matches. Additionally, the python scripts read NO environment variables at all: a grep for `os.environ`, `getenv`, `os.getenv` across all `scripts/qrspi_*.py` returned zero matches, and `process.env` does not appear in `qrspi-batch.js`.

**Evidence:**

```
$ grep -rn "CLAUDE_PLUGIN_ROOT" scripts/ .claude/ docs/   → (no output)
$ grep -rn "os.environ|getenv|os.getenv" scripts/qrspi_*.py → (no output)
$ grep -n "process.env|CLAUDE_PLUGIN" .claude/workflows/qrspi-batch.js → (no output)
```

— search queries run from `REPO_ROOT`

**Dependencies:** None — repo-root discovery is purely `__file__`- and git-based today; there is no env-var injection point.
**Implicit contracts:** The harness currently has NO environment-driven location mechanism. Introducing `CLAUDE_PLUGIN_ROOT` (or any env var) would be a brand-new discovery channel, not an extension of an existing one.

## Q7: How is the per-ticket worktree path (`.worktrees/<id>/`) constructed and where is it rooted today — relative to the self-located repo root, and which scripts read or write under it?

**Answer:** The worktree path is uniformly `os.path.join(<repo_root>, ".worktrees", <ticket>)`. It is rooted at the self-located repo root in every script. Construction sites:
- `qrspi_resolve.py:298-299` (`setup_worktree`, the only WRITER — runs `git worktree add` / `gt track`).
- `qrspi_restack.py:69-72` (`worktree_path`, pure helper).
- `qrspi_pr_body.py:59-62` (`worktree_path`).
- `qrspi_revise_amend.py:67-70` (`worktree_path`).
- `qrspi_persist.py:58-62` (`dest_path` embeds `.worktrees/<ticket>/.qrspi/<ticket>/<artifact>.md`).
- `qrspi_cleanup.py:208` (imports `worktree_path` from restack; reaps the dir).

`setup_worktree` is idempotent: reuse existing dir, else check out the highest existing phase branch (`pick_tip`), else (only when `create_design=True`) create `<ticket>/design` off trunk.

**Evidence:**

```python
def setup_worktree(ticket, trunk="main", create_design=False):
    worktrees_dir = os.path.join(REPO_ROOT, ".worktrees")
    worktree = os.path.join(worktrees_dir, ticket)
    if os.path.isdir(worktree):
        return worktree  # reuse
```

— `scripts/qrspi_resolve.py:283-302`

**Dependencies:** `setup_worktree` depends on `pick_tip` + `_existing_branches` (git `branch --list` cwd=REPO_ROOT). All readers share the same `os.path.join(repo_root, ".worktrees", ticket)` formula.
**Implicit contracts:** Every script must agree on the SAME repo root for the worktree path to be consistent — `qrspi_resolve.py` writes it under `__file__`-derived `REPO_ROOT`, while pr_body/revise_amend READ it under their git-common-dir-derived root. If those two roots diverged (engine ≠ target repo, or running from a non-worktree copy), the writer and readers would point at different `.worktrees/` trees.

## Q8: Where does `qrspi_persist.py` resolve the canonical artifact destination (`.worktrees/<id>/.qrspi/<id>/`), and does that destination derive from the engine's `__file__` root or from the target repo?

**Answer:** In `dest_path(repo_root, ticket, artifact)` (lines 58-62), called from `main()` with the module-level `REPO_ROOT` (line 99). That `REPO_ROOT` is **purely `__file__`-derived** (lines 40-41) — there is NO git-discovery fallback in persist (Pattern A, unlike pr_body/revise_amend). So the destination derives from the ENGINE's `__file__` location, which today is assumed identical to the target repo. If the persist script lived outside the target repo, artifacts would be moved into `<engine>/.worktrees/...` rather than the target repo's worktree.

**Evidence:**

```python
def dest_path(repo_root, ticket, artifact):
    return os.path.join(repo_root, ".worktrees", ticket, ".qrspi", ticket,
                        "%s.md" % artifact)
...
    dest = dest_path(REPO_ROOT, args.ticket, args.artifact)
```

— `scripts/qrspi_persist.py:58-62, 99`

**Dependencies:** `persist()` does the filesystem move (src staged file → dest). `main()` emits `"repoRoot": REPO_ROOT` and `dest` in the JSON envelope.
**Implicit contracts:** The staged source (`/tmp/phase-stage/<id>/<artifact>.md`) is token-free and engine-agnostic, but the DESTINATION is engine-`__file__`-rooted. The whole "Fix A" design assumes engine root == target-repo root; persist is the script most tightly coupled to that assumption because it has no git fallback.

## Q9: What happens in each affected script when `git rev-parse --show-toplevel` from cwd fails or returns a non-zero exit (e.g., cwd is not inside a git repo)? Is there any existing error handling for a missing repo root?

**Answer:** No script uses `git rev-parse --show-toplevel` at all. Two scripts use `git rev-parse --git-common-dir` for refinement and both degrade gracefully:
- `qrspi_pr_body.py` / `qrspi_revise_amend.py` `resolve_repo_root()`: on `rc != 0` or empty output, they **fall back to the `__file__`-derived `REPO_ROOT`** (line 165 / 176). No error raised.
- `qrspi_clear_stale_pr.py` `pr_info_path()`: on `rc != 0`/empty, falls back to `os.path.join(repo_root, ".git")` (line 133). Never raises; the script's `ok` is hardcoded `True` because an absent cache is a no-op (line 152).

For scripts WITHOUT git discovery (resolve, persist, restack, cleanup), there is no `show-toplevel`/`rev-parse` for the root — they trust `__file__` and never check whether cwd is a git repo. The git SUBPROCESS calls they do make (worktree add, branch list, gt track) run with `cwd=REPO_ROOT`; failures there raise `RuntimeError` (resolve `setup_worktree` lines 308-309, 318-323) which `main()` catches into a single `ok:false` envelope (resolve lines 368-373).

**Evidence:**

```python
rc, out, _ = _run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"])
common = (out or "").strip()
if rc == 0 and common:
    return os.path.dirname(common)
return REPO_ROOT
```

— `scripts/qrspi_pr_body.py:161-165`

**Dependencies:** The `__file__` fallback is the universal safety net; git discovery is best-effort refinement only.
**Implicit contracts:** "git can't answer" is treated as "we were invoked by absolute main path and `__file__` is correct" (pr_body docstring lines 159-160). There is NO handling for the case where BOTH `__file__` is wrong (engine ≠ repo) AND cwd is outside a repo — that case silently yields the engine dir as the root.

## Q10: In dev mode, where the engine checkout *is* the target repo (engine == repo), what current behavior would the new discovery mechanism need to preserve, and how is "running from a checkout" distinguishable from "running as an installed plugin"?

**Answer:** Today the codebase assumes engine == target repo unconditionally — there is no notion of "installed plugin" anywhere (Q6: no `CLAUDE_PLUGIN_ROOT`, no env vars). The behavior to preserve when engine == repo:
1. `REPO_ROOT` = two-levels-up from `scripts/qrspi_*.py` resolves to the checkout root (correct today).
2. From inside a linked worktree, pr_body/revise_amend prefer the git-common-dir's parent (the MAIN checkout) over `__file__` (which would point at `<worktree>/scripts`), so `.worktrees/<ticket>` resolves under the main checkout — see docstrings at pr_body lines 44-47, revise_amend lines 44-47.
3. resolve/persist/restack/cleanup trust `__file__` with no git fallback and currently work because the scripts physically sit in the target repo's `scripts/`.

There is currently NO mechanism to distinguish "running from a checkout" vs "installed plugin" — the only signal that exists is `__file__` itself and `git rev-parse --git-common-dir` (which answers "am I inside a git work-area"). An installed plugin's `__file__` would point at the plugin dir, and `git rev-parse` run from cwd would describe the *target* repo (cwd), so the two would DIVERGE — that divergence is the distinguishing signal the codebase does not yet exploit.

**Evidence:**

```python
# This is the FALLBACK root; main() prefers the git-common-dir root (below) so the
# script is correct whether invoked from the main checkout OR from inside a linked
# worktree (where __file__ would point at the worktree's own copy and mis-resolve
# <worktree>/.worktrees/<ticket>).
```

— `scripts/qrspi_pr_body.py:44-47`

**Dependencies:** Worktree consistency between the resolve WRITER (`__file__`-rooted) and the pr_body/revise_amend READERS (git-common-dir-rooted) depends on both resolving to the same checkout — guaranteed today only because engine == repo.
**Implicit contracts:** "Running from a checkout" is the ONLY mode the code handles; the git-common-dir preference exists solely to handle the worktree-vs-main-checkout sub-case, NOT engine-vs-plugin. Any new discovery must keep #1-#3 working when engine == repo.

## Q11: How do callers in `qrspi-batch.js` currently establish cwd before invoking the scripts, and could a discrepancy between the JS process cwd and the spawned script's cwd cause `git rev-parse --show-toplevel` to resolve a different repo than intended?

**Answer:** `qrspi-batch.js` does NOT programmatically set cwd. It spawns worker agents via `agent(prompt, …)` and establishes cwd by NATURAL-LANGUAGE INSTRUCTION in the prompt — e.g. "Your cwd is the main repo root" (persist line 288, resolve line 338, restack line 414) or "the MAIN repo root (NOT a worktree...)" (cleanup line 784). The JS runner has no `process.chdir` and passes no cwd option (no `process.env`/`process.cwd` appears in the file, Q6). So the *actual* cwd is whatever the spawned worker agent happens to be in.

A discrepancy is possible: if a worker's real cwd is a *worktree* rather than the main checkout while running a Pattern-A script (resolve/persist), `__file__` (not cwd) still governs the root, so those are cwd-insensitive for the root itself — BUT the `gh repo view` / `git branch` subprocess calls run `cwd=REPO_ROOT`, so they stay anchored. For the Pattern-B scripts (pr_body/revise_amend), `resolve_repo_root()` runs `git rev-parse --git-common-dir` from the worker's cwd; if that cwd were a DIFFERENT repo than intended, it would resolve that other repo's common dir. No script uses `--show-toplevel`; the relevant call is `--git-common-dir`, run from the (worker-controlled, prompt-asserted) cwd.

**Evidence:**

```javascript
`You are the RESOLVE worker for QRSPI ticket ${t.id}. Your cwd is the main repo root.
...
     python3 scripts/qrspi_resolve.py --ticket ${t.id} --linear-status "<status>" --ticket-content-file ${ticketFile}
```

— `.claude/workflows/qrspi-batch.js:338, 370`

**Dependencies:** Correctness of cwd-relative invocations (`scripts/qrspi_*.py`) depends entirely on the worker honoring the prompt's "cwd is the main repo root" assertion; nothing in the runner enforces it.
**Implicit contracts:** cwd is asserted, never enforced. Pattern-B scripts' git-discovery is implicitly trusted to run from inside the intended repo; a worker that drifted into a sibling repo's directory would silently retarget `resolve_repo_root()`.

## Q12: What patterns do the existing `scripts/qrspi_*_test.py` stdlib-only tests use to construct fixtures (temp dirs, fake repo roots, monkeypatching `__file__` or cwd), so new tests can cover engine-dir ≠ target-repo, git discovery, `--repo-root` override, and dev fallback?

**Answer:** Tests are stdlib-only (`unittest` or assert-based), import the module by inserting `scripts/` on `sys.path` (or relying on cwd), and exercise PURE helpers with explicit path arguments — they do NOT monkeypatch `__file__` or cwd, and do NOT run the subprocess-backed paths (git/gh/gt). Patterns observed:
- **Pure helpers passed a fake root as an argument**: `qrspi_persist_test.py` calls `qp.dest_path("/repo", ...)` and `qp.staging_path("/tmp/...", ...)` with literal roots (lines 13, 25). This is the key seam — `dest_path`/`worktree_path` take `repo_root` as a parameter even though `main()` hardcodes `REPO_ROOT`.
- **`tempfile.TemporaryDirectory()`** for filesystem-touching helpers: `PersistTest.setUp` creates a temp root, stages a file, and asserts the move (lines 35-55).
- **`sys.path.insert(0, _HERE)`** import shim: `qrspi_pr_body_test.py:15-16`.
- The subprocess parts (`resolve_repo_root`, `setup_worktree`, gt/git) are explicitly NOT unit-tested by convention — verified by manual e2e (pr_body_test.py docstring lines 7-9).

**Evidence:**

```python
class PersistTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
...
    def test_moves_non_empty_file_and_reports_bytes(self):
        src = self._stage("RUS-21", "plan", "# Plan\n\n16 steps\n")
        dest = qp.dest_path(self.root, "RUS-21", "plan")
```

— `scripts/qrspi_persist_test.py:34-51`

**Dependencies:** Tests depend on the pure helpers accepting `repo_root` as a parameter (the existing testability seam). `resolve_repo_root()` (no params, reads git+`__file__`) is the part currently UNTESTED.
**Implicit contracts:** New tests for git-discovery / `--repo-root` override / dev-fallback would need a NEW seam: the resolution chain must be a pure function taking (flag value, git output, `__file__` fallback) so it can be unit-tested without spawning git — mirroring how `dest_path` takes `repo_root` explicitly. No existing test monkeypatches `__file__`, so that pattern would be novel here.

## Q13: How are the pure repo-root-derivation helpers currently factored within each script — are they isolated functions that can be unit-tested directly, or inlined into `main`/argument handling?

**Answer:** Mixed:
- **Module-level inline constants (NOT functions)**: `_SCRIPT_DIR` / `REPO_ROOT` are computed at import time in EVERY affected script (resolve:40-41, persist:40-41, pr_body:48-49, revise_amend:48-49, clear_stale:47-48, cleanup:42-43, restack:53-54). These run on import and are NOT parameterized, so they cannot be unit-tested with a fake `__file__` without re-importing under a patched environment.
- **Isolated, testable resolver function**: only pr_body and revise_amend factor a `resolve_repo_root()` function (pr_body:154-165, revise_amend:169-176) — but it takes NO arguments and calls `_run(git ...)` directly, so it is effectively untestable without subprocessing (and indeed is not tested).
- **Path-from-root helpers ARE isolated and pure**: `worktree_path(repo_root, ticket)`, `dest_path(repo_root, ticket, artifact)`, `pr_info_path(repo_root)`, `staging_path(...)` all take the root as a parameter and ARE unit-tested.

So the DERIVATION of the root is inlined/constant or wrapped in a git-calling function; the USE of the root is cleanly parameterized and tested.

**Evidence:**

```python
def worktree_path(repo_root, ticket):
    """Canonical worktree path for a ticket. Pure; computed here, never typed by the
    model. Matches qrspi_pr_body.worktree_path / qrspi_persist."""
    return os.path.join(repo_root, ".worktrees", ticket)
```

— `scripts/qrspi_revise_amend.py:67-70`

**Dependencies:** `qrspi_cleanup.py` reuses `qrspi_restack.worktree_path` and `qrspi_resolve.parse_name_with_owner` (lines 52-53), so the pure helpers are already shared across modules.
**Implicit contracts:** The pure path helpers consistently take `repo_root` as the FIRST parameter — a uniform seam a new discovery function could feed. The missing piece is a pure, parameterized root-RESOLUTION helper (taking flag/env/git-output/`__file__` as inputs) — that factoring does not exist yet; resolution is either a module constant or a git-coupled function.

## Q14: What does each affected script log or emit (stderr messages, envelope fields, exit codes) when it resolves the repo root, so a manual run from a path *outside* this repo can be verified to have discovered the correct target?

**Answer:** NO script writes to stderr for logging — every grep for `sys.stderr` matched only `classify_*` helpers naming a `stderr` parameter, not logging. The repo root is surfaced ONLY as the `repoRoot` field in the JSON envelope on stdout, plus derived path fields:
- `qrspi_resolve.py`: `{ok, repoRoot, worktreeDir, existing, decision, commentTargets, reviewers, teamReviewers, ticketContent, error?}` (build_envelope lines 213-223). Exit 0 if `ok` else 1 (line 377).
- `qrspi_persist.py`: `{ok, repoRoot, src, dest, bytes, error?}` (lines 102-110).
- `qrspi_pr_body.py`: envelope includes `repoRoot` (defaults to module `REPO_ROOT`, or the resolved one passed in) (lines 127-133).
- `qrspi_revise_amend.py`: `repoRoot` field (lines 144-148).
- `qrspi_clear_stale_pr.py`: `{ok, repoRoot, prInfoPath, ticket, removed, warning?}` (lines 151-159); `ok` hardcoded True.
- `qrspi_cleanup.py`: `{ok, repoRoot, decision, reason, removed{...}, dryRun, error?}` (line 192 onward).

So to verify discovery from outside the repo, a manual run inspects `repoRoot` (and `worktreeDir`/`dest`/`prInfoPath`) in the stdout JSON; there is no stderr trace and no verbose/log flag.

**Evidence:**

```python
env = {
    "ok": error is None,
    "repoRoot": REPO_ROOT,
    "src": src,
    "dest": dest,
    "bytes": bytes_written,
}
```

— `scripts/qrspi_persist.py:102-108`

**Dependencies:** The JS `parseResolveEnvelope` reads these fields; it validates `worktreeDir` but not `repoRoot` (Q3).
**Implicit contracts:** `repoRoot` in the envelope is the canonical observability hook for "what did I resolve". Exit code is a binary ok/fail signal (resolve uses 0/1). There is no dedicated "discovered root via X mechanism" diagnostic — a verifier must infer correctness by comparing the emitted `repoRoot`/`worktreeDir` against the intended target.

---

## Discovered Patterns

- **Two repo-root derivation patterns coexist.** Pattern A (pure `__file__`, no fallback): `qrspi_resolve.py`, `qrspi_persist.py`, `qrspi_restack.py`, `qrspi_cleanup.py`. Pattern B (`__file__` as fallback, `git rev-parse --git-common-dir` parent preferred at runtime): `qrspi_pr_body.py`, `qrspi_revise_amend.py`. `qrspi_clear_stale_pr.py` is a hybrid (`__file__` root, git-common-dir only to locate `.graphite_pr_info`). This inconsistency is the central fact for any "decouple engine from repo" work.
- **Uniform "two levels up" idiom**: every affected script computes `_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))` then `REPO_ROOT = os.path.dirname(_SCRIPT_DIR)` as a module-level constant at import time, with a near-identical docstring ("never cwd, never an argument").
- **Pure path helpers take `repo_root` as their first parameter** (`worktree_path`, `dest_path`, `pr_info_path`, `staging_path`) and are the unit-tested seam; the root DERIVATION itself is a module constant or a git-coupled function and is NOT unit-tested.
- **`qrspi_pr_state.py` and `qrspi_resolve_state.py` are fully pure** — no `__file__`, no git discovery, no cwd; `build_state(owner, repo, ...)` and `resolve(state)` receive everything as arguments. They are the orchestration "brain"; the location concern lives entirely in the wrapper scripts.
- **cwd is asserted in prose, never enforced in code** — `qrspi-batch.js` sets cwd only via "Your cwd is the main repo root" prompt text; the JS runner uses no `process.chdir`/cwd option and reads no env vars.
- **`repoRoot` is the sole observability surface** for root resolution — emitted in every script's stdout JSON envelope; no stderr logging, no verbose flag, no log file.
- **Envelope conflates engine and target repo**: `repoRoot` simultaneously means "where `scripts/qrspi_*.py` live" (used to build `${r.repoRoot}/scripts/...` invocations) and "which repo's `.worktrees/` to act on". This conflation holds only while engine == target repo.

## Inconsistencies

- **Inconsistent fallback discipline across scripts.** `qrspi_persist.py` (which physically MOVES artifacts into `.worktrees/<id>/.qrspi/<id>/`) has NO git-discovery fallback and trusts `__file__` alone, while the LESS destructive `qrspi_pr_body.py`/`qrspi_revise_amend.py` DO prefer git-common-dir over `__file__`. The script with the strongest correctness need (persist) has the weakest resolution.
- **Mixed invocation path styles in `qrspi-batch.js`.** Some workers invoke `scripts/qrspi_*.py` cwd-relative (persist/resolve/restack/cleanup), others invoke `${r.repoRoot}/scripts/qrspi_*.py` absolute (pr_body/revise_amend/comment_reply). The relative ones silently depend on the worker honoring "cwd is the main repo root"; the absolute ones depend on the resolve envelope's `repoRoot`.
- **`parseResolveEnvelope` validates `worktreeDir` but not `repoRoot`** (`qrspi-batch.js:148-149`). The field used to build absolute script-invocation paths (`${r.repoRoot}/scripts/...`) is accepted unchecked, while the worktree path is strictly shape-checked.
- **`wd` is `r.worktreeDir`, not `r.repoRoot`** (`qrspi-batch.js:438`). Template/artifact path helpers (`tpl(wd,...)`, `art(wd,...)`) build `${wd}/.qrspi/...` from the WORKTREE, while finalize workers build `${r.repoRoot}/scripts/...` from the REPO ROOT — two different anchors used in the same workflow for related path construction.
- **Comment vs. code on git-discovery semantics.** pr_body/revise_amend docstrings say the `__file__` fallback is reached "e.g. cwd outside a repo, in which case the caller invoked us by absolute main path and `__file__` is correct" — this assumes `__file__` is ALWAYS the target repo when git fails, which is exactly the assumption that breaks under engine ≠ target-repo (installed-plugin) mode the questions probe for.
- **No env-var / plugin-root channel despite the question framing.** `CLAUDE_PLUGIN_ROOT` and any env-var-based discovery are entirely absent (Q6), so the codebase has no existing hook the "decouple" feature could extend — it would be a new mechanism, not an extension.
