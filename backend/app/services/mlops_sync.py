"""
MLOps Sync Service - Real-Time Sync
Syncs diagnosed scans to proper class folders for data pipeline compatibility
"""
import logging
from datetime import datetime
from typing import List, Dict, Optional
import pandas as pd
import os
import random

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.scan import Scan
from app.models.scan_image import ScanImage
from app.models.patient_profile import PatientProfile
from app.models.user import User
from app.services.gcs_storage import gcs_storage

logger = logging.getLogger(__name__)


class DiagnosisMappingService:
    """Maps radiologist diagnosis to MLOps class folders."""
    
    # TB class mapping (capitalized as per vision_pipeline.yml)
    TB_CLASS_MAP = {
        'normal': 'Normal',
        'tuberculosis': 'Tuberculosis',
    }
    
    # Lung Cancer class mapping (lowercase as per vision_pipeline.yml)
    LUNG_CANCER_CLASS_MAP = {
        'normal': 'normal',
        'adenocarcinoma': 'adenocarcinoma',
        'squamous_cell_carcinoma': 'squamous_cell_carcinoma',
        'large_cell_carcinoma': 'large_cell_carcinoma',
        'benign': 'benign',
        'malignant': 'malignant',
    }
    
    @staticmethod
    def get_class_folder(
        radiologist_diagnosis: str,
        dataset_type: str,
        ai_predicted_class: Optional[str] = None
    ) -> Optional[str]:
        """
        Map radiologist diagnosis to MLOps class folder name.
        
        LOGIC:
        1. Radiologist diagnosis is PRIMARY (ground truth for training)
        2. EXCEPTION: If radiologist gives generic "lung_cancer" and AI has specific subtype,
           use AI's specific class for better folder organization
        
        Args:
            radiologist_diagnosis: Final diagnosis from radiologist
            dataset_type: 'tb' or 'lung_cancer'
            ai_predicted_class: AI's specific prediction (from ai_predictions table)
            
        Returns:
            Class folder name matching data pipeline requirements, or None if not trainable
        """
        diagnosis_lower = str(radiologist_diagnosis).lower()
        
        if dataset_type == 'tb':
            # TB: Simple mapping (Normal or Tuberculosis)
            return DiagnosisMappingService.TB_CLASS_MAP.get(diagnosis_lower)
        
        elif dataset_type == 'lung_cancer':
            # Lung Cancer: Handle generic vs specific diagnosis
            
            # If radiologist gave SPECIFIC diagnosis, use it
            if diagnosis_lower in DiagnosisMappingService.LUNG_CANCER_CLASS_MAP:
                return DiagnosisMappingService.LUNG_CANCER_CLASS_MAP[diagnosis_lower]
            
            # If radiologist gave GENERIC "lung_cancer" diagnosis
            if diagnosis_lower == 'lung_cancer':
                # Try to use AI's specific class if available
                if ai_predicted_class:
                    ai_class_lower = str(ai_predicted_class).lower()
                    if ai_class_lower in DiagnosisMappingService.LUNG_CANCER_CLASS_MAP:
                        logger.info(
                            f"Radiologist gave generic 'lung_cancer', "
                            f"using AI's specific class: '{ai_class_lower}'"
                        )
                        return DiagnosisMappingService.LUNG_CANCER_CLASS_MAP[ai_class_lower]
                
                # Fallback: Use 'malignant' for generic lung cancer
                logger.warning(
                    "Generic 'lung_cancer' diagnosis without AI specific subtype. "
                    "Defaulting to 'malignant' folder."
                )
                return 'malignant'
        
        return None
    
    @staticmethod
    def is_trainable(diagnosis: str, dataset_type: str) -> bool:
        """
        Check if diagnosis is suitable for training data.
        
        Filters out:
        - inconclusive
        - other_abnormality
        - unknown
        """
        diagnosis_lower = str(diagnosis).lower()
        
        # Exclude non-trainable diagnoses
        non_trainable = ['inconclusive', 'other_abnormality', 'unknown']
        if diagnosis_lower in non_trainable:
            return False
        
        # Accept if it maps to a valid class folder
        if dataset_type == 'tb':
            return diagnosis_lower in DiagnosisMappingService.TB_CLASS_MAP
        elif dataset_type == 'lung_cancer':
            return (diagnosis_lower in DiagnosisMappingService.LUNG_CANCER_CLASS_MAP or 
                    diagnosis_lower == 'lung_cancer')  # Generic LC is trainable
        
        return False


