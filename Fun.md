# LocationHQ Function Registry

## Core Infrastructure
- `app.db.connection.test_connection()`: Verifies connectivity to Neon PostgreSQL via AsyncSession.
- `app.db.session.get_db()`: FastAPI dependency yielding an asynchronous database session.
- `app.core.error_logger.log_system_error(db, source, lead_id, error)`: Persists pipeline or system failures into the `system_errors` table for audit.

## AI Services (Agents)
- `app.services.ai.llm_client.call(messages, system, ...)`: Shared utility for high-speed LLaMA 3.3 calls via Groq with exponential backoff.
- `app.services.ai.llm_client.call_json(messages, system, ...)`: Enforces valid JSON output from the LLM, essential for automated parsing.
- `app.services.ai.intake_service.parse(lead_id, db)`: (Phase 6) Extracts structured requirements from raw inquiry data using LLM (A1).
- `app.services.ai.readiness_service.score(lead_id, structured_data, db)`: (Phase 6) Scores lead completeness and identifies missing fields via LLM (A2).

## Core Logic (Controllers)
- `app.services.ai.core.workflow_engine.WorkflowEngine.transition(lead_id, target_state, trigger, ...)`: The authoritative state manager for leads (C1).
- `app.services.core.routing_service.RoutingService.route(readiness_result)`: Deterministic logic to decide if a lead moves to matching or needs more info (C2).

## Pipelines
- `app.pipelines.intake_pipeline.run_intake_pipeline(lead_id)`: Orchestrates the A1 → A2 → C2 flow as an asynchronous background task.
