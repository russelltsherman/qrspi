# Questions — Decouple QRSPI engine location from the target repo

**Ticket:** RUS-61
**Generated:** 2026-06-10T00:00:00Z
**Status:** draft

## Data Flow

- Q1: How does `scripts/qrspi_resolve.py` currently derive the repo root from `__file__` (the `_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))` "two levels up" computation at line ~40), and what downstream values (OWNER/REPO, worktree path, artifact paths) are computed from that derived root?
  **Target:** `scripts/qrspi_resolve.py`
- Q2: Which `qrspi_*.py` scripts compute the repo root from their own file location versus receiving it as an input, across `qrspi_persist.py`, `qrspi_pr_body.py`, `qrspi_revise_amend.py`, `qrspi_clear_stale_pr.py`, `qrspi_cleanup.py`, and `qrspi_restack.py`?
  **Target:** the `scripts/qrspi_*.py` modules that locate the repo
- Q3: How does the resolver envelope produced by `qrspi_resolve.py` carry the repo root to callers — specifically what is the `repoRoot` field, and where is `${r.repoRoot}` consumed in `.claude/workflows/qrspi-batch.js`?
  **Target:** `scripts/qrspi_resolve.py` and `.claude/workflows/qrspi-batch.js`

## API Surface

- Q4: What command-line arguments does each affected `qrspi_*.py` script currently accept, and do any already expose a `--repo-root` (or equivalent) flag that the new explicit-override mechanism could extend?
  **Target:** the argument-parsing sections of `scripts/qrspi_*.py`
- Q5: How do `.claude/skills/qrspi-*` and `.claude/agents/qrspi-*` currently invoke the scripts — what literal invocation strings (`scripts/qrspi_*.py`, `${r.repoRoot}/scripts/...`) appear, and are paths relative to cwd or absolute?
  **Target:** `.claude/skills/qrspi-*` and `.claude/agents/qrspi-*`
- Q6: Is `${CLAUDE_PLUGIN_ROOT}` referenced anywhere in the current codebase (scripts, skills, agents, or `qrspi-batch.js`), and what environment variables do the scripts already read?
  **Target:** the `scripts/`, `.claude/skills/qrspi-*`, `.claude/agents/qrspi-*`, and `.claude/workflows/qrspi-batch.js` trees

## State Management

- Q7: How is the per-ticket worktree path (`.worktrees/<id>/`) constructed and where is it rooted today — relative to the self-located repo root, and which scripts read or write under it?
  **Target:** the module responsible for worktree setup in `scripts/qrspi_resolve.py`
- Q8: Where does `qrspi_persist.py` resolve the canonical artifact destination (`.worktrees/<id>/.qrspi/<id>/`), and does that destination derive from the engine's `__file__` root or from the target repo?
  **Target:** `scripts/qrspi_persist.py`

## Edge Cases

- Q9: What happens in each affected script when `git rev-parse --show-toplevel` from cwd fails or returns a non-zero exit (e.g., cwd is not inside a git repo)? Is there any existing error handling for a missing repo root?
  **Target:** the repo-discovery code paths in `scripts/qrspi_*.py`
- Q10: In dev mode, where the engine checkout *is* the target repo (engine == repo), what current behavior would the new discovery mechanism need to preserve, and how is "running from a checkout" distinguishable from "running as an installed plugin"?
  **Target:** `scripts/qrspi_resolve.py` and peer self-locating scripts
- Q11: How do callers in `qrspi-batch.js` currently establish cwd before invoking the scripts, and could a discrepancy between the JS process cwd and the spawned script's cwd cause `git rev-parse --show-toplevel` to resolve a different repo than intended?
  **Target:** `.claude/workflows/qrspi-batch.js`

## Testing

- Q12: What patterns do the existing `scripts/qrspi_*_test.py` stdlib-only tests use to construct fixtures (temp dirs, fake repo roots, monkeypatching `__file__` or cwd), so new tests can cover engine-dir ≠ target-repo, git discovery, `--repo-root` override, and dev fallback?
  **Target:** the `scripts/qrspi_*_test.py` sibling test files
- Q13: How are the pure repo-root-derivation helpers currently factored within each script — are they isolated functions that can be unit-tested directly, or inlined into `main`/argument handling?
  **Target:** the repo-location helper functions across `scripts/qrspi_*.py`

## Observability

- Q14: What does each affected script log or emit (stderr messages, envelope fields, exit codes) when it resolves the repo root, so a manual run from a path *outside* this repo can be verified to have discovered the correct target?
  **Target:** the logging/output paths of `scripts/qrspi_resolve.py` and peer scripts
