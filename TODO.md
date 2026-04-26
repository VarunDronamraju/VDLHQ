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

## 🟢 PHASE 8 — A5 Communication Service (COMPLETED)
- [x] **Template Engine**: Render templates and (optional) LLM tone rewrite.
- [x] **Channel Stubs**: Email/WhatsApp logging stubs.

---

## 🟢 PHASE 9 — APScheduler (COMPLETED)
- [x] **Scheduler Init**: AsyncIOScheduler in FastAPI lifespan.
- [x] **Jobs**: Inactivity scanner, follow-up scanner, permit reminders.

---

## 🟢 PHASE 10 — GET Endpoints (COMPLETED)
- [x] **Ops/Client APIs**: Full dashboard and pipeline read/write routes.
- [x] **Internal Retry**: Endpoint to manually re-trigger intake pipeline.

---

## 🟢 PHASE 11-15 — Completion (COMPLETED)
- [x] **Phase 11**: Permits (A4) implementation.
- [x] **Phase 12**: Analytics (C5) snapshots.
- [x] **Phase 13**: Nurturing (A6) + Follow-up (C4) implementation.
- [x] **Phase 14**: JWT Auth overlay.
- [x] **Phase 15**: Resilience + Observability (JSON logging, request IDs).

---

## 🚧 PHASE 16 — Railway Deployment (CURRENT)
- [x] **Create Procfile**: `web: uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- [x] **Lock Python Version**: Create `.python-version` with `3.9`.
- [ ] **Railway Configuration**: Link GitHub repo and deploy.
- [ ] **Environment Variables**: Add all keys from `.env.example` to Railway dashboard.
- [ ] **Verify Production**: Test public URL `/health` and `/docs`.
---

## 🚧 PHASE 17 — Frontend Foundation (Vite + React)
- [ ] **Repository Setup**: Initialize Vite + React project.
- [ ] **Design System Setup**: Configure Tailwind theme with premium colors, dark/light surface tokens.
- [ ] **Typography**: Import fluid typography (clamp) and set primary fonts.
- [ ] **Global Components**: Build base Button, Input, Card with subtle glassmorphism.
- [ ] **API Client**: Configure Axios/Fetch instance to connect to deployed Railway backend.

---

## ✅ PHASE 17 — FOUNDATION
- [x] **Vite + React setup**: Initialize minimal project.
- [x] **Tailwind config**: Setup basic styling rules.
- [x] **API client**: Axios/Fetch with base URL and JWT header.

---

## 🟢 PHASE 18 — CORE FLOW (COMPLETED)
- [x] **Inquiry Page**: Simple form mapping to `POST /api/v1/inquiry`.
- [x] **Ops Dashboard**: List leads, group by status, valid state transitions only.
- [x] **Client Dashboard**: List client leads showing status and details.

---

## 🚧 PHASE 19 — MINIMAL UI & POLISH (CURRENT)
- [ ] **Clean Layout**: Ensure strictly minimal, no parallax, no heavy animations.
- [ ] **Refine Dashboards**: subtle design updates to Inquiry, Ops, and Client views.
- [ ] **Navigation**: Implement simple Navbar (Home, Portfolio, Reviews, Inquiry, Login).

---

## 🚧 PHASE 20 — PRODUCT PAGES
- [ ] **Landing Page (/)**:
    - [ ] Hero: Strong headline + Inquiry CTA.
    - [ ] Previous Productions: Horizontal card slider.
    - [ ] Production Spaces: Grid of location cards.
    - [ ] Final CTA.
- [ ] **Portfolio Page (/portfolio)**: Static showcase grid, minimal text.
- [ ] **Reviews Page (/reviews)**: Simple testimonials list.

---

### 📏 Frontend Hard Rules
1. **No Code Reuse**: Do not reuse code from old projects. Visual inspiration ONLY.
2. **Product-Focused**: Clean, modern UI. No marketing fluff.
3. **No Overengineering**: No search, no complex filtering, no AI features in UI.
4. **Subtle Motion**: Fade/translate micro-interactions only. No parallax.
5. **Verified**: Test 1:1 with backend APIs.

### 📏 Hard Rules
1. **Vertical Build**: No skipping ahead.
2. **Deterministic State**: Only C1 modifies `status`.
3. **Async Only**: No blocking calls.
4. **Verified**: Test → Commit → Proceed.
