# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-15T00:00:00Z
**Generated:** 2026-06-15T00:00:00Z
**Status:** draft

> CRITICAL CROSS-CUTTING FINDING (affects Q1, Q6, Q13): **There is no file named
> `journal.jsonl` anywhere in the repo.** A repo-wide search for `journal.jsonl`
> matches only `questions.md` itself. The durable per-run critic verdict store is
> `.worktrees/<id>/.qrspi/<id>/critic-metrics.jsonl` (one JSON line per terminated
> critic step), written by `scripts/qrspi_metrics_append.py`. Questions that name
> `journal.jsonl` are answered against this actual ledger.

## Q1: What fields does each critic/synthesize verdict currently write into `journal.jsonl`, and is critic type/lens, phase, ticket, round, pass/fail, and findings-count already present or partially derivable from the existing records?

**Answer:** No `journal.jsonl` exists. The durable store is the per-ticket
**`critic-metrics.jsonl` ledger**. It does NOT store raw critic/synthesize verdicts;
it stores one reduced `CriticMetricsLedgerLine` per *terminated critic step* (one
edge-critic loop OR one panel loop). The line shape is the `CriticStepMetrics` record
(`scripts/qrspi_critic_metrics.py:build_record`) wrapped by the appender envelope:
`{ phase, rounds:[{lens, pass, findingsCount}], terminalAction, tokensIn?, tokensOut?,
ticketId, timestamp }`.

- **phase** — present (e.g. `"design"`, `"research"`); passed via `--phase`.
- **lens** — present per round element. `null` for single-edge critics
  (`runCriticLoop` pushes `{ lens: null, … }`, qrspi-batch.js:743); the lens id
  (e.g. `"completeness"`) for panel rounds (qrspi-batch.js:904).
- **ticket** — present as `ticketId`, injected by the appender (`wrap_envelope`,
  qrspi_metrics_append.py:67-76).
- **round** — NOT stored as an explicit index. It is **derivable from array position**
  in `rounds[]` (one entry per lens per round, appended in order).
- **pass/fail** — present per round (`pass` bool).
- **findings-count** — present per round as `findingsCount` (derived in Python from
  `len(findings)`, never carries finding text).
- **critic type** — NOT a distinct field; inferable from `lens` (null ⇒ single edge
  critic; non-null ⇒ design panel lens).
- **terminalAction** — present: one of `converged|cap_reached|exhausted|aborted`.
- **tokensIn/tokensOut** — schema-OPTIONAL and **never populated in the live path**
  (see Q14).

**Evidence:**

```python
record = {
    "phase": phase,
    "rounds": rounds,           # [{lens, pass, findingsCount}, ...]
    "terminalAction": terminalAction,
}
if usage:
    if usage.get("tokensIn") is not None:  record["tokensIn"]  = usage["tokensIn"]
    if usage.get("tokensOut") is not None: record["tokensOut"] = usage["tokensOut"]
```

— `scripts/qrspi_critic_metrics.py:89-102`

```python
def wrap_envelope(record, ticket, timestamp):
    line = dict(record)
    line["ticketId"]  = ticket
    line["timestamp"] = timestamp
    return line
```

— `scripts/qrspi_metrics_append.py:67-76`

**Dependencies:** Producer chain is `runCriticLoop`/`runCriticPanelLoop` (JS,
qrspi-batch.js) → `recordCriticMetrics` (qrspi-batch.js:1062) → `qrspi_critic_metrics.py`
(reducer) → `qrspi_metrics_append.py` (envelope + append). The synthesize verdict
(`qrspi_critic_synthesize.py`) is reduced into the round-level `pass`/`findingsCount`
*before* it reaches the ledger; the synthesize output itself is NOT persisted.
**Implicit contracts:** `findingsCount` is computed in Python only (never in JS).
`revise` is deliberately NOT a `terminalAction` (it is mid-loop). `tokensIn/Out` keys
are omitted entirely (not null) when unmeasured. One ledger line == one terminated step.

## Q2: How does the design panel currently supply `research.md` to each of the 4 lenses — is the full file inlined into every lens prompt, and where is that read/splice performed?

**Answer:** Research is supplied **by absolute PATH, not inlined**. Each lens is spawned
with `RESEARCH_PATH = <abs path to research.md>` in its prompt and the lens agent itself
Reads the file (the lens agents have the `Read` tool). The path is set in `doDesign`
(`upstreamPath: art(wd, t.id, 'research.md')`, qrspi-batch.js:1707) and threaded into the
per-lens prompt in `runCriticPanelLoop` (qrspi-batch.js:872). All four lenses receive the
identical input set and each re-reads the full file independently — i.e. research.md is
read **N times (once per lens) per round**, which is the measured cost driver the RUS-77
digest lever targets.

