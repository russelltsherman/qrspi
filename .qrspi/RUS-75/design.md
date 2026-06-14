# Design — Wire the RUS-58 per-slice edge critic into the doImplementation slice loop

**Ticket:** RUS-75
**Research basis:** research.md @ 2026-06-14T00:00:00Z
**Generated:** 2026-06-14T00:00:00Z
**Status:** draft

## Current State

The per-slice edge critic helper `runSliceCritic(t, r, wd, sliceN, dec, planSlice, structureSlice, maxRounds)` is defined at `qrspi-batch.js:1721` with its full produce→critique→revise→cap loop, complete logging, and revise-amend wiring — but it is **never called**; it is dead code (ref: Q4, Discovered Patterns). The diff-scope reducer `qrspi_slice_critic.py decide(setup, idx)` is a pure, tested stdlib reducer returning `{run, skipReason, diffBase, diffHead}`, and it too is never invoked from `doImplementation` (ref: Q1, Q10).

The slice loop is `for (const s of setup.slices)` at `qrspi-batch.js:1848-1887`; per iteration it only implements then commits, parenting slice N on `${id}/plan` (N=1) or `${id}/slice-${n-1}` (N>1) inline in the commit-worker prompt (ref: Q9). The only cross-iteration JS state is `let previousNotes` (ref: Q9). `alreadyCommitted` slices are `continue`-skipped at :1849 before any post-commit critic could run (ref: Q10). Each slice's `planSlice`/`structureSlice` rubric strings are already in memory on the loop var `s` (`s.planSlice`, `s.structureSlice`), produced once by the impl-setup worker — no disk read is needed at the call site (ref: Q2).

Config is read once via `const implCriticCfg = await readImplementationCriticConfig(wd, t.id)` at :1810, resolving to the four-field shape `{enabled, maxRounds, coherence:{enabled, maxRounds}}` with disabled defaults (ref: Q7). Today only `implCriticCfg.coherence.*` is consumed; the top-level `implCriticCfg.enabled` / `.maxRounds` are resolved but unused — they are the gate this ticket wires (ref: Q7). The coherence pass (gated by `implCriticCfg.coherence.enabled`) runs once before the loop and establishes the integration template: gate → fail-closed input guard → run helper → `if (!coh.ok) return skip(...)` → carry `residualFindings` in memory (ref: Q8). `skip(t, decision, note)` returns `{ticketId, action, summary}`, stops the ticket without unwinding committed slices, and is the established `ok:false` mapping everywhere in `doImplementation` (ref: Q12).

The finalize worker (:1901-1911) splices only `pr-summary.md` into the slice-1 commit message via `qrspi_pr_body.py --ticket … --slice 1`, then runs one `gt submit --publish --stack` (ref: Q13). Neither coherence nor per-slice findings are spliced today — `coherenceFindings` is carried in memory but never reaches a PR body, and `criticBodyStep` is only ever called with `'design'`/`'plan'`, never `'slice'`, despite `qrspi_critic_body.py` supporting `--phase slice --slice N` (ref: Q6, Q13, Inconsistencies). `gt submit` seeds PR bodies from commit messages at creation only, so any findings must be amended in before submit (ref: Q6, Q13). `runSliceCritic` and the loop already emit `log()` lines for every critic terminal state and per-slice commit (ref: Q15).

> **Note on stale inputs:** the ticket/questions name `qrspi_critics_config.py` and a two-field `{enabled, maxRounds}` shape. That script does not exist; the real reader is `qrspi_config.py` via `readImplementationCriticConfig`, and the resolved shape is four-field (ref: Q7, Inconsistencies). The ticket's line `1614` and param `n` for `runSliceCritic` are also stale — actual is line `1721`, param `sliceN` (ref: Q4, Inconsistencies). This design uses the verified facts.

## Desired End State

