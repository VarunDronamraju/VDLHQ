# Lead State Machine (Canonical)
This file MUST match the canonical state machine defined in `README.md`, `Architecture.md`, and `AGENTS.md`.

```
new
 ├─→ needs_info          (missing fields or below readiness threshold)
 │    ├─→ ready          (client provides missing fields, readiness passes)
 │    └─→ inactive       (no response after 7+ days)
 │         └─→ archived  (no response after extended nurturing period)
 └─→ ready               (readiness passes on first attempt)
      └─→ matching_in_progress
           ├─→ needs_clarification  (poor match results; one clarification loop)
           │    └─→ matching_in_progress  (max once; enforced by clarification_count)
           ├─→ matched              (shortlist sent to client)
           │    ├─→ ready           (client rejects; re-enters routing and matching)
           │    ├─→ booked          (client confirms location)
           │    │    └─→ permit_pending
           │    │         └─→ permit_submitted
           │    │              └─→ permit_in_review
           │    │                   ├─→ permit_approved
           │    │                   │    └─→ coordination
           │    │                   │         └─→ closed
           │    │                   └─→ permit_rejected
           │    │                        └─→ permit_pending  (resubmission after resolution)
           │    └─→ inactive        (no client response after 7+ days at matched)
           └─→ manual_review        (clarification loop exhausted; ops takes over)
                └─→ ready           (ops resolves; clarification_count reset to 0)
```

**Ownership rule (strict):** ONLY `C1 (WorkflowEngine)` can modify `leads.status`. All transitions MUST go through `C1.transition()` and MUST be appended to `workflow_state`.
