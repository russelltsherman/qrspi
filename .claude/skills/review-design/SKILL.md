---
name: review-design
description: On-demand advisory review of a QRSPI ticket's DESIGN artifact. Run the read-only node-validity design lens over design.md against the real codebase, iterate the producer until the lens converges, answer the design's open questions, then post one advisory synopsis comment to the design PR and append an agreement-extended ledger row — WITHOUT mutating the PR branch. Use whenever the user asks to review, critique, sanity-check, validate, or get a second opinion on a ticket's design (e.g. "/review-design RUS-89", "review the design for RUS-42", "is the design for RUS-50 sound?", "run the design panel on RUS-7"). This is the design-phase entry of the /review-* family; for the plan use /review-plan, for code use /review-implementation, for the whole stack use /review.
allowed-tools: Agent, Bash, Read
---

# /review-design

Run an **advisory, propose-only** review of a ticket's design artifact and post a synopsis to its design PR. This is the design-phase member of the `/review-*` family. It is deliberately **read-only with respect to the branch**: it spawns review lenses and a producer-as-reviser against a *scratch copy* of `design.md`, never the tracked file, and it posts a PR **comment** — it never runs `gt submit`, `gt modify`, or any `gh` write that mutates the branch. The PR head SHA must be identical before and after a run.

The point is to give a human reviewer a sharp, evidence-grounded second opinion (is the design materially WRONG against the real code?) plus answers to the design's open questions, and to record whether the panel and the human ended up agreeing — all without touching the work itself.

## Inputs

Parse `$ARGUMENTS` for a single `<ticket-id>` (Linear format, e.g. `RUS-89`). If it is missing, ask the user for it and stop.

## Overview of the run

```
resolve → derive design PR number → scratch-copy design.md
  → loop rounds 0..2: spawn design-review lens → synthesize → next_action
        revise ⇒ re-spawn qrspi-design to rewrite the scratch copy, continue
        converged / cap_reached ⇒ stop the loop
  → post-loop open-question pass (qrspi-design, non-strict)
  → build agreement-extended ReviewRecord → append to the ledger
  → post the advisory synopsis comment to the design PR
```

Every script below is invoked with `python3` from the worktree. Use the **absolute** paths the resolve envelope gives you; do not type the `.qrspi` path by hand where a script can compute it.

## Step 1 — Resolve paths and PR state

Run the one-shot resolver and read its JSON envelope:

```bash
python3 scripts/qrspi_resolve.py <ticket-id>
```

Capture from the envelope:

- `repoRoot` — the host checkout root.
- `worktreeDir` — the ticket's worktree (`<repoRoot>/.worktrees/<ticket-id>`). The design artifact lives at `<worktreeDir>/.qrspi/<ticket-id>/design.md`.
- `existing` — the per-phase branch/PR existence booleans. If the design phase does not exist yet, there is nothing to review: tell the user and stop.

The artifacts you will reference:

- `DESIGN` = `<worktreeDir>/.qrspi/<ticket-id>/design.md`
- `RESEARCH` = `<worktreeDir>/.qrspi/<ticket-id>/research.md`
- `QUESTIONS` = `<worktreeDir>/.qrspi/<ticket-id>/questions.md` (optional, pass if present)
- `CODEBASE` = `<worktreeDir>` (the lens reads/greps real source here)

## Step 2 — Derive the design PR number and its human review decision

The resolve envelope does not carry a PR number, so derive it from the branch:

```bash
gh pr list --head <ticket-id>/design --json number,reviewDecision --jq '.[0]'
```

Capture `DESIGN_PR` (`.number`) and `DESIGN_REVIEW_DECISION` (`.reviewDecision`). GitHub returns `reviewDecision` as `APPROVED`, `CHANGES_REQUESTED`, `COMMENTED`, or `null`/empty when no human has reviewed yet — pass it straight through to the agreement reducer in Step 6, which normalizes it (a missing decision becomes `agreement: "pending"`, never a false disagreement). If `gh pr list` returns no PR for `<ticket-id>/design`, tell the user the design PR does not exist and stop.

Record the PR head SHA now so you can confirm it is unchanged at the end (the propose-only invariant):