- **AC1** — After each slice's commit succeeds, when `implCriticCfg.enabled`, the call site invokes `qrspi_slice_critic.py decide(setup, s.n)` via a worker, parsing `{run, skipReason, diffBase, diffHead}` into `dec`. The projected `setup` passed in carries `{id: t.id, slices: setup.slices}` (only `id` + per-slice `alreadyCommitted` are load-bearing) and `s.n` (1-based) as `--slice-index` (ref: Q1, Q5). When `dec.run` is false (`single-slice` or `alreadyCommitted`), the critic is skipped for that slice — the slice still ships; this is a critic-skip, never a ticket `skip()` (ref: Q10).
- **AC2** — When `dec.run`, the call site invokes `runSliceCritic(t, r, wd, s.n, dec, s.planSlice, s.structureSlice, implCriticCfg.maxRounds)` (ref: Q2, Q4).
- **AC3** — A `runSliceCritic` result with `ok:false` maps to `return skip(t, r.decision, \`Slice ${s.n} critic spawn failed; stopped without shipping.\`)` — no silent ship (ref: Q4, Q12).
- **AC4** — Each slice's `residualFindings` are spliced into THAT slice's commit message via `qrspi_critic_body.py --phase slice --slice N` in the finalize step, amended lowest-N-first BEFORE the single `gt submit --stack` (ref: Q6, Q13). Per-slice findings target slice-N; coherence findings (if enabled) target slice-1 — separate buckets, never conflated (ref: Q8, Discovered Patterns). The finalize splice **skips the amend entirely (caller-side) for any bucket whose findings array is empty or whitespace-only** — it does NOT invoke `qrspi_critic_body.py` for that slice at all. This is load-bearing, not cosmetic: although `qrspi_critic_body.py` renders an *empty* findings section as a message-level no-op (`render_findings_section` returns `''` and `compose_message` returns the message unchanged, scripts/qrspi_critic_body.py:124-154), `set_findings` (:197-213) still unconditionally runs `gt checkout` + `gt modify -m <unchanged message>`, and `gt modify` re-commits and restacks the upper slices regardless of whether the message content changed. Relying on the script's idempotency alone would therefore still incur a needless per-slice `gt modify`/restack; the caller must gate the call on a non-empty array (a real JSON array file is always passed; the empty case is the no-op).
- **AC4b** — The carried `coherenceFindings` (currently dead: the code comment at `qrspi-batch.js:1766-1767` claims they are "surfaced into the SLICE-1 PR body later" but the finalize worker splices ONLY `pr-summary.md` — verified by reading :1901-1911) are ALSO spliced into slice-1's commit message in the same finalize step, when non-empty, via `qrspi_critic_body.py --phase slice --slice 1` — and, like the per-slice buckets (AC4), the coherence amend is **skipped caller-side when `coherenceFindings` is empty**, so an enabled-coherence-but-no-residual-findings run incurs no slice-1 `gt modify`/restack. Ordering on slice-1: coherence-findings splice → any slice-1 per-slice-findings splice → the existing `pr-summary.md` splice, all before the single `gt submit --stack`. This makes good on the existing in-memory `coherenceFindings` carry — it surfaces an *already-produced* finding set (the coherence pass itself is unchanged) and is gated by the same `implCriticCfg.coherence.enabled` that produced it, so AC5's disabled-path invariant is preserved.
- **AC5** — When `implCriticCfg.enabled` is false, the path is byte-for-byte unchanged: the entire critic block is inside `if (implCriticCfg.enabled)`, so zero extra worker spawns and no per-slice findings splice occur (ref: Q7, Q8).
- **AC6** — The critic runs in-loop, after each slice's commit and before the next slice is built. Because the critic's revise branch amends slice N in place and `gt modify` auto-restacks N+1…M, and the loop builds N before N+1, slice N is fully settled before N+1's parent base (`${id}/slice-N`) is used — restack ordering stays correct (ref: Q3, Q9, Q11).
- **AC7** — Verified by a manual end-to-end batch run on a multi-slice ticket with `implCriticCfg.enabled: true`; the JS glue is not unit-testable in the non-importable workflow, and the pure parts are already unit-tested (ref: Q14).

## Delta

**Modified file:** `.claude/workflows/qrspi-batch.js` only. No new scripts; all Python reducers and the `runSliceCritic`/`skip`/`decide` helpers are reused as-is (ticket Constraints, ref: Discovered Patterns).

Concrete changes:

