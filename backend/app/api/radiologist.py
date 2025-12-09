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
        
        # Get images and convert to signed URLs
        images_result = db.execute(text("""
            SELECT image_path, file_size_bytes, image_format, image_order
            FROM scan_images
            WHERE scan_id = :scan_id
            ORDER BY image_order
        """), {"scan_id": str(scan_id)})
        
        images = []
        for img in images_result:
            # Convert gs:// to signed HTTPS URL (1 hour expiration)
            signed_url = gcs_storage.get_signed_url(img.image_path, expiration=3600)
            
            images.append({
                "url": signed_url,
                "gcs_path": img.image_path,
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
# AI ANALYSIS ENDPOINTS
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
        
        model_info = determine_model(scan.examination_type, scan.body_region)
        
        if not model_info:
            raise HTTPException(
                status_code=400,
                detail=f"No model for {scan.examination_type} {scan.body_region}"
            )
        
        scan.status = 'in_progress'
        scan.ai_analysis_started_at = datetime.utcnow()
        db.commit()
        
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


@router.get("/scans/{scan_id}/ai-results")
async def get_ai_results(
    scan_id: UUID,
    current_user: User = Depends(require_role(["radiologist"])),
    db: Session = Depends(get_db)
):
    """Get AI prediction results for a scan."""
    try:
        from app.services.gcs_storage import gcs_storage
        
        # Get latest AI prediction
        result = db.execute(text("""
            SELECT 
                id, predicted_class, confidence_score, class_probabilities,
                inference_timestamp, model_name
            FROM ai_predictions
            WHERE scan_id = :scan_id
            ORDER BY inference_timestamp DESC
            LIMIT 1
        """), {"scan_id": str(scan_id)})
        
        prediction = result.fetchone()
        
        if not prediction:
            raise HTTPException(status_code=404, detail="No AI results available yet")
        
        # Get GradCAM if available
        gradcam_result = db.execute(text("""
            SELECT overlay_url
            FROM gradcam_outputs
            WHERE scan_id = :scan_id
            ORDER BY created_at DESC
            LIMIT 1
        """), {"scan_id": str(scan_id)})
        
        gradcam = gradcam_result.fetchone()
        gradcam_url = None
        
        if gradcam and gradcam.overlay_url:
            # Convert to signed URL
            gradcam_url = gcs_storage.get_signed_url(gradcam.overlay_url, expiration=3600)
        
        # Get original scan image
        image_result = db.execute(text("""
            SELECT image_path
            FROM scan_images
            WHERE scan_id = :scan_id
            ORDER BY image_order
            LIMIT 1
        """), {"scan_id": str(scan_id)})
        
        image = image_result.fetchone()
        original_image_url = None
        
        if image:
            original_image_url = gcs_storage.get_signed_url(image.image_path, expiration=3600)
        
        # Parse class_probabilities (stored as string)
        import json
        try:
            probs = json.loads(prediction.class_probabilities) if isinstance(prediction.class_probabilities, str) else prediction.class_probabilities
        except:
            probs = {}
        
        return {
            "prediction_id": str(prediction.id),
            "predicted_class": prediction.predicted_class,
            "confidence_score": float(prediction.confidence_score),
            "class_probabilities": probs,
            "model_name": prediction.model_name,
            "inference_timestamp": prediction.inference_timestamp.isoformat(),
            "gradcam_url": gradcam_url,
            "original_image_url": original_image_url
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get AI results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scans/{scan_id}/draft-report")
async def get_draft_report(
    scan_id: UUID,
    current_user: User = Depends(require_role(["radiologist"])),
    db: Session = Depends(get_db)
):
    """Get draft report (AI-generated or create from template)."""
    try:
        # Check if report already exists
        result = db.execute(text("""
            SELECT 
                r.id, r.report_number, r.report_title, r.clinical_indication,
                r.technique, r.findings, r.impression, r.recommendations,
                r.report_status, s.scan_number,
                u.first_name || ' ' || u.last_name as patient_name
            FROM reports r
            JOIN scans s ON r.scan_id = s.id
            JOIN patient_profiles pp ON s.patient_id = pp.id
            JOIN users u ON pp.user_id = u.id
            WHERE r.scan_id = :scan_id
            ORDER BY r.created_at DESC
            LIMIT 1
        """), {"scan_id": str(scan_id)})
        
        report = result.fetchone()
        
        if report:
            # Return existing report
            return {
                "id": str(report.id),
                "report_number": report.report_number,
                "report_title": report.report_title,
                "clinical_indication": report.clinical_indication,
                "technique": report.technique,
                "findings": report.findings,
                "impression": report.impression,
                "recommendations": report.recommendations,
                "report_status": report.report_status,
                "scan_number": report.scan_number,
                "patient_name": report.patient_name
            }
        
        # No report exists - create template based on AI prediction
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            raise HTTPException(status_code=404, detail="Scan not found")
        
        # Get AI prediction
        ai_result = db.execute(text("""
            SELECT predicted_class, confidence_score
            FROM ai_predictions
            WHERE scan_id = :scan_id
            ORDER BY inference_timestamp DESC
            LIMIT 1
        """), {"scan_id": str(scan_id)})
        
        ai_prediction = ai_result.fetchone()
        
        # Get patient info
        patient_result = db.execute(text("""
            SELECT u.first_name || ' ' || u.last_name as patient_name, s.scan_number
            FROM scans s
            JOIN patient_profiles pp ON s.patient_id = pp.id
            JOIN users u ON pp.user_id = u.id
            WHERE s.id = :scan_id
        """), {"scan_id": str(scan_id)})
        
        patient = patient_result.fetchone()
        
        # Generate template report
        if ai_prediction:
            predicted_class = ai_prediction.predicted_class
            confidence = float(ai_prediction.confidence_score)
        else:
            predicted_class = "Unknown"
            confidence = 0.0
        
        # Create report template based on prediction
        report_template = generate_report_template(
            scan=scan,
            predicted_class=predicted_class,
            confidence=confidence
        )
        
        # Create new report in database
        report_id = str(uuid.uuid4())
        report_number = f"RPT-{scan.scan_number}"
        
        db.execute(text("""
            INSERT INTO reports (
                id, scan_id, report_number, report_type, report_status,
                report_title, clinical_indication, technique,
                findings, impression, recommendations,
                created_at, updated_at
            ) VALUES (
                :id, :scan_id, :report_number, 'preliminary_ai', 'draft',
                :title, :indication, :technique,
                :findings, :impression, :recommendations,
                NOW(), NOW()
            )
        """), {
            'id': report_id,
            'scan_id': str(scan_id),
            'report_number': report_number,
            'title': report_template['title'],
            'indication': report_template['indication'],
            'technique': report_template['technique'],
            'findings': report_template['findings'],
            'impression': report_template['impression'],
            'recommendations': report_template['recommendations']
        })
        
        db.commit()
        
        return {
            "id": report_id,
            "report_number": report_number,
            "report_title": report_template['title'],
            "clinical_indication": report_template['indication'],
            "technique": report_template['technique'],
            "findings": report_template['findings'],
            "impression": report_template['impression'],
            "recommendations": report_template['recommendations'],
            "report_status": "draft",
            "scan_number": patient.scan_number,
            "patient_name": patient.patient_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get draft report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def generate_report_template(scan: Scan, predicted_class: str, confidence: float) -> dict:
    """Generate report template based on AI prediction."""
    
    exam_type = str(scan.examination_type)
    
    if predicted_class == "Tuberculosis":
        return {
            "title": f"{exam_type} Report - Chest",
            "indication": "Evaluation for tuberculosis",
            "technique": f"Chest {exam_type} PA and lateral views obtained",
            "findings": f"AI-assisted analysis suggests findings consistent with active pulmonary tuberculosis (confidence: {confidence*100:.1f}%). Bilateral upper lobe infiltrates noted with features suggestive of cavitation. Hilar lymphadenopathy observed. Image quality is adequate for diagnostic interpretation.",
            "impression": "Findings consistent with active pulmonary tuberculosis. Recommend sputum culture and clinical correlation.",
            "recommendations": "1. Sputum culture for Mycobacterium tuberculosis\n2. Initiate respiratory isolation if clinically indicated\n3. Clinical correlation with symptom history\n4. Consider TB treatment protocol if culture positive\n5. Contact tracing if diagnosis confirmed"
        }
    
    elif predicted_class in ["adenocarcinoma", "squamous_cell_carcinoma", "large_cell_carcinoma"]:
        return {
            "title": f"{exam_type} Report - Chest",
            "indication": "Evaluation for lung pathology",
            "technique": f"Chest {exam_type} with standard protocol",
            "findings": f"AI-assisted analysis suggests {predicted_class.replace('_', ' ')} (confidence: {confidence*100:.1f}%). Mass lesion identified in lung parenchyma requiring further characterization. Image quality is adequate for evaluation.",
            "impression": f"Findings suspicious for {predicted_class.replace('_', ' ')}. Recommend tissue sampling and oncology consultation.",
            "recommendations": "1. CT chest with contrast for better characterization\n2. PET-CT for staging evaluation\n3. Tissue biopsy for histological confirmation\n4. Oncology consultation\n5. Molecular testing if malignancy confirmed"
        }
    
    else:  # Normal or other
        return {
            "title": f"{exam_type} Report - Chest",
            "indication": "Routine chest imaging",
            "technique": f"Chest {exam_type} obtained",
            "findings": f"AI-assisted analysis suggests no acute abnormality (confidence: {confidence*100:.1f}%). Lungs are clear bilaterally. No focal consolidation, mass, or nodule identified. Cardiac silhouette is normal. No pleural effusion or pneumothorax. Image quality is adequate for diagnostic interpretation.",
            "impression": "No acute cardiopulmonary abnormality detected.",
            "recommendations": "Continue routine care. No immediate follow-up required based on imaging."
        }


def determine_model(exam_type, body_region):
    """Determine model - handles capitalized enum values from database."""
    from app.models.scan import ExaminationType, BodyRegion
    
    # Get string values
    if hasattr(exam_type, 'value'):
        exam_val = exam_type.value
    else:
        exam_val = str(exam_type)
    
    if hasattr(body_region, 'value'):
        body_val = body_region.value  
    else:
        body_val = str(body_region)
    
    # X-ray (capitalized) + Chest → TB Model
    if exam_val == 'X-ray' and body_val == 'Chest':
        return {'type': 'tb', 'name': 'TB Detection Model'}
    
    # CT (capitalized) + Chest → Lung Cancer Model
    elif exam_val == 'CT' and body_val == 'Chest':
        return {'type': 'lung_cancer', 'name': 'Lung Cancer Model'}
    
    return None


def run_ai_analysis_workflow(scan_id: str, model_type: str):
    """Background task: Run ML model."""
    from app.core.database import SessionLocal
    from app.services.gcs_storage import gcs_storage
    from app.services.ml_model_service import ml_model_service
    import uuid
    
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
                :id, :scan_id, :model, :version,
                :class, :confidence, :probs, NOW()
            )
        """), {
            'id': str(uuid.uuid4()),
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
                    :id, :scan_id, :url, :url, :class, NOW()
                )
            """), {
                'id': str(uuid.uuid4()),
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
# REPORT ENDPOINTS
# ============================================================================

@router.put("/reports/{report_id}")
async def update_report(
    report_id: UUID,
    report_data: ReportUpdate,
    current_user: User = Depends(require_role(["radiologist"])),
    db: Session = Depends(get_db)
):
    """Update report."""
    try:
        # Build update query dynamically
        updates = []
        params = {'report_id': str(report_id)}
        
        if report_data.report_title is not None:
            updates.append("report_title = :title")
            params['title'] = report_data.report_title
        
        if report_data.clinical_indication is not None:
            updates.append("clinical_indication = :indication")
            params['indication'] = report_data.clinical_indication
        
        if report_data.technique is not None:
            updates.append("technique = :technique")
            params['technique'] = report_data.technique
        
        if report_data.findings is not None:
            updates.append("findings = :findings")
            params['findings'] = report_data.findings
        
        if report_data.impression is not None:
            updates.append("impression = :impression")
            params['impression'] = report_data.impression
        
        if report_data.recommendations is not None:
            updates.append("recommendations = :recommendations")
            params['recommendations'] = report_data.recommendations
        
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        updates.append("updated_at = NOW()")
        
        query = f"UPDATE reports SET {', '.join(updates)} WHERE id = :report_id"
        db.execute(text(query), params)
        db.commit()
        
        return {"message": "Report updated successfully", "report_id": str(report_id)}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update report: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reports/{report_id}/publish")
async def publish_report(
    report_id: UUID,
    current_user: User = Depends(require_role(["radiologist"])),
    db: Session = Depends(get_db)
):
    """Publish report to patient."""
    try:
        db.execute(text("""
            UPDATE reports 
            SET report_status = 'published', 
                published_at = NOW(),
                updated_at = NOW()
            WHERE id = :report_id
        """), {"report_id": str(report_id)})
        
        db.commit()
        
        logger.info(f"✓ Report published: {report_id}")
        
        return {"message": "Report published successfully", "report_id": str(report_id)}
        
    except Exception as e:
        logger.error(f"Failed to publish report: {e}")
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