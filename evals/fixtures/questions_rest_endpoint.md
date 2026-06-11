# Questions — Add user preference endpoint for notification and display settings

**Ticket:** DASH-417
**Generated:** 2026-06-11T00:00:00Z
**Status:** approved

## Data Flow

- Q1: How does a request for a single user's data currently travel from the router through middleware to the response, and where is the `user_preferences` table read today?
  **Target:** the route module that loads the full user profile, plus the data-access layer that touches `user_preferences`
- Q2: What is the existing shape of a notification/display preference record as it is read out of the `user_preferences` table?
  **Target:** the model or query that maps `user_preferences` rows to objects

## API Surface

- Q3: What URL/parameter conventions do existing `GET /api/users/:id/...` routes follow for path params, serialization, and content type?
  **Target:** the users route file and its sibling resource routes
- Q4: What is the standard JSON envelope (field naming, error body) returned by existing read endpoints?
  **Target:** the response serializer or base controller used by user routes

## State Management

- Q5: Is any preference data cached, and if so where is the cache keyed and invalidated?
  **Target:** the caching layer or memoized accessor for user data
- Q6: Does the `user_preferences` table store notification and display prefs in one row or across joined rows?
  **Target:** the schema/migration defining `user_preferences`

## Edge Cases

- Q7: What does the system return today when a requested user id does not exist on an existing user read route?
  **Target:** the not-found handling in the users route
- Q8: How is a request for another user's data currently gated, and where is the admin-role check performed?
  **Target:** the authorization middleware and role-check helper
- Q9: What happens when a user exists but has no `user_preferences` row yet?
  **Target:** the preference accessor's empty-result path

## Testing

- Q10: What test harness and fixtures do existing user read endpoints use for authenticated and forbidden cases?
  **Target:** the route test directory for users
- Q11: Is there an existing p95 latency assertion or load-test scaffold for read endpoints?
  **Target:** the performance/load test configuration

## Observability

- Q12: How are 401 and 403 responses logged and counted today on user read routes?
  **Target:** the auth middleware logging and metrics emitter
- Q13: What request-timing instrumentation already wraps the users routes?
  **Target:** the metrics middleware applied to the router
