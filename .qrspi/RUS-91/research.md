# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-18T00:00:00Z
**Generated:** 2026-06-18T00:30:00Z
**Status:** draft

All paths below are relative to the worktree root `/workspaces/qrspi/.worktrees/RUS-91/`.

## Q1: How does each `/review-*` skill currently feed the artifact and the ticket text into its single node-validity lens, and at what point (if any) is the ticket made available to the lens prompt?

**Answer:** Each `/review-*` skill (a `SKILL.md` with `allowed-tools: Agent, Bash, Read`) drives the same shape: resolve paths → derive the phase PR → make a **scratch copy** of the artifact under `/tmp/phase-stage/<id>/review/` → run a 0..2 round loop that spawns ONE node-validity lens via the `Agent` tool. The lens is fed **named PATH inputs in the prompt body** (the skill says "no `model` override — model selection is not wired in v1"):

- `/review-design`: `DESIGN_PATH` (scratch copy), `RESEARCH_PATH`, `CODEBASE_PATH` (= `<worktreeDir>`), `QUESTIONS_PATH` (only if present). `subagent_type: qrspi-design-critic-design-review`.
- `/review-plan`: `PLAN_PATH` (scratch), `RESEARCH_PATH`, `CODEBASE_PATH`, `STRUCTURE_PATH`/`DESIGN_PATH` (only if present). `subagent_type: qrspi-plan-critic-plan-review`.
- `/review-implementation`: `IMPL_PATH` (scratch `impl-log.md`), `RESEARCH_PATH`, `CODEBASE_PATH`, `PLAN_PATH`/`STRUCTURE_PATH`/`DESIGN_PATH` (only if present). `subagent_type: qrspi-impl-critic-impl-review`.

**The ticket text is NOT supplied to the lens in any `/review-*` skill.** The lens agent definitions accept an OPTIONAL `TICKET_CONTENT_PATH` (design/impl lenses) — but no `/review-*` SKILL.md ever passes it. `/review-design` Step 4a passes only `DESIGN_PATH/RESEARCH_PATH/CODEBASE_PATH/QUESTIONS_PATH`. The `qrspi-research` firewall (ticket hidden) means the lens judges node-validity against research + real code only, never ticket intent.

**Evidence:**

```
- Prompt body carrying the named PATH inputs (no `model` override ...):
  - `DESIGN_PATH = /tmp/phase-stage/<ticket-id>/review/design.md`
  - `RESEARCH_PATH = <RESEARCH>`
  - `CODEBASE_PATH = <worktreeDir>`
  - `QUESTIONS_PATH = <QUESTIONS>` (only if the file exists)
```

— `.claude/skills/review-design/SKILL.md:88-92`

```
- `TICKET_CONTENT_PATH` — OPTIONAL. Absolute path to the ticket content ..., when supplied.
```

— `.claude/agents/qrspi-design-critic-design-review.md:17` (the lens accepts it; no skill passes it)

**Dependencies:** `qrspi_resolve.py` (path/PR-existence envelope), the `Agent` tool, scratch dir under `/tmp/phase-stage/<id>/review/`, the three lens agents under `.claude/agents/`.
**Implicit contracts:** The lens reads its inputs by PATH (absolute), opts OUT of any `DIGEST_PATH`, and returns exactly ONE `{pass, findings}` verdict object. The scratch copy — never the tracked artifact — is the subject. The plan lens does NOT even declare a `TICKET_CONTENT_PATH` input.

## Q2: How do `qrspi_critic_synthesize.py` and `qrspi_critic_loop.py` ingest a set of lens verdicts, and what is the exact input/output contract?

**Answer:** Both are pure stdlib CLIs with a `printf JSON | python3 …` stdin→stdout shim.

`qrspi_critic_synthesize.py` reads a JSON **array** of per-lens entries from stdin and prints `{"pass": bool, "findings": list}`. Reduction (the `synthesize(verdicts)` function): `pass` is True **only if the list is non-empty AND every coerced lens passed** (AND-reduction; an empty list → fail-closed `{pass:false, findings:[]}`). `findings` is the **exact-string-deduped union** in first-seen order. When an entry carries a `lens` id, its bare-string findings are wrapped `{"text": …, "lens": …}`; already-structured findings dedupe by their `text`. Every entry is coerced fail-closed via the landed `_coerce_verdict`/`parse_critic_verdict` (a malformed/non-dict entry reads as NOT-passed, contributes nothing).

`qrspi_critic_loop.py` exposes `next_action(verdicts, round, max_rounds)` (CLI flags `--round`, `--max-rounds`). It reads a JSON **array** of verdict dicts, treats the **last element** as authoritative, and prints `{"action": ..., "residual_findings": [...]}`: `converged` (latest passed), `cap_reached` (not passed AND `round+1 >= max_rounds`, surfacing latest findings), or `revise` (not passed, rounds remain). Fails closed: empty/garbled latest → NOT-passed, never `converged`.

