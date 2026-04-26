from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.core import Lead
from app.services.ai import llm_client

logger = structlog.get_logger()

NURTURING_SYSTEM_PROMPT = """You are a senior concierge for a premium film location agency.
Your goal is to re-engage a client whose inquiry became inactive.
You will be provided with:
1. Client Name
2. Details of their last inquiry (shoot type, requirements)
3. History of prior communications

Task:
Generate a short, professional, and personalized re-engagement message.
Acknowledge their previous interest in "{shoot_type}".
Suggest that we have updated our location portfolio and would love to help with their next project.

Rules:
- Keep it under 100 words.
- Tone: Professional, helpful, non-intrusive.
- Do NOT invent specific new locations.
- If the history is empty, be warm but general.
- Return ONLY the message body.
"""


class NurturingService:
    async def generate(self, lead_id: UUID, db: AsyncSession) -> dict:
        """
        A6 - Generates a personalized re-engagement message.
        Returns a dict with subject and body.
        """
        try:
            # 1. Load context
            stmt = select(Lead).options(selectinload(Lead.client), selectinload(Lead.communications)).where(Lead.id == lead_id)
            result = await db.execute(stmt)
            lead = result.scalar_one_or_none()

            if not lead:
                return self._get_fallback_message("Client")

            client = lead.client
            shoot_type = lead.intake_data.get("shoot_type", "production")

            # 2. Format history for LLM
            comms_history = "\n".join([f"- {c.created_at.date()}: {c.template_name} via {c.channel}" for c in lead.communications])

            user_prompt = f"""
            Client: {client.name}
            Last Inquiry: {shoot_type}
            Requirements: {lead.intake_data.get('requirements', 'Not specified')}
            Prior Comms:
            {comms_history}
            """

            # 3. Call LLM
            body = await llm_client.call(
                messages=[{"role": "user", "content": user_prompt}],
                system=NURTURING_SYSTEM_PROMPT.format(shoot_type=shoot_type),
                service_name="A6_nurturing",
                lead_id=str(lead_id),
            )

            if body is None or body == "" or body.strip() == "":
                return self._get_fallback_message(client.name, shoot_type)

            return {"subject": f"Re: Your {shoot_type} shoot requirements", "body": body, "channel": "email"}

        except Exception as e:
            logger.error("nurturing_generation_failed", lead_id=str(lead_id), error=str(e))
            client_name = "Client"
            if "lead" in locals() and lead and lead.client:
                client_name = lead.client.name
            return self._get_fallback_message(client_name, shoot_type if "shoot_type" in locals() else "production")

    def _get_fallback_message(self, client_name: str, shoot_type: str = "production") -> dict:
        """Standard fallback template if AI fails"""
        return {
            "subject": f"Checking in regarding your {shoot_type} inquiry",
            "body": (
                f"Hi {client_name},\n\nI hope you're doing well. "
                f"We haven't heard from you in a while regarding your {shoot_type} inquiry.\n\n"
                "We've recently added several new locations to our portfolio that might be a great fit for your upcoming projects. "
                "Would you like to schedule a quick call to discuss your current needs?\n\n"
                "Best regards,\nThe LocationHQ Team"
            ),
            "channel": "email",
        }


nurturing_service = NurturingService()
