# QRSPI Working Example: Real Feature Walkthrough

A complete, annotated example of one feature going through the full QRSPI workflow — from ticket creation, through three stacked phase PRs (design, plan, implementation), to landing the whole stack. Use this as a reference for what good outputs look like at each stage and how **PR review state** drives the work.

---

## Feature: Add User Email Preferences

Simple feature that integrates with an existing e-commerce system. This walkthrough shows what real QRSPI work looks like, including where the human review gates sit and how each phase becomes its own stacked PR.

### How the workflow is shaped

Feature work is decomposed into sequential phases, each producing a reviewable artifact:

```
Ticket  -->  Questions  -->  Research  -->  Design  -->  Structure  -->  Plan  -->  Worktree  -->  Implement  -->  PR
  (Linear)      Q             R             D             S             P           W              I + impl-log
```

Two things shape everything below:

1. **The ticket is a Linear issue**, not a local markdown file. It lives in your Linear team, QRSPI project, with an ID like `RUS-42`. Every other artifact is a local file under `.qrspi/RUS-42/`. Linear holds status and phase-transition comments only — artifacts are never uploaded to Linear.

2. **PR review state — not Linear status — is the authority for advancement.** Linear has exactly two roles: an **entry gate** (a ticket may only begin if it is *assigned* and in `Selected`) and a **best-effort reporting projection** of the active phase (a failed Linear write never blocks work). The lifecycle is a single Graphite stack, one PR per phase, built bottom-up and **held open** until the whole feature is approved, then landed bottom-up:

   ```
   trunk
    └── RUS-42/design    Design PR  — questions.md, research.md, design.md
         └── RUS-42/plan   Plan PR   — structure.md, plan.md, worktree.md   (stacked on design)
              └── RUS-42/slice-1..N  slice PRs — code                        (stacked on plan)
   ```

   A phase PR is **ready** when `reviewDecision == APPROVED` *and* it has zero unresolved review threads. Approving a phase PR **auto-advances**: the next phase is built stacked on top. A human approving each phase PR is what moves the ticket forward. The `*Approved` Linear statuses were **dropped** — approval lives in the PR. Reporting statuses are `Selected` → `Design Review` → `Plan Review` → `Code Review` → `Done`.

   A formal `CHANGES_REQUESTED` on an **upstream** phase PR **resets**: every downstream phase is automatically discarded (PRs closed, branches deleted, stale artifacts removed) and the ticket returns to that phase. **Revise** — addressing review comments *within* a phase — is **manual**, on explicit re-invocation. The decision is computed by the tested resolver `scripts/qrspi_resolve_state.py`; `/qrspi-work` and the batch workflow both call it rather than re-deriving state logic.

Each phase lives on its **own** branch (`RUS-42/design`, `RUS-42/plan`, `RUS-42/slice-N`) as a single commit, stacked on the phase below it. The design PR is opened at Design Review; the plan PR is stacked on it at Plan Review; the slice PRs are stacked on plan at Code Review. Nothing merges until the whole feature is approved.

---

## Phase 0: Ticket — create the Linear issue

### What Actually Happened

Engineer ran: `/qrspi-ticket We need to let users control which emails they receive`

The `qrspi-ticket` skill opened a guided conversation, then created a **Linear issue** in your Linear team, QRSPI project. Linear assigned the identifier `RUS-42`. The skill also created the local artifact directory `.qrspi/RUS-42/`.

### The Conversation

```txt
Agent: You want users to be able to opt in or out of specific email types.
  A couple of questions to flesh this out:
  1. What email types exist today (e.g. transactional, marketing, digest)?
  2. Should preferences apply immediately, or only to future sends?

Engineer: There are three types: order confirmations, promotions, and weekly digest.
  Changes should apply immediately — no queued sends should go out after a user opts out.

Agent: Got it. One more:
  Are there any users who must always receive certain emails
  (e.g. order confirmations can't be opted out of for legal reasons)?

Engineer: Yes — order confirmations are mandatory. Users can only opt out of
  promotions and weekly digest.
```

### The Linear Issue (RUS-42)

The agent created the issue with this content. (This is the Linear issue body — there is no `ticket.md` file.)

```markdown
# Add user email preference controls for promotions and digest

## Description
Users currently receive all email types with no way to opt out. This creates
friction for users who want marketing emails reduced without losing transactional
emails they depend on.

The system sends three email types: order confirmations (mandatory), promotional
emails, and weekly digest. Users need a self-service way to disable promotions
and/or the weekly digest.

Changes must take effect immediately — no queued sends should dispatch after a
user has opted out.

## Acceptance Criteria
- [ ] AC1: Users can enable or disable promotional emails from their account settings
- [ ] AC2: Users can enable or disable the weekly digest from their account settings
- [ ] AC3: Preference changes take effect immediately; no queued sends bypass the setting
- [ ] AC4: Order confirmation emails are always sent regardless of user preferences

## Constraints
- Order confirmation emails are legally required and must not be suppressible
- Preference changes must be reflected before any queued send dispatches

## Out of Scope
- Unsubscribe links in email footers (follow-on ticket)
- Admin-level overrides for bulk sends
- Preference management for non-registered users
```

The issue starts in `Backlog`. Once the engineer is ready to work it, they **assign it to themselves** and move it to `Selected` — that pair (assigned + `Selected`) is the entry gate. Then they run `/qrspi-work RUS-42`. From here the orchestrator resolves state from the PR stack and drives the work forward.

**Time investment:** ~15 minutes

---

## The Design Phase (Design PR)

`/qrspi-work RUS-42` resolves state from the PR stack. With no `RUS-42/design` branch yet and the entry gate satisfied (assigned + `Selected`), the resolver returns `run_design`. The orchestrator sets up the worktree at `.worktrees/RUS-42/` (creating the `RUS-42/design` branch from `main`), then runs the **design phase** — Questions, Research, Design — three artifacts committed as a single commit on `RUS-42/design`.

