"""Entrypoint to run the DocChat FastAPI backend application."""
import uvicorn
from backend.core.config import CONFIG
from backend.core.logger import get_logger

logger = get_logger("run")


def log_startup_banner():
    """Logs the platform banner and clickable access URLs using standard logger."""
    ui_url = f"http://{CONFIG.API_HOST}:{CONFIG.API_PORT}/"
    docs_url = f"http://{CONFIG.API_HOST}:{CONFIG.API_PORT}/docs"
    redoc_url = f"http://{CONFIG.API_HOST}:{CONFIG.API_PORT}/redoc"

    logger.info("=" * 68)
    logger.info("  DocChat Enterprise AI Platform Starting...")
    logger.info(f"  Web Application UI  : {ui_url}")
    logger.info(f"  Swagger API Docs    : {docs_url}")
    logger.info(f"  ReDoc Documentation : {redoc_url}")
    logger.info("=" * 68)


if __name__ == "__main__":
    log_startup_banner()
    uvicorn.run(
        "backend.api.app:app",
        host=CONFIG.API_HOST,
        port=CONFIG.API_PORT,
        reload=True
    )
