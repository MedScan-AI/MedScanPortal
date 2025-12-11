"""
GCS Storage Service for MedScan Web Platform
Handles all image uploads/downloads using GCS
"""
import os
from pathlib import Path
from typing import Optional, List
from datetime import timedelta
from io import BytesIO
import logging

from google.cloud import storage
from google.cloud.exceptions import NotFound

logger = logging.getLogger(__name__)


class GCSStorageService:
    """Manage medical scan images in GCS."""
    
    def __init__(self):
        self._client = None
        self._bucket = None
        self.project_id = None
        self.bucket_name = None
    
    def _initialize(self):
        """Lazy initialization - only when first used."""
        if self._client is not None:
            return
        
        # Load from config (which reads .env)
        from app.core.config import settings
        
        self.project_id = settings.GCP_PROJECT_ID
        self.bucket_name = settings.GCS_BUCKET_NAME
        
        # Set credentials path
        if settings.GOOGLE_APPLICATION_CREDENTIALS:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.GOOGLE_APPLICATION_CREDENTIALS
        
        # Initialize GCS client
        self._client = storage.Client(project=self.project_id)
        self._bucket = self._client.bucket(self.bucket_name)
        
        logger.info(f"GCS Storage initialized: gs://{self.bucket_name}")
    
    @property
    def client(self):
        """Get GCS client (lazy load)."""
        self._initialize()
        return self._client
    
    @property
    def bucket(self):
        """Get GCS bucket (lazy load)."""
        self._initialize()
        return self._bucket
    
    def upload_scan_image(
        self,
        file_data: BytesIO,
        patient_id: str,
        scan_id: str,
        filename: str,
        content_type: str = 'image/jpeg'
    ) -> str:
        """
        Upload scan image to GCS.
        
        Args:
            file_data: Image file data
            patient_id: Patient ID (e.g., PT-001)
            scan_id: Scan ID (UUID)
            filename: Filename (e.g., original.jpg, gradcam.jpg)
            content_type: MIME type
            
        Returns:
            GCS URL (gs://bucket/path)
        """
        # Path: platform/raw_scans/patients/{patient_id}/{scan_id}/{filename}
        gcs_path = f"platform/raw_scans/patients/{patient_id}/{scan_id}/{filename}"
        
        blob = self.bucket.blob(gcs_path)
        file_data.seek(0)
        blob.upload_from_file(file_data, content_type=content_type)
        
        # Return GCS URL
        url = f"gs://{self.bucket_name}/{gcs_path}"
        
        logger.info(f"Uploaded: {url}")
        return url
    
    def get_signed_url(
        self, 
        gcs_url: str, 
        expiration: int = 3600
    ) -> str:
        """
        Generate signed URL for secure time-limited access.
        
        Args:
            gcs_url: GCS URL (gs://bucket/path) or just path
            expiration: URL expiration in seconds (default 1 hour)
            
        Returns:
            Signed HTTPS URL
        """
        self._initialize()  # Ensure initialized
        
        # Extract path from gs:// URL
        if gcs_url.startswith('gs://'):
            gcs_path = gcs_url.split(f'{self.bucket_name}/')[-1]
        else:
            gcs_path = gcs_url
        
        blob = self.bucket.blob(gcs_path)
        
        # Generate signed URL
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(seconds=expiration),
            method="GET"
        )
        
        return signed_url
    
    def download_image(self, gcs_url: str) -> BytesIO:
        """
        Download image from GCS.
        
        Args:
            gcs_url: GCS URL (gs://bucket/path)
            
        Returns:
            BytesIO with image data
        """
        self._initialize() 
        
        # Extract path
        if gcs_url.startswith('gs://'):
            gcs_path = gcs_url.split(f'{self.bucket_name}/')[-1]
        else:
            gcs_path = gcs_url
        
        blob = self.bucket.blob(gcs_path)
        
        if not blob.exists():
            raise NotFound(f"Image not found: {gcs_url}")
        
        image_data = BytesIO()
        blob.download_to_file(image_data)
        image_data.seek(0)
        
        return image_data
    
    def delete_image(self, gcs_url: str) -> bool:
        """Delete image from GCS."""
        try:
            self._initialize()  # Ensure initialized
            
            if gcs_url.startswith('gs://'):
                gcs_path = gcs_url.split(f'{self.bucket_name}/')[-1]
            else:
                gcs_path = gcs_url
            
            blob = self.bucket.blob(gcs_path)
            blob.delete()
            
            logger.info(f"Deleted: {gcs_url}")
            return True
        except Exception as e:
            logger.error(f"Delete failed: {e}")
            return False
    
    def list_scan_images(self, patient_id: str, scan_id: str) -> List[str]:
        """
        List all images for a scan.
        
        Returns:
            List of GCS URLs
        """
        self._initialize()  # Ensure initialized
        
        prefix = f"platform/raw_scans/patients/{patient_id}/{scan_id}/"
        blobs = self.client.list_blobs(self.bucket_name, prefix=prefix)
        return [f"gs://{self.bucket_name}/{blob.name}" for blob in blobs if not blob.name.endswith('/')]
    
    def copy_to_mlops_folder(
        self,
        source_url: str,
        diagnosis: str,
        patient_id: str,
        date_partition: Optional[str] = None
    ) -> str:
        """
        Copy image from platform/ to vision/ folder for MLOps.
        Server-side copy (very fast, no download/upload).
        
        Args:
            source_url: Source GCS URL (gs://bucket/platform/...)
            diagnosis: 'tb' or 'lung_cancer'
            patient_id: Patient ID
            date_partition: Optional date string (YYYY/MM/DD), defaults to today
            
        Returns:
            Destination GCS URL
        """
        self._initialize()  # Ensure initialized
        
        # Extract source path
        if source_url.startswith('gs://'):
            source_path = source_url.split(f'{self.bucket_name}/')[-1]
        else:
            source_path = source_url
        
        # Generate date partition
        if not date_partition:
            from datetime import datetime
            today = datetime.utcnow()
            date_partition = f"{today.year}/{today.month:02d}/{today.day:02d}"
        
        # Extract filename
        filename = Path(source_path).name
        
        # Destination: vision/raw/{diagnosis}/YYYY/MM/DD/{patient_id}_{filename}
        dest_path = f"vision/raw/{diagnosis}/{date_partition}/{patient_id}_{filename}"
        
        # Server-side copy (no data transfer!)
        source_blob = self.bucket.blob(source_path)
        self.bucket.copy_blob(source_blob, self.bucket, dest_path)
        
        dest_url = f"gs://{self.bucket_name}/{dest_path}"
        logger.info(f"Copied to MLOps: {dest_url}")
        
        return dest_url


# Singleton instance
gcs_storage = GCSStorageService()