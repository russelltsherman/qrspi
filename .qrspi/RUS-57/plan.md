# Implementation Plan — qrspi critics 3/5: single edge critics for planning phases + citation validator

**Structure basis:** structure.md @ 2026-06-13T00:00:00Z
**Generated:** 2026-06-13T00:00:00Z
**Status:** draft
**Total steps:** 23

## Slice 1: Citation validator script + unit tests

**Goal:** A self-locating, stdlib-only `qrspi_verify_citations.py` that parses research.md citations and resolves them against an explicitly-supplied worktree root, fully verified in isolation by its `_test.py` sibling.

### Setup

1. ✨ Create `scripts/qrspi_verify_citations.py` — module skeleton: stdlib-only imports (`argparse`, `json`, `os`, `re`, `sys`), module docstring stating it is the AC2 deterministic citation node-check, and a `resolve_repo_root()` helper that self-locates from `__file__` **only** for its own module imports — never used to resolve citations (Decision 3 Option A; structure.md Contracts).

### Core Logic

2. ✨ Add `parse_citations(text: str) -> list[str]` to `scripts/qrspi_verify_citations.py` — extract literal citation tokens from backtick-delimited spans: `file:line`, `file:start-end`, and bare-file backtick forms. Exclude any token containing `*`, `<`, or `>` (Decision 4 Option A — glob/placeholder exclusion). Return verbatim tokens (no normalization), preserving order (structure.md Contracts; Decision 4).

3. ✨ Add `resolve_citation(token: str, worktree_root: str) -> bool` to `scripts/qrspi_verify_citations.py` — split the token into `file` and optional `line`/`start-end`. Return `True` (resolves) when: (a) the file is **absent** under `worktree_root` (tolerated forward reference, OQ3 RESOLVED=tolerated), OR (b) the file exists and the cited line/range is within the file's line count. Return `False` **only** when the file exists and the cited line/range is out of bounds (the AC2 hard-fail case). Join paths against `worktree_root`, never against `resolve_repo_root()` (Decision 3; Risk Register med/high) (structure.md Contracts; Decision 4 forward-reference split).

4. ✨ Add the CLI entrypoint to `scripts/qrspi_verify_citations.py` — `argparse` with required `--artifact-path` and `--worktree-root`. Read the artifact file, run `parse_citations`, collect tokens where `resolve_citation(token, worktree_root)` is `False` into `unresolved`. Print exactly one single-line `CitationCheckEnvelope` `{ "ok": bool, "unresolved": [...], "error"?: str }` (ok=false when `unresolved` is non-empty or on error), exit `0` when ok else `1`. Wrap I/O in try/except, reporting the error verbatim once into the `error` field (structure.md Contracts; CitationCheckEnvelope shape).

### Tests

5. ✨ Create `scripts/qrspi_verify_citations_test.py` — stdlib-only sibling (`unittest`, `tempfile`, `sys.path.insert` to import the module). Cover: (a) file-present + in-range `file:line` → resolves; (b) file-present + in-range `file:start-end` → resolves; (c) file-present + out-of-range line → `unresolved` / hard-fail with verbatim token; (d) file-absent entirely → tolerated, NOT reported (OQ3 forward-reference split); (e) tokens with `*`, `<`, `>` → excluded by `parse_citations`; (f) bare-file token → resolves when present, tolerated when absent; (g) worktree-root resolution asserted against a `tempfile.TemporaryDirectory()` root — NOT `resolve_repo_root()` (Risk Register med/high item) (structure.md Slice 1 Files touched).

6. Run: `python3 scripts/qrspi_verify_citations_test.py`
   - **Expected:** all test cases pass (exit 0).

### Verify Slice 1

7. **Checkpoint:** `python3 scripts/qrspi_verify_citations_test.py && python3 scripts/qrspi_verify_citations.py --artifact-path <fixture research.md> --worktree-root <tempdir>`
   - [ ] `python3 scripts/qrspi_verify_citations_test.py` passes
   - [ ] Manual CLI smoke against a fixture research.md: one valid `file:line` resolves; one out-of-range line yields `ok:false` with the verbatim token; one absent-file token is tolerated (`ok:true`)
   - [ ] Output is exactly one single-line JSON envelope; exit code is `0` on ok and `1` on a non-resolving citation

---

## Slice 2: Wire four edge critics + research node check into the orchestrator

