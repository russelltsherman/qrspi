# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-14T00:00:00Z
**Generated:** 2026-06-14T00:00:00Z
**Status:** draft

> Scope note: all paths are under `REPO_ROOT = /workspaces/qrspi/.worktrees/RUS-75`.
> Line numbers are from the current HEAD of branch `RUS-75/...`.
> **Top-level fact:** `runSliceCritic()` (qrspi-batch.js:1721) and the pure reducer
> `scripts/qrspi_slice_critic.py` already EXIST, but `runSliceCritic` is **defined and
> never called** — the per-slice loop in `doImplementation` (qrspi-batch.js:1848-1887)
> has no critic invocation. This ticket wires the existing helper into the loop.

## Q1: After a slice's commit succeeds in the slice loop, what inputs does `qrspi_slice_critic.py decide(setup, n)` require, and what is the exact shape of the `setup` object the caller must assemble (fields, types, source of each)?

**Answer:** `decide(setup, slice_index)` is a pure stdlib reducer. `setup` is a dict with two
keys: `"id"` (str ticket id) and `"slices"` (list of dicts, each carrying at least
`{"alreadyCommitted": bool}`). `slice_index` is a **1-based** int. It returns
`{run, skipReason, diffBase, diffHead}`. The reducer reads only `setup["id"]`,
`setup["slices"]`, and `slices[idx-1]["alreadyCommitted"]` — it never touches goal/plan/
structure text. In the JS orchestrator the matching object is `setup` returned by the
impl-setup worker (qrspi-batch.js:1789-1796, schema `IMPL_SETUP_SCHEMA` at :479-502),
whose `slices[]` items carry `n, goal, structureSlice, planSlice, worktreeSession,
alreadyCommitted`. So `decide`'s `setup` is a SUBSET projection of that worker `setup`
(only `id` + per-slice `alreadyCommitted` are load-bearing). `id` is not on the worker
`setup` object; the caller has it as `t.id`.

**Evidence:**

```python
def decide(setup, slice_index):
    slices = setup.get("slices", []) if isinstance(setup, dict) else []
    ticket_id = setup.get("id") if isinstance(setup, dict) else None
    idx = int(slice_index)
```

— `scripts/qrspi_slice_critic.py:42-74`

```js
required: ['n', 'goal', 'structureSlice', 'planSlice', 'worktreeSession', 'alreadyCommitted'],
```

— `.claude/workflows/qrspi-batch.js:490` (IMPL_SETUP_SCHEMA slice item)

**Dependencies:** Upstream: the impl-setup worker (qrspi-batch.js:1789). Downstream: invoked
via stdin->stdout CLI (`printf '%s' '<json>' | python3 qrspi_slice_critic.py --slice-index N`,
:107-125). The pure `decide` has zero filesystem/git/agent coupling.
**Implicit contracts:** `setup["id"]` must be the ticket id (used to build branch names);
omitting it yields branch names like `None/slice-2`. `slice_index` is 1-based and the loop
variable `s.n` is the slice number — caller must pass `s.n`, not a 0-based loop index.
`alreadyCommitted` precedence is evaluated FIRST (before single-slice), per the docstring.

## Q2: How are `planSlice` and `structureSlice` (the per-slice rubric inputs passed to `runSliceCritic`) currently resolved or loaded within `doImplementation`, and from which artifact paths?

**Answer:** They are NOT loaded from disk inside `doImplementation`. The impl-setup worker
(qrspi-batch.js:1789-1796) parses `structure.md` and `plan.md` once and returns, per slice,
the inline strings `structureSlice` ("Types+Contracts+'Slice N'") and `planSlice`
("Slice N"). The loop then passes those strings straight into the implement agent prompt
(`s.structureSlice` at :1856, `s.planSlice` at :1859). They are already in memory as
`s.structureSlice` / `s.planSlice` for each slice `s`, so `runSliceCritic(... s.planSlice,
s.structureSlice ...)` would pass them with no extra read. `runSliceCritic` concatenates
them into its rubric (qrspi-batch.js:1726).

**Evidence:**

```js
3. Parse them and return one entry per vertical slice the PLAN defines... Fields per entry:
structureSlice (Types+Contracts+"Slice N"), planSlice ("Slice N"), worktreeSession (session N),
goal (one line), alreadyCommitted (...)
```

— `.claude/workflows/qrspi-batch.js:1793`

```js
const rubric = `PLAN_SLICE (the planned steps this slice must faithfully implement):\n${planSlice}\n\nSTRUCTURE_SLICE (the types/contracts/slice definition):\n${structureSlice}`
```

— `.claude/workflows/qrspi-batch.js:1726`

**Dependencies:** impl-setup worker → `setup.slices[].{planSlice,structureSlice}` → loop var
`s` → would feed `runSliceCritic`. Artifact source-of-truth paths (read by the worker, not
the JS): `art(wd, id, 'structure.md')` and `art(wd, id, 'plan.md')` where
`art = (wd,id,name) => ${wd}/.qrspi/${id}/${name}` (qrspi-batch.js:673).
**Implicit contracts:** The rubric strings are MANDATORY per planned slice — the worker is
told every `## Slice` heading yields an entry (no optional skips). Empty `planSlice`/
`structureSlice` would yield a degenerate rubric but `runSliceCritic` does not guard for it.

