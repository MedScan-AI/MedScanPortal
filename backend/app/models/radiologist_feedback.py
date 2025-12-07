from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum as SQLEnum, Numeric, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
import enum
from app.core.database import Base

class FeedbackType(str, enum.Enum):
    accept = "accept"
    partial_override = "partial_override"
    full_override = "full_override"
    reject = "reject"

class DiagnosisClass(str, enum.Enum):
    normal = "Normal"
    tuberculosis = "Tuberculosis"
    lung_cancer = "Lung_Cancer"
    other_abnormality = "Other_Abnormality"
    inconclusive = "Inconclusive"

class RadiologistFeedback(Base):
    __tablename__ = "radiologist_feedback"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey('scans.id', ondelete='CASCADE'), nullable=False, index=True)
    radiologist_id = Column(UUID(as_uuid=True), ForeignKey('radiologist_profiles.id', ondelete='CASCADE'), nullable=False)
    
    # Feedback details
    feedback_type = Column(SQLEnum(FeedbackType), nullable=False)
    
    # Diagnosis
    ai_diagnosis = Column(String(50))  # What AI predicted
    radiologist_diagnosis = Column(SQLEnum(DiagnosisClass), nullable=False)
    
    # Detailed feedback
    clinical_notes = Column(Text)
    disagreement_reason = Column(Text)
    additional_findings = Column(Text)
    
    # Confidence & Quality
    radiologist_confidence = Column(Numeric(3, 2))  # 0.00 to 1.00
    image_quality_rating = Column(Integer)  # 1-5
    
    # Timestamps
    feedback_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<RadiologistFeedback {self.radiologist_diagnosis}>"