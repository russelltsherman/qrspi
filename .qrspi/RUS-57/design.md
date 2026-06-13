# Design — qrspi critics 3/5: single edge critics for planning phases + citation validator

**Ticket:** RUS-57
**Research basis:** research.md @ 2026-06-13T00:00:00Z
**Generated:** 2026-06-13T00:00:00Z
**Status:** draft

## Current State

The single-critic foundation loop `runCriticLoop(name, id, criticConfig)` already exists; it judges the staged artifact `stg(id, name)` against `criticConfig.upstreamPath`, defaulting `maxRounds` to 2, and spawns one `qrspi-critic` agent per round with `UPSTREAM_PATH`/`ARTIFACT_PATH` (+ optional `RUBRIC`) under `CRITIC_VERDICT_SCHEMA` (ref: Q1). Only the **plan** phase wires this loop today (`{ upstreamPath: art(wd,id,'structure.md'), maxRounds: 2 }`); questions, research, and structure pass no `criticConfig` and so skip the critic block entirely (ref: Q1, ref: Q12). `runPhase` has a fixed sequence — reuse short-circuit, spawn producer, `if (criticConfig)` run the critic loop on the staged file, then `persistArtifact` as the success gate — with exactly one branch point and **no node-check step anywhere today** (ref: Q2). The dispatch chooses panel-vs-single on `criticConfig.lenses?.length` (truthy routes to `runCriticPanelLoop`, design only; absent routes to `runCriticLoop`), not on a numeric cardinality field (ref: Q6).

All critic work runs on the **staged** path `stg(id,name) = /tmp/phase-stage/<id>/<name>.md` (token-free, Fix A) before persist; the upstream anchor is the prior phase's already-persisted canonical path `art(wd,id,'<name>.md')`; `scripts/qrspi_persist.py` then moves staged to canonical and is the real gate (ref: Q3). The verdict schema is `{ pass: boolean, findings: array<string> }`, both required, consumed by `scripts/qrspi_critic_loop.py` which fails closed (malformed verdict reads as not-passed) and decides converge / revise / cap_reached; a failed critic does not block submit — it converges, revises up to the cap, or finalizes with residual findings spliced into the PR body. Only an agent-spawn failure returns `ok:false` and fails the phase (ref: Q4, ref: Q7).

Self-locating stdlib scripts (`qrspi_persist.py`, `qrspi_config.py`) follow a fixed convention: stdlib-only, self-locate the repo root from `__file__` (never cwd), print exactly one `{ ok, ..., error? }` JSON envelope, exit `0`/`1`, report errors verbatim once, never retry, with pure helpers factored out for in-memory unit tests (ref: Q5). Critically, `resolve_repo_root()` / git-common-dir returns the **main checkout, not the worktree** — `qrspi_persist.py` re-prepends `.worktrees/<ticket>` to reach the worktree tree (ref: Q11). `critics.design` is the only per-phase config read today, via `--key critics` (the reader is single-top-level-key but object values round-trip intact; only dot-paths are unsupported) with the JS indexing `.design`; there is no per-phase config for questions/research/structure/plan (ref: Q6, ref: Q8). `scripts/qrspi_verify_citations.py` **does not exist** (ref: Q9, ref: Q10). Real research.md citations appear as backtick `file:line` / `file:start-end` (1226 tokens), bare-file paths, and glob/placeholder forms containing `*` or `<...>` (944 tokens) (ref: Q9). The JS orchestrator has no unit tests; only the pure Python decision core is tested (`qrspi_critic_loop_test.py`), via `sys.path.insert` + in-memory assertions on pure functions (ref: Q13, ref: Q14). The `evals/` + `run_eval.py` harness is a non-functional placeholder; per-round `log()` output is the only critic observability surface (ref: Q15).

## Desired End State

Maps each acceptance criterion to concrete behavior:

