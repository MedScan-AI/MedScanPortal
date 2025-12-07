from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from datetime import datetime
from pathlib import Path
from io import BytesIO
import logging

from app.core.database import get_db
from app.core.security import require_role
from app.models.user import User
from app.models.scan import Scan
from app.models.scan_image import ScanImage
from app.models.patient_profile import PatientProfile
from app.models.radiologist_feedback import RadiologistFeedback
from app.models.radiologist_profile import RadiologistProfile
from app.schemas.schemas import (
    ScanResponse, 
    ReportResponse, 
    ReportUpdate,
    FeedbackCreate,
    FeedbackResponse
)

logger = logging.getLogger(__name__)
router = APIRouter()

# ============================================================================
# SCAN QUEUE ENDPOINTS
# ============================================================================

@router.get("/scans/pending", response_model=List[ScanResponse])
async def get_pending_scans(
    current_user: User = Depends(require_role(["radiologist"])),
    db: Session = Depends(get_db)
):
    """Get all pending scans."""
    return []

@router.get("/scans/completed", response_model=List[ScanResponse])
async def get_completed_scans(
    current_user: User = Depends(require_role(["radiologist"])),
    db: Session = Depends(get_db)
):
    """Get completed scans."""
    return []

@router.get("/scans/{scan_id}", response_model=ScanResponse)
async def get_scan_details(
    scan_id: UUID,
    current_user: User = Depends(require_role(["radiologist"])),
    db: Session = Depends(get_db)
):
    """Get scan details."""
    raise HTTPException(status_code=404, detail="Scan not found")

# ============================================================================
# IMAGE UPLOAD ENDPOINT
# ============================================================================

