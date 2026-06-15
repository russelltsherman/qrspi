# Questions — Critic effectiveness: instrumentation, cost reduction, and teeth eval

**Ticket:** RUS-78
**Generated:** 2026-06-15T00:00:00Z
**Status:** draft

## Data Flow

- Q1: What fields does each critic/synthesize verdict currently write into `journal.jsonl`, and is critic type/lens, phase, ticket, round, pass/fail, and findings-count already present or partially derivable from the existing records?
  **Target:** the module responsible for emitting verdicts to `journal.jsonl` (the critic loops in `.claude/workflows/qrspi-batch.js`)

- Q2: How does the design panel currently supply `research.md` to each of the 4 lenses — is the full file inlined into every lens prompt, and where is that read/splice performed?
  **Target:** the design-panel critic invocation region in `.claude/workflows/qrspi-batch.js` and the `qrspi-design-critic-*` agent prompts in `.claude/agents/`

## API Surface

- Q3: What is the current schema of the `critics` block in `.qrspi/config.json` (and `.qrspi/config.example.json`), and which keys does the critic loop already read from it?
  **Target:** the `critics` config block in `.qrspi/config.json` / `.qrspi/config.example.json` and its reader in the critic loop

- Q4: How does the config reader expose nested values today — does it support reading sub-keys under `critics`, or only single top-level string keys (per `scripts/qrspi_config.py` / the JS `parseConfigEnvelope`)?
  **Target:** `scripts/qrspi_config.py` and the JS config-parsing helper in `.claude/workflows/qrspi-batch.js`

- Q5: What invocation interface do the existing edge critic, 4-lens design panel, per-slice edge critic, and whole-stack coherence critic share — how are they spawned and how is model selection passed (if at all) per critic?
  **Target:** `runCriticLoop` and the critic-spawning helpers in `.claude/workflows/qrspi-batch.js`

## State Management

- Q6: Where and how is the per-run round/iteration state for the critic loop tracked, and how would a summarizer scope verdicts to a single run vs. across runs when reading `journal.jsonl`?
  **Target:** the critic-loop state handling in `.claude/workflows/qrspi-batch.js` and the `journal.jsonl` record structure

- Q7: How is `critic-synthesize` wired relative to the individual lenses — does it consume the lens verdicts as input, and what does it write back as the panel's combined verdict?
  **Target:** the `critic-synthesize` step in the design panel region of `.claude/workflows/qrspi-batch.js`

## Edge Cases

- Q8: How does the critic loop currently behave when a lens returns `pass=false` with findings — does it trigger an artifact-change round, and where is the dissent→artifact-change transition recorded so a summarizer can compute that rate?
  **Target:** the fail/findings branch of `runCriticLoop` in `.claude/workflows/qrspi-batch.js`

- Q9: What happens if a critic invocation fails to produce a parseable verdict or the `journal.jsonl` write fails mid-run — is the loop fail-closed, and would a partial/corrupt record break the proposed summarizer?
  **Target:** the verdict-parsing and journal-write error handling in `.claude/workflows/qrspi-batch.js`

- Q10: How does the design panel currently determine which lenses are "relevant" to a given artifact, since the teeth eval must assert each *relevant* lens returns `pass=false`?
  **Target:** the lens-selection logic in the design panel region of `.claude/workflows/qrspi-batch.js` and the `qrspi-design-critic-*` prompts

## Testing

- Q11: What pattern do existing `scripts/*_test.py` use for components that touch LLM agents vs. pure logic, and is there any existing seam (e.g., the `evals/` + `scripts/run_eval.py` placeholder) that an opt-in teeth eval would attach to?
  **Target:** `scripts/run_tests.py`, the `scripts/*_test.py` siblings, and `evals/` + `scripts/run_eval.py`

- Q12: Is any part of the critic verdict path (parsing, journal record shape, base-rate computation) deterministic enough to cover with a stdlib unit test, separate from the non-deterministic agent spawning?
  **Target:** the verdict-parsing / record-construction functions in `.claude/workflows/qrspi-batch.js` and any Python helper they delegate to

## Observability

- Q13: What is the exact on-disk location, format, and append/rotation behavior of `journal.jsonl`, and does it already capture token-cost data per critic invocation that the summarizer could report alongside dissent rate?
  **Target:** the module responsible for writing `journal.jsonl` and the journal file path resolution in `.claude/workflows/qrspi-batch.js`

- Q14: How is subagent token consumption currently surfaced or attributed per critic invocation (the ~749K-token figure cited for the first RUS-76 run) — is it captured anywhere queryable, or only observable externally?
  **Target:** the subagent-spawning and any token/usage accounting in `.claude/workflows/qrspi-batch.js`
