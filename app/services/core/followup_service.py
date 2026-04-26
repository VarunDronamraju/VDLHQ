from typing import List
from uuid import UUID

from pydantic import BaseModel


class FollowUpContext(BaseModel):
    lead_id: UUID
    template_name: str
    template_data: dict
    channel: str


class FollowUpService:
    def build_followup(self, lead_id: UUID, client_name: str, shoot_type: str, missing_fields: List[str]) -> FollowUpContext:
        """
        C4 - Pure logic to construct follow-up context.
        """
        missing_fields_list = "- " + "\n- ".join(missing_fields) if missing_fields else "Inquiry details"

        return FollowUpContext(
            lead_id=lead_id,
            template_name="followup_missing_fields",
            template_data={
                "client_name": client_name,
                "shoot_type": shoot_type,
                "missing_fields_list": missing_fields_list,
            },
            channel="email",
        )


followup_service = FollowUpService()
