# Implementation Plan — Add user preference endpoint for notification and display settings

**Structure basis:** structure_rest_endpoint.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** approved
**Total steps:** 10

> Scenario: DASH-417. This is the faithful Slice-1 subset of
> plan_rest_endpoint.md — the Slice-1 steps are copied verbatim.

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

## Rollback Notes

- Step 1/3-5: delete `src/controllers/preferences.js`.
- Step 2/6: revert the import and `router.get` line in `src/routes/users.js`.
- Step 7-8: delete `test/routes/preferences.test.js`.
- No schema or data migration is involved; rollback is purely file deletion/reversion.
