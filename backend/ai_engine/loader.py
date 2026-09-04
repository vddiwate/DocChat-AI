"""Document loading module for extracting text from PDF and TXT files."""
import os
from typing import List

from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader, TextLoader

from backend.core.config import CONFIG
from backend.core.logger import get_logger

logger = get_logger("ai_engine.loader")


class DocumentLoader:
    def __init__(self, supported_extensions: List[str] = None, encoding: str = None):
        """Initializes loader with supported extensions and character encoding."""
        self.supported_extensions = supported_extensions or CONFIG.SUPPORTED_EXTENSIONS
        self.encoding = encoding or CONFIG.DEFAULT_ENCODING

    def load_single_document(self, file_path: str) -> List[Document]:
        """Loads a single PDF or TXT document and returns Document objects."""
        if not os.path.exists(file_path):
            error_msg = f"Target file not found at path: {file_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self.supported_extensions:
            error_msg = f"Unsupported format '{ext}'. Allowed: {self.supported_extensions}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        try:
            logger.info(f"Loading document from: {file_path}")
            if ext == ".pdf":
                loader = PyPDFLoader(file_path)
            elif ext == ".txt":
                loader = TextLoader(file_path, encoding=self.encoding)
            else:
                raise ValueError(f"No loader configured for extension: {ext}")

            docs = loader.load()
            logger.info(f"Loaded {len(docs)} document page(s) from {os.path.basename(file_path)}")
            return docs

        except Exception as e:
            logger.exception(f"Error loading file {file_path}: {e}")
            raise RuntimeError(f"Document loading failed for {file_path}: {e}") from e

    def load_multiple_documents(self, file_paths: List[str]) -> List[Document]:
        """Loads multiple document files and aggregates all Document objects."""
        aggregated_docs: List[Document] = []
        for path in file_paths:
            try:
                docs = self.load_single_document(path)
                aggregated_docs.extend(docs)
            except Exception as e:
                logger.warning(f"Skipping {path} due to error: {e}")

        logger.info(f"Total documents loaded across {len(file_paths)} files: {len(aggregated_docs)}")
        return aggregated_docs
