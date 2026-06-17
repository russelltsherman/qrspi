---
name: review-implementation
description: On-demand advisory review of a QRSPI ticket's IMPLEMENTATION (the slice stack). Run the read-only node-validity implementation lens over the implemented code + tests against the real codebase, iterate the producer until the lens converges, then post ONE rolled-up advisory synopsis comment to the top slice PR and append an agreement-extended ledger row — WITHOUT mutating any PR branch. Use whenever the user asks to review, critique, sanity-check, validate, or get a second opinion on a ticket's implementation/code (e.g. "/review-implementation RUS-89", "review the implementation for RUS-42", "is the code for RUS-50 correct?", "run the impl panel on RUS-7"). This is the implementation-phase entry of the /review-* family; for the design use /review-design, for the plan use /review-plan, for the whole stack use /review.
allowed-tools: Agent, Bash, Read
---

# /review-implementation

Run an **advisory, propose-only** review of a ticket's implementation (its slice stack) and post a single rolled-up synopsis to the top slice PR. This is the implementation-phase member of the `/review-*` family. It is deliberately **read-only with respect to every branch**: it spawns review lenses and a producer-as-reviser against a *scratch copy* of the implementation record, never the tracked files, and it posts a PR **comment** — it never runs `gt submit`, `gt modify`, or any `gh` write that mutates a branch. The top slice PR head SHA must be identical before and after a run.

The point is to give a human reviewer a sharp, evidence-grounded second opinion (is the implemented code materially WRONG — incorrect, insecure, inefficient, or unfit for its stated scale — against the real code and its tests?) and to record whether the panel and the human ended up agreeing — all without touching the work itself.

## Inputs

Parse `$ARGUMENTS` for a single `<ticket-id>` (Linear format, e.g. `RUS-89`). If it is missing, ask the user for it and stop.

## Overview of the run

```
resolve → derive top slice PR number → scratch-copy the impl record
  → loop rounds 0..2: spawn impl-review lens → synthesize → next_action
        revise ⇒ re-spawn qrspi-implement to rewrite the scratch copy, continue
        converged / cap_reached ⇒ stop the loop
  → build agreement-extended ReviewRecord → append to the ledger
  → post ONE rolled-up advisory synopsis comment to the top slice PR
```

Every script below is invoked with `python3` from the worktree. Use the **absolute** paths the resolve envelope gives you; do not type the `.qrspi` path by hand where a script can compute it.

## Step 1 — Resolve paths and PR state

Run the one-shot resolver and read its JSON envelope:

```bash
python3 scripts/qrspi_resolve.py <ticket-id>
```

Capture from the envelope:

- `repoRoot` — the host checkout root.
- `worktreeDir` — the ticket's worktree (`<repoRoot>/.worktrees/<ticket-id>`). The implementation artifacts live under `<worktreeDir>/.qrspi/<ticket-id>/`.
- `existing` — the per-phase branch/PR existence booleans. If the implementation phase does not exist yet (no slice branches), there is nothing to review: tell the user and stop.
- `slices` — the ascending list of slice branch names (`["<ticket-id>/slice-1", ...]`). If it is empty, there is no implementation to review: tell the user and stop.
- `tip` — the stack's tip branch (`<ticket-id>/slice-<maxN>`); this is the **top slice** whose PR receives the rolled-up synopsis.

The artifacts you will reference:

- `IMPL` = `<worktreeDir>/.qrspi/<ticket-id>/impl-log.md` (the implementation record anchoring what was built across slices)
- `RESEARCH` = `<worktreeDir>/.qrspi/<ticket-id>/research.md`
- `PLAN` = `<worktreeDir>/.qrspi/<ticket-id>/plan.md` (optional, pass if present)
- `STRUCTURE` = `<worktreeDir>/.qrspi/<ticket-id>/structure.md` (optional, pass if present)
- `DESIGN` = `<worktreeDir>/.qrspi/<ticket-id>/design.md` (optional, pass if present)
- `CODEBASE` = `<worktreeDir>` (the lens reads/greps the real implemented source **and its tests** here)

## Step 2 — Derive the top slice PR number and its human review decision

The implementation is a stack of slice PRs; the rolled-up synopsis goes to the **top** slice PR. Take the top slice branch from the envelope's `tip` (equivalently, the last element of `slices`), then derive its PR number from the branch:

```bash
gh pr list --head <tip> --json number,reviewDecision --jq '.[0]'
```

Capture `IMPL_PR` (`.number`) and `IMPL_REVIEW_DECISION` (`.reviewDecision`). GitHub returns `reviewDecision` as `APPROVED`, `CHANGES_REQUESTED`, `COMMENTED`, or `null`/empty when no human has reviewed yet — pass it straight through to the agreement reducer in Step 5, which normalizes it (a missing decision becomes `agreement: "pending"`, never a false disagreement). If `gh pr list` returns no PR for `<tip>`, tell the user the top slice PR does not exist and stop.