def sync_scan_to_mlops(
    scan_id: str,
    diagnosis: str,
    db: Session
) -> Dict[str, any]:
    """
    Sync a single scan to MLOps pipeline with proper class folder structure.
    
    USES EXISTING TABLES:
    - ai_predictions: Get AI's specific predicted_class
    - radiologist_feedback: Get radiologist's final diagnosis (ground truth)
    - scan_images: Get images to copy
    
    CREATES STRUCTURE:
    vision/raw/{dataset_type}/{split}/{class_folder}/{date}_{patient_id}_{filename}
    
    Args:
        scan_id: Scan UUID
        diagnosis: Radiologist diagnosis (from radiologist_feedback.radiologist_diagnosis)
        db: Database session
        
    Returns:
        Result dictionary with 'success', 'message', 'paths'
    """
    try:
        # Get scan to determine exam type
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            return {'success': False, 'message': 'Scan not found'}
        
        # Determine dataset type from examination_type + body_region
        exam_type = str(scan.examination_type).lower()
        body_region = str(scan.body_region).lower()
        
        if exam_type == 'xray' and body_region == 'chest':
            dataset_type = 'tb'
        elif exam_type == 'ct' and body_region == 'chest':
            dataset_type = 'lung_cancer'
        else:
            logger.info(
                f"Skipping sync for {scan.scan_number}: "
                f"exam_type={exam_type}, body_region={body_region} (not TB/LC)"
            )
            return {
                'success': False,
                'message': f'Exam type "{exam_type}" + region "{body_region}" not supported for training',
                'synced': False
            }
        
        # Check if diagnosis is trainable
        if not DiagnosisMappingService.is_trainable(diagnosis, dataset_type):
            logger.info(
                f"Skipping sync for {scan.scan_number}: "
                f"diagnosis='{diagnosis}' (not trainable)"
            )
            return {
                'success': False,
                'message': f'Diagnosis "{diagnosis}" not suitable for training',
                'synced': False
            }
        
        # Get patient
        patient = db.query(PatientProfile).filter(
            PatientProfile.id == scan.patient_id
        ).first()
        
        if not patient:
            return {'success': False, 'message': 'Patient not found'}
        
        # Get AI prediction from EXISTING ai_predictions table
        ai_prediction_result = db.execute(text("""
            SELECT predicted_class 
            FROM ai_predictions 
            WHERE scan_id = :scan_id
        """), {"scan_id": str(scan_id)})
        
        ai_row = ai_prediction_result.fetchone()
        ai_predicted_class = ai_row.predicted_class if ai_row else None
        
        # Get class folder name (radiologist diagnosis is primary, AI used for LC subtypes)
        class_folder = DiagnosisMappingService.get_class_folder(
            radiologist_diagnosis=diagnosis,
            dataset_type=dataset_type,
            ai_predicted_class=ai_predicted_class
        )
        
        if not class_folder:
            return {
                'success': False,
                'message': f'Cannot map diagnosis "{diagnosis}" to class folder for {dataset_type}'
            }
        
        # Get images
        scan_images = db.query(ScanImage).filter(
            ScanImage.scan_id == scan.id
        ).all()
        
        if not scan_images:
            return {'success': False, 'message': 'No images found'}
        
        # Determine train/test split (80/20, deterministic by scan_id)
        random.seed(int(str(scan_id).replace('-', '')[:8], 16))
        split = 'train' if random.random() < 0.8 else 'test'
        
        logger.info(
            f"Syncing {scan.scan_number} → {dataset_type}/{split}/{class_folder}/"
        )
        
        # Copy images to MLOps folder with proper class structure
        mlops_paths = []
        
        for scan_image in scan_images:
            try:
                # Skip if already synced
                if scan_image.gcs_path:
                    logger.info(f"Image already synced: {scan_image.id}")
                    mlops_paths.append(scan_image.gcs_path)
                    continue
                
                # Copy to MLOps folder (uses UPDATED gcs_storage method)
                mlops_url = gcs_storage.copy_to_mlops_folder(
                    source_url=scan_image.image_url,
                    dataset_type=dataset_type,
                    class_folder=class_folder,
                    patient_id=patient.patient_id,
                    split=split
                )
                
                # Update scan_image.gcs_path (tracks MLOps location)
                scan_image.gcs_path = mlops_url
                mlops_paths.append(mlops_url)
                
                logger.info(f"✓ Copied: {mlops_url}")
                
            except Exception as e:
                logger.error(f"Failed to copy image {scan_image.id}: {e}")
                continue
        
        if not mlops_paths:
            return {'success': False, 'message': 'Failed to copy images'}
        
        # Mark scan as synced (uses EXISTING scans table columns)
        scan.synced_to_gcs = True
        scan.gcs_sync_date = datetime.utcnow()
        scan.gcs_paths = mlops_paths  # JSONB array of paths
        
        db.commit()
        
        # Generate metadata CSV (single scan)
        try:
            metadata_url = generate_metadata_csv(
                scans=[scan],
                dataset_type=dataset_type,
                class_folder=class_folder,
                db=db
            )
            logger.info(f"✓ Metadata uploaded: {metadata_url}")
        except Exception as e:
            logger.error(f"Metadata generation failed (non-critical): {e}")
        
        return {
            'success': True,
            'message': f'Synced {len(mlops_paths)} images to {dataset_type}/{split}/{class_folder}/',
            'synced': True,
            'paths': mlops_paths,
            'dataset_type': dataset_type,
            'class_folder': class_folder,
            'split': split
        }
        
    except Exception as e:
        logger.error(f"MLOps sync failed for scan {scan_id}: {e}")
        db.rollback()
        return {
            'success': False,
            'message': str(e)
        }


