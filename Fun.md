FILE: app/main.py
FUNCTION: startup_event — runs at FastAPI startup and checks database connectivity once.
FUNCTION: health_check — returns API health status and verifies DB connection before responding.

FILE: app/db/connection.py
FUNCTION: _load_env_file — loads key-value pairs from `.env` into environment variables if missing.
FUNCTION: _normalize_postgres_url — converts `POSTGRES_URL` into a SQLAlchemy-compatible async Postgres URL.
FUNCTION: test_connection — executes `SELECT 1` using the DB engine to confirm connectivity.

FILE: app/db/session.py
FUNCTION: get_db — yields an async SQLAlchemy session for request-scoped DB access.

FILE: app/db/init_db.py
FUNCTION: init_db — initializes schema objects, extension/index setup, and recreates core DB tables.

FILE: app/api/routes/intake.py
FUNCTION: submit_inquiry — creates or finds a client, creates a lead, logs initial workflow state, and commits atomically.

FILE: app/api/routes/workflow.py
FUNCTION: transition_lead — applies a lead state transition through the workflow engine and maps failures to HTTP errors.

FILE: app/api/schemas/intake.py
FUNCTION: email_or_phone_required — validates that each inquiry contact contains at least email or phone.

FILE: app/services/ai/llm_client.py
FUNCTION: call — sends a standard async Groq chat completion request with retries and returns text output.
FUNCTION: call_json — sends a Groq request in JSON mode and returns parsed JSON output.

FILE: app/services/core/workflow_engine.py
FUNCTION: __init__ — stores the async DB session inside the workflow engine instance.
FUNCTION: transition — validates and executes lead status changes, writes workflow history, and returns transition metadata.

FILE: app/core/exceptions.py
FUNCTION: __init__ (LeadNotFound) — creates a custom error when a lead ID is missing in DB.
FUNCTION: __init__ (InvalidTransition) — creates a custom error for invalid workflow state changes.
FUNCTION: __init__ (LLMFailure) — creates a custom error for LLM/API call failures.
FUNCTION: __init__ (IntakeParseFailure) — creates a custom error for inquiry parsing failures.
FUNCTION: __init__ (ReadinessFailure) — creates a custom error for readiness evaluation failures.
FUNCTION: __init__ (MatchingFailure) — creates a custom error for location matching failures.

FILE: app/models/base.py
FUNCTIONS: none (contains ORM base class only).

FILE: app/models/core.py
FUNCTIONS: none (contains ORM models/enums/relationships only).

FILE: app/api/__init__.py
FUNCTIONS: none.

FILE: app/api/routes/__init__.py
FUNCTIONS: none.

FILE: app/api/schemas/__init__.py
FUNCTIONS: none.

FILE: app/core/__init__.py
FUNCTIONS: none.

FILE: app/services/__init__.py
FUNCTIONS: none.

FILE: app/services/ai/__init__.py
FUNCTIONS: none.

FILE: app/services/core/__init__.py
FUNCTIONS: none.

FILE: scratch/verify_neon.py
FUNCTIONS: none (script-style verification without function definitions).

FILE: scratch/verify_workflow.py
FUNCTION: verify_workflow — runs an async workflow transition test including valid and invalid transition checks.

FILE: scratch/verify_llm.py
FUNCTION: verify_llm — verifies standard and JSON Groq LLM client calls.

FILE: scratch/verify_phase2.py
FUNCTION: verify_phase2 — validates DB schema completeness, inserts test records, and checks basic relationships.

FILE: scratch/verify_inquiry.py
FUNCTION: verify_atomic_inquiry — validates DB records created by inquiry submission flow.
