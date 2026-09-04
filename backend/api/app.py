"""FastAPI application entrypoint for serving DocChat API endpoints and web frontend."""
import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

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

# Mount frontend directory
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))

if os.path.exists(frontend_dir):
    app.mount("/app", StaticFiles(directory=frontend_dir), name="frontend_assets")

    @app.get("/", include_in_schema=False)
    async def serve_index():
        """Serves the main DocChat web UI."""
        index_path = os.path.join(frontend_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"message": "DocChat API is operational.", "docs_url": "/docs"}

    @app.get("/styles.css", include_in_schema=False)
    async def serve_css():
        return FileResponse(os.path.join(frontend_dir, "styles.css"))

    @app.get("/app.js", include_in_schema=False)
    async def serve_js():
        return FileResponse(os.path.join(frontend_dir, "app.js"))
else:
    @app.get("/")
    def root():
        return {
            "message": "DocChat API is operational.",
            "docs_url": "/docs",
            "endpoints": {
                "upload_document": "POST /api/v1/documents/upload",
                "chat": "POST /api/v1/chat"
            }
        }
