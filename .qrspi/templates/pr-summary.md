# PR: <title, max 72 chars>

**Ticket:** <TICKET-ID>
**Design:** design.md @ <timestamp>
**Structure:** structure.md @ <timestamp>

## Summary

<3-5 sentences. What changed, why, and what the reviewer should focus on.>

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: ... | `<file>:<function>` | `<test file>:<test name>` |
| AC2: ... | ... | ... |

## Changes by Slice

### Slice 1: <name>

| File | Change | Lines |
|------|--------|-------|
| `src/foo/types.ts` | ✨ new | +45 |
| `src/routes/index.ts` | ⚠️ modified | +3, -0 |

### Slice 2: <name>

| File | Change | Lines |
|------|--------|-------|
| ... | ... | ... |

## Testing Summary

- [ ] Slice 1: unit tests — `<command>` — <N> passed
- [ ] Slice 2: integration — `<command>` — <N> passed
- [ ] Manual verification: <description>

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| (none if clean) | | | |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| ... | mitigated / accepted / discovered-new | ... |

## Open Items

- <Anything deferred, tech debt introduced, or follow-up tickets needed>
