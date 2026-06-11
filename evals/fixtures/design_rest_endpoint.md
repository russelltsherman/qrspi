# Design — Add user preference endpoint for notification and display settings

**Ticket:** DASH-417
**Research basis:** research_rest_endpoint.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** approved

## Current State

Single-user reads enter through `userRouter` and pass `requireAuth` then `loadUser` before any handler runs, so handlers may assume `req.user` is populated and never query the path-param id directly (ref: Q1). The only current reader of the `user_preferences` table is the full-profile path via `UserPreferences.forUser`, which returns one row per `user_id` with `notifications` and `display` JSON sub-objects (ref: Q2).

Sub-resource routes already follow the `/api/users/:id/<resource>` shape, take `:id` as a string, and serialize with `res.json`, but no preferences sub-route exists yet (ref: Q3). Success bodies return the bare resource object while errors use the uniform `{ error: { code, message } }` envelope produced by `BaseController.fail` (ref: Q4).

There is no caching of preference data; `getUserProfile` reads `user_preferences` on every request with no memoization layer (ref: Q5). The table stores both preference groups as JSON columns on a single row, and the ticket forbids new tables, so that JSON shape is the binding contract (ref: Q6).

Not-found is centralized: `loadUser` emits `404 not_found` before handlers run (ref: Q7), while authorization is split — `requireAuth` emits 401 for a missing token and the per-handler `canAccess(req.auth, targetId)` emits 403 for the wrong subject, allowing self or `admin` (ref: Q8). A user with no preferences row is a normal state: `forUser` returns undefined and the handler substitutes `DEFAULT_PREFERENCES` (ref: Q9).

Existing route tests use `supertest` with a `seedUser`/`authToken` helper and assert 403 with a foreign token (ref: Q10), but there is no p95 latency assertion or load-test scaffold anywhere in the repo (ref: Q11). Auth denials are observable but asymmetric: 403 is both logged and counted via `metrics.increment('auth.denied')` while 401 is only logged (ref: Q12). A global `timing` middleware records per-route duration histograms keyed by route template, so any new sub-route is instrumented automatically (ref: Q13).

## Desired End State

A dedicated `GET /api/users/:id/preferences` route returns only the `notifications` and `display` objects, satisfying the mobile team's need to load settings without the full profile. Each acceptance criterion maps to a concrete behavior:

- "returns notification and display prefs" → a new handler reads `UserPreferences.forUser(:id)`, substitutes `DEFAULT_PREFERENCES` on a missing row, and returns the two sub-objects.
- "p95 < 200ms" → the route reuses the existing inline read with no added I/O; a load-test scaffold is introduced to make the target checkable.
- "401 on unauthorized" → the route mounts behind the existing `requireAuth` so a missing token short-circuits to 401.
- "403 unless admin" → the handler calls the existing `canAccess(req.auth, :id)` so non-self, non-admin subjects get 403.

## Delta

- New file `src/controllers/preferences.js` — `getPreferences` handler reusing `UserPreferences.forUser`, `DEFAULT_PREFERENCES`, and `canAccess`.
- Modified file `src/routes/users.js` — register `router.get('/api/users/:id/preferences', requireAuth, loadUser, getPreferences)` alongside the existing sub-routes.
- New test file `test/routes/preferences.test.js` — authenticated 200, missing-row defaults, 401, and 403 cases via `supertest`.
- New file `perf/preferences.load.js` — load-test scaffold asserting p95 < 200ms (closes the gap from ref: Q11).
- No schema change: the existing `user_preferences` JSON columns are reused (constraint honored).

## Pattern Decisions

### Decision 1: Reuse the full-profile read vs. add a narrowed query

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Call existing `UserPreferences.forUser` and return its `notifications`/`display` | Zero new query surface; identical defaults behavior; smallest diff | Reads the whole prefs row even though both groups are needed anyway |
| B | Add a projection query returning only the two JSON columns | Slightly less data over the wire from DB | New query to test and maintain; diverges from the single accessor pattern |

**Recommendation:** Option A
**Rationale:** Both preference groups are required by the criterion, so a projection saves nothing meaningful, and reusing the single `forUser` accessor preserves the established "missing row = defaults" contract from research (ref: Q9).
**NEW PATTERN?** No — this composes existing middleware, accessor, and error patterns.

### Decision 2: How to make the p95 < 200ms criterion verifiable

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Add a `perf/` load-test scaffold (e.g. autocannon) asserting p95 | Makes the criterion automatically checkable; reusable for other routes | Introduces a perf tool the repo does not yet have |
| B | Rely on the existing `timing` histogram and manual dashboard check | No new tooling | Criterion stays unverified in CI; research found no automated check (ref: Q11) |

**Recommendation:** Option A
**Rationale:** The latency target is a hard acceptance criterion; leaving it manual repeats the existing observability gap, so a minimal scaffold is justified.
**NEW PATTERN?** Yes — a `perf/` load-test scaffold does not exist today; it is introduced deliberately and scoped to this route to keep the footprint small.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Auth-denied metric undercounts because 401 is not counted (carried from existing asymmetry, ref: Q12) | med | low | Document the asymmetry; optionally add a 401 counter as a follow-up rather than in this slice |
| New `perf/` tooling adds CI flakiness or slows the pipeline | med | med | Run the load test in a dedicated job, not the unit suite; gate only on p95 threshold |
| Preference-read latency is not separable from profile latency in the shared histogram (ref: Q13) | low | low | Keep the route template distinct (`/api/users/:id/preferences`) so the histogram keys it independently |

## Open Questions

- OQ1: Should the 401-counting asymmetry (ref: Q12) be fixed within this ticket or tracked separately, given it is pre-existing?
- OQ2: What concurrency level and dataset size should the p95 load test use to be representative of production traffic?