**Evidence:**

```javascript
const verdict = await agent(
  `You are the ${lens} lens ... round ${round + 1}/${maxRounds}.
DESIGN_PATH = ${artifactPath}
TICKET_CONTENT_PATH = ${ticketContentPath}
RESEARCH_PATH = ${researchPath}
QUESTIONS_PATH = ${questionsPath}${digestLine}
Read all four paths and judge DESIGN_PATH through your lens. Return { pass, findings } ...`,
  agentOpts
)
```

— `.claude/workflows/qrspi-batch.js:868-876`

The lens agent prompt confirms it Reads the path itself: "Read `TICKET_CONTENT_PATH`,
the research input (`DIGEST_PATH` if it was provided, otherwise `RESEARCH_PATH`) ..."
— `.claude/agents/qrspi-design-critic-completeness.md:18`

**Existing cost lever (RUS-77):** when `criticConfig.digest.enabled`, a single shared
trimmed digest is built once before the round loop (`buildResearchDigest`,
qrspi-batch.js:998) and its path is threaded as an extra `DIGEST_PATH = ...` line
(`digestLine`, qrspi-batch.js:864); lenses then read the digest in place of research.md.
Default OFF ⇒ `digestPath` null ⇒ full research.md read per lens (qrspi-batch.js:837-847).

**Dependencies:** `runCriticPanelLoop` ← `doDesign` (sets the paths) ← `readCriticsConfig`
(resolves `digest.enabled`). Lens agents `qrspi-design-critic-<id>` (tools: `Read`).
**Implicit contracts:** Every lens receives the SAME four paths each round; the staged
design (`DESIGN_PATH = stg(id,'design')`) is what mutates across revise rounds, not
research.md — hence the digest is built once and reused for all rounds.

## Q3: What is the current schema of the `critics` block in `.qrspi/config.json` (and `.qrspi/config.example.json`), and which keys does the critic loop already read from it?

**Answer:** `.qrspi/config.json` is gitignored and absent in this worktree; the schema
is documented in `.qrspi/config.example.json`. The `critics` block has six phase
sub-blocks: `questions`, `research`, `structure`, `plan` (each `{enabled, maxRounds}`);
`design` (`{enabled, maxRounds, lenses[], candidates, digest:{enabled}, gateBehindEdge:
{enabled}, lensModel?}`); and `implementation` (`{enabled, maxRounds, coherence:{enabled,
maxRounds}}`). Every phase honors a uniform `enabled` flag defaulting **OFF** (opt-in).

Keys actually consumed (resolved by `qrspi_critics_config.py`, then read in JS):
`enabled`, `maxRounds`, `lenses`, `candidates`, `digest.enabled`,
`gateBehindEdge.enabled`, `lensModel` (design); `coherence.enabled`/`coherence.maxRounds`
(implementation).

**Evidence:**

```json
"design": {
  "candidates": 1,
  "digest": { "enabled": false },
  "enabled": false,
  "gateBehindEdge": { "enabled": false },
  "lenses": ["completeness","internal-consistency","edge-alignment","simplicity"],
  "maxRounds": 2
}
```

— `.qrspi/config.example.json:7-25`

**Dependencies:** `qrspi_critics_config.py:resolve_critics` reads it; JS reads it via
`readCriticsConfig` → `parseCriticsEnvelope`. `lensModel` is the only key OMITTED (not
null) by default (qrspi_critics_config.py:188-190).
**Implicit contracts:** Only an explicit boolean flips `enabled`; non-boolean ⇒ default
OFF. Unknown lenses are dropped (warned); all-unknown/empty falls back to the default
four. `candidates` clamps to `[1, 3]`. The example mirrors the all-defaults resolution
(every `enabled: false`) so it changes nothing as written.

## Q4: How does the config reader expose nested values today — does it support reading sub-keys under `critics`, or only single top-level string keys (per `scripts/qrspi_config.py` / the JS `parseConfigEnvelope`)?

**Answer:** TWO distinct readers exist, with different capabilities:

1. **`scripts/qrspi_config.py`** + JS **`parseConfigEnvelope`** — reads ONE top-level key
   and REQUIRES the value be a STRING. `parseConfigEnvelope` returns `ok:false` if
   `typeof env.value !== 'string'` (qrspi-batch.js:354). It cannot read nested blocks or
   non-string values. It is used only for `linearProject` (qrspi-batch.js:2631).
