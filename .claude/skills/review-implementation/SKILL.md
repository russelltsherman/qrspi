---
name: review-implementation
description: On-demand advisory review of a QRSPI ticket's IMPLEMENTATION (the slice stack). Run the full read-only implementation review panel (node-validity + fidelity + completeness lenses) over the implemented code + tests against the real codebase, iterate a non-producer reviser until the panel converges, then post ONE rolled-up axis-enumerated advisory synopsis comment to the top slice PR and append an agreement-extended ledger row — WITHOUT mutating any PR branch. Use whenever the user asks to review, critique, sanity-check, validate, or get a second opinion on a ticket's implementation/code (e.g. "/review-implementation RUS-89", "review the implementation for RUS-42", "is the code for RUS-50 correct?", "run the impl panel on RUS-7"). This is the implementation-phase entry of the /review-* family; for the design use /review-design, for the plan use /review-plan, for the whole stack use /review.
allowed-tools: Agent, Bash, Read, mcp__linear__get_issue
---

# /review-implementation

Run an **advisory, propose-only** review of a ticket's implementation (its slice stack) and post a single rolled-up synopsis to the top slice PR. This is the implementation-phase member of the `/review-*` family. It is deliberately **read-only with respect to every branch**: it spawns the review panel and a shared non-producer reviser against a *scratch copy* of the implementation record, never the tracked files, and it posts a PR **comment** — it never runs `gt submit`, `gt modify`, or any `gh` write that mutates a branch. The top slice PR head SHA must be identical before and after a run.

The point is to give a human reviewer a sharp, evidence-grounded second opinion (is the implemented code materially WRONG — incorrect, insecure, inefficient, or unfit for its stated scale — against the real code and its tests?) across the **full implementation panel** — the node-validity `impl-review`, `impl-fidelity`, and `impl-completeness` — run **once over the aggregated slice stack** (not per-slice), and to record whether the panel and the human ended up agreeing — all without touching the work itself. (There is **no** decision-readiness lens for the implementation phase — that lens is design-phase-only.)

## Inputs

Parse `$ARGUMENTS` for a single `<ticket-id>` (Linear format, e.g. `RUS-89`). If it is missing, ask the user for it and stop.

## Overview of the run

