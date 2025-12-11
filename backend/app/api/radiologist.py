"""
Radiologist API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text
from uuid import UUID
from datetime import datetime
import logging
import uuid as uuid_lib

from app.core.database import get_db
from app.core.security import require_role
from app.models.user import User
from app.models.scan import Scan
from app.models.scan_image import ScanImage
from app.models.patient_profile import PatientProfile
from app.models.radiologist_feedback import RadiologistFeedback
from app.models.radiologist_profile import RadiologistProfile
from app.schemas.schemas import (
    ReportUpdate,
    FeedbackCreate,
    FeedbackResponse
)

# Import report generation helper
from app.services.report_templates import (
    generate_report_template,
    capitalize_for_display
)

logger = logging.getLogger(__name__)
router = APIRouter()


def normalize_diagnosis(ml_prediction: str) -> str:
    """
    Normalize ML model prediction to LOWERCASE diagnosis_class enum.
    
    Database values: 'normal', 'tuberculosis', 'lung_cancer', 
                    'other_abnormality', 'inconclusive'
    """
    pred_lower = ml_prediction.lower()
    
    # Normal cases
    if pred_lower in ['normal', 'no finding', 'negative']:
        return 'normal'
    
    # TB cases
    elif pred_lower in ['tuberculosis', 'tb', 'positive']:
        return 'tuberculosis'
    
    # Lung cancer cases  
    elif pred_lower in ['adenocarcinoma', 'squamous_cell_carcinoma', 'squamous_cell',
                        'large_cell_carcinoma', 'large_cell', 'lung_cancer', 'malignant',
                        'benign']:
        return 'lung_cancer'
    
    # Inconclusive
    elif pred_lower in ['inconclusive', 'uncertain', 'unknown']:
        return 'inconclusive'
    
    # Other abnormality
    else:
        return 'other_abnormality'


def capitalize_diagnosis_for_display(diagnosis: str) -> str:
    """Capitalize diagnosis for display in UI."""
    display_map = {
        'normal': 'Normal',
        'tuberculosis': 'Tuberculosis',
        'lung_cancer': 'Lung Cancer',
        'other_abnormality': 'Other Abnormality',
        'inconclusive': 'Inconclusive'
    }
    return display_map.get(diagnosis, diagnosis.replace('_', ' ').title())


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
                    WHEN 'emergent' THEN 1
                    WHEN 'urgent' THEN 2
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
                "examination_type": capitalize_for_display(row.examination_type, 'examination_type'),
                "body_region": capitalize_for_display(row.body_region, 'body_region'),
                "urgency_level": capitalize_for_display(row.urgency_level, 'urgency_level'),
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
    """Get completed scans with report status."""
    try:
        result = db.execute(text("""
            SELECT 
                s.id, s.scan_number, s.examination_type, s.body_region,
                s.urgency_level, s.status, s.scan_date, s.created_at,
                s.presenting_symptoms, s.current_medications, s.previous_surgeries,
                pp.patient_id,
                u.first_name || ' ' || u.last_name as patient_name,
                r.report_status
            FROM scans s
            JOIN patient_profiles pp ON s.patient_id = pp.id
            JOIN users u ON pp.user_id = u.id
            LEFT JOIN reports r ON s.id = r.scan_id
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
                "examination_type": capitalize_for_display(row.examination_type, 'examination_type'),
                "body_region": capitalize_for_display(row.body_region, 'body_region'),
                "urgency_level": capitalize_for_display(row.urgency_level, 'urgency_level'),
                "status": row.status,
                "scan_date": row.scan_date.isoformat(),
                "created_at": row.created_at.isoformat(),
                "presenting_symptoms": row.presenting_symptoms or [],
                "current_medications": row.current_medications or [],
                "previous_surgeries": row.previous_surgeries or [],
                "report_status": row.report_status or "draft"
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
            "examination_type": capitalize_for_display(row.examination_type, 'examination_type'),
            "body_region": capitalize_for_display(row.body_region, 'body_region'),
            "urgency_level": capitalize_for_display(row.urgency_level, 'urgency_level'),
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


