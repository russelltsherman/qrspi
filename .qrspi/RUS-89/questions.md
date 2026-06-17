# Questions — Phase review-panel commands (/review-*): on-demand node-validity review panels

**Ticket:** RUS-89
**Generated:** 2026-06-17T00:00:00Z
**Status:** draft

## Data Flow

- Q1: What does `qrspi_resolve.py` return in its envelope, and which fields identify the worktree path, the phase artifact path, and the phase PR for a given ticket id — i.e. what is already available to a `/review-<phase>` command without re-deriving it?
  **Target:** scripts/qrspi_resolve.py (and its envelope shape)
- Q2: How does the existing batch path locate and read each phase artifact (`design.md`, `plan.md`, slice diffs) for a ticket, and where do those artifacts live on disk relative to the resolved worktree?
  **Target:** the module/script responsible for phase-artifact location (qrspi_persist.py and qrspi-batch.js)
- Q3: How does the current `qrspi-design-critic-design-review` node-validity lens receive its inputs (artifact contents, codebase access, ticket/upstream context) and what format does it emit?
  **Target:** .claude/agents/ (the qrspi-design-critic-design-review agent definition)

## API Surface

- Q4: What is the input/output contract of `qrspi_critic_synthesize.py` — what does it consume from the panel agents and what synthesized structure does it produce?
  **Target:** scripts/qrspi_critic_synthesize.py
- Q5: How are panel lens agents currently spawned and orchestrated in the batch path (`runCriticPanelLoop` / `runCriticLoop`), and what is the existing interface for invoking a single lens against an artifact?
  **Target:** .claude/workflows/qrspi-batch.js (runCriticPanelLoop / runCriticLoop)
- Q6: How are slash-command wrappers in `.claude/skills/` structured to accept a ticket id argument and invoke their underlying agent/workflow, so a new `/review-design <id>` family follows the same convention?
  **Target:** .claude/skills/ (existing qrspi-* skill wrappers)

## State Management

- Q7: What is the schema and write mechanism of the RUS-78 agreement ledger that AC2 requires reuse of — where is it stored, what records a "structured verdict", and how is panel-vs-human agreement keyed?
  **Target:** the module responsible for the RUS-78 ledger (verdict/agreement logging)
- Q8: How does the loop-until-stable mechanism in the batch critic path track round count and detect "stable", and what state does it carry between rounds that a `≤3 round` scratch-copy loop would need to replicate?
  **Target:** the module responsible for the critic loop iteration/termination (qrspi-batch.js)
- Q9: What are the RUS-78 cost levers (`digest` / `lensModel`) referenced in the constraints — where are they configured and how does a panel run consume them?
  **Target:** the module/config responsible for digest and lensModel settings

## Edge Cases

- Q10: How does `qrspi_resolve.py` behave when the requested phase artifact does not yet exist or the phase PR is absent (e.g. `/review-plan` invoked before the plan PR exists) — does it error, return a sentinel, or partial envelope?
  **Target:** scripts/qrspi_resolve.py
- Q11: How is the "frontier" phase determined for `/review` (comprehensive) and `/review-implementation`, and what happens when the stack is partially built or partially landed (some PRs merged, top slice open)?
  **Target:** scripts/qrspi_resolve_state.py and scripts/qrspi_pr_state.py
- Q12: For AC1's "scratch copy" requirement, how does the existing harness create an isolated working copy of an artifact/worktree without mutating or pushing the open PR branch, and what mechanism guarantees no push occurs?
  **Target:** the module responsible for worktree/scratch isolation (qrspi-batch.js, using-git-worktrees usage)

## Testing

- Q13: What deterministic seams in the existing critic/synthesis path already have stdlib `scripts/*_test.py` coverage, and how do those tests stub the agent invocations so a new verdict/agreement reducer test follows the same pattern?
  **Target:** scripts/qrspi_critic_synthesize_test.py and scripts/run_tests.py

## Observability

- Q14: How does the batch path currently post a synopsis/comment to a phase PR (which script/command and which PR), so the advisory synopsis comment for AC1/AC3/AC4/AC5 reuses the same posting mechanism?
  **Target:** scripts/qrspi_comment_reply.py (and the PR-comment posting path in qrspi-batch.js)
- Q15: What does the RUS-78 ledger record per run that enables a future data-gated decision (verdict, agreement, round count, which lens fired), and where can a human inspect those logged records?
  **Target:** the module responsible for the RUS-78 ledger storage/output
