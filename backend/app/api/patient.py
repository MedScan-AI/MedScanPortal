from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from uuid import UUID
from app.core.database import get_db
from app.core.security import require_role
from app.models.user import User
from app.models.patient_profile import PatientProfile
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Helper to capitalize for display
def capitalize_for_display(value: str, field_type: str) -> str:
    """Capitalize lowercase enum values for UI display."""
    if field_type == 'examination_type':
        return {'xray': 'X-ray', 'ct': 'CT', 'mri': 'MRI', 'pet': 'PET', 'ultrasound': 'Ultrasound'}.get(value, value)
    elif field_type in ['body_region', 'urgency_level']:
        return value.capitalize()
    return value


@router.get("/scans")
async def get_patient_scans(
    current_user: User = Depends(require_role(["patient"])),
    db: Session = Depends(get_db)
):
    """Get all scans for the current patient."""
    try:
        # Get patient profile
        patient_profile = db.query(PatientProfile).filter(
            PatientProfile.user_id == current_user.id
        ).first()
        
        if not patient_profile:
            return []
        
        # Query scans
        result = db.execute(text("""
            SELECT 
                s.id, s.scan_number, s.examination_type, s.body_region,
                s.urgency_level, s.status, s.scan_date, s.created_at,
                s.presenting_symptoms, s.clinical_notes
            FROM scans s
            WHERE s.patient_id = :patient_id
            ORDER BY s.scan_date DESC
        """), {"patient_id": str(patient_profile.id)})
        
        scans = []
        for row in result:
            scans.append({
                "id": str(row.id),
                "scan_number": row.scan_number,
                "examination_type": capitalize_for_display(row.examination_type, 'examination_type'),
                "body_region": capitalize_for_display(row.body_region, 'body_region'),
                "urgency_level": capitalize_for_display(row.urgency_level, 'urgency_level'),
                "status": row.status,
                "scan_date": row.scan_date.isoformat(),
                "created_at": row.created_at.isoformat(),
                "presenting_symptoms": row.presenting_symptoms or [],
                "clinical_notes": row.clinical_notes
            })
        
        logger.info(f"Retrieved {len(scans)} scans for patient {patient_profile.patient_id}")
        return scans
        
    except Exception as e:
        logger.error(f"Failed to get patient scans: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scans/{scan_id}")
