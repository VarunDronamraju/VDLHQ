# ✦ LocationHQ — Production operations platform for film, advertising, and media shoot coordination

Welcome to the definitive operational manual and architectural handbook for **LocationHQ**. 

LocationHQ is a production-grade, workflow-driven operations platform designed to coordinate film, advertising, and media shoots. It integrates a structured client intake pipeline, automated background communication, vector-similarity location matching, and a robust state machine to manage the full lifecycle of lead processing: **Inquiry Intake → Lead Qualification → Location Matching → Booking → Permits → Shoot Coordination → Close**.

---

## 🏗️ 1. Complete System Architecture & Modular Layout

The system is constructed as a **modular monolith** — a single deployable backend unit utilizing a single PostgreSQL database with pgvector, keeping all state centrally persisted to enforce total reliability.

```
/locationhq
  /app
    /api
      /routes/          ← Intake, leads, bookings, client, and ops REST endpoints
      /middlewares/     ← Request loggers, auth protections
      /schemas/         ← Pydantic schemas (LeadBrief, BookingBrief, etc.)
    /services
      /core/            ← C1, C2, C3, C4, C5 (Deterministic, no LLM allowed)
      /ai/              ← A1, A2, A3, A4, A5, A6 (LLM-assisted services)
    /models/            ← Lead, booking, client, location, permit, and workflow_state SQLAlchemy models
    /scheduler/         ← APScheduler job engines (Inactivity scanner, reminders)
    /db/                ← SQLAlchemy async engines, connection pool, migrations
    /core/              ← exceptions, error loggers, and shared libraries
    main.py             ← API gateway app factory, CORS, and scheduler startup
  /frontend             ← React + Vite client-facing interface (Pure minimalist teal/white styling)
  /tests                ← Fully-hardened test suite (pytest-asyncio, 90%+ target coverage)
```

---

## 📊 2. High-Fidelity Architectural & Flow Diagrams

These diagrams map the complete operational lifecycle, service dependency trees, database relationships, and the central lead state machine.

### Diagram A: High-Level System Flow
Shows the ingestion boundaries (Inquiry vs Partial) and how the intake pipeline flows to the PostgreSQL DB and out to communications and dashboards.

```mermaid
---
config:
  layout: elk
---
flowchart TB
 subgraph Input["Input Boundary"]
        F1["Full Inquiry Form"]
        F11["Partial Submission"]
  end
 subgraph Core["Core System Monolith"]
        A1["IntakeService (A1)"]
        A2["ReadinessService (A2)"]
        C1["WorkflowEngine (C1)"]
        C2["RoutingService (C2)"]
        A3["MatchingService (A3)"]
        A4["PermitService (A4)"]
        C4["FollowUpService (C4)"]
        A6["NurturingService (A6)"]
        A5["CommunicationService (A5)"]
        C3["ProfileService (C3)"]
        API["API Gateway (FastAPI)"]
  end
 subgraph Output["Output & Dashboards"]
        ClientDash["Client Dashboard"]
        InternalDash["Internal Dashboard"]
        Messages["Email / SMTP Notifications"]
  end
    Client(["Client"]) --> API
    API --> F1 & F11
    
    %% Full inquiry triggers intake pipeline (A1 → A2 → C2 → C1.transition)
    F1 --> A1

    %% Partial inquiry creates a lead in needs_info directly
    F11 --> C3

    %% Intake pipeline: services return results; ONLY C1 writes leads.status
    A1 --> A2
    A2 --> C2
    C2 --> C1

    %% Profile lookup/creation is synchronous during inquiry/partial submission
    C3 --> DB[("PostgreSQL Database")]

    %% Workflow orchestration + persistence
    C1 --> DB & A3 & C4 & A4 & A5
    C2 --> C1
    A3 --> C1
    A4 --> C1
    C4 --> A5
    A6 --> A5
    A5 --> Messages
    DB --> ClientDash & InternalDash
    Messages --> Client

    style Client fill:#0D7C66,stroke:#41C9B4,color:#fff
    style DB fill:#1e293b,stroke:#cbd5e1,color:#fff
```

### Diagram B: Operational Workflow Pipeline (W1–W9)
An end-to-end flowchart from structural intake through matching, booking, permits, issue tracking, and automated failure/inactivity nurturing.

