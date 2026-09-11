"""Document controller exposing REST API endpoints for document upload and ingestion."""
from fastapi import APIRouter, File, Request, UploadFile, status

from backend.api.models.schemas import DocumentUploadResponse
from backend.api.services.document_service import DocumentService
from backend.core.logger import get_logger

logger = get_logger("controllers.document")
router = APIRouter(prefix="/api/v1/documents", tags=["Document Management"])

document_service = DocumentService()


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(req: Request, file: UploadFile = File(...)):
    """Handles multipart file upload, disk persistence, and vector store indexing."""
    request_id = getattr(req.state, "request_id", None)
    logger.info(f"[{request_id}] Received upload request for file: {file.filename}")
    response = document_service.process_uploaded_document(file)
    if request_id:
        response.request_id = request_id
    return response
