"""Centralized enterprise logging configuration with dynamic levels and timed rotation for DocChat."""
import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler
from typing import Optional

# Dynamically resolve logs directory and filename
LOGS_DIR = os.getenv("LOG_DIR", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs")))
os.makedirs(LOGS_DIR, exist_ok=True)
LOG_FILE_PATH = os.path.join(LOGS_DIR, os.getenv("LOG_FILE", "docchat.log"))

# Dynamic log level configuration (DEBUG, INFO, WARNING, ERROR, CRITICAL)
_LOG_LEVEL_STR = os.getenv("LOG_LEVEL", "INFO").strip().upper()
LOG_LEVEL = getattr(logging, _LOG_LEVEL_STR, logging.INFO)

# Retention: default 14 days of daily rotation
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "14"))


class DocChatLogger:
    """Singleton logging manager configuring unified console and file handlers."""
    _instance: Optional["DocChatLogger"] = None

    def __init__(self):
        self.root_logger = logging.getLogger("docchat")
        self.root_logger.setLevel(LOG_LEVEL)
        self.root_logger.propagate = False

        if not self.root_logger.handlers:
            # Standardized enterprise log format: timestamp, level, logger name, caller, message
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)-8s] [%(name)s:%(funcName)s:%(lineno)d] - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )

            # 1. Console Stream Handler (stdout for container log collection)
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(LOG_LEVEL)
            console_handler.setFormatter(formatter)
            self.root_logger.addHandler(console_handler)

            # 2. Daily Timed Rotating File Handler
            try:
                file_handler = TimedRotatingFileHandler(
                    filename=LOG_FILE_PATH,
                    when="midnight",
                    interval=1,
                    backupCount=LOG_BACKUP_COUNT,
                    encoding="utf-8"
                )
                file_handler.setLevel(LOG_LEVEL)
                file_handler.setFormatter(formatter)
                self.root_logger.addHandler(file_handler)
            except Exception as e:
                # Fallback if filesystem write is restricted
                self.root_logger.warning(f"Could not initialize rotating file logger at '{LOG_FILE_PATH}': {e}")

        # Silence overly verbose external third-party loggers in production
        for noisy_lib in ("httpx", "httpcore", "urllib3", "watchfiles"):
            logging.getLogger(noisy_lib).setLevel(logging.WARNING)

    @classmethod
    def get_logger(cls, module_name: str) -> logging.Logger:
        """Returns a hierarchical logger namespaced under 'docchat'."""
        if cls._instance is None:
            cls._instance = DocChatLogger()

        if not module_name or module_name == "docchat":
            return cls._instance.root_logger

        # Prevent double prefixing if module_name already begins with 'docchat.'
        clean_name = module_name
        if clean_name.startswith("docchat."):
            clean_name = clean_name[len("docchat."):]

        return logging.getLogger(f"docchat.{clean_name}")


def get_logger(module_name: str) -> logging.Logger:
    """Helper function to obtain a standardized named module logger."""
    return DocChatLogger.get_logger(module_name)