```bash
gh pr view <DESIGN_PR> --json headRefOid --jq '.headRefOid'
```

## Step 3 — Make a scratch copy of the design

The loop must never edit the tracked `design.md` — the producer-as-reviser rewrites a throwaway copy so the branch stays untouched. Copy it to a short, token-free scratch path:

```bash
mkdir -p /tmp/phase-stage/<ticket-id>/review
cp "<DESIGN>" /tmp/phase-stage/<ticket-id>/review/design.md
```

Use `SCRATCH` = `/tmp/phase-stage/<ticket-id>/review/design.md` as the artifact under review everywhere below.

## Step 4 — The review loop (rounds 0..2)

The cap is **3 rounds** (`--max-rounds 3`). For each round `r` starting at `0`:

### 4a. Spawn the design-review lens

Spawn the read-only node-validity lens via the `Agent` tool:

- `subagent_type: qrspi-design-critic-design-review`
- Prompt body carrying the named PATH inputs (no `model` override — model selection is not wired in v1):
  - `DESIGN_PATH = /tmp/phase-stage/<ticket-id>/review/design.md`
  - `RESEARCH_PATH = <RESEARCH>`
  - `CODEBASE_PATH = <worktreeDir>`
  - `QUESTIONS_PATH = <QUESTIONS>` (only if the file exists)

The lens reads the scratch design + the real source under `CODEBASE_PATH` and returns exactly one `{pass, findings}` verdict. Capture that verdict object.

### 4b. Synthesize the round's verdict

Reduce the round's lens verdict(s) to one authoritative verdict. Tag the verdict with its lens id so findings are attributable, then pipe the JSON **array** into the synthesizer:

```bash
printf '%s' '[{"lens":"design-review","pass":<bool>,"findings":<findings-array>}]' \
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

Record each round's synthesized verdict as a round entry of the shape `{"lens": "design-review", "pass": <round-pass>, "findings": <round-findings>}`. The accumulated list of these entries is the `rounds` argument for Step 6 — one entry per round you actually ran.

### 4d. Revise (producer-as-reviser)

On `revise`, re-spawn the **producer** to rewrite the scratch copy in place using the round's findings as guidance. Spawn via the `Agent` tool:

- `subagent_type: qrspi-design`
- Prompt body instructing it to read the current scratch design and its upstream inputs, address the findings, and write the improved design **back to the same scratch path** — never to the tracked artifact:
  - `TICKET_ID = <ticket-id>`
  - `TICKET_CONTENT_PATH` — write the ticket text to a scratch file if you have it; otherwise omit and note the producer should treat the existing design's framing as the ticket intent.
  - `QUESTIONS_PATH = <QUESTIONS>`
  - `RESEARCH_PATH = <RESEARCH>`
  - `OUTPUT_PATH = /tmp/phase-stage/<ticket-id>/review/design.md` (the scratch copy — verbatim)
  - `TEMPLATE_PATH = <worktreeDir>/.qrspi/templates/design.md`
  - Include the round's `residual_findings` as the concrete defects to fix.

Then continue to the next round against the rewritten scratch copy.

## Step 5 — Post-loop open-question pass

After the loop terminates (`converged` or `cap_reached`), answer the design's **Open Questions** in free text. This is design-phase-specific (the plan/impl review commands omit it). Spawn the producer in a **non-strict, advisory** mode (full upstream context + codebase access — NOT the strict lens):

- `subagent_type: qrspi-design`
- Prompt body asking it to read the (final) scratch design's "Open Questions" section plus `RESEARCH` and the real codebase, and return concise free-text answers/recommendations for each open question — for the synopsis only. Tell it explicitly **not to write any files** in this pass; you only need its text reply.

Capture the open-question answers as text for the synopsis.

## Step 6 — Build and append the ledger record

Compute the panel↔human agreement and build the agreement-extended record, then append it to the per-ticket ledger.

The panel verdict for agreement is the **terminal** round's pass: `true` when the loop ended `converged`, `false` when it ended `cap_reached`.

Build the record in Python so the shapes are exact (the helpers are pure and self-locating):

```bash
python3 - <<'PY'
import json, sys
sys.path.insert(0, "scripts")
import qrspi_review_agreement, qrspi_review_record

