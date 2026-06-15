# Implementation Log — Critic effectiveness: instrumentation, cost reduction, and teeth eval

## Session 1 — Slice 1: Instrumentation (runId field + critic summarizer)

**Timestamp:** 2026-06-15T19:47:22Z
**Tasks completed:** T1, T2, T3, T4, T5, T6, T7, T8, T9, T10, T11, T12, T13, T14, T15, T16, T17, T18, T19, T20, T21, T22
**Tasks failed:** none
**Tests:**

- `python3 scripts/run_tests.py critic_summary` → 1 file passed (qrspi_critic_summary_test.py), 0 failed
- `python3 scripts/run_tests.py metrics_append` → 1 file passed (qrspi_metrics_append_test.py), 0 failed
- `python3 scripts/run_tests.py` → 38 passed, 0 failed (full suite, no regression)
- Manual: `python3 scripts/qrspi_critic_summary.py --run-id run-A <sample-ledger.jsonl>` printed JSON carrying `stepCount`, `timestampSpan`, `dissentRate`, `dissentRevisedRate`, `terminalActionCounts`, `perLens` (with `lens:null` rolled under `"edge"`), and `abortedRecords` (truncated trailing line counted). `--run-id` correctly excluded the other run's lines.

**Deviations from structure.md:**

- none. `load_ledger(path) -> list[dict]` is exact; aborted-record counting is exposed to the CLI via the sibling `_read_lines(path) -> (list[dict], int)` helper (explicitly sanctioned by plan step 3 / structure note in §Contracts).

**Deviations from plan.md:**

- none material. Plan step 9 pinned `const runId = process.env.QRSPI_RUN_ID || crypto.randomUUID()`. Implemented with the project's defensive `typeof`-guard style (matching the existing ENGINE_ROOT constant) plus a timestamp+random string fallback when webcrypto is absent in the sandbox — preserves the "always a string" contract without changing the env-var-first / generated-id semantics. `crypto` is a global (Node webcrypto), so no explicit import was needed.

**Notes for next session:**

- The appender's `--run-id` is now a REQUIRED argument (no default). Any future caller of `scripts/qrspi_metrics_append.py` MUST pass `--run-id`; the only call site (`.claude/workflows/qrspi-batch.js` `recordCriticMetrics`, ~line 1080) was updated to thread the module-level `runId` constant.
- The module-level `runId` constant lives just after `const SKILL = ...` near the top of `qrspi-batch.js` (the imperative shell). Source precedence: `process.env.QRSPI_RUN_ID` → `crypto.randomUUID()` → `run-<ts>-<rand>` fallback.
- `CriticSummary` `perLens` key convention: lens string verbatim, with `lens === null` (the single edge critic) rolled under the literal key `"edge"`. `dissentRevisedRate` is the named revise-ATTEMPTED proxy (docstringed), not an artifact-changed measure.
- Slice 1 has no `pr-summary.md` yet (that is the qrspi-pr phase after all slices). Slices 2 and 3 are independent (`Depends on: none`) and touch disjoint files (config.example.json / docs vs. evals + teeth assert), so no cross-slice coupling from this slice.

---

## Session 2 — Slice 2: Cost-reduction (document the existing digest lever)

**Timestamp:** 2026-06-15T20:31:00Z
**Tasks completed:** T23, T24, T25, T26
**Tasks failed:** none
**Tests:**

- `python3 scripts/run_tests.py` → 38 passed, 0 failed (full suite, no regression)
- `python3 scripts/run_tests.py research_digest` → 1 file passed (cited RUS-77 `test_digest_strictly_shorter` et al.)
- `python3 scripts/run_tests.py critics_config` → 1 file passed (cited RUS-77 `test_digest_default_off` / `test_digest_enabled_true_parses`)
- Manual: `python3 -c "import json; json.load(open('.qrspi/config.example.json'))"` parses; asserted `critics.design.digest.enabled` is still `false` (no default flip) AND the opt-in example (`$comment_optin`) is present/discoverable.
- Manual: `test -s docs/critic-cost-ab.md` → runbook present, non-empty.

**Deviations from structure.md:**

- none material. Structure §Slice 2 said "add a commented/example `critics.design.digest.enabled: true` entry." The file ALREADY shipped a `critics.design.digest` block (`enabled: false`, mirroring the runtime default) plus a `$comment_cost_levers` note from RUS-77. To satisfy the contract's hard "**No default flip** (default stays OFF)" while making opt-in discoverable, I did NOT set the live `enabled` value to `true` (that would have flipped the default-mirror); instead I added a `$comment_optin` sibling INSIDE the `digest` block that documents the literal opt-in (`"digest": { "enabled": true }`) and points at the cited RUS-77 tests and the runbook. This keeps valid JSON (the structure-sanctioned `_comment` sibling fallback, plan step 23) and preserves OFF as the mirrored default. The discoverability + no-flip ACs both hold.

**Deviations from plan.md:**

- none material. Plan step 24 pinned the runbook home as `docs/critic-cost-ab.md` (markdown, not a script) — created exactly there. Plan step 23's `_comment` sibling fallback was used (see structure deviation above). Plan step 25 is an explicit no-op (no new automated test by design — the structural cost claim is cited via the shipped RUS-77 tests, not re-created).

**Notes for next session:**

