"""
RAG Chat Endpoint - Connects to GCP Cloud Run RAG Service
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
    Send user question to RAG model and return answer.
    """
    try:
        # Format request for RAG endpoint
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
        
        # Extract answer
        raw_answer = prediction.get("answer", "")
        
        # Extract references from the answer
        # Your RAG includes references in markdown format at the end
        sources = extract_sources(raw_answer)
        
        # Clean up answer (remove the duplicate text if present)
        clean_answer = clean_rag_response(raw_answer)
        
        # Get stats (optional)
        stats = prediction.get("stats", {})
        
        logger.info(f"✓ RAG response: {len(clean_answer)} chars, {len(sources)} sources")
        
        return ChatResponse(
            response=clean_answer,
            sources=sources,
            stats={
                "confidence": stats.get("avg_retrieval_score"),
                "num_docs": stats.get("num_retrieved_docs"),
                "tokens": stats.get("total_tokens")
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


def extract_sources(answer: str) -> List[Dict[str, str]]:
    """
    Extract reference links from RAG answer.
    Your RAG includes markdown links like: [Text](URL)
    """
    sources = []
    
    # Find all markdown links: [text](url)
    markdown_links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', answer)
    
    for title, url in markdown_links:
        if url.startswith('http'):  # Only include actual URLs
            sources.append({
                "title": title.strip(),
                "url": url.strip()
            })
    
    # Deduplicate
    seen_urls = set()
    unique_sources = []
    for source in sources:
        if source["url"] not in seen_urls:
            seen_urls.add(source["url"])
            unique_sources.append(source)
    
    return unique_sources[:5]  # Limit to top 5


def clean_rag_response(answer: str) -> str:
    """
    Clean up RAG response.
    Your RAG seems to repeat the answer multiple times, keep only the best version.
    """
    # Split by "Source:" markers to find repeated sections
    parts = answer.split("Source: Document")
    
    if len(parts) > 1:
        # Take the last version (usually most complete)
        # Find the section before **References:**
        if "**References:**" in answer:
            main_answer = answer.split("**References:**")[0].strip()
            references = "**References:**" + answer.split("**References:**")[1]
            
            # Get last paragraph before references (most refined version)
            paragraphs = main_answer.split("\n\n")
            # Filter out source citations
            clean_paragraphs = [p for p in paragraphs if not p.startswith("Source:")]
            
            if clean_paragraphs:
                # Take last substantial paragraph (usually the refined version)
                final_answer = clean_paragraphs[-1].strip()
                
                # Add references back
                return f"{final_answer}\n\n{references}"
        
        # Fallback: just take everything
        return answer.strip()
    
    return answer.strip()


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