**Evidence:**

```python
def synthesize(verdicts):
    if not isinstance(verdicts, list) or not verdicts:
        return {"pass": False, "findings": []}
    all_passed = True
    ...
        if not coerced["pass"]:
            all_passed = False
    return {"pass": all_passed, "findings": findings}
```

— `scripts/qrspi_critic_synthesize.py:76-118`

```python
    if latest["pass"]:
        return {"action": "converged", "residual_findings": []}
    if int(round) + 1 >= int(max_rounds):
        return {"action": "cap_reached", "residual_findings": list(latest["findings"])}
    return {"action": "revise", "residual_findings": list(latest["findings"])}
```

— `scripts/qrspi_critic_loop.py:109-115`

**Dependencies:** `synthesize` imports `_coerce_verdict`/`parse_critic_verdict` from `qrspi_critic_loop` (`scripts/qrspi_critic_synthesize.py:39-42`). The `/review-*` skills pipe a **one-element array** (single lens) into synthesize, then pipe the synthesized verdict (again a one-element array) into the loop CLI.
**Implicit contracts:** AND-reduction over M lenses is already implemented — adding lenses requires no synthesize change (proven by the five-lens tests, Q12). The loop's authoritative-element rule is "last element wins". Both are fail-closed: a missing/garbled verdict can never report pass/converged.

## Q3: What is the full set of lens prompts in the existing design critic panel, and how is each invoked?

**Answer:** Five design lens agents exist under `.claude/agents/`:

1. `qrspi-design-critic-completeness.md` — COMPLETENESS (does the design cover every ticket AC + answered question). tools: `Read`. Takes `TICKET_CONTENT_PATH`.
2. `qrspi-design-critic-edge-alignment.md` — EDGE-ALIGNMENT (faithful derivation of ticket intent + research; no scope drift). tools: `Read`.
3. `qrspi-design-critic-internal-consistency.md` — INTERNAL CONSISTENCY (no contradictions/dangling refs/contract mismatch). tools: `Read`.
4. `qrspi-design-critic-simplicity.md` — SIMPLICITY (no unjustified complexity). tools: `Read`.
5. `qrspi-design-critic-design-review.md` — NODE-VALIDITY (is the design materially WRONG against real code). tools: `Read, Grep` — the ONLY design lens with codebase Grep access.

The batch design **panel** is invoked by `runCriticPanelLoop(name, id, criticConfig)` in `.claude/workflows/qrspi-batch.js:727`, which fans out each configured lens id to `agentType = \`qrspi-design-critic-${lens}\`` (`qrspi-batch.js:769`). The lens set is resolved by `scripts/qrspi_critics_config.py`. The **default** panel is the four edge/fidelity lenses; `design-review` is whitelist-acceptable but DEFAULT-OFF (opt-in only). The whole batch panel is itself default-OFF (`enabled` opt-in).

**Evidence:**

```python
DEFAULT_DESIGN_LENSES = ["completeness", "internal-consistency", "edge-alignment", "simplicity"]
# design-review is whitelist-acceptable ... but DELIBERATELY NOT in DEFAULT_DESIGN_LENSES — it
# stays default-OFF ...
KNOWN_DESIGN_LENSES = set(DEFAULT_DESIGN_LENSES) | {"design-review"}
```

— `scripts/qrspi_critics_config.py:62-69`

```javascript
        const agentType = `qrspi-design-critic-${lens}`
```

— `.claude/workflows/qrspi-batch.js:769`

**Dependencies:** `runCriticPanelLoop` (JS, in qrspi-batch.js) → lens agents → `qrspi_critic_synthesize.py` → `qrspi_critic_loop.py`. Config from `qrspi_critics_config.py`.
**Implicit contracts:** Each lens id maps by convention to `qrspi-design-critic-<id>`. Only `design-review` has Grep/codebase access; the four edge lenses are `Read`-only (they judge the artifact↔upstream edge, not the code). The `/review-design` skill bypasses the batch panel and spawns ONLY the `design-review` lens directly.

## Q4: What lens prompts exist today for the plan and implementation phases, and which fidelity/completeness lenses are absent?

**Answer:** For PLAN there is exactly ONE lens: `qrspi-plan-critic-plan-review.md` (node-validity). For IMPLEMENTATION there is exactly ONE: `qrspi-impl-critic-impl-review.md` (node-validity). Both have tools `Read, Grep`. There is **no plan or impl edge/fidelity/completeness/internal-consistency/simplicity lens** — those four lens families exist ONLY for the design phase (the `qrspi-design-critic-*` set, Q3). So the ticket's premise holds: plan and impl have a node-validity lens but **no fidelity/completeness lens at all**.

