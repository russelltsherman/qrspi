# Design — Fix run_loop.sh agent path references

**Ticket:** RUS-35
**Research basis:** research.md @ 2026-06-09T00:00:00Z
**Generated:** 2026-06-09T00:00:00Z
**Status:** revision-1

## Current State

`run_loop.sh` is a top-level shell driver that takes two required positional
args — `SKILL_PATH` (`$1`) and `EVAL_SUITE` (`$2`) — guarded with `${N:?Usage:…}`,
plus two optional args (`max_iter` default 5, `target_score` default 0.85) and two
env knobs (`TRIALS`, `WORKERS`) (ref: Q1, Q3). `SKILL_PATH` is echoed in the banner
and passed verbatim as `--skill` to `run_eval.py`, `diagnose.py`, and `revise.py`
(the latter also `--output "$SKILL_PATH"`, so revisions write back in place); the
shell never opens the file — `run_eval.load_skill()` does the bare `open()` (ref: Q1).
The path is used verbatim: no `cd`, no base-dir prefix, no `realpath`/env resolution,
so the effective contract is "run from repo root" (ref: Q5).

The header comment documents usage on line 7 and carries a worked example. The
ticket asserts the stale agent path lives on line 9; research confirms it is
actually on **line 10** — line 9 is the bare `#   Example:` comment (ref: Q3, Q8).
That line 10 example reads `.qrspi/agents/01-questions.md evals/suite.json 5 0.85`,
and it is the **sole** occurrence of `.qrspi/agents/` in the file — no other
comment, default, or fallback references it (ref: Q8). Neither the directory
`.qrspi/agents/` nor the filename `01-questions.md` exists on disk; agent files
live at `.claude/agents/qrspi-<phase>.md` (8 files including `qrspi-questions.md`),
the layout documented in `.claude/CLAUDE.md` (ref: Q6).

No active caller invokes `run_loop.sh` — a repo-wide grep found only the script
itself plus prose mentions in prior-ticket artifacts; no workflow, Makefile, or CI
executes it (there is no `.github/`) (ref: Q4). The example string is never emitted
to stdout/stderr — the banner echoes the runtime `SKILL_PATH` *value*, and the
usage guards print the `<skill_path>` placeholder, not the literal stale path
(ref: Q12). There is no test, smoke check, ShellCheck config, or CI covering the
script; no test asserts on the path string or header (ref: Q10). `evals/suite.json`
exists (valid 15-case `qrspi-agent-evals` suite) and contains zero agent-path
references — the agent is injected at runtime via `--skill`, never embedded
(ref: Q11). The eval runtime itself is a non-functional placeholder:
`run_eval.execute_single()` returns empty output and zeroed metrics (ref: Q9).

## Dependency & Merge Ordering

This ticket carries a hard dependency on the **runtime ticket** that makes the eval
executor functional (`run_eval.execute_single()` is a placeholder today, ref: Q9).
Per the resolved reviewer answer (RQ1), **this ticket will not merge before the
runtime ticket.** The doc fix is authored and reviewed independently now, but its
merge/land is gated behind the runtime ticket so that AC1's documented invocation is
*live* — not merely compilable — at land time. Concretely: this design and its PR
proceed immediately; the stack is held until the runtime ticket lands, then this
lands on top of it. Merge order is therefore fixed (runtime first), which is why the
AC1 note below reads "once the runtime ticket lands" and why the AC1 risk row is no
longer open.

## Desired End State

The acceptance criteria map to behavior as follows:

