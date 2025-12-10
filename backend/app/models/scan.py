from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum, Text, ARRAY, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
import enum
from app.core.database import Base

class ScanStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    ai_analyzed = "ai_analyzed"
    radiologist_reviewed = "radiologist_reviewed"
    completed = "completed"
    cancelled = "cancelled"

class UrgencyLevel(str, enum.Enum):
    routine = "routine"          
    urgent = "urgent"            
    emergent = "emergent"        

class ExaminationType(str, enum.Enum):
    xray = "xray"                
    ct = "ct"                    
    mri = "mri"                  
    pet = "pet"                  
    ultrasound = "ultrasound"    

class BodyRegion(str, enum.Enum):
    chest = "chest"              
    head = "head"                
    abdomen = "abdomen"          
    pelvis = "pelvis"            
    spine = "spine"              
    extremities = "extremities"  

class Scan(Base):
    __tablename__ = "scans"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey('patient_profiles.id', ondelete='CASCADE'), nullable=False)
    scan_number = Column(String(50), unique=True, nullable=False, index=True)
    
    # Clinical Information
    examination_type = Column(SQLEnum(ExaminationType), nullable=False)
    body_region = Column(SQLEnum(BodyRegion), nullable=False)
    urgency_level = Column(SQLEnum(UrgencyLevel), default=UrgencyLevel.routine)
    presenting_symptoms = Column(ARRAY(Text))
    current_medications = Column(ARRAY(Text))
    previous_surgeries = Column(ARRAY(Text))
    
    # Scan Details
    scan_date = Column(DateTime(timezone=True), server_default=func.now())
    imaging_facility = Column(String(200))
    referring_physician = Column(String(200))
    clinical_notes = Column(Text)
    
    # Workflow Status
    status = Column(SQLEnum(ScanStatus), default=ScanStatus.pending, index=True)
    assigned_radiologist_id = Column(UUID(as_uuid=True), ForeignKey('radiologist_profiles.id'))
    
    # GCS Sync Status (for MLOps integration)
    synced_to_gcs = Column(Boolean, default=False, index=True)
    gcs_sync_date = Column(DateTime(timezone=True))
    gcs_paths = Column(JSONB)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    ai_analysis_started_at = Column(DateTime(timezone=True))
    ai_analysis_completed_at = Column(DateTime(timezone=True))
    radiologist_review_started_at = Column(DateTime(timezone=True))
    radiologist_review_completed_at = Column(DateTime(timezone=True))
    
    def __repr__(self):
        return f"<Scan {self.scan_number}>"
    
    # Helper methods for display
    def get_display_exam_type(self) -> str:
        """Get capitalized exam type for display."""
        display_map = {
            'xray': 'X-ray',
            'ct': 'CT',
            'mri': 'MRI',
            'pet': 'PET',
            'ultrasound': 'Ultrasound'
        }
        return display_map.get(self.examination_type.value, self.examination_type.value)
    
    def get_display_body_region(self) -> str:
        """Get capitalized body region for display."""
        return self.body_region.value.capitalize()
    
    def get_display_urgency(self) -> str:
        """Get capitalized urgency for display."""
        return self.urgency_level.value.capitalize()