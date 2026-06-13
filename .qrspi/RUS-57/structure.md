# Structure Outline — qrspi critics 3/5: single edge critics for planning phases + citation validator

**Design basis:** design.md @ 2026-06-13T00:00:00Z
**Generated:** 2026-06-13T00:00:00Z
**Status:** draft

## New Types

No new persistent data types. Two new JSON envelope shapes (in-process / CLI contracts, not stored schemas):

- `CitationCheckEnvelope { ok: boolean, unresolved: array<string>, error?: string }` — single-line JSON printed by `qrspi_verify_citations.py`. `unresolved` holds verbatim offending citation tokens; `ok:false` when `unresolved` is non-empty or on error.
- `EdgeCriticConfig { upstreamPath: string, maxRounds: integer, nodeCheck?: NodeCheckSpec, rubric?: string }` — the single-critic `criticConfig` object `doDesign`/`doPlan` pass to `runPhase` (no `lenses` field, so it routes to `runCriticLoop`). `nodeCheck` is present only for the research phase.
- `NodeCheckSpec { cmd: string }` (shape TBD in implementation) — describes the deterministic pre-critic check `runPhase` runs against `stg(id,name)`; for research it invokes `qrspi_verify_citations.py --artifact-path <staged research.md> --worktree-root <wd>`. Returning non-`ok` fails the phase before persist.

## Modified Types

- `criticConfig` (the object consumed by `runPhase`) — add optional field `nodeCheck` (ref: design.md §Delta, Decision 2 Option A). Absent for questions/structure/plan; present for research.

## Contracts

Python (in `scripts/qrspi_verify_citations.py`, pure helpers behind a thin CLI):

- `parse_citations(text: str) -> list[str]` — extract literal citation tokens (`file:line`, `file:start-end`, bare-file backtick forms) from research.md; exclude any token containing `*`, `<`, or `>` (Decision 4 Option A). Returns verbatim tokens.
- `resolve_citation(token: str, worktree_root: str) -> bool` — return `True` (resolves) when the file is absent (tolerated forward reference, OQ3) OR the file exists and the cited line/range is in bounds; return `False` ONLY when the file exists and the cited line/range is out of bounds (provably broken pointer, the AC2 hard-fail case).
- CLI: `--artifact-path`, `--worktree-root`; prints one `CitationCheckEnvelope`; exit `0`/`1`; self-locates repo root only for its own module imports, never to resolve citations (Decision 3 Option A).

JavaScript (in `.claude/workflows/qrspi-batch.js`):

