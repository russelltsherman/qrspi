---
name: qrspi-structure
description: Define vertical slices, types, and contracts from the approved design. Use after design is approved.
command: /qrspi-structure
argument-hint: <ticket-id>
allowed-tools: Read, Glob, Grep
---

# Structure Outline Phase (S)

Read `.qrspi/$ARGUMENTS/design.md` (must have Status: approved in it or user must have said approved).

Produce `.qrspi/$ARGUMENTS/structure.md`.

## Rules
1. Define new/modified types and function signatures (pseudo-code, not implementations).
2. Organize into VERTICAL SLICES — each delivers a testable end-to-end path.
   - CORRECT: "Slice 1: Mock API → UI component → hardcoded data"
   - WRONG: "Phase 1: All database changes"
3. Each slice has: Goal, Files touched (new/modify marked), Verification step, Context cost (S/M/L), Dependencies.
4. No slice touches > 10 files. Split if it does.
5. Order slices so dependencies flow forward.
6. Include a Contracts section for cross-slice interfaces.
7. Include an Unverified Assumptions section — claims from design.md you can't map to concrete code.

After writing, tell the user: "Structure written to `.qrspi/<id>/structure.md`. Check slice boundaries and contracts. If any slice is too large, I'll split it. Tell me 'approved' to proceed to Plan."
