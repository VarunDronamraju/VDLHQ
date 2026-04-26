# API.md — LocationHQ

All endpoints use JSON. Auth is JWT-based with two roles: `client` and `ops`. Role is encoded in the JWT payload and enforced by middleware on every request.

---

## Authentication

```
Authorization: Bearer <jwt_token>
```

- `client` role: all queries filter by `client_id = current_user.client_id` — clients cannot see other clients' data
- `ops` role: unrestricted read and write access across all pipeline data
- All endpoints require a valid JWT except health check

---

## Response Envelope

Successful responses return the resource directly. Error responses follow:

```json
{
  "error": "short_error_code",
  "detail": "Human-readable description of the error",
  "request_id": "uuid"
}
```

Common status codes:
- `202` — request accepted, async processing initiated
- `400` — validation failure
- `401` — missing or invalid token
- `403` — authenticated but not authorized for this resource
- `404` — resource not found
- `422` — request body structurally valid but semantically invalid
- `500` — unhandled server error (logged to `system_errors`)

---

## Client-Facing Endpoints

---

### `POST /inquiry`

**Purpose:** Full inquiry form submission. Creates a lead record and triggers the intake pipeline asynchronously.

**Auth:** `client`

**Request:**
```json
{
  "contact": {
    "name": "Arjun Mehta",
    "email": "arjun@blueframe.in",
    "phone": "+91-9876543210",
    "company": "Blue Frame Productions"
  },
  "shoot_type": "commercial",
  "dates": {
    "start": "2025-03-10",
    "end": "2025-03-12"
  },
  "budget": {
    "min": 50000,
    "max": 80000,
    "currency": "INR"
  },
  "location_type": "industrial warehouse",
  "crew_size": 25,
  "requirements": "Need loading dock access, 3-phase power, no residential neighbors"
}
```

**Required fields:** `contact.name`, `contact.email` or `contact.phone`, `shoot_type`

**Response: `202 Accepted`**
```json
{
  "lead_id": "uuid",
  "status": "new",
  "message": "Inquiry received. We'll follow up shortly."
}
```

**Behavior:**
1. Validates required fields — returns 422 if missing
2. C3 matches or creates client profile
3. Creates `leads` record with `status: new`
4. Returns 202
5. Enqueues `run_intake_pipeline(lead_id)` as BackgroundTask

---

### `POST /inquiry/partial`

**Purpose:** Saves an incomplete inquiry. Used when a client submits without filling all fields. Saves whatever is provided and marks the lead `needs_info`.

**Auth:** `client`

**Request:** Same shape as `POST /inquiry` — all fields optional except at least one contact field.

**Response: `202 Accepted`**
```json
{
  "lead_id": "uuid",
  "status": "needs_info",
  "missing_fields": ["shoot_dates", "budget_range"],
  "message": "Partial inquiry saved. We'll reach out to collect remaining details."
}
```

**Behavior:**
1. Saves whatever fields are present
2. Creates lead with `status: needs_info`
3. Stores `missing_fields` on the lead
4. Enqueues C4 follow-up (via scheduler — not immediate)
5. Does NOT trigger A1/A2 pipeline until missing fields are provided

---

### `GET /client/dashboard`

**Purpose:** Client's view of all their leads and bookings — status, last update, next expected action.

**Auth:** `client`

**Response: `200 OK`**
```json
{
  "client": {
    "id": "uuid",
    "name": "Arjun Mehta",
    "email": "arjun@blueframe.in"
  },
  "leads": [
    {
      "lead_id": "uuid",
      "status": "matched",
      "submitted_at": "2025-02-10T09:30:00Z",
      "last_updated": "2025-02-11T14:22:00Z",
      "next_action": "Review shortlisted locations and confirm or reject"
    }
  ],
  "bookings": [
    {
      "booking_id": "uuid",
      "location_name": "Worli Industrial Complex",
      "shoot_date": "2025-03-10",
      "status": "permit_pending",
      "permit_status": "pending"
    }
  ]
}
```

---

### `GET /client/leads/:id`

**Purpose:** Detailed view of a single lead. Includes current status, matched locations (if any), and booking/permit status if applicable.

