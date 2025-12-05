from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from datetime import datetime
from app.core.database import get_db
from app.core.security import require_role
from app.models.user import User
from app.schemas.schemas import (
    ScanResponse, 
    ReportResponse, 
    ReportUpdate,
    FeedbackCreate,
    FeedbackResponse
)
from app.models.radiologist_profile import RadiologistProfile

router = APIRouter()

@router.get("/scans/pending", response_model=List[ScanResponse])
async def get_pending_scans(
    current_user: User = Depends(require_role(["radiologist"])),
    db: Session = Depends(get_db)
):
    """
    Get all pending scans in the queue for review.
    Sorted by urgency and scan date.
    """
    # TODO: Implement actual database query
    # Filter scans with status: pending, in_progress, ai_analyzed
    return []

@router.get("/scans/completed", response_model=List[ScanResponse])
async def get_completed_scans(
    current_user: User = Depends(require_role(["radiologist"])),
    db: Session = Depends(get_db)
):
    """
    Get all completed scans reviewed by this radiologist.
    """
    # TODO: Implement actual database query
    # Filter scans with status: completed
    return []

@router.get("/scans/{scan_id}", response_model=ScanResponse)
async def get_scan_details(
    scan_id: UUID,
    current_user: User = Depends(require_role(["radiologist"])),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific scan including AI predictions.
    """
    # TODO: Implement actual database query
    # Include AI predictions and Grad-CAM outputs
    raise HTTPException(status_code=404, detail="Scan not found")

@router.post("/scans/{scan_id}/analyze")
async def start_ai_analysis(
    scan_id: UUID,
    current_user: User = Depends(require_role(["radiologist"])),
    db: Session = Depends(get_db)
):
    """
    Trigger AI analysis for a specific scan.
    This will run the ML model and generate predictions + Grad-CAM visualizations.
    """
    # TODO: Implement AI analysis workflow
    # 1. Update scan status to 'in_progress'
    # 2. Call ML service to run inference
    # 3. Store predictions and Grad-CAM outputs
    # 4. Generate draft report
    # 5. Update scan status to 'ai_analyzed'
    return {
        "message": "AI analysis started",
        "scan_id": str(scan_id),
        "status": "processing"
    }

@router.post("/scans/{scan_id}/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    scan_id: UUID,
    feedback: FeedbackCreate,
    current_user: User = Depends(require_role(["radiologist"])),
    db: Session = Depends(get_db)
):
    """
    Submit radiologist feedback for a scan.
    This feedback is used for model retraining.
    """
    # TODO: Implement feedback storage
    # 1. Get AI prediction for this scan
    # 2. Store radiologist feedback
    # 3. Add to training data queue
    # 4. Update scan status
    return FeedbackResponse(
        id=UUID("00000000-0000-0000-0000-000000000000"),
        feedback_type=feedback.feedback_type,
        ai_diagnosis="placeholder",
        radiologist_diagnosis=feedback.radiologist_diagnosis,
        feedback_timestamp=datetime.utcnow()
    )

@router.put("/reports/{report_id}", response_model=ReportResponse)
async def update_report(
    report_id: UUID,
    report_data: ReportUpdate,
    current_user: User = Depends(require_role(["radiologist"])),
    db: Session = Depends(get_db)
):
    """
    Update a report (edit AI-generated content).
    """
    # TODO: Implement report update
    # 1. Verify report exists and belongs to this radiologist
    # 2. Update report fields
    # 3. Store edit history
    # 4. Increment version number
    raise HTTPException(status_code=404, detail="Report not found")

@router.post("/reports/{report_id}/publish")
async def publish_report(
    report_id: UUID,
    current_user: User = Depends(require_role(["radiologist"])),
    db: Session = Depends(get_db)
):
    """
    Publish a report to make it visible to the patient.
    """
    # TODO: Implement report publication
    # 1. Update report status to 'published'
    # 2. Create report_publication record
    # 3. Send notification to patient
    # 4. Update scan status to 'completed'
    return {
        "message": "Report published successfully",
        "report_id": str(report_id)
    }

@router.post("/reports/{report_id}/unpublish")
async def unpublish_report(
    report_id: UUID,
    current_user: User = Depends(require_role(["radiologist"])),
    db: Session = Depends(get_db)
):
    """
    Unpublish a report (hide from patient).
    """
    # TODO: Implement report unpublication
    # 1. Update report_publication record
    # 2. Set unpublished_at timestamp
    # 3. Send notification to relevant parties
    return {
        "message": "Report unpublished successfully",
        "report_id": str(report_id)
    }

@router.get("/profile")
async def get_radiologist_profile(
    current_user: User = Depends(require_role(["radiologist"])),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive radiologist profile information.
    """
    # Query radiologist_profiles table
    radiologist_profile = db.query(RadiologistProfile).filter(
        RadiologistProfile.user_id == current_user.id
    ).first()
    
    if not radiologist_profile:
        raise HTTPException(status_code=404, detail="Radiologist profile not found")
    
    return {
        # User account data
        "user_id": str(current_user.id),
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "email": current_user.email,
        "phone": current_user.phone,
        
        # Radiologist profile data from radiologist_profiles table
        "license_number": radiologist_profile.license_number,
        "specialization": radiologist_profile.specialization,
        "years_of_experience": radiologist_profile.years_of_experience,
        "institution": radiologist_profile.institution,
    }