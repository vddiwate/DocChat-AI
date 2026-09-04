"""Document service handling file persistence, document chunking, and vector store indexing."""
import os
import shutil
from fastapi import HTTPException, UploadFile, status

from backend.ai_engine.loader import DocumentLoader
from backend.ai_engine.splitter import DocumentSplitter
from backend.ai_engine.vectorstore import VectorStoreManager
from backend.api.models.schemas import DocumentUploadResponse
from backend.core.config import CONFIG
from backend.core.logger import get_logger

logger = get_logger("services.document")


class DocumentService:
    def __init__(self):
        """Initializes the document service with loader, splitter, and vector manager instances."""
        self.loader = DocumentLoader()
        self.splitter = DocumentSplitter()
        self.vector_manager = VectorStoreManager()

    def process_uploaded_document(self, file: UploadFile) -> DocumentUploadResponse:
        """Saves an uploaded file to disk and indexes its chunks into the FAISS vector store."""
        if not file.filename:
            logger.error("Upload failed: Missing filename.")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No filename provided.")

        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in CONFIG.SUPPORTED_EXTENSIONS:
            logger.warning(f"Upload rejected: Unsupported extension '{ext}'.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format '{ext}'. Allowed: {CONFIG.SUPPORTED_EXTENSIONS}"
            )

        os.makedirs(CONFIG.UPLOAD_DIR, exist_ok=True)
        destination_path = os.path.join(CONFIG.UPLOAD_DIR, file.filename)

        try:
            logger.info(f"Saving uploaded file to: {destination_path}")
            with open(destination_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            file_size = os.path.getsize(destination_path)
            logger.info(f"File '{file.filename}' saved successfully. Size: {file_size} bytes.")

            docs = self.loader.load_single_document(destination_path)
            chunks = self.splitter.split_documents(docs)

            vectorstore = self.vector_manager.load_vectorstore()
            if vectorstore is None:
                logger.info("Vector store not found. Building fresh index...")
                self.vector_manager.build_vectorstore(chunks, save_path=CONFIG.VECTOR_STORE_PATH)
            else:
                logger.info("Appending new document chunks to existing vector store...")
                vectorstore.add_documents(chunks)
                vectorstore.save_local(CONFIG.VECTOR_STORE_PATH)

            logger.info(f"Successfully indexed {len(chunks)} chunks for file '{file.filename}'.")

            return DocumentUploadResponse(
                filename=file.filename,
                file_size_bytes=file_size,
                chunks_indexed=len(chunks),
                status="success",
                message=f"File '{file.filename}' uploaded and indexed successfully into vector store."
            )

        except Exception as e:
            logger.exception(f"Error occurred while processing upload for '{file.filename}': {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process document: {e}"
            ) from e
