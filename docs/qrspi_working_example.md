# QRSPI Working Example: Real Feature Walkthrough

A complete, annotated example of one feature going through all 8 QRSPI phases. Use this as a reference for what good outputs look like at each stage.

---

## Feature: Add User Email Preferences

Simple feature that integrates with an existing e-commerce system. This walkthrough shows what real QRSPI work looks like.

---

## Phase 1: Questions (Q)

### What Actually Happened

Engineer initiated: "We need to let users control which emails they receive."

Agent received Q1.1 prompt from qrspi_test_prompts.md (adapted for email system).

### Agent's Output: questions.md

```markdown
# Codebase Exploration Questions

**Feature Context:** Add user control over which email types they receive
**Codebase:** Node.js/TypeScript, 3-year-old e-commerce platform
**Generated:** 2025-04-05T14:15:00Z

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

### Engineer's Validation

Checklist:

- [x] 12 questions minimum → Has 12 questions ✅
- [x] Each references specific files → All do ✅
- [x] Zero assumptive language → Zero instances of "should" ✅
- [x] Covers multiple areas → Auth, email, storage, API, compliance ✅
- [x] Each has "why this matters" → All do ✅

**Engineer's notes:** "Good. Questions cover what I need to understand. One minor thing: I'd add a question about error handling (what happens if email fails). But this is solid."

**Time spent:** 20 minutes

---

## Phase 2: Research (R)

### What Happened

Engineer ran research prompt with the questions.md as input.

Agent explored codebase, read actual code, documented findings.

### Agent's Output: research.md (Key Sections)

```markdown
# Codebase Research: Email Preferences Feature

**Feature:** User Email Preferences
**Codebase:** CheckoutNow e-commerce (Node.js/TypeScript)
**Research Date:** 2025-04-05T14:45:00Z
**Researcher Model:** Claude Opus 4.5

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
- Behavior is inconsistent

**Impact:** Medium. Design needs to clarify: are transactional emails exempt from preferences?

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

```md

### Engineer's Validation

Checklist:
- [x] Zero "should" language → Zero instances ✅
- [x] All claims code-referenced → Every claim has file path ✅
- [x] Database schema exact → Copied from schema.prisma ✅
- [x] Uncertainty flagged → "Unclear:" sections present ✅
- [x] Known issues documented → Issue 1-3 listed ✅
- [x] New team member could learn → Yes ✅

**Engineer's feedback:** 
"One thing: In Issue 1, you say 'behavior is inconsistent.' That's accurate 
but might want to note: 'This is a design decision we need to make, not a bug.'"

**Agent's response:** "Right. Updated Issue 1 to clarify: this is a decision 
point for the design phase, not a code bug."

**Time spent:** 45 minutes

---

## Phase 3: Design (D)

### What Actually Happened

Engineer hid the feature ticket. Agent read research.md and proposed architecture.

Then engineer gave feedback (brain surgery).

### Agent's Initial Proposal (Before Feedback)

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
- Order confirmations / Shipping updates
- Promotional emails
- Weekly digest
- All non-critical emails

(Password reset always sends—non-negotiable)

## Architectural Decisions

### Decision 1: Preference Storage

**Options:**
- Option A: Extend existing newsletter boolean to preferences JSON column
- Option B: Create separate UserEmailPreferences table  
- Option C: Store preferences in Redis cache only

**Decision:** Option A (JSON column in UserSettings)

**Rationale:**
- UserSettings already extends per-user config
- JSON allows flexible email type structure
- Keeps settings in one place

**Trade-offs:**
- Plus: No new table, migration is simple
- Plus: Reads don't require joins
- Minus: Schema less documented (JSON is opaque)

### Decision 2: Transactional Email Handling

**Options:**
- Option A: Transactional emails always send (ignore preferences)
- Option B: All emails respect preferences (user might miss critical info)
- Option C: Transactional emails send, but user can snooze for 24h

**Decision:** Option A (transactional always send)

**Rationale:**
- Research showed order confirmations are critical for fulfillment
- Users need password resets—can't be blocked
- Marketing researched: users expect order updates

**Trade-offs:**
- Plus: User won't miss critical info
- Minus: User can't disable even if annoyed
```

### Engineer's Feedback (Brain Surgery)

Engineer read the design and noted:

