# SCHEMA.md — LocationHQ

All tables use PostgreSQL. UUIDs for primary keys. Timestamps are `TIMESTAMPTZ` stored in UTC. `updated_at` is managed by a trigger or application layer on every write.

---

## Enums

Defined as PostgreSQL native enum types.

```sql
CREATE TYPE lead_status AS ENUM (
    'new',
    'needs_info',
    'ready',
    'matching_in_progress',
    'needs_clarification',
    'matched',
    'manual_review',
    'booked',
    'permit_pending',
    'permit_submitted',
    'permit_in_review',
    'permit_approved',
    'permit_rejected',
    'coordination',
    'closed',
    'inactive',
    'archived'
);

CREATE TYPE booking_status AS ENUM (
    'confirmed',
    'permit_pending',
    'coordination',
    'completed',
    'cancelled'
);

CREATE TYPE permit_status AS ENUM (
    'pending',
    'submitted',
    'in_review',
    'approved',
    'rejected'
);

CREATE TYPE communication_status AS ENUM (
    'pending',
    'sent',
    'failed'
);

CREATE TYPE communication_channel AS ENUM (
    'email',
    'whatsapp'
);
```

---

## Tables

---

### `clients`

Stores client profiles. Created on first inquiry. Matched by email or phone on re-inquiry to pre-fill known data.

```sql
CREATE TABLE clients (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255)    NOT NULL,
    email           VARCHAR(255)    NOT NULL UNIQUE,
    phone           VARCHAR(50),
    profile_data    JSONB           NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT now()
);

CREATE INDEX idx_clients_email ON clients (email);
CREATE INDEX idx_clients_phone ON clients (phone);
```

**`profile_data` shape (example):**
```json
{
  "company": "Blue Frame Productions",
  "shoot_types": ["commercial", "editorial"],
  "preferred_locations": ["industrial", "outdoor"],
  "notes": "Returns frequently, prefers email"
}
```

**Relationships:**
- Referenced by `leads.client_id`
- Referenced by `bookings.client_id`

---

### `leads`

Core table. Tracks every inquiry from submission to close. `status` is the authoritative workflow state — only written by C1.

```sql
CREATE TABLE leads (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id           UUID            NOT NULL REFERENCES clients(id),
    status              lead_status     NOT NULL DEFAULT 'new',
    readiness_score     NUMERIC(4,3),   -- 0.000 to 1.000; NULL until A2 runs
    missing_fields      JSONB           NOT NULL DEFAULT '[]',
    clarification_count INTEGER         NOT NULL DEFAULT 0,
    intake_data         JSONB           NOT NULL DEFAULT '{}',
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT now()
);

CREATE INDEX idx_leads_client_id  ON leads (client_id);
CREATE INDEX idx_leads_status     ON leads (status);
CREATE INDEX idx_leads_updated_at ON leads (updated_at);
```

**`intake_data` shape (example):**
```json
{
  "shoot_type": "commercial",
  "dates": { "start": "2025-03-10", "end": "2025-03-12" },
  "budget": { "min": 50000, "max": 80000, "currency": "INR" },
  "location_type": "industrial warehouse",
  "crew_size": 25,
  "requirements": "Need loading dock access, 3-phase power",
  "raw_submission": "..."
}
```

**`missing_fields` shape (example):**
```json
["shoot_dates", "budget_range", "crew_size"]
```

**Constraints:**
- `clarification_count` must not exceed 1 before C1 forces `manual_review` (enforced in application logic, not DB constraint)
- `status` is constrained to the `lead_status` enum — invalid states rejected at DB level

**Relationships:**
- `client_id` → `clients.id`
- Referenced by `workflow_state.lead_id`
- Referenced by `bookings.lead_id`
- Referenced by `communications_log.lead_id`

---

### `workflow_state`

Append-only audit log. One row per state transition. Never updated or deleted. The complete history of every lead's journey through the system.

```sql
CREATE TABLE workflow_state (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id         UUID        NOT NULL REFERENCES leads(id),
    previous_state  VARCHAR(50) NOT NULL,
    new_state       VARCHAR(50) NOT NULL,
    trigger         VARCHAR(100) NOT NULL,  -- e.g. 'intake_pipeline', 'ops_manual', 'inactivity_scanner'
    actor           VARCHAR(100) NOT NULL,  -- service name or user_id
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_workflow_state_lead_id    ON workflow_state (lead_id);
CREATE INDEX idx_workflow_state_created_at ON workflow_state (created_at);
```

**`trigger` values (examples):**
- `intake_pipeline` — automated intake flow
- `ops_manual` — ops team action
- `inactivity_scanner` — scheduled job
- `client_update` — client updated inquiry fields
- `clarification_response` — client responded to clarification request
- `permit_approval` — permit approved by authority

**`actor` values (examples):**
- `workflow_engine` — C1 automated action
- `inactivity_scanner` — scheduled job
- `user:{uuid}` — specific ops user who triggered the action

**Constraints:**
- No UPDATE, no DELETE — enforced by application convention and can be locked down with a DB trigger in a second pass
- Any `lead.status` change without a corresponding row here indicates a C1 bypass

---

### `bookings`

Created when a client confirms a location. Tracks the booking from confirmation through coordination.