```
resolve → derive top slice PR number (via gh pr list --state all) → scratch-copy the impl record → stage ticket text
  → loop rounds 0..2: fan out the 3-lens impl panel (over the aggregated stack) → partition decision-readiness (guard)
        → synthesize the PANEL array → next_action
        revise ⇒ spawn qrspi-critic-reviser (PHASE=impl) to rewrite the scratch copy, continue
        converged / cap_reached ⇒ stop the loop
  → build agreement-extended ReviewRecord (per-lens rounds) + merge axes/nonBlockingNotes → append to the ledger
  → render the axis-enumerated synopsis → post ONE rolled-up advisory comment to the top slice PR
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
- `TICKET_CONTENT` = `/tmp/phase-stage/<ticket-id>/review/ticket.md` (staged in Step 3 — passed to the fidelity/completeness lenses ONLY, never the node-validity `impl-review` lens)

## Step 2 — Derive the top slice PR number and its human review decision

The implementation is a stack of slice PRs; the rolled-up synopsis goes to the **top** slice PR. Take the top slice branch from the envelope's `tip` (equivalently, the last element of `slices`), then derive its PR number from the branch. Resolve it with `--state all` (NOT the default open-only filter) so a partially-landed stack — where lower slice PRs have already merged but the top slice PR is open or itself merged — still resolves the correct frontier PR instead of misfiring as "no PR" (the partially-landed-stack misfire):

```bash
gh pr list --head <tip> --state all --json number,reviewDecision,state --jq '.[0]'
```

Capture `IMPL_PR` (`.number`) and `IMPL_REVIEW_DECISION` (`.reviewDecision`). GitHub returns `reviewDecision` as `APPROVED`, `CHANGES_REQUESTED`, `COMMENTED`, or `null`/empty when no human has reviewed yet — pass it straight through to the agreement reducer in Step 5, which normalizes it (a missing decision becomes `agreement: "pending"`, never a false disagreement). If `gh pr list --state all` returns no PR for `<tip>`, tell the user the top slice PR does not exist and stop.

Record the top slice PR head SHA now so you can confirm it is unchanged at the end (the propose-only invariant):

```bash
gh pr view <IMPL_PR> --json headRefOid --jq '.headRefOid'
```

## Step 3 — Make a scratch copy of the implementation record and stage the ticket text

The loop must never edit the tracked artifacts — the shared reviser rewrites a throwaway copy so every branch stays untouched. Copy the implementation record to a short, token-free scratch path:

```bash
mkdir -p /tmp/phase-stage/<ticket-id>/review
cp "<IMPL>" /tmp/phase-stage/<ticket-id>/review/impl-log.md
```

Use `SCRATCH` = `/tmp/phase-stage/<ticket-id>/review/impl-log.md` as the artifact under review everywhere below. The lens's primary evidence is the **real implemented source + tests** under `CODEBASE_PATH` (the worktree); the scratch record anchors what was built.

**Stage the ticket text.** Fetch the ticket via the Linear MCP and write its content to `TICKET_CONTENT` so the fidelity/completeness lenses can verify the implementation against the ticket's acceptance criteria:

- Call `mcp__linear__get_issue` with `id: <ticket-id>`.
- Write the issue's title + description (its full markdown body) to `TICKET_CONTENT` = `/tmp/phase-stage/<ticket-id>/review/ticket.md` (use the `Write` tool, not a shell heredoc, so the content is stored verbatim).

If the Linear fetch fails or the ticket has no description, write a short note to `TICKET_CONTENT` recording that the ticket text was unavailable and proceed — the lenses treat a missing/empty ticket as "no stated AC to check against" rather than failing. `TICKET_CONTENT` is passed to the `impl-fidelity` and `impl-completeness` lenses ONLY; the node-validity `impl-review` lens stays research+code-only (unchanged).

## Step 4 — The review loop (rounds 0..2)

The cap is **3 rounds** (`--max-rounds 3`). For each round `r` starting at `0`:

### 4a. Fan out the full implementation review panel

Spawn the **whole implementation review panel** (sourced from `DEFAULT_REVIEW_IMPL_LENSES` in `scripts/qrspi_critics_config.py`) — three lenses, each via the `Agent` tool. The lens id → agent mapping is `qrspi-impl-critic-<lens-id>`. All three lenses run **once over the AGGREGATED slice stack** — one panel pass over the whole implementation under `CODEBASE_PATH`, NOT per-slice — consistent with the single rolled-up synopsis posted to the top slice PR:

| Lens id | `subagent_type` | Gets `TICKET_CONTENT_PATH`? |
| --- | --- | --- |
| `impl-review` | `qrspi-impl-critic-impl-review` | **no** (node-validity stays research+code-only) |
| `impl-fidelity` | `qrspi-impl-critic-impl-fidelity` | yes |
| `impl-completeness` | `qrspi-impl-critic-impl-completeness` | yes |

For each lens, the prompt body carries the named PATH inputs (no `model` override — model selection is not wired in v1):

- `IMPL_PATH = /tmp/phase-stage/<ticket-id>/review/impl-log.md`
- `RESEARCH_PATH = <RESEARCH>`
- `CODEBASE_PATH = <worktreeDir>` — REQUIRED for all three; the fidelity/completeness lenses verify against the real implemented source + tests over the aggregated slice stack.
- `PLAN_PATH = <PLAN>` (only if the file exists)
- `STRUCTURE_PATH = <STRUCTURE>` (only if the file exists)
- `DESIGN_PATH = <DESIGN>` (only if the file exists)
- `QUESTIONS_PATH = <worktreeDir>/.qrspi/<ticket-id>/questions.md` (only if the file exists — `impl-completeness` consumes it)
- `TICKET_CONTENT_PATH = <TICKET_CONTENT>` — **ONLY** for the lenses marked "yes" above (`impl-fidelity`, `impl-completeness`). Do NOT pass it to the node-validity `impl-review` lens.

Each lens reads the scratch impl record + the **real implemented source and tests** under `CODEBASE_PATH` and returns exactly one `LensVerdict` — `{pass, findings}` (the fidelity/completeness lenses may also carry `nonBlockingNotes`). **Tag each verdict with its lens id** and collect them into the **pre-reduction verdict array** for this round:

```json
[
  {"lens":"impl-review","pass":<bool>,"findings":[...]},
  {"lens":"impl-fidelity","pass":<bool>,"findings":[...],"nonBlockingNotes":[...]},
  {"lens":"impl-completeness","pass":<bool>,"findings":[...],"nonBlockingNotes":[...]}
]
```

Keep this full pre-reduction array — it is the source for both the per-lens `rounds[]` entries (Step 5) and the axis-enumerated synopsis (Step 6).

### 4b. Synthesize the round's verdict

Reduce the round's pre-reduction verdict array to one authoritative verdict. The impl panel carries no decision-readiness lens, but apply `partition_decision_readiness()` as a harmless guard so a stray decision-readiness element (should one ever appear) is split out before synthesize:

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
  | python3 scripts/qrspi_critic_loop.py --round <r> --max-rounds 3
```

