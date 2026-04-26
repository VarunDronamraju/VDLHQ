from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import LHQException
from app.models.core import Booking, Permit
from app.services.ai.llm_client import call_json


class PermitChecklistError(LHQException):
    def __init__(self, message: str):
        super().__init__(message, status_code=500)


class PermitTransitionError(LHQException):
    def __init__(self, message: str):
        super().__init__(message, status_code=400)


class PermitService:
    async def generate_checklist(self, booking_id: UUID, db: AsyncSession) -> dict:
        """
        A4 - Infers permit requirements using Groq and creates Permit records.
        """
        # 1. Load context with lead joined to avoid lazy loading issues
        stmt = select(Booking).options(selectinload(Booking.lead), selectinload(Booking.location)).where(Booking.id == booking_id)
        result = await db.execute(stmt)
        booking = result.scalar_one_or_none()
        if not booking:
            raise PermitChecklistError(f"Booking {booking_id} not found")

        shoot_type = booking.lead.intake_data.get("shoot_type", "commercial")
        location = booking.location

        # Rules-based fallback for common types
        if location.type.lower() == "studio":
            # Standard studios usually don't need municipal permits
            permit_type = "internal_studio_approval"
            checklist = {"items": ["Sign waiver", "Confirm insurance"], "authority": "Studio Manager", "expected_approval_days": 1}
            return await self._create_permit(db, booking_id, permit_type, checklist)

        # Groq-based inference for other types
        prompt = f"""
        Analyze the following shoot details and infer permit requirements.
        Location: {location.name} ({location.type})
        Address: {location.address}
        Shoot Type: {shoot_type}

        Return a JSON object with:
        - permit_types: list of required permit types
        - details: list of objects for each permit type containing:
            - type: name of the permit
            - authority: issuing authority
            - expected_approval_days: integer estimate
            - requirements: list of strings
        """

        try:
            data = await call_json(
                messages=[{"role": "user", "content": prompt}],
                system="You are a production permit expert. You must return ONLY a valid JSON object.",
                service_name="permit_inference",
                lead_id=str(booking.lead_id),
            )

            # Use data directly as it's already parsed by call_json
            main_permit = data["details"][0]  # Just take the first one for the main record
            return await self._create_permit(db, booking_id, main_permit["type"], main_permit)

        except Exception:
            # Fallback to general municipal permit if LLM fails
            return await self._create_permit(
                db, booking_id, "municipal_general", {"authority": "Local Municipal Corp", "expected_approval_days": 5, "requirements": ["Insurance", "Shoot schedule"]}
            )

    async def _create_permit(self, db: AsyncSession, booking_id: UUID, permit_type: str, checklist: dict) -> dict:
        permit = Permit(booking_id=booking_id, permit_type=permit_type, status="pending", checklist=checklist)
        db.add(permit)
        await db.flush()
        await db.refresh(permit)
        return {"permit_id": str(permit.id), "permit_type": permit_type, "status": "pending", "checklist": checklist}

    async def update_permit_status(self, permit_id: UUID, new_status: str, db: AsyncSession, notes: str = None) -> dict:
        """
        A4 - Updates permit status and enforces valid transitions.
        """
        permit = await db.get(Permit, permit_id)
        if not permit:
            raise PermitChecklistError(f"Permit {permit_id} not found")

        valid_transitions = {"pending": ["submitted"], "submitted": ["in_review"], "in_review": ["approved", "rejected"], "rejected": ["pending"]}

        current = permit.status
        if new_status not in valid_transitions.get(current, []):
            raise PermitTransitionError(f"Invalid permit transition: {current} -> {new_status}")

        permit.status = new_status
        if notes:
            permit.rejection_notes = notes

        await db.flush()
        await db.refresh(permit)

        return {"permit_id": str(permit.id), "previous_status": current, "new_status": new_status, "rejection_notes": permit.rejection_notes, "booking_id": permit.booking_id}


permit_service = PermitService()
