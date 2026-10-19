"""Configuration parameters and settings for DocChat."""
import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

from sqlalchemy.engine import URL

load_dotenv()


def _parse_list(env_key: str, fallback: str = "") -> List[str]:
    """Parses a comma-separated string from environment variables into a list."""
    val = os.getenv(env_key, fallback)
    return [item.strip() for item in val.split(",") if item.strip()]


def _parse_separators(env_key: str, fallback: str = r"\n\n,\n, ,") -> List[str]:
    """Parses text splitter separators from environment variable with escaped newlines/tabs."""
    val = os.getenv(env_key, fallback)
    return [
        s.replace(r"\n", "\n").replace(r"\t", "\t").replace(r"\r", "\r")
        for s in val.split(",")
    ]


@dataclass(frozen=True)
class DocChatConfig:
    PROJECT_ROOT: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    # Storage Paths (Loaded dynamically from .env with generic defaults)
    VECTOR_STORE_DIR_NAME: str = os.getenv("VECTOR_STORE_DIR_NAME", "faiss_index")
    VECTOR_STORE_PATH: str = os.path.join(os.path.dirname(__file__), "..", os.getenv("VECTOR_STORE_DIR_NAME", "faiss_index"))

    UPLOAD_DIR_NAME: str = os.getenv("UPLOAD_DIR_NAME", "uploads")
    UPLOAD_DIR: str = os.path.join(os.path.dirname(__file__), "..", os.getenv("UPLOAD_DIR_NAME", "uploads"))

    # Embeddings & LLM Settings (Loaded dynamically from .env)
    EMBEDDING_MODEL_NAME: str = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "").strip()
    GROQ_MODEL_NAME: str = (os.getenv("GROQ_MODEL_NAME") or os.getenv("MODEL_NAME") or "").strip()
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.0"))

    # Text Splitting & Vector Retrieval Settings (Loaded dynamically from .env with generic defaults)
    DEFAULT_CHUNK_SIZE: int = int(os.getenv("DEFAULT_CHUNK_SIZE", "400"))
    DEFAULT_CHUNK_OVERLAP: int = int(os.getenv("DEFAULT_CHUNK_OVERLAP", "50"))
    SPLITTER_SEPARATORS: List[str] = field(default_factory=lambda: _parse_separators("SPLITTER_SEPARATORS"))

    DEFAULT_TOP_K: int = int(os.getenv("DEFAULT_TOP_K", "3"))
    DEFAULT_SEARCH_TYPE: str = os.getenv("DEFAULT_SEARCH_TYPE", "similarity")
    MMR_LAMBDA_MULT: float = float(os.getenv("MMR_LAMBDA_MULT", "0.5"))

    # File Ingestion Settings (Loaded dynamically from .env with generic defaults)
    SUPPORTED_EXTENSIONS: List[str] = field(
        default_factory=lambda: _parse_list("SUPPORTED_EXTENSIONS", ".pdf,.txt")
    )
    DEFAULT_ENCODING: str = os.getenv("DEFAULT_ENCODING", "utf-8")

    # API Server Network Settings (Loaded dynamically from .env with generic defaults)
    API_HOST: str = os.getenv("API_HOST", "127.0.0.1")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    API_RELOAD: bool = os.getenv("API_RELOAD", "true").lower() in ("true", "1", "yes")

    # Database Configuration (Loaded dynamically from .env)
    DB_USER: str = os.getenv("DB_USER", "").strip()
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "").strip()
    DB_HOST: str = os.getenv("DB_HOST", "").strip()
    DB_PORT: int = int(os.getenv("DB_PORT", "5432").strip() if os.getenv("DB_PORT") else 5432)
    DB_NAME: str = os.getenv("DB_NAME", "").strip()
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "10"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "20"))

    # Logging Settings (Loaded dynamically from .env with production defaults)
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    LOG_BACKUP_COUNT: int = int(os.getenv("LOG_BACKUP_COUNT", "14"))

    def __post_init__(self):
        """Validates genuinely required settings at startup."""
        if not self.GROQ_API_KEY:
            raise ValueError(
                "Required setting 'GROQ_API_KEY' is missing or empty. "
                "Please configure GROQ_API_KEY in your .env file."
            )
        if not self.GROQ_MODEL_NAME:
            raise ValueError(
                "Required setting 'MODEL_NAME' (or 'GROQ_MODEL_NAME') is missing or empty. "
                "Please configure MODEL_NAME in your .env file."
            )
        
        # In production, either a full DATABASE_URL or individual DB parameters must be present
        raw_db_url = os.getenv("DATABASE_URL")
        if not raw_db_url or not raw_db_url.strip():
            if not self.DB_NAME:
                raise ValueError(
                    "Required database setting 'DB_NAME' (or 'DATABASE_URL') is missing. "
                    "Please configure DB_NAME in your .env file."
                )
            if not self.DB_USER:
                raise ValueError(
                    "Required database setting 'DB_USER' (or 'DATABASE_URL') is missing. "
                    "Please configure DB_USER in your .env file."
                )
            if not self.DB_HOST:
                raise ValueError(
                    "Required database setting 'DB_HOST' (or 'DATABASE_URL') is missing. "
                    "Please configure DB_HOST in your .env file."
                )

    @property
    def DATABASE_URL(self) -> str:
        """Constructs safe connection URL or uses full DATABASE_URL supplied in production environment."""
        raw_db_url = os.getenv("DATABASE_URL")
        if raw_db_url and raw_db_url.strip():
            return raw_db_url.strip()

        return URL.create(
            drivername="postgresql",
            username=self.DB_USER,
            password=self.DB_PASSWORD or None,
            host=self.DB_HOST,
            port=self.DB_PORT,
            database=self.DB_NAME,
        ).render_as_string(hide_password=False)


CONFIG = DocChatConfig()