The orchestrator spawns each phase as a purpose-built agent defined in `.claude/agents/qrspi-<phase>.md` (each with its own tool lockdown). The slash-command wrappers in `.claude/skills/qrspi-<phase>/` exist for manual re-runs, but `/qrspi-work` spawns the agents directly by `subagent_type`.

---

## Phase 1: Questions (Q)

### What Actually Happened

The orchestrator spawned the `qrspi-questions` agent with the ticket content (title + description from the Linear fetch). The questions agent has no `Glob`, `Grep`, or `Bash` — exploring the codebase is structurally impossible at this phase. It produces 8–15 technical questions derived from the ticket.

The artifact is written to `.qrspi/RUS-42/questions.md`. The design-phase artifacts are committed together once all three exist, as the single commit on `RUS-42/design` (`gt create RUS-42/design`, message `RUS-42 [QR]: Design`).

### Agent's Output: questions.md

```markdown
# Codebase Exploration Questions

**Feature Context:** Add user control over which email types they receive
**Codebase:** Node.js/TypeScript, 3-year-old e-commerce platform
**Generated:** 2026-05-31T14:15:00Z

## Category 1: Current Email System

### Q1.1: How are emails currently being sent?
**Target Files/Modules:** `src/services/email.service.ts`, `src/jobs/email.worker.ts`
**Why This Matters:** Need to understand current architecture before adding preference checks

### Q1.2: Where are email addresses stored and accessed?
**Target Files/Modules:** `src/db/models/user.model.ts`, `src/db/schema.prisma`
**Why This Matters:** Preferences must be associated with users correctly

### Q1.3: What email types currently exist (transactional, marketing, digest)?
**Target Files/Modules:** `src/constants/emailTypes.ts`, `src/services/email.service.ts`
**Why This Matters:** Preferences are per email type, need to enumerate them

## Category 2: User Preferences Storage

### Q2.1: How are other user preferences currently stored?
**Target Files/Modules:** `src/db/models/user.model.ts`, `src/db/models/userSettings.model.ts`
**Why This Matters:** Want to follow existing pattern (separate table vs. embedded vs. JSON column)

### Q2.2: Is there any existing preference/settings table we should extend?
**Target Files/Modules:** `src/db/schema.prisma`, schema documentation
**Why This Matters:** Avoid creating new tables if existing structure exists

## Category 3: Email Triggering Logic

### Q3.1: Which services/jobs trigger emails (registration, order, promotions)?
**Target Files/Modules:** `src/services/`, `src/jobs/`
**Why This Matters:** Each email trigger point needs to check preferences before sending

### Q3.2: How are email triggers currently conditioned (feature flags, A/B testing)?
**Target Files/Modules:** `src/middleware/featureFlags.ts`, `src/services/email.service.ts`
**Why This Matters:** Preference checks will integrate similarly to existing conditions

## Category 4: Frontend & API

### Q4.1: How do users currently manage account settings?
**Target Files/Modules:** `frontend/pages/AccountSettings/`, `src/api/users/settings`
**Why This Matters:** Email preferences will likely live in same settings UI

### Q4.2: What API endpoint pattern is used for user settings?
**Target Files/Modules:** `src/api/routes/users.ts`, API documentation
**Why This Matters:** Will follow same pattern (GET /api/users/{id}/settings, etc.)

## Category 5: Compliance & Privacy

### Q5.1: Are there any unsubscribe mechanisms already in place?
**Target Files/Modules:** `src/services/email.service.ts`, email templates
**Why This Matters:** Email preferences might integrate with unsubscribe logic

### Q5.2: Are there GDPR or other compliance requirements documented?
**Target Files/Modules:** `docs/compliance/`, `src/constants/`
**Why This Matters:** Preferences might have legal implications (consent recording)

## Exploration Notes

**Implicit Assumptions Being Tested:**
- Assumption 1: Email sending is centralized in email.service.ts
- Assumption 2: Users table has email field
- Assumption 3: Preferences can be stored in separate table (not embedded in User)

**Out of Scope for This Feature:**
- Unsubscribe page (that's separate feature)
- Email template customization (out of scope)
- Analytics on email preferences (future feature)

**Risk Areas to Highlight During Research:**
- How is email sent from jobs (async)? Do jobs have access to user preferences?
- Is there any caching of user data that might be stale?
```

### What good looks like

- 12 questions (within the 8–15 range)
- Each references specific files
- Zero assumptive language (no "should")
- Covers multiple areas: email, storage, triggering, API, compliance
- Each has a "why this matters" rationale

**Time spent:** 20 minutes

---

## Phase 2: Research (R)

### What Happened

The orchestrator spawned the `qrspi-research` agent. This phase enforces the **anchoring firewall**: the agent never sees the ticket. The orchestrator deliberately does NOT pass `TICKET_CONTENT` to it — only `questions.md`, the output path, the template, and the repo root. The research agent's own tool definition also excludes Linear MCP and forbids reading the ticket. Defense in depth: it answers the questions purely by reading the codebase.

The artifact is written to `.qrspi/RUS-42/research.md` — staged alongside `questions.md` and `design.md` for the single `RUS-42/design` commit.

### Agent's Output: research.md (Key Sections)

