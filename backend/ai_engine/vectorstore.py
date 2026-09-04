"""Vector store management module for embedding computation and FAISS index persistence."""
import os
from typing import List, Optional

from langchain_core.documents import Document
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

from backend.core.config import CONFIG
from backend.core.logger import get_logger

logger = get_logger("ai_engine.vectorstore")


class VectorStoreManager:
    def __init__(self, model_name: str = None, default_save_path: str = None):
        """Initializes the vector store manager with model name and storage path."""
        self.model_name = model_name or CONFIG.EMBEDDING_MODEL_NAME
        self.default_save_path = default_save_path or CONFIG.VECTOR_STORE_PATH
        self._embedding_model: Optional[HuggingFaceEmbeddings] = None
        self._vectorstore: Optional[FAISS] = None

    def get_embedding_model(self) -> HuggingFaceEmbeddings:
        """Lazily initializes and returns the HuggingFace embedding model."""
        if self._embedding_model is None:
            try:
                logger.info(f"Initializing embedding model: {self.model_name}")
                self._embedding_model = HuggingFaceEmbeddings(model_name=self.model_name)
                logger.info("Embedding model initialized successfully.")
            except Exception as e:
                logger.exception(f"Failed to initialize embedding model '{self.model_name}': {e}")
                raise RuntimeError(f"Embedding initialization error: {e}") from e

        return self._embedding_model

    def build_vectorstore(self, chunks: List[Document], save_path: str = None) -> FAISS:
        """Creates and persists a FAISS vector store from document chunks."""
        if not chunks:
            error_msg = "Cannot build vector store with an empty list of chunks."
            logger.error(error_msg)
            raise ValueError(error_msg)

        target_path = save_path or self.default_save_path
        embeddings = self.get_embedding_model()

        try:
            logger.info(f"Building FAISS vector store for {len(chunks)} chunks...")
            vectorstore = FAISS.from_documents(chunks, embeddings)
            self._vectorstore = vectorstore
            logger.info("FAISS vector store built successfully.")

            if target_path:
                vectorstore.save_local(target_path)
                logger.info(f"FAISS index saved to disk at: {target_path}")

            return vectorstore

        except Exception as e:
            logger.exception(f"Error creating vector store: {e}")
            raise RuntimeError(f"Vector store creation failed: {e}") from e

    def load_vectorstore(self, load_path: str = None) -> Optional[FAISS]:
        """Loads an existing FAISS vector store index from local disk."""
        target_path = load_path or self.default_save_path

        if not os.path.exists(target_path):
            logger.warning(f"Vector store not found at: {target_path}")
            return None

        embeddings = self.get_embedding_model()
        try:
            logger.info(f"Loading FAISS vector store from: {target_path}")
            vectorstore = FAISS.load_local(
                target_path,
                embeddings,
                allow_dangerous_deserialization=True
            )
            self._vectorstore = vectorstore
            logger.info("FAISS vector store loaded successfully.")
            return vectorstore

        except Exception as e:
            logger.exception(f"Error loading vector store from {target_path}: {e}")
            raise RuntimeError(f"Vector store loading error: {e}") from e
