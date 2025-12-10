"""
MLOps Sync Service - Real-Time Sync
Syncs diagnosed scans immediately to MLOps pipeline
"""
import logging
from datetime import datetime
from typing import List, Dict
import pandas as pd
import os

from sqlalchemy.orm import Session

from app.models.scan import Scan
from app.models.scan_image import ScanImage
from app.models.patient_profile import PatientProfile
from app.models.user import User
from app.models.radiologist_feedback import DiagnosisClass
from app.services.gcs_storage import gcs_storage

logger = logging.getLogger(__name__)


def sync_scan_to_mlops(
    scan_id: str,
    diagnosis: str,
    db: Session
) -> Dict[str, any]:
    """
    Sync a single scan to MLOps pipeline immediately.
    
    Args:
        scan_id: Scan UUID
        diagnosis: Diagnosis string (e.g., "Tuberculosis", "Lung_Cancer")
        db: Database session
        
    Returns:
        Result dictionary with 'success', 'message', 'paths'
    """
    try:
        # Map diagnosis to MLOps folder (handle lowercase from database)
        diagnosis_lower = diagnosis.lower()
        diagnosis_mapping = {
            'tuberculosis': 'tb',
            'lung_cancer': 'lung_cancer',
            'normal': 'normal',
            'other_abnormality': 'other',
            'inconclusive': 'inconclusive'
        }
        
        mlops_folder = diagnosis_mapping.get(diagnosis_lower)
        
        # Only sync TB and Lung Cancer (training data)
        if mlops_folder not in ['tb', 'lung_cancer']:
            logger.info(f"Skipping sync: diagnosis={diagnosis} (not training data)")
            return {
                'success': False,
                'message': f'Diagnosis "{diagnosis}" not training data',
                'synced': False
            }
        
        # Get scan
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            return {'success': False, 'message': 'Scan not found'}
        
        # Get patient
        patient = db.query(PatientProfile).filter(
            PatientProfile.id == scan.patient_id
        ).first()
        
        if not patient:
            return {'success': False, 'message': 'Patient not found'}
        
        # Get images
        scan_images = db.query(ScanImage).filter(
            ScanImage.scan_id == scan.id
        ).all()
        
        if not scan_images:
            return {'success': False, 'message': 'No images found'}
        
        # Copy images to MLOps folder (server-side copy - instant!)
        mlops_paths = []
        
        for scan_image in scan_images:
            try:
                # Skip if already synced
                if scan_image.gcs_path:
                    logger.info(f"Image already synced: {scan_image.id}")
                    mlops_paths.append(scan_image.gcs_path)
                    continue
                
                # Copy to MLOps folder
                mlops_url = gcs_storage.copy_to_mlops_folder(
                    source_url=scan_image.image_url,
                    diagnosis=mlops_folder,
                    patient_id=patient.patient_id
                )
                
                # Update database
                scan_image.gcs_path = mlops_url
                mlops_paths.append(mlops_url)
                
                logger.info(f"✓ Copied image to MLOps: {mlops_url}")
                
            except Exception as e:
                logger.error(f"Failed to copy image {scan_image.id}: {e}")
                continue
        
        if not mlops_paths:
            return {'success': False, 'message': 'Failed to copy images'}
        
        # Mark scan as synced
        scan.synced_to_gcs = True
        scan.gcs_sync_date = datetime.utcnow()
        scan.gcs_paths = mlops_paths
        
        db.commit()
        
        # Generate metadata CSV (single scan)
        try:
            metadata_url = generate_metadata_csv([scan], mlops_folder, db)
            logger.info(f"✓ Metadata uploaded: {metadata_url}")
        except Exception as e:
            logger.error(f"Metadata generation failed (non-critical): {e}")
        
        return {
            'success': True,
            'message': f'Synced {len(mlops_paths)} images to {mlops_folder}',
            'synced': True,
            'paths': mlops_paths
        }
        
    except Exception as e:
        logger.error(f"MLOps sync failed: {e}")
        return {
            'success': False,
            'message': str(e)
        }


def generate_metadata_csv(
    scans: List[Scan],
    diagnosis: str,
    db: Session
) -> str:
    """
    Generate and upload metadata CSV for one or more scans.
    
    Returns:
        GCS URL of uploaded CSV
    """
    rows = []
    
    for scan in scans:
        patient = db.query(PatientProfile).filter(
            PatientProfile.id == scan.patient_id
        ).first()
        
        user = db.query(User).filter(
            User.id == patient.user_id
        ).first()
        
        scan_images = db.query(ScanImage).filter(
            ScanImage.scan_id == scan.id,
            ScanImage.gcs_path.isnot(None)
        ).all()
        
        for scan_image in scan_images:
            image_path = scan_image.gcs_path.replace(
                f'gs://{gcs_storage.bucket_name}/', ''
            )
            
            row = {
                'Patient_Full_Name': f"{user.first_name} {user.last_name}",
                'Patient_ID': patient.patient_id,
                'Presenting_Symptoms': ', '.join(scan.presenting_symptoms or []),
                'Current_Medications': ', '.join(scan.current_medications or []),
                'Previous_Relevant_Surgeries': ', '.join(scan.previous_surgeries or []),
                'Age_Years': patient.age_years,
                'Weight_KG': float(patient.weight_kg) if patient.weight_kg else None,
                'Height_CM': float(patient.height_cm) if patient.height_cm else None,
                'Gender': str(patient.gender) if patient.gender else None,
                'Examination_Type': str(scan.examination_type),
                'Body_Region': str(scan.body_region),
                'Urgency_Level': str(scan.urgency_level),
                'Image_Path': image_path,
                'Diagnosis_Class': diagnosis.capitalize()
            }
            rows.append(row)
    
    if not rows:
        return None
    
    # Create CSV
    df = pd.DataFrame(rows)
    today = datetime.utcnow()
    
    # Use timestamp for uniqueness (multiple syncs per day)
    csv_filename = f"{diagnosis}_patients_{today.strftime('%Y%m%d_%H%M%S')}.csv"
    temp_path = f"/tmp/{csv_filename}"
    df.to_csv(temp_path, index=False)
    
    # Upload to GCS
    year = today.strftime('%Y')
    month = today.strftime('%m')
    day = today.strftime('%d')
    gcs_path = f"vision/metadata/{diagnosis}/{year}/{month}/{day}/{csv_filename}"
    
    blob = gcs_storage.bucket.blob(gcs_path)
    blob.upload_from_filename(temp_path)
    
    # Cleanup
    os.remove(temp_path)
    
    gcs_url = f"gs://{gcs_storage.bucket_name}/{gcs_path}"
    return gcs_url