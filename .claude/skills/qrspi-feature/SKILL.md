---
name: qrspi-feature
description: "The front door for NEW feature work in QRSPI — start here whenever someone wants to turn a feature idea or request into Linear ticket(s). Use when the user says 'create tickets for <feature>', 'I want to build <feature>', 'let's add <capability>', 'break this feature into tickets', 'plan out <feature>', or hands you a feature with no ticket yet. This ALSO covers feature-scale work phrased as a direct imperative — 'let's migrate <system> to <X>', 'ship/distribute <thing> as a <Y>', 'rework/redesign <subsystem>' — when there is no ticket yet: such work must be ticketed and its decomposition reviewed here BEFORE it is built, never freelanced into an unreviewed split (the exact failure this skill prevents). It elicits requirements, then proposes a REVIEWED decomposition (one ticket vs many, a dependency DAG, and an overlap scan against in-flight work) and STOPS for your approval before any Linear write. For a single, already-scoped ticket the user explicitly wants filed as one, /qrspi-ticket is the direct entry; for a whole feature that might split or carry dependencies, this is the skill, even if the user only says 'make tickets'. (For progressing an EXISTING ticket — 'work on RUS-42' — that's /qrspi-work, not this.)"
command: /qrspi-feature
argument-hint: <feature description>
allowed-tools: Read, Glob, Grep, Write, Bash, Skill, mcp__linear__save_issue, mcp__linear__list_issues, mcp__linear__list_teams
---

# Feature Intake (the front door)

You are QRSPI-Feature, the **sole documented entry point** for new feature work. The user has
described a feature: "$ARGUMENTS"

## Why this skill exists

Everything downstream of a ticket — questions, research, design, structure, plan, slices — is
heavily gated and reviewed. The **ticket boundary itself is not**. Yet *how a feature splits into
tickets* is the highest-leverage, least-reversible decision in the whole pipeline: every ticket
boundary is a **concurrency edge**, and an undeclared dependency between two tickets that touch
the same files produces divergent, mutually-incompatible designs that *cannot both land* (this is
the exact failure this skill exists to prevent — two tickets were split from one feature by an
unstructured "create tickets for X" with no plan and no gate, and each was carried all the way to
an open PR before the conflict surfaced).

So this skill front-loads rigor onto the **decomposition**: it produces a reviewable plan and
**stops for human approval before any Linear write**. The plan — a one-page DAG + overlap flags —
is deliberately right-sized so it *can't* be rubber-stamped as blindly as two full drafted
tickets would be. **Garbage in, garbage out:** a mis-decomposed feature propagates through all the
downstream rigor and emerges as a polished, conflicting artifact.

## The flow — four steps, one hard gate

```
1. Elicit requirements   (conversation; persist requirements.md)
2. Propose decomposition (zero Linear writes; persist decomposition.md)
3. ── HUMAN REVIEW GATE ──  approve / edit the PLAN before any Linear write   ← the checkpoint
4. Commit                (only on approval: parent issue + tickets via shared writer + edges)
```

Steps 1–3 touch **no** Linear state. The first Linear write happens in step 4, *after* explicit
approval. Do not collapse the gate: drafting tickets that follow the decomposition automatically
rebuilds the exact trap with more ceremony. **The approval is a hard stop.**

---

## Step 0 — Name the feature, pick a slug

From the description, restate the feature in 1–2 sentences and propose a short kebab-case **slug**
(e.g. *"distribute QRSPI as a Claude Code plugin"* → `plugin-distribution`). Confirm or adjust it
with the user. All intake artifacts for this feature live under `.qrspi/features/<slug>/` — this
mirrors the `.qrspi/` artifact convention and makes the approved plan auditable. Create the
directory: `mkdir -p .qrspi/features/<slug>`.

## Step 1 — Elicit requirements (proportionate)

Interview the user at the **feature** level — once. The goal is enough shared understanding to
decompose well, not a heavyweight spec. **Match the ceremony to the feature's size** — friction
that gets skipped is worse than no process, and over-eliciting a small feature trains people to
bypass the front door.

Cover, briefly: **goal** (what this enables, for whom), **constraints** (architectural, deadline,
backward-compat), **acceptance criteria** (observable outcomes), and **known risks** (shared
files, layered dependencies, anything that smells like "these parts must serialize").

- For a genuinely **large** feature, use the `writing-prds` skill to structure the elicitation.
  For anything smaller, keep it light — a few targeted questions, never more than two at once.
- Stay in the **problem space**. Like `qrspi-ticket`, do not design the solution here; technical
  approaches emerge in the downstream Design phase. You need enough to judge *how the work splits*,
  not *how it's built*.

Persist the result to `.qrspi/features/<slug>/requirements.md` (goal, constraints, acceptance,
risks). This is the input to the decomposition and to every ticket you later write.

## Step 2 — Propose a decomposition (NO Linear writes)

Produce a one-page proposal. This is analysis only — **make zero Linear writes in this step.**
Read `references/decomposition.md` for the proposal template, the overlap-scan procedure, and
worked examples. The proposal has four parts:

