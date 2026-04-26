# LocationHQ Implementation Checklist (v2)

This checklist is the **Source of Truth** for the LocationHQ build, strictly following the [Full Build Guide (TODOHUGE.md)](file:///Users/VD/Desktop/LHQ/TODOHUGE.md) and [Agent Rules](file:///Users/VD/Desktop/LHQ/FIles).

---

## 🟢 PHASE 1 — Foundation (COMPLETED)
- [x] FastAPI + Uvicorn + Pydantic v2 setup.
- [x] Neon PostgreSQL connection via async SQLAlchemy.
- [x] `.env` / `.env.example` configured.
- [x] Initial models (`Client`, `Lead`, `WorkflowState`) created.
- [x] Tables verified in Neon.
- [x] `/health` endpoint functional.

---

## 🟢 PHASE 2 — Schema Completion (COMPLETED)
*Target: Complete the DB backbone. Refer to [Schema.md](file:///Users/VD/Desktop/LHQ/FIles/Schema.md).*

- [x] **Correct Vector Dimension**: Update `locations.embedding` to `Vector(384)` (for `all-MiniLM-L6-v2`).
- [x] **Implement Remaining Models**:
    - [x] `Location` (with 384-dim vector).
    - [x] `Booking`.
    - [x] `Permit`.
    - [x] `CommunicationsLog`.
    - [x] `SystemError`.
- [x] **Verification**:
    - [x] Run initialization script.
    - [x] Confirm all 8 tables exist and dimensions are correct.

---

## 🟢 PHASE 3 — POST /inquiry Endpoint (COMPLETED)
*Target: Atomic lead creation. Refer to [STageAPI.md](file:///Users/VD/Desktop/LHQ/STageAPI.md).*

- [x] **Schemas**: Pydantic models for `InquiryRequest`.
- [x] **Route**: `POST /inquiry` with atomic transaction (Client → Lead → WorkflowState).
- [x] **Verification**: Submit test payload, check DB audit trail.

---

## 🟢 PHASE 4 — C1 WorkflowEngine (COMPLETED)
*Target: Centralized state machine. Refer to [lead_State_machine.md](file:///Users/VD/Desktop/LHQ/FIles/lead_State_machine.md).*

- [x] **Workflow Service**: Implement `WorkflowEngine.transition()` with guards.
- [x] **Audit Trail**: Ensure every state change is logged in `workflow_state`.

---

## 🟢 PHASE 5 — LLM Client Utility (Groq) (COMPLETED)
*Target: Shared AI infrastructure.*

- [x] **Groq Client**: Implement `call()` and `call_json()` using `AsyncGroq`.
- [x] **Retry Logic**: Implement `tenacity` retries for rate limits.

---

## 🟢 PHASE 6 — Intake Pipeline (A1 + A2 + C2) (COMPLETED)
*Target: Async lead processing. Refer to [Workflow.md](file:///Users/VD/Desktop/LHQ/FIles/Workflow.md).*

- [x] **A1 (Parser)**: Groq-powered extraction to `intake_data`.
- [x] **A2 (Readiness)**: Completeness scoring.
- [x] **Background Task**: Wire pipeline to `/inquiry` endpoint.

---

## 🟢 PHASE 7 — A3 Matching (pgvector) (COMPLETED)
*Target: Semantic location discovery.*

- [x] **Local Embeddings**: `sentence-transformers` for location matching.
- [x] **Matching Logic**: pgvector cosine similarity + LLM ranking.

---

## 🚧 PHASE 8 — A5 Communication Service (CURRENT)
- [ ] **Template Engine**: Render templates and (optional) LLM tone rewrite.
- [ ] **Channel Stubs**: Email/WhatsApp logging stubs.

---

## ⚪ PHASE 9 — APScheduler
- [ ] **Scheduler Init**: AsyncIOScheduler in FastAPI lifespan.
- [ ] **Jobs**: Inactivity scanner, follow-up scanner, permit reminders.

---

## 🟢 PHASE 10 — GET Endpoints (COMPLETED)
- [x] **Ops/Client APIs**: Full dashboard and pipeline read/write routes.
- [x] **Internal Retry**: Endpoint to manually re-trigger intake pipeline.

---

## ⚪ PHASE 11-15 — Completion
- [x] **Phase 11**: Permits (A4) implementation.
- [ ] **Phase 12**: Analytics (C5) snapshots.
- [ ] **Phase 13**: Nurturing (A6) + Follow-up (C4).
- [ ] **Phase 14**: JWT Auth overlay.
- [ ] **Phase 15**: Resilience + Observability (JSON logging, request IDs).

---

### 📏 Hard Rules
1. **Vertical Build**: No skipping ahead.
2. **Deterministic State**: Only C1 modifies `status`.
3. **Async Only**: No blocking calls.
4. **Verified**: Test → Commit → Proceed.
