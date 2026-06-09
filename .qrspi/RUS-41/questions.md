# Questions — Build multi-agent eval driver

**Ticket:** RUS-41
**Generated:** 2026-06-09T00:00:00Z
**Status:** draft

## Data Flow

- Q1: What inputs does `run_loop.sh` accept (agent name, flags, environment variables) and how does it pass them to the underlying eval invocation that the wrapper must iterate over?
  **Target:** `run_loop.sh`
- Q2: How does the existing single-agent eval path locate and load fixtures, and what is the file/path contract the per-agent runs depend on?
  **Target:** the module responsible for fixture loading (`scripts/run_eval.py` / `evals/`)
- Q3: What is the structure and on-disk format of the per-agent result output that the consolidated `results/all/` report must aggregate from?
  **Target:** `scripts/run_eval.py` and any existing `results/` output directory

## API Surface

- Q4: What command-line interface does `run_loop.sh` currently expose, and which flags or positional arguments identify the target agent that `--phase <name>` must map onto?
  **Target:** `run_loop.sh`
- Q5: How are the 8 phase agents discovered on disk, and what is the exact glob pattern and naming convention for `.claude/agents/qrspi-*.md` that `--all` must enumerate?
  **Target:** `.claude/agents/` directory and `run_loop.sh`
- Q6: What exit-code conventions does the existing eval runner use to signal pass versus regression, which `--regression-only` CI mode must propagate non-zero on?
  **Target:** `scripts/run_eval.py` / `run_loop.sh`

## State Management

- Q7: How does the current eval flow distinguish a regression iteration from a revision iteration, given that `--regression-only` must skip the revision step?
  **Target:** `run_loop.sh` and `scripts/run_eval.py`
- Q8: Where are per-phase scores recorded and how would the wrapper accumulate them into a top-level summary without overwriting individual phase results under `results/all/`?
  **Target:** the module responsible for writing eval results

## Edge Cases

- Q9: What happens in the current single-agent path when an agent run fails, produces no score, or times out — and how is that failure surfaced versus a legitimate low score?
  **Target:** `scripts/run_eval.py` / `run_loop.sh`
- Q10: How does the existing runner behave when a fixture is missing or malformed for a given phase agent, which the iterating wrapper would encounter across all 8 agents?
  **Target:** the module responsible for fixture loading
- Q11: What is the current behavior when `results/` (or a target output subdirectory) already exists or is partially written from a prior run, which `--all` would re-enter for `results/all/`?
  **Target:** the module responsible for writing eval results

## Testing

- Q12: What testing convention do the existing `scripts/qrspi_*_test.py` siblings follow (stdlib-only, `python3`-run) that a new `eval_all` implementation would need matching unit tests under?
  **Target:** `scripts/qrspi_*_test.py`
- Q13: Is there an existing end-to-end or smoke test that exercises `run_loop.sh` against a single agent that the multi-agent wrapper could be validated against?
  **Target:** `evals/` and `scripts/`

## Observability

- Q14: How does the current eval runner emit progress and score output (stdout format, log lines, summary block) that the consolidated report must reproduce per-phase and at suite level?
  **Target:** `scripts/run_eval.py` / `run_loop.sh`
- Q15: What mechanism, if any, currently distinguishes a phase-level signal from a suite-level signal in the runner's output, which the report must use to separate phase-level from suite-level regressions?
  **Target:** the module responsible for writing eval results
