---
name: review
description: On-demand advisory WHOLE-STACK review of a QRSPI ticket. Resolve the ticket's frontier (highest existing) phase via `gh pr list --state all` (dodging the partially-landed misfire), run each reviewed phase's full read-only review panel (design / plan / implementation) over the real codebase via the same scratch loop, then post ONE rolled-up axis-enumerated synopsis comment — with a per-phase sub-section — to the frontier PR and append one agreement-extended ledger row PER reviewed phase, WITHOUT mutating any PR branch. Use whenever the user asks to review, critique, sanity-check, validate, or get a second opinion on a ticket's WHOLE stack across phases (e.g. "/review RUS-89", "review the whole stack for RUS-42", "is RUS-50 sound end-to-end?", "run the full review panel on RUS-7"). This is the comprehensive entry of the /review-* family; for a single phase use /review-design, /review-plan, or /review-implementation.
allowed-tools: Agent, Bash, Read, mcp__linear__get_issue
---

# /review

Run an **advisory, propose-only** whole-stack review of a ticket across every reviewed phase and post a single rolled-up synopsis to the **frontier PR**. This is the comprehensive member of the `/review-*` family — it composes each phase's **full upgraded review panel** (the same panels `/review-design`, `/review-plan`, and `/review-implementation` fan out) rather than inventing a new one. It is deliberately **read-only with respect to every branch**: it spawns review lenses and the shared non-producer reviser (`qrspi-critic-reviser`) against *scratch copies* of each phase's artifact, never the tracked files, and it posts a PR **comment** — it never runs `gt submit`, `gt modify`, or any `gh` write that mutates a branch. The frontier PR head SHA must be identical before and after a run.

The point is to give a human reviewer a sharp, evidence-grounded second opinion on the whole stack — is any phase materially WRONG against the real code? — and to record, per phase, whether the panel and the human ended up agreeing, all without touching the work itself.

## Inputs

Parse `$ARGUMENTS` for a single `<ticket-id>` (Linear format, e.g. `RUS-89`). If it is missing, ask the user for it and stop.

## Overview of the run

```
resolve → resolve the FRONTIER phase + its PR (gh pr list --state all) → stage ticket text
  → for each reviewed phase up to the frontier (design, plan, implementation):
        scratch-copy that phase's artifact
        loop rounds 0..2: fan out that phase's FULL panel → partition decision-readiness
              → synthesize the PANEL array → next_action
              revise ⇒ spawn qrspi-critic-reviser (PHASE=<phase>) to rewrite the scratch copy, continue
              converged / cap_reached ⇒ stop the loop
        (design only) spawn the decision-readiness lens (terminal-advisory; feeds synopsis only)
        build that phase's agreement-extended ReviewRecord (per-lens rounds) + merge axes/nonBlockingNotes → append a ledger row
        render that phase's axis-enumerated synopsis sub-section via render_synopsis()
  → post ONE rolled-up synopsis (per-phase axis-enumerated sub-sections) to the FRONTIER PR
```

Every script below is invoked with `python3` from the worktree. Use the **absolute** paths the resolve envelope gives you; do not type the `.qrspi` path by hand where a script can compute it.

## Step 1 — Resolve paths and phase existence

Run the one-shot resolver and read its JSON envelope:

```bash
python3 scripts/qrspi_resolve.py <ticket-id>
```

Capture from the envelope:

- `repoRoot` — the host checkout root.
- `worktreeDir` — the ticket's worktree (`<repoRoot>/.worktrees/<ticket-id>`). Every phase artifact lives under `<worktreeDir>/.qrspi/<ticket-id>/`.
- `existing` — the per-artifact existence booleans (`design`, `plan`, etc.). Use these to know which phase artifacts are present to review.
- `slices` — the ascending list of slice branch names (`["<ticket-id>/slice-1", ...]`); empty when there is no implementation phase.
- `tip` — the stack's tip branch (`<ticket-id>/slice-<maxN>`, or `<id>/plan` / `<id>/design` if no slices yet).

If `resolve` errors or the ticket has no phases at all, tell the user there is nothing to review and stop.

The per-phase artifacts you will reference (each only if it exists):

