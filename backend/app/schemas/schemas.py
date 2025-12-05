from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime, date
from uuid import UUID

# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    phone: Optional[str] = None
    date_of_birth: Optional[date] = None

class UserCreate(UserBase):
    password: str
    role: str

class UserResponse(UserBase):
    id: UUID
    role: str
    status: str
    created_at: datetime
    last_login: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

# Authentication Schemas
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    token: str
    user: UserResponse

class TokenData(BaseModel):
    sub: str
    exp: datetime

# Scan Schemas
class ScanBase(BaseModel):
    examination_type: str
    body_region: str
    urgency_level: str
    presenting_symptoms: Optional[list[str]] = []
    current_medications: Optional[list[str]] = []
    previous_surgeries: Optional[list[str]] = []

class ScanResponse(ScanBase):
    id: UUID
    scan_number: str
    patient_name: str
    patient_id: str
    status: str
    scan_date: datetime
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# AI Prediction Schemas
class AIPredictionResponse(BaseModel):
    id: UUID
    predicted_class: str
    confidence_score: float
    class_probabilities: dict
    inference_timestamp: datetime
    
    model_config = ConfigDict(from_attributes=True)

# Report Schemas
class ReportBase(BaseModel):
    report_title: str
    clinical_indication: Optional[str] = None
    technique: Optional[str] = None
    findings: str
    impression: str
    recommendations: Optional[str] = None

class ReportCreate(ReportBase):
    scan_id: UUID

class ReportUpdate(BaseModel):
    report_title: Optional[str] = None
    findings: Optional[str] = None
    impression: Optional[str] = None
    recommendations: Optional[str] = None

class ReportResponse(ReportBase):
    id: UUID
    report_number: str
    report_type: str
    report_status: str
    published_at: Optional[datetime] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# Feedback Schemas
class FeedbackCreate(BaseModel):
    feedback_type: str  # accept, partial_override, full_override, reject
    radiologist_diagnosis: str
    clinical_notes: Optional[str] = None
    disagreement_reason: Optional[str] = None
    additional_findings: Optional[str] = None
    radiologist_confidence: Optional[float] = None
    image_quality_rating: Optional[int] = None

class FeedbackResponse(BaseModel):
    id: UUID
    feedback_type: str
    ai_diagnosis: str
    radiologist_diagnosis: str
    feedback_timestamp: datetime
    
    model_config = ConfigDict(from_attributes=True)