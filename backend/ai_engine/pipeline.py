"""End-to-end RAG pipeline orchestrator for DocChat."""
import os
import sys
from typing import List, Optional

from backend.ai_engine.generator import RAGGenerator
from backend.ai_engine.loader import DocumentLoader
from backend.ai_engine.retriever import RAGRetriever
from backend.ai_engine.splitter import DocumentSplitter
from backend.ai_engine.vectorstore import VectorStoreManager
from backend.core.config import CONFIG, DocChatConfig
from backend.core.logger import get_logger

logger = get_logger("ai_engine.pipeline")


class DocChatPipeline:
    def __init__(self, config: Optional[DocChatConfig] = None):
        """Initializes the DocChat pipeline with loader, splitter, and vector manager."""
        self.config = config or CONFIG
        self.loader = DocumentLoader(supported_extensions=self.config.SUPPORTED_EXTENSIONS)
        self.splitter = DocumentSplitter(
            chunk_size=self.config.DEFAULT_CHUNK_SIZE,
            chunk_overlap=self.config.DEFAULT_CHUNK_OVERLAP,
            separators=self.config.SPLITTER_SEPARATORS
        )
        self.vector_manager = VectorStoreManager(
            model_name=self.config.EMBEDDING_MODEL_NAME,
            default_save_path=self.config.VECTOR_STORE_PATH
        )
        self.vectorstore = None
        self.retriever = None
        self.generator = None

        logger.info("DocChatPipeline initialized successfully.")

    def ingest(self, file_paths: List[str], force_reindex: bool = False) -> None:
        """Loads documents, splits into chunks, and builds/persists vector store."""
        if not force_reindex and os.path.exists(self.config.VECTOR_STORE_PATH):
            logger.info("Found existing vector store index. Loading from disk...")
            self.vectorstore = self.vector_manager.load_vectorstore()
            if self.vectorstore is not None:
                self._setup_retrieval_and_generation()
                return

        logger.info(f"Starting ingestion for {len(file_paths)} file(s)...")
        try:
            raw_docs = self.loader.load_multiple_documents(file_paths)
            if not raw_docs:
                raise ValueError("No documents loaded from the provided file paths.")

            chunks = self.splitter.split_documents(raw_docs)
            self.vectorstore = self.vector_manager.build_vectorstore(
                chunks=chunks,
                save_path=self.config.VECTOR_STORE_PATH
            )
            self._setup_retrieval_and_generation()
            logger.info("Ingestion and vector indexing completed successfully.")

        except Exception as e:
            logger.exception(f"Error during document ingestion: {e}")
            raise RuntimeError(f"Ingestion pipeline failed: {e}") from e

    def _setup_retrieval_and_generation(self) -> None:
        """Configures retriever and generator once vector store is initialized."""
        if self.vectorstore is None:
            raise ValueError("Vector store is not initialized.")

        rag_retriever = RAGRetriever(self.vectorstore)
        self.retriever = rag_retriever.get_retriever(
            search_type=self.config.DEFAULT_SEARCH_TYPE,
            k=self.config.DEFAULT_TOP_K
        )
        self.generator = RAGGenerator(
            retriever=self.retriever,
            model_name=self.config.GROQ_MODEL_NAME,
            temperature=self.config.LLM_TEMPERATURE
        )
        logger.info("Retriever and Generator components configured successfully.")

    def query(self, question: str) -> str:
        """Processes a question through the pipeline and returns the synthesized answer."""
        if not self.generator:
            error_msg = "Pipeline is not initialized. Run ingest() first or upload a document."
            logger.error(error_msg)
            return error_msg

        try:
            return self.generator.generate_answer(question)
        except Exception as e:
            logger.exception(f"Error querying DocChat pipeline: {e}")
            return f"An error occurred while answering your question: {e}"