async def get_scan_details(
    scan_id: UUID,
    current_user: User = Depends(require_role(["patient"])),
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific scan."""
    try:
        from app.services.gcs_storage import gcs_storage
        
        # Get patient profile
        patient_profile = db.query(PatientProfile).filter(
            PatientProfile.user_id == current_user.id
        ).first()
        
        if not patient_profile:
            raise HTTPException(status_code=404, detail="Patient profile not found")
        
        # Get scan details
        result = db.execute(text("""
            SELECT 
                s.*, pp.patient_id,
                u.first_name || ' ' || u.last_name as patient_name
            FROM scans s
            JOIN patient_profiles pp ON s.patient_id = pp.id
            JOIN users u ON pp.user_id = u.id
            WHERE s.id = :scan_id AND s.patient_id = :patient_id
        """), {
            "scan_id": str(scan_id),
            "patient_id": str(patient_profile.id)
        })
        
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Scan not found")
        
        # Get images with signed URLs
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
                "size": img.file_size_bytes,
                "format": img.image_format,
                "order": img.image_order
            })
        
        return {
            "id": str(row.id),
            "scan_number": row.scan_number,
            "patient_name": row.patient_name,
            "patient_id": row.patient_id,
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
        logger.error(f"Failed to get scan details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports")
async def get_patient_reports(
    current_user: User = Depends(require_role(["patient"])),
    db: Session = Depends(get_db)
):
    """Get all published reports for the current patient."""
    try:
        # Get patient profile
        patient_profile = db.query(PatientProfile).filter(
            PatientProfile.user_id == current_user.id
        ).first()
        
        if not patient_profile:
            return []
        
        # Query published reports
        result = db.execute(text("""
            SELECT 
                r.id, r.report_number, r.report_title, 
                r.report_status, r.published_at, r.created_at,
                s.scan_number, s.examination_type, s.body_region, s.scan_date
            FROM reports r
            JOIN scans s ON r.scan_id = s.id
            WHERE s.patient_id = :patient_id
              AND r.report_status = 'published'
            ORDER BY r.published_at DESC
        """), {"patient_id": str(patient_profile.id)})
        
        reports = []
        for row in result:
            reports.append({
                "id": str(row.id),
                "report_number": row.report_number,
                "report_title": row.report_title,
                "report_status": row.report_status,
                "published_at": row.published_at.isoformat() if row.published_at else None,
                "created_at": row.created_at.isoformat(),
                "scan_number": row.scan_number,
                "examination_type": capitalize_for_display(row.examination_type, 'examination_type'),
                "body_region": capitalize_for_display(row.body_region, 'body_region'),
                "scan_date": row.scan_date.isoformat()
            })
        
        logger.info(f"Retrieved {len(reports)} reports for patient {patient_profile.patient_id}")
        return reports
        
    except Exception as e:
        logger.error(f"Failed to get patient reports: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports/{report_id}")
async def get_report_details(
    report_id: UUID,
    current_user: User = Depends(require_role(["patient"])),
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific report."""
    try:
        # Get patient profile
        patient_profile = db.query(PatientProfile).filter(
            PatientProfile.user_id == current_user.id
        ).first()
        
        if not patient_profile:
            raise HTTPException(status_code=404, detail="Patient profile not found")
        
        # Query report with verification that it belongs to this patient
        result = db.execute(text("""
            SELECT 
                r.*, s.scan_number, s.examination_type, s.body_region,
                s.scan_date, s.patient_id,
                u.first_name || ' ' || u.last_name as patient_name
            FROM reports r
            JOIN scans s ON r.scan_id = s.id
            JOIN patient_profiles pp ON s.patient_id = pp.id
            JOIN users u ON pp.user_id = u.id
            WHERE r.id = :report_id 
              AND s.patient_id = :patient_id
              AND r.report_status = 'published'
        """), {
            "report_id": str(report_id),
            "patient_id": str(patient_profile.id)
        })
        
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Report not found or not published")
        
        return {
            "id": str(row.id),
            "report_number": row.report_number,
            "report_title": row.report_title,
            "clinical_indication": row.clinical_indication,
            "technique": row.technique,
            "findings": row.findings,
            "impression": row.impression,
            "recommendations": row.recommendations,
            "report_status": row.report_status,
            "published_at": row.published_at.isoformat() if row.published_at else None,
            "created_at": row.created_at.isoformat(),
            "scan_number": row.scan_number,
            "patient_name": row.patient_name,
            "examination_type": capitalize_for_display(row.examination_type, 'examination_type'),
            "body_region": capitalize_for_display(row.body_region, 'body_region'),
            "scan_date": row.scan_date.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get report details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profile")
async def get_patient_profile(
    current_user: User = Depends(require_role(["patient"])),
    db: Session = Depends(get_db)
):
    """Get comprehensive patient profile information."""
    try:
        patient_profile = db.query(PatientProfile).filter(
            PatientProfile.user_id == current_user.id
        ).first()
        
        if not patient_profile:
            return {
                "user_id": str(current_user.id),
                "first_name": current_user.first_name,
                "last_name": current_user.last_name,
                "email": current_user.email,
                "phone": current_user.phone,
                "date_of_birth": current_user.date_of_birth,
                "patient_id": None,
                "age_years": None,
                "weight_kg": None,
                "height_cm": None,
                "gender": None,
                "blood_type": None,
                "allergies": [],
                "emergency_contact_name": None,
                "emergency_contact_phone": None,
                "medical_history": None,
            }
        
        return {
            "user_id": str(current_user.id),
            "first_name": current_user.first_name,
            "last_name": current_user.last_name,
            "email": current_user.email,
            "phone": current_user.phone,
            "date_of_birth": current_user.date_of_birth,
            "patient_id": patient_profile.patient_id,
            "age_years": patient_profile.age_years,
            "weight_kg": float(patient_profile.weight_kg) if patient_profile.weight_kg else None,
            "height_cm": float(patient_profile.height_cm) if patient_profile.height_cm else None,
            "gender": str(patient_profile.gender) if patient_profile.gender else None,
            "blood_type": patient_profile.blood_type,
            "allergies": patient_profile.allergies or [],
            "emergency_contact_name": patient_profile.emergency_contact_name,
            "emergency_contact_phone": patient_profile.emergency_contact_phone,
            "medical_history": patient_profile.medical_history,
        }
    except Exception as e:
        logger.error(f"ERROR in get_patient_profile: {str(e)}") 
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching profile: {str(e)}")