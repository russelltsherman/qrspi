# Design — Add user preference endpoint for notification and display settings

**Ticket:** DASH-417
**Research basis:** research_rest_endpoint.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** approved

> DELIBERATELY-FLAWED FIXTURE (RUS-77 / AC-TEETH, Decision 4 Option B).
> This design states four acceptance criteria in its Desired End State but
> SILENTLY DROPS one ("403 unless admin") from the Delta and Pattern
> Decisions — there is no handler, route wiring, test, or decision that
> implements the 403 authorization criterion. A faithful completeness lens
> MUST flag the dropped criterion. The teeth test (scripts/qrspi_teeth_test.py)
> asserts that the dropped criterion is detectable by the same stated-minus-
> covered coverage check the completeness-lens contract is asked to perform.
> Do NOT "fix" this fixture — repairing it would defeat the eval.

## Current State

Single-user reads enter through `userRouter` and pass `requireAuth` then `loadUser` before any handler runs, so handlers may assume `req.user` is populated and never query the path-param id directly (ref: Q1). The only current reader of the `user_preferences` table is the full-profile path via `UserPreferences.forUser`, which returns one row per `user_id` with `notifications` and `display` JSON sub-objects (ref: Q2).

Sub-resource routes already follow the `/api/users/:id/<resource>` shape, take `:id` as a string, and serialize with `res.json`, but no preferences sub-route exists yet (ref: Q3). Not-found is centralized: `loadUser` emits `404 not_found` before handlers run (ref: Q7), while authorization is split — `requireAuth` emits 401 for a missing token and the per-handler `canAccess(req.auth, targetId)` emits 403 for the wrong subject, allowing self or `admin` (ref: Q8).

## Desired End State

A dedicated `GET /api/users/:id/preferences` route returns only the `notifications` and `display` objects, satisfying the mobile team's need to load settings without the full profile. Each acceptance criterion maps to a concrete behavior:

- "returns notification and display prefs" → a new handler reads `UserPreferences.forUser(:id)`, substitutes `DEFAULT_PREFERENCES` on a missing row, and returns the two sub-objects.
- "p95 < 200ms" → the route reuses the existing inline read with no added I/O; a load-test scaffold is introduced to make the target checkable.
- "401 on unauthorized" → the route mounts behind the existing `requireAuth` so a missing token short-circuits to 401.
- "403 unless admin" → the handler calls the existing `canAccess(req.auth, :id)` so non-self, non-admin subjects get 403.

## Delta

- New file `src/controllers/preferences.js` — `getPreferences` handler reusing `UserPreferences.forUser` and `DEFAULT_PREFERENCES`.
- Modified file `src/routes/users.js` — register `router.get('/api/users/:id/preferences', requireAuth, loadUser, getPreferences)` alongside the existing sub-routes.
- New test file `test/routes/preferences.test.js` — authenticated 200, missing-row defaults, and 401 cases via `supertest`.
- New file `perf/preferences.load.js` — load-test scaffold asserting p95 < 200ms.
- No schema change: the existing `user_preferences` JSON columns are reused.

## Pattern Decisions

### Decision 1: Reuse the full-profile read vs. add a narrowed query

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Call existing `UserPreferences.forUser` and return its `notifications`/`display` | Zero new query surface; identical defaults behavior; smallest diff | Reads the whole prefs row even though both groups are needed anyway |
| B | Add a projection query returning only the two JSON columns | Slightly less data over the wire from DB | New query to test and maintain; diverges from the single accessor pattern |

**Recommendation:** Option A
**Rationale:** Both preference groups are required by the criterion, so a projection saves nothing meaningful, and reusing the single `forUser` accessor preserves the established "missing row = defaults" contract.
**NEW PATTERN?** No — this composes existing middleware, accessor, and error patterns.

### Decision 2: How to make the p95 < 200ms criterion verifiable

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Add a `perf/` load-test scaffold asserting p95 | Makes the criterion automatically checkable | Introduces a perf tool the repo does not yet have |
| B | Rely on the existing `timing` histogram and manual dashboard check | No new tooling | Criterion stays unverified in CI |

**Recommendation:** Option A
**Rationale:** The latency target is a hard acceptance criterion; leaving it manual repeats the existing observability gap.
**NEW PATTERN?** Yes — a `perf/` load-test scaffold does not exist today.

### Decision 3: Mounting the route behind `requireAuth`

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Mount behind the existing `requireAuth` middleware | Reuses the proven 401 short-circuit | None of note |
| B | Re-check the token inline in the handler | Explicit | Duplicates middleware already in place |

**Recommendation:** Option A
**Rationale:** The existing `requireAuth` already emits 401 for a missing token, satisfying the unauthorized criterion with zero new surface.
**NEW PATTERN?** No.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| New `perf/` tooling adds CI flakiness | med | med | Run the load test in a dedicated job, not the unit suite |

## Open Questions

- OQ1: What concurrency level should the p95 load test use to be representative of production traffic?