A separate `qrspi-coherence-critic.md` agent exists for the implementation whole-stack coherence pass (`runCoherenceCritic` in qrspi-batch.js), but it is a cross-phase coherence critic, not a plan/impl fidelity lens, and is not part of the `/review-*` family.

**Evidence:**

```
$ ls .claude/agents/ | grep -E 'critic'
qrspi-coherence-critic.md
qrspi-design-critic-completeness.md
qrspi-design-critic-design-review.md
qrspi-design-critic-edge-alignment.md
qrspi-design-critic-internal-consistency.md
qrspi-design-critic-simplicity.md
qrspi-impl-critic-impl-review.md
qrspi-plan-critic-plan-review.md
```

— directory listing of `.claude/agents/`

**Dependencies:** plan lens consumes `PLAN_PATH/RESEARCH_PATH/CODEBASE_PATH` (+ optional STRUCTURE/DESIGN); impl lens consumes `IMPL_PATH/RESEARCH_PATH/CODEBASE_PATH` (+ optional PLAN/STRUCTURE/DESIGN).
**Implicit contracts:** A new plan/impl edge or completeness lens would need a matching `qrspi-<phase>-critic-<id>.md` agent file and would plug into `synthesize` (which already AND-reduces M lenses, Q2). `qrspi_critics_config.py` only knows DESIGN lenses (`KNOWN_DESIGN_LENSES`); there is no plan/impl lens allow-list — those phases have no multi-lens config seam yet.

## Q5: How does the whole-stack `/review` skill enumerate and compose the three per-phase lenses, and where would an upgraded multi-lens panel plug in?

**Answer:** `/review` (`.claude/skills/review/SKILL.md`) resolves the **frontier** phase via `gh pr list --state all` (dodging the partially-landed-stack misfire), then loops over every reviewed phase up to the frontier (`[design]`, `[design, plan]`, or `[design, plan, implementation]`). For each phase it runs the **identical scratch loop** the single-phase commands use, keyed by a per-phase binding table mapping phase → lens `subagent_type` → producer `subagent_type` → artifact → lens id. It posts **ONE rolled-up synopsis** with per-phase sub-sections to the frontier PR and appends **one ledger row per reviewed phase** sharing a single runId.

**Evidence:**

```
| phase | lens (`subagent_type`) | producer (`subagent_type`) | artifact | lens id |
|---|---|---|---|---|
| design | `qrspi-design-critic-design-review` | `qrspi-design` | `design.md` | `design-review` |
| plan | `qrspi-plan-critic-plan-review` | `qrspi-plan` | `plan.md` | `plan-review` |
| implementation | `qrspi-impl-critic-impl-review` | `qrspi-implement` | `impl-log.md` | `impl-review` |
```

— `.claude/skills/review/SKILL.md:91-95`

**Dependencies:** Composes the three per-phase node-validity lenses (does NOT invent a new cross-phase lens); calls `qrspi_resolve.py`, the synthesize/loop CLIs, `qrspi_review_agreement.py`/`qrspi_review_record.py`, `qrspi_metrics_append.py`, `qrspi_comment_reply.py`.
**Implicit contracts:** Per OQ3 resolution it does "per-phase sub-synopses under one comment" — **no cross-phase verdict reducer is invented** (`review/SKILL.md:192`). An upgraded multi-lens panel would plug in at the per-phase lens-spawn step (3b): instead of spawning one lens it would fan out a phase's lens set and feed the array to `synthesize` (which already AND-reduces M lenses). The single-phase `/review-*` skills' Step 4a is the symmetric plug point.

## Q6: How does each `/review-*` skill enforce the propose-only invariant today, and where is the scratch copy created and torn down?

**Answer:** Three mechanisms: (1) **scratch copy** — Step 3 copies the tracked artifact to `/tmp/phase-stage/<id>/review/<artifact>` via `mkdir -p` + `cp`; the loop and the producer-as-reviser write ONLY there (`OUTPUT_PATH` = scratch path verbatim). (2) **PR head SHA snapshot** — Step 2 records `gh pr view <PR> --json headRefOid` before the run; the final step re-reads it and asserts equality ("surface that loudly" if changed). (3) **comment-only write** — the only GitHub write is a top-level PR **comment** via `qrspi_comment_reply.py`; the Hard Rules forbid `gt submit`/`gt modify`/any `gh` branch-pushing write.

There is **no explicit teardown** of the scratch copy — `/tmp/phase-stage/<id>/review/` is created with `mkdir -p` and left in place (transient `/tmp`, never committed). Tracked artifacts under `<worktreeDir>/.qrspi/<id>/` are never touched.

**Evidence:**

