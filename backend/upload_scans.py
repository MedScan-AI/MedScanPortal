"""
Upload 6 Scans - Fixed Version
Avoids SQLAlchemy table creation issues
"""
import os
import sys
from pathlib import Path
import random
from datetime import datetime, timedelta
import uuid
from io import BytesIO

# Set environment BEFORE any app imports
from dotenv import load_dotenv
load_dotenv()

if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# Now safe to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Create engine without triggering metadata
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
    """Find images."""
    dir_path = Path(directory).expanduser()
    
    if not dir_path.exists():
        logger.error(f"❌ Not found: {directory}")
        return []
    
    images = []
    for ext in ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.PNG']:
        images.extend(list(dir_path.glob(ext)))
    
    return sorted(images)


def upload_scans(image_dir: str = './scans/'):
    """Upload scans using raw SQL to avoid schema conflicts."""
    
    # Import after engine created
    from app.services.gcs_storage import gcs_storage
    from sqlalchemy import text
    
    db = SessionLocal()
    
    try:
        images = find_images(image_dir)
        
        if not images:
            logger.error(f"\n❌ No images in {image_dir}")
            return
        
        # Get patients using raw SQL
        result = db.execute(text("""
            SELECT pp.id, pp.patient_id, u.first_name, u.last_name
            FROM patient_profiles pp
            JOIN users u ON pp.user_id = u.id
            WHERE u.role = 'patient'
            ORDER BY pp.patient_id
        """))
        patients = result.fetchall()
        
        if len(patients) < 3:
            logger.error("\n❌ Need 3 patients! Run create_2_new_patients.sql first")
            return
        
        print(f"\n{'='*70}")
        print(f"📤 UPLOADING {len(images)} SCANS")
        print(f"{'='*70}\n")
        
        print("👥 Patients:")
        for p in patients:
            print(f"   {p.first_name} {p.last_name} ({p.patient_id})")
        print("")
        
        print("📊 Filename detection:")
        print("   • 'lung*' → CT    → Lung Cancer Model")
        print("   • 'tb*'   → X-ray → TB Model")
        print("")
        
        # Status options
        statuses = ['pending', 'pending', 'pending', 'in_progress', 'ai_analyzed', 'completed']
        random.shuffle(statuses)
        
        urgencies = ['Routine'] * (len(images) - 1) + ['Urgent']
        random.shuffle(urgencies)
        
        # Upload
        created = 0
        img_idx = 0
        per_patient = len(images) // len(patients)
        
        tb_count = 0
        lc_count = 0
        
        for patient in patients:
            print(f"📤 {patient.first_name} {patient.last_name}:")
            
            for _ in range(per_patient):
                if img_idx >= len(images):
                    break
                
                img = images[img_idx]
                
                try:
                    scan_id = str(uuid.uuid4())
                    scan_number = f"SCAN-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
                    
                    # Detect from filename
                    filename_lower = img.name.lower()
                    if filename_lower.startswith('lung'):
                        exam_type = 'CT'
                        model_type = 'LC'
                        lc_count += 1
                    else:
                        exam_type = 'X-ray'
                        model_type = 'TB'
                        tb_count += 1
                    
                    scan_date = datetime.utcnow() - timedelta(days=random.randint(0, 20))
                    
                    # Insert scan using raw SQL
                    db.execute(text("""
                        INSERT INTO scans (
                            id, patient_id, scan_number, examination_type, body_region,
                            urgency_level, status, presenting_symptoms, current_medications,
                            previous_surgeries, scan_date, clinical_notes, imaging_facility,
                            created_at, updated_at
                        ) VALUES (
                            :id, :patient_id, :scan_number, :exam_type, :body_region,
                            :urgency, :status, :symptoms, :medications,
                            :surgeries, :scan_date, :notes, :facility,
                            NOW(), NOW()
                        )
                    """), {
                        'id': scan_id,
                        'patient_id': str(patient.id),
                        'scan_number': scan_number,
                        'exam_type': exam_type,
                        'body_region': 'Chest',
                        'urgency': urgencies[img_idx],
                        'status': statuses[img_idx],
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
                    
                    # Insert scan_image - match exact database schema
                    db.execute(text("""
                        INSERT INTO scan_images (
                            scan_id, 
                            image_path,
                            image_url,
                            file_size_bytes,
                            image_format,
                            image_order
                        ) VALUES (
                            :scan_id, 
                            :image_path,
                            :image_url,
                            :file_size,
                            :format,
                            :order
                        )
                    """), {
                        'scan_id': scan_id,
                        'image_path': gcs_url,  # Required NOT NULL field
                        'image_url': gcs_url,   # Optional but we fill it
                        'file_size': img.stat().st_size,
                        'format': 'jpg',
                        'order': 1
                    })
                    
                    db.commit()
                    
                    created += 1
                    img_idx += 1
                    
                    icons = {'pending': '⏳', 'in_progress': '🔄', 'ai_analyzed': '🤖', 'completed': '✅'}
                    
                    print(
                        f"   {icons.get(statuses[img_idx-1], '✓')} {scan_number} | "
                        f"{img.name:20s} → {exam_type:5s} | {model_type}"
                    )
                    
                except Exception as e:
                    logger.error(f"   ❌ Error: {str(e)[:100]}")
                    db.rollback()
                    img_idx += 1
            
            print("")
        
        # Summary
        print("="*70)
        print("✅ COMPLETE!")
        print("="*70)
        print(f"\nUploaded: {created}/{len(images)}\n")
        
        print("📊 By Patient:")
        for p in patients:
            result = db.execute(text("""
                SELECT COUNT(*) FROM scans WHERE patient_id = :patient_id
            """), {'patient_id': str(p.id)})
            count = result.scalar()
            print(f"   {p.first_name} {p.last_name}: {count}")
        
        print(f"\n📊 By Model Type:")
        print(f"   TB scans:          {tb_count}")
        print(f"   Lung Cancer scans: {lc_count}")
        
        print("\n💡 Model Selection (automatic):")
        print("   X-ray + Chest → TB Model")
        print("   CT + Chest    → Lung Cancer Model")
        
        print("\n🎯 Next: Login as radiologist to see scans!")
        print("\n" + "="*70 + "\n")
        
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', nargs='?', default='./scans/')
    parser.add_argument('--clear', action='store_true')
    args = parser.parse_args()
    
    if args.clear:
        from sqlalchemy import text
        db = SessionLocal()
        try:
            print("\n⚠️  Clearing...")
            db.execute(text("DELETE FROM scan_images"))
            db.execute(text("DELETE FROM scans"))
            db.commit()
            print("✓ Cleared\n")
        finally:
            db.close()
    
    upload_scans(args.directory)