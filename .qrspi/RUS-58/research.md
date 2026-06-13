# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-13T00:00:00Z
**Generated:** 2026-06-13T20:50:00Z
**Status:** draft

> Scope note: research is the Stage-3 (implementation) critics feature. The implementation
> phase today has **NO** edge-critic, **NO** slice-diff gathering, and **NO** whole-stack
> coherence pass. Critics exist only for `design` (multi-lens panel, RUS-56) and `plan`
> (single critic, RUS-55). The relevant facts are therefore (a) the existing critic machinery
> to reuse and (b) the seams in the implementation phase where new wiring would attach.

## Q1: At the planning→implementation seam, how are the slice's planned steps located and read so they can be handed to the per-slice edge critic as its rubric?

**Answer:** The implementation phase does NOT read plan files itself. The `impl-setup` worker (a typed agent) parses `structure.md` / `plan.md` / `worktree.md` from the worktree and returns, per slice, the three text blobs `structureSlice`, `planSlice`, `worktreeSession` (plus `n`, `goal`, `alreadyCommitted`) in the `IMPL_SETUP_SCHEMA` envelope. These blobs are already in memory in `doImplementation` and are passed into the `qrspi-implement` agent prompt as `STRUCTURE_SLICE` / `PLAN_SLICE` / `WORKTREE_SESSION`. A per-slice critic would reuse `s.planSlice` (and `s.structureSlice`) as the rubric anchor — no new file read needed; the steps are already structured per-slice. The canonical plan path, if a path is preferred over the blob, is `art(wd, t.id, 'plan.md')` = `${wd}/.qrspi/${id}/plan.md`.

**Evidence:**

```js
const setup = await agent(
  `You are the implementation setup worker for ${t.id}. ...
3. Parse them and return one entry per vertical slice the PLAN defines, in order. ...
Fields per entry: structureSlice (Types+Contracts+"Slice N"), planSlice ("Slice N"),
worktreeSession (session N), goal (one line), alreadyCommitted ...`,
  { label: `impl-setup:${t.id}`, phase: 'Implementation', schema: IMPL_SETUP_SCHEMA }
)
...
for (const s of setup.slices) {
  ...
  `STRUCTURE_SLICE =\n${s.structureSlice}\n\nPLAN_SLICE =\n${s.planSlice}\n\n...`
```

— `.claude/workflows/qrspi-batch.js:1449-1486`
`IMPL_SETUP_SCHEMA` (slices[] with n/goal/structureSlice/planSlice/worktreeSession/alreadyCommitted) — `.claude/workflows/qrspi-batch.js:413-436`

**Dependencies:** `doImplementation` (upstream) ← `impl-setup` agent ← `structure.md`/`plan.md`/`worktree.md` artifacts. The `qrspi-implement` agent consumes the blobs downstream.
**Implicit contracts:** EVERY planned slice is mandatory (`alreadyCommitted` is the SOLE legal skip, for resume — optionality/gating is NOT honored). A plan with N `## Slice` headings MUST yield N entries (the slice-count source — see Q10).

## Q2: How does the whole-stack coherence critic obtain the six upstream artifacts (ticket, questions, research, design, structure, plan) together for a single pass?

**Answer:** No existing component loads all six artifacts together — there is no coherence pass today. The six artifacts live at deterministic canonical paths under `${wd}/.qrspi/${id}/`, addressable via the `art(wd, id, name)` helper. Five are persisted phase outputs (`questions.md`, `research.md`, `design.md`, `structure.md`, `plan.md`); the ticket is staged separately as `/tmp/phase-stage/${id}/ticket.md` during Resolve and surfaced as `r.ticketContentPath` (the resolver emits the PATH, never the body, to avoid HTML-escaping the Linear `<issue>` tags through worker stdout). `scripts/qrspi_persist.py` only persists ONE artifact per call (`--artifact` is a single choice from `ARTIFACTS`); it does not bundle. A coherence pass would resolve the six paths in `doImplementation` (where `wd`/`r`/`t` are in scope, exactly as `doDesign` resolves its panel inputs at lines 1349-1360) and hand them to a critic agent that Reads each.

**Evidence:**

```js
const art = (wd, id, name) => `${wd}/.qrspi/${id}/${name}`
...
// in doImplementation: PR_SUMMARY/DESIGN/STRUCTURE already resolved this way:
DESIGN_PATH = ${art(wd, t.id, 'design.md')}
STRUCTURE_PATH = ${art(wd, t.id, 'structure.md')}
```

