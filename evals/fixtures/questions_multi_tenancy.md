# Questions — Add multi-tenancy support to the dashboard

**Ticket:** PLAT-1205
**Generated:** 2026-06-11T00:00:00Z
**Status:** approved

## Data Flow

- Q1: How does a request currently flow from the router through middleware to a database query, and at what point could a tenant context be attached?
  **Target:** the request pipeline and the data-access entry point
- Q2: Where is the single organization's identity assumed today (config, constant, implicit) in the query path?
  **Target:** the data-access layer and any hard-coded org reference

## API Surface

- Q3: How is the incoming request's host/subdomain or headers currently parsed, and is anything tenant-like already read from them?
  **Target:** the request-parsing middleware and header access
- Q4: What is the existing API response shape, and where would a tenant scope need to be enforced to prevent cross-tenant leakage?
  **Target:** the serializer and the query-building layer

## State Management

- Q5: How are database queries constructed today — a query builder, an ORM, or raw SQL — and is there a single chokepoint where a tenant filter could be injected?
  **Target:** the query construction layer
- Q6: How are dashboard configurations stored and loaded, and are they currently global or per-user?
  **Target:** the dashboard-config model and loader

## Edge Cases

- Q7: What happens to existing single-tenant rows that have no tenant id, and how would they map to a default tenant during migration?
  **Target:** the schema and any migration scaffolding for existing data
- Q8: How is the current admin role defined, and what is the gap between "admin" and the required "tenant admin" vs "super-admin" distinction?
  **Target:** the role/permission model
- Q9: What happens today if a query is issued with no organization context — does it fail closed or return all rows?
  **Target:** the default behavior of the data-access layer with no scope

## Testing

- Q10: What test harness covers the data-access layer, and does it allow seeding rows under different scopes?
  **Target:** the model/repository test directory
- Q11: Is there any existing test that asserts data isolation between users or scopes that could be extended for tenants?
  **Target:** the authorization or access-control test suite

## Observability

- Q12: How are queries and access denials logged today, and is any scope/owner dimension already attached to those logs?
  **Target:** the query logging and access-denial logging
- Q13: How would a cross-tenant access attempt be detected or counted with the current metrics vocabulary?
  **Target:** the metrics emitter and any access-control counters