- **AC1 — each planning phase runs its single edge critic before submit, upstream supplied as rubric.** `doDesign`/`doPlan` pass a single-critic `criticConfig` (no `lenses`) to `runPhase` for **questions, research, structure, and plan**. Each routes to `runCriticLoop` with `upstreamPath` set to that phase's correct upstream anchor: questions → `r.ticketContentPath` (ticket, not an artifact; ref: Q12); research → `art(wd,id,'questions.md')` (NOT the ticket — the research firewall forbids anchoring on the ticket; ref: Q12, Inconsistencies); structure → `art(wd,id,'design.md')`; plan → `art(wd,id,'structure.md')` (already wired; ref: Q1). `maxRounds` is **config-overridable per phase**, mirroring `critics.design` exactly (Decision 5; resolved OQ4): each phase reads `critics.<phase>.maxRounds` (positive integer) with config-value > JS-default precedence, defaulting to 2 when absent or malformed. Worktree critic is out of scope (ticket marks it optional).
- **AC2 — research additionally runs `qrspi_verify_citations.py`; a non-resolving citation fails the phase with the verbatim citation.** A new self-locating stdlib script parses research.md's resolvable `file:line` / `file:start-end` / bare-file citations, resolves them against the **worktree** tree, and emits `ok:false` with the verbatim offending token when any does not resolve. It runs as a node check inside `runPhase` for research only — after the producer succeeds, before the research edge critic, both inside the pre-persist staging window so a failure leaves nothing persisted and `runPhase` returns false (ref: Q2). Glob/placeholder tokens (`*`, `<`, `>`) are excluded as non-literal (ref: Q9). **Scope boundary (resolved OQ3, reviewer PR #268):** a citation to a not-yet-created file within the same Graphite stack is **tolerated** — research runs in the design-phase worktree, which only carries files present at design time, so a later-slice file citation that does not yet exist on disk must not fail the phase. The validator therefore resolves against **only the file's existence/line-range on disk**, and a missing path that the design itself introduces as a planned future file is out of the validator's deterministic reach (see Decision 4: a missing path is reported, but the *design intent* of "this file will exist after slice N" cannot be discriminated from a typo by a stdlib check — the residual risk is accepted as tolerated rather than hard-failing legitimate forward references).
- **AC3 — per-phase eval scores reported before/after.** Since the eval harness is a non-functional placeholder (ref: Q15), before/after numbers come from per-round `log()` output and manual e2e observation, recorded in the PR body via the existing critic-summary splice — not from `run_eval.py`. This is surfaced as an open question for the human.

## Delta

New files:
- `scripts/qrspi_verify_citations.py` — self-locating, stdlib-only node-check script (pure `parse_citations(text)` + `resolve_citation(token, worktree_root)` helpers behind a thin CLI taking `--artifact-path` and `--worktree-root` and printing `{ ok, unresolved: [...], error? }`). Per resolved OQ3, `resolve_citation` only reports a token as `unresolved` when the file **exists** but the cited line/range is out of bounds; a wholly-absent file is **tolerated** (treated as a possible same-stack forward reference) and never reported.
- `scripts/qrspi_verify_citations_test.py` — stdlib-only sibling: resolving vs broken cases, in-memory via `tempfile` — explicitly including the OQ3 forward-reference split (file-present + out-of-range line → unresolved/hard-fail; file-absent → tolerated, NOT reported), plus glob-excluded and bare-file cases.

Modified files:
- `.claude/workflows/qrspi-batch.js` — (a) add a node-check branch in `runPhase` driven by a new optional `criticConfig.nodeCheck` field (Decision 2 Option A — the `name === 'research'` guard is rejected there) that runs the citation validator on `stg(id,'research')` before the edge critic and returns false on `ok:false`; (b) in `doDesign`, add single-critic `criticConfig` args to the `runPhase` calls for questions, research, structure (plan already has one in `doPlan`); (c) splice each phase's residual findings into its finalize commit body via the existing `criticBodyStep`/`criticSummary` mechanism; (d) resolve each phase's `maxRounds` from the parsed `critics` block (Decision 5) — extend the existing `readDesignCriticConfig`/`parseCriticConfig` plumbing (the whole `critics` object already round-trips via `--key critics`; ref: Q6/Q8) with a small `resolveEdgeCriticMaxRounds(parsedCritics, phase)` helper returning `critics.<phase>.maxRounds` (positive integer) else 2, and feed its result into each phase's `criticConfig.maxRounds` rather than the literal `2`.

