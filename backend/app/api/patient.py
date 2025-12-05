from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from app.core.database import get_db
from app.core.security import require_role
from app.models.user import User
from app.schemas.schemas import ScanResponse, ReportResponse
from app.models.patient_profile import PatientProfile

router = APIRouter()

@router.get("/scans", response_model=List[ScanResponse])
async def get_patient_scans(
    current_user: User = Depends(require_role(["patient"])),
    db: Session = Depends(get_db)
):
    """
    Get all scans for the current patient.
    """
    # TODO: Implement actual database query
    # This is a placeholder that returns mock data
    return []

@router.get("/scans/{scan_id}", response_model=ScanResponse)
async def get_scan_details(
    scan_id: UUID,
    current_user: User = Depends(require_role(["patient"])),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific scan.
    """
    # TODO: Implement actual database query
    # Verify that the scan belongs to the current patient
    raise HTTPException(status_code=404, detail="Scan not found")

@router.get("/reports", response_model=List[ReportResponse])
async def get_patient_reports(
    current_user: User = Depends(require_role(["patient"])),
    db: Session = Depends(get_db)
):
    """
    Get all published reports for the current patient.
    """
    # TODO: Implement actual database query
    # Only return reports that are published and visible
    return []

@router.get("/reports/{report_id}", response_model=ReportResponse)
async def get_report_details(
    report_id: UUID,
    current_user: User = Depends(require_role(["patient"])),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific report.
    """
    # TODO: Implement actual database query
    # Verify that the report belongs to the current patient
    raise HTTPException(status_code=404, detail="Report not found")

@router.get("/profile")
async def get_patient_profile(
    current_user: User = Depends(require_role(["patient"])),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive patient profile information.
    """
    try:
        # Import here to see the exact error
        from app.models.patient_profile import PatientProfile
        
        # Query patient_profiles table
        patient_profile = db.query(PatientProfile).filter(
            PatientProfile.user_id == current_user.id
        ).first()
        
        if not patient_profile:
            # Return basic user data if no profile exists
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
            # User account data
            "user_id": str(current_user.id),
            "first_name": current_user.first_name,
            "last_name": current_user.last_name,
            "email": current_user.email,
            "phone": current_user.phone,
            "date_of_birth": current_user.date_of_birth,
            
            # Patient profile data
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
        print(f"ERROR in get_patient_profile: {str(e)}") 
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching profile: {str(e)}")