It prints `{"action": ..., "residual_findings": [...]}` where `action` is one of:

- `converged` — the round passed. Stop the loop; this is the terminal action.
- `cap_reached` — the round did not pass and this was the last allowed round. Stop the loop; `residual_findings` are the surviving findings. This is the terminal action.
- `revise` — the round did not pass and rounds remain. Go to Step 4d, then start the next round (`r + 1`).

Record this round's **per-lens** entries — append every element of the round's pre-reduction verdict array (from 4a) to the accumulated `rounds` list, each of the shape `{"lens": "<lens-id>", "pass": <bool>, "findings": [...]}`. Do NOT collapse the round to one synthesized entry: the ledger summary (`qrspi_critic_summary.summarize`) buckets per-lens dissent on `rnd["lens"]`, so the round must contribute one entry per lens (N lenses × R rounds). The accumulated list is the `rounds` argument for Step 5.

### 4d. Revise (shared non-producer reviser)

On `revise`, spawn the **shared non-producer reviser** (`qrspi-critic-reviser`) to rewrite the scratch copy in place using the round's residual findings as guidance — NOT the producer. Spawn via the `Agent` tool:

- `subagent_type: qrspi-critic-reviser`
- Prompt body carrying:
  - `PHASE = impl`
  - `OUTPUT_PATH = /tmp/phase-stage/<ticket-id>/review/impl-log.md` (the scratch copy — the ONLY path it may write, verbatim)
  - `RESIDUAL_FINDINGS` = the round's `residual_findings` from 4c — node-validity/fidelity findings ONLY.
  - `RESEARCH_PATH = <RESEARCH>`
  - `CODEBASE_PATH = <worktreeDir>`
  - `PLAN_PATH = <PLAN>` (only if the file exists)
  - `STRUCTURE_PATH = <STRUCTURE>` (only if the file exists)
  - `DESIGN_PATH = <DESIGN>` (only if the file exists)
  - `TICKET_CONTENT_PATH = <TICKET_CONTENT>`
  - `IMPL_PATH = /tmp/phase-stage/<ticket-id>/review/impl-log.md`

The reviser reads the scratch impl record + supplied inputs, addresses each residual finding, and writes the revised record back to `OUTPUT_PATH` verbatim. It is an **advisory propose-only** pass — it must NOT touch any tracked source or branch, only the scratch copy. Then continue to the next round against the rewritten scratch copy.

## Step 5 — Build and append the ledger record

After the loop terminates (`converged` or `cap_reached`), compute the panel↔human agreement and build the agreement-extended record, then append it to the per-ticket ledger.

(There is **no** post-loop decision-readiness pass for `/review-implementation` — that lens is design-phase-only. Go straight from the terminated loop to the ledger record.)

The panel verdict for agreement is the **terminal** round's pass: `true` when the loop ended `converged`, `false` when it ended `cap_reached`.

Build the record in Python so the shapes are exact (the helpers are pure and self-locating). The `rounds` argument is the **accumulated per-lens entries** from Step 4c (N lenses × R rounds). After `build_record`, MERGE the additive axis/non-blocking fields derived from the **last round's** pre-reduction verdict array via `ledger_row_fields()` onto the record dict (they are additive — `qrspi_critic_summary.summarize` reads via `.get()` and is unaffected):

