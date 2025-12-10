"""
Upload 6 Scans
"""
import os
import sys
from pathlib import Path
import random
from datetime import datetime, timedelta
import uuid
from io import BytesIO

from dotenv import load_dotenv
load_dotenv()

if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.services.gcs_storage import gcs_storage

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)

import logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

SYMPTOMS = [
    ["Persistent cough", "Night sweats"],
    ["Chest pain", "Fever"],
    ["Shortness of breath", "Fatigue"],
]

MEDICATIONS = [["None"], ["Albuterol"], ["Isoniazid"]]
SURGERIES = [["None"], ["Appendectomy"]]


def find_images(directory: str) -> list:
    dir_path = Path(directory).expanduser()
    if not dir_path.exists():
        logger.error(f"Not found: {directory}")
        return []
    images = []
    for ext in ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.PNG']:
        images.extend(list(dir_path.glob(ext)))
    return sorted(images)


def upload_scans(image_dir: str = './scans/'):
    """Upload scans with ALL lowercase enum values."""
    
    db = SessionLocal()
    
    try:
        images = find_images(image_dir)
        
        if not images:
            logger.error(f"\n No images in {image_dir}")
            return
        
        # Get patients
        result = db.execute(text("""
            SELECT pp.id, pp.patient_id, u.first_name, u.last_name
            FROM patient_profiles pp
            JOIN users u ON pp.user_id = u.id
            WHERE u.role = 'patient'
            ORDER BY pp.patient_id
        """))
        patients = result.fetchall()
        
        if len(patients) < 3:
            logger.error("\n Need 3 patients!")
            return
        
        print(f"UPLOADING {len(images)} SCANS")
        
        print("👥 Patients:")
        for p in patients:
            print(f"   {p.first_name} {p.last_name} ({p.patient_id})")
        print("")
        
        urgencies = ['routine'] * (len(images) - 2) + ['urgent', 'emergent']
        random.shuffle(urgencies)
        
        created = 0
        img_idx = 0
        per_patient = len(images) // len(patients)
        
        tb_count = 0
        lc_count = 0
        
        for patient in patients:
            print(f" {patient.first_name} {patient.last_name}:")
            
            for _ in range(per_patient):
                if img_idx >= len(images):
                    break
                
                img = images[img_idx]
                
                try:
                    scan_id = str(uuid.uuid4())
                    scan_number = f"SCAN-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
                    
                    # Filename detection 
                    filename_lower = img.name.lower()
                    if filename_lower.startswith('lung'):
                        exam_type = 'ct'       
                        model_type = 'LC'
                        lc_count += 1
                    else:
                        exam_type = 'xray'      
                        model_type = 'TB'
                        tb_count += 1
                    
                    scan_date = datetime.utcnow() - timedelta(days=random.randint(0, 20))
                    
                    # Insert with ALL LOWERCASE enum values
                    db.execute(text("""
                        INSERT INTO scans (
                            id, patient_id, scan_number, 
                            examination_type, body_region, urgency_level, status,
                            presenting_symptoms, current_medications, previous_surgeries,
                            scan_date, clinical_notes, imaging_facility,
                            created_at, updated_at
                        ) VALUES (
                            :id, :patient_id, :scan_number,
                            :exam_type, :body_region, :urgency, :status,
                            :symptoms, :medications, :surgeries,
                            :scan_date, :notes, :facility,
                            NOW(), NOW()
                        )
                    """), {
                        'id': scan_id,
                        'patient_id': str(patient.id),
                        'scan_number': scan_number,
                        'exam_type': exam_type,         # 'xray' or 'ct'
                        'body_region': 'chest',         # 'chest' (lowercase!)
                        'urgency': urgencies[img_idx],  # 'routine', 'urgent', 'emergent' (lowercase!)
                        'status': 'pending',            # 'pending'
                        'symptoms': random.choice(SYMPTOMS),
                        'medications': random.choice(MEDICATIONS),
                        'surgeries': random.choice(SURGERIES),
                        'scan_date': scan_date,
                        'notes': f"{exam_type} for {model_type} evaluation.",
                        'facility': 'Massachusetts General Hospital'
                    })
                    
                    # Upload to GCS
                    with open(img, 'rb') as f:
                        gcs_url = gcs_storage.upload_scan_image(
                            file_data=BytesIO(f.read()),
                            patient_id=patient.patient_id,
                            scan_id=scan_id,
                            filename="original.jpg"
                        )
                    
                    # Insert image
                    db.execute(text("""
                        INSERT INTO scan_images (
                            scan_id, image_path, image_url, 
                            file_size_bytes, image_format, image_order
                        ) VALUES (
                            :scan_id, :path, :url, :size, :format, :order
                        )
                    """), {
                        'scan_id': scan_id,
                        'path': gcs_url,
                        'url': gcs_url,
                        'size': img.stat().st_size,
                        'format': 'jpg',
                        'order': 1
                    })
                    
                    db.commit()
                    created += 1
                    img_idx += 1
                    
                    print(f"   ✅ {scan_number} | {img.name:20s} → {exam_type:5s} | {model_type}")
                    
                except Exception as e:
                    logger.error(f"   {str(e)[:200]}")
                    db.rollback()
                    img_idx += 1
            
            print("")
        
        print(f"\nUploaded: {created}/{len(images)}\n")
        
        if created > 0:
            print(" By Patient:")
            for p in patients:
                result = db.execute(text("SELECT COUNT(*) FROM scans WHERE patient_id = :pid"),
                                   {'pid': str(p.id)})
                count = result.scalar()
                print(f"   {p.first_name} {p.last_name}: {count}")
            
            print(f"\n By Model:")
            print(f"   TB (xray):  {tb_count}")
            print(f"   LC (ct):    {lc_count}")
            
            print(f"\n All PENDING ({created} scans)")
            
            print("\n Model Selection:")
            print("   'xray' + 'chest' → TB Model")
            print("   'ct' + 'chest'   → Lung Cancer Model")
        
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', nargs='?', default='./scans/')
    args = parser.parse_args()
    upload_scans(args.directory)