> "On Decision 1: We moved away from JSON columns in 2023 because it made
> migrations harder. Use a separate `UserEmailPreferences` table with a
> preference per row (email_type, enabled, frequency). Follows our pattern
> from UserNotifications table."

Agent's response: "Understood. JSON was a pattern mismatch. Switching to
separate table following existing pattern."

Agent's revised design (Decision 1 only):

```markdown
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

**Constraints from Research:**
- Research revealed UserNotifications uses separate table pattern
- Discovered we moved away from JSON columns in 2023
- This decision respects that architectural constraint

**Trade-offs:**
- Plus: Follows existing pattern (UserNotifications)
- Plus: Simpler, more predictable migrations
- Plus: Indexed query by (user_id, email_type)
- Minus: Slightly more joins for reads (negligible at our scale)
```

### Final Approved Design

Design looks good after correction. Approved by engineer.

Key decisions:

1. Separate `UserEmailPreferences` table (one row per email type)
2. Transactional emails send regardless (user choice doesn't override)
3. Frequency preference: `immediate`, `daily`, `never`
4. API endpoint: `PUT /api/v1/users/{id}/preferences/email`
5. Audit logging: Not in MVP (documented as future work)

**Time spent:** 40 minutes (30 min agent, 10 min feedback/correction)

---

## Phase 4: Structure (S)

### Agent's Output

```markdown
# Structure Outline: Email Preferences Feature

**Approved Design:** ✓
**Build Order:** Vertical slices

## Slice 1: Mock API + Frontend (2.5 hours)

**Objective:** Users see preferences UI, can toggle settings, API accepts changes (no persistence)

**Files to Create/Modify:**
- `src/models/emailPreferences.model.ts` (NEW) - Type definitions
- `src/api/routes/users.ts` (MODIFY) - Add mock endpoint
- `frontend/pages/AccountSettings.tsx` (MODIFY) - Add email prefs section
- `frontend/components/EmailPreferences.tsx` (NEW) - Preference toggles
- `tests/integration/emailPreferences.integration.test.ts` (NEW)

**Interface Definition:**

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

**Can Run in Parallel:** Yes

**Lines of Code Estimate:** 200-250

---

## Slice 2: Real Database + Persistence (3 hours)

**Objective:** Preferences actually persist to database. Real queries work.

**Files to Create/Modify:**

- `db/schema.prisma` (MODIFY) - Add UserEmailPreferences model
- `db/migrations/2025-04-05_add_email_preferences.sql` (NEW)
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

**Can Run in Parallel:** No

**Lines of Code Estimate:** 250-300

---

## Slice 3: Email Sending Respects Preferences (2.5 hours)

**Objective:** When email is triggered, check preferences before sending.

**Files to Create/Modify:**

- `src/services/email.service.ts` (MODIFY) - Add preference checks
- `src/services/preferences.service.ts` (MODIFY) - Add query method
- `tests/unit/email.service.test.ts` (NEW) - Test preference logic
- `tests/integration/emailSending.integration.test.ts` (MODIFY)

**Definition of Done:**

- [ ] Promotional emails check preferences before sending
- [ ] Shipping updates check preferences
- [ ] Transactional emails (order confirmation) ignore preferences
- [ ] Unit tests cover all cases
- [ ] Integration test: Trigger email → Verify sent/not-sent per preference

**Dependencies:** Slice 2 (preferences must be in database)

**Can Run in Parallel:** No (depends on Slice 2)

**Lines of Code Estimate:** 150-200

---

## Critical Path

Slice 1 (2.5h) → Slice 2 (3h) → Slice 3 (2.5h) = 8 hours total

All slices are sequential (no parallelization possible).

```md
**Engineer's validation:**
- [x] End-to-end testable → Each slice has working test ✅
- [x] Vertical not horizontal → Not "all DB then all API" ✅
- [x] Realistic estimates → Correlates with LOC estimates ✅
- [x] Clear dependencies → S1 → S2 → S3 ✅

**Time spent:** 30 minutes

---

## Phase 5: Plan (P)

### Agent's Output (Selected Sections)

```markdown
# Implementation Plan: Email Preferences - Slice 1

**Approved Structure:** ✓
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

**Functions:** None (types only)

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

**Testing:** Mock all calls, test request/response

**Estimated LOC:** 60-80

**Notes:**

- Use existing auth middleware
- Follow existing error pattern from codebase
- Validation: Use existing validateUserIdParam middleware

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

**Testing:** Component renders, toggles work, onChange fires

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

  it('EmailPreferences component renders and toggles work', () => {
    const prefs = DEFAULT_PREFERENCES;
    const { getByRole, getByText } = render(
      <EmailPreferences preferences={prefs} onUpdate={jest.fn()} />
    );
    
    expect(getByText(/promotion/i)).toBeInTheDocument();
    const toggle = getByRole('switch', { name: /promotion/i });
    fireEvent.click(toggle);
  });
});
```

**Estimated LOC:** 80-100

---

## Implementation Sequence

**Sequential (recommended for one person):**

1. Create emailPreferences.model.ts (40 min)
2. Add GET endpoint (20 min)
3. Add PUT endpoint (20 min)
4. Create EmailPreferences component (40 min)
5. Wire component to API calls (30 min)
6. Write integration tests (50 min)

Total: ~3.5 hours (higher than estimate, includes buffer)

**Parallel (if two developers):**

- Dev A: Steps 1-3 (types + endpoints)
- Dev B: Steps 4-5 (component)
- Both: Step 6 (tests)

---

## Code Quality Gates

Before submitting for review:

- [ ] TypeScript: `npm run type-check` passes
- [ ] Lint: `npm run lint` passes
- [ ] Tests: `npm run test` passes (100% coverage)
- [ ] No console.log() except logging service
- [ ] JSDoc on public exports
- [ ] Import paths use established patterns (not relative imports across packages)

---

## Notes

### Patterns to Follow

- Error handling: Use AppError class (existing pattern)
- Middleware: Use existing auth, validation middleware
- Component state: Use React hooks (not class components)
- API responses: Follow existing { data, error, success } format

### Pitfalls to Avoid

- Don't create new middleware (reuse existing auth)
- Don't hardcode email types (use enum from model)
- Don't forget to add TypeScript strict checking

```md
**Engineer's validation:**
- [x] Zero new architectural decisions → All reference design.md ✅
- [x] File breakdown specific → Types, functions, dependencies listed ✅
- [x] Testing strategy detailed → Unit, integration tests specified ✅
- [x] No TODOs → All specific ✅
- [x] Effort estimates reasonable → Correlates with LOC ✅

**Time spent:** 40 minutes

---

## Phase 6: Work Tree (W)

### Agent's Output: work_tree.md (Slice 1)

```markdown
# Work Tree: Email Preferences - Slice 1

**Slice:** 1 (Mock API + Frontend)
**Approved Plan:** ✓
**Total Tasks:** 8
**Critical Path:** ~3 hours

## Task Hierarchy

├── T1: Types Definition
│   ├── T1.1: Define EmailType enum
│   │   Effort: 15 min
│   │   Files: src/models/emailPreferences.model.ts
│   │   Definition of Done: Enum has all 4 email types
│   │   Depends: None
│   │
│   ├── T1.2: Define PreferenceFrequency enum
│   │   Effort: 10 min
│   │   Definition of Done: Enum compiles, used in UserEmailPreference
│   │   Depends: T1.1
│   │
│   └── T1.3: Define DEFAULT_PREFERENCES constant
│       Effort: 10 min
│       Definition of Done: Constant has all 4 email types with defaults
│       Depends: T1.1, T1.2
│
├── T2: API Endpoints
│   ├── T2.1: Implement GET endpoint
│   │   Effort: 25 min
│   │   Files: src/api/routes/users.ts
│   │   Acceptance: GET /api/v1/users/{id}/preferences/email returns 200
│   │   Depends: T1.1, T1.2, T1.3
│   │
│   └── T2.2: Implement PUT endpoint
│       Effort: 25 min
│       Acceptance: PUT request returns 200, response includes updated prefs
│       Depends: T2.1
│
├── T3: Frontend Component
│   ├── T3.1: Create EmailPreferences component skeleton
│   │   Effort: 20 min
│   │   Files: frontend/components/EmailPreferences.tsx
│   │   Acceptance: Component renders without error
│   │   Depends: T1.1 (types)
│   │
│   ├── T3.2: Add toggles for each email type
│   │   Effort: 20 min
│   │   Acceptance: All 4 toggles visible, labeled correctly
│   │   Depends: T3.1
│   │
│   └── T3.3: Add frequency selects (show when enabled)
│       Effort: 15 min
│       Acceptance: Select visible only when toggle is on
│       Depends: T3.2
│
├── T4: Integration
│   ├── T4.1: Wire component to API calls
│   │   Effort: 30 min
│   │   Files: frontend/pages/AccountSettings.tsx
│   │   Acceptance: Clicking toggle calls PUT /api/v1/users/{id}/preferences/email
│   │   Depends: T2.1, T2.2, T3.3
│   │
│   └── T4.2: Add error handling
│       Effort: 15 min
│       Acceptance: Error message shown if API call fails
│       Depends: T4.1
│
└── T5: Testing
    ├── T5.1: Write integration tests
    │   Effort: 40 min
    │   Files: tests/integration/emailPreferences.integration.test.ts
    │   Acceptance: 5+ tests pass, >90% coverage
    │   Depends: T2.1, T2.2, T3.1, T3.2, T3.3
    │
    └── T5.2: Verify quality gates
        Effort: 15 min
        Acceptance: TypeScript, lint, tests all pass
        Depends: T5.1

---

## Critical Path

T1.1 (15) → T1.2 (10) → T1.3 (10) → T2.1 (25) → T2.2 (25) → 
T3.1 (20) → T3.2 (20) → T3.3 (15) → T4.1 (30) → T5.1 (40) → T5.2 (15)

= 225 minutes = 3.75 hours

---

## Parallelization

Can run in parallel:
- T1.1/T1.2/T1.3 are independent (actually sequential for ergonomics)
- T2.1/T2.2 sequential (GET before PUT)
- T3.1/T3.2/T3.3 sequential (building component)
- T4.1 depends on T2+T3 (can start as soon as endpoints defined)

If two developers:
- Dev A: T1 + T2 (types + endpoints)
- Dev B: T3 + T4 (component + integration)
- Both: T5 (tests)

Best case with 2 devs: 2 hours (parallel streams)
Single dev: 3.75 hours (sequential)
```

**Time spent:** 30 minutes

---

## Phase 7: Implement (I)

Agent writes code for all 8 tasks.

### Example Commits

```txt
Commit: a3f2b1c - feat(T1.1): Define EmailType enum
Files: src/models/emailPreferences.model.ts (+50 lines)
Time: 15 min (matches estimate)

Test Results:
  ✅ TypeScript compilation: 0 errors
  ✅ Lint: 0 errors
  ✅ No runtime tests yet (types only)

Commit: b4e3c2d - feat(T2.1): Implement GET preferences endpoint
Files: src/api/routes/users.ts (+65 lines)
       tests/integration/emailPreferences.integration.test.ts (+30 lines)
Time: 25 min (matches estimate)

Test Results:
  ✅ TypeScript: 0 errors
  ✅ Lint: 0 errors
  ✅ Integration test: 1 test, 1 pass
  ✅ Coverage: 100% (just endpoint)

Commit: c5f4d3e - feat(T2.2): Implement PUT preferences endpoint
Files: src/api/routes/users.ts (+65 lines)
       tests/integration/emailPreferences.integration.test.ts (+30 lines)
Time: 22 min (within estimate)

Test Results:
  ✅ All gates pass
  ✅ Integration tests: 2 tests, 2 pass
  ✅ Coverage: 100%

[... continue for T3, T4, T5 ...]

Total actual time: 3.5 hours (estimate was 3.75 hours)
Estimate accuracy: 93% (well within 10% target)
```

**Time spent:** Implementation varies (for Slice 1: ~3.5 hours)

---

## Phase 8: Pull Request (PR)

### PR Title

```txt
feat: Add user control over email preferences
```

### PR Description

```markdown
# Pull Request: User Email Preferences

**Branch:** `feature/email-preferences-slice-1`
**Base:** `main`
**Related:** #2341 (feature ticket)
**Design:** [link to design.md]
**Plan:** [link to plan.md]

---

## What Changed

Slice 1: Users can now see and toggle email preference settings.

**Files:**
- `src/models/emailPreferences.model.ts` (NEW) — Type definitions
- `src/api/routes/users.ts` (MODIFIED) — Added GET/PUT endpoints
- `frontend/components/EmailPreferences.tsx` (NEW) — Preference UI
- `frontend/pages/AccountSettings.tsx` (MODIFIED) — Integrated component
- `tests/integration/emailPreferences.integration.test.ts` (NEW) — Tests

**Lines:** +350 added, -0 deleted

---

## Code Quality

```txt
✅ TypeScript: 0 errors, 0 warnings
✅ ESLint: 0 errors, 0 warnings
✅ Tests: 5 tests, 5 pass
✅ Coverage: 98% (only skipping error paths)
```

---

## What This Does

- GET `/api/v1/users/{id}/preferences/email` returns user's preferences
- PUT `/api/v1/users/{id}/preferences/email` updates preferences (not persisted yet)
- Frontend: EmailPreferences component with toggles + frequency selects
- Integrated into AccountSettings page

---

## What This Does NOT Do

This is Slice 1 (mock API + frontend).

**Not included (Slice 2-3):**

- Preferences not yet persisted to database
- Email sending doesn't check preferences yet
- Only in-memory responses

---

## Design Alignment

- ✅ Follows approved design.md
- ✅ Uses separate preferences model (not JSON column—per feedback)
- ✅ API follows existing conventions (/api/v1/users/{id}/...)
- ✅ Component uses existing Toggle component
- ✅ Error handling follows existing pattern

---

## Architecture

No new architectural decisions introduced.
All implementation details reference:

- Type definitions (emailPreferences.model.ts) ← Approved in Design
- API pattern (/api/v1/users/...) ← Discovered in Research
- Component structure ← Existing pattern from AccountSettings

---

## Risk Assessment

**Low risk.**

This is mocked data, not production features.

Next slices (database + email sending) will have more risk.

---

## Testing

```txt
npm test -- emailPreferences
✅ 5 tests pass
✅ No skipped tests
✅ Coverage: src/api/routes/users.ts (100%)
✅ Coverage: frontend/components/EmailPreferences.tsx (98%)
```

---

## Deployment

Can merge and deploy immediately.

- No database changes
- No feature flags needed
- No configuration needed
- Frontend-only at this stage

---

## Next Steps

1. Code review + merge this PR
2. Deploy to production
3. Start Slice 2: Real database persistence
4. Start Slice 3: Email sending respects preferences

---

## Reviewer Checklist

- [x] Code follows existing patterns
- [x] No new architectural decisions
- [x] All tests pass
- [x] TypeScript strict
- [x] Error handling appropriate
- [x] Type safety maintained
- [x] Design alignment verified
- [x] Commit messages clear
- [x] Documentation complete (JSDoc)
- [x] No surprises (all aligns with prior artifacts)

```md

### Reviewer (Engineer)

Reads PR.
- Checks: Does everything align with design.md and plan.md? ✅
- Checks: Are there surprises? (No—everything was approved beforehand) ✅
- Checks: Do tests pass? (Yes) ✅
- Checks: Does code follow patterns? (Yes) ✅

**Approval:** "Looks good. Merging."

**Time spent:** 15 minutes (quick review, no surprises)

---

## Summary: Total QRSPI Time

```txt
Phase 1 (Questions):  20 min
Phase 2 (Research):   45 min
Phase 3 (Design):     40 min (30 agent + 10 feedback)
Phase 4 (Structure):  30 min
Phase 5 (Plan):       40 min
Phase 6 (Work Tree):  30 min
Phase 7 (Implement):  3.5 hours (Slice 1 only)
Phase 8 (PR):         15 min

Total: 5.5 hours for Slice 1 (mock API)

Estimate was 6 hours (2.5 align + 2.5 implement + 1 review)
Actual was 5.5 hours
Accuracy: 92% ✅

---

Slices 2-3 would follow same pattern:
Slice 2: +3 hours implementation (database)
Slice 3: +2.5 hours implementation (email logic)

Total feature: ~9-10 hours end-to-end
All code integrated perfectly (0 rework needed)
```

---

## Key Takeaways from This Example

1. **Alignment phases aren't wasted time** — They catch design issues early (JSON column mistake was caught in Design, not code review)

2. **Estimates become accurate** — After alignment, estimates are within 10% (3.5h actual vs. 3.75h estimated)

3. **Code review is boring** — No surprises, quick approval (15 min review)

4. **Artifacts compound** — Each artifact feeds the next. By Phase 7, implementation is mechanical (follow the plan)

5. **Brain surgery is essential** — One piece of feedback (use separate table, not JSON) saved rework later

6. **Vertical slices are testable** — Slice 1 ships with no database, but is fully testable and deployable

This is what QRSPI looks like in practice. Not theoretical—actual time investments and artifacts.
