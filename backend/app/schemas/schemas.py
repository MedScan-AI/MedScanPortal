from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, Dict, List
from datetime import datetime, date
from uuid import UUID

# USER SCHEMAS
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

# AUTHENTICATION SCHEMAS
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    token: str
    user: UserResponse

class TokenData(BaseModel):
    sub: str
    exp: datetime

# SCAN SCHEMAS
class ScanBase(BaseModel):
    examination_type: str
    body_region: str
    urgency_level: str
    presenting_symptoms: Optional[List[str]] = []
    current_medications: Optional[List[str]] = []
    previous_surgeries: Optional[List[str]] = []

class ScanDetailResponse(ScanBase):
    id: UUID
    scan_number: str
    patient_name: str
    patient_id: str
    status: str
    scan_date: datetime
    clinical_notes: Optional[str] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ScanResponse(ScanBase):
    id: UUID
    scan_number: str
    patient_name: str
    patient_id: str
    status: str
    scan_date: datetime
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# IMAGE SCHEMAS
class ScanImageResponse(BaseModel):
    id: UUID
    url: str
    gcs_url: str
    order: int
    size_bytes: Optional[int] = None
    format: Optional[str] = None
    created_at: Optional[datetime] = None

# AI PREDICTION SCHEMAS
class AIPredictionResponse(BaseModel):
    prediction_id: str
    predicted_class: str
    confidence_score: float
    class_probabilities: Dict[str, float]
    gradcam_url: Optional[str] = None
    original_image_url: Optional[str] = None
    inference_timestamp: datetime
    
    model_config = ConfigDict(from_attributes=True)

# FEEDBACK SCHEMAS
class FeedbackCreate(BaseModel):
    feedback_type: str  # accept, partial_override, full_override, reject
    radiologist_diagnosis: str
    ai_diagnosis: Optional[str] = None
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

# REPORT SCHEMAS
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
    clinical_indication: Optional[str] = None
    technique: Optional[str] = None
    findings: Optional[str] = None
    impression: Optional[str] = None
    recommendations: Optional[str] = None

class DraftReportResponse(ReportBase):
    id: UUID
    report_number: str
    report_type: str
    report_status: str
    scan_number: str
    patient_name: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ReportResponse(ReportBase):
    id: UUID
    report_number: str
    report_type: str
    report_status: str
    published_at: Optional[datetime] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)