**Auth:** `client` (enforced: `lead.client_id == current_user.client_id`)

**Response: `200 OK`**
```json
{
  "lead_id": "uuid",
  "status": "matched",
  "readiness_score": 0.92,
  "missing_fields": [],
  "matched_locations": [
    {
      "location_id": "uuid",
      "name": "Worli Industrial Complex",
      "type": "industrial",
      "reasoning": "Matches power and loading dock requirements. 8000 sqft within budget."
    }
  ],
  "booking": null,
  "permit": null,
  "submitted_at": "2025-02-10T09:30:00Z",
  "last_updated": "2025-02-11T14:22:00Z"
}
```

---

### `POST /client/leads/:id`

**Purpose:** Client updates inquiry fields (e.g. provides missing details after a follow-up). Re-triggers the readiness assessment.

**Auth:** `client` (enforced: `lead.client_id == current_user.client_id`)

**Request:**
```json
{
  "dates": {
    "start": "2025-03-10",
    "end": "2025-03-12"
  },
  "budget": {
    "min": 40000,
    "max": 70000,
    "currency": "INR"
  }
}
```

**Response: `202 Accepted`**
```json
{
  "lead_id": "uuid",
  "status": "needs_info",
  "message": "Details updated. Re-assessing your inquiry."
}
```

**Behavior:**
1. Merges updated fields into `leads.intake_data`
2. Re-enqueues `run_intake_pipeline(lead_id)` — A1 → A2 → C2 → C1

---

## Ops-Facing Endpoints

---

### `GET /ops/pipeline`

**Purpose:** Full pipeline view — all leads grouped or filterable by status. Primary ops working view.

**Auth:** `ops`

**Query params:**
- `status` — filter by one or more statuses (comma-separated)
- `page` — default 1
- `page_size` — default 50, max 200

**Response: `200 OK`**
```json
{
  "leads": [
    {
      "lead_id": "uuid",
      "client_name": "Arjun Mehta",
      "status": "matched",
      "readiness_score": 0.92,
      "submitted_at": "2025-02-10T09:30:00Z",
      "last_updated": "2025-02-11T14:22:00Z",
      "hours_in_state": 28
    }
  ],
  "counts_by_status": {
    "new": 2,
    "needs_info": 5,
    "ready": 1,
    "matched": 3,
    "booked": 2,
    "permit_pending": 1
  },
  "total": 14,
  "page": 1,
  "page_size": 50
}
```

---

### `GET /ops/leads/:id`

**Purpose:** Full lead detail including audit trail, all communications, client profile, and current booking/permit state.

**Auth:** `ops`

**Response: `200 OK`**
```json
{
  "lead": {
    "lead_id": "uuid",
    "status": "matched",
    "readiness_score": 0.92,
    "missing_fields": [],
    "clarification_count": 1,
    "intake_data": { ... }
  },
  "client": {
    "id": "uuid",
    "name": "Arjun Mehta",
    "email": "arjun@blueframe.in",
    "phone": "+91-9876543210",
    "profile_data": { ... }
  },
  "audit_trail": [
    {
      "previous_state": "new",
      "new_state": "ready",
      "trigger": "intake_pipeline",
      "actor": "workflow_engine",
      "created_at": "2025-02-10T09:35:12Z"
    }
  ],
  "communications": [
    {
      "template_name": "shortlist_sent",
      "channel": "email",
      "status": "sent",
      "sent_at": "2025-02-11T14:22:00Z"
    }
  ],
  "booking": null,
  "permit": null
}
```

---

### `POST /ops/leads/:id/action`

**Purpose:** Manual state override or reassignment by the ops team. Used after resolving `manual_review` leads or handling edge cases.

**Auth:** `ops`

**Request:**
```json
{
  "action": "transition",
  "target_state": "ready",
  "notes": "Client clarified requirements over call. Ready to proceed."
}
```

**Actions:**
- `transition` — forces a state change; `target_state` required
- `reassign` — updates the ops owner on the lead; `assignee_id` required

