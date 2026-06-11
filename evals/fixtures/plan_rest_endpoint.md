# Implementation Plan — Add user preference endpoint for notification and display settings

**Structure basis:** structure_rest_endpoint.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** approved
**Total steps:** 18

> Scenario: DASH-417. Each step is a single atomic action. Modify steps carry
> **Current** / **After**. Every slice ends in a verify checkpoint.

## Slice 1: Authorized happy-path read

### Setup

1. ✨ Create `src/controllers/preferences.js` — empty module exporting `getPreferences` (ref: structure §Contracts `getPreferences`).
2. ⚠️ Modify `src/routes/users.js` — import `getPreferences` from `../controllers/preferences`.
   - **Current:** `const { getUserProfile, listSessions } = require('../controllers/users')`
   - **After:** add `const { getPreferences } = require('../controllers/preferences')`

### Core Logic

3. ✨ In `src/controllers/preferences.js`, implement `getPreferences` to read `UserPreferences.forUser(req.params.id)`.
4. ✨ In `getPreferences`, substitute `DEFAULT_PREFERENCES` when `forUser` returns undefined (ref: Q9).
5. ✨ In `getPreferences`, respond with `res.json({ notifications, display })` (the `PreferencesResponse` shape).
6. ⚠️ Modify `src/routes/users.js` — register the route.
   - **Current:** `router.get('/api/users/:id/sessions', requireAuth, loadUser, listSessions)`
   - **After:** add `router.get('/api/users/:id/preferences', requireAuth, loadUser, getPreferences)`

### Tests

7. ✨ Create `test/routes/preferences.test.js` — authenticated 200 case asserting `notifications` and `display` are returned.
8. ✨ Add a missing-row case asserting `DEFAULT_PREFERENCES` is returned, not an error.
9. Run: `npm test -- preferences`
   - **Expected:** the 200 and defaults cases pass.

### Verify Slice 1

10. **Checkpoint:** `npm test -- preferences`
    - [ ] Authenticated self-read returns 200 with `notifications` + `display`
    - [ ] Missing preferences row yields `DEFAULT_PREFERENCES`

---

## Slice 2: Authorization and not-found enforcement

### Setup

11. ⚠️ Modify `src/controllers/preferences.js` — import `canAccess`.
    - **Current:** `const { UserPreferences, DEFAULT_PREFERENCES } = require('../models/user_preferences')`
    - **After:** also `const { canAccess } = require('../auth/access')`

### Core Logic

12. ⚠️ Modify `getPreferences` — add the 403 guard before reading prefs.
    - **Current:** `const prefs = (await UserPreferences.forUser(req.params.id)) ?? DEFAULT_PREFERENCES`
    - **After:** `if (!canAccess(req.auth, req.params.id)) return BaseController.fail(res, 403, 'forbidden', '...')` then the read

### Tests

13. ✨ Add a 401 case to `test/routes/preferences.test.js` (no Authorization header).
14. ✨ Add a 403 case (foreign non-admin token) and a 404 case (unknown id).
15. ✨ Add an admin-reads-other-user 200 case.

### Verify Slice 2

16. **Checkpoint:** `npm test -- preferences`
    - [ ] No token → 401; foreign non-admin → 403; unknown id → 404
    - [ ] Admin token reading another user returns 200

---

## Slice 3: p95 latency scaffold

### Setup

17. ⚠️ Modify `package.json` — add a `perf:preferences` script.
    - **Current:** `"scripts": { "test": "jest" }`
    - **After:** `"scripts": { "test": "jest", "perf:preferences": "node perf/preferences.load.js" }`

### Core Logic

18. ✨ Create `perf/preferences.load.js` — drive the route under load, emit `LoadTestResult`, exit non-zero if p95 ≥ 200ms.

### Verify Slice 3

19. **Checkpoint:** `npm run perf:preferences`
    - [ ] Reports a p95 value and passes when p95 < 200ms

---

## Rollback Notes

- Step 1/3-5: delete `src/controllers/preferences.js`.
- Step 2/6: revert the import and `router.get` line in `src/routes/users.js`.
- Step 7-8/13-15: delete `test/routes/preferences.test.js`.
- Step 17-18: remove the `perf:preferences` script and delete `perf/preferences.load.js`.
- No schema or data migration is involved; rollback is purely file deletion/reversion.