1. **New schema constant** (near `LOOP_DECISION_SCHEMA` :619) — `SLICE_DECIDE_SCHEMA` for the `decide()` envelope `{run:boolean, skipReason:string|null, diffBase:string|null, diffHead:string|null}`, so the worker round-trip is schema-validated (ref: Q5).
2. **New worker helper** `sliceCriticDecide(t, setup, n)` (modeled on `criticDecision` :1251) — pipes `JSON.stringify({id:t.id, slices:setup.slices})` on stdin to `python3 ${engineCmdFor(r,'scripts/qrspi_slice_critic.py')} --slice-index ${n}`, validates against `SLICE_DECIDE_SCHEMA`, post-checks `typeof out.run === 'boolean'`, returns `dec` or null (ref: Q5).
3. **In-loop critic block** inside `for (const s of setup.slices)`, placed AFTER the commit at :1885 and gated by `if (implCriticCfg.enabled)`: call `sliceCriticDecide`; if null → `return skip(...)`; if `!dec.run` → log a skip line and fall through (slice ships); else `runSliceCritic(...)`, map `ok:false → return skip(...)`, and accumulate `perSliceFindings[s.n] = sc.residualFindings`.
4. **New cross-iteration accumulator** `const perSliceFindings = {}` declared beside `let coherenceFindings` / `previousNotes`, keyed by slice number (ref: Q8, Q9).
5. **Finalize-worker splice extension** (:1901-1911) — before the `gt submit --stack`: (a) when `coherenceFindings` is non-empty, amend slice-1's commit via `qrspi_critic_body.py --phase slice --slice 1 --findings-file <staged coherence json>` (the coherence-findings splice — see AC4b); (b) for each slice N with non-empty `perSliceFindings[N]`, amend slice-N's commit via `qrspi_critic_body.py --phase slice --slice N --findings-file <staged json>`, amending lowest-N-first; (c) the existing slice-1 `pr-summary` amend; (d) submit (ref: Q6, Q13). All slice-1 amends (coherence, then any slice-1 per-slice findings, then pr-summary) land lowest-first so the single stack restack is settled once. **Skip-on-empty is caller-side and mandatory at each of (a)/(b):** the finalize worker only invokes `qrspi_critic_body.py` for a bucket whose findings array is non-empty after whitespace-stripping — an empty bucket is skipped without spawning the script, because `qrspi_critic_body.py`'s empty-findings handling is a *message*-level no-op only and its `set_findings` still runs `gt checkout` + `gt modify`, which restacks (see AC4). A real JSON array file is always staged for the buckets that ARE non-empty.
6. **New log line** for the `dec.run === false` critic-skip, mirroring the coherence "skipping" lines (ref: Q15).

## Pattern Decisions

### Decision 1: Critique placement — in-loop vs after-loop (AC6)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Critique each slice in-loop, immediately after its commit, before next slice builds | Parent base for N+1 is the already-critiqued/amended N; restack via `gt modify` is automatic and settled before N+1; mirrors the per-slice `diffBase` the reducer expects (ref: Q3, Q9, Q11) | `previousNotes` for N+1 reflects pre-amend notes — a known soft-staleness (ref: Q11) |
| B | Commit all slices, then critique in a second pass after the loop | Single clean separation of build vs critique; `previousNotes` fully settled | A mid-stack amend in the second pass restacks upward and the diff range must be recomputed against settled branches; diverges from the reducer's per-slice base assumption; more bespoke restack handling |

**Recommendation:** Option A
**Rationale:** The reducer's `diffBase` (`${id}/plan` for N=1, else `${id}/slice-(N-1)`) is computed per slice and exactly mirrors the loop's commit-time parent selection (ref: Q3, Q9). Critiquing in-loop keeps these in lockstep: slice N is settled (including any amend-restack of N+1…M) before N+1's parent base is consumed. The coherence pass is the one structural exception (it runs once, pre-loop, with no slice context) and does not change this (ref: Q8). The only cost is `previousNotes` soft-staleness, captured as a risk below.
**NEW PATTERN?** No — reuses the coherence gate→run→`ok:false→skip`→carry-findings template (ref: Q8) and the `ok:false → skip` invariant (ref: Q12, Discovered Patterns).

### Decision 2: How to obtain `dec` from the pure reducer (AC1)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Invoke `decide()` via a single-purpose worker (`sliceCriticDecide`) and parse its JSON envelope | Follows the pure-reducer + JS-glue split exactly (ref: Q5, Discovered Patterns); reuses the tested reducer; no logic duplication | One extra worker spawn per slice (only when `enabled`) |
| B | Replicate the run/skip/diff-base logic inline in JS | No worker spawn | Duplicates the tested reducer — explicitly flagged anti-pattern (ref: Q5); two copies of the base-selection rule drift apart |

**Recommendation:** Option A
**Rationale:** Every deterministic decision in this codebase lives in a tested `qrspi_*.py` reducer invoked through a worker; the JS never re-derives it (ref: Q5, Discovered Patterns). The extra spawn only occurs on the opt-in path, preserving AC5's byte-for-byte-unchanged disabled path.
**NEW PATTERN?** No — directly mirrors `criticDecision` (:1251) invoking `qrspi_critic_loop.py` (ref: Q5).

### Decision 3: Per-slice findings splice site (AC4)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Splice per-slice findings in the finalize worker, lowest-N-first, before the single `gt submit --stack` | Honors "PR bodies seeded at creation only" (ref: Q6); one stack submit; amend-lowest-first avoids restack churn (ref: Q13) | Finalize prompt grows a per-slice amend loop |
| B | Amend each slice's findings immediately in-loop right after its critique | Findings land next to where they're produced | Each in-loop amend restacks the as-yet-unbuilt upper slices repeatedly; fights the build order; more churn |

