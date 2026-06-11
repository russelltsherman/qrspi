# Research — Codebase Map

**Questions source:** questions_multi_tenancy.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** approved

> Scenario: PLAT-1205 — Add multi-tenancy support to the dashboard. This
> research pass was time-boxed and is deliberately INCOMPLETE: most questions
> could not be answered from the codebase in the time available. It is a
> SPARSE fixture — a downstream design agent must NOT fabricate current-system
> behavior from these gaps, and must surface the unanswered questions rather
> than fill them with assumptions.

## Q1: How does a request currently flow from the router through middleware to a database query, and at what point could a tenant context be attached?

**Answer:** NOT FOUND. Did not trace the full request pipeline this pass; the router and middleware stack were not located.
**Evidence:**

```
// not investigated — request pipeline not traced
```

**Dependencies:** unknown
**Implicit contracts:** unknown

## Q2: Where is the single organization's identity assumed today (config, constant, implicit) in the query path?

**Answer:** NOT FOUND. No hard-coded organization reference was located. It is unclear whether org identity is implicit or absent.
**Evidence:**

```
// searched briefly; no org constant confirmed
```

**Dependencies:** unknown
**Implicit contracts:** unknown

## Q3: How is the incoming request's host/subdomain or headers currently parsed, and is anything tenant-like already read from them?

**Answer:** NOT FOUND. Header/subdomain parsing was not located; cannot say whether any tenant-like value is read today.
**Evidence:**

```
// header parsing not located
```

**Dependencies:** unknown
**Implicit contracts:** unknown

## Q4: What is the existing API response shape, and where would a tenant scope need to be enforced to prevent cross-tenant leakage?

**Answer:** Partial / uncertain. There appears to be some kind of serializer, but its location and shape were not confirmed, and the enforcement point is unknown.
**Evidence:**

```
// serializer suspected but not located
```

**Dependencies:** unknown
**Implicit contracts:** unknown

## Q5: How are database queries constructed today — a query builder, an ORM, or raw SQL — and is there a single chokepoint where a tenant filter could be injected?

**Answer:** NOT FOUND. The query-construction approach (builder vs ORM vs raw SQL) was not determined, so no chokepoint could be identified.
**Evidence:**

```
// query layer not identified
```

**Dependencies:** unknown
**Implicit contracts:** unknown

## Q6: How are dashboard configurations stored and loaded, and are they currently global or per-user?

**Answer:** NOT FOUND. The dashboard-config storage and loader were not located; global vs per-user is unknown.
**Evidence:**

```
// dashboard config model not found this pass
```

**Dependencies:** unknown
**Implicit contracts:** unknown

## Q7: What happens to existing single-tenant rows that have no tenant id, and how would they map to a default tenant during migration?

**Answer:** NOT FOUND. No schema or migration scaffolding was examined; the existing-row shape is unknown.
**Evidence:**

```
// migrations not examined
```

**Dependencies:** unknown
**Implicit contracts:** unknown

## Q8: How is the current admin role defined, and what is the gap between "admin" and the required "tenant admin" vs "super-admin" distinction?

**Answer:** Partial / uncertain. There seems to be a single "admin" notion, but the role/permission model was not read, so the gap to tenant-admin / super-admin is not established.
**Evidence:**

```
// role model not read
```

**Dependencies:** unknown
**Implicit contracts:** unknown

## Q9: What happens today if a query is issued with no organization context — does it fail closed or return all rows?

**Answer:** NOT FOUND. The default no-scope behavior was not tested or located; cannot say whether it fails closed or returns everything.
**Evidence:**

```
// default-scope behavior not determined
```

**Dependencies:** unknown
**Implicit contracts:** unknown

## Q10: What test harness covers the data-access layer, and does it allow seeding rows under different scopes?

**Answer:** NOT FOUND. The data-access test directory was not located.
**Evidence:**

```
// data-access tests not located
```

**Dependencies:** unknown
**Implicit contracts:** unknown

## Q11: Is there any existing test that asserts data isolation between users or scopes that could be extended for tenants?

**Answer:** NOT FOUND. No isolation/access-control test was found this pass.
**Evidence:**

```
// isolation tests not found
```

**Dependencies:** unknown
**Implicit contracts:** unknown

## Q12: How are queries and access denials logged today, and is any scope/owner dimension already attached to those logs?

**Answer:** NOT FOUND. Query and access-denial logging were not located; no scope/owner dimension confirmed.
**Evidence:**

```
// logging not located
```

**Dependencies:** unknown
**Implicit contracts:** unknown

## Q13: How would a cross-tenant access attempt be detected or counted with the current metrics vocabulary?

**Answer:** NOT FOUND. The metrics vocabulary was not enumerated; no access-control counter confirmed.
**Evidence:**

```
// metrics not enumerated
```

**Dependencies:** unknown
**Implicit contracts:** unknown

---

## Discovered Patterns

- None established. This pass did not locate the request pipeline, query layer, role model, or storage layout, so no cross-cutting pattern can be asserted from evidence.

## Inconsistencies

- None confirmed. Because almost every question is unanswered, any claimed inconsistency would be speculation rather than a grounded observation — none is recorded.
