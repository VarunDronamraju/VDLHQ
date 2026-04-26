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

## 🚧 PHASE 2 — Schema Completion (CURRENT)
*Target: Complete the DB backbone. Refer to [Schema.md](file:///Users/VD/Desktop/LHQ/FIles/Schema.md).*

- [ ] **Correct Vector Dimension**: Update `locations.embedding` to `Vector(384)` (for `all-MiniLM-L6-v2`).
- [ ] **Implement Remaining Models**:
    - [ ] `Location` (with 384-dim vector).
    - [ ] `Booking`.
    - [ ] `Permit`.
    - [ ] `CommunicationsLog`.
    - [ ] `SystemError`.
- [ ] **Verification**:
    - [ ] Run initialization script.
    - [ ] Confirm all 8 tables exist and dimensions are correct.

---

## ⚪ PHASE 3 — POST /inquiry Endpoint
*Target: Atomic lead creation. Refer to [STageAPI.md](file:///Users/VD/Desktop/LHQ/STageAPI.md).*

- [ ] **Schemas**: Pydantic models for `InquiryRequest`.
- [ ] **Route**: `POST /inquiry` with atomic transaction (Client → Lead → WorkflowState).
- [ ] **Verification**: Submit test payload, check DB audit trail.

---

## ⚪ PHASE 4 — C1 WorkflowEngine
*Target: Centralized state machine. Refer to [lead_State_machine.md](file:///Users/VD/Desktop/LHQ/FIles/lead_State_machine.md).*

- [ ] **Workflow Service**: Implement `WorkflowEngine.transition()` with guards.
- [ ] **Audit Trail**: Ensure every state change is logged in `workflow_state`.

---

## ⚪ PHASE 5 — LLM Client Utility (Groq)
*Target: Shared AI infrastructure.*

- [ ] **Groq Client**: Implement `call()` and `call_json()` using `AsyncGroq`.
- [ ] **Retry Logic**: Implement `tenacity` retries for rate limits.

---

## ⚪ PHASE 6 — Intake Pipeline (A1 + A2 + C2)
*Target: Async lead processing. Refer to [Workflow.md](file:///Users/VD/Desktop/LHQ/FIles/Workflow.md).*

- [ ] **A1 (Parser)**: Groq-powered extraction to `intake_data`.
- [ ] **A2 (Readiness)**: Completeness scoring.
- [ ] **Background Task**: Wire pipeline to `/inquiry` endpoint.

---

## ⚪ PHASE 7 — A3 Matching (pgvector)
- [ ] **Local Embeddings**: `sentence-transformers` for location matching.
- [ ] **Matching Logic**: pgvector cosine similarity + LLM ranking.

---

## ⚪ PHASE 8 — A5 Communication Service
- [ ] **Template Engine**: Render templates and (optional) LLM tone rewrite.
- [ ] **Channel Stubs**: Email/WhatsApp logging stubs.

---

## ⚪ PHASE 9 — APScheduler
- [ ] **Scheduler Init**: AsyncIOScheduler in FastAPI lifespan.
- [ ] **Jobs**: Inactivity scanner, follow-up scanner, permit reminders.

---

## ⚪ PHASE 10 — GET Endpoints
- [ ] **Ops/Client APIs**: Full dashboard and pipeline read/write routes.

---

## ⚪ PHASE 11-15 — Completion
- [ ] **Phase 11**: Permits (A4) implementation.
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