**Recommendation:** Option A
**Rationale:** All commit-message amends must precede the single stack `gt submit`, and amending a lower slice auto-restacks those above it — so amending lowest-N-first in finalize, once, minimizes churn (ref: Q13). This matches where `pr-summary.md` is already spliced (ref: Q13). Coherence findings (slice-1) and per-slice findings (slice-N) stay in separate buckets (ref: Q8).
**NEW PATTERN?** No — extends the existing finalize splice (`qrspi_pr_body.py --slice 1`) using the already-built-but-unwired `qrspi_critic_body.py --phase slice` path (ref: Q6, Inconsistencies).

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Disabled path regresses (extra spawn / behavior change), violating AC5 | med | high | Wrap the entire critic block (decide call, runSliceCritic, findings accumulation, finalize splice loop) in `if (implCriticCfg.enabled)`; verify the disabled e2e run produces an identical transcript (no critic/decide spawns) (ref: Q7, Q8) |
| `ok:false` falls through to submit — silent ship of an un-critiqued/failed-revise slice | low | high | Map every `runSliceCritic` `ok:false` AND a null `decide` result to `return skip(t, r.decision, …)`; this is the documented no-silent-ship invariant (ref: Q4, Q12) |
| `previousNotes` for slice N+1 reflects pre-amend code after a revise of slice N | med | low | Accept as known soft-staleness (ref: Q11); revise edits rarely change "notes for next session". If it proves material, re-derive notes post-amend in a follow-up — out of scope here |
| Findings spliced into the wrong PR body (per-slice findings landing on slice-1, or vice-versa) | low | med | Keep `perSliceFindings[N]` and `coherenceFindings` as distinct buckets; per-slice → `--phase slice --slice N`, coherence → slice-1; never merge (ref: Q6, Q8, Q13) |
| `decide`'s `setup` projection omits `id` (yielding `None/slice-N` branch names) | low | med | `id` is not on the worker `setup` object — the caller must inject `t.id` into the projected `{id, slices}` before piping to the reducer (ref: Q1) |
| Coherence-findings splice still unwired — wiring per-slice without it leaves a half-finished finalize | med | med | RESOLVED (reviewer call on OQ1): wire the coherence-findings splice in the same finalize step as the per-slice splice (AC4b, Delta item 5a). This surfaces the already-produced in-memory `coherenceFindings` (the coherence *pass* itself — RUS-58's scope — is untouched); it only completes the surfacing the dead `:1766-1767` comment already promised, in the very finalize worker this ticket is already editing. The disabled path stays byte-for-byte unchanged because the splice is gated by the same `coherence.enabled` that produced the findings (ref: Q13, Inconsistencies) |

## Open Questions

- OQ1: RESOLVED (reviewer, in design review) — YES, wire the slice-1 coherence-findings splice here too. The ticket's Out of Scope excludes the coherence *pass* (the critic that produces the findings, already shipped in RUS-58), NOT the *surfacing* of its already-produced findings; the surfacing is a finalize-worker change, exactly the area this ticket edits. Research confirmed `coherenceFindings` is carried in memory but never spliced — the `:1766-1767` comment's "surfaced into the SLICE-1 PR body later" is currently false. See AC4b and Delta item 5a for the wiring and the slice-1 ordering (coherence → slice-1 per-slice findings → pr-summary, all amended lowest-first before the single `gt submit --stack`).
- OQ2: Is the `previousNotes` pre-amend soft-staleness (Risk row 3) acceptable for the first landing, or must revise re-derive notes-for-next-session? Default assumption: acceptable, deferred.
- OQ3: RESOLVED (reviewer, in design review — "empty findings as no-op") — YES, an empty/whitespace-only bucket is an explicit **caller-side** no-op: the finalize worker skips the amend entirely (does not invoke `qrspi_critic_body.py`) for any empty `perSliceFindings[N]` or empty `coherenceFindings`, and passes a real JSON array file only for the buckets that ARE non-empty. Verified necessity (not merely relying on the script): `qrspi_critic_body.py`'s no-op is *message*-level only — `render_findings_section`/`compose_message` (scripts/qrspi_critic_body.py:124-154) leave the message unchanged for empty findings, but `set_findings` (:197-213) still runs `gt checkout` + `gt modify -m <unchanged message>` unconditionally, and `gt modify` re-commits and restacks the upper slices regardless. So deferring the skip to the script would still incur a needless per-slice `gt modify`/restack; the caller-side gate (now normative in AC4, AC4b, and Delta item 5) is what actually avoids that churn.