No new queries, middleware, or schema: the four edge critics reuse `qrspi-critic` and `CRITIC_VERDICT_SCHEMA` (ref: Q4); no new agent prompt files are needed (unlike the design panel's four lens agents).

## Pattern Decisions

### Decision 1: Edge-critic agent — reuse `qrspi-critic` vs four new lens agents

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Reuse the existing single `qrspi-critic` agent for all four phases; only vary `upstreamPath` per phase | No new agent files; matches the foundation loop's existing single-critic contract (ref: Q1, Q4); minimal surface | Generic prompt, no phase-specific framing of "high-leverage ambiguities" / "scope creep" |
| B | Author four new `qrspi-<phase>-critic` agent prompts mirroring the design lens agents | Phase-tailored rubric language | Four new files; the ticket explicitly chooses single (not panel) because leverage is lower than design — extra agents contradict that intent |

**Recommendation:** Option A
**Rationale:** The foundation loop already drives `qrspi-critic` with a per-call `upstreamPath`, and plan already uses exactly this shape (ref: Q1). The ticket frames these as cardinality-1 critics deliberately lighter than the design panel; reusing one agent honors that. Per-phase nuance can be injected via the loop's optional `rubric` line (ref: Q1) without new agent files.
**NEW PATTERN?** No — direct reuse of the RUS-55 single-critic loop and `qrspi-critic` agent.

### Decision 2: How research's citation node check slots into `runPhase`

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Add a generic `criticConfig.nodeCheck` field; `runPhase` runs it before the edge critic when present | Phase-agnostic, reusable for future node checks; keeps `runPhase` free of phase-name special-casing | Slightly more config plumbing in `doDesign` |
| B | Hard-code a `name === 'research'` guard in `runPhase` that invokes the validator | Simplest diff | Bakes a phase name into the generic dispatcher; not reusable; violates the existing presence-based dispatch idiom (ref: Q6) |

**Recommendation:** Option A
**Rationale:** `runPhase` today dispatches by presence of a config field (`lenses?.length`), not by phase name (ref: Q6). A `nodeCheck` field extends that idiom cleanly and keeps the node check before the edge critic, inside the staging window, matching the established "all checks on `stg` before persist" contract (ref: Q2).
**NEW PATTERN?** Yes — `runPhase` has no node-check step today (ref: Q2). Justified: the citation check is mechanical, not an LLM edge judgment, so it cannot reuse the critic loop; it is a new deterministic gate that the ticket explicitly calls for.

### Decision 3: Worktree-root resolution for the validator

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Validator takes an explicit `--worktree-root` arg (the JS passes `wd = r.worktreeDir`) | Correct against the worktree tree research actually ran on (ref: Q11); no ambiguity | One extra arg to pass |
| B | Validator self-locates via `resolve_repo_root()` and resolves citations against it | Matches other scripts' self-location | `resolve_repo_root()` returns the MAIN checkout, not the worktree — citations would resolve against the wrong tree (ref: Q11, Inconsistencies) |

**Recommendation:** Option A
**Rationale:** git-common-dir returns the main checkout; the research producer is already scoped to `REPO_ROOT = wd` (the worktree) and its citations are worktree-relative (ref: Q11). Passing `wd` explicitly is the only correct anchor. The script may still self-locate for nothing but its own module imports.
**NEW PATTERN?** No — mirrors how `runPhase` already passes `wd` to the research producer (ref: Q11).

### Decision 4: Citation parsing scope (and the forward-reference tolerance, resolved OQ3)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Resolve only literal forms (`file:line`, `file:start-end`, bare file); exclude any token with `*`, `<`, or `>` | Avoids false failures on the 944 illustrative glob/placeholder tokens (ref: Q9) | A genuinely broken glob-shaped citation slips through (acceptable — illustrative by design) |
| B | Attempt to resolve every backtick token | Maximal coverage | Mass false positives on placeholders/globs; would block legitimate research |

**Recommendation:** Option A
**Rationale:** Research artifacts intentionally contain placeholder/glob tokens as illustration (ref: Q9); only `:N`/`:N-M` and bare-file forms are literal references. Excluding `*`/`<`/`>` tokens matches the corpus and the fail-closed-but-not-false-positive intent.
**NEW PATTERN?** No — codifies the citation-form taxonomy already observed in research.md (ref: Q9).

**Forward-reference tolerance (resolves OQ3, reviewer PR #268 — "tolerated"):** the reviewer directs that a citation to a not-yet-created file within the same Graphite stack be **tolerated**, not hard-failed. The mechanical resolution is to split "non-resolving" into two cases the stdlib check can actually distinguish on disk:
- **file present, line/range out of bounds** → provably broken pointer → **hard-fail** with the verbatim token (this is the case AC2's "non-resolving citation fails the phase" genuinely targets);
- **file absent entirely** → indistinguishable by a stdlib check from a legitimate forward reference to a file a later slice will create → **tolerated** (no phase failure), since research runs in the design-time worktree which does not yet contain later-slice files (ref: Q11, which flags this behavior as undefined).

Honest limitation: this *does* let a typo'd missing-file path slip through (a false negative), exactly the trade the reviewer chose by saying "tolerated" — better than hard-failing every legitimate forward reference. A stdlib node check cannot read design intent to tell a planned future file from a typo, so the tolerance is applied at the coarsest safe boundary (file-existence) rather than fabricating a stack-aware discriminator the validator has no access to.

### Decision 5: Per-phase `maxRounds` — config-overridable vs hard-coded 2 (resolves OQ4)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Make each edge phase's `maxRounds` config-overridable from `critics.<phase>.maxRounds`, mirroring `critics.design` exactly; default to 2 | Consistent with the design phase the reviewer cited (`resolveDesignCritic` already does `Number.isInteger(cfg.maxRounds) && cfg.maxRounds > 0 ? cfg.maxRounds : 2`); the `critics` object already round-trips whole via `--key critics`, so no new config-reader capability is needed (ref: Q6, Q8); one operator knob covers all phases | A few lines of helper + per-phase wiring |
| B | Hard-code `maxRounds: 2` for the four edge phases | Smallest diff | Asymmetric with design (which IS config-overridable); the cap is the one critic knob most likely to need tuning, and re-adding it later is another ticket |

**Recommendation:** Option A
**Rationale:** The reviewer's comment asks for the planning-phase critics to be configurable "similar to design phase." Design already resolves `maxRounds` from `critics.design.maxRounds` with config > default-2 precedence via `resolveDesignCritic` (ref: Q8). The single-top-level-key config reader is not a blocker: `readDesignCriticConfig` already pulls the **entire** `critics` object with one `--key critics` read, so a sibling `resolveEdgeCriticMaxRounds(parsedCritics, phase)` can index `critics.<phase>.maxRounds` from the same parse — no dot-path reader and no extra config worker call (ref: Q6, the single-key constraint that bit slice 3). This keeps the planning critics symmetric with the design panel without new config machinery.
**NEW PATTERN?** No — reuses the existing `parseCriticConfig`/`resolveDesignCritic` precedence pattern (config-value > JS-default), generalized to a per-phase key.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Validator resolves citations against the main checkout instead of the worktree, producing spurious failures | med | high | Decision 3 Option A — pass `--worktree-root wd` explicitly; add a test asserting resolution against a tempdir-supplied root, not `resolve_repo_root()` (ref: Q11) |
| Research edge critic mistakenly anchored on the ticket, breaching the research firewall | med | high | Anchor research's `upstreamPath` on `art(wd,id,'questions.md')`, never `r.ticketContentPath`; call out in code comment (ref: Q12, Inconsistencies) |
| Citation validator false-positives on placeholder/glob tokens block legitimate research phases | med | med | Decision 4 — exclude `*`/`<`/`>` tokens; cover excluded forms explicitly in `_test.py` (ref: Q9) |
| Node check runs against canonical path instead of staged, so a failure still persists a bad artifact | low | high | Run validator on `stg(id,'research')` before `persistArtifact`, returning false to leave nothing persisted (ref: Q2, Q3) |
| New JS wiring (four critic configs + node-check branch) is untested since no JS test runner exists | high | med | Keep all testable logic in pure Python (`qrspi_verify_citations.py` fully unit-tested); verify JS glue by manual e2e per project convention (ref: Q14) |

## Open Questions

- OQ1: AC3 asks for before/after per-phase eval scores, but the eval harness is a non-functional placeholder (ref: Q15). Is reporting via per-round `log()` output + manual e2e (spliced into the PR body) acceptable, or must this ticket wait on / partially revive `run_eval.py`?
- OQ2: Should each edge critic receive a phase-tailored `rubric` line (e.g. questions = "high-leverage ambiguities", structure = "no scope creep"), or is the generic upstream→produced fidelity judgment sufficient for the first cut?
- OQ3: ~~How should a citation to a not-yet-created file within the same Graphite stack be treated — hard-fail, or tolerated (ref: Q11 notes this behavior is undefined and stacked later-slice files may not yet exist in the worktree tree)?~~ **RESOLVED (reviewer, PR #268): tolerated.** A wholly-absent file is treated as a tolerable forward reference (no phase failure); only a file that *exists* with an out-of-range line hard-fails. See Decision 4 (forward-reference tolerance) and AC2's scope boundary.
- OQ4: ~~Should per-phase `maxRounds` be config-overridable (extending `critics.<phase>` parsing like `critics.design`; ref: Q8) in this ticket, or is the hard-coded default of 2 sufficient for now?~~ **RESOLVED (reviewer, PR #268): yes — make per-phase `maxRounds` config-overridable, mirroring the design phase.** See Decision 5; reflected in AC1 and the Delta.