## Q3: How does `decide()` derive `diffBase`/`diffHead` for a slice (the Graphite diff-base computation), and what state must exist for that computation to be valid at the call site?

**Answer:** `diffHead` is always `"${id}/slice-${idx}"`. `diffBase` is `"${id}/plan"` for
slice 1, else `"${id}/slice-${idx-1}"`. So the diff range scopes to exactly this slice's
change against its Graphite parent. For the range to be valid at the call site, those
branches must already exist and be committed: slice N's commit must be done (the loop
commits at :1876-1884 before any critic would run), and the parent branch (`${id}/plan` for
slice 1, the prior slice branch otherwise) must exist. The loop already parents slice N on
`${id}/plan` (N=1) or `${id}/slice-${n-1}` (N>1) at commit time (:1877), matching `decide`'s
base exactly.

**Evidence:**

```python
    diff_head = "%s/slice-%d" % (ticket_id, idx)
    if idx == 1:
        diff_base = "%s/plan" % (ticket_id,)
    else:
        diff_base = "%s/slice-%d" % (ticket_id, idx - 1)
    return {"run": True, "skipReason": None, "diffBase": diff_base, "diffHead": diff_head}
```

— `scripts/qrspi_slice_critic.py:90-95`

```js
...create ${t.id}/slice-${s.n} with Graphite parented on ${s.n === 1 ? `${t.id}/plan` : `${t.id}/slice-${s.n - 1}`}...
```

— `.claude/workflows/qrspi-batch.js:1877`

**Dependencies:** `decide()` (pure) → branch-name strings consumed by `runSliceCritic`'s
`diffRange = ${dec.diffBase}..${dec.diffHead}` (qrspi-batch.js:1725) → the critic worker runs
`gt checkout ${branch}` then `git diff ${diffRange}` (:1731).
**Implicit contracts:** The critic must run AFTER the slice commit (so `${id}/slice-N` exists)
and after the prior slice committed (parent base exists). `decide`'s base mirrors the commit's
parent-selection logic at :1877 — these two must stay in sync (both encode the same
plan-for-slice-1 / prior-slice-otherwise rule).

## Q4: What is the full signature and return contract of `runSliceCritic()` — every parameter (`t, r, wd, n, dec, planSlice, structureSlice, maxRounds`) and the exact shape of its `{ok, residualFindings}` return?

**Answer:** Signature is `async function runSliceCritic(t, r, wd, sliceN, dec, planSlice,
structureSlice, maxRounds)` (qrspi-batch.js:1721 — note the questions file cited line 1614
and param `n`; the actual line is **1721** and the param is **`sliceN`**). Params: `t`
(ticket obj, uses `t.id`), `r` (resolver envelope, uses `engineCmdFor(r, ...)` for the
revise-amend path), `wd` (worktree dir, the worker cwd), `sliceN` (1-based slice number),
`dec` (the `decide()` result, uses `dec.diffBase`/`dec.diffHead`), `planSlice`/`structureSlice`
(rubric strings), `maxRounds` (cap; non-positive/non-int falls back to 2 at :1722). Return:
`{ok, residualFindings}` matching `runCriticLoop`'s shape — `ok:true` whenever the loop
completed (converged OR cap_reached), `ok:false` on any critic/revise/decision SPAWN failure;
`residualFindings` is `[]` on converge and the last decision's `residual_findings` on
cap_reached.

**Evidence:**

```js
async function runSliceCritic(t, r, wd, sliceN, dec, planSlice, structureSlice, maxRounds) {
  const rounds = Number.isInteger(maxRounds) && maxRounds > 0 ? maxRounds : 2
  const id = t.id
  const branch = `${id}/slice-${sliceN}`
  const diffRange = `${dec.diffBase}..${dec.diffHead}`
```

— `.claude/workflows/qrspi-batch.js:1721-1725`

```js
    if (decision.action === 'cap_reached') {
      ...
      return { ok: true, residualFindings: decision.residual_findings }
    }
```

— `.claude/workflows/qrspi-batch.js:1754-1756`

**Dependencies:** Calls `agent({agentType:'qrspi-critic', schema: CRITIC_VERDICT_SCHEMA})`
(:1729-1735), `criticDecision()` (:1745), and on revise the `qrspi_revise_amend.py` worker
(:1761-1772). Mirrors `runCoherenceCritic` (:1667) and `runCriticLoop` (:759) return contract.
**Implicit contracts:** Caller MUST map `ok:false` to `skip(t, r.decision, ...)` (no silent
ship — documented at :1719-1720) and carry `residualFindings` into THIS slice's PR body (not
slice-1; coherence findings go to slice-1, per-slice findings go to slice-N). `dec.run` must
be true before calling (caller is expected to gate on `decide()` first; `runSliceCritic`
itself does not re-check `dec.run`).

## Q5: How is a worker invoked from `doImplementation` to run a Python reducer like `decide()`, and what is the existing pattern for parsing its JSON envelope back into a JS object (`dec`)?

