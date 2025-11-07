# app/models.py
import sqlalchemy as sa
from sqlalchemy.orm import declarative_base
from sqlalchemy.dialects.postgresql import UUID
import uuid

Base = declarative_base()


class SymptomSession(Base):
    __tablename__ = "symptom_sessions"
    session_id = sa.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = sa.Column(UUID(as_uuid=True), nullable=True)
    created_at = sa.Column(sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"))
    collected_at = sa.Column(sa.TIMESTAMP(timezone=True), nullable=True)
    presenting_complaint = sa.Column(sa.Text, nullable=True)
    urgency = sa.Column(sa.Text, nullable=True)
    confidence_score = sa.Column(sa.Float, nullable=True)
    model_version = sa.Column(sa.Text, nullable=True)
    status = sa.Column(sa.Text, nullable=True, default="in_progress")