```
1. **Never mutate the design PR branch.** No `gt submit`, no `gt modify`, no `gh` write that
   pushes commits. The only write to GitHub is the top-level PR **comment** in Step 7.
   The head SHA check in Step 8 is the guardrail.
2. **The loop edits only the scratch copy** under `/tmp/phase-stage/<ticket-id>/review/`, ...
```

— `.claude/skills/review-design/SKILL.md:223-224`

**Dependencies:** `gh pr view --json headRefOid` (snapshot/verify), `/tmp/phase-stage/<id>/review/` scratch dir, the producer agents (write to scratch only).
**Implicit contracts:** The invariant is enforced by **convention + a head-SHA assertion**, not by a sandbox — a misbehaving producer that wrote to a tracked path or pushed a branch would only be caught by the post-run SHA check (and by the producer being told "advisory propose-only — must NOT touch any tracked source or branch"). No automated diff of the worktree is taken.

## Q7: How is the agreement-extended ledger row computed and written per review run, and what fields does a row record?

**Answer:** Two pure helpers plus an appender. `qrspi_review_agreement.compute(panel_pass, human_decision)` reduces the panel's terminal pass and the gh `reviewDecision` to an `AgreementResult` `{panelVerdict, humanVerdict, agreement}` (`pass|fail`, normalized human verdict or null, `agree|disagree|pending`). `qrspi_review_record.build_record(phase, rounds, terminal_action, agreement)` wraps the base `CriticStepMetrics` (from `qrspi_critic_metrics.build_record`) with the `agreement` block and `mode: "on-demand-review"`. The skill then calls `qrspi_metrics_append.py --ticket --record --run-id`, which injects `ticketId`, `timestamp`, `runId` and appends one JSON line to `.worktrees/<id>/.qrspi/<id>/critic-metrics.jsonl`.

The row shape: `{phase, rounds: [{lens, pass, findingsCount}], terminalAction, agreement: {panelVerdict, humanVerdict, agreement}, mode: "on-demand-review", ticketId, timestamp, runId}`. Note `build_record` collapses each round's findings to a **findingsCount only** — the finding TEXT is NOT persisted in the ledger.

**Evidence:**

```python
    record = qrspi_critic_metrics.build_record(rounds, terminal_action, phase=phase)
    record["agreement"] = agreement
    record["mode"] = MODE_ON_DEMAND_REVIEW
    return record
```

— `scripts/qrspi_review_record.py:68-72`

```python
        rounds.append({"lens": entry.get("lens"), "pass": bool(entry.get("pass")),
                       "findingsCount": len(findings)})
```

— `scripts/qrspi_critic_metrics.py:84-89`

**Dependencies:** `qrspi_review_record` → `qrspi_critic_metrics`; agreement → `qrspi_review_agreement`; append → `qrspi_metrics_append` → `qrspi_paths.resolve_repo_root`.
**Implicit contracts:** `terminal_action` MUST be one of `{converged, cap_reached, exhausted, aborted}` — `revise` is rejected (`ValueError`, fail-closed). The ledger stores per-round pass + findingsCount + lens id but **drops finding text and quality-axis labels** — a row cannot say WHICH quality axes were checked, only which lens ran and how many findings it raised. An upgraded multi-lens/multi-phase synopsis that wants "what was reviewed vs. what remains open" would need richer per-axis fields the current row does not carry.

## Q8: On `revise`, where does each skill re-spawn the producing agent, and what is the spawn interface a non-producer/adversarial reviser would have to satisfy?

**Answer:** Each skill's Step 4d (3c in `/review`) re-spawns the **producer** (`qrspi-design` / `qrspi-plan` / `qrspi-implement`) via the `Agent` tool, instructing it to rewrite the scratch copy in place. The spawn interface (named PATH inputs in the prompt body):

- design: `TICKET_ID`, `TICKET_CONTENT_PATH` (optional), `QUESTIONS_PATH`, `RESEARCH_PATH`, `OUTPUT_PATH` (= scratch, verbatim), `TEMPLATE_PATH`, plus the round's `residual_findings`.
- plan: `TICKET_ID`, `STRUCTURE_PATH`, `DESIGN_PATH`, `OUTPUT_PATH` (scratch), `TEMPLATE_PATH`, `residual_findings`.
- impl: `TICKET_ID`, `STRUCTURE_PATH`, `PLAN_PATH`, `OUTPUT_PATH` (scratch), `residual_findings`, "advisory propose-only" flag.

**Evidence:**

```
- `subagent_type: qrspi-design`
... OUTPUT_PATH = /tmp/phase-stage/<ticket-id>/review/design.md` (the scratch copy — verbatim)
  - `TEMPLATE_PATH = <worktreeDir>/.qrspi/templates/design.md`
  - Include the round's `residual_findings` as the concrete defects to fix.
