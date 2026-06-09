# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-09T00:00:00Z
**Generated:** 2026-06-09T00:00:00Z
**Status:** draft

## Q1: How does the eval harness resolve a fixture filename referenced by a case in `evals/suite.json` into a path under `evals/fixtures/`, and what exact load step errors when the file is absent?

**Answer:** Fixtures are referenced by each case as `context.files` entries written **relative to `evals/`** (e.g. `"fixtures/ticket_rest_endpoint.md"`, suite.json:23). The only code that resolves and loads them is `build_messages()` in `scripts/run_eval.py`. It does NOT join against `evals/fixtures/` — it passes the string straight to `os.path.exists()` and `open()`, so resolution is relative to the **process current working directory**. The harness must therefore be run from inside `evals/` for `fixtures/...` to resolve.

Critically, a missing fixture does NOT raise. `build_messages` guards every file with `if os.path.exists(file_path):` (run_eval.py:79), so an absent fixture is silently skipped — its content never enters the user message. There is no error, no warning, and no exit code on a missing fixture. (See Q14.)

**Evidence:**

```python
context_files = case.get("context", {}).get("files", [])
file_context_parts = []
for file_path in context_files:
    if os.path.exists(file_path):
        with open(file_path) as f:
            content = f.read()
        file_context_parts.append(f"--- {file_path} ---\n{content}")
```

— `scripts/run_eval.py:76-83`

**Dependencies:** `run_eval.py` → `os.path` (stdlib). `suite.json` `context.files` strings are the upstream contract. `grade.py` does NOT read fixtures (Q8).
**Implicit contracts:** Paths are relative (`fixtures/<name>`), so the harness must be invoked with cwd=`evals/`. A missing fixture degrades silently rather than failing — "loads cleanly" today means only "the path exists at load time."

## Q2: For the generate-then-curate path, what is the on-disk relationship between a source ticket and the artifact a phase agent produces, and where does a phase agent write its output before persistence?

