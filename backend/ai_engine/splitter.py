"""Text chunking module for splitting documents into overlapping chunks."""
from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.core.config import CONFIG
from backend.core.logger import get_logger

logger = get_logger("ai_engine.splitter")


class DocumentSplitter:
    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None,
        separators: List[str] = None
    ):
        """Initializes the text splitter with chunk size, overlap, and separators."""
        self.chunk_size = chunk_size or CONFIG.DEFAULT_CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or CONFIG.DEFAULT_CHUNK_OVERLAP
        self.separators = separators or CONFIG.SPLITTER_SEPARATORS

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=self.separators
        )
        logger.info(f"Initialized DocumentSplitter (chunk_size={self.chunk_size}, chunk_overlap={self.chunk_overlap})")

    def split_documents(self, docs: List[Document]) -> List[Document]:
        """Splits a list of Document objects into overlapping text chunks."""
        if not docs:
            logger.warning("Empty document list provided to split_documents.")
            return []

        try:
            logger.info(f"Splitting {len(docs)} document(s)...")
            chunks = self.splitter.split_documents(docs)
            logger.info(f"Generated {len(chunks)} chunks from {len(docs)} document(s).")
            return chunks

        except Exception as e:
            logger.exception(f"Error during document splitting: {e}")
            raise RuntimeError(f"Document splitting failed: {e}") from e
