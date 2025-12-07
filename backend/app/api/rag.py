"""
RAG Chat Endpoint - Proxy to GCP Vertex AI RAG Model
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import httpx
import os
import logging

from app.core.security import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

# GCP RAG Endpoint (from your deployment)
RAG_ENDPOINT_URL = os.getenv(
    "RAG_ENDPOINT_URL",
    "https://us-central1-medscanai-476500.cloudfunctions.net/rag-inference"
)


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    conversation_history: Optional[List[ChatMessage]] = []


class ChatResponse(BaseModel):
    response: str
    sources: Optional[List[str]] = []


@router.post("/chat", response_model=ChatResponse)
async def chat_with_rag(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Send user question to RAG model and return answer.
    Only accessible to authenticated users.
    """
    try:
        # Prepare request for your RAG endpoint
        rag_request = {
            "query": request.message,
            "conversation_history": [
                {"role": msg.role, "content": msg.content}
                for msg in (request.conversation_history or [])
            ]
        }
        
        # Call your GCP RAG endpoint
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                RAG_ENDPOINT_URL,
                json=rag_request,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code != 200:
                logger.error(f"RAG endpoint error: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=502,
                    detail="AI assistant temporarily unavailable"
                )
            
            result = response.json()
        
        # Extract response (adjust based on your RAG endpoint response format)
        answer = result.get("answer") or result.get("response") or result.get("result", "")
        sources = result.get("sources", [])
        
        logger.info(f"RAG query from {current_user.email}: {request.message[:50]}...")
        
        return ChatResponse(
            response=answer,
            sources=sources
        )
        
    except httpx.TimeoutException:
        logger.error("RAG endpoint timeout")
        raise HTTPException(
            status_code=504,
            detail="Request timeout. Please try again."
        )
    except Exception as e:
        logger.error(f"RAG chat error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get response from AI assistant"
        )


@router.get("/health")
async def check_rag_health():
    """Check if RAG endpoint is accessible."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{RAG_ENDPOINT_URL}/health")
            return {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "endpoint": RAG_ENDPOINT_URL
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "endpoint": RAG_ENDPOINT_URL,
            "error": str(e)
        }