# Ticket: DASH-417

## Title
Add user preference endpoint for notification and display settings

## Description
Users currently have no way to retrieve their notification and display
preferences via the API. The mobile team needs a dedicated endpoint to
load these settings on app launch without fetching the full user profile.

## Acceptance Criteria
- [ ] GET /api/users/:id/preferences returns notification and display prefs
- [ ] Response time < 200ms at p95
- [ ] Unauthorized requests return 401
- [ ] Requesting another user's prefs returns 403 unless admin role

## Constraints
- Must use existing auth middleware, not a new auth mechanism
- Must not add new database tables (use existing user_preferences table)

## Out of Scope
- Updating preferences (PUT endpoint is a separate ticket)
- Email preference migration from legacy system
