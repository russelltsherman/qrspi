# Implementation Log — Surface blocking finding text in the review synopsis

## Session 1 — Slice 1

**Timestamp:** 2026-06-19T01:48:46Z
**Tasks completed:** T1 (read + locate per-lens table render), T2 (render_synopsis emits Blocking findings sub-section beneath FAIL rows), T3 (tests), T4 (run tests)
**Tasks failed:** none
**Tests:**

- `python3 scripts/qrspi_review_synopsis_test.py` → 21 passed, 0 failed (16 prior + 5 new)
- `python3 scripts/run_tests.py` → 40 passed, 0 failed

**Deviations from structure.md:**

- Structure says "beneath each FAIL row a 'Blocking findings' sub-section". Emitting prose between table rows would break the Markdown table, so the sub-sections are rendered as a block immediately **after** the per-lens table (one `#### Blocking findings — <lens>` sub-section per FAIL lens that has findings). The literal finding strings still surface verbatim and the per-lens PASS|FAIL|count table row is unchanged — satisfying AC #1. Counts a faithful presentation choice, not a contract change; `render_synopsis(...) -> str` signature unchanged.

**Deviations from plan.md:**

- none

**Notes for next session:**

- `render_synopsis` now emits, after the axis table, a `#### Blocking findings — <lens>` sub-section per FAIL lens with non-empty findings; finding strings are deduped (first-seen order) via a new `_dedupe` helper. Passing lenses and FAIL lenses with empty `findings` emit no sub-section. The Advisory (non-blocking) section and `ledger_row_fields`/`partition_decision_readiness` are untouched.

---

## Session 2 — Slice 2

**Timestamp:** 2026-06-19T02:00:00Z
**Tasks completed:** T6 (read qrspi_critics_config.py, confirm resolve_design / DEFAULT_DESIGN_LENSES / batch envelope + "do NOT couple" comments + fail-closed reader convention), T7 (add resolve_review_lens_model(cfg) reading critics.review.lensModel, fail-closed), T8 (tests: configured id returned/stripped, None on absent/malformed, non-coupling regression vs resolve_design), T9 (run critics test), T10 (checkpoint both green)
**Tasks failed:** none
**Tests:**

- `python3 scripts/qrspi_critics_config_test.py` → 59 passed, 0 failed (49 prior + 10 new in ResolveReviewLensModelTests)
- `python3 scripts/run_tests.py critics` → 1 file passed, 0 failed
- `python3 scripts/run_tests.py` → 40 passed, 0 failed (full-suite regression; batch critics contract fixture unaffected)

**Deviations from structure.md:**

- none. Added `resolve_review_lens_model(cfg) -> str | None` reading `critics.review.lensModel`; left `resolve_design` / `DEFAULT_DESIGN_LENSES` / the batch `critics.design.*` envelope and the "do NOT couple" comments untouched. One presentation choice worth noting (not a contract change): the reader returns the `.strip()`-ed model id (so a spawn gets a clean arg) and treats blank/whitespace-only as unset (→ None), mirroring `resolve_design`'s `lensModel` empty/blank handling.

**Deviations from plan.md:**

- none

**Notes for next session:**

- New pure reader `resolve_review_lens_model(cfg)` in `scripts/qrspi_critics_config.py`: `cfg` is the parsed `critics` block (same object `resolve_critics` receives); it navigates `cfg["review"]["lensModel"]` and returns the stripped non-empty string, else `None`. Fail-closed — never raises; a non-dict `critics`, non-dict `review`, or non-string/blank `lensModel` all yield `None`. It is DELIBERATELY SEPARATE from `resolve_design`'s `critics.design.lensModel`; the two keys/families are decoupled (non-coupling regression asserted in `ResolveReviewLensModelTests.test_separate_from_design_lens_model_non_coupling`). The engine slice (qrspi-review.js, plan step 77) should call this ONCE as `resolve_review_lens_model(config.get("critics"))` and pass the result as the `model` key on the `*-review` lens `agent(...)` spawn ONLY.
- INFRA CAVEAT (recurring, persists from Session 1): the worktree admin dir `/workspaces/qrspi/.git/worktrees/RUS-93` was orphaned/pruned again at the start of this session AND re-pruned within seconds of being rebuilt (known "worktree metadata pruned -> orphans" issue). This slice's work is file-edits + `python3` verification only, which need no git, so it completed cleanly. But NO git/gt command can currently run in this worktree without first rebuilding the admin dir (commondir=`../..`, gitdir, `HEAD ref: refs/heads/RUS-93/slice-1`) + `git worktree repair` — and the rebuild does not survive the next git invocation. The finalize/submit worker MUST health-check (`git rev-parse --is-inside-work-tree`) and rebuild the admin dir immediately before EACH git/gt command (not just once), or `gt submit` will hard-stop with "not a git repository". The slice-2 edits are committed to neither index nor branch yet (git unavailable) — they live in the working tree only; the orchestrator's commit step must stage them after rebuilding the admin dir.

---

## Session 3 — Slice 3

**Timestamp:** 2026-06-19T03:10:00Z
**Tasks completed:** T11-T14 (reads + seam decision: qrspi-batch.js engine conventions, the three review-*/SKILL.md, the Python modules, and the JS↔Python seam decision), T15 (build `.claude/workflows/qrspi-review.js`), T16-T18 (thin SKILL wrappers design/plan/impl), T19-T21 (`*-review` agent model notes now-wired), T22 (mark reviser dormant), T25-T26 (verify suite + grep gates). T23-T24 (seam fixtures) SKIPPED per the T14 decision (no new JS↔Python parser seam — recorded in the engine header).
**Tasks failed:** none
**Tests:**

