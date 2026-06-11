# Design — Land excludes the tip slice on multi-slice stacks, producing half-landed stacks

**Ticket:** RUS-70
**Research basis:** research.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** draft

## Current State

The `land` action is the lone phase action with no deterministic, tested script wrapper — it is free-text prose executed by a LAND worker agent against raw `gt` shell, whereas every other phase action (`qrspi_resolve.py`, `qrspi_persist.py`, `qrspi_pr_body.py`, `qrspi_cleanup.py`, `qrspi_revise_amend.py`) is backed by a self-locating unit-tested script (ref: Q5). `doLand` in `qrspi-batch.js` does not check out any branch itself; it spawns the LAND worker and hands it a prompt telling it to follow the `## action: land` steps of the qrspi-work SKILL (ref: Q1).

The authoritative checkout instruction lives in `.claude/skills/qrspi-work/SKILL.md:449` and hard-codes `gt checkout <ticket-id>/slice-1` — the stack **bottom** — regardless of how many slices exist (ref: Q1, Q8). It then runs `gt submit --publish --stack --no-edit --no-interactive` to refresh remotes, followed by `gt merge --no-interactive` (explicitly not `--confirm`) (ref: Q3, Q6). The inline comment claims `gt merge` "merges bottom-up," but the repo's own Graphite reference does not document `gt merge` at all; the only documented directionality is "downstack = toward trunk, upstack = away from trunk" (ref: Q3). Because `gt merge` operates on the current branch and its downstack, starting from slice-1 lands slice-1 + plan + design but leaves the upstack slices 2..N OPEN — the core defect (ref: Q3, Inconsistencies). For a single-slice stack, slice-1 **is** the tip, so the same instruction lands the full stack correctly; the bug manifests only when N>1 (ref: Q8).

The stack tip is already computable: `pick_tip()` in `qrspi_resolve.py` returns `<ticket>/slice-<maxN>` via `slice_numbers()` in `qrspi_pr_state.py`, but it is consumed only for worktree reuse and is never placed in the resolver envelope nor passed to land (ref: Q2). The envelope assembled by `build_envelope()` exposes `ok`, `repoRoot`, `worktreeDir`, `existing`, `decision`, `commentTargets`, `reviewers`, `teamReviewers`, and `ticketContent` — neither the slice count nor the tip branch (ref: Q4). The land worker reconstructs `<ticket-id>/slice-1` from the ticket id alone, breaking the envelope-as-contract pattern that governs every other phase (ref: Q4, Discovered Patterns).

"Done" is self-reported by the LAND worker via its `newStatus` field; the workflow never independently confirms every slice PR reached MERGED before declaring Done (ref: Q7). The only MERGED verification in the repo is `is_stack_fully_merged(stack_merge_state(...))` from `qrspi_pr_state.py`, queried over real gh GraphQL nodes — but it is consumed only by `qrspi_cleanup.py` as a reap gate, not by the Done path (ref: Q7, Q14). When the tip is left open, `gt merge` of slice-1 exits 0, the worker self-reports Done, and cleanup independently returns `decision: "skip"`, logged as a benign informational line, not an error (ref: Q9, Q13). That `skip` verdict is overloaded: it covers both "nothing merged yet" and "partially landed, tip open," so a half-landed stack is indistinguishable from a not-yet-started one (ref: Q13, Inconsistencies). A separate known hazard is that a partially-landed stack can later trip the resolver into `entry_blocked "No design branch"` (tracked separately, out of scope) (ref: Q9, Inconsistencies).

There is no test that exercises `gt merge` landing every slice; the resolver's two land cases assert only that APPROVED review state yields `{action: "land"}`, never branch checkout, merge order, or MERGED outcome (ref: Q11). Reusable N=2 fixtures already exist: `["RUS-1/slice-1","RUS-1/slice-2"]` mapped to `_node(prNumber, state, merged)` GraphQL stubs, covering fully-merged, partial, and all-OPEN (ref: Q12).

## Desired End State

**AC1 — all N slice PRs merged in one land, none left open.** The land step merges the entire stack through its actual tip in a single pass. After land, `is_stack_fully_merged(stack_merge_state(...))` over the stack's branches returns true; any OPEN slice fails the land rather than silently passing.

**AC2 — land merges every slice, slice-by-slice bottom-up, not a single hard-coded lower slice.** The land step iterates the slices in ascending order (k = 1..maxN, derived from the computed `slice_numbers`/`pick_tip` metadata on the envelope), running `gt checkout <id>/slice-<k>` then `gt merge --no-interactive` per slice, so the hard-coded single `slice-1` merge is replaced by an explicit bottom-up loop that lands the full stack through its actual tip (RQ1). The bottom-up order and the `gt merge --no-interactive` invocation are preserved (constraint).