2. **`scripts/qrspi_critics_config.py`** + JS **`parseCriticsEnvelope`** — the
   purpose-built nested reader for `critics`. It reads `.qrspi/config.json` once and emits
   a fully-resolved `{ ok, phases:{…six phases…}, warnings }` envelope with all nested
   sub-keys (lenses, digest, coherence, etc.) already resolved. `parseCriticsEnvelope`
   extracts `env.phases` and shallow-merges over `DEFAULT_CRITIC_PHASES`.

So nested `critics` sub-keys are handled exclusively by the second reader; the first
cannot do it. This is the documented "single-top-level-key only" limitation of
`qrspi_config.py` (project MEMORY: "Config reader is single-top-level-key only").

**Evidence:**

```javascript
if (typeof env.value !== 'string')
  return { ok: false, error: `config: envelope value not a string (got ${env.value})` }
```

— `.claude/workflows/qrspi-batch.js:354`

```python
def select_value(config, key, default):
    value = config.get(key)        # single top-level key, no dot-path
    return value if value else default
```

— `scripts/qrspi_config.py:36-42`

**Dependencies:** `qrspi_critics_config.py` imports `read_config` from `qrspi_config.py`
(qrspi_critics_config.py:52) to reuse the best-effort file read, then does its own nested
resolution. **Implicit contracts:** Any new nested critic config (e.g. a summarizer
toggle) must go through `qrspi_critics_config.py`, never `qrspi_config.py` — the latter
will reject a non-string/nested value as `ok:false`.

## Q5: What invocation interface do the existing edge critic, 4-lens design panel, per-slice edge critic, and whole-stack coherence critic share — how are they spawned and how is model selection passed (if at all) per critic?

**Answer:** All critics are spawned via the runtime-provided `agent(prompt, opts)`
function with `{ label, phase:'Critic', agentType, schema }`. Each critic type maps to a
landed `agentType`:
- Single edge critic: `agentType: 'qrspi-critic'`, schema `CRITIC_VERDICT_SCHEMA`
  (qrspi-batch.js:733).
- Design panel: one agent per lens, `agentType: 'qrspi-design-critic-<lens>'`, fanned out
  with `parallel(...)` (qrspi-batch.js:858-879).
- Per-slice edge critic (RUS-75) and whole-stack coherence critic: also single-critic
  `agent()` spawns (coherence uses `qrspi-coherence-critic`); the decision of *whether* to
  run the slice critic is delegated to `qrspi_slice_critic.py` via `sliceCriticDecide`
  (qrspi-batch.js:1357).

**Model selection:** Only the design panel has a per-critic model seam: `lensModel`.
When set, it is attached as `agentOpts.model` on each lens spawn. This is a **speculative,
unverified seam** — the code comment states there is no evidence the harness honors an
`agent()` `model` option, so the lever may be **inert**. No other critic accepts a model
option; default is no `model` key (current harness behavior).

**Evidence:**

```javascript
const agentOpts = { label: `critic:${id}:${name}:${lens}#${round + 1}`,
                    phase: 'Critic', agentType, schema: CRITIC_VERDICT_SCHEMA }
if (lensModel) agentOpts.model = lensModel
```

— `.claude/workflows/qrspi-batch.js:866-867`

```javascript
// NOTE (Risk Register / Q4): there is no evidence the harness honors an agent() `model`
// option, so this lever may be inert — it ships default-OFF ...
```

— `.claude/workflows/qrspi-batch.js:850-852`

**Dependencies:** `agent()`/`parallel()` are injected globals from the Workflow runtime
(not defined in the file). Decision logic for converge/revise/cap is shared across all
loops via `criticDecision` → `qrspi_critic_loop.py:next_action`.
**Implicit contracts:** All critics return the canonical `{pass, findings}` verdict via
schema validation at the runner boundary. The panel reduces M lens verdicts to one via
`synthesizeVerdicts` before reusing the single-critic `next_action` decision.

## Q6: Where and how is the per-run round/iteration state for the critic loop tracked, and how would a summarizer scope verdicts to a single run vs. across runs when reading `journal.jsonl`?

**Answer:** Per-run round state is tracked **in-memory** during a loop, then reduced to
one ledger line at termination — there is no persistent per-round record and **no
`journal.jsonl`**.

- In-loop: `metricRounds` (a JS array) accumulates `{lens, pass, findings}` for every
  lens × round; `summaryRounds` accumulates a display string (qrspi-batch.js:825-828).
- At termination: `recordCriticMetrics(id, phase, metricRounds, terminalAction)` reduces
  the rounds to one `CriticStepMetrics` and appends one line to the ledger.

**Run-scoping problem (load-bearing for a summarizer):** The ledger line carries
`ticketId` + `timestamp` but **NO run id**. The ledger is APPEND-only and is NEVER
truncated between runs (`open(path, "a")`, qrspi_metrics_append.py:86). So a summarizer
cannot distinguish "this run" from "across all historical runs" from the data alone — it
would have to scope by `timestamp` window or by ticket, or the appender would need a
new run-id field. This is a real gap to call out for the design.

**Evidence:**

```javascript
const metricRounds = []
...
for (const v of lensVerdicts) metricRounds.push({ lens: v.lens, pass: v.pass, findings: v.findings })
...
const metrics = await recordCriticMetrics(id, name, metricRounds, 'converged')
```

— `.claude/workflows/qrspi-batch.js:828, 904, 930`

```python
with open(path, "a") as fh:          # append-only; never truncated per run
    fh.write(json.dumps(ledger_line) + "\n")
