"""Configuration parameters and settings for DocChat."""
import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class DocChatConfig:
    PROJECT_ROOT: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    VECTOR_STORE_DIR_NAME: str = os.getenv("VECTOR_STORE_DIR_NAME", "faiss_index")
    VECTOR_STORE_PATH: str = os.path.join(os.path.dirname(__file__), "..", VECTOR_STORE_DIR_NAME)

    UPLOAD_DIR_NAME: str = os.getenv("UPLOAD_DIR_NAME", "uploads")
    UPLOAD_DIR: str = os.path.join(os.path.dirname(__file__), "..", UPLOAD_DIR_NAME)

    EMBEDDING_MODEL_NAME: str = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")

    GROQ_MODEL_NAME: str = os.getenv("MODEL_NAME", "qwen/qwen3.8-27b")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.0"))

    DEFAULT_CHUNK_SIZE: int = int(os.getenv("DEFAULT_CHUNK_SIZE", "400"))
    DEFAULT_CHUNK_OVERLAP: int = int(os.getenv("DEFAULT_CHUNK_OVERLAP", "50"))
    SPLITTER_SEPARATORS: List[str] = field(default_factory=lambda: ["\n\n", "\n", " ", ""])

    DEFAULT_TOP_K: int = int(os.getenv("DEFAULT_TOP_K", "3"))
    DEFAULT_SEARCH_TYPE: str = os.getenv("DEFAULT_SEARCH_TYPE", "similarity")
    MMR_LAMBDA_MULT: float = float(os.getenv("MMR_LAMBDA_MULT", "0.5"))

    SUPPORTED_EXTENSIONS: List[str] = field(default_factory=lambda: [".pdf", ".txt"])
    DEFAULT_ENCODING: str = "utf-8"

    API_HOST: str = os.getenv("API_HOST", "127.0.0.1")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))


CONFIG = DocChatConfig()
