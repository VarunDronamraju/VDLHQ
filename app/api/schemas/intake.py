import uuid
from typing import Any, Dict, Optional

from pydantic import BaseModel, model_validator


class ContactSchema(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None

    @model_validator(mode="after")
    def email_or_phone_required(self):
        if not self.email and not self.phone:
            raise ValueError("Either email or phone is required")
        return self


class DatesSchema(BaseModel):
    start: Optional[str] = None
    end: Optional[str] = None


class BudgetSchema(BaseModel):
    min: Optional[float] = None
    max: Optional[float] = None
    currency: Optional[str] = "GBP"


class InquiryRequest(BaseModel):
    contact: ContactSchema
    client_profile: Optional[Dict[str, Any]] = None
    shoot_type: str
    dates: Optional[DatesSchema] = None
    budget: Optional[Any] = None  # Flexible budget for demo
    location_type: Optional[str] = None
    crew_size: Optional[int] = None
    requirements: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class InquiryResponse(BaseModel):
    lead_id: uuid.UUID
    client_id: uuid.UUID
    status: str
    message: str