```

— `scripts/qrspi_metrics_append.py:86-87`

**Dependencies:** `runCriticLoop`/`runCriticPanelLoop` own the in-memory state;
`qrspi_metrics_append.py` owns durability. **Implicit contracts:** One ledger line per
terminated step; ordering within a line's `rounds[]` is the only round-sequence signal.
No run-id ⇒ cross-run vs. single-run scoping is not currently supported.

## Q7: How is `critic-synthesize` wired relative to the individual lenses — does it consume the lens verdicts as input, and what does it write back as the panel's combined verdict?

**Answer:** Yes. After the per-lens fan-out, `runCriticPanelLoop` builds a tagged list of
`{pass, findings, lens}` from the lens replies (qrspi-batch.js:898-902) and passes it to
`synthesizeVerdicts`, which shells out to `scripts/qrspi_critic_synthesize.py` (the JS
sandbox can't run Python). The script reduces M lens verdicts to ONE authoritative
`{pass, findings}` round verdict: `pass` only if EVERY lens passed; `findings` is the
exact-string-deduped union, each finding optionally lens-tagged as `{text, lens}`.

It does NOT write to disk. The synthesized verdict is handed (as a one-element list) to
`criticDecision` (the same `next_action` the single critic uses) to decide
converge/revise/cap (qrspi-batch.js:922). On `revise`, the synthesized findings drive the
design-reviser re-spawn (qrspi-batch.js:942-953). The synthesized verdict is NOT itself
persisted — only its reduced `pass`/`findingsCount` per round survive into the ledger via
`metricRounds`.

**Evidence:**

```javascript
const synth = await synthesizeVerdicts(lensVerdicts)
...
const passed = synth.pass === true
const synthFindings = Array.isArray(synth.findings) ? synth.findings : []
...
const decision = await criticDecision([{ pass: passed, findings: synthFindings }], round, maxRounds)
```

— `.claude/workflows/qrspi-batch.js:907-922`

**Dependencies:** `synthesizeVerdicts` (qrspi-batch.js:971) → `qrspi_critic_synthesize.py`
worker → `SYNTHESIZED_VERDICT_SCHEMA` (qrspi-batch.js:565-590). Feeds `criticDecision`.
**Implicit contracts:** Synthesize is the tested single source of truth for the M→1
reduction (JS never re-derives it). Findings items may be a bare string OR a `{text, lens}`
object — both accepted downstream (reviser renders either, qrspi-batch.js:949).

## Q8: How does the critic loop currently behave when a lens returns `pass=false` with findings — does it trigger an artifact-change round, and where is the dissent→artifact-change transition recorded so a summarizer can compute that rate?

**Answer:** A `pass=false` synthesized verdict (any lens dissenting ⇒ panel fails) leads
`criticDecision`/`next_action` to return `action: 'revise'` **if rounds remain**, or
`action: 'cap_reached'` **if this is the last round** (`round+1 >= max_rounds`). On
`revise` the loop re-spawns the design producer to **rewrite the staged artifact in place**
(qrspi-batch.js:942-953), then re-runs the panel. So yes — dissent triggers an
artifact-change round, but ONLY when the cap has not been reached.

**Where the transition is recorded:** It is NOT recorded as an explicit
"dissent→change" event. The ONLY persisted trace is the ledger's `rounds[]`: a summarizer
must INFER an artifact-change round from a `pass:false` round that is FOLLOWED by another
round in the same step (i.e. round R failed and round R+1 exists ⇒ a revise happened
between them). The terminal `revise` action is explicitly NOT a `terminalAction`
(qrspi_critic_metrics.py:31). A `cap_reached` terminal with a final failing round means
dissent that did NOT get a further change round (findings went to the PR body instead).

**Evidence:**

```python
if int(round) + 1 >= int(max_rounds):
    return {"action": "cap_reached", "residual_findings": list(latest["findings"])}
