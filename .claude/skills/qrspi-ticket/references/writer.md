# Shared writer — materialize a QRSPI ticket in Linear

This is the single, shared procedure for turning an **approved ticket draft** into a real
Linear issue in QRSPI format. Two skills follow it:

- **`qrspi-ticket`** — interviews the user for one ticket, then runs this writer once.
- **`qrspi-feature`** — interviews once at the *feature* level, decomposes into N drafts, and
  runs this writer once **per draft** (passing a pre-seeded draft, plus a parent and any
  `blockedBy` edges).

Extracting the write here means the Linear-destination logic, the field mapping, and the
artifact-directory convention live in exactly one place — a fix to any of them is a fix for
both callers. The interview is *not* part of the writer: a caller supplies a finished draft
(freshly interviewed or pre-seeded) and the writer materializes it.

## Inputs

The caller provides:

- **draft** (required) — an approved ticket with: Title, Description (Context / Goal / Why Now),
  Acceptance Criteria, Constraints, Out of Scope. Format per `.qrspi/templates/ticket.md`.
- **parentId** (optional) — a Linear parent-issue identifier (e.g. `RUS-80`) to attach this
  ticket under as a sub-issue. `qrspi-feature` passes this for multi-ticket features; a single
  ticket has no parent.
- **blockedBy** (optional) — a list of Linear identifiers this ticket is blocked by (e.g.
  `["RUS-81"]`). `qrspi-feature` passes the approved dependency edges; the writer sets them at
  creation so the resolver's entry-gate serializes the work (a blocker is "open" until its
  status type is `completed`/`canceled`, which a QRSPI ticket reaches only after its stack
  lands).

## Step A — Resolve the Linear destination (never hard-code a team)

Read `.qrspi/config.json` (it may not exist):

- **team** — use its `linearTeam` field. If the file is missing or has no `linearTeam`, call
  `mcp__linear__list_teams`; if exactly one team exists, use it, otherwise ask the user which
  team to file under. Then suggest they add `"linearTeam": "<name>"` to `.qrspi/config.json` to
  skip this next time.
- **project** — use its `linearProject` field, defaulting to `"QRSPI"` when unset.

When the caller is `qrspi-feature` creating several tickets in one run, resolve the destination
**once** and reuse it for every `save_issue` — don't re-read config or re-ask per ticket.

## Step B — Create the issue

Call `mcp__linear__save_issue` with:

- `title` — the draft's Title.
- `team` — the team resolved in Step A.
- `project` — the project resolved in Step A.
- `assignee` — `"me"`.
- `description` — the full ticket body as markdown: the Description (Context / Goal / Why Now),
  Acceptance Criteria, Constraints, and Out of Scope sections, laid out per
  `.qrspi/templates/ticket.md`.
- `parentId` — **only if** the caller supplied one (omit it entirely otherwise; do not pass null
  on the create path).
- `blockedBy` — **only if** the caller supplied a non-empty list. The edge can only be set once
  its blocker already exists, so a caller creating a dependency chain must create tickets in
  **dependency order** (blockers first) and pass each dependent's `blockedBy` with the
  already-created blocker identifiers.

Do **not** set `state` — a new ticket lands in the team's default state. Moving it to `Selected`
is a deliberate "start this" action the user takes when ready (the resolver's entry-gate only
admits an *assigned* + `Selected` ticket), so the writer never auto-selects.

## Step C — On success

1. Extract the `id` field from the response (e.g. `RUS-42`). This is the ticket ID.
2. Create the local artifact directory: `mkdir -p .qrspi/<id>` via Bash.

## Step D — On failure

If `save_issue` fails, report the exact error to the user and **STOP**. Do not create a local
directory, do not fall back to local files, and — for a multi-ticket run — do not continue to
the next ticket (a half-created dependency chain is worse than none; surface it and let the user
decide). Report which tickets (if any) were already created so the state is clear.
