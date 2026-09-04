"""Centralized logging configuration with timed rotation for DocChat."""
import os
import logging
from logging.handlers import TimedRotatingFileHandler

LOGS_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(LOGS_DIR, exist_ok=True)
LOG_FILE_PATH = os.path.join(LOGS_DIR, "docchat.log")


class DocChatLogger:
    _instance = None

    def __init__(self):
        """Initializes logger instance with console and rotating file handlers."""
        self.logger = logging.getLogger("docchat")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

        if not self.logger.handlers:
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [%(name)s.%(funcName)s:%(lineno)d] - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )

            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

            file_handler = TimedRotatingFileHandler(
                filename=LOG_FILE_PATH,
                when="midnight",
                interval=1,
                backupCount=2,
                encoding="utf-8"
            )
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    @classmethod
    def get_logger(cls, module_name: str) -> logging.Logger:
        """Returns a named logger instance for the given module."""
        if cls._instance is None:
            cls._instance = DocChatLogger()
        return logging.getLogger(f"docchat.{module_name}")


def get_logger(module_name: str) -> logging.Logger:
    """Helper function to get a named module logger."""
    return DocChatLogger.get_logger(module_name)