**Answer:** The JS sandbox cannot run python, so every python reducer is invoked via a
single-purpose worker agent: `await agent("...Run EXACTLY this one command verbatim... return
its JSON stdout verbatim", {label, phase, schema})`. The canonical pattern is `criticDecision`
(qrspi-batch.js:1251-1265): it pipes a JSON-serialized payload through `printf '%s' <json> |
python3 ${engineCmd('scripts/qrspi_*.py')} ...`, schema-validates the result, and post-checks
the parsed object (`if (!out || typeof out.action !== 'string') return null`). For
`qrspi_slice_critic.py`, `setup` is passed on stdin and `--slice-index N` as a flag (CLI at
:107-125). The JSON envelope is parsed by the harness against the supplied `schema`; the JS
then reads fields off the returned object. No new schema exists yet for the slice-critic
`decide` envelope (`{run, skipReason, diffBase, diffHead}`) — one would be added like
`LOOP_DECISION_SCHEMA` (:619-626).

**Evidence:**

```js
async function criticDecision(verdicts, round, maxRounds) {
  const out = await agent(
    `...Run EXACTLY this one command verbatim ...:
  printf '%s' ${JSON.stringify(JSON.stringify(verdicts))} | python3 ${engineCmd('scripts/qrspi_critic_loop.py')} --round ${round} --max-rounds ${maxRounds}
...`, { label: `critic-decision#${round}`, phase: 'Critic', schema: LOOP_DECISION_SCHEMA })
  if (!out || typeof out.action !== 'string') return null
```

— `.claude/workflows/qrspi-batch.js:1251-1262`

```python
#   printf '%s' '<json setup blob>' | python3 qrspi_slice_critic.py --slice-index N
```

— `scripts/qrspi_slice_critic.py:103`

**Dependencies:** `engineCmd(rel)` (:76) for runner-cwd workers; `engineCmdFor(r, rel)` (:105)
for worker-cwd. `agent()`, `log()`, `phase()` are framework-injected globals (no local def).
**Implicit contracts:** The worker prompt MUST say "return JSON verbatim, HARD STOP on
ok:false, do not retry/improvise". The JS MUST post-validate beyond the schema (criticDecision
checks `typeof out.action === 'string'` and coerces `residual_findings` to `[]`). Note: this
worker round-trip for `decide()` is one option; because `decide` is pure and trivial, the
wiring could alternatively replicate the run/skip/diff-base logic in JS — but that would
duplicate the tested reducer (anti-pattern flagged in Discovered Patterns).

## Q6: What is the exact output contract of `qrspi_critic_body.py --phase slice --slice N` (stdout shape, file it writes, the resolved `<ticket>/slice-N` path) that the finalize step consumes?

**Answer:** It amends the commit message of branch `${ticket}/slice-N` (resolved by
`phase_branch(ticket,'slice',N)` → `"%s/slice-%d"`, :77) to append a "## Residual critic
findings" section, then prints a single JSON envelope to stdout:
`{ok, repoRoot, ticket, phase, branch, worktreeDir, subject, bytes, error?}`. It reads findings
from a `--findings-file` (a JSON array of strings; relative paths resolve against the worktree).
Empty/no findings ⇒ success no-op (`ok:true`, `subject:None`, `bytes:0`, no amend). The amend
goes through `gt checkout <branch> --no-interactive` then `gt modify --no-interactive -m
<message>` (:200-211). `--slice N` is REQUIRED when `--phase slice` (CLI guard at :231-232 and
pure-helper guard at :69-77).

**Evidence:**

```python
    if phase == "slice":
        ... n = int(slice_index) ...
        return "%s/slice-%d" % (ticket, n)
```

— `scripts/qrspi_critic_body.py:69-77`

```python
    env = build_envelope(args.ticket, args.phase, branch, worktree, ok=ok, subject=subject,
                         bytes_=len(section.encode("utf-8")), error=error, repo_root=repo_root)
    json.dump(env, sys.stdout, indent=2)
```

— `scripts/qrspi_critic_body.py:278-281`

**Dependencies:** Uses `qrspi_paths.resolve_repo_root` (self-locating, :37). Mirrors the
`criticBodyStep()` JS fragment (qrspi-batch.js:1274-1277) that today wires design/plan findings
into the design/plan finalize prompts (`designBodyStep` :1563, `planBodyStep` :1636). The
`slice` phase exists in `criticBodyStep`'s callable surface but `criticBodyStep` currently
hard-passes `'design'`/`'plan'` only.
**Implicit contracts:** The amend must run BEFORE `gt submit` for that branch — `gt submit`
seeds the PR body from the commit message at CREATION only (qrspi-batch.js:1268-1273). After
submit, the PR body would not update. So per-slice findings must be spliced into slice-N's
commit message before the stack's `gt submit --stack` (or before that slice's own submit).
`gt modify` on slice N auto-restacks slices above it.

## Q7: How is `implCriticCfg` (`{enabled, maxRounds}`) currently derived from `qrspi_critics_config.py` and threaded into `doImplementation`, given the PR #288 restructuring referenced by the ticket?

**Answer:** **`scripts/qrspi_critics_config.py` does NOT exist** (searched `ls
scripts/qrspi_critics_config.py` → not found). The actual config reader is
`scripts/qrspi_config.py`, read via `readImplementationCriticConfig(wd, id)`
(qrspi-batch.js:1230-1245). That helper spawns a CONFIG worker running `python3
qrspi_config.py --key critics` (the WHOLE `critics` object — qrspi_config.py is
single-top-level-key only, so `--key critics.implementation` is forbidden), then digs
`value.implementation` via `parseImplementationCriticConfig(text)` (:424-435) and resolves it
through `resolveImplementationCritic(impl)` (:446-457) to the shape `{enabled, maxRounds,
coherence:{enabled, maxRounds}}` with DISABLED defaults (absent block ⇒ all false). In
`doImplementation`, `const implCriticCfg = await readImplementationCriticConfig(wd, t.id)` at
:1810 — currently only `implCriticCfg.coherence.enabled` / `.coherence.maxRounds` are consumed
(:1812, :1838). The top-level `implCriticCfg.enabled` / `.maxRounds` (the per-slice knobs) are
RESOLVED but NOT yet consumed anywhere — they are the gate this ticket wires.

**Evidence:**

```js
function resolveImplementationCritic(impl) {
  const cfg = impl && typeof impl === 'object' ? impl : {}
  const coh = cfg.coherence && typeof cfg.coherence === 'object' ? cfg.coherence : {}
  return {
    enabled: cfg.enabled === true,
    maxRounds: Number.isInteger(cfg.maxRounds) && cfg.maxRounds > 0 ? cfg.maxRounds : 2,
    coherence: { enabled: coh.enabled === true,
      maxRounds: Number.isInteger(coh.maxRounds) && coh.maxRounds > 0 ? coh.maxRounds : 2 } }
}
```

— `.claude/workflows/qrspi-batch.js:446-457`

```js
  const implCriticCfg = await readImplementationCriticConfig(wd, t.id)