Record the top slice PR head SHA now so you can confirm it is unchanged at the end (the propose-only invariant):

```bash
gh pr view <IMPL_PR> --json headRefOid --jq '.headRefOid'
```

## Step 3 — Make a scratch copy of the implementation record

The loop must never edit the tracked artifacts — the producer-as-reviser rewrites a throwaway copy so every branch stays untouched. Copy the implementation record to a short, token-free scratch path:

```bash
mkdir -p /tmp/phase-stage/<ticket-id>/review
cp "<IMPL>" /tmp/phase-stage/<ticket-id>/review/impl-log.md
```

Use `SCRATCH` = `/tmp/phase-stage/<ticket-id>/review/impl-log.md` as the artifact under review everywhere below. The lens's primary evidence is the **real implemented source + tests** under `CODEBASE_PATH` (the worktree); the scratch record anchors what was built.

## Step 4 — The review loop (rounds 0..2)

The cap is **3 rounds** (`--max-rounds 3`). For each round `r` starting at `0`:

### 4a. Spawn the impl-review lens

Spawn the read-only node-validity lens via the `Agent` tool:

- `subagent_type: qrspi-impl-critic-impl-review`
- Prompt body carrying the named PATH inputs (no `model` override — model selection is not wired in v1):
  - `IMPL_PATH = /tmp/phase-stage/<ticket-id>/review/impl-log.md`
  - `RESEARCH_PATH = <RESEARCH>`
  - `CODEBASE_PATH = <worktreeDir>`
  - `PLAN_PATH = <PLAN>` (only if the file exists)
  - `STRUCTURE_PATH = <STRUCTURE>` (only if the file exists)
  - `DESIGN_PATH = <DESIGN>` (only if the file exists)

The lens reads the scratch impl record + the **real implemented source and tests** under `CODEBASE_PATH` and returns exactly one `{pass, findings}` verdict. Capture that verdict object.

### 4b. Synthesize the round's verdict

Reduce the round's lens verdict(s) to one authoritative verdict. Tag the verdict with its lens id so findings are attributable, then pipe the JSON **array** into the synthesizer:

```bash
printf '%s' '[{"lens":"impl-review","pass":<bool>,"findings":<findings-array>}]' \
  | python3 scripts/qrspi_critic_synthesize.py
```

This prints `{pass, findings}` for the round (fail-closed: a garbled/empty verdict reads as not-passed). Keep this synthesized verdict — you will both feed it to `next_action` and record it as this round's entry.

### 4c. Decide the next action

Pipe the round's synthesized verdict (as a one-element JSON array) into the already-existing loop-decision CLI:

```bash
printf '%s' '[{"pass":<round-pass>,"findings":<round-findings>}]' \
  | python3 scripts/qrspi_critic_loop.py --round <r> --max-rounds 3
```

It prints `{"action": ..., "residual_findings": [...]}` where `action` is one of:

- `converged` — the round passed. Stop the loop; this is the terminal action.
- `cap_reached` — the round did not pass and this was the last allowed round. Stop the loop; `residual_findings` are the surviving findings. This is the terminal action.
- `revise` — the round did not pass and rounds remain. Go to Step 4d, then start the next round (`r + 1`).

Record each round's synthesized verdict as a round entry of the shape `{"lens": "impl-review", "pass": <round-pass>, "findings": <round-findings>}`. The accumulated list of these entries is the `rounds` argument for Step 5 — one entry per round you actually ran.

### 4d. Revise (producer-as-reviser)

On `revise`, re-spawn the **producer** to rewrite the scratch copy in place using the round's findings as guidance. Spawn via the `Agent` tool:

- `subagent_type: qrspi-implement`
- Prompt body instructing it to read the current scratch impl record and its upstream inputs, address the findings, and write the improved record **back to the same scratch path** — never to a tracked artifact or any source file:
  - `TICKET_ID = <ticket-id>`
  - `STRUCTURE_PATH = <STRUCTURE>` (the approved structure/contracts the implementation honors)
  - `PLAN_PATH = <PLAN>` (the plan the implementation executed, reference only)
  - `OUTPUT_PATH = /tmp/phase-stage/<ticket-id>/review/impl-log.md` (the scratch copy — verbatim)
  - Tell it the scratch copy already holds the current implementation record to improve, that this is an **advisory propose-only** pass (it must NOT touch any tracked source or branch), and include the round's `residual_findings` as the concrete defects to address in the record.

Then continue to the next round against the rewritten scratch copy.

## Step 5 — Build and append the ledger record

After the loop terminates (`converged` or `cap_reached`), compute the panel↔human agreement and build the agreement-extended record, then append it to the per-ticket ledger.

(There is **no** post-loop open-question pass for `/review-implementation` — that step is design-phase-only in v1, per the OQ1 resolution. Go straight from the terminated loop to the ledger record.)

