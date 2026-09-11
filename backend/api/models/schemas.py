"""Pydantic schemas and data models for DocChat API request and response validation."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standardized enterprise error response schema (RFC 7807 problem details aligned)."""
    success: bool = Field(default=False, description="Indicates unsuccessful request execution.")
    status_code: int = Field(..., description="HTTP status code associated with the error.")
    error_code: str = Field(..., description="Machine-readable unique error code identifier.")
    message: str = Field(..., description="Human-readable explanation of the error.")
    request_id: Optional[str] = Field(default=None, description="Unique correlation ID for tracing and diagnostics.")
    path: Optional[str] = Field(default=None, description="API endpoint path where the error occurred.")
    timestamp: str = Field(..., description="ISO 8601 formatted timestamp of the error event.")
    details: Optional[Any] = Field(default=None, description="Granular error details or validation field breakdowns.")


class DocumentUploadResponse(BaseModel):
    """Schema for document upload and indexing response."""
    success: bool = Field(default=True, description="Indicates successful upload operation.")
    filename: str = Field(..., description="Name of the uploaded file.")
    file_size_bytes: int = Field(..., description="File size in bytes.")
    chunks_indexed: int = Field(..., description="Total number of chunks created and indexed.")
    status: str = Field(default="success", description="Status of the upload operation.")
    message: str = Field(..., description="Detailed status message.")
    request_id: Optional[str] = Field(default=None, description="Unique correlation ID for tracing.")


class ChatRequest(BaseModel):
    """Unified chat request schema supporting both streaming and standard completion."""
    question: str = Field(..., min_length=1, description="The user question for the RAG pipeline.")
    stream: bool = Field(default=False, description="Set to True for real-time SSE token streaming, False for standard JSON.")


class ChatResponse(BaseModel):
    """Schema for synchronous chat answers."""
    success: bool = Field(default=True, description="Indicates successful chat completion.")
    question: str = Field(..., description="The original user question.")
    answer: str = Field(..., description="The context-grounded synthesized answer.")
    status: str = Field(default="success", description="Status of the chat response.")
    request_id: Optional[str] = Field(default=None, description="Unique correlation ID for tracing.")