def generate_metadata_csv(
    scans: List[Scan],
    dataset_type: str,
    class_folder: str,
    db: Session
) -> str:
    """
    Generate and upload metadata CSV for one or more scans.
    Matches schema from synthetic_data.yml for Great Expectations compatibility.
    
    Args:
        scans: List of scans to include
        dataset_type: 'tb' or 'lung_cancer'
        class_folder: Class folder name (e.g., 'Tuberculosis', 'adenocarcinoma')
        db: Database session
    
    Returns:
        GCS URL of uploaded CSV
    """
    rows = []
    
    for scan in scans:
        # Get patient profile
        patient = db.query(PatientProfile).filter(
            PatientProfile.id == scan.patient_id
        ).first()
        
        # Get user (for name)
        user = db.query(User).filter(
            User.id == patient.user_id
        ).first()
        
        # Get synced images (only those with gcs_path populated)
        scan_images = db.query(ScanImage).filter(
            ScanImage.scan_id == scan.id,
            ScanImage.gcs_path.isnot(None)  # Only synced images
        ).all()
        
        for scan_image in scan_images:
            # Image path relative to bucket (without gs://bucket/ prefix)
            # NEW: Path includes train/test and class folder
            # Example: vision/raw/tb/train/Tuberculosis/20241211_PT-001_original.jpg
            image_path = scan_image.gcs_path.replace(
                f'gs://{gcs_storage.bucket_name}/', ''
            )
            
            # Create row matching synthetic_data.yml schema exactly
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
                'Examination_Type': str(scan.examination_type).upper(),  # X-RAY or CT
                'Body_Region': str(scan.body_region).capitalize(),  # Chest
                'Urgency_Level': str(scan.urgency_level).capitalize(),  # Routine, Urgent, Emergent
                'Image_Path': image_path,  # UPDATED: includes train/class/ structure
                'Diagnosis_Class': class_folder  # MUST match class folder name exactly
            }
            rows.append(row)
    
    if not rows:
        logger.warning("No rows to write to CSV")
        return None
    
    # Create DataFrame
    df = pd.DataFrame(rows)
    
    # Save to temp file with timestamp
    today = datetime.utcnow()
    csv_filename = f"{dataset_type}_patients_{today.strftime('%Y%m%d_%H%M%S')}.csv"
    temp_path = f"/tmp/{csv_filename}"
    df.to_csv(temp_path, index=False)
    
    # Upload to GCS in date-partitioned metadata folder
    year = today.strftime('%Y')
    month = today.strftime('%m')
    day = today.strftime('%d')
    gcs_path = f"vision/metadata/{dataset_type}/{year}/{month}/{day}/{csv_filename}"
    
    blob = gcs_storage.bucket.blob(gcs_path)
    blob.upload_from_filename(temp_path)
    
    # Cleanup temp file
    os.remove(temp_path)
    
    gcs_url = f"gs://{gcs_storage.bucket_name}/{gcs_path}"
    logger.info(f"✓ Metadata CSV: {gcs_url}")
    logger.info(f"  Rows: {len(rows)}, Class: {class_folder}, Dataset: {dataset_type}")
    
    return gcs_url