# Research — Codebase Map

**Questions source:** questions.md @ /workspaces/qrspi/.worktrees/RUS-93/.qrspi/RUS-93/questions.md
**Generated:** 2026-06-19T00:00:00Z
**Status:** draft

> Scope note: the autonomous `qrspi-batch` critic loops (`runCriticPanelLoop`,
> `runCoherenceCritic`) referenced in several Python module docstrings were
> RETIRED (RUS-88). They no longer exist in `.claude/workflows/qrspi-batch.js`
> (verified by grep — only doc-comment mentions remain). The on-demand
> `/review-*` family (three `SKILL.md` files) is the only surviving caller of
> these Python helpers. The "loop" today is the hand-written step sequence inside
> each `SKILL.md`, driven by an LLM agent, NOT a JS function.

## Q1: How does a per-lens finding currently flow from a fired lens Agent through `qrspi_critic_synthesize` into `qrspi_review_synopsis`, and at what step is the blocking finding *text* (vs. just a per-lens count) dropped so it never reaches the rendered synopsis?

**Answer:** Finding TEXT is **preserved** through `synthesize` (it returns the
deduped union of finding strings/objects), but it is **dropped at the synopsis
render boundary**: `render_synopsis` only emits a per-lens *count* in the "Review
axes" table, never the finding text. The flow:

1. Each lens Agent returns a `LensVerdict` `{lens, pass, findings:[str], nonBlockingNotes?:[str]}` (assembled by the SKILL into a "pre-reduction verdict array").
2. `qrspi_critic_synthesize.synthesize(panel)` reduces the array to `{pass, findings}` — `findings` is the exact-string-deduped union of all lenses' blocking findings, first-seen order (text retained, optionally lens-tagged as `{text, lens}`).
3. That synthesized `{pass, findings}` is fed to `qrspi_critic_loop.next_action` (as a one-element array) to pick `converged|revise|cap_reached`. The synthesized `findings` become `residual_findings` handed to the reviser — so finding text IS used inside the loop.
4. The **synopsis** is rendered by `qrspi_review_synopsis.render_synopsis(verdict_array, decision_readiness, terminal_action)` from the *pre-reduction array* (NOT the synthesized findings). Its "Review axes" table renders only `_blocking_count(verdict)` = `len(findings)` per lens. The actual blocking finding strings are never written into the synopsis body.

So the synthesized union of finding TEXT reaches the reviser/loop, but the
rendered synopsis exposes only a per-lens FAIL + integer count. `nonBlockingNotes`
text IS rendered (advisory section); blocking `findings` text is not.

**Evidence:**

```python
def _blocking_count(verdict):
    return len(_as_list(verdict.get("findings")))
...
    for verdict in verdict_array:
        ...
        count = _blocking_count(verdict)
        verdict_label = "PASS" if passed else "FAIL"
        lines.append(f"| {lens} | {verdict_label} | {count} |")
```

— `scripts/qrspi_review_synopsis.py:52-57,140-147` (count-only render)

```python
        for finding in coerced["findings"]:
            key = _finding_key(finding)
            if key in seen: continue
            seen.add(key)
            ... findings.append(finding)   # text preserved in the union
    return {"pass": all_passed, "findings": findings}
```

— `scripts/qrspi_critic_synthesize.py:106-118` (text preserved through reduce)

**Dependencies:** `render_synopsis` is called only from the three `SKILL.md`
Step-6/7 heredocs. `synthesize` is called from each SKILL's Step-4b heredoc and
from `qrspi_critic_synthesize.py` CLI `main`.
**Implicit contracts:** The blocking invariant `pass:false ⟺ findings non-empty`
is enforced per-lens by the lens agents (e.g. `qrspi-design-critic-design-review.md:60`),
so `blockingCount > 0 ⟺ FAIL` in the rendered table. The synopsis reader
currently must infer "what is wrong" from the count alone; the finding text exists
upstream but is not surfaced.

## Q2: In the current loop, what exactly is fed to the panel on each round — the original artifact, or the reviser-mutated scratch copy — and where does the round-0 (artifact-as-written) verdict get retained or overwritten as the loop iterates `0..MAX-1`?

**Answer:** The panel is fed the **scratch copy** every round. Step 3 of each
SKILL copies the tracked artifact to `/tmp/phase-stage/<id>/review/<artifact>.md`
(`SCRATCH`); round 0 reads the artifact-as-written (a fresh copy), and on a
`revise` the shared reviser (`qrspi-critic-reviser`) **rewrites SCRATCH in place**,
so round `r>0` reads the reviser-mutated copy. The reviser's `OUTPUT_PATH` is
exactly `SCRATCH`.

Round-0 verdict retention: the SKILL instructs accumulating **per-lens entries
across ALL rounds** into a `rounds` list (N lenses × R rounds), appended each
round — so round-0's per-lens entries are RETAINED in that ledger list. BUT the
synopsis and `ledger_row_fields` are fed only the **FINAL round's** pre-reduction
array ("last_round_verdicts"), so round-0's *axis/synopsis* view is overwritten by
the last round. There is no code retaining the round-0 verdict as a distinct
"as-written" datum for the synopsis — only the accumulated `rounds[]` keeps it,
and that list is reduced by `qrspi_critic_metrics.build_record` to
`{lens, pass, findingsCount}` per entry.

**Evidence:**