```

— `.claude/skills/review-design/SKILL.md:127-136`

**Dependencies:** The producer agents (`qrspi-design.md`, `qrspi-plan.md`, `qrspi-implement.md` under `.claude/agents/`), the `Agent` tool, the round's `residual_findings` from `qrspi_critic_loop.py`.
**Implicit contracts:** The reviser contract is "read scratch + upstream, address findings, **write improved artifact back to the SAME scratch path** (`OUTPUT_PATH` verbatim), never a tracked artifact or branch". Any replacement (a non-producer/adversarial reviser) must satisfy the same `OUTPUT_PATH`=scratch-verbatim + propose-only constraints, accept `residual_findings` as the defect list, and produce an artifact the same lens will re-judge next round. The producer is invoked by `subagent_type` only — swapping it is a one-line `subagent_type` change in the skill.

## Q9: Where in `/review-design` is the open-question pass, and what determines whether an open question is reported as resolved versus blocking?

**Answer:** Step 5 ("Post-loop open-question pass"), `.claude/skills/review-design/SKILL.md:140-147`. After the loop terminates, it spawns `qrspi-design` in a **non-strict, advisory** mode (full upstream + codebase access, NOT the strict lens) to read the final scratch design's "Open Questions" section + `RESEARCH` + real codebase and return **concise free-text answers/recommendations** per open question, for the synopsis only. The producer is told explicitly **not to write any files** — only its text reply is captured.

**There is no resolved-vs-blocking classifier.** Open-question answers are free text folded into the synopsis (Step 7: "The **open-question answers** from Step 5"). They do NOT feed the panel verdict, the agreement computation, or the ledger row. This pass is **design-phase-only** — `/review-plan` and `/review-implementation` explicitly omit it (`review-plan/SKILL.md:144`, `review-implementation/SKILL.md:147`), and `/review` omits it (`review/SKILL.md:148`).

**Evidence:**

```
## Step 5 — Post-loop open-question pass
... Spawn the producer in a **non-strict, advisory** mode ...
- Prompt body asking it to read the (final) scratch design's "Open Questions" section ...
  and return concise free-text answers/recommendations for each open question — for the
  synopsis only. Tell it explicitly **not to write any files** in this pass ...
```

— `.claude/skills/review-design/SKILL.md:140-145`

**Dependencies:** `qrspi-design` producer (advisory mode), the scratch design's "Open Questions" section, `RESEARCH`, the codebase.
**Implicit contracts:** Answers are advisory free text — nothing decides "resolved vs blocking" programmatically; the human reads the synopsis and decides. No structured open-question status is recorded.

## Q10: How does the synopsis derive its verdict text, and where is the blocking-only bar applied that dropped the real `critics_config` inaccuracy as non-blocking?

**Answer:** The verdict text is derived directly from the loop's terminal action: `converged ⇒ pass`, `cap_reached ⇒ unresolved findings` (the synopsis "panel **verdict**" line). The surviving findings are the terminal round's findings / `residual_findings`. There is **no separate synopsis-rendering script** — the skill composes a markdown file by hand (e.g. `synopsis-design.md`) and posts it; the verdict wording ("converged ⇒ pass / cap_reached ⇒ unresolved findings") is prose in the SKILL.md, not code.

The **blocking-only bar** lives in the **lens agent prompts**, not in any reducer: each node-validity lens has a "Severity bar — blocking only" section enforcing `pass:false ⟺ findings non-empty` and instructing "Do NOT emit stylistic notes ... into the structured `findings`". So a finding that the lens deems non-blocking (e.g. a `critics_config` factual inaccuracy judged non-material) is never emitted, hence `pass:true`, hence the synopsis reports "converged, pass" with zero findings. `qrspi_critic_synthesize.py` and `qrspi_critic_loop.py` apply NO severity filter — they faithfully AND-reduce whatever the lens emitted. The drop happens entirely at the lens's blocking-only judgment.

**Evidence:**

```
## Severity bar — blocking only
Emit a finding ONLY when it is **blocking** ... A sound-but-imperfect artifact ... returns
`pass:true, findings:[]`. ... The invariant is strict:
> `pass:false ⟺ findings non-empty`.
```

— `.claude/agents/qrspi-design-critic-design-review.md:44-48`

```
- The panel **verdict** (converged ⇒ pass / cap_reached ⇒ unresolved findings) and the
  terminal action.