return {"action": "revise", "residual_findings": list(latest["findings"])}
```

— `scripts/qrspi_critic_loop.py:111-114`

```javascript
// action === 'revise': re-spawn the design producer to rewrite stg(id, name) in place
log(`  ${id}: ${name} panel REVISE at round ${round + 1} — rewriting design to address ...`)
const rev = await agent(`You are the REVISER for ${id} artifact "${name}". ...`)
```

— `.claude/workflows/qrspi-batch.js:938-953`

**Dependencies:** `next_action` (decision) → JS revise spawn → next round. Metrics:
`metricRounds` → `qrspi_critic_metrics.py` → ledger. **Implicit contracts:** The
"dissent→artifact-change rate" a summarizer wants is DERIVABLE but not directly stored:
count steps whose `rounds[]` contain a `pass:false` round that has a successor round.
There is no field that directly says "this round caused a rewrite."

## Q9: What happens if a critic invocation fails to produce a parseable verdict or the `journal.jsonl` write fails mid-run — is the loop fail-closed, and would a partial/corrupt record break the proposed summarizer?

**Answer:** The loop is **fail-closed** at every spawn/parse/write boundary:

- A lens (or single critic) returning `null` (failed spawn) ⇒ the loop logs, emits an
  `aborted` metrics record (capturing partial lens replies), and returns
  `{ok:false}` — stopping the ticket, never treating a missing verdict as a pass
  (qrspi-batch.js:883-895; runCriticLoop 735-738).
- An unparseable verdict is coerced to NOT-passed by `parse_critic_verdict`/`_coerce_verdict`
  (never raises) so a garbled reply can never mark "converged"
  (qrspi_critic_loop.py:51-78).
- `synthesizeVerdicts` returning null ⇒ aborted record + stop (qrspi-batch.js:908-912).
- The ledger write (`qrspi_metrics_append.py`) fails CLOSED: a write leaving the ledger
  empty returns an error and the CLI exits non-zero; `recordCriticMetrics` chains the
  reducer + appender and treats a non-zero appender exit as a null return — logged, never
  silently dropped (qrspi-batch.js:1062-1075).

**Partial/corrupt record risk to a summarizer:** Each ledger line is written atomically
as one `json.dumps(...) + "\n"`. The MAIN corruption risk is a **partial final line** if
a process is killed mid-write (the append is not fsync'd / not written via temp-rename).
A summarizer reading the JSONL must therefore tolerate a trailing unparseable line
(skip-on-`JSONDecodeError` per line), or it could break. Aborted records ARE valid lines
(they intentionally emit so base rates aren't biased toward successful terminations,
qrspi_critic_metrics.py:27-30) — those are fine.

**Evidence:**

```javascript
const failedLens = replies.find(rp => !rp || rp.verdict === null)
if (failedLens) {
  ... const metrics = await recordCriticMetrics(id, name, metricRounds, 'aborted')
  return { ok: false, residualFindings: [], metrics }
}
```

— `.claude/workflows/qrspi-batch.js:883-894`

```python
if size == 0:
    return 0, 0, "ledger is empty after append: %s" % path