```
cp "<DESIGN>" /tmp/phase-stage/<ticket-id>/review/design.md
Use `SCRATCH` = /tmp/phase-stage/<ticket-id>/review/design.md as the artifact under review
...
- OUTPUT_PATH = /tmp/phase-stage/<ticket-id>/review/design.md (the scratch copy — the ONLY path it may write)
... Then continue to the next round against the rewritten scratch copy.
```

— `.claude/skills/review-design/SKILL.md:86-89,177,186`

```
last_round_verdicts = <the FINAL round's pre-reduction per-lens verdict array from Step 4a>
```

— `.claude/skills/review-design/SKILL.md:222,257` (synopsis + ledger fed last round only)

**Dependencies:** Loop is hand-driven by the SKILL agent; mutation is in
`qrspi-critic-reviser` (Agent), decision in `qrspi_critic_loop.next_action`.
**Implicit contracts:** The reviser MUST write only `OUTPUT_PATH` verbatim
(propose-only invariant; head-SHA check in the final Step guards it). The "last
round wins" convention means a non-converged cap_reached run's synopsis reflects
the most-revised scratch, not the original — round-0 is not separately surfaced.

## Q3: What are the function signatures and JSON input/output contracts of the surviving Python helpers that a deterministic orchestrator must call?

**Answer:** All are pure (no IO except the thin CLIs / smoke blocks), stdlib-only,
self-locating where they import siblings.

- `qrspi_critic_synthesize.synthesize(verdicts: list) -> dict` — in: list of raw per-lens entries (dict/str/other, each coerced fail-closed); out: `{"pass": bool, "findings": list}`. `pass` True only if list non-empty AND every coerced lens passed. CLI: stdin JSON array → stdout `{pass, findings}`.
- `qrspi_critic_loop.next_action(verdicts: list, round: int, max_rounds: int) -> dict` — out: `{"action": "converged"|"revise"|"cap_reached", "residual_findings": [...]}`. Latest (last) element authoritative. CLI: `--round R --max-rounds M`, stdin JSON array. Also `parse_critic_verdict(text: str) -> {pass, findings}` (fail-closed parser).
- `qrspi_review_synopsis`: `partition_decision_readiness(verdict_array) -> (panel_list, decision_readiness_dict|None)`; `ledger_row_fields(verdict_array) -> {"axes":[{lens,pass,blockingCount}], "nonBlockingNotes":[str]}`; `render_synopsis(verdict_array, decision_readiness, terminal_action) -> str` (Markdown). No CLI — imported by SKILL heredocs.
- `qrspi_review_agreement.compute(panel_pass: bool, human_decision: str|None) -> {panelVerdict, humanVerdict, agreement}`. `panelVerdict` "pass"/"fail"; `humanVerdict` normalized or None; `agreement` "agree"/"disagree"/"pending". Has a `__main__` smoke block (argv), not a piping CLI.
- `qrspi_critics_config` (`main()` CLI, no args) → stdout `{"ok":bool, "phases":{design, implementation}, "warnings":[...]}`. `resolve_critics(critics) -> (phases, warnings)`; `resolve_design(cfg, warnings)`; `resolve_implementation(cfg)`. Exposes the lens constants (Q11).
- Adjacent (used by the SKILLs): `qrspi_review_record.build_record(phase, rounds, terminal_action, agreement) -> ReviewRecord` (wraps `qrspi_critic_metrics.build_record(verdicts, terminalAction, phase=...)`). `terminal_action` must be in `VALID_TERMINAL_ACTIONS = {converged, cap_reached, exhausted, aborted}` (revise rejected → `ValueError`).

**Evidence:**

```python
def synthesize(verdicts):
    if not isinstance(verdicts, list) or not verdicts:
        return {"pass": False, "findings": []}
```

— `scripts/qrspi_critic_synthesize.py:76,94-95`

```python
def next_action(verdicts, round, max_rounds):
    latest = _coerce_verdict(verdicts[-1]) if isinstance(verdicts, list) and verdicts else {...}
    if latest["pass"]: return {"action": "converged", "residual_findings": []}
    if int(round) + 1 >= int(max_rounds): return {"action": "cap_reached", ...}
    return {"action": "revise", "residual_findings": list(latest["findings"])}
```

— `scripts/qrspi_critic_loop.py:84,106-115`

```python
def build_record(phase, rounds, terminal_action, agreement):
    record = qrspi_critic_metrics.build_record(rounds, terminal_action, phase=phase)
    record["agreement"] = agreement
    record["mode"] = MODE_ON_DEMAND_REVIEW
    return record
```

— `scripts/qrspi_review_record.py:48,68-72`

**Dependencies:** `qrspi_critic_synthesize` imports `_coerce_verdict`,
`parse_critic_verdict` from `qrspi_critic_loop`. `qrspi_review_record` imports
`qrspi_critic_metrics`. `qrspi_critics_config` imports `qrspi_config.read_config`.
**Implicit contracts:** Every helper fails closed (never raises) EXCEPT
`build_record`, which raises `ValueError` on a non-terminal/invalid
`terminalAction` (so it must be called only after the loop terminates). CLIs
print exactly one JSON line on stdout.

## Q4: How does the existing `.claude/workflows/qrspi-batch.js` orchestrator structure its agent fan-out, JSON piping to `python3` helpers, and worktree/path resolution — i.e., what patterns must a new shared review engine match?

**Answer:** Key patterns:

