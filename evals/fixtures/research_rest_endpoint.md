# Research — Codebase Map

**Questions source:** questions_rest_endpoint.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** approved

> Scenario: DASH-417 — Add user preference endpoint for notification and
> display settings. Findings are factual observations of the (fictional
> reference) codebase the eval harness models; every answer is backed by a
> `file:line` citation.

## Q1: How does a request for a single user's data currently travel from the router through middleware to the response, and where is the `user_preferences` table read today?

**Answer:** Requests enter through `userRouter`, pass `requireAuth` then `loadUser`, and are served by `getUserProfile`, which reads the user row and eager-loads preferences via `UserPreferences.forUser(id)`. The full-profile path is the only current reader of `user_preferences`.
**Evidence:**

```
router.get('/api/users/:id', requireAuth, loadUser, getUserProfile)
```

— `src/routes/users.js:14`
**Dependencies:** `src/middleware/auth.js` (requireAuth), `src/models/user_preferences.js` (forUser)
**Implicit contracts:** `loadUser` attaches `req.user` before any handler runs; handlers never query the DB for the path-param id directly.

## Q2: What is the existing shape of a notification/display preference record as it is read out of the `user_preferences` table?

**Answer:** `UserPreferences.forUser` returns a single object with `notifications` and `display` sub-objects; both are JSON columns on one row keyed by `user_id`.
**Evidence:**

```
return db('user_preferences').where({ user_id: id }).first()
```

— `src/models/user_preferences.js:22`
**Dependencies:** `src/db/knex.js`
**Implicit contracts:** exactly one row per `user_id`; callers treat a missing row as "defaults", not an error.

## Q3: What URL/parameter conventions do existing `GET /api/users/:id/...` routes follow for path params, serialization, and content type?

**Answer:** Sub-resource routes use the `/api/users/:id/<resource>` shape, take `:id` as a string, and return `application/json` via `res.json`. No sub-resource read route exists for preferences yet.
**Evidence:**

```
router.get('/api/users/:id/sessions', requireAuth, loadUser, listSessions)
```

— `src/routes/users.js:19`
**Dependencies:** `src/serializers/json.js`
**Implicit contracts:** `:id` is never parsed to an integer at the route layer; serialization happens in the handler, not middleware.

## Q4: What is the standard JSON envelope (field naming, error body) returned by existing read endpoints?

**Answer:** Success bodies return the resource object directly (no wrapper); errors return `{ error: { code, message } }` produced by `BaseController.fail`.
**Evidence:**

```
res.status(code).json({ error: { code, message } })
```

— `src/controllers/base.js:41`
**Dependencies:** none beyond Express `res`
**Implicit contracts:** field names are camelCase; error `code` is a stable string, not the HTTP status.

## Q5: Is any preference data cached, and if so where is the cache keyed and invalidated?

**Answer:** No caching exists for preferences. `getUserProfile` reads `user_preferences` on every request; there is no memoization or Redis layer in the read path.
**Evidence:**

```
// no cache wrapper around UserPreferences.forUser
const prefs = await UserPreferences.forUser(req.user.id)
```

— `src/controllers/users.js:58`
**Dependencies:** none
**Implicit contracts:** reads are assumed cheap; adding a cache would be a new pattern.

## Q6: Does the `user_preferences` table store notification and display prefs in one row or across joined rows?

**Answer:** One row per user, with `notifications` and `display` stored as JSON columns; no join table.
**Evidence:**

```
table.jsonb('notifications'); table.jsonb('display')
```

— `migrations/20240110_user_preferences.js:6`
**Dependencies:** `migrations/` (knex)
**Implicit contracts:** schema changes are forbidden by the ticket (no new tables); the JSON columns are the contract.

## Q7: What does the system return today when a requested user id does not exist on an existing user read route?

**Answer:** `loadUser` returns `404` with `{ error: { code: 'not_found', message } }` before the handler runs.
**Evidence:**

```
if (!user) return BaseController.fail(res, 404, 'not_found', 'User not found')
```

