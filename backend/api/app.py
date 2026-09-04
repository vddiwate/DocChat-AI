"""FastAPI application entrypoint for serving DocChat API endpoints."""
import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.controllers.chat_controller import router as chat_router
from backend.api.controllers.document_controller import router as document_router
from backend.core.config import CONFIG
from backend.core.logger import get_logger

logger = get_logger("api.app")

app = FastAPI(
    title="DocChat API",
    description="Enterprise-grade layered REST API for document ingestion and conversational RAG.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(document_router)
app.include_router(chat_router)


@app.get("/")
def root():
    """Root endpoint returning service status and available documentation links."""
    return {
        "message": "DocChat API is operational.",
        "docs_url": "/docs",
        "endpoints": {
            "upload_document": "POST /api/v1/documents/upload",
            "chat": "POST /api/v1/chat"
        }
    }