1. **No `Agent` tool in JS** — the Workflow RUNNER spawns typed agents via the injected `agent(prompt, {label, phase, agentType?, schema?})` global. Injected globals: `['agent','parallel','pipeline','phase','log','args','budget','workflow']` (verified in `scripts/contract_seam_runner.js:43`). `log` and `agent` are NOT defined in batch.js — they are runtime-injected.
2. **JS sandbox cannot run python** — every `python3 …` call is embedded as a literal command STRING inside a worker-agent prompt; the worker runs it and returns the parsed JSON envelope. The JS never executes python directly.
3. **Engine-root indirection** — bare-relative script paths are prefixed: `engineCmd(rel) = ${ENGINE_ROOT}/${rel}` for runner-cwd, and `engineCmdFor(r, rel) = ${engineRootFor(r)}/${rel}` for WORKER-cwd prompts (a worker's cwd is a worktree, so its prompt must use `engineCmdFor`/`r.worktreeDir`, not `engineCmd`'s `.`). `ENGINE_ROOT` precedence: `CLAUDE_PLUGIN_ROOT` env > `process.cwd()` > `'.'`.
4. **Staging helper** — `stg(id, name) = /tmp/phase-stage/${id}/${name}.md`; agents write here, then a deterministic `qrspi_persist.py` worker moves it.
5. **Worktree (re-)provision** — every worker prompt prepends a MANDATORY `provisionStep` running `python3 scripts/qrspi_provision.py --ticket <id>` (git admin metadata does not survive the agent boundary; HARD STOP on ok:false).
6. **Worker fan-out is sequential per ticket** (one autonomous step per run); there is no per-lens `parallel()` fan-out in batch.js today (the panel was retired). The `/review-*` SKILLs fan lenses out via repeated `Agent` calls inside a single skill session, NOT via the JS runner.

**Evidence:**

```js
const engineCmd = (rel) => `${ENGINE_ROOT}/${rel}`
const engineCmdFor = (r, rel) => `${engineRootFor(r)}/${rel}`
const stg = (id, name) => `/tmp/phase-stage/${id}/${name}.md`
```

— `.claude/workflows/qrspi-batch.js:76,105,464`

```js
const res = await agent(prompt, { label: `${name}:${id}`, phase: phaseLabel, agentType })
```

— `.claude/workflows/qrspi-batch.js:517`

**Dependencies:** Runner injects globals; workers run python + git/gh/gt; resolver
is `qrspi_resolve.py`. **Implicit contracts:** A worker prompt that runs in a
worktree MUST use `engineCmdFor(r, …)` / `r.worktreeDir`, never `engineCmd`'s `.`
(documented bite: RUS-62, MEMORY.md "batch worker-cwd engine path"). qrspi-batch.js
is harness-coupled (top-level `return`, injected globals, no import) and not
unit-testable in isolation.

## Q5: How is the `lensModel` seam currently declared (and documented as "not wired") in the node-validity `*-review` lens agent definitions, and what is the mechanism by which an agent's model is selected vs. silently inheriting the session model?

**Answer:** Two distinct, **disconnected** `lensModel` mentions exist:

1. **Config resolver** — `qrspi_critics_config.resolve_design` reads an optional `critics.design.lensModel` string and includes it in the resolved design phase envelope ONLY when it is a non-empty string; otherwise the key is OMITTED entirely (not None). Tested. But NOTHING consumes this resolved key — there is no code path that passes it to an Agent.
2. **Lens agents** — the three node-validity `*-review` agent definitions carry a "Note — target model (documentation only)" section explicitly stating the Opus-tier intent is **NOT wired** via any `lensModel`/model frontmatter key; the lens "inherits the panel's session model at runtime."