**Goal:** `doDesign`/`doPlan` drive the single edge critic for questions, research, structure, and plan, each anchored on its correct upstream; research additionally runs the citation node check on the staged artifact before its edge critic; per-phase `maxRounds` is config-overridable; residual findings splice into each finalize body.

### Setup

8. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — add `resolveEdgeCriticMaxRounds(parsedCritics, phase)` helper near the existing `resolveDesignCritic` (Decision 5; structure.md Contracts).
   - **Current:** no per-phase maxRounds resolver for questions/research/structure/plan; only `resolveDesignCritic` reads `cfg.maxRounds`.
   - **After:** `function resolveEdgeCriticMaxRounds(parsedCritics, phase) { const cfg = parsedCritics?.[phase]; return (cfg && Number.isInteger(cfg.maxRounds) && cfg.maxRounds > 0) ? cfg.maxRounds : 2; }` — reads from the already-parsed whole `critics` object, no new config read (ref Q6/Q8).

### Core Logic

9. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — add the `criticConfig.nodeCheck` branch inside `runPhase`.
   - **Current:** `runPhase` runs reuse short-circuit → producer → `if (criticConfig)` edge critic on `stg(id,name)` → `persistArtifact`; no node-check step (Decision 2, ref Q2).
   - **After:** after the producer succeeds and **before** the edge critic loop, `if (criticConfig?.nodeCheck)` run the node check against `stg(id,name)`; on a non-`ok` result `return false` so nothing persists (Decision 2 Option A; node check inside the pre-persist staging window).

10. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — define the research `nodeCheck` so it invokes the validator. Choose the minimal `NodeCheckSpec` shape consistent with existing `runPhase` plumbing (the structure flags the exact shape as TBD; pin it here).
    - **Current:** no `nodeCheck` field constructed anywhere.
    - **After:** research's `criticConfig.nodeCheck` runs `python3 <repoRoot>/scripts/qrspi_verify_citations.py --artifact-path <stg(id,'research')> --worktree-root <wd>` (per the worker-cwd engine-path convention — use `r.repoRoot`/`wd`, not `.`), parses the single-line `CitationCheckEnvelope`, and yields `ok:false` to fail the phase (Decision 3 — pass `--worktree-root wd` explicitly).

11. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — in `doDesign`, add single-critic `criticConfig` to the `runPhase` call for **questions**.
    - **Current:** questions passes no `criticConfig`, so it skips the critic block (ref Q1, Q12).
    - **After:** questions `criticConfig = { upstreamPath: r.ticketContentPath, maxRounds: resolveEdgeCriticMaxRounds(parsedCritics, 'questions') }` (no `lenses`, routes to `runCriticLoop`; questions anchors on the ticket, ref Q12).

12. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — in `doDesign`, add single-critic `criticConfig` to the `runPhase` call for **research**, with the node check and the research-firewall guard.
    - **Current:** research passes no `criticConfig`, so it skips the critic block (ref Q1).
    - **After:** research `criticConfig = { upstreamPath: art(wd,id,'questions.md'), maxRounds: resolveEdgeCriticMaxRounds(parsedCritics, 'research'), nodeCheck: <step 10 spec> }`. Add a code comment stating `upstreamPath` is `questions.md` and **NEVER** `r.ticketContentPath` (research firewall, Risk Register med/high; ref Q12, Inconsistencies).

13. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — in `doDesign`, add single-critic `criticConfig` to the `runPhase` call for **structure**.
    - **Current:** structure passes no `criticConfig`, so it skips the critic block (ref Q1).
    - **After:** structure `criticConfig = { upstreamPath: art(wd,id,'design.md'), maxRounds: resolveEdgeCriticMaxRounds(parsedCritics, 'structure') }`.

14. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — in `doPlan`, replace the literal `maxRounds: 2` on the existing plan `criticConfig` with `resolveEdgeCriticMaxRounds(parsedCritics, 'plan')`.
    - **Current:** `doPlan` passes `{ upstreamPath: art(wd,id,'structure.md'), maxRounds: 2 }` (ref Q1).
    - **After:** `{ upstreamPath: art(wd,id,'structure.md'), maxRounds: resolveEdgeCriticMaxRounds(parsedCritics, 'plan') }`.

15. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — ensure `parsedCritics` (the whole parsed `critics` object) is in scope for `doDesign` and `doPlan` where the four `criticConfig`s are built.
    - **Current:** only `resolveDesignCritic` consumes the parsed critics for the design panel.
    - **After:** the existing `readDesignCriticConfig`/`parseCriticConfig` result (whole `critics` object via one `--key critics` read) is threaded to `doDesign`/`doPlan` so each `resolveEdgeCriticMaxRounds(parsedCritics, phase)` call resolves — no second config read (Decision 5; ref Q6/Q8; the single-key constraint that bit slice 3).

16. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — splice each phase's residual critic findings into its finalize commit body via the existing `criticBodyStep`/`criticSummary` mechanism, for questions, research, and structure (plan already participates).
    - **Current:** only the wired-up phases route residual findings into the finalize body.
    - **After:** questions/research/structure residual findings flow through the same `criticBodyStep`/`criticSummary` splice already used by plan/design (Delta (c)).

### Tests

17. ✨ Create/extend a JS fixture or document the manual e2e procedure — per project convention there is **no JS test runner**; all testable logic lives in the Python validator (Slice 1). Record the manual e2e steps (steps 19–22) in the PR body / a comment, not as an automated test (Risk Register high/med; ref Q14).

### Verify Slice 2

18. ⚠️ Modify `.qrspi/config.example.json` — document the new `critics.<phase>.maxRounds` keys for questions/research/structure/plan (mirroring the existing `critics.design` example) so the config-overridable knob is discoverable.
    - **Current:** `config.example.json` documents `critics.design` only.
    - **After:** adds `critics.questions`/`critics.research`/`critics.structure`/`critics.plan` example blocks with `maxRounds`.

19. **Checkpoint:** manual e2e — `node .claude/workflows/qrspi-batch.js` (design-phase run on a test ticket), inspecting `log()` output.
    - [ ] questions, research, and structure each spawn an edge critic with the expected upstream anchor (questions→ticket, research→questions.md, structure→design.md), confirmed via per-round `log()` output
    - [ ] research's edge critic upstream is `questions.md`, NEVER the ticket (research firewall)

20. **Checkpoint:** e2e — stage a `research.md` containing an out-of-range `file:line` and run the research phase.
    - [ ] the research phase fails with the verbatim offending token in the envelope
    - [ ] nothing is persisted (canonical `research.md` absent after the failed run)

21. **Checkpoint:** e2e — stage a `research.md` citing a wholly-absent file and run the research phase.
    - [ ] research does NOT fail (forward-reference tolerance, OQ3 RESOLVED=tolerated)

22. **Checkpoint:** e2e — set `critics.research.maxRounds` in config and run; then unset/malform it.
    - [ ] the research critic loop honors the configured value (confirmed via `log()`)
    - [ ] absent/malformed `maxRounds` falls back to `2`

23. **Checkpoint:** `python3 scripts/qrspi_verify_citations_test.py`
    - [ ] Slice 1 tests still pass after Slice 2 wiring (no regression to the validator)

---

## Rollback Notes

- **Steps 1–5 (new files):** rollback = delete `scripts/qrspi_verify_citations.py` and `scripts/qrspi_verify_citations_test.py`; no other code references them until Slice 2, so removal is clean.
- **Steps 9–16 (`qrspi-batch.js` edits):** rollback = revert the `qrspi-batch.js` changes. The four edge `criticConfig`s and the `nodeCheck` branch are additive — reverting restores the prior behavior (questions/research/structure skip the critic block; plan keeps `maxRounds: 2`). No data migration; no persisted-artifact format change.
- **Step 18 (`config.example.json`):** doc-only; rollback = revert the example file. Operator configs (`.qrspi/config.json`) are gitignored and unaffected; absent `critics.<phase>` keys safely default to `maxRounds: 2`.
- No DB migrations, no destructive ops.

## Unverified Assumptions (carried from structure.md)

- **AC3** (per-phase before/after eval scores) has no concrete code mapping — the eval harness is a non-functional placeholder. No step produces eval scores; before/after observation is routed to `log()` + manual e2e spliced into the PR body. Needs human confirmation (design OQ1) that this satisfies AC3, or AC3 is deferred.
- **OQ2** — per-phase `rubric` lines are undecided. Steps 11–13 wire generic single critics (no `rubric`); injecting phase-specific rubric framing is a non-blocking enhancement pending the human's OQ2 answer.
- **`NodeCheckSpec` exact shape** is not pinned by the design; step 10 pins the minimal shape (a command invoking the validator with `--artifact-path`/`--worktree-root`) consistent with existing `runPhase` plumbing.