```

— `.claude/skills/review-design/SKILL.md:194`

**Dependencies:** Lens agent (blocking-only judgment) → `qrspi_critic_synthesize.py` (AND-reduce) → `qrspi_critic_loop.py` (terminal action) → hand-composed synopsis markdown.
**Implicit contracts:** The verdict is binary (pass/unresolved) keyed only on the terminal action; the synopsis carries no "what axes were checked" structure. The blocking-only bar is the lens's own discretion — there is no machine gate that would surface a non-blocking-but-true inaccuracy. (The `critics_config` example in Q10 reflects exactly this: a real factual inaccuracy the lens judged non-blocking was silently dropped.)

## Q11: For `/review-implementation`, how is the slice stack discovered and aggregated, and what happens when slices are partially landed or a slice is missing?

**Answer:** `/review-implementation` Step 1 reads `qrspi_resolve.py`'s envelope for `slices` (ascending slice branch list) and `tip` (the stack tip = top slice). If `slices` is empty (no implementation phase) it stops. Step 2 derives the **top slice PR** via `gh pr list --head <tip> --json number,reviewDecision`; if no PR for `<tip>`, it stops. The rolled-up synopsis goes to that **single top slice PR**. The lens reviews the impl record (`impl-log.md`) anchoring "what was built across slices" plus the real source+tests under `CODEBASE_PATH` — it does NOT iterate per-slice; aggregation is "one lens over the whole worktree's implemented source, one rolled-up comment".

**Partial-land / missing-slice handling is weak.** `/review-implementation` itself does NOT use `gh pr list --state all`; it trusts `qrspi_resolve.py`'s `tip`/`slices`. The known partially-landed-stack resolver misfire (lower PRs merged, top slice open → resolver wrongly says `entry_blocked` "No design branch") is dodged ONLY in the whole-stack `/review` skill (which uses `--state all`), NOT in `/review-implementation`. A missing/landed slice would surface as a resolve-envelope anomaly the skill does not specially handle beyond "stop if slices/top-slice PR absent".

**Evidence:**

```
- `slices` — the ascending list of slice branch names ... If it is empty, there is no
  implementation to review: tell the user and stop.
- `tip` — the stack's tip branch (`<ticket-id>/slice-<maxN>`); this is the **top slice**
  whose PR receives the rolled-up synopsis.
```

— `.claude/skills/review-implementation/SKILL.md:43-44`

```
4. **Resolve the frontier with `gh pr list --state all`** so a partially-landed stack does
   not misfire (ref: Q11). Do not trust the resolver's own frontier ...
