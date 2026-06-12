# Questions — Scaffold the QRSPI plugin package and marketplace

**Ticket:** RUS-62
**Generated:** 2026-06-12T00:00:00Z
**Status:** draft

## Data Flow

- Q1: Which engine-code files currently reference `scripts/qrspi_*.py` paths, and through what mechanism (shell invocation, constant, heredoc) is each path constructed, so every reference can be rewritten to `${CLAUDE_PLUGIN_ROOT}/scripts/...`?
  **Target:** `scripts/qrspi_*.py`, `.claude/skills/`, `.claude/agents/`, and `.claude/workflows/qrspi-batch.js`
- Q2: How does the engine currently locate its own root and the target repo root (per the RUS-61 decoupling), and which functions or env vars supply those paths to the bundled scripts?
  **Target:** `scripts/qrspi_resolve.py`, `scripts/qrspi_persist.py`, and the shared resolver introduced by RUS-60/RUS-61

## API Surface

- Q3: What is the exact required and optional field set for `plugin.json` and `marketplace.json` as consumed by the Claude Code plugin loader, and where (if anywhere) is that schema documented in this repo?
  **Target:** the module/docs responsible for Claude Code plugin manifest definitions
- Q4: What is the current directory layout of `qrspi-*` skills, `qrspi-*` agents, `scripts/qrspi_*.py`, and the Linear `.mcp.json`, and what cross-references (relative paths, frontmatter, imports) bind them together?
  **Target:** `.claude/skills/`, `.claude/agents/`, `scripts/`, and `.mcp.json`
- Q5: Which skills and agents carry the `qrspi-*` prefix versus the `using-*`/`writing-*`/`aws-cli`/`atmos` (non-QRSPI) prefixes, so the move/exclude boundary is unambiguous?
  **Target:** `.claude/skills/` and `.claude/agents/` directory listings

## State Management

- Q6: How is `${CLAUDE_PLUGIN_ROOT}` populated at plugin load time, and do any current scripts assume the engine sits at the repo root or rely on cwd in a way that breaks once relocated under a plugin subtree?
  **Target:** `scripts/qrspi_resolve.py` and `scripts/qrspi_persist.py` (their self-location logic)
- Q7: Where does the Linear `.mcp.json` binding currently live and how is the server name `linear` referenced, so folding it into the plugin preserves the `mcp__linear__*` tool names?
  **Target:** `.mcp.json` and any file referencing `mcp__linear__`

## Edge Cases

- Q8: What sibling-import or relative-path assumptions do the `scripts/qrspi_*.py` files and their `_test.py` siblings make that would break when moved under a plugin `scripts/` directory?
  **Target:** `scripts/qrspi_*.py` and `scripts/qrspi_*_test.py`
- Q9: Which references to the QRSPI block of `.claude/CLAUDE.md` exist (skills, agents, docs) that assume the host repo's CLAUDE.md owns that content, given the ticket states the host CLAUDE.md is not ours to own?
  **Target:** `.claude/CLAUDE.md` and the skills/agents that depend on its QRSPI context
- Q10: Does any `qrspi_*` script or agent invoke `scripts/...` paths that the RUS-60 work already engine-root-prefixed, and are there any remaining bare `scripts/...` call sites not yet converted?
  **Target:** `.claude/workflows/qrspi-batch.js` (the `SKILL` constant and `scripts/...` invocations)

## Testing

- Q11: How are the `scripts/qrspi_*_test.py` unit tests currently discovered and run (path assumptions, `python3` invocation), and what would they need to resolve correctly from a plugin `scripts/` location?
  **Target:** `scripts/qrspi_*_test.py` and any test runner or CI config invoking them
- Q12: Is there an existing dev-install or `--plugin-dir` verification path in the repo, and what does the `evals/`/`scripts/run_eval.py` placeholder currently cover versus leave unverified?
  **Target:** `scripts/run_eval.py` and the `evals/` harness

## Observability

- Q13: How do the `qrspi_*` scripts currently signal failure (exit codes, stderr messages, fail-loud aborts), so a misresolved `${CLAUDE_PLUGIN_ROOT}` or missing bundled script surfaces a clear error rather than a silent path-mangle?
  **Target:** `scripts/qrspi_resolve.py`, `scripts/qrspi_persist.py`, and their error-handling paths