- Slice 2 is config/docs only — zero code or default-behavior change. The runtime default for the digest lever remains OFF; only the example file and a new runbook were added/edited. No new automated test was introduced (intentional, per plan step 25).
- The opt-in example lives at `.qrspi/config.example.json` → `critics.design.digest.$comment_optin` (a doc-only `$comment*` key the harness ignores); the live `digest.enabled` stays `false`. The runbook is `docs/critic-cost-ab.md` (manual A/B, explicitly OFF the CI gate).
- Slice 3 (teeth eval) is independent (`Depends on: none`) and touches disjoint files (`evals/teeth/*`, `scripts/qrspi_teeth_assert.py` + `_test.py`, `.claude/workflows/qrspi-teeth-eval.js`). No coupling to Slice 2. Note: the worktree.md Session-3 table still names the OLD `scripts/qrspi_teeth_eval.py` layout (T29/T30); the AUTHORITATIVE layout is the corrected one in structure.md §Contracts / plan.md §Plan-phase pins (workflow runner `.claude/workflows/qrspi-teeth-eval.js` + pure CI-tested `scripts/qrspi_teeth_assert.py`). Follow structure/plan, not the stale worktree task descriptions.
- Cited RUS-77 tests confirmed green this session: `qrspi_research_digest_test.py` and `qrspi_critics_config_test.py` both pass under `run_tests.py`. Full suite still 38/38.

---

## Session 3 — Slice 3: Teeth eval (flawed-design fixtures + pure assertion core + opt-in workflow runner)

**Timestamp:** 2026-06-15T21:10:00Z
**Tasks completed:** T27, T28, T29, T30, T31, T32, T33, T34 (plan steps 27–34)
**Tasks failed:** none
**Tests:**

- `python3 scripts/run_tests.py teeth_assert` → 1 file passed (`qrspi_teeth_assert_test.py`), 0 failed (the pure majority/marker core — deterministic, in CI)
- `python3 scripts/run_tests.py` → 39 passed, 0 failed (full suite; +1 vs prior 38, the new `qrspi_teeth_assert_test.py`; no regression, AC-No-regression)
- `node scripts/check_workflows.js .claude/workflows/*.js` → 2 ok, 0 failed (both `qrspi-batch.js` and the new `qrspi-teeth-eval.js` compile under the harness loader)
- `python3 scripts/run_tests.py --list | grep -i teeth` → lists `qrspi_teeth_assert_test.py` (and the pre-existing RUS-77 `qrspi_teeth_test.py`); NO `.js` workflow appears — the runner stays off the deterministic CI gate (AC-Teeth-eval, Q11).
- Inspection (non-vacuity / digest-risk, review finding #1): built the digest from the new fixture — `python3 scripts/qrspi_research_digest.py --research evals/teeth/research.md --out /tmp/x` then grep — the `frobnicate_widget()` fact and its "synchronous and idempotent" prose SURVIVE the digest (it lives in prose, not a fenced block; the digest strips only fences). So a correct digest retains the edge-alignment fact and the lens still catches it digest-ON; a digest that trimmed it would make edge-alignment pass and `overallPass` go false.
- Manual (opt-in, NOT run here — requires `Workflow({name:"qrspi-teeth-eval", args:{trials:3}})` agent spawning, off CI): deferred. The deterministic decision math it relies on is fully CI-covered by `qrspi_teeth_assert_test.py`.

**Deviations from structure.md:**

- none material. Followed the AUTHORITATIVE corrected layout (structure §Contracts / plan §Plan-phase pins), NOT the stale worktree.md Session-3 table (which still named `scripts/qrspi_teeth_eval.py`). Shipped: 4 fixtures under `evals/teeth/` (`design.md`, `research.md`, `ticket.md`, `questions.md`), the pure CI-tested `scripts/qrspi_teeth_assert.py` (+ `_test.py`), and the opt-in workflow runner `.claude/workflows/qrspi-teeth-eval.js`.

**Deviations from plan.md:**

- none material. Plan step 30 pinned `evaluate(trials_by_lens, markers, threshold=2)` — implemented exactly, with a fail-closed catch rule (`pass is False AND marker ∈ some finding`) and a guarded non-positive-threshold fallback to 2 (a non-positive threshold would let a lens "pass" with zero catches). The workflow derives `THRESHOLD = floor(trials/2)+1` so the default `trials:3` yields the structure's ">=2-of-3" (2); a custom trial count still gets an integer majority. The workflow uses its own local `ENGINE_ROOT`/`engineCmd` (no per-ticket worktree here — the eval runs against the engine's own `evals/teeth/` fixtures), mirroring qrspi-batch.js's constant.

**Notes for next session:**

- Slice 3 is all-additive: `evals/teeth/{design,research,ticket,questions}.md`, `scripts/qrspi_teeth_assert.py` + `_test.py`, `.claude/workflows/qrspi-teeth-eval.js`. NO existing file modified. Only `qrspi_teeth_assert_test.py` joins CI (suite is now 39).
- DISTINCT from the pre-existing RUS-77 `scripts/qrspi_teeth_test.py` (a structural fixture check over `evals/fixtures/`, untouched, out of scope). My core is `scripts/qrspi_teeth_assert.py` — different name, different fixture dir (`evals/teeth/`).
- The lens→marker ownership map (single source: both the workflow's `LENS_MARKERS` and the test's `MARKERS`): completeness→`AC-TEETH-COMPLETENESS` (omitted AC, lives in `ticket.md`), internal-consistency→`TEETH-INCONSISTENCY` (`MAX_RETRIES` stated as both 3 and 5 in `design.md`), edge-alignment→`frobnicate_widget()` (design claims it's async; research verifies sync+idempotent). If a fixture marker changes, update BOTH the fixture text and the map.
- The opt-in eval has not been run end-to-end (agent spawning is off-CI and non-deterministic). All deterministic pieces verified. After all slices, the qrspi-pr phase writes `pr-summary.md`.

---