— helper `art` `.claude/workflows/qrspi-batch.js:593`; doImplementation path resolution `.claude/workflows/qrspi-batch.js:1505-1512`
`ARTIFACTS = ["questions","research","design","structure","plan","worktree"]` (single-artifact persist) — `scripts/qrspi_persist.py:52`
ticket staged path → `r.ticketContentPath` — `.claude/workflows/qrspi-batch.js:1219` and the resolve worker steps `:1247-1256`

**Dependencies:** `qrspi_persist.py` writes each canonical artifact; `qrspi_resolve.py` emits `ticketContentPath`. A coherence critic would depend on all five canonical files already existing + the staged ticket file.
**Implicit contracts:** Canonical paths are owned by the scripts (the `qrspi` token is never typed by a worker — Fix A). `worktree.md` exists too but the question's "six" excludes it.

## Q3: What is the contract (inputs and return envelope) of the existing foundation critic loop that the per-slice edge critic is said to reuse?

**Answer:** Two reusable layers. (1) The JS glue `runCriticLoop(name, id, criticConfig)` runs the produce→critique→revise loop entirely in the pre-persist staging window: it spawns ONE `qrspi-critic` agent per round against `UPSTREAM_PATH` (rubric anchor) and `ARTIFACT_PATH` (= `stg(id,name)`), and on non-pass spawns a reviser that REWRITES `stg(id,name)` in place. It returns `{ ok, residualFindings }` — `ok:true` on converge OR cap_reached; `ok:false` on a spawn failure. `criticConfig` consumes `upstreamPath` (required), `maxRounds` (default 2), and optional `rubric` (spliced into the critic prompt). (2) The `qrspi-critic` agent returns the `CRITIC_VERDICT_SCHEMA` verdict `{ pass: bool, findings: string[] }`. The converge/revise/cap decision is delegated to the tested pure module `scripts/qrspi_critic_loop.py::next_action(verdicts, round, max_rounds)` → `{ action: 'converged'|'revise'|'cap_reached', residual_findings: [] }` (invoked from JS via `criticDecision`).

**Evidence:**

```js
async function runCriticLoop(name, id, criticConfig) {
  const maxRounds = criticConfig.maxRounds ?? 2
  const upstreamPath = criticConfig.upstreamPath
  const artifactPath = stg(id, name)
  ...
  return { ok: true, residualFindings: decision.residual_findings } // cap_reached
```

— `.claude/workflows/qrspi-batch.js:653-717`
verdict schema `CRITIC_VERDICT_SCHEMA = { pass:bool, findings:string[] }` — `.claude/workflows/qrspi-batch.js:481-488`
pure decision `next_action` (converged/revise/cap_reached + residual_findings) — `scripts/qrspi_critic_loop.py:82-113`
`qrspi-critic` agent edge-contract + verdict — `.claude/agents/qrspi-critic.md:8-42`

**Dependencies:** `runCriticLoop` → `agent()` (critic + reviser spawns), `criticDecision` → `qrspi_critic_loop.py`. The reviser is "the same typed phase PRODUCER agent re-prompted with findings" — but here the reviser is spawned WITHOUT an `agentType` (generic agent), reading both paths.
**Implicit contracts:** The loop operates on the STAGED file (`stg(id,name)`), so persist remains the single success gate. A per-slice critic on committed code (not a staged file) breaks this assumption — the slice is already committed to a branch before any critic could run (see Q4/Q11). The reviser must keep `stg` non-empty.

## Q4: How is the implementation phase currently sequenced in `runPhase` so that a critic can be inserted after tests pass and before `gt submit`?

**Answer:** The implementation phase does NOT go through `runPhase`. `runPhase` (lines 1153-1207) is used only for the single-artifact phases (questions/research/design/structure/plan/worktree); its critic block runs on the staged artifact between produce and persist. The implementation phase is a bespoke function `doImplementation(t, r)` that: (1) runs `impl-setup`; (2) loops over slices — per slice spawns `qrspi-implement` (which runs/writes code and is expected to make tests pass), then a `slice commit` worker that stages every changed file and creates `${id}/slice-N` via Graphite; (3) after the loop spawns the `qrspi-pr` agent to write `pr-summary.md`; (4) `phase('Finalize')` then the impl finalize worker splices `pr-summary.md` and runs `gt submit --publish --stack`. A per-slice critic would insert INSIDE the slice loop — after `qrspi-implement` returns (tests pass) and BEFORE the slice commit, OR after the commit but before the final `gt submit`. There is no `runPhase`-style staging window here; the slice is committed, not staged.

**Evidence:**

