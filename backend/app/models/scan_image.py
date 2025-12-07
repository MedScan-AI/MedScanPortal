from sqlalchemy import Column, String, Integer, BigInteger, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
from app.core.database import Base

class ScanImage(Base):
    __tablename__ = "scan_images"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey('scans.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Storage paths
    image_url = Column(Text, nullable=False)  # GCS URL: gs://medscan-data/platform/raw_scans/...
    gcs_path = Column(Text)                    # MLOps GCS path: gs://medscan-data/vision/raw/tb/...
    
    # Image metadata
    image_order = Column(Integer, default=1)
    file_size_bytes = Column(BigInteger)
    image_width = Column(Integer)
    image_height = Column(Integer)
    image_format = Column(String(10))
    
    # DICOM metadata
    dicom_metadata = Column(JSONB)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<ScanImage {self.id} - Order {self.image_order}>"