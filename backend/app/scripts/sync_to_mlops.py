"""
Sync Diagnosed Scans to MLOps Pipeline
Copies images from platform/ to vision/ within GCS (server-side copy)
Only syncs scans that have been diagnosed by radiologist
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict
import logging

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.scan import Scan
from app.models.scan_image import ScanImage
from app.models.patient_profile import PatientProfile
from app.models.radiologist_feedback import RadiologistFeedback
from app.models.user import User
from app.services.gcs_storage import gcs_storage

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MLOpsSyncService:
    """Sync diagnosed scans to MLOps pipeline."""
    
    def __init__(self):
        self.db: Session = SessionLocal()
        logger.info("MLOps Sync Service initialized")
    
    def get_unsynced_scans(self, days_back: int = 1) -> List[Scan]:
        """
        Get scans that are:
        1. Completed (status = 'completed')
        2. Have radiologist feedback (diagnosed)
        3. Not yet synced (synced_to_gcs = False)
        4. Within specified time range
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        
        scans = self.db.query(Scan).join(
            RadiologistFeedback,
            Scan.id == RadiologistFeedback.scan_id
        ).filter(
            Scan.status == 'completed',
            Scan.synced_to_gcs == False,
            Scan.radiologist_review_completed_at >= cutoff_date
        ).all()
        
        logger.info(f"Found {len(scans)} unsynced diagnosed scans")
        return scans
    
    def get_diagnosis_label(self, scan_id: str) -> str:
        """Get final diagnosis label from radiologist feedback."""
        feedback = self.db.query(RadiologistFeedback).filter(
            RadiologistFeedback.scan_id == scan_id
        ).first()
        
        if not feedback:
            return 'unknown'
        
        # Map to MLOps folder names (handle lowercase from database)
        diagnosis_mapping = {
            'tuberculosis': 'tb',
            'lung_cancer': 'lung_cancer',
            'normal': 'normal',
            'other_abnormality': 'other',
            'inconclusive': 'inconclusive'
        }
        
        return diagnosis_mapping.get(
            str(feedback.radiologist_diagnosis).lower(),
            'unknown'
        )
    
    def sync_scan(self, scan: Scan) -> bool:
        """
        Sync single scan to MLOps pipeline.
        Copies images from platform/ to vision/ using server-side copy.
        """
        try:
            # Get diagnosis
            diagnosis = self.get_diagnosis_label(str(scan.id))
            
            # Only sync TB and Lung Cancer (training data)
            if diagnosis not in ['tb', 'lung_cancer']:
                logger.info(
                    f"Skipping {scan.scan_number}: "
                    f"diagnosis={diagnosis} (not training data)"
                )
                return False
            
            # Get patient
            patient = self.db.query(PatientProfile).filter(
                PatientProfile.id == scan.patient_id
            ).first()
            
            if not patient:
                logger.error(f"Patient not found for scan {scan.scan_number}")
                return False
            
            # Get scan images
            scan_images = self.db.query(ScanImage).filter(
                ScanImage.scan_id == scan.id
            ).all()
            
            if not scan_images:
                logger.warning(f"No images for scan {scan.scan_number}")
                return False
            
            # Copy each image to MLOps folder (server-side copy)
            mlops_paths = []
            
            for scan_image in scan_images:
                try:
                    # Copy within GCS (no data transfer!)
                    mlops_url = gcs_storage.copy_to_mlops_folder(
                        source_url=scan_image.image_url,
                        diagnosis=diagnosis,
                        patient_id=patient.patient_id
                    )
                    
                    # Update database
                    scan_image.gcs_path = mlops_url
                    mlops_paths.append(mlops_url)
                    
                except Exception as e:
                    logger.error(f"Failed to copy image {scan_image.id}: {e}")
                    continue
            
            if mlops_paths:
                # Mark scan as synced
                scan.synced_to_gcs = True
                scan.gcs_sync_date = datetime.utcnow()
                scan.gcs_paths = mlops_paths
                self.db.commit()
                
                logger.info(
                    f"✓ Synced {scan.scan_number} ({diagnosis}): "
                    f"{len(mlops_paths)} images"
                )
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Sync failed for {scan.scan_number}: {e}")
            self.db.rollback()
            return False
    
    def generate_metadata_csv(
        self, 
        scans: List[Scan], 
        diagnosis: str
    ) -> str:
        """
        Generate metadata CSV matching existing MLOps format.
        
        CSV Format:
        Patient_Full_Name,Patient_ID,Presenting_Symptoms,Current_Medications,
        Previous_Relevant_Surgeries,Age_Years,Weight_KG,Height_CM,Gender,
        Examination_Type,Body_Region,Urgency_Level,Image_Path,Diagnosis_Class
        """
        import pandas as pd
        
        rows = []
        
        for scan in scans:
            # Get patient profile with user info
            patient = self.db.query(PatientProfile).filter(
                PatientProfile.id == scan.patient_id
            ).first()
            
            user = self.db.query(User).filter(
                User.id == patient.user_id
            ).first()
            
            # Get radiologist feedback
            feedback = self.db.query(RadiologistFeedback).filter(
                RadiologistFeedback.scan_id == scan.id
            ).first()
            
            # Get synced images
            scan_images = self.db.query(ScanImage).filter(
                ScanImage.scan_id == scan.id,
                ScanImage.gcs_path.isnot(None)  # Only synced images
            ).all()
            
            for scan_image in scan_images:
                # Remove gs://bucket-name/ prefix for Image_Path
                image_path = scan_image.gcs_path.replace(f'gs://{gcs_storage.bucket_name}/', '')
                
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
                    'Diagnosis_Class': str(feedback.radiologist_diagnosis) if feedback else 'Unknown'
                }
                rows.append(row)
        
        if not rows:
            logger.warning("No rows to write to CSV")
            return None
        
        # Create DataFrame
        df = pd.DataFrame(rows)
        
        # Save to temp file
        today = datetime.utcnow()
        csv_filename = f"{diagnosis}_patients_{today.strftime('%Y%m%d')}.csv"
        temp_path = f"/tmp/{csv_filename}"
        df.to_csv(temp_path, index=False)
        
        logger.info(f"✓ Generated CSV: {len(rows)} rows")
        return temp_path
    
    def upload_metadata_to_gcs(self, csv_path: str, diagnosis: str) -> str:
        """Upload metadata CSV to vision/metadata/ folder."""
        if not csv_path or not os.path.exists(csv_path):
            logger.warning("No CSV to upload")
            return None
        
        today = datetime.utcnow()
        year = today.strftime('%Y')
        month = today.strftime('%m')
        day = today.strftime('%d')
        
        # Path: vision/metadata/{diagnosis}/YYYY/MM/DD/filename.csv
        filename = Path(csv_path).name
        gcs_path = f"vision/metadata/{diagnosis}/{year}/{month}/{day}/{filename}"
        
        blob = gcs_storage.bucket.blob(gcs_path)
        blob.upload_from_filename(csv_path)
        
        gcs_url = f"gs://{gcs_storage.bucket_name}/{gcs_path}"
        logger.info(f"✓ Uploaded metadata: {gcs_url}")
        
        return gcs_url
    
    def run_sync(self, days_back: int = 1) -> Dict[str, int]:
        """
        Run complete sync process.
        
        Args:
            days_back: Sync scans from last N days (default 1 = last 24 hours)
            
        Returns:
            Statistics dictionary
        """
        logger.info("="*60)
        logger.info("MLOPS SYNC STARTED")
        logger.info(f"Syncing diagnosed scans from last {days_back} day(s)")
        logger.info("="*60)
        
        stats = {
            'total_scans': 0,
            'synced_tb': 0,
            'synced_lung_cancer': 0,
            'skipped': 0,
            'failed': 0
        }
        
        try:
            # Get unsynced scans
            unsynced_scans = self.get_unsynced_scans(days_back=days_back)
            stats['total_scans'] = len(unsynced_scans)
            
            if not unsynced_scans:
                logger.info("✓ No new scans to sync")
                return stats
            
            # Group by diagnosis for metadata CSV
            tb_scans = []
            lc_scans = []
            
            # Sync each scan
            for scan in unsynced_scans:
                diagnosis = self.get_diagnosis_label(str(scan.id))
                
                if self.sync_scan(scan):
                    if diagnosis == 'tb':
                        tb_scans.append(scan)
                        stats['synced_tb'] += 1
                    elif diagnosis == 'lung_cancer':
                        lc_scans.append(scan)
                        stats['synced_lung_cancer'] += 1
                else:
                    if diagnosis in ['tb', 'lung_cancer']:
                        stats['failed'] += 1
                    else:
                        stats['skipped'] += 1
            
            # Generate and upload metadata CSVs
            if tb_scans:
                logger.info(f"Generating TB metadata for {len(tb_scans)} scans")
                csv_path = self.generate_metadata_csv(tb_scans, 'tb')
                if csv_path:
                    self.upload_metadata_to_gcs(csv_path, 'tb')
                    os.remove(csv_path)
            
            if lc_scans:
                logger.info(f"Generating Lung Cancer metadata for {len(lc_scans)} scans")
                csv_path = self.generate_metadata_csv(lc_scans, 'lung_cancer')
                if csv_path:
                    self.upload_metadata_to_gcs(csv_path, 'lung_cancer')
                    os.remove(csv_path)
            
            logger.info("="*60)
            logger.info("MLOPS SYNC COMPLETED")
            logger.info("="*60)
            
            return stats
            
        except Exception as e:
            logger.error(f"Sync failed: {e}", exc_info=True)
            raise
        finally:
            self.db.close()


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Sync diagnosed scans from web platform to MLOps GCS bucket'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=1,
        help='Sync scans from last N days (default: 1)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be synced without actually syncing'
    )
    
    args = parser.parse_args()
    
    try:
        sync_service = MLOpsSyncService()
        
        if args.dry_run:
            logger.info("DRY RUN MODE - No changes will be made")
            # TODO: Implement dry run logic
        
        stats = sync_service.run_sync(days_back=args.days)
        
        # Print summary
        print("\n" + "="*60)
        print("SYNC SUMMARY")
        print("="*60)
        print(f"Total scans found:        {stats['total_scans']}")
        print(f"TB scans synced:          {stats['synced_tb']}")
        print(f"Lung cancer scans synced: {stats['synced_lung_cancer']}")
        print(f"Skipped (normal/other):   {stats['skipped']}")
        print(f"Failed:                   {stats['failed']}")
        print("="*60)
        
        # Exit code
        if stats['failed'] > 0:
            sys.exit(1)
        
    except Exception as e:
        logger.error(f"Sync script failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()