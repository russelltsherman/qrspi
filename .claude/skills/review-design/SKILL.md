---
name: review-design
description: On-demand advisory review of a QRSPI ticket's DESIGN artifact. Run the full read-only design review panel (node-validity + edge lenses) over design.md against the real codebase, iterate a non-producer reviser until the panel converges, partition decision-readiness out as terminal-advisory, then post one axis-enumerated advisory synopsis comment to the design PR and append an agreement-extended ledger row — WITHOUT mutating the PR branch. Use whenever the user asks to review, critique, sanity-check, validate, or get a second opinion on a ticket's design (e.g. "/review-design RUS-89", "review the design for RUS-42", "is the design for RUS-50 sound?", "run the design panel on RUS-7"). This is the design-phase entry of the /review-* family; for the plan use /review-plan, for code use /review-implementation.
allowed-tools: Agent, Bash, Read, mcp__linear__get_issue
---

# /review-design

Run an **advisory, propose-only** review of a ticket's design artifact and post a synopsis to its design PR. This is the design-phase member of the `/review-*` family. It is deliberately **read-only with respect to the branch**: it spawns the review panel and a shared non-producer reviser against a *scratch copy* of `design.md`, never the tracked file, and it posts a PR **comment** — it never runs `gt submit`, `gt modify`, or any `gh` write that mutates the branch. The PR head SHA must be identical before and after a run.

The point is to give a human reviewer a sharp, evidence-grounded second opinion (is the design materially WRONG against the real code?) across the **full design panel** — `completeness`, `internal-consistency`, `edge-alignment`, `simplicity`, and the node-validity `design-review` — plus a partition of the design's open questions into genuine human decisions vs. answerable ones, and a record of whether the panel and the human ended up agreeing — all without touching the work itself.

## Inputs

Parse `$ARGUMENTS` for a single `<ticket-id>` (Linear format, e.g. `RUS-89`). If it is missing, ask the user for it and stop.

## Overview of the run