Mechanism for model selection: an agent's model is set via its frontmatter (the
`*-review` agents have only `claude: { tools: Read, Grep }` — no `model` key), so
they silently inherit the spawning session's model. The `/review-*` SKILLs spawn
each lens via `Agent` with NO `model` override ("no `model` override — model
selection is not wired in v1"). So `lensModel` is resolvable in config and
documented in agents, but there is NO wire connecting them.

**Evidence:**

```python
    lens_model = cfg.get("lensModel")
    if isinstance(lens_model, str) and lens_model.strip():
        result["lensModel"] = lens_model
```

— `scripts/qrspi_critics_config.py:208-210`

```
... it is NOT wired via any `lensModel`/model frontmatter key — the lens inherits
the panel's session model at runtime, and the panel-wide model seam is out of
scope for this lens (ref: RUS-82 design AC7).
```

— `.claude/agents/qrspi-design-critic-design-review.md:74` (identical at
`qrspi-plan-critic-plan-review.md:73`, `qrspi-impl-critic-impl-review.md:74`)

**Dependencies:** Config seam: `qrspi_critics_config.py`. Agent frontmatter:
the three `*-review.md`. SKILL spawn: `review-*/SKILL.md` step 4a tables.
**Implicit contracts:** Frontmatter `claude.tools` restricts the lens to
Read/Grep; absence of a `model` key ⇒ inherit session model. The `lensModel`
config key is currently a no-op (resolved but never read).

## Q6: What fields does a `mode:"on-demand-review"` ledger row currently contain, where is the ledger persisted, and what does `qrspi_review_agreement` read from / write to that row?

**Answer:** The row is built by `qrspi_review_record.build_record` and is:
`{phase, rounds:[{lens, pass, findingsCount}], terminalAction, agreement:{panelVerdict, humanVerdict, agreement}, mode:"on-demand-review"}`, then MERGED
(via `record.update(...)`) with `ledger_row_fields()` additive fields `axes` and
`nonBlockingNotes`. It is appended by `scripts/qrspi_metrics_append.py --ticket … --run-id … --record …`, which stamps each line with `ticketId`, `timestamp`,
`runId`. The ledger is the per-ticket `critic-metrics.jsonl` (named in the SKILL
Step-4c notes and the synopsis module docstring; appended via `qrspi_metrics_append.py`).

`qrspi_review_agreement` does NOT read or write the ledger directly. It is a pure
reducer: `compute(panel_pass, human_decision)` returns the `agreement` block that
`build_record` embeds. The human decision comes from `gh pr list … --json reviewDecision` (Step 2 of each SKILL), not from the row.

**Evidence:**

```python
    record["agreement"] = agreement
    record["mode"] = MODE_ON_DEMAND_REVIEW
    return record
```

— `scripts/qrspi_review_record.py:70-72`

```
record = qrspi_review_record.build_record(phase="design", rounds=rounds, terminal_action=..., agreement=agreement)
record.update(qrspi_review_synopsis.ledger_row_fields(last_round_verdicts))
...
python3 scripts/qrspi_metrics_append.py --ticket <ticket-id> --run-id "review-design-..." --record '<record JSON>'
```

— `.claude/skills/review-design/SKILL.md:225-243`

**Dependencies:** `build_record` → `qrspi_critic_metrics.build_record` for the
base shape; `ledger_row_fields` from `qrspi_review_synopsis`; append via
`qrspi_metrics_append.py`; summary read via `qrspi_critic_summary.summarize`.
**Implicit contracts:** `axes`/`nonBlockingNotes` are ADDITIVE — `qrspi_critic_summary.summarize` reads via `.get()` so it is unaffected by their
presence/absence. `mode:"on-demand-review"` is the discriminator separating these
rows from any batch critic rows. `rounds` buckets per-lens dissent on `rnd["lens"]`,
so each round must contribute one entry per lens (N×R), never one synthesized entry.

## Q7: Where does the loop hold the scratch copy of the artifact, and what is the relationship between the scratch path and the real artifact path under `.worktrees/<id>/.qrspi/<id>/`?

**Answer:** Scratch path: `/tmp/phase-stage/<ticket-id>/review/<artifact>.md`
(design.md / plan.md / impl-log.md). The real artifact lives at
`<worktreeDir>/.qrspi/<ticket-id>/<artifact>.md` where
`worktreeDir = <repoRoot>/.worktrees/<ticket-id>` (from the `qrspi_resolve.py`
envelope). Step 3 copies real → scratch ONCE; the loop and the reviser thereafter
touch ONLY the scratch copy. The reviser's `OUTPUT_PATH` is the scratch path
"verbatim — the ONLY path it may write." This is what keeps the PR branch
untouched (propose-only): the tracked artifact under `.qrspi/<id>/` is never
mutated, and a head-SHA check (captured Step 2, re-checked final step) is the
guardrail.

**Evidence:**

```
mkdir -p /tmp/phase-stage/<ticket-id>/review
cp "<DESIGN>" /tmp/phase-stage/<ticket-id>/review/design.md
Use `SCRATCH` = /tmp/phase-stage/<ticket-id>/review/design.md as the artifact under review
```

— `.claude/skills/review-design/SKILL.md:85-89`

```
2. The loop edits only the scratch copy under /tmp/phase-stage/<ticket-id>/review/,
   never <worktreeDir>/.qrspi/<ticket-id>/design.md.
```

— `.claude/skills/review-design/SKILL.md:294`

**Dependencies:** Scratch dir mirrors `stg()`'s `/tmp/phase-stage/<id>/` root
(qrspi-batch.js:464) but with a `review/` subdir. `worktreeDir` from
`qrspi_resolve.py`. **Implicit contracts:** Scratch paths are deliberately
token-free/short (same rationale as Fix-A staging — avoid weak-model path
mangling). The propose-only invariant rests entirely on the reviser obeying
`OUTPUT_PATH` and the SKILL never running `gt submit`/`gt modify`.

## Q8: How does the current synopsis render when a lens returns zero blocking findings vs. when it returns findings — and what does the comment show today on a non-converged review where the reviser hit the cap without converging?

**Answer:** Per lens: `render_synopsis` always emits ONE table row
`| <lens> | PASS|FAIL | <blockingCount> |`. Zero findings ⇒ `PASS | 0`; findings
⇒ `FAIL | N`. The actual finding TEXT is NOT shown (Q1). `nonBlockingNotes` (if
any) render as a separate "Advisory (non-blocking)" bullet list with full text;
omitted when empty. Decision-readiness `blockingDecisions` render as a "Decision
readiness (blocking for human)" bullet list (design phase only); omitted when None
or empty. A final `**Terminal action:** <action>` line.

On a non-converged cap-reached review: `terminal_action` = `"cap_reached"`, so the
synopsis ends `**Terminal action:** cap_reached`. The axis table shows the FINAL
round's per-lens PASS/FAIL+counts (so failing lenses show FAIL + count), but NO
blocking finding text and NO explicit "did not converge" prose beyond the
`cap_reached` action label. The SKILL wraps it with an advisory header and an
`**Agreement:**` line.

**Evidence:**

```python
    for verdict in verdict_array:
        ...
        verdict_label = "PASS" if passed else "FAIL"
        lines.append(f"| {lens} | {verdict_label} | {count} |")
    ...
    lines.append(f"**Terminal action:** {terminal_action}")
```

— `scripts/qrspi_review_synopsis.py:140-147,180`

Test confirms count render and advisory passthrough:

```python
        self.assertIn("| edge-alignment | FAIL | 2 |", out)
...
        self.assertIn("Advisory (non-blocking)", out)
        self.assertIn("consider X", out)
```

— `scripts/qrspi_review_synopsis_test.py:116,121-123`

**Dependencies:** Rendered by SKILL Step 6/7 heredoc; posted via
`qrspi_comment_reply.py --reply-mode toplevel`. **Implicit contracts:** The
synopsis is a count-only honest enumeration; a human must open the PR / re-run to
see WHAT failed. `cap_reached` is the only signal that the panel did not converge.

## Q9: What does `qrspi_critic_synthesize` do when one lens errors, returns malformed JSON, or returns an empty finding list — does the AND-reduce treat a missing lens result as pass, fail, or abort?

**Answer:** Fail-closed, never aborts. Each entry is coerced via `_coerce_lens`:
a dict → `_coerce_verdict`, a str → `parse_critic_verdict`, anything else →
`{pass:False, findings:[]}`. A malformed/empty/non-dict entry reads as NOT-passed
and contributes no findings, so it FAILS the AND-reduce (does not pass, does not
abort). An empty verdict list ⇒ `{pass:False, findings:[]}` (no lens attested ⇒
fail closed). A lens that legitimately passes with an empty finding list ⇒
contributes `pass:True`, no findings. `pass` is True ONLY if the list is non-empty
AND every coerced lens passed. A "missing" lens manifests either as a missing
array element (the orchestrator must include it) or a garbled element → treated as
FAIL. `synthesize` never raises (battery test asserts this).

**Evidence:**

```python
def _coerce_lens(entry):
    if isinstance(entry, dict): return _coerce_verdict(entry)
    if isinstance(entry, str): return parse_critic_verdict(entry)
    return {"pass": False, "findings": []}
```

— `scripts/qrspi_critic_synthesize.py:45-53`

```python
check("a non-dict (None) lens entry ⇒ coerced NOT-passed, contributes nothing",
      synthesize([{"pass": True, "findings": []}, None]),
      {"pass": False, "findings": []})
```

— `scripts/qrspi_critic_synthesize_test.py:109-114`

**Dependencies:** Coercion reuses `_coerce_verdict` / `parse_critic_verdict` from
`qrspi_critic_loop` (no re-implemented logic). **Implicit contracts:** "A garbled
lens reply can never silently pass the round." Note: `synthesize` does NOT detect
a *count* mismatch (it cannot know how many lenses were expected) — a lens entirely
omitted from the array is simply not in the AND; correctness depends on the
orchestrator always supplying all lenses. There is no abort/error path.

## Q10: How is the propose-only invariant enforced today — specifically, where is the PR head-SHA captured before the run and asserted unchanged after, and what happens to that assertion if the only GitHub write (the PR comment) fails?

**Answer:** Captured in Step 2 (`gh pr view <PR> --json headRefOid --jq '.headRefOid'`)
and re-read + asserted equal in the final Step (Step 8 design, Step 7 plan/impl).
If changed, the SKILL must "surface that loudly." Enforcement is procedural
(SKILL instructions + the fact that no `gt submit`/`gt modify`/branch-pushing `gh`
write is ever issued) plus the head-SHA equality check; there is NO automated
gate that blocks a push — it is a post-hoc assertion an LLM agent performs.

If the only GitHub write (the toplevel PR comment via `qrspi_comment_reply.py`)
fails: a PR **comment** does not change the branch head, so the head-SHA assertion
still passes (head unchanged). The SKILL separately requires confirming the
comment-reply envelope is `"ok": true`; a failed comment is a failure of the run's
purpose but does NOT trip the propose-only assertion. There is no transactional
coupling between the comment write and the SHA check.

**Evidence:**

```
gh pr view <DESIGN_PR> --json headRefOid --jq '.headRefOid'
If it changed, something mutated the branch — surface that loudly; the run was
supposed to be advisory only.
```

— `.claude/skills/review-design/SKILL.md:286-289`

```
1. Never mutate the design PR branch. No gt submit, no gt modify, no gh write that
   pushes commits. The only write to GitHub is the top-level PR comment in Step 7.
   The head SHA check in Step 8 is the guardrail.
```

— `.claude/skills/review-design/SKILL.md:293`

**Dependencies:** `gh pr view` (read), `qrspi_comment_reply.py` (comment write,
self-locates owner/repo, posts via `gh pr comment`). **Implicit contracts:** The
invariant is enforced by DISCIPLINE (no branch-mutating command in the SKILL),
verified by the SHA equality post-check. A comment write and a branch write are
categorically separate — only the latter moves the head SHA.

## Q11: How are the on-demand panel lens constants (`DEFAULT_REVIEW_*_LENSES`) kept distinct from the batch `DEFAULT_DESIGN_LENSES`, and what code path reads each so that a change to the shared engine cannot accidentally couple them?

**Answer:** They are SEPARATE module-level constants in
`scripts/qrspi_critics_config.py`, with explicit "do NOT collapse/couple" comments:

- Batch: `DEFAULT_DESIGN_LENSES = [completeness, internal-consistency, edge-alignment, simplicity]`; `KNOWN_DESIGN_LENSES = set(DEFAULT_DESIGN_LENSES) | {design-review}` (design-review whitelist-acceptable but default-OFF, RUS-82). Read ONLY by `resolve_design` (the batch/config resolver).
- On-demand: `DEFAULT_REVIEW_DESIGN_LENSES = (completeness, internal-consistency, edge-alignment, simplicity, design-review)` — a tuple that INCLUDES design-review; `DEFAULT_REVIEW_PLAN_LENSES = (plan-review, plan-fidelity, plan-completeness)`; `DEFAULT_REVIEW_IMPL_LENSES = (impl-review, impl-fidelity, impl-completeness)`; `KNOWN_PLAN_LENSES`/`KNOWN_IMPL_LENSES` sets.

The `DEFAULT_REVIEW_*` tuples are NOT read by any resolver function — they are
declarative constants the `/review-*` SKILLs reference by name ("sourced from
`DEFAULT_REVIEW_DESIGN_LENSES`") to know which lenses to fan out. The batch
`resolve_design` reads only `DEFAULT_DESIGN_LENSES`/`KNOWN_DESIGN_LENSES`. Because
the two sets are distinct names with no resolver crossing between them, changing
one (e.g. the batch default) cannot alter the on-demand panel.

**Evidence:**

```python
DEFAULT_DESIGN_LENSES = ["completeness", "internal-consistency", "edge-alignment", "simplicity"]
KNOWN_DESIGN_LENSES = set(DEFAULT_DESIGN_LENSES) | {"design-review"}
...
DEFAULT_REVIEW_DESIGN_LENSES = ("completeness", "internal-consistency", "edge-alignment", "simplicity", "design-review")
# ... do NOT collapse DEFAULT_REVIEW_DESIGN_LENSES into DEFAULT_DESIGN_LENSES.
```

— `scripts/qrspi_critics_config.py:62,69,84-90`

**Dependencies:** `resolve_design` reads `DEFAULT_DESIGN_LENSES`/`KNOWN_DESIGN_LENSES`;
SKILLs reference `DEFAULT_REVIEW_*` by name only. **Implicit contracts:** The
on-demand tuples are NOT config-overridable today (no resolver reads them); they
are hardcoded panels. The plan/impl lens ids are PHASE-QUALIFIED
(`plan-fidelity`, not `fidelity`) so `qrspi-<phase>-critic-<id>` resolves a
distinct agent AND the bare-lens-keyed `critic-metrics.jsonl` summary does not
collide.

## Q12: What is the existing `_test.py` coverage for `qrspi_review_synopsis` and `qrspi_critic_synthesize`, and what fixture shape do those tests feed?

**Answer:**

- `qrspi_review_synopsis_test.py` (unittest): `PartitionDecisionReadinessTests`, `LedgerRowFieldsTests`, `RenderSynopsisTests`. Helper `_verdict(lens, passed, findings=None, non_blocking=None)` builds `{lens, pass, findings[, nonBlockingNotes]}`; `_dr(blocking, answerable)` builds the decision-readiness shape. Tests assert: partition splits out decision-readiness (keeps first dup, lenient on non-list); `ledger_row_fields` axes enumerate every lens with `blockingCount = len(findings)`, nonBlockingNotes union; `render_synopsis` lists every lens with PASS/FAIL, renders the FAIL count row `| edge-alignment | FAIL | 2 |`, advisory passthrough, decision-readiness section presence/omission, terminal action.
- `qrspi_critic_synthesize_test.py` (assert-based `check()`): feeds `{pass, findings[, lens]}` dicts, JSON strings, and garbage; covers all-pass, one-fail AND, 5-lens (with design-review), dedupe, fail-closed coercion, lens-tagging, pre-structured `{text, lens}` passthrough, never-raises battery.

A "render finding TEXT" change must EXTEND `qrspi_review_synopsis_test.py`: today
NO test asserts blocking finding *text* appears in the rendered output (only counts
and nonBlockingNotes text). Fixtures already carry `findings:[str]` per lens (via
`_verdict(..., findings=["x","y"])`) — the text is in the input, just never
asserted in the output. The change would add assertions that finding strings
surface in the synopsis body.

**Evidence:**

```python
def _verdict(lens, passed, findings=None, non_blocking=None):
    v = {"lens": lens, "pass": passed, "findings": findings or []}
    if non_blocking is not None: v["nonBlockingNotes"] = non_blocking
    return v
```

— `scripts/qrspi_review_synopsis_test.py:19-23`

```python
    def test_axis_enumeration_lists_every_lens_with_pass(self):
        arr = [_verdict("completeness", True, findings=[]),
               _verdict("edge-alignment", False, findings=["x", "y"]), ...]
        out = render_synopsis(arr, None, "advance")
        ... self.assertIn("| edge-alignment | FAIL | 2 |", out)
```

— `scripts/qrspi_review_synopsis_test.py:102-116`

**Dependencies:** Both run under `scripts/run_tests.py` (subprocess per file).
**Implicit contracts:** synopsis tests use `unittest` (exit non-zero on fail);
synthesize tests use a hand-rolled `check()` + `sys.exit(1 if failures)`. Both
conventions are accepted by `run_tests.py` (it only checks exit code).

## Q13: How does `scripts/run_tests.py` discover and run sibling `_test.py` files, and what is the contract-fixture approach used elsewhere to cover the JS↔Python seam?

**Answer:** `run_tests.py` discovers every `scripts/*_test.py` (sorted basenames,
optional substring filter), runs each as its OWN subprocess `[python3, path]`
(180s timeout, timeout = fail), prints PASS/FAIL + aggregate, exits non-zero if any
fail. It is the CI regression gate (`.github/workflows/tests.yml`). Stdlib-only,
self-locating.

JS↔Python contract-seam approach (RUS-76): committed fixtures under
`scripts/fixtures/contract_seam/<seam>/*.json` (one dir per envelope kind:
`resolve`, `land`, `ordered-tickets`, `critics`, `config`, …, with `wellformed` /
`malformed` / edge variants). A Node harness `scripts/contract_seam_runner.js`
loads `qrspi-batch.js` the same way the Workflow harness does (strip the lone
`export`, async-wrap, `vm.compileFunction` with the 8 injected globals stubbed),
splices a `return {...parsers}` shim before `phase('Query')` to expose the 8
envelope parsers WITHOUT running orchestration, and is driven as a subprocess by
`qrspi_contract_fixtures_consumer_test.py` (PRODUCER side:
`qrspi_contract_fixtures_producer_test.py` asserts the Python emitters produce
matching shapes). The consumer test SKIPS (not fails) when `node` is absent. A
ported review engine would add a new `<seam>/` dir + fixtures and (if it adds a JS
parser) drive it through this runner.

**Evidence:**

```python
    names = sorted(n for n in os.listdir(scripts_dir) if n.endswith("_test.py"))
    ...
        proc = subprocess.run([python, path], capture_output=True, text=True, timeout=timeout)
        ok = proc.returncode == 0
```

— `scripts/run_tests.py:42-48,61-64`

```
CLI: node scripts/contract_seam_runner.js <parser-name> <fixture-path> [...]
For each fixture it prints one line of JSON: {"parser","fixture","result"}.
```

— `scripts/contract_seam_runner.js:28-30`

Existing critics fixture (a `qrspi_critics_config.py` envelope):

```json
{"ok": true, "phases": {"design": {"enabled": false, "maxRounds": 2, "lenses":
["completeness","internal-consistency","edge-alignment","simplicity"], ...}, ...}}
```

— `scripts/fixtures/contract_seam/critics/wellformed.json`

**Dependencies:** `contract_seam_runner.js` ↔ `qrspi-batch.js` (loaded via vm);
consumer/producer `_test.py` ↔ runner + fixtures. **Implicit contracts:** Every
test file is a standalone `python3 scripts/<name>_test.py` exiting 0/non-0.
node-less machines skip the JS seam test rather than failing. See
`docs/testing-dynamic-workflows.md` (the documented strategy).

## Q14: What logging conventions do the event-log/observability tickets (RUS-86/RUS-85/RUS-87) establish that the ported review orchestrator is expected to follow, and where are run/round/verdict events emitted today?

**Answer:** NOT FOUND — no event-log/observability ticket infrastructure exists in
the repo. Searched `grep -rwn "RUS-86\|RUS-85\|RUS-87"` across `docs/`, `scripts/`,
`.claude/`: the only matches are in `scripts/qrspi_restack.py:409` and
`scripts/qrspi_restack_test.py:184`, where RUS-85/RUS-87 are referenced as
**orphaned-worktree restack-conflict** regressions — unrelated to observability.
No `eventLog`/`event_log`/`emitEvent`/structured-event-jsonl code exists (greps
returned only incidental substring hits in `qrspi_pr_state.py` / `qrspi-batch.js`,
not an event-log facility).

The ONLY logging convention today is the injected `log(...)` global in
`qrspi-batch.js` — free-text progress lines (e.g. `log(\`  ${id}: ${name} → saved
${p.bytes}B\`)`), NOT structured run/round/verdict events. `log` is a
runtime-injected global (in the `INJECTED` list `['agent','parallel','pipeline',
'phase','log','args','budget','workflow']`), not defined in the file. The
`/review-*` SKILLs emit NO structured per-round/verdict events — they print the
synopsis and an `ok` envelope. The closest thing to a "verdict event" persisted is
the `critic-metrics.jsonl` ledger row (Q6), appended once per review run via
`qrspi_metrics_append.py`, not per round.

**Evidence:**

```js
const INJECTED = ['agent', 'parallel', 'pipeline', 'phase', 'log', 'args', 'budget', 'workflow']
```

— `scripts/contract_seam_runner.js:43`

```python
    (RUS-85/RUS-87 came back `restack_conflict` on the very first `gt checkout`). Re-provision
```

— `scripts/qrspi_restack.py:409` (the only RUS-85/87 refs — restack, not observability)

**Search queries attempted:** `RUS-86|RUS-85|RUS-87` (word) over docs/scripts/.claude;
`eventLog|event_log|emitEvent|jsonl.*event|observability`; `function log|const log`.
**Dependencies:** `log` is harness-provided. **Implicit contracts:** Today
observability = free-text `log()` lines (batch) + one JSONL ledger row per review
run. There is no run/round/verdict event schema to "follow."

## Q15: Where does the current design-only post-loop decision-readiness lens record its outcome, and how is that distinct terminal-advisory result surfaced in the posted synopsis vs. the per-lens panel results?

**Answer:** The decision-readiness lens runs POST-loop (Step 5 of
`review-design/SKILL.md`) as a non-producer Agent
(`qrspi-design-critic-decision-readiness`), returning a `DecisionReadinessVerdict`
`{lens:"decision-readiness", blockingDecisions:[{question, rationale}], answerable:[{question}]}` — NOT the `{pass, findings}` shape. It is captured in the
SKILL's `decision_readiness` variable and:

1. Fed as the SECOND positional arg to `render_synopsis(last_round_verdicts, decision_readiness, terminal_action)` — rendered in its OWN section "Decision readiness (blocking for human)" (each `blockingDecisions` item as `- <question> — <rationale>`), DISTINCT from the per-lens "Review axes" table. The section is OMITTED when decision_readiness is None or has no blockingDecisions.
2. NOT recorded as its own ledger field by `build_record` — it is excluded from the synthesize array (`partition_decision_readiness`) and does NOT appear in the `rounds`/`agreement` ledger structure (it is advisory-only, surfacing in the synopsis comment only).

It is "terminal-advisory": partitioned out of the reducer so it never drives a
`revise` round or changes the loop's terminal action. Plan/impl SKILLs pass `None`
(no decision-readiness lens; design-phase-only).

**Evidence:**

```
3. Decision readiness (blocking for human) — the DecisionReadinessVerdict's
   blockingDecisions (Decision 5); these surface to the human but trigger NO revise round.
```

— `scripts/qrspi_review_synopsis.py:126-128`

```python
    if isinstance(decision_readiness, dict):
        blocking = _as_list(decision_readiness.get("blockingDecisions"))
        if blocking:
            lines.append("### Decision readiness (blocking for human)")
            ...
                if rationale: lines.append(f"- {question} — {rationale}")
```

— `scripts/qrspi_review_synopsis.py:163-174`

```
It returns a DecisionReadinessVerdict ... NOT the {pass, findings} shape. Capture
this verdict for the synopsis (Step 7). It is NOT fed to synthesize and does NOT
change the loop's terminal action.
```

— `.claude/skills/review-design/SKILL.md:202`

**Dependencies:** Lens agent `qrspi-design-critic-decision-readiness.md`;
`partition_decision_readiness` + `render_synopsis` in `qrspi_review_synopsis.py`.
**Implicit contracts:** Every extracted open question MUST land in exactly one of
`blockingDecisions`/`answerable` (lens rule 7). The verdict is NOT persisted to the
ledger — its only durable trace is the posted PR comment. The `answerable` list is
captured but NOT rendered by `render_synopsis` (only `blockingDecisions` is shown).

---

## Discovered Patterns

- **Pure-core / harness-shell split.** Every decision/transform is a pure stdlib-only `scripts/qrspi_*.py` function with a `_test.py` sibling; the untestable I/O (agent fan-out, git/gh, file moves) lives in the SKILL `.md` step sequences and the harness-coupled `qrspi-batch.js`. Helpers fail closed (never raise) so a weak model cannot crash the pipeline — the sole exception is `build_record`, which raises `ValueError` on a non-terminal `terminalAction`.
- **Thin stdin→stdout CLIs.** `qrspi_critic_synthesize.py` and `qrspi_critic_loop.py` expose their pure functions as JSON-piping CLIs because the JS sandbox cannot run python; `qrspi_review_synopsis.py` / `qrspi_review_agreement.py` / `qrspi_review_record.py` are imported by SKILL heredocs instead (`sys.path.insert(0,"scripts")`).
- **Token-free staging paths everywhere.** `/tmp/phase-stage/<id>/…` (the `stg()` convention) is reused for review scratch (`…/review/<artifact>.md`) to avoid the documented `qrspi`-token path-mangling by weak writer models (Fix A).
- **Additive ledger fields read via `.get()`.** `axes`/`nonBlockingNotes` were grafted onto the `critic-metrics.jsonl` row additively so the existing summary reader is untouched — the established way to extend that row.
- **Explicit "do NOT couple" guard comments.** The batch vs on-demand lens constants, and the `lensModel` whitelist/default decoupling, carry in-code comments forbidding re-coupling — a recurring defensive convention.
- **Disconnected seams left for later wiring.** `lensModel` is resolvable in config + documented in agents but consumed by nothing; the on-demand `DEFAULT_REVIEW_*` tuples are declarative (no resolver reads them, so not config-overridable today). These are deliberate dormant seams.
- **Loop "last round wins" for surfacing.** The synopsis and additive ledger fields are fed only the FINAL round's pre-reduction array; the full per-round history survives only in the reduced `rounds[]` (lens/pass/findingsCount).

## Inconsistencies

- **Docstring vs reality: retired loops.** `qrspi_critic_synthesize.py`, `qrspi_critic_loop.py`, and `qrspi_critics_config.py` docstrings describe `runCriticPanelLoop`/`runCoherenceCritic` in `qrspi-batch.js` as the live caller, but those functions were RETIRED (RUS-88) and do not exist in `qrspi-batch.js` today (`runPhase` comment at qrspi-batch.js:509 confirms "the autonomous batch runs no critics or node-checks"). The only live caller is the on-demand `/review-*` SKILLs.
- **Finding text retained then discarded.** `synthesize` carefully preserves and dedupes blocking finding TEXT, and `next_action` hands it to the reviser, but `render_synopsis` discards it and shows only a per-lens count — the synopsis reader cannot see WHAT a lens flagged (the apparent gap the Q1 framing targets). nonBlockingNotes text IS rendered, making the blocking-text omission more conspicuous.
- **`answerable` captured but never rendered.** The decision-readiness verdict carries an `answerable` list (lens rule 7 requires every question to be in exactly one of the two lists), but `render_synopsis` renders only `blockingDecisions`; `answerable` has no output sink.
- **Q14 premise unsupported.** The questions reference observability tickets RUS-86/RUS-85/RUS-87 as establishing logging conventions; no such tickets/infrastructure exist in-repo (RUS-85/87 appear only as restack-conflict regression refs). A ported orchestrator has no structured event-log convention to follow — only free-text `log()` and the per-run JSONL ledger row.
- **lensModel double-declaration, zero wiring.** `critics.design.lensModel` is resolved into the config envelope AND three lens agents document a `lensModel` intent — but no code passes a model to any Agent; the `/review-*` SKILLs explicitly state "model selection is not wired in v1." Two declarations, no connecting wire.