panel_pass = <True if converged else False>
human_decision = <DESIGN_REVIEW_DECISION or None>   # the gh reviewDecision string, or None
rounds = <the accumulated list of {"lens","pass","findings"} round entries from Step 4>
terminal_action = "<converged|cap_reached>"          # the loop's terminal action verbatim

agreement = qrspi_review_agreement.compute(panel_pass, human_decision)
record = qrspi_review_record.build_record(
    phase="design", rounds=rounds,
    terminal_action=terminal_action, agreement=agreement)
print(json.dumps(record))
PY
```

`terminal_action` MUST be `converged` or `cap_reached` — `revise` is non-terminal and `build_record` rejects it (fail-closed), so only build the record once the loop has actually terminated.

Append the printed record JSON to the ledger. `qrspi_metrics_append.py` requires `--ticket`, `--record`, AND `--run-id` (it stamps every line with `ticketId`, `timestamp`, and `runId`); use a stable per-invocation run id such as `review-design-<ticket-id>-<UTC-timestamp>`:

```bash
python3 scripts/qrspi_metrics_append.py \
  --ticket <ticket-id> \
  --run-id "review-design-<ticket-id>-$(date -u +%Y%m%dT%H%M%SZ)" \
  --record '<the record JSON from above>'
```

The appended line carries `mode: "on-demand-review"`, `phase: "design"`, and the `agreement` block. With no human review yet, `agreement` resolves to `"pending"`; after a human review it resolves to `"agree"`/`"disagree"` against the present `reviewDecision`.

## Step 7 — Post the advisory synopsis comment

Compose the synopsis as a markdown file (so you never quote markdown on a command line), then post it as a **top-level** PR comment. Write the body to a scratch file, e.g. `/tmp/phase-stage/<ticket-id>/review/synopsis-design.md`, containing:

- A clear "Advisory design review (propose-only — no branch changes)" header.
- The panel **verdict** (converged ⇒ pass / cap_reached ⇒ unresolved findings) and the terminal action.
- The surviving **findings** (the terminal round's findings / `residual_findings`), each as a bullet citing the design claim and the real source location the lens indicted.
- The **open-question answers** from Step 5.
- The **agreement** line (panel verdict vs. the current human `reviewDecision`, or "pending — no human review yet").

Post it (toplevel mode does not need a parent comment id — Slice 1 relaxed `--comment-id` to optional; `--ticket` and `--reply-mode` remain required):

```bash
python3 scripts/qrspi_comment_reply.py \
  --ticket <ticket-id> \
  --pr <DESIGN_PR> \
  --reply-mode toplevel \
  --body-file /tmp/phase-stage/<ticket-id>/review/synopsis-design.md
```

The script self-locates the repo and owner/repo and posts via `gh pr comment` (a comment write, not a branch write). Confirm the returned envelope has `"ok": true`.

## Step 8 — Confirm the propose-only invariant

Re-read the PR head SHA and assert it equals the value captured in Step 2:

```bash
gh pr view <DESIGN_PR> --json headRefOid --jq '.headRefOid'
```

If it changed, something mutated the branch — surface that loudly; the run was supposed to be advisory only. If it matches, report success to the user: the synopsis was posted to PR `<DESIGN_PR>`, a `mode:"on-demand-review"` ledger row was appended, and the branch is untouched.

## Hard rules

1. **Never mutate the design PR branch.** No `gt submit`, no `gt modify`, no `gh` write that pushes commits. The only write to GitHub is the top-level PR **comment** in Step 7. The head SHA check in Step 8 is the guardrail.
2. **The loop edits only the scratch copy** under `/tmp/phase-stage/<ticket-id>/review/`, never `<worktreeDir>/.qrspi/<ticket-id>/design.md`.
3. **Fail closed and stop** if the design phase/PR does not exist, if `resolve` errors, or if `qrspi_metrics_append.py` returns `ok:false`. Do not invent a PR number or a verdict.
4. **Build the ledger record only after the loop terminates** (`converged`/`cap_reached`); never with `revise`.
5. This command is **advisory**. It does not change Linear status and does not advance the PR-gated lifecycle — a human reviewer still owns the approval.