- **AC1 — `./run_loop.sh .claude/agents/qrspi-questions.md evals/suite.json` runs
  without errors (once the runtime ticket lands).** The corrected example path now
  names a file that exists on disk (ref: Q6). All five shelled scripts, the suite,
  and the skill file are present, so the driver runs to completion (ref: Q9). Note
  the runtime is a placeholder, so "without errors" means the shell driver completes
  — not that meaningful evaluation occurs (ref: Q9). This design changes only the
  comment text; it does not make the stub runtime functional (that is the dependency
  ticket's scope). The "once the runtime ticket lands" qualifier is fixed by the
  resolved merge ordering (RQ1) — see **Dependency & Merge Ordering** — so this is a
  settled constraint, not an open caveat.
- **AC2 — Header comment references the correct path.** The example comment is
  updated to `.claude/agents/qrspi-questions.md`, matching the canonical on-disk
  layout (ref: Q6) and the AC1 invocation.
- **AC3 — Any other `.qrspi/agents/` references in the script are updated.** Research
  confirms exactly one occurrence (line 10); updating it fully removes the stale
  token from the file (ref: Q8). No other references exist to update.

After the change, `grep -n ".qrspi/agents/" run_loop.sh` returns nothing, and the
header example is copy-pasteable into a working invocation.

## Delta

- **Modified file: `run_loop.sh` (line 10, the `#   Example:` body).** Replace
  `.qrspi/agents/01-questions.md` with `.claude/agents/qrspi-questions.md`. The rest
  of the example line (`evals/suite.json 5 0.85`) is correct and stays. This is a
  single-line comment edit; no executable code, arg parsing, or control flow changes.
- **No change to `evals/suite.json`** — it is agent-agnostic (ref: Q11).
- **No change to the Python scripts** — the path flows through `--skill` unchanged
  (ref: Q1).
- **No new files, queries, or registrations.**
- **Scope boundary (RQ2 — keep scope):** per the resolved reviewer answer, the change
  stays **strictly doc-only** — the single-line comment correction above is the entire
  delta. It does not expand into correcting the ticket text's own line-9/line-10 error
  (handled robustly by anchoring on the unique literal string, Decision 1), adding a
  `SKILL_PATH` existence guard (Decision 2 Option A stands), or introducing a
  ShellCheck/CI gate (Decision 3 Option A stands).
- **Verification artifact (manual):** because no automated gate covers the script
  (ref: Q10), record a manual check — `grep -n ".qrspi/agents/" run_loop.sh` returns
  empty, and a dry invocation of the documented command — as the acceptance evidence.

## Pattern Decisions

### Decision 1: How to target the stale reference for editing

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Edit by matching the literal example string `.qrspi/agents/01-questions.md` and replacing the path segment | Robust to the line-9/10 discrepancy; string-anchored, not line-anchored | Requires the exact stale string to match |
| B | Edit by line number (line 10) | Direct | Ticket said line 9; line-number drift risk if file changes upstream (ref: Q3) |

**Recommendation:** Option A
**Rationale:** Research found a concrete line-number mismatch between the ticket
(line 9) and the file (line 10) (ref: Q3, Q8). Anchoring on the unique literal
string sidesteps that ambiguity entirely and matches the "single occurrence"
finding (ref: Q8). This is the standard exact-string-replacement convention.
**NEW PATTERN?** No — ordinary in-place comment edit.

### Decision 2: Whether to add a file-existence guard for `SKILL_PATH`

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Leave validation as-is (fails inside `run_eval.load_skill()` with a Python traceback) | Stays within ticket scope (doc-only fix); matches existing fail-fast convention via `set -euo pipefail` (ref: Q5, Q7) | A bad path still surfaces as a late Python error, not a friendly shell message (ref: Q7) |
| B | Add `[ -f "$SKILL_PATH" ]` guard emitting a shell-level error | Friendlier failure for a missing agent file | Scope creep beyond the ticket; new behavior with no test to cover it (ref: Q10) |

**Recommendation:** Option A
**Rationale:** The ticket is a documentation-string correction; the acceptance
criteria say nothing about validation behavior. The existing convention is
caller-responsibility validation with fail-fast Python errors (ref: Q7). Adding a
guard expands surface area with no requested benefit and nothing to test it.
**NEW PATTERN?** No — preserves the existing arg-guard convention (ref: Q7).

### Decision 3: How to verify the fix given no automated gate

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Manual grep + documented dry invocation, recorded in the PR | Matches project convention (harness verified by manual e2e + unit tests) (ref: Q9, Q10) | Not regression-protected by automation |
| B | Add a ShellCheck config / smoke test asserting no `.qrspi/agents/` remains | Regression protection going forward | No CI exists to run it (no `.github/`); larger scope than the ticket (ref: Q10) |

**Recommendation:** Option A
**Rationale:** No CI or ShellCheck config exists (ref: Q10), and the project
explicitly verifies this harness via manual e2e per `.claude/CLAUDE.md` (ref: Q9).
A grep check plus a documented invocation is proportionate to a one-line comment fix.
**NEW PATTERN?** No — matches the documented manual-verification posture.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Edit targets line 9 (per ticket) instead of the actual line 10, missing the stale path | med | high | Anchor the edit on the unique literal string `.qrspi/agents/01-questions.md`, not on line number (Decision 1); confirm with `grep -n ".qrspi/agents/" run_loop.sh` returning empty (ref: Q3, Q8) |
| "Runs without errors" misread as "produces real eval results" | med | med | Design explicitly scopes AC1 to the shell driver completing; the executor is a placeholder and this ticket does not change it (ref: Q9) |
| A second `.qrspi/agents/` reference is missed | low | med | Research confirms exactly one occurrence; re-verify post-edit with grep (ref: Q8) |
| AC1 invocation cannot be exercised until the dependency "runtime ticket" lands | med | low | Resolved by RQ1: merge ordering is fixed — this ticket lands *after* the runtime ticket, so AC1 is verifiable live at land time; AC2/AC3 (the comment fix) remain independently verifiable now (ref: Q9, RQ1) |

## Resolved Questions

Both open questions were answered by the design reviewer and are now resolved; the
answers are folded into the design body above — RQ1 into the **Dependency & Merge
Ordering** section (and the AC1 note + risk row), RQ2 into the **Delta** scope-boundary
bullet. This appendix records the verbatim question/answer pairs for traceability.

- **RQ1 (was OQ1) — Merge ordering relative to the runtime ticket.**
  *Question:* Should this PR be held/merged before the runtime ticket, or land
  independently as a doc-only fix? AC2/AC3 are satisfiable immediately; only AC1's live
  invocation depends on the runtime work.
  *Answer (reviewer):* **This ticket will not merge before the runtime ticket.** The
  doc fix is authored independently, but its merge/land is gated behind the runtime
  ticket so that AC1's documented invocation is live (not just compilable) when this
  lands. Practically: this design and its PR proceed now, but the stack is held until
  the runtime ticket has landed, then this lands on top of it. This sharpens the AC1
  note ("once the runtime ticket lands") and the risk-register row about deferred AC1
  verification — they are no longer open: the order is fixed (runtime first).

- **RQ2 (was OQ2) — Scope.**
  *Question:* Should the scope stay strictly doc-only, or also fix the ticket's own
  line-9/line-10 error?
  *Answer (reviewer):* **Keep scope.** Stay strictly doc-only — the single-line
  comment correction in `run_loop.sh` (Delta) is the entire change. Do not expand into
  the ticket-text line-number correction, a validation guard (Decision 2 Option A
  stands), or a ShellCheck/CI gate (Decision 3 Option A stands). The line-9/line-10
  discrepancy is already handled robustly by anchoring on the unique literal string
  (Decision 1), so no separate fix is warranted within this ticket.
