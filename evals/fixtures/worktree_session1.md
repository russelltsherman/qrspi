# Work Tree — Add user preference endpoint for notification and display settings

**Plan basis:** plan_rest_endpoint.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** approved
**Total sessions:** 3
**Critical path:** T1 → T2 → T3 → T4 → T5 → T6 → T7 → (Slice 1 done) → T8 → T9 → T10 → T11 → (Slice 2) → T12 → T13 → T14

> Scenario: DASH-417. Each slice maps to one session and terminates in a verify
> checkpoint — a natural session boundary. The ticket ID and Acceptance-Criteria
> text are threaded verbatim from `ticket_rest_endpoint.md`:
>
> - [ ] GET /api/users/:id/preferences returns notification and display prefs
> - [ ] Response time < 200ms at p95
> - [ ] Unauthorized requests return 401
> - [ ] Requesting another user's prefs returns 403 unless admin role

## Session 1 — Slice 1: Authorized happy-path read

**Load:** structure_rest_endpoint.md §New Types, structure_rest_endpoint.md §Contracts
        (`getPreferences`), plan_rest_endpoint_slice1.md §Slice 1
**Estimated context:** ~18%

**Files in scope for this session (do NOT touch anything else):**

- `src/controllers/preferences.js`
- `src/routes/users.js`
- `test/routes/preferences.test.js`

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create `src/controllers/preferences.js` — empty module exporting `getPreferences` | — | §1.1 | S | pending |
| T2 | Modify `src/routes/users.js` — import `getPreferences` from `../controllers/preferences` | T1 | §1.2 | S | pending |
| T3 | In `src/controllers/preferences.js`, implement `getPreferences` to read `UserPreferences.forUser(req.params.id)` | T1 | §1.3 | M | pending |
| T4 | In `getPreferences`, substitute `DEFAULT_PREFERENCES` when `forUser` returns undefined | T3 | §1.4 | S | pending |
| T5 | In `getPreferences`, respond with `res.json({ notifications, display })` (the `PreferencesResponse` shape) | T4 | §1.5 | S | pending |
| T6 | Modify `src/routes/users.js` — register `router.get('/api/users/:id/preferences', requireAuth, loadUser, getPreferences)` | T2,T5 | §1.6 | S | pending |
| T7 | **Verify Slice 1** — create `test/routes/preferences.test.js` (authenticated 200 + defaults cases) and run `npm test -- preferences` | T6 | §1.10 | M | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete and verified — the authorized happy-path read returns
`notifications` + `display` and falls back to `DEFAULT_PREFERENCES`. Fresh context for
the authorization-enforcement slice.

## Session 2 — Slice 2: Authorization and not-found enforcement

**Load:** structure_rest_endpoint.md §New Types, structure_rest_endpoint.md §Contracts
        (`canAccess`), plan_rest_endpoint.md §Slice 2, impl-log.md §Slice 1 (notes only)
**Estimated context:** ~16%

**Files in scope for this session (do NOT touch anything else):**

- `src/controllers/preferences.js`
- `test/routes/preferences.test.js`

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T8 | Modify `src/controllers/preferences.js` — import `canAccess` from `../auth/access` | T7 | §2.11 | S | pending |
| T9 | Modify `getPreferences` — add the 403 guard (`requesting another user's prefs returns 403 unless admin role`) before reading prefs | T8 | §2.12 | M | pending |
| T10 | Add 401 (no Authorization header) and 403 (foreign non-admin token) cases plus a 404 (unknown id) case to `test/routes/preferences.test.js` | T9 | §2.13 | M | pending |
| T11 | **Verify Slice 2** — add the admin-reads-other-user 200 case and run `npm test -- preferences` | T10 | §2.16 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 2 complete — 401/403/404 enforcement and admin override are covered.
Fresh context for the latency scaffold, which touches `package.json` and a new `perf/`
file rather than the controller.

## Session 3 — Slice 3: p95 latency scaffold

**Load:** structure_rest_endpoint.md §New Types (`LoadTestResult`), plan_rest_endpoint.md
        §Slice 3, impl-log.md §Slice 2 (notes only)
**Estimated context:** ~14%

**Files in scope for this session (do NOT touch anything else):**

- `package.json`
- `perf/preferences.load.js`

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T12 | Modify `package.json` — add a `perf:preferences` script | T11 | §3.17 | S | pending |
| T13 | Create `perf/preferences.load.js` — drive the route under load, emit `LoadTestResult`, exit non-zero if p95 ≥ 200ms (`response time < 200ms at p95`) | T12 | §3.18 | M | pending |
| T14 | **Verify Slice 3** — run `npm run perf:preferences` and confirm it reports a p95 value and passes when p95 < 200ms | T13 | §3.19 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 3 complete — the full DASH-417 feature (read, authorization, latency
scaffold) is implemented and verified. No further sessions.
