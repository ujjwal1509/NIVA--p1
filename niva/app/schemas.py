# app/schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime


class SymptomItem(BaseModel):
    name: str
    onset_date: Optional[str] = None
    onset_relative: Optional[str] = None
    duration_days: Optional[int] = None
    severity: Optional[str] = None
    associated_symptoms: Optional[List[str]] = []
    triggers: Optional[List[str]] = []
    relievers: Optional[List[str]] = []
    notes: Optional[str] = None


class StructuredReport(BaseModel):
    session_id: str
    patient_id: Optional[str] = None
    collected_at: datetime
    presenting_complaint: Optional[str] = None
    symptoms: List[SymptomItem] = []
    allergies: Optional[List[str]] = []
    current_medications: Optional[List[str]] = []
    past_medical_history: Optional[List[str]] = []
    urgency: Optional[str] = None
    differential_hypotheses: Optional[List[str]] = []
    recommended_next_action: Optional[str] = None
    evidence_snippets: Optional[List[Any]] = []
    confidence_score: Optional[float] = None
    model_version: Optional[str] = None
    notes_for_doctor: Optional[str] = None
