"""Structured logging configuration using loguru + structlog."""
import sys
from pathlib import Path

from loguru import logger

from backend.config import settings

# Ensure log directory exists
LOG_DIR = Path(settings.data_dir) / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


def _fmt_console(record: dict) -> str:
    """Custom formatter that safely handles missing request_id."""
    extra = record.get("extra", {})
    if hasattr(extra, "get"):
        rid = extra.get("request_id", "N/A")
    else:
        rid = "N/A"
    time_str = record["time"].strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    level_name = record["level"].name if hasattr(record["level"], "name") else str(record["level"])
    return (
        f"<green>{time_str}</green> | "
        f"<level>{level_name: <8}</level> | "
        f"<cyan>{rid: <36}</cyan> | "
        f"<bold>{record['name']}:{record['function']}:{record['line']}</bold> - "
        f"<level>{record['message']}</level>\n"
    )


def setup_logging() -> None:
    """Configure loguru with structured JSON logging and request ID support."""
    # Remove default handler
    logger.remove()

    # Console handler — pretty format for development
    logger.add(
        sys.stderr,
        level="INFO",
        format=_fmt_console,
        colorize=True,
    )

    # File handler — JSON format for production/ELK stack
    logger.add(
        LOG_DIR / "jarvis_{time:YYYY-MM-DD}.log",
        level="DEBUG",
        rotation="1 day",
        retention="30 days",
        compression="zip",
        serialize=True,  # JSON format
        enqueue=True,  # Thread-safe
    )

    # Error-only file
    logger.add(
        LOG_DIR / "error_{time:YYYY-MM-DD}.log",
        level="ERROR",
        rotation="1 day",
        retention="90 days",
        compression="zip",
        serialize=True,
        enqueue=True,
    )


def get_logger(name: str = __name__):
    """Get a logger instance with request ID context."""
    return logger.bind(request_id="N/A")
