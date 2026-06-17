---
name: review
description: On-demand advisory WHOLE-STACK review of a QRSPI ticket. Resolve the ticket's frontier (highest existing) phase via `gh pr list --state all` (dodging the partially-landed misfire), run each reviewed phase's read-only node-validity lens (design / plan / implementation) over the real codebase via the same scratch loop, then post ONE rolled-up synopsis comment — with a per-phase sub-section — to the frontier PR and append one agreement-extended ledger row PER reviewed phase, WITHOUT mutating any PR branch. Use whenever the user asks to review, critique, sanity-check, validate, or get a second opinion on a ticket's WHOLE stack across phases (e.g. "/review RUS-89", "review the whole stack for RUS-42", "is RUS-50 sound end-to-end?", "run the full review panel on RUS-7"). This is the comprehensive entry of the /review-* family; for a single phase use /review-design, /review-plan, or /review-implementation.
allowed-tools: Agent, Bash, Read
---

# /review

Run an **advisory, propose-only** whole-stack review of a ticket across every reviewed phase and post a single rolled-up synopsis to the **frontier PR**. This is the comprehensive member of the `/review-*` family — it composes the three per-phase lenses (`qrspi-design-critic-design-review`, `qrspi-plan-critic-plan-review`, `qrspi-impl-critic-impl-review`) rather than inventing a new one. It is deliberately **read-only with respect to every branch**: it spawns review lenses and producers-as-revisers against *scratch copies* of each phase's artifact, never the tracked files, and it posts a PR **comment** — it never runs `gt submit`, `gt modify`, or any `gh` write that mutates a branch. The frontier PR head SHA must be identical before and after a run.

The point is to give a human reviewer a sharp, evidence-grounded second opinion on the whole stack — is any phase materially WRONG against the real code? — and to record, per phase, whether the panel and the human ended up agreeing, all without touching the work itself.

## Inputs

Parse `$ARGUMENTS` for a single `<ticket-id>` (Linear format, e.g. `RUS-89`). If it is missing, ask the user for it and stop.

## Overview of the run

```
resolve → resolve the FRONTIER phase + its PR (gh pr list --state all)
  → for each reviewed phase up to the frontier (design, plan, implementation):
        scratch-copy that phase's artifact
        loop rounds 0..2: spawn that phase's lens → synthesize → next_action
              revise ⇒ re-spawn that phase's producer to rewrite the scratch copy, continue
              converged / cap_reached ⇒ stop the loop
        build that phase's agreement-extended ReviewRecord → append a ledger row
        collect that phase's verdict + findings for the synopsis
  → post ONE rolled-up synopsis (per-phase sub-sections) to the FRONTIER PR
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
- `CODEBASE` = `<worktreeDir>` (every lens reads/greps the real source — and, for implementation, its tests — here)

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

## Step 3 — Per-phase review (loop over the reviewed phases)

For **each** reviewed phase determined in Step 2, run the identical scratch loop the single-phase `/review-*` commands use, but with that phase's lens, producer, and artifact. Each phase is independent; do them in order (design, then plan, then implementation) and collect a per-phase result.

The per-phase bindings:

| phase | lens (`subagent_type`) | producer (`subagent_type`) | artifact | lens id |
|---|---|---|---|---|
| design | `qrspi-design-critic-design-review` | `qrspi-design` | `design.md` | `design-review` |
| plan | `qrspi-plan-critic-plan-review` | `qrspi-plan` | `plan.md` | `plan-review` |
| implementation | `qrspi-impl-critic-impl-review` | `qrspi-implement` | `impl-log.md` | `impl-review` |

### 3a. Scratch-copy that phase's artifact

The loop must never edit the tracked artifact — the producer-as-reviser rewrites a throwaway copy so every branch stays untouched:

```bash
mkdir -p /tmp/phase-stage/<ticket-id>/review
cp "<that phase's artifact>" /tmp/phase-stage/<ticket-id>/review/<artifact-filename>
```

Use that scratch path as the artifact under review for this phase. The lens's primary evidence is the **real source** under `CODEBASE_PATH` (the worktree); the scratch artifact anchors what was designed/planned/built.

### 3b. The review loop (rounds 0..2)

The cap is **3 rounds** (`--max-rounds 3`). For each round `r` starting at `0`:

**Spawn the phase's lens** via the `Agent` tool with that phase's `subagent_type`, no `model` override (model selection is not wired in v1), carrying the named PATH inputs:

- design lens: `DESIGN_PATH` = the scratch copy, `RESEARCH_PATH` = `<RESEARCH>`, `CODEBASE_PATH` = `<worktreeDir>`, `QUESTIONS_PATH` = `<QUESTIONS>` (only if it exists)
- plan lens: `PLAN_PATH` = the scratch copy, `STRUCTURE_PATH` = `<STRUCTURE>`, `RESEARCH_PATH` = `<RESEARCH>`, `CODEBASE_PATH` = `<worktreeDir>`, plus `DESIGN_PATH` = `<DESIGN>` (only if it exists)
- impl lens: `IMPL_PATH` = the scratch copy, `RESEARCH_PATH` = `<RESEARCH>`, `CODEBASE_PATH` = `<worktreeDir>`, plus `PLAN_PATH` / `STRUCTURE_PATH` / `DESIGN_PATH` (each only if it exists)

The lens reads the scratch artifact + the real source under `CODEBASE_PATH` and returns exactly one `{pass, findings}` verdict. Capture it.

**Synthesize the round's verdict** — tag it with the phase's lens id and pipe the JSON **array** into the synthesizer:

```bash
printf '%s' '[{"lens":"<lens id>","pass":<bool>,"findings":<findings-array>}]' \
  | python3 scripts/qrspi_critic_synthesize.py