```markdown
# Codebase Research: Email Preferences Feature

**Codebase:** CheckoutNow e-commerce (Node.js/TypeScript)
**Research Date:** 2026-05-31T14:45:00Z

> Note: the feature ticket is intentionally hidden from this phase. Findings below
> answer questions.md against the codebase, with no knowledge of the proposed feature.

---

## 1. Current Email System Architecture

### Email Service (`src/services/email.service.ts`)
- Central service handling all email sending
- Methods: `sendTransactional()`, `sendMarketing()`, `sendDigest()`
- Uses NodeMailer with Gmail SMTP
- Configured via environment variables

### Email Types Currently Supported

File: `src/constants/emailTypes.ts`

```typescript
export const EMAIL_TYPES = {
  ORDER_CONFIRMATION: 'order_confirmation',
  SHIPPING_UPDATE: 'shipping_update',
  PROMOTION: 'promotion',
  DIGEST: 'weekly_digest',
  PASSWORD_RESET: 'password_reset'
};
```

All 5 types documented, no others found.

### Email Job Queue

File: `src/jobs/email.worker.ts`

- Uses Bull queue (Redis-backed)
- Triggers happen via:
  - Synchronous calls from API (order confirmation)
  - Async job triggers (promotions queued daily)
  - Webhook handlers (shipping updates from carrier)

---

## 2. User & Settings Storage

### Users Table

File: `db/schema.prisma`

```prisma
model User {
  id            String   @id @default(cuid())
  email         String   @unique
  password_hash String
  created_at    DateTime @default(now())

  // Relations
  orders        Order[]
  settings      UserSettings?
}
```

Email is unique constraint—one email per user.

### User Settings Table (Existing)

File: `db/schema.prisma`

```prisma
model UserSettings {
  id              String  @id @default(cuid())
  user_id         String  @unique
  theme           String  @default("light")
  newsletter      Boolean @default(true)

  user User @relation(fields: [user_id], references: [id])
}
```

Status: **Exists but minimal**. Has newsletter preference already (boolean).
Could extend this table or create separate preferences table.

---

## 3. Email Triggering Points

### Trigger 1: Order Confirmation (Transactional)

File: `src/api/routes/orders.ts` (line 124)

```typescript
const order = await OrderService.create(orderData);
// SYNC call
await emailService.sendTransactional(user.email, 'ORDER_CONFIRMATION', {
  order: order
});
```

Status: Synchronous, in request handler. Preference check would block request.

### Trigger 2: Promotions (Marketing)

File: `src/jobs/promotions.worker.ts` (hourly cron)

```typescript
const users = await User.findAll({ newsletter: true });
for (const user of users) {
  await emailQueue.add('send_promotion', { userId: user.id });
}
```

Status: Already has one preference check (`newsletter: true`).
New preferences would add more conditions here.

### Trigger 3: Shipping Updates (Transactional)

File: `src/webhooks/shipping.webhook.ts`
Receives webhook from carrier, triggers email asynchronously.

---

## 4. Existing Patterns for Conditional Logic

### Pattern: Feature Flags

File: `src/middleware/featureFlags.ts`

```typescript
if (await featureFlagService.isEnabled('EMAIL_PROMOTIONS', userId)) {
  // Send email
}
```

Used for A/B testing, gradual rollouts.

### Pattern: User Settings Checks

File: `src/services/order.service.ts`
Checks `userSettings.newsletter` before sending promotional emails.

```typescript
const userSettings = await UserSettings.findOne({ user_id });
if (userSettings.newsletter) {
  // send
}
```

Pattern: Check settings, conditionally send. No caching observed.

---

## 5. API Endpoint Conventions

### Existing Settings Endpoint

File: `src/api/routes/users.ts` (line 200)

```txt
GET /api/v1/users/{id}/settings
Response: { theme: 'light', newsletter: true }

PUT /api/v1/users/{id}/settings
Request body: { theme: 'light', newsletter: true }
Response: { theme: 'light', newsletter: true }
```

Pattern: RESTful, idempotent, returns full settings object.

### Frontend Integration

File: `frontend/pages/AccountSettings.tsx`

- Uses existing /settings endpoint
- Component: `<PreferenceToggle />` (already used for newsletter)
- API call: `updateSettings({ ...settings, ...changes })`

---

## 6. Known Issues & Constraints

### Issue 1: Newsletter Preference Mismatch

File: `src/services/order.service.ts` vs. `src/db/schema.prisma`

- Code checks `userSettings.newsletter`
- But some transactional emails ignore this (order confirmation sends always)
- This is a design decision the design phase must make explicit, not a code bug

**Impact:** Medium. Design needs to decide: are transactional emails exempt from preferences?

### Issue 2: No Email Preference Audit Log

Currently no record of when preferences changed.
Marketing has asked for this—might want to add from the start.

### Issue 3: Email Sending Can Fail Silently

File: `src/services/email.service.ts` (line 45)

```typescript
try {
  await transporter.sendMail(...);
} catch (error) {
  logger.error('Email send failed', { error });
  // No retry, no user notification
}
```

Email failures are logged but not surfaced to user.

---

## 7. Replication & Caching

### Database Replication

- Write: Primary database (PostgreSQL, single)
- Read: 2 read replicas (5-minute replication lag)
- Email service: Reads from primary (immediate consistency needed)

### Caching

- UserSettings is NOT cached
- User object IS cached (Redis, 5-minute TTL)
- If user preferences are embedded in User cache, they'd be stale for 5 min

---

## 8. Existing Patterns Worth Reusing

- **Service layer pattern:** All domain logic in services (e.g., EmailService)
- **Conditional email sending:** Already use settings checks for newsletter
- **API conventions:** RESTful, PUT for updates
- **Component patterns:** PreferenceToggle already exists in UI
- **TypeScript strict mode:** All code is typed
- **Error handling pattern:** Try/catch, log, return error

---

## 9. Areas of Uncertainty

**Unclear:** Should transactional emails (password reset, order confirmation) respect user preferences?

- Code sends them always
- UX perspective: users might not want any emails
- Compliance perspective: password reset must be delivered
- Need clarification before design

**Unclear:** Should preference changes be logged for audit trail?

- Marketing wants this (for analytics)
- No current logging infrastructure for settings changes
- Nice to have but not essential for MVP

---

## Summary Stats

- Files inspected: 18
- Email types: 5 (transactional, marketing, digest)
- Triggering points: 3 main (order, promotions, shipping)
- Existing preferences: 1 (newsletter boolean)
- API pattern established: YES
- Frontend component exists: YES
- Confidence in findings: 95%
```

### What good looks like