```bash
python3 - <<'PY'
import json, sys
sys.path.insert(0, "scripts")
import qrspi_review_agreement, qrspi_review_record, qrspi_review_synopsis

panel_pass = <True if converged else False>
human_decision = <IMPL_REVIEW_DECISION or None>   # the gh reviewDecision string, or None
rounds = <the accumulated list of per-lens {"lens","pass","findings"} entries from Step 4c>
terminal_action = "<converged|cap_reached>"          # the loop's terminal action verbatim
last_round_verdicts = <the FINAL round's pre-reduction per-lens verdict array from Step 4a>

agreement = qrspi_review_agreement.compute(panel_pass, human_decision)
record = qrspi_review_record.build_record(
    phase="implementation", rounds=rounds,
    terminal_action=terminal_action, agreement=agreement)
# Merge the OPTIONAL additive fields (axes + nonBlockingNotes) onto the record.
record.update(qrspi_review_synopsis.ledger_row_fields(last_round_verdicts))
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

## Step 6 — Render and post the single rolled-up advisory synopsis comment

Render the **axis-enumerated** synopsis via `render_synopsis()` (the honest, per-lens body) and wrap it with the advisory header + agreement line, writing the result to a scratch markdown file (so you never quote markdown on a command line). The renderer is fed the **final round's pre-reduction per-lens verdict array** (so every lens appears as an axis row, not just the reduced verdict), `None` for decision-readiness (the implementation phase has no such lens), and the loop's **terminal action**:

```bash
python3 - <<'PY' > /tmp/phase-stage/<ticket-id>/review/synopsis-implementation.md
import json, sys
sys.path.insert(0, "scripts")
import qrspi_review_synopsis

last_round_verdicts = <the FINAL round's pre-reduction per-lens verdict array from Step 4a>
terminal_action = "<converged|cap_reached>"
agreement_line = "<panel verdict vs. human reviewDecision, or 'pending — no human review yet'>"

print("## Advisory implementation review (propose-only — no branch changes)\n")
print(qrspi_review_synopsis.render_synopsis(
    last_round_verdicts, None, terminal_action))
print("\n**Agreement:** " + agreement_line)
PY
```

The rendered body contains, in order: the **Review axes** table (one row per lens — `impl-review`, `impl-fidelity`, `impl-completeness` — each with PASS/FAIL + blocking finding count), an **Advisory (non-blocking)** section (the union of the fidelity/completeness lenses' `nonBlockingNotes`, when any), the **Terminal action**, and the **Agreement** line you appended — all rolled up across the whole slice stack into this one comment. (No decision-readiness section — `decision_readiness` is `None`, so `render_synopsis` omits it.) Post it as a single **top-level** comment to the **top slice PR** (toplevel mode does not need a parent comment id — Slice 1 relaxed `--comment-id` to optional; `--ticket` and `--reply-mode` remain required):

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
3. **One rolled-up synopsis.** Post exactly one comment, to the top slice PR — do not fan out a comment per slice. The panel itself also runs ONE pass over the aggregated slice stack, not per-slice.
4. **Fail closed and stop** if the implementation phase/slices/top-slice PR do not exist, if `resolve` errors, or if `qrspi_metrics_append.py` returns `ok:false`. Do not invent a PR number or a verdict.
5. **Resolve the frontier with `gh pr list --state all`.** The default open-only filter misfires on a partially-landed stack (lower slices merged, top slice open/merged) — always pass `--state all` when deriving the top slice PR number in Step 2.
6. **Build the ledger record only after the loop terminates** (`converged`/`cap_reached`); never with `revise`.
7. **`TICKET_CONTENT_PATH` is scoped.** Pass it to the fidelity/completeness lenses (`impl-fidelity`, `impl-completeness`) and the reviser ONLY. The node-validity `impl-review` lens stays research+code-only — do not pass the ticket to it.
8. **No decision-readiness lens.** That lens is design-phase-only; `/review-implementation` passes `None` as the decision-readiness argument to `render_synopsis()` and runs no post-loop decision-readiness pass. `partition_decision_readiness()` is still applied in Step 4b as a harmless guard.
9. This command is **advisory**. It does not change Linear status and does not advance the PR-gated lifecycle — a human reviewer still owns the approval.