```

— `.claude/workflows/qrspi-batch.js:1810`

**Dependencies:** `readImplementationCriticConfig` → CONFIG worker → `qrspi_config.py --key
critics` → `parseImplementationCriticConfig` → `resolveImplementationCritic`. Config source:
`.qrspi/config.json` (gitignored); example block at `.qrspi/config.example.json:25-31`
(`implementation: {enabled:false, maxRounds:2, coherence:{enabled:false, maxRounds:2}}`).
**Implicit contracts:** Opt-in: an absent/false block leaves the byte-for-byte-unchanged
no-critic path. The per-slice gate must read `implCriticCfg.enabled` and `implCriticCfg.maxRounds`
(already resolved at :1810) — no second config read is needed; `readImplementationCriticConfig`
is the single read. **The ticket's reference to `qrspi_critics_config.py` and a two-field
`{enabled, maxRounds}` shape is stale/inaccurate** — see Inconsistencies.

## Q8: How does the existing coherence pass (`implCriticCfg.coherence.enabled`) gate and structure its wiring, so the per-slice gate can mirror that integration pattern?

**Answer:** The coherence pass runs ONCE before the slice loop, gated by
`if (implCriticCfg.coherence.enabled)` (qrspi-batch.js:1812). Inside the gate: (T13) resolve the
six artifact paths inline via `art(wd,id,name)` + `r.ticketContentPath` (:1815-1822); (T14)
fail-closed guard — check `r.existing` flags for the five planning artifacts + `r.ticketContentPath`,
and `return skip(...)` if any missing (:1827-1834); (T15) `const coh = await runCoherenceCritic(t.id,
coherencePaths, implCriticCfg.coherence.maxRounds)` (:1838); (T16) `if (!coh.ok) return skip(...)`
(no silent ship, :1841-1843); then `coherenceFindings = coh.residualFindings` carried in memory
(:1844). The per-slice gate should mirror this: gate on `implCriticCfg.enabled`, call `decide()`
per slice, run `runSliceCritic`, map `ok:false → skip`, carry per-slice `residualFindings`.

**Evidence:**

```js
  const implCriticCfg = await readImplementationCriticConfig(wd, t.id)
  let coherenceFindings = []
  if (implCriticCfg.coherence.enabled) {
    ...
    const coh = await runCoherenceCritic(t.id, coherencePaths, implCriticCfg.coherence.maxRounds)
    if (!coh.ok) {
      return skip(t, r.decision, 'Coherence critic spawn failed; stopped without implementing.')
    }
    coherenceFindings = coh.residualFindings
  }