```sql
CREATE TABLE bookings (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id         UUID            NOT NULL REFERENCES leads(id),
    client_id       UUID            NOT NULL REFERENCES clients(id),
    location_id     UUID            NOT NULL REFERENCES locations(id),
    status          booking_status  NOT NULL DEFAULT 'confirmed',
    shoot_date      DATE,
    shoot_end_date  DATE,
    budget          NUMERIC(12,2),
    notes           TEXT,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT now()
);

CREATE INDEX idx_bookings_lead_id     ON bookings (lead_id);
CREATE INDEX idx_bookings_client_id   ON bookings (client_id);
CREATE INDEX idx_bookings_location_id ON bookings (location_id);
CREATE INDEX idx_bookings_status      ON bookings (status);
```

**Relationships:**
- `lead_id` → `leads.id`
- `client_id` → `clients.id`
- `location_id` → `locations.id`
- Referenced by `permits.booking_id`
- Referenced by `communications_log.booking_id`

---

### `permits`

One permit record per booking. Tracks the permit lifecycle from generation through approval or rejection.

```sql
CREATE TABLE permits (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    booking_id      UUID            NOT NULL REFERENCES bookings(id),
    permit_type     VARCHAR(100)    NOT NULL,  -- e.g. 'municipal', 'police_noc', 'fire_noc'
    status          permit_status   NOT NULL DEFAULT 'pending',
    checklist       JSONB           NOT NULL DEFAULT '{}',
    rejection_notes TEXT,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT now()
);

CREATE INDEX idx_permits_booking_id ON permits (booking_id);
CREATE INDEX idx_permits_status     ON permits (status);
```

**`checklist` shape (example):**
```json
{
  "items": [
    { "task": "Submit application to municipal office", "completed": false },
    { "task": "Attach shoot schedule", "completed": true },
    { "task": "Attach NOC from location owner", "completed": true },
    { "task": "Pay permit fee", "completed": false }
  ],
  "authority": "BMC",
  "expected_approval_days": 7
}
```

**Relationships:**
- `booking_id` → `bookings.id`
- One booking may have multiple permits (different authorities)

---

### `locations`

Location inventory. Each record has a vector embedding used by A3 for semantic similarity search.

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE locations (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(255) NOT NULL,
    type        VARCHAR(100) NOT NULL,   -- e.g. 'industrial', 'outdoor', 'residential'
    address     TEXT        NOT NULL,
    available   BOOLEAN     NOT NULL DEFAULT true,
    embedding   vector(1536),            -- NULL until first embedding run
    metadata    JSONB       NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_locations_available ON locations (available);
CREATE INDEX idx_locations_type      ON locations (type);

-- pgvector index for cosine similarity search
CREATE INDEX idx_locations_embedding ON locations
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 50);
```

**`metadata` shape (example):**
```json
{
  "area_sqft": 8000,
  "power": "3-phase",
  "parking": true,
  "daily_rate": 45000,
  "owner_id": "...",
  "amenities": ["loading dock", "freight elevator", "AC"],
  "restrictions": ["no wet scenes", "shoot hours 8am-10pm"]
}
```

**pgvector usage:**
- Model: `text-embedding-3-small` (1536 dimensions) — same model used at ingestion and at query time
- Index type: `ivfflat` with `lists = 50` — sufficient for an inventory of hundreds of locations
- Re-embedding: triggered by A3 when a location record is updated; full recompute and store

---

### `communications_log`

Append-only record of every outbound message sent or attempted by A5. Never updated — failed sends create a new row with `status: failed`.

```sql
CREATE TABLE communications_log (
    id              UUID                    PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id         UUID                    REFERENCES leads(id),
    booking_id      UUID                    REFERENCES bookings(id),
    template_name   VARCHAR(100)            NOT NULL,
    channel         communication_channel   NOT NULL,
    status          communication_status    NOT NULL DEFAULT 'pending',
    sent_at         TIMESTAMPTZ,
    error_detail    TEXT,
    created_at      TIMESTAMPTZ             NOT NULL DEFAULT now()
);

CREATE INDEX idx_comms_lead_id   ON communications_log (lead_id);
CREATE INDEX idx_comms_booking_id ON communications_log (booking_id);
CREATE INDEX idx_comms_status    ON communications_log (status);
```

**Constraints:**
- At least one of `lead_id` or `booking_id` must be non-null (enforced by application)
- `sent_at` is NULL until A5 confirms the send succeeded
- Failed sends are surfaced on the ops dashboard via query on `status = 'failed'`

---

### `system_errors`

Operational error log for background task and scheduler failures. Used to surface system-level issues on the ops dashboard.

```sql
CREATE TABLE system_errors (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    source      VARCHAR(100) NOT NULL,  -- e.g. 'intake_pipeline', 'inactivity_scanner'
    lead_id     UUID        REFERENCES leads(id),
    error_type  VARCHAR(100) NOT NULL,
    message     TEXT        NOT NULL,
    detail      JSONB       NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_system_errors_source     ON system_errors (source);
CREATE INDEX idx_system_errors_lead_id    ON system_errors (lead_id);
CREATE INDEX idx_system_errors_created_at ON system_errors (created_at);
```

---

## Relationship Summary

```
clients
  └─→ leads (one client, many leads)
       └─→ workflow_state (one lead, many state rows — append-only)
       └─→ bookings (one lead, one booking)
            └─→ permits (one booking, one or more permits)
       └─→ communications_log (lead_id reference)

bookings
  └─→ communications_log (booking_id reference)
  └─→ locations (many bookings reference one location)

locations
  └─→ embedding (vector for similarity search)
```

---

## Migration Notes

- All schema changes go through Alembic migration files in `/db/migrations/`
- Never apply schema changes directly to production
- Adding a NOT NULL column requires a default or a multi-step migration (add nullable → backfill → add constraint)
- The `lead_status` enum can be extended with `ALTER TYPE lead_status ADD VALUE` — no migration rebuild needed for additions