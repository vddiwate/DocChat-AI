"""FastAPI application entrypoint for serving DocChat API endpoints and web frontend."""
import datetime
import os
import sys
import uuid
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.api.controllers.chat_controller import router as chat_router
from backend.api.controllers.document_controller import router as document_router
from backend.api.models.schemas import ErrorResponse
from backend.core.config import CONFIG
from backend.core.logger import get_logger

logger = get_logger("api.app")

app = FastAPI(
    title="DocChat Enterprise API",
    description="Enterprise-grade layered REST API for document ingestion and conversational RAG.",
    version="1.0.0"
)

# 1. CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"]
)


# 2. Enterprise Correlation ID Middleware
@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    """Assigns or propagates a unique correlation ID (X-Request-ID) across all logs and response headers."""
    request_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:12]}"
    request.state.request_id = request_id

    logger.info(f"[{request_id}] --> {request.method} {request.url.path}")
    start_time = datetime.datetime.now(datetime.timezone.utc)

    try:
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        duration_ms = (datetime.datetime.now(datetime.timezone.utc) - start_time).total_seconds() * 1000
        logger.info(f"[{request_id}] <-- {request.method} {request.url.path} {response.status_code} ({duration_ms:.1f}ms)")
        return response
    except Exception as exc:
        duration_ms = (datetime.datetime.now(datetime.timezone.utc) - start_time).total_seconds() * 1000
        logger.exception(f"[{request_id}] Unhandled exception in middleware: {exc} ({duration_ms:.1f}ms)")
        raise


# 3. Global Exception Handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Standardized handler for HTTPExceptions (400, 404, etc.)."""
    request_id = getattr(request.state, "request_id", None) or f"req_{uuid.uuid4().hex[:12]}"
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    # Map status code to standard error code
    error_codes = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "RESOURCE_NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        429: "TOO_MANY_REQUESTS",
        500: "INTERNAL_SERVER_ERROR",
        503: "SERVICE_UNAVAILABLE"
    }
    error_code = error_codes.get(exc.status_code, "HTTP_ERROR")

    # If detail is dict, unpack it
    if isinstance(exc.detail, dict):
        message = exc.detail.get("message", "An HTTP error occurred.")
        details = exc.detail.get("details", None)
        error_code = exc.detail.get("error_code", error_code)
    else:
        message = str(exc.detail) if exc.detail else "An error occurred."
        details = None

    error_payload = ErrorResponse(
        success=False,
        status_code=exc.status_code,
        error_code=error_code,
        message=message,
        request_id=request_id,
        path=request.url.path,
        timestamp=now_iso,
        details=details
    )
    logger.warning(f"[{request_id}] HTTPException [{exc.status_code}]: {message} at {request.url.path}")

    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload.model_dump(),
        headers={"X-Request-ID": request_id}
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Standardized handler for schema and validation errors (422)."""
    request_id = getattr(request.state, "request_id", None) or f"req_{uuid.uuid4().hex[:12]}"
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    formatted_errors = []
    for err in exc.errors():
        field = " -> ".join(str(loc) for loc in err.get("loc", []))
        formatted_errors.append({
            "field": field,
            "message": err.get("msg", "Validation error"),
            "type": err.get("type", "value_error")
        })

    error_payload = ErrorResponse(
        success=False,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error_code="VALIDATION_ERROR",
        message="Request validation failed. Please check input parameters.",
        request_id=request_id,
        path=request.url.path,
        timestamp=now_iso,
        details=formatted_errors
    )
    logger.warning(f"[{request_id}] Validation error at {request.url.path}: {formatted_errors}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_payload.model_dump(),
        headers={"X-Request-ID": request_id}
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch-all handler ensuring no raw tracebacks or unformatted errors leak to client."""
    request_id = getattr(request.state, "request_id", None) or f"req_{uuid.uuid4().hex[:12]}"
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    logger.exception(f"[{request_id}] Unhandled server exception on {request.url.path}: {exc}")

    error_payload = ErrorResponse(
        success=False,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code="INTERNAL_SERVER_ERROR",
        message="An unexpected server error occurred. Reference the request_id for support diagnostics.",
        request_id=request_id,
        path=request.url.path,
        timestamp=now_iso,
        details=str(exc) if os.getenv("ENVIRONMENT") == "development" else None
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_payload.model_dump(),
        headers={"X-Request-ID": request_id}
    )


# 4. Include Routers
app.include_router(document_router)
app.include_router(chat_router)

# 5. Mount Static Frontend Assets
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))

if os.path.exists(frontend_dir):
    app.mount("/app", StaticFiles(directory=frontend_dir), name="frontend_assets")

    @app.get("/", include_in_schema=False)
    async def serve_index():
        """Serves the main DocChat web UI."""
        index_path = os.path.join(frontend_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"message": "DocChat Enterprise API is operational.", "docs_url": "/docs"}

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
            "message": "DocChat Enterprise API is operational.",
            "docs_url": "/docs",
            "endpoints": {
                "upload_document": "POST /api/v1/documents/upload",
                "chat": "POST /api/v1/chat (supports stream=true/false)"
            }
        }