# AI ANALYSIS
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
        
        logger.info(f" Starting {model_info['name']} for {scan.scan_number}")
        
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
    """Get AI prediction results."""
    try:
        from app.services.gcs_storage import gcs_storage
        
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
        
        # Get GradCAM
        gradcam_result = db.execute(text("""
            SELECT overlay_url, overlay_path, heatmap_url, heatmap_path
            FROM gradcam_outputs
            WHERE ai_prediction_id = :ai_pred_id
            ORDER BY created_at DESC
            LIMIT 1
        """), {"ai_pred_id": str(prediction.id)})
        
        gradcam = gradcam_result.fetchone()
        gradcam_url = None
        
        if gradcam:
            gcs_path = gradcam.overlay_path or gradcam.overlay_url or gradcam.heatmap_path or gradcam.heatmap_url
            if gcs_path:
                gradcam_url = gcs_storage.get_signed_url(gcs_path, expiration=3600)
        
        # Get original image
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
        
        # Parse class_probabilities
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
    """Get draft report with radiologist information."""
    try:
        # Check if report exists
        result = db.execute(text("""
            SELECT 
                r.id, r.report_number, r.report_title, r.clinical_indication,
                r.technique, r.findings, r.impression, r.recommendations,
                r.report_status, r.created_at, r.published_at,
                s.scan_number,
                u.first_name || ' ' || u.last_name as patient_name,
                rad_u.first_name || ' ' || rad_u.last_name as radiologist_name,
                rad_p.license_number, rad_p.specialization
            FROM reports r
            JOIN scans s ON r.scan_id = s.id
            JOIN patient_profiles pp ON s.patient_id = pp.id
            JOIN users u ON pp.user_id = u.id
            LEFT JOIN radiologist_profiles rad_p ON rad_p.user_id = :radiologist_id
            LEFT JOIN users rad_u ON rad_p.user_id = rad_u.id
            WHERE r.scan_id = :scan_id
            ORDER BY r.created_at DESC
            LIMIT 1
        """), {
            "scan_id": str(scan_id),
            "radiologist_id": str(current_user.id)
        })
        
        report = result.fetchone()
        
        if report:
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
                "patient_name": report.patient_name,
                "radiologist_name": report.radiologist_name or f"Dr. {current_user.first_name} {current_user.last_name}",
                "license_number": report.license_number,
                "specialization": report.specialization,
                "created_at": report.created_at.isoformat(),
                "published_at": report.published_at.isoformat() if report.published_at else None
            }
        
        # Create template report if none exists
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
        
        # Get radiologist info
        radiologist_name = f"Dr. {current_user.first_name} {current_user.last_name}"
        
        if ai_prediction:
            predicted_class = ai_prediction.predicted_class
            confidence = float(ai_prediction.confidence_score)
        else:
            predicted_class = "Unknown"
            confidence = 0.0
        
        # Generate comprehensive report using helper function
        report_template = generate_report_template(
            scan, 
            predicted_class, 
            confidence, 
            radiologist_name
        )
        
        report_id = str(uuid_lib.uuid4())
        report_number = f"RPT-{scan.scan_number}"
        
        # Insert report
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
            "patient_name": patient.patient_name,
            "radiologist_name": radiologist_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get draft report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def determine_model(exam_type, body_region):
    """Determine model."""
    
    if hasattr(exam_type, 'value'):
        exam_val = exam_type.value
    else:
        exam_val = str(exam_type)
    
    if hasattr(body_region, 'value'):
        body_val = body_region.value  
    else:
        body_val = str(body_region)
    
    if exam_val == 'xray' and body_val == 'chest':
        return {'type': 'tb', 'name': 'TB Detection Model'}
    elif exam_val == 'ct' and body_val == 'chest':
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
        
        # Normalize predicted_class
        normalized_class = normalize_diagnosis(prediction['predicted_class'])
        
        # Save prediction
        from psycopg2.extras import Json
        ai_prediction_id = str(uuid_lib.uuid4())
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
            'id': ai_prediction_id,
            'scan_id': scan_id,
            'model': f'{model_type.upper()}-ResNet50',
            'version': 'v1.0',
            'class': normalized_class,
            'confidence': prediction['confidence'],
            'probs': Json(prediction['class_probabilities'])
        })
        
        # Upload GradCAM
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
                    ai_prediction_id, 
                    scan_image_id,
                    heatmap_path,
                    heatmap_url,
                    overlay_path,
                    overlay_url,
                    target_class
                ) VALUES (
                    :ai_pred_id, 
                    :scan_img_id,
                    :path,
                    :url,
                    :path,
                    :url,
                    :target_class
                )
            """), {
                'ai_pred_id': ai_prediction_id,
                'scan_img_id': str(scan_image.id),
                'path': gradcam_url,
                'url': gradcam_url,
                'target_class': normalized_class
            })
        
        # Update scan
        scan.status = 'ai_analyzed'
        scan.ai_analysis_completed_at = datetime.utcnow()
        db.commit()
        
        logger.info(f" Complete: {scan.scan_number} → {normalized_class}")
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        scan.status = 'pending'
        db.commit()
    finally:
        db.close()


# FEEDBACK & REPORTS
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
        
        # Normalize diagnosis
        normalized_diagnosis = normalize_diagnosis(feedback.radiologist_diagnosis)
        
        feedback_record = RadiologistFeedback(
            scan_id=scan_id,
            radiologist_id=radiologist.id,
            feedback_type=feedback.feedback_type,
            ai_diagnosis=getattr(feedback, 'ai_diagnosis', None),
            radiologist_diagnosis=normalized_diagnosis,
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
        
        logger.info(f" Diagnosis: {scan.scan_number} → {normalized_diagnosis}")
        
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


@router.put("/reports/{report_id}")
async def update_report(
    report_id: UUID,
    report_data: ReportUpdate,
    current_user: User = Depends(require_role(["radiologist"])),
    db: Session = Depends(get_db)
):
    """Update report."""
    try:
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
        
        return {"message": "Report updated", "report_id": str(report_id)}
        
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
    """Publish report."""
    try:
        db.execute(text("""
            UPDATE reports 
            SET report_status = 'published', published_at = NOW(), updated_at = NOW()
            WHERE id = :report_id
        """), {"report_id": str(report_id)})
        
        db.commit()
        logger.info(f" Report published: {report_id}")
        
        return {"message": "Report published", "report_id": str(report_id)}
        
    except Exception as e:
        logger.error(f"Failed to publish: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reports/{report_id}/unpublish")
async def unpublish_report(
    report_id: UUID,
    current_user: User = Depends(require_role(["radiologist"])),
    db: Session = Depends(get_db)
):
    """Unpublish report - makes it invisible to patient and editable again."""
    try:
        # Check if report exists
        result = db.execute(text("""
            SELECT id, report_status 
            FROM reports 
            WHERE id = :report_id
        """), {"report_id": str(report_id)})
        
        report = result.fetchone()
        
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        if report.report_status != 'published':
            raise HTTPException(
                status_code=400, 
                detail="Report is not published. Only published reports can be unpublished."
            )
        
        # Update report status to draft
        db.execute(text("""
            UPDATE reports 
            SET report_status = 'draft', 
                published_at = NULL, 
                updated_at = NOW()
            WHERE id = :report_id
        """), {"report_id": str(report_id)})
        
        db.commit()
        logger.info(f" Report unpublished: {report_id}")
        
        return {
            "message": "Report unpublished successfully",
            "report_id": str(report_id),
            "status": "draft"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to unpublish: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


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