The panel verdict for agreement is the **terminal** round's pass: `true` when the loop ended `converged`, `false` when it ended `cap_reached`.

Build the record in Python so the shapes are exact (the helpers are pure and self-locating):

```bash
python3 - <<'PY'
import json, sys
sys.path.insert(0, "scripts")
import qrspi_review_agreement, qrspi_review_record

panel_pass = <True if converged else False>
human_decision = <IMPL_REVIEW_DECISION or None>   # the gh reviewDecision string, or None
rounds = <the accumulated list of {"lens","pass","findings"} round entries from Step 4>
terminal_action = "<converged|cap_reached>"          # the loop's terminal action verbatim

agreement = qrspi_review_agreement.compute(panel_pass, human_decision)
record = qrspi_review_record.build_record(
    phase="implementation", rounds=rounds,
    terminal_action=terminal_action, agreement=agreement)
print(json.dumps(record))
PY
```

`terminal_action` MUST be `converged` or `cap_reached` — `revise` is non-terminal and `build_record` rejects it (fail-closed), so only build the record once the loop has actually terminated.

Append the printed record JSON to the ledger. `qrspi_metrics_append.py` requires `--ticket`, `--record`, AND `--run-id` (it stamps every line with `ticketId`, `timestamp`, and `runId`); use a stable per-invocation run id such as `review-implementation-<ticket-id>-<UTC-timestamp>`:

```bash
python3 scripts/qrspi_metrics_append.py \
  --ticket <ticket-id> \
  --run-id "review-implementation-<ticket-id>-$(date -u +%Y%m%dT%H%M%SZ)" \
  --record '<the record JSON from above>'
```

The appended line carries `mode: "on-demand-review"`, `phase: "implementation"`, and the `agreement` block. With no human review yet, `agreement` resolves to `"pending"`; after a human review it resolves to `"agree"`/`"disagree"` against the present `reviewDecision`.

## Step 6 — Post the single rolled-up advisory synopsis comment

Compose ONE rolled-up synopsis as a markdown file (so you never quote markdown on a command line), then post it as a single **top-level** comment to the **top slice PR**. Write the body to a scratch file, e.g. `/tmp/phase-stage/<ticket-id>/review/synopsis-implementation.md`, containing:

- A clear "Advisory implementation review (propose-only — no branch changes)" header.
- The panel **verdict** (converged ⇒ pass / cap_reached ⇒ unresolved findings) and the terminal action.
- The surviving **findings** (the terminal round's findings / `residual_findings`), each as a bullet naming the specific code (file/symbol) the lens indicted and why it is wrong — rolled up across the whole slice stack into this one comment.
- The **agreement** line (panel verdict vs. the current human `reviewDecision`, or "pending — no human review yet").

Post it (toplevel mode does not need a parent comment id — Slice 1 relaxed `--comment-id` to optional; `--ticket` and `--reply-mode` remain required):

```bash
python3 scripts/qrspi_comment_reply.py \
  --ticket <ticket-id> \
  --pr <IMPL_PR> \
  --reply-mode toplevel \
  --body-file /tmp/phase-stage/<ticket-id>/review/synopsis-implementation.md
```

The script self-locates the repo and owner/repo and posts via `gh pr comment` (a comment write, not a branch write). Confirm the returned envelope has `"ok": true`. Post exactly ONE synopsis comment — to the top slice PR only, never per-slice.

## Step 7 — Confirm the propose-only invariant

Re-read the top slice PR head SHA and assert it equals the value captured in Step 2:

```bash
gh pr view <IMPL_PR> --json headRefOid --jq '.headRefOid'
```

If it changed, something mutated the branch — surface that loudly; the run was supposed to be advisory only. If it matches, report success to the user: the rolled-up synopsis was posted to PR `<IMPL_PR>`, a `mode:"on-demand-review"` ledger row was appended, and no branch was touched.

## Hard rules

1. **Never mutate any slice PR branch.** No `gt submit`, no `gt modify`, no `gh` write that pushes commits. The only write to GitHub is the single top-level PR **comment** in Step 6. The head SHA check in Step 7 is the guardrail.
2. **The loop edits only the scratch copy** under `/tmp/phase-stage/<ticket-id>/review/`, never `<worktreeDir>/.qrspi/<ticket-id>/impl-log.md` and never any source file under the worktree.
3. **One rolled-up synopsis.** Post exactly one comment, to the top slice PR — do not fan out a comment per slice.
4. **Fail closed and stop** if the implementation phase/slices/top-slice PR do not exist, if `resolve` errors, or if `qrspi_metrics_append.py` returns `ok:false`. Do not invent a PR number or a verdict.
5. **Build the ledger record only after the loop terminates** (`converged`/`cap_reached`); never with `revise`.
6. This command is **advisory**. It does not change Linear status and does not advance the PR-gated lifecycle — a human reviewer still owns the approval.