— `src/middleware/load_user.js:17`
**Dependencies:** `src/controllers/base.js`
**Implicit contracts:** handlers may assume `req.user` exists; not-found is centralized in middleware.

## Q8: How is a request for another user's data currently gated, and where is the admin-role check performed?

**Answer:** `requireAuth` populates `req.auth`; the cross-user check is done per-handler via `canAccess(req.auth, targetId)`, which allows self or `admin` role.
**Evidence:**

```
if (!canAccess(req.auth, req.params.id)) return BaseController.fail(res, 403, 'forbidden', '...')
```

— `src/controllers/users.js:49`
**Dependencies:** `src/auth/access.js` (canAccess)
**Implicit contracts:** 401 is emitted by `requireAuth` (no token); 403 by `canAccess` (token, wrong subject).

## Q9: What happens when a user exists but has no `user_preferences` row yet?

**Answer:** `forUser` returns `undefined`; `getUserProfile` substitutes `DEFAULT_PREFERENCES` so the response is never empty.
**Evidence:**

```
const prefs = (await UserPreferences.forUser(id)) ?? DEFAULT_PREFERENCES
```

— `src/controllers/users.js:59`
**Dependencies:** `src/models/user_preferences.js`
**Implicit contracts:** a missing row is a normal state, not a 404.

## Q10: What test harness and fixtures do existing user read endpoints use for authenticated and forbidden cases?

**Answer:** Tests use `supertest` against the Express app with a `seedUser`/`authToken` helper; forbidden cases assert `403` with a foreign token.
**Evidence:**

```
const res = await request(app).get('/api/users/'+id).set('Authorization', token)
```

— `test/routes/users.test.js:28`
**Dependencies:** `test/helpers/auth.js`
**Implicit contracts:** each test seeds its own user; no shared global fixture state.

## Q11: Is there an existing p95 latency assertion or load-test scaffold for read endpoints?

**Answer:** NOT FOUND. Searched `test/`, `perf/`, and `package.json` scripts for `p95`, `latency`, `autocannon`, and `k6`; no load-test scaffold or latency assertion exists. The `< 200ms p95` criterion has no current automated check.
**Evidence:**

```
// grep -r "p95\|autocannon\|k6" test/ perf/  -> no matches
```

— `package.json:12`
**Dependencies:** none
**Implicit contracts:** latency targets are currently verified manually, if at all.

## Q12: How are 401 and 403 responses logged and counted today on user read routes?

**Answer:** `requireAuth` and `canAccess` both call `logger.warn` with an `event` tag; a `metrics.increment('auth.denied')` counter is emitted on 403 only.
**Evidence:**

```
logger.warn({ event: 'auth.denied', subject }); metrics.increment('auth.denied')
```

— `src/auth/access.js:31`
**Dependencies:** `src/observability/logger.js`, `src/observability/metrics.js`
**Implicit contracts:** 401 is logged but not counted; 403 is both logged and counted.

## Q13: What request-timing instrumentation already wraps the users routes?

**Answer:** A global `timing` middleware records per-route duration histograms keyed by route template, applied before the router mounts.
**Evidence:**

```
app.use(timing({ histogram: 'http.request.duration' }))
```

— `src/app.js:23`
**Dependencies:** `src/observability/metrics.js`
**Implicit contracts:** the histogram is keyed by route template (`/api/users/:id/...`), so a new sub-route is instrumented automatically.

---

## Discovered Patterns

- All user routes follow `requireAuth → loadUser → handler`; not-found and auth are centralized in middleware, so handlers assume a valid `req.user`.
- Errors are uniformly `{ error: { code, message } }` via `BaseController.fail`; success bodies are bare resource objects.
- Missing `user_preferences` rows are treated as "defaults", never as errors, across the read path.

## Inconsistencies

- 403 denials are both logged and counted (`metrics.increment('auth.denied')`), but 401 denials are only logged — the auth-denied metric undercounts total denials.
- The `timing` histogram is keyed by route template, yet `getUserProfile` reads preferences inline without its own span, so preference-read latency is not separable from profile latency.