@router.post("/scans/{scan_id}/upload-image")
async def upload_scan_image(
    scan_id: UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(require_role(["radiologist"])),
    db: Session = Depends(get_db)
):
    """
    Upload scan image to GCS.
    """
    try:
        from app.services.gcs_storage import gcs_storage
        
        # Verify scan exists
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            raise HTTPException(status_code=404, detail="Scan not found")
        
        # Get patient
        patient = db.query(PatientProfile).filter(
            PatientProfile.id == scan.patient_id
        ).first()
        
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        # Read file
        file_content = await file.read()
        file_data = BytesIO(file_content)
        
        # Upload to GCS
        gcs_url = gcs_storage.upload_scan_image(
            file_data=file_data,
            patient_id=patient.patient_id,
            scan_id=str(scan_id),
            filename=file.filename or "scan.jpg",
            content_type=file.content_type or 'image/jpeg'
        )
        
        # Save to database
        scan_image = ScanImage(
            scan_id=scan_id,
            image_url=gcs_url,
            file_size_bytes=len(file_content),
            image_format=Path(file.filename).suffix.lstrip('.') if file.filename else 'jpg',
            image_order=db.query(ScanImage).filter(ScanImage.scan_id == scan_id).count() + 1
        )
        db.add(scan_image)
        db.commit()
        
        return {
            "message": "Image uploaded successfully",
            "image_url": gcs_url,
            "scan_id": str(scan_id)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# FEEDBACK ENDPOINT (WITH REAL-TIME SYNC)
# ============================================================================

@router.post("/scans/{scan_id}/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    scan_id: UUID,
    feedback: FeedbackCreate,
    background_tasks: BackgroundTasks,  # ← Correctly placed as parameter
    current_user: User = Depends(require_role(["radiologist"])),
    db: Session = Depends(get_db)
):
    """
    Submit radiologist feedback with diagnosis.
    ✨ Automatically syncs to MLOps pipeline in real-time!
    """
    try:
        # Get scan
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            raise HTTPException(status_code=404, detail="Scan not found")
        
        # Get radiologist profile
        radiologist = db.query(RadiologistProfile).filter(
            RadiologistProfile.user_id == current_user.id
        ).first()
        
        if not radiologist:
            raise HTTPException(status_code=404, detail="Radiologist profile not found")
        
        # Create feedback record
        feedback_record = RadiologistFeedback(
            scan_id=scan_id,
            radiologist_id=radiologist.id,
            feedback_type=feedback.feedback_type,
            ai_diagnosis=getattr(feedback, 'ai_diagnosis', None),
            radiologist_diagnosis=feedback.radiologist_diagnosis,
            clinical_notes=feedback.clinical_notes,
            disagreement_reason=feedback.disagreement_reason,
            additional_findings=feedback.additional_findings,
            radiologist_confidence=feedback.radiologist_confidence,
            image_quality_rating=feedback.image_quality_rating
        )
        
        db.add(feedback_record)
        
        # Update scan status
        scan.status = 'completed'
        scan.radiologist_review_completed_at = datetime.utcnow()
        
        db.commit()
        db.refresh(feedback_record)
        
        logger.info(f"✓ Diagnosis: {scan.scan_number} → {feedback.radiologist_diagnosis}")
        
        # REAL-TIME SYNC (background task - non-blocking!)
        from app.services.mlops_sync import sync_scan_to_mlops
        
        background_tasks.add_task(
            sync_scan_to_mlops,
            scan_id=str(scan_id),
            diagnosis=str(feedback.radiologist_diagnosis),
            db=db
        )
        
        return FeedbackResponse(
            id=feedback_record.id,
            feedback_type=str(feedback_record.feedback_type),
            ai_diagnosis=feedback_record.ai_diagnosis or "N/A",
            radiologist_diagnosis=str(feedback_record.radiologist_diagnosis),
            feedback_timestamp=feedback_record.feedback_timestamp
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Feedback failed: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# AI ANALYSIS
# ============================================================================

@router.post("/scans/{scan_id}/analyze")
async def start_ai_analysis(
    scan_id: UUID,
    current_user: User = Depends(require_role(["radiologist"])),
    db: Session = Depends(get_db)
):
    """Trigger AI analysis."""
    return {
        "message": "AI analysis started",
        "scan_id": str(scan_id),
        "status": "processing"
    }

# ============================================================================
# REPORT ENDPOINTS
# ============================================================================

@router.put("/reports/{report_id}", response_model=ReportResponse)
async def update_report(
    report_id: UUID,
    report_data: ReportUpdate,
    current_user: User = Depends(require_role(["radiologist"])),
    db: Session = Depends(get_db)
):
    """Update report."""
    raise HTTPException(status_code=404, detail="Report not found")

@router.post("/reports/{report_id}/publish")
async def publish_report(
    report_id: UUID,
    current_user: User = Depends(require_role(["radiologist"])),
    db: Session = Depends(get_db)
):
    """Publish report."""
    return {"message": "Report published", "report_id": str(report_id)}

@router.post("/reports/{report_id}/unpublish")
async def unpublish_report(
    report_id: UUID,
    current_user: User = Depends(require_role(["radiologist"])),
    db: Session = Depends(get_db)
):
    """Unpublish report."""
    return {"message": "Report unpublished", "report_id": str(report_id)}

# ============================================================================
# PROFILE
# ============================================================================

@router.get("/profile")
async def get_radiologist_profile(
    current_user: User = Depends(require_role(["radiologist"])),
    db: Session = Depends(get_db)
):
    """Get radiologist profile."""
    radiologist_profile = db.query(RadiologistProfile).filter(
        RadiologistProfile.user_id == current_user.id
    ).first()
    
    if not radiologist_profile:
        raise HTTPException(status_code=404, detail="Radiologist profile not found")
    
    return {
        "user_id": str(current_user.id),
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "email": current_user.email,
        "phone": current_user.phone,
        "license_number": radiologist_profile.license_number,
        "specialization": radiologist_profile.specialization,
        "years_of_experience": radiologist_profile.years_of_experience,
        "institution": radiologist_profile.institution,
    }