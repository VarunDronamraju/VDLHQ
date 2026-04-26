import json
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.core import Lead
from app.services.ai import llm_client
from app.core.exceptions import IntakeParseFailure

SYSTEM_PROMPT = """You are a data extraction assistant for a film location agency.
Extract structured shoot requirements from the inquiry data provided.
Respond with ONLY valid JSON. No preamble. No explanation.

JSON schema:
{
  "shoot_type": "string",
  "dates": {"start": "YYYY-MM-DD or null", "end": "YYYY-MM-DD or null"},
  "budget": {"min": number or null, "max": number or null, "currency": "string"},
  "location_type": "string or null",
  "crew_size": number or null,
  "requirements": "string or null"
}

Rules:
- Normalise ambiguous budgets: "around 50k" → {"min": 45000, "max": 55000}
- If a field is genuinely absent, use null — do not invent values
- Dates must be ISO format or null"""

async def parse(lead_id: UUID, db: AsyncSession) -> dict:
    """
    Load lead.intake_data from DB.
    Call Groq to extract structured fields (A1).
    Return structured dict.
    """
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    
    if not lead:
        raise IntakeParseFailure(f"Lead {lead_id} not found")

    raw = json.dumps(lead.intake_data)
    user_message = f"Extract structured data from this inquiry:\n\n{raw}"

    try:
        structured = await llm_client.call_json(
            messages=[{"role": "user", "content": user_message}],
            system=SYSTEM_PROMPT,
            service_name="A1",
            lead_id=str(lead_id),
        )
    except Exception as e:
        raise IntakeParseFailure(f"A1 LLM call failed: {e}") from e

    # Update Lead record with structured data
    # We merge the structured data into the existing intake_data
    current_data = lead.intake_data or {}
    lead.intake_data = {**current_data, **structured}
    
    # We don't commit here, the pipeline handles the final commit
    return structured