- design phase: `DESIGN` = `<worktreeDir>/.qrspi/<ticket-id>/design.md`, `RESEARCH` = `.../research.md`, `QUESTIONS` = `.../questions.md` (optional)
- plan phase: `PLAN` = `.../plan.md`, plus `STRUCTURE` = `.../structure.md`, `RESEARCH`, `DESIGN` (optional context)
- implementation phase: `IMPL` = `.../impl-log.md`, plus `RESEARCH`, `PLAN`, `STRUCTURE`, `DESIGN` (optional context)
- `QUESTIONS` = `.../questions.md` (optional; consumed by the design panel and the plan/impl `*-completeness` lenses)
- `CODEBASE` = `<worktreeDir>` (every lens reads/greps the real source — and, for implementation, its tests — here)
- `TICKET_CONTENT` = `/tmp/phase-stage/<ticket-id>/review/ticket.md` (staged in Step 2 — passed to each phase's coverage/fidelity/decision-readiness lenses ONLY, never the node-validity `*-review` lenses)

## Step 2 — Resolve the FRONTIER phase and its PR

The synopsis goes to **one** PR: the frontier (highest existing) phase's PR. The resolve envelope carries no PR number, and a partially-landed stack can make the resolver's own frontier logic misfire to `entry_blocked` (a known bug, ref: Q11) — so derive the frontier directly from GitHub with `--state all`, which sees merged/closed PRs too.

List every PR for the ticket's branches and pick the highest phase that has a PR, ordering `implementation (slice-N) > plan > design`:

```bash
gh pr list --state all --json number,headRefName,reviewDecision \
  --jq '[.[] | select(.headRefName | startswith("<ticket-id>/"))]'
```

From the returned array:

- Determine the **frontier phase**: if any `headRefName` matches `<ticket-id>/slice-*`, the frontier is **implementation** and the frontier branch is the highest-numbered slice (the envelope's `tip` / last element of `slices`). Else if `<ticket-id>/plan` is present, the frontier is **plan**. Else if `<ticket-id>/design` is present, the frontier is **design**.
- The **frontier PR** is the PR whose `headRefName` is that frontier branch. Capture `FRONTIER_PR` (`.number`).
- The **reviewed phases** to run are every phase from design up to and including the frontier: design only ⇒ `[design]`; plan frontier ⇒ `[design, plan]`; implementation frontier ⇒ `[design, plan, implementation]`. Skip any phase whose artifact does not exist in `existing` (defensive — normally all lower phases exist).

For each reviewed phase, also capture that phase's own PR `reviewDecision` from the same `gh pr list` output (match `headRefName` to `<id>/design`, `<id>/plan`, or the top slice branch) — call them `DESIGN_REVIEW_DECISION`, `PLAN_REVIEW_DECISION`, `IMPL_REVIEW_DECISION`. GitHub returns each as `APPROVED`, `CHANGES_REQUESTED`, `COMMENTED`, or `null`/empty when unreviewed — pass each straight through to the agreement reducer (a missing decision becomes `agreement: "pending"`, never a false disagreement).

If no PR matches `<ticket-id>/` at all, tell the user the ticket has no PRs to review and stop.

Record the frontier PR head SHA now so you can confirm it is unchanged at the end (the propose-only invariant):

```bash
gh pr view <FRONTIER_PR> --json headRefOid --jq '.headRefOid'
```

**Stage the ticket text once for the whole run.** Every phase's coverage/fidelity (and the design decision-readiness) lenses verify the artifact against the ticket's acceptance criteria, so fetch the ticket once and reuse the staged file across all reviewed phases:

```bash
mkdir -p /tmp/phase-stage/<ticket-id>/review
```

- Call `mcp__linear__get_issue` with `id: <ticket-id>`.
- Write the issue's title + description (its full markdown body) to `TICKET_CONTENT` = `/tmp/phase-stage/<ticket-id>/review/ticket.md` (use the `Write` tool, not a shell heredoc, so the content is stored verbatim).

If the Linear fetch fails or the ticket has no description, write a short note to `TICKET_CONTENT` recording that the ticket text was unavailable and proceed — the lenses treat a missing/empty ticket as "no stated AC to check against" rather than failing. `TICKET_CONTENT` is passed to each phase's coverage/fidelity/decision-readiness lenses ONLY; the node-validity `*-review` lenses stay research+code-only.

## Step 3 — Per-phase review (loop over the reviewed phases)

For **each** reviewed phase determined in Step 2, run the identical full-panel scratch loop the single-phase `/review-*` commands use, but with that phase's panel, the shared reviser, and that phase's artifact. Each phase is independent; do them in order (design, then plan, then implementation) and collect a per-phase result. This command composes the **same upgraded per-phase panels** the single-phase commands fan out — it does not invent its own lenses.

### Per-phase binding table

Each phase's panel is the ordered tuple in `scripts/qrspi_critics_config.py`; the lens id → agent mapping is `qrspi-<phase>-critic-<lens-id>`. The "ticket?" column marks which lenses receive `TICKET_CONTENT_PATH` (the node-validity `*-review` lenses NEVER do — they stay research+code-only):

| phase | panel constant | lenses (`subagent_type` = `qrspi-<phase>-critic-<id>`) — gets `TICKET_CONTENT_PATH`? | reviser | artifact | decision-readiness? |
|---|---|---|---|---|---|
| design | `DEFAULT_REVIEW_DESIGN_LENSES` | `completeness` (yes), `internal-consistency` (no), `edge-alignment` (yes), `simplicity` (no), `design-review` (no) | `qrspi-critic-reviser` (`PHASE=design`) | `design.md` | yes (terminal-advisory, post-loop) |
| plan | `DEFAULT_REVIEW_PLAN_LENSES` | `plan-review` (no), `plan-fidelity` (yes), `plan-completeness` (yes) | `qrspi-critic-reviser` (`PHASE=plan`) | `plan.md` | no |
| implementation | `DEFAULT_REVIEW_IMPL_LENSES` | `impl-review` (no), `impl-fidelity` (yes), `impl-completeness` (yes) | `qrspi-critic-reviser` (`PHASE=impl`) | `impl-log.md` | no |

The exact PATH inputs each phase's lenses and reviser carry are the same as the single-phase commands: see `/review-design`, `/review-plan`, and `/review-implementation` Steps 4a/4d for the per-lens input list. Notable phase deltas: the **impl** panel runs ONCE over the **aggregated** slice stack (one pass over `CODEBASE_PATH` = `<worktreeDir>`, not per-slice — `CODEBASE_PATH` is REQUIRED for all three impl lenses); only the **design** phase runs a post-loop decision-readiness lens.

### 3a. Scratch-copy that phase's artifact

The loop must never edit the tracked artifact — the producer-as-reviser rewrites a throwaway copy so every branch stays untouched:

```bash
mkdir -p /tmp/phase-stage/<ticket-id>/review
cp "<that phase's artifact>" /tmp/phase-stage/<ticket-id>/review/<artifact-filename>
```

Use that scratch path as the artifact under review for this phase. The lens's primary evidence is the **real source** under `CODEBASE_PATH` (the worktree); the scratch artifact anchors what was designed/planned/built.

### 3b. The review loop (rounds 0..2)

The cap is **3 rounds** (`--max-rounds 3`). For each round `r` starting at `0`:

**Fan out this phase's FULL panel** — spawn every lens in the phase's panel constant (Step 3 binding table) via the `Agent` tool, no `model` override (model selection is not wired in v1). Each lens carries the named PATH inputs identical to the single-phase command (`/review-design` 4a, `/review-plan` 4a, `/review-implementation` 4a) — the scratch artifact as the phase's `*_PATH`, `RESEARCH_PATH`, `CODEBASE_PATH = <worktreeDir>`, the optional upstream `*_PATH` inputs (only when the file exists), `QUESTIONS_PATH` (only if it exists — the `*-completeness` lenses consume it), and `TICKET_CONTENT_PATH = <TICKET_CONTENT>` **only** for the lenses marked "yes" in the binding table.

Each lens reads the scratch artifact + the real source under `CODEBASE_PATH` and returns exactly one `LensVerdict` — `{pass, findings}` (the coverage/fidelity lenses may also carry `nonBlockingNotes`). **Tag each verdict with its lens id** and collect them into this round's **pre-reduction verdict array**, e.g. for the plan phase:

```json
[
  {"lens":"plan-review","pass":<bool>,"findings":[...]},
  {"lens":"plan-fidelity","pass":<bool>,"findings":[...],"nonBlockingNotes":[...]},
  {"lens":"plan-completeness","pass":<bool>,"findings":[...],"nonBlockingNotes":[...]}
]
```

Keep this full pre-reduction array — it is the source for both the per-lens `rounds[]` entries and the axis-enumerated synopsis sub-section.

**Partition decision-readiness out, then synthesize the round's verdict** — the design phase's decision-readiness lens (when present) is terminal-advisory and must never reach the reducer; apply `partition_decision_readiness()` as the guard (harmless for plan/impl, which carry no such lens) before synthesize:

```bash
printf '%s' '<the pre-reduction verdict array from above>' | python3 - <<'PY'
import json, sys
sys.path.insert(0, "scripts")
import qrspi_review_synopsis, qrspi_critic_synthesize
verdicts = json.load(sys.stdin)
panel, _decision_readiness = qrspi_review_synopsis.partition_decision_readiness(verdicts)
print(json.dumps(qrspi_critic_synthesize.synthesize(panel)))
PY
```

This prints `{pass, findings}` for the round (fail-closed: a garbled/empty verdict reads as not-passed). The synthesized `findings` is the union of every lens's blocking findings — these become the `residual_findings` the reviser fixes on a `revise`. Keep both the synthesized verdict (for `next_action`) and the full pre-reduction array (for the round's per-lens entries).

**Decide the next action** — pipe the round's synthesized verdict (a one-element JSON array) into the loop-decision CLI:

```bash
printf '%s' '[{"pass":<round-pass>,"findings":<round-findings>}]' \
  | python3 scripts/qrspi_critic_loop.py --round <r> --max-rounds 3
```

It prints `{"action": ..., "residual_findings": [...]}` where `action` is:

- `converged` — the round passed. Stop this phase's loop; terminal action.
- `cap_reached` — the round did not pass and this was the last allowed round. Stop; `residual_findings` are the survivors. Terminal action.
- `revise` — the round did not pass and rounds remain. Run 3c, then start round `r + 1`.

Record this round's **per-lens** entries — append every element of the round's pre-reduction verdict array to the accumulated `rounds` list, each of the shape `{"lens": "<lens-id>", "pass": <bool>, "findings": [...]}`. Do NOT collapse the round to one synthesized entry: `qrspi_critic_summary.summarize` buckets per-lens dissent on `rnd["lens"]`, so the round must contribute one entry per lens (N lenses × R rounds). The accumulated list is this phase's `rounds` argument for Step 3d.

### 3c. Revise (shared non-producer reviser)

On `revise`, spawn the **shared non-producer reviser** (`qrspi-critic-reviser`) — NOT the producer — to rewrite the scratch copy in place using the round's residual findings as guidance. Spawn via the `Agent` tool with `subagent_type: qrspi-critic-reviser`, carrying the same prompt body the single-phase command uses (see `/review-design` 4d / `/review-plan` 4d / `/review-implementation` 4d):

- `PHASE = <design|plan|impl>` (this phase)
- `OUTPUT_PATH` = the scratch copy path (verbatim — the ONLY path it may write)
- `RESIDUAL_FINDINGS` = the round's `residual_findings` from 3b — node-validity/fidelity findings ONLY (decision-readiness is partitioned out and never reaches the reviser).
- `RESEARCH_PATH = <RESEARCH>`, `CODEBASE_PATH = <worktreeDir>`, the relevant optional upstream `*_PATH` inputs, `TICKET_CONTENT_PATH = <TICKET_CONTENT>`, the scratch artifact as the phase's `*_PATH`, and `TEMPLATE_PATH = <worktreeDir>/.qrspi/templates/<artifact-filename>`.

The reviser reads the scratch artifact + supplied inputs, addresses each residual finding, and writes the revised artifact back to `OUTPUT_PATH` verbatim — never to a tracked artifact or any source file. Then continue to the next round against the rewritten scratch copy.

### 3c-design. Decision-readiness lens (design phase ONLY, terminal-advisory)

After the **design** phase's loop terminates (`converged`/`cap_reached`), spawn the non-producer decision-readiness lens over the final scratch design — exactly as `/review-design` Step 5. The plan and implementation phases SKIP this step (that lens is design-phase-only).

- `subagent_type: qrspi-design-critic-decision-readiness`
- Prompt body: `DESIGN_PATH` = the scratch copy, `TICKET_CONTENT_PATH = <TICKET_CONTENT>`, `RESEARCH_PATH = <RESEARCH>`, `QUESTIONS_PATH = <QUESTIONS>` (only if it exists), `CODEBASE_PATH = <worktreeDir>`.

It returns a `DecisionReadinessVerdict` — `{"lens":"decision-readiness","blockingDecisions":[{question, rationale}],"answerable":[{question}]}`, NOT `{pass, findings}`. Capture it for the design phase's synopsis sub-section (Step 4); it is NOT fed to synthesize and does NOT change the loop's terminal action. For plan/impl, treat decision-readiness as `None`.

### 3d. Build and append this phase's ledger record

After this phase's loop terminates (`converged` or `cap_reached`), compute the panel↔human agreement for this phase and append **one** `mode:"on-demand-review"` ledger row for it. The panel verdict is the terminal round's pass: `true` on `converged`, `false` on `cap_reached`.

Build the record in Python so the shapes are exact. The `rounds` argument is the **accumulated per-lens entries** from Step 3b (N lenses × R rounds). After `build_record`, MERGE the additive axis/non-blocking fields derived from the **last round's** pre-reduction verdict array via `ledger_row_fields()` onto the record dict (they are additive — `qrspi_critic_summary.summarize` reads via `.get()` and is unaffected):

```bash
python3 - <<'PY'
import json, sys
sys.path.insert(0, "scripts")
import qrspi_review_agreement, qrspi_review_record, qrspi_review_synopsis

panel_pass = <True if converged else False>
human_decision = <this phase's REVIEW_DECISION or None>   # the gh reviewDecision string, or None
rounds = <this phase's accumulated list of per-lens {"lens","pass","findings"} entries from 3b>
terminal_action = "<converged|cap_reached>"               # the loop's terminal action verbatim
last_round_verdicts = <this phase's FINAL round's pre-reduction per-lens verdict array from 3b>

agreement = qrspi_review_agreement.compute(panel_pass, human_decision)
record = qrspi_review_record.build_record(
    phase="<design|plan|implementation>", rounds=rounds,
    terminal_action=terminal_action, agreement=agreement)
# Merge the OPTIONAL additive fields (axes + nonBlockingNotes) onto the record.
record.update(qrspi_review_synopsis.ledger_row_fields(last_round_verdicts))
print(json.dumps(record))
PY
```

`terminal_action` MUST be `converged` or `cap_reached` — `revise` is non-terminal and `build_record` rejects it (fail-closed), so only build the record once this phase's loop has actually terminated.

Append the printed record JSON. `qrspi_metrics_append.py` requires `--ticket`, `--record`, AND `--run-id`; use a stable per-invocation run id shared across this `/review` run so the per-phase rows correlate:

```bash
python3 scripts/qrspi_metrics_append.py \
  --ticket <ticket-id> \
  --run-id "review-<ticket-id>-<UTC-timestamp>" \
  --record '<the record JSON from above>'
```

Compute the `<UTC-timestamp>` **once** at the start of the run (`date -u +%Y%m%dT%H%M%SZ`) and reuse it for every phase's row so all rows of this run carry the same `runId`. Confirm each append returns `ok:true`; a `ok:false` is a hard stop.

### 3e. Collect this phase's synopsis result

Keep, for the synopsis sub-section: this phase's name, its **final round's pre-reduction per-lens verdict array** (from 3b — the axis-enumeration source), its **decision-readiness verdict** (the `DecisionReadinessVerdict` from 3c-design for the design phase, else `None`), its **terminal action**, and its **agreement line**. These are the exact inputs `render_synopsis()` takes (one call per phase in Step 4).

## Step 4 — Post ONE rolled-up synopsis to the FRONTIER PR

Per the plan-time **OQ3 resolution**, `/review` posts **per-phase sub-synopses under one comment** — a single top-level comment whose body concatenates one **axis-enumerated** section per reviewed phase (no cross-phase verdict reducer is invented). Each sub-section is rendered by the SAME `render_synopsis()` helper the single-phase commands use, so the sub-sections are honest per-lens axis enumerations — not hand-composed prose. Compose ONE markdown file, e.g. `/tmp/phase-stage/<ticket-id>/review/synopsis-review.md`, by:

- Writing a top header: `## Advisory whole-stack review (propose-only — no branch changes)` naming the ticket and the frontier phase/PR.
- Appending, **for each reviewed phase in order** (design, plan, implementation as applicable), a phase sub-section produced by `render_synopsis()` fed that phase's collected Step 3e inputs — its final round's pre-reduction per-lens verdict array, its decision-readiness verdict (the design phase's `DecisionReadinessVerdict`, else `None`), and its terminal action — prefixed with a `### <Phase> phase` heading and suffixed with that phase's `**Agreement:**` line.

Generate the whole body in one Python pass so the shapes stay exact:

```bash
python3 - <<'PY' > /tmp/phase-stage/<ticket-id>/review/synopsis-review.md
import sys
sys.path.insert(0, "scripts")
import qrspi_review_synopsis

print("## Advisory whole-stack review (propose-only — no branch changes)")
print("\nTicket <ticket-id> — frontier phase **<frontier phase>** (PR #<FRONTIER_PR>).\n")

# One entry per reviewed phase, in order, from the Step 3e collected results:
phases = [
    # ("Design", <design last_round_verdicts>, <design decision_readiness or None>, "<terminal>", "<agreement line>"),
    # ("Plan",   <plan last_round_verdicts>,   None,                                 "<terminal>", "<agreement line>"),
    # ("Implementation", <impl last_round_verdicts>, None,                           "<terminal>", "<agreement line>"),
]
for name, verdicts, decision_readiness, terminal_action, agreement_line in phases:
    print("\n### " + name + " phase\n")
    print(qrspi_review_synopsis.render_synopsis(verdicts, decision_readiness, terminal_action))
    print("\n**Agreement:** " + agreement_line)
PY
```

Each rendered sub-section contains, in order: the **Review axes** table (one row per lens with PASS/FAIL + blocking finding count), an **Advisory (non-blocking)** section (the union of that phase's lenses' `nonBlockingNotes`, when any), a **Decision readiness (blocking for human)** section (design phase only — omitted when `decision_readiness` is `None`), the **Terminal action**, and the phase's **Agreement** line.

Post it as a single **top-level** comment to the **frontier PR** (toplevel mode does not need a parent comment id — Slice 1 relaxed `--comment-id` to optional; `--ticket` and `--reply-mode` remain required):

```bash
python3 scripts/qrspi_comment_reply.py \
  --ticket <ticket-id> \
  --pr <FRONTIER_PR> \
  --reply-mode toplevel \
  --body-file /tmp/phase-stage/<ticket-id>/review/synopsis-review.md
```

The script self-locates the repo and owner/repo and posts via `gh pr comment` (a comment write, not a branch write). Confirm the returned envelope has `"ok": true`. Post exactly ONE synopsis comment — to the frontier PR only, never one per phase.

## Step 5 — Confirm the propose-only invariant

Re-read the frontier PR head SHA and assert it equals the value captured in Step 2:

```bash
gh pr view <FRONTIER_PR> --json headRefOid --jq '.headRefOid'
```

If it changed, something mutated the branch — surface that loudly; the run was supposed to be advisory only. If it matches, report success to the user: the rolled-up synopsis was posted to the frontier PR `<FRONTIER_PR>`, one `mode:"on-demand-review"` ledger row per reviewed phase was appended (all sharing this run's `runId`), and no branch was touched.

## Hard rules

1. **Never mutate any PR branch.** No `gt submit`, no `gt modify`, no `gh` write that pushes commits. The only write to GitHub is the single top-level PR **comment** in Step 4. The head SHA check in Step 5 is the guardrail.
2. **The loops edit only the scratch copies** under `/tmp/phase-stage/<ticket-id>/review/`, never `<worktreeDir>/.qrspi/<ticket-id>/*.md` and never any source file under the worktree.
3. **One rolled-up synopsis.** Post exactly one comment, to the frontier PR — per-phase sub-sections under that one comment, never a comment per phase.
4. **Resolve the frontier with `gh pr list --state all`** so a partially-landed stack does not misfire (ref: Q11). Do not trust the resolver's own frontier when a lower PR may already be merged.
5. **Fail closed and stop** if the ticket has no phases/PRs, if `resolve` errors, or if `qrspi_metrics_append.py` returns `ok:false`. Do not invent a PR number or a verdict.
6. **Build each phase's ledger record only after that phase's loop terminates** (`converged`/`cap_reached`); never with `revise`. One row per reviewed phase, all sharing the run's `runId`.
7. **Compose the upgraded per-phase panels — do not invent lenses.** Each phase fans out its full panel constant (`DEFAULT_REVIEW_{DESIGN,PLAN,IMPL}_LENSES`) exactly as the single-phase `/review-*` commands; record per-lens `rounds[]` (N×R) and merge `ledger_row_fields()` onto each phase's record.
8. **`TICKET_CONTENT_PATH` is scoped.** Pass it to each phase's coverage/fidelity (and the design decision-readiness) lenses and the reviser ONLY. The node-validity `*-review` lenses stay research+code-only — never pass the ticket to them.
9. **Decision-readiness is design-phase-only and terminal-advisory.** It runs once post-loop for the design phase, feeds the synopsis ONLY (never synthesize / never a `revise`), and is `None` for the plan/impl sub-sections.
10. This command is **advisory**. It does not change Linear status and does not advance the PR-gated lifecycle — a human reviewer still owns the approval.
