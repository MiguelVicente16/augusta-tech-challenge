"""
FastAPI router for chatbot endpoints

Provides REST API endpoints for:
- Chatbot conversations with streaming support
- Chat history management
- Cost tracking
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ...agents.chatbot_agent import ChatbotService
from ...database.service import DatabaseService
from ..dependencies import get_db_service

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/chatbot", tags=["chatbot"])


# ============================================================================
# Request/Response Models
# ============================================================================

class ChatMessage(BaseModel):
    """Single chat message"""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    message: str = Field(..., description="User's message", min_length=1)
    conversation_history: Optional[List[ChatMessage]] = Field(
        default=None,
        description="Previous messages in conversation (optional)"
    )
    stream: bool = Field(
        default=True,
        description="Whether to stream the response (default: True for better UX)"
    )


class ChatResponse(BaseModel):
    """Response model for non-streaming chat"""
    response: str = Field(..., description="Agent's response")
    tokens_used: Optional[int] = Field(None, description="Tokens used in this request")
    cost: Optional[float] = Field(None, description="Estimated cost in USD")


class ChatStatsResponse(BaseModel):
    """Response model for chat statistics"""
    total_messages: int
    average_cost_per_message: float
    total_cost: float


# ============================================================================
# Chatbot Endpoints
# ============================================================================

@router.post("/chat")
async def chat(
    request: ChatRequest,
    db_service: DatabaseService = Depends(get_db_service)
):
    """
    Chat with the AI assistant about incentives, companies, and matches.

    **Features:**
    - Intelligent tool selection (exact queries vs semantic search)
    - Streaming responses for better UX (<20s first chunk)
    - Cost-optimized (<$15/1k messages)
    - Bilingual support (Portuguese/English)

    **Example queries:**
    - "Quais são os incentivos para tecnologia?"
    - "Show me company XYZ"
    - "What are the top matches for incentive 123?"
    - "Find companies in renewable energy sector"

    **Streaming:**
    When `stream=true` (default), returns Server-Sent Events (text/event-stream).
    When `stream=false`, returns complete response as JSON.

    Args:
        request: Chat request with message and optional history

    Returns:
        Streaming response (text/event-stream) or JSON response
    """
    try:
        # Initialize chatbot service
        chatbot = ChatbotService(db_service)

        # Convert conversation history to Pydantic AI format if provided
        message_history = None
        if request.conversation_history:
            message_history = [
                {
                    "role": msg.role,
                    "content": msg.content
                }
                for msg in request.conversation_history
            ]

        if request.stream:
            # Streaming response for better UX
            async def generate():
                try:
                    import json
                    async for chunk in chatbot.run_stream(
                        request.message,
                        conversation_history=message_history
                    ):
                        # Server-Sent Events format with type discrimination
                        chunk_type = chunk.get("type")

                        if chunk_type == "text":
                            # Text chunk - encode as JSON to handle newlines properly
                            content = chunk.get("content", "")
                            content_json = json.dumps(content)
                            yield f"data: {content_json}\n\n"

                        elif chunk_type == "tool_call":
                            # Tool call event - stream to frontend
                            tool_data = chunk.get("content", {})
                            yield f"data: __TOOL_CALL__:{json.dumps(tool_data)}\n\n"

                        elif chunk_type == "tool_result":
                            # Tool result event - stream to frontend
                            tool_data = chunk.get("content", {})
                            yield f"data: __TOOL_RESULT__:{json.dumps(tool_data)}\n\n"

                        elif chunk_type == "metadata":
                            # Metadata chunk - send as JSON with special prefix
                            metadata = chunk.get("content", {})
                            yield f"data: __METADATA__:{json.dumps(metadata)}\n\n"

                    # Send [DONE] signal
                    yield "data: [DONE]\n\n"

                except Exception as e:
                    logger.error(f"Streaming error: {e}")
                    yield f"data: Error: {str(e)}\n\n"
                    yield "data: [DONE]\n\n"

            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"  # Disable nginx buffering
                }
            )

        else:
            # Non-streaming response
            response = await chatbot.run(
                request.message,
                conversation_history=message_history
            )

            return ChatResponse(
                response=response,
                tokens_used=None,  # TODO: Add token tracking
                cost=None  # TODO: Add cost tracking
            )

    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/health")
async def chatbot_health(db_service: DatabaseService = Depends(get_db_service)):
    """
    Check chatbot health and readiness.

    Verifies:
    - Database connection
    - Embeddings availability
    - Model configuration

    Returns:
        Health status information
    """
    try:
        # Check database
        count = await db_service.count_incentives()

        # Check embeddings (via vector_db)
        from ...ai.vector_db import VectorDB
        vector_db = VectorDB(db_service.pool)
        stats = await vector_db.get_stats()

        return {
            "status": "healthy",
            "database": "connected",
            "incentives_count": count,
            "companies_with_embeddings": stats['companies_with_embeddings'],
            "incentives_with_embeddings": stats['incentives_with_embeddings'],
            "message": "Chatbot ready for queries"
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@router.post("/test")
async def test_chatbot(db_service: DatabaseService = Depends(get_db_service)):
    """
    Test chatbot with a simple query.

    Returns:
        Test response to verify chatbot is working
    """
    try:
        chatbot = ChatbotService(db_service)
        response = await chatbot.run("Olá! Quantos incentivos existem no sistema?")

        return {
            "status": "success",
            "test_query": "Olá! Quantos incentivos existem no sistema?",
            "response": response
        }

    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")