```

This prints `{pass, findings}` for the round (fail-closed: a garbled/empty verdict reads as not-passed).

**Decide the next action** — pipe the round's synthesized verdict (a one-element JSON array) into the loop-decision CLI:

```bash
printf '%s' '[{"pass":<round-pass>,"findings":<round-findings>}]' \
  | python3 scripts/qrspi_critic_loop.py --round <r> --max-rounds 3
```

It prints `{"action": ..., "residual_findings": [...]}` where `action` is:

- `converged` — the round passed. Stop this phase's loop; terminal action.
- `cap_reached` — the round did not pass and this was the last allowed round. Stop; `residual_findings` are the survivors. Terminal action.
- `revise` — the round did not pass and rounds remain. Run 3c, then start round `r + 1`.

Record each round's synthesized verdict as a round entry `{"lens": "<lens id>", "pass": <round-pass>, "findings": <round-findings>}`. The accumulated list is this phase's `rounds` argument for Step 3d.

### 3c. Revise (producer-as-reviser)

On `revise`, re-spawn this phase's **producer** via the `Agent` tool to rewrite the scratch copy in place using the round's `residual_findings` as guidance. Instruct it to read the current scratch artifact and its upstream inputs, address the findings, and write the improved artifact **back to the same scratch path** — never to a tracked artifact or any source file. Pass `TICKET_ID = <ticket-id>`, `OUTPUT_PATH` = the scratch path (verbatim), the relevant upstream `*_PATH` inputs, and the round's `residual_findings`. Make clear this is an **advisory propose-only** pass: it must NOT touch any tracked source or branch. Then continue to the next round against the rewritten scratch copy.

(There is **no** post-loop open-question pass in `/review` — open-question resolution is design-phase-only and lives in `/review-design`; the comprehensive command focuses on cross-phase validity.)

### 3d. Build and append this phase's ledger record

After this phase's loop terminates (`converged` or `cap_reached`), compute the panel↔human agreement for this phase and append **one** `mode:"on-demand-review"` ledger row for it. The panel verdict is the terminal round's pass: `true` on `converged`, `false` on `cap_reached`.

```bash
python3 - <<'PY'
import json, sys
sys.path.insert(0, "scripts")
import qrspi_review_agreement, qrspi_review_record

panel_pass = <True if converged else False>
human_decision = <this phase's REVIEW_DECISION or None>   # the gh reviewDecision string, or None
rounds = <this phase's accumulated list of {"lens","pass","findings"} round entries from 3b>
terminal_action = "<converged|cap_reached>"               # the loop's terminal action verbatim

agreement = qrspi_review_agreement.compute(panel_pass, human_decision)
record = qrspi_review_record.build_record(
    phase="<design|plan|implementation>", rounds=rounds,
    terminal_action=terminal_action, agreement=agreement)
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

Keep, for the synopsis: this phase's name, its terminal verdict (converged ⇒ pass / cap_reached ⇒ unresolved), its terminal action, its surviving findings (terminal round's findings / `residual_findings`), and its agreement line.

## Step 4 — Post ONE rolled-up synopsis to the FRONTIER PR

Per the plan-time **OQ3 resolution**, `/review` posts **per-phase sub-synopses under one comment** — a single top-level comment whose body concatenates a per-phase section (no cross-phase verdict reducer is invented). Compose ONE markdown file, e.g. `/tmp/phase-stage/<ticket-id>/review/synopsis-review.md`, containing:

- A clear "Advisory whole-stack review (propose-only — no branch changes)" header naming the ticket and the frontier phase/PR.
- One section **per reviewed phase** (design, plan, implementation as applicable), each with:
  - the phase **verdict** (pass / unresolved findings) and its terminal action;
  - the phase's surviving **findings**, each a bullet citing the specific artifact claim and the real source location the lens indicted;
  - the phase's **agreement** line (panel verdict vs. that phase's human `reviewDecision`, or "pending — no human review yet").

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
7. This command is **advisory**. It does not change Linear status and does not advance the PR-gated lifecycle — a human reviewer still owns the approval.