```js
for (const s of setup.slices) {
  if (s.alreadyCommitted) { ...; continue }
  const impl = await agent( `TICKET_ID = ${t.id}\nSLICE_NUMBER = ${s.n}...`,
    { label: `implement:${t.id}#${s.n}`, phase: 'Implementation', agentType: 'qrspi-implement' })
  if (impl === null) { ... return skip(...) }
  const commit = await agent( `You are the slice commit worker ... create ${t.id}/slice-${s.n} ...`,
    { label: `commit:${t.id}#${s.n}`, ... schema: SLICE_COMMIT_SCHEMA })
  ...
}
// after loop: qrspi-pr writes pr-summary.md, then Finalize → gt submit --publish --stack
```

— slice loop `.claude/workflows/qrspi-batch.js:1464-1503`; pr-summary `:1505-1514`; Finalize/submit `:1516-1528`
`runPhase` critic block (for reference, design/plan only) — `.claude/workflows/qrspi-batch.js:1178-1196`

**Dependencies:** `doImplementation` → impl-setup → per-slice {implement, commit} → qrspi-pr → impl finalize. Submission is `gt submit --publish --stack --no-edit --no-interactive` at line 1523.
**Implicit contracts:** Tests passing is the `qrspi-implement` agent's own responsibility (the prompt is just the slice context — see `.claude/agents/qrspi-implement.md`, not read here but referenced). The orchestrator does not run tests itself; "after tests pass" maps to "after `qrspi-implement` returns non-null".

## Q5: What is the existing mechanism for surfacing critic findings into a PR body, and what API does it use?

**Answer:** Two cooperating pieces. (1) `criticBodyStep(id, phase, findings, wd)` (JS) builds a finalize-prompt FRAGMENT: it writes the findings as a JSON array to a token-free staged file `/tmp/phase-stage/${id}/critic-findings-${phase}.json` and instructs the finalize worker to run `python3 scripts/qrspi_critic_body.py --ticket ${id} --phase ${phase} --findings-file <file>` BEFORE `gt submit`. (2) `scripts/qrspi_critic_body.py` amends the phase commit MESSAGE to append a `## Residual critic findings` section, because Graphite seeds the PR body from the commit message AT CREATION ONLY. `criticBodyStep` is hard-wired to design/plan: `_PHASE_BRANCH = {"design","plan"}` in `qrspi_critic_body.py` and `phase ∈ {'design'|'plan'}` in the JS — it would need an implementation/slice branch path added. The doc note (CLAUDE.md) and `doImplementation` finalize also describe the post-hoc REST PATCH `gh api repos/<owner>/<repo>/pulls/<N> -X PATCH -F body=@<file>` as the lever for editing a body AFTER creation (preferred over `gh pr edit`, which aborts on the Projects-classic GraphQL bug).

**Evidence:**

```js
function criticBodyStep(id, phase, findings, wd) {
  if (!Array.isArray(findings) || findings.length === 0) return ''
  const stageFile = `/tmp/phase-stage/${id}/critic-findings-${phase}.json`
  return ` Then surface the edge-critic's residual findings ... write this EXACT JSON ... to
${stageFile} ... run ... qrspi_critic_body.py --ticket ${id} --phase ${phase} --findings-file ...`
}
```

— `.claude/workflows/qrspi-batch.js:1136-1140`
`_PHASE_BRANCH = {"design":"design","plan":"plan"}` (design/plan only) — `scripts/qrspi_critic_body.py:45`; `render_findings_section`/`compose_message` (the `## Residual critic findings` splice) — `scripts/qrspi_critic_body.py:106-136`
REST PATCH body lever — `.claude/workflows/qrspi-batch.js:1518` and `.claude/CLAUDE.md` codebase-conventions note

**Dependencies:** `criticBodyStep` ← `runCriticLoop`/`runCriticPanelLoop` residualFindings (cap_reached only) ← finalize worker → `qrspi_critic_body.py` → `gt modify -m`. For implementation, the slice PR body is composed by `scripts/qrspi_pr_body.py` (splices `pr-summary.md` into the slice-1 commit message).
**Implicit contracts:** Findings only surface on `cap_reached` (converged ⇒ empty ⇒ `criticBodyStep` returns `''`, finalize prompt byte-for-byte unchanged). Implementation has its own body mechanism (`qrspi_pr_body.py`); a slice-critic surfacing into a slice PR body would integrate there, not via `qrspi_critic_body.py` as-is.

## Q6: How is per-slice critic cardinality (single critic, no panel) currently expressed for other phases, and where is the panel-vs-single configuration read from?

