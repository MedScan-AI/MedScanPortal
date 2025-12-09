from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from uuid import UUID
from datetime import datetime
from pathlib import Path
from io import BytesIO
import logging

from app.core.database import get_db
from app.core.security import require_role
from app.models.user import User
from app.models.scan import Scan, ExaminationType, BodyRegion
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

@router.get("/scans/pending")
async def get_pending_scans(
    current_user: User = Depends(require_role(["radiologist"])),
    db: Session = Depends(get_db)
):
    """Get all pending scans."""
    try:
        result = db.execute(text("""
            SELECT 
                s.id, s.scan_number, s.examination_type, s.body_region,
                s.urgency_level, s.status, s.scan_date, s.created_at,
                s.presenting_symptoms, s.current_medications, s.previous_surgeries,
                pp.patient_id,
                u.first_name || ' ' || u.last_name as patient_name
            FROM scans s
            JOIN patient_profiles pp ON s.patient_id = pp.id
            JOIN users u ON pp.user_id = u.id
            WHERE s.status IN ('pending', 'in_progress', 'ai_analyzed')
            ORDER BY 
                CASE s.urgency_level 
                    WHEN 'Emergent' THEN 1
                    WHEN 'Urgent' THEN 2
                    ELSE 3
                END,
                s.created_at DESC
        """))
        
        scans = []
        for row in result:
            scans.append({
                "id": str(row.id),
                "scan_number": row.scan_number,
                "patient_name": row.patient_name,
                "patient_id": row.patient_id,
                "examination_type": row.examination_type,
                "body_region": row.body_region,
                "urgency_level": row.urgency_level,
                "status": row.status,
                "scan_date": row.scan_date.isoformat(),
                "created_at": row.created_at.isoformat(),
                "presenting_symptoms": row.presenting_symptoms or [],
                "current_medications": row.current_medications or [],
                "previous_surgeries": row.previous_surgeries or []
            })
        
        logger.info(f"Retrieved {len(scans)} pending scans")
        return scans
        
    except Exception as e:
        logger.error(f"Failed to get pending scans: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scans/completed")
async def get_completed_scans(
    current_user: User = Depends(require_role(["radiologist"])),
    db: Session = Depends(get_db)
):
    """Get completed scans."""
    try:
        result = db.execute(text("""
            SELECT 
                s.id, s.scan_number, s.examination_type, s.body_region,
                s.urgency_level, s.status, s.scan_date, s.created_at,
                s.presenting_symptoms, s.current_medications, s.previous_surgeries,
                pp.patient_id,
                u.first_name || ' ' || u.last_name as patient_name
            FROM scans s
            JOIN patient_profiles pp ON s.patient_id = pp.id
            JOIN users u ON pp.user_id = u.id
            WHERE s.status = 'completed'
            ORDER BY s.radiologist_review_completed_at DESC
        """))
        
        scans = []
        for row in result:
            scans.append({
                "id": str(row.id),
                "scan_number": row.scan_number,
                "patient_name": row.patient_name,
                "patient_id": row.patient_id,
                "examination_type": row.examination_type,
                "body_region": row.body_region,
                "urgency_level": row.urgency_level,
                "status": row.status,
                "scan_date": row.scan_date.isoformat(),
                "created_at": row.created_at.isoformat(),
                "presenting_symptoms": row.presenting_symptoms or [],
                "current_medications": row.current_medications or [],
                "previous_surgeries": row.previous_surgeries or []
            })
        
        return scans
        
    except Exception as e:
        logger.error(f"Failed to get completed scans: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scans/{scan_id}")
