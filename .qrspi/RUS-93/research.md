# Research — Codebase Map

**Questions source:** questions.md @ /workspaces/qrspi/.worktrees/RUS-93/.qrspi/RUS-93/questions.md
**Generated:** 2026-06-18T00:00:00Z
**Status:** draft

> Scope note: the on-demand `/review-*` family is currently **hand-executed prose
> procedures** in four `SKILL.md` files that shell out to pure-Python helpers in
> `scripts/`. There is **no** orchestrator (`.js` workflow) for `/review-*` today —
> the loop, fan-out, and rendering are all narrated steps the model performs.
> `runCriticPanelLoop`/`runCoherenceCritic` (the autonomous in-pipeline critic glue
> the helpers were originally built for) **no longer exist** in `qrspi-batch.js`
> (the autonomous batch runs no in-pipeline critics — see `docs/testing-dynamic-workflows.md:200-201`).

## Q1: How does the JSON produced by the panel lenses flow from the fan-out `Agent` lenses through the `python3` heredocs to the rendered synopsis comment, and at which step does per-lens blocking finding text become available versus collapsed to a count?

**Answer:** The flow per round is: (1) the model fans out N lens `Agent`s, each returning one `LensVerdict` `{lens, pass, findings, nonBlockingNotes?}`; the model hand-assembles these into a **pre-reduction verdict array** (the model is told to "Keep this full pre-reduction array"). (2) A heredoc pipes that array through `partition_decision_readiness()` then `qrspi_critic_synthesize.synthesize()`, producing the round's reduced `{pass, findings}` (findings = union of blocking findings). (3) A second call pipes `[{pass, findings}]` into `qrspi_critic_loop.py --round R --max-rounds M` to get the terminal `action`. (4) Post-loop, the **final round's pre-reduction array** is fed to `render_synopsis()`.

The key data-loss point: `render_synopsis()` emits only a **PASS/FAIL label and a blocking finding COUNT per lens** — never the finding TEXT. The blocking finding text exists in the pre-reduction array and survives into `synthesize().findings` (used as `residual_findings` for the reviser), but it is **collapsed to `_blocking_count(verdict)` = `len(findings)`** at the synopsis step. So the human reviewer's posted comment shows counts, not the actual finding strings.

**Evidence:**

```python
def render_synopsis(verdict_array, decision_readiness, terminal_action):
    ...
    lines.append("| Lens | Verdict | Blocking findings |")
    for verdict in verdict_array:
        lens = verdict.get("lens")
        passed = bool(verdict.get("pass"))
        count = _blocking_count(verdict)   # len(findings) — TEXT dropped here
        verdict_label = "PASS" if passed else "FAIL"
        lines.append(f"| {lens} | {verdict_label} | {count} |")
```

— `scripts/qrspi_review_synopsis.py:116-147`

The SKILL render steps (heredoc → `synopsis-*.md` → `qrspi_comment_reply.py`):

— `.claude/skills/review-design/SKILL.md:247-279` (Step 7); `.claude/skills/review-plan/SKILL.md` Step 6; `.claude/skills/review-implementation/SKILL.md` Step 6; `.claude/skills/review/SKILL.md:240-283` (Step 4)

**Dependencies:** SKILL prose (producer of arrays) → `qrspi_review_synopsis.partition_decision_readiness`/`render_synopsis` → `qrspi_critic_synthesize.synthesize` → `qrspi_critic_loop.next_action` (via CLI) → `qrspi_comment_reply.py` (the only GitHub write).
**Implicit contracts:** Each lens verdict MUST carry a `lens` key (the model tags them); `findings` is the blocking channel, `nonBlockingNotes` the advisory channel. The synopsis renderer treats a missing `findings` as a 0 count (lenient `_as_list`). The finding TEXT is only surfaced to the reviser, never to the human comment.

## Q2: What is the data shape returned by `qrspi_critic_synthesize` for each lens (does it carry the finding text, severity, and blocking flag, or only aggregate counts), and where is that structure consumed downstream?

**Answer:** `synthesize(verdicts)` returns one reduced dict `{"pass": bool, "findings": list}` — NOT per-lens. `pass` is True only if the verdict list is non-empty AND every coerced lens passed (AND-over-all, fail-closed on empty). `findings` is the **exact-string-deduped union** of every lens's findings, preserving first-seen order, carrying the full finding **text** (not counts, no severity field). There is no severity dimension — "blocking" is implicit (everything in `findings` is blocking; `nonBlockingNotes` is a separate channel the synthesizer ignores). Optional lens-tagging: a bare-string finding from a lens carrying a `lens` id is wrapped as `{"text": finding, "lens": lens}`; already-structured findings pass through unchanged and dedupe on their `text`.