```
resolve → derive design PR number → scratch-copy design.md → stage ticket text
  → loop rounds 0..MAX_ROUNDS-1 (MAX_ROUNDS from critics.design.maxRounds): fan out the 5-lens design panel → partition decision-readiness
        → synthesize the PANEL array (decision-readiness excluded) → next_action
        revise ⇒ spawn qrspi-critic-reviser (PHASE=design) to rewrite the scratch copy, continue
        converged / cap_reached ⇒ stop the loop
  → spawn the decision-readiness lens (terminal-advisory; feeds synopsis only, never the loop)
  → build agreement-extended ReviewRecord (per-lens rounds) + merge axes/nonBlockingNotes → append to the ledger
  → render the axis-enumerated synopsis → post the advisory comment to the design PR
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
- `TICKET_CONTENT` = `/tmp/phase-stage/<ticket-id>/review/ticket.md` (staged in Step 3 — passed to the fidelity/coverage/decision-readiness lenses ONLY, never the node-validity lens)

### Step 1b — Resolve the configurable round cap

The review-loop cap is **not hardcoded** — it reads `critics.design.maxRounds` from `.qrspi/config.json` via the tested resolver (the SAME key the autonomous `qrspi-batch` design panel uses, so the on-demand review and the batch share one knob):

```bash
python3 scripts/qrspi_critics_config.py
```

From its JSON envelope (`{"ok":true,"phases":{"design":{...,"maxRounds":N,...}}}`) capture `MAX_ROUNDS` = `.phases.design.maxRounds`. The resolver always returns a usable integer — it falls back to the source default (`2`) when the key is absent, unreadable, or non-positive, so `MAX_ROUNDS` is never empty. Use this `MAX_ROUNDS` value everywhere Step 4 caps the loop (the loop runs rounds `0 .. MAX_ROUNDS-1`). Do not hardcode a round count.

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

## Step 3 — Make a scratch copy of the design and stage the ticket text

The loop must never edit the tracked `design.md` — the shared reviser rewrites a throwaway copy so the branch stays untouched. Copy it to a short, token-free scratch path:

```bash
mkdir -p /tmp/phase-stage/<ticket-id>/review
cp "<DESIGN>" /tmp/phase-stage/<ticket-id>/review/design.md
```

Use `SCRATCH` = `/tmp/phase-stage/<ticket-id>/review/design.md` as the artifact under review everywhere below.

**Stage the ticket text.** Fetch the ticket via the Linear MCP and write its content to `TICKET_CONTENT` so the coverage/fidelity/decision-readiness lenses can verify the design against the ticket's acceptance criteria:

- Call `mcp__linear__get_issue` with `id: <ticket-id>`.
- Write the issue's title + description (its full markdown body) to `TICKET_CONTENT` = `/tmp/phase-stage/<ticket-id>/review/ticket.md` (use the `Write` tool, not a shell heredoc, so the content is stored verbatim).

If the Linear fetch fails or the ticket has no description, write a short note to `TICKET_CONTENT` recording that the ticket text was unavailable and proceed — the lenses treat a missing/empty ticket as "no stated AC to check against" rather than failing. `TICKET_CONTENT` is passed to the `edge-alignment`, `completeness`, and `decision-readiness` lenses ONLY; the node-validity `design-review` lens stays research+code-only (unchanged).

## Step 4 — The review loop (rounds 0..MAX_ROUNDS-1)

The cap is **`MAX_ROUNDS` rounds** — the configurable value resolved in Step 1b from `critics.design.maxRounds` (`--max-rounds <MAX_ROUNDS>`), not a hardcoded literal. For each round `r` starting at `0`:

### 4a. Fan out the full design review panel

Spawn the **whole design review panel** (sourced from `DEFAULT_REVIEW_DESIGN_LENSES` in `scripts/qrspi_critics_config.py`) — five lenses, each via the `Agent` tool. The lens id → agent mapping is `qrspi-design-critic-<lens-id>`:

| Lens id | `subagent_type` | Gets `TICKET_CONTENT_PATH`? |
| --- | --- | --- |
| `completeness` | `qrspi-design-critic-completeness` | yes |
| `internal-consistency` | `qrspi-design-critic-internal-consistency` | no |
| `edge-alignment` | `qrspi-design-critic-edge-alignment` | yes |
| `simplicity` | `qrspi-design-critic-simplicity` | no |
| `design-review` | `qrspi-design-critic-design-review` | **no** (node-validity stays research+code-only) |

For each lens, the prompt body carries the named PATH inputs (no `model` override — model selection is not wired in v1):

- `DESIGN_PATH = /tmp/phase-stage/<ticket-id>/review/design.md`
- `RESEARCH_PATH = <RESEARCH>`
- `CODEBASE_PATH = <worktreeDir>`
- `QUESTIONS_PATH = <QUESTIONS>` (only if the file exists)
- `TICKET_CONTENT_PATH = <TICKET_CONTENT>` — **ONLY** for the lenses marked "yes" above (`completeness`, `edge-alignment`). Do NOT pass it to `internal-consistency`, `simplicity`, or the node-validity `design-review` lens.

Each lens reads the scratch design + the real source under `CODEBASE_PATH` and returns exactly one `LensVerdict` — `{pass, findings}` (any panel lens may also carry an OPTIONAL `nonBlockingNotes` advisory channel; all five now emit it). **Tag each verdict with its lens id** and collect them into the **pre-reduction verdict array** for this round:

```json
[
  {"lens":"completeness","pass":<bool>,"findings":[...],"nonBlockingNotes":[...]},
  {"lens":"internal-consistency","pass":<bool>,"findings":[...],"nonBlockingNotes":[...]},
  {"lens":"edge-alignment","pass":<bool>,"findings":[...],"nonBlockingNotes":[...]},
  {"lens":"simplicity","pass":<bool>,"findings":[...],"nonBlockingNotes":[...]},
  {"lens":"design-review","pass":<bool>,"findings":[...],"nonBlockingNotes":[...]}
]
```

Keep this full pre-reduction array — it is the source for both the per-lens `rounds[]` entries (Step 6) and the axis-enumerated synopsis (Step 7).

### 4b. Partition decision-readiness out, then synthesize the round's verdict

Reduce the round's pre-reduction verdict array to one authoritative verdict. The **decision-readiness lens is terminal-advisory and MUST never reach the reducer** (it would otherwise drive a `revise` round). The in-loop panel does not include it (decision-readiness runs once, post-loop, in Step 5), but apply `partition_decision_readiness()` as a guard so a stray decision-readiness element is split out before synthesize:

```bash
printf '%s' '<the pre-reduction verdict array from 4a>' | python3 - <<'PY'
import json, sys
sys.path.insert(0, "scripts")
import qrspi_review_synopsis, qrspi_critic_synthesize
verdicts = json.load(sys.stdin)
panel, _decision_readiness = qrspi_review_synopsis.partition_decision_readiness(verdicts)
print(json.dumps(qrspi_critic_synthesize.synthesize(panel)))
PY
```

This prints `{pass, findings}` for the round (fail-closed: a garbled/empty verdict reads as not-passed). The synthesized `findings` is the union of every lens's blocking findings — these become the `residual_findings` the reviser fixes on a `revise`. Keep both the synthesized verdict (for `next_action`) and the full pre-reduction array (for the round's per-lens entries).

### 4c. Decide the next action

Pipe the round's synthesized verdict (as a one-element JSON array) into the already-existing loop-decision CLI:

```bash
printf '%s' '[{"pass":<round-pass>,"findings":<round-findings>}]' \
  | python3 scripts/qrspi_critic_loop.py --round <r> --max-rounds <MAX_ROUNDS>