- `resolveEdgeCriticMaxRounds(parsedCritics, phase): integer` — return `parsedCritics?.<phase>?.maxRounds` when a positive integer, else `2` (Decision 5; mirrors `resolveDesignCritic`'s `Number.isInteger(cfg.maxRounds) && cfg.maxRounds > 0 ? cfg.maxRounds : 2`). Reads from the already-parsed whole `critics` object — no new config read (ref: Q6/Q8).
- `runPhase(...)` node-check branch — when `criticConfig.nodeCheck` is present, run it on `stg(id,name)` after the producer succeeds and before the edge critic; return `false` on a non-`ok` result so nothing persists (Decision 2 Option A; ref: Q2/Q3).

## Slice 1: Citation validator script + unit tests

**Goal:** A self-locating, stdlib-only `qrspi_verify_citations.py` that parses research.md citations and resolves them against an explicitly-supplied worktree root, fully verified in isolation by its `_test.py` sibling — independent of any JS wiring. This is the deterministic gate AC2 calls for, testable end-to-end via the CLI before it is ever wired in.
**Files touched:**

- ✨ `scripts/qrspi_verify_citations.py` — pure `parse_citations(text)` + `resolve_citation(token, worktree_root)` helpers behind a CLI taking `--artifact-path`/`--worktree-root`, printing one `{ ok, unresolved, error? }` envelope, exit 0/1 (Decision 3/4)
- ✨ `scripts/qrspi_verify_citations_test.py` — stdlib-only sibling using `tempfile`: file-present + out-of-range line → unresolved/hard-fail; file-absent → tolerated, NOT reported (OQ3 forward-reference split); glob/placeholder tokens (`*`, `<`, `>`) excluded; bare-file and resolving `file:line`/`file:start-end` cases; worktree-root resolution asserted against a tempdir root (NOT `resolve_repo_root()` — the Risk Register med/high item)
**Verification:**
- [ ] `python3 scripts/qrspi_verify_citations_test.py` passes
- [ ] Manual CLI smoke: run against a fixture research.md with one valid `file:line`, one out-of-range line (expect `ok:false` with verbatim token), and one absent-file token (expect tolerated, `ok:true`)
**Context cost:** S
**Depends on:** none

## Slice 2: Wire four edge critics + research node check into the orchestrator

**Goal:** `doDesign`/`doPlan` drive the single edge critic for questions, research, structure, and plan, each anchored on its correct upstream; research additionally runs the citation node check on the staged artifact before its edge critic; per-phase `maxRounds` is config-overridable; residual findings splice into each finalize body. End-to-end testable path: a design-phase batch run exercises all four edge critics, and a research.md with an out-of-range citation fails the research phase with the verbatim token while leaving nothing persisted.
**Files touched:**

- ⚠️ `.claude/workflows/qrspi-batch.js` — (a) add the `criticConfig.nodeCheck` branch in `runPhase` (run on `stg(id,'research')` before the edge critic, return `false` on non-`ok`; Decision 2 Option A); (b) in `doDesign`, add single-critic `criticConfig` to the `runPhase` calls for questions (`upstreamPath: r.ticketContentPath`), research (`upstreamPath: art(wd,id,'questions.md')` — NEVER the ticket; research-firewall guard with a code comment, Risk Register med/high), and structure (`upstreamPath: art(wd,id,'design.md')`); plan already wired in `doPlan`; (c) splice each phase's residual findings into its finalize commit body via the existing `criticBodyStep`/`criticSummary` mechanism; (d) add `resolveEdgeCriticMaxRounds(parsedCritics, phase)` and feed its result into each phase's `criticConfig.maxRounds` (replacing literal `2`); pass `--worktree-root wd` to the validator
**Verification:**
- [ ] Manual e2e (per project convention — no JS test runner; Risk Register high/med): run a design-phase batch on a ticket; confirm via per-round `log()` output that questions, research, structure each spawn an edge critic with the expected upstream anchor
- [ ] e2e: a staged research.md containing an out-of-range `file:line` fails the research phase with the verbatim token and persists nothing (canonical research.md absent after the failed run)
- [ ] e2e: a staged research.md citing a wholly-absent file does NOT fail research (forward-reference tolerance, OQ3)
- [ ] Set `critics.research.maxRounds` in config and confirm via `log()` the research critic loop honors it; absent/malformed falls back to 2
**Context cost:** M
**Depends on:** Slice 1

---

## Unverified Assumptions

- **AC3 (per-phase eval scores before/after) has no concrete code mapping.** The eval harness is a non-functional placeholder (ref: Q15, OQ1); the design routes "before/after numbers" to per-round `log()` output + manual e2e spliced into the PR body, not to `run_eval.py`. No slice produces eval scores. This needs human confirmation (design's OQ1) that `log()`-derived observation satisfies AC3, or AC3 is deferred.
- **OQ2 — phase-tailored `rubric` lines are undecided.** The contracts allow an optional `rubric` per `EdgeCriticConfig`, but the design leaves open whether each edge critic gets phase-specific framing (questions = "high-leverage ambiguities", structure = "no scope creep") or a generic fidelity judgment. Slice 2 wires generic single critics by default; injecting per-phase rubrics is a non-blocking enhancement pending the human's OQ2 answer.
- **`NodeCheckSpec` exact shape is not pinned by the design.** The design specifies the behavior (run the validator on `stg(id,'research')` before the edge critic, fail on non-`ok`) and the field name `criticConfig.nodeCheck`, but not the precise object shape (e.g. a command-builder closure vs a declarative `{ cmd, args }`). Implementation must choose the minimal shape consistent with the existing `runPhase` plumbing; flagged so the plan phase settles it concretely.
