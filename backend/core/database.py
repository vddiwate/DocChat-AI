"""SQLAlchemy database connection and session management for DocChat."""
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from backend.core.config import CONFIG
from backend.core.logger import get_logger

logger = get_logger("core.database")

try:
    engine = create_engine(
        CONFIG.DATABASE_URL,
        pool_pre_ping=True,
        pool_size=CONFIG.DB_POOL_SIZE,
        max_overflow=CONFIG.DB_MAX_OVERFLOW,
        echo=False
    )
    logger.info(f"Database engine configured for {CONFIG.DB_NAME} at {CONFIG.DB_HOST}:{CONFIG.DB_PORT}")
except Exception as e:
    logger.exception(f"Failed to create database engine: {e}")
    raise

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative Base for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for yielding database session with automatic closure."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_connection() -> bool:
    """Verifies active connectivity to PostgreSQL database."""
    try:
        with engine.connect() as conn:
            from sqlalchemy import text
            conn.execute(text("SELECT 1"))
            logger.info("Database connection test succeeded.")
            return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False
