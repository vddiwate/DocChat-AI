"""Chat controller exposing unified REST API endpoints for question answering and streaming."""
from typing import Union
from fastapi import APIRouter, Request, status
from fastapi.responses import StreamingResponse

from backend.api.models.schemas import ChatRequest, ChatResponse
from backend.api.services.chat_service import ChatService
from backend.core.logger import get_logger

logger = get_logger("controllers.chat")
router = APIRouter(prefix="/api/v1/chat", tags=["Chat & Q&A"])

chat_service = ChatService()


@router.post(
    "",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "JSON ChatResponse (when stream=false) or Server-Sent Events stream (when stream=true)",
            "content": {
                "application/json": {"schema": {"$ref": "#/components/schemas/ChatResponse"}},
                "text/event-stream": {"schema": {"type": "string", "example": "data: {\"token\": \"Hello\"}\n\ndata: [DONE]\n\n"}}
            }
        }
    }
)
async def chat_with_documents(request_body: ChatRequest, req: Request):
    """Unified chat endpoint supporting both real-time SSE token streaming and standard JSON completion."""
    request_id = getattr(req.state, "request_id", None)
    
    if request_body.stream:
        logger.info(f"[{request_id}] Initiating SSE stream for question: '{request_body.question}'")
        return StreamingResponse(
            chat_service.stream_answer_question(request_body.question, request_id=request_id),
            media_type="text/event-stream",
            headers={"X-Request-ID": request_id} if request_id else None
        )
    else:
        logger.info(f"[{request_id}] Generating synchronous answer for question: '{request_body.question}'")
        response = chat_service.answer_question(request_body.question)
        if request_id:
            response.request_id = request_id
        return response


@router.post("/stream", status_code=status.HTTP_200_OK, include_in_schema=False)
async def stream_chat_legacy_alias(request_body: ChatRequest, req: Request):
    """Backward-compatible alias for /api/v1/chat/stream pointing to unified handler."""
    request_body.stream = True
    return await chat_with_documents(request_body, req)
