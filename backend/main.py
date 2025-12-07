from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import auth, patient, radiologist, rag

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="MedScanAI - AI-Assisted Medical Imaging System"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(patient.router, prefix="/api/patient", tags=["Patient"])
app.include_router(radiologist.router, prefix="/api/radiologist", tags=["Radiologist"])
app.include_router(rag.router, prefix="/api/rag", tags=["RAG Chat"])

@app.get("/")
async def root():
    return {
        "message": "MedScan API",
        "version": settings.VERSION,
        "status": "active"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)