**Answer:** This is the production QRSPI Fix-A staging flow, separate from the eval harness. A phase agent never writes the canonical `qrspi`-laden path. The `stg()` helper in `.claude/workflows/qrspi-batch.js` hands each phase a short, token-free staging path `/tmp/phase-stage/<id>/<artifact>.md`; the agent writes there (this research agent's own `OUTPUT_PATH` follows the same pattern). `scripts/qrspi_persist.py` then verifies the staged file is non-empty and moves it to the canonical `.worktrees/<id>/.qrspi/<id>/` destination. The source ticket likewise lands at a staging path first (`/tmp/phase-stage/<id>/ticket.md`, qrspi-batch.js:310).

The relationship between a source ticket fixture and a phase artifact in the **eval** fixtures is by **filename stem**, not a path link: `ticket_rest_endpoint.md` → `questions_rest_endpoint.md` → `research_rest_endpoint.md` → `design_rest_endpoint.md` → `structure_rest_endpoint.md` → `plan_rest_endpoint.md`. The suffix after the phase prefix is the shared "scenario" key.

**Evidence:**

```javascript
// Token-free staging path a phase agent writes its artifact to (Fix A). It carries
const stg = (id, name) => `/tmp/phase-stage/${id}/${name}.md`
```

— `.claude/workflows/qrspi-batch.js:238-241`

```text
Fix A removes the qrspi path from the model entirely. The phase agent writes its
artifact to a SHORT, token-free staging path it cannot corrupt
(`/tmp/phase-stage/<ticket>/<artifact>.md`), and THIS script ... owns the
canonical destination, moves the file there, and verifies it is non-empty.
```

— `scripts/qrspi_persist.py:17-22`

**Dependencies:** `qrspi-batch.js` (`stg`, `runPhase`) → `qrspi_persist.py` → `.worktrees/<id>/.qrspi/<id>/`. Eval fixtures do not use this flow; they are static files committed under `evals/fixtures/`.
**Implicit contracts:** Eval fixture naming is `<phase>_<scenario>.md`; a curated fixture is the gold-standard OUTPUT of running that phase agent on the prior phase's fixture for the same scenario.

## Q3: Which existing 4 ticket fixtures are already present in `evals/fixtures/`, and what naming and content conventions do they establish for the 17 missing files?

**Answer:** The four present fixtures are all `ticket_*.md`:
- `ticket_rest_endpoint.md` (DASH-417, scenario `rest_endpoint`)
- `ticket_websocket.md` (ORD-892, scenario `websocket`)
- `ticket_multi_tenancy.md` (PLAT-1205, scenario `multi_tenancy`)
- `ticket_15_acceptance_criteria.md` (RPT-2100, scenario `15_acceptance_criteria`)

**Naming convention:** `<phase>_<scenario>.md`, snake_case, phase prefix first. Variants append a suffix: `_slice1` (per-slice), `_broken_contract` / `_sparse` (adversarial), `_session1` / `_session_broken_contract` (worktree sessions). One non-`.md` fixture exists by reference: `git_diff_rest_endpoint.txt`.

**Content convention (from the 4 tickets):** H1 `# Ticket: <ID>`; then `## Title`, `## Description`, `## Acceptance Criteria` (as `- [ ]` checkboxes), `## Constraints`, `## Out of Scope`. Tickets are 850–1626 bytes. The `rest_endpoint` ticket is deliberately simple (4 ACs, 2 constraints); `multi_tenancy` is hard (7 ACs, isolation-heavy); `15_acceptance_criteria` stress-tests the 15-question ceiling (16 ACs); `websocket` introduces a NEW PATTERN (real-time vs existing polling).

**Evidence:**

```text
# Ticket: DASH-417
## Title
Add user preference endpoint for notification and display settings
...
## Acceptance Criteria
- [ ] GET /api/users/:id/preferences returns notification and display prefs
- [ ] Response time < 200ms at p95
```

— `evals/fixtures/ticket_rest_endpoint.md:1-16`

**Dependencies:** Downstream phase fixtures must internally reference these ticket IDs and ACs to be consistent (e.g. design `Desired End State` maps ACs from the matching ticket).
**Implicit contracts:** Scenario stems are load-bearing: a case wires ticket+questions+research of the same stem together (case_005 loads all three `_rest_endpoint` files). Fixtures must use the same ticket ID and ACs across the chain.

## Q4: What is the full list of fixture filenames each eval case references, and does it match the 17 names in the ticket exactly?

**Answer:** suite.json references **21 distinct** `fixtures/*` paths; **4 exist** (the tickets), **17 are missing**. The 17 missing exactly match the list enumerated in `docs/eval-system.md:80-89`. Computed via `comm -23` of distinct refs vs. on-disk files:

Missing (17): `design_billing_migration.md`, `design_rest_endpoint.md`, `git_diff_rest_endpoint.txt`, `impl_log_complete.md`, `plan_broken_contract_slice1.md`, `plan_rest_endpoint.md`, `plan_rest_endpoint_slice1.md`, `questions_multi_tenancy.md`, `questions_rest_endpoint.md`, `questions_websocket.md`, `research_multi_tenancy_sparse.md`, `research_rest_endpoint.md`, `research_websocket.md`, `structure_broken_contract.md`, `structure_rest_endpoint.md`, `worktree_session1.md`, `worktree_session_broken_contract.md`.

**Evidence:**

```text
fixtures/design_billing_migration.md      ← case_008
fixtures/design_rest_endpoint.md          ← case_005, case_007(?no), case_009, case_013
fixtures/git_diff_rest_endpoint.txt       ← case_013
...
17 missing
```

— `evals/suite.json` (refs) cross `evals/fixtures/` (have); doc list at `docs/eval-system.md:80-89`

**Dependencies:** Each missing fixture is consumed by ≥1 case `context.files`. Note `design_rest_endpoint.md`, `questions_rest_endpoint.md`, `structure_rest_endpoint.md` are each referenced 3×; `ticket_rest_endpoint.md`, `ticket_multi_tenancy.md`, `questions_websocket.md`, `worktree_session1.md` 2×.
**Implicit contracts:** The doc's 17-name list and suite.json are in agreement (no drift). The ticket's "17 missing" therefore maps 1:1 to suite references.

## Q5: What format and required sections does each phase's artifact template define, so a curated fixture matches the gold-standard shape its consuming case expects?

**Answer:** Templates live in `.qrspi/templates/`. Required sections per phase (these are also the sections asserted by `has_section(...)` checks in suite.json):

- **questions.md** (template): `## Data Flow`, `## API Surface`, `## State Management`, `## Edge Cases`, `## Testing`, `## Observability`. Questions are `- QN: ...` lines each with `**Target:**`. Suite asserts `>=8` and `<=15` questions, `has_section 'Observability'`, `section_question_count('Edge Cases') >= 2`, `all_questions_have_target`, `no_solution_language`.
- **research.md** (template): per-Q `**Answer:** / **Evidence:** / file:line citation / **Dependencies:** / **Implicit contracts:**`, plus `## Discovered Patterns` and `## Inconsistencies`. Suite asserts those two sections, `all_questions_answered`, `all_answers_have_evidence`, `all_evidence_has_file_citations`, `code_snippets_under_limit(20)`.
- **design.md** (template): `## Current State` (every claim `(ref: QN)`), `## Desired End State`, `## Delta`, `## Pattern Decisions` (Option A/B table), `## Risk Register` (table), `## Open Questions`. Suite asserts all six sections, `current_state_has_citations`, `no_code_blocks`, `risk_register_min_entries(2)`, `pattern_decisions_have_options(2)`, `line_count<=300`, `NEW PATTERN?` flag.
- **structure.md** (template): `## New Types`, `## Modified Types`, `## Contracts`, per-slice `## Slice N` with `**Goal/Files touched (✨/⚠️)/Verification/Context cost/Depends on**`, `## Unverified Assumptions`. Suite asserts `slice_count>=2` (case_008 `>=5`), `all_slices_have_verification`, `all_slices_have_context_cost`, `no_slice_exceeds_file_limit(10)`, `all_files_marked_new_or_modify`.
- **plan.md** (template): per-slice `### Setup/Core Logic/Tests/Verify Slice N`, numbered atomic steps, `**Current:**`/`**After:**` on modify steps, `**Checkpoint:**` per slice, `## Rollback Notes`. Suite asserts `total_steps<=100`, `all_modify_steps_have_current_after`, `all_slices_have_verify_checkpoint`, `all_steps_are_atomic`.
- **worktree.md** (template): header `**Critical path:**`, `## Session N` with `**Load:**`/`**Estimated context:**`, task table `| Task ID | Description | Depends On | Plan Step | Cost | Status |`, `--- SESSION BOUNDARY ---` + `**Reason:**`. Suite asserts `has_critical_path`, `all_tasks_have_required_fields`, `session_boundaries_have_reasons`, `sessions_have_load_manifests`.
- **impl-log.md** (template, consumed via `impl_log_complete.md`): per-session `**Tasks completed/failed/Tests/Deviations from structure.md/Deviations from plan.md/Notes**`. (case_013 asserts AC mapping in `pr-summary.md`, but `impl_log_complete.md` is its input.)
- **pr-summary.md** (template): `## Summary`, `## Acceptance Criteria Mapping`, `## Changes by Slice`, `## Testing Summary`, `## Deviations from Structure`, `## Risks & Rollback`, `## Open Items`.

**Evidence:**

```text
## Current State
<...EVERY claim must cite a research.md section: "(ref: Q1)", "(ref: Q3)".>
## Desired End State
## Delta
## Pattern Decisions
## Risk Register
## Open Questions
```

— `.qrspi/templates/design.md:8-45`

**Dependencies:** Fixtures are templates filled with scenario-specific content. The fixture must satisfy the consuming case's `has_section`/structural assertions even though those assertions today run against agent OUTPUT, not the fixture (Q8) — but golden/reference fixtures should still match shape.
**Implicit contracts:** Section headings are matched case-insensitively by substring regex `^#+\s+.*<heading>` (grade.py:30), so heading text must contain the asserted phrase. `git_diff_rest_endpoint.txt` has no template — it is a raw unified-diff input.

## Q6: How is the mapping between an eval case and its phase under test recorded, so the 11 currently-erroring cases can be tied back to the missing fixture each requires?

**Answer:** Each case records `"phase"` explicitly (e.g. case_001 `"phase": "questions"`, suite.json:19) and lists its inputs in `context.files`. The phase→cases table is also mirrored in `docs/eval-system.md:17-26`. The "11 erroring cases" are those whose `context.files` include ≥1 missing fixture. Cross-referencing: case_001/002/015 (questions) use only ticket fixtures that EXIST → they are the cases that do NOT error on fixtures. All other cases (003–014) reference ≥1 missing fixture, i.e. **12** cases touch a missing fixture, but case_004/006/014 share missing fixtures with others. (The ticket's "11" likely excludes one; flagged in Inconsistencies.)

**Evidence:**

```json
{ "id": "case_001", "name": "questions_happy_path", "phase": "questions",
  "context": { "files": ["fixtures/ticket_rest_endpoint.md"], ... } }
```

— `evals/suite.json:16-25`

**Dependencies:** `phase` field + `context.files` are the only mapping. No separate manifest ties a case to "the fixture it errors on."
**Implicit contracts:** A case is exercisable iff every `context.files` entry exists; the phase label is descriptive metadata, not enforced. See Inconsistencies for the 11-vs-12 count.

## Q7: Where does the harness expect the `.txt` diff fixture versus the `.md` artifact fixtures, and is the load path branch by extension?

**Answer:** Same directory (`evals/fixtures/`) and same loader. `build_messages` (run_eval.py:76-83) does NOT branch on extension — it `open()`s and `read()`s every `context.files` entry as text and concatenates it under a `--- <path> ---` header regardless of `.md` vs `.txt`. `git_diff_rest_endpoint.txt` is loaded identically to the `.md` fixtures; only case_013 references it.

**Evidence:**

```python
for file_path in context_files:
    if os.path.exists(file_path):
        with open(file_path) as f:
            content = f.read()
        file_context_parts.append(f"--- {file_path} ---\n{content}")
```

— `scripts/run_eval.py:78-83`

**Dependencies:** None extension-specific. `check_scope.py` (used by case_011's `script` assertion) is a separate executable, not a fixture loader.
**Implicit contracts:** All `context.files` are UTF-8 text readable by `open().read()`. The `.txt` diff must be a plain unified diff (no template), used as raw context.

## Q8: What does "loads cleanly" mean concretely — file existence/non-emptiness only, or parse/schema-check?

**Answer:** For the eval harness, "loads cleanly" = the path exists at `build_messages` time so its content is included. There is NO parsing, schema check, or non-empty check on fixtures inside `run_eval.py`. `load_suite` validates the SUITE schema (`name`, `cases`, and per-case `id`/`prompt`/`assertions`) but never the fixtures (run_eval.py:42-58). `grade.py` checks run against the agent's produced `result["output"]`/`result["files"]`, not the fixture files (grade.py:21-40). So a fixture that exists but is empty still "loads" — it just contributes an empty content block.

The production persist path (`qrspi_persist.py`) DOES enforce non-empty, but that governs phase artifacts in worktrees, not eval fixtures.

**Evidence:**

```python
required = {"name", "cases"}
missing = required - set(suite.keys())
if missing:
    raise ValueError(f"Suite missing required fields: {missing}")
for case in suite["cases"]:
    case_required = {"id", "prompt", "assertions"}
```

— `scripts/run_eval.py:47-53`

**Dependencies:** Suite schema validation in `load_suite`; no fixture validation anywhere in the harness.
**Implicit contracts:** Fixtures are trusted to be well-formed; correctness of their content is unverified by code. Any "loads cleanly" gate beyond existence would be NEW behavior.

## Q9: How are the "broken" fixtures expected to differ from passing counterparts, and does any case assert failure against them?

**Answer:** The broken fixtures (`structure_broken_contract.md`, `plan_broken_contract_slice1.md`, `worktree_session_broken_contract.md`) are inputs to **case_012** (`implement_deviation_reporting`, `"difficulty": "hard"`, `"split": "test"`). The case prompt states "The type signature in structure.md will not work as-is — report the deviation" (suite.json:606). The assertions do NOT assert that the harness/grader fails; they assert the AGENT correctly reports the deviation: `impl_log_has_deviations('impl-log.md')` (weight 2.0) and an llm_judge that the agent "stopped and reported the contract deviation rather than silently changing the type signature" (weight 3.0). So "broken" means the fixture's structure/plan contains an intentionally infeasible contract; success = the agent flags it, not a harness error.

**Evidence:**

```json
"prompt": "Implement the tasks assigned to this session. The type signature in
 structure.md will not work as-is — report the deviation.",
"context": { "files": ["fixtures/worktree_session_broken_contract.md",
 "fixtures/structure_broken_contract.md", "fixtures/plan_broken_contract_slice1.md"] },
...
{ "check": "impl_log_has_deviations('impl-log.md')", "weight": 2.0 }
```

— `evals/suite.json:606-627`

**Dependencies:** The three broken fixtures form a self-consistent chain (same broken contract referenced across structure→plan→worktree-session).
**Implicit contracts:** The broken fixture must contain a contract/type signature that is genuinely unimplementable as written, so the agent has something concrete to deviate on. No assertion expects a non-zero exit or parse failure; the "failure" is behavioral, judged on the agent's output.

## Q10: For multi-slice plan fixtures, what distinguishes the whole-plan fixture from the per-slice fixture, and which case consumes each?

**Answer:** `plan_rest_endpoint.md` (whole plan) is consumed by **case_010** (`worktree_session_boundaries`, phase worktree) — the worktree agent needs the FULL multi-slice plan to compute session boundaries and a critical path (suite.json:517). `plan_rest_endpoint_slice1.md` (per-slice) is consumed by **case_011** (`implement_scope_enforcement`, phase implement) — the implement agent receives only the one slice it is scoped to (suite.json:567-574), enforcing scope (`check_scope.py`). So the whole-plan fixture contains all slices' Setup/Core/Tests/Verify; the per-slice fixture is just Slice 1's steps, matching what a single implementation session loads.

**Evidence:**

```json
// case_010 (worktree): full plan
"context": { "files": ["fixtures/plan_rest_endpoint.md"] }
// case_011 (implement): single slice
"context": { "files": ["fixtures/worktree_session1.md",
  "fixtures/structure_rest_endpoint.md", "fixtures/plan_rest_endpoint_slice1.md"] }
```

— `evals/suite.json:517-519, 567-574`

**Dependencies:** `plan_rest_endpoint_slice1.md` should be a faithful subset of `plan_rest_endpoint.md` (Slice 1 only) so the implement and worktree fixtures stay consistent.
**Implicit contracts:** Per-slice fixtures carry the suffix `_slice1`; the whole-plan fixture has none. `plan_broken_contract_slice1.md` follows the same per-slice convention for the adversarial chain.

## Q11: Does any fixture name in the ticket NOT have a referencing case (or vice versa), leaving an orphaned/unmet reference?

**Answer:** No orphans in either direction. All 21 distinct fixture references in suite.json are accounted for; the 17 missing ones each have ≥1 consuming case (Q4 mapping). Conversely, every fixture named in `docs/eval-system.md:80-89` appears as a `context.files` entry in suite.json. There is no fixture referenced only by the doc, and no missing fixture lacking a case. The doc's 17-name list and suite.json's missing set are identical (verified by set comparison).

One nuance: `worktree_session_broken_contract.md` is consumed by case_012 (implement), not a worktree-phase case — the `worktree_session_` prefix names the artifact TYPE (a worktree session fixture), not the consuming phase. Not an orphan, but a naming/phase cross-reference worth noting.

**Evidence:**

```text
comm -23 (suite refs) (on-disk)  →  17 lines
== docs/eval-system.md:80-89 enumerated list  (identical set)
```

— derived from `evals/suite.json` and `docs/eval-system.md:80-89`

**Dependencies:** suite.json `context.files` ↔ doc list ↔ `evals/fixtures/`.
**Implicit contracts:** The doc is currently in sync with the suite; any new fixture must be added to both to avoid drift (no automated check enforces this — see Q13).

## Q12: How is the harness currently exercised given it is a "non-functional placeholder," and what command/test demonstrates a fixture loads cleanly?

**Answer:** `run_eval.py` is a CLI: `python3 scripts/run_eval.py --skill <path> --suite evals/suite.json --output <dir>` (run_eval.py:217-236). It runs but produces zeros — `execute_single` is a stub that sets `result.output = ""` and never invokes an agent (run_eval.py:117-137; confirmed by `docs/eval-system.md:97,108`). There is NO `run_eval_test.py` sibling (`ls scripts/ | grep run_eval` → only `run_eval.py`). The only way to demonstrate a fixture "loads cleanly" today is to invoke `build_messages(case)` directly (or run the CLI from cwd `evals/`) and confirm the fixture content appears in the assembled user message — there is no existing test that does this.

**Evidence:**

```python
messages = build_messages(case)
result.output = ""
result.files = []
result.tokens = {"input": 0, "output": 0}
```

— `scripts/run_eval.py:132-135`

**Dependencies:** CLI args `--skill/--suite/--output`. `run_suite` writes `results.json` to `--output`.
**Implicit contracts:** Must be run with cwd=`evals/` for relative `fixtures/...` to resolve (Q1). The harness is documented non-functional; manual e2e + unit tests are the verification path per project conventions (CLAUDE.md, MEMORY.md "eval-harness-placeholder").

## Q13: Are there existing stdlib-only unit tests covering fixture presence or suite-to-fixture reference integrity?

**Answer:** NO. `grep -rlE 'fixtures|suite\.json|run_eval' scripts/*_test.py` returns nothing. The project's `_test.py` files (`scripts/qrspi_*_test.py`) cover the PR-gated resolver/persist/pr_state logic, not the eval harness. No test asserts that every `context.files` reference in suite.json exists on disk, nor that fixtures are non-empty or shape-valid. This is a gap: the 17 missing fixtures are not caught by any automated check today.

**Evidence:**

```text
$ ls scripts/ | grep -iE 'run_eval|fixture'  →  run_eval.py   (no _test.py)
$ grep -rlE 'fixtures|suite\.json|run_eval' scripts/*_test.py  →  (empty)
```

— shell verification over `scripts/`

**Dependencies:** None — no test references the eval harness or fixtures.
**Implicit contracts:** Per CLAUDE.md, harness changes are "verified with unit tests + manual e2e," but no such fixture-integrity test currently exists.

## Q14: When a fixture fails to load today, what does the harness emit, and how would an operator identify which of the 11 cases errored on which missing file?

**Answer:** Nothing. A missing fixture is silently skipped by the `if os.path.exists(file_path):` guard (run_eval.py:79) — no exception, no log line, no exit-code change. The case still "runs" with the fixture's content simply absent from the prompt. The per-case console line printed by `run_suite` ("OK"/"ERROR") reflects only whether `execute_single` raised (run_eval.py:186-187); since the stub never reads the missing file, it never raises, so a missing fixture reports **OK**. There is therefore NO way today for an operator to identify which case lost which fixture from harness output. They must manually diff `suite.json` `context.files` against `ls evals/fixtures/` (the `comm` approach used in this research).

**Evidence:**

```python
result = future.result()
all_results.append(asdict(result))
status = "ERROR" if result.error else "OK"
print(f"  [{completed}/{total_runs}] {case_id} trial={trial} {status} ...")
```

— `scripts/run_eval.py:184-187`

**Dependencies:** `result.error` is set only inside `execute_single`'s try/except (run_eval.py:139-140), which the stub never triggers on missing fixtures.
**Implicit contracts:** "ERROR" status means an execution exception, not a missing input. Surfacing missing-fixture failures would require NEW code (e.g. raising in `build_messages` or a pre-flight integrity check).

---

## Discovered Patterns

- **Scenario-stem chaining:** Fixtures share a scenario stem across phases (`rest_endpoint`, `websocket`, `multi_tenancy`, plus `billing_migration`, `15_acceptance_criteria`). A case wires same-stem fixtures together (case_005 loads ticket+questions+research for `rest_endpoint`). Curated fixtures must keep the ticket ID and ACs consistent down the chain.
- **Variant suffixes** encode fixture purpose: `_slice1` (per-slice subset), `_broken_contract` (adversarial-infeasible), `_sparse` (deliberately thin research for fabrication-detection, case_014), `_session1`/`_session_broken_contract` (worktree session slices).
- **Grader operates on agent output, not fixtures:** every `grade.py` check reads `result["output"]`/`result["files"]`. Fixtures are pure INPUT context; their shape is never validated by code, only by the templates a human follows when authoring them.
- **Section matching is loose:** `has_section` uses `^#+\s+.*<heading>` case-insensitive substring (grade.py:27-32). A heading need only CONTAIN the asserted phrase. Fixture authors should still use the exact template headings.
- **Two distinct persistence worlds:** production phase artifacts use the Fix-A staging→`qrspi_persist.py` non-empty-verified move; eval fixtures are static committed files with no such gate. Do not conflate them.
- **`graphite-evals.json`** is a separate 5-case suite for the Graphite skill (eval-system.md:30) — not in scope for the 17 fixtures.

## Inconsistencies

- **"11 erroring cases" vs. 12 cases touching missing fixtures.** The questions phase frames "11 currently-erroring cases." By set analysis, cases that reference ≥1 missing fixture are case_003–case_014 = **12** cases (only case_001, case_002, case_015 use solely existing ticket fixtures). The discrepancy of 1 is unexplained by code; possibly the ticket counts cases that error *and* are runnable, or excludes a stub-only case. Flagged — the count "11" is not derivable from suite.json alone, which yields 12.
- **Doc says "4 of 21 referenced fixtures exist" → 17 missing** (eval-system.md:80, 102). This is internally consistent and matches the on-disk `comm` result (21 distinct refs, 4 present, 17 missing). No drift between doc and suite here.
- **Missing fixtures fail SILENTLY (Q1/Q14):** the harness's `os.path.exists` guard means a missing fixture is not an error today — contradicting the intuitive reading of "11 erroring cases." Cases do not actually error on the missing file; they would run with empty context. The "error" is conceptual (incomplete suite), not a runtime exception.
- **`worktree_session_broken_contract.md` is consumed by an `implement`-phase case** (case_012), not a worktree-phase case — its `worktree_session_` prefix names the artifact type, not the consuming phase. Mildly inconsistent with the "phase prefix" reading of other fixtures.
- **No automated suite↔fixture integrity test** (Q13) despite CLAUDE.md's "verify with unit tests" convention — the 17 missing fixtures slipped in undetected because nothing checks reference completeness.
- **Relative-path coupling (Q1):** suite.json uses `fixtures/...` relative paths resolved against cwd, but nothing documents or enforces cwd=`evals/`. Running from repo root would silently skip ALL fixtures (every `os.path.exists` false), making even existing fixtures "missing" — an undocumented operational footgun.