**Answer:** Cardinality is dispatched in `runPhase` on `criticConfig.lenses?.length`: a non-empty `lenses` list routes to `runCriticPanelLoop` (the multi-lens design panel); its absence routes to the single-critic `runCriticLoop`. So "single critic, no panel" is simply a `criticConfig` WITHOUT a `lenses` field — exactly how the plan phase is wired (`planCritic = { upstreamPath, maxRounds: 2 }`, no lenses). Config is read by `readDesignCriticConfig()`, which runs `python3 scripts/qrspi_config.py --key critics` and parses via `parseCriticConfig` → `resolveDesignCritic` (config-value > JS-default). `qrspi_config.py` is single-top-level-key only, so the WHOLE `critics` object is round-tripped under `--key critics` and `parseCriticConfig` digs out `value.design`. There is NO `critics.implementation` reader today — a slice critic would add an analogous reader (or extend `resolveDesignCritic`).

**Evidence:**

```js
const cr = criticConfig.lenses?.length
  ? await runCriticPanelLoop(name, id, criticConfig)
  : await runCriticLoop(name, id, criticConfig)
```

— dispatch `.claude/workflows/qrspi-batch.js:1185-1187`
single-critic plan wiring `const planCritic = { upstreamPath: art(wd, t.id,'structure.md'), maxRounds: 2 }` — `.claude/workflows/qrspi-batch.js:1411`
config read path `readDesignCriticConfig` → `qrspi_config.py --key critics` — `.claude/workflows/qrspi-batch.js:1092-1106`; `parseCriticConfig` (digs `value.design`) — `:337-348`; `resolveDesignCritic` — `:363-391`

**Dependencies:** `runPhase` ← `criticConfig` shape ← `doDesign`/`doPlan`. Config: `parseCriticConfig` ← `parseConfigEnvelope`-sibling ← `qrspi_config.py` ← `.qrspi/config.json`.
**Implicit contracts:** `qrspi_config.py` reads ONE top-level key (no dot-path) — a `critics.implementation` block must be read by round-tripping the whole `critics` object, NOT `--key critics.implementation` (which returns the default empty). `select_value` returns the raw value (an object for `critics`), so the `value:<str|null>` docstring is inaccurate for object values (see Inconsistencies).

## Q7: Where does the revise path for an implementation slice live, so the edge critic's "revise = fix the slice" outcome can be wired to it?

**Answer:** Two distinct "revise" mechanisms. (1) The in-loop critic reviser inside `runCriticLoop` rewrites the STAGED artifact `stg(id,name)` in place — but implementation has no staged artifact (the slice is committed), so this does NOT apply as-is. (2) The post-submission `doRevise(t, r)` action handles a reviewer's CHANGES_REQUESTED on an already-submitted slice PR: it amends the slice commit IN PLACE via `scripts/qrspi_revise_amend.py --ticket <id> --branch <id>/slice-<N>`, which checks out the branch, stages every edit (excluding caches), amends with `gt modify -m <existing message>`, and VERIFIES the amend captured the changes (fails if nothing staged or tree left dirty). For implementation, `doRevise` already iterates "EVERY slice whose PR is CHANGES_REQUESTED, lowest slice number first (changes restack upward)". An edge-critic "fix the slice" outcome would reuse `qrspi_revise_amend.py` (amend a committed slice branch) rather than the staged-file rewrite, since the slice is committed by the time a critic could see its diff.

**Evidence:**

```python
def stage_and_amend(worktree, branch):
    rc, out, err = _run(["gt", "checkout", branch, "--no-interactive"], cwd=worktree)
    ...
    rc, out, err = _run(_ADD_CMD, cwd=worktree)   # git add -A excluding caches
    rc_staged, _, _ = _run(["git","diff","--cached","--quiet"], cwd=worktree)
    staged = rc_staged != 0
    ...
    rc, out, err = _run(["gt","modify","--no-interactive","-m", existing], cwd=worktree)
    ...
    ok, error = verify_amend(staged, dirty)
```

— `scripts/qrspi_revise_amend.py:192-245`; `verify_amend` gate `:116-147`
`doRevise` per-slice amend wiring (`qrspi_revise_amend.py --branch <id>/slice-<N>`) — `.claude/workflows/qrspi-batch.js:1628-1633`

**Dependencies:** `doRevise` → `qrspi_revise_amend.py` → `gt checkout`/`gt modify`. The slice-commit worker (`doImplementation`) is the original committer; the reviser amends that commit.
**Implicit contracts:** `qrspi_revise_amend.py` REQUIRES the branch to already exist (it checks out the branch). It refuses an empty amend (the RUS-53 silent-no-op fix). Per-slice amends restack upward automatically (`gt modify`). A bare `gt modify --no-interactive` without staging silently drops edits — always use this script.

## Q8: What happens in the implementation phase flow when tests pass but the per-slice edge critic fails after the maximum revise attempts — is submission blocked, and where is that terminal state handled?

