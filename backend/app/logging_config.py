"""Centralized logging configuration for E-Waste Management System."""
import os
import logging
from logging.handlers import RotatingFileHandler
from app.runtime import log_directory

# Get log level from environment or default to INFO.
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_DIR = log_directory()
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Create logger
logger = logging.getLogger("ewaste")
logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

# Avoid duplicate handlers
if not logger.handlers:
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    logger.addHandler(console_handler)
    console_handler.setFormatter(console_format)

    # File logging is best-effort: a console diagnostic is still available if
    # the per-user directory is unexpectedly unwritable.
    try:
        file_handler = RotatingFileHandler(
            LOG_DIR / "ewaste.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s:%(module)s:%(funcName)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
    except OSError as exc:
        logger.warning("File logging unavailable at %s: %s", LOG_DIR, exc)

# Convenience functions
def get_logger(name: str = "ewaste") -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(name)
