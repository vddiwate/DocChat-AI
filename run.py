"""Entrypoint to run the DocChat FastAPI backend application."""
import uvicorn
from backend.core.config import CONFIG
from backend.core.logger import get_logger

logger = get_logger("run")

if __name__ == "__main__":
    logger.info(f"Starting DocChat backend on {CONFIG.API_HOST}:{CONFIG.API_PORT}")
    uvicorn.run(
        "backend.api.app:app",
        host=CONFIG.API_HOST,
        port=CONFIG.API_PORT,
        reload=True
    )