```mermaid
---
config:
  layout: elk
---
flowchart TB

    %% ========== INPUT ==========
    subgraph Input["Input Boundary"]
        START["Inquiry Received"]
    end

    %% ========== CORE SYSTEM ==========
    subgraph Core["LocationHQ Core System"]

        API["API Gateway"]

        %% Workflow Sections
        subgraph W1["W1: Inquiry Intake"]
            IA["Profile Check (C3)"]
            IB["Intake Processing (A1)"]
            IC["Readiness Evaluation (A2)"]
        end

        subgraph W2["W2: Routing"]
            RD{"Lead Ready?"}
            RE["Route → Matching"]
            RF["Route → Follow-up"]
        end

        subgraph W3["W3: Location Matching"]
            MA["Matching Engine (A3)"]
            MB{"Match Found?"}
            MC["Shortlist Stored"]
            MD["Clarification Sent"]
            ME{"Client Confirms?"}
        end

        subgraph W4["W4: Booking & Permits"]
            BA["Client Selects Location"]
            BB["State: booked"]
            BC["Permit Engine (A4)"]
            BD["permit_pending"]
            BE["permit_submitted"]
            BF{"permit_in_review"}
            BG["permit_approved"]
            BZ["permit_rejected"]
            BH["coordination"]
        end

        subgraph W8["W8: Issue Resolution"]
            IA2["Issue Logged"]
            IB2["Assigned to Ops"]
            IC2["Tracked in DB"]
            ID2["Client Acknowledged"]
        end

        subgraph W9["W9: Nurturing & Follow-up"]
            FU["FollowUp (C4)"]
            FUA["Targeted Message"]
            FUB{"Client responds?"}
            NU["Nurturing (A6)"]
            NUA["Re-engagement"]
            NUB{"Client responds?"}
        end

    end

    %% ========== OUTPUT ==========
    subgraph Output["Output Endpoints"]
        CLOSED["Closed (Shoot Done)"]
        ARC["Archived"]
        Messages["Email Outreach"]
        Dashboard["Ops Console"]
    end

    %% ========== FLOW ==========
    START --> API
    API --> IA

    IA --> IB --> IC --> RD
    RD -- Yes --> RE --> MA
    RD -- No --> RF --> FU

    MA --> MB
    MB -- Yes --> MC --> ME
    MB -- No --> MD --> MA

    ME -- No --> MA
    ME -- Yes --> BA --> BB

    BB --> BC --> BD --> BE --> BF
    BF -- Approved --> BG --> BH
    BF -- Rejected --> BZ --> BD

    BH --> CLOSED

    %% Outbound Alerts
    BB & BG & BH --> Messages

    %% Issues
    Messages --> IA2 --> IB2 --> IC2 --> ID2

    %% Nurturing loop
    FU --> FUA --> FUB
    FUB -- Yes --> IB
    FUB -- No --> NU --> NUA --> NUB
    NUB -- Yes --> IB
    NUB -- No --> ARC

    style START fill:#0D7C66,stroke:#41C9B4,color:#fff
    style CLOSED fill:#0f172a,stroke:#d1e7e4,color:#fff
    style ARC fill:#475569,stroke:#94a3b8,color:#fff
```

### Diagram C: Sequence Diagram (Time-ordered Transactions)
A transactional roadmap showing the exact synchronous responses and asynchronous task processing pipelines.