```

— `.claude/skills/review/SKILL.md:227` (this guard exists in `/review`, NOT in `/review-implementation`)

**Dependencies:** `qrspi_resolve.py` (`slices`/`tip`), `gh pr list --head <tip>`, the impl lens (one pass over the worktree).
**Implicit contracts:** Aggregation = ONE comment to the top slice PR, never per-slice. The impl lens's primary evidence is the real implemented source+tests in the worktree, not a per-slice diff. The partially-landed protection is **inconsistent** across the family (see Inconsistencies).

## Q12: What stdlib `_test.py` siblings cover the synthesize/loop CLIs, and what cases must new lens wiring keep passing?

**Answer:** `scripts/qrspi_critic_synthesize_test.py` and `scripts/qrspi_critic_loop_test.py` (assert-based via a `check()` helper, no test runner; both enumerated by `python3 scripts/run_tests.py --list`). Also relevant: `qrspi_critic_metrics_test.py`, `qrspi_review_agreement_test.py`, `qrspi_review_record_test.py`.

Synthesize cases new lens wiring must keep passing include:
- all four lenses pass ⇒ `pass:true`, no findings; all-pass with nit findings ⇒ pass:true but findings still unioned.
- **Five-lens reduction (incl. `design-review`)** ⇒ pass only when ALL five pass; fail when only `design-review` fails (AND over 5) — proves adding a lens needs no synthesize change.
- one/multiple failing lenses ⇒ pass:false, ordered deduped union; identical finding from two lenses ⇒ deduped first-seen; empty list ⇒ fail-closed; non-dict / malformed-dict / non-list-findings entries coerced; lens-id tagging `{text, lens}`; JSON-string and garbage-string entries coerced via landed parser.

Loop cases: pass@round0 ⇒ converged (no residual); fail+rounds-remain ⇒ revise (carrying findings); fail@cap ⇒ cap_reached + residual; empty list ⇒ never converged; last-element-authoritative; int-coercion of round/max_rounds; `parse_critic_verdict` fail-closed (prose-embedded, empty string).

**Evidence:**

```
check("all five lenses pass (incl. design-review) ⇒ pass:true, no findings", ...
check("five lenses, only design-review fails ⇒ pass:false with its finding (AND over 5)", ...
```

— `scripts/qrspi_critic_synthesize_test.py:60-71`

**Dependencies:** `run_tests.py` runs each `scripts/*_test.py` as a subprocess; the same suite is the CI gate (`.github/workflows/tests.yml`).
**Implicit contracts:** The AND-reduction + deduped-union + fail-closed contract is locked by tests; any new plan/impl multi-lens wiring that feeds `synthesize` must preserve these. The five-lens test is the explicit precedent that adding lenses is a no-op for the reducer.

## Q13: What artifacts exist for the RUS-86 / PR #347 regression case, and where would a regression fixture live?

**Answer:** **NOT FOUND.** There is no RUS-86 / PR #347 design artifact (the retry-events + shared-log-descoping `design.md`) anywhere under the worktree. The only references to "RUS-86", "347", "retry-event", or "shared-log" are inside the questions file itself (`.qrspi/RUS-91/questions.md`). Searches run:
- `grep -rln "RUS-86\|retry-event\|shared-log\|shared log" .qrspi docs evals results` → only `.qrspi/RUS-91/questions.md`.
- `grep -rln "347" .qrspi/RUS-91 docs` → only the questions file.
- `grep -rln "retry" evals/fixtures` → only `research_websocket.md` (unrelated websocket reconnect-retry content).

Where a regression fixture **would** live: the existing eval fixture corpus is `evals/fixtures/` (provenance-tracked per `evals/fixtures/README.md`; e.g. `design_dropped_criterion_broken.md`, `design_rest_endpoint.md` are the design-phase fixtures). The negative/adversarial design fixture pattern already present is `design_dropped_criterion_broken.md` (hand-edited, `_broken_contract`-style). A RUS-86 regression `design.md` for re-running `/review-design` would naturally be added there. **Caveat:** the eval harness is documented as a **non-functional placeholder** (CLAUDE.md: "evals/ + scripts/run_eval.py harness is a non-functional placeholder"), so a fixture would be reference/manual-only, not auto-run.

**Evidence:**

```
$ grep -rln "RUS-86\|retry-event\|shared-log\|shared log" .qrspi docs evals results
.qrspi/RUS-91/questions.md
```

— search output (only the questions artifact matches)

**Dependencies:** `evals/fixtures/` corpus + `evals/fixtures/README.md` provenance table; `evals/suite.json` (the placeholder harness).
**Implicit contracts:** Any new design fixture must add a provenance-table row in `evals/fixtures/README.md` (closed vocabulary: `generated` | `hand-edited`) and be loaded with cwd=`evals/`. No RUS-86 fixture exists to re-run today — it must be authored.

## Q14: What does a `/review-*` run emit to the PR comment and to the ledger that records which quality axes were checked?

**Answer:** **PR comment** (hand-composed markdown, posted via `qrspi_comment_reply.py --reply-mode toplevel`): a header ("Advisory <phase> review (propose-only — no branch changes)"), the panel verdict (pass / unresolved findings) + terminal action, the surviving findings (each citing the artifact claim + the real source location), the agreement line, and (design only) the open-question answers. **Ledger** (one JSONL line per phase via `qrspi_metrics_append.py` to `.worktrees/<id>/.qrspi/<id>/critic-metrics.jsonl`): `{phase, rounds:[{lens, pass, findingsCount}], terminalAction, agreement:{panelVerdict, humanVerdict, agreement}, mode:"on-demand-review", ticketId, timestamp, runId}`.

**Neither the comment nor the ledger records "which quality axes were checked".** The ledger carries the **lens id** per round (e.g. `"design-review"`) and a findingsCount — but the node-validity lens covers many axes (codebase-claim validity, architectural soundness, correctness, failure modes, operability, testability, security/performance) under one id, so the ledger cannot say which axes were exercised vs. clean. The comment lists only emitted (blocking) findings; a clean pass shows zero findings and no statement of what was examined-but-fine. There is **no "honest verdict" field** stating reviewed-vs-open axes today.

**Evidence:**

```
- The panel **verdict** (converged ⇒ pass / cap_reached ⇒ unresolved findings) ...
- The surviving **findings** ... each as a bullet citing the design claim and the real
  source location the lens indicted.
- The **open-question answers** from Step 5.
- The **agreement** line ...
```

— `.claude/skills/review-design/SKILL.md:194-197`

**Dependencies:** `qrspi_comment_reply.py` (comment), `qrspi_review_record.py`/`qrspi_critic_metrics.py`/`qrspi_metrics_append.py` (ledger).
**Implicit contracts:** Observability is finding-centric and lens-id-centric — a single lens id stands in for all its axes. An "honest verdict" enumerating checked-vs-open axes would require new per-axis fields neither artifact currently carries (findingsCount collapses finding text; there is no axis enumeration).

## Q15: How can a reviewer/operator confirm the propose-only invariant held — where is the before/after PR head SHA observable and which write operations are logged?

**Answer:** The head SHA is observable via `gh pr view <PR> --json headRefOid --jq '.headRefOid'`, captured in Step 2 (before) and re-read in the final step (after); the skill asserts equality and "surface that loudly" on mismatch. This is a **runtime, in-session assertion** — the SHAs are printed to the agent's transcript, NOT persisted to the ledger or any durable log. An operator confirms the invariant by (a) reading the run transcript's two `headRefOid` reads, or (b) independently running `gh pr view <PR> --json headRefOid` and comparing to the pre-run value, or (c) confirming the PR's commit history is unchanged.

The only **logged/durable write** is the top-level PR comment (whose creation `qrspi_comment_reply.py` confirms with an `"ok": true` envelope; `gh pr comment` prints a URL, so `replyId` is None but `ok` is true). There is no automated worktree-diff check and no persisted before/after SHA record — the guarantee rests on the SKILL.md hard rules + the in-session SHA assertion + the absence of any `gt submit`/`gt modify` call.

**Evidence:**

```
## Step 8 — Confirm the propose-only invariant
Re-read the PR head SHA and assert it equals the value captured in Step 2:
```bash
gh pr view <DESIGN_PR> --json headRefOid --jq '.headRefOid'
```
If it changed, something mutated the branch — surface that loudly ...
```

— `.claude/skills/review-design/SKILL.md:211-219`

```python
        # gh pr comment prints a URL, not JSON: success with no numeric reply id.
```

— `scripts/qrspi_comment_reply.py:111`

**Dependencies:** `gh pr view --json headRefOid` (SHA observation), `qrspi_comment_reply.py` (the one logged write, `ok:true` envelope).
**Implicit contracts:** The invariant is verified by an ephemeral in-transcript SHA comparison, not a durable audit record. The single sanctioned GitHub write is the comment; everything else is forbidden by hard rule, not by a sandbox. A run leaves no persisted "head SHA unchanged" proof beyond the transcript.

---

## Discovered Patterns

- **Three-layer separation:** every `/review-*` skill is thin orchestration (SKILL.md prose) over (1) adversarial lens **agents** (`.claude/agents/qrspi-*-critic-*.md`, the only codebase-aware reasoning), (2) pure stdlib **reducer CLIs** (`qrspi_critic_synthesize.py`, `qrspi_critic_loop.py`, `qrspi_critic_metrics.py`, `qrspi_review_agreement.py`, `qrspi_review_record.py` — all fail-closed, all `_test.py`-covered), and (3) deterministic **IO scripts** (`qrspi_resolve.py`, `qrspi_metrics_append.py`, `qrspi_comment_reply.py`). The "untestable" surface is pushed into the lens prompts + the JS orchestrator; everything reducible is a tested pure function.
- **Self-locating scripts:** every `scripts/*.py` derives the repo root from `__file__` (`Path(__file__).resolve().parents[1]`), never cwd, so a worker types only the invocation. The `qrspi` token in paths is computed by scripts, never typed by a model (Fix A discipline).
- **Fail-closed everywhere:** empty/garbled verdicts read as NOT-passed; missing human review → `agreement:"pending"` (never false disagreement); invalid `terminalAction` → `ValueError`; `revise` is non-terminal and rejected by the record builder.
- **`design-review` is the only "node-validity-with-Grep" lens family** replicated per phase (design/plan/impl). The four design edge/fidelity lenses (`Read`-only) have NO plan/impl counterpart — the asymmetry the ticket targets.
- **Blocking-only severity lives in the lens prompt, not in code** — the reducers never filter by severity; whatever the lens judges non-blocking is simply never emitted.

## Inconsistencies

- **Partially-landed protection is inconsistent across the `/review-*` family.** Only `/review` (the whole-stack skill) uses `gh pr list --state all` to dodge the partially-landed-stack resolver misfire (`review/SKILL.md:227`). `/review-implementation` trusts `qrspi_resolve.py`'s `tip`/`slices` and uses `gh pr list --head <tip>` (no `--state all`), so a stack with lower slices already merged could misfire there (Q11). The MEMORY note "resolver: partially-landed stack bug" documents this hazard generally.
- **The node-validity lens accepts `TICKET_CONTENT_PATH` but no `/review-*` skill ever passes it** (Q1). The design/impl lens agents declare the optional input (`qrspi-design-critic-design-review.md:17`), yet every skill's lens-spawn step omits it — so node-validity is judged against research + code only, never ticket intent, even though the lens is wired to accept it.
- **`design.md:76` is documented as stale** in `qrspi_critic_metrics.py:36-38`: that design listed only `converged/cap_reached` terminal actions, while the faithful set is the four-value `{converged, cap_reached, exhausted, aborted}` (flagged in `structure.md:19`). The code is authoritative; the design comment is the inconsistency.
- **Ledger collapses finding text to a count** (`qrspi_critic_metrics.build_record`, Q7/Q14): the row stores `findingsCount` and a single lens id, losing both the finding text and any per-quality-axis breakdown — so the durable record cannot answer "which axes were checked" or reproduce what was indicted, only how many findings a lens raised.
- **Propose-only proof is ephemeral** (Q15): the before/after head-SHA comparison lives only in the run transcript; nothing durable records that the branch was untouched, despite the invariant being the skill's central safety claim.
