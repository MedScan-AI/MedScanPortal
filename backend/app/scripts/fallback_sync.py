"""
Fallback Sync Script - Catches Any Failed Real-Time Syncs
Run daily at 2 AM to retry any scans that failed to sync
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from app.core.database import SessionLocal
from app.models.scan import Scan
from app.services.mlops_sync import sync_scan_to_mlops
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def retry_failed_syncs(days_back: int = 7):
    """
    Find and retry scans that should be synced but aren't.
    
    Args:
        days_back: Check last N days for failed syncs
    """
    db = SessionLocal()
    
    try:
        cutoff = datetime.utcnow() - timedelta(days=days_back)
        
        # Find completed scans that aren't synced yet
        failed_scans = db.query(Scan).filter(
            Scan.status == 'completed',
            Scan.synced_to_gcs == False,
            Scan.radiologist_review_completed_at >= cutoff
        ).all()
        
        if not failed_scans:
            logger.info("✓ All scans synced - nothing to retry")
            return
        
        logger.info(f"Found {len(failed_scans)} scans to retry")
        
        success = 0
        failed = 0
        
        for scan in failed_scans:
            # Get diagnosis from feedback
            from app.models.radiologist_feedback import RadiologistFeedback
            
            feedback = db.query(RadiologistFeedback).filter(
                RadiologistFeedback.scan_id == scan.id
            ).first()
            
            if not feedback:
                logger.warning(f"No diagnosis for {scan.scan_number}, skipping")
                continue
            
            # Retry sync
            result = sync_scan_to_mlops(
                scan_id=str(scan.id),
                diagnosis=str(feedback.radiologist_diagnosis),
                db=db
            )
            
            if result.get('success'):
                success += 1
            else:
                failed += 1
                logger.error(f"Retry failed for {scan.scan_number}: {result.get('message')}")
        
        logger.info(f"✓ Retry complete: {success} synced, {failed} failed")
        
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Retry failed MLOps syncs')
    parser.add_argument('--days', type=int, default=7, help='Check last N days')
    args = parser.parse_args()
    
    retry_failed_syncs(days_back=args.days)