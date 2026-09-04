"""Pydantic schemas and data models for DocChat API request and response validation."""
from pydantic import BaseModel, Field


class DocumentUploadResponse(BaseModel):
    filename: str = Field(..., description="Name of the uploaded file.")
    file_size_bytes: int = Field(..., description="File size in bytes.")
    chunks_indexed: int = Field(..., description="Total number of chunks created and indexed.")
    status: str = Field(default="success", description="Status of the upload operation.")
    message: str = Field(..., description="Detailed status message.")


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="The user question for the RAG pipeline.")


class ChatResponse(BaseModel):
    question: str = Field(..., description="The original user question.")
    answer: str = Field(..., description="The context-grounded synthesized answer.")
    status: str = Field(default="success", description="Status of the chat response.")
