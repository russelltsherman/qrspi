# Design — Implement meta-agent diagnosis + revision loop

**Ticket:** RUS-40
**Research basis:** research.md @ 2026-06-09T00:00:00Z
**Generated:** 2026-06-09T00:00:00Z
**Status:** draft

## Current State

The optimization loop is structurally a no-op. `categorize_failure(failure, skill_text)` takes two in-memory arguments and classifies failures using string-matching heuristics; it receives no transcripts at all — only a per-assertion `evidence` string lifted from the first trial of `grades.json` (ref: Q1). Its docstring sketches the intended meta-agent call as `meta_agent.complete(system=DIAGNOSIS_PROMPT, messages=[...])`, but `DIAGNOSIS_PROMPT` and `meta_agent` are defined nowhere (ref: Q5). It returns `{case_id, score, categories, failed_assertions, regression_risk}` (ref: Q4).

`propose_revisions(skill_text, diagnosis)` iterates `diagnosis["recommendations"]` and emits one revision per recommendation, but every edit is hard-coded `old_text=None`/`new_text=None` with `type="pending_meta_agent"`; `skill_text` is used only for risk assessment, never to locate edit anchors (ref: Q2). Because no concrete edit is ever produced, `apply_revisions` — which locates edits by literal substring match and applies `modified.replace(old_text, new_text, 1)` — always falls to its "pending" branch and returns the text unchanged (ref: Q4, Q7). Consequently `revise_skill` always returns `pending_meta_agent`, the skill file is never rewritten, and every iteration re-scores an identical skill, so the loop cannot converge (ref: Q12).

`run_loop.sh` chains the stages by files on disk: `run_eval.py` → `results.json`, `grade.py` → `grades.json`, `diagnose.py` reads `grades.json` and writes `diagnosis.json`, `revise.py` reads `diagnosis.json` and writes **in place to `SKILL_PATH`** (output path equals input path) — that in-place overwrite is the only persistence mechanism between iterations; there is no snapshot or rollback (ref: Q3, Q8). The loop never branches on `revise.py`'s `pending_meta_agent` status and `set -euo pipefail` aborts on any non-zero exit (ref: Q3, Q12).

Dry-run mode exists only in `revise.py` (`--dry-run` skips `apply_revisions` and skips writing the skill, but still appends to `revision-log.json`); `diagnose.py` has no dry-run concept and always writes `diagnosis.json` (ref: Q9). `run_loop.sh` never passes `--dry-run` (ref: Q9). There is no LLM client, wrapper, or invocation pattern anywhere in the repo — `run_eval.py:execute_single` and `grade.py:run_llm_judge` are likewise stubs returning empty/placeholder values; the only documented invocation path is the `using-claude-cli` skill, which no code uses (ref: Q6). The dominant codebase pattern is "stub-with-pseudocode-docstring": every integration boundary is an explicit stub whose docstring shows a `*.complete(system, messages)` shape (ref: Q6, Discovered Patterns).

`report.py` already has regression machinery but at different thresholds: per-case `detect_regressions` flags drops `> 0.2`, `check_promotion_criteria` requires non-decreasing `test_score`, plateau is `< 0.01` over the last 3 versions. The only `> 0.05` guard in the codebase is in `run_loop.sh` shell, not `report.py`; there is no version-level test_score-drop alert in `report.py` (ref: Q15). There are **no tests** for `diagnose.py`, `revise.py`, `apply_revisions`, or any eval-system module (ref: Q13). Fixtures are sparse: `evals/fixtures/` holds 4 ticket files, `evals/golden/` is empty, and no dedicated under-specified-prompt convergence fixture exists; since `run_eval.py`/`grade.py` are stubs producing zeros, convergence cannot currently be observed (ref: Q14).

## Desired End State

**AC1 — `diagnose.py` produces categorizations grounded in transcript evidence, not heuristics.** `categorize_failure` invokes a real Opus meta-agent that receives the full skill text plus the failing case's evidence, and returns a category drawn from the existing `CATEGORIES` set plus a grounded rationale string that quotes specific failure evidence. The string-matching heuristic is replaced by the meta-agent call; the function's return shape stays compatible with `produce_diagnosis`' downstream `recommendations`/`non_prompt_issues` assembly (ref: Q1, Q4).