```

It prints `{"action": ..., "residual_findings": [...]}` where `action` is one of:

- `converged` — the round passed. Stop the loop; this is the terminal action.
- `cap_reached` — the round did not pass and this was the last allowed round. Stop the loop; `residual_findings` are the surviving findings. This is the terminal action.
- `revise` — the round did not pass and rounds remain. Go to Step 4d, then start the next round (`r + 1`).

Record this round's **per-lens** entries — append every element of the round's pre-reduction verdict array (from 4a) to the accumulated `rounds` list, each of the shape `{"lens": "<lens-id>", "pass": <bool>, "findings": [...]}`. Do NOT collapse the round to one synthesized entry: the ledger summary (`qrspi_critic_summary.summarize`) buckets per-lens dissent on `rnd["lens"]`, so the round must contribute one entry per lens (N lenses × R rounds). The accumulated list is the `rounds` argument for Step 6.

### 4d. Revise (shared non-producer reviser)

On `revise`, spawn the **shared non-producer reviser** (`qrspi-critic-reviser`) to rewrite the scratch copy in place using the round's residual findings as guidance — NOT the producer. Spawn via the `Agent` tool:

- `subagent_type: qrspi-critic-reviser`
- Prompt body carrying:
  - `PHASE = design`
  - `OUTPUT_PATH = /tmp/phase-stage/<ticket-id>/review/design.md` (the scratch copy — the ONLY path it may write, verbatim)
  - `RESIDUAL_FINDINGS` = the round's `residual_findings` from 4c — node-validity/fidelity findings ONLY (decision-readiness is partitioned out and never reaches the reviser).
  - `RESEARCH_PATH = <RESEARCH>`
  - `CODEBASE_PATH = <worktreeDir>`
  - `QUESTIONS_PATH = <QUESTIONS>` (only if the file exists)
  - `TICKET_CONTENT_PATH = <TICKET_CONTENT>`
  - `DESIGN_PATH = /tmp/phase-stage/<ticket-id>/review/design.md`
  - `TEMPLATE_PATH = <worktreeDir>/.qrspi/templates/design.md`

The reviser reads the scratch design + supplied inputs, addresses each residual finding, and writes the revised design back to `OUTPUT_PATH` verbatim. Then continue to the next round against the rewritten scratch copy.

## Step 5 — Decision-readiness lens (terminal-advisory)

After the loop terminates (`converged` or `cap_reached`), spawn the **non-producer decision-readiness lens** over the final scratch design. This **replaces** the old self-grading open-question pass (where the producer free-text "answered" its own open questions). It is design-phase-specific (the plan/impl review commands omit it) and **terminal-advisory**: its verdict feeds the synopsis ONLY and triggers NO reviser round.

Spawn via the `Agent` tool:

- `subagent_type: qrspi-design-critic-decision-readiness`
- Prompt body carrying:
  - `DESIGN_PATH = /tmp/phase-stage/<ticket-id>/review/design.md`
  - `TICKET_CONTENT_PATH = <TICKET_CONTENT>`
  - `RESEARCH_PATH = <RESEARCH>`
  - `QUESTIONS_PATH = <QUESTIONS>` (only if the file exists)
  - `CODEBASE_PATH = <worktreeDir>`

It returns a `DecisionReadinessVerdict` — `{"lens":"decision-readiness", "blockingDecisions":[{question, rationale}], "answerable":[{question}]}`, NOT the `{pass, findings}` shape. Capture this verdict for the synopsis (Step 7). It is NOT fed to synthesize and does NOT change the loop's terminal action.

## Step 6 — Build and append the ledger record

Compute the panel↔human agreement and build the agreement-extended record, then append it to the per-ticket ledger.

The panel verdict for agreement is the **terminal** round's pass: `true` when the loop ended `converged`, `false` when it ended `cap_reached`.

Build the record in Python so the shapes are exact (the helpers are pure and self-locating). The `rounds` argument is the **accumulated per-lens entries** from Step 4c (N lenses × R rounds). After `build_record`, MERGE the additive axis/non-blocking fields derived from the **last round's** pre-reduction verdict array via `ledger_row_fields()` onto the record dict (they are additive — `qrspi_critic_summary.summarize` reads via `.get()` and is unaffected):

```bash
python3 - <<'PY'
import json, sys
sys.path.insert(0, "scripts")
import qrspi_review_agreement, qrspi_review_record, qrspi_review_synopsis