Downstream: the reduced `{pass, findings}` is consumed by `qrspi_critic_loop.next_action` (via the SKILL's second heredoc) — `findings` becomes `residual_findings` handed to `qrspi-critic-reviser`. The reduced view is deliberately **NOT** used for the synopsis (the SKILLs feed the synopsis the pre-reduction array instead, because the reduced view loses per-lens identity).

**Evidence:**

```python
def synthesize(verdicts):
    if not isinstance(verdicts, list) or not verdicts:
        return {"pass": False, "findings": []}
    all_passed = True
    findings = []
    seen = set()
    for entry in verdicts:
        coerced = _coerce_lens(entry)
        if not coerced["pass"]:
            all_passed = False
        ...
    return {"pass": all_passed, "findings": findings}
```

— `scripts/qrspi_critic_synthesize.py:76-118`

Test confirms shape + behaviors (AND, dedupe, lens-tagging, fail-closed):
— `scripts/qrspi_critic_synthesize_test.py:40-169` (assert-based via a `check()` helper, no unittest runner)

**Dependencies:** imports `_coerce_verdict` / `parse_critic_verdict` from `qrspi_critic_loop.py` (the LANDED coercion, reused not re-implemented). Also exposes a thin stdin→stdout CLI.
**Implicit contracts:** A garbled/empty entry fails closed to NOT-passed and contributes no findings. Empty input list ⇒ `{pass:False}` (no lens attested). Severity is **not modeled** — only blocking text in `findings`. The reducer is the wrong source for an axis-enumerated synopsis (it has no per-lens output) — that is why the SKILLs keep the pre-reduction array.

## Q3: How does the artifact get scratch-copied at the start of a run, and where does the reviser (`qrspi-critic-reviser`) read from and write to during a revise round?

**Answer:** The scratch-copy and revise loop are **not in a Python module** — they are hand-executed SKILL steps. There is NO `scripts/qrspi_critic_loop.py` scratch-copy (the question's "Target" mis-attributes it: `qrspi_critic_loop.py` is only the pure `next_action`/`parse_critic_verdict` decision core, no scratch/IO). The scratch copy is a literal `cp` in the SKILL:

```bash
mkdir -p /tmp/phase-stage/<ticket-id>/review
cp "<DESIGN>" /tmp/phase-stage/<ticket-id>/review/design.md
```
— `.claude/skills/review-design/SKILL.md:84-86` (Step 3); analogous in review-plan/impl/review.

The reviser (`qrspi-critic-reviser`, the **one shared phase-parameterized non-producer**) is spawned via `Agent` on a `revise` action. It READS its current `OUTPUT_PATH` (the scratch copy) + supplied upstream inputs (`RESEARCH_PATH`, `CODEBASE_PATH`, etc.) + `RESIDUAL_FINDINGS`, and WRITES **only** to `OUTPUT_PATH` — the same throwaway scratch path, verbatim, never a tracked file or branch. Then the loop continues against the rewritten scratch copy.

**Evidence:**

```
- `OUTPUT_PATH` — absolute scratch path of the artifact you must rewrite **in place, verbatim**
  (e.g. `/tmp/phase-stage/<ticket-id>/review/design.md`). This is the ONLY path you may Write.
- `RESIDUAL_FINDINGS` — the list of blocking node-validity / fidelity findings from the round's
  reduced verdict. ... **Decision-readiness items are NOT in this list**
```
— `.claude/agents/qrspi-critic-reviser.md:25-34` (tools: `Read, Grep, Write`)

Spawn contract (subagent_type, PHASE, OUTPUT_PATH, RESIDUAL_FINDINGS, TEMPLATE_PATH):
— `.claude/skills/review-design/SKILL.md:170-186` (Step 4d)

**Dependencies:** The reviser is shared by `/review-design`, `/review-plan`, `/review-implementation`, `/review`, parameterized by `PHASE ∈ {design, plan, impl}`. No Python module mediates the loop — the model drives rounds.
**Implicit contracts:** Propose-only: the reviser may write exactly one path (the scratch copy). Decision-readiness findings never reach it. The loop must edit only `/tmp/phase-stage/<ticket-id>/review/`, never `<worktreeDir>/.qrspi/<ticket-id>/*.md`.

## Q4: What are the current function signatures of the tested Python helpers, and which already accept finding-level detail vs only counts?

**Answer:**

- `qrspi_critic_synthesize.synthesize(verdicts: list) -> {"pass": bool, "findings": list}` — accepts per-lens verdicts with **full finding text**; emits reduced text union. (`scripts/qrspi_critic_synthesize.py:76`)
- `qrspi_critic_loop.parse_critic_verdict(text: str) -> {"pass": bool, "findings": list}` and `next_action(verdicts: list, round: int, max_rounds: int) -> {"action": str, "residual_findings": list}` — `next_action` carries **finding text** through as `residual_findings`. (`scripts/qrspi_critic_loop.py:53, 84`)
- `qrspi_review_synopsis.partition_decision_readiness(verdict_array) -> (panel_array, decision_readiness_verdict|None)`; `ledger_row_fields(verdict_array) -> {"axes":[{lens, pass, blockingCount}], "nonBlockingNotes":[...]}`; `render_synopsis(verdict_array, decision_readiness, terminal_action) -> str`. These accept the **full pre-reduction array** but **emit only `blockingCount` / PASS-FAIL** — finding text is dropped (count only). (`scripts/qrspi_review_synopsis.py:60, 84, 116`)
- `qrspi_review_agreement.compute(panel_pass, human_decision) -> {"panelVerdict", "humanVerdict", "agreement"}`. No finding detail (verdict-level only). (`scripts/qrspi_review_agreement.py:59`)
- `qrspi_critics_config.resolve_critics(critics) -> (phases, warnings)`; `resolve_design(cfg, warnings)`; `resolve_implementation(cfg)`; `default_phases()`. Config-only (no findings). (`scripts/qrspi_critics_config.py:143, 215, 232, 247`)
- Supporting: `qrspi_review_record.build_record(phase, rounds, terminal_action, agreement) -> ReviewRecord` and `qrspi_critic_metrics.build_record(verdicts, terminalAction, usage=None, phase=None) -> CriticStepMetrics` — the latter reduces each round verdict to `{lens, pass, findingsCount}` (**count only**, text dropped at ledger time). (`scripts/qrspi_review_record.py:48`, `scripts/qrspi_critic_metrics.py:54`)

**Answer to the finding-detail axis:** `synthesize`, `next_action`/`parse_critic_verdict` carry full finding TEXT. `render_synopsis`/`ledger_row_fields` (synopsis + ledger axes) and `qrspi_critic_metrics.build_record` (ledger rounds) reduce to COUNTS only. `compute` and the config resolver carry no finding detail.

**Evidence:**

```python
def build_record(verdicts, terminalAction, usage=None, phase=None):
    ...
    for entry in (verdicts or []):
        findings = entry.get("findings") or []
        rounds.append({"lens": entry.get("lens"), "pass": bool(entry.get("pass")),
                       "findingsCount": len(findings)})   # text → count
```
— `scripts/qrspi_critic_metrics.py:54-89`

**Dependencies:** `qrspi_review_record` → `qrspi_critic_metrics.build_record` (reuses base shape). `qrspi_critic_synthesize` → `qrspi_critic_loop`. All are pure, stdlib-only, self-locating.
**Implicit contracts:** Every helper is fail-closed and additive. `ledger_row_fields()` fields are OPTIONAL/additive so `qrspi_critic_summary.summarize` (which reads via `.get()`) is unaffected. `build_record` rejects a non-terminal `revise` (ValueError).

## Q5: What constants and configuration distinguish the on-demand review panels (`DEFAULT_REVIEW_*_LENSES`) from the batch panels (`DEFAULT_DESIGN_LENSES`), and where are each defined and referenced?

**Answer:** All live in `scripts/qrspi_critics_config.py`. The **batch** panel is `DEFAULT_DESIGN_LENSES = ["completeness", "internal-consistency", "edge-alignment", "simplicity"]` (4 edge-fidelity lenses; `design-review` is deliberately EXCLUDED — whitelist-acceptable via config but default-OFF, the RUS-82 decoupling). The **on-demand** panels are separate ordered tuples: `DEFAULT_REVIEW_DESIGN_LENSES` = the four edge lenses PLUS `design-review` (5 lenses); `DEFAULT_REVIEW_PLAN_LENSES = ("plan-review", "plan-fidelity", "plan-completeness")`; `DEFAULT_REVIEW_IMPL_LENSES = ("impl-review", "impl-fidelity", "impl-completeness")`. Plan/impl lens ids are phase-qualified so `qrspi-<phase>-critic-<id>` resolves distinctly and they don't collide in the bare-lens-keyed metrics summary.

Critically, these `DEFAULT_REVIEW_*_LENSES` constants are **referenced only narratively in the SKILL prose** (the binding tables) — no Python or JS code reads them at runtime (the loop is hand-executed). `qrspi_critics_config.py`'s own `resolve_*` functions consume only `DEFAULT_DESIGN_LENSES`/`KNOWN_DESIGN_LENSES` (the batch set), NOT the `DEFAULT_REVIEW_*` constants.

**Evidence:**

```python
DEFAULT_DESIGN_LENSES = ["completeness", "internal-consistency", "edge-alignment", "simplicity"]
KNOWN_DESIGN_LENSES = set(DEFAULT_DESIGN_LENSES) | {"design-review"}
...
DEFAULT_REVIEW_DESIGN_LENSES = ("completeness","internal-consistency","edge-alignment","simplicity","design-review")
DEFAULT_REVIEW_PLAN_LENSES = ("plan-review","plan-fidelity","plan-completeness")
DEFAULT_REVIEW_IMPL_LENSES = ("impl-review","impl-fidelity","impl-completeness")
```
— `scripts/qrspi_critics_config.py:62-108`

SKILL references (binding tables citing the constants by name):
— `.claude/skills/review-design/SKILL.md:104-112`; `.claude/skills/review/SKILL.md:108-114`

**Dependencies:** `resolve_design` filters config-supplied lenses against `KNOWN_DESIGN_LENSES`; SKILLs map lens id → agent `qrspi-<phase>-critic-<id>`.
**Implicit contracts:** Do NOT collapse `DEFAULT_REVIEW_DESIGN_LENSES` into `DEFAULT_DESIGN_LENSES` (explicit "Do NOT re-couple" note). The on-demand panels are NOT config-driven today — they are fixed tuples the prose narrates; only `maxRounds` is read from config (Q9).

## Q6: How does the `lensModel` seam currently exist in the agent/lens definitions — is there a documented-but-unwired parameter, and what is the call path that selects the model a lens runs under?

**Answer:** `lensModel` is a **documented-but-deliberately-unwired** seam. Two facets:

1. In `qrspi_critics_config.resolve_design`, `lensModel` is a recognized config key: if config supplies a non-empty string, it lands on the resolved design envelope (key OMITTED entirely otherwise). But this resolved value is consumed by **nothing** today — no SKILL or JS reads it (the design panel that would have consumed it, `runCriticPanelLoop`, is gone). (`scripts/qrspi_critics_config.py:205-211`)

2. In the lens agent definitions, model selection is **NOT wired via any frontmatter key**. The `design-review` lens documents the intent as a doc-note only: "intended to run under the strongest available model (Opus-tier)... It is NOT wired via any `lensModel`/model frontmatter key — the lens inherits the panel's session model at runtime, and the panel-wide model seam is out of scope for this lens (ref: RUS-82 design AC7)."

The SKILLs explicitly say "no `model` override — model selection is not wired in v1" at the fan-out step. So the call path is: a lens runs under whatever **session/default model** the spawning command inherits; there is no per-lens model selection in effect.

**Evidence:**

```
This lens does the panel's hardest reasoning (adversarial validity against real source) and is
intended to run under the strongest available model (Opus-tier). That intent is recorded here as a
**doc note only**: it is NOT wired via any `lensModel`/model frontmatter key — the lens inherits
the panel's session model at runtime, and the panel-wide model seam is out of scope for this lens
```
— `.claude/agents/qrspi-design-critic-design-review.md:72-74`

```python
    lens_model = cfg.get("lensModel")
    if isinstance(lens_model, str) and lens_model.strip():
        result["lensModel"] = lens_model
```
— `scripts/qrspi_critics_config.py:208-211`

SKILL "no model override" instruction:
— `.claude/skills/review-design/SKILL.md:114` ("no `model` override — model selection is not wired in v1")

**Dependencies:** `resolve_design` (producer of the unconsumed `lensModel`) → nothing. The Agent fan-out → session-inherited model.
**Implicit contracts:** The frontmatter for a lens agent (`claude: tools: Read, Grep`) carries NO model field — adding one is the unbuilt seam. A future wiring would have to thread `lensModel` from the config envelope into each `Agent` spawn's model parameter, which the prose-driven loop has no mechanism for today.

## Q7: How is the `mode:"on-demand-review"` ledger row constructed and appended, and what fields (including agreement) does it record per run?

**Answer:** The row is built by `qrspi_review_record.build_record(phase, rounds, terminal_action, agreement)`: it calls `qrspi_critic_metrics.build_record(rounds, terminal_action, phase=phase)` for the base `{phase, rounds:[{lens, pass, findingsCount}], terminalAction}`, then sets `record["agreement"] = agreement` (the `AgreementResult` from `qrspi_review_agreement.compute`) and `record["mode"] = "on-demand-review"`. The SKILL then MERGES the additive `ledger_row_fields()` output (`axes` + `nonBlockingNotes`) onto the dict. So the appended row carries: `phase`, `rounds` (per-lens, count-only), `terminalAction`, `agreement` block, `mode`, `axes`, `nonBlockingNotes`.

Appending is via `scripts/qrspi_metrics_append.py --ticket --record --run-id`, which injects `ticketId`, `timestamp` (UTC now), and `runId`, then appends one JSON line to the per-ticket `critic-metrics.jsonl`, failing closed if the write is empty.

**Evidence:**

```python
def build_record(phase, rounds, terminal_action, agreement):
    record = qrspi_critic_metrics.build_record(rounds, terminal_action, phase=phase)
    record["agreement"] = agreement
    record["mode"] = MODE_ON_DEMAND_REVIEW   # "on-demand-review"
    return record
```
— `scripts/qrspi_review_record.py:48-72`

Append envelope injection:
```python
    line["ticketId"] = ticket
    line["timestamp"] = timestamp
    line["runId"] = run_id
```
— `scripts/qrspi_metrics_append.py:76-78`

SKILL build+merge+append step:
— `.claude/skills/review-design/SKILL.md:204-245` (Step 6)

**Dependencies:** `qrspi_review_record` → `qrspi_critic_metrics` (base) + `qrspi_review_agreement` (agreement) + `qrspi_review_synopsis.ledger_row_fields` (additive axes). Append → `qrspi_metrics_append.py` → `critic-metrics.jsonl`. Read side: `qrspi_critic_summary.summarize` (buckets per-lens dissent on `rnd["lens"]`).
**Implicit contracts:** `terminal_action` MUST be terminal (`converged`/`cap_reached`/`exhausted`/`aborted`) — `revise` raises ValueError. `rounds` must be N-lenses × R-rounds (one entry per lens per round) so the per-lens summary buckets correctly. `agreement`/`mode`/`axes`/`nonBlockingNotes` are additive — readers use `.get()`.

## Q8: Where and how is the panel↔human agreement value computed, and what makes it structurally always `pending`?

**Answer:** Agreement is computed by `qrspi_review_agreement.compute(panel_pass, human_decision)`. `panel_pass` = the loop's terminal round pass (`True` on `converged`, `False` on `cap_reached`). `human_decision` = the PR's GitHub `reviewDecision` string, read in the SKILL via `gh pr list --head <id>/design --json reviewDecision`. `_derive_agreement`: a `None` human verdict OR `"commented"` → `"pending"`; `pass + approved` or `fail + changes_requested` → `"agree"`; otherwise `"disagree"`.

It is **structurally always `pending`** in practice because the `/review-*` commands are advisory and typically run **before** any human review decision exists — `gh` returns `reviewDecision: null` (or `COMMENTED`, also → pending) for a not-yet-decided PR, and a `null` normalizes to `humanVerdict=None` → `agreement="pending"` ("never a false disagreement"). There IS a real code path (`compute`) that reads `reviewDecision` and yields `agree`/`disagree` — but only once a human has formally `APPROVED`/`CHANGES_REQUESTED` the PR, which the advisory review usually precedes. So the structural cause is **timing** (the human decision rarely exists at review-run time), not a missing code path.

**Evidence:**

```python
def _derive_agreement(panel_pass, human_verdict):
    if human_verdict is None or human_verdict == HUMAN_COMMENTED:
        return PENDING
    if panel_pass and human_verdict == HUMAN_APPROVED:
        return AGREE
    if (not panel_pass) and human_verdict == HUMAN_CHANGES_REQUESTED:
        return AGREE
    return DISAGREE
```
— `scripts/qrspi_review_agreement.py:89-102`

SKILL reads `reviewDecision` from the PR (often null at advisory-run time):
— `.claude/skills/review-design/SKILL.md:64-72` (Step 2)

Tests pin pending-on-None and agree/disagree on decided decisions:
— `scripts/qrspi_review_agreement_test.py:16-45`

**Dependencies:** SKILL (`gh pr list ... reviewDecision`) → `compute`. Output embeds into the ReviewRecord (Q7).
**Implicit contracts:** A missing/unknown/`COMMENTED` decision is "no decisive verdict" → pending, never an error or false disagreement. Case-insensitive, whitespace-tolerant, non-string tolerated. The `AgreementResult` keys are exactly `{panelVerdict, humanVerdict, agreement}`.

## Q9: How is the loop round counter and convergence/cap state (`next_action` converge/revise/cap) tracked across rounds `0..MAX-1`, and where does the MAX bound come from?

**Answer:** The round counter `r` is tracked **by the model** in the hand-executed SKILL loop (a narrated `for round r starting at 0`), not by any Python state — `next_action(verdicts, round, max_rounds)` is **stateless**: the SKILL passes the current `round` index and the `max_rounds` cap on each call via `--round <r> --max-rounds <MAX_ROUNDS>`. The decision: `latest.pass` → `converged`; else if `round + 1 >= max_rounds` → `cap_reached` (surfacing residual findings); else → `revise`.

The MAX bound's SOURCE **differs by command** (an inconsistency, see Inconsistencies): `/review-design` resolves `MAX_ROUNDS` from config via `qrspi_critics_config.py` → `.phases.design.maxRounds` (default 2, the `DEFAULT_MAX_ROUNDS` source default). But `/review-plan` and `/review-implementation` **hardcode** `--max-rounds 3` ("The cap is 3 rounds"). `/review` (whole-stack) also hardcodes `0..2` / `--max-rounds 3`.

**Evidence:**

```python
def next_action(verdicts, round, max_rounds):
    latest = _coerce_verdict(verdicts[-1]) if isinstance(verdicts, list) and verdicts else {"pass": False, "findings": []}
    if latest["pass"]:
        return {"action": "converged", "residual_findings": []}
    if int(round) + 1 >= int(max_rounds):
        return {"action": "cap_reached", "residual_findings": list(latest["findings"])}
    return {"action": "revise", "residual_findings": list(latest["findings"])}
```
— `scripts/qrspi_critic_loop.py:84-115`

`DEFAULT_MAX_ROUNDS = 2` and design reads it from config:
— `scripts/qrspi_critics_config.py:56`; `.claude/skills/review-design/SKILL.md:54-62` (Step 1b)

Hardcoded `3` in plan/impl/review:
— `.claude/skills/review-plan/SKILL.md:90,147`; `.claude/skills/review-implementation/SKILL.md:93,151`; `.claude/skills/review/SKILL.md:129,164`

Tests cover converge-at-0, revise→converge, cap_reached, empty-list-fail-closed:
— `scripts/qrspi_critic_loop_test.py:40-72`

**Dependencies:** SKILL prose (round counter + cap source) → `next_action` (stateless decision). Design cap → `qrspi_critics_config`.
**Implicit contracts:** Loop runs rounds `0 .. MAX_ROUNDS-1`. `next_action` is stateless — all state (round index, accumulated `rounds[]`, the pre-reduction arrays) lives in the model's working memory across hand-executed steps. A garbled/empty verdict can never report `converged` (fail-closed).

## Q10: What does the synopsis currently render when a review is non-converged (does it emit any finding text, or only per-lens counts), and how does it render when a lens returns zero findings?

**Answer:** `render_synopsis` renders the **same structure regardless of convergence** — the terminal action (`converged`/`cap_reached`/etc.) is printed only as a trailing `**Terminal action:** <action>` line; it does NOT change the body. The body is always: (1) a "Review axes" Markdown table with one row per lens (`| <lens> | PASS|FAIL | <count> |`), (2) an optional "Advisory (non-blocking)" section (union of `nonBlockingNotes`), (3) an optional "Decision readiness (blocking for human)" section (design only). It emits **only per-lens blocking COUNTS, never the finding text** — even when non-converged with surviving (`cap_reached`) findings, the human sees a count, not the strings. A lens with zero findings renders as `| <lens> | PASS | 0 |` (and FAIL with 0 is structurally possible but the lens contract forbids it — `pass:false ⟺ findings non-empty`). The advisory/decision-readiness sections are omitted entirely when empty.

**Evidence:**

```python
    # 4. Terminal action
    lines.append(f"**Terminal action:** {terminal_action}")
    return "\n".join(lines)
```
— `scripts/qrspi_review_synopsis.py:179-182` (terminal action is the only convergence-dependent output; body is count-only)

Test asserting count-only rendering (`| edge-alignment | FAIL | 2 |`) and zero-note omission:
— `scripts/qrspi_review_synopsis_test.py:102-148`

**Dependencies:** SKILL feeds the **final round's pre-reduction array** (so a FAIL lens still appears as a row even on cap_reached). `ledger_row_fields` mirrors the same count-only `blockingCount`.
**Implicit contracts:** `_blocking_count` = `len(findings)`; `nonBlockingNotes` is NOT counted as blocking. A non-dict array element is skipped. The renderer never raises and performs no IO. The cap_reached residual finding TEXT is available to the SKILL (from synthesize) but is NOT placed in the synopsis — a real information-loss point for the "is X wrong?" goal.

## Q11: How does the existing flow assert the PR head SHA is unchanged before/after a run, and at what point in the procedure is that assertion made?

**Answer:** It is a **hand-executed two-point SKILL assertion**, not a helper. (1) Early (Step 2, right after deriving the PR number) the SKILL captures the head SHA via `gh pr view <PR> --json headRefOid --jq '.headRefOid'`. (2) Final (the last step, "Confirm the propose-only invariant") it re-reads `headRefOid` and asserts equality with the captured value; a mismatch must be surfaced loudly. There is **no Python helper** for this — it is two `gh pr view` calls bracketing the run, recorded in the SKILL prose and reinforced by a "Hard rules" entry ("Never mutate the PR branch... The head SHA check in Step N is the guardrail"). A workflow port must preserve both the early capture and the final re-read+compare.

**Evidence:**

```bash
# early capture (Step 2)
gh pr view <DESIGN_PR> --json headRefOid --jq '.headRefOid'
```
— `.claude/skills/review-design/SKILL.md:74-78` (capture) and `:281-289` (Step 8 re-read+assert)

Plan/impl/review mirror it:
— `.claude/skills/review-plan/SKILL.md:64-67, 255-265`; `.claude/skills/review-implementation/SKILL.md:67-70, 259-265`; `.claude/skills/review/SKILL.md:83-87, 285-293`

**Dependencies:** `gh pr view` (read-only). The invariant is enforced upstream by: the reviser writing only to `/tmp/.../review/`, and the only GitHub write being `qrspi_comment_reply.py` (a comment, not a branch push).
**Implicit contracts:** No `gt submit`/`gt modify`/`gh` branch-write anywhere in the run. The SHA bracket is the guardrail that detects any accidental mutation. A port must keep the SHA capture BEFORE the loop and the compare AFTER the comment post.

## Q12: What references to `/review` exist beyond `.claude/skills/review/` — in `.claude/CLAUDE.md` "Available skills", the `/review-*` cross-links in the three remaining SKILL descriptions, and docs?

**Answer:**

- `.claude/CLAUDE.md` "Available skills" lists all four: `/review-design` (line 126), `/review-plan` (127), `/review-implementation` (128), `/review` (129). Notably the `/review-design`/`/review-plan`/`/review-implementation` blurbs here are **stale** — they describe the OLD single-node-validity-lens behavior ("Runs the read-only design node-validity lens... answers the design's open questions"), not the upgraded 5-lens panel + decision-readiness + agreement the RUS-91 SKILLs now implement.
- Cross-links: each of the four `SKILL.md` `description` frontmatter blocks names the sibling commands ("for the design use /review-design, for the plan use /review-plan, for code use /review-implementation, for the whole stack use /review"). — `.claude/skills/review-design/SKILL.md:3`; `review-plan/SKILL.md:3`; `review-implementation/SKILL.md:3`; `review/SKILL.md:3`.
- `.claude/skills/qrspi-work/references/review-cascade.md` does **NOT** reference the `/review-*` family at all — it documents the PR-gated within-phase `revise` vs cross-phase `reset` cascade (a different "review" concept entirely). The question's premise that it cross-links `/review` is **not borne out**.
- `docs/testing-dynamic-workflows.md:200-201` references the `/review-*` family as "a live LLM-judge over the produced artifacts (the autonomous batch itself runs no in-pipeline critics)."

**Evidence:**

```
- `/review-design <ticket-id>` — **Advisory, propose-only** on-demand review of a ticket's design.
  Runs the read-only design node-validity lens (`qrspi-design-critic-design-review`) over `design.md`
  ... answers the design's open questions, then posts a synopsis comment ...
```
— `.claude/CLAUDE.md:126` (STALE — pre-RUS-91 single-lens description)

**Dependencies:** CLAUDE.md is the user-facing skill index; the four SKILL descriptions are the trigger/cross-link surface; the README also documents the skill family (`README.md`).
**Implicit contracts:** Each SKILL description must keep the cross-links consistent (they form the "family" navigation). The CLAUDE.md blurbs are documentation-only and currently DRIFTED from the implemented behavior — flagged in Inconsistencies.

## Q13: How does the design-only post-loop decision-readiness lens differ in inputs and outputs from the node-validity lens, and what happens for plan/implementation runs that lack it?

**Answer:** **Inputs:** the decision-readiness lens (`qrspi-design-critic-decision-readiness`) takes `DESIGN_PATH`, `TICKET_CONTENT_PATH` (required — it judges open questions against the ticket AC), and optional `RESEARCH_PATH`/`QUESTIONS_PATH`/`CODEBASE_PATH`. The node-validity lens (`qrspi-design-critic-design-review`) takes `DESIGN_PATH`, `RESEARCH_PATH` (always full), `CODEBASE_PATH`, and **deliberately does NOT get `TICKET_CONTENT_PATH`** (it stays research+code-only).

**Outputs:** decision-readiness emits a `DecisionReadinessVerdict` = `{"lens":"decision-readiness", "blockingDecisions":[{question, rationale}], "answerable":[{question}]}` — NOT the `{pass, findings}` shape. Node-validity emits `{pass, findings, nonBlockingNotes?}`.

**Role:** decision-readiness runs **once, post-loop, terminal-advisory** — it is partitioned OUT of the synthesize array (`partition_decision_readiness`) so it can never drive a revise round; it feeds the synopsis's "Decision readiness (blocking for human)" section only. Node-validity runs **every round inside the loop** and DOES gate the round's pass.

**For plan/impl:** there is **no** decision-readiness lens — those panels are 3-lens (`*-review`/`*-fidelity`/`*-completeness`) with no post-loop pass. The SKILLs still call `partition_decision_readiness()` as a harmless **guard** (it returns `(panel, None)` when no such lens is present), and `render_synopsis` is fed `decision_readiness=None`, omitting that section entirely. The plan/impl SKILLs and `/review` explicitly state "no decision-readiness lens for the plan/impl phase — that lens is design-phase-only."

**Evidence:**

```
Your output is a **terminal-advisory** `DecisionReadinessVerdict`. It feeds the synopsis ONLY — it
is partitioned OUT of the array fed to `synthesize`, so it can NEVER trigger a revise round.
```
— `.claude/agents/qrspi-design-critic-decision-readiness.md:15-17` (schema at `:60-74`)

`partition_decision_readiness` returns `None` when the lens is absent (the plan/impl guard):
— `scripts/qrspi_review_synopsis.py:60-81`

SKILL plan/impl "no decision-readiness" note:
— `.claude/skills/review-plan/SKILL.md:11`; `.claude/skills/review/SKILL.md:186-193` (Step 3c-design, design-only)

**Dependencies:** decision-readiness lens → `partition_decision_readiness` (split) → `render_synopsis` (decision-readiness section). Replaced the old producer self-grading open-question pass.
**Implicit contracts:** Every extracted open question must land in exactly one of `blockingDecisions`/`answerable`. Decision-readiness is non-producing and never reaches the reviser. `partition_decision_readiness` is idempotent/safe on arrays lacking the lens (the plan/impl guard is harmless).

## Q14: Which `scripts/*_test.py` files cover the review helpers, what behavior do they assert, and how does `scripts/run_tests.py` discover and run them?

**Answer:** Coverage:
- `qrspi_critic_synthesize_test.py` — AND-over-all-pass, text-deduped union, lens-tagging, fail-closed (empty/non-dict/malformed/JSON-string entries). Uses a bare `check(label, got, want)` helper (no unittest).
- `qrspi_critic_loop_test.py` — `next_action` converge-at-0 / revise→converge / cap_reached+residual / empty-list-fail-closed; `parse_critic_verdict` fail-closed parsing. Bare `check()` style.
- `qrspi_review_synopsis_test.py` — `unittest`: `partition_decision_readiness` (splits/None/no-mutate/dup-keeps-first/lenient), `ledger_row_fields` (axes enumerate every lens, notes union, blockingCount uses findings not notes, empty), `render_synopsis` (axis table, advisory passthrough, decision-readiness section, terminal action).
- `qrspi_review_agreement_test.py` — `unittest`: agree/disagree/pending matrix, case-insensitivity, unknown→pending, exact key contract.
- `qrspi_review_record_test.py` — `unittest`: base passthrough, agreement embed, `mode` discriminator, invalid-terminal-action raises.
- Plus `qrspi_critic_metrics_test.py`, `qrspi_critic_summary_test.py`, `qrspi_critics_config_test.py` (supporting).

Discovery: `run_tests.py.discover_tests` lists `scripts/` for every basename ending `_test.py` (sorted, optional substring filter), and `run_one` runs each as its own `subprocess.run([python, path])` with a 180s timeout, exiting non-zero if any fails. Both `check()`-style and `unittest`-style files work because each is a standalone script that exits 0/non-zero.

**Evidence:**

```python
def discover_tests(scripts_dir=SCRIPT_DIR, pattern=None):
    names = sorted(n for n in os.listdir(scripts_dir) if n.endswith("_test.py"))
    if pattern:
        names = [n for n in names if pattern in n]
    return [os.path.join(scripts_dir, n) for n in names]
```
— `scripts/run_tests.py:36-48` (runner at `:51-104`)

Test inventory:
— `scripts/qrspi_review_synopsis_test.py:34-148`; `qrspi_review_agreement_test.py:16-80`; `qrspi_review_record_test.py:15-68`; `qrspi_critic_synthesize_test.py:40-169`; `qrspi_critic_loop_test.py:40-72`

**Dependencies:** `run_tests.py` is the CI regression gate (`.github/workflows/tests.yml`, per `.claude/CLAUDE.md`). Each `_test.py` is a self-contained subprocess.
**Implicit contracts:** A `_test.py` MUST exit non-zero on failure (subprocess return-code gating). No pytest — stdlib only. New helpers must ship a `_test.py` sibling (auto-discovered, zero registration). A hung test (>180s) counts as failure.

## Q15: How are the existing `.claude/workflows` scripts structured and tested, and what contract-fixture mechanism exists to cover the JS↔Python seam that a ported review engine would need?

**Answer:** `.claude/workflows/qrspi-batch.js` (1682 lines) is the **imperative shell**: a top-level `export const meta = {...}` (name/description/whenToUse/phases) followed by orchestration that runs at module load (top-level `await`/`return`) and references harness-injected globals (`agent()`, `parallel()`, `pipeline()`, `phase()`, `log()`, `args`, `budget`, `workflow()`). It is **dual-illegal outside the harness** (CommonJS `export` syntax error / ESM top-level `return` syntax error) and **cannot `import`/`require` siblings** (the sandbox exposes no `require`/`process`/`fs`/dynamic `import` — proven by probe, `docs/testing-dynamic-workflows.md:204-228`). So it is **not unit-testable as-is**.

The strategy is **Functional Core / Imperative Shell**: all deterministic decision logic lives in tested `scripts/*.py` the JS only shells out to; the JS keeps ~10 pure JSON-envelope parsers (`parseResolveEnvelope`, `parseConfigEnvelope`, `parseCriticsEnvelope`, etc.) + path/flag helpers.

The **contract-fixture mechanism** (RUS-76, the seam a ported review engine would use): goldens at `scripts/fixtures/contract_seam/<seam>/<variant>.json`, asserted on BOTH sides — `qrspi_contract_fixtures_producer_test.py` (Python producer's output is byte-for-byte the fixture) and `qrspi_contract_fixtures_consumer_test.py` (drives `scripts/contract_seam_runner.js`, a `node:vm` harness that loads `qrspi-batch.js` via strip-`export`+async-wrap+injected-globals and exposes the parsers through an appended shim, asserting each parser accepts well-formed and fail-closes on malformed variants). Covers all eight `parse*` seams. A ported `/review` JS engine would (a) push decisions into Python helpers, (b) add `parse*` parsers covered by new contract-seam fixtures on both sides, (c) be exercised end-to-end manually (no agent-eval in the per-PR gate). Note `qrspi-teeth-eval.js` is a second existing workflow (an eval harness, not orchestration).

**Evidence:**

```js
export const meta = {
  name: 'qrspi-batch',
  ...
  phases: [ { title: 'Query', ... }, { title: 'Resolve', ... }, ... ],
}
```
— `.claude/workflows/qrspi-batch.js:1-15`

Contract-seam mechanism + node:vm consumer harness:
— `docs/testing-dynamic-workflows.md:124-182` (and the "Open experiment" no-import result at `:204-228`)

**Dependencies:** JS parsers (consumer) ↔ Python script `main()` serializers (producer), pinned by committed goldens. `run_tests.py` auto-discovers both `_test.py` sides. `contract_seam_runner.js` is the vm bridge.
**Implicit contracts:** Any new deterministic decision goes in a `scripts/*.py` + `_test.py`, never inline JS. A JS parser is only as strong as its fixture's field completeness (it validates only fields it dereferences). The harness yields a bare `null` on `agent()` failure (no error text) — so a port relies on the resume/recompute guarantee, not retry classification.

## Q16: What logging or run-trace output does the current hand-executed loop emit per round, and where would a deterministic orchestrator surface that signal for a human inspecting a run?

**Answer:** The current `/review-*` loop emits **no structured run-trace** — it is a sequence of hand-executed SKILL steps the model narrates in its own conversational output (the `printf ... | python3 ...` heredocs print `{pass, findings}` / `{action, residual_findings}` to the terminal, visible only as transient command output). The pure helpers (`qrspi_critic_loop.py`, `qrspi_critic_synthesize.py`) do **no logging** — they are stdin→stdout pure functions. The ONLY durable per-run record is the **post-loop ledger row** appended to `critic-metrics.jsonl` (one row per phase: `rounds[]` with per-lens pass + `findingsCount`, `terminalAction`, `agreement`, `axes`, `nonBlockingNotes`) — but this is a single terminal summary, NOT a per-round trace, and it carries counts, not finding text.

For comparison, the autonomous `qrspi-batch.js` orchestrator surfaces per-step signal via the harness-injected `log()` (e.g. `log(\`  ${id}: ${name} → saved ...\`)` at `qrspi-batch.js:530`) — dozens of `log()` calls trace each ticket's phase/finalize/land. A deterministic `/review` orchestrator would analogously surface per-round signal through `log()` (each round's panel verdict, synthesize result, next_action, and any revise) and/or richer `critic-metrics.jsonl` rows — the `log()` stream is where the harness shows a human the run trace, and the JSONL ledger is the durable inspection surface read by `qrspi_critic_summary.summarize`.

**Evidence:**

```js
  log(`  ${id}: ${name} → saved ${p.bytes ?? '?'}B (${String(res).slice(0, 60)})`)
```
— `.claude/workflows/qrspi-batch.js:530` (the harness `log()` trace surface the batch uses; `/review-*` has no equivalent today)

Ledger read side (the durable inspection surface):
— `scripts/qrspi_critic_summary.py:100-184` (`summarize` → dissentRate / dissentRevisedRate / terminalActionCounts / perLens)

**Dependencies:** Per-round signal: only the model's transient stdout. Durable: `qrspi_metrics_append.py` → `critic-metrics.jsonl` → `qrspi_critic_summary.py`. A port would add `log()` (harness-injected) for the live trace.
**Implicit contracts:** `log()` is a harness-injected global — available only inside a Workflow runner, not in a SKILL or a plain Python script. The ledger's `rounds[]` is per-lens-per-round but count-only. `dissentRevisedRate` is a "revise-attempted proxy" (a `pass:false` round followed by a later round), NOT "the artifact changed."

---

## Discovered Patterns

- **Functional Core / Imperative Shell is the law of the repo.** Every deterministic decision lives in a pure, stdlib-only, self-locating `scripts/qrspi_*.py` with a `_test.py` sibling; the untestable boundary (JS workflow, or SKILL prose) only shells out. The `/review-*` helpers (`synthesize`, `next_action`, `compute`, `build_record`, `render_synopsis`) all follow this exactly. (`docs/testing-dynamic-workflows.md:21-27`)
- **Fail-closed everywhere.** Every reducer coerces malformed/empty input to a NOT-passed / pending / empty result and NEVER raises (except `build_record` on a non-terminal `revise`, which is deliberate). Garbled lens replies can never silently pass a round.
- **Count-only synopsis + ledger.** Both the human-facing synopsis (`render_synopsis`) and the durable ledger row (`qrspi_critic_metrics.build_record`) reduce findings to `len()` counts; finding TEXT survives only as far as the reviser's `residual_findings`. This is the single largest information-loss pattern relevant to "is the artifact WRONG?" surfacing.
- **The on-demand loop is entirely hand-executed prose.** Unlike the autonomous batch (a `.js` orchestrator with `log()` tracing), `/review-*` has no orchestrator — round counting, fan-out, array assembly, and rendering are narrated SKILL steps. The `DEFAULT_REVIEW_*_LENSES` constants are referenced only in prose, never read by code.
- **Scratch-copy + propose-only invariant.** Every `/review-*` run works on `/tmp/phase-stage/<id>/review/` copies, writes GitHub only via a comment (`qrspi_comment_reply.py`), and brackets the run with a `headRefOid` capture/compare. The reviser may write exactly one scratch path.
- **Additive ledger fields.** `agreement`, `mode`, `axes`, `nonBlockingNotes` are merged onto the base `CriticStepMetrics` record additively; readers (`qrspi_critic_summary.summarize`) use `.get()` so they are unaffected.
- **Whitelist/default decoupling.** `design-review` is whitelist-acceptable but default-OFF in the batch panel, while it is a default member of the on-demand `DEFAULT_REVIEW_DESIGN_LENSES` — two distinct constants kept deliberately separate.

## Inconsistencies

1. **MAX_ROUNDS source differs across the family.** `/review-design` resolves the cap from config (`qrspi_critics_config.py` → `critics.design.maxRounds`, default **2**), but `/review-plan`, `/review-implementation`, and `/review` **hardcode `--max-rounds 3`** ("The cap is 3 rounds"). So design caps at 2 by default while plan/impl/whole-stack cap at 3, and only design is config-driven. (`.claude/skills/review-design/SKILL.md:54-62` vs `review-plan/SKILL.md:90`, `review-implementation/SKILL.md:93`, `review/SKILL.md:129`)
2. **Stale agent descriptions.** Five `qrspi-design-critic-*.md` agents (and `qrspi-design-critic-design-review.md`) say "Spawned by `runCriticPanelLoop` in qrspi-batch.js" — but `runCriticPanelLoop`/`runCoherenceCritic` **no longer exist** in `qrspi-batch.js` (the autonomous batch runs no in-pipeline critics; `docs/testing-dynamic-workflows.md:200-201`). The only live spawners are the `/review-*` SKILLs. (`.claude/agents/qrspi-design-critic-design-review.md:3`)
3. **Stale CLAUDE.md skill blurbs.** The `.claude/CLAUDE.md` "Available skills" entries for `/review-design`/`/review-plan`/`/review-implementation` describe the OLD single-node-validity-lens behavior ("Runs the read-only design node-validity lens... answers the design's open questions"), not the upgraded RUS-91 5-lens panel + post-loop decision-readiness + agreement that the SKILLs now implement. (`.claude/CLAUDE.md:126-128`)
4. **Question premise mismatch (Q12 review-cascade).** `.claude/skills/qrspi-work/references/review-cascade.md` does NOT reference the `/review-*` family at all — it documents the PR-gated `revise`/`reset` cascade (a different "review" concept). Any design that assumes it cross-links `/review` is mistaken.
5. **`design.md:76` staleness noted in source.** `qrspi_critic_metrics.py:36-38` flags that a `design.md` listed only `converged/cap_reached` as terminal actions, while the actual valid set is four (`converged/cap_reached/exhausted/aborted`). (`scripts/qrspi_critic_metrics.py:50-51`)
6. **`lensModel` resolved but unconsumed.** `qrspi_critics_config.resolve_design` recognizes and emits a `lensModel` config value, but no live code path reads it (its former consumer, the batch panel, is gone) — a config key that does nothing today. (`scripts/qrspi_critics_config.py:205-211`)
7. **`agreement` is structurally always `pending` in practice** despite a real `agree`/`disagree` code path — because the advisory review runs before a human `reviewDecision` exists (Q8). Not a bug, but a structural artifact of run timing.
