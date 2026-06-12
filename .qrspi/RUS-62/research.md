# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-12T00:00:00Z
**Generated:** 2026-06-12T00:00:00Z
**Status:** draft

## Q1: Which engine-code files currently reference `scripts/qrspi_*.py` paths, and through what mechanism (shell invocation, constant, heredoc) is each path constructed, so every reference can be rewritten to `${CLAUDE_PLUGIN_ROOT}/scripts/...`?

**Answer:** Three distinct mechanism classes reference the scripts:

1. **`.claude/workflows/qrspi-batch.js` — already indirected through `engineCmd()`.** Every live script invocation is `python3 ${engineCmd('scripts/qrspi_*.py')}`, where `engineCmd(rel) => `${ENGINE_ROOT}/${rel}`` and `ENGINE_ROOT` already has `process.env.CLAUDE_PLUGIN_ROOT` as its FIRST precedence (RUS-60 §Delta interim). There are 12 such `engineCmd('scripts/...')` call sites; every remaining bare `scripts/qrspi_*.py` string in this file is a **comment**, not an invocation (lines 30, 47, 59, 92, 388, 861, 1219). So flipping the workflow to a real plugin install requires no per-call-site change — only that `CLAUDE_PLUGIN_ROOT` be populated.
2. **`.claude/skills/qrspi-work/SKILL.md` — bare, un-prefixed prose.** This is the SKILL the batch finalize/revise prompts tell workers to follow; it embeds literal `python3 scripts/qrspi_resolve.py ...`, `scripts/qrspi_pr_body.py`, `scripts/qrspi_comment_reply.py`, `scripts/qrspi_revise_amend.py`, `scripts/qrspi_cleanup.py` references (a mix of bare `scripts/...` and `<repo-root>/scripts/...`). These assume cwd is the engine/host root and are NOT engine-root-prefixed.
3. **Per-phase skill SKILL.md files** (`qrspi-research`, `qrspi-design`, etc.) reference `.qrspi/...` artifact paths under `<REPO_ROOT>`, not scripts; they are host-path, not engine-path, references.

The Python scripts themselves never reference each other by `scripts/...` path — they import siblings via `sys.path.insert(0, ENGINE_ROOT)` (see Q2/Q8).

**Evidence:**

```js
const ENGINE_ROOT =
  (typeof process !== 'undefined' && process.env && process.env.CLAUDE_PLUGIN_ROOT) ||
  (typeof process !== 'undefined' && process.cwd && process.cwd()) ||
  '.'
const engineCmd = (rel) => `${ENGINE_ROOT}/${rel}`
const SKILL = engineCmd('.claude/skills/qrspi-work/SKILL.md')
```

— `.claude/workflows/qrspi-batch.js:68-78`

```
python3 scripts/qrspi_resolve.py --ticket "<ticket-id>" \
```

— `.claude/skills/qrspi-work/SKILL.md:71` (bare, un-prefixed)

