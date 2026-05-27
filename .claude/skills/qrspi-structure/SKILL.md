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

Read `.qrspi/templates/structure.md` for the output format.

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
8. **Do NOT over-slice cohesive work.** If all changes are directly related and mutually dependent — meaning no file can be meaningfully tested or verified without the others — they belong in a single slice regardless of file count. A slice represents a unit of work a developer would do in one sitting. Do not split a coherent deliverable into artificial sub-units just because it spans multiple files.
   - WRONG: Slice 1 writes a config file, Slice 2 writes the code that reads it, Slice 3 runs validation — these are one slice.
   - WRONG: Separate slices for a main file and its reference/support files that it directly depends on.
   - CORRECT: Split when there is a genuine testability boundary — one part can be verified independently before the next starts, and that verification provides real signal.
9. Validation passes (linting, running a review tool, invoking skill-creator) are the final step of the slice that produced the files — not a separate slice.

After writing, tell the user: "Structure written to `.qrspi/<id>/structure.md`. Check slice boundaries and contracts. If any slice is too large, I'll split it. Tell me 'approved' to proceed to Plan."
