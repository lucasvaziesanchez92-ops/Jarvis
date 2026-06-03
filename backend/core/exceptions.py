"""Global exception handlers for consistent error responses."""
import json
import traceback
from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import ValidationError


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic/request validation errors with detailed field errors."""
    request_id = getattr(request.state, "request_id", "N/A")
    logger.bind(request_id=request_id).warning(
        f"Validation error: {exc.errors()}"
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "type": "validation_error",
                "message": "Input validation failed",
                "details": exc.errors(),
                "request_id": request_id,
            }
        },
    )


async def pydantic_validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Handle Pydantic model validation errors."""
    request_id = getattr(request.state, "request_id", "N/A")
    logger.bind(request_id=request_id).warning(
        f"Pydantic validation error: {exc.errors()}"
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "type": "validation_error",
                "message": "Data validation failed",
                "details": exc.errors(),
                "request_id": request_id,
            }
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unhandled exceptions."""
    request_id = getattr(request.state, "request_id", "N/A")
    logger.bind(request_id=request_id).error(
        f"Unhandled exception: {exc}\n{traceback.format_exc()}"
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "type": "internal_error",
                "message": "An unexpected error occurred. Please try again later.",
                "request_id": request_id,
            }
        },
    )


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle FastAPI HTTP exceptions."""
    from fastapi import HTTPException

    if not isinstance(exc, HTTPException):
        raise exc  # Not an HTTP exception, let generic handler deal with it

    request_id = getattr(request.state, "request_id", "N/A")
    log_level = "warning" if exc.status_code < 500 else "error"
    log_func = getattr(logger.bind(request_id=request_id), log_level)

    log_func(
        f"HTTP {exc.status_code}: {exc.detail}"
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": "http_error",
                "status_code": exc.status_code,
                "message": exc.detail,
                "request_id": request_id,
            }
        },
    )


class AppError(Exception):
    """Base class for custom application errors with structured details."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_type: str = "app_error",
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_type = error_type
        self.details = details or {}
        super().__init__(message)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Handle custom AppError exceptions."""
    request_id = getattr(request.state, "request_id", "N/A")
    log_level = "warning" if exc.status_code < 500 else "error"
    log_func = getattr(logger.bind(request_id=request_id), log_level)

    log_func(f"{exc.error_type}: {exc.message}")

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": exc.error_type,
                "message": exc.message,
                "details": exc.details,
                "request_id": request_id,
            }
        },
    )
