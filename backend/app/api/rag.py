"""
RAG Chat Endpoint - Connects to GCP Cloud Run RAG Service
Cleans response: removes References section and Important notice
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import httpx
import logging
import re

from app.core.config import settings
from app.core.security import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


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


@router.post("/chat", response_model=ChatResponse)
async def chat_with_rag(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Send user question to RAG model and return cleaned answer.
    """
    try:
        rag_request = {
            "instances": [
                {
                    "query": request.message
                }
            ]
        }
        
        logger.info(f"RAG query from {current_user.email}: '{request.message[:100]}'")
        
        # Call GCP RAG endpoint
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                settings.RAG_ENDPOINT_URL,
                json=rag_request,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code != 200:
                logger.error(f"RAG endpoint error: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=502,
                    detail="AI assistant temporarily unavailable. Please try again."
                )
            
            result = response.json()
        
        # Parse response
        if not result.get("predictions"):
            raise HTTPException(status_code=500, detail="Invalid response from RAG model")
        
        prediction = result["predictions"][0]
        
        if not prediction.get("success"):
            error_msg = prediction.get("error", "RAG model returned an error")
            logger.error(f"RAG prediction failed: {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)
        
        # Get raw answer
        raw_answer = prediction.get("answer", "")
        
        # Clean the response
        cleaned_answer, sources = clean_rag_response(raw_answer)
        
        # Get stats
        stats = prediction.get("stats", {})
        
        logger.info(f"✓ RAG response: {len(cleaned_answer)} chars, {len(sources)} sources")
        
        return ChatResponse(
            response=cleaned_answer,
            sources=sources,
            stats={
                "confidence": stats.get("avg_retrieval_score"),
                "num_docs": stats.get("num_retrieved_docs")
            } if stats else None
        )
        
    except httpx.TimeoutException:
        logger.error("RAG endpoint timeout")
        raise HTTPException(
            status_code=504,
            detail="The AI assistant is taking too long. Please try again."
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"RAG chat error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to get response from AI assistant."
        )


def clean_rag_response(raw_answer: str) -> tuple[str, List[Dict[str, str]]]:
    """
    Clean RAG response:
    1. Remove "References:" section
    2. Remove "Important:" disclaimer
    3. Extract sources from markdown links
    
    Returns:
        (cleaned_answer, sources_list)
    """
    # Step 1: Remove "References:" section and everything after it
    if "References:" in raw_answer or "**References:**" in raw_answer:
        # Split at References and take only the part before it
        answer = re.split(r'\*\*References:\*\*|References:', raw_answer)[0].strip()
    else:
        answer = raw_answer
    
    # Step 2: Remove "Important:" disclaimer
    if "Important:" in answer or "**Important:**" in answer:
        answer = re.split(r'\*\*Important:\*\*|Important:', answer)[0].strip()
    
    # Step 3: Remove trailing "---" markers
    answer = re.sub(r'\n*---\n*$', '', answer).strip()
    
    # Step 4: Extract sources from markdown links in the ORIGINAL answer
    # Format: [Title](URL)
    sources = []
    markdown_links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', raw_answer)
    
    seen_urls = set()
    for title, url in markdown_links:
        # Only include actual URLs (start with http)
        if url.startswith('http') and url not in seen_urls:
            # Clean title (remove underscores, numbers)
            clean_title = title.strip().replace('__', '').strip()
            clean_title = re.sub(r'^\d+\.\s*', '', clean_title)  # Remove leading numbers
            
            sources.append({
                "title": clean_title,
                "url": url.strip()
            })
            seen_urls.add(url)
    
    # Limit to 5 sources
    return answer, sources[:5]


@router.get("/health")
async def check_rag_health():
    """Check if RAG endpoint is accessible."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            test_request = {
                "instances": [{"query": "test"}]
            }
            
            response = await client.post(
                settings.RAG_ENDPOINT_URL,
                json=test_request,
                headers={"Content-Type": "application/json"}
            )
            
            is_healthy = response.status_code == 200
            
            if is_healthy:
                result = response.json()
                success = result.get("predictions", [{}])[0].get("success", False)
            else:
                success = False
            
            return {
                "status": "healthy" if (is_healthy and success) else "unhealthy",
                "endpoint": settings.RAG_ENDPOINT_URL,
                "status_code": response.status_code,
                "rag_success": success
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "endpoint": settings.RAG_ENDPOINT_URL,
            "error": str(e)
        }