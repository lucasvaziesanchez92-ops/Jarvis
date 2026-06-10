"""Structured logging configuration using loguru + structlog."""
import sys
from pathlib import Path

from loguru import logger

from backend.config import settings

# Ensure log directory exists
LOG_DIR = Path(settings.data_dir) / "logs"
try:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
except PermissionError:
    pass  # Railway runtime filesystem, loguru writes to stderr anyway


def _fmt_console(record: dict) -> str:
    """Custom formatter that safely handles missing request_id, JSON in messages, and angle brackets in function names.

    CRITICAL: must NEVER raise — if it raises, loguru's internal format() call
    propagates the exception into the request path and produces 500s on what
    should be a clean error log. We catch everything and return a plain string.
    """
    try:
        import re
        extra = record.get("extra", {})
        if hasattr(extra, "get"):
            rid = extra.get("request_id", "N/A")
        else:
            rid = "N/A"
        time_str = record["time"].strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        level_name = record["level"].name if hasattr(record["level"], "name") else str(record["level"])
        raw_msg = str(record["message"])
        # Escape braces so loguru's internal format() doesn't try to interpret
        # JSON-like substrings in the message as placeholders.
        safe_msg = raw_msg.replace("{", "{{").replace("}", "}}")
        func_name = str(record.get("function", "?")).replace("<", r"\<").replace(">", r"\>")
        mod_name = str(record.get("name", "N/A"))
        
        exception_text = ""
        if record.get("exception"):
            import traceback
            type_, value_, tb_ = record["exception"]
            exception_text = "".join(traceback.format_exception(type_, value_, tb_))
            exception_text = "\n" + exception_text.replace("{", "{{").replace("}", "}}").replace("<", r"\<").replace(">", r"\>")

        return (
            f"<green>{time_str}</green> | "
            f"<level>{level_name: <8}</level> | "
            f"<cyan>{rid: <36}</cyan> | "
            f"<bold>{mod_name}:{func_name}:{record['line']}</bold> - "
            f"<level>{safe_msg}</level>{exception_text}\n"
        )
    except Exception:
        # If ANYTHING in formatting fails, return a minimal safe string.
        # This MUST NOT raise — a failure here would propagate into the
        # request path and turn normal error logs into 500 responses.
        try:
            return f"[log-fmt-error] {str(record.get('message', ''))[:500]}\n"
        except Exception:
            return "[log-fmt-error] <unprintable>\n"


def setup_logging() -> None:
    """Configure loguru with structured JSON logging and request ID support.

    catch=True on all handlers so a malformed log message (e.g. containing
    JSON-like `{}` that confuses loguru's internal format()) can NEVER
    propagate into the request path. Without this, an error during logging
    turns into a 500 response — see git history of the OOM saga.

    On Railway (and any ephemeral container) we disable file logging
    to avoid wasting disk I/O on files that get nuked on every redeploy.
    Set DISABLE_FILE_LOGGING=false to force-enable.
    """
    # Remove default handler
    logger.remove()

    is_railway = bool(os.environ.get("RAILWAY_ENVIRONMENT_NAME")) or bool(os.environ.get("RAILWAY_PROJECT_ID"))
    disable_file = os.environ.get("DISABLE_FILE_LOGGING", "true" if is_railway else "false").lower() in ("1", "true", "yes")

    # Console handler — pretty format for development
    logger.add(
        sys.stderr,
        level="INFO",
        format=_fmt_console,
        colorize=True,
        catch=True,  # NEVER raise from a log call
    )

    if disable_file:
        logger.info("File logging disabled (Railway mode).")
        return

    # File handler — JSON format for production/ELK stack
    logger.add(
        LOG_DIR / "jarvis_{time:YYYY-MM-DD}.log",
        level="DEBUG",
        rotation="1 day",
        retention="30 days",
        compression="zip",
        serialize=True,  # JSON format
        enqueue=True,    # Thread-safe
        catch=True,
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
        catch=True,
    )


def get_logger(name: str = __name__):
    """Get a logger instance with request ID context."""
    return logger.bind(request_id="N/A")
