from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel

from app.models.core import LeadStatus


class LeadBrief(BaseModel):
    id: UUID
    status: LeadStatus
    created_at: datetime
    updated_at: datetime
    intake_data: Dict[str, Any]

    class Config:
        from_attributes = True


class BookingBrief(BaseModel):
    id: UUID
    lead_id: UUID
    location_id: UUID
    status: str
    shoot_date: Optional[datetime]
    location_name: Optional[str] = None

    class Config:
        from_attributes = True


class ClientDashboard(BaseModel):
    leads: List[LeadBrief]
    bookings: List[BookingBrief]


class WorkflowStateSchema(BaseModel):
    previous_state: Optional[str]
    new_state: str
    trigger: str
    actor: str
    created_at: datetime

    class Config:
        from_attributes = True


class CommunicationLogSchema(BaseModel):
    template_name: str
    channel: str
    status: str
    sent_at: Optional[datetime]
    error_detail: Optional[str]

    class Config:
        from_attributes = True


class LeadDetail(BaseModel):
    id: UUID
    client_id: UUID
    status: LeadStatus
    readiness_score: Optional[float]
    missing_fields: List[str]
    intake_data: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    workflow_history: List[WorkflowStateSchema]
    communications: List[CommunicationLogSchema]

    class Config:
        from_attributes = True


class LeadUpdate(BaseModel):
    intake_data: Dict[str, Any]


class LeadAction(BaseModel):
    target_state: str
    actor: str = "ops"
    trigger: str = "manual_action"
    metadata: Optional[Dict[str, Any]] = None


class PermitBrief(BaseModel):
    id: UUID
    permit_type: str
    status: str
    updated_at: datetime


class BookingDetail(BaseModel):
    id: UUID
    lead_id: UUID
    client_name: str
    location_name: str
    status: str
    shoot_date: Optional[datetime]
    shoot_end_date: Optional[datetime]
    permits: List[PermitBrief]

    class Config:
        from_attributes = True


class PermitUpdate(BaseModel):
    status: str
    rejection_notes: Optional[str] = None


class AnalyticsSnapshot(BaseModel):
    status_counts: Dict[str, int]
    total_leads: int
    conversion_rate: float
    # Add more as needed by Phase 12 later
