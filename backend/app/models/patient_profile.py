from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.sql import func
import uuid
from app.core.database import Base

class PatientProfile(Base):
    __tablename__ = "patient_profiles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    patient_id = Column(String(50), unique=True, nullable=False, index=True)
    
    # Demographics
    age_years = Column(Integer)
    weight_kg = Column(Numeric(5, 2))
    height_cm = Column(Numeric(5, 2))
    gender = Column(String(50))
    
    # Contact
    address = Column(Text)
    emergency_contact_name = Column(String(200))
    emergency_contact_phone = Column(String(20))
    
    # Medical
    blood_type = Column(String(5))
    allergies = Column(ARRAY(Text))
    medical_history = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<PatientProfile {self.patient_id}>"