- Zero "should" language
- All claims code-referenced (every claim has a file path)
- Database schema copied exactly from schema.prisma
- Uncertainty flagged ("Unclear:" sections)
- Known issues documented (Issue 1–3) — including the note that Issue 1 is a design decision, not a bug
- A new team member could learn the system from this document

**Time spent:** 45 minutes

---

## Phase 3: Design (D)

### What Actually Happened

The orchestrator spawned the `qrspi-design` agent. Unlike research, design DOES receive the ticket content again — it combines the ticket, the answered questions, and the research findings into pattern decisions, a risk register, the delta, and open questions.

The artifact is written to `.qrspi/RUS-42/design.md` — the third and final design-phase artifact, committed together on `RUS-42/design`.

### Agent's Proposal

```markdown
# Design Document: User Email Preferences

## Current State Analysis

### What Works Today
- Email service is centralized and well-structured
- Settings infrastructure already exists (UserSettings table)
- Frontend already has preference UI patterns (PreferenceToggle)
- Email triggering logic is in place and handles various types

### What's Constrained
- Newsletter preference already exists (boolean field)
- Transactional emails currently send regardless of preferences
- No audit logging of preference changes
- 5-minute replication lag on read replicas

### What's Missing
- Granular email type preferences (currently only newsletter)
- User control over email frequencies (immediate vs. digest)
- Preference changes recorded for compliance

## Desired End State

Users can selectively disable:
- Promotional emails
- Weekly digest

(Order confirmations always send — mandatory per the ticket constraints)

## Architectural Decisions

### Decision 1: Preference Storage

**Options:**
- Option A: Extend existing newsletter boolean to preferences JSON column
- Option B: Create separate UserEmailPreferences table
- Option C: Store preferences in Redis cache only

**Decision:** Option B (separate UserEmailPreferences table)

**Rationale:**
- Aligns with existing pattern (UserNotifications table uses same approach)
- Migrations are simpler and more type-safe
- Each preference is a row: (user_id, email_type, enabled, frequency)
- Scales well if preferences become complex later

**Trade-offs:**
- Plus: Follows existing pattern (UserNotifications)
- Plus: Simpler, more predictable migrations
- Plus: Indexed query by (user_id, email_type)
- Minus: Slightly more joins for reads (negligible at our scale)

### Decision 2: Transactional Email Handling

**Options:**
- Option A: Transactional emails always send (ignore preferences)
- Option B: All emails respect preferences (user might miss critical info)

**Decision:** Option A (transactional always send)

**Rationale:**
- Order confirmations are mandatory per the ticket's AC4 and Constraints
- Research showed order confirmations are critical for fulfillment
- Password resets must be delivered

**Trade-offs:**
- Plus: User won't miss critical info
- Minus: User can't disable order confirmations even if annoyed

## Risk Register

- R1 (Medium): Promotions worker already filters on `newsletter`; the new preference
  table must not double-suppress or conflict with that legacy flag. Mitigation: Slice 3
  replaces the `newsletter` check with the preference lookup.
- R2 (Low): User object is cached 5 min; preferences live in a separate, uncached table,
  so AC3 (immediate effect) holds. No cache invalidation needed.

## Open Questions

- Audit logging of preference changes: deferred to a future ticket (not in MVP).
```

### The Design Review gate

The orchestrator finishes the design phase, commits the three artifacts as the single commit on `RUS-42/design`, and **submits the Design PR**. It then projects the Linear status to **Design Review** (best-effort) and stops.

```
gt create RUS-42/design --no-interactive -m "RUS-42 [QR]: Design"
gt submit --no-edit --no-interactive
→ Design PR: https://github.com/.../pull/318  (RUS-42/design → main)
Linear (best-effort): RUS-42 → Design Review
"Design submitted. PR: <url>. → Design Review."
```

This is a **human turn**. The engineer reviews the Design PR. Suppose they leave one comment:

> "On Decision 1: confirm this matches the UserNotifications pattern — separate table, one
> row per type. Looks right. Approving."

The PR review state is the gate, not Linear. On the next `/qrspi-work RUS-42` invocation, the resolver reads the Design PR. If it had unresolved threads, the action would be `revise` — address the feedback bounded to the design-phase artifacts only (Questions → Research → Design), amend the `RUS-42/design` commit, and re-submit. Here the comment is approving with no unresolved threads, so the resolver returns `wait` and the orchestrator stops.

The engineer **approves the Design PR**. That approval (`reviewDecision == APPROVED`, zero unresolved threads) is the only thing that unblocks the plan phase — the next `/qrspi-work RUS-42` will resolve to `advance` and build the plan PR stacked on top.

**Time spent:** 40 minutes (30 min agent, 10 min review)

---

## The Plan Phase (Plan PR, stacked on design)

With the Design PR approved, the next `/qrspi-work RUS-42` resolves to `advance` and runs the **plan phase**: Structure, Plan, Work Tree. These three artifacts are committed as a single commit on a **new** `RUS-42/plan` branch **stacked on `RUS-42/design`** — a separate branch and a separate PR from the design phase.

---

## Phase 4: Structure (S)

### Agent's Output

The orchestrator spawned the `qrspi-structure` agent (input: `design.md`). It defines the vertical slices, the shared types, and the cross-slice contracts. Output: `.qrspi/RUS-42/structure.md` (staged for the `RUS-42/plan` commit).

```markdown
# Structure Outline: Email Preferences Feature

**Build Order:** Vertical slices

## Slice 1: Mock API + Frontend (2.5 hours)

**Objective:** Users see preferences UI, can toggle settings, API accepts changes (no persistence)

**Files to Create/Modify:**
- `src/models/emailPreferences.model.ts` (NEW) - Type definitions
- `src/api/routes/users.ts` (MODIFY) - Add mock endpoint
- `frontend/pages/AccountSettings.tsx` (MODIFY) - Add email prefs section
- `frontend/components/EmailPreferences.tsx` (NEW) - Preference toggles
- `tests/integration/emailPreferences.integration.test.ts` (NEW)

**Interface Definition (cross-slice contract):**

```typescript
// emailPreferences.model.ts
export enum EmailType {
  ORDER_CONFIRMATION = 'order_confirmation',
  SHIPPING_UPDATE = 'shipping_update',
  PROMOTION = 'promotion',
  DIGEST = 'digest'
}

