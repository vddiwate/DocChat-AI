"""Chat controller exposing REST API endpoints for question answering."""
from fastapi import APIRouter, status

from backend.api.models.schemas import ChatRequest, ChatResponse
from backend.api.services.chat_service import ChatService
from backend.core.logger import get_logger

logger = get_logger("controllers.chat")
router = APIRouter(prefix="/api/v1/chat", tags=["Chat & Q&A"])

chat_service = ChatService()


@router.post("", response_model=ChatResponse, status_code=status.HTTP_200_OK)
def chat_with_documents(request: ChatRequest):
    """Receives user question and returns synthesized answer from uploaded documents."""
    logger.info(f"Received chat request: '{request.question}'")
    return chat_service.answer_question(request.question)