async def get_scan_details(
    scan_id: UUID,
    current_user: User = Depends(require_role(["radiologist"])),
    db: Session = Depends(get_db)
):
    """Get detailed scan info with signed image URLs."""
    try:
        from app.services.gcs_storage import gcs_storage
        
        result = db.execute(text("""
            SELECT 
                s.*, pp.patient_id, pp.age_years, pp.weight_kg, pp.height_cm,
                pp.gender, pp.blood_type, pp.allergies,
                u.first_name || ' ' || u.last_name as patient_name
            FROM scans s
            JOIN patient_profiles pp ON s.patient_id = pp.id
            JOIN users u ON pp.user_id = u.id
            WHERE s.id = :scan_id
        """), {"scan_id": str(scan_id)})
        
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Scan not found")
        
        # Get images and convert GCS URLs to signed URLs
        images_result = db.execute(text("""
            SELECT image_path, file_size_bytes, image_format, image_order
            FROM scan_images
            WHERE scan_id = :scan_id
            ORDER BY image_order
        """), {"scan_id": str(scan_id)})
        
        images = []
        for img in images_result:
            # Convert gs:// URL to signed HTTPS URL
            signed_url = gcs_storage.get_signed_url(img.image_path, expiration=3600)  # 1 hour
            
            images.append({
                "url": signed_url,  # ← HTTPS URL that browser can load
                "gcs_path": img.image_path,  # Keep original for reference
                "size": img.file_size_bytes,
                "format": img.image_format,
                "order": img.image_order
            })
        
        return {
            "id": str(row.id),
            "scan_number": row.scan_number,
            "patient_name": row.patient_name,
            "patient_id": row.patient_id,
            "age_years": row.age_years,
            "examination_type": row.examination_type,
            "body_region": row.body_region,
            "urgency_level": row.urgency_level,
            "status": row.status,
            "scan_date": row.scan_date.isoformat(),
            "presenting_symptoms": row.presenting_symptoms or [],
            "current_medications": row.current_medications or [],
            "previous_surgeries": row.previous_surgeries or [],
            "clinical_notes": row.clinical_notes,
            "images": images
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get scan: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# AI ANALYSIS
# ============================================================================

@router.post("/scans/{scan_id}/analyze")
async def start_ai_analysis(
    scan_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_role(["radiologist"])),
    db: Session = Depends(get_db)
):
    """Start AI analysis."""
    try:
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            raise HTTPException(status_code=404, detail="Scan not found")
        
        # Determine model
        model_info = determine_model(scan.examination_type, scan.body_region)
        
        if not model_info:
            raise HTTPException(
                status_code=400,
                detail=f"No model for {scan.examination_type.value} {scan.body_region.value}"
            )
        
        # Update status
        scan.status = 'in_progress'
        scan.ai_analysis_started_at = datetime.utcnow()
        db.commit()
        
        # Run in background
        background_tasks.add_task(
            run_ai_analysis_workflow,
            scan_id=str(scan_id),
            model_type=model_info['type']
        )
        
        logger.info(f"✓ Starting {model_info['name']} for {scan.scan_number}")
        
        return {
            "message": "AI analysis started",
            "scan_id": str(scan_id),
            "model": model_info['name'],
            "status": "processing"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def determine_model(exam_type, body_region):
    """Determine model."""
    if exam_type == ExaminationType.xray and body_region == BodyRegion.chest:
        return {'type': 'tb', 'name': 'TB Detection Model'}
    elif exam_type == ExaminationType.ct and body_region == BodyRegion.chest:
        return {'type': 'lung_cancer', 'name': 'Lung Cancer Model'}
    return None


def run_ai_analysis_workflow(scan_id: str, model_type: str):
    """Background task: Run ML model."""
    from app.core.database import SessionLocal
    from app.services.gcs_storage import gcs_storage
    from app.services.ml_model_service import ml_model_service
    
    db = SessionLocal()
    
    try:
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            return
        
        scan_image = db.query(ScanImage).filter(
            ScanImage.scan_id == scan_id,
            ScanImage.image_order == 1
        ).first()
        
        if not scan_image:
            logger.error(f"No image for {scan_id}")
            scan.status = 'pending'
            db.commit()
            return
        
        logger.info(f"Downloading image from GCS...")
        image_data = gcs_storage.download_image(scan_image.image_path)
        
        # Call ML model
        if model_type == 'tb':
            prediction, gradcam_image = ml_model_service.predict_tb(image_data)
        elif model_type == 'lung_cancer':
            prediction, gradcam_image = ml_model_service.predict_lung_cancer(image_data)
        else:
            raise Exception(f"Unknown model: {model_type}")
        
        # Save prediction
        db.execute(text("""
            INSERT INTO ai_predictions (
                id, scan_id, model_name, model_version,
                predicted_class, confidence_score, class_probabilities,
                inference_timestamp
            ) VALUES (
                gen_random_uuid(), :scan_id, :model, :version,
                :class, :confidence, :probs, NOW()
            )
        """), {
            'scan_id': scan_id,
            'model': f'{model_type.upper()}-ResNet50',
            'version': 'v1.0',
            'class': prediction['predicted_class'],
            'confidence': prediction['confidence'],
            'probs': str(prediction['class_probabilities'])
        })
        
        # Upload GradCAM if available
        if gradcam_image:
            patient = db.query(PatientProfile).filter(
                PatientProfile.id == scan.patient_id
            ).first()
            
            logger.info("Uploading GradCAM...")
            gradcam_url = gcs_storage.upload_scan_image(
                file_data=gradcam_image,
                patient_id=patient.patient_id,
                scan_id=scan_id,
                filename="gradcam_overlay.jpg"
            )
            
            db.execute(text("""
                INSERT INTO gradcam_outputs (
                    id, scan_id, heatmap_url, overlay_url, 
                    target_class, created_at
                ) VALUES (
                    gen_random_uuid(), :scan_id, :url, :url,
                    :class, NOW()
                )
            """), {
                'scan_id': scan_id,
                'url': gradcam_url,
                'class': prediction['predicted_class']
            })
        
        # Update scan
        scan.status = 'ai_analyzed'
        scan.ai_analysis_completed_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"✓ Complete: {scan.scan_number} → {prediction['predicted_class']}")
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        scan.status = 'pending'
        db.commit()
    finally:
        db.close()

# ============================================================================
# FEEDBACK
# ============================================================================

@router.post("/scans/{scan_id}/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    scan_id: UUID,
    feedback: FeedbackCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_role(["radiologist"])),
    db: Session = Depends(get_db)
):
    """Submit diagnosis."""
    try:
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            raise HTTPException(status_code=404, detail="Scan not found")
        
        radiologist = db.query(RadiologistProfile).filter(
            RadiologistProfile.user_id == current_user.id
        ).first()
        
        if not radiologist:
            raise HTTPException(status_code=404, detail="Radiologist profile not found")
        
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
        scan.status = 'completed'
        scan.radiologist_review_completed_at = datetime.utcnow()
        db.commit()
        db.refresh(feedback_record)
        
        logger.info(f"✓ Diagnosis: {scan.scan_number} → {feedback.radiologist_diagnosis}")
        
        # Sync to MLOps
        try:
            from app.services.mlops_sync import sync_scan_to_mlops
            background_tasks.add_task(
                sync_scan_to_mlops,
                scan_id=str(scan_id),
                diagnosis=str(feedback.radiologist_diagnosis),
                db=db
            )
        except ImportError:
            logger.warning("MLOps sync not available")
        
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