```mermaid
sequenceDiagram
    participant Client as Client Browser
    participant API as API Gateway (FastAPI)
    participant A1 as A1 IntakeService
    participant C3 as C3 ProfileService
    participant A2 as A2 ReadinessService
    participant C2 as C2 RoutingService
    participant C1 as C1 WorkflowEngine
    participant A3 as A3 MatchingService
    participant A4 as A4 PermitService
    participant C4 as C4 FollowUpService
    participant A5 as A5 CommunicationService
    participant DB as PostgreSQL DB

    Client->>API: Submit inquiry form
    API->>C3: Lookup or pre-fill client profile (Sync)
    C3->>DB: Read/write client profile records
    API->>DB: Create lead (status: new) & save raw data (Sync)
    API-->>Client: 202 Accepted (Sync Response: pipeline enqueued)
    Note over API,C1: BackgroundTask triggers asynchronously
    API->>A1: run_intake_pipeline(lead_id) starts
    
    A1->>A2: Parse and pass structured JSON
    A2->>A2: Evaluate field completeness
    alt Lead is fully ready
        A2-->>C2: ReadinessResult(status=ready, score)
        C2-->>C1: Route to Matching
        C1->>DB: C1.transition() writes state: qualified
        C1->>A3: Trigger Location Matching
    else Lead is incomplete
        A2-->>C2: ReadinessResult(status=needs_info)
        C2-->>C1: Route to Follow-up
        C1->>DB: C1.transition() writes state: needs_info
        C1->>C4: Schedule Follow-up scanner
        C4->>A5: Build outbound template with missing_fields
        A5-->>Client: Send targeted follow-up email
    end

    Note over C1,A3: Vector Matching Pipeline
    A3->>DB: Cosine similarity similarity search (pgvector)
    A3->>A3: LLM ranks and scores top locations
    A3-->>C1: Return location shortlist
    C1->>DB: Save shortlist & transition state: matched
    C1->>A5: Dispatch shortlist communication
    A5-->>Client: Email shortlist details
    
    Client->>API: Select location & book
    API->>C1: Trigger booking confirmation
    C1->>DB: Transition state: booked
    C1->>A4: Query permit regulations
    A4->>A4: Evaluate location zones and infer permit needs
    A4-->>C1: Return required checklist
    C1->>DB: Create permit records (status: permit_pending)
    
    Note over C1,A4: Permit Status Lifecycle
    A4->>C1: Update to permit_submitted
    C1->>DB: Update state in DB
    A4->>C1: Update to permit_in_review
    C1->>DB: Update state in DB
    alt Permit is Approved
        A4->>C1: Update to permit_approved
        C1->>DB: Transition state: coordination
        C1->>A5: Send shoot coordination instructions
        A5-->>Client: Email coordination details
    else Permit is Rejected
        A4->>C1: Update to permit_rejected
        C1->>DB: Transition state: permit_pending (resubmit corrects)
    end
    
    C1->>DB: Transition state: closed (shoot completed successfully)
```

### Diagram D: Finite Lead State Machine
Constrains all lead journeys. Every transition is centrally written and validated by `C1`.

```mermaid
---
config:
  layout: elk
---
stateDiagram-v2
    [*] --> new

    new --> needs_info: Readiness below threshold
    new --> ready: Readiness passes

    needs_info --> ready: Client provides missing fields
    needs_info --> inactive: 7 days of inactivity

    ready --> matching_in_progress: Matching starts
    matching_in_progress --> matched: Shortlist generated
    matching_in_progress --> needs_clarification: Poor match (max 1x)
    matching_in_progress --> manual_review: Clarification loop exhausted
    needs_clarification --> matching_in_progress: Client clarifies

    matched --> ready: Client rejects shortlist
    matched --> inactive: 7 days of inactivity
    matched --> booked: Client confirms booking
    manual_review --> ready: Ops resolves (resets count)

    booked --> permit_pending: Permit flow initiated
    permit_pending --> permit_submitted: Submitted by ops
    permit_submitted --> permit_in_review: Review under authorities
    permit_in_review --> permit_approved: Approved
    permit_in_review --> permit_rejected: Rejected by authority
    permit_rejected --> permit_pending: Correct & resubmit

    permit_approved --> coordination: Logistics active
    coordination --> closed: Shoot completed

    inactive --> needs_info: Client reactivates
    inactive --> archived: Extended nurturing expires

    archived --> [*]
    closed --> [*]
```

### Diagram E: Entity-Relationship Database Diagram
Shows the primary physical tables, constraints, pgvector integrations, and append-only audits.

