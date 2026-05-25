# Structure Outline — <Ticket Title>

**Design basis:** design.md @ <timestamp>
**Generated:** <ISO-8601 timestamp>
**Status:** draft | approved

## New Types

- `<TypeName> { field: type, field: type }`

## Modified Types

- `<TypeName>` — add field `<field: type>` (ref: design.md §Delta)

## Contracts

- `<functionName>(params): ReturnType` — <one-line purpose>

## Slice 1: <Name>

**Goal:** <what this slice delivers as a testable end-to-end path>
**Files touched:**

- ✨ `<new file path>` — <purpose>
- ⚠️ `<existing file path>` — <what changes>
**Verification:**
- [ ] <concrete test or manual check>
**Context cost:** S | M | L
**Depends on:** none

## Slice 2: <Name>

**Goal:** <what this slice delivers as a testable end-to-end path>
**Files touched:**

- ✨ `<new file path>` — <purpose>
- ⚠️ `<existing file path>` — <what changes>
**Verification:**
- [ ] <concrete test or manual check>
**Context cost:** S | M | L
**Depends on:** Slice 1

---

## Unverified Assumptions

<Any claim from design.md that could not be mapped to a concrete type,
file, or interface. These need human attention before planning.>