**Answer:** No implementation critic exists, so there is no current terminal handling for it. The closest precedent is the existing critic loop's cap_reached: `runCriticLoop`/`runCriticPanelLoop` return `{ ok: true, residualFindings }` on cap_reached — i.e. cap_reached is NOT a blocker; the artifact is STILL finalized/submitted, and the residual findings are surfaced into the PR body (Q5). `next_action` returns `cap_reached` (not a failure) when the latest verdict did not pass at `round+1 >= max_rounds`. Submission is blocked ONLY when the loop returns `ok:false`, which happens solely on a spawn failure (critic or reviser agent returns null) — `runPhase` then logs "critic loop did not complete" and returns false, aborting the ticket. So in the existing pattern, a critic that fails after max rounds does NOT block submission; it ships with findings in the PR body for the human reviewer. A Stage-3 design must DECIDE whether a slice critic adopts this "ship-with-findings" semantics or a stricter "block submission" one — the codebase precedent is ship-with-findings.

**Evidence:**

```js
if (decision.action === 'cap_reached') {
  log(`... critic CAP-REACHED at round ${round + 1} — ${decision.residual_findings.length} residual finding(s) carried to PR body`)
  return { ok: true, residualFindings: decision.residual_findings }
}
```

— cap_reached returns ok:true — `.claude/workflows/qrspi-batch.js:688-690`
`next_action` cap branch `if int(round)+1 >= int(max_rounds): return {"action":"cap_reached", ...}` — `scripts/qrspi_critic_loop.py:110-111`
ok:false only on spawn miss; runPhase aborts ticket — `.claude/workflows/qrspi-batch.js:669-671, 1188-1191`

**Dependencies:** loop result ← `next_action` decision ← critic verdict. `runPhase` consumes `cr.ok`.
**Implicit contracts:** cap_reached = "best effort exhausted, ship anyway with disclosure". A failed spawn = "could not run the loop, abort the ticket". These are deliberately different (a missing critic must never silently pass an artifact — fail-closed). For implementation, there is no `runPhase` wrapper, so a slice-critic loop's `ok:false` would need explicit handling inside `doImplementation`'s slice loop (return `skip(...)` like the implement/commit failure paths at lines 1487-1500).

## Q9: When the coherence pass flags intent drift in an upstream artifact, what is the existing mechanism (if any) for triggering a targeted upstream revise from the implementation seam, and how is downstream work affected?

**Answer:** There is NO existing mechanism to trigger an upstream revise FROM the implementation seam. The only upstream-drift machinery is the PR-gated `reset` action in `scripts/qrspi_resolve_state.py`, and it is driven exclusively by a reviewer's formal `CHANGES_REQUESTED` on an upstream phase PR — never by an automated coherence finding. `resolve()` computes: if a NON-frontier phase carries `CHANGES_REQUESTED` (`phase_changes_requested`), it emits `reset` with `resetToPhase = lowest CR phase` and `discardPhases = everything above it`. The `doReset` worker then closes downstream PRs, deletes downstream branches (`gt delete --force --close`), removes stale downstream artifacts, and `git clean -fd .qrspi/<id>/` so the skip-if-exists resume sees them absent, returning the ticket to that phase. So "intent drift flagged in an upstream artifact" maps conceptually to a reset, but today only a human reviewer can initiate it; an automated coherence pass has no path to inject a CHANGES_REQUESTED or to call `reset` directly. Downstream effect of a reset: total discard of all stacked phases above the reset target.

**Evidence:**

```python
cr = [p for p in existing if phase_changes_requested(phases, p)]
if cr:
    k = min(cr, key=_order)
    above = [p for p in existing if _order(p) > _order(k)]
    if above:
        return decision("reset", resetToPhase=k, discardPhases=above, ...)
```

— `scripts/qrspi_resolve_state.py:190-197`
`doReset` (close PRs, delete branches, git clean downstream artifacts) — `.claude/workflows/qrspi-batch.js:1548-1562`

**Dependencies:** `resolve()` ← PR review state gather (`qrspi_pr_state.py`). `doReset` ← `gt delete`, `git clean`. There is no producer→resolver feedback channel for an automated finding.
**Implicit contracts:** Reset is reviewer-initiated and total (all downstream discarded). PHASES order is `["design","plan","implementation"]` — drift in design/plan/structure would discard implementation slices entirely. An automated coherence-driven upstream revise is a NET-NEW capability with no current hook; the design must specify how a coherence finding reaches `resolve`/`reset` (e.g. surface-as-finding-only vs. auto-request-changes).

## Q10: For a single-slice ticket, does the per-slice critic loop still execute, and how is the slice count derived to bound the N critic runs?