```

— `.claude/workflows/qrspi-batch.js:1810-1845`

**Dependencies:** `runCoherenceCritic` (:1667), `art()` (:673), `skip()` (:680), `r.existing` /
`r.ticketContentPath` (resolver envelope fields). `coherenceFindings` is consumed downstream —
it must reach the SLICE-1 PR body (comment at :1808-1809), distinct from per-slice findings
which target slice-N.
**Implicit contracts:** Difference for the per-slice gate: the coherence pass runs ONCE
(no slice context); the per-slice critic runs INSIDE the `for (const s of setup.slices)` loop
AFTER each slice's commit. The fail-closed-guard pattern (skip on bad inputs) and the
`ok:false → skip` pattern should be reused. `coherenceFindings` (slice-1) and per-slice findings
(slice-N) are SEPARATE buckets that must not be conflated.

## Q9: How does the slice loop currently track the parent branch (the "parent-on-slice-(N-1)" logic) across iterations, and where is restack ordering applied?

**Answer:** The loop is `for (const s of setup.slices)` (qrspi-batch.js:1848). There is NO
explicit JS parent-branch variable; parent selection is encoded inline in the commit-worker
prompt: `parented on ${s.n === 1 ? \`${t.id}/plan\` : \`${t.id}/slice-${s.n - 1}\`}` (:1877).
The only cross-iteration state carried in JS is `let previousNotes = ''` (:1847), updated to
`commit.notesForNext` after each commit (:1885) and fed to the next slice's implement agent as
`PREVIOUS_NOTES`. `alreadyCommitted` slices are `continue`-skipped at :1849. Restack ordering is
NOT applied in the loop body — Graphite restacks implicitly: `gt create` parents on the named
branch (:1877) and later `gt modify` (amend) on a lower slice auto-restacks slices above it
(documented for `qrspi_pr_body.py` at :1903-1906 and `qrspi_revise_amend.py`). The whole-stack
restack happens earlier in the workflow's Restack phase (meta phase :8), not per-slice here.

**Evidence:**

```js
  let previousNotes = ''
  for (const s of setup.slices) {
    if (s.alreadyCommitted) { log(`  ${t.id}: slice ${s.n} already committed — skipping`); continue }
    ...
    previousNotes = commit.notesForNext || ''
    log(`  ${t.id}: slice ${s.n}/${setup.slices.length} committed (${commit.branch})`)
  }
```

— `.claude/workflows/qrspi-batch.js:1847-1887`

**Dependencies:** Commit worker (:1876-1880, schema `SLICE_COMMIT_SCHEMA` :504-513 returns
`{ok, branch, notesForNext}`). `previousNotes` thread → implement agent prompt (:1864-1865).
**Implicit contracts:** Parent-of-slice-N is `${id}/plan` for N=1 else `${id}/slice-(N-1)` —
identical to `decide()`'s `diffBase` (Q3), so a per-slice critic placed AFTER the commit at
:1885 sees a valid `diffBase..diffHead`. The loop preserves prior slices on failure
(`return skip(...)` mid-loop leaves committed slices intact, :1872-1873, :1882-1883).

## Q10: How does `decide()` signal and what are the `skipReason` values for the `single-slice` and `alreadyCommitted` skips, and what does the loop currently do (if anything) when `dec.run` is false?

**Answer:** `decide()` signals a skip with `run:false` and a `skipReason` of either
`"alreadyCommitted"` or `"single-slice"` (and `diffBase:None, diffHead:None`).
`"alreadyCommitted"` is evaluated FIRST (so a single committed slice yields
`"alreadyCommitted"`, not `"single-slice"`). `"single-slice"` fires when `len(slices) == 1`.
On a RUN, `skipReason` is `None`. **The loop currently does NOTHING with `dec.run`** — `decide()`
is never invoked in `doImplementation`; the only existing skip is the `alreadyCommitted`
`continue` at :1849 (a separate check on `s.alreadyCommitted`, not via `decide`). So today
there is no per-slice critic to skip; the ticket must add the `dec.run === false → skip the
critic (not the slice)` branch.

**Evidence:**

```python
    if already:
        return {"run": False, "skipReason": "alreadyCommitted", "diffBase": None, "diffHead": None}
    if len(slices) == 1:
        return {"run": False, "skipReason": "single-slice", "diffBase": None, "diffHead": None}
```

— `scripts/qrspi_slice_critic.py:82-87`

```js
    if (s.alreadyCommitted) { log(`  ${t.id}: slice ${s.n} already committed — skipping`); continue }
```

— `.claude/workflows/qrspi-batch.js:1849`

**Dependencies:** `decide()` is pure; its `run:false` result is the gate. The example config
comment confirms the intent: "a single-slice ticket skips it — the coherence pass covers the
lone slice" (`.qrspi/config.example.json:25`).
**Implicit contracts:** When `dec.run === false`, the per-slice critic is SKIPPED (the slice
itself still commits). This is NOT a `skip(t, ...)` ticket-stop — it is a no-op continue of the
critic only. Conflating "critic skip" with "ticket skip" would wrongly abort the run. The
`alreadyCommitted` critic-skip overlaps the existing `s.alreadyCommitted` loop-`continue`
(:1849) — a committed slice never reaches a post-commit critic anyway, so `decide`'s
`alreadyCommitted` branch is mainly defensive/for the CLI.

## Q11: When `runSliceCritic` takes its revise branch (amend slice N via `qrspi_revise_amend.py` then restack N+1…M), what loop state could become stale, and how does the loop's parent-tracking interact with an in-place amend mid-iteration?

**Answer:** `runSliceCritic`'s revise branch (qrspi-batch.js:1758-1777) runs a worker that
`gt checkout ${id}/slice-N`, edits, and amends via `qrspi_revise_amend.py --ticket ${id}
--branch ${id}/slice-N` (:1769), then re-critiques on the next round. An in-place amend of slice
N changes slice N's commit OID and `gt modify` auto-restacks slices N+1…M onto the new N. State
that could go stale: (1) `previousNotes` — captured from slice N's ORIGINAL commit
(:1885) before the amend; the amend may have changed code but `previousNotes` is already
consumed by the time the critic runs (critic runs after commit), so it is not re-derived — a
later slice would carry pre-amend notes. (2) Any cached branch OIDs / the diff range — but
`runSliceCritic` re-runs `git diff ${diffRange}` each round by branch NAME (:1731), not OID, so
the range stays valid after amend. (3) Because the critic runs per-slice in loop order (N before
N+1), and the amend restacks upward, slice N is fully settled before N+1's critic runs — so the
parent base for N+1 (`${id}/slice-N`) is the amended N, which is correct. The main staleness risk
is `previousNotes` not reflecting a post-amend code change.

**Evidence:**

```js
3. Stage your edits AND amend the slice commit IN PLACE by running EXACTLY this one self-locating command verbatim ...:
     python3 ${engineCmdFor(r, 'scripts/qrspi_revise_amend.py')} --ticket ${id} --branch ${branch}
   It checks out the branch, stages every edit ..., amends with `gt modify` ... and VERIFIES the amend captured your changes ...
```

— `.claude/workflows/qrspi-batch.js:1768-1770`

```js
    previousNotes = commit.notesForNext || ''
```

— `.claude/workflows/qrspi-batch.js:1885`

**Dependencies:** `qrspi_revise_amend.py` (self-locating; stages+amends+verifies). The revise
worker returns `WORKER_SCHEMA {ok, summary}` (:1772); `ok!==true → return {ok:false}` stops the
ticket (:1774-1777).
**Implicit contracts:** The critic must run AFTER the slice commits and BEFORE the next slice
commits, so an amend of N restacks cleanly before N+1 is built. If the per-slice critic is
placed at the END of each loop iteration (after :1885), `previousNotes` for N+1 reflects the
PRE-amend notes — acceptable if revise edits don't change the "notes for next session", but a
known soft-staleness. Restack of N+1…M is delegated to `gt modify` (auto), not coded in the loop.

## Q12: How is `skip(t, r.decision, …)` currently called elsewhere in the batch (its signature and the effect of skipping), so a `runSliceCritic` `ok:false` result can map to it without a silent ship?

**Answer:** `function skip(t, decision, note)` returns `{ticketId: t.id, action:
decision.action, summary: note}` (qrspi-batch.js:680-682). The effect: the ticket advances NO
further this run — the returned object becomes `doImplementation`'s result, surfaced in the run
summary; nothing is submitted/landed. It is called throughout `doImplementation` on every
failure path: impl-setup failure (:1798-1799), coherence inputs missing (:1833), coherence spawn
failure (:1842), per-slice implement failure (:1873), per-slice commit failure (:1883). The
established convention is `return skip(t, r.decision, '<reason>')`. So a `runSliceCritic`
`ok:false` maps directly: `if (!sc.ok) return skip(t, r.decision, \`Slice ${s.n} critic spawn
failed; stopped without shipping.\`)`.

**Evidence:**

```js
function skip(t, decision, note) {
  return { ticketId: t.id, action: decision.action, summary: note }
}
```

— `.claude/workflows/qrspi-batch.js:680-682`

```js
    if (!coh.ok) {
      return skip(t, r.decision, 'Coherence critic spawn failed; stopped without implementing.')
    }
```

— `.claude/workflows/qrspi-batch.js:1841-1843`

**Dependencies:** `skip()` reads `t.id` and `decision.action`; callers pass `r.decision`. The
result object shape `{ticketId, action, summary}` matches `finResult`'s success/failure shapes
(:2210-2216) so the run summary renders uniformly.
**Implicit contracts:** `skip` PRESERVES already-committed slices (it just stops; it does not
unwind). A `runSliceCritic` `ok:false` (critic/revise/decision spawn failure) MUST map to `skip`
(documented at :1719-1720, Risk Register row 2) — never fall through to finalize/submit (that
would be a silent ship of an un-critiqued / failed-revise slice).

## Q13: Where does the finalize worker currently splice content into the slice-1 commit message (pr-summary/coherence), and what amend/`gt submit` ordering must per-slice findings respect to land in each slice's PR body?

**Answer:** The finalize worker (qrspi-batch.js:1901-1911) splices `pr-summary.md` into the
SLICE-1 commit message via `python3 qrspi_pr_body.py --ticket ${t.id} --slice 1` (:1905) BEFORE
`gt submit --publish --stack --no-edit --no-interactive` (:1907). Step 1 amends pr-summary.md
into the last slice commit as the durable artifact (:1903); step 2 splices it into slice-1's
message (:1904-1906); step 3 submits the whole stack. **Coherence findings are NOT yet spliced
in the finalize worker** — `coherenceFindings` is carried in memory (:1844) but there is no
`criticBodyStep`/`qrspi_critic_body.py --phase slice --slice 1` call in the impl finalize prompt
yet (the design/plan finalize prompts DO use `criticBodyStep` at :1563/:1636, but impl does not).
For per-slice findings to land: each slice-N's findings must be spliced into slice-N's commit
message (via `qrspi_critic_body.py --phase slice --slice N`) BEFORE the stack `gt submit`,
because `gt submit` seeds PR bodies from commit messages at CREATION only (:1268-1273).
Amend-then-submit ordering: amend lowest-N first (restacks upward), then one `gt submit --stack`.

**Evidence:**

```js
2. Splice pr-summary.md into the SLICE-1 commit MESSAGE ..., BEFORE submitting, by running EXACTLY this one self-locating command verbatim ...:
     python3 ${engineCmdFor(r, 'scripts/qrspi_pr_body.py')} --ticket ${t.id} --slice 1
...
3. Submit the entire stack PUBLISHED with Graphite ...: `gt submit --publish --stack${reviewerFlags(r)} --no-edit --no-interactive`
```

— `.claude/workflows/qrspi-batch.js:1904-1907`

```python
the slice commit's message to `<existing subject> + <body file contents> + <existing trailer>`
and amends it via `gt modify -m` (which auto-restacks the slices above it).
```

— `scripts/qrspi_pr_body.py:23-24`

**Dependencies:** `qrspi_pr_body.py` (slice-1 summary), `qrspi_critic_body.py --phase slice`
(per-slice findings — Q6), `criticBodyStep()` (:1274, the design/plan splice helper). Order:
slice-N findings amend → slice-1 summary amend → `gt submit --stack`.
**Implicit contracts:** All commit-message amends MUST precede the single stack `gt submit` (body
seeded at creation only). Amending slice N auto-restacks N+1…M, so amend lowest-first to avoid
re-restacking churn. Slice-1 carries pr-summary + coherence findings; slice-N (N>1) carries its
own "Part N/total" body + that slice's per-slice findings. Mixing buckets corrupts which PR shows
which finding.

## Q14: What unit tests already cover `qrspi_slice_critic.py decide()` and `qrspi_critic_body.py --phase slice`, and which input combinations (single-slice, alreadyCommitted, multi-slice) do they assert?

**Answer:** `scripts/qrspi_slice_critic_test.py` is stdlib-only assert-based (no runner). It
asserts: slice-1 multi-slice non-committed → run, `diffBase=RUS-58/plan`,
`diffHead=RUS-58/slice-1`; slice-2/3 → run, base=prior slice; run case has `skipReason None`;
`alreadyCommitted` mid-slice → skip "alreadyCommitted" no diff; committed slice-1 → skip
"alreadyCommitted" (resume); `len==1` non-committed → skip "single-slice"; single COMMITTED
slice → "alreadyCommitted" precedence over "single-slice". `scripts/qrspi_critic_body_test.py`
covers `phase_branch` for the slice phase: design/plan IGNORE a passed slice_index;
`slice` N=1 → `RUS-9/slice-1`, N>1 → `RUS-9/slice-7`; str index coerced; None/0/non-int →
ValueError; `"slice" in _PHASE_BRANCH` (registered choice). It does NOT test the full
`--phase slice` CLI/subprocess path (the amend mechanics are manual-e2e, not unit-tested).

**Evidence:**

```python
check("len(slices) == 1, non-committed ⇒ skip with reason single-slice",
      decide(SINGLE, 1),
      {"run": False, "skipReason": "single-slice", "diffBase": None, "diffHead": None})
check("single committed slice ⇒ alreadyCommitted precedence over single-slice",
      decide(SINGLE_COMMITTED, 1),
      {"run": False, "skipReason": "alreadyCommitted", "diffBase": None, "diffHead": None})
```

— `scripts/qrspi_slice_critic_test.py:80-89`

```python
check("phase_branch slice N=1", phase_branch("RUS-9", "slice", 1), "RUS-9/slice-1")
check("phase_branch slice N>1", phase_branch("RUS-9", "slice", 7), "RUS-9/slice-7")
```

— `scripts/qrspi_critic_body_test.py:79-80`

**Dependencies:** Tests import `decide` / `phase_branch, _PHASE_BRANCH` directly (pure). Run with
`python3 scripts/qrspi_*_test.py`. No JS-side test for `runSliceCritic` exists (it is untested
orchestration glue — matching the "pure logic unit-tested, JS glue manual-e2e" convention).
**Implicit contracts:** The pure reducers ARE tested; the JS wiring (the loop integration this
ticket adds) is NOT unit-testable in this harness — verify via the python tests + manual e2e
(per CLAUDE.md: "verify pure logic with unit tests and orchestration changes with manual
end-to-end runs"). Any NEW pure JS helper added for the wiring (e.g. `resolveImplementationCritic`)
has a `_test.py`/JS-test precedent to follow.

## Q15: What logging or status output does `runSliceCritic` and the surrounding loop emit to make a critique run (its rounds, skips, and residual findings) visible in a batch run's output?

**Answer:** `runSliceCritic` already emits `log(...)` lines for every state: per-round verdict
`slice N critic round R/M → PASS|FAIL (k finding(s))` (:1743), CONVERGED (:1751), CAP-REACHED
with residual count (:1755), REVISE (:1760), revise-amend failure (:1775), critic/decision spawn
failure (:1738/:1747), and loop exhausted (:1779). The surrounding loop emits per-slice commit
lines `slice N/total committed (branch)` (:1886) and `slice N already committed — skipping`
(:1849). The coherence pass emits ENABLED/maxRounds (:1837) and findings-carried lines
(:1700). What's MISSING for the new wiring: a log line for the `dec.run === false` per-slice
skip (single-slice / alreadyCommitted critic-skip), and a line surfacing how many per-slice
residual findings were carried into slice-N's PR body. `log` is a framework-injected global
(no local definition in the file).

**Evidence:**

```js
    log(`  ${id}: slice ${sliceN} critic round ${round + 1}/${rounds} → ${passed ? 'PASS' : `FAIL (${findings.length} finding(s))`}`)
    ...
    log(`  ${id}: slice ${sliceN} critic CAP-REACHED at round ${round + 1} — ${decision.residual_findings.length} residual finding(s) carried to the slice PR body (ship-with-disclosure)`)
```

— `.claude/workflows/qrspi-batch.js:1743,1755`

```js
    log(`  ${t.id}: implementation coherence pass ENABLED — maxRounds ${implCriticCfg.coherence.maxRounds}`)
```

— `.claude/workflows/qrspi-batch.js:1837`

**Dependencies:** `log()` injected global; `phase()` injected global marks phase transitions
(`phase('Implementation')` :1787, `phase('Finalize')` :1900). Log lines use the `  ${id}: ...`
two-space-indent convention.
**Implicit contracts:** Every critic terminal state (converge/cap/revise/skip/spawn-fail) SHOULD
emit one `  ${id}: slice N ...` line so a batch run is auditable. The new wiring should add a
`dec.run === false` skip line (mirroring the coherence "skipping" lines) and reuse the existing
PASS/FAIL/CAP/REVISE logging inside `runSliceCritic` unchanged.

---

## Discovered Patterns

- **Pure-reducer + JS-glue split.** Every deterministic decision lives in a stdlib-only
  `scripts/qrspi_*.py` module with a `_test.py` sibling and a thin stdin->stdout CLI; the JS
  orchestrator invokes it through a single-purpose worker agent and never re-derives the logic
  (`qrspi_slice_critic.py`+`decide`, `qrspi_critic_loop.py`+`criticDecision`,
  `qrspi_critic_body.py`, `qrspi_pr_body.py`). The slice-critic wiring is expected to follow
  this: call `decide()` via a worker rather than replicate run/skip/diff-base in JS.
- **Critic helpers share one return contract** `{ok, residualFindings}` (`runCriticLoop` :759,
  `runCoherenceCritic` :1667, `runSliceCritic` :1721), so the caller treats all three uniformly:
  `ok:false → skip(...)`, carry `residualFindings` into a PR body.
- **`ok:false → skip(t, r.decision, ...)` everywhere** in `doImplementation` — no failure path
  falls through to submit. This is the "no silent ship" invariant (Risk Register row 2).
- **PR bodies are commit-message-seeded at CREATION only.** All body content (pr-summary,
  residual findings) must be amended into the commit message BEFORE `gt submit`; `gt modify` on a
  lower slice auto-restacks slices above it, so amend lowest-N first.
- **Opt-in config via a single `--key critics` read.** `qrspi_config.py` is single-top-level-key
  only; `--key critics.implementation` is forbidden — read the whole `critics` object once and dig
  `value.implementation` (`readImplementationCriticConfig` :1230). Absent/false ⇒ byte-for-byte
  unchanged no-critic path.
- **Two separate findings buckets:** coherence findings → SLICE-1 PR body; per-slice findings →
  SLICE-N PR body. They must not be conflated.
- **`runSliceCritic` is dead code today** — defined (:1721) with full logging and revise wiring
  but never invoked. The entire ticket is the integration of this existing helper into the loop.

## Inconsistencies

- **Ticket/questions reference a non-existent script.** Q7 (and the ticket) name
  `scripts/qrspi_critics_config.py` and a two-field `{enabled, maxRounds}` config shape. That
  file does NOT exist (`ls` → no such file). The real reader is `scripts/qrspi_config.py`,
  surfaced via the JS helpers `parseImplementationCriticConfig`/`resolveImplementationCritic`
  (:424-457) and `readImplementationCriticConfig` (:1230). The resolved shape is the FOUR-field
  `{enabled, maxRounds, coherence:{enabled, maxRounds}}`, not `{enabled, maxRounds}`. Treat the
  ticket's `qrspi_critics_config.py` as a stale name for this JS-side config resolution.
- **Q4 line/param drift.** The questions file cites `runSliceCritic()` at
  `qrspi-batch.js:1614` with a param `n`; the actual definition is at **line 1721** with param
  **`sliceN`** (the full signature is `(t, r, wd, sliceN, dec, planSlice, structureSlice,
  maxRounds)`). Line 1614 is inside the doPlan finalize block, unrelated.
- **`alreadyCommitted` double-gate.** `decide()` returns `skipReason:"alreadyCommitted"` for a
  committed slice, but the loop ALSO `continue`s committed slices before any post-commit critic
  (:1849). So `decide`'s `alreadyCommitted` branch is effectively unreachable from a
  post-commit call site — it is defensive / for the standalone CLI. Not a bug, but the two skip
  mechanisms overlap.
- **Comment says "carried to the slice PR body" but no splice exists yet.** `runSliceCritic`'s
  cap-reached log claims residual findings are "carried to the slice PR body" (:1755), and the
  coherence pass claims findings are "carried to slice-1 PR body" (:1700/:1844), but the impl
  finalize worker (:1901-1911) currently splices ONLY pr-summary.md — there is no
  `criticBodyStep`/`qrspi_critic_body.py --phase slice` call for coherence or per-slice findings
  yet. The carry is in-memory only; the actual PR-body splice is unimplemented (part of this
  ticket's work).
- **`criticBodyStep` supports `slice` downstream but is only called with `design`/`plan`.**
  `qrspi_critic_body.py`'s `_PHASE_BRANCH` includes `slice` (:48) and the CLI accepts
  `--phase slice --slice N`, but the JS `criticBodyStep(id, phase, findings, wd)` helper (:1274)
  is only invoked as `criticBodyStep(t.id, 'design', ...)` (:1563) and `criticBodyStep(t.id,
  'plan', ...)` (:1636) — never with `'slice'`. The slice path in the python script is built but
  not yet wired from JS.
