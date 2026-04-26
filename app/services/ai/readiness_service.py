import json
from uuid import UUID
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.core import Lead
from app.services.ai import llm_client
from app.core.exceptions import ReadinessFailure

READINESS_THRESHOLD = 0.80

SYSTEM_PROMPT = """You are a lead qualification assistant for a film location agency.
Evaluate whether this inquiry has enough information to proceed to location matching.

Required fields:
- contact (name + email or phone)
- shoot_type
- dates (start AND end — must be specific, not vague)
- budget (min AND max — must be a usable range, not vague like "around something")
- location_type

Scoring rules:
- Each required field that is present AND usable = 0.20
- A field that is present but unusable (vague, contradictory, impossible) = 0.00
- Score = sum of usable required fields / 5

Respond with ONLY valid JSON:
{
  "score": 0.0 to 1.0,
  "status": "ready" or "needs_info",
  "missing_fields": ["field_name", ...],
  "reasoning": "one sentence"
}"""

@dataclass
class ReadinessResult:
    score: float
    status: str
    missing_fields: list[str]
    reasoning: str

async def score(
    lead_id: UUID,
    structured_data: dict,
    db: AsyncSession,
) -> ReadinessResult:
    """
    Score lead completeness via Groq (A2).
    Threshold: score >= 0.80 → 'ready', else 'needs_info'.
    """
    user_message = f"Evaluate this inquiry:\n\n{json.dumps(structured_data)}"

    try:
        data = await llm_client.call_json(
            messages=[{"role": "user", "content": user_message}],
            system=SYSTEM_PROMPT,
            service_name="A2",
            lead_id=str(lead_id),
        )
    except Exception as e:
        raise ReadinessFailure(f"A2 scoring failed: {e}") from e

    score_val = float(data.get("score", 0.0))
    # Threshold check
    status = "ready" if score_val >= READINESS_THRESHOLD else "needs_info"

    # Update Lead record with readiness data
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if lead:
        lead.readiness_score = score_val
        lead.missing_fields = data.get("missing_fields", [])
        # Note: We don't update status here, C1/WorkflowEngine does that in the pipeline

    return ReadinessResult(
        score=score_val,
        status=status,
        missing_fields=data.get("missing_fields", []),
        reasoning=data.get("reasoning", ""),
    )