**AC2 — `revise.py` produces concrete `old_text`/`new_text` edits that `apply_revisions` can apply.** `propose_revisions` invokes a real Opus meta-agent that receives the diagnosis plus the skill text and returns concrete `old_text`/`new_text` pairs anchored in the actual skill content, so `apply_revisions`' substring-match-and-replace mechanism applies them mechanically and `revise_skill` returns `revised` (not `pending_meta_agent`) when edits land (ref: Q2, Q7, Q12).

**AC3 — Empirical convergence.** Running `run_loop.sh` against a deliberately under-specified prompt produces a monotonically non-decreasing `test_score` across iterations. This requires a new under-specified skill fixture and depends on the runtime/judge being real (the ticket's stated dependency) (ref: Q14).

**AC4 — Regression guard in `report.py`.** `report.py` flags any version whose `test_score` drops more than 0.05 from the prior version, surfaced in the `alerts` block and the durable `ledger.json`, complementing the existing per-case 0.2 guard (ref: Q15).

**Cross-cutting:** Both meta-agent paths support dry-run for human review before applying. Both capture the meta-agent's prompt/response (rationale and proposed diff) for human review, since today no such trace exists (ref: Q9, Q16).

## Delta

- **New file `scripts/meta_agent.py`** — a single shared LLM-invocation wrapper exposing a `complete(system, user)` -> str function over the `using-claude-cli` path, used by both `diagnose.py` and `revise.py`. Centralizes the boundary the docstrings already assume and keeps it mockable for tests (ref: Q6).
- **Modify `scripts/diagnose.py`** — replace the heuristic body of `categorize_failure` with a `meta_agent.complete` call; parse the structured response into category + rationale; preserve the existing return keys and the `ALL_PASSING`/empty-failures short-circuit (ref: Q1, Q11). Add a `--dry-run` flag that emits the diagnosis without committing side effects beyond the diagnosis file (ref: Q9).
- **Modify `scripts/revise.py`** — replace the placeholder edit construction in `propose_revisions` with a `meta_agent.complete` call returning concrete `old_text`/`new_text`; keep `apply_revisions` mechanically unchanged (it already replaces first-occurrence substrings) (ref: Q7). Fix the dry-run side effect so `revision-log.json` is not mutated under `--dry-run` (ref: Q9).
- **Modify `scripts/report.py`** — add a version-level `test_score` drop guard (`> 0.05`) in `build_ledger_entry`, surfaced in `report["alerts"]` and `ledger.json` (ref: Q15).
- **New fixture** — a deliberately under-specified skill prompt under `evals/fixtures/` for convergence validation, plus whatever golden output `evals/golden/` needs (ref: Q14).
- **New tests** — `scripts/diagnose_test.py`, `scripts/revise_test.py` (stdlib-only `_test.py` siblings) mocking `meta_agent.complete`, plus `report.py` guard tests, satisfying the project's untested-module gap (ref: Q13).

## Pattern Decisions

### Decision 1: How to invoke the Opus meta-agent

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Shared `scripts/meta_agent.py` wrapper over the `using-claude-cli` subprocess path | Single mockable boundary; matches "stub-with-pseudocode-docstring" convention; no new SDK dependency; reuses documented invocation path | Subprocess/CLI parsing overhead; CLI output must be parsed for structured JSON |
| B | Inline `anthropic` SDK calls directly in each script | Direct structured responses | Adds a runtime dependency absent from the repo; duplicates client setup in two files; harder to mock per-script; no in-repo precedent (ref: Q6) |

**Recommendation:** Option A
**Rationale:** Research found no in-repo LLM client and identified `using-claude-cli` as the only documented invocation path; the stub docstrings already assume a single `*.complete(system, messages)` boundary shared across `diagnose`/`revise`/`grade` (ref: Q5, Q6). A shared wrapper is the smallest change that fits the existing boundary shape and keeps both scripts testable via one mock seam.
**NEW PATTERN?** Yes — there is no LLM-invocation module today; this introduces the first real one. Justified because the docstrings explicitly anticipate it and no existing pattern provides live model access (ref: Q6).

### Decision 2: Structured output contract from the meta-agent

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Meta-agent returns JSON (category + rationale for diagnose; list of `{old_text,new_text,description}` for revise), parsed by the caller | Maps directly onto existing return shapes and `apply_revisions`' substring mechanism; validatable; testable with fixture strings | Requires defensive JSON parsing of model output |
| B | Meta-agent returns a unified-diff/patch the script applies via patch tooling | Richer multi-line edits | `apply_revisions` is substring-replace, not patch-based — would require replacing it (ref: Q7); larger blast radius; new failure modes |

**Recommendation:** Option A
**Rationale:** `apply_revisions` already locates edits by literal substring and replaces the first occurrence; concrete `old_text`/`new_text` pairs slot in with zero change to the application mechanism (ref: Q7). JSON also mirrors the existing file-on-disk JSON hand-off pattern between stages (ref: Q3).
**NEW PATTERN?** No — reuses the existing JSON hand-off and the unchanged `apply_revisions` contract.

### Decision 3: Anchor safety for applied edits

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Prompt the meta-agent to return unique, verbatim anchors; verify each `old_text` is present and unique before applying, logging skip/ambiguous otherwise | Catches the silent first-occurrence and not-found behaviors research flagged; preserves `apply_revisions` semantics; surfaces conflicts for human review | Adds a validation pass; some valid edits rejected as non-unique |
| B | Keep `apply_revisions` as-is (first-occurrence replace, skip-if-missing) with no uniqueness check | Zero change | Silent partial application; overlapping edits corrupt anchors with no detection (ref: Q10) |

**Recommendation:** Option A
**Rationale:** Research shows `apply_revisions` replaces only the first occurrence and performs no uniqueness, overlap, or conflict detection (ref: Q10). A pre-apply verification layer is the minimal guard that prevents the meta-agent from silently mis-editing the live skill file, which has no backup (ref: Q8). Implement verification in the revise layer so `apply_revisions`' contract stays unchanged (supports Decision 2).
**NEW PATTERN?** Yes — anchor verification is new. Justified because the existing apply path trusts but never verifies anchor uniqueness, and the convergence/regression risk is highest at this exact seam (ref: Q10, Risk).

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Meta-agent drifts the prompt, regressing untested behaviors (subtle drops the 0.05 guard misses) | high | high | AC4 version-level guard catches large drops; dry-run + captured rationale enable human review before apply; defer per ticket until a solid baseline exists; snapshot skill before each edit (rollback is only a commented placeholder today — ref: Q8) |
| No real runtime/judge yet — `run_eval.py`/`grade.py` are stubs producing zeros, so AC3 convergence cannot be empirically observed | high | high | Ticket's stated dependency (runtime + fixtures + checks + LLM judge); gate AC3 acceptance on those landing; until then validate logic via mocked unit tests (ref: Q6, Q14) |
| Meta-agent returns an `old_text` anchor that is missing, non-unique, or overlapping — silent partial/wrong edit | med | high | Decision 3 pre-apply verification; log skipped/ambiguous edits; never write skill when verification fails (ref: Q7, Q10) |
| Model output is not valid JSON / unparseable | med | med | Defensive parsing in `meta_agent.py`; on parse failure emit a no-edit result and a logged error rather than crashing the `set -euo pipefail` loop (ref: Q3) |
| In-place skill overwrite with no backup loses the original on a bad edit | med | high | Snapshot `SKILL_PATH` before write; wire the commented rollback in `run_loop.sh` (ref: Q8) |
| dry-run still mutates `revision-log.json` | low | low | Fix as part of AC2/cross-cutting so dry-run is truly read-only (ref: Q9) |

## Open Questions

- OQ1: Which concrete model id / invocation should `meta_agent.py` use (e.g. the `using-claude-cli` skill vs. a direct `claude -p` call), and is an API key / CLI auth available in the loop's execution environment? Research found no existing invocation and no key (ref: Q6).
- OQ2: Should the loop snapshot/rollback the skill file (wiring the commented `git checkout HEAD~1` placeholder) as part of this ticket, or is that a separate hardening ticket? It materially affects the in-place-overwrite risk (ref: Q8).
- OQ3: Score scale is ambiguous — `report.py` treats 0.2 as "1 point on a 5-point scale" while diagnose's 0.9 and the loop's 0.85 imply 0–1. Is the new 0.05 guard a 0–1-scale absolute, and is normalization needed before comparing versions (ref: Q15, Inconsistencies)?
- OQ4: Is the `regression_risk` inversion in `diagnose.py:102` (`"low" if difficulty == "hard"`) intentional, and should this ticket correct it while touching the file (ref: Q4, Inconsistencies)?
- OQ5: What exactly defines the "deliberately under-specified prompt" fixture for AC3, and what target delta counts as convergence given the per-case 0.9 bar vs the loop's 0.85 `TARGET_SCORE` (ref: Q11, Q14)?
