# Shared writer — pointer

The "materialize a QRSPI ticket in Linear" procedure is **shared** with `qrspi-ticket` and lives
in one place so a fix to the Linear-destination logic, field mapping, or artifact convention is a
fix for both callers. Do not duplicate it here.

**Read and follow:** `.claude/skills/qrspi-ticket/references/writer.md`

It accepts a pre-seeded `draft` plus optional `parentId` and `blockedBy` — exactly what
`qrspi-feature` passes for each ticket of a decomposed feature. Resolve the Linear destination
once (its Step A) and reuse it across every ticket you create in one run.