```mermaid
---
config:
  layout: elk
---
erDiagram
    CLIENT ||--o{ LEAD : "triggers inquiries"
    CLIENT ||--o{ BOOKING : "owns bookings"
    LEAD ||--o{ WORKFLOW_STATE : "logs state history"
    LEAD ||--o| BOOKING : "converts to"
    LOCATION ||--o{ BOOKING : "hosts shoots"
    BOOKING ||--o{ PERMIT : "requires permits"
    LEAD ||--o{ COMMUNICATIONS_LOG : "audits messages"

    CLIENT {
        uuid id PK
        string name
        string email UK
        string phone
        timestamp created_at
    }

    LEAD {
        uuid id PK
        uuid client_id FK
        string status "enum (new, ready, matched...)"
        int readiness_score
        jsonb missing_fields
        int clarification_count
        timestamp created_at
        timestamp updated_at
    }

    WORKFLOW_STATE {
        uuid id PK
        uuid lead_id FK
        string previous_state
        string new_state
        string trigger "api, scheduler, ops"
        string actor "client, ops, system"
        timestamp created_at
    }

    BOOKING {
        uuid id PK
        uuid client_id FK
        uuid location_id FK
        uuid lead_id FK
        string status
        date shoot_date
        decimal budget
        timestamp created_at
        timestamp updated_at
    }

    LOCATION {
        uuid id PK
        string name
        string type
        string address
        boolean available
        vector embedding "1536 (pgvector)"
        jsonb metadata
        timestamp created_at
    }

    PERMIT {
        uuid id PK
        uuid booking_id FK
        string permit_type
        string status "enum (pending, submitted, approved...)"
        jsonb checklist
        timestamp created_at
        timestamp updated_at
    }

    COMMUNICATIONS_LOG {
        uuid id PK
        uuid lead_id FK
        uuid booking_id FK
        string template_name
        string channel "email"
        timestamp sent_at
        string status "sent, failed"
    }
```

---

## 🧩 3. In-Depth Multi-Agent & Service Brief

LocationHQ decouples its processes into deterministic core controllers (**C-series**) and LLM-assisted cognitive engines (**A-series**). 

### A. Core Deterministic Services (No LLM Allowed)
These represent the absolute bedrock of the system, governed by strict conditional algorithms and database logic.
* **C1: WorkflowEngine**
  * **Role**: The single system control point and sole orchestrator of state transitions.
  * **Responsibility**: Constrains transitions using a validated `ALLOWED_TRANSITIONS` map. On success, writes the state atomically to the DB, appends a row to `workflow_state`, and dispatches templates to `A5`.
  * **Rule**: No direct modifications of `lead.status` can exist anywhere else in the application.
* **C2: RoutingService**
  * **Role**: Conditional router of qualified intake data.
  * **Responsibility**: Evaluates the `ReadinessService` score. Routes leads in `ready` state to matching (`A3`) and leads in `needs_info` to follow-up (`C4`).
* **C3: ProfileService**
  * **Role**: CRM Identity pre-filler.
  * **Responsibility**: Looks up returning client profiles synchronously using incoming emails or phones, merging records and pre-filling historic data.
* **C4: FollowUpService**
  * **Role**: Follow-up coordinator.
  * **Responsibility**: Evaluates leads sitting in `needs_info` for less than 72 hours, building context lists of missing fields and handing them over to `A5` for template composition.
* **C5: AnalyticsService**
  * **Role**: SQL Aggregator.
  * **Responsibility**: Periodically queries booking metrics, permit completion rates, and lead pipeline states, materializing data structures for ops dashboards.

### B. LLM-Assisted Cognitive Services (Assistive, Never Flow-Controlling)
These services integrate LLMs exclusively to parse unstructured content, rank candidates, or adjust tones. 
* **A1: IntakeService**
  * **Role**: Unstructured document parser.
  * **Responsibility**: Processes raw incoming text inquiries (email, WhatsApp) and parses them into structured variables (budget, location type, shoot dates).
* **A2: ReadinessService**
  * **Role**: Lead completeness validator.
  * **Responsibility**: Scores lead readiness from 0 to 100 based on parsed fields, defining missing fields and categorizing leads.
* **A3: MatchingService**
  * **Role**: Contextual location matchmaker.
  * **Responsibility**: Performs a cosine similarity search across local location inventories utilizing **pgvector** and ranks shortlists based on client preferences.
* **A4: PermitService**
  * **Role**: Regulatory permit advisor.
  * **Responsibility**: Infers location zones (e.g. municipal, regional) and generates a structured regulatory checklist for ops.
* **A5: CommunicationService**
  * **Role**: Dynamic outbound delivery layer.
  * **Responsibility**: Receives structured templates from `C1`/`C4`, allows the LLM to rewrite the tone for professional personalization (never facts), validates outputs, and handles SMTP logging.
* **A6: NurturingService**
  * **Role**: Long-term re-engagement generator.
  * **Responsibility**: Evaluates inactive leads and generates personalized outreach emails to reactivate clients.

---

