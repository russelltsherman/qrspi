# Implementation Log — qrspi critics 3/5: single edge critics for planning phases + citation validator

## Session 1 — Slice 1

**Timestamp:** 2026-06-13T19:40:00Z
**Tasks completed:** T1, T2, T3, T4, T5, T6, T7
**Tasks failed:** none
**Tests:**

- `python3 scripts/qrspi_verify_citations_test.py` → 16 passed, 0 failed
- Manual CLI smoke (fixture research.md): out-of-range `real.py:99` → `{"ok": false, "unresolved": ["real.py:99"]}` exit 1; clean (valid `file:line` + absent-file forward ref) → `{"ok": true, "unresolved": []}` exit 0

**Deviations from structure.md:**

- none

**Deviations from plan.md:**

- none

**Notes for next session:**

- New files: `scripts/qrspi_verify_citations.py` and `scripts/qrspi_verify_citations_test.py`. Stdlib-only, self-locating only for its own imports.
- Public API for Slice 2 wiring: `verify(artifact_path, worktree_root) -> {ok, unresolved, error?}`, plus pure `parse_citations(text)` and `resolve_citation(token, worktree_root)`.
- CLI contract (the `nodeCheck` Slice 2 invokes): `python3 scripts/qrspi_verify_citations.py --artifact-path <staged research.md> --worktree-root <wd>` prints one single-line `CitationCheckEnvelope` and exits 0 on ok, 1 otherwise. Both args are REQUIRED.
- Resolution semantics confirmed by tests: absent file => tolerated (True, forward reference OQ3); file present + line/range out of bounds => the only False (AC2 hard-fail); glob/placeholder tokens (`*`, `<`, `>`) excluded at parse; bare backtick code-words (`runPhase`, `ok`) are NOT treated as citations (require a `/` or dotted extension to count as a file).
- Citation resolution joins ONLY against the supplied `--worktree-root`, never `resolve_repo_root()` (Risk Register med/high) — Slice 2 must pass `wd`, not `r.repoRoot`, as `--worktree-root`.

---

## Session 2 — Slice 2

**Timestamp:** 2026-06-13T20:30:00Z
**Tasks completed:** T8, T9, T10, T11, T12, T13, T14, T15, T16, T17, T18, T19
**Tasks failed:** none
**Tests:**

- `node --check .claude/workflows/qrspi-batch.js` → syntax OK
- Ad-hoc node unit test of the two new pure helpers (`parseCriticsObject`, `resolveEdgeCriticMaxRounds`) → 14 passed, 0 failed (positive-int honored; 0/negative/non-int/absent-phase/undefined-parsedCritics/empty-obj all fall back to 2; whole-object parse vs empty/ok:false/key-mismatch/array/garbage all undefined)
- `python3 -c json.load(.qrspi/config.example.json)` → valid JSON
- Slice 1 regression: `python3 scripts/qrspi_verify_citations_test.py` → 16 passed, 0 failed (step 23)
- Validator CLI contract smoke against the exact `nodeCheck.cmd` form (`--artifact-path <staged research.md> --worktree-root <wd>`): clean (in-bounds `real.py:2` + absent-file forward ref) → `{"ok": true, "unresolved": []}` exit 0; out-of-bounds `real.py:99` → `{"ok": false, "unresolved": ["real.py:99"]}` exit 1

**Deviations from structure.md:**

- none. `NodeCheckSpec` shape pinned (per structure's explicit TBD) to `{ cmd: <full command string> }` — the command is built at the `doDesign` call site (where `wd`/`r` are in scope) and carried verbatim, so `runPhase`/`runNodeCheck` need no path context.

**Deviations from plan.md:**

- **T16 (residual-findings splice) implemented by aggregation, not per-phase splice.** `scripts/qrspi_critic_body.py` only knows the `design`/`plan` branch suffixes (`_PHASE_BRANCH`, and `--phase` is `choices=['design','plan']`); there is NO questions/research/structure branch — questions+research+design all land on `<id>/design`, structure+plan+worktree on `<id>/plan`. So questions+research residual findings are AGGREGATED into the single design-commit splice (each tagged `[questions]`/`[research]`), and structure findings into the plan-commit splice (tagged `[structure]`). This faithfully realizes the design intent ("flow through the same criticBodyStep/criticSummary mechanism") without inventing branches the script cannot address. The plan's literal "criticBodyStep(t.id,'questions',…)" call form would have been rejected by the script.
- **`doPlan` now does its OWN `--key critics` read** (via `readDesignCriticConfig()`, which I extended to also return `parsedCritics`). The plan's step 15 phrasing ("thread the existing parsed result") assumed doDesign's read was reachable from doPlan; they are SEPARATE batch actions/invocations, so doPlan reads once itself — still one read per invocation (Q6/Q8 honored).

**Notes for next session:**

- **No remaining implementation slices.** Both slices done; the feature is whole.
- **JS changes** (all in `.claude/workflows/qrspi-batch.js`): new pure helpers `parseCriticsObject(text)` (whole `critics` object; `parseCriticConfig` now layers on it) and `resolveEdgeCriticMaxRounds(parsedCritics, phase)` (positive-int else 2); new `runNodeCheck(id, name, nodeCheck)` + `NODECHECK_SCHEMA`; `runPhase` gained a pre-critic `if (criticConfig?.nodeCheck)` branch that runs on `stg(id,name)` and `return false`s on non-ok (nothing persists); `readDesignCriticConfig()` now returns `{…, parsedCritics }` from ONE read; `doDesign` wires questions (upstream=ticket), research (upstream=questions.md + nodeCheck, with a firewall comment that it is NEVER the ticket), reusing the design panel; `doPlan` wires structure (upstream=design.md) and swaps plan's literal `maxRounds:2` for the resolver.
- **Research firewall** is load-bearing: `researchCritic.upstreamPath = art(wd,t.id,'questions.md')` — never `r.ticketContentPath` (Risk Register med/high). Verified present with its guard comment.
- **`nodeCheck.cmd`** uses `engineCmdFor(r, 'scripts/qrspi_verify_citations.py')` (host-checkout root, survives a relocating ticket) and passes `--worktree-root ${wd}` (NOT `r.repoRoot`) per Slice 1's hard requirement — citation resolution joins against the worktree root only.
- **Manual e2e procedure (T17 — recorded here for the PR phase to surface; no JS test runner exists per project convention):**
  1. Run a design-phase batch on a test ticket; via per-round `log()` confirm questions/research/structure each spawn an edge critic with the expected upstream anchor (questions→ticket, research→questions.md NEVER the ticket, structure→design.md).
  2. Stage a `research.md` with an out-of-range `file:line`; the research phase must fail with the verbatim token in the node-check envelope and persist nothing (canonical `research.md` absent after the failed run).
  3. Stage a `research.md` citing a wholly-absent file; research must NOT fail (forward-reference tolerance, OQ3).
  4. Set `critics.research.maxRounds` in `.qrspi/config.json` and confirm via `log()` the research critic loop honors it; unset/malform it and confirm fallback to 2.
- **AC3 (per-phase before/after eval scores) and OQ2 (per-phase rubric framing)** remain carried-forward unverified assumptions (eval harness is a placeholder; generic single critics wired, no `rubric`). Neither blocks; both are human-confirmation items at PR review.