export enum PreferenceFrequency {
  IMMEDIATE = 'immediate',
  DAILY = 'daily',
  NEVER = 'never'
}

export interface UserEmailPreference {
  email_type: EmailType;
  enabled: boolean;
  frequency: PreferenceFrequency;
  updated_at: Date;
}

// API endpoints (mocked in Slice 1)
GET /api/v1/users/{id}/preferences/email
→ Returns hardcoded preferences for user

PUT /api/v1/users/{id}/preferences/email
→ Accepts update, returns success (doesn't persist)
```

**Definition of Done:**
- [ ] Email preferences page renders with 4 toggles + frequency selects
- [ ] Clicking toggle sends PUT request
- [ ] Page doesn't error
- [ ] Integration test passes: GET → modify → PUT → returns success

**Dependencies:** None (fully mocked)
**Lines of Code Estimate:** 200-250

---

## Slice 2: Real Database + Persistence (3 hours)

**Objective:** Preferences actually persist to database. Real queries work.

**Files to Create/Modify:**
- `db/schema.prisma` (MODIFY) - Add UserEmailPreferences model
- `db/migrations/2026-05-31_add_email_preferences.sql` (NEW)
- `src/services/preferences.service.ts` (NEW) - Database queries
- `src/api/routes/users.ts` (MODIFY) - Call service instead of mock
- `tests/integration/emailPreferences.integration.test.ts` (MODIFY)

**Definition of Done:**
- [ ] Table created with proper indexes
- [ ] Service queries database correctly
- [ ] Data persists across page refreshes
- [ ] Integration test: Write → Read → Verify
- [ ] Migration is idempotent

**Dependencies:** Slice 1 (API contract must be stable)
**Lines of Code Estimate:** 250-300

---

## Slice 3: Email Sending Respects Preferences (2.5 hours)

**Objective:** When email is triggered, check preferences before sending.

**Files to Create/Modify:**
- `src/services/email.service.ts` (MODIFY) - Add preference checks
- `src/services/preferences.service.ts` (MODIFY) - Add query method
- `src/jobs/promotions.worker.ts` (MODIFY) - Replace legacy newsletter check
- `tests/unit/email.service.test.ts` (NEW) - Test preference logic
- `tests/integration/emailSending.integration.test.ts` (MODIFY)

**Definition of Done:**
- [ ] Promotional emails check preferences before sending
- [ ] Weekly digest checks preferences
- [ ] Order confirmation emails ignore preferences (always send)
- [ ] Unit tests cover all cases
- [ ] Integration test: Trigger email → Verify sent/not-sent per preference

**Dependencies:** Slice 2 (preferences must be in database)
**Lines of Code Estimate:** 150-200

---

## Critical Path

Slice 1 (2.5h) → Slice 2 (3h) → Slice 3 (2.5h) = 8 hours total

All slices are sequential (no parallelization possible).
```

### What good looks like

- End-to-end testable: each slice has a working test
- Vertical not horizontal: not "all DB then all API"
- Realistic estimates that correlate with the LOC estimates
- Clear dependencies: S1 → S2 → S3

**Time spent:** 30 minutes

---

## Phase 5: Plan (P)

### Agent's Output (Selected Sections)

The `qrspi-plan` agent (input: `structure.md`, `design.md`) writes atomic implementation steps per slice with verification checkpoints. Output: `.qrspi/RUS-42/plan.md` (staged for the `RUS-42/plan` commit).

```markdown
# Implementation Plan: Email Preferences - Slice 1

**Slice:** 1 (Mock API + Frontend)
**Estimated Effort:** 2.5 hours
**Confidence:** High (clear requirements, no unknowns)

---

## File-by-File Breakdown

### File 1: `src/models/emailPreferences.model.ts`

**Purpose:** Type definitions for email preferences

**Types:**
```typescript
export enum EmailType {
  ORDER_CONFIRMATION = 'order_confirmation',
  SHIPPING_UPDATE = 'shipping_update',
  PROMOTION = 'promotion',
  DIGEST = 'digest'
}

export enum PreferenceFrequency {
  IMMEDIATE = 'immediate',
  DAILY = 'daily',
  NEVER = 'never'
}

export interface UserEmailPreference {
  email_type: EmailType;
  enabled: boolean;
  frequency: PreferenceFrequency;
  updated_at: Date;
}

export const DEFAULT_PREFERENCES: Record<EmailType, UserEmailPreference> = {
  [EmailType.ORDER_CONFIRMATION]: {
    email_type: EmailType.ORDER_CONFIRMATION,
    enabled: true,
    frequency: PreferenceFrequency.IMMEDIATE
  },
  [EmailType.SHIPPING_UPDATE]: {
    email_type: EmailType.SHIPPING_UPDATE,
    enabled: true,
    frequency: PreferenceFrequency.IMMEDIATE
  },
  // ... other defaults
};
```

**Dependencies:** None
**Testing:** Type compilation only
**Estimated LOC:** 40-50
**Notes:** Keep enums synchronized with EmailTypes constant in codebase

---

### File 2: `src/api/routes/users.ts` (ADD ENDPOINT)

**Purpose:** HTTP handler for email preferences endpoints

**New Functions:**

```typescript
export async function getEmailPreferences(
  req: Express.Request,
  res: Express.Response
): Promise<void> {
  // GET /api/v1/users/:id/preferences/email
  // For Slice 1: return DEFAULT_PREFERENCES
}

export async function updateEmailPreferences(
  req: Express.Request,
  res: Express.Response
): Promise<void> {
  // PUT /api/v1/users/:id/preferences/email
  // For Slice 1: return updated preferences (don't persist)
}
```

**Dependencies:** emailPreferences.model.ts

**Error Handling:**
- 400: Invalid user ID or request body
- 401: Not authenticated
- 404: User not found (real check in Slice 2)
- 200: Success

**Verification checkpoint:** Mock all calls, test request/response
**Estimated LOC:** 60-80
**Notes:** Use existing auth + validateUserIdParam middleware; follow existing error pattern

---

### File 3: `frontend/components/EmailPreferences.tsx`

**Purpose:** Preference toggles component

**Key JSX:**

```typescript
export function EmailPreferences({ preferences, onUpdate }) {
  return (
    <div className="email-prefs">
      {Object.entries(preferences).map(([type, pref]) => (
        <div key={type} className="pref-row">
          <Toggle
            label={prettyLabel(type)}
            checked={pref.enabled}
            onChange={(enabled) => onUpdate(type, enabled)}
          />
          {pref.enabled && (
            <FrequencySelect
              value={pref.frequency}
              onChange={(freq) => onUpdate(type, freq)}
              options={['immediate', 'daily', 'never']}
            />
          )}
        </div>
      ))}
    </div>
  );
}
```

**Dependencies:** React, existing Toggle component
**Verification checkpoint:** Component renders, toggles work, onChange fires
**Estimated LOC:** 80-100

---

### File 4: `tests/integration/emailPreferences.integration.test.ts`

**Purpose:** Integration test for Slice 1

```typescript
describe('Slice 1: Email Preferences Mock API', () => {
  it('GET returns mock preferences', async () => {
    const res = await request(app)
      .get('/api/v1/users/test-user/preferences/email')
      .set('Authorization', `Bearer ${token}`);

    expect(res.status).toBe(200);
    expect(res.body).toHaveProperty('order_confirmation');
    expect(res.body.order_confirmation.enabled).toBe(true);
  });

  it('PUT accepts update and returns updated preferences', async () => {
    const res = await request(app)
      .put('/api/v1/users/test-user/preferences/email')
      .set('Authorization', `Bearer ${token}`)
      .send({ promotion: { enabled: false } });

    expect(res.status).toBe(200);
    expect(res.body.promotion.enabled).toBe(false);
  });
});
```

**Estimated LOC:** 80-100

---

## Implementation Sequence

1. Create emailPreferences.model.ts (40 min)
2. Add GET endpoint (20 min)
3. Add PUT endpoint (20 min)
4. Create EmailPreferences component (40 min)
5. Wire component to API calls (30 min)
6. Write integration tests (50 min)

Total: ~3.5 hours (higher than estimate, includes buffer)

---

## Verification Gates (per slice)

- [ ] TypeScript: `npm run type-check` passes
- [ ] Lint: `npm run lint` passes
- [ ] Tests: `npm run test` passes
- [ ] No console.log() except logging service
- [ ] JSDoc on public exports
- [ ] Import paths use established patterns

---

## Notes

### Patterns to Follow
- Error handling: Use AppError class (existing pattern)
- Middleware: Use existing auth, validation middleware
- Component state: Use React hooks
- API responses: Follow existing { data, error, success } format

### Pitfalls to Avoid
- Don't create new middleware (reuse existing auth)
- Don't hardcode email types (use enum from model)
```

### What good looks like

- Zero new architectural decisions — all reference design.md
- File breakdown is specific (types, functions, dependencies)
- Verification checkpoints per file/slice
- No vague TODOs
- Effort estimates correlate with LOC

**Time spent:** 40 minutes

---

## Phase 6: Work Tree (W)

### Agent's Output: worktree.md (Slice 1 session)

The `qrspi-worktree` agent (input: `plan.md`) builds a **session-aware task DAG** with per-session context budgets. Each slice maps to one fresh implementation session. Output: `.qrspi/RUS-42/worktree.md` (the third and final plan-phase artifact, committed together on `RUS-42/plan`).

```markdown
# Work Tree: Email Preferences

**Total slices/sessions:** 3 (one fresh session per slice)
**This section: Slice 1 session (Mock API + Frontend)**
**Context budget for this session:** ~40% (well under the /context threshold)
**Total Tasks:** 8

## Task DAG — Slice 1 session

├── T1: Types Definition
│   ├── T1.1: Define EmailType enum
│   │   Effort: 15 min · Files: src/models/emailPreferences.model.ts
│   │   Done: Enum has all 4 email types · Depends: None
│   ├── T1.2: Define PreferenceFrequency enum
│   │   Effort: 10 min · Done: Enum compiles · Depends: T1.1
│   └── T1.3: Define DEFAULT_PREFERENCES constant
│       Effort: 10 min · Done: all 4 types with defaults · Depends: T1.1, T1.2
│
├── T2: API Endpoints
│   ├── T2.1: Implement GET endpoint
│   │   Effort: 25 min · Done: GET returns 200 · Depends: T1.1–T1.3
│   └── T2.2: Implement PUT endpoint
│       Effort: 25 min · Done: PUT returns 200 with updated prefs · Depends: T2.1
│
├── T3: Frontend Component
│   ├── T3.1: Create EmailPreferences component skeleton
│   │   Effort: 20 min · Done: renders without error · Depends: T1.1
│   ├── T3.2: Add toggles for each email type
│   │   Effort: 20 min · Done: 4 toggles visible · Depends: T3.1
│   └── T3.3: Add frequency selects (show when enabled)
│       Effort: 15 min · Done: select shown only when toggle on · Depends: T3.2
│
├── T4: Integration
│   ├── T4.1: Wire component to API calls
│   │   Effort: 30 min · Files: frontend/pages/AccountSettings.tsx
│   │   Done: toggle calls PUT endpoint · Depends: T2.1, T2.2, T3.3
│   └── T4.2: Add error handling
│       Effort: 15 min · Done: error shown on API failure · Depends: T4.1
│
└── T5: Testing
    ├── T5.1: Write integration tests
    │   Effort: 40 min · Done: tests pass · Depends: T2.1, T2.2, T3.1–T3.3
    └── T5.2: Verify gates (type-check, lint, test)
        Effort: 15 min · Done: all gates pass · Depends: T5.1

## Critical Path (Slice 1 session)

T1.1 → T1.2 → T1.3 → T2.1 → T2.2 → T3.1 → T3.2 → T3.3 → T4.1 → T5.1 → T5.2
= 225 minutes ≈ 3.75 hours

## Session boundary

Slices 2 and 3 each run in their own fresh session (per the "fresh /clear session
between slices" rule), each with its own task DAG and context budget.
```

### The Plan Review gate

The plan phase is done. Its three artifacts (`structure.md`, `plan.md`, `worktree.md`) sit on the single commit on `RUS-42/plan`, stacked on `RUS-42/design`. The orchestrator **submits the Plan PR** — a separate PR from the design PR, with the design PR as its base — and projects the Linear status to **Plan Review**.

```
gt create RUS-42/plan --no-interactive -m "RUS-42 [SP]: Plan"
gt submit --no-edit --no-interactive
→ Plan PR #319 opened  (RUS-42/plan → RUS-42/design)
Linear (best-effort): RUS-42 → Plan Review
"Plan submitted. PR: <url>. → Plan Review."
```

Second **human turn**. The engineer reviews the Plan PR. Suppose they leave one comment on `structure.md` (an unresolved thread, not a formal change request):

> "Decision 1 is right, but call out explicitly in Slice 3 that we're removing the legacy
> `newsletter` check from promotions.worker.ts so we don't double-suppress."

Because this comment is on the **plan** PR (the active phase), it does not reset the design — it is a within-phase `revise`. On an explicit re-invocation, the orchestrator reads the unresolved thread, addresses it bounded to the plan-phase artifacts (Slice 3 in `structure.md` already lists the `promotions.worker.ts` change, so this is a one-line clarification), amends the `RUS-42/plan` commit, and re-submits the Plan PR. (If instead the reviewer had filed a formal `CHANGES_REQUESTED` on the **design** PR, that would `reset`: the plan branch and PR would be discarded automatically and the ticket would return to design.)

The engineer **approves the Plan PR**. Approval (with zero unresolved threads) is the only thing that unblocks implementation — the next `/qrspi-work RUS-42` resolves to `advance` and builds the slice stack on top of `RUS-42/plan`.

**Time spent:** Work Tree 30 min + Plan Review 10 min

---

## Phase 7: Implement (I)

With the Plan PR approved, `/qrspi-work RUS-42` resolves to `advance` and runs implementation. It reads `structure.md` to count the slices, then implements each slice in its own fresh session by spawning the `qrspi-implement` agent. Each slice becomes its own branch **stacked** on the previous one via Graphite:

- Slice 1 branches off `RUS-42/plan`
- Slice 2 branches off `RUS-42/slice-1`
- Slice 3 branches off `RUS-42/slice-2`

The implement agent writes code and appends to `.qrspi/RUS-42/impl-log.md`. The orchestrator is the only place commits happen — sub-agents never commit. After each slice, it stages every changed file (code, tests, and the impl-log entry) and creates the slice branch.

### Example commits (Slice 1)

```txt
Branch: RUS-42/slice-1  (parent: RUS-42/plan)
Commit: "RUS-42 [I] 1/3: Mock API + Frontend"

Files:
  src/models/emailPreferences.model.ts            (+50)
  src/api/routes/users.ts                          (+130)
  frontend/components/EmailPreferences.tsx         (+95)
  frontend/pages/AccountSettings.tsx               (+20)
  tests/integration/emailPreferences.integration.test.ts (+90)
  .qrspi/RUS-42/impl-log.md                        (slice-1 entry)

Verification:
  ✅ TypeScript: 0 errors
  ✅ Lint: 0 errors
  ✅ Integration tests: 5 pass

Actual time: ~3.5 hours (estimate was 3.75 hours)
```

Slices 2 and 3 follow the same pattern, each in a fresh session, each stacked on the prior slice.

### impl-log.md (Slice 1 entry)

```markdown
## Slice 1 — Mock API + Frontend

**Status:** complete
**Time:** 3.5h (est. 3.75h)

**What was built:** Type definitions, mock GET/PUT endpoints, EmailPreferences
component wired into AccountSettings. No persistence yet.

**Deviations from plan:** None.

**Notes for next session (Slice 2):**
- API contract is stable: GET/PUT /api/v1/users/{id}/preferences/email
- Slice 2 replaces the mock handler body with preferences.service.ts calls
- DEFAULT_PREFERENCES in the model is the seed for new users
```

**Time spent:** ~3.5 hours per slice session

---

## Phase 8: PR — submit the slice stack and move to Code Review

### What Actually Happened

After all slices are implemented, the orchestrator spawns the `qrspi-pr` agent to produce `.qrspi/RUS-42/pr-summary.md`, which maps acceptance criteria to implementation and tests. The summary is amended into the **last** slice commit (not a separate commit). The orchestrator then submits the **entire stack** with Graphite — **one PR per slice** — and sets the PR summary as the body on the bottom (slice-1) PR. The slice stack is stacked on the still-open Plan PR, which is stacked on the still-open Design PR; nothing has merged.

```
gt submit --stack --no-edit --no-interactive
→ PR #321  RUS-42/slice-1 → RUS-42/plan   (body = pr-summary.md)
→ PR #322  RUS-42/slice-2 → RUS-42/slice-1
→ PR #323  RUS-42/slice-3 → RUS-42/slice-2
Linear (best-effort): RUS-42 → Code Review
"Implementation submitted: 3 slice PRs. → Code Review."
```

### pr-summary.md (on the slice-1 PR)

```markdown
# Pull Request: User Email Preferences (RUS-42)

Stacked PRs (Graphite): slice-1 → slice-2 → slice-3

## Acceptance Criteria → Implementation

| AC | Where it's satisfied | Tests |
|----|----------------------|-------|
| AC1 (toggle promotions) | Slice 1 UI + Slice 2 persistence + Slice 3 send gate | emailPreferences.integration, emailSending.integration |
| AC2 (toggle digest) | same path as AC1 | emailSending.integration |
| AC3 (immediate effect) | preferences table is uncached; read on every send | emailSending.integration |
| AC4 (order confirmations always send) | Slice 3 exempts transactional types | email.service.test |

## What Changed (by slice)

- **Slice 1** — Mock API + frontend toggles. No persistence.
- **Slice 2** — UserEmailPreferences table, migration, preferences.service.ts.
- **Slice 3** — email.service + promotions.worker check preferences;
  legacy `newsletter` filter removed to avoid double-suppression.

## Design Alignment

- ✅ Separate UserEmailPreferences table (Decision 1)
- ✅ Transactional emails always send (Decision 2 / AC4)
- ✅ API follows existing /api/v1/users/{id}/... convention (from research)
- ✅ Reuses existing Toggle component

## Risk Assessment

- Slice 3 is the highest-risk change (touches live send paths). Covered by unit +
  integration tests for both the "send" and "suppress" branches.
```

### The Code Review gate

Third **human turn**. The engineer reviews the stack. On an explicit `/qrspi-work RUS-42` re-invocation, the resolver reads review state across all slice PRs (and the upstream design/plan PRs). If a slice PR has unresolved threads, the action is `revise`: address them starting from the lowest-numbered affected slice (changes propagate upward through the stack via `gt modify`, which auto-restacks descendants), then re-submit the stack. Here, suppose the review is clean:

> "Clean stack. Tests cover the suppress/send branches. Approving all three."

The engineer **approves all three slice PRs**. Now every PR in the stack — design, plan, and all slices — is approved with zero unresolved threads. The resolver's land predicate (`READY(design) AND READY(plan) AND ∀ slices READY(slice_i)`) is satisfied, so the next `/qrspi-work RUS-42` resolves to `land`. The orchestrator restacks onto `main` and merges the whole stack **bottom-up** with `gt merge` — nothing merged before this point.

```
gt checkout RUS-42/slice-1 --no-interactive
gt submit --stack --no-edit --no-interactive   # ensure remotes current
gt merge --confirm --no-interactive            # merges design → plan → slice-1..3, bottom-up
```

After the merge, the orchestrator syncs `main` (`gt sync --force`, which prunes the merged branches), removes the `.qrspi/RUS-42/` artifacts and the `.worktrees/RUS-42/` worktree, and projects the Linear status to **Done** (best-effort).

**Time spent:** PR generation 10 min + Code Review 15 min

---

## Summary: Total QRSPI Time

```txt
Phase 0 (Ticket):            15 min
Phase 1 (Questions):         20 min
Phase 2 (Research):          45 min
Phase 3 (Design):            40 min  ──┐
[Design PR → approved]                 ├─ design phase + Design PR
Phase 4 (Structure):         30 min  ──┐
Phase 5 (Plan):              40 min    ├─ plan phase + Plan PR
Phase 6 (Work Tree):         30 min  ──┘
[Plan PR → approved]
Phase 7 (Implement):    ~3.5 h/slice × 3 slices
Phase 8 (PR):                10 min
[Slice PRs → all approved → land stack]

Planning total (phases 0–6 + 2 PRs): ~3.5 hours
Implementation total (3 slices):     ~9–10 hours
```

Each phase shipped as its **own** stacked PR: `RUS-42/design` → `RUS-42/plan` →
`RUS-42/slice-1..3`. The Design PR was opened and approved first; the Plan PR was stacked
on it and approved; the three slice PRs were stacked on plan. The whole stack was held open
and landed **bottom-up** only once every PR was approved + clean. Code integrated cleanly —
no rework needed.

---

## Key Takeaways from This Example

1. **PR review state is the authority, not Linear.** `/qrspi-work` resolves what to do from the PR stack (via the tested resolver `scripts/qrspi_resolve_state.py`); a phase is ready when its PR is `APPROVED` with zero unresolved threads. Linear plays exactly two roles: an **entry gate** (assigned + `Selected`) and a **best-effort reporting projection** that never blocks work. Local files under `.qrspi/RUS-42/` hold the artifacts.

2. **Approving a phase PR auto-advances; a change request resets.** Approving the Design PR builds the Plan PR on top; approving the Plan PR builds the slice stack. A formal `CHANGES_REQUESTED` on an upstream PR automatically discards the downstream phases (PRs closed, branches deleted, stale artifacts removed) and returns the ticket there. Within-phase revision is manual. This is where design issues get caught early — at the design gate, not in code review.

3. **One PR per phase, stacked, held open.** `RUS-42/design` → `RUS-42/plan` → `RUS-42/slice-1..N`, each its own branch and PR, each a single commit. Nothing merges until the whole feature is approved, then the stack lands bottom-up. The old single `RUS-42/planning` branch is gone.

4. **The research firewall prevents anchoring.** Research never sees the ticket and has no Linear access — it answers the questions against the codebase alone, so its findings aren't bent to fit the proposed solution.

5. **Agents vs. skills.** Phase logic lives in `.claude/agents/qrspi-<phase>.md` (tool-locked, spawned by `subagent_type`). The `.claude/skills/qrspi-<phase>/` wrappers exist for manual invocation; `/qrspi-work` orchestrates the agents directly.

6. **Vertical slices ship as a stack.** Each slice is end-to-end testable and becomes its own Graphite PR stacked on the previous one. Slice 1 ships with no database but is fully testable.

7. **Batch mode for many tickets.** `.claude/workflows/qrspi-batch.js` drives many assigned tickets one PR-gated step forward — the autonomously-runnable actions (`run_design`, `advance`, `submit`, `land`, and automatic `reset`) — by spawning the typed phase agents. It deliberately leaves `wait` (not yet approved) and the manual `revise` path untouched.

This is what QRSPI looks like in practice. Not theoretical — actual artifacts, actual PR gates, actual stacked PRs.