```

— `scripts/qrspi_metrics_append.py:92-93`

**Dependencies:** Parser `qrspi_critic_loop.py`; appender `qrspi_metrics_append.py`.
**Implicit contracts:** A summarizer must parse the ledger line-by-line and tolerate a
trailing partial line. Aborted records are first-class and must be counted.

## Q10: How does the design panel currently determine which lenses are "relevant" to a given artifact, since the teeth eval must assert each *relevant* lens returns `pass=false`?

**Answer:** There is **no per-artifact lens-relevance selection**. The panel runs the
FULL configured lens set on EVERY design artifact, every round — `lenses` comes from
config (default all four) and `runCriticPanelLoop` fans out one agent per lens
unconditionally (qrspi-batch.js:858-879). The only filtering is config-time validation
(`qrspi_critics_config.py` drops unknown lens names and falls back to the default four if
the set is empty) — not artifact-driven relevance.

"Relevance" is instead an INTERNAL judgment each lens makes about each upstream item: the
completeness lens, for example, judges "every acceptance criterion ... **that bears on the
design**" and is told "Do not invent requirements the upstream inputs do not state"
(qrspi-design-critic-completeness.md:24, 38). So a lens can self-determine an item is not
applicable and still pass. **Implication for a teeth eval:** "each *relevant* lens returns
pass=false" is not something the harness computes — the eval would have to define
relevance itself (e.g. "all configured lenses" or per-lens fixtures), because the code
treats all configured lenses as always-run.

**Evidence:**

```javascript
const replies = await parallel(
  lenses.map(lens => async () => {
    const agentType = `qrspi-design-critic-${lens}`
    ...
  })
)
```

— `.claude/workflows/qrspi-batch.js:858-879`

```python
lenses = known if known else list(DEFAULT_DESIGN_LENSES)  # config-time only, not per-artifact
```

— `scripts/qrspi_critics_config.py:152`

**Dependencies:** `lenses` resolved by `qrspi_critics_config.py`; consumed in
`runCriticPanelLoop`. Lens agents under `.claude/agents/qrspi-design-critic-*.md` (four:
completeness, internal-consistency, edge-alignment, simplicity).
**Implicit contracts:** All configured lenses run on every artifact. Each lens fails
closed on doubt (completeness rule 3) but may legitimately pass an item it judges
non-applicable — so "relevant" is a per-lens semantic, not a routing decision.

## Q11: What pattern do existing `scripts/*_test.py` use for components that touch LLM agents vs. pure logic, and is there any existing seam (e.g., the `evals/` + `scripts/run_eval.py` placeholder) that an opt-in teeth eval would attach to?

**Answer:** The established pattern is a **functional-core / imperative-shell split**: all
testable logic lives in pure, stdlib-only Python modules (`scripts/qrspi_*.py`) with
`unittest`-based `_test.py` siblings exercising the pure functions against in-memory data
/ temp dirs. The agent-spawning glue lives in `qrspi-batch.js` and is **deliberately NOT
unit-tested** (harness-coupled: top-level return, injected globals — see
`docs/testing-dynamic-workflows.md` and run_tests.py:19-21). Tests never invoke `agent()`.

- Pure-logic tests: `qrspi_critic_loop_test.py`, `qrspi_critic_metrics_test.py`,
  `qrspi_critic_synthesize_test.py`, `qrspi_critics_config_test.py`,
  `qrspi_metrics_append_test.py` (uses `tempfile` for the ledger write).
- Aggregating runner: `scripts/run_tests.py` discovers every `scripts/*_test.py`, runs
  each as a subprocess, exits non-zero if any fails; it is the CI gate
  (`.github/workflows/tests.yml`).

**The `evals/` + `scripts/run_eval.py` seam:** It EXISTS (`run_eval.py` defines
`ExecutionResult`/`EvalConfig` dataclasses, trials, ThreadPoolExecutor) but is a
**documented NON-FUNCTIONAL placeholder** (CLAUDE.md + project MEMORY: "Eval harness is a
placeholder"). An opt-in teeth eval that actually spawns critic agents would NOT belong in
the deterministic `run_tests.py` suite (it would be flaky/costly — see
docs/testing-dynamic-workflows.md:99,148); it would attach to the `evals/`/`run_eval.py`
seam, which currently does not really execute anything.

**Evidence:**

```python
@dataclass
class EvalConfig:
    skill_path: str
    suite_path: str
    ...
    trials: int = 3
    max_workers: int = 4
    timeout_ms: int = 120000
```

— `scripts/run_eval.py:33-41`

**Dependencies:** `run_tests.py` (deterministic gate, CI) vs. `evals/`+`run_eval.py`
(placeholder, manual). **Implicit contracts:** Anything that spawns an agent cannot live
in the deterministic suite. The teeth-eval must be opt-in and off the CI gate.

## Q12: Is any part of the critic verdict path (parsing, journal record shape, base-rate computation) deterministic enough to cover with a stdlib unit test, separate from the non-deterministic agent spawning?

**Answer:** Yes — substantial parts are ALREADY pure and unit-tested, and a base-rate
computation would be a natural new pure module:

- **Parsing:** `qrspi_critic_loop.py:parse_critic_verdict` / `_coerce_verdict` — pure,
  fail-closed, tested by `qrspi_critic_loop_test.py`.
- **Record shape:** `qrspi_critic_metrics.py:build_record` — pure reducer (verdicts →
  `CriticStepMetrics`), tested by `qrspi_critic_metrics_test.py`.
- **Synthesis:** `qrspi_critic_synthesize.py:synthesize` — pure M→1 reduction, tested.
- **Decision:** `qrspi_critic_loop.py:next_action` — pure, tested.
- **Ledger envelope + append:** `qrspi_metrics_append.py` pure helpers (`ledger_path`,
  `wrap_envelope`, `append_line`) — tested against temp dirs.

**Base-rate / summarizer computation does not exist yet** but would slot cleanly as a new
pure module reading the JSONL (a list of dicts) and computing rates (pass rate, dissent
rate, terminal-action distribution, findings-count stats). It can be fully stdlib-unit-
tested with in-memory ledger-line fixtures, exactly like `qrspi_critic_metrics_test.py`'s
`SAMPLE_RECORD`. The non-deterministic agent spawning stays in JS, untested.

**Evidence:**

```python
SAMPLE_RECORD = {
    "phase": "design",
    "rounds": [
        {"lens": "completeness", "pass": False, "findingsCount": 2},
        {"lens": "edge", "pass": True, "findingsCount": 0},
    ],
    "terminalAction": "cap_reached",
}
```

— `scripts/qrspi_metrics_append_test.py:13-21`

**Dependencies:** A new summarizer module would consume the same ledger lines
`qrspi_metrics_append.py` writes. **Implicit contracts:** Pure modules take already-parsed
dicts / plain text and never touch agent/git/network, so a `_test.py` sibling can exercise
them; this is the repo's hard rule for what is testable.

## Q13: What is the exact on-disk location, format, and append/rotation behavior of `journal.jsonl`, and does it already capture token-cost data per critic invocation that the summarizer could report alongside dissent rate?

**Answer:** No `journal.jsonl`. The actual file:

- **Location:** `<host-checkout-root>/.worktrees/<id>/.qrspi/<id>/critic-metrics.jsonl`,
  computed by `qrspi_metrics_append.py:ledger_path`. The root is resolved via
  `qrspi_paths.resolve_repo_root(validate=False)` (git-common-dir first) so it lands in
  the MAIN checkout's worktree, never a double-nested phantom path
  (qrspi_metrics_append.py:60-64, 125-126).
- **Format:** JSON Lines — one `CriticMetricsLedgerLine` object per line (see Q1 shape).
- **Append/rotation:** Pure append (`open(path, "a")`), parent dir auto-created, NO
  rotation, NO truncation, NO size cap. After each append it verifies the file is
  non-empty and re-counts lines (fail-closed on empty).
- **Token-cost data:** `tokensIn`/`tokensOut` exist in the schema but are
  **NEVER populated in the live path** (usage is always absent — see Q14). So the ledger
  does NOT currently carry per-critic token cost; a summarizer can report dissent rate but
  NOT real token cost from this file today.

**Evidence:**

```python
def ledger_path(repo_root, ticket):
    return os.path.join(repo_root, ".worktrees", ticket, ".qrspi", ticket,
                        "critic-metrics.jsonl")
```

— `scripts/qrspi_metrics_append.py:60-64`

```python
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, "a") as fh:
    fh.write(json.dumps(ledger_line) + "\n")
```

— `scripts/qrspi_metrics_append.py:85-87`

**Dependencies:** `qrspi_paths.resolve_repo_root`; written only by
`qrspi_metrics_append.py` (invoked by `recordCriticMetrics`). **Implicit contracts:** The
`qrspi` token in the path is computed by the script off the resolved root, NEVER typed by
a model (the path-mangling mitigation). Unbounded append ⇒ a long-lived ticket's ledger
grows monotonically.

## Q14: How is subagent token consumption currently surfaced or attributed per critic invocation (the ~749K-token figure cited for the first RUS-76 run) — is it captured anywhere queryable, or only observable externally?

**Answer:** It is **NOT captured anywhere queryable in the harness.** Per the
documented open question (OQ2), the Workflow runtime exposes **no per-subagent token
usage** to the orchestrator. Consequently:

- `recordCriticMetrics` passes NO `usage` to `qrspi_critic_metrics.py:build_record`, so
  `tokensIn`/`tokensOut` are always omitted from every ledger line
  (qrspi_critic_metrics.py:95-101 — emitted only `if usage`, and `usage` is always None).
- The `qrspi_critic_metrics.py` module docstring states plainly: "the harness exposes no
  per-subagent token usage ... the AC-INSTR 'at what token cost' dimension is therefore
  currently UNMET" (qrspi_critic_metrics.py:38-45).
- `agent()` is an injected runtime global; the file never reads a usage/token field off its
  return value. The ~749K figure is therefore an EXTERNALLY observed run total, not an
  attributable-per-critic value the harness records.

The only token-shaped accounting structure anywhere is `ExecutionResult.tokens` /
`tokens: dict` in the NON-FUNCTIONAL `scripts/run_eval.py` placeholder (run_eval.py:24) —
which does not run, so it captures nothing.

**Evidence:**

```python
# tokensIn / tokensOut are OPTIONAL. Per OQ2 the harness exposes no
# per-subagent token usage, so the slice-2 JS wiring supplies no `usage` and these
# keys are NEVER populated in practice. The AC-INSTR ... dimension is therefore
# currently UNMET ...
```

— `scripts/qrspi_critic_metrics.py:38-45`

**Dependencies:** Token attribution would require a new harness capability (usage on the
`agent()` return). **Implicit contracts:** `tokensIn`/`tokensOut` keys are reserved for a
future ticket once the harness exposes usage; today any cost dimension must be measured
externally (run-level), not per-critic.

---

## Discovered Patterns

- **Functional core / imperative shell.** Every testable decision lives in a pure,
  stdlib-only `scripts/qrspi_*.py` module with a `_test.py` sibling; the JS orchestrator
  (`qrspi-batch.js`) holds only untestable agent-spawn glue and NEVER re-derives a
  decision the Python owns. New deterministic logic (e.g. a summarizer) should follow this
  split: pure Python module + `_test.py`, attached to `run_tests.py`/CI.
- **Python-via-worker invocation idiom.** The JS sandbox cannot run Python, so JS spawns a
  worker agent that runs EXACTLY one verbatim `python3 scripts/qrspi_*.py` command and
  echoes its JSON stdout. Fragile text (verdicts, findings) is piped on **stdin** (via
  `printf '%s' <json-of-json>`), never through the worker's stdout echo. All reducers
  (`synthesizeVerdicts`, `criticDecision`, `recordCriticMetrics`, `buildResearchDigest`,
  `selectDesignWinner`) follow this exact pattern (qrspi-batch.js:971-1076).
- **Uniform opt-in `enabled` vocabulary.** Every phase critic defaults OFF; only an
  explicit boolean flips it; non-boolean ⇒ default. Resolved once per action by
  `qrspi_critics_config.py` ("single read discipline").
- **Fail-closed everywhere.** Missing/garbled verdicts coerce to NOT-passed; empty ledger
  writes error and exit non-zero; aborted critic steps STILL emit a metrics record so base
  rates are unbiased.
- **Self-locating scripts.** `qrspi_config.py`, `qrspi_critics_config.py`,
  `qrspi_metrics_append.py`, `qrspi_persist.py` all resolve the repo root from `__file__`
  or `resolve_repo_root`, so the `qrspi` path token is never typed by a model.
- **Cost levers ship default-OFF and one is admittedly inert.** The RUS-77 `digest` lever
  is real and wired; the `lensModel` lever rides an unverified harness seam and may do
  nothing; `gateBehindEdge` is a no-op in the current call graph (design routes to panel OR
  edge, never a sequence) — all three default OFF.

## Inconsistencies

- **`journal.jsonl` is a phantom.** The questions (Q1, Q6, Q9, Q13) name `journal.jsonl`,
  but no such file exists. The real store is `.qrspi/<id>/critic-metrics.jsonl`. Any design
  must use the actual name/shape or explicitly introduce a new file.
- **`tokensIn`/`tokensOut` schema fields are dead.** They exist in
  `CRITIC_METRICS_SCHEMA` (qrspi-batch.js:1037-1038) and `build_record`, but are NEVER
  populated (OQ2 — no harness usage exposure). The "at what token cost" AC is documented as
  UNMET in `qrspi_critic_metrics.py:38-45`. The code self-flags this.
- **Stale design doc vs. code on terminal actions.** `qrspi_critic_metrics.py:33-36` notes
  `design.md:76` is stale — it lists only `converged/cap_reached`, while the faithful set is
  the four `converged|cap_reached|exhausted|aborted` (flagged in `structure.md:19`).
- **No run-id / round-index in the ledger.** A summarizer cannot cleanly scope to a single
  run (only `timestamp`/`ticketId` exist) and must infer round sequence from `rounds[]`
  array position and the dissent→change rate from `pass:false`-followed-by-a-later-round —
  neither is stored explicitly.
- **Two config readers with divergent capabilities.** `qrspi_config.py` rejects
  non-string/nested values (`ok:false`); only `qrspi_critics_config.py` handles nested
  `critics` sub-keys. Easy to reach for the wrong one for a new nested toggle.
- **"Relevant lens" has no code referent.** The panel always runs all configured lenses;
  there is no per-artifact relevance routing, so a teeth eval asserting "each relevant lens
  fails" must define relevance itself.
