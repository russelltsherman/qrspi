# Implementation Plan — Critic effectiveness: instrumentation, cost reduction, and teeth eval

**Structure basis:** structure.md @ 2026-06-15T00:00:00Z
**Generated:** 2026-06-15T00:00:00Z
**Status:** draft
**Total steps:** 34

> **Plan-phase pins (decisions the structure deferred):**
> - **`runId` source** — the JS append call site passes the orchestrator's per-invocation id when present, else a generated id. Mechanism: a module-level `runId` constant computed once at the top of `qrspi-batch.js` (the imperative shell) as `process.env.QRSPI_RUN_ID || crypto.randomUUID()`; the Python appender takes `run_id` as a required string argument (no default), so the contract "always present, always a string on every appended line" holds. Step 8 confirms the actual call site against the file before editing; if the line-building site differs in shape, thread the same constant there.
> - **`perLens` key shape** — `perLens` is keyed by the lens string; the single edge critic (`lens` is `null`) rolls under the literal key `"edge"`. No other lens key is rewritten.
> - **Slice 2 runbook home** — a markdown runbook section, not a script (the structure left it open; a doc avoids adding an untested script to satisfy a manual/opt-in measurement). Home: `docs/critic-cost-ab.md`.
> - **Teeth-eval layout (corrected — the design's `scripts/qrspi_teeth_eval.py` is infeasible).** A lens is a registered `agentType` spawnable **only from a Workflow runner** (qrspi-batch.js:20–24) and Reads its inputs as files (`tools: Read`), so a plain `python3` script cannot drive it and `run_eval.py`'s tool-less single-turn seam cannot either. The runner is therefore the workflow **`.claude/workflows/qrspi-teeth-eval.js`**. Fixtures live under `evals/teeth/`: `design.md`, `research.md`, **`ticket.md`** (carries the omitted AC the completeness lens anchors on), **`questions.md`** (the completeness lens Reads `QUESTIONS_PATH`). The majority/marker decision is extracted to a pure CI-tested core **`scripts/qrspi_teeth_assert.py`** (+ `_test.py`) so Slice 3 has a deterministic test contribution while the agent spawning stays off CI.
> - **Trial count / threshold** — `--trials` default 3, majority threshold ≥2-of-3. The workflow runs the trial loop (it does NOT reuse `run_eval.py` — confirmed not reusable: its `call_model` is a tool-less single-turn API call that cannot let a lens Read fixtures); the threshold math lives in `qrspi_teeth_assert.py`. Each defect carries a **unique quotable marker** the owning lens must cite, turning "names its defect" into a deterministic substring test on the verdict `findings`.

## Slice 1: Instrumentation — runId field + critic summarizer

### Setup

1. ✨ Create `scripts/qrspi_critic_summary.py` — module skeleton (module docstring, stdlib imports `json`, `sys`, `argparse`; no logic yet) for the pure summarizer (structure §Contracts: `load_ledger`, `summarize`, `main`).

### Core Logic

2. ⚠️ Modify `scripts/qrspi_critic_summary.py` — add `def load_ledger(path: str) -> list[dict]:` — read the file line by line; `json.loads` each non-empty line; on `json.JSONDecodeError` skip the line and increment an aborted-record counter; tolerate a trailing partial line. Return the list of parsed dicts (per the structure contract this is pure with no aggregation; the aborted count is recomputed inside `summarize`, or returned via a module-level helper — keep `load_ledger` returning only the dict list and have `summarize` receive the raw lines).
   - **Note:** to keep `load_ledger` signature exactly `-> list[dict]` per structure, expose aborted-record counting through `summarize` (which re-scans for malformed lines) OR add a sibling `load_ledger_with_stats`. Choose: `load_ledger` returns `list[dict]` of good lines only; `summarize` receives the already-parsed list plus an `aborted: int` kwarg defaulting to 0. The CLI (`main`) computes aborted via a single read that returns `(lines, aborted)`.
3. ⚠️ Modify `scripts/qrspi_critic_summary.py` — add `def _read_lines(path: str) -> tuple[list[dict], int]:` — single-pass reader returning `(good_lines, aborted_count)`; `load_ledger` calls it and returns only `good_lines`. This keeps the structure's `load_ledger(path) -> list[dict]` contract while preserving aborted-record counting for the CLI.
4. ⚠️ Modify `scripts/qrspi_critic_summary.py` — add `def summarize(lines: list[dict], since: str|None = None, ticket: str|None = None, run_id: str|None = None, aborted: int = 0) -> dict:` — filter `lines` by exact `run_id` (when given), then by `ticket` (exact), then by `since` (timestamp `>=`); compute `stepCount` (len of scoped lines), `timestampSpan` (`{start, end}` min/max `timestamp`, `null` when empty), `dissentRate`, `dissentRevisedRate`, `terminalActionCounts`, `perLens`, and `abortedRecords` (= `aborted`). Return the `CriticSummary` dict.
5. ⚠️ Modify `scripts/qrspi_critic_summary.py` — implement the dissent/revise math inside `summarize`: for each scoped step (line), each entry in `rounds[]` is a round; a round is **dissent** if `round.get("pass") is False` OR `round.get("findingsCount", 0) > 0`; `dissentRate` = dissent-rounds / total-rounds. `dissentRevisedRate` = (count of `pass:false` rounds that are followed by a later round in the same step's `rounds[]`) / (count of `pass:false` rounds). Add a docstring on `summarize` stating `dissentRevisedRate` measures "a revise round was attempted after dissent," NOT "the artifact changed" (structure §Contracts, design §AC-Instrumentation).
6. ⚠️ Modify `scripts/qrspi_critic_summary.py` — implement `perLens` and `terminalActionCounts`: `perLens` keyed by each round's `lens` string, with `lens is None` rolled under key `"edge"`; each value is `{steps: int, dissentRate: float}` (steps = rounds seen for that lens key). `terminalActionCounts` = count of each `terminalAction` across scoped steps.
7. ⚠️ Modify `scripts/qrspi_critic_summary.py` — add `def main(argv) -> int:` (and `if __name__ == "__main__": sys.exit(main(sys.argv[1:]))`) — argparse with `--run-id`, `--since`, `--ticket`, and a positional ledger path; call `_read_lines`, `summarize(...)`, then `print(json.dumps(summary))`; return 0.

### runId on the append seam

8. ⚠️ Modify `scripts/qrspi_metrics_append.py` — add a required `run_id: str` parameter to the function that builds/appends a `CriticMetricsLedgerLine`, and stamp the emitted dict with `"runId": run_id`. One additive field; no rename, no new store, no critic-loop control-flow edit.
   - **Current:** the append function builds `{ phase, rounds, terminalAction, ticketId, timestamp, tokensIn, tokensOut }` with no `runId` and no `run_id` parameter.
   - **After:** the same function takes `run_id: str` and the built dict additionally carries `"runId": run_id`.
9. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — add a module-level `runId` constant near the top of the imperative shell: `const runId = process.env.QRSPI_RUN_ID || crypto.randomUUID();` (import `crypto` if not already in scope). Confirm the exact existing append call site first (structure Unverified Assumption #2); this is the single place instrumentation reaches into existing JS.
10. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — at the existing call site that invokes `qrspi_metrics_append.py` (or builds the ledger line), pass the `runId` constant through as the new `run_id`/`--run-id` argument. Touch only the append call site, NOT the critic-loop control flow (design §Slicing-premise note).

### Tests

11. ✨ Create `scripts/qrspi_critic_summary_test.py` — stdlib `unittest`; define in-memory ledger-line fixtures mirroring `qrspi_metrics_append_test.py:SAMPLE_RECORD`, each now including a `runId` field.
12. ⚠️ Modify `scripts/qrspi_critic_summary_test.py` — add `test_dissent_via_fail`: a round with `pass:false` counts as dissent; assert `dissentRate` reflects it.
13. ⚠️ Modify `scripts/qrspi_critic_summary_test.py` — add `test_dissent_via_nonempty_findings`: a round with `pass:true` but `findingsCount > 0` counts as dissent.
14. ⚠️ Modify `scripts/qrspi_critic_summary_test.py` — add `test_dissent_revised_rate`: a step whose `rounds[]` has a `pass:false` round followed by a later round yields `dissentRevisedRate` = 1.0 for that pass:false round; a trailing `pass:false` with no following round yields 0.0.
15. ⚠️ Modify `scripts/qrspi_critic_summary_test.py` — add `test_trailing_partial_line`: a ledger string ending in a truncated/invalid JSON line is tolerated; good lines still parse and `abortedRecords` counts the bad one.
16. ⚠️ Modify `scripts/qrspi_critic_summary_test.py` — add `test_aborted_record_counting`: multiple malformed lines interleaved are skipped and counted in `abortedRecords`.
17. ⚠️ Modify `scripts/qrspi_critic_summary_test.py` — add `test_run_id_exact_scoping`: lines with two distinct `runId`s; `summarize(..., run_id=X)` returns only X's steps in `stepCount`.
18. ⚠️ Modify `scripts/qrspi_critic_summary_test.py` — add `test_since_and_ticket_scoping`: `--since`/`since=` window and `ticket=` exact filter each restrict the scoped set.
19. ⚠️ Modify `scripts/qrspi_critic_summary_test.py` — add `test_timestamp_span` and `test_per_lens_edge_rollup`: `timestampSpan` reports min/max; `perLens` rolls `lens:null` under `"edge"` and keys other lenses by their string.
20. ⚠️ Modify `scripts/qrspi_metrics_append_test.py` — add `test_run_id_present_and_round_trips`: call the appender with a `run_id`, read the written line back, assert `"runId"` is present and equals the passed value.
21. Run: `python3 scripts/run_tests.py critic_summary && python3 scripts/run_tests.py metrics_append`
    - **Expected:** both filtered runs pass.

### Verify Slice 1

22. **Checkpoint:** `python3 scripts/run_tests.py`
    - [ ] `python3 scripts/run_tests.py critic_summary` passes (summarizer tests incl. `--run-id` exact scoping and partial-line tolerance).
    - [ ] `python3 scripts/run_tests.py metrics_append` passes (new `runId` presence/round-trip case).
    - [ ] Full `python3 scripts/run_tests.py` stays green (AC-No-regression).
    - [ ] Manual: `python3 scripts/qrspi_critic_summary.py --run-id <id> <sample-ledger.jsonl>` prints JSON carrying `stepCount`, `timestampSpan`, `dissentRate`, `dissentRevisedRate`, `terminalActionCounts`, `perLens`.

---

## Slice 2: Cost-reduction — document the existing digest lever

### Setup

23. ⚠️ Modify `.qrspi/config.example.json` — add a commented/example `critics.design.digest.enabled: true` entry documenting how an operator opts into the existing RUS-77 digest lever. **No default flip** (default stays OFF). Keep the file valid JSON (if a JSON comment is not viable, add the key under a documented example block / sibling `_comment` key rather than breaking parse).
    - **Current:** `.qrspi/config.example.json` has no `critics.design.digest` example entry.
    - **After:** the file shows a discoverable `critics.design.digest.enabled` example with an accompanying note that the runtime default remains OFF.

### Core Logic

24. ✨ Create `docs/critic-cost-ab.md` — a markdown runbook documenting the manual, opt-in run-level digest-OFF vs digest-ON external-token A/B (the literal "measurably fewer tokens" measurement, externally observed like the ~749K figure). State explicitly: this is a documented procedure, NOT a deterministic test, and NOT wired into `run_tests.py`/CI. Cross-reference that the structural cost claim is already covered by the shipped RUS-77 tests `qrspi_research_digest_test.py:test_digest_strictly_shorter` and `qrspi_critics_config_test.py:test_digest_default_off`/`_enabled_true_parses` (cited, not re-created — design §Delta "NOT re-created").

### Tests

25. (No new automated test — the structural cost claim and config-resolution are covered by already-shipped RUS-77 tests, cited not re-created. This slice's verification is the JSON-validity check below plus the existing suite staying green.)

### Verify Slice 2

26. **Checkpoint:** `python3 -c "import json,sys; json.load(open('.qrspi/config.example.json'))" && python3 scripts/run_tests.py`
    - [ ] `.qrspi/config.example.json` parses as valid JSON and the `critics.design.digest.enabled` example is present/discoverable.
    - [ ] `python3 scripts/run_tests.py` stays green — confirms the already-shipped digest-size proxy + config-resolution tests still pass and nothing broke them.
    - [ ] Manual (opt-in): `docs/critic-cost-ab.md` is followed once if a reviewer wants the literal token figure; not part of CI.

---

## Slice 3: Teeth eval — flawed-design fixtures + pure assertion core + opt-in workflow runner

> **Mechanism correction (pinned above):** the design named `scripts/qrspi_teeth_eval.py`, but a lens is a registered `agentType` spawnable only from a **Workflow runner** (qrspi-batch.js:20–24) and Reads its inputs as files, so a `python3` script cannot drive it and `run_eval.py`'s tool-less single-turn seam cannot either. Slice 3 therefore ships: (1) four fixtures under `evals/teeth/`, (2) a pure CI-tested decision core `scripts/qrspi_teeth_assert.py`, (3) the workflow runner `.claude/workflows/qrspi-teeth-eval.js`. Steps renumbered accordingly.

### Fixtures

27. ✨ Create `evals/teeth/research.md` — companion research fixture documenting one identifiable, quotable fact (e.g. a named symbol `frobnicate_widget()` behaves as X). This is the fact the flawed design will contradict; it anchors the edge-alignment defect. The fact must be one a **correct** digest retains (so digest-ON the lens must still catch it) — structure §Contracts teeth lens→defect map, design review finding #1.
28. ✨ Create `evals/teeth/ticket.md` + `evals/teeth/questions.md` — the completeness lens anchors on ticket ACs (Reads `TICKET_CONTENT_PATH`) and answered questions (Reads `QUESTIONS_PATH`), so the omitted-AC defect must live in `ticket.md` (carry an AC with a unique marker, e.g. `AC-TEETH-COMPLETENESS`); `questions.md` is a minimal valid answered-questions fixture that the design fully covers (so completeness fails ONLY on the omitted AC, not on a question gap).
29. ✨ Create `evals/teeth/design.md` — single flawed design fixture carrying **three** clearly-labelled defects, each citing its unique marker: (a) silently omits `AC-TEETH-COMPLETENESS` from `ticket.md` → **completeness**; (b) a named internal contradiction (e.g. states a constant as two different values) → **internal-consistency**; (c) a claim contradicting the `frobnicate_widget()` fact in `evals/teeth/research.md` → **edge-alignment**. One combined fixture per OQ3 (reviewer: "single design"), each defect labelled so per-lens attribution stays unambiguous.

### Core Logic — pure assertion core (CI-tested)

30. ✨ Create `scripts/qrspi_teeth_assert.py` — pure decision core, no agents. `evaluate(trials_by_lens: dict[str, list[dict]], markers: dict[str, str], threshold: int = 2) -> dict` where each verdict is `{pass: bool, findings: list[str]}`: a trial **catches** iff `verdict["pass"] is False AND markers[lens] in some finding string`; a lens passes iff `caught >= threshold`. Returns `{perLens: {lens: {caught, total, pass}}, overallPass: all-lenses-pass}`. Add a thin `main(argv)` reading the trials JSON on stdin + markers/threshold args and printing the report JSON (the `synthesizeVerdicts` stdin pattern, qrspi-batch.js:972–986), so the workflow can call it via a worker.
31. ✨ Create `scripts/qrspi_teeth_assert_test.py` — stdlib `unittest` over synthetic verdicts: catch-via-marker-with-fail, no-catch-when-pass-true, no-catch-when-marker-absent, majority threshold (2-of-3 passes, 1-of-3 fails), `overallPass` aggregation. Auto-discovered by `run_tests.py`.

### Core Logic — opt-in workflow runner (off CI)

32. ✨ Create `.claude/workflows/qrspi-teeth-eval.js` — opt-in runner (REPLACES the infeasible `scripts/qrspi_teeth_eval.py`). `meta` with `name: 'qrspi-teeth-eval'`; `args.trials` default 3. Resolve the four `evals/teeth/*` fixture paths to absolute. **Build the digest** by spawning a worker that runs `python3 <engineCmd>scripts/qrspi_research_digest.py --research <evals/teeth/research.md> --out /tmp/teeth/research-digest.md && test -s …` (verbatim `buildResearchDigest` pattern, qrspi-batch.js:999–1004); fail loud if empty. **Fan out** `parallel()` over `{completeness, internal-consistency, edge-alignment} × trials`, each `agent({ agentType: 'qrspi-design-critic-<lens>', schema: CRITIC_VERDICT_SCHEMA })` with the SAME prompt shape `runCriticPanelLoop` uses (qrspi-batch.js:870–875): `DESIGN_PATH`/`TICKET_CONTENT_PATH`/`RESEARCH_PATH`/`QUESTIONS_PATH` + the threaded `DIGEST_PATH` line (digest-ON). Group verdicts by lens.
33. ⚠️ Modify `.claude/workflows/qrspi-teeth-eval.js` — hand the grouped verdicts + the per-lens markers + threshold (2) to `scripts/qrspi_teeth_assert.py` via a worker (the `synthesizeVerdicts` stdin worker pattern), and `return` its `{perLens, overallPass}` report augmented with `{digestOn: true, trials}`. The edge-alignment marker is the `frobnicate_widget()` fact present in `evals/teeth/research.md`, so a digest that trimmed it makes edge-alignment pass and `overallPass` go false (the non-vacuity / digest-risk-gating check, review finding #1).

### Verify Slice 3

34. **Checkpoint:** `python3 scripts/run_tests.py teeth_assert` (deterministic, in CI) **and** the opt-in workflow run.
    - [ ] `python3 scripts/run_tests.py teeth_assert` passes (the pure majority/marker core).
    - [ ] Manual (opt-in): `Workflow({name:"qrspi-teeth-eval", args:{trials:3}})` returns a report where completeness, internal-consistency, and edge-alignment each show `pass=false` naming their marker in ≥2-of-3 trials, `digestOn:true`, `overallPass:true`.
    - [ ] `python3 scripts/run_tests.py --list` does NOT list any teeth runner (the workflow lives in `.claude/workflows/`, outside the `scripts/*_test.py` glob — off the deterministic CI gate; AC-Teeth-eval, Q11).
    - [ ] Inspection: the edge-alignment marker references a fact present in `evals/teeth/research.md` that a correct digest retains (the non-vacuity / digest-risk check, review finding #1).

---

## Rollback Notes

- **Step 8 (`qrspi_metrics_append.py` `run_id` param):** the new parameter is required; reverting means removing the `run_id` parameter and the `"runId"` field. Because Step 10's JS call site passes it, revert Steps 8 and 10 together (and Step 9's constant) to avoid a call-site/signature mismatch that would break the append seam at runtime.
- **Step 9/10 (`qrspi-batch.js` call site):** edits touch only the append call site, not critic-loop control flow; revert by removing the `runId` constant and restoring the original append argument list. No data migration — the ledger is append-only and a missing `runId` on old lines is tolerated by the summarizer (`run_id` filter simply excludes them).
- **Step 23 (`.qrspi/config.example.json`):** config example only; no default-behavior change (default stays OFF). Revert by removing the example entry. No runtime config is altered (the example file is not the active `config.json`).
- **Steps 30–33 (teeth eval):** all-additive new files (`evals/teeth/*`, `scripts/qrspi_teeth_assert.py`/`_test.py`, `.claude/workflows/qrspi-teeth-eval.js`). No existing file is modified and nothing is wired into CI, so revert = delete the new files; the deterministic suite is unaffected either way (only the additive `teeth_assert` test joins `run_tests.py`).
- **No DB migrations and no destructive operations** in this plan. The ledger schema change is purely additive (one new field on new lines; existing lines unchanged).
