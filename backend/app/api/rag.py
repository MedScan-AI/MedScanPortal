"""
RAG Chat Endpoint
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import httpx
import logging
import re
import uuid
from datetime import datetime, timedelta

from app.core.config import settings
from app.core.security import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory job storage (use Redis in production)
rag_jobs = {}

class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    conversation_history: Optional[List[ChatMessage]] = []


class ChatResponse(BaseModel):
    response: str
    sources: Optional[List[Dict[str, str]]] = []
    stats: Optional[Dict[str, Any]] = None


class JobStartResponse(BaseModel):
    job_id: str
    status: str
    message: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: Optional[int] = None
    result: Optional[ChatResponse] = None
    error: Optional[str] = None


def clean_rag_response(prediction: Dict) -> tuple[str, List[Dict[str, str]]]:
    """
    Clean RAG response based on ACTUAL endpoint structure.
    
    Response structure from endpoint:
    {
      "answer": "Main text...Limitations:...\\n\\n**References:**\\n1. [Title](URL)\\n\\n---\\n**Important:**...",
      "stats": {
        "sources": [
          {"rank": 1, "title": "...", "link": "...", "score": 0.85},
          ...
        ]
      }
    }
    
    Returns:
        (cleaned_answer, sources_list)
    """
    
    raw_answer = prediction.get("answer", "")
    stats = prediction.get("stats", {})
    
    if not raw_answer:
        return "", []
    
    # Step 1: Remove everything after "Limitations:"
    # Pattern: "Limitations: While the provided documents..."
    if "Limitations:" in raw_answer:
        answer = raw_answer.split("Limitations:")[0].strip()
    elif "Limitation:" in raw_answer:
        answer = raw_answer.split("Limitation:")[0].strip()
    else:
        answer = raw_answer
    
    # Step 2: Remove "**References:**" section (everything after it)
    if "**References:**" in answer:
        answer = answer.split("**References:**")[0].strip()
    elif "References:" in answer:
        answer = answer.split("References:")[0].strip()
    
    # Step 3: Remove "---" separator line
    answer = re.sub(r'\n*---+\n*', '', answer).strip()
    
    # Step 4: Remove "**Important:**" disclaimer section
    if "**Important:**" in answer:
        answer = answer.split("**Important:**")[0].strip()
    elif "Important:" in answer:
        answer = answer.split("Important:")[0].strip()
    
    # Step 5: Remove any "Answer:" labels at the start
    answer = re.sub(r'^(Answer:|Answer\s*:)\s*', '', answer, flags=re.IGNORECASE).strip()
    
    # Step 6: Remove duplicate paragraphs (paragraph-level deduplication)
    paragraphs = answer.split('\n\n')
    seen_paragraphs = set()
    unique_paragraphs = []
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        # Normalize for comparison
        normalized = ' '.join(para.lower().split())
        
        if normalized not in seen_paragraphs:
            seen_paragraphs.add(normalized)
            unique_paragraphs.append(para)
    
    answer = '\n\n'.join(unique_paragraphs)
    
    # Step 7: Remove repetitive sentences within text
    sentences = re.split(r'(?<=[.!?])\s+', answer)
    seen_sentences = set()
    unique_sentences = []
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        
        normalized = ' '.join(sentence.lower().split())
        
        if normalized not in seen_sentences:
            seen_sentences.add(normalized)
            unique_sentences.append(sentence)
    
    answer = ' '.join(unique_sentences)
    
    # Step 8: Remove incomplete sentence at the end
    if answer and answer[-1] not in '.!?':
        last_period = max(
            answer.rfind('.'),
            answer.rfind('!'),
            answer.rfind('?')
        )
        
        if last_period > 0:
            answer = answer[:last_period + 1].strip()
    
    # Step 9: Final whitespace cleanup
    answer = re.sub(r'\s+', ' ', answer)  # Multiple spaces to single
    answer = re.sub(r'\n{3,}', '\n\n', answer)  # Max 2 newlines
    answer = answer.strip()
    
    # Step 10: Extract sources from stats.sources (structured data!)
    sources = []
    sources_data = stats.get("sources", [])
    
    for source in sources_data[:5]:  # Limit to 5 sources
        title = source.get("title", "").strip()
        link = source.get("link", "").strip()
        
        if title and link and link.startswith('http'):
            # Clean title (remove extra characters)
            title = title.replace('__', '').strip()
            title = re.sub(r'^\d+\.\s*', '', title)  # Remove leading numbers
            
            # Remove "-Tuberculosis-Tuberculosis" type duplicates in title
            title = re.sub(r'-(\w+)-\1', r'-\1', title)
            
            sources.append({
                "title": title,
                "url": link
            })
    
    # If no sources in stats, try extracting from markdown links in original answer
    if not sources:
        markdown_links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', raw_answer)
        seen_urls = set()
        
        for title, url in markdown_links:
            if url.startswith('http') and url not in seen_urls:
                clean_title = title.strip().replace('__', '').strip()
                clean_title = re.sub(r'^\d+\.\s*', '', clean_title)
                sources.append({"title": clean_title, "url": url.strip()})
                seen_urls.add(url)
        
        sources = sources[:5]
    
    return answer, sources


async def process_rag_job(job_id: str, message: str):
    """Background task to process RAG request."""
    try:
        logger.info(f"[Job {job_id}] Starting RAG processing...")
        
        rag_jobs[job_id]["status"] = "processing"
        rag_jobs[job_id]["progress"] = 20
        
        rag_request = {"instances": [{"query": message}]}
        
        timeout_config = httpx.Timeout(
            connect=30.0,
            read=300.0,
            write=30.0,
            pool=30.0
        )
        
        rag_jobs[job_id]["progress"] = 40
        
        async with httpx.AsyncClient(timeout=timeout_config) as client:
            response = await client.post(
                settings.RAG_ENDPOINT_URL,
                json=rag_request,
                headers={"Content-Type": "application/json"}
            )
            
            rag_jobs[job_id]["progress"] = 80
            
            if response.status_code != 200:
                raise Exception(f"RAG endpoint returned {response.status_code}")
            
            result = response.json()
        
        if not result.get("predictions"):
            raise Exception("Invalid RAG response - no predictions")
        
        prediction = result["predictions"][0]
        
        # Check success flag
        if "success" in prediction and not prediction.get("success"):
            error_msg = prediction.get("error", "RAG processing failed")
            raise Exception(error_msg)
        
        # Clean response using CORRECT extraction
        cleaned_answer, sources = clean_rag_response(prediction)
        
        if not cleaned_answer:
            raise Exception("Cleaning produced empty answer")
        
        logger.info(f"[Job {job_id}] Cleaned: {len(cleaned_answer)} chars, {len(sources)} sources")
        
        # Store result
        rag_jobs[job_id]["status"] = "completed"
        rag_jobs[job_id]["progress"] = 100
        rag_jobs[job_id]["result"] = ChatResponse(
            response=cleaned_answer,
            sources=sources,
            stats={
                "confidence": prediction.get("stats", {}).get("avg_retrieval_score"),
                "num_docs": prediction.get("stats", {}).get("num_retrieved_docs")
            }
        )
        rag_jobs[job_id]["completed_at"] = datetime.utcnow()
        
        logger.info(f"[Job {job_id}] Completed successfully")
        
    except Exception as e:
        logger.error(f"[Job {job_id}] ✗ Failed: {e}")
        rag_jobs[job_id]["status"] = "failed"
        rag_jobs[job_id]["error"] = str(e)
        rag_jobs[job_id]["completed_at"] = datetime.utcnow()


@router.post("/chat/start", response_model=JobStartResponse)
async def start_chat_job(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Start RAG processing in background."""
    job_id = str(uuid.uuid4())
    
    rag_jobs[job_id] = {
        "status": "pending",
        "progress": 0,
        "created_at": datetime.utcnow(),
        "user_id": str(current_user.id),
        "message": request.message
    }
    
    background_tasks.add_task(process_rag_job, job_id, request.message)
    
    logger.info(f"[Job {job_id}] Created for user {current_user.email}")
    
    return JobStartResponse(
        job_id=job_id,
        status="pending",
        message="RAG processing started"
    )