**Answer:** The slice count is `setup.slices.length`, produced by the `impl-setup` worker by parsing the plan's `## Slice` headings — "a plan with N `## Slice` headings MUST yield N entries". `doImplementation` iterates `for (const s of setup.slices)`, so a single-slice ticket yields exactly one iteration. A per-slice critic placed inside that loop would therefore run exactly once for a single-slice ticket (N critic runs = number of NON-`alreadyCommitted` slices). The slice count is also used to label commits as `Part ${s.n}/${setup.slices.length}`. There is no separate "skip critic if only one slice" branch today (no critic exists), so a single-slice ticket would still execute the loop once unless the design adds an explicit guard.

**Evidence:**

```js
const wd = setup.worktreeDir
let previousNotes = ''
for (const s of setup.slices) {
  if (s.alreadyCommitted) { log(`... slice ${s.n} already committed — skipping`); continue }
  ...
  // subject "${t.id} [I] ${s.n}/${setup.slices.length}: ${s.goal}"
```

— `.claude/workflows/qrspi-batch.js:1462-1502`; slice-count enumeration contract in impl-setup prompt `:1453`

**Dependencies:** `setup.slices` ← `impl-setup` agent ← `plan.md`/`structure.md`/`worktree.md`.
**Implicit contracts:** `alreadyCommitted` slices are skipped (resume) — so the critic-run count is bounded by NOT-already-committed slices, not the raw slice count. A resumed run with all-but-one slice committed would critique only the remaining slice.

## Q11: How is the slice diff computed and scoped (which commit range or branch comparison) so that the edge critic sees only that slice's code and not the whole stack?

**Answer:** No slice diff is computed anywhere today. The orchestrator never runs `git diff` for a slice. The slice's code is isolated only structurally: each slice is committed as its OWN branch `${id}/slice-N`, parented (via Graphite) on `${id}/plan` for slice 1 or `${id}/slice-(N-1)` for slice N>1. Therefore a slice's own diff is, by construction, the single commit on that branch — `git diff ${id}/slice-(N-1)..${id}/slice-N` (or `git show ${id}/slice-N` for the slice-1-vs-plan case `git diff ${id}/plan..${id}/slice-1`). The parent for slice N is already computed in JS as the Graphite parent string. A slice-critic would compute the diff against that parent branch. The slice-commit worker stages "EVERY changed/untracked file EXCEPT generated caches" — so the committed slice is the deliverable diff. `qrspi_revise_amend.py` already uses `git diff --cached`/`git status --porcelain` patterns that a diff-gatherer could mirror.

**Evidence:**

```js
const commit = await agent(
  `... create ${t.id}/slice-${s.n} with Graphite parented on
${s.n === 1 ? `${t.id}/plan` : `${t.id}/slice-${s.n - 1}`}. ...`,
  { label: `commit:${t.id}#${s.n}`, ... schema: SLICE_COMMIT_SCHEMA })
```

— parent computation `.claude/workflows/qrspi-batch.js:1492-1496`
git-diff/status idioms (reusable) — `scripts/qrspi_revise_amend.py:64-69, 210-242`

**Dependencies:** slice branch topology ← Graphite (`gt create` parenting). A diff-gatherer would depend on the slice branch + its parent branch both existing.
**Implicit contracts:** The slice's diff == its single branch commit relative to its parent. This holds ONLY after the commit worker runs (a critic placed BEFORE the commit would have to diff the working tree against the parent branch instead, e.g. `git diff ${parent}`). Caches (`__pycache__/`, `*.pyc`) are excluded from the deliverable and should be excluded from any critic diff too.

## Q12: How are existing critic-wiring unit tests structured to stub inputs (e.g., diff and steps), so the slice-critic and coherence-pass triggering tests can follow the same pattern?

**Answer:** All critic logic is unit-tested as stdlib-only, assert-based `_test.py` siblings with NO test runner and NO third-party deps, run via `python3 scripts/qrspi_*_test.py`. The pattern: import the PURE functions from the sibling module, define a `check(label, got, want)` helper that increments `total`/`failures`, and call it with in-memory inputs (no filesystem, no git, no agent). `qrspi_critic_loop_test.py` stubs verdicts as plain dicts (`{"pass": True, "findings": []}`) and asserts `next_action(...)` outputs. The key design principle (stated in `qrspi_critic_loop.py`'s docstring): "neither touches the filesystem, the agent runner, or git — so the whole decision is verifiable ... with zero dependency on `agent()` or the JS orchestrator." A slice-critic decision or coherence-trigger reducer should likewise be a pure Python function (its TRIGGERING/cardinality/diff-scope decision extracted from the JS glue), tested with stubbed verdict dicts and stubbed diff/steps strings — exactly mirroring `qrspi_critic_loop_test.py` (and `qrspi_critic_synthesize_test.py`, `qrspi_design_select_test.py`).

**Evidence:**

```python
def check(label, got, want):
    global failures, total
    total += 1
    if got == want: print("ok: %s" % label)
    else: failures += 1; print("FAIL: %s\n   got:  %r\n   want: %r" % (label, got, want))

