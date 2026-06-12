# Decomposition proposal — template, overlap scan, examples

This is the reference for **Step 2** of `qrspi-feature`. It defines the one-page proposal you
persist to `.qrspi/features/<slug>/decomposition.md` and present at the gate. **No Linear writes
happen in this step** — the overlap scan only *reads* Linear.

## Table of contents

1. [Proposal template](#proposal-template)
2. [Overlap / duplication scan procedure](#overlap--duplication-scan-procedure)
3. [Worked example — one ticket (the default)](#worked-example--one-ticket-the-default)
4. [Worked example — genuine multi-ticket split](#worked-example--genuine-multi-ticket-split)
5. [Regression case — the split that should have been caught](#regression-case--the-split-that-should-have-been-caught)

---

## Proposal template

Fill in this exact structure. Keep it to roughly one page — its tightness is what makes the gate
a real review instead of a rubber stamp.

```markdown
# Decomposition — <feature name>

## Recommendation
<ONE ticket with slices | N tickets> — <one-sentence rationale>.

## Tickets
### T1 — <title>
- Scope: <what this ticket delivers>
- Slices (sketch): <slice 1>, <slice 2>, ...        # for the one-ticket case, list the slices
- Blocked by: <none | T-x, T-y>                     # multi-ticket only

### T2 — <title>            # only if multi-ticket
- Scope: ...
- Blocked by: T1 — <concrete reason: T2 reads/edits the <file/interface> T1 creates>

## Dependency DAG          # multi-ticket only; omit for one ticket
T1 → T2 → T3              # "A → B" means B is blockedBy A

## Overlap scan
- Scanned: project <name>, <N> open/in-flight tickets.
- Findings: <none> | <RUS-NN "<title>" — overlaps T2 on <files/scope>; recommend <merge / depend / proceed>>

## Risk flags
- <shared file X touched by T1 and T2 — must serialize> | <none>
```

For the **one-ticket case** (the common outcome) the DAG and per-ticket "Blocked by" lines are
omitted — there is a single ticket with a slice sketch, an overlap scan, and risk flags.

---

## Overlap / duplication scan procedure

The goal: catch *before creating a ticket* that the proposed work duplicates or collides with
something already in flight. Be honest about its limits — at intake you only know **stated
scope**, not changed files. A precise changed-file conflict check is only possible later, at each
ticket's **structure** phase. Don't over-promise precision here; flag plausible overlap and let
the human judge.

1. Resolve the project to scan: `.qrspi/config.json` → `linearProject` (default `"QRSPI"`).
2. Read in-flight work with `mcp__linear__list_issues`:
   - `mcp__linear__list_issues({ project: "<project>", limit: 100 })` — recent issues in the
     project. Ignore any whose state type is `completed` or `canceled` (done/abandoned work can't
     collide); the live set is everything else (backlog / unstarted / started).
   - Optionally narrow with `query: "<key noun from the feature>"` to surface title/description
     matches (e.g. `query: "plugin"` for a plugin-packaging feature).
3. For each proposed ticket, compare its **stated scope** against the live set. Flag a ticket when
   it appears to:
   - deliver the **same capability** as an existing one (duplication), or
   - **rewrite or move the same files / interfaces** an in-flight ticket touches (collision — the
     dangerous case: two tickets editing the same file produce designs that can't both land).
4. For each finding, recommend an action: **merge** into the existing ticket, **declare a
   `blockedBy` dependency** on it (so they serialize), or **proceed** (overlap is superficial).
   Put findings in the proposal's Overlap scan section; surface them at the gate.

---

## Worked example — one ticket (the default)

> Feature: "Add a `--dry-run` flag to the batch orchestrator so operators can preview actions."

```markdown
## Recommendation
ONE ticket with slices — a single cohesive change to one workflow; the parts are not
independently landable.

## Tickets
### T1 — Add --dry-run preview mode to qrspi-batch
- Scope: a flag that resolves each ticket's action and prints it without executing.
- Slices (sketch): (1) thread a dryRun flag through the resolver call; (2) gate each
  side-effecting action on it + print the planned action; (3) docs + tests.

## Overlap scan
- Scanned: project QRSPI, 6 open tickets.
- Findings: none — no in-flight ticket touches the batch action-dispatch path.

## Risk flags
- none.
```

Three ordered steps, but they share one workflow file and only make sense landed together → one
ticket, three slices. Splitting would create three concurrency edges for zero independence.

---

## Worked example — genuine multi-ticket split

> Feature: "Stand up a metrics pipeline: a collector service, and a dashboard that reads it."

```markdown
## Recommendation
TWO tickets — the collector and the dashboard are independently reviewable and landable, in
different subtrees, owned by different concerns; only a thin declared dependency links them.

## Tickets
### T1 — Metrics collector service
- Scope: service that ingests events and exposes a read API.
- Blocked by: none.

### T2 — Metrics dashboard
- Scope: UI that reads T1's API and renders charts.
- Blocked by: T1 — T2 consumes the read API T1 defines; building it first would design against a
  nonexistent contract.

## Dependency DAG
T1 → T2

## Overlap scan
- Scanned: project QRSPI, 6 open tickets. Findings: none.

## Risk flags
- T2 depends on T1's API shape — the blockedBy edge serializes them so T2 designs against a real,
  landed contract rather than a guessed one.
```

T1 can land and ship on its own; T2 is genuinely separable but depends on T1's contract → two
tickets with one `blockedBy` edge. Note this is **not** a strict full chain — T1 stands alone.

---

## Regression case — the split that should have been caught

This is the failure that motivated the skill. Treat it as the canonical "what good looks like."

> Feature: "Migrate QRSPI so it can be distributed as a Claude Code plugin."

What actually happened (the trap): an unstructured "create tickets for this" produced **two**
tickets — one moving the engine into a `plugin/` subtree + marketplace, the other keeping
everything in `.claude/` + `scripts/` and adding a repo-root `plugin.json` + a sync skill. They
were **two mutually-incompatible plugin-root strategies**, each designed against `main` with no
knowledge of the other, both rewriting the **same** `qrspi-work/SKILL.md` engine refs. They could
not both land — and each reached an open PR before anyone noticed.

What this skill produces instead:

```markdown
## Recommendation
ONE ticket with slices — "distribute as a plugin" is a single architectural decision (one
plugin-root strategy) with sequential parts; it is NOT two independently-landable features. Two
tickets here would each pick a different plugin root and rewrite the same engine refs → designs
that cannot co-land.

## Tickets
### T1 — Package QRSPI as a Claude Code plugin
- Scope: choose ONE plugin-root strategy, add the manifest, wire the engine refs, add a sync path.
- Slices (sketch): (1) plugin.json manifest at the chosen root; (2) relocate/declare engine
  (skills, agents, scripts); (3) rewrite qrspi-work engine refs to the chosen layout; (4)
  marketplace + install e2e.

## Overlap scan
- Scanned: project QRSPI. Findings: if a second "plugin" ticket already exists, FLAG it — this
  feature collides with it on plugin root + qrspi-work refs. Recommend: ONE strategy wins; merge
  or supersede, never run both concurrently.

## Risk flags
- Multiple slices rewrite the SAME files (plugin.json, qrspi-work/SKILL.md). That shared-file
  coupling is the proof they must be ONE serialized stack, not parallel tickets.
```

The lesson the skill encodes: when every candidate ticket rewrites the same load-bearing files and
picks competing versions of one decision, that is one ticket's slice stack — and the overlap scan
must flag a pre-existing sibling ticket as a collision *before* a second conflicting one is born.
