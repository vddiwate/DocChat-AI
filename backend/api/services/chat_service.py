"""Chat service for coordinating vector retrieval and Groq LLM answer generation."""
import json
from typing import Generator, Optional
from fastapi import HTTPException, status

from backend.ai_engine.generator import RAGGenerator
from backend.ai_engine.retriever import RAGRetriever
from backend.ai_engine.vectorstore import VectorStoreManager
from backend.api.models.schemas import ChatResponse
from backend.core.config import CONFIG
from backend.core.logger import get_logger

logger = get_logger("services.chat")


class ChatService:
    def __init__(self):
        """Initializes chat service with vector store manager and lazy generator."""
        self.vector_manager = VectorStoreManager()
        self._generator = None

    def get_generator(self, force_reload: bool = False) -> RAGGenerator:
        """Initializes or reloads the RAGGenerator instance with the latest vector store."""
        if self._generator is None or force_reload:
            vectorstore = self.vector_manager.load_vectorstore()
            if vectorstore is None:
                logger.error("Chat failed: Vector store not found on disk.")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error_code": "VECTOR_STORE_EMPTY",
                        "message": "Vector store is empty. Please upload at least one document (.pdf or .txt) first."
                    }
                )

            rag_retriever = RAGRetriever(vectorstore)
            retriever_instance = rag_retriever.get_retriever(
                search_type=CONFIG.DEFAULT_SEARCH_TYPE,
                k=CONFIG.DEFAULT_TOP_K
            )
            self._generator = RAGGenerator(
                retriever=retriever_instance,
                model_name=CONFIG.GROQ_MODEL_NAME,
                temperature=CONFIG.LLM_TEMPERATURE
            )
            logger.info("RAGGenerator wired successfully in ChatService.")

        return self._generator

    def answer_question(self, question: str, request_id: Optional[str] = None) -> ChatResponse:
        """Processes user question through the RAG pipeline and returns structured answer."""
        req_tag = f"[{request_id}] " if request_id else ""
        if not question or not question.strip():
            logger.warning(f"{req_tag}Empty question provided to ChatService.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "EMPTY_QUESTION",
                    "message": "Question field cannot be empty."
                }
            )

        try:
            logger.info(f"{req_tag}Generating answer for question: '{question}'")
            generator = self.get_generator()
            answer = generator.generate_answer(question)
            logger.info(f"{req_tag}Answer generated successfully.")

            return ChatResponse(
                question=question,
                answer=answer,
                status="success",
                request_id=request_id
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"{req_tag}Error during chat generation for '{question}': {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error_code": "LLM_GENERATION_FAILED",
                    "message": f"Failed to generate answer: {e}"
                }
            ) from e

    def stream_answer_question(self, question: str, request_id: Optional[str] = None) -> Generator[str, None, None]:
        """Streams answer chunks formatted as Server-Sent Events (SSE) data frames with keep-alive and error frames."""
        req_tag = f"[{request_id}] " if request_id else ""
        if not question or not question.strip():
            err_frame = json.dumps({
                "error": {
                    "code": "EMPTY_QUESTION",
                    "message": "Question field cannot be empty.",
                    "request_id": request_id
                }
            })
            yield f"data: {err_frame}\n\n"
            return

        try:
            logger.info(f"{req_tag}Initiating streaming for question: '{question}'")
            generator = self.get_generator()
            for token in generator.stream_answer(question):
                payload = json.dumps({"token": token, "request_id": request_id})
                yield f"data: {payload}\n\n"

            yield "data: [DONE]\n\n"
            logger.info(f"{req_tag}Streaming completed successfully for question: '{question}'")

        except HTTPException as he:
            err_msg = he.detail.get("message") if isinstance(he.detail, dict) else str(he.detail)
            err_code = he.detail.get("error_code", "CHAT_ERROR") if isinstance(he.detail, dict) else "CHAT_ERROR"
            logger.warning(f"{req_tag}HTTP exception in streaming: {err_msg}")
            err_frame = json.dumps({
                "error": {
                    "code": err_code,
                    "message": err_msg,
                    "request_id": request_id
                }
            })
            yield f"data: {err_frame}\n\n"
        except Exception as e:
            logger.exception(f"{req_tag}Error during streaming for '{question}': {e}")
            err_frame = json.dumps({
                "error": {
                    "code": "STREAMING_ERROR",
                    "message": str(e),
                    "request_id": request_id
                }
            })
            yield f"data: {err_frame}\n\n"
