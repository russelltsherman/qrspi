# Structure Outline — Add user preference endpoint for notification and display settings

**Design basis:** design_rest_endpoint.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** approved

> Scenario: DASH-417. Slices are vertical end-to-end paths: each delivers a
> testable behavior for the new `GET /api/users/:id/preferences` route.

## New Types

- `PreferencesResponse { notifications: object, display: object }` — the bare body returned by the new read route (ref: design §Desired End State)
- `LoadTestResult { route: string, p95Ms: number, passed: boolean }` — the assertion shape emitted by the new `perf/` scaffold (ref: design §Pattern Decisions Decision 2)

## Modified Types

- none — the `user_preferences` JSON columns are reused unchanged; the ticket forbids new tables (ref: design §Delta, Q6)

## Contracts

- `getPreferences(req, res): void` — reads `UserPreferences.forUser(req.params.id)`, substitutes `DEFAULT_PREFERENCES` on a missing row, returns `PreferencesResponse` as JSON (ref: design §Delta)
- `canAccess(auth, targetId): boolean` — existing helper reused to gate cross-user reads (self or admin); unchanged (ref: Q8)

## Slice 1: Authorized happy-path read

**Goal:** `GET /api/users/:id/preferences` returns the caller's own `notifications` and `display` objects (with defaults on a missing row) behind the existing auth middleware — a testable end-to-end 200 path.
**Files touched:**

- ✨ `src/controllers/preferences.js` — `getPreferences` handler reusing `forUser` + `DEFAULT_PREFERENCES`
- ⚠️ `src/routes/users.js` — register the new `GET /api/users/:id/preferences` route after the existing sub-routes
- ✨ `test/routes/preferences.test.js` — authenticated 200 + missing-row-defaults cases
**Verification:**
- [ ] `npm test -- preferences` passes the 200 and defaults cases
- [ ] A seeded user with no preferences row receives `DEFAULT_PREFERENCES`, not an error
**Context cost:** M
**Depends on:** none

## Slice 2: Authorization and not-found enforcement

**Goal:** The route returns 401 with no token, 403 for a non-self non-admin subject, and 404 for an unknown user — reusing `requireAuth`, `canAccess`, and `loadUser` so the read path is fully gated end-to-end.
**Files touched:**

- ⚠️ `src/controllers/preferences.js` — add the `canAccess` 403 guard to `getPreferences`
- ⚠️ `test/routes/preferences.test.js` — add 401, 403, and 404 cases
**Verification:**
- [ ] No-token request returns 401; foreign-token non-admin returns 403; unknown id returns 404
- [ ] Admin token reading another user's prefs returns 200
**Context cost:** S
**Depends on:** Slice 1

## Slice 3: p95 latency scaffold

**Goal:** A `perf/` load test asserts the route meets p95 < 200ms, making the latency acceptance criterion checkable rather than manual.
**Files touched:**

- ✨ `perf/preferences.load.js` — load-test scaffold emitting `LoadTestResult` and asserting p95 < 200ms
- ⚠️ `package.json` — add a `perf:preferences` script entry
**Verification:**
- [ ] `npm run perf:preferences` reports a p95 and exits non-zero if p95 ≥ 200ms
- [ ] The scaffold runs in its own job, not the unit suite
**Context cost:** M
**Depends on:** Slice 1

---

## Unverified Assumptions

- The exact concurrency/dataset the p95 load test should model is unspecified (design OQ2); Slice 3 picks a documented default that the reviewer can adjust.
- Whether the pre-existing 401-counting asymmetry (design OQ1) is in scope is left to review; no slice changes 401 counting.
