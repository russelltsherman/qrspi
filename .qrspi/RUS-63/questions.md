# Questions — Ship the qrspi-batch workflow under the plugin

**Ticket:** RUS-63
**Generated:** 2026-06-12T00:00:00Z
**Status:** draft

## Data Flow

- Q1: What inputs does `qrspi-batch.js` read at startup (project scope, config, env vars) and where do those values originate today?
  **Target:** `.claude/workflows/qrspi-batch.js`
- Q2: How does the batch workflow currently locate and invoke the `scripts/qrspi_*.py` engine scripts, and what path assumptions (cwd-relative, repo-root-relative) does each invocation make?
  **Target:** `.claude/workflows/qrspi-batch.js` and `scripts/qrspi_resolve.py`
- Q3: How is the target repository discovered today versus the decoupled discovery mechanism introduced by RUS-61, and which of the two does the workflow currently consume?
  **Target:** the module responsible for target-repo discovery (RUS-61 mechanism)

## API Surface

- Q4: What does the Claude Code plugin manifest support as component types, and which directory/manifest fields declare skills, commands, agents, hooks, and supporting files?
  **Target:** the plugin manifest schema / plugin packaging configuration
- Q5: How do existing skills in this repo reference `${CLAUDE_PLUGIN_ROOT}` (or an equivalent engine-root variable), and is that variable already resolved anywhere in the engine scripts?
  **Target:** `.claude/skills/` and the engine-root resolution helper referenced by `scripts/qrspi_*.py`
- Q6: What is the contract by which the Workflow tool loads `.claude/workflows/qrspi-batch.js` — what host-side path must the file occupy for the tool to find it?
  **Target:** `.claude/workflows/qrspi-batch.js` and its loading convention

## State Management

- Q7: Where does the engine root resolve from within `scripts/qrspi_resolve.py` and its siblings (self-location from their own path), and how does that interact with the engine living at `${CLAUDE_PLUGIN_ROOT}` after a plugin install?
  **Target:** `scripts/qrspi_resolve.py`, `scripts/qrspi_persist.py` (self-locating helpers)
- Q8: What persists in the host's `.claude/workflows/` directory across the workflow's lifecycle, and is there any existing version or staleness marker the engine writes or reads?
  **Target:** the module responsible for writing host-side `.claude/` artifacts

## Edge Cases

- Q9: What happens when `${CLAUDE_PLUGIN_ROOT}` changes on a plugin update — does any current code re-resolve engine script paths, or would already-synced copies become stale?
  **Target:** `.claude/workflows/qrspi-batch.js` and the engine-root resolution path
- Q10: How does the batch workflow behave when an engine script referenced by an absolute or cwd-relative path is missing — does it fail loud or silently skip?
  **Target:** `.claude/workflows/qrspi-batch.js` (script invocation error handling)
- Q11: What does the workflow do when run in a host repo that is not the engine repo (no `scripts/qrspi_*.py` present locally) — which paths currently break?
  **Target:** `.claude/workflows/qrspi-batch.js` and `scripts/qrspi_resolve.py`

## Testing

- Q12: What test coverage exists for the batch workflow and the engine scripts' path resolution, and are any of those tests cwd-dependent in a way that would mask a plugin-relative path change?
  **Target:** `scripts/qrspi_*_test.py` and any tests covering `qrspi-batch.js`
- Q13: How are orchestration changes to `qrspi-batch.js` verified today given the `evals/` harness is a non-functional placeholder?
  **Target:** `scripts/run_eval.py`, `evals/`, and the manual end-to-end verification path

## Observability

- Q14: What does `qrspi-batch.js` emit (logs, per-ticket status, decision envelope output) that would let an operator confirm phase agents dispatched correctly in a host repo, and where is that output written?
  **Target:** `.claude/workflows/qrspi-batch.js` (logging / status reporting)
