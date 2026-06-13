# Work Tree — qrspi critics 3/5: single edge critics for planning phases + citation validator

**Plan basis:** plan.md @ 2026-06-13T00:00:00Z
**Generated:** 2026-06-13T00:00:00Z
**Status:** draft
**Total sessions:** 2
**Critical path:** T1 → T2 → T3 → T4 → T5 → T6 → T7 (Slice 1 validator) → T8 → T9 → T10 → T11 → T12 → T16 → T17 → T19 (Slice 2 wiring + e2e)

## Session 1 — Slice 1: Citation validator script + unit tests

**Load:** structure.md §Contracts (CitationCheckEnvelope shape), plan.md §Slice 1, design.md §Decision 3 / §Decision 4 (forward-reference + glob exclusion)
**Estimated context:** ~18%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create `scripts/qrspi_verify_citations.py` skeleton: stdlib-only imports, docstring, `resolve_repo_root()` (own-module imports only, never citation resolution) | — | §1.1 | S | pending |
| T2 | Add `parse_citations(text) -> list[str]` — extract backtick `file:line` / `file:start-end` / bare-file tokens; exclude `*`,`<`,`>`; verbatim, order-preserving | T1 | §1.2 | M | pending |
| T3 | Add `resolve_citation(token, worktree_root) -> bool` — absent file tolerated (True); existing in-bounds True; existing out-of-bounds False; join against `worktree_root` never `resolve_repo_root()` | T2 | §1.3 | M | pending |
| T4 | Add CLI entrypoint — argparse `--artifact-path`/`--worktree-root`, collect unresolved, print single-line `CitationCheckEnvelope`, exit 0/1, verbatim error field | T3 | §1.4 | M | pending |
| T5 | Create `scripts/qrspi_verify_citations_test.py` — cases (a)–(g): in-range line/range resolve, out-of-range hard-fail, absent-file tolerated, glob/placeholder excluded, bare-file, worktree-root asserted against a tempdir not `resolve_repo_root()` | T4 | §1.5 | M | pending |
| T6 | Run `python3 scripts/qrspi_verify_citations_test.py` — expect all pass (exit 0) | T5 | §1.6 | S | pending |
| T7 | **Verify Slice 1** — tests pass + manual CLI smoke (valid resolves, out-of-range `ok:false` verbatim token, absent-file tolerated, single-line JSON, exit 0/1) | T6 | §1.7 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete (self-contained Python validator landed and verified in isolation). Fresh context for Slice 2, which is a different file (`qrspi-batch.js`) and a different mental model (orchestrator wiring); only the validator's CLI contract carries forward, not its implementation detail.

## Session 2 — Slice 2: Wire four edge critics + research node check into the orchestrator

**Load:** structure.md §Contracts (`NodeCheckSpec`, `resolveEdgeCriticMaxRounds`), plan.md §Slice 2, design.md §Decision 2 / §Decision 3 / §Decision 5, impl-log.md §Slice 1 (validator CLI contract only: `--artifact-path`/`--worktree-root`, `CitationCheckEnvelope`, exit codes)
**Estimated context:** ~30%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T8 | Add `resolveEdgeCriticMaxRounds(parsedCritics, phase)` helper near `resolveDesignCritic` (reads parsed `critics` object, defaults 2) | T7 | §2.8 | S | pending |
| T9 | Add `criticConfig.nodeCheck` branch in `runPhase` — after producer, before edge critic loop; non-`ok` → `return false` (pre-persist) | T8 | §2.9 | M | pending |
| T10 | Define research `nodeCheck` `NodeCheckSpec` — invokes `qrspi_verify_citations.py` with `--artifact-path stg(...)` `--worktree-root wd` (use `r.repoRoot`/`wd`, not `.`), parse envelope, `ok:false` fails phase | T9 | §2.10 | M | pending |
| T11 | Thread `parsedCritics` (whole parsed `critics` object) into `doDesign` and `doPlan` scope — no second config read | T8 | §2.15 | S | pending |
| T12 | `doDesign`: questions `criticConfig = { upstreamPath: r.ticketContentPath, maxRounds: resolveEdgeCriticMaxRounds(...,'questions') }` (anchors on ticket) | T11 | §2.11 | S | pending |
| T13 | `doDesign`: research `criticConfig` `{ upstreamPath: art(...,'questions.md'), maxRounds: ...'research', nodeCheck: T10 }` + firewall comment (NEVER `r.ticketContentPath`) | T10, T11 | §2.12 | M | pending |
| T14 | `doDesign`: structure `criticConfig = { upstreamPath: art(...,'design.md'), maxRounds: ...'structure' }` | T11 | §2.13 | S | pending |
| T15 | `doPlan`: replace literal `maxRounds: 2` with `resolveEdgeCriticMaxRounds(parsedCritics, 'plan')` on existing plan `criticConfig` | T11 | §2.14 | S | pending |
| T16 | Splice questions/research/structure residual findings into finalize body via existing `criticBodyStep`/`criticSummary` (plan already participates) | T12, T13, T14 | §2.16 | M | pending |
| T17 | Document manual e2e procedure (no JS test runner) — record steps 19–22 in PR body / comment | T16 | §2.17 | S | pending |
| T18 | Document `critics.<phase>.maxRounds` keys (questions/research/structure/plan) in `.qrspi/config.example.json` | T15 | §2.18 | S | pending |
| T19 | **Verify Slice 2** — e2e: per-phase critic upstream anchors correct (questions→ticket, research→questions.md never ticket, structure→design.md); out-of-range citation fails + nothing persists; absent-file tolerated; configured `maxRounds` honored, absent/malformed → 2; `python3 scripts/qrspi_verify_citations_test.py` still passes | T16, T17, T18 | §2.19–§2.23 | M | pending |

--- SESSION BOUNDARY ---
**Reason:** Final session. Slice 2 complete — both slices implemented and verified; the feature (four wired edge critics + research citation node check) is whole and ready for PR.

## Notes

- **Slice/session 1:1 mapping** is deliberate: the plan's two slices are file-disjoint (Python validator vs `qrspi-batch.js`) and the only cross-slice coupling is the validator's CLI contract, which fits a compact load manifest — so no slice needs to span sessions and no session needs to mix slices.
- **Critical path** is the dependency spine: validator must exist and be verified (T1→T7) before the orchestrator can invoke it (T10/T13), and the helper + threading (T8, T11) gate the per-phase `criticConfig` tasks. T13 (research wiring) is the deepest join, depending on both the `nodeCheck` spec (T10, itself rooted in the validator) and the threaded config (T11).
- **Carried-forward unverified assumptions** (from plan §Unverified Assumptions): AC3 has no concrete code mapping (eval harness is a placeholder); OQ2 per-phase rubric framing is deferred; `NodeCheckSpec` exact shape is pinned at T10. None block the DAG but each is a human-confirmation item at review.