check("passing verdict at round 0 ⇒ converged, no residual findings",
      next_action([{"pass": True, "findings": []}], round=0, max_rounds=2),
      {"action": "converged", "residual_findings": []})
```

— `scripts/qrspi_critic_loop_test.py:29-42`
purity contract — `scripts/qrspi_critic_loop.py:25-27`

**Dependencies:** test ← pure module (no agent/git/fs). Siblings: `qrspi_critic_loop_test.py`, `qrspi_critic_synthesize_test.py`, `qrspi_critic_body_test.py`, `qrspi_design_select_test.py`.
**Implicit contracts:** Testability REQUIRES the decision live in a pure Python function; untestable agent-spawn/git mechanics stay in the JS glue or in the script's subprocess-backed section (`# --- subprocess-backed mechanics (not unit-tested; manual e2e) ---`). The JS orchestration itself has no unit tests — it is verified by manual e2e (per CLAUDE.md / MEMORY).

## Q13: How is the implementation-phase eval score currently computed and reported, so a before/after comparison can be emitted?

**Answer:** It is NOT computed in any functional way. `scripts/run_eval.py` + the `evals/` harness is a documented NON-FUNCTIONAL placeholder (CLAUDE.md: "The `evals/` + `scripts/run_eval.py` harness is a non-functional placeholder — verify pure logic with the unit tests and orchestration changes with manual end-to-end runs"; project MEMORY echoes this, and notes the skill-creator run_eval returns bogus uniform-0/3 in this sandbox). `run_eval.py` loads a suite JSON, calls the Anthropic Messages API per case×trial via the `call_model` seam, and writes raw `results.json` (output/tokens/transcript) — there is NO scoring/grading step (it captures outputs, not pass/fail scores; assertions in cases are loaded but not evaluated). So there is no existing implementation-phase eval score to do a before/after comparison against. A "before/after" comparison would have to be built net-new or done via manual e2e per the documented practice.

**Evidence:**

```python
def run_suite(config: EvalConfig) -> dict:
    ...
    output = { "skill_hash": ..., "suite": ..., "results": all_results }  # raw outputs, no scores
    with open(output_path, "w") as f: json.dump(output, f, indent=2)
```

— `scripts/run_eval.py:201-289` (no grading); assertions loaded but unused `:53-57`
placeholder status — `.claude/CLAUDE.md` codebase-conventions; project MEMORY `eval-harness-placeholder.md`

**Dependencies:** `run_eval.py` → Anthropic SDK (`call_model`, local import). No coupling to the implementation phase at all.
**Implicit contracts:** Treat any eval score as non-authoritative. Verification of orchestration changes = manual end-to-end; verification of pure logic = the `_test.py` siblings. Do NOT rely on `run_eval.py` output for a real before/after score.

## Q14: Where are critic findings and revise outcomes logged or emitted during a batch run so the coherence-pass findings are observable to an operator?

**Answer:** Via the `log()` function (console output during the batch run) and the per-ticket result `summary` string folded back at finalize. `runCriticLoop`/`runCriticPanelLoop` emit `log()` lines per round: PASS/FAIL with finding count, CONVERGED, REVISE, and CAP-REACHED with residual-finding count. The finalize step then folds critic outcomes into the human-visible PR + result summary: `criticBodyStep` surfaces cap_reached residual findings into the PR BODY (the durable operator-visible artifact), and `doDesign`/`doPlan` append `[critic: N residual finding(s) in PR body]` (and for design, `[criticSummary]` / `[selectSummary]`) to `out.summary`. For a coherence pass, the same two channels exist: transient `log()` during the run and durable surfacing into the PR body (via the `qrspi_critic_body.py` / `qrspi_pr_body.py` commit-message mechanism) plus the result `summary`. There is no separate findings log file.

**Evidence:**

```js
log(`  ${id}: ${name} critic round ${round + 1}/${maxRounds} → ${passed ? 'PASS' : `FAIL (${findings.length} finding(s))`}`)
...
log(`  ${id}: ${name} critic CAP-REACHED at round ${round + 1} — ${decision.residual_findings.length} residual finding(s) carried to PR body`)
```

— `.claude/workflows/qrspi-batch.js:675, 689`
summary fold-in (design) — `.claude/workflows/qrspi-batch.js:1390-1392`; (plan) `:1437-1439`