panel_pass = <True if converged else False>
human_decision = <DESIGN_REVIEW_DECISION or None>   # the gh reviewDecision string, or None
rounds = <the accumulated list of per-lens {"lens","pass","findings"} entries from Step 4c>
terminal_action = "<converged|cap_reached>"          # the loop's terminal action verbatim
last_round_verdicts = <the FINAL round's pre-reduction per-lens verdict array from Step 4a>

agreement = qrspi_review_agreement.compute(panel_pass, human_decision)
record = qrspi_review_record.build_record(
    phase="design", rounds=rounds,
    terminal_action=terminal_action, agreement=agreement)
# Merge the OPTIONAL additive fields (axes + nonBlockingNotes) onto the record.
record.update(qrspi_review_synopsis.ledger_row_fields(last_round_verdicts))
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

## Step 7 — Render and post the advisory synopsis comment

Render the **axis-enumerated** synopsis via `render_synopsis()` (the honest, per-lens body) and wrap it with the advisory header + agreement line, writing the result to a scratch markdown file (so you never quote markdown on a command line). The renderer is fed the **final round's pre-reduction per-lens verdict array** (so every lens appears as an axis row, not just the reduced verdict), the **decision-readiness verdict** from Step 5, and the loop's **terminal action**:

```bash
python3 - <<'PY' > /tmp/phase-stage/<ticket-id>/review/synopsis-design.md
import json, sys
sys.path.insert(0, "scripts")
import qrspi_review_synopsis

last_round_verdicts = <the FINAL round's pre-reduction per-lens verdict array from Step 4a>
decision_readiness = <the DecisionReadinessVerdict dict from Step 5>
terminal_action = "<converged|cap_reached>"
agreement_line = "<panel verdict vs. human reviewDecision, or 'pending — no human review yet'>"

print("## Advisory design review (propose-only — no branch changes)\n")
print(qrspi_review_synopsis.render_synopsis(
    last_round_verdicts, decision_readiness, terminal_action))
print("\n**Agreement:** " + agreement_line)
PY
```

The rendered body contains, in order: the **Review axes** table (one row per lens — `completeness`, `internal-consistency`, `edge-alignment`, `simplicity`, `design-review` — each with PASS/FAIL + blocking finding count), an **Advisory (non-blocking)** section (the union of all panel lenses' `nonBlockingNotes`, when any), a **Decision readiness (blocking for human)** section (the decision-readiness lens's `blockingDecisions`, each with its rationale), the **Terminal action**, and the **Agreement** line you appended. Post it as a **top-level** PR comment (toplevel mode does not need a parent comment id — Slice 1 relaxed `--comment-id` to optional; `--ticket` and `--reply-mode` remain required):

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
5. **Decision-readiness is terminal-advisory.** Its verdict is partitioned out of the synthesize array (`partition_decision_readiness()`) and feeds the synopsis ONLY — it must never drive a `revise` round or change the loop's terminal action.
6. **`TICKET_CONTENT_PATH` is scoped.** Pass it to the coverage/fidelity/decision-readiness lenses (`completeness`, `edge-alignment`, `decision-readiness`) and the reviser ONLY. The node-validity `design-review` lens (and `internal-consistency`/`simplicity`) stay research+code-only — do not pass the ticket to them.
7. This command is **advisory**. It does not change Linear status and does not advance the PR-gated lifecycle — a human reviewer still owns the approval.