**AC3 — multi-slice land verified end-to-end without manual intervention.** A post-merge verification queries per-PR state via the existing `qrspi_pr_state.py` gather and confirms every slice PR reached MERGED before the land is reported Done. A genuinely half-landed outcome surfaces as a distinct failure (not a benign `skip`), and the Done projection is gated on the MERGED truth rather than the worker's self-report.

## Delta

- **Modify** `.claude/skills/qrspi-work/SKILL.md` (`## action: land`, ~lines 446-452): replace the single hard-coded `gt checkout <ticket-id>/slice-1` + one `gt merge` with an explicit **slice-by-slice bottom-up loop** (RQ1) — for k = 1..maxN, `gt checkout <id>/slice-<k>` then `gt merge --no-interactive` — keeping `gt submit --publish --stack --no-edit --no-interactive` as the pre-land remote refresh, and correct the misleading "merges bottom-up" comment to describe the explicit per-slice ascending loop. Keep the `<id>/design` fallback (single merge) for plan-only features with no slices.
- **New tested helper** `scripts/qrspi_land_verify.py` (self-locating, like its siblings): given a ticket id, gathers per-branch PR state via `qrspi_pr_state.py` and returns a deterministic verdict — `landed` only when `is_stack_fully_merged` is true, else a distinct `incomplete` with the OPEN branches named. Stdlib-only `_test.py` sibling reuses the existing `["RUS-1/slice-1","RUS-1/slice-2"]` + `_node` fixtures.
- **Expose tip/slice metadata on the envelope root** (RQ3) — extend `build_envelope()` (`qrspi_resolve.py`) to carry the computed tip branch and slice count as **root-level** fields (additive, alongside `repoRoot`/`worktreeDir`/`existing`/`decision`), **not** nested inside the `decision` dict, so the land worker receives the slice list from the envelope instead of reconstructing branch names from the ticket id (restores the envelope-as-contract pattern). `decision()` in `qrspi_resolve_state.py` is unchanged.
- **Modify** `doLand` (`qrspi-batch.js:807-812`): after `fin.ok` and before reporting Done, invoke `qrspi_land_verify.py`; on `incomplete`, **stop the land with `ok:false`** and defer to the next batch pass (RQ2) — do **not** auto-retry the merge in the same run — rather than projecting Done. Distinguish a half-landed `skip` from a not-started `skip` in the logs.
- **New tests:** a land-completion case asserting all N slice PRs reach MERGED (reusing N=2 fixtures), and a negative case where slice-2 OPEN yields `incomplete`.

## Pattern Decisions

### Decision 1: Where does the slice list / merge anchor come from?

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Compute the slice list + tip in the resolver, thread it through the **envelope root** to the worker (reuse `pick_tip`/`slice_numbers`) | Restores envelope-as-contract; worker stops reconstructing branch names; logic already exists and is tested | Touches `build_envelope` and its tests; more surface |
| B | Have the SKILL prose tell the worker to derive the slices locally (`gt log`/`slice_numbers` against branches) | Smallest change; no envelope schema change | Re-introduces prose-derived branch names — the exact anti-pattern that caused the bug (ref: Q4, Discovered Patterns) |

**Recommendation:** Option A, with the metadata placed on the **envelope root** (RQ3) — not nested in `decision` — so `decision()` stays focused on the action verdict and the additive field matches the root-level fields the worker already reads.
**Rationale:** The envelope is the deterministic contract for every other phase, and land's reconstruction of `<ticket-id>/slice-1` in prose is explicitly flagged as the pattern break behind this defect (ref: Q4, Discovered Patterns). `pick_tip()`/`slice_numbers()` already compute the slice list and `<ticket>/slice-<maxN>` and are tested (ref: Q2), so this reuses existing building blocks rather than adding new logic. The worker then iterates the slice list bottom-up (RQ1) instead of merging once from a single anchor.
**NEW PATTERN?** No — reuses `pick_tip`/`slice_numbers` and the existing root-level envelope contract.

### Decision 2: How is land completion verified?

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | New `qrspi_land_verify.py` reusing `stack_merge_state`/`is_stack_fully_merged`, called in `doLand` before Done | Matches the deterministic-script-per-action pattern; MERGED data already queryable (ref: Q14); independently testable | One more script + test to maintain |
| B | Reuse `qrspi_cleanup.py`'s verdict — treat its `skip` as the land-failure signal | No new script; cleanup already computes MERGED state | `skip` is overloaded (not-started vs half-landed) (ref: Q13); conflates reap gating with land success; cleanup runs after Done is set |

