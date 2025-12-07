from pydantic_settings import BaseSettings
from typing import List, Optional
import os
import json

class Settings(BaseSettings):
    # Project Info
    PROJECT_NAME: str = "MedScanAI API"
    VERSION: str = "1.0.0"
    
    # Security
    SECRET_KEY: str = "your-secret-key-here-change-in-production-09876543210987654321"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Database - Supabase PostgreSQL
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/postgres"
    
    # CORS 
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    ]
    
    # File Storage
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    
    # AI Model Settings
    MODEL_PATH: str = "./models"
    GRADCAM_OUTPUT_DIR: str = "./gradcam_outputs"

    # GCS Storage (SAME AS DATA PIPELINE)
    GCP_PROJECT_ID: str = "medscanai"
    GCS_BUCKET_NAME: str = "medscan-pipeline-medscanai"
    GOOGLE_APPLICATION_CREDENTIALS: str = "/Users/username/gcp-service-account.json"

    # Email Alerts
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    ALERT_EMAIL_RECIPIENTS: List[str] = []

    # RAG Model
    RAG_ENDPOINT_URL: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"
        
        @classmethod
        def parse_env_var(cls, field_name: str, raw_val: str):
            """Parse environment variables, especially JSON arrays"""
            if field_name == 'ALLOWED_ORIGINS':
                if raw_val.startswith('['):
                    try:
                        return json.loads(raw_val)
                    except json.JSONDecodeError:
                        pass
            return raw_val

settings = Settings()