**Dependencies:** `log()` (defined earlier in batch.js; transient stdout) and the result `summary` returned by each `do*` action. Durable channel = PR body via `qrspi_critic_body.py`.
**Implicit contracts:** Operator observability = run-time `log()` (ephemeral) + PR body (durable) + result summary (per-ticket roll-up). A coherence pass's findings, to be durably observable, must land in the PR body or the result summary, not only `log()`.

---

## Discovered Patterns

1. **Pure-decision-core + agent-glue split.** Every testable decision (critic converge/cap, lens synthesis, design winner selection, PR-state resolution, config selection) lives in a pure stdlib-only Python module with a `_test.py` sibling; the JS orchestrator holds only the untestable agent-spawn/git mechanics and delegates the decision via a worker that runs the script and returns its JSON. (`qrspi_critic_loop.py`, `qrspi_critic_synthesize.py`, `qrspi_design_select.py`, `qrspi_resolve_state.py`, `qrspi_config.py`.)
2. **Self-locating one-shot scripts.** All `qrspi_*.py` scripts derive the repo root from `__file__`/git-common-dir (never typed by the weak worker model) and own the `qrspi`-laden canonical paths; the worker types only short tokens (`--ticket`, `--artifact`, `--slice`, `--branch`). This is "Fix A" — the path-mangling root-cause fix.
3. **Staging window vs. committed branch.** Single-artifact phases (design/plan/etc.) critique a STAGED file (`stg(id,name)`) before the persist gate, so the reviser rewrites in place and persist is the single success gate. The implementation phase has NO staging window — slices are COMMITTED to Graphite branches — so a slice critic must operate on a committed diff and revise via `qrspi_revise_amend.py`, not via a staged-file rewrite. This is the central structural asymmetry the Stage-3 feature must bridge.
4. **Cap_reached = ship-with-disclosure, not block.** The established critic semantics finalize the artifact even when the critic never passes, surfacing residual findings into the PR body. Only a spawn failure aborts.
5. **Cardinality by config shape.** Panel-vs-single is dispatched purely on `criticConfig.lenses?.length` in `runPhase` — no enum, no flag. Single critic = config without `lenses`.
6. **PR body is seeded from the commit message at creation.** All durable PR-body content (summaries, residual findings) is amended into the branch commit message before `gt submit`, because Graphite seeds the body at creation only. Post-hoc correction is `gh api ... pulls/N -X PATCH -F body=@file` (NOT `gh pr edit`).
7. **Fail-closed everywhere.** Missing/garbled verdicts coerce to NOT-passed; absent config falls back to safe JS defaults; unreadable blockers count as OPEN; an empty amend is a hard stop.

## Inconsistencies

1. **`qrspi_config.py` value type docstring vs. actual behavior.** The module docstring and envelope comment type `value` as `<str|null>` (`scripts/qrspi_config.py:16-18`), and `parseConfigEnvelope` (JS) rejects a non-string `value` (`qrspi-batch.js:324`). But `select_value` returns `config.get(key)` verbatim, so `--key critics` returns a nested OBJECT, and `parseCriticConfig` (a SEPARATE lenient parser, `:337-348`) is required precisely because the object value would be rejected by the string-only `parseConfigEnvelope`. This is a known wrinkle (CLAUDE.md: "qrspi_config.py reads one top-level key (no dot-path); JS parseConfigEnvelope rejects non-string values") and means a `critics.implementation` block, like `critics.design`, must be read by round-tripping the whole `critics` object under `--key critics`, never `--key critics.implementation`.
2. **`qrspi_critic_body.py` is design/plan-only despite "edge-critic" generality.** `_PHASE_BRANCH = {"design","plan"}` (`:45`) and `--phase` choices are `sorted(_PHASE_BRANCH)` (`:202`), so the residual-findings-into-PR-body script cannot today target an implementation/slice branch. The `criticBodyStep` JS helper is likewise `phase ∈ {design,plan}`. A Stage-3 slice critic surfacing findings would need this script (or `qrspi_pr_body.py`) extended.
3. **Reviser agentType asymmetry.** `runCriticLoop`'s comment says the reviser is "the same typed phase PRODUCER agent re-prompted" (`:692-695`), but the actual reviser spawn passes NO `agentType` (a generic agent), while `runCriticPanelLoop` re-spawns the design producer. Minor doc/code drift; not load-bearing for Stage-3 but worth noting if the slice reviser is modeled on this.
4. **`runCriticLoop` defensive tail returns `ok:true` with empty findings on loop exhaustion** (`:712-716`), whereas `next_action` always returns an explicit `cap_reached` at the final round — so the tail is dead code today, but it silently treats exhaustion as a pass-equivalent (empty residual findings), a subtly weaker fail-closed than the cap_reached branch above it.