@router.get("/chat/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get status of RAG processing job."""
    if job_id not in rag_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = rag_jobs[job_id]
    
    if job["user_id"] != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    created_at = job["created_at"]
    if datetime.utcnow() - created_at > timedelta(minutes=10):
        job["status"] = "failed"
        job["error"] = "Job expired"
    
    return JobStatusResponse(
        job_id=job_id,
        status=job["status"],
        progress=job.get("progress"),
        result=job.get("result"),
        error=job.get("error")
    )


@router.post("/chat", response_model=ChatResponse)
async def chat_with_rag(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)
):
    """Legacy synchronous endpoint."""
    try:
        rag_request = {"instances": [{"query": request.message}]}
        
        logger.info(f"RAG query from {current_user.email}: '{request.message[:100]}'")
        
        timeout_config = httpx.Timeout(
            connect=10.0,
            read=50.0,
            write=10.0,
            pool=10.0
        )
        
        async with httpx.AsyncClient(timeout=timeout_config) as client:
            try:
                response = await client.post(
                    settings.RAG_ENDPOINT_URL,
                    json=rag_request,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code != 200:
                    raise HTTPException(status_code=502, detail="AI assistant temporarily unavailable")
                
                result = response.json()
                
            except httpx.TimeoutException:
                raise HTTPException(
                    status_code=504,
                    detail="Response taking too long. Use /chat/start endpoint."
                )
        
        if not result.get("predictions"):
            raise HTTPException(status_code=500, detail="Invalid response from RAG model")
        
        prediction = result["predictions"][0]
        
        if "success" in prediction and not prediction.get("success"):
            error_msg = prediction.get("error", "RAG processing failed")
            raise HTTPException(status_code=500, detail=error_msg)
        
        # Use CORRECT extraction
        cleaned_answer, sources = clean_rag_response(prediction)
        
        if not cleaned_answer:
            raise HTTPException(status_code=500, detail="Cleaning produced empty answer")
        
        logger.info(f"RAG response: {len(cleaned_answer)} chars, {len(sources)} sources")
        
        return ChatResponse(
            response=cleaned_answer,
            sources=sources,
            stats={
                "confidence": prediction.get("stats", {}).get("avg_retrieval_score"),
                "num_docs": prediction.get("stats", {}).get("num_retrieved_docs")
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"RAG chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get response from AI assistant")


@router.get("/health")
async def check_rag_health():
    """Check if RAG endpoint is accessible."""
    try:
        timeout_config = httpx.Timeout(10.0)
        
        async with httpx.AsyncClient(timeout=timeout_config) as client:
            test_request = {"instances": [{"query": "test"}]}
            
            response = await client.post(
                settings.RAG_ENDPOINT_URL,
                json=test_request,
                headers={"Content-Type": "application/json"}
            )
            
            is_healthy = response.status_code == 200
            
            return {
                "status": "healthy" if is_healthy else "unhealthy",
                "endpoint": settings.RAG_ENDPOINT_URL,
                "status_code": response.status_code
            }
    except Exception as e:
        logger.error(f"RAG health check failed: {e}")
        return {
            "status": "unhealthy",
            "endpoint": settings.RAG_ENDPOINT_URL,
            "error": str(e)
        }