**Recommendation:** Option A
**Rationale:** Land is the only phase action lacking a tested script wrapper, which is the structural reason the defect went unguarded (ref: Q5, Discovered Patterns). The MERGED gather already exists in `qrspi_pr_state.py` with `prefer="merged"` (ref: Q14), so the verifier reuses it. Separating land-success verification from cleanup's reap gate resolves the overloaded-`skip` ambiguity (ref: Q13).
**NEW PATTERN?** No — a new script, but it follows the established self-locating tested-helper convention.

### Decision 3: What is the Done gate?

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Gate Done on `qrspi_land_verify.py` returning `landed` (every PR MERGED) | Done reflects MERGED truth; eliminates worker-self-report vs cleanup contradiction (ref: Q7, Inconsistencies) | On `incomplete`, land stops with `ok:false` and defers to the next batch pass (RQ2) — no in-pass auto-retry |
| B | Keep worker `newStatus` self-report, add verification only as a warning log | Minimal behavior change | Preserves the silent half-landed pass (ref: Q13); fails AC3 |

**Recommendation:** Option A
**Rationale:** Done currently trusts the worker's word while the only MERGED check gates only reaping, letting a partial stack report Done and `skip` simultaneously (ref: Q7, Inconsistencies). Gating Done on the verifier makes "land succeeded" mean "whole feature on trunk," exactly AC3.
**NEW PATTERN?** No — wires an existing MERGED verdict into the Done path.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `gt merge`'s exact downstack branch-consumption is undocumented in-repo (ref: Q3, Q10) | high | high | Resolved by RQ1 — land merges **slice-by-slice bottom-up** (one `gt checkout`/`gt merge` per slice) so it never depends on a single `gt merge` consuming the full downstack; still gate on `qrspi_land_verify.py` MERGED check (Decision 2) and verify with the live N>1 end-to-end run (AC3) |
| `pick_tip` assumes max-N is the true tip; a non-linear or non-contiguous stack could mis-anchor (ref: Q2, Q9) | low | high | Reuse the existing tested `slice_numbers`/`pick_tip`; add a verify step that names OPEN branches so a mis-anchor is caught, not silently landed |
| Re-running land on an already-partially-landed stack may not cleanly re-attempt only the open tip (resolver hazard, ref: Q9) | med | med | Out of scope per ticket. Per RQ2, an `incomplete` land stops with `ok:false` and defers to the next batch pass (no in-pass auto-retry); the verifier's explicit `incomplete` verdict surfaces the state instead of a silent Done; document the leftover for the separate resolver ticket |
| Squaring up local state via `gt submit --stack` overwrites an approved remote head | low | high | Preserve `--no-edit` and avoid any `--force`; force ops stay quarantined to cleanup (ref: Q6) — constraint already honored |
| New root-level envelope field breaks existing resolver tests/consumers (ref: Q4) | med | low | Additive root-level field only (RQ3); `decision()` is untouched; update `qrspi_resolve_test.py`/`qrspi_resolve_state_test.py` fixtures alongside |

## Resolved Questions

The three questions below were raised during review and answered by the reviewer; their answers are now integrated into the design above (AC2, Delta, and Pattern Decisions 1–3).

- **RQ1 (was OQ1) — `gt merge` directionality: land iterates slice-by-slice, bottom-up.** Rather than relying on a single `gt merge` from the tip consuming the whole downstack (undocumented in-repo, ref: Q3), the land step merges **slice-by-slice bottom-up** — `gt checkout <id>/slice-<k>` then `gt merge --no-interactive` for k = 1..maxN in ascending order (changes restack/merge upward). This makes the merge order explicit and removes the dependency on undocumented `gt merge` downstack behavior; the per-slice loop lands every slice deterministically. **Decision: slice-by-slice bottom-up** (reviewer answer).
- **RQ2 (was OQ2) — incomplete land: stop, do not auto-retry.** On a verified-`incomplete` land, `doLand` **stops with `ok:false`** and defers to the next batch pass rather than auto-retrying the merge within the same run. This keeps land idempotent and avoids compounding the out-of-scope resolver re-trigger hazard inside one pass; the next pass re-evaluates from a clean gather. **Decision: stop (`ok:false`), no in-pass auto-retry** (reviewer answer).
- **RQ3 (was OQ3) — tip/slice metadata lives on the envelope root.** The computed tip branch (and slice count) is exposed on the **envelope root** returned by `build_envelope()` (alongside `repoRoot`, `worktreeDir`, `existing`, `decision`, …), **not** nested inside the `decision` dict. This matches the additive, root-level fields the worker already consumes and keeps `decision` focused on the action verdict. **Decision: envelope root** (reviewer answer).
