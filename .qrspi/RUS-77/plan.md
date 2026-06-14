# Implementation Plan — Critic effectiveness: instrumentation, cost reduction, teeth eval

**Structure basis:** structure.md @ 2026-06-14T18:30:00Z
**Generated:** 2026-06-14T19:00:00Z
**Revised:** 2026-06-14 (addressed plan-PR #299 CHANGES_REQUESTED — findings #1–#6 + Low); 2026-06-15 (follow-up: fixed a residual step-22 leak that still told the implementer to resolve the digest script path via `engineCmdFor`/`r.repoRoot` inside `runCriticPanelLoop`, where `r` is out of scope — now uses the `engineCmd`/main-repo-root-worker convention per finding #4 and the call-graph note)
**Status:** draft
**Total steps:** 41

> Slice→AC map (from structure.md): Slice 1–2 → AC-INSTR; Slice 3–4 → AC-COST;
> Slice 5 → AC-TEETH. Slices 1, 3, 5 are tested Python cores with no JS dependency
> (parallelizable); Slice 2 depends on 1, Slice 4 depends on 3.

## Slice 1: Metrics reducer + ledger appender (tested Python core)

### Setup

1. ✨ Create `scripts/qrspi_critic_metrics.py` — pure reducer module. Define the canonical record shape per structure.md `CriticStepMetrics { phase: str, rounds: CriticRoundRecord[], terminalAction: str, tokensIn?: int, tokensOut?: int }` where `CriticRoundRecord { lens: str, pass: bool, findingsCount: int }`. Module-level docstring referencing the mirror of `qrspi_critic_synthesize.py`.
   - **Known limitation (review finding — token cost ships unmeasured):** `tokensIn?`/`tokensOut?` are OPTIONAL and, per OQ2 (no per-subagent token usage is exposed by the harness today), the JS wiring in slice 2 supplies no `usage`, so these keys are **never populated** in practice. The AC-INSTR "at what token cost" dimension therefore ships **unmeasured** in this ticket — acknowledged at design level (OQ2). The fields are kept optional/absent (not removed) so a future ticket can populate them if the harness later exposes usage, but the docstring and step 23/Slice-2 checkpoint must state plainly that the cost dimension is currently unmet rather than implying it is captured.

### Core Logic

2. ⚠️ Modify `scripts/qrspi_critic_metrics.py` — implement `build_record(verdicts, terminalAction, usage=None, phase=...) -> dict` per structure.md Contract. `verdicts` is a list of per-lens/per-round dicts each carrying `lens`, `pass`, `findings` (list); map each to `{lens, pass: bool, findingsCount: len(findings)}`. `phase` is taken from a `phase` argument. Validate `terminalAction` against the set of **actual loop terminations** — `{"converged","cap_reached","exhausted","aborted"}` — and raise `ValueError` otherwise. **`revise` is NOT in the enum**: `revise` is a mid-loop continuation (the loop re-critiques after it; see `runCriticLoop`/`runCriticPanelLoop` in `qrspi-batch.js`), never a terminal state, so a record is only ever built once the loop has actually terminated. The four enum values map to the loops' real return sites: `converged` (decision.action == 'converged'), `cap_reached` (decision.action == 'cap_reached'), `exhausted` (loop ran out of rounds without an explicit decision return — the defensive `ok:true` tail), and `aborted` (any `ok:false` early return — verdict-agent failure, decision failure, or reviser failure — so aborted steps still emit a record and AC-INSTR base rates are NOT biased toward successful terminations). Emit `tokensIn`/`tokensOut` keys ONLY when `usage` supplies them (absent by default per OQ2).
   - **Current:** file is a bare module skeleton (step 1)
   - **After:** `build_record(verdicts, terminalAction, usage=None, phase=...) -> {phase, rounds:[{lens,pass,findingsCount}...], terminalAction, tokensIn?, tokensOut?}`; `terminalAction` enum = `{converged, cap_reached, exhausted, aborted}` (NOT `revise`)
   - **Note (node-vs-edge — chain reconciled):** `structure.md:19` previously added the non-terminal `revise` to the `terminalAction` enum (and omitted `exhausted`/`aborted`), and `design.md:76` lists only `converged/cap_reached`. Both were stale against the actual loop terminations. `structure.md:19` has now been corrected **in this same PR** to the four-value enum `{converged, cap_reached, exhausted, aborted}` (with a one-line note flagging the `design.md:76` discrepancy), so plan, structure, and the real `runCriticLoop` return sites (`qrspi-batch.js:710-773`) now agree. `design.md:76` remains stale by one value-set; that is a node-level (design) wording fix, out of scope for this plan PR, and is now called out in `structure.md` so a future design touch can reconcile it.
3. ✨ Create `scripts/qrspi_critic_metrics_test.py` — unit tests for `build_record`: (a) all-pass verdicts → rounds with `pass:true`, `findingsCount:0`; (b) mixed pass/fail → correct per-lens flags and findings counts; (c) `usage=None` → no `tokensIn`/`tokensOut` keys present (OQ2); (d) `usage` provided → keys present; (e) **each** of the four valid `terminalAction` values (`converged`, `cap_reached`, `exhausted`, `aborted`) is accepted; (f) `terminalAction="revise"` raises `ValueError` (revise is not terminal); (g) any other invalid `terminalAction` raises `ValueError`. Stdlib `unittest` only.

### Core Logic (appender)

4. ✨ Create `scripts/qrspi_metrics_append.py` — self-locating CLI modeled on `qrspi_persist.py`. Argparse `--ticket <id>` and `--record <json>`. **Resolve the repo root EXACTLY as `qrspi_persist.py` does — via `qrspi_paths.resolve_repo_root(cwd=os.getcwd(), validate=False)` (git-common-dir first, so it yields the MAIN checkout even when invoked from a worktree; `__file__`-parent is only `resolve_repo_root`'s internal last resort, NOT something this script keys off directly).** Do NOT self-locate from `__file__`: this script lives at `.worktrees/<id>/scripts/…` in a worktree, so an `__file__`-parent root would be the *worktree* root, and joining `.worktrees/<id>/.qrspi/<id>/` onto it double-nests to `.worktrees/<id>/.worktrees/<id>/.qrspi/…` — a silent mis-persist that the non-empty verify would still pass (the exact failure class `qrspi_persist.py` and `resolve_repo_root` exist to prevent; see `scripts/qrspi_persist.py:37-50`). Resolve the ledger path off the `resolve_repo_root` result `<root>/.worktrees/<id>/.qrspi/<id>/critic-metrics.jsonl`. Parse `--record` as JSON (fail-closed: exit non-zero on invalid JSON). `--ticket <id>` is consumed for BOTH path resolution AND as the `ticketId` envelope field (next step) — per structure.md `CriticMetricsLedgerLine`, the line is NOT the bare `CriticStepMetrics` record.
   - File purpose: append one `CriticMetricsLedgerLine` per critic step to the durable per-ticket ledger.
   - Path-resolution reference: import and call `qrspi_paths.resolve_repo_root` (same import `qrspi_persist.py` uses), NOT `os.path.dirname(__file__)`.
5. ⚠️ Modify `scripts/qrspi_metrics_append.py` — implement envelope-wrap + append-and-verify. Build the **ledger line** as the parsed `CriticStepMetrics` record **plus the two required envelope fields** per structure.md `CriticMetricsLedgerLine`: inject `ticketId` (from `--ticket <id>`) and `timestamp` (generated at write time, UTC ISO-8601 — `datetime.now(timezone.utc).isoformat()`, stdlib only) into a shallow copy of the record; if the parsed record already carries `ticketId`/`timestamp` the appender's values win (the appender is the single envelope authority). Create parent dir if needed, open in append mode, write `json.dumps(ledger_line)` + `\n` (NOT bare `json.dumps(record)` — the envelope MUST be present), then verify the file is non-empty (`os.path.getsize > 0`) like `qrspi_persist.py`; exit non-zero if the verify fails (fail-closed).
   - **Current:** parses args + record only (step 4)
   - **After:** appends one verified `CriticMetricsLedgerLine` JSON-line carrying `{...CriticStepMetrics, ticketId, timestamp}`; second invocation appends rather than overwrites
6. ✨ Create `scripts/qrspi_metrics_append_test.py` — unit tests: (a) first call creates the ledger file with exactly one line; (b) second call appends → two lines, first line intact (no overwrite); (c) each line is valid JSON and, when parsed, carries **every** `CriticStepMetrics` field of the input record AND the two envelope fields — `ticketId` equals the `--ticket` value and `timestamp` is a present, non-empty ISO-8601 string (assert the line is the envelope-wrapped shape, NOT the bare record); (d) invalid `--record` JSON exits non-zero and writes nothing (fail-closed); (e) **path-resolution regression** — drive the resolver through a known root (pass an explicit root / monkeypatch `qrspi_paths.resolve_repo_root` to a `tempfile` dir, mirroring how `qrspi_persist`'s tests pin the root) and assert the ledger lands at exactly `<root>/.worktrees/<id>/.qrspi/<id>/critic-metrics.jsonl` with NO `.worktrees/<id>/.worktrees/<id>/…` double-nesting (guards finding #2); use a `tempfile.TemporaryDirectory` ticket sandbox.

### Verify Slice 1

7. **Checkpoint:** `python3 scripts/run_tests.py metrics`
   - [ ] Both `qrspi_critic_metrics_test.py` and `qrspi_metrics_append_test.py` pass
   - [ ] `build_record` omits `tokensIn`/`tokensOut` when no usage given (OQ2)
   - [ ] Ledger preserves BOTH pass/fail tally AND `findingsCount` per step (OQ4 — not collapsed to a single rate)
   - [ ] Each ledger line is a `CriticMetricsLedgerLine` = the `CriticStepMetrics` record PLUS `ticketId` (from `--ticket`) and `timestamp` envelope fields (structure.md New Types — NOT the bare record)
   - [ ] A second appender call appends rather than overwrites

---

## Slice 2: Wire metrics into the critic loops + result object (JS shell)

### Setup

8. ✅ **No `.gitignore` edit needed (review finding: redundant).** The ledger lands at `.worktrees/<id>/.qrspi/<id>/critic-metrics.jsonl`, and `.gitignore` already ignores `.worktrees/` (`.gitignore:3`), so the ledger is already untracked — verified via `git check-ignore -v .worktrees/<id>/.qrspi/<id>/critic-metrics.jsonl` → matches `.gitignore:3:.worktrees/`. The Risk Register "untracked-file leak" is therefore already covered; do NOT add a `**/.qrspi/*/critic-metrics.jsonl` rule (it would be dead). Action for this step: just confirm the `git check-ignore` probe still matches `.worktrees/` after the ledger is first written.
   - **Current:** ledger path already ignored by the existing `.worktrees/` rule
   - **After:** unchanged `.gitignore`; ledger confirmed untracked by the existing rule

### Core Logic

> **Call-graph reality (resolves review findings #3, #4, #5 — read before steps 9–12):**
> The critic loops are NOT called from `doDesign` directly. `doDesign` (`qrspi-batch.js:1457`)
> calls `runPhase` (`:1238`), and `runPhase` dispatches the loops at `:1281-1286`
> (`criticConfig.lenses?.length ? runCriticPanelLoop : runCriticLoop`). So the metrics record
> must flow **loop → `runPhase` return value → `doDesign`**, with `runPhase` as the named
> intermediary — a literal implementer editing `doDesign` to "call the loop" would edit the
> wrong function. Two more realities the prior wording got wrong:
> - **Neither loop accumulates per-round verdicts today, and each `return`s from 5–6 internal
>   sites** (converged / cap_reached / exhausted-tail / each `ok:false` abort — `runCriticLoop`
>   `:710-773`, `runCriticPanelLoop` `:801-…`). Capturing `rounds[]` + the `terminalAction` is a
>   **per-return-site restructure**, not a single tail append: introduce a `rounds` accumulator
>   pushed each iteration (the per-lens/per-round `{lens, pass, findings}` verdict), and at EVERY
>   return site stamp the matching `terminalAction` (`converged`/`cap_reached`/`exhausted` for the
>   `ok:true` sites, `aborted` for the `ok:false` sites) and build+append the record there (or
>   return `{rounds, terminalAction}` on the existing `{ok, residualFindings}` envelope and let a
>   single helper build+append once at the loop boundary). Aborts MUST emit a record too, or
>   AC-INSTR base rates skew toward successful terminations.
> - **`r`/`repoRoot` is NOT in scope in either loop** — both take only `(name, id, criticConfig)`.
>   So the script path can't use `engineCmdFor(r, …)` directly. Thread `repoRoot` into the loops
>   the SAME way `ticketContentPath`/`questionsPath` are already threaded — as a field on
>   `criticConfig` (populated in `doDesign`/`runPhase` where `r` is in scope; see the comment at
>   `:799`) — then build the script path from `criticConfig.repoRoot`. Reconcile with the existing
>   reducer-sibling `synthesizeVerdicts` (`:903`), whose worker runs Python via **`engineCmd`** (the
>   `.`-relative form); pick ONE convention for the metrics shell-out and state it explicitly
>   (recommended: match `synthesizeVerdicts` and run via `engineCmd('scripts/…')` from the worker's
>   main-repo-root cwd, since that path is already proven for the synthesize reducer — do NOT just
>   assert `engineCmdFor` without the in-scope `r` to feed it).

9. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — in `runCriticLoop` (edge-critic single loop), inside the existing `if (criticConfig)` guard, accumulate a `rounds[]` verdict array across iterations and, at EACH return site, stamp the matching `terminalAction` and build+append the record (or return `{rounds, terminalAction}` on the existing envelope for a single build+append at the loop boundary — see the call-graph note). Build the record via the reducer (`qrspi_critic_metrics.py`) and append via `python3 scripts/qrspi_metrics_append.py --ticket <id> --record <json>`, running the Python through the SAME convention `synthesizeVerdicts` uses (a worker at main-repo-root cwd via `engineCmd('scripts/…')`), since `r`/`repoRoot` is not in scope here. Return the produced record on the loop's envelope for `runPhase` to surface.
   - **Current:** `runCriticLoop` records outcomes only in `log(...)` + the free-text `summary`; returns `{ok, residualFindings}`; no verdict accumulation; 5–6 internal return sites
   - **After:** on each invocation (critics enabled only) it appends one ledger line covering EVERY termination (including `aborted`) and surfaces its `CriticStepMetrics` record via the envelope
10. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — in `runCriticPanelLoop`, inside the same `if (criticConfig)` guard, accumulate the per-lens/per-round verdicts array (lens, pass, findings) and apply the SAME per-return-site `terminalAction`-stamp + build+append pattern as step 9 across all of its 5–6 return sites; surface the record on its envelope.
    - **Current:** panel outcomes recorded only in `log` + `summary` string; `{ok, residualFindings}` envelope; multiple return sites; no verdict accumulation
    - **After:** one ledger line per panel loop (every termination, including aborts); returns the record on the envelope
11. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — in `runPhase` (`:1238`, the intermediary that actually dispatches the loops at `:1281-1286`), capture the record(s) surfaced on each loop's envelope and include them on `runPhase`'s return value; then in `doDesign` (`:1457`) collect the records from `runPhase`'s return into a `criticMetrics` array and fold it into the ticket result object alongside the existing summary splices. (Thread `repoRoot` onto `criticConfig` here, where `r` is in scope, per the call-graph note.)
    - **Current:** result object is `{ticketId, action, newStatus?, summary, prUrl?}` (no metrics slot); `runPhase` returns a bare boolean and does not surface critic records; loops are reached only via `runPhase`, never `doDesign` directly
    - **After:** `runPhase` surfaces the loop records to its caller; `doDesign` result object gains `criticMetrics: CriticStepMetrics[]` (per structure.md Modified Types: `TicketResult`)
12. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — confirm every new reducer/appender call (in both loops) and the `runPhase`-surface + `doDesign` `criticMetrics` fold are reachable ONLY when critics are enabled: the loop-level calls stay inside the existing `if (criticConfig)` guard, and in `runPhase`/`doDesign` the record-capture and fold are reachable only when the loops actually ran (which `runPhase` already gates on `if (criticConfig)` at `:1280`). When `criticConfig` is falsy the loops are never dispatched, so `runPhase` surfaces no records and `doDesign` adds no `criticMetrics` key — the disabled path returns the byte-for-byte-unchanged result object with no ledger write.
    - **Current:** (after steps 9–11) new calls present
    - **After:** disabled path provably untouched — no metrics calls reachable when `criticConfig` is falsy (loops un-dispatched ⇒ no records to surface or fold)

### Verify Slice 2

13. **Checkpoint:** Manual end-to-end design run with critics ENABLED on a scratch ticket, then a second run with critics DISABLED.
    - [ ] Enabled run writes `.worktrees/<id>/.qrspi/<id>/critic-metrics.jsonl` with one line per edge-critic loop AND one per panel loop
    - [ ] Each emitted line is the envelope-wrapped `CriticMetricsLedgerLine` (carries `ticketId` matching the run's `<id>` and a `timestamp`), not the bare `CriticStepMetrics`
    - [ ] The enabled-run ticket result object carries a non-empty `criticMetrics` array
    - [ ] The disabled run writes NO ledger and returns an unchanged result object (guard verified)
    - [ ] `git status` shows the ledger is gitignored by the existing `.worktrees/` rule (no untracked-file leak; no new `.gitignore` entry was added — step 8)

---

## Slice 3: Config gates for the three cost levers (tested Python core + mirror)

### Core Logic

14. ⚠️ Modify `scripts/qrspi_critics_config.py` — extend `resolve_design(config)` to add three nested keys to the returned `DesignCriticConfig`: `digest: {enabled: bool}` (default `{"enabled": False}`), `lensModel` (optional `str`, default absent/`None`), `gateBehindEdge: {enabled: bool}` (default `{"enabled": False}`). All default OFF/absent, preserving the current `{enabled, maxRounds, lenses, candidates}` shape.
    - **Current:** `resolve_design(config) -> {enabled, maxRounds, lenses, candidates}`
    - **After:** `resolve_design(config) -> {enabled, maxRounds, lenses, candidates, digest:{enabled}, lensModel?, gateBehindEdge:{enabled}}` (three new gates default OFF/absent)
15. ⚠️ Modify `scripts/qrspi_critics_config_test.py` — add tests: (a) with no critics-config keys, all three new gates default OFF / `lensModel` absent (current behavior preserved); (b) `digest.enabled=true` parses through; (c) `lensModel="..."` parses through; (d) `gateBehindEdge.enabled=true` parses through; (e) a parity assertion that the Python defaults equal the JS `DEFAULT_CRITIC_PHASES` mirror values (e.g. load/compare the expected default dict literal kept in sync with step 16).
16. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — update the `DEFAULT_CRITIC_PHASES` mirror so its design defaults include `digest:{enabled:false}`, `lensModel` absent, `gateBehindEdge:{enabled:false}`, kept in lockstep with `resolve_design` (ref: structure.md Modified Types `DEFAULT_CRITIC_PHASES`).
    - **Current:** mirror reflects `{enabled, maxRounds, lenses, candidates}` only
    - **After:** mirror includes the three new default-OFF nested gates
17. ⚠️ Modify `.qrspi/config.example.json` — document the new design-critic knobs under the `critics` design block: `digest.enabled`, `lensModel`, `gateBehindEdge.enabled`, each shown with its default-OFF value and a short comment-style key (example file is JSON; document via representative default values).
    - **Current:** example shows `{enabled, maxRounds, lenses, candidates}` for design critics
    - **After:** example also shows the three default-OFF cost-lever knobs

### Verify Slice 3

18. **Checkpoint:** `python3 scripts/run_tests.py critics_config`
    - [ ] All `qrspi_critics_config_test.py` cases pass
    - [ ] Tests assert all three gates default OFF / `lensModel` absent (current behavior preserved)
    - [ ] Parity test asserts the Python defaults and the JS `DEFAULT_CRITIC_PHASES` mirror agree (lockstep)

---

## Slice 4: Cost levers — shared digest (primary), per-lens model, edge gate

> **Scope honesty — only ONE of the three AC-COST levers is guaranteed to do work; the other two are speculative and may ship inert (addresses plan-PR #299 inline comment).** State plainly:
> - **Digest (steps 19–23, 28–30) — the real lever.** Deterministic, pure-Python, unit-tested, and it provably trims a REAL `research.md` (the 4× ~36KB re-reads are the measured cost driver, Q1). This is the lever AC-COST actually rests on. Decision 3 already named it primary.
> - **`lensModel` (step 24; checkpoint step 31, line 183) — speculative.** It rides an **unverified harness seam**: there is no evidence the `agent()` call honors a `model` option (Risk Register / Q4). If the harness ignores it, the knob is inert. Ships default-OFF; verified by a single manual spawn; explicitly does NOT block the ticket.
> - **`gateBehindEdge` (step 25; checkpoint step 32) — speculative, and the call graph cannot currently support it.** Verified against the code: `runPhase` (`qrspi-batch.js:1280-1286`) routes design to `runCriticPanelLoop` (it has `lenses`) **OR** `runCriticLoop` (the edge critic) as **mutually-exclusive alternatives at the same dispatch — not a sequence.** So for the **design** phase there is no edge-critic pass/fail outcome in scope to gate the panel behind. The lever therefore degrades to "no-op when no edge outcome exists, record the gap, don't block" (step 25 risk note, line 160). It is honest config wiring, not a working optimization, until/unless an upstream edge outcome is plumbed in.
>
> **Why `gateBehindEdge` is NOT cut from this ticket** (the reviewer's second ask, considered): cutting it cannot be done as a plan-phase edit. The `gateBehindEdge:{enabled}` gate is a fixed contract in the upstream **structure.md** (`DesignCriticConfig`, Slice 3 config gate, Slice 4 wiring, AC-COST mapping) and **design.md** Decision 3 Option C / OQ3-RESOLVED. The plan must derive faithfully from structure; unilaterally dropping a structure-level contract here would create a plan↔structure divergence, which is a **reset-to-structure** action, not an in-place plan revision. The defensible plan-phase response is what steps 14–17, 25, and this note now do: ship the config gate (default-OFF, tested in step 18) and the **honestly-conditional** wiring that no-ops when the call graph offers no edge outcome — never a knob that claims a sequence the code can't provide. If the reviewer wants `gateBehindEdge` removed from the feature outright (a reasonable call, since two of three levers are speculative), that is a `CHANGES_REQUESTED` on the **design/structure** PRs to drop Decision 3 Option C and the `DesignCriticConfig` key, after which this plan would faithfully follow.

### Setup

19. ✨ Create `scripts/qrspi_research_digest.py` — self-locating CLI. Argparse `--research <path>` and `--out <path>` per structure.md Contract. Module docstring defining the concrete extraction policy **re-derived from research.md's ACTUAL structure** (this resolves a Slice-5/structure Unverified Assumption AND fixes review finding #1 — the prior whitelist named `## Current State`/`## Desired End State`/`## Delta`, which belong to the design/structure template and **never appear in research.md**; see `.qrspi/templates/research.md` and any real `research.md`, whose top-level sections are `## Q1`…`## Q<n>` plus `## Discovered Patterns` and `## Inconsistencies`). The policy is therefore **content-reducing, not section-dropping**: KEEP every `## Q<n>` section header and its title line, every `## Discovered Patterns` section, and every `## Inconsistencies` section (i.e. retain ALL of research's real top-level sections — there is no header to drop), but within each section STRIP the fenced ` ``` ` **Evidence** code blocks (the bulk of the bytes — each Q carries up to a 20-line code fence per the template) while keeping the prose lines (`**Answer:**`, `**Dependencies:**`, `**Implicit contracts:**`, the Discovered-Patterns / Inconsistencies prose). This is deterministic (line-scan: drop everything between a fenced-code opening ` ``` ` and its matching closing ` ``` `, keep all other lines verbatim; no LLM), and it actually reduces tokens on the REAL research structure rather than matching headers that don't exist.
   - File purpose: produce a deterministic trimmed digest of research.md once, passed by path to all lenses. The lenses still receive every question's findings/contracts; only the verbose evidence code fences are elided.
20. ⚠️ Modify `scripts/qrspi_research_digest.py` — implement extraction: read `--research`, scan lines, and emit every line EXCEPT those inside a fenced code block (toggle a `in_fence` flag on each ` ``` ` line; drop the fence delimiters and their contents), preserving all section headers and prose in document order; write the result to `--out`. If the read yields an empty/whitespace-only file OR the digest after stripping is empty/whitespace-only, write nothing and exit non-zero (fail-closed; the call site also guards with `test -s`). (Note: because the policy keeps headers rather than whitelisting by name, the only fail-closed trigger is genuinely-empty input/output — there is no "no whitelisted header found" branch to dead-end on a real research.md.)
   - **Current:** arg-parsing skeleton (step 19)
   - **After:** deterministic evidence-fence-stripped digest written to `--out`; empty input or empty result exits non-zero
21. ✨ Create `scripts/qrspi_research_digest_test.py` — unit tests built on a fixture shaped like the REAL research template (`## Q1`/`## Q2` with `**Answer:**` prose + a fenced ` ``` ` evidence block, plus `## Discovered Patterns` and `## Inconsistencies`): (a) output retains every section header and all prose lines, and contains NONE of the fenced code-block contents (and is strictly shorter than the input — the lever actually trims); (b) output is byte-identical across two runs on the same input (determinism); (c) empty-input research → exit non-zero, no/empty output (fail-closed); (d) a research file that is ALL fenced code (digest would be empty after stripping) → exit non-zero (fail-closed). Use `tempfile` for paths.

### Core Logic (JS wiring)

22. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — when `criticConfig.digest.enabled`, before the panel fan-out shell out to `python3 scripts/qrspi_research_digest.py --research <researchPath> --out <digestPath>`, then guard with `test -s <digestPath>`; if the guard fails, fail the phase fail-closed (ref: Q1, Q8) — do NOT fan out with an empty digest. **Script-path resolution: this shell-out lives inside `runCriticPanelLoop`, where `r`/`repoRoot` is NOT in scope (the loop takes only `(name, id, criticConfig)`), so it CANNOT use `engineCmdFor(r, …)` — use the SAME convention `synthesizeVerdicts` (`:903`) already proves for its Python shell-out: run it via a worker at main-repo-root cwd using `engineCmd('scripts/qrspi_research_digest.py')` (the same single convention picked for the metrics shell-out in steps 9–10; see the call-graph note above, lines 76–85). Do NOT reintroduce `engineCmdFor`/`r.repoRoot` here.
    - **Current:** panel fan-out always passes the four full paths to every lens; no digest step
    - **After:** with `digest.enabled`, a digest is built once and `test -s`-guarded before fan-out
23. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — when `digest.enabled`, thread `DIGEST_PATH=<digestPath>` into each lens `agent(...)` input; when disabled, pass no `DIGEST_PATH` (lenses fall back to full `RESEARCH_PATH`, unchanged default).
    - **Current:** lenses receive only DESIGN_PATH, TICKET_CONTENT_PATH, RESEARCH_PATH, QUESTIONS_PATH
    - **After:** lenses additionally receive `DIGEST_PATH` only when the digest lever is ON
24. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — when `criticConfig.lensModel` is set, pass it as the `model` option on each lens `agent(...)` call; otherwise pass no model option (current behavior).
    - **Current:** lens `agent(...)` calls pass `{label, phase, agentType?, schema?}` — no `model`
    - **After:** lens `agent(...)` calls pass `model: criticConfig.lensModel` when the lever is ON
25. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — implement the `gateBehindEdge` lever where the edge-vs-panel dispatch actually lives. The edge critic and the panel are NOT both invoked from a single function today: `runPhase` (`:1281-1286`) routes a phase to EITHER `runCriticPanelLoop` (design, `lenses?.length`) OR `runCriticLoop` (single edge critic) — they are alternatives, not a sequence, so "skip the panel when the edge passed" requires first establishing where an edge-critic outcome for the design phase exists to gate on. Concretely: (a) identify/define the upstream edge-critic outcome the design panel should gate behind (the prior-phase edge critic's pass/fail), and plumb that outcome into the design-phase `runPhase` call (e.g. as a field on the design `criticConfig`, populated in `doDesign` where the prior-phase result `r` is in scope — the same threading channel used for `repoRoot`/`ticketContentPath`); (b) when `criticConfig.gateBehindEdge.enabled` AND that upstream edge outcome is "passed", `runPhase`/`doDesign` skips dispatching `runCriticPanelLoop` for the design phase; (c) when disabled (default) or the edge did not pass, the panel runs as today. Name `runPhase`/`doDesign` (not a mythical single edge-then-panel function) as the gate site.
    - **Current:** `runPhase` routes to panel OR single-critic unconditionally; there is no edge→panel sequencing to gate, and no prior-edge outcome plumbed into the design-phase `runPhase` call
    - **After:** with `gateBehindEdge.enabled` and a passing upstream edge outcome (plumbed into the design `criticConfig`), the design panel is skipped at the `runPhase`/`doDesign` dispatch; default always runs the panel
    - Risk note: this lever depends on a prior-phase edge-critic outcome existing to gate on. If no such upstream edge outcome is available for the design phase in the current call graph, treat `gateBehindEdge` as a no-op-when-no-edge (default-OFF already, so unchanged behavior) and record that gap rather than fabricating a sequence — do NOT block the ticket on it (digest is the primary cost lever).

### Core Logic (agent input contract)

26. ⚠️ Modify `.claude/agents/qrspi-design-critic-completeness.md` — accept an optional `DIGEST_PATH` input; when present, Read it in place of (or in addition to) `RESEARCH_PATH`; when absent, Read `RESEARCH_PATH` as today (ref: structure.md Lens agent input contract).
    - **Current:** lens always Reads `RESEARCH_PATH` (full research.md)
    - **After:** lens prefers `DIGEST_PATH` when provided, else `RESEARCH_PATH`
27. ⚠️ Modify the remaining design-critic lens agents (`.claude/agents/qrspi-design-critic-*.md`, the other three lenses) — apply the same optional-`DIGEST_PATH` input contract as step 26, one file per lens, identical wording.
    - **Current:** each lens always Reads `RESEARCH_PATH`
    - **After:** each lens prefers `DIGEST_PATH` when provided, else `RESEARCH_PATH`
    - Note: this is one action repeated across the sibling lens files; treat each file as its own atomic edit during implementation.

### Verify Slice 4

28. **Checkpoint:** `python3 scripts/run_tests.py research_digest`
    - [ ] All `qrspi_research_digest_test.py` cases pass (determinism, evidence-fence stripping with all headers/prose retained, digest strictly shorter than input, fail-closed on empty input / empty result)
    - [ ] Sanity: run the digest against the ticket's own real `.qrspi/<id>/research.md` and confirm it produces a non-empty, shorter output (guards finding #1 — the lever must work on a REAL research.md, not just a synthetic fixture)
29. **Checkpoint:** Manual end-to-end with `digest.enabled` ON.
    - [ ] Digest file generated once before fan-out; all lenses receive `DIGEST_PATH`
    - [ ] Empty/missing digest aborts the phase fail-closed (no lens fan-out)
30. **Checkpoint:** Manual end-to-end with all levers OFF (default).
    - [ ] Lenses read full `RESEARCH_PATH`; no digest produced; behavior unchanged
31. **Checkpoint:** Manual single spawn with `lensModel` set.
    - [ ] The `agent()` `model` option is observed on the spawn (Risk Register: unverified harness seam — record the observation but do NOT block the ticket if the harness ignores it; digest is the primary lever)
32. **Checkpoint:** Manual end-to-end with `gateBehindEdge.enabled` ON vs OFF.
    - [ ] ON: panel skipped when edge critics pass
    - [ ] OFF (default): panel always runs

---

## Slice 5: Teeth eval — flawed-design fixture + golden + contract-style assertion

### Setup

33. ✨ Create `evals/fixtures/design_dropped_criterion_broken.md` — a deliberately-flawed design fixture: a design that states N acceptance criteria in its scope/Desired-End-State but silently drops one (the injected flaw) from its Delta/Decisions, so a faithful completeness lens must flag the missing criterion (ref: Decision 4 Option B).
34. ✨ Create `evals/golden/design_dropped_criterion_broken.json` — golden expectation for the fixture: the JSON record of the dropped criterion's identifier/label and the expectation that the lens contract surfaces it (e.g. `{"droppedCriterion": "<id>", "mustSurface": true}`). (Resolves the structure Unverified Assumption on golden extension by fixing it to `.json`.)

### Core Logic

35. ✨ Create `scripts/qrspi_teeth_test.py` — contract-style `unittest` (Decision 4 Option B): load the fixture (step 33) and golden (step 34); deterministically assert the lens prompt/agent contract would surface the injected flaw. Concretely (resolving the structure Unverified Assumption on the teeth mechanism): parse the fixture to extract the set of stated acceptance criteria and the set covered in the Delta/Decisions; assert exactly the golden's `droppedCriterion` is present in (stated − covered), i.e. the flaw is detectable by the same criterion-coverage check the completeness lens contract is asked to perform. This is a deterministic structural check over the fixture, not a live LLM call.
36. ⚠️ Modify `scripts/qrspi_teeth_test.py` — add the negative/teeth-of-the-teeth case: a helper that "repairs" the fixture in memory (re-adds the dropped criterion to the covered set) and asserts the detection then finds NO dropped criterion — so the test fails if the injected flaw is removed (proves the test has teeth, per structure Verification).
    - **Current:** asserts the flaw is detected on the broken fixture (step 35)
    - **After:** also asserts a repaired fixture yields no detection (the test would fail if the flaw were absent)

### Verify Slice 5

37. **Checkpoint:** `python3 scripts/run_tests.py teeth`
    - [ ] `qrspi_teeth_test.py` passes
    - [ ] It is picked up by the aggregating runner (appears in `python3 scripts/run_tests.py --list`)
38. **Checkpoint:** Confirm the test actually has teeth.
    - [ ] The repaired-fixture case (step 36) demonstrates the assertion would fail if the injected flaw were removed

> **Scope of this teeth test — named gap (not real critic-teeth):** Steps 35–36 are a
> **deterministic structural check over the *fixture*, not an exercise of any lens.** They
> assert the golden's `droppedCriterion` is present in `(stated − covered)` of the fixture —
> i.e. they verify the fixture is *well-formed* (it really does carry a detectable
> dropped-criterion flaw, and the "teeth-of-the-teeth" repair case proves that detection is
> load-bearing). They do **not** run, mock, or otherwise exercise the completeness lens (or any
> lens), so they do **not** verify AC-TEETH's stated intent that "a flawed design must make
> *each lens* fail." That live-critic teeth assertion is **explicitly out of scope** here,
> because `evals/run_eval.py` is a non-functional placeholder (Decision 4 Option B; design OQ1)
> — Option B is an acknowledged *weaker-teeth* tradeoff that runs in the existing CI gate
> today. **Do not mistake this structural check for real critic-teeth coverage.** True
> behavioral teeth on the LLM critic (Decision 4 Option A) require reviving the eval runner and
> are deferred to follow-up work; the fixture + golden created here are the durable substrate
> that a revived runner would consume.

---

## Final full-suite gate

39. **Checkpoint:** `python3 scripts/run_tests.py`
    - [ ] The entire `scripts/*_test.py` suite passes (metrics, append, critics_config, research_digest, teeth, plus all pre-existing tests) — the CI regression gate is green
40. **Checkpoint:** `python3 scripts/run_tests.py --list`
    - [ ] All five new `_test.py` modules are enumerated by the aggregating runner
41. **Checkpoint:** Re-confirm the disabled-critic path is byte-for-byte unchanged.
    - [ ] A critics-DISABLED design run produces no ledger, no digest, an unchanged result object, and identical lens inputs to pre-RUS-77 (the `if (criticConfig)` guard and all default-OFF gates verified)

---

## Rollback Notes

- **Step 8 (.gitignore):** Nothing to roll back — no `.gitignore` edit is made (the existing `.worktrees/` rule already covers the ledger; review-confirmed redundant). Any ledger files already written are untracked artifacts under `.worktrees/<id>/.qrspi/<id>/`; delete them manually (`rm .worktrees/<id>/.qrspi/<id>/critic-metrics.jsonl`). No history impact.
- **Steps 4–5 (metrics ledger, destructive-adjacent append):** The appender only ever appends; it never deletes. To roll back a bad ledger, delete the per-ticket `critic-metrics.jsonl` file — it is regenerated on the next critics-enabled run. No DB/migration.
- **Steps 9–12, 22–25 (qrspi-batch.js wiring):** Reversible via `gt`/revert of the JS edits. Because every new call is gated behind `if (criticConfig)` and the cost levers are default-OFF, reverting them cannot affect a disabled-critic run; no data migration is needed.
- **Steps 14, 16, 17 (config defaults + mirror + example):** Reversible — the new keys default OFF/absent, so removing them restores prior behavior with no config migration. Keep step 14 (Python) and step 16 (JS mirror) reverted together to preserve lockstep.
- **No DB migrations, middleware, or other destructive operations** — this is a CLI/orchestrator codebase (ref: design.md "No DB / middleware changes").
