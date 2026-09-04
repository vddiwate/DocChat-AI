"""Chat service for coordinating vector retrieval and Groq LLM answer generation."""
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

    def _get_generator(self) -> RAGGenerator:
        """Lazily initializes and returns the RAGGenerator instance."""
        if self._generator is None:
            vectorstore = self.vector_manager.load_vectorstore()
            if vectorstore is None:
                logger.error("Chat failed: Vector store not found on disk.")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Vector store is empty. Please upload at least one document first via /api/v1/documents/upload."
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

    def answer_question(self, question: str) -> ChatResponse:
        """Processes user question through the RAG pipeline and returns structured answer."""
        if not question or not question.strip():
            logger.warning("Empty question provided to ChatService.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Question field cannot be empty."
            )

        try:
            logger.info(f"Generating answer for question: '{question}'")
            generator = self._get_generator()
            answer = generator.generate_answer(question)
            logger.info("Answer generated successfully.")

            return ChatResponse(
                question=question,
                answer=answer,
                status="success"
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Error during chat generation for '{question}': {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An error occurred during answer generation: {e}"
            ) from e
