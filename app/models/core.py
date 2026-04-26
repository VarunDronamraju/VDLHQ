import enum
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, Column, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.models.base import Base

class LeadStatus(enum.Enum):
    new = "new"
    needs_info = "needs_info"
    ready = "ready"
    matching_in_progress = "matching_in_progress"
    needs_clarification = "needs_clarification"
    matched = "matched"
    manual_review = "manual_review"
    booked = "booked"
    permit_pending = "permit_pending"
    permit_submitted = "permit_submitted"
    permit_in_review = "permit_in_review"
    permit_approved = "permit_approved"
    permit_rejected = "permit_rejected"
    coordination = "coordination"
    closed = "closed"
    inactive = "inactive"
    archived = "archived"

class Client(Base):
    __tablename__ = "clients"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    profile_data: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default='{}')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    leads: Mapped[List["Lead"]] = relationship("Lead", back_populates="client")
    bookings: Mapped[List["Booking"]] = relationship("Booking", back_populates="client")

class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    status: Mapped[LeadStatus] = mapped_column(Enum(LeadStatus, name="lead_status"), nullable=False, default=LeadStatus.new, index=True)
    readiness_score: Mapped[Optional[float]] = mapped_column(Numeric(4, 3))
    missing_fields: Mapped[list] = mapped_column(JSONB, nullable=False, server_default='[]')
    clarification_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    intake_data: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default='{}')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), index=True)

    # Relationships
    client: Mapped["Client"] = relationship("Client", back_populates="leads")
    workflow_history: Mapped[List["WorkflowState"]] = relationship("WorkflowState", back_populates="lead")
    bookings: Mapped[List["Booking"]] = relationship("Booking", back_populates="lead")
    communications: Mapped[List["CommunicationsLog"]] = relationship("CommunicationsLog", back_populates="lead")
    errors: Mapped[List["SystemError"]] = relationship("SystemError", back_populates="lead")

class WorkflowState(Base):
    __tablename__ = "workflow_state"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("leads.id"), nullable=False, index=True)
    previous_state: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    new_state: Mapped[str] = mapped_column(String(50), nullable=False)
    trigger: Mapped[str] = mapped_column(String(100), nullable=False)
    actor: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    lead: Mapped["Lead"] = relationship("Lead", back_populates="workflow_history")

class Location(Base):
    __tablename__ = "locations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    embedding: Mapped[Optional[list]] = mapped_column(Vector(384))  # all-MiniLM-L6-v2
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, server_default='{}')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    bookings: Mapped[List["Booking"]] = relationship("Booking", back_populates="location")

class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("leads.id"), nullable=False, index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("locations.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="confirmed", index=True)
    shoot_date: Mapped[Optional[datetime]] = mapped_column(Date)
    shoot_end_date: Mapped[Optional[datetime]] = mapped_column(Date)
    budget: Mapped[Optional[float]] = mapped_column(Numeric(12, 2))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    lead: Mapped["Lead"] = relationship("Lead", back_populates="bookings")
    client: Mapped["Client"] = relationship("Client", back_populates="bookings")
    location: Mapped["Location"] = relationship("Location", back_populates="bookings")
    permits: Mapped[List["Permit"]] = relationship("Permit", back_populates="booking")
    communications: Mapped[List["CommunicationsLog"]] = relationship("CommunicationsLog", back_populates="booking")

class Permit(Base):
    __tablename__ = "permits"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bookings.id"), nullable=False, index=True)
    permit_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending", index=True)
    checklist: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default='{}')
    rejection_notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    booking: Mapped["Booking"] = relationship("Booking", back_populates="permits")

class CommunicationsLog(Base):
    __tablename__ = "communications_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("leads.id"), nullable=True, index=True)
    booking_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("bookings.id"), nullable=True, index=True)
    template_name: Mapped[str] = mapped_column(String(100), nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)  # 'email' | 'whatsapp'
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    error_detail: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    lead: Mapped[Optional["Lead"]] = relationship("Lead", back_populates="communications")
    booking: Mapped[Optional["Booking"]] = relationship("Booking", back_populates="communications")

class SystemError(Base):
    __tablename__ = "system_errors"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    lead_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("leads.id"), nullable=True, index=True)
    error_type: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    detail: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default='{}')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    lead: Mapped[Optional["Lead"]] = relationship("Lead", back_populates="errors")