**Response: `200 OK`**
```json
{
  "lead_id": "uuid",
  "previous_state": "manual_review",
  "new_state": "ready",
  "workflow_state_id": "uuid",
  "notes": "Client clarified requirements over call. Ready to proceed."
}
```

**Behavior:**
- Calls `C1.transition(lead_id, target_state, context)` with `actor: user:{ops_user_id}`
- Validates against allowed transitions — returns 422 if not valid
- If transitioning `manual_review → ready`: `clarification_count` is reset to 0

---

### `GET /ops/bookings`

**Purpose:** Full booking pipeline view. Includes location, client, and permit status per booking.

**Auth:** `ops`

**Query params:**
- `status` — filter by booking status
- `permit_status` — filter by permit status

**Response: `200 OK`**
```json
{
  "bookings": [
    {
      "booking_id": "uuid",
      "lead_id": "uuid",
      "client_name": "Arjun Mehta",
      "location_name": "Worli Industrial Complex",
      "shoot_date": "2025-03-10",
      "booking_status": "permit_pending",
      "permit": {
        "permit_id": "uuid",
        "permit_type": "municipal",
        "status": "submitted",
        "expected_approval_days": 7
      },
      "created_at": "2025-02-12T10:00:00Z"
    }
  ],
  "total": 3
}
```

---

### `POST /ops/bookings/:id/permit`

**Purpose:** Ops team updates permit status after submitting to or hearing back from the relevant authority.

**Auth:** `ops`

**Request:**
```json
{
  "status": "submitted",
  "notes": "Filed with BMC on Feb 14. Expected turnaround: 7 days."
}
```

**Valid transitions:** `pending → submitted`, `submitted → in_review`, `in_review → approved`, `in_review → rejected`, `rejected → pending`

**Response: `200 OK`**
```json
{
  "booking_id": "uuid",
  "permit_id": "uuid",
  "previous_status": "pending",
  "new_status": "submitted",
  "notes": "Filed with BMC on Feb 14."
}
```

**Behavior:**
- Calls A4 to update permit status
- If `approved`: A4 returns result to C1 → C1 transitions lead to `coordination`, A5 notifies client
- If `rejected`: A4 returns result → C1 notifies ops and client via A5, lead stays in `permit_rejected`

---

### `GET /ops/analytics`

**Purpose:** Aggregated metrics for ops dashboard. Powered by C5.

**Auth:** `ops`

**Query params:**
- `from_date` — ISO date, default 30 days ago
- `to_date` — ISO date, default today

**Response: `200 OK`**
```json
{
  "period": {
    "from": "2025-01-15",
    "to": "2025-02-15"
  },
  "volume_by_status": {
    "new": 12,
    "needs_info": 8,
    "ready": 5,
    "matched": 9,
    "booked": 6,
    "closed": 4,
    "inactive": 3,
    "archived": 1
  },
  "conversion_rate": 0.42,
  "avg_time_to_booking_days": 4.2,
  "drop_off_by_stage": {
    "needs_info": 3,
    "matched": 2
  },
  "active_leads": 18,
  "bookings_this_period": 6
}
```

---

## Internal Endpoints

---

### `POST /internal/retry/:lead_id`

**Purpose:** Manually re-triggers the intake pipeline for a lead that failed during async processing. Used when a lead is stuck in `new` or `needs_info` due to a pipeline failure.

**Auth:** `ops`

**Response: `202 Accepted`**
```json
{
  "lead_id": "uuid",
  "current_status": "new",
  "message": "Intake pipeline re-triggered."
}
```

**Behavior:**
- Validates lead exists and is in a retrigger-eligible state (`new`, `needs_info`, `ready`)
- Enqueues `run_intake_pipeline(lead_id)` as BackgroundTask
- Returns 422 if lead is in a non-retrigger state (e.g. `booked`, `closed`)

---

## Notes

- All list endpoints are cursor-paginated when result sets may be large
- `lead_id`, `booking_id`, `client_id` are UUIDs in all requests and responses
- Timestamps are ISO 8601 in UTC
- The ops dashboard reads `system_errors` directly via DB query — no dedicated endpoint required at this scale