1. **Unit recommendation + rationale** — one ticket (with a slice sketch) vs N tickets, and *why*.
   **Bias hard toward ONE ticket with slices** (see [Decomposition default](#decomposition-default-d3)).
2. **Dependency DAG** (multi-ticket only) — who blocks whom, and the concrete reason (usually:
   B reads a file/interface A creates or rewrites). Each edge becomes a Linear `blockedBy`
   relation in step 4.
3. **Overlap / duplication scan** — query in-flight Linear tickets and flag any that the proposed
   work duplicates or collides with. Procedure in `references/decomposition.md`. This is the check
   that catches "this overlaps an existing in-flight ticket" *before* you create a conflicting one.
4. **Risk flags** — shared files, layered architecture, anything signalling "these must serialize."

Persist the proposal to `.qrspi/features/<slug>/decomposition.md` so the approved plan is
auditable. Then present it inline and proceed to the gate.

## Step 3 — HUMAN REVIEW GATE (hard stop)

Present the decomposition plan and **stop**. Ask the user to approve or edit **the plan** — the
unit split, the DAG edges, the overlap findings — *not* drafted tickets (there are none yet, by
design; reviewing a tight plan is harder to rubber-stamp than two polished tickets).

> "Here's the proposed decomposition. Reply 'approved' to create the ticket(s) as laid out, or
> tell me what to change (the split, the dependencies, the scope)."

Do **not** proceed to any Linear write until the user explicitly approves. If they edit, revise
`decomposition.md` and re-present. This gate is the entire point of the skill — it must not be
auto-skipped into drafting.

## Step 4 — Commit (only on approval)

Now, and only now, write to Linear. Resolve the destination team/project **once** (the shared
writer's Step A) and reuse it for every issue below.

### Single-ticket case (the common, preferred outcome)

No parent container — a parent with one child is noise. Follow `references/writer.md`
(the shared writer) once: `draft` = the single ticket, no `parentId`, no `blockedBy`. Report the
created `<id>` and point the user at `/qrspi-questions <id>`.

### Multi-ticket case

1. **Create the parent container** (D5 — a Linear **parent issue**, not a Project; a Project would
   collide with the existing `linearProject` batch-scoping). Call `mcp__linear__save_issue` with
   `title` = the feature name, `description` = the requirements summary, `team`/`project` =
   resolved destination. Do **NOT** assign it or set its state to `Selected` — the parent is an
   inert container, and the resolver's entry-gate only admits *assigned* + `Selected` tickets, so
   an unassigned parent is never picked up as work. Capture its identifier as `<parentId>`.

2. **Create the child tickets in dependency order — blockers first.** A `blockedBy` edge can only
   reference an already-created ticket, so topologically sort the DAG and create upstream tickets
   before the tickets that depend on them. For each ticket, follow `references/writer.md` with:
   `draft` = that ticket's draft, `parentId` = `<parentId>`, and `blockedBy` = the identifiers of
   its already-created blockers per the approved DAG. The writer sets `assignee: "me"` and creates
   `.qrspi/<id>/` for each.

   Because every dependent carries its `blockedBy` edge, the resolver serializes them
   automatically: a blocked ticket stays `entry_blocked` (never enters `run_design`) until its
   blocker's stack fully lands and the blocker reaches a `completed` status type. This is the
   mechanism that would have prevented the original collision.

3. If any `save_issue` fails, the writer STOPs and reports it. A half-built dependency chain is
   worse than none — surface exactly which tickets were created and let the user decide whether to
   continue or unwind; never silently push on.

4. Report the result: the parent `<id>`, each child `<id>` with its blockers, and that the user
   moves a ticket to `Selected` (and `/qrspi-questions <id>` or `qrspi-batch`) when ready to start
   it. Blocked children can be selected immediately — the entry-gate holds them until unblocked.

---

## Decomposition default (D3)

**Bias hard toward ONE ticket with slices. Create separate tickets ONLY when parts have genuinely
independent review and landability.**

QRSPI already serializes work *within* a single ticket: a ticket is one Graphite stack of slices,
built and landed bottom-up, each slice its own reviewed PR. So "this feature has several steps
that must happen in order" is **not** a reason to split — that is precisely what a slice stack is
for, and keeping it in one ticket means one held-open stack with no cross-ticket concurrency edge
to mis-manage.

Split into separate tickets only when the parts are genuinely **independent** — each could be
reviewed, approved, and landed on its own schedule without waiting on the other, and they don't
rewrite the same files. A **strict chain** of fully-dependent tickets (A blocks B blocks C, each
needing the last) is a strong signal the work should have been **one ticket's slice stack** — if
you find yourself drawing a single line through every ticket, collapse it back to one ticket.

Every ticket boundary you create is a concurrency edge someone has to get right. Don't create them
casually. When in doubt: one ticket, more slices.

## Hard rules

- **No Linear write before the gate.** Steps 0–3 are analysis and conversation only. The overlap
  scan in step 2 *reads* Linear (`list_issues`); it never writes.
- **The gate is a hard stop.** Never proceed from the decomposition to ticket creation without an
  explicit user approval of the plan.
- **The shared writer is the only way tickets reach Linear.** Do not inline `save_issue` field
  mapping here — follow `references/writer.md` so `qrspi-ticket` and `qrspi-feature` stay in sync.
- **Stay in the problem space during elicitation.** Solutions are the Design phase's job.
- If a Linear read or write fails for an infrastructure reason (auth, config, tooling), STOP and
  print the exact error — do not improvise around it.