- `python3 scripts/run_tests.py` → 40 passed, 0 failed (full-suite regression; no Python source changed in this slice, suite confirms no breakage)
- `node --check .claude/workflows/qrspi-review.js` → SYNTAX OK
- Manual end-to-end simulation of the engine's deterministic Python pipeline (file-arg form): synthesize → terminal action (`converged` all-pass / `exhausted` on a FAIL) → `build_record(phase, rounds, terminal_action, agreement={})` (record carries `agreement: {}`, `mode: "on-demand-review"`, `axes`, `nonBlockingNotes`) → `render_synopsis(verdicts, decision_readiness|null, terminal_action)` (axis table + per-FAIL blocking-findings text + advisory section + design-only decision-readiness section + Terminal action; NO Agreement line) — all verified against the real Slice-1/Slice-2 helpers.

**Deviations from structure.md:**

- none on contract. One IMPLEMENTATION CORRECTION worth flagging: the old SKILL.md procedures (and a naive transcription) used `printf '%s' '<json>' | python3 - <<'PY' ... json.load(sys.stdin)` to feed the verdict array. That construct is BROKEN — a pipe and a heredoc both redirect stdin, the heredoc wins the fd, so `python3 -` reads the SCRIPT from stdin and `json.load(sys.stdin)` would re-read the heredoc, not the piped JSON (verified: it executes the JSON as a program → SyntaxError). The engine's SYNOPSIS worker therefore WRITES the verdict array + decision-readiness verdict to files (via the Write tool, verbatim) and the Python heredocs read them via `sys.argv` file paths (`python3 - <verdictFile> [<drFile>] "$(cat <actionFile>)" > out <<'PY'`). This is a faithfulness-preserving correction (same helpers, same contract), not a contract change.

**Deviations from plan.md:**

- T23-T24 (contract_seam fixtures) intentionally NOT done — conditional on T14 finding a JS↔Python parser seam. Decision: the engine introduces NO new JS function that parses Python stdout into a data structure (it hands every Python call to a worker as a command string and validates the worker's STRUCTURED envelope via JSON schema at the `agent()` boundary, exactly like qrspi-batch.js's finalize/persist workers). The existing `scripts/fixtures/contract_seam/` family covers the batch's JS parse functions (parseResolveEnvelope etc.), which this engine does not add. The Python transforms it drives are already stdlib-unit-tested. Recorded in the engine header.
- T27 (manual e2e on a real ticket PR) is ORCHESTRATOR-DEFERRED: it requires live git/gt/gh/Linear, which are unavailable in this worktree (the admin-dir-orphan caveat persists) and are the orchestrator's province per the slice's hard constraints. The deterministic pipeline + propose-only invariant + model-override-placement were verified statically (suite, node --check, Python simulation, greps) instead.

**Notes for next session:**

- NEW FILE `.claude/workflows/qrspi-review.js` — the `{ticket, phase}` deterministic review engine (phase ∈ design|plan|impl). It: (1) RESOLVE worker folds worktree + phase PR# + head SHA + scratch-copy of the artifact + staged ticket text + the `*-review` lens model (via a `python3 -c` calling Slice-2's `resolve_review_lens_model(read_config(REPO_ROOT).get("critics"))`) into ONE envelope; (2) fans out the phase `DEFAULT_REVIEW_*` lenses ONCE via `parallel()` (round 0, NO revise loop) with the model override on the `*-review` (node-validity) lens spawn ONLY (guarded `lensId === cfg.reviewLens && resolved.lensModel`, line ~324) and TICKET_CONTENT_PATH scoped to the fidelity/coverage lenses; (3) design-ONLY post-panel decision-readiness lens (terminal-advisory); (4) SYNOPSIS worker runs synthesize→build_record(agreement={})→render_synopsis→`qrspi_comment_reply.py`→`qrspi_metrics_append.py`→re-assert head SHA. Terminal action = `converged` (round-0 reduced pass) else `exhausted`; `revise` is impossible (build_record rejects it).
- PROPOSE-ONLY: head SHA captured in RESOLVE, re-asserted in SYNOPSIS; the engine emits NO branch-mutating command — only `gh pr list`/`gh pr view` (reads) and the single `gh pr comment` (via the helper) + the local ledger append. Both worker prompts carry an explicit "issue NO branch-mutating command" prohibition. Grep gate confirmed clean.
- The three `review-*/SKILL.md` are now thin wrappers: frontmatter `allowed-tools: Workflow`, body invokes `Workflow({ name: "qrspi-review", args: { ticket, phase } })` with phase design/plan/impl. The lens-fan-out, scratch-copy, decision-readiness, comment, ledger, and SHA-assert prose all moved into the engine.
- The three `qrspi-{design,plan,impl}-critic-*-review.md` model notes now say "now wired at spawn" — the engine supplies the override at spawn, frontmatter stays model-less (do NOT add a `model`/`lensModel` frontmatter key). `qrspi-critic-reviser.md` carries a DORMANT banner (no longer spawned by `/review-*` since the loop is gone); the `qrspi_critic_loop` MODULE is RETAINED (still imported by `qrspi_critic_synthesize`).
- INFRA CAVEAT (persists, unchanged): the worktree admin dir is still orphaned/re-pruned; this slice's work was file-edits + Python verification only (no git needed). The orchestrator's commit/submit step MUST rebuild the admin dir (or run `qrspi_provision.py`) before staging — the slice-3 edits live in the working tree only, uncommitted.

---
