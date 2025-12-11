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
        
        # Configure timeout - longer for cross-cloud communication
        timeout_config = httpx.Timeout(
            connect=300.0,   # 15 seconds to establish connection
            read=300.0,     # 2 minutes to read response
            write=300.0,     # 10 seconds to send request
            pool=300.0       # 10 seconds to get connection from pool
        )
        
        # Call GCP RAG endpoint with better error handling
        async with httpx.AsyncClient(timeout=timeout_config) as client:
            try:
                response = await client.post(
                    settings.RAG_ENDPOINT_URL,
                    json=rag_request,
                    headers={"Content-Type": "application/json"}
                )
                
                logger.info(f"RAG response status: {response.status_code}")
                
                if response.status_code != 200:
                    logger.error(f"RAG endpoint error: {response.status_code} - {response.text}")
                    
                    # Specific error messages based on status code
                    if response.status_code == 403:
                        raise HTTPException(
                            status_code=502,
                            detail="AI assistant access denied. Please contact administrator."
                        )
                    elif response.status_code == 404:
                        raise HTTPException(
                            status_code=502,
                            detail="AI assistant endpoint not found. Please contact administrator."
                        )
                    elif response.status_code >= 500:
                        raise HTTPException(
                            status_code=502,
                            detail="AI assistant is experiencing issues. Please try again later."
                        )
                    else:
                        raise HTTPException(
                            status_code=502,
                            detail="AI assistant temporarily unavailable. Please try again."
                        )
                
                result = response.json()
                
            except httpx.ConnectTimeout:
                logger.error("RAG endpoint connection timeout")
                raise HTTPException(
                    status_code=504,
                    detail="Could not connect to AI assistant. The service may be starting up. Please try again in 30 seconds."
                )
            except httpx.ReadTimeout:
                logger.error("RAG endpoint read timeout")
                raise HTTPException(
                    status_code=504,
                    detail="AI assistant is taking longer than expected. Please try a simpler question or try again later."
                )
            except httpx.WriteTimeout:
                logger.error("RAG endpoint write timeout")
                raise HTTPException(
                    status_code=504,
                    detail="Could not send request to AI assistant. Please try again."
                )
            except httpx.NetworkError as e:
                logger.error(f"RAG endpoint network error: {e}")
                raise HTTPException(
                    status_code=502,
                    detail="Network error connecting to AI assistant. Please check your connection and try again."
                )
        
        # Parse response
        if not result.get("predictions"):
            logger.error("Invalid RAG response format - no predictions")
            raise HTTPException(
                status_code=500, 
                detail="Invalid response from RAG model"
            )
        
        prediction = result["predictions"][0]
        
        # Handle both "success" key present or missing (some RAG endpoints don't include it)
        if "success" in prediction and not prediction.get("success"):
            error_msg = prediction.get("error", "RAG model returned an error")
            logger.error(f"RAG prediction failed: {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)
        
        # Get raw answer
        raw_answer = prediction.get("answer", "")
        
        if not raw_answer:
            logger.warning("RAG returned empty answer")
            raise HTTPException(
                status_code=500,
                detail="AI assistant returned empty response. Please try rephrasing your question."
            )
        
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
        
    except HTTPException:
        raise
    except httpx.TimeoutException as e:
        logger.error(f"RAG endpoint timeout: {e}")
        raise HTTPException(
            status_code=504,
            detail="The AI assistant is taking too long. Please try again."
        )
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
    3. Remove "Limitation:" section
    4. Extract sources from markdown links
    
    Returns:
        (cleaned_answer, sources_list)
    """
    # Step 1: Remove "References:" section and everything after it
    if "References:" in raw_answer or "**References:**" in raw_answer:
        answer = re.split(r'\*\*References:\*\*|References:', raw_answer)[0].strip()
    else:
        answer = raw_answer
    
    # Step 2: Remove "Important:" disclaimer
    if "Important:" in answer or "**Important:**" in answer:
        answer = re.split(r'\*\*Important:\*\*|Important:', answer)[0].strip()
    
    # Step 3: Remove "Limitation:" section
    if "Limitation:" in answer or "**Limitation:**" in answer:
        answer = re.split(r'\*\*Limitation:\*\*|Limitation:', answer)[0].strip()
    
    # Step 4: Remove trailing "---" markers
    answer = re.sub(r'\n*---\n*$', '', answer).strip()
    
    # Step 5: Extract sources from markdown links in the ORIGINAL answer
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
        # Use shorter timeout for health check
        timeout_config = httpx.Timeout(300.0)
        
        async with httpx.AsyncClient(timeout=timeout_config) as client:
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
                # Some RAG endpoints don't return "success" field
                success = result.get("predictions", [{}])[0].get("success", True)
            else:
                success = False
            
            return {
                "status": "healthy" if (is_healthy and success) else "unhealthy",
                "endpoint": settings.RAG_ENDPOINT_URL,
                "status_code": response.status_code,
                "rag_success": success
            }
    except httpx.TimeoutException:
        logger.error("RAG health check timeout")
        return {
            "status": "unhealthy",
            "endpoint": settings.RAG_ENDPOINT_URL,
            "error": "Timeout - service may be cold starting"
        }
    except httpx.ConnectError as e:
        logger.error(f"RAG health check connection error: {e}")
        return {
            "status": "unhealthy",
            "endpoint": settings.RAG_ENDPOINT_URL,
            "error": f"Connection error: {str(e)}"
        }
    except httpx.NetworkError as e:
        logger.error(f"RAG health check network error: {e}")
        return {
            "status": "unhealthy",
            "endpoint": settings.RAG_ENDPOINT_URL,
            "error": f"Network error: {str(e)}"
        }
    except Exception as e:
        logger.error(f"RAG health check failed: {e}")
        return {
            "status": "unhealthy",
            "endpoint": settings.RAG_ENDPOINT_URL,
            "error": str(e)
        }