**Dependencies:** qrspi-batch.js → ENGINE_ROOT → (env or cwd); the batch prompts → SKILL.md prose; SKILL.md → scripts/*.py at runtime cwd.
**Implicit contracts:** Batch invocations already tolerate the engine not being cwd; SKILL.md prose does NOT (it assumes cwd == engine root, or hard-codes `<repo-root>/scripts/...`). Comments containing `scripts/...` must not be mechanically rewritten — only the 12 `engineCmd` call sites are live.

## Q2: How does the engine currently locate its own root and the target repo root (per the RUS-61 decoupling), and which functions or env vars supply those paths to the bundled scripts?

**Answer:** RUS-61 already shipped the engine-root vs host-root split as a shared module, `scripts/qrspi_paths.py`. It exposes two functions:

- **`engine_root()`** — `os.path.dirname(os.path.abspath(__file__))`; the dir holding the engine's `scripts/`. Stable regardless of host cwd. Used only for `sys.path.insert(0, engine_root())` sibling imports.
- **`resolve_repo_root(repo_root=None, cwd=None, validate=True)`** — the single source of truth for the HOST checkout root, with precedence: (1) explicit `--repo-root` (validated via `gh repo view`), (2) git-common-dir auto-detect from cwd (validated), (3) `__file__` fallback = `os.path.dirname(engine_root())` (unvalidated last resort). Raises `HostRootError` on validation failure (fail-loud).

Every consuming script follows the identical pattern at module load: `ENGINE_ROOT = os.path.dirname(os.path.abspath(__file__))` → `sys.path.insert(0, ENGINE_ROOT)` → `import qrspi_paths` → `REPO_ROOT = qrspi_paths.resolve_repo_root(cwd=os.getcwd(), validate=False)`. Consumers: `qrspi_resolve.py`, `qrspi_persist.py`, `qrspi_pr_body.py`, `qrspi_comment_reply.py`, `qrspi_revise_amend.py`, `qrspi_cleanup.py`, `qrspi_restack.py`, `qrspi_clear_stale_pr.py`. In `main()`, the script re-resolves with `resolve_repo_root(args.repo_root, cwd=os.getcwd())` (validate defaults true) to honor the `--repo-root` override.

No environment variable feeds the Python scripts — they derive everything from `__file__` and cwd/git. `${CLAUDE_PLUGIN_ROOT}` is referenced only in the JS workflow's `ENGINE_ROOT` (Q1), never in the scripts.

**Evidence:**

```python
def engine_root():
    return os.path.dirname(os.path.abspath(__file__))

def resolve_repo_root(repo_root=None, cwd=None, validate=True):
    if repo_root:
        root = os.path.abspath(repo_root)
        if validate:
            _validate_root(root)
        return root
    common = _git_common_dir(cwd=cwd)
    if common:
        if validate:
            _validate_root(common)
        return common
    return os.path.dirname(engine_root())
```

— `scripts/qrspi_paths.py:47-143`

**Dependencies:** all 8 host-path scripts → `qrspi_paths` (sibling import); `_validate_root` → `gh repo view`; `_git_common_dir` → `git rev-parse --git-common-dir`.
**Implicit contracts:** A script's own `scripts/` dir must contain `qrspi_paths.py` (sibling-import contract). The host root is whatever git/gh resolves from cwd — NOT `__file__`'s parent unless git is unavailable. `validate=False` at import time keeps `gh` off the import path; validation happens in `main()`.

## Q3: What is the exact required and optional field set for `plugin.json` and `marketplace.json` as consumed by the Claude Code plugin loader, and where (if anywhere) is that schema documented in this repo?

**Answer:** NOT FOUND in this repo. There is no `plugin.json`, no `marketplace.json`, no `.claude-plugin/` directory anywhere under `REPO_ROOT` (verified: `ls .claude-plugin` → "No such file or directory"; `find` for those filenames returns only prior-ticket research/design prose under `.qrspi/RUS-*/`). The Claude Code plugin manifest schema is an external Claude Code platform contract not vendored or documented in this repo's source. The only in-repo discussion is design prose in prior tickets (`.qrspi/RUS-60/design.md:99-108` describes wiring the `linear` MCP server into a plugin via the normal MCP schema `command`/`args`/`env`/`cwd` with `${CLAUDE_PLUGIN_ROOT}`), but that is design narrative, not a manifest schema definition.

**Evidence:**

```
$ ls .claude-plugin → cannot access '.claude-plugin': No such file or directory
$ find . -name plugin.json -o -name marketplace.json → (only .qrspi/RUS-*/*.md prose hits)
```

— shell verification under `REPO_ROOT`

**Dependencies:** none in-repo.
**Implicit contracts:** The manifest schema must be sourced from external Claude Code plugin documentation; this repo offers no canonical field list.

## Q4: What is the current directory layout of `qrspi-*` skills, `qrspi-*` agents, `scripts/qrspi_*.py`, and the Linear `.mcp.json`, and what cross-references bind them together?

**Answer:** Layout (all under `REPO_ROOT`):

- `.claude/skills/` — 10 `qrspi-*` skill dirs, each a `SKILL.md` (with frontmatter): `qrspi-design`, `qrspi-implement`, `qrspi-plan`, `qrspi-pr`, `qrspi-questions`, `qrspi-research`, `qrspi-structure`, `qrspi-ticket`, `qrspi-work` (has a `references/` subdir), `qrspi-worktree`.
- `.claude/agents/` — 8 `qrspi-*.md` agent definitions: `qrspi-design`, `qrspi-implement`, `qrspi-plan`, `qrspi-pr`, `qrspi-questions`, `qrspi-research`, `qrspi-structure`, `qrspi-worktree`. (No `qrspi-ticket` or `qrspi-work` agent — those are skill-only.)
- `scripts/` — `qrspi_*.py` engine scripts + `qrspi_*_test.py` siblings + shared `qrspi_paths.py`; plus non-qrspi eval scripts (`grade.py`, `diagnose.py`, `run_eval.py`, etc.).
- `.mcp.json` — at repo root; binds server name `linear` → `https://mcp.linear.app/mcp` (http type).

Cross-references: skill SKILL.md frontmatter declares `allowed-tools`/`tools` (e.g. `qrspi-work` lists `mcp__linear__*` tools and `Agent`); skill prose invokes `scripts/qrspi_*.py` and references `.qrspi/<id>/*` artifact paths; the batch workflow invokes scripts via `engineCmd('scripts/...')` and points workers at `SKILL` (qrspi-work). Agents are spawned by the matching skill or by qrspi-work. The `linear` server name in `.mcp.json` is what makes `mcp__linear__*` tool names resolve.

**Evidence:**

```json
{ "mcpServers": { "linear": { "type": "http", "url": "https://mcp.linear.app/mcp" } } }
```

— `.mcp.json:1-9`

**Dependencies:** skills → agents (spawn) → scripts (Bash) → `.qrspi/` artifacts; all → `.mcp.json` `linear` binding for Linear tools.
**Implicit contracts:** Skill dir name must equal the skill/agent `name` frontmatter; `mcp__linear__*` tool names depend on the server being named exactly `linear`.

## Q5: Which skills and agents carry the `qrspi-*` prefix versus the `using-*`/`writing-*`/`aws-cli`/`atmos` (non-QRSPI) prefixes, so the move/exclude boundary is unambiguous?

**Answer:** Within `REPO_ROOT`, the move boundary is clean: **every** skill dir under `.claude/skills/` and **every** agent file under `.claude/agents/` carries the `qrspi-*` prefix (10 skills, 8 agents — enumerated in Q4). There are **no** `using-*`/`writing-*`/`aws-cli`/`atmos` skills or agents committed in this repo's `.claude/` tree. (Those non-QRSPI skill names appear in the runtime system-reminder skill catalog, which is host/global-plugin-provided, not under `REPO_ROOT`.) So the QRSPI-vs-non-QRSPI split is unambiguous in-repo: all `.claude/skills/qrspi-*` and `.claude/agents/qrspi-*` are in scope; nothing in those two dirs is out of scope by prefix.

**Evidence:**

```
.claude/skills/: qrspi-design qrspi-implement qrspi-plan qrspi-pr qrspi-questions
                 qrspi-research qrspi-structure qrspi-ticket qrspi-work qrspi-worktree
.claude/agents/: qrspi-{design,implement,plan,pr,questions,research,structure,worktree}.md
```

— directory listing under `REPO_ROOT/.claude/`

**Dependencies:** none.
**Implicit contracts:** Skill-only (no paired agent): `qrspi-ticket`, `qrspi-work`. The orchestrator skill `qrspi-work` spawns the 8 phase agents.

## Q6: How is `${CLAUDE_PLUGIN_ROOT}` populated at plugin load time, and do any current scripts assume the engine sits at the repo root or rely on cwd in a way that breaks once relocated under a plugin subtree?

**Answer:** `${CLAUDE_PLUGIN_ROOT}` population is an external Claude Code platform behavior (NOT FOUND in-repo — no code sets it; only `qrspi-batch.js:69` *reads* `process.env.CLAUDE_PLUGIN_ROOT`). Regarding relocation safety of the scripts:

- **Sibling imports are SAFE under relocation.** `qrspi_paths.engine_root()` and every consumer's `ENGINE_ROOT = os.path.dirname(os.path.abspath(__file__))` are `__file__`-derived, so they follow the script wherever it is installed (Q2). Sibling import `import qrspi_paths` works from a plugin subtree as long as `qrspi_paths.py` is a sibling.
- **Host paths are SAFE** because `resolve_repo_root()` resolves the host root from cwd/git-common-dir, explicitly decoupled from `__file__` (RUS-60 Decision 2). The git-common-dir-first precedence resolves the MAIN checkout even from a worktree.
- **The remaining cwd assumption is in `qrspi-work/SKILL.md` prose** (bare `python3 scripts/qrspi_resolve.py`, Q1), which assumes the worker's cwd is the engine root. That breaks if the engine relocates under a plugin subtree distinct from cwd. The scripts themselves do not have this problem.

Prior research (`.qrspi/RUS-60/research.md:230-256`) flagged that the OLD `qrspi_resolve.py` used `__file__`-only derivation with no git fallback — RUS-60/61 replaced that with `resolve_repo_root`, so that specific break is already fixed.

**Evidence:**

```python
ENGINE_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ENGINE_ROOT)
import qrspi_paths  # noqa: E402
REPO_ROOT = qrspi_paths.resolve_repo_root(cwd=os.getcwd(), validate=False)
```

— `scripts/qrspi_persist.py:45-50` (identical pattern in 7 other scripts)

**Dependencies:** scripts → `__file__` (engine) + cwd/git (host); SKILL.md prose → worker cwd.
**Implicit contracts:** `qrspi_paths.py` must remain a sibling of every consumer. The host repo must be a real git checkout discoverable from cwd (or `--repo-root` passed explicitly).

## Q7: Where does the Linear `.mcp.json` binding currently live and how is the server name `linear` referenced, so folding it into the plugin preserves the `mcp__linear__*` tool names?

**Answer:** The binding lives in `REPO_ROOT/.mcp.json` (project-scoped, committed). It maps the server key `"linear"` to the public HTTP endpoint `https://mcp.linear.app/mcp`, type `"http"`, no secrets. The server key `linear` is what generates the `mcp__linear__*` tool namespace. References to the name `linear`/`mcp__linear__`:

- `.mcp.json:3` — the server key itself.
- `.claude/CLAUDE.md` — prose documenting the `linear` binding and `mcp__linear__*` tools, and stating no per-user server name is hard-coded.
- `.claude/skills/qrspi-work/SKILL.md:6` — frontmatter `allowed-tools` lists `mcp__linear__get_issue`, `mcp__linear__save_issue`, `mcp__linear__list_issue_statuses`, `mcp__linear__save_comment`; skill prose calls `mcp__linear__get_issue` etc.
- `.claude/skills/qrspi-design/SKILL.md:6` and other phase skills — list `mcp__linear__get_issue`.
- `docs/qrspi_claude_code_guide.md` — references `.mcp.json`.

To preserve tool names when folding into a plugin, the server key must remain exactly `linear` (the `mcp__linear__*` names derive mechanically from it).

**Evidence:**

```json
"mcpServers": { "linear": { "type": "http", "url": "https://mcp.linear.app/mcp" } }
```

— `.mcp.json:2-7`

```
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, mcp__linear__get_issue,
  mcp__linear__save_issue, mcp__linear__list_issue_statuses, mcp__linear__save_comment
```

— `.claude/skills/qrspi-work/SKILL.md:6`

**Dependencies:** every Linear tool call → `linear` server key; CLAUDE.md + skill frontmatter document/declare it.
**Implicit contracts:** The server key string `linear` is the load-bearing identifier; changing it would break all `mcp__linear__*` references in skill frontmatter and prose.

## Q8: What sibling-import or relative-path assumptions do the `scripts/qrspi_*.py` files and their `_test.py` siblings make that would break when moved under a plugin `scripts/` directory?

**Answer:** Two assumption classes:

1. **Production scripts: SAFE.** Each does `ENGINE_ROOT = os.path.dirname(os.path.abspath(__file__))` + `sys.path.insert(0, ENGINE_ROOT)` + `import qrspi_paths` — a relocation-robust, `__file__`-relative sibling import. As long as the whole `scripts/` dir moves together (qrspi_paths.py stays a sibling), imports resolve. No script hard-codes an absolute `scripts/` path for imports.
2. **`_test.py` siblings: FRAGILE re: discovery, but self-correcting where they re-derive `__file__`.** Tests do bare `import qrspi_persist as qp` / `import qrspi_resolve` (no `sys.path.insert` in some, e.g. `qrspi_persist_test.py:8`), which relies on the test runner's cwd or sys.path already including the `scripts/` dir — i.e. they must be run *from* `scripts/` (or with `scripts/` on `PYTHONPATH`). `qrspi_paths_test.py:22-23` DOES insert `_HERE` first, so it is robust. The divergence-proving tests already assert engine-vs-host separation (e.g. `qrspi_resolve_test.py:155`, `qrspi_persist_test.py:38-40`).

So the move-under-plugin risk is concentrated in **test discovery/invocation cwd**, not in production import logic.

**Evidence:**

```python
import qrspi_persist as qp
...
engine_dir = os.path.dirname(os.path.abspath(qp.__file__))
self.assertNotEqual(host_root, os.path.dirname(engine_dir))
```

— `scripts/qrspi_persist_test.py:8,38-40` (bare import, no path insert)

```python
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
```

— `scripts/qrspi_paths_test.py:22-23` (robust)

**Dependencies:** tests → module-under-test as sibling on sys.path; production → `qrspi_paths` sibling.
**Implicit contracts:** Tests must be invoked with `scripts/` on the path (cwd=`scripts/` or `PYTHONPATH`). Moving the dir wholesale preserves production imports; test invocation cwd must move with it.

## Q9: Which references to the QRSPI block of `.claude/CLAUDE.md` exist (skills, agents, docs) that assume the host repo's CLAUDE.md owns that content, given the ticket states the host CLAUDE.md is not ours to own?

**Answer:** `.claude/CLAUDE.md` is the project-scoped instruction file holding the entire "QRSPI Workflow" narrative (Setup—Linear MCP, Lifecycle—PR-gated, Available skills, Workflow rules, Worktrees, Codebase conventions). It is loaded as project context. References/dependencies on its content:

- **`.claude/CLAUDE.md` top line** `@~/.agents/AGENTS.md` — imports the user's global instructions (an out-of-scope path, not read).
- **`docs/qrspi_claude_code_guide.md`** references `.mcp.json` and the workflow conventions (overlapping the CLAUDE.md narrative).
- The CLAUDE.md "Available skills" section enumerates `/qrspi-*` slash commands — i.e. the skills depend on CLAUDE.md to document/advertise them, and CLAUDE.md depends on the skills existing.
- No agent `.md` or skill `SKILL.md` *imports* `.claude/CLAUDE.md` by path; the dependency is implicit (CLAUDE.md is auto-injected project context describing the workflow the skills/agents implement). The "Codebase conventions" block documents `scripts/qrspi_*.py`, the resolver/persist Fix-A flow, reviewer resolution, etc. — content describing engine behavior that would need to migrate into plugin-owned instructions rather than host CLAUDE.md.

There is no mechanism that *reads* `.claude/CLAUDE.md` programmatically; the coupling is documentation ownership, not a code reference.

**Evidence:**

```
### Available skills (invoke with / or let Claude auto-invoke)
- `/qrspi-ticket <initial description>` — Create a Linear issue through guided conversation
- `/qrspi-questions <ticket-id>` — Generate technical questions from a ticket ...
```

— `.claude/CLAUDE.md` (Available skills section)

**Dependencies:** skills/agents ↔ CLAUDE.md (documentation), CLAUDE.md → `~/.agents/AGENTS.md` (out-of-scope import), `docs/qrspi_claude_code_guide.md` overlaps.
**Implicit contracts:** No code parses CLAUDE.md; migrating the QRSPI block to plugin-owned instructions is a documentation-ownership move, not a code-reference rewrite. The `@~/.agents/AGENTS.md` import is host-user-owned.

## Q10: Does any `qrspi_*` script or agent invoke `scripts/...` paths that the RUS-60 work already engine-root-prefixed, and are there any remaining bare `scripts/...` call sites not yet converted?

**Answer:** In `.claude/workflows/qrspi-batch.js`, RUS-60 already converted **all live invocations** to `engineCmd('scripts/...')` — 12 call sites (verified `grep -c "engineCmd('scripts" → 12`). The scripts invoked: `qrspi_persist.py`, `qrspi_resolve.py`, `qrspi_restack.py`, `qrspi_pr_body.py` (×2), `qrspi_revise_amend.py` (×2), `qrspi_comment_reply.py`, `qrspi_cleanup.py`, `qrspi_land_verify.py`, `qrspi_config.py`, `qrspi_order_tickets.py`. **Every remaining bare `scripts/qrspi_*.py` string in the file is a comment** (lines 30, 47, 59, 92, 388, 861, 1219), not an invocation — so there are zero un-converted live call sites in the workflow.

The **remaining bare call sites live in `.claude/skills/qrspi-work/SKILL.md`** (prose, Q1): `python3 scripts/qrspi_resolve.py`, `scripts/qrspi_pr_body.py`, `scripts/qrspi_comment_reply.py`, `scripts/qrspi_revise_amend.py`, `scripts/qrspi_cleanup.py`, plus `<repo-root>/scripts/qrspi_clear_stale_pr.py`. These were NOT engine-root-prefixed by RUS-60 (which scoped the workflow JS, not the SKILL prose). Python scripts do not invoke each other by `scripts/...` path at all (they sibling-import).

**Evidence:**

```js
python3 ${engineCmd('scripts/qrspi_persist.py')} --ticket ${id} --artifact ${name}
...
python3 ${engineCmd('scripts/qrspi_resolve.py')} --ticket ${t.id} ...
```

— `.claude/workflows/qrspi-batch.js:416,498` (representative of all 12)

**Dependencies:** workflow → `engineCmd`/`ENGINE_ROOT`; SKILL.md prose → cwd-relative `scripts/`.
**Implicit contracts:** Workflow invocations survive engine relocation; SKILL.md prose does not (still cwd-relative or `<repo-root>`-templated).

## Q11: How are the `scripts/qrspi_*_test.py` unit tests currently discovered and run (path assumptions, `python3` invocation), and what would they need to resolve correctly from a plugin `scripts/` location?

**Answer:** Tests are stdlib `unittest`-based (`import unittest`; `unittest.main()` under `if __name__ == "__main__"`). Per the convention in `.claude/CLAUDE.md`, they are "stdlib-only unit tests as `_test.py` siblings (`scripts/qrspi_*_test.py`, run with `python3`)." There is **no CI config** (`ls .github/workflows` → not found) and **no dedicated test runner/discovery script** for the qrspi tests; they are run directly, e.g. `python3 scripts/qrspi_persist_test.py` or `python3 -m unittest` from `scripts/`. They import the module under test as a bare sibling (`import qrspi_persist as qp` — `qrspi_persist_test.py:8`), so they require the `scripts/` dir on `sys.path` (achieved by cwd=`scripts/`, or running the file by path so Python adds its dir to `sys.path[0]`). `qrspi_paths_test.py` additionally does `sys.path.insert(0, _HERE)` for robustness.

To resolve from a plugin `scripts/` location, nothing in the test logic changes (imports are `__file__`/cwd-relative); the **invocation cwd** must be the plugin's `scripts/` dir (or that dir on `PYTHONPATH`). No path is hard-coded to the current repo location.

**Evidence:**

```python
import unittest
...
if __name__ == "__main__":
    unittest.main()
```

— `scripts/qrspi_persist_test.py:6,103-104` (pattern shared across all `_test.py`)

**Dependencies:** tests → `python3` + `unittest` (stdlib) + sibling module on sys.path.
**Implicit contracts:** Run from `scripts/` (or with it on `PYTHONPATH`); no external test framework, no CI. The eval-suite scripts (`run_eval.py`, `grade.py`) are separate (Q12).

## Q12: Is there an existing dev-install or `--plugin-dir` verification path in the repo, and what does the `evals/`/`scripts/run_eval.py` placeholder currently cover versus leave unverified?

**Answer:** NO dev-install or `--plugin-dir` verification path exists in-repo (no `.claude-plugin/`, no install script, no e2e harness for plugin install — verified Q3). Per `.claude/CLAUDE.md` "Codebase conventions": "The `evals/` + `scripts/run_eval.py` harness is a **non-functional placeholder** — verify pure logic with the unit tests and orchestration changes with manual end-to-end runs." `scripts/run_eval.py` is structured (dataclasses `ExecutionResult`/`EvalConfig`, `load_suite`, a `_execute` path that sets `executed=True` and is stubbed offline in tests — `run_eval.py:112,165-195`), but it is the placeholder eval-suite runner, not a plugin-install verifier. So: **covered** = pure logic via stdlib unit tests (`qrspi_*_test.py`); **left unverified** = end-to-end plugin install into a foreign repo, the read-only-`${CLAUDE_PLUGIN_ROOT}` write-target risk (prior tickets defer this to a "sub-ticket 4 dogfood install" — `.qrspi/RUS-60/pr-summary.md:112`), and any `--plugin-dir` flow.

**Evidence:**

```python
result.executed = True
...
result.executed = False
```

— `scripts/run_eval.py:191,195` (stubbed offline in tests)

> The `evals/` + `scripts/run_eval.py` harness is a **non-functional placeholder**

— `.claude/CLAUDE.md` (Codebase conventions)

**Dependencies:** run_eval.py → (optional SDK, stubbed); unit tests → stdlib only.
**Implicit contracts:** Logic correctness is the unit tests' job; orchestration/plugin-install correctness is verified only by manual e2e runs, which do not yet exist for plugin install.

## Q13: How do the `qrspi_*` scripts currently signal failure (exit codes, stderr messages, fail-loud aborts), so a misresolved `${CLAUDE_PLUGIN_ROOT}` or missing bundled script surfaces a clear error rather than a silent path-mangle?

**Answer:** Two layered mechanisms:

1. **Structured JSON envelope + exit code.** Scripts emit a JSON envelope to stdout with `"ok": bool` and (on failure) `"error": "<Type>: <msg>"`, and `return 0 if ok else 1`. `qrspi_resolve.py:402-415` wraps the whole `main()` body in `try/except Exception` and emits ONE `ok:false` envelope with the verbatim `"%s: %s" % (type(exc).__name__, exc)` — explicitly "never partial-retry: a clean stop is what keeps a weak model from spiralling." `qrspi_persist.py:119-133` returns `(bytes, error)` and emits `ok:false` + `error` on a missing/empty staged file ("staged artifact not found or unreadable: ...", "staged artifact is empty: ...").
2. **Fail-loud host-root validation.** `qrspi_paths._validate_root` raises `HostRootError` when a supplied/auto-detected root fails `gh repo view` (stale `--repo-root` or wrong cwd surfaces as an exception, not silent wrong-repo operation — `qrspi_paths.py:81-108`). This propagates into the calling script's `try/except` and becomes an `ok:false` envelope.

A **missing bundled script** itself surfaces at the OS level: `engineCmd` produces an absolute path; `python3 <missing>` exits non-zero with a "No such file or directory" stderr — caught by the batch's per-phase success gate (`runPhase`). A **missing sibling** (`qrspi_paths.py`) surfaces as an `ImportError` at module load (before `main`'s try/except), which is a hard non-zero exit. The token-free staging path (`STAGE_ROOT = "/tmp/phase-stage"`, no `qrspi` token) is the deliberate defense against the silent path-mangle the persist Fix-A addressed.

**Evidence:**

```python
except Exception as exc:  # noqa: BLE001 - any failure is reported, not retried
    err_root = os.path.abspath(args.repo_root) if args.repo_root else REPO_ROOT
    worktree = os.path.join(err_root, ".worktrees", args.ticket)
    env = build_envelope(..., ok=False, error="%s: %s" % (type(exc).__name__, exc), ...)
json.dump(env, sys.stdout, indent=2); print()
return 0 if env["ok"] else 1
```

— `scripts/qrspi_resolve.py:402-415`

```python
raise HostRootError(
    "host root %r failed gh repo view validation: %s" % (candidate, msg))
```

— `scripts/qrspi_paths.py:101-103`

**Dependencies:** scripts → JSON envelope contract consumed by `qrspi-batch.js` (`parseResolveEnvelope`, `runPhase` gate); `_validate_root` → `gh`.
**Implicit contracts:** ok/error envelope + exit-code-1 is the universal failure signal; any uncaught exception (ImportError on a missing sibling, OSError on a missing script) is a hard non-zero exit. No script silently continues on a bad path.

---

## Discovered Patterns

- **Uniform engine/host-root split (RUS-60/61, already shipped).** All 8 host-path scripts share the exact idiom: `ENGINE_ROOT = os.path.dirname(os.path.abspath(__file__))` → `sys.path.insert(0, ENGINE_ROOT)` → `import qrspi_paths` → `REPO_ROOT = qrspi_paths.resolve_repo_root(cwd=os.getcwd(), validate=False)`, then re-resolve with `--repo-root` honored in `main()`. The plugin-relocation groundwork is substantially done at the script layer.
- **`${CLAUDE_PLUGIN_ROOT}` is wired as first-precedence but inert.** Only `qrspi-batch.js:69` reads it; with no plugin install it falls through to `process.cwd()`. The workflow is already plugin-ready (12 `engineCmd` invocations); the scripts derive engine location from `__file__` independently.
- **JSON-envelope `{ok, error, ...}` + exit code is the universal script→orchestrator contract.** Every orchestration script (`qrspi_resolve`, `qrspi_persist`, `qrspi_cleanup`, `qrspi_restack`, `qrspi_revise_amend`, `qrspi_pr_body`, `qrspi_clear_stale_pr`) emits it; the batch parses/gates on it.
- **Fail-loud over silent-wrong.** `HostRootError` via `gh repo view`, token-free staging (`/tmp/phase-stage`), single `ok:false` envelope with no partial-retry — all deliberate defenses against a weak worker model silently corrupting paths or operating on the wrong repo.
- **Stdlib-only `unittest` tests, no CI.** Every `qrspi_*` script has a `_test.py` sibling run directly with `python3`; there is no `.github/workflows`, no pytest, no test-runner script.
- **Clean qrspi-* prefix boundary in-repo.** All `.claude/skills/` and `.claude/agents/` entries are `qrspi-*`; no `using-*`/`writing-*`/`aws-cli`/`atmos` are committed here (they are host/global-plugin runtime context).

## Inconsistencies

- **Workflow JS is engine-root-prefixed; the SKILL.md prose it points workers at is NOT.** `qrspi-batch.js` runs scripts via `engineCmd('scripts/...')` (relocation-safe), but `.claude/skills/qrspi-work/SKILL.md` still embeds bare `python3 scripts/qrspi_*.py` (and some `<repo-root>/scripts/...`) that assume cwd == engine root. A plugin relocation would break the SKILL-driven invocations while the batch-driven ones survive. (Q1/Q10)
- **`qrspi_cleanup.py` module docstring is stale vs. code.** `qrspi_cleanup.py:14` says "Self-locating: REPO_ROOT is derived from `__file__` (two levels up)", but the code (line 58) actually derives `REPO_ROOT` from `qrspi_paths.resolve_repo_root(cwd=os.getcwd())` (git-common-dir first, `__file__` only as last-resort fallback). The docstring predates the RUS-60/61 decoupling. (Q2)
- **Test sibling-import robustness is inconsistent.** `qrspi_paths_test.py` does `sys.path.insert(0, _HERE)` before importing; `qrspi_persist_test.py` (and others) rely on a bare `import qrspi_persist` with no path insert, so they depend on invocation cwd/`PYTHONPATH` including `scripts/`. Same test suite, two discovery assumptions. (Q8/Q11)
- **Plugin manifest schema is undocumented in-repo while design prose assumes it.** `.qrspi/RUS-60/design.md` discusses wiring the `linear` MCP server and `${CLAUDE_PLUGIN_ROOT}` carriage into a plugin, but no `plugin.json`/`marketplace.json`/`.claude-plugin/` or field-schema documentation exists, so the manifest contract is asserted in narrative without a vendored definition. (Q3/Q12)
