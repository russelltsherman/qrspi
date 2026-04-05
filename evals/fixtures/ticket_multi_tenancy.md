# Ticket: PLAT-1205

## Title

Add multi-tenancy support to the dashboard

## Description

The dashboard currently serves a single organization. We need to support
multiple tenants sharing the same deployment, with strict data isolation.
Each tenant should see only their own data, dashboards, and configurations.

## Acceptance Criteria

- [ ] Tenant context is resolved from the request (subdomain or header)
- [ ] All database queries are scoped to the current tenant
- [ ] Dashboard configurations are tenant-specific
- [ ] API responses never leak data from another tenant
- [ ] Tenant admin can manage users within their tenant only
- [ ] Super-admin can switch between tenant contexts
- [ ] Existing single-tenant data migrates to a default tenant

## Constraints

- Shared database (not separate DB per tenant)
- Must not break existing API contracts for current users
- Migration must be zero-downtime

## Out of Scope

- Per-tenant billing or usage metering
- Tenant self-service provisioning (admin-only for now)
- Custom domain per tenant