## 🛡️ 4. Shared LLM Client Failover Pipeline (Groq + Ollama Only)

All LLM calls throughout the `A-series` services go through our unified, hardened **LLM Client Failover Pipeline**:

```
[Groq Cloud] ──(Success)──> Return Response
     │
 (Timeout/5xx/Fail)
     ▼
[Pytest Env?] ──(Yes)──> Prevent Local Calls (Raise LLMFailure)
     │
    (No)
     ▼
[Ollama Local (qwen2.5:3b)] ──(Success)──> Return Response
```

* **Primary Engine**: Queries the Groq Cloud endpoint (`llama-3.3-70b-versatile` / API key) utilizing a shared connection pool, configured with exponential backoffs and a 30s timeout.
* **Failover Engine**: If Groq is unavailable, has exceeded limits, or returns a 5xx error, it catches the exception and falls back to **Ollama** running locally (`qwen2.5:3b` at `http://localhost:11434/api/chat`).
* **Test Isolation**: Prevents unit tests from making real HTTP calls to local Ollama. Testing automatically bypasses fallback unless explicitly enabled via `TEST_OLLAMA_FALLBACK=true`.
* **Out of Scope**: OpenAI, Anthropic (Claude), and Google (Gemini) are **completely bypassed** in production, maintaining total cost boundaries and localized sovereignty.

---

## ⚡ 5. Execution Model & Idempotent Schedules

### Operations Pipeline
* **Synchronous**: Form submissions, profile checks, and ops dashboard updates must respond instantly.
* **Asynchronous**: Pipeline enrichment (`A1` → `A2` → `C2` → `C1`), matching (`A3`), and sending notifications (`A5`) run out-of-band via FastAPI's `BackgroundTask` queue to ensure sub-second UI responsiveness.

### Automated Cron Scheduler
Powered by `APScheduler`, running inside the primary application process to ensure low-footprint operations:
* **Inactivity Scanner (Every 6 Hours)**: Transitions leads stuck in `needs_info` or `matched` with no updates for 7+ days to `inactive`.
* **Follow-up Scanner (Every 2 Hours)**: Identifies leads in `needs_info` under 72 hours and dispatches missing-field follow-ups.
* **Permit Reminder (Daily)**: Alerts ops if a permit has been stuck in `permit_in_review` beyond expected timelines.
* **Nurturing Runner (Weekly)**: Evaluates `inactive` leads, triggers `A6` re-engagement templates, and updates records.

---

## 🚀 6. Local Quickstart, Formatting, & Testing Handbooks

Ensure your `.env` contains:
```ini
POSTGRES_URL=postgresql://your_db_user:your_db_password@your_db_host/your_db_name?sslmode=require
GROQ_API_KEY=gsk_your_groq_api_key_here
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/your_slack_webhook_here
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:3b
```

### Quickstart Operations

#### Boot the Backend Server (FastAPI)
```bash
# 1. Activate environment
source .venv/bin/activate

# 2. Start Uvicorn
uvicorn app.main:app --reload
```
* **Endpoint**: `http://127.0.0.1:8000`
* **Interactive Swagger Documentation**: `http://127.0.0.1:8000/docs`
* **Status Healthcheck (Postgres + pgvector verification)**: `http://127.0.0.1:8000/health`

#### Boot the Frontend Client (React + Vite)
```bash
cd frontend
npm install
npm run dev
```
* **Endpoint**: `http://localhost:5173`

---

### CI/CD Quality Enforcements

To ensure total code sanity and complete adherence to project standards, run the following quality gates before submitting pull requests:

#### 1. Code Formatting (Black)
Checks and automatically formats Python files according to the strict 88-character standard.
```bash
.venv/bin/black app/ tests/ scratch/
```

#### 2. Import Sorting (isort)
Automatically cleans up and categories imports (standard library, third-party, local).
```bash
.venv/bin/isort app/ tests/ scratch/
```

#### 3. Linting Checks (flake8)
Scans the code for logic errors, unused variables, and style infractions.
```bash
.venv/bin/flake8 app/ tests/ scratch/
```

#### 4. Run the Unit Test Suite (pytest)
Runs our automated unit, integration, and mocking suites.
```bash
.venv/bin/pytest tests/test_breakpoints.py tests/test_hardening_layers.py -v
```
*(Confirms that both the fallback system, API states, and general operations